# Context Vault Engine - Master Roadmap

## Executive Direction

Context Vault Engine is moving from a usable local vault application into a private context operating layer for humans, local LLMs, and agent clients. The deterministic foundation (Markdown validation, schema enforcement, analysis, improvement tasks, feedback, lexical search, context bundles, export packages, security scanning, FastAPI routes, the local web UI, MCP stdio compatibility, private cloud mode, session and project state, safe memory write queue, device profiles, trust/staleness/evidence metadata, safe Markdown and Obsidian-compatible import, local diagnostics and support reporting, local backup, restore, and migration safety, and MCP client setup and connection testing) is complete.

The next strategic direction preserves the existing local-first, deterministic-first model while adding a new post-completion target: a user can run Context Vault Engine locally or on a private personal VPS, manage it through a web UI, and expose a safe MCP-compatible context layer to local LLM clients. The project must not become generic SaaS, generic RAG, or a cloud AI product. The stronger endpoint is a self-hostable private context service.

## Product North Star

Context Vault Engine should become a private, deterministic context service for structured Markdown knowledge, usable by humans, local LLMs, and trusted agent clients.

Target shape:

```
Human Web UI
Local LLM Client
MCP-Compatible Client
        |
Context Controller
        |
Context Vault Engine API
        |
Validated Markdown Vault
```

## Core Principles

- Markdown remains the source of truth.
- Schema remains the contract.
- Validation and security gates protect output.
- Bundles and exports are derived artefacts.
- Feedback adjusts priority, not content.
- Local-first remains the default.
- Private-cloud mode is optional and self-hosted.
- Deterministic behaviour comes before semantic or LLM behaviour.
- LLM and agent clients must not freely mutate notes.
- Semantic retrieval remains optional and deferred.

## Strategic Non-Goals

Context Vault Engine is explicitly not, and must not become:

- generic SaaS;
- a generic RAG wrapper;
- a cloud AI service;
- a database-heavy CMS;
- an autonomous content writer;
- an Obsidian replacement;
- a multi-tenant enterprise platform;
- an embedding-first retrieval system.

## Current Baseline

The deterministic backend, the local web application, the MCP stdio surface, the private cloud mode, the safe memory and pending-change write lifecycle, the import pipeline, the diagnostics and support report, the backup and restore lifecycle, and the MCP client setup and connection testing surface are all implemented. The UI is at release-candidate source-level quality with documented manual QA still to be performed by a human reviewer. The verification suite is the single source of truth for behavioural claims.

## Current Status

- Phases 0 to 26F are complete.
- Phases 29A to 31C are complete.
- Phase 32 (Human Release QA and Evidence Capture) remains planned and manual.
- Phases 37, 38, 39, and 39A are complete.
- Phase 39A (MCP Stdio Verification Batch Pass) is complete: a manual/copilot-assisted 12-batch verification pass validated the MCP stdio surface, catalogue, error handling, pending-change safety, documentation, UI build, boundary separation, artefact hygiene, and final release gate. No runtime code changes, no source modifications, and no commit were required by the verification itself.
- Phase 40 (Public Security Posture and Release Trust) is the next planned implementation phase.
- Phases 41, 42, 43, and 45 remain planned.
- Phase 44 is complete as a grouped lifecycle track because Phase 44A and Phase 44B are both complete.
- Phase 27 (Registry and Reuse Layer) remains deferred.
- Phase 28 (Optional Semantic Retrieval) remains Deferred.
- The current verification total is 1166 tests in `mcp/test_verify.py`.

The Phase Status Overview table in the next section is the single source of truth for the status of every phase.

## Phase Status Overview

| Phase | Name                                     | Status   |
|-------|------------------------------------------|----------|
| 0     | Correctness stabilisation               | Complete |
| 1     | API capability exposure                 | Complete |
| 2     | Context bundle generation               | Complete |
| 3     | Feedback loop                           | Complete |
| 4     | Export and packaging                    | Complete |
| 5     | Context security scanning               | Complete |
| 6     | Documentation and positioning           | Complete |
| 7     | Deterministic lexical search            | Complete |
| 8     | Demo vault and schema data improvements | Complete |
| 9     | Public presentation pass                | Complete |
| 10    | Local Web UI Foundation                 | Complete |
| 11    | Guided Vault Bootstrap                  | Complete |
| 12    | Vault Dashboard and Issue Review        | Complete |
| 13    | Bundle, Export, and Security UI         | Complete |
| 14    | Feedback and Task Workflow UI           | Complete |
| 15    | Note Browser and Safe Editing UI        | Complete |
| 16    | Visual Graph and Missing Concepts UI    | Complete |
| 17A   | HTML Bundle Renderer                    | Complete |
| 17    | Distribution and Local App Launcher     | Complete |
| 18    | CI and Release Hardening                | Complete |
| 19    | Context Controller Layer                | Complete |
| 20    | MCP Compatibility Layer                 | Complete |
| 21    | Private Cloud Mode                      | Complete |
| 22    | Session and Project State Layer         | Complete |
| 23    | Safe Memory Write Queue                 | Complete |
| 24    | Device Profiles and Context Budgets     | Complete |
| 25    | Trust, Staleness, and Evidence Metadata | Complete |
| 26    | Import Pipelines                        | Complete |
| 29    | UI/UX Quality and Design System         | Complete |
| 30A   | UI Release Quality Pass - Audit         | Complete |
| 30B   | UI Foundation (shell, theme, primitives)| Complete |
| 30C   | Dashboard Redesign                      | Complete |
| 30D   | Core Workflow Page Redesigns            | Complete |
| 30D1  | Validation, Tasks, Raw real impls       | Complete |
| 30D2  | Notes and Graph workspace redesigns     | Complete |
| 30D3  | Import, Bundles, Exports, Security      | Complete |
| 30E   | Review/Governance/Developer Polish      | Complete |
| 30E1  | Pending, Trust, Feedback gov polish     | Complete |
| 30E2  | Controller and Vault Setup polish       | Complete |
| 30F   | Final QA, A11y, Responsive, Light Mode  | Complete |
| 31A   | Release Candidate Verification          | Complete |
| 31B   | App Header and Toolbar Normalisation    | Complete |
| 31C   | RC Visual QA and Defect Triage          | Complete |
| 32    | Human Release QA and Evidence Capture   | Planned  |
| 33    | Official Website and Public Docs        | Planned  |
| 34    | Windows Desktop Distribution            | Planned  |
| 35    | Deterministic In-App Guidance Assistant | Planned  |
| 36    | First-Run Onboarding Workflow           | Planned  |
| 37    | Local Diagnostics and Support Report    | Complete |
| 38    | Backup, Restore, and Migration Safety   | Complete |
| 39    | MCP Client Setup and Connection Testing | Complete |
| 39A   | MCP Stdio Verification Batch Pass       | Complete |
| 40    | Public Security Posture & Release Trust | Planned  |
| 41    | Example Vaults and Demonstration Packs  | Planned  |
| 42    | Context Health Recommendation Layer     | Planned  |
| 43    | MCP Response Ergonomics & Budget Diag   | Planned  |
| 44    | Pending Change Lifecycle (parent)       | Complete |
| 44A   | Pending Change Lifecycle Investigation  | Complete |
| 44B   | Pending Change Lifecycle Implementation | Complete |
| 45    | Legacy Acronym Neutralisation (CVE)     | Planned  |
| 27    | Registry and Reuse Layer                | Deferred |
| 28    | Optional Semantic Retrieval             | Deferred |

## Completed Capability Summary

### Deterministic backend and validation

Schema enforcement, Markdown validation, deterministic analysis reports, improvement task generation, feedback weighting, deterministic lexical search, drift detection between vault state and schema, and structured JSON error envelopes across every CLI and API path. All behaviour is regex- or rule-based; no LLM, no embeddings, no remote calls.

### API and local web UI

FastAPI backend with path-traversal blocking, rate limiting, and structured JSON errors. Local Astro and Svelte web UI covering the full lifecycle: guided vault bootstrap, dashboard, validation, tasks, note browser and safe editor, bundle builder, exports, security scan view, feedback workflow, graph explorer and missing concepts, controller, pending review, trust, governance, imports, diagnostics, backups, and MCP setup. The UI is theme-aware (light and dark) with a tokenised `--cve-*` design system and `cve-*` primitives.

### Context packaging and security scanning

Context bundle generation, deterministic HTML bundle renderer, SHA-256 artefact manifests, context export packages, deterministic security scanner covering credential leak patterns, prompt-injection patterns, and suspicious executable or script blocks. Every finding is explainable, reproducible, and auditable.

### MCP stdio and local client setup

JSON-RPC 2.0 stdio compatibility layer (`py run.py mcp`), a documented `.vscode/mcp.json` known-working example, a deterministic local `py run.py mcp-smoke` connection test, the `mcp/smoke.py` helper module, and a static MCP Setup UI page at `/app/mcp` that surfaces the start command, smoke command, working-directory and stdio model, a conservative read-only safety notice that does not overclaim, and an explicit client-compatibility caveat. The MCP layer has no direct vault-note write path and never auto-accepts pending changes.

### Private cloud and supportability

Private cloud mode with remote read-only enforcement, a bearer-token auth layer, session and project state, device profiles and context budgets, and a local, redacted diagnostics and support report (`py run.py diagnostics`, `GET /diagnostics`, `/app/diagnostics`) that omits note bodies and redacts secrets to a stable `<redacted>` marker.

### Safe memory and write lifecycle

Safe memory write queue with pending changes, schema-validated proposals, archive-aware listing, the safe `revalidate` surface that never writes to vault notes, trust, staleness, and evidence metadata, stale-hash protection on accept, immutable audit history, and explicit typed confirmations on destructive actions (`OVERWRITE`, `DELETE <vault>`, `ACCEPT` / `REJECT`, `RESTORE <backup_id>`). No autonomous mutation; every vault write requires explicit human confirmation.

### Import, backup, diagnostics, and support tooling

Safe Markdown folder import with browser review UI, post-import review integration, edge-case hardening, Obsidian-compatible Markdown import, end-to-end import lifecycle finalisation, and a preview-first local backup and restore service (`dist/backups/cve-backup-<utc>-<id>.zip` with SHA-256 manifests, generated artefacts excluded by default, typed `RESTORE <backup_id>` confirmation). Combined with the diagnostics report, this gives users a complete local debugging, recovery, and support story without any remote telemetry.

### UI/UX quality and release-candidate guardrails

A full UI/UX quality and design system pass (Phase 29), a release quality pass covering audit, foundation, dashboard, core workflow redesigns, governance polish, controller and vault-setup polish, final QA, accessibility, responsive, and light-mode theme work (Phase 30), and release-candidate verification and toolbar normalisation passes with source-level guardrails (Phase 31). Manual browser visual QA, keyboard QA, and screen-reader QA are tracked in `RELEASE_CHECKLIST.md` and remain manual unless actually performed.

## Completed Phase Notes

### Phases 0-9 - Deterministic Backend Foundation

**Status:** Complete.

**Delivered**
- Schema enforcement and Markdown validation.
- Analysis reports and improvement task generation.
- Feedback loop and feedback weighting.
- Deterministic lexical search and context bundle generation.
- Context export packages and SHA-256 manifests.
- Deterministic security scanner with credential leak, prompt-injection, and suspicious-script-block detection.
- FastAPI surface with path-traversal blocking, rate limiting, and structured JSON errors.
- Documentation and public positioning baseline.

**Safety / Non-goals**
- No LLM, no embeddings, no remote calls.
- No autonomous content writing.

**Verification**
- Covered by the deterministic verification suite in `mcp/test_verify.py`.

### Phases 10-16 - Local Web Application Foundation

**Status:** Complete.

**Delivered**
- Astro and Svelte UI shell and guided vault bootstrap.
- Dashboard, issue review, bundle builder, export UI, security scan UI, feedback workflow UI, note browser, safe note edit API and UI.
- Visual graph explorer and missing concepts UI.

**Safety / Non-goals**
- Mutating actions remain explicit and human-confirmed.
- No autonomous note rewriting.

**Verification**
- UI build (`cd ui && npm run build`) succeeds; behaviour covered by the deterministic verification suite.

### Phases 17-26F - Distribution, MCP, Private Cloud, Memory, Trust, and Import Foundations

**Status:** Complete.

**Delivered**
- HTML bundle renderer and distribution/local app launcher (`py run.py app`).
- CI and release hardening (GitHub Actions verification workflow, README badge, `RELEASE_CHECKLIST.md`).
- Context Controller Layer (`GET /context/state`, `POST /context/plan`, `/app/controller`).
- MCP Compatibility Layer (JSON-RPC 2.0 stdio, deterministic tool, resource, and prompt catalogues).
- Private Cloud Mode (remote read-only enforcement, bearer-token auth, network deployment guidance).
- Session and Project State Layer and Safe Memory Write Queue with pending-change lifecycle.
- Device Profiles and Context Budgets.
- Trust, Staleness, and Evidence Metadata.
- Safe Markdown folder import (26A backend, 26B review UI, 26C post-import review integration, 26D edge-case hardening), Obsidian-compatible Markdown import (26E), and end-to-end import lifecycle finalisation (26F).

**Safety / Non-goals**
- Private cloud mode never permits direct vault writes from a remote read-only deployment.
- Imports are preview-first and never auto-write.
- Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain Deferred and are not started, prepared, or implied by any phase in this range.

**Verification**
- Covered by the deterministic verification suite in `mcp/test_verify.py`, the `py run.py mcp-smoke` connection test, and the local app launcher.

### Phases 29A-31C - UI/UX and Release-Candidate Guardrails

**Status:** Complete.

**Delivered**
- Phase 29A documentation guardrails and UI/UX audit; 29B navigation and information architecture redesign (Overview, Vault, Context, Review and Governance, Developer); 29C design system foundation with `--cve-*` tokens and `cve-*` primitives in `ui/src/styles/global.css`; 29D page-level UX consistency; 29E final polish and release-readiness (focus-visible coverage, disabled-state styling, raw and table overflow guards).
- Phase 30A audit; 30B app shell, theme, and primitive foundation; 30C Dashboard redesign; 30D1 Validation, Tasks, and Raw Developer real implementations; 30D2 Notes and Graph workspace redesigns; 30D3 Import, Bundles, Exports, and Security; 30E1 Pending, Trust, and Feedback governance polish; 30E2 Controller and Vault Setup polish; 30F final QA, accessibility, responsive layout, and the persisted light/dark theme toggle (`cve-theme` localStorage key, default-dark fallback).
- Phase 31A release-candidate verification checklist; 31B `cve-toolbar` page header normalisation across all migrated `/app` routes; 31C release-candidate visual QA and defect-triage documentation-honesty guardrails (source-level only).

**Safety / Non-goals**
- No backend route, API contract, schema, or MCP changes during the 29-31 range.
- No new runtime dependency, external font, icon library, or animation library.
- The agent that executed Phase 31C did not open a browser, did not perform live keyboard traversal, and did not run an assistive technology. The manual browser visual QA, keyboard QA, and screen-reader QA rows in `RELEASE_CHECKLIST.md` remain manual and unchecked.

**Verification**
- UI build green (`cd ui && npm run build`).
- Source-level guardrails covered by the deterministic verification suite.
- Manual browser visual QA, keyboard QA, and screen-reader QA remain tracked manually in `RELEASE_CHECKLIST.md` and are deferred to Phase 32.

### Phase 37 - Local Diagnostics and Support Report

**Status:** Complete.

**Delivered**
- `mcp/core/diagnostics.py` service module exposing `build_diagnostics_report`, `redact_value`, `redact_mapping`, and per-section collectors.
- `py run.py diagnostics` CLI, `GET /diagnostics` read-only HTTP endpoint, and the `/app/diagnostics` UI page under the Developer nav group.
- Deterministic redaction of secrets to a stable `<redacted>` marker. `CVE_AUTH_TOKEN` is reported as a boolean only.
- 22 deterministic tests (`test_p37_01_*` through `test_p37_22_*`) covering report shape, redaction helpers, CLI exit, HTTP envelope, token non-leakage, demo-vault body exclusion, UI presence, docs guardrails, the Phase 27/28 deferral, and the no-new-dependency rule.

**Safety / Non-goals**
- Note bodies, prompt contents, context bundle contents, and pending-change proposed content are never included.
- Local absolute paths are clearly labelled under `local_path` keys.
- No remote telemetry, no crash upload, no automatic issue reporting.
- No semantic retrieval, embeddings, LLM calls, or new runtime dependency.

**Verification**
- `py run.py diagnostics` exits 0 and emits the documented redacted JSON envelope.
- `GET /diagnostics` returns the `{status, data}` envelope with `redaction` and `runtime` sections.
- Phase 37 tests pass as part of the full suite.

### Phase 38 - Backup, Restore, and Migration Safety

**Status:** Complete.

**Delivered**
- `mcp/core/backup_restore.py` service producing local zip archives at `dist/backups/cve-backup-<utc>-<id>.zip` with `backup-manifest.json` and SHA-256 per file. Standard library only (`zipfile`, `hashlib`, `tempfile`, `shutil`).
- Backup plan covers vaults (notes, schema, templates, feedback, state) and `config/config.yaml`. Generated artefacts and note bodies are excluded.
- Preview-first restore (`build_restore_preview`, `apply_restore`) with typed `RESTORE <backup_id>` confirmation, explicit `overwrite` flag, blocking errors (`MANIFEST_MISSING`, `HASH_MISMATCH`, `UNSAFE_ARCHIVE_PATH`, `UNSAFE_RESTORE_TARGET`, `FORMAT_VERSION_UNSUPPORTED`), and migration warnings.
- `py run.py backup` (`--preview`, `--write`, `--list`, `--vault NAME`) and `py run.py restore` (`--backup`, `--preview`, `--write`, `--overwrite`, `--restore-config`, `--confirm`).
- HTTP API: `GET /backups`, `POST /backup/plan`, `POST /backup/create`, `POST /restore/preview`, `POST /restore/apply`. Write routes are added to `_WRITE_PATH_PREFIXES` and blocked in remote read-only mode.
- `/app/backups` UI page under the Developer nav group with existing-backup table, create-backup form, and typed-confirmation restore form.
- 32 deterministic Phase 38 tests (`test_p38_01_*` through `test_p38_32_*`).

**Safety / Non-goals**
- Restore rejects unsafe paths (absolute, `..`, escapes repo root).
- Restore never writes without explicit `RESTORE <backup_id>` confirmation matching the preview and an `overwrite` flag for existing targets.
- Backups are local-only inspectable zip files; nothing is uploaded.
- No registry implementation (Phase 27 remains Deferred). No semantic retrieval (Phase 28 remains Deferred). No new runtime dependency.

**Verification**
- `py run.py backup --preview` and `py run.py backup --list` succeed.
- `POST /restore/apply` blocked in remote read-only mode.
- Phase 38 tests pass as part of the full suite.

### Phase 39 - MCP Client Setup and Connection Testing

### Phase 39A - MCP Stdio Verification Batch Pass

**Status:** Complete.

**Purpose**
- Document the manual/copilot-assisted MCP verification cycle completed after Phase 39. This pass validated the MCP stdio surface, catalogue, error handling, pending-change safety, documentation, UI build, boundary separation, artefact hygiene, and final release gate, beyond the existing deterministic `mcp-smoke` command, without changing runtime behaviour.

**Delivered**
- 12-batch MCP stdio verification pass, including:
        1. Baseline verification: full repository verification gate, final git status clean, generated artefacts ignored.
        2. MCP smoke test: `py run.py mcp-smoke` passed, MCP stdio server startup verified.
        3. JSON-RPC stdio cleanliness: stdout reserved for newline-delimited JSON-RPC 2.0 only, logs/diagnostics kept off stdout.
        4. MCP catalogue audit: 29 tools, 23 resources, 7 prompts observed; catalogue stable and deterministic; no direct vault-note write tool; no autonomous accept path; no blanket "all tools are read-only" overclaim.
        5. MCP read-only tool execution: representative read-only tools executed through stdio; structured JSON-RPC responses confirmed; invalid inputs returned structured errors; no vault mutation.
        6. MCP error handling: malformed JSON, non-JSON-RPC JSON, unknown methods, missing params, invalid vaults, unsafe paths, invalid filters, and wrong parameter types returned structured JSON-RPC errors; server did not crash; stdout remained JSON-only.
        7. Pending-change safety: pending list/get/revalidate paths checked where safe; no accept path exercised; no vault notes mutated; pending changes remain human-reviewed.
        8. MCP documentation consistency: README, QUICKSTART, API, ARCHITECTURE, DEPLOYMENT, `.vscode/mcp.json`, and MCP setup UI wording checked; no drift found.
        9. UI MCP setup page build check: `/app/mcp` route built successfully; page surfaces `py run.py mcp` and `py run.py mcp-smoke`; no browser visual QA claimed.
        10. Remote/private-cloud boundary check: MCP stdio confirmed local-only; MCP stdio not confused with private-cloud HTTP API; no remote MCP transport introduced.
        11. Generated artefact hygiene: `dist/`, `ui/dist/`, context bundle exports, and generated outputs remain ignored; final git status clean.
        12. Final release gate: corrective rerun from repository root passed; all verification, validation, security, feedback, export, smoke, and UI build commands passed; final git status clean.

**Safety / Non-goals**
- Documentation-only phase; no runtime code changes, no source modifications, and no commit required by the verification itself.
- Did not perform Phase 32 manual browser visual QA, keyboard QA, or screen-reader QA.
- Did not change MCP tool names, resource URI patterns, prompt names, commands, routes, API contracts, or public behaviours.
- Did not add semantic retrieval, embeddings, LLM calls, new dependencies, or autonomous vault-note writes.
- Did not start Phase 27 or Phase 28.
- Did not alter Phase 40 planning except to keep it as the next planned implementation phase after the completed Phase 39A documentation entry.

**Verification**
- All 12 MCP verification batches completed and documented.
- All verification, validation, security, feedback, export, smoke, and UI build commands passed from the repository root.
- No source changes and no commit were required.

**Limitations**
- This was a manual/copilot-assisted verification pass, not new runtime implementation.
- Did not perform Phase 32 manual browser visual QA, keyboard QA, or screen-reader QA.
- Does not replace Phase 32 Human Release QA.


**Status:** Complete.

**Delivered**
- MCP client setup documentation in `QUICKSTART.md` section 24, with the Windows `py run.py mcp` and macOS/Linux `python3 run.py mcp` commands, a `.vscode/mcp.json` known-working configuration snippet, the working-directory reminder, an explicit distinction between the MCP stdio server, the HTTP API server, and the local web UI, a safe-use notice that the MCP layer never auto-accepts pending changes, and a troubleshooting checklist.
- `API.md` MCP section revised to remove the inaccurate "all tools are read-only" claim, state that there is no direct vault-note write path and no autonomous accept, and confirm that no semantic retrieval, embeddings, or LLM calls are introduced.
- Deterministic local smoke test command `py run.py mcp-smoke` that spawns the MCP stdio server as a subprocess, sends a minimal JSON-RPC sequence (`initialize`, `notifications/initialized`, `tools/list`, `resources/list`, `prompts/list`, a safe `cve_list_vaults` call), verifies that every stdout line parses as JSON-RPC 2.0, exits `0` on pass and non-zero on fail, prints concise diagnostics, and never mutates a vault note. Standard library only.
- `mcp/smoke.py` helper module exposing `parse_jsonrpc_line`, `check_stdout_clean`, and `run_smoke`.
- `.vscode/mcp.json` retained as the documented known-working VS Code workspace configuration; no secrets and no absolute user-specific paths.
- `/app/mcp` MCP Setup UI page rendered by `ui/src/components/McpSetup.svelte` and `ui/src/pages/mcp.astro`, exposed via the Developer sidebar group. The page is static, read-only guidance: it surfaces the start command, generic stdio config snippet (with copy buttons), the `py run.py mcp-smoke` command, the working-directory and stdio model, a conservative read-only safety notice that does not claim all MCP tools are read-only, and an explicit client-compatibility caveat.
- 24 deterministic Phase 39 tests (P39-1 through P39-24). P39-1 through P39-16 cover the docs, `.vscode/mcp.json`, the `mcp-smoke` command, the smoke helper, deterministic discovery, and the no-semantic / no-new-write-path guarantees. P39-17 through P39-24 cover the MCP Setup UI page, component, surfaced commands, working-directory and stdio wording, the read-only safety notice without overclaim, the client-compatibility caveat, and the Developer-group navigation entry.

**Safety / Non-goals**
- Examples are conservative; the documented `.vscode/mcp.json` is described as a verified VS Code example, not a guarantee of compatibility with any other MCP client.
- The MCP safety model is unchanged: no new direct vault-note write path, no autonomous accept, no semantic retrieval, no embeddings, no LLM calls.
- Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain Deferred.
- No manual browser QA is claimed; Phase 39 does not verify the rendered web UI.

**Verification**
- `py run.py mcp-smoke` reports `PASS` against the local MCP stdio server (29 tools, 23 resources, 7 prompts).
- Phase 39 tests pass as part of the full suite.

### Phase 44 - Pending Change Lifecycle and Agent Draft Hardening

**Status:** Complete (Phase 44A and Phase 44B both Complete).

**Delivered**
- Phase 44A: Formal pending-change lifecycle contract documented after live MCP testing. Storage split between the active `pending-changes/` directory (status `pending` or `invalid`) and the immutable `archive/` directory (status `accepted` or `rejected`). The list call surfaces only active records; archived records remain retrievable per ID. Acceptance re-validates against the active schema and re-checks the SHA-256 of the target note (`STALE_PENDING_CHANGE` on mismatch). Invalid records cannot be accepted. MCP draft tool descriptions now warn against unknown `title` frontmatter, against `status: draft` when the schema rejects it, and against non-canonical headings.
- Phase 44B: Archive-aware listing with a transient `archived` flag and deterministic `(created_at, id)` desc ordering. New safe `revalidate_pending_change` service helper, `POST /memory/pending/{change_id}/revalidate` HTTP route (blocked in remote read-only mode), and `cve_revalidate_pending_change` MCP tool. The revalidate surface never writes to vault notes, never accepts the proposal, never bypasses stale-hash protection, and returns `ARCHIVED_NOT_REVALIDATABLE` for archived records. UI: typed `revalidatePendingChange` helper in `ui/src/lib/api.ts`, an `archived` pill on the queue rail and inspector header, and a dedicated Revalidate section in the inspector for active pending or invalid records (accept and reject remain gated by `{#if ch.status === 'pending'}`).

**Safety / Non-goals**
- No vault note is mutated by investigation or revalidation.
- No autonomous accept; every vault write requires explicit human confirmation.
- No new direct vault-write path. The only write-like helper in `pending_changes` remains `write_pending_change`, which serialises pending JSON.
- No semantic retrieval, embeddings, or LLM invocation.
- Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain Deferred.

**Verification**
- Phase 44A and Phase 44B tests pass as part of the full suite.
- Pending-change list and revalidate endpoints behave as documented under the deterministic test suite.

## Planned Productisation Phases

The remaining planned phases focus on release readiness, public presentation, packaging, onboarding, supportability, trust, and ergonomics rather than new engine capability. **Phase 40 (Public Security Posture and Release Trust) is the next planned implementation phase**, in parallel with the manual Phase 32 (Human Release QA and Evidence Capture). The next planned phase is Phase 40. None of the planned phases below start, prepare, or imply Phase 27 (Registry and Reuse Layer) or Phase 28 (Optional Semantic Retrieval).

### Phase 32 - Human Release QA and Evidence Capture

**Status:** Planned.

**Purpose**

Perform real release-candidate QA in a browser and capture honest evidence. Phase 31C executed only automated source-level verification; Phase 32 is the human-driven complement.

**Deliver**

- Manual browser visual QA across all `/app/*` routes.
- Viewport checks across ultrawide, 2560x1440, 1920x1080, 1366x768, and a narrow mobile or tablet width.
- Light and dark theme checks.
- Keyboard-only traversal checks.
- Basic screen-reader checks using a real assistive technology (NVDA, JAWS, VoiceOver, or Narrator) where possible.
- Screenshot and evidence capture policy.
- Release-note wording that clearly states what was and was not manually verified.

**Acceptance**

- No claim of browser, keyboard, or screen-reader QA unless actually performed.
- `RELEASE_CHECKLIST.md` remains the source of truth for manual QA rows.
- Any defects found are documented and triaged.
- No backend route, API contract, schema, or MCP changes.

**Suggested Commit**

```
docs(release): record Phase 32 human visual QA evidence
```

### Phase 33 - Official Website and Public Docs

**Status:** Planned.

**Purpose**

Create a public-facing product website and documentation layer so new users can understand the project without reading the entire repository.

**Deliver**

- Website content plan and initial site and docs structure.
- Home page explaining the product in plain language.
- How-it-works page: Markdown vault, schema validation, security scan, bundle and export, MCP and API and UI.
- Security model page.
- Install and run page.
- Releases, downloads, and checksums page.
- Roadmap page.
- Licence and commercial-licensing note.
- Screenshots or UI previews where appropriate.

**Acceptance**

- Website does not position the project as generic SaaS, generic RAG, a cloud AI product, or an Obsidian replacement.
- Website reflects AGPL licensing and the separate commercial licensing possibility.
- Website links back to GitHub, README, QUICKSTART, API, and RELEASE_CHECKLIST.
- No runtime feature work.

**Suggested Commit**

```
docs(site): scaffold official product website and public docs
```

### Phase 34 - Windows Desktop Distribution

**Status:** Planned.

**Purpose**

Reduce install friction by packaging the existing local app flow for Windows.

**Deliver**

- Staged packaging plan: portable Windows bundle, Windows `.exe` launcher, installer, signed release.
- Launcher behaviour that reuses the existing local app model (start or reuse the backend server, verify or build UI presence, open the browser to `/app`, show clear dependency or setup errors).
- Release hashes and checksums.
- Source availability and AGPL compliance notes.

**Acceptance**

- No rewrite into Electron unless explicitly chosen later.
- Packaging must preserve local-first behaviour.
- The packaged app must not hide where user vault data lives.
- Packaged releases must not commit generated artefacts.
- No semantic retrieval or registry work.

**Suggested Commit**

```
build(dist): plan Windows desktop distribution staging
```

### Phase 35 - Deterministic In-App Guidance Assistant

**Status:** Planned.

**Purpose**

Add bot-like help without embeddings or LLM dependency.

**Deliver**

- Deterministic guidance panel in the UI.
- Static help registry keyed by route, user intent, and current vault state.
- Uses existing API state such as validation, tasks, trust, security, import state, and context controller recommendations.
- Answers concise operational questions ("What should I do next?", "Why is this note draft?", "Can I export safely?", "How do I import notes?", "What does pending mean?") with route links and next actions.

**Acceptance**

- No embeddings, semantic retrieval, or LLM invocation.
- No autonomous note mutation.
- Answers must be derived from current state and curated help content.
- Mutating actions must remain explicit and human-confirmed.

**Suggested Commit**

```
feat(ui): add deterministic in-app guidance assistant
```

### Phase 36 - First-Run Onboarding Workflow

**Status:** Planned.

**Purpose**

Turn the app from technically complete into approachable for a first-time user.

**Deliver**

- First-run onboarding page or guided workflow.
- User mode choices: explore demo vault, create new vault, import Markdown folder, import Obsidian vault.
- Guided steps: select or create vault, validate, inspect first task, build first context bundle, run security scan, export package, optional MCP setup.
- Persistent completion state, local only.

**Acceptance**

- Onboarding is non-destructive by default.
- Import and write actions retain preview and confirmation gates.
- The user can skip onboarding.
- No new backend capability unless strictly required for state tracking.

**Suggested Commit**

```
feat(ui): add first-run onboarding workflow
```

### Phase 40 - Public Security Posture and Release Trust

**Status:** Planned. **This is the next planned implementation phase.**

**Purpose**

Make the public security claim credible for release users.

**Deliver**

- `SECURITY.md` plan or section in the roadmap.
- Threat model documentation.
- Responsible disclosure process.
- Release checksums and hashes.
- Dependency audit guidance.
- Optional SBOM plan.
- A clear "protects against / does not protect against" section.
- AGPL source-availability note for packaged and network deployments.

**Acceptance**

- Security posture must be honest.
- No claim that deterministic scanning proves factual correctness.
- No claim that local-first means risk-free.
- No secrets committed.
- Release artefact hygiene remains enforced.

**Suggested Commit**

```
docs(security): publish public security posture and release trust plan
```

### Phase 41 - Example Vaults and Demonstration Packs

**Status:** Planned.

**Purpose**

Show concrete use cases without bloating the core product.

**Deliver**

- Example or demo plan for: cybersecurity analyst lab vault, software project documentation vault, personal knowledge vault, compliance or process vault, local LLM project-memory vault.
- Each example defines purpose, before/after validation state, sample bundle or export, screenshots or static review artefacts, and what capability it demonstrates.
- Decide whether examples live in the repo, an `examples/` directory, releases, or a companion repository.

**Acceptance**

- Examples must not bloat the main app.
- Examples must avoid private or personal data.
- Generated exports must not be accidentally committed unless intentionally included as static demo artefacts.
- No new core engine behaviour required.

**Suggested Commit**

```
docs(examples): plan example vaults and demonstration packs
```

### Phase 42 - Context Health Recommendation Layer

**Status:** Planned.

**Purpose**

Add deterministic, non-LLM recommendations that explain what the user should fix next based on validation, tasks, trust, stale notes, imports, feedback, security, and context readiness.

**Deliver**

- Recommendation categories.
- Severity and priority rules.
- Links to relevant app pages.

**Acceptance**

- Recommendations are deterministic and explainable.
- Recommendations do not mutate notes.
- Recommendations do not replace the existing task engine.
- No LLM, no embeddings, no semantic retrieval.

**Suggested Commit**

```
feat(context): plan deterministic health recommendations
```

### Phase 43 - MCP Response Ergonomics and Budget Diagnostics

**Status:** Planned.

**Purpose**

Improve MCP responses for real agent clients by making responses easier to inspect, budget, and recover from without changing core behaviour.

**Deliver**

- Clearer budget diagnostics.
- More compact response summaries where useful.
- Better truncation warnings.
- Safer troubleshooting guidance.
- Client-friendly examples.

**Acceptance**

- Existing MCP contracts remain backwards-compatible unless explicitly documented.
- No new write capability.
- No semantic retrieval.
- No LLM dependency.

**Suggested Commit**

```
feat(mcp): plan response ergonomics and budget diagnostics
```

### Phase 45 - Legacy Acronym Neutralisation (CVE)

**Status:** Planned.

**Purpose**

Reduce confusion between "CVE" as the product abbreviation for Context Vault Engine and "CVE" as the well-known security industry acronym.

**Deliver**

- Audit of public-facing strings, UI copy, docs, and headings that use the bare "CVE" abbreviation.
- A neutralisation plan that retains the internal `cve-*` token and code-symbol prefixes (which are widely used and stable) while clarifying public-facing copy.
- Documentation and release-note guidance for downstream users.

**Acceptance**

- Internal code symbol prefixes (`cve-*` CSS primitives, `cve_*` MCP tools, `CVE_AUTH_TOKEN`, etc.) are preserved to avoid a destructive rename.
- Public-facing copy is unambiguous.
- No runtime behaviour change.

**Suggested Commit**

```
docs(naming): neutralise legacy CVE acronym in public copy
```

## Completed Phase Index

This index records each individually-completed historical phase as a stable anchor for documentation drift guards. The compressed range entries under `## Completed Phase Notes` remain the human-readable summary; the per-phase stubs below act as a structured registry. Each stub records `**Status:** Complete.` and the key descriptor wording. None of the entries below start, prepare, or imply Phase 27 (Registry and Reuse Layer) or Phase 28 (Optional Semantic Retrieval).

### Phase 23 - Safe Memory Write Queue

**Status:** Complete.

Pending-change lifecycle and safe memory write queue. Does not start Phase 27. Does not start Phase 28.

### Phase 24 - Device Profiles and Context Budgets

**Status:** Complete.

Device profiles and context-budget enforcement. Does not start Phase 27. Does not start Phase 28.

### Phase 25 - Trust, Staleness, and Evidence Metadata

**Status:** Complete.

Trust, staleness, and evidence metadata on every note. Does not start Phase 27. Does not start Phase 28.

### Phase 26 - Import Pipelines

**Status:** Complete. Phase 26 is complete. Phase 26 (Import Pipelines) is complete.

End-to-end Markdown import lifecycle. Routes `/import/markdown-folder` and `/import/obsidian-vault` (UI `import-markdown` and `import-obsidian`). Obsidian-compatible imports read from a `.obsidian`-bearing folder. Does not start Phase 27. Does not start Phase 28.

#### Phase 26A - Safe Markdown Folder Import Backend

**Status:** Complete.

#### Phase 26B - Markdown Folder Import Review UI

**Status:** Complete.

#### Phase 26C - Post-Import Review Integration

**Status:** Complete.

#### Phase 26D - Import Edge-Case Hardening

**Status:** Complete. Phase 26D adds no new import sources.

#### Phase 26E - Obsidian-Compatible Markdown Import

**Status:** Complete.

#### Phase 26F - End-to-End Import Lifecycle Finalisation

**Status:** Complete.

### Phase 29 - UI/UX Quality and Design System

**Status:** Complete. Phase 29 does not supersede or start Phase 27. Phase 29 does not start Phase 28.

##### Phase 29A - Roadmap formalisation and UI/UX audit

**Status: Complete.**

##### Phase 29B - Navigation and information architecture redesign

**Status: Complete.**

##### Phase 29C - Global design system and shared UI primitives

**Status: Complete.**

##### Phase 29D - Page-level UX consistency pass

**Status: Complete.**

##### Phase 29E - Final polish, docs, and release readiness

**Status: Complete.**

### Phase 30 - UI Release Quality Pass

**Status:** Complete. Phase 30 is complete. Phase 30 (UI Release Quality Pass) is complete.

#### Phase 30A - Audit

**Status:** Complete.

#### Phase 30B - App shell, theme, and primitive foundation

**Status:** Complete.

#### Phase 30C - Dashboard Redesign

**Status:** Complete.

#### Phase 30D - Core Workflow Page Redesigns

**Status:** Complete.

##### Phase 30D1 - Validation, Tasks, Raw real implementations

**Status:** Complete.

##### Phase 30D2 - Notes and Graph workspace redesigns

**Status:** Complete.

##### Phase 30D3 - Import, Bundles, Exports, Security

**Status:** Complete.

#### Phase 30E - Review, Governance, and Developer Polish

**Status:** Complete.

##### Phase 30E1 - Pending, Trust, and Feedback governance polish

**Status:** Complete.

##### Phase 30E2 - Controller and Vault Setup polish

**Status:** Complete.

#### Phase 30F - Final QA, accessibility, responsive, light mode

**Status:** Complete. Phase 30F is complete.

### Phase 31A - Release Candidate Verification

**Status:** Complete. Phase 31A is release-candidate verification only. Phase 31A does not start Phase 27. Phase 31A does not start Phase 28.

### Phase 31B - App Header and Toolbar Normalisation

**Status:** Complete. Phase 31B is a UI polish pass focused on header and toolbar normalisation across the migrated `/app` routes.

### Phase 31C - RC Visual QA and Defect Triage

**Status:** Complete. Phase 31C performed automated source-level visual QA and defect triage guardrails only.

## Deferred Phases

Phase 27 and Phase 28 have not started, are not prepared by any completed or currently planned phase, and remain deferred until the stated preconditions are met.

### Phase 27 - Registry and Reuse Layer

**Status: Deferred.**

**Purpose**

Manage generated context packages over time.

**Possible Features**

- Package registry.
- Package list UI.
- Package verification.
- Package tags.
- Stale package detection.
- Archive or delete package.
- Compare manifests.
- Optional signing.

**Do Not Start Until**

- Exports are used frequently.
- A package browser exists.
- Multiple bundles need management.

**Suggested Commit**

```
feat(registry): add local context package registry
```

### Phase 28 - Optional Semantic Retrieval

**Status: Deferred.**

**Purpose**

Add embeddings only when deterministic lexical search becomes insufficient.

**Do Not Start Until**

- At least 75 or more real notes exist.
- Lexical search has clear failure cases.
- An embedding model choice is justified.
- A cache invalidation design is clear.
- Tests can avoid brittle ranking assertions.
- The security scanner handles retrieval input surfaces.

**Possible Features**

- Local embedding index.
- Hybrid lexical and semantic search.
- Semantic bundle selection.
- Explainable ranking metadata.
- Embedding cache invalidation.
- Model and version hash in bundle metadata.

**Suggested Commit**

```
feat(search): add optional semantic retrieval
```
