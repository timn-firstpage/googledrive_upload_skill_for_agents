import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'gdrive_upload.py'
if SCRIPT.exists():
    spec = importlib.util.spec_from_file_location('gdrive_upload', SCRIPT)
    u = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(u)
else:
    u = None


class Request:
    def __init__(self, fn): self.fn = fn
    def execute(self, **kwargs): return self.fn()
    def next_chunk(self, **kwargs): return None, self.fn()


class Drive:
    """In-memory boundary for the external Drive API; no real credentials/network."""
    def __init__(self):
        self.items = {
            'root': folder('root'),
            'inside': folder('inside', 'root'),
            'outside': folder('outside'),
        }
        self.writes = []
    def files(self): return self
    def get(self, fileId, **kwargs):
        return Request(lambda: dict(self.items[fileId]))
    def list(self, q, **kwargs):
        parent = re.search(r"'([^']+)' in parents", q).group(1)
        return Request(lambda: {'files': [dict(v) for v in self.items.values()
            if parent in v.get('parents', []) and not v.get('trashed')]})
    def create(self, body, media_body=None, **kwargs):
        def run():
            item = dict(body, id=f'new{len(self.writes)}', driveId='drive')
            if item.get('mimeType') == 'application/vnd.google-apps.folder':
                item['capabilities'] = {'canAddChildren': True}
            if media_body:
                item['md5Checksum'] = hashlib.md5(Path(media_body).read_bytes()).hexdigest()
            self.items[item['id']] = item
            self.writes.append(('create', item))
            return item
        return Request(run)
    def update(self, fileId, media_body, **kwargs):
        def run():
            self.writes.append(('update', fileId))
            item = self.items[fileId]
            item['md5Checksum'] = hashlib.md5(Path(media_body).read_bytes()).hexdigest()
            return dict(item)
        return Request(run)


def folder(id, parent=None, **kwargs):
    return dict(id=id, name=id, mimeType='application/vnd.google-apps.folder',
                driveId='drive', parents=[parent] if parent else [],
                capabilities={'canAddChildren': True}, **kwargs)


class Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(u, 'upload helper not implemented yet')
        self.tmp = tempfile.TemporaryDirectory(dir=SCRIPT.parent.parent)
        self.addCleanup(self.tmp.cleanup)
        temp_patch = patch.object(tempfile, 'tempdir', str(SCRIPT.parent.parent))
        temp_patch.start()
        self.addCleanup(temp_patch.stop)
        self.file = Path(self.tmp.name) / 'report.txt'
        self.file.write_text('finished audit', encoding='utf-8')
        self.drive = Drive()
        self.work = u.Workspace(self.drive, 'root')

    def test_discovery_does_not_read_key_contents(self):
        key = Path(self.tmp.name) / 'sa.json'
        key.write_text('not a credential; discovery must not parse it')
        with patch.object(Path, 'read_text', side_effect=AssertionError('secret read')):
            found = u.detect({'GDRIVE_SA_KEY_FILE': str(key)})
        self.assertEqual(found['credential_candidates'][0]['path'], str(key.resolve()))
        self.assertTrue(found['credential_candidates'][0]['exists'])

    def test_discovery_reports_both_different_credentials(self):
        found = u.detect({'GDRIVE_SA_KEY_FILE': '/a.json', 'GOOGLE_APPLICATION_CREDENTIALS': '/b.json'})
        self.assertEqual(len(found['credential_candidates']), 2)

    def test_no_confirmation_no_authentication(self):
        with patch.object(u, 'build_service', side_effect=AssertionError('auth attempted')):
            with self.assertRaises(u.UploadError):
                u.run_command('doctor', confirmed_key=None, root_id='root')

    def test_reject_my_drive(self):
        del self.drive.items['root']['driveId']
        with self.assertRaises(u.UploadError): u.Workspace(self.drive, 'root')

    def test_reject_nonfolder_root(self):
        self.drive.items['root']['mimeType'] = 'text/plain'
        with self.assertRaises(u.UploadError): u.Workspace(self.drive, 'root')

    def test_reject_readonly_root(self):
        self.drive.items['root']['capabilities']['canAddChildren'] = False
        with self.assertRaises(u.UploadError): u.Workspace(self.drive, 'root')

    def test_accept_descendant(self):
        self.assertEqual(self.work.destination(folder_id='inside')['folder_id'], 'inside')

    def test_reject_sibling_even_in_same_drive(self):
        with self.assertRaises(u.UploadError): self.work.destination(folder_id='outside')

    def test_reject_shortcut(self):
        self.drive.items['inside']['mimeType'] = 'application/vnd.google-apps.shortcut'
        with self.assertRaises(u.UploadError): self.work.destination(folder_id='inside')

    def test_reject_different_shared_drive(self):
        self.drive.items['inside']['driveId'] = 'other'
        with self.assertRaises(u.UploadError): self.work.destination(folder_id='inside')

    def test_reject_cycle(self):
        self.drive.items['outside']['parents'] = ['outside']
        with self.assertRaises(u.UploadError): self.work.destination(folder_id='outside')

    def test_dry_run_never_creates_subfolders(self):
        result = self.work.upload(self.file, subfolder='audit/run', create_subfolders=True, dry_run=True)
        self.assertEqual(result['planned_subfolders'], ['audit', 'run'])
        self.assertEqual(result['local_file'], str(self.file.resolve()))
        self.assertEqual(self.drive.writes, [])

    def test_missing_subfolder_requires_explicit_creation(self):
        with self.assertRaises(u.UploadError): self.work.destination(subfolder='audit')

    def test_reject_path_traversal_and_empty_components(self):
        for path in ('../audit', '/audit', 'audit//run', 'audit/', 'audit\\run'):
            with self.subTest(path=path), self.assertRaises(u.UploadError):
                self.work.destination(subfolder=path, create=True)

    def test_exact_subfolder_name_no_fuzzy_match(self):
        self.drive.items['x'] = dict(folder('x', 'root'), name='audit-old')
        result = self.work.destination(subfolder='audit', create=True)
        self.assertEqual(result['planned_subfolders'], ['audit'])

    def test_ambiguous_subfolder_stops(self):
        for id in ('a', 'b'):
            self.drive.items[id] = dict(folder(id, 'root'), name='audit')
        with self.assertRaises(u.UploadError): self.work.destination(subfolder='audit')

    def test_named_file_cannot_be_reused_as_folder(self):
        self.drive.items['f'] = dict(id='f', name='audit', mimeType='text/plain', parents=['root'], driveId='drive')
        with self.assertRaises(u.UploadError): self.work.destination(subfolder='audit', create=True)

    def test_upload_creates_only_requested_subfolders(self):
        with patch.object(u, 'make_media', side_effect=lambda p: str(p)):
            result = self.work.upload(self.file, subfolder='audit/run', create_subfolders=True)
        self.assertEqual([w[1]['name'] for w in self.drive.writes], ['audit', 'run', 'report.txt'])
        self.assertEqual(result['action'], 'uploaded')

    def test_duplicate_blocks_upload(self):
        self.drive.items['dup'] = dict(id='dup', name=self.file.name, parents=['root'], driveId='drive', mimeType='text/plain')
        with self.assertRaises(u.UploadError): self.work.upload(self.file)
        self.assertEqual(self.drive.writes, [])

    def test_dry_run_surfaces_duplicate_without_writing(self):
        self.drive.items['dup'] = dict(id='dup', name=self.file.name, parents=['root'], driveId='drive', mimeType='text/plain')
        result = self.work.upload(self.file, dry_run=True)
        self.assertEqual(result['same_name_file_ids'], ['dup'])
        self.assertEqual(self.drive.writes, [])

    def test_explicit_replacement_stays_in_destination(self):
        self.drive.items['f'] = dict(id='f', name='existing.txt', parents=['inside'], driveId='drive', mimeType='text/plain', capabilities={'canEdit': True})
        with patch.object(u, 'make_media', side_effect=lambda p: str(p)):
            result = self.work.upload(self.file, folder_id='inside', replace_file_id='f')
        self.assertEqual(result['file_id'], 'f')
        self.assertEqual(self.drive.writes, [('update', 'f')])

    def test_replacement_cannot_touch_sibling_folder(self):
        self.drive.items['f'] = dict(id='f', name='report.txt', parents=['outside'], driveId='drive', mimeType='text/plain', capabilities={'canEdit': True})
        with self.assertRaises(u.UploadError): self.work.upload(self.file, replace_file_id='f')
        self.assertEqual(self.drive.writes, [])

    def test_native_google_doc_replacement_blocked(self):
        self.drive.items['f'] = dict(id='f', name='doc', parents=['root'], driveId='drive', mimeType='application/vnd.google-apps.document', capabilities={'canEdit': True})
        with self.assertRaises(u.UploadError): self.work.upload(self.file, replace_file_id='f')

    def test_missing_file_does_not_create_folders(self):
        with self.assertRaises(u.UploadError):
            self.work.upload(Path(self.tmp.name) / 'missing', subfolder='audit', create_subfolders=True)
        self.assertEqual(self.drive.writes, [])

    def test_destination_id_and_subfolder_are_mutually_exclusive(self):
        with self.assertRaises(u.UploadError): self.work.destination(folder_id='inside', subfolder='audit')

    def test_folder_only_grant_does_not_require_whole_drive_membership(self):
        original = self.drive.list
        def memberless_list(**kwargs):
            if kwargs.get('corpora') != 'user' or 'driveId' in kwargs:
                raise PermissionError('Shared Drive membership not granted')
            return original(**kwargs)
        self.drive.list = memberless_list
        self.assertEqual(self.work.upload(self.file, dry_run=True)['same_name_file_ids'], [])

    def test_incomplete_listing_cannot_be_used_for_duplicate_check(self):
        self.drive.list = lambda **kwargs: Request(lambda: {'files': [], 'incompleteSearch': True})
        with self.assertRaises(u.UploadError): self.work.upload(self.file)
        self.assertEqual(self.drive.writes, [])

    def test_parent_moved_after_preview_blocks_file_creation(self):
        original = self.drive.list
        def move_after_check(**kwargs):
            self.drive.items['inside']['parents'] = ['outside']
            return original(**kwargs)
        self.drive.list = move_after_check
        with patch.object(u, 'make_media', side_effect=lambda p: str(p)):
            with self.assertRaises(u.UploadError):
                self.work.upload(self.file, folder_id='inside')
        self.assertEqual(self.drive.writes, [])

    def test_upload_uses_approved_snapshot_even_if_source_changes(self):
        approved = hashlib.md5(self.file.read_bytes()).hexdigest()
        self.drive.items['f'] = dict(id='f', name='report.txt', parents=['root'], driveId='drive', mimeType='text/plain', capabilities={'canEdit': True})
        def mutate_source(media_path):
            self.file.write_text('unapproved changes')
            return str(media_path)
        with patch.object(u, 'make_media', side_effect=mutate_source):
            result = self.work.upload(self.file, replace_file_id='f')
        self.assertEqual(result['md5'], approved)
        self.assertEqual(self.drive.items['f']['md5Checksum'], approved)

    def test_upload_returns_id_if_original_file_disappears_after_snapshot(self):
        def delete_original(media_path):
            self.file.unlink()
            return str(media_path)
        with patch.object(u, 'make_media', side_effect=delete_original):
            result = self.work.upload(self.file)
        self.assertTrue(result['file_id'])

    def test_changed_file_since_dry_run_stops_before_folder_creation(self):
        preview = self.work.upload(self.file, subfolder='audit', create_subfolders=True, dry_run=True)
        self.file.write_text('changed since preview')
        with self.assertRaises(u.UploadError):
            self.work.upload(self.file, subfolder='audit', create_subfolders=True, expected_md5=preview['md5'])
        self.assertEqual(self.drive.writes, [])

    def test_cli_upload_without_approved_digest_never_authenticates(self):
        with patch.object(u, 'build_service') as authenticate:
            with self.assertRaisesRegex(u.UploadError, 'expected-md5'):
                u.run_command('upload', file=str(self.file), confirmed_key=str(self.file), root_id='root')
        authenticate.assert_not_called()

    def test_media_handle_closes_when_parent_changes_before_send(self):
        class Media:
            def __init__(self, path): self._fd = path.open('rb')
        media = None
        def moved_parent(path):
            nonlocal media
            media = Media(path)
            self.drive.items['inside']['parents'] = ['outside']
            return media
        with patch.object(u, 'make_media', side_effect=moved_parent):
            with self.assertRaises(u.UploadError): self.work.upload(self.file, folder_id='inside')
        self.assertTrue(media._fd.closed)
        self.assertEqual(self.drive.writes, [])


if __name__ == '__main__': unittest.main()
