# Context Vault Engine - Updated Master Roadmap

## Executive Direction

Context Vault Engine is moving from a usable local vault application into a private context operating layer for humans, local LLMs, and agent clients.

The current foundation is strong: deterministic Markdown validation, schema enforcement, analysis, improvement tasks, feedback, lexical search, context bundles, export packages, security scanning, FastAPI routes, and a local UI are already implemented. The current roadmap places the active work around Phase 17 - Distribution and Local App Launcher.

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

**Phase 21 - Private Cloud Mode**

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
| 22    | Session and Project State Layer         | Planned  |
| 23    | Safe Memory Write Queue                 | Planned  |
| 24    | Device Profiles and Context Budgets     | Planned  |
| 25    | Trust, Staleness, and Evidence Metadata | Planned  |
| 26    | Import Pipelines                        | Planned  |
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

### Phase 16 - Visual Graph and Missing Concepts UI — Complete

**Status:** Complete (Phase 16 — 2026-05-11)

**UI build:** PASS (GraphExplorer.svelte 31.75 kB / 9.00 kB gzip)
**Backend tests:** 242 (all pass, no changes to backend)

**Delivered:**
- `ui/src/components/GraphExplorer.svelte` — vault selector, graph summary metrics, node type/edge type filters, grouped searchable node browser, node inspector (neighbours + related notes + missing neighbours), missing concepts tab with ranked table and non-destructive action card generator.
- `ui/src/pages/graph.astro` — new Astro page at `/app/graph`.
- `ui/src/lib/api.ts` — `fetchGraph`, `fetchGraphNeighbors`, `fetchGraphRelated`, `fetchGraphMissing` helper functions and all associated types.
- `ui/src/layouts/AppLayout.astro` — **Graph** added to sidebar navigation.
- QUICKSTART.md, TESTING.md, ROADMAP.md updated.

**Safety:** No backend changes. Action card is non-destructive (no file writes, no API writes). Raw JSON panels collapsed by default. UI clearly labels all relationships as schema-derived and deterministic.

#### Suggested Commit

```
feat(ui): add graph and missing concept visualisation
```
---

### Phase 17A - HTML Bundle Renderer

**Status:** Complete (Phase 17A — 2026-05-11)

**Backend tests:** 254 (12 new Phase 17A tests + 6 existing P4 tests updated; all pass)
**UI build:** PASS (no frontend changes)

**Delivered:**
- `core/shared/context_html.py` — NEW: `render_context_html()` and `_render_*` helpers. Python standard library only (`html`, `json`). All user content is HTML-escaped. No remote assets. Deterministic output.
- `core/shared/context_package.py` — imports `render_context_html`; generates `context.html` before manifest; adds `context.html` to `files_info` and `manifest["files"]`; writes `context.html` to package temp dir.
- `mcp/test_verify.py` — 12 new Phase 17A tests (security, determinism, content, manifest hash); 6 existing P4 export tests updated for 7-file expectation.
- `README.md`, `QUICKSTART.md`, `TESTING.md`, `API.md` — package file list and export docs updated.

**Safety:** All note body/section/frontmatter content is HTML-escaped via `html.escape`. No `<script>` tags, no `javascript:` URLs, no remote assets, no external stylesheets. CSS is inline in a `<style>` block. Output is deterministic for identical bundle input (no render timestamps, no random IDs).

#### Suggested Commit

```
feat(export): add deterministic HTML bundle renderer
```

---

### Phase 17 - Distribution and Local App Launcher

**Status:** Complete (Phase 17 — 2026-05-11)

**Backend tests:** 264 (10 new Phase 17 launcher tests; all pass)
**UI build:** PASS (no frontend changes)

**Delivered:**
- `core/app_launcher.py` — NEW: `check_ui_built()`, `probe_server()`, `is_context_vault_health_response()`, `wait_for_server()`, `open_browser()`, `launch_server()`, `main()`. Standard library only (`subprocess`, `urllib.request`, `webbrowser`, `json`, `time`, `pathlib`).
- `run.py` — `app` command added to `USAGE` string; dispatches to `core.app_launcher.main(repo_root)`.
- `mcp/test_verify.py` — 10 new Phase 17 tests (constants, health validator, connection refused, UI build detection, command dispatch).
- `README.md`, `QUICKSTART.md`, `TESTING.md` — local app launcher documented.

**Behaviour:**
- `py run.py app` starts the FastAPI server if not already running, waits for `/health`, opens `http://127.0.0.1:8000/app` in the browser, stays attached to terminal.
- If a compatible server is already running (detected via `/health` response shape), reuses it and opens the browser — no duplicate server started.
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

### Phase 18B-U - Schema Builder UX Hardening — **Complete**

#### Purpose

Close the usability gap where users had to manually edit `vault_schema.py` to add expected concepts after bootstrap. Bootstrap now writes expected concepts directly into the generated schema so that Missing Concepts works immediately after vault creation.

#### Delivered

- `generate_schema_content()` accepts `expected_concepts` list; renders it as `EXPECTED_CONCEPTS` using `repr()` (injection-safe, deterministic).
- `bootstrap_vault_noninteractive()` passes cleaned concepts to schema generator; removed stale warning; returns `expected_concepts: {requested, written}` count in result.
- `POST /vault/bootstrap` API response includes `expected_concepts` counts.
- `VaultSetup.svelte` — removed "Backend limitation" amber warning; updated helper text; success panel shows concept count.
- `api.ts` — `VaultBootstrapResponse` includes optional `expected_concepts` field.
- 10 new P18BU tests covering generation, deduplication, injection safety, importability, API response, and `GET /missing`.
- Docs updated: QUICKSTART.md, API.md, TESTING.md, ROADMAP.md.

#### Suggested Commit

```
feat(bootstrap): write expected concepts into generated schemas
```

---

### Phase 18C - Vault Lifecycle Management — **Complete**

#### Purpose

Allow users to safely delete non-demo vaults through the API and UI without manually editing `config.yaml`. Deletion is destructive and requires explicit typed confirmation.

#### Delivered

- `mcp/core/vault_delete.py` (NEW) — service layer with `validate_delete_request()`, `assert_safe_vault_path()`, `update_config_after_delete()`, and `delete_vault()`.
- `mcp/core/note_index.py` — `clear_vault_index(vault_name)` evicts a vault's in-process note index.
- `mcp/core/result_cache.py` — `clear_vault_cache(vault_name)` clears all cached results for a vault.
- `DELETE /vault/{vault_name}` endpoint — requires exact `"DELETE {vault_name}"` confirmation; protects `demo-vault` and the last remaining vault; updates config atomically; clears registry, index, and cache.
- `ui/src/lib/api.ts` — `deleteVault()`, `VaultDeleteRequest`, `VaultDeleteResponse`.
- `ui/src/components/VaultSetup.svelte` — Danger Zone section with vault selector, confirmation phrase input, and delete button; post-delete localStorage fallback.
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

### Phase 19 - Context Controller Layer — **Complete**

#### Purpose

Add the orchestration layer between local LLM/tool clients and raw API routes.

A weak local LLM should not decide low-level retrieval strategy. It should ask for context, and the controller should choose the plan.

#### Delivered

- `mcp/core/context_controller.py` — deterministic controller service; exports `get_context_state(vault_name)` and `build_context_plan(vault_name, intent)`.
- `GET /context/state` — returns a full snapshot: per-service summaries, 7 boolean readiness flags, blockers, and warnings.
- `POST /context/plan` — accepts one of five intents (`review`, `export`, `agent-context`, `quality`, `security`) and returns a ranked recommendation list with `next_best_action`.
- UI page at `/app/controller` backed by `ContextController.svelte` — vault/intent selectors, readiness grid, service summary table, recommendation list.
- "Controller" nav item added to `AppLayout.astro`.
- 19 Phase 19 test cases added to `mcp/test_verify.py`.
- `API.md` updated with full endpoint documentation.

#### Acceptance Criteria — Met

- Controller is deterministic: same vault + intent always returns the same output.
- Controller is read-only: no vault files are mutated.
- No LLM is invoked; all output is derived from current vault state.
- Security scan status is reflected in readiness flags.

#### Commit

```
feat(context): add context controller layer (Phase 19)
```

---

### Phase 20 - MCP Compatibility Layer — **Complete**

#### Purpose

Allow local LLM apps and agent clients to use Context Vault Engine as a read-only MCP tool server.

#### Delivered

MCP stdio server (`py run.py mcp`) using JSON-RPC 2.0 over stdin/stdout:

**Tools (10):** `cve.list_vaults`, `cve.get_context_state`, `cve.get_context_plan`, `cve.query_notes`, `cve.get_note`, `cve.validate_vault`, `cve.get_tasks`, `cve.get_missing_concepts`, `cve.security_scan`, `cve.build_context_bundle`

**Resources (9 URI patterns):** `cve://vaults`, vault summary, state, plan, notes, tasks, missing, security, graph

**Prompts (4):** `cve.vault_review`, `cve.security_review`, `cve.context_handoff`, `cve.quality_plan`

#### Files Created

- `mcp/core/mcp_protocol.py` — JSON-RPC 2.0 protocol handler
- `mcp/core/mcp_tools.py` — tool catalogue and dispatch
- `mcp/core/mcp_resources.py` — resource catalogue and read
- `mcp/core/mcp_prompts.py` — prompt definitions with safety footer
- `mcp/server/mcp_stdio_server.py` — main stdio server loop

#### Files Modified

- `run.py` — added `mcp` command
- `mcp/test_verify.py` — 41 Phase 20 tests
- `README.md`, `QUICKSTART.md`, `API.md`, `TESTING.md`, `ROADMAP.md` — updated docs

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

#### Purpose

Give weak local LLMs durable continuity without relying on chat history.

#### Deliver

Session records:

- `active_vault`
- `current_project`
- `current_topic`
- `recent_notes`
- `recent_bundle_ids`
- `open_tasks`
- `user_goal`
- `last_activity`

Project state files:

- `current_phase`
- `completed_work`
- `next_actions`
- `blockers`
- `decisions`
- `risks`

Tools/API:

- `start_session`
- `resume_session`
- `summarise_session`
- `attach_note_to_session`
- `close_session`
- `get_project_state`
- `update_project_state`

#### Acceptance Criteria

- User can ask "where was I up to?"
- Local LLM can resume with explicit state.
- Project state is stored outside model memory.
- State files remain human-readable and versionable.

#### Suggested Commit

```
feat(state): add sessions and project state
```

---

### Phase 23 - Safe Memory Write Queue

#### Purpose

Allow local LLMs to propose context changes without directly mutating the vault.

#### Deliver

Pending change objects:

- `create_note_draft`
- `suggest_note_update`
- `update_note_section_draft`
- `review_pending_change`
- `accept_pending_change`
- `reject_pending_change`

Each pending change should include:

- `type`
- `path`
- `section`
- `proposed_content`
- `reason`
- `source`
- `created_at`
- `validation_status`
- `diff`

#### Rules

- LLMs do not directly rewrite notes by default.
- Proposed changes are validated before acceptance.
- UI shows diff before write.
- Accepted changes use existing safe note edit path.
- Rejected changes are retained or archived for audit.

#### Acceptance Criteria

- Agent/client can propose changes.
- User can accept/reject/edit from UI.
- Accepted changes validate before disk write.
- Full diff is visible.

#### Suggested Commit

```
feat(memory): add pending change review queue
```

---

### Phase 24 - Device Profiles and Context Budgets

#### Purpose

Make context output usable by different clients, especially small local LLMs on phones.

#### Deliver

Device/context profiles:

```yaml
profiles:
  s25-local-llm:
    max_chars: 8000
    include_body: false
    include_sections:
      - Key Principles
      - How It Works
    require_security_scan: true
    prefer_complete: true

  desktop-agent:
    max_chars: 30000
    include_body: true
    include_related: true
    require_security_scan: true
```

Bundle modes:

- `tiny`
- `small`
- `medium`
- `large`
- `agent`

#### Acceptance Criteria

- User can select a profile.
- Local LLM receives bounded context.
- Bundle builder supports profiles.
- MCP tools can request context by profile.

#### Suggested Commit

```
feat(context): add device profiles and context budgets
```

---

### Phase 25 - Trust, Staleness, and Evidence Metadata

#### Purpose

Help local LLMs prefer better sources and avoid stale/generated/low-confidence notes.

#### Deliver

Optional frontmatter fields:

```yaml
trust_level: verified | working | draft | external | deprecated
source_type: authored | imported | generated | agent_suggested
last_reviewed: 2026-05-07
review_after: 2026-08-01
```

Endpoints/UI:

- `/stale`
- `/trust`
- `/evidence`

Evidence mode should return source paths, sections, and confidence metadata.

#### Acceptance Criteria

- Retrieval can prefer verified notes.
- Stale notes are visible.
- Deprecated notes are deprioritised.
- Answers can cite source note paths.

#### Suggested Commit

```
feat(metadata): add trust and staleness controls
```

---

### Phase 26 - Import Pipelines

#### Purpose

Make it easier to ingest existing knowledge without bypassing schema controls.

#### Import Sources

- Markdown folder
- Obsidian vault
- GitHub repo docs
- Copilot/agent reports
- chat transcript
- browser article
- PDF-to-Markdown, later

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

- User can import Markdown safely.
- Imported files are schema-mapped.
- Invalid imports produce actionable tasks.
- No unsafe path writes.

#### Suggested Commit

```
feat(import): add markdown import pipeline
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
27. Registry and Reuse Layer
28. Optional Semantic Retrieval

## Strategic Interpretation

The project should now be understood in three layers:

1. **Vault Application** — Human-facing local UI for creating, validating, editing, improving, and packaging vaults.
2. **Context Service** — API/controller layer that assembles bounded, validated, security-scanned context.
3. **Local AI Context Backend** — MCP-compatible private service that lets weak local LLMs retrieve durable project memory.

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