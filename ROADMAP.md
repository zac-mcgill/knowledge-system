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

Phase 29A (Roadmap formalisation and UI/UX audit). Phases 0 to 26 are complete. Phase 29 (UI/UX Quality and Design System) is now active. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain deferred and are not started by Phase 29.

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
| 29    | UI/UX Quality and Design System         | Active   |
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

**Status: Active (Phase 29A in progress).**

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

**Suggested Commit**

```
feat(ui): grouped sidebar and information architecture (Phase 29B)
```

##### Phase 29C - Global design system and shared UI primitives

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

**Suggested Commit**

```
feat(ui): introduce design tokens and shared primitives (Phase 29C)
```

##### Phase 29D - Page-level UX consistency pass

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

**Suggested Commit**

```
feat(ui): page-level UX consistency pass (Phase 29D)
```

##### Phase 29E - Final polish, docs, and release readiness

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

**Suggested Commit**

```
feat(ui): final UI/UX polish, accessibility, and docs (Phase 29E)
```

#### Phase 29 Strategic Note

Phase 29 does not supersede or start Phase 27 (Registry and Reuse Layer) or Phase 28 (Optional Semantic Retrieval). Both remain explicitly deferred. Phase 29 only addresses the UI/UX quality gap in the already-shipped local web application.

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
29. UI/UX Quality and Design System (active, does not start Phase 27 or Phase 28)
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