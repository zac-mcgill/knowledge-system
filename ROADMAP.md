# Context Vault Engine - Updated Master Roadmap

## Executive Direction

Context Vault Engine is moving from a usable local vault application into a private context operating layer for humans, local LLMs, and agent clients.

The current foundation is strong: deterministic Markdown validation, schema enforcement, analysis, improvement tasks, feedback, lexical search, context bundles, export packages, security scanning, FastAPI routes, the local web UI, MCP stdio compatibility, private cloud mode, session and project state, safe memory write queue, device profiles, trust/staleness/evidence metadata, safe Markdown folder import, and Obsidian-compatible Markdown import are all implemented. Phases 0 to 26 are complete. Phases 27 (Registry and Reuse Layer) and 28 (Optional Semantic Retrieval) remain deferred.

The next strategic direction should preserve the existing local-first, deterministic-first model while adding a new post-completion target:

A user can run Context Vault Engine locally or on a private personal VPS, manage it through a web UI, and expose a safe MCP-compatible context layer to local LLM clients.

This should not become generic SaaS, generic RAG, or a cloud AI product. The stronger endpoint is a self-hostable private context service.

## Product North Star

Context Vault Engine should become:

A private, deterministic context service for structured Markdown knowledge, usable by humans, local LLMs, and trusted agent clients.

Target shape:

```
Human Web UI
Local LLM Client
MCP-Compatible Client
        ↓
Context Controller
        ↓
Context Vault Engine API
        ↓
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
- Deterministic behaviour comes before semantic/LLM behaviour.
- LLM clients must not freely mutate notes.
- Semantic retrieval remains optional and deferred.

## Strategic Non-Goals

Do not turn the project into:

- generic SaaS
- generic RAG wrapper
- cloud AI service
- database-heavy CMS
- autonomous content writer
- Obsidian replacement
- multi-tenant enterprise platform
- embedding-first retrieval system

## Current Baseline

### Implemented

- Schema validation
- Analysis reports
- Improvement task generation
- Feedback loop and feedback weighting
- Deterministic lexical search
- Context bundle generation
- Context export packages
- SHA-256 manifests
- Context security scanner
- Prompt-injection and credential-pattern scanning
- FastAPI API
- Path-traversal protection
- Rate limiting
- Structured JSON errors
- Guided vault bootstrap backend/UI
- Vault dashboard and issue review UI
- Bundle/export/security UI
- Feedback/task workflow UI
- Note browser UI
- Safe note edit API
- Safe note editing UI
- Documentation suite
- Verification test suite

## Current Product State

The backend is strong. The local UI has reached a usable application baseline. The next move is to make the system better at serving structured context, not merely managing a vault.

## Current Active Phase

Phase 30 (UI Release Quality Pass) is complete. Phase 29A (Roadmap formalisation and UI/UX audit), Phase 29B, Phase 29C, Phase 29D, and Phase 29E shipped earlier and remain complete. Phase 30A, 30B, 30C, 30D (30D1, 30D2, 30D3), 30E (30E1, 30E2), and 30F all shipped. Phase 30F delivered the user-facing light/dark theme toggle (persisted via the `cve-theme` localStorage key with a default-dark fallback), completed the `--cve-*` token sweep so every primitive has explicit dark and light values, tokenised the AppLayout chrome, added source-level accessibility and responsive guardrails (form labelling, icon-only button names, status-badge text, bounded raw/diff/table viewports, narrow-viewport workbench fallback), and reaffirmed write-safety contracts (typed `OVERWRITE`, typed `DELETE <vault>`, typed `ACCEPT` / `REJECT`, import preview/write separation). Parent Phase 30 is complete. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain explicitly deferred and are not started, prepared, or implied by Phase 30 or Phase 30F.

Phase 31A (Release Candidate Verification) is release-candidate verification only. It prepares the project for a clean release candidate by documenting the automated verification command order, the manual browser visual QA matrix, the manual keyboard QA checklist, the manual screen-reader QA checklist, and release artefact hygiene rules in `RELEASE_CHECKLIST.md`. Phase 31A does not start Phase 27 (Registry and Reuse Layer) and does not start Phase 28 (Optional Semantic Retrieval); both remain Deferred. Phase 31A introduces no backend route, API contract, schema, MCP, or runtime dependency changes, performs no UI redesign or new feature work, adds no new write actions, and does not create a release tag or publish a GitHub release. Phase 30F automated source-level tests do not replace manual browser visual QA or screen-reader QA; those remain manual and are tracked in `RELEASE_CHECKLIST.md`.

Phase 31B (App Header and Toolbar Normalisation Pass) is a focused UI polish and normalisation pass that sits on top of Phase 30 and Phase 31A. It normalises the `cve-toolbar` page header contract across all migrated /app routes so page title typography, the vault selector placement, status pills, Validation/Tasks/Refresh action ordering, and responsive wrapping behaviour are consistent. Phase 31B is a UI polish pass, not feature work: it makes no backend route, API contract, schema, or MCP changes, introduces no new runtime dependency, imports no external font, redesigns no page bodies, removes no routes, and adds no new write actions. Phase 31B does not start Phase 27 (Registry and Reuse Layer) and does not start Phase 28 (Optional Semantic Retrieval); both remain Deferred.

## Phase Status Overview

| Phase | Name                                    | Status   |
|-------|-----------------------------------------|----------|
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
| 30E1  | Pending/Trust/Feedback governance polish| Complete |
| 30E2  | Controller and Vault Setup polish       | Complete |
| 30F   | Final QA, A11y, Responsive, Light Mode  | Complete |
| 31A   | Release Candidate Verification          | Active   |
| 31B   | App Header and Toolbar Normalisation    | Complete |
| 27    | Registry and Reuse Layer                | Deferred |
| 28    | Optional Semantic Retrieval             | Deferred |

## Completed Capability Summary

### Phases 0-9 - Deterministic Backend

Delivered:

- validation
- analysis
- improve/task engine
- feedback
- lexical search
- bundles
- export
- security scanning
- API routes
- graph routes
- public README/docs positioning
- complete demo vault
- schema version and expected concepts

### Phases 10-15 - Local Web Application

Delivered:

- UI shell
- vault bootstrap UI
- dashboard
- issue review
- bundle builder
- export UI
- security scan UI
- feedback workflow UI
- note browser
- safe note edit API
- safe note editing UI
- graph explorer and missing concepts UI

This completes the first major usability pass.

## Remaining Roadmap

### Phase 16 - Visual Graph and Missing Concepts UI - Complete

**Status:** Complete (Phase 16 - 2026-05-11)

**UI build:** PASS (GraphExplorer.svelte 31.75 kB / 9.00 kB gzip)
**Backend tests:** 242 (all pass, no changes to backend)

**Delivered:**
- `ui/src/components/GraphExplorer.svelte` - vault selector, graph summary metrics, node type/edge type filters, grouped searchable node browser, node inspector (neighbours + related notes + missing neighbours), missing concepts tab with ranked table and non-destructive action card generator.
- `ui/src/pages/graph.astro` - new Astro page at `/app/graph`.
- `ui/src/lib/api.ts` - `fetchGraph`, `fetchGraphNeighbors`, `fetchGraphRelated`, `fetchGraphMissing` helper functions and all associated types.
- `ui/src/layouts/AppLayout.astro` - **Graph** added to sidebar navigation.
- QUICKSTART.md, TESTING.md, ROADMAP.md updated.

**Safety:** No backend changes. Action card is non-destructive (no file writes, no API writes). Raw JSON panels collapsed by default. UI clearly labels all relationships as schema-derived and deterministic.

#### Suggested Commit

```
feat(ui): add graph and missing concept visualisation
```
---

### Phase 17A - HTML Bundle Renderer

**Status:** Complete (Phase 17A - 2026-05-11)

**Backend tests:** 254 (12 new Phase 17A tests + 6 existing P4 tests updated; all pass)
**UI build:** PASS (no frontend changes)

**Delivered:**
- `core/shared/context_html.py` - NEW: `render_context_html()` and `_render_*` helpers. Python standard library only (`html`, `json`). All user content is HTML-escaped. No remote assets. Deterministic output.
- `core/shared/context_package.py` - imports `render_context_html`; generates `context.html` before manifest; adds `context.html` to `files_info` and `manifest["files"]`; writes `context.html` to package temp dir.
- `mcp/test_verify.py` - 12 new Phase 17A tests (security, determinism, content, manifest hash); 6 existing P4 export tests updated for 7-file expectation.
- `README.md`, `QUICKSTART.md`, `TESTING.md`, `API.md` - package file list and export docs updated.

**Safety:** All note body/section/frontmatter content is HTML-escaped via `html.escape`. No `<script>` tags, no `javascript:` URLs, no remote assets, no external stylesheets. CSS is inline in a `<style>` block. Output is deterministic for identical bundle input (no render timestamps, no random IDs).

#### Suggested Commit

```
feat(export): add deterministic HTML bundle renderer
```

---

### Phase 17 - Distribution and Local App Launcher

**Status:** Complete (Phase 17 - 2026-05-11)

**Backend tests:** 264 (10 new Phase 17 launcher tests; all pass)
**UI build:** PASS (no frontend changes)

**Delivered:**
- `core/app_launcher.py` - NEW: `check_ui_built()`, `probe_server()`, `is_context_vault_health_response()`, `wait_for_server()`, `open_browser()`, `launch_server()`, `main()`. Standard library only (`subprocess`, `urllib.request`, `webbrowser`, `json`, `time`, `pathlib`).
- `run.py` - `app` command added to `USAGE` string; dispatches to `core.app_launcher.main(repo_root)`.
- `mcp/test_verify.py` - 10 new Phase 17 tests (constants, health validator, connection refused, UI build detection, command dispatch).
- `README.md`, `QUICKSTART.md`, `TESTING.md` - local app launcher documented.

**Behaviour:**
- `py run.py app` starts the FastAPI server if not already running, waits for `/health`, opens `http://127.0.0.1:8000/app` in the browser, stays attached to terminal.
- If a compatible server is already running (detected via `/health` response shape), reuses it and opens the browser - no duplicate server started.
- If port 8000 is occupied by an unrecognised process, prints a clear error and exits 1.
- If `ui/dist` is missing, prints build instructions and starts the API server anyway.
- No new external dependencies.
- `py mcp/server/mcp_server.py` direct invocation unchanged.

#### Suggested Commit

```
feat(app): add local browser launcher
```

---

### Phase 18 - CI and Release Hardening

#### Purpose

Make the public repo easier to trust.

#### Deliver

GitHub Actions workflow:

- install `requirements.txt`
- install `mcp/requirements.txt`
- run full test suite
- run validate
- run security
- optional export smoke test
- README badge
- `RELEASE_CHECKLIST.md`

#### Acceptance Criteria

- CI runs on push/PR.
- Release checklist exists.
- Generated artefacts are not committed.

#### Suggested Commit

```
ci: add verification workflow
```

---

### Phase 18B-U - Schema Builder UX Hardening - **Complete**

#### Purpose

Close the usability gap where users had to manually edit `vault_schema.py` to add expected concepts after bootstrap. Bootstrap now writes expected concepts directly into the generated schema so that Missing Concepts works immediately after vault creation.

#### Delivered

- `generate_schema_content()` accepts `expected_concepts` list; renders it as `EXPECTED_CONCEPTS` using `repr()` (injection-safe, deterministic).
- `bootstrap_vault_noninteractive()` passes cleaned concepts to schema generator; removed stale warning; returns `expected_concepts: {requested, written}` count in result.
- `POST /vault/bootstrap` API response includes `expected_concepts` counts.
- `VaultSetup.svelte` - removed "Backend limitation" amber warning; updated helper text; success panel shows concept count.
- `api.ts` - `VaultBootstrapResponse` includes optional `expected_concepts` field.
- 10 new P18BU tests covering generation, deduplication, injection safety, importability, API response, and `GET /missing`.
- Docs updated: QUICKSTART.md, API.md, TESTING.md, ROADMAP.md.

#### Suggested Commit

```
feat(bootstrap): write expected concepts into generated schemas
```

---

### Phase 18C - Vault Lifecycle Management - **Complete**

#### Purpose

Allow users to safely delete non-demo vaults through the API and UI without manually editing `config.yaml`. Deletion is destructive and requires explicit typed confirmation.

#### Delivered

- `mcp/core/vault_delete.py` (NEW) - service layer with `validate_delete_request()`, `assert_safe_vault_path()`, `update_config_after_delete()`, and `delete_vault()`.
- `mcp/core/note_index.py` - `clear_vault_index(vault_name)` evicts a vault's in-process note index.
- `mcp/core/result_cache.py` - `clear_vault_cache(vault_name)` clears all cached results for a vault.
- `DELETE /vault/{vault_name}` endpoint - requires exact `"DELETE {vault_name}"` confirmation; protects `demo-vault` and the last remaining vault; updates config atomically; clears registry, index, and cache.
- `ui/src/lib/api.ts` - `deleteVault()`, `VaultDeleteRequest`, `VaultDeleteResponse`.
- `ui/src/components/VaultSetup.svelte` - Danger Zone section with vault selector, confirmation phrase input, and delete button; post-delete localStorage fallback.
- 18 new P18C tests covering all error paths, happy path, config updates, cache clearing, and UI/API contract assertions.
- Docs updated: QUICKSTART.md, API.md, TESTING.md, ROADMAP.md.

#### Safety Design

- Vault path resolved only from registry (never from user input).
- `demo-vault` is permanently protected.
- Last vault is protected.
- Directory deleted first; config updated only after successful deletion.
- Exact case-sensitive confirmation phrase prevents accidental or agent-triggered deletion.

#### Suggested Commit

```
feat(vault): safe vault deletion with typed confirmation
```

---

### Phase 19 - Context Controller Layer - **Complete**

#### Purpose

Add the orchestration layer between local LLM/tool clients and raw API routes.

A weak local LLM should not decide low-level retrieval strategy. It should ask for context, and the controller should choose the plan.

#### Delivered

- `mcp/core/context_controller.py` - deterministic controller service; exports `get_context_state(vault_name)` and `build_context_plan(vault_name, intent)`.
- `GET /context/state` - returns a full snapshot: per-service summaries, 7 boolean readiness flags, blockers, and warnings.
- `POST /context/plan` - accepts one of five intents (`review`, `export`, `agent-context`, `quality`, `security`) and returns a ranked recommendation list with `next_best_action`.
- UI page at `/app/controller` backed by `ContextController.svelte` - vault/intent selectors, readiness grid, service summary table, recommendation list.
- "Controller" nav item added to `AppLayout.astro`.
- 19 Phase 19 test cases added to `mcp/test_verify.py`.
- `API.md` updated with full endpoint documentation.

#### Acceptance Criteria - Met

- Controller is deterministic: same vault + intent always returns the same output.
- Controller is read-only: no vault files are mutated.
- No LLM is invoked; all output is derived from current vault state.
- Security scan status is reflected in readiness flags.

#### Commit

```
feat(context): add context controller layer (Phase 19)
```

---

### Phase 20 - MCP Compatibility Layer - **Complete**

#### Purpose

Allow local LLM apps and agent clients to use Context Vault Engine as a read-only MCP tool server.

#### Delivered

MCP stdio server (`py run.py mcp`) using JSON-RPC 2.0 over stdin/stdout:

**Tools (10):** `cve.list_vaults`, `cve.get_context_state`, `cve.get_context_plan`, `cve.query_notes`, `cve.get_note`, `cve.validate_vault`, `cve.get_tasks`, `cve.get_missing_concepts`, `cve.security_scan`, `cve.build_context_bundle`

**Resources (9 URI patterns):** `cve://vaults`, vault summary, state, plan, notes, tasks, missing, security, graph

**Prompts (4):** `cve.vault_review`, `cve.security_review`, `cve.context_handoff`, `cve.quality_plan`

#### Files Created

- `mcp/core/mcp_protocol.py` - JSON-RPC 2.0 protocol handler
- `mcp/core/mcp_tools.py` - tool catalogue and dispatch
- `mcp/core/mcp_resources.py` - resource catalogue and read
- `mcp/core/mcp_prompts.py` - prompt definitions with safety footer
- `mcp/server/mcp_stdio_server.py` - main stdio server loop

#### Files Modified

- `run.py` - added `mcp` command
- `mcp/test_verify.py` - 41 Phase 20 tests
- `README.md`, `QUICKSTART.md`, `API.md`, `TESTING.md`, `ROADMAP.md` - updated docs

#### Rules Met

- All tool calls are read-only and deterministic.
- No destructive mutation tools exposed.
- Path traversal blocked for `get_note` and resource URIs.
- All prompts include safety footer.
- Logs go to stderr only; stdout is clean JSON-RPC.

---

### Phase 21 - Private Cloud Mode

#### Purpose

Support the post-completion use case: run Context Vault Engine on a personal VPS/private server and connect local LLM clients from phone or desktop.

#### Target User Story

As a user, I can run Context Vault Engine as a private service on my VPS and connect a local LLM app on my phone through a private/authenticated MCP endpoint.

#### Deliver

- server deployment docs
- private network guidance
- token-based auth
- HTTPS/reverse proxy guide
- environment config
- service mode
- read-only remote mode
- backup guidance
- health/status checks

#### Preferred Access Models

- Tailscale
- WireGuard
- Cloudflare Tunnel with Access
- authenticated HTTPS

#### Hard Rules

- Do not expose unauthenticated API publicly.
- Do not expose raw file writes.
- Default remote mode is read-only.
- Write paths require auth and validation.
- Secrets must not live in the repo.

#### Acceptance Criteria

- VPS deployment documented.
- Private access works.
- MCP endpoint can be copied into a local LLM client.
- Health check confirms remote readiness.
- Security guidance is explicit.

#### Suggested Commit

```
feat(deploy): add private cloud mode
```

---

### Phase 22 - Session and Project State Layer

**Status:** Complete

**Backend tests:** 429 (33 new Phase 22 tests; all pass)
**UI build:** PASS (no frontend changes in this phase)

#### Purpose

Give weak local LLMs durable continuity without relying on chat history. Deterministic, human-readable, file-backed session/project state so CVE can answer "where was I?" and local LLMs can resume work.

#### Delivered

- `mcp/core/session_state.py` (NEW) - session and project state service. Functions: `start_session`, `resume_session`, `summarise_session`, `attach_note_to_session`, `close_session`, `list_sessions`, `get_project_state`, `update_project_state`, `_atomic_write_json`. Pure stdlib. All writes atomic via temp-file + replace. All functions accept `_vault_path` for test isolation.
- Session records: `session_id`, `status`, `active_vault`, `current_project`, `current_topic`, `recent_notes`, `user_goal`, `created_at`, `last_activity`, `closed_at`, `summary`.
- Project state: `vault`, `current_phase`, `completed_work`, `next_actions`, `blockers`, `decisions`, `risks`, `updated_at`.
- 7 new HTTP endpoints: `POST /session/start`, `GET /session/resume`, `GET /session/summary`, `POST /session/attach-note`, `POST /session/close`, `GET /project/state`, `PUT /project/state`.
- 7 new MCP tools: `cve.start_session`, `cve.resume_session`, `cve.summarise_session`, `cve.attach_note_to_session`, `cve.close_session`, `cve.get_project_state`, `cve.update_project_state`.
- 2 new MCP resource templates: `cve://vault/{vault}/session/current`, `cve://vault/{vault}/project-state`.
- `cve.resume_work` MCP prompt for guided "where was I?" workflow.
- 2 new CLI commands: `py run.py session`, `py run.py project-state`.
- Write routes blocked when `CVE_REMOTE_READ_ONLY=true`.

#### Storage layout

```
<vault>/Vault Files/State/sessions/<YYYYMMDDTHHMMSS-xxxxxxxx>.json
<vault>/Vault Files/State/project-state.json
```

#### Acceptance Criteria - Met

- User can ask "where was I up to?" - answered from stored state.
- Local LLM can resume with explicit state via `cve.resume_work` prompt.
- Project state is stored outside model memory.
- State files are human-readable and versionable.
- Atomic writes prevent partial state corruption.
- Path traversal blocked for all note-path inputs.
- Write routes blocked under `CVE_REMOTE_READ_ONLY=true`.
- 33 new tests; all 429 tests pass.

#### Suggested Commit

```
feat(state): add sessions and project state (Phase 22)
```

---

### Phase 23 - Safe Memory Write Queue

**Status:** Complete

**Backend tests:** 507 (38 new Phase 23 tests; all pass)
**UI build:** PASS

#### Purpose

Allow local LLMs to propose context changes without directly mutating the vault. Core safety rule: "LLMs may propose changes. They must not directly rewrite notes by default."

#### Delivered

- `mcp/core/pending_changes.py` (NEW) - full pending-change service: `create_note_draft`, `suggest_note_update`, `update_note_section_draft`, `list_pending_changes`, `review_pending_change`, `accept_pending_change`, `reject_pending_change`, `validate_pending_change`. Pure stdlib. All writes atomic. All functions accept `_vault_path` for test isolation.
- Pending change records: `id`, `type`, `vault`, `path`, `section`, `proposed_content`, `reason`, `source`, `created_at`, `updated_at`, `status`, `validation_status`, `validation_errors`, `diff`, `original_content_hash`, `proposed_content_hash`, `session_id`, `project`, `applied_at`, `rejected_at`, `reviewer`, `audit_note`.
- 7 new HTTP endpoints: `GET /memory/pending`, `POST /memory/create-note-draft`, `POST /memory/suggest-note-update`, `POST /memory/update-section-draft`, `GET /memory/pending/{id}`, `POST /memory/pending/{id}/accept`, `POST /memory/pending/{id}/reject`.
- 7 new MCP tools: `cve.create_note_draft`, `cve.suggest_note_update`, `cve.update_note_section_draft`, `cve.list_pending_changes`, `cve.review_pending_change`, `cve.accept_pending_change`, `cve.reject_pending_change`.
- 1 new MCP resource template: `cve://vault/{vault}/pending-changes`.
- `cve.review_pending_change` MCP prompt for guided review workflow.
- 1 new CLI command: `py run.py pending`.
- `ui/src/components/PendingChanges.svelte` - vault selector, change list, detail panel, diff display, accept/reject with confirmation.
- `ui/src/pages/pending.astro` - Pending Changes page.
- Write routes blocked when `CVE_REMOTE_READ_ONLY=true`.

#### Storage layout

```
<vault>/Vault Files/State/pending-changes/<YYYYMMDDTHHMMSS-xxxxxxxx>.json        (active)
<vault>/Vault Files/State/pending-changes/archive/<YYYYMMDDTHHMMSS-xxxxxxxx>.json (accepted/rejected)
```

#### Acceptance Criteria - Met

- LLM can propose note changes; proposals are stored, not applied.
- Human reviews full diff before accepting.
- Accept validates schema and checks staleness hash before writing.
- Rejected/accepted proposals archived; nothing deleted.
- Write routes blocked under `CVE_REMOTE_READ_ONLY=true`.
- 38 new tests; all 467 tests pass.

#### Suggested Commit

```
feat(memory): add pending change review queue (Phase 23)
```

---

### Phase 24 - Device Profiles and Context Budgets

**Status:** Complete

**Backend tests:** 507 (40 new Phase 24 tests; all pass)
**UI build:** PASS

#### Purpose

Make context output usable by different clients, especially small local LLMs on phones.

#### Delivered

- `mcp/core/context_profiles.py` (NEW) - profile service: `get_builtin_modes`, `get_builtin_profiles`, `list_context_profiles`, `get_context_profile`, `resolve_context_profile`, `validate_context_profile`, `apply_context_profile_to_request`, `profile_status_summary`. Pure stdlib.
- Built-in modes: `tiny` (2 notes / 2k chars), `small` (5 / 8k), `medium` (10 / 20k), `large` (25 / 80k), `agent` (50 / 200k).
- Built-in device profiles: `phone-local-llm`, `desktop-agent`, `full-review`.
- New endpoints: `GET /context/profiles`, `GET /context/profiles/{name}`.
- `POST /context/bundle`, `POST /context/export`, `POST /context/security` now accept `profile` and `mode` fields; responses include `profile_metadata`.
- 1 new MCP tool: `cve.list_context_profiles`.
- Updated MCP tools: `cve.build_context_bundle` and `cve.security_scan` accept `profile`/`mode`.
- New MCP resource: `cve://context/profiles`; per-profile resources `cve://context/profile/{name}`.
- 1 new CLI command: `py run.py profiles`.
- `ui/src/components/BundleBuilder.svelte` - profile/mode selector panel; mode badges; device profile badges; effective budget summary; override labels (⚠); `profile_metadata` in result panel.
- `ui/src/lib/api.ts` - `ProfileMetadata`, `ContextProfileDefinition`, `ContextProfilesData` types; `fetchContextProfiles`, `fetchContextProfile` functions.

#### Acceptance Criteria - Met

- User can select a profile/mode in Bundle Builder; defaults applied to manual controls.
- Local LLM receives bounded context; profile enforces max_notes/max_chars.
- Profile values are defaults only; explicit request fields always override.
- Hard caps (`max_notes ≤ 100`, `max_chars ≤ 500,000`) always enforced.
- `profile_metadata` in all context endpoint responses.
- `GET /context/profiles` and `GET /context/profiles/{name}` accessible in read-only mode.
- 40 new tests; all 507 tests pass.

#### Suggested Commit

```
feat(context): add device profiles and context budgets (Phase 24)
```

---

### Phase 25 - Trust, Staleness, and Evidence Metadata

**Status: Complete**

Optional `trust_level`, `source_type`, `last_reviewed`, `review_after` frontmatter fields. Trust metadata service (`trust_metadata.py`) with confidence scoring, staleness detection, and evidence builder. `/trust`, `/stale`, and `/evidence` REST endpoints. MCP tools (`cve.get_trust_summary`, `cve.get_stale_notes`, `cve.build_evidence`), resources (`cve://vault/{vault}/trust`, `cve://vault/{vault}/stale`), and prompt (`cve.evidence_review`). Trust & Evidence UI page at `/app/trust`. CLI `trust` and `stale` commands. Validation extended to check trust field values. 41 new tests (548 total).

---

### Phase 26 - Import Pipelines

**Status: Complete - Phase 26A, Phase 26B, Phase 26C, Phase 26D, Phase 26E, and Phase 26F complete. Other import sources remain deferred.**

#### Purpose

Make it easier to ingest existing knowledge without bypassing schema controls.

#### Import Sources

- Markdown folder (Phase 26A backend, Phase 26B review UI, Phase 26C post-import review integration, Phase 26D edge-case hardening, Phase 26E Obsidian-compatible mode, Phase 26F lifecycle finalisation - implemented)
- Obsidian vault (deferred)
- GitHub repo docs (deferred)
- Copilot/agent reports (deferred)
- chat transcript (deferred)
- browser article (deferred)
- PDF-to-Markdown (deferred)

#### Flow

1. import raw content
2. scan
3. extract metadata
4. map to schema
5. mark as draft
6. generate improvement tasks

#### Rules

- Imported content starts as draft.
- Imported content is security-scanned.
- Imported content must validate or produce tasks.
- Import should not blindly trust external text.

#### Acceptance Criteria

- User can import Markdown safely. (Phase 26A - done)
- Imported files are schema-mapped. (Phase 26A - done)
- Invalid imports produce actionable tasks. (Phase 26A - done)
- No unsafe path writes. (Phase 26A - done)
- User can preview and confirm imports through the browser before writing. (Phase 26B - done)
- After import, the user can review imported notes in context (filters, trust metadata, validation, tasks) without any automatic trust promotion or LLM rewriting. (Phase 26C - done)
- The Markdown import pipeline handles real-world edge cases (malformed YAML, duplicate keys, null bytes, oversize files, nested folders, duplicate filenames, Windows backslashes, destination collisions) deterministically and with clear item-level error codes, without crashing the batch and without adding new import sources. (Phase 26D - done)
- A safe, Obsidian-compatible Markdown import mode imports notes from an Obsidian vault folder, skipping `.obsidian/` config and binary attachments, preserving wikilinks verbatim, surfacing wikilinks, embeds, tags, aliases, callouts, and attachment references as deterministic per-item metadata, and reusing the entire Phase 26A-D safety pipeline. (Phase 26E - done)
- The full import lifecycle is verified end-to-end across `/notes`, `/query`, `/validation`, `/tasks`, `/trust`, `/context/bundle`, export, and graph build for both Markdown folder and Obsidian-compatible imports, both endpoints expose a single per-item contract (`source_path`, `destination_path`, `action`, `status`, `fields`, `warnings`, `errors`, `security`, `validation`) with Obsidian metadata strictly additive, repeated dry-run / overwrite-false / overwrite-true behaviour is deterministic, and the documentation set names Phase 26 complete without implying any deferred source is implemented. (Phase 26F - done)

#### Phase 26A Summary

Phase 26A delivers `core/shared/import_pipeline.py`, the `POST /import/markdown-folder` API endpoint, and the `py run.py import-markdown` CLI command. The pipeline discovers Markdown files deterministically, scans each source body via the project security scanner, drops unknown source frontmatter, recomputes section booleans from body content, marks imports with `trust_level: draft` and `source_type: imported`, serialises candidate notes, validates them through the existing `validate_file` engine, and writes only when validation passes. Default destination is `Imported/`, default mode is dry-run, no overwrite, no writes inside `Vault Files/`, and the note index plus result cache are invalidated after any successful write so imported notes appear immediately in `/notes`, `/query`, `/validation`, and `/tasks`. Other import sources remain deferred.

#### Phase 26B Summary

Phase 26B adds the Import Review UI without changing the Phase 26A backend. It introduces a new browser page at `/app/import`, a Svelte `ImportReview` component, and an `Import` nav item in the app sidebar. The component talks to the existing `POST /import/markdown-folder` endpoint via a new typed `importMarkdownFolder` helper in `ui/src/lib/api.ts`. Preview/dry-run is the default first action; the write button is disabled until a successful preview exists, the user has ticked an explicit confirmation checkbox, and the form values still match the previewed values. Any change to vault, source folder, destination, or overwrite marks the preview stale. The page surfaces every summary field (`discovered`, `planned`, `written`, `skipped`, `blocked`, `errors`, `warnings`), every per-item destination path, action, status, security and validation state, and full warning and error lists. Errors are mapped to non-developer language. The source folder field is a plain text input with helper text explaining that the path is resolved on the backend host. Markdown folder import only; PDF, GitHub repo, browser article, Obsidian-specific, chat transcript, semantic, and LLM-extraction imports remain deferred and are not exposed as buttons or actions in the UI.

#### Suggested Commit

```
feat(ui): add markdown import review workflow
```

#### Phase 26C Summary

Phase 26C extends the Phase 26B Import Review UI with a post-import review path and integrates imported notes into the existing Notes browsing surface. After a successful write, the Import Review page renders an Imported Review Summary panel (imported total, imported drafts, imported with validation issues, imported with tasks, imported stale, imported deprecated) and vault-aware follow-up links into Notes (with `imported`, `draft`, and `imported-draft` filters), Validation, Tasks, Trust, Security, and the dashboard. The Notes page now reads `source_type` and `trust_level` from the `/notes` listing (now surfaced by `notes_adapter.get_notes`) and offers Imported-only and Draft-trust-only filters, deep-link URL parameters (`vault`, `filter`, `path`) for cross-page navigation, badges on every row, and a Trust and Import detail panel showing `source_type`, `trust_level`, `last_reviewed`, `review_after`, `confidence`, and `stale`. The Trust and Import panel includes the standing disclaimer that trust metadata reflects review and maintenance state only and does not prove factual correctness. No automatic trust promotion, no automatic LLM rewriting, no new import sources. PDF, browser article, GitHub repo, Obsidian-specific, chat transcript, semantic, and LLM-extraction imports remain deferred.

#### Suggested Commit

```
feat(ui): add post-import review workflow
```

#### Phase 26D Summary

Phase 26D hardens the Markdown import workflow against real-world edge cases without adding any new import sources. The pipeline now reports `INVALID_FRONTMATTER` for orphan opening markers, `FRONTMATTER_NOT_OBJECT` for non-mapping YAML, `DUPLICATE_YAML_KEY` for duplicate mapping keys, `NULL_BYTE` for sources containing null bytes, and `SOURCE_TOO_LARGE` for sources exceeding the 5 MB cap, all at the item level so one bad file no longer crashes the batch. Dry-run is deterministic across repeated identical inputs, summary counts (`discovered`, `planned`, `written`, `skipped`, `errors`, `warnings`) match per-item statuses exactly, and repeated writes with `overwrite=false` skip existing destinations deterministically with `DESTINATION_EXISTS`. Filename punctuation, non-ASCII characters, and empty stems collapse deterministically to safe slugs (with an `untitled` fallback). Nested source folders preserve their relative structure under the destination, duplicate filenames in different folders produce distinct destinations, and Windows backslash destinations are normalised into forward slashes. Section booleans are still recomputed from the body and invalid source enum values are still replaced with schema-safe values. The Import Review UI now surfaces a dedicated `DESTINATION_EXISTS` collision banner, a dedicated malformed-frontmatter banner, a clearer empty-items message that names the `.md` extension and the Markdown-only scope, and per-item plain-language labels for every Phase 26D error code. Phase 26D adds no new import sources, no semantic mapping, no LLM extraction, no automatic trust promotion, and no automatic content rewriting. PDF, browser article, GitHub repo, Obsidian-specific, chat transcript, semantic, and LLM-extraction imports remain deferred.

#### Suggested Commit

```
test(import): harden markdown import workflow edge cases
```

#### Phase 26E Summary

Phase 26E adds a safe, Obsidian-compatible Markdown import on top of the hardened Phase 26A-D pipeline. The new endpoint `POST /import/obsidian-vault` and CLI `py run.py import-obsidian` accept the root of an Obsidian vault folder, skip `.obsidian/` config and binary attachments, ignore `.canvas` files, and reuse every Phase 26A-D safety control (null-byte rejection, oversize rejection, duplicate YAML key detection, malformed-frontmatter detection, security scan before write, schema validation before write, destination safety checks, atomic writes, cache and index invalidation, dry-run by default, no overwrite by default). Obsidian wikilinks (`[[Note]]`, `[[Note|Alias]]`, `[[Note#Heading]]`, `[[Note#^block-id]]`) are preserved verbatim in note bodies. Each item carries a deterministic `obsidian` metadata block with sorted, de-duplicated lists for wikilinks, embeds, tags (YAML and inline `#tag`), aliases, callouts (lowercased), block references, and attachment references, plus advisory warnings for preserved wikilinks and detected attachments. Unknown Obsidian YAML fields are dropped from the written note and surfaced under the per-item metadata. The default destination is `Imported/Obsidian`. The Import Review UI gains a source-type selector (Markdown folder / Obsidian vault), helper text describing the Obsidian rules, a per-item Obsidian metadata section, and stale-preview detection on source-type changes; explicit confirmation is still required before any write. No automatic wikilink rewriting, no automatic trust promotion, no automatic LLM rewriting, and no new import sources beyond Obsidian-compatible Markdown. PDF, GitHub repo, browser article, chat transcript, semantic mapping, and LLM-extraction imports remain deferred.

#### Suggested Commit

```
feat(import): add Obsidian-compatible Markdown import
```

#### Phase 26F Summary

Phase 26F finalises the Phase 26 Import Pipelines without adding any new import source. It adds 20 end-to-end tests (`test_p26f_1`..`test_p26f_20`) that exercise the full import lifecycle: Markdown folder and Obsidian-compatible writes are verified against `/notes`, `/query`, `/validation`, `/tasks`, `/trust`, `/context/bundle`, `export_context_package`, and graph build; both endpoints share the same per-item contract (`source_path`, `destination_path`, `action`, `status`, `fields`, `warnings`, `errors`, `security`, `validation`) with Obsidian metadata strictly additive (per-item `obsidian` block, `source_type: "obsidian-vault"`, summary wikilink/embed/attachment counters); repeated dry-run, overwrite-false skip, and overwrite-true update behaviour are all deterministic across both source types; Obsidian-specific YAML keys are surfaced in the response but never leak into the written frontmatter while wikilinks are preserved verbatim in the body. The documentation set (`README.md`, `QUICKSTART.md`, `API.md`, `TESTING.md`, `ROADMAP.md`, `RELEASE_CHECKLIST.md`) is consolidated to declare Phase 26 complete, list the implemented (Markdown folder, Obsidian-compatible) and deferred (PDF, GitHub repo, browser article, chat transcript, semantic, LLM-extraction) sources, document the Obsidian limitations (wikilinks preserved not rewritten, binary attachments detected not imported, `.canvas` not imported), and reaffirm that imported content still requires human review with no automatic trust promotion and no automatic LLM rewriting. New doc-drift guardrails (`test_p26f_20`) keep these guarantees in place.

#### Suggested Commit

```
docs(import): finalise Phase 26 import lifecycle
```

---

### Phase 29 - UI/UX Quality and Design System

**Status: Complete.**

#### Purpose

Phases 0 to 26 delivered the backend, the API surface, the MCP layer, and a functional but unpolished local web UI. Phase 29 turns that functional UI into a coherent, navigable, and visually consistent application without changing backend behaviour, route contracts, or the local-first deterministic model.

Phase 29 is a UI/UX quality phase only. It does not introduce semantic retrieval, a registry, SaaS features, cloud dependencies, or LLM-driven UI behaviour. It does not start Phase 27 or Phase 28, and it does not change any backend API contract.

#### Scope

- Information architecture and sidebar grouping.
- Shared design system tokens (colour, spacing, typography, radius, focus).
- Reusable UI primitives (card, button, badge, table, empty state, raw JSON panel, dangerous action confirm, trust warning, page header).
- Page-level consistency across existing routes.
- Final polish, accessibility minimums, and docs.

#### Non-Goals

- No new backend routes.
- No removal of existing backend routes.
- No semantic retrieval.
- No registry.
- No cloud features.
- No LLM-driven UI behaviour.
- No React introduction unless a future sub-phase demonstrates a concrete reason and Svelte is materially worse for that specific use case.
- No removal of existing pages unless a sub-phase is explicitly documentation-only and only recommends consolidation.
- No changes to runtime CLI, API, or MCP behaviour.

#### Sub-Phases

##### Phase 29A - Roadmap formalisation and UI/UX audit

**Purpose**

Make the UI/UX direction official in the project roadmap, document the existing UI and routes, identify the design and information architecture problems, and propose the sequence for sub-phases 29B to 29E. Documentation and tests only.

**Scope**

- Add this Phase 29 section to ROADMAP.md.
- Produce `UI_UX_AUDIT.md` with executive verdict, screenshot findings, route inventory, component inventory, information architecture recommendation, proposed sidebar grouping, page consolidation recommendations, design system proposal, React decision, recommended sequence for 29B to 29E, and risks/non-goals.
- Update TESTING.md, README.md, and RELEASE_CHECKLIST.md to reflect that Phase 29A is active and is documentation/audit only.
- Add deterministic guardrail tests that prevent docs from drifting on Phase 29 status, Phase 27 deferral, and Phase 28 deferral.

**Non-Goals**

- No UI implementation.
- No CSS redesign.
- No component rewrites.
- No page consolidation.
- No backend changes.
- No dependency changes.

**Acceptance Criteria**

- ROADMAP.md lists Phase 29 in the status table and includes a full Phase 29 section with all five sub-phases (29A to 29E).
- ROADMAP.md still marks Phase 27 and Phase 28 as Deferred.
- ROADMAP.md Current Active Phase references Phase 29A.
- `UI_UX_AUDIT.md` exists and contains the required sections.
- TESTING.md documents Phase 29A and the new tests are wired into the manual runner.
- README.md does not claim any Phase 29 UI implementation is complete.
- All previous verification commands still pass.

**Suggested Commit**

```
docs(phase29a): formalise UI/UX quality phase and produce audit plan
```

##### Phase 29B - Navigation and information architecture redesign

**Status:** Complete (Phase 29B - 2026-05-12)

**Purpose**

Reorganise the sidebar and top-level navigation around user intent groups (for example: Overview, Vault, Review/Governance, Context, Imports, Developer) rather than a flat list, and surface the active vault clearly in the chrome. Implements the information architecture recommendation from `UI_UX_AUDIT.md`.

**Scope**

- Sidebar grouping with section headers.
- Active state, hover state, focus-visible state.
- Persistent vault selector in the layout chrome rather than per page.
- Mobile navigation pattern that matches the new groups.
- No backend changes. No route removals.

**Non-Goals**

- No new pages.
- No design tokens beyond what is strictly required for the new nav.
- No React.

**Acceptance Criteria**

- All current routes remain reachable.
- Sidebar groups match `UI_UX_AUDIT.md` proposed grouping.
- Keyboard navigation reaches every nav item and visibly focuses it.
- Mobile shell still works.
- `cd ui; npm run build` succeeds with zero errors.
- Backend tests are unchanged.

**Delivered**

- `ui/src/layouts/AppLayout.astro` rewritten with a data-driven `navGroups` array. Five groups: Overview, Vault, Context, Review and Governance, Developer. Every existing `/app/*` route is preserved and reachable.
- Semantic `<nav aria-label="Primary">` landmark wrapping the sidebar.
- `aria-current="page"` on the active link, with a visible left accent rail and stronger background.
- Visible keyboard focus state implemented via a plain CSS `:focus-visible` rule on `.cve-nav-link`.
- Brand/header hierarchy improved: primary label "Context Vault" with secondary label "Engine" in a separate uppercase strap.
- Footer label refreshed from the stale "Phase 18 - Stable" to "Phase 29B - Navigation".
- No new dependencies, no React, no client-side JS required for the sidebar, no route renames, no page consolidation.

**Suggested Commit**

```
feat(ui): grouped sidebar and information architecture (Phase 29B)
```

##### Phase 29C - Global design system and shared UI primitives

**Status: Complete.**

**Purpose**

Introduce a shared design system that every page consumes. Define tokens for colour (background, surface, border, text, muted text, accent, danger, warning, success, info), typography, spacing, radius, and focus, expressed either as CSS custom properties or Tailwind theme extensions. Extract reusable Svelte primitives for the patterns used across multiple existing components.

**Scope**

- Design tokens.
- Shared primitives: page header, card, button (primary/secondary/ghost/danger), badge (status/trust/severity), status indicator, raw JSON expander, empty state, loading state, error state, success state, table, dangerous action confirm, trust/security warning.
- Migration of one or two existing pages to the new primitives as a worked example. Other pages are migrated in Phase 29D.
- No backend changes.

**Non-Goals**

- No new business behaviour.
- No new dependencies.
- No React.

**Acceptance Criteria**

- Tokens exist and are documented in the audit or in a new `ui/src/styles/` doc.
- Primitives compile and are used in at least one page.
- Keyboard focus is visible on every interactive primitive.
- `cd ui; npm run build` succeeds.
- Backend tests are unchanged.

**Delivered**

- `ui/src/styles/global.css` now formalises a token layer using CSS custom properties for app background, elevated and muted surfaces, hairline and soft borders, strong/normal/muted/faint text, accent and accent-soft, success, warning, danger, info, and focus ring, alongside a documented radius and spacing scale.
- A `cve-*` class layer adds shared primitives for typography (`cve-app-title`, `cve-page-title`, `cve-section-title`, `cve-card-title`, `cve-body`, `cve-meta`, `cve-mono`), layout (`cve-shell`, `cve-page`, `cve-page-header`, `cve-stack`, `cve-section`, `cve-card-grid`, `cve-meta-row`), cards (`cve-card` with `--muted` and `__header` modifiers), buttons (`cve-btn` plus primary/secondary/ghost/danger variants), badges (neutral/success/warning/danger/info/draft/deprecated), alerts (info/success/warning/danger), forms (`cve-field`, `cve-label`, `cve-helper`, `cve-input`, `cve-select`, `cve-textarea`), tables and lists (`cve-table-wrap`, `cve-table`, `cve-list`), state patterns (`cve-empty`, `cve-loading`, `cve-error`, `cve-success`), raw JSON and details blocks (`cve-raw`, `cve-details`), and dangerous-action, warning, and trust-warning blocks (`cve-danger-zone`, `cve-warning-block`, `cve-trust-warning`).
- A single `:focus-visible` rule targets every interactive primitive and references the `--cve-focus` token, ensuring keyboard focus remains visible without removing native focus rings.
- A `prefers-reduced-motion` guard is documented even though Phase 29C introduces no animations, so any future motion is opt-out by default.
- `ui/src/layouts/AppLayout.astro` is unchanged and still ships the Phase 29B grouped sidebar (Overview, Vault, Context, Review and Governance, Developer) with `/app/raw` surfaced as API / Raw under Developer. All 15 existing `/app/*` routes are preserved; no page is consolidated.
- 19 new tests (`test_p29c_1` through `test_p29c_19`) verify tokens, every shared primitive class, the focus-visible rule, the AppLayout navigation, and the deferral status of Phases 27 and 28. Documentation drift guardrails are updated to the new total of 740 test functions.

**Suggested Commit**

```
feat(ui): design system tokens and shared primitives (Phase 29C)
```

##### Phase 29D - Page-level UX consistency pass

**Status: Complete.**

**Purpose**

Migrate every existing page to the Phase 29C primitives, tighten copy, standardise empty/loading/error/success states, standardise raw JSON expanders, and apply consistent dangerous action and trust/security warning patterns. No new pages, no new backend.

**Scope**

- Apply primitives to every page under `ui/src/pages/`.
- Standardise headings, descriptions, and helper text.
- Standardise the dangerous action pattern (typed confirmation, danger button variant, audit-friendly copy).
- Standardise the trust/security warning pattern.
- Standardise the raw JSON / details pattern.

**Non-Goals**

- No backend route changes.
- No removal of existing pages. Consolidation is only allowed if it is purely cosmetic and the underlying routes remain.
- No React.

**Acceptance Criteria**

- Every page renders the new page header pattern.
- Every page handles loading, empty, and error states consistently.
- Every dangerous action uses the standardised pattern.
- Every raw JSON panel is collapsed by default and uses the standardised expander.
- `cd ui; npm run build` succeeds.
- Backend tests are unchanged.

**Delivered**

- Every Astro page under `ui/src/pages/` continues to mount its existing Svelte island. Each major Svelte component (`Dashboard`, `VaultSetup`, `NoteBrowser`, `BundleBuilder`, `ExportPackage`, `SecurityScan`, `FeedbackWorkflow`, `GraphExplorer`, `ContextController`, `PendingChanges`, `TrustEvidence`, `ImportReview`) and the `PlaceholderPage.astro` shim now adopt the Phase 29C `cve-*` primitives: a `cve-page` shell, a `cve-page-header` containing a `cve-page-title`, plus targeted use of `cve-card`, `cve-btn`, `cve-badge`, `cve-input` / `cve-select`, `cve-table`, `cve-list`, `cve-details` / `cve-raw`, `cve-empty` / `cve-loading` / `cve-error`, `cve-danger-zone`, `cve-warning-block`, and `cve-trust-warning` where each pattern applies.
- `VaultSetup.svelte` flags its destructive vault-delete surface with `cve-danger-zone` and applies `cve-btn-danger` to the confirmation button; the typed-confirmation phrase, audit copy, and disabled-until-match behaviour are unchanged.
- `TrustEvidence.svelte` carries an explicit `cve-trust-warning` block that restates the standing disclaimer: trust metadata reflects review and maintenance state only and does not prove factual correctness.
- `ImportReview.svelte` wraps its write-confirmation block with `cve-warning-block` so import safety wording remains visually prominent; the typed checkbox and dry-run / write gating are preserved.
- `PendingChanges.svelte` adopts `cve-empty`, `cve-loading`, `cve-error`, `cve-list`, and `cve-badge` for the change list so review states are consistent with the rest of the UI.
- Phase 29B's grouped sidebar in `AppLayout.astro` is unchanged. All 15 existing `/app/*` routes still resolve. `/app/raw` continues to appear under Developer as API / Raw. No backend route is added, renamed, or removed; no dependency is added; no page is consolidated.
- 22 new tests (`test_p29d_1` through `test_p29d_22`) verify that every app page renders a `cve-page` shell, that every major Svelte component consumes at least one `cve-*` primitive, that each required primitive family is used somewhere in the UI, that destructive and trust surfaces use the documented warning blocks, that the Phase 29B navigation is intact, that Phases 27 and 28 remain deferred, that Phase 29D is recorded as Complete in `ROADMAP.md`, and that no project-authored doc modified by Phase 29D contains em dashes.

**Suggested Commit**

```
feat(ui): page-level UX consistency pass (Phase 29D)
```

##### Phase 29E - Final polish, docs, and release readiness

**Status: Complete.**

**Purpose**

Final pass before any UI release tag. Tighten visual rhythm, accessibility (keyboard focus, colour contrast, screen-reader labels for icon-only controls), responsive behaviour, and update the documentation to reflect the new UI shape without claiming behaviour that the backend does not implement.

**Scope**

- Accessibility minimums: visible focus, contrast on text and badges, labels on icon-only controls, semantic landmarks (`header`, `nav`, `main`, `aside`).
- Responsive review at common breakpoints.
- Documentation updates (README current status, QUICKSTART screenshots if any, ROADMAP marks 29 complete only when truly complete).
- Verification: `py mcp/test_verify.py`, `py run.py validate`, `py run.py security`, `py run.py feedback`, `py run.py export --overwrite`, `cd ui; npm run build`.

**Non-Goals**

- No backend changes.
- No semantic retrieval, no registry.
- No React.

**Acceptance Criteria**

- All Phase 29 acceptance criteria from 29A to 29D remain satisfied.
- Accessibility minimums pass manual inspection on every page.
- Docs reflect the implemented UI only.
- ROADMAP marks Phase 29 complete and notes Phase 27 and Phase 28 are still deferred.

**Delivered**

- `ui/src/styles/global.css` now gives `cve-details > summary` an explicit textual disclosure cue. A pseudo-element chevron and a "Show details" / "Hide details" label make every collapsed block visibly interactive without relying on the removed native triangle.
- `cve-btn:disabled`, `cve-btn[aria-disabled="true"]`, and the new `cve-btn-disabled` class share a clearly distinct visual state (reduced opacity, desaturated, not-allowed cursor, no pointer events). Disabled form controls share the same treatment.
- `cve-raw` and `cve-table-wrap` are pinned to `max-width: 100%` and scroll inside themselves so long JSON, stack traces, wide tables, and Markdown payloads no longer push the page into horizontal overflow.
- The `:focus-visible` rule now covers ordinary anchor links and native buttons inside the page shell in addition to the existing `cve-*` primitives, so keyboard focus is visible everywhere the user can land.
- A small responsive guard caps `.cve-page` at the viewport width and constrains any descendant image/svg/video to its parent, preventing accidental overflow on narrow viewports.
- The `prefers-reduced-motion` guard is preserved; the new pseudo-element transition is so short that it remains under the reduced-motion ceiling.
- `ui/src/layouts/AppLayout.astro` footer label moves from the stale "Phase 29B - Navigation" to "Phase 29 - Stable" so the visible chrome no longer claims an old sub-phase is active. Grouped navigation, `/app/raw` labelled API / Raw under Developer, and all 15 `/app/*` routes are preserved.
- Documentation closes out Phase 29: ROADMAP marks Phase 29 (and every sub-phase) Complete, TESTING.md adds a Phase 29E section, README states Phase 29 is complete while keeping Phase 27 and Phase 28 deferred, RELEASE_CHECKLIST is bumped to the new test total, and UI_UX_AUDIT records a Phase 29E implementation note plus a Phase 29 closure note.
- 24 new tests (`test_p29e_1` through `test_p29e_24`) verify the disclosure cue, the broadened focus-visible rule, the disabled-state styling, the raw and table overflow guards, the reduced-motion guard, the danger and trust warning blocks, the AppLayout grouped navigation and footer wording, the existence of every `/app` page file, the ROADMAP completion markers, the deferral of Phases 27 and 28, the TESTING/README/RELEASE/audit doc updates, the absence of em dashes in modified docs and modified UI sources, the verification command index, and that `ui/package.json` is unchanged.
- No new dependency, no new icon library, no animation library, no React, no backend route change, no route removal, no page consolidation, no business logic change.

#### Phase 29 Closure Summary

Phase 29 delivered a coherent UI/UX layer on top of the existing local web UI without touching backend contracts. Phase 29A formalised the phase and produced the audit. Phase 29B grouped the sidebar by intent and preserved every `/app/*` route. Phase 29C added the design system foundation in `global.css`. Phase 29D applied the `cve-*` primitives across every existing Svelte component. Phase 29E hardened accessibility (disclosure cues, focus-visible coverage, disabled states), pinned raw and table blocks against page overflow, refreshed the AppLayout footer wording, and closed the documentation set. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain explicitly deferred. No backend route was added, removed, or renamed during Phase 29; no React was introduced; no new dependency was added.

**Suggested Commit**

```
feat(ui): final UI/UX polish, accessibility, and docs (Phase 29E)
```

#### Phase 29 Strategic Note

Phase 29 does not supersede or start Phase 27 (Registry and Reuse Layer) or Phase 28 (Optional Semantic Retrieval). Both remain explicitly deferred. Phase 29 only addresses the UI/UX quality gap in the already-shipped local web application.

---

### Phase 30 - UI Release Quality Pass

#### Purpose

Phase 29 produced grouped navigation, semantic primitives, and a `cve-*` token layer. The screenshot-driven Phase 30A audit (consolidated in `UI_UX_AUDIT.md` sections 18 and 19) confirmed the UI is functional but not release-quality. Most pages waste ultrawide space, many use whole-page scroll where internal scroll is needed, light mode is not real today, raw JSON is overexposed across workflow pages, and several routes (Validation, Tasks, Raw / Developer Diagnostics) are still placeholders. Phase 30 closes that gap in five planned sub-phases (30B to 30F) after the Phase 30A audit.

Phase 30 does not start Phase 27 or Phase 28, does not introduce semantic retrieval, registry, LLM, RAG, SaaS, cloud, React, or charting work, and does not change backend route contracts.

#### Phase 30A - Page-by-Page UX Audit Consolidation

**Status:** Complete (Phase 30A - 2026-05-12)

**Deliver:**
- A screenshot-driven audit of all 15 `/app` routes captured in `UIReport1.txt` through `UIReport14.txt`.
- `UI_UX_AUDIT.md` section 18 "Phase 30A Audit Consolidation" with the audited route list, severity summary, cross-page root causes, per-page verdict table, real-implementation list, structural-redesign list, secondary-polish list, deferred items, and Phase 30B acceptance criteria.
- `UI_UX_AUDIT.md` section 19 "Phase 30B Implementation Brief" defining the exact foundation-only scope, out-of-scope list, and acceptance criteria for the next implementation slice.
- `ROADMAP.md` Phase 30 entries (this section), status-table rows, and Current Active Phase updated.
- `TESTING.md` documents planned Phase 30 UI guardrail families.
- `RELEASE_CHECKLIST.md` UI release-readiness section reflecting that the UI is not release-quality today and listing the criteria Phase 30 must meet.

**Acceptance criteria:**
- All documentation updates listed above are in place.
- No UI source file or test file is modified by Phase 30A.
- Phase 27 and Phase 28 remain Deferred in the status table.
- The standard verification suite passes unchanged.

**Suggested Commit**

```
docs(phase30a): consolidate UI/UX audit and brief Phase 30B foundation
```

#### Phase 30B - App Shell, Theme, Layout, and Primitive Foundation

**Status:** Complete (Phase 30B - 2026-05-12).

**Backend tests:** 800 (13 new Phase 30B guardrail tests; all pass).
**UI build:** PASS.

Foundation-only slice. Phase 30B exists so Phase 30C, 30D, 30E, and 30F do not have to re-invent layout, theme, or shared primitives per page.

**Delivered:**
- `ui/src/layouts/AppLayout.astro` - new `layoutMode` prop with `standard` (default), `wide`, `workspace`, and `developer` values. Emits `data-layout-mode` on the shell main and content containers. Default remains `standard`; existing pages render unchanged.
- `ui/src/styles/global.css` - added `html[data-theme="dark"]` and `html[data-theme="light"]` token blocks with full token parity (18 `--cve-*` tokens each); declared `color-scheme: dark light`; added new layout-mode containers (`cve-shell-main`, `cve-shell-content--{mode}`); added new primitive classes: `cve-workbench` (with rail/inspector and `cve-scroll-region`), `cve-toolbar` (main/title/meta/actions), `cve-status-strip` and `cve-status-tile`, `cve-table` sticky header + hover + `cve-table-empty`, `cve-banner` with info / warning / danger / success variants, `cve-details--inspector` and `cve-details__developer-link`, `cve-slide-over` (backdrop/panel/header/body/footer), `cve-diff` (line/add/remove/hunk). Tokenised `:focus-visible` rules cover every new primitive.
- `ui/src/pages/*.astro` - workflow pages now declare a non-`standard` layout mode: Notes / Graph / Pending / Feedback use `workspace`; Bundles / Exports / Security / Import / Controller / Trust / Validation / Tasks use `wide`; Raw uses `developer`. Dashboard, Vault Setup remain on `standard`. PlaceholderPage on Validation / Tasks / Raw is preserved (real implementation lands in Phase 30D).
- `mcp/test_verify.py` - 13 new Phase 30B guardrail tests covering the layout-mode contract, dark/light theme parity, `color-scheme` declaration, new primitive class presence, Developer nav group, Tailwind dark literal absence in new primitive CSS, preserved placeholders, and unchanged dependencies.

**Safety:** No backend route, schema, or contract change. No new runtime dependency added to `ui/package.json`. No React, Vue, charting, icon, or animation library introduced. PlaceholderPage removal is deliberately deferred to Phase 30D.

**Out of scope (handed to later phases):**
- Phase 30C - Dashboard redesign.
- Phase 30D - Core workflow page redesigns (Notes, Import, Bundles, Exports, Security, Graph, Validation, Tasks, Raw).
- Phase 30E - Review/Governance/Developer polish (Pending, Trust, Feedback, Controller, Vault Setup, Diff fill-out).
- Phase 30F - Final QA, accessibility, responsive, and user-facing light-mode toggle.

**Suggested Commit**

```
feat(ui): app shell layout modes, theme tokens, and foundation primitives (Phase 30B)
```

#### Phase 30C - Dashboard Redesign

**Status:** Complete (Phase 30C - 2026-05-12).

**Backend tests:** 818 (18 new Phase 30C tests; all pass).

**Scope:**
- Promote a canonical vault status band (validation, security, coverage, missing concepts, feedback) as the headline using `cve-status-strip` and `cve-banner`.
- Demote raw JSON disclosures into the Developer route deep-link contract.
- Make every status tile actionable with a single CTA and a last-checked timestamp.
- Resolve Dashboard / Issue Review duplication (Missing Concepts shown twice, feedback severity vs Pass headline).
- Light-mode token coverage validated on this page.

**Delivered:**
- `/app/` now mounts AppLayout with `layoutMode="wide"`.
- Dashboard rewritten around the Phase 30B primitives: `cve-toolbar` header, single `cve-banner` readiness headline (success / warning / danger / info), five-tile `cve-status-strip` (Validation, Security, Coverage, Missing concepts, Feedback) with deterministic last-checked text and a single CTA per tile deep-linking to `/app/validation`, `/app/security`, `/app/notes`, `/app/graph`, and `/app/feedback` respectively.
- Two-column `cve-dashboard-grid`: Next best actions (top three pending tasks, CTA to `/app/tasks`) and Vault health (uptime, requests, latency, rate limit, notes indexed, schema hash, index size).
- Raw JSON demoted: inline `JSON.stringify` / `Show raw JSON` / `cve-raw` blocks removed; a single `cve-details--inspector` block with a `cve-details__developer-link` deep-links to `/app/raw?vault=...`.
- Issue Review duplication eliminated.
- New Phase 30C primitives in `ui/src/styles/global.css` (`.cve-link`, `.cve-status-tile--*`, `.cve-status-tile__cta`, `.cve-status-tile__meta`, `.cve-dashboard-grid`, `.cve-kv-row*`, `.cve-next-action*`) use `var(--cve-*)` tokens only - no Tailwind dark literals.

**Out of scope:** Workflow page redesigns (deferred to 30D); Validation / Tasks / Raw implementation (also 30D); Controller redesign (deferred to 30E).

**Suggested Commit**

```
feat(ui): dashboard redesign on Phase 30B foundation (Phase 30C)
```

#### Phase 30D - Core Workflow Page Redesigns

**Status:** Complete. Phase 30D1 complete (2026-05-19). Phase 30D2 complete (2026-05-13). Phase 30D3 complete (2026-05-22).

**Scope:**
- `/app/notes` migrate to `cve-workbench` (resizable list rail + inspector with internal scroll body).
- `/app/import` state-aware layout: setup, preview, write-confirmation, with the Write action visually separated from Preview.
- `/app/bundles` sectioned builder with sticky action and state-aware right pane.
- `/app/exports` reconciled with Bundles via shared form composable; overwrite and security-pass treated as destructive with visible warning treatment; security gate on by default.
- `/app/security` defaults to full-vault scan; sampling / filter knobs demoted to "Advanced scope" disclosure; pre-run note count surfaced.
- `/app/graph` restructured to a split-pane relationship browser (node list, inspector, missing concepts surfaced inline); misnamed Graph tab dropped.
- `/app/validation` real implementation backed by `fetchValidation`.
- `/app/tasks` real implementation backed by `fetchTasks`.
- `/app/raw` real Developer endpoint explorer / JSON viewer with vault selector, request form, copy and download affordances.

**Out of scope:** Review / Governance polish (Pending, Trust, Feedback, Controller) and final QA - deferred to 30E and 30F.

**Suggested Commit**

```
feat(ui): core workflow page redesigns on Phase 30B foundation (Phase 30D)
```

#### Phase 30D1 - Validation, Tasks, and Raw Real Implementations

**Status:** Complete (Phase 30D1 - 2026-05-19).

**Backend tests:** 842 (24 new Phase 30D1 tests; all pass).

**Scope:**
- Replace the `/app/validation`, `/app/tasks`, and `/app/raw` placeholders with real, fully wired implementations on the Phase 30B foundation.
- Reuse the existing `fetchValidation`, `fetchTasks`, and read-only API helpers in `ui/src/lib/api.ts`. No backend routes added.
- Surface a Developer endpoint explorer that exposes only safe read GETs; destructive and write operations are not callable from `/app/raw`.

**Delivered:**
- `/app/validation` mounts `ValidationReview.svelte` (vault selector, `cve-toolbar`, `cve-banner` severity headline, `cve-status-strip` totals tiles, sortable invalid-notes `cve-table` with `Open in Notes` deep-links, and a `cve-details--inspector` Developer deep-link to `/app/raw?endpoint=validation&vault=...`).
- `/app/tasks` mounts `TaskReview.svelte` (deterministic priority/type/path sort, type filter, status tiles for Total / High / Medium / Low, feedback weighting badges, Open-in-Notes deep-links, and Developer deep-link to `/app/raw?endpoint=tasks&vault=...`).
- `/app/raw` mounts `RawDeveloperExplorer.svelte`: a read-only diagnostic surface listing 13 safe GET helpers (health, vaults, summary, validation, tasks, missing, feedback, notes, graph, graph/missing, context/profiles, trust, stale). Run / Copy / Download (Blob URL) affordances, bounded JSON viewer with internal scroll, `?vault`/`?endpoint`/`?source`/`?focus` deep-link contract tolerated, and a visible warning banner documenting that destructive routes are intentionally excluded.
- New Phase 30D1 primitives in `ui/src/styles/global.css`: `.cve-p30d1-table`, `.cve-p30d1-filters`, `.cve-p30d1-raw-controls`, `.cve-p30d1-provenance`, `.cve-p30d1-raw-actions`, `.cve-p30d1-raw-viewer`, `.cve-p30d1-raw-pre` (bounded `max-height` / internal scroll). All token-only; no Tailwind dark literals.

**Out of scope:** Notes / Graph (Phase 30D2), Import / Bundles / Exports / Security (Phase 30D3), Review and Governance polish (Phase 30E), final QA / a11y / responsive / light-mode pass (Phase 30F).

**Suggested Commit**

```
feat(ui): real validation, tasks, and raw developer pages (Phase 30D1)
```

#### Phase 30D2 - Notes and Graph Workspace Redesigns

**Status:** Complete (2026-05-13).

**Scope:**
- `/app/notes` rebuilt as a `cve-workbench` split-pane workspace. Header is a `cve-toolbar` with vault selector and Refresh; status messages surface in a `cve-banner`. The rail hosts filters (text, status, difficulty, missing sections, imported-only, draft-trust-only), the POST /query search disclosure, and a deterministic note list inside a `cve-scroll-region`. The inspector shows note frontmatter, section outline, full markdown body, validation context, improvement task, and the Trust+Import panel inside its own `cve-scroll-region`. All filters, badges (`data-testid="badge-imported"`, `data-testid="badge-draft"`), the trust-import panel (`data-testid="trust-import-panel"`), and `?vault=` / `?filter=` / `?path=` deep-links are preserved.
- `/app/graph` rebuilt as a `cve-workbench` split-pane workspace. The legacy `'graph' | 'inspector' | 'missing'` tab model is removed. The rail hosts node-type and edge-type filters, a node search input, and a grouped deterministic node list inside a `cve-scroll-region`. The inspector either surfaces the ranked missing concepts overview (default view when no node is selected) or, when a node is selected, the node header followed by Neighbours, Related notes, and Missing concepts near this node, all inline (no sub-tabs). The non-destructive copyable Action Card for missing concepts is preserved as a secondary disclosure under the ranked overview.
- Inline raw JSON disclosure panels for `/notes`, `/note`, `/query`, `/graph`, `/graph/neighbors`, `/graph/related`, `/graph/missing`, and `/missing` are removed from the primary inspector. Both pages expose a `cve-details--inspector` block with a `cve-details__developer-link` pointing to `/app/raw?endpoint=...&vault=...&source=notes|graph` for full diagnostic JSON.
- New Phase 30D2 primitives in `ui/src/styles/global.css`: `.cve-p30d2-rail`, `.cve-p30d2-rail__head`, `.cve-p30d2-rail__list-head`, `.cve-p30d2-section-title`, `.cve-p30d2-section-row`, `.cve-p30d2-filter-row`, `.cve-p30d2-checkbox-row`, `.cve-p30d2-checkbox`, `.cve-p30d2-fieldset`, `.cve-p30d2-search-disclosure`, `.cve-p30d2-search-actions`, `.cve-p30d2-list`, `.cve-p30d2-note-list` / `.cve-p30d2-node-list`, `.cve-p30d2-note-row` / `.cve-p30d2-node-row`, `.cve-p30d2-node-group`, `.cve-p30d2-inspector`, `.cve-p30d2-inspector__head` / `__actions` / `__body`, `.cve-p30d2-empty-pane`, `.cve-p30d2-status-strip`, `.cve-p30d2-table`, `.cve-p30d2-kv`, `.cve-p30d2-outline`, `.cve-p30d2-badge-list`, `.cve-p30d2-body` / `-body-edit`, `.cve-p30d2-edit-grid` / `-edit-row` / `-edit-complex`, `.cve-p30d2-error-list`, `.cve-p30d2-task` / `__head`, `.cve-p30d2-related-controls`, `.cve-p30d2-strength-select`, `.cve-p30d2-action-card` / `-action-text`, `.cve-p30d2-link-btn`. All token-only; no Tailwind dark literals.
- 24 new deterministic tests (`test_p30d2_1` through `test_p30d2_24`) cover layout mode, primitive usage, internal scroll regions, imported/draft contract preservation, raw JSON removal, Developer deep-link, removal of the tab model, inline missing concepts, helper usage, dark-literal absence, form labelling, static link resolution, deferred phase guardrails, dependency stability, and em-dash hygiene. Total deterministic test count: 866.

**Out of scope:** Import / Bundles / Exports / Security (Phase 30D3), Review and Governance polish (Phase 30E), final QA / a11y / responsive / light-mode pass (Phase 30F).

**Suggested Commit**

```
feat(ui): notes and graph workspace redesigns (Phase 30D2)
```

#### Phase 30D3 - Import, Bundles, Exports, and Security Workflow Redesigns

**Status:** Complete (2026-05-22).

**Scope:**
- `/app/import` rebuilt as a sectioned workflow page on `AppLayout layoutMode="wide"`. Header uses `cve-toolbar` with a state pill (`data-testid="import-state-pill"`). Source-type select keeps markdown and obsidian sources only and preserves all Phase 26 testids (source-type-select, source-type-help, summary-wikilinks, summary-embeds, summary-attachments, empty-items-message, collision-banner, frontmatter-banner, item-errors, obsidian-metadata). Preview and Write are separate buttons; Write is disabled before a successful preview, behind a confirmation checkbox (`import-confirm-checkbox`), and is re-disabled when form input changes (`import-stale-banner`). Post-write summary renders the existing `ImportedReviewSummary` component and surfaces follow-up links to `/app/notes`, `/app/validation`, `/app/tasks`, `/app/trust`, `/app/security`.
- `/app/bundles` rebuilt as a two-column workflow: left rail collects Scope, Filters, Sections, and Budget inside `cve-p30d3-section` cards; right pane shows Readiness stages until the user generates a preview, then a `cve-status-strip` summary (mode, vault, notes included, budget used). A sticky `cve-p30d3-sticky-action` keeps the Generate Preview button visible. State pill (`bundle-state-pill`) reflects idle/loading/ok/error. Raw bundle JSON is demoted into a `cve-details--inspector` with a Developer deep-link to `/app/raw?endpoint=bundle&vault=...&source=bundles`.
- `/app/exports` reuses the same shape via the shared `ui/src/lib/bundleConfig.ts` helper. Security gate (`export-require-security-checkbox`) defaults to ON. Overwrite (`export-overwrite-checkbox`) reveals a typed-confirmation block (`export-overwrite-confirm-block`) and the submit button (`export-submit-btn`) only enables once the input matches `OVERWRITE`. Files manifest renders in a bounded `cve-table` with sha256, bytes, and dest columns. Raw export JSON is confined to `cve-details--inspector` with a deep-link to `/app/raw?endpoint=export&vault=...&source=exports`.
- `/app/security` rebuilt with a full-vault default scope. The cve-toolbar header shows a state pill (`security-state-pill`). A `cve-status-strip` surfaces a pre-run note count (`security-prerun-tile`) via `fetchNotes(vault)` so users see what the deterministic scan will cover before they run it. Sampling, filters, sections, allow_partial, max_notes, and max_chars are demoted into an Advanced scope `<details class="cve-p30d3-disclosure">` (`security-advanced-summary`) that is closed by default. Findings render in a bounded `cve-table` inside `cve-p30d3-findings-table` with severity / rule / path / field / detail columns, severity segmented filter, and free-text filter (`security-finding-filter`). Raw response is confined to `cve-details--inspector` with a deep-link to `/app/raw?endpoint=security&vault=...&source=security`.
- New shared helper `ui/src/lib/bundleConfig.ts` exposes `defaultBundleConfig`, `clampMaxNotes`, `clampMaxChars`, `buildBundleFilters`, `buildContextBundleRequest`, `validateSections`, `resolveActiveProfile`, `applyProfileToConfig`, and `describeFilters` so Bundle and Export pages share a single form model.
- New Phase 30D3 primitives in `ui/src/styles/global.css` (all under `@layer components`, all token-only): `.cve-p30d3-workflow`, `.cve-p30d3-twocol`, `.cve-p30d3-section` (with `--danger` / `--warning` variants), `.cve-p30d3-field` / `.cve-p30d3-field-row` / `.cve-p30d3-field__help`, `.cve-p30d3-checkbox`, `.cve-p30d3-segmented`, `.cve-p30d3-chip-list` / `__chip` / `__chip__remove`, `.cve-p30d3-sticky-action`, `.cve-p30d3-action-row`, `.cve-p30d3-table-wrap`, `.cve-p30d3-item-list` / `.cve-p30d3-item` / `__path` / `__dest`, `.cve-p30d3-tag` (with `--planned` / `--written` / `--skipped` / `--blocked` / `--error` / `--fail` / `--warning` / `--pass` / `--success` / `--info` / `--neutral`), `.cve-p30d3-readiness`, `.cve-p30d3-stage-list`, `.cve-p30d3-stage--done` / `--pending`, `.cve-p30d3-summary-kv`, `.cve-p30d3-mono`, `.cve-p30d3-divider`, `.cve-p30d3-followup`, `.cve-p30d3-toolbar-pill` (`--stale` / `--ready`), `.cve-p30d3-confirm-block`, `.cve-p30d3-disclosure`, `.cve-p30d3-progress`, `.cve-p30d3-empty`, `.cve-p30d3-findings-table`, `.cve-p30d3-findings-detail`, `.cve-p30d3-btn-success`, `.cve-p30d3-btn-danger`. No Tailwind dark literals introduced.
- 24 new deterministic tests (`test_p30d3_1` through `test_p30d3_24`) cover layoutMode="wide" across all four pages, cve-toolbar/banner/status-strip usage in each component, ImportReview source-type preservation and preview/write separation, BundleBuilder shared helper + sticky action + state pane, ExportPackage shared helper + security gate default + typed OVERWRITE gate + separate route from bundles, SecurityScan full-vault default + Advanced disclosure + pre-run note count + bounded findings table, state-pill presence, no primary inline raw JSON, Developer deep-links, no Tailwind dark literals, form labelling, static link resolution, deferred phase guardrails, Phase 30D3 + parent 30D Complete with 30E/30F Planned, no em dashes, and no new runtime dependencies. Total deterministic test count: 890.

**Out of scope:** Review and Governance polish (Phase 30E), final QA / a11y / responsive / light-mode pass (Phase 30F).

**Suggested Commit**

```
feat(ui): import, bundles, exports, and security workflow redesigns (Phase 30D3)
```

#### Phase 30E - Review, Governance, and Developer Polish

**Status:** Complete (2026-05-13). Both Phase 30E1 (Pending, Trust, Feedback) and Phase 30E2 (Controller, Vault Setup) are delivered.

##### Phase 30E1 - Pending / Trust / Feedback governance polish

**Status:** Complete.

**Scope (delivered):**
- `/app/pending` rebuilt on the Phase 30B workbench primitives. Internal scroll on the queue rail and the inspector body. Typed-confirmation gates for both Accept (`ACCEPT`) and Reject (`REJECT`). Provenance, target, and a deterministic trust-impact panel surfaced inline. Diff rendered with the `cve-diff` primitive. Raw JSON moved to a `/app/raw` deep-link.
- `/app/trust` leads with the stale / low-trust governance queue table. Per-row links to Notes, Pending, and Feedback. Evidence Builder demoted into a secondary disclosure. Trust disclaimer retained as `cve-trust-warning`. Status strip summarises stale, low-trust, draft, deprecated, and missing-metadata counts.
- `/app/feedback` rebuilt as a triage workbench. Full-width filterable table with deterministic severity-first sort. Pinned tasks side-panel. Add Feedback gated behind a `cve-slide-over` opened from the toolbar. Edit and delete retained inline on each row.
- Shared helper `ui/src/lib/phase30e1.ts` exposes the typed-confirmation phrases, severity weights, resolved-signal predicate, and the `/app/raw` deep-link builder.
- No new runtime dependencies, no backend or schema changes, no new MCP tools.

**Suggested Commit**

```
feat(ui): pending, trust, and feedback governance polish (Phase 30E1)
```

##### Phase 30E2 - Controller and Vault Setup polish

**Status:** Complete (2026-05-13).

**Scope (delivered):**
- `/app/controller` rebuilt as a two-column command-centre at xl+ (`controller-state-column` left, `controller-recommendation-column` right). Toolbar, state pill, headline banner, and status strip render on the Phase 30B primitives. Readiness polarity is corrected via `readinessPolarity()` so negative flags (`has_tasks`, `has_missing_concepts`, `has_feedback_warnings`) no longer render as positive. Recommendations are sorted deterministically and deep-link to authoritative `/app/*` routes through `recommendationRoute()`. Raw controller/plan responses are demoted to a `cve-details--inspector` disclosure with Developer deep-links into `/app/raw` via `buildRawDeepLink()`.
- `/app/vault-setup` collapsed scattered per-field cards into one grouped `cve-p30e2-form-grid` panel. Live validation and the bootstrap preview are preserved. Destructive vault deletion is fully removed from the primary setup form and relocated into a dedicated vault management panel; the actual delete flow runs inside a `cve-slide-over` (`vault-setup-delete-slide-over`) that names the target vault, explains the real backend semantics (files deleted from disk, `config/config.yaml` rewritten, action not reversible by the app), and requires a typed `DELETE <vault>` confirmation enforced by `isDeleteConfirmed()`. `demo-vault` is protected via `VAULT_DELETE_PROTECTED`.
- Shared helper `ui/src/lib/phase30e2.ts` exposes readiness polarity, recommendation routing, the typed-confirmation phrase, and the deletion-semantics constant; `buildRawDeepLink` is re-exported from `phase30e1`.
- New token primitives `cve-p30e2-*` added to `global.css` inside `@layer components`. No Tailwind dark literals, no new runtime dependencies, no backend or schema changes, no new MCP tools.

**Suggested Commit**

```
feat(ui): controller and vault setup polish (Phase 30E2)
```

#### Phase 30F - Final QA, Accessibility, Responsive, Light Mode, and Guardrail Tests

**Status:** Complete (2026-05-13). Phase 30F is complete; parent Phase 30 (UI Release Quality Pass) is complete. Phase 27 and Phase 28 remain explicitly deferred.

**Honesty note:** Phase 30F automated only source-level, deterministic guardrails in `mcp/test_verify.py`. Browser visual verification, screen-reader traversal, and live keyboard navigation are manual checks recorded in `RELEASE_CHECKLIST.md`. This roadmap does not claim those manual checks were automated.

**Scope (delivered):**
- User-facing light/dark theme toggle wired into `AppLayout.astro` for both desktop and mobile top bars. An inline (non-hydrated) bootstrap script applies `data-theme` on `documentElement` before paint, defaulting to `dark` when no preference is saved. Preference persists under the `cve-theme` localStorage key. The toggle declares `aria-label`, `aria-pressed`, and a visible text label that stay in sync with the active theme.
- Token sweep: every `--cve-*` token defined under `html[data-theme="dark"]` is also defined under `html[data-theme="light"]`. Tokenised AppLayout chrome via `cve-app-chrome-bg`, `cve-app-chrome-border`, `cve-app-chrome-text-strong`, `cve-app-chrome-text-muted`, and `cve-app-chrome-text-faint` classes. Raw block now uses `var(--cve-raw-bg)` instead of a hard-coded hex.
- Source-level accessibility guardrails: form controls across migrated components have label coverage (`cve-label`, `<label>`, or `aria-label`); icon-only buttons declare accessible names; status badges convey state with text, not colour alone; slide-overs declare `role="dialog"`, `aria-modal="true"`, an accessible name, and a Close control.
- Responsive guardrails: `cve-raw` and `cve-diff` are bounded with internal vertical scroll; tables retain horizontal scroll inside `cve-table-wrap` (or the Phase 30D3 `cve-p30d3-table-wrap` variant); the workbench shell collapses to a single column at viewports under 900px; slide-overs collapse to full width under 640px.
- Write-safety reaffirmed: ExportPackage requires typed `OVERWRITE`; ImportReview preserves the preview/write separation; VaultSetup keeps destructive delete behind a slide-over with typed `DELETE <vault>` confirmation and `demo-vault` protection; PendingChanges keeps typed Accept/Reject; FeedbackWorkflow Add Feedback routes through a slide-over.
- Route integrity: every static `/app/*` link in migrated UI resolves to an existing Astro route. No stale `/app/api` or invented `/app/registry`, `/app/semantic`, `/app/search`, `/app/settings`, or admin routes appear in migrated UI.
- Deterministic guardrail tests P30F-1 through P30F-48 added in `mcp/test_verify.py`.
- No new runtime dependencies, no backend or schema changes, no new MCP tools, no em dashes in modified files.

**Out of scope (explicitly):** Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval); any new feature; any backend route; LLM-driven UI behaviour; charting, animation, or icon libraries.

**Original planned scope (now delivered):**

**Scope:**
- Light-mode toggle wired in once tokens cover every primitive across every migrated page.
- Verified breakpoints: ultrawide (3440+ px), 1440p, 1080p, 1366x768, narrow (mobile / tablet).
- Keyboard navigation pass: every interactive control reachable; `:focus-visible` visible in both themes; no keyboard trap.
- Screen-reader pass: landmarks present, form labels associated, status badges paired with text, dangerous actions announce as such.
- Deterministic guardrail tests added in `mcp/test_verify.py`:
  - No raw Tailwind dark palette literal (`bg-zinc-*`, `text-zinc-*`, etc.) remains on migrated pages.
  - Both `data-theme="dark"` and `data-theme="light"` define every semantic token.
  - Workflow pages declare a layout mode that is not `standard` where the audit requires `wide` / `workspace`.
  - `/app/validation`, `/app/tasks`, and `/app/raw` no longer render `PlaceholderPage.astro`.
  - Destructive actions on Import, Exports, Security, Pending, and Vault Setup are visually separated and gated (banner, slide-over, typed confirmation, distinct button variant).
  - Deep-link contracts (raw inspection -> `/app/raw`, recommendations -> authoritative pages) resolve to real routes.
- README, RELEASE_CHECKLIST, and TESTING updated to mark Phase 30 complete.

**Suggested Commit**

```
feat(ui): final UI release-quality QA, accessibility, and light-mode toggle (Phase 30F)
```

#### Phase 30 Strategic Note

Phase 30 does not supersede or start Phase 27 (Registry and Reuse Layer) or Phase 28 (Optional Semantic Retrieval). Both remain explicitly deferred and are not started, prepared, or implied by any Phase 30 sub-phase. No semantic retrieval, registry, LLM, RAG, SaaS, cloud, React, charting, or third-party UI library work is introduced.

---

### Phase 31A - Release Candidate Verification

**Status:** Active (post-Phase-30 release-candidate preparation). Phase 30 is complete. Phase 31A is release-candidate verification only. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain Deferred and are not started by Phase 31A.

**Purpose**

Phase 30 closed the UI Release Quality Pass at the source level. The Phase 30F closure report explicitly states that browser visual QA and screen-reader QA remain manual checks before any release announcement. Phase 31A prepares the project for a clean release candidate by capturing the manual QA matrix and verification command order in `RELEASE_CHECKLIST.md` without starting any new feature work.

**Scope**

- Document the automated verification command order in `RELEASE_CHECKLIST.md`.
- Document the manual browser visual QA matrix (15 `/app/*` routes across 5 viewport tiers, per-route layout, theme, scroll, table, slide-over, destructive-action, and theme-persistence checks) in `RELEASE_CHECKLIST.md`.
- Document the manual keyboard QA checklist in `RELEASE_CHECKLIST.md`.
- Document the manual screen-reader QA checklist in `RELEASE_CHECKLIST.md`, clearly marked manual unless actually performed.
- Document release artefact hygiene rules (`dist/`, `ui/dist/`, runtime-generated artefacts, screenshots, local reports, temporary files) in `RELEASE_CHECKLIST.md`.
- Add a concise Release Candidate Verification section to `TESTING.md` that distinguishes automated source-level checks from manual browser/screen-reader QA.
- Add deterministic guardrail tests that verify the checklist exists and that Phase 27 and Phase 28 remain Deferred.

**Out of scope**

- No backend route changes, API contract changes, schema changes, or MCP changes.
- No new dependencies, no React, Vue, charting, animation, or icon library.
- No UI redesign, no new feature work, no new write actions, no route removal, no page consolidation.
- No registry layer, no semantic retrieval, no LLM/RAG/cloud/SaaS work.
- Phase 27 and Phase 28 are not started, prepared, or implied.
- No release tag, no GitHub release.
- No claim that browser visual QA or screen-reader QA has passed unless actually performed.

**Honesty note**

Phase 31A automates only the existence of the manual checklist and the deferred status of Phase 27 and Phase 28. The browser visual QA, keyboard QA, and screen-reader QA passes themselves remain manual. Ticking those rows in `RELEASE_CHECKLIST.md` requires a human carrying out the check; nothing in Phase 31A or Phase 30F performs those passes automatically.

**Suggested Commit**

```
docs(release): add Phase 31A release-candidate verification checklist
```

---

### Phase 27 - Registry and Reuse Layer

**Status: Deferred.**

#### Purpose

Manage generated context packages over time.

#### Possible Features

- package registry
- package list UI
- package verification
- package tags
- stale package detection
- archive/delete package
- compare manifests
- optional signing

#### Do Not Start Until

- exports are used frequently
- package browser exists
- multiple bundles need management

#### Suggested Commit

```
feat(registry): add local context package registry
```

---

### Phase 28 - Optional Semantic Retrieval

**Status: Deferred.**

#### Purpose

Add embeddings only when deterministic lexical search becomes insufficient.

#### Do Not Start Until

- at least 75+ real notes exist
- lexical search has clear failure cases
- embedding model choice is justified
- cache invalidation design is clear
- tests can avoid brittle ranking assertions
- security scanner handles retrieval input surfaces

#### Possible Features

- local embedding index
- hybrid lexical + semantic search
- semantic bundle selection
- explainable ranking metadata
- embedding cache invalidation
- model/version hash in bundle metadata

#### Suggested Commit

```
feat(search): add optional semantic retrieval
```

---

## Priority Order

Recommended sequence:

16. Visual Graph and Missing Concepts UI
17. Distribution and Local App Launcher
18. CI and Release Hardening
19. Context Controller Layer
20. MCP Compatibility Layer
21. Private Cloud Mode
22. Session and Project State Layer
23. Safe Memory Write Queue
24. Device Profiles and Context Budgets
25. Trust, Staleness, and Evidence Metadata
26. Import Pipelines
29. UI/UX Quality and Design System (complete)
30. UI Release Quality Pass (30A complete; 30B to 30F planned; does not start Phase 27 or Phase 28)
27. Registry and Reuse Layer
28. Optional Semantic Retrieval

## Strategic Interpretation

The project should now be understood in three layers:

1. **Vault Application** - Human-facing local UI for creating, validating, editing, improving, and packaging vaults.
2. **Context Service** - API/controller layer that assembles bounded, validated, security-scanned context.
3. **Local AI Context Backend** - MCP-compatible private service that lets weak local LLMs retrieve durable project memory.

The strongest future positioning is:

> Context Vault Engine gives local LLMs structured, validated, persistent project memory without handing your knowledge base to a cloud model.

## Memory Replacement Note

This roadmap supersedes the previous master roadmap.

### Crucial context preserved

- Context Vault Engine identity
- local-first principle
- deterministic-first principle
- Markdown source-of-truth principle
- schema-as-contract principle
- bundles as generated artefacts
- validation before packaging
- security scanning before external delivery
- feedback influences priority but does not mutate notes
- safe note editing through validation
- semantic retrieval remains deferred
- registry remains future work
- forensic reports are historical snapshots, not permanent truth

### New direction added

- Context Controller Layer
- MCP Compatibility Layer
- Private Cloud Mode
- Session and Project State Layer
- Safe Memory Write Queue
- Device Profiles and Context Budgets
- Trust/Staleness/Evidence metadata
- Import pipelines

This keeps the current roadmap context while extending the project toward the private local-LLM context backend use case.