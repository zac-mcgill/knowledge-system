# Changelog

## Unreleased - Phase 38: Backup, Restore, and Migration Safety

Add a local, preview-first backup and restore surface so users can capture and recover their vaults, config, feedback, state, and templates without risking accidental data loss.

### Added

- `mcp/core/backup_restore.py` service exposing `build_backup_plan`, `create_backup_archive`, `list_backups`, `read_backup_manifest`, `validate_backup_archive`, `build_restore_preview`, `apply_restore`, `build_migration_summary`, and `FORMAT_VERSION="1"`. Standard-library only (`zipfile`, `hashlib`, `tempfile`, `shutil`).
- Local zip backups written to `dist/backups/cve-backup-<utc>-<id>.zip` with `backup-manifest.json` at the archive root and SHA-256 per file. Generated artefacts (`dist/`, `node_modules/`, caches, `.git/`, vault reports) are excluded by default; note bodies are never embedded in the manifest.
- `py run.py backup` CLI command (`--preview`, `--write`, `--list`, `--vault NAME`) and `py run.py restore` CLI command (`--backup`, `--preview`, `--write`, `--overwrite`, `--restore-config`, `--confirm`).
- HTTP API: `GET /backups`, `POST /backup/plan`, `POST /backup/create`, `POST /restore/preview`, `POST /restore/apply`. Write routes are added to `_WRITE_PATH_PREFIXES` and are blocked in private cloud read-only mode.
- `/app/backups` UI page under the Developer nav group, with an existing-backups table, a create-backup form, and a preview-first restore form with typed `RESTORE <backup_id>` confirmation gate, plus `overwrite` and `restore_config` opt-in checkboxes.
- 32 deterministic Phase 38 tests (`test_p38_01_*` through `test_p38_32_*`), bringing the suite to 1135 tests.

### Safety

- Restore is **preview-first**. `build_restore_preview` reports every entry as `target_exists` / `would_overwrite` / `in_registry`, surfaces blocking errors (`MANIFEST_MISSING`, `HASH_MISMATCH`, `UNSAFE_ARCHIVE_PATH`, `UNSAFE_RESTORE_TARGET`, `FORMAT_VERSION_UNSUPPORTED`), and emits migration warnings (`SCHEMA_VERSION_CHANGED`, `CONFIG_SHAPE_CHANGED`, `TARGET_EXISTS`, `VAULT_NOT_REGISTERED`) before any write.
- `apply_restore` requires a typed `RESTORE <backup_id>` confirmation that exactly matches the preview's `confirmation_phrase`, an explicit `overwrite=True` flag to replace existing files, and an explicit `restore_config=True` flag to touch `config/config.yaml`.
- Restored files are staged into a temporary directory and hash-validated before any live target is replaced (atomic on validation failure - no partial restores).
- Archive entries with absolute paths, `..` segments, or paths escaping the repository root are rejected with `UNSAFE_ARCHIVE_PATH` / `UNSAFE_RESTORE_TARGET`.
- Backups are local-only inspectable zip files. Nothing is uploaded; no cloud backup target was introduced.

### Non-goals

Phase 38 does not start Phase 27 (Registry and Reuse Layer) or Phase 28 (Optional Semantic Retrieval); both remain Deferred. No semantic retrieval, embeddings, LLM calls, autonomous note writing, registry/reuse, desktop packaging, onboarding workflow, new runtime dependency, new UI framework, React, external icon library, animation library, remote telemetry, crash upload service, automatic issue reporting, or cloud backup target was added.

## Unreleased - Phase 37: Local Diagnostics and Support Report

Add a local, redacted diagnostics and support report so users can debug and share triage information safely without leaking note bodies, tokens, or other secrets.

### Added

- `mcp/core/diagnostics.py` service exposing `build_diagnostics_report`, `redact_value`, `redact_mapping`, and per-section collectors. All data sourcing is local; nothing is uploaded.
- `py run.py diagnostics` CLI command that prints the redacted report as JSON to stdout (exit 0 on success, exit 1 with a structured error envelope on failure).
- `GET /diagnostics` read-only HTTP endpoint returning the standard `{status, data}` envelope. Subject to the same authentication rules as the rest of the API and allowed in private cloud read-only mode.
- `/app/diagnostics` UI page (Astro + Svelte) under the Developer nav group with Runtime, UI build, Vault and configuration, Commands, Private cloud, Environment (CVE_*), Redaction and safety, Warnings, and Raw JSON sections, plus a "Copy JSON" button.
- 22 deterministic Phase 37 tests (`test_p37_01_*` through `test_p37_22_*`), bringing the suite to 1103 tests.

### Safety

- Note bodies, prompt contents, context bundle contents, and pending-change proposed content are never included in diagnostics output.
- Auth tokens, API keys, passwords, bearer values, cookies, sessions, and other secret environment values are redacted using a stable `<redacted>` marker; `CVE_AUTH_TOKEN` is reported as a boolean only.
- Local absolute paths are labelled under `local_path` keys so consumers can sanitise them before sharing.
- Diagnostics is read-only and is not uploaded; no telemetry, no crash upload, no automatic issue reporting was introduced.

### Non-goals

Phase 37 does not start Phase 27 (Registry and Reuse Layer) or Phase 28 (Optional Semantic Retrieval); both remain Deferred. No semantic retrieval, embeddings, LLM calls, autonomous note writing, registry/reuse, backup/restore, desktop packaging, onboarding workflow, MCP client setup work, new runtime dependency, new UI framework, React, external icon library, animation library, remote telemetry, crash upload service, or automatic issue reporting was added.

---

## Unreleased - release-candidate documentation drift cleanup

Documentation-only pass. No runtime, API, schema, MCP, UI behaviour, or dependency changes were made.

### Changed

- Documentation now reflects the current 1028-test release-candidate state.
- README "Current Status" no longer claims the local app, CLI, HTTP API, or MCP stdio surface are "production-quality for local use"; they are now described as release-candidate quality for local use, pending manual browser visual QA, keyboard QA, and screen-reader QA.
- ROADMAP "Import Sources" list now shows Obsidian-compatible Markdown import as implemented in Phase 26E, with full Obsidian-native behaviour (automatic wikilink rewriting, attachment copying/import, binary attachment processing, full Obsidian graph semantics) remaining deferred.
- README Phase 26 capability bullets and QUICKSTART Phase 26B UI bullet now correctly distinguish between implemented Markdown folder import, implemented Obsidian-compatible Markdown import, and deferred richer Obsidian-native behaviour.

### Fixed

- Removed wording that implied Phase 31C had completed rendered browser visual QA, live keyboard traversal, or screen-reader QA. Phase 31C is now consistently documented as automated source-level/static verification only; the agent that executed Phase 31C did not open a browser, did not perform live keyboard traversal, and did not run a screen reader.
- Removed stale "Obsidian-specific imports remain deferred" and "Obsidian vault (deferred)" current-state wording that contradicted Phase 26E. Historical Phase 26A-D phase records that describe what those phases did not include at the time were preserved as historical context.

### Verification

Verified with the current verification sequence (source-level only):

```bash
py mcp/test_verify.py
py run.py validate
py run.py security
py run.py feedback
py run.py export --overwrite
cd ui; npm run build
```

Expected result:

- 1028 verification tests pass.
- Vault validation, security scan, feedback, and export commands all exit successfully.
- UI build completes successfully.
- Browser visual QA, live keyboard QA, and screen-reader QA remain manual and are tracked in `RELEASE_CHECKLIST.md`.

### Known limitations

- Phase 27 (Registry and Reuse Layer) remains deferred.
- Phase 28 (Optional Semantic Retrieval) remains deferred.
- Phase 32 (Human Release QA and Evidence Capture) has not started; it is the next planned phase, and Phases 32 to 44 are planned.
- Obsidian-compatible Markdown import is implemented; full Obsidian graph semantics, automatic wikilink rewriting, attachment copying/import, binary attachment processing, and richer Obsidian-native behaviour remain deferred.
- Browser visual QA, live keyboard QA, and screen-reader QA remain manual and must be performed by a human against a real browser and, where applicable, a real assistive technology before any release tag claims those passes.
- Autonomous note writing is not enabled; pending memory changes remain human-reviewed before acceptance.

## v1.0.1 - CI and runtime artefact hygiene patch

### Fixed

- Restored GitHub Actions verification after the UI build ordering change.
- Made Python UI build verification POSIX-portable by removing `shell=True` npm subprocess calls.
- Centralised npm build execution through shell-free helpers in `mcp/test_verify.py`.
- Ensured UI build tests run `npm ci` when `node_modules` is missing instead of skipping.
- Removed generated pending-change JSON runtime artefacts from version control.
- Ignored generated pending-change runtime output under `Vault Files/State/pending-changes/`.
- Updated the mutating feedback write test so `feedback.md` is snapshotted and restored.

### Verification

Verified with:

```bash
python mcp/test_verify.py
python run.py validate
python run.py security
python run.py feedback
python run.py export --overwrite
cd ui && npm run build
```

Expected result:

- 695 verification tests pass.
- Vault validation passes.
- Security scan exits successfully.
- Feedback command exits successfully.
- Export command writes package output successfully.
- UI build completes successfully.
- GitHub Actions verify workflow passes.

### Known limitations

- Registry and Reuse Layer remains deferred.
- Optional Semantic Retrieval remains deferred.
- Autonomous note writing is not enabled.
- Pending memory changes remain human-reviewed before acceptance.
