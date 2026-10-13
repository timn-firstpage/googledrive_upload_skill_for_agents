# Implementation plan

Goal: portable Codex Skill with guided service-account setup and folder-confined upload helpers.
Approved design: [design.md](design.md); user additionally requires existing-credential detection and path confirmation before authentication.
Stack: Python 3.10+, google-api-python-client, google-auth; local scripts, no MCP server.

1. [x] Write offline tests for credential discovery (no content reads), root/descendant confinement, Shared Drive enforcement, dry-run zero writes, exact subfolder handling, duplicate refusal and explicit replacement.
2. [x] Implement discovery plus authenticated doctor/upload using a confirmed credential path; verify red-to-green tests.
3. [x] Write SKILL.md, guided Mac setup, README, sample environment config and external onsite prompt. Explain service-account uploads to Shared Drive and direct-folder grants, plus GUI environment inheritance.
4. [x] Run all offline tests, skill validator, CLI checks and credential-exclusion review. Publication target: the supplied repository's initial main branch.

Review focus: mixed credential paths, ambiguous same-name folders, shortcuts/outside-root targets, My Drive destinations and transient upload failure. No live key or production Drive write is part of these tests.

Execution: inline, as requested. Existing local credential paths will not be put in the repository. The current destination type remains a runtime setup check rather than a hardcoded installation choice.
