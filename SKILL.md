---
name: gdrive-upload
description: Set up isolated Google Drive access through an existing or new service account, then upload confirmed local outputs into a configured folder and its subfolders. Use for Drive upload requests or service-account upload setup; onsite audits remain separate workflows.
---

# Google Drive upload

Use the bundled local Python helper on macOS or Windows; no MCP server is required. This skill has setup and upload modes. Run commands relative to this skill's absolute directory, not the current audit project. Choose commands for the actual runtime OS and shell; do not send Bash syntax to PowerShell.

## Start with existing configuration

Run `scripts/gdrive_upload.py detect` through the configured venv interpreter. On macOS use `"${GDRIVE_PYTHON:-python3}"`; on Windows PowerShell use `& $env:GDRIVE_PYTHON` when configured, otherwise a verified Python 3.10+ interpreter (`py -3` or `python`). Windows Store aliases are not proof that Python is installed. This reads path metadata only; it does not read credentials or contact Google. If Python is missing, guide its installation first.

If a candidate key path exists, show that path and ask the user which path to use. **Wait for their confirmation before loading the key or authenticating.** If two variables point to different files, let the user choose; never select silently. A configured path is not proof of a working connection. Reuse path confirmation already given in the current session; re-confirm when the path changes or at the start of a new session. Never display, embed or commit key contents. Do not search the whole computer for secrets.

If no candidate exists, ask whether the user already has a credential file elsewhere before creating an account/key. Read the guide for the current OS: [macOS](references/setup-macos.md) or [Windows PowerShell](references/setup-windows.md), and guide one step at a time in the user's language. Reuse their existing project/account and retain existing authorization. Confirm the intended root folder ID as well as the key path before `doctor --confirmed-key-file "<confirmed path>"` checks identity and destination without writing; do not silently reuse a stale root configuration. Credential paths and Python paths are machine-specific; never reuse a Windows path on a Mac or vice versa. Drive folder IDs can be reused.

## Scope and setup

Configure `GDRIVE_ROOT_FOLDER_ID` from the user's exact folder ID/URL. The helper requires a Shared Drive folder, refuses shortcuts and verifies descendants against the configured root. Direct-folder sharing controls the service account's actual access; do not default to whole-drive Content Manager membership. My Drive new-file uploads by this service account are unsupported; report this rather than switching identity.

Setup includes credentials, venv, folder access and the read-only doctor check. A real test upload is optional and needs authorization for that test file. Do not claim a live upload was tested solely from doctor or offline tests.

## Upload outputs

Require exact local file paths and a confirmed final version plus upload authorization. The default destination is the configured root; an exact descendant ID or relative subfolder path can refine it. No fuzzy client-name lookup. Upload explicitly listed artifacts one at a time; do not scan and publish a whole project.

1. Preview with `upload "<file>" --confirmed-key-file "<path>" --dry-run`, adding destination options as needed. Inspect actual filename, size, destination and any planned folders/replacement.
2. If existing user instructions already authorize these exact outputs and destination, execute within that scope. Otherwise show the preview and wait for approval. Dry-run never creates folders or uploads.
3. Real upload uses the same arguments without `--dry-run`, plus `--expected-md5 "<md5 from approved preview>"`. Never recompute a new digest silently after approval. The helper stages a temporary copy and refuses changed bytes before writing. Add `--subfolder "audit/run" --create-subfolders` only when creating that path was authorized. Same-name files stop by default. Replace only an explicitly authorized ordinary file using `--replace-file-id "<id>"`; native Docs/Sheets editing is outside scope.
4. Report action, file ID, destination ID and returned link. Links do not change sharing permissions. On uncertain failure, inspect the exact destination/name before retrying; subfolders may already exist. Google Drive permits duplicate names, so sequential duplicate checks are not an atomic concurrency lock.

For CLI details run `scripts/gdrive_upload.py --help`. For external onsite orchestration use [the prompt example](examples/onsite-upload-prompt.md). This skill does not perform onsite audits or change sharing during normal uploads.
