# Design

A portable Mac Codex Skill guides setup of isolated service-account Drive access and uploads onsite audit outputs using a local Python helper. The user approved this design and requested existing-account detection, key-path confirmation, a GitHub repository and README.

Setup discovers only configured credential paths without reading contents or contacting Google. The user confirms the selected path before authentication; two different paths require a choice. Existing projects/accounts/keys are reused. New setup guides Drive API enablement, service account creation, JSON download, private local storage, folder-scoped sharing and Python venv installation.

The root is an exact user-specified Shared Drive folder ID. Service-account new files cannot be owned in My Drive. Direct folder access is preferred over whole-drive membership. Script boundaries do not remove broader real Google permissions; isolation requires inspection by the user/administrator.

Upload accepts an explicit final local file and the configured root, an exact descendant ID or exact relative subfolder path. Dry-run reports source and destination without writing. Explicitly authorized missing subfolders may be created. Existing same-name files stop; replacement requires an explicit ordinary-file ID in the selected destination. No native Docs editing, deletion or routine permission management.

Outputs are Drive IDs and links. API retries are bounded and uploads are resumable in the current process. Uncertain failures require checking remote state before repeating. Concurrent writers may still race because Drive names are not unique and there is no atomic folder lock.

Onsite checking remains separate. External prompts can authorize upload of explicit final outputs and requested subfolders. Existing clear authorization is honored without repeated upload confirmation; new-session credential path confirmation is still required by the user.

No live credentials or actual customer settings are shipped. Automated tests use an offline Drive substitute; real Mac setup and production upload are not established by offline tests.
