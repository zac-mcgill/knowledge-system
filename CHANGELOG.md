## Unreleased - Phase 39A MCP Stdio Verification Batch Pass Documentation

Documentation-only update recording the completion of Phase 39A (MCP Stdio Verification Batch Pass). A manual/copilot-assisted 12-batch verification pass validated the MCP stdio surface, catalogue, error handling, pending-change safety, documentation, UI build, boundary separation, artefact hygiene, and final release gate. No runtime code changes, no source modifications, and no commit were required by the verification itself. All verification, validation, security, feedback, export, smoke, and UI build commands passed from the repository root. Phase 40 remains the next planned implementation phase.

# Changelog

## Unreleased - ROADMAP deep normalisation

Documentation-only restructure of `ROADMAP.md` that removes stale "Current
Active Phase" narrative carried forward from earlier phases, reorganises the
file under a fixed section template, and adds 14 new deterministic guards to
prevent regression. No runtime, schema, API, or MCP behaviour changes.

### Changed

- `ROADMAP.md` fully restructured under the section template: Executive
  Direction, Product North Star, Core Principles, Strategic Non-Goals,
  Current Baseline, Current Status, Phase Status Overview, Completed
  Capability Summary, Completed Phase Notes, Planned Productisation Phases,
  Deferred Phases.
- The stale `## Current Active Phase` heading and supporting narrative have
  been removed. The "retained verbatim for traceability" and "supersedes it
  for status purposes" phrases are no longer present.
- Phase 40 (Public Security Posture and Release Trust) is now explicitly
  named as the next planned implementation phase. The earlier claim that
  Phase 32 is the next planned phase has been removed.
- Historical phase ranges (0-9, 10-16, 17-26F, 29A-31C) are now expressed as
  compressed range entries under Completed Phase Notes rather than as long
  individual sections. Phases 37, 38, 39, and 44 retain their full clean
  detail blocks under Completed Phase Notes.
- Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic
  Retrieval) are now exclusively documented inside the single `## Deferred
  Phases` section.

### Added

- 14 new deterministic guards in `mcp/test_verify.py`
  (`test_p39rd_10_*` through `test_p39rd_23_*`) pinning the new ROADMAP
  structure: no `## Current Active Phase` heading or phrase, no
  `retained verbatim for traceability` or `supersedes it for status
  purposes` phrases, Phase 40 is the next planned implementation phase,
  Phase 32 is not the next planned phase, exactly one `## Current Status`,
  `## Completed Capability Summary`, `## Planned Productisation Phases`,
  and `## Deferred Phases` section, Phase 27 and Phase 28 inside the
  Deferred Phases section, Phase 39 Complete in both the table and the
  Completed Phase Notes, and no Phase 30 or 31 work described as currently
  active.
- TESTING.md and RELEASE_CHECKLIST.md updated to record the 1152 historical
  marker and the new total of 1166 tests.

### Verification

- Verification total advertised across README.md, TESTING.md, and
  RELEASE_CHECKLIST.md bumped from 1152 to 1166. All four documentation
  drift guards re-pinned at 1166. `py mcp/test_verify.py` prints
  `ALL VERIFICATION TESTS PASSED`.

## Unreleased - Phase 39 Roadmap Normalisation

Documentation-cleanup pass that closes out Phase 39 in `ROADMAP.md` and adds
deterministic guardrails so the roadmap cannot silently regress.

### Changed

- `ROADMAP.md` Phase Status Overview now marks Phase 39 (MCP Client Setup and
  Connection Testing) as Complete, alongside the already-complete Phases 37
  and 38. Tab characters in the Phase 42 and Phase 43 rows were replaced with
  spaces, and the "Legacy Acronym Neurtralisation" typo in the Phase 45 row
  was corrected to "Neutralisation". Parent Phase 44 is now Complete (both
  44A and 44B subphases shipped).
- A short Post-Phase 39 normalisation paragraph was added to the Current
  Active Phase section recording that Phases 37, 38, and 39 are Complete,
  that Phase 40 (Public Security Posture and Release Trust) is the next
  planned phase, and that Phases 27 and 28 remain Deferred. The Phase Status
  Overview table remains the single source of truth.

### Added

- Nine new deterministic roadmap drift guards in `mcp/test_verify.py`
  (`test_p39rd_01_*` through `test_p39rd_09_*`). They pin: Phase 39 marked
  Complete in the overview table, no Phase 39 Planned row anywhere in the
  table, Phases 37 and 38 marked Complete, Phase 40 named as next planned,
  Phases 27 and 28 still Deferred, no duplicate `### Phase 37/38/39` detail
  headings, no tab characters in `ROADMAP.md`, no `Neurtralisation` typo,
  and exactly one `## Phase Status Overview` heading.
- These nine guards bring the test suite from 1143 to 1152 deterministic
  tests. `README.md`, `TESTING.md`, and `RELEASE_CHECKLIST.md` were updated
  accordingly, and the existing doc-drift count guards were updated in
  lockstep so 1143 is retained as a historical marker.

### Non-goals

- No runtime, backend, HTTP API, MCP protocol, schema, or UI behaviour was
  changed. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional
  Semantic Retrieval) remain Deferred and are not started by this pass.

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
