# Verification

Offline checks on Windows with Python 3.12; no real service-account key was read, and no production Drive write was made.

Result: 33 unit tests passed; Skill metadata validation passed; CLI help and credential-path detection succeeded. Repository files were checked for private-key content and machine-specific credential values, with no matches. Credentials and local validation dependencies are excluded by `.gitignore`.

- Behavioral review: existing/mixed credential paths require user selection and confirmation before authentication; Shared Drive setup does not silently broaden folder permissions; externally authorized final outputs can proceed without repeated upload approval.
- Code review identified directly shared folder listing, concurrent parent movement and source changes. Regression tests first reproduced the failures, then passed after fixes.
- Uploads stage a temporary copy and CLI real uploads require the approved dry-run MD5. Destination ancestry is refreshed immediately before folder/file writes. Google Drive sharing remains the access boundary; concurrent moves cannot be made atomic with the upload API.
- Unit tests cover detection without key-content reads, root and descendant confinement, Shared Drive requirements, dry-run zero writes, exact subfolder creation, duplicate protection, ordinary-file replacement, incomplete listing, changed source bytes and media-handle cleanup.
- macOS and Windows setup guides are documented. Windows PowerShell configuration and command examples pass syntax parsing; 33 offline tests pass locally on Windows. An optional GitHub Actions template covers macOS/Windows with Python 3.10/3.12; it is not active because the publishing OAuth authorization lacks workflow scope. A live doctor check and explicitly authorized test upload remain runtime setup steps on each machine.

Reproduce:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/gdrive_upload.py --help
python3 scripts/gdrive_upload.py detect
```
