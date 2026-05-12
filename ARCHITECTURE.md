# Context Vault Engine - Architecture

## Overview

Context Vault Engine is a local-first, deterministic-first system for managing the lifecycle of structured Markdown knowledge. It validates vault content against explicit schemas, analyses quality and gaps, generates improvement tasks, assembles context bundles, exports portable packages, scans for security issues, and feeds usage feedback back into the vault improvement cycle.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Human-Authored Markdown Vault                 │
│  (e.g. demo-vault/)                                             │
│  Notes with YAML frontmatter  +  Vault Files/feedback.md        │
└────────────────────────────┬────────────────────────────────────┘
                             │ schema contract
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     vault_schema.py                              │
│  (lives inside the vault at Vault Files/Scripts/vault_schema.py)│
│  Defines: required fields, enums, section maps, derivation rules│
│           EXPECTED_CONCEPTS (optional), ALL_KNOWN_FIELDS        │
└────────────────────────────┬────────────────────────────────────┘
                             │ loaded at startup
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Runtime Index / Cache (mcp/core/)                   │
│  note_index.py - parses notes, builds per-vault index           │
│  vault_registry.py - maps vault names → paths + schemas         │
│  query_engine.py - filtered queries, pagination, aggregation     │
│  graph_builder.py - deterministic relationship graph             │
│  graph_query.py - graph traversal (neighbors, related, missing) │
│  result_cache.py - in-memory cache with invalidation            │
│  schema_loader.py - loads vault_schema.py dynamically           │
└──────────┬──────────────────────────┬───────────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────────┐   ┌──────────────────────────────────────┐
│   core/shared/       │   │   mcp/core/adapters/                 │
│   Engine Modules     │   │   Adapter Layer                      │
│                      │   │                                      │
│  validate_vault.py   │   │  validation_adapter.py               │
│  analyse_vault.py    │   │  tasks_adapter.py                    │
│  upgrade_vault.py    │   │  notes_adapter.py                    │
│  generate_report.py  │   │  quality_adapter.py                  │
│  quality_audit.py    │   │  missing_adapter.py                  │
│  discover_missing.py │   │  compare_adapter.py                  │
│  inject_frontmatter.py   └──────────────────────────────────────┘
│  compare_reports.py  │
│  context_bundle.py   │   ┌──────────────────────────────────────┐
│  context_package.py  │   │   Generated Artefacts (dist/)        │
│  context_security.py │→──│                                      │
│  feedback.py         │   │  dist/context-bundles/<bundle-id>/   │
└──────────────────────┘   │    context.json                      │
           │               │    context.md                        │
           │               │    context.html                      │
           ▼               │    manifest.json                     │
┌──────────────────────┐   │    validation.json                   │
│   CLI Entry Point    │   │    graph.json                        │
│   run.py             │   │    feedback-summary.json             │
│                      │   └──────────────────────────────────────┘
│                      │
│  validate            │   ┌──────────────────────────────────────┐
│  analyse             │   │   FastAPI / MCP Server               │
│  improve             │   │   mcp/server/mcp_server.py           │
│  report              │   │                                      │
│  bundle              │   │  Read   /vaults /health /contract    │
│  export              │   │         /summary /validation /tasks  │
│  feedback            │   │         /notes /quality /missing     │
│  security            │   │         /gaps /feedback /note /stats │
│  profiles            │   │         /graph[/{vault}[/related]]   │
│  trust / stale       │   │         /private/status              │
│  templates           │   │         /context/profiles            │
│  init / bootstrap    │   │         /context/state               │
│  start-ui            │   │         /trust /stale                │
│  app                 │   │         /session/* /project/*        │
│  serve (MCP stdio)   │   │         /memory/pending              │
└──────────────────────┘   │         /app (web UI mount)          │
                           │  Write  /context/bundle              │
                           │         /context/export              │
                           │         /context/security            │
                           │         /context/plan                │
                           │         /query /compare /evidence    │
                           │         /vault/bootstrap             │
                           │         /vault/{name} (DELETE)       │
                           │         /note (POST/PUT)             │
                           │         /feedback (POST/PUT/DELETE)  │
                           │         /memory/create-note-draft    │
                           │         /memory/suggest-note-update  │
                           │         /memory/update-section-draft │
                           │  See API.md for the full route list. │
                           └──────────────────────────────────────┘

                           ┌──────────────────────────────────────┐
                           │   MCP stdio Server                   │
                           │   mcp/server/mcp_stdio_server.py     │
                           │                                      │
                           │  Tools, resources, and prompts over  │
                           │  the Model Context Protocol stdio    │
                           │  transport. Same logic as HTTP.      │
                           └──────────────────────────────────────┘
```

---

## Layers

### 1. Markdown Vault

The vault is a directory of plain Markdown files with YAML frontmatter. It is the single source of truth for all knowledge content.

- Files are organised into subdirectories (e.g. `Fundamentals/`).
- Each note has a `---`-delimited YAML block at the top.
- `Vault Files/` contains system-generated files (reports, schema, templates, feedback) that are excluded from note validation.
- The schema (`vault_schema.py`) lives inside the vault at `Vault Files/Scripts/vault_schema.py`.

### 2. Schema Contract

`vault_schema.py` is the authoritative contract for the vault. It defines:

- Required fields and their allowed values (enums).
- Canonical section names (e.g. `Key Principles`, `How It Works`, `Trade-offs`).
- Field derivation rules (e.g. `domain` derived from directory name).
- `ALL_KNOWN_FIELDS` - the set of filterable field names.
- `EXPECTED_CONCEPTS` (optional) - concepts expected to exist in each subdomain.

**Schema changes are high-risk.** Any change to the schema interface must be treated as a breaking change to all downstream validation, analysis, and bundle generation.

### 3. Runtime Index / Cache

`mcp/core/note_index.py` parses all vault notes and maintains a per-vault in-memory index. The index is checked on the next API call that needs it, subject to a 2-second cooldown window to suppress rebuild spam. Once the cooldown has elapsed, both the schema hash and a notes fingerprint (sorted set of `path:mtime_ns:size` for every Markdown file) are recomputed. If either has changed (added, modified, or deleted notes, or schema edits), the index is rebuilt. CLI commands always build a fresh index.

### 4. Core Engine Modules (`core/shared/`)

These are deterministic engine and service modules. Read-only modules (e.g. `validate_vault.py`, `analyse_vault.py`, `quality_audit.py`, `discover_missing.py`, `feedback.py`) only inspect the vault. Write-capable modules (e.g. `context_package.py` writes packages to `dist/`, `generate_report.py` and `generate_templates.py` write under `Vault Files/`, `inject_frontmatter.py` and `upgrade_vault.py` can update notes when invoked) perform clearly scoped, auditable file writes. None call external services.

- `validate_vault.py` (read) validates notes against the schema.
- `analyse_vault.py` (read) runs structured analyses on vault metadata.
- `upgrade_vault.py` (read/write) scores improvement tasks; can rewrite frontmatter when explicitly invoked.
- `quality_audit.py` (read) audits section content quality.
- `discover_missing.py` (read) detects missing expected concepts.
- `context_bundle.py` (read) generates deterministic context bundles.
- `context_package.py` (write) exports bundles as portable packages under `dist/`.
- `context_security.py` (read) scans bundles for security issues.
- `feedback.py` (read) parses and validates vault feedback entries.

These modules do not depend on the API layer or the runtime index directly. They accept vault paths and schema references as parameters.

### 5. Adapter Layer (`mcp/core/adapters/`)

Thin wrappers that bridge the runtime index and core engine modules to the API. Each adapter translates between the internal data model and the HTTP response shape.

### 6. CLI Entry Point (`run.py`)

The CLI reads `config/config.yaml`, resolves the vault path and schema, and dispatches to the appropriate module. Current commands include: `validate`, `analyse`, `improve`, `report`, `bundle`, `export`, `feedback`, `security`, `templates`, `init`, `bootstrap`, `app` (local app launcher), `mcp` (MCP stdio server), `profiles` (list context profiles and modes), `trust` (trust summary), `stale` (stale notes list), `session` (current session summary), `project-state` (project state JSON), and `pending` (pending change proposals). Run `py run.py` with no arguments to see the live list.

### 7. FastAPI / MCP Server (`mcp/server/mcp_server.py`)

The HTTP API layer. At startup it:

1. Validates vault configuration.
2. Preloads all vault indexes.
3. Runs a lightweight contract check.
4. Starts a background thread for periodic contract rechecks.

Request middleware enforces a global rate limit (50 req/s) and structured JSON logging.

### 8. Generated Artefacts (`dist/`)

Context packages exported by `run.py export` or `POST /context/export` are written to `dist/context-bundles/<bundle-id>/`. The `dist/` directory is gitignored. These are build artefacts - they are regenerated from the vault, not edited directly.

### 9. Private Cloud Mode

`mcp/core/private_cloud.py` implements an optional authenticated remote access layer for the FastAPI server. It is **disabled by default**. When `CVE_PRIVATE_CLOUD_ENABLED=1`, the server requires a bearer token (`CVE_AUTH_TOKEN`) on protected routes. Setting `CVE_REMOTE_READ_ONLY=1` additionally blocks all write routes (bundle, export, security, query, compare, bootstrap, note, feedback, memory). Status is reported by `GET /private/status`.

### 10. Context Controller and Profiles

`mcp/core/context_controller.py` and `mcp/core/context_profiles.py` provide named device profiles (`phone-local-llm`, `desktop-agent`, ...) and budget modes (`tiny`, `small`, `medium`, `large`, `agent`) for context bundles and exports. Profiles enforce hard caps on bundle size, note count, body inclusion, and related-note inclusion. They are exposed through `/context/profiles`, the `cve.list_context_profiles` MCP tool, and the `cve://context/profiles` resource.

### 11. Session and Project State

`mcp/core/session_state.py` persists session and project state as human-readable JSON files under `<vault>/Vault Files/State/`. Sessions are written atomically (temp file + replace), keyed by `session_id`, and survive server restarts. Project state is a single JSON file per vault. There is no database and no cloud sync. The `/session/start`, `/session/resume`, `/session/summary`, `/session/attach-note`, `/session/close`, `GET /project/state`, and `PUT /project/state` routes expose this layer.

### 12. Safe Memory Write Queue

`mcp/core/pending_changes.py` and `mcp/core/note_write.py` implement the write path. All proposed note creations, section updates, and update suggestions are written to `Vault Files/State/pending-changes/` as YAML proposals and require explicit user approval before being applied to vault Markdown. The `/memory/*` routes and pending changes UI surface these proposals. There is no autonomous write path.

### 13. Trust, Staleness, and Evidence (Phase 25)

`mcp/core/trust_metadata.py` extracts optional `trust_level`, `source_type`, `last_reviewed`, and `review_after` frontmatter fields per note. It computes a deterministic confidence score reflecting the freshness and reviewer assertion of each note (not factual correctness). `GET /trust` and `GET /stale` surface aggregate views; `POST /evidence` builds a citation-ready evidence pack. Trust annotations are injected into context bundles and query results automatically.

---

## Data Flow

```
1. Note file (.md)
      ↓
2. note_index.py: parse YAML frontmatter → validate structure
      ↓
3. query_engine.py: apply filters → apply deterministic lexical scoring (if q present) → return ranked note objects
      ↓
4. context_bundle.py: select notes by filter + budget → assemble bundle
      ↓
5. context_security.py: scan bundle text for security issues (optional)
      ↓
6. context_package.py: write bundle files to dist/ + hash all files (optional)
      ↓
7. API / CLI: return JSON response or write to stdout
```

---

## Cache and Index Freshness

The index is considered stale when:

- A note file modification time is newer than the index build time.
- The schema file hash changes.

The index rebuilds lazily on the next API call after a 2-second cooldown (to avoid rebuilding on every save keystroke during active editing). CLI commands always rebuild the index fresh.

**Stale context is a correctness failure.** Generated bundles should be considered stale if vault files have been modified since the bundle was created.

---

## Determinism Principles

- **Same inputs → same outputs.** Given the same vault state and request parameters, all commands return the same result (except `created_at` timestamps).
- **`bundle_id` is deterministic.** Computed as SHA-256 of the bundle request parameters (vault name, filters, sections, flags, bounds). The same request always produces the same `bundle_id`.
- **Sort order is stable.** All lists (notes, tasks, graph nodes, findings) are sorted by a deterministic key before returning.
- **No LLM calls in core operations.** Validation, analysis, bundle generation, and security scanning do not call any AI service.

---

## Known Boundaries

- **Single vault per config.** The CLI (`run.py`) reads one vault from `config/config.yaml`. The API server can serve multiple vaults registered in `vault_registry.py`.
- **Markdown source of truth.** Notes must be edited as Markdown files. The system does not provide a write API for note content.
- **Generated artefacts are not source.** Context packages, validation reports, and generated templates are derived outputs. Do not treat them as authoritative.
- **Deterministic lexical search in query layer.** `POST /query` supports an optional `q` parameter for free-text lexical search over note body, path, or frontmatter values. Scoring is deterministic and pure-Python: for each unique query term, TF = occurrences / corpus length; score = mean TF across unique terms. Results are ranked by score descending then path ascending. No embeddings, no persistent index, no new dependencies.
- **No semantic retrieval.** The current implementation does not use embeddings or vector search. All structured queries are filter-based (equality, substring, list membership). The lexical `q` parameter is deterministic keyword scoring only. Semantic retrieval (embeddings, vector search) remains a future phase and is not implemented.
- **No registry.** Context packages are written to `dist/` but there is no registry, versioning, or deduplication layer. This is a future phase.
- **Trust metadata layer (Phase 25).** Optional `trust_level`, `source_type`, `last_reviewed`, `review_after` frontmatter fields per note. `mcp/core/trust_metadata.py` provides extraction, confidence scoring, staleness detection, and the evidence builder. Confidence reflects user/system-provided maintenance metadata, not factual correctness. Trust annotations are injected into context bundles and query results automatically. The `/trust`, `/stale`, and `/evidence` endpoints expose this layer to API consumers.

---

## Safe Extension Zones

These areas are safe to extend without breaking existing behaviour:

- Adding new API routes (add after existing routes, avoid path conflicts with `/{vault}` patterns).
- Adding new adapter functions (they are thin wrappers).
- Adding new security rules to `context_security.py` (additive, no breaking changes to existing rule names).
- Adding new CLI commands to `run.py` (add new `if command == "..."` blocks).
- Adding new schema fields (additive, but regenerate templates after schema changes).

## Unsafe Zones

These changes carry high risk of breaking existing behaviour:

- Changing the `vault_schema.py` interface (field names, enum values, function signatures).
- Changing the `bundle_id` hash computation (breaks existing package directory names).
- Changing the note index structure (all adapters depend on it).
- Modifying the `ALL_KNOWN_FIELDS` contract (breaks query validation).
- Changing the `feedback.md` YAML structure (breaks the feedback parser).
