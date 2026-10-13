#!/usr/bin/env python3
"""Folder-confined Drive uploads with explicit credential-path confirmation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import shutil
import tempfile

FOLDER = 'application/vnd.google-apps.folder'
FIELDS = 'id,name,mimeType,parents,driveId,trashed,capabilities,webViewLink,md5Checksum,size'
SCOPES = ['https://www.googleapis.com/auth/drive']


class UploadError(Exception):
    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise UploadError('Supply an exact Drive folder/file ID, not a name or URL.')
    return value


def detect(env=None):
    """Check path metadata only; do not parse keys or authenticate to Google."""
    env = os.environ if env is None else env
    candidates = []
    for name in ('GDRIVE_SA_KEY_FILE', 'GOOGLE_APPLICATION_CREDENTIALS'):
        if env.get(name):
            path = Path(env[name]).expanduser().resolve()
            candidates.append({'variable': name, 'path': str(path), 'exists': path.is_file()})
    return {'action': 'detected', 'credential_candidates': candidates,
            'root_folder_id': env.get('GDRIVE_ROOT_FOLDER_ID'),
            'python': env.get('GDRIVE_PYTHON'),
            'note': 'Candidates are not proof of a working connection. Ask the user to confirm a path before doctor/upload.'}


def build_service(key):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from google_auth_httplib2 import AuthorizedHttp
        import httplib2
    except ImportError:
        raise UploadError('Install requirements.txt in the selected Python venv.', 5)
    try:
        creds = service_account.Credentials.from_service_account_file(str(key), scopes=SCOPES)
        service = build('drive', 'v3', http=AuthorizedHttp(creds, http=httplib2.Http(timeout=60)),
                        cache_discovery=False)
        return service, creds.service_account_email
    except Exception:
        # Do not dump credential parsing errors or secret content into logs.
        raise UploadError('Cannot load the confirmed service-account credential file. Check its type and validity.', 5)


def make_media(path):
    from googleapiclient.http import MediaFileUpload
    return MediaFileUpload(str(path), chunksize=8 * 1024 * 1024, resumable=True)


def checksum(path):
    md5 = hashlib.md5()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            md5.update(chunk)
    return md5.hexdigest()


class Workspace:
    def __init__(self, service, root_id):
        self.api = service.files()
        self.root_id = valid_id(root_id)
        self.root = self.get(root_id)
        self.folder(self.root)
        self.drive_id = self.root.get('driveId')
        if not self.drive_id:
            raise UploadError('Root is in My Drive. Service-account new-file uploads require a Shared Drive target.', 6)

    def get(self, id):
        return self.api.get(fileId=valid_id(id), fields=FIELDS, supportsAllDrives=True).execute(num_retries=3)

    def folder(self, item):
        if item.get('trashed') or item.get('mimeType') != FOLDER:
            raise UploadError('Destination must be an existing, untrashed folder, not a shortcut.', 6)
        if not item.get('capabilities', {}).get('canAddChildren'):
            raise UploadError('Service account cannot add files/subfolders here. Check the direct folder grant.', 6)

    def confined(self, item):
        pending, seen = [item], set()
        while pending:
            node = pending.pop()
            id = node['id']
            if id in seen:
                continue
            seen.add(id)
            if node.get('trashed') or node.get('driveId') != self.drive_id:
                continue
            if id == self.root_id:
                return
            if len(seen) > 100:
                raise UploadError('Folder ancestry exceeds the supported depth; refusing an unverified destination.', 6)
            pending.extend(self.get(parent) for parent in node.get('parents', []))
        raise UploadError('Target is outside the configured root folder.', 6)

    def children(self, parent):
        token = None
        result = []
        while True:
            response = self.api.list(q=f"'{valid_id(parent)}' in parents and trashed = false",
                # user corpus includes directly shared items; drive corpus can
                # require drive membership, which would weaken folder isolation.
                corpora='user', spaces='drive',
                supportsAllDrives=True, includeItemsFromAllDrives=True,
                fields=f'nextPageToken,incompleteSearch,files({FIELDS})', pageSize=100,
                **({'pageToken': token} if token else {})).execute(num_retries=3)
            if response.get('incompleteSearch'):
                raise UploadError('Drive listing was incomplete; cannot safely resolve folders or check duplicate names.', 6)
            result.extend(response.get('files', []))
            token = response.get('nextPageToken')
            if not token:
                return result

    def destination(self, folder_id=None, subfolder=None, create=False):
        if folder_id and subfolder:
            raise UploadError('Use either --folder-id or --subfolder, not both.')
        current = self.get(folder_id or self.root_id)
        self.folder(current)
        self.confined(current)
        parts = [] if subfolder is None else subfolder.split('/')
        if any(not p.strip() or p in ('.', '..') or '\\' in p or '\x00' in p for p in parts):
            raise UploadError('Subfolder must be a relative path with nonempty names, without . or .. components.')
        missing = []
        for part in parts:
            if missing:
                missing.append(part)
                continue
            matches = [c for c in self.children(current['id']) if c['name'] == part]
            if len(matches) > 1:
                raise UploadError(f'Ambiguous subfolder name: {part}. Supply an exact folder ID.', 3)
            if matches:
                current = matches[0]
                self.folder(current)
                self.confined(current)
            elif create:
                missing.append(part)
            else:
                raise UploadError(f'Missing subfolder: {part}. Use --create-subfolders only when explicitly authorized.', 3)
        return {'folder_id': current['id'], 'folder_name': current['name'],
                'subfolder': subfolder, 'planned_subfolders': missing, 'drive_id': self.drive_id}

    def materialize(self, destination):
        parent = destination['folder_id']
        for name in destination['planned_subfolders']:
            # Recheck after preview: a folder may have appeared concurrently.
            matches = [c for c in self.children(parent) if c['name'] == name]
            if len(matches) > 1:
                raise UploadError(f'Ambiguous subfolder name: {name}.', 3)
            if matches:
                item = matches[0]
            else:
                self.check_parent(parent)
                item = self.api.create(body={'name': name, 'mimeType': FOLDER, 'parents': [parent]},
                    fields=FIELDS, supportsAllDrives=True).execute(num_retries=0)
                # Fresh metadata includes authoritative capabilities/parents.
                item = self.get(item['id'])
            self.folder(item)
            self.confined(item)
            parent = item['id']
        self.check_parent(parent)
        return parent

    def check_parent(self, parent):
        item = self.get(parent)
        self.folder(item)
        self.confined(item)

    def upload(self, file, folder_id=None, subfolder=None, create_subfolders=False,
               replace_file_id=None, dry_run=False, expected_md5=None):
        src = Path(file).expanduser().resolve()
        if not src.is_file():
            raise UploadError('Local upload file does not exist or is not a regular file.')
        if expected_md5 is not None and not re.fullmatch(r'[a-fA-F0-9]{32}', expected_md5):
            raise UploadError('--expected-md5 must be the 32-character digest from the approved dry-run.')
        with tempfile.TemporaryDirectory(prefix='gdrive-upload-') as staging:
            snapshot = Path(staging) / src.name
            shutil.copyfile(src, snapshot)
            before = checksum(snapshot)
            if expected_md5 is not None and before != expected_md5.lower():
                raise UploadError('Local file changed since the approved dry-run; preview and confirm it again.')
            return self._upload_snapshot(src, snapshot, before, folder_id, subfolder,
                                         create_subfolders, replace_file_id, dry_run)

    def _upload_snapshot(self, src, snapshot, before, folder_id, subfolder,
                         create_subfolders, replace_file_id, dry_run):
        info = snapshot.stat()
        target = self.destination(folder_id, subfolder, create_subfolders)
        replacement = None
        if replace_file_id:
            if target['planned_subfolders']:
                raise UploadError('An existing replacement cannot be inside a not-yet-created folder.')
            replacement = self.get(replace_file_id)
            self.confined(replacement)
            if target['folder_id'] not in replacement.get('parents', []):
                raise UploadError('Replacement file must be directly inside the selected destination.', 6)
            if replacement.get('mimeType', '').startswith('application/vnd.google-apps.'):
                raise UploadError('Only ordinary uploaded files can be replaced; native Google documents are not supported.')
            if not replacement.get('capabilities', {}).get('canEdit'):
                raise UploadError('Service account cannot edit the selected file.', 6)
        name = replacement['name'] if replacement else src.name
        duplicates = [] if target['planned_subfolders'] else [c['id'] for c in self.children(target['folder_id']) if c['name'] == name]
        plan = dict(target, action='dry-run', local_file=str(src), filename=name,
                    bytes=info.st_size, md5=before, replace_file_id=replace_file_id,
                    same_name_file_ids=duplicates)
        if dry_run:
            return plan
        if duplicates and not replacement:
            raise UploadError('Same-name file already exists; no upload performed. IDs: ' + ', '.join(duplicates), 4)
        parent = self.materialize(target)
        if not replacement and any(c['name'] == name for c in self.children(parent)):
            raise UploadError('Same-name file appeared before upload; stopped without overwriting.', 4)
        media = make_media(snapshot)
        try:
            return self._send(media, parent, name, before, replacement, replace_file_id)
        finally:
            # MediaFileUpload owns an open handle; close before removing staging,
            # including on errors (required for Windows temporary-file cleanup).
            stream = getattr(media, '_fd', None)
            if stream is not None:
                stream.close()

    def _send(self, media, parent, name, before, replacement, replace_file_id):
        self.check_parent(parent)
        if replacement:
            # Re-read just before replacement in case another user moved it.
            item = self.get(replace_file_id)
            self.confined(item)
            if parent not in item.get('parents', []) or not item.get('capabilities', {}).get('canEdit'):
                raise UploadError('Replacement moved or permissions changed; upload stopped.', 6)
            request = self.api.update(fileId=replace_file_id, media_body=media,
                fields='id,name,webViewLink,md5Checksum,size', supportsAllDrives=True)
        else:
            request = self.api.create(body={'name': name, 'parents': [parent]}, media_body=media,
                fields='id,name,webViewLink,md5Checksum,size', supportsAllDrives=True)
        try:
            result = None
            while result is None:
                _, result = request.next_chunk(num_retries=3)
        except Exception:
            raise UploadError('Upload interrupted; outcome may be uncertain. Check the exact destination/name before retrying. Planned subfolders may already exist.', 1)
        if result.get('md5Checksum') != before:
            raise UploadError('File was written but checksum validation failed. Inspect file ID ' + result['id'] + ' before retrying.', 1)
        return {'action': 'replaced' if replacement else 'uploaded', 'file_id': result['id'],
                'filename': result['name'], 'folder_id': parent, 'md5': before,
                'link': result.get('webViewLink') or f"https://drive.google.com/file/d/{result['id']}/view"}


def run_command(command, confirmed_key=None, root_id=None, **kwargs):
    if command == 'detect':
        return detect()
    if command == 'upload' and not kwargs.get('dry_run') and not kwargs.get('expected_md5'):
        raise UploadError('Real upload requires --expected-md5 from the approved dry-run.')
    if not confirmed_key:
        raise UploadError('First run detect, then ask the user to confirm the credential path. Pass it as --confirmed-key-file.')
    key = Path(confirmed_key).expanduser().resolve()
    if not key.is_file():
        raise UploadError('Confirmed credential path does not point to an existing file.')
    root = root_id or os.environ.get('GDRIVE_ROOT_FOLDER_ID')
    if not root:
        raise UploadError('Set GDRIVE_ROOT_FOLDER_ID to the approved root folder ID.')
    service, email = build_service(key)
    work = Workspace(service, root)
    if command == 'doctor':
        return {'action': 'checked', 'service_account_email': email, 'root_folder_id': root,
                'root_folder_name': work.root['name'], 'drive_id': work.drive_id,
                'can_add_children': True, 'note': 'Read-only check; this does not prove a live upload or Google Docs editing.'}
    if not kwargs.get('file'):
        raise UploadError('Supply the exact final local file path.')
    return work.upload(**kwargs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['detect', 'doctor', 'upload'])
    parser.add_argument('file', nargs='?')
    parser.add_argument('--confirmed-key-file', help='Credential PATH explicitly confirmed by the user; never a key value.')
    parser.add_argument('--root-folder-id', help='Approved root ID (otherwise GDRIVE_ROOT_FOLDER_ID).')
    parser.add_argument('--folder-id', help='Exact descendant folder ID; cannot escape the configured root.')
    parser.add_argument('--subfolder', help='Exact relative folder path under the configured root.')
    parser.add_argument('--create-subfolders', action='store_true', help='Explicitly authorize creating missing path components.')
    parser.add_argument('--replace-file-id', help='Explicit ordinary-file content replacement; no automatic overwrite.')
    parser.add_argument('--dry-run', action='store_true', help='Preview upload and planned folders without writing.')
    parser.add_argument('--expected-md5', help='Approved dry-run digest; required for real uploads.')
    args = parser.parse_args(argv)
    try:
        result = run_command(args.command, confirmed_key=args.confirmed_key_file, root_id=args.root_folder_id,
            file=args.file, folder_id=args.folder_id, subfolder=args.subfolder,
            create_subfolders=args.create_subfolders, replace_file_id=args.replace_file_id,
            dry_run=args.dry_run, expected_md5=args.expected_md5)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except UploadError as error:
        print(json.dumps({'error': str(error), 'exit_code': error.code}, ensure_ascii=False), file=sys.stderr)
        return error.code
    except Exception as error:
        status = getattr(getattr(error, 'resp', None), 'status', None)
        print(json.dumps({'error': 'Drive request failed. Check credential validity, API enablement, folder ID, sharing restrictions and network.',
                          'http_status': status, 'exit_code': 1}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
