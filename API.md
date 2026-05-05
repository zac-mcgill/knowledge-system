# Context Vault Engine — API Reference

The Context Vault Engine API is a read-mostly HTTP API served by `mcp/server/mcp_server.py`. It exposes validation status, improvement tasks, quality audits, context bundles, export operations, security scans, and graph relationships.

**Start the server:**
```bash
pip install -r mcp/requirements.txt
py mcp/server/mcp_server.py
# Server listens on http://127.0.0.1:8000
```

## General Conventions

- All responses use the envelope `{"status": "ok", "data": {...}}` on success.
- All errors use `{"status": "error", "error": {"code": "...", "message": "..."}}`.
- The `vault` parameter defaults to the first registered vault when omitted.
- Rate limit: 50 requests/second (global, in-memory). HTTP 429 on excess.
- All note paths use vault-relative POSIX forward slashes (e.g. `Fundamentals/Algorithms.md`).

---

## Route Index

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/vaults` | List registered vault names |
| `GET` | `/health` | Server health and request metrics |
| `GET` | `/contract` | System contract check |
| `GET` | `/summary` | Vault-level completion summary |
| `POST` | `/query` | Filtered note query |
| `GET` | `/note` | Single note by vault + path |
| `GET` | `/stats` | Field-value frequency aggregation |
| `GET` | `/validation` | Schema validation result |
| `GET` | `/tasks` | Prioritised improvement tasks |
| `GET` | `/notes` | All notes with metadata |
| `GET` | `/quality` | Content quality audit |
| `GET` | `/missing` | Missing concept detection |
| `GET` | `/gaps` | High-priority incomplete notes |
| `GET` | `/feedback` | Vault feedback entries |
| `POST` | `/compare` | Delta comparison between two vault states |
| `GET` | `/graph` | Full vault relationship graph |
| `GET` | `/graph/neighbors` | All nodes directly connected to a node |
| `GET` | `/graph/related` | Notes related to a node (query-param form) |
| `GET` | `/graph/missing` | Missing concepts near a node (query-param form) |
| `GET` | `/graph/{vault}` | Graph by vault (path-param form) |
| `GET` | `/graph/{vault}/related` | Related notes by vault (path-param form) |
| `GET` | `/graph/{vault}/missing` | Missing concepts by vault (path-param form) |
| `POST` | `/context/bundle` | Generate a deterministic context bundle |
| `POST` | `/context/export` | Export a context bundle as a portable package |
| `POST` | `/context/security` | Scan a context bundle for security issues |
| `GET` | `/app` | Serve compiled local web UI (index.html) |
| `GET` | `/app/{ui_path:path}` | Serve compiled local web UI static assets |

---

## Core Endpoints

### GET /vaults

List all registered vault names.

**Response:**
```json
{"status": "ok", "data": {"vaults": ["demo-vault"]}}
```

---

### GET /health

Server health, vault metrics, and request statistics.

**Response data:**
- `vaults` — per-vault index stats (notes, schema_hash, last_index_time).
- `uptime_seconds` — seconds since server started.
- `requests_served` — total requests handled.
- `rate_limit_status` — current rate-limiter counters.
- `metrics` — per-endpoint request counts and average response time.

**Example response:**
```json
{
  "status": "ok",
  "data": {
    "vaults": {
      "demo-vault": {"notes": 19, "schema_hash": "abc123..."}
    },
    "uptime_seconds": 42,
    "requests_served": 10,
    "rate_limit_status": {"max_per_second": 50, "current_window": 1, "total_rejected": 0},
    "metrics": {"per_endpoint": {"/health": 1}, "avg_response_time_ms": 2.5}
  }
}
```

---

### GET /contract

Run system contract checks.

**Query parameters:**
- `full` (bool, default `false`) — if `true`, includes vault script checks.

**Response data:**
- `status` — `"pass"` or `"fail"`.
- `duration_ms` — time taken.
- `total_violations` — total violation count.
- `violations` — list of violation descriptions.

---

### GET /summary

Aggregate vault-level completion summary.

**Response data:**
- `total_notes`, `complete`, `partial`, `coverage` (percentage).

---

## Query Endpoints

### POST /query

Query vault notes with optional filters and optional free-text lexical search.

**Request body:**
```json
{
  "vault": "demo-vault",
  "filters": {"domain": "fundamentals", "status": "complete"},
  "limit": 50,
  "offset": 0,
  "strict": false,
  "q": "recursion algorithm",
  "q_fields": ["body"]
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `vault` | string | required | Vault name |
| `filters` | object | `{}` | Key/value filters. Supports `field` (equality), `field__in` (list), `field__contains` (substring). |
| `limit` | int | `50` | Page size (1–500) |
| `offset` | int | `0` | Page offset |
| `strict` | bool | `false` | Reject unknown filter fields when `true` (both modes reject unknown fields now) |
| `q` | string | `null` | Free-text lexical search (max 1000 chars). Omit or leave blank to preserve filter-only behaviour. |
| `q_fields` | list[string] | `["body"]` | Fields to search when `q` is supplied. Allowed values: `body`, `path`, `frontmatter`. |

**Lexical search behaviour:**
- When `q` is omitted or blank, the endpoint behaves exactly as before (filter-only).
- When `q` is present, notes are scored by deterministic term-frequency coverage and ranked by score descending, then path ascending.
- Only notes with score > 0 are returned.
- Each result includes a `score` key (float, range 0.0–1.0) when `q` is supplied.
- Lexical search **intersects** with `filters`; both constraints must be satisfied.
- No embeddings, no persistent index, no new dependencies.

**Scoring model:** For each unique query term, TF = (occurrences in corpus) / (corpus length). Score = mean TF across all unique query terms. Missing terms contribute zero; the score is deterministic (no synonyms, stemming, or semantic relevance).

**Filter validation:** Unknown fields, unsupported operators, and `__in` with a non-list value return `INVALID_FILTER` with zero results.

**Response data:** `count`, `returned`, `offset`, `limit`, `results` (list of `{path, fields}`, or `{path, fields, score}` when `q` is present).

**Error codes:**
- `INVALID_FILTER` — unknown field or invalid operator (HTTP 400).
- `INVALID_QUERY` — `q` exceeds 1000 characters, `q_fields` contains an unsupported field name, or `q_fields` is an empty list (HTTP 400).

---

### GET /note

Retrieve a single note by vault and path.

**Query parameters:**
- `vault` (required) — vault name.
- `path` (required) — vault-relative path.

**Response data:** `path`, `fields` (all frontmatter fields).

**Error codes:**
- `NOT_FOUND` — no note at that path (HTTP 404).
- `PATH_TRAVERSAL` — path attempts to escape vault root (HTTP 400).

---

### GET /stats

Aggregate distinct values for a field across a vault.

**Query parameters:**
- `vault` (required) — vault name.
- `field` (required) — field to aggregate.

**Response data:** `field`, `stats` (mapping of value → count, ordered by frequency).

**Error codes:**
- `INVALID_FIELD` — field not known to vault schema (HTTP 400).

---

## Analysis Endpoints

### GET /validation

Run vault validation and return structured results.

**Query parameters:**
- `vault` (optional)

**Response data:**
- `status` — `"pass"` or `"fail"`.
- `invalid_count` — number of notes that failed.
- `invalid_notes` — sorted list of vault-relative paths of invalid notes.

---

### GET /tasks

Return prioritised upgrade tasks.

**Query parameters:**
- `vault` (optional)
- `limit` (int, default `10`) — max tasks to return.
- `min_priority` (float, optional) — minimum priority threshold.
- `include_feedback` (bool, default `false`) — adjust scores by feedback signals.

**Response data:**
- `total` — total tasks available.
- `tasks` — normalised task objects.

**Each task:**
- `note` — note stem name.
- `path` — vault-relative POSIX path.
- `priority` — computed priority score.
- `type` — always `"missing_section"`.
- `target` — primary missing section.
- `missing` — all missing sections.
- `instruction` — human-readable action.
- `constraints` — writing constraints for the primary issue.
- `feedback_weight` — score delta and entry summary (only when `include_feedback=true`).

When `include_feedback=true`, response also includes:
- `feedback_status` — `"ok"` or `"error"`.
- `feedback_errors` — structured errors from feedback parser.

---

### GET /notes

List all notes with metadata.

**Query parameters:**
- `vault` (optional)

**Response data:** `notes` (list of note objects sorted by name, case-insensitive).

**Each note:** `name`, `status`, `difficulty`, `missing` (missing section slugs), `path`.

---

### GET /quality

Run content quality audit.

**Query parameters:**
- `vault` (optional)

**Response data:**
- `total`, `flagged`, `highest_score`, `average_score`.
- `notes` — per-note audit results sorted descending by score.

**Each note entry:** `file`, `score`, `severity`, `issues` (list of `{rule, weight, explanation}`).

---

### GET /missing

Detect missing concepts across expected subdomains.

**Query parameters:**
- `vault` (optional)

**Response data:**
- `total_expected`, `total_actual`, `total_missing`, `domains_assessed`, `subdomains`.
- `gaps` — mapping of subdomain → list of missing concept objects.
- `ranked` — all missing concepts ranked by score.

**Note:** Returns `MISSING_CONCEPTS_EMPTY` (HTTP 422) if `EXPECTED_CONCEPTS` is not defined or empty in `vault_schema.py`. The demo vault defines `EXPECTED_CONCEPTS` with example gap data for the Fundamentals domain.

---

### GET /gaps

Return high-priority incomplete notes (priority >= 2).

**Response data:** `gaps` — list of `{note, priority, missing}`, sorted descending by priority.

---

### GET /feedback

Return vault feedback entries from `Vault Files/feedback.md`.

**Query parameters:**
- `vault` (optional)

**Response data:**
- `status` — `"ok"` or `"error"`.
- `vault` — resolved vault name.
- `entries` — validated feedback entries.
- `warnings` — non-fatal issues (e.g. feedback for a missing note path).
- `errors` — structured validation errors (empty when `status="ok"`).

**Each feedback entry:** `path`, `source`, `signal`, `severity`, `comment`, `created_at`.

**Error codes:**
- `FEEDBACK_ERROR` — feedback file is malformed (HTTP 500).

---

### POST /compare

Compare two vault states and return a structured delta report.

**Request body:**
```json
{
  "before": "Vault Files/Vault Report.md",
  "after": null,
  "vault": "demo-vault"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `before` | string (required) | Path to BEFORE report (relative to vault root or absolute). Must be non-empty. |
| `after` | string \| null | Path to AFTER report. Omit to compare against live vault state. |
| `vault` | string \| null | Vault name; defaults to first registered vault. |

**Response data:** `before`, `after`, `delta`, `report` (full Markdown delta).

**Error codes:**
- `INVALID_INPUT` — `before` is blank (HTTP 400).
- `COMPARE_FAILED` — report file not found or comparison error (HTTP 500).

---

## Graph Endpoints

All graph endpoints derive relationships from schema-defined hierarchy (domain / subdomain / topic) and frontmatter fields. No LLMs, no embeddings.

### GET /graph

Return full vault relationship graph.

**Query parameters:**
- `vault` (optional)

**Response data:**
- `nodes` — all graph nodes, sorted ascending by id. Each: `id`, `type`, `label`.
- `edges` — all graph edges, sorted ascending by (from, to, type). Each: `from`, `to`, `type`.

Node types: `note`, `domain`, `subdomain`, `topic`, `expected_concept`.
Edge types: `parent`, `same_domain`, `same_subdomain`, `same_topic`, `expected_coverage`.

---

### GET /graph/neighbors

Return all nodes directly connected to a given node (both edge directions).

**Query parameters:**
- `node` (required) — node id to query (e.g. `note::Fundamentals/Algorithms.md`).
- `vault` (optional)

**Response data:** `node_id`, `found`, `neighbors` (list sorted ascending by id).

Each neighbor: `id`, `type`, `label`, `edge_type` (the type of the connecting edge).

---

### GET /graph/related

Return notes related to a node via shared group hubs.

**Query parameters:**
- `node` (required) — node id to query.
- `vault` (optional)
- `min_strength` (string, default `"domain"`) — minimum relationship strength: `topic` | `subdomain` | `domain`.

**Response data:** `node_id`, `found`, `related` (list sorted by strength desc, then id asc).

Each related entry: `id`, `type`, `label`, `via` (strongest shared group node), `strength`.

---

### GET /graph/missing

Return expected concepts missing near a node's group hubs.

**Query parameters:**
- `node` (required) — node id to query.
- `vault` (optional)

**Response data:** `node_id`, `found`, `missing` (list sorted ascending by id).

Each missing entry: `id`, `label`, `via`.

---

### GET /graph/{vault}

Same as `GET /graph?vault={vault}`. Vault name in path.

---

### GET /graph/{vault}/related

Same as `GET /graph/related?node={node_id}&vault={vault}`.

**Query parameters:**
- `node_id` (required) — node id to query.
- `min_strength` (optional, default `"domain"`)

---

### GET /graph/{vault}/missing

Same as `GET /graph/missing?node={node_id}&vault={vault}`.

**Query parameters:**
- `node_id` (required) — node id to query.

---

## Context Endpoints

### POST /context/bundle

Generate a deterministic context bundle. See [CONTEXT_BUNDLE_SPEC.md](CONTEXT_BUNDLE_SPEC.md) for full specification.

**Request body:**
```json
{
  "vault": "demo-vault",
  "filters": {"domain": "fundamentals", "status": "complete"},
  "include_sections": ["Key Principles", "How It Works", "Trade-offs"],
  "include_related": false,
  "include_body": true,
  "max_notes": 10,
  "max_chars": 20000,
  "allow_partial": false
}
```

All fields except `vault` are optional. See [CONTEXT_BUNDLE_SPEC.md](CONTEXT_BUNDLE_SPEC.md) for defaults and field descriptions.

**Response:** Full bundle JSON (see [CONTEXT_BUNDLE_SPEC.md](CONTEXT_BUNDLE_SPEC.md) for response shape).

**Error codes:**
- `INVALID_VAULT` — vault not registered (HTTP 404).
- `INVALID_FILTER` — unknown filter field (HTTP 400).
- `VALIDATION_ERROR` — `max_notes` or `max_chars` out of range (HTTP 422).
- `BUNDLE_FAILED` — unexpected error (HTTP 500).

---

### POST /context/export

Generate a context bundle and write it to disk as a portable package.

**Request body:** Same fields as `/context/bundle`, plus:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `overwrite` | bool | `false` | Replace existing package for this `bundle_id`. |
| `require_security_pass` | bool | `false` | Abort export if security scan status is `fail`. |

**Response:**
```json
{
  "status": "ok",
  "bundle_id": "c240ffb1e9250194",
  "package_dir": "dist/context-bundles/c240ffb1e9250194",
  "files": {
    "context.json":          {"sha256": "...", "bytes": 12345},
    "context.md":            {"sha256": "...", "bytes": 6789},
    "manifest.json":         {"sha256": "...", "bytes": 890},
    "validation.json":       {"sha256": "...", "bytes": 234},
    "graph.json":            {"sha256": "...", "bytes": 56},
    "feedback-summary.json": {"sha256": "...", "bytes": 78}
  },
  "warnings": []
}
```

**Error codes:**
- `INVALID_VAULT` — vault not registered (HTTP 404).
- `INVALID_FILTER` — unknown filter field (HTTP 400).
- `PACKAGE_EXISTS` — package exists and `overwrite=false` (HTTP 409).
- `SECURITY_SCAN_FAIL` — scan status is `fail` and `require_security_pass=true` (HTTP 400).
- `BUNDLE_FAILED` / `EXPORT_FAILED` — unexpected error (HTTP 500).

**Notes:**
- Packages are written to `dist/context-bundles/<bundle_id>/` under the repo root.
- `manifest.json` contains SHA-256 hashes of the other five files, plus metadata.
- The `dist/` directory is gitignored.

---

### POST /context/security

Scan selected vault notes for security issues using deterministic regex rules.

**Request body:**
```json
{
  "vault": "demo-vault",
  "filters": {"status": "complete"},
  "include_sections": ["Key Principles", "How It Works", "Trade-offs"],
  "include_body": true,
  "max_notes": 10,
  "max_chars": 20000,
  "allow_partial": false
}
```

All fields except `vault` are optional.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "status": "pass",
    "findings": [],
    "summary": {"fail": 0, "warning": 0, "info": 0},
    "scanned": {
      "note_count": 8,
      "source_paths": ["Fundamentals/Algorithms.md", "..."]
    }
  }
}
```

**Scan status levels:**

| Status | Meaning |
|--------|---------|
| `pass` | No findings |
| `warning` | Findings present, none blocking-severity |
| `fail` | Blocking finding detected (private key, API key, bearer token, password pattern) |

**Each finding:** `path`, `severity` (`low`/`medium`/`high`/`critical`), `rule`, `field`, `detail`.

**Error codes:**
- `INVALID_VAULT` — vault not registered (HTTP 404).
- `INVALID_FILTER` — unknown filter field (HTTP 400).
- `SECURITY_SCAN_FAILED` — unexpected error (HTTP 500).

**Important:** This is a rule-based static scanner. It may produce false positives on documentation that describes security concepts. Review findings manually.

---

## Local Web UI

### GET /app

### GET /app/{ui_path:path}

Serve the compiled local web UI static files from `ui/dist/`.

- **`GET /app`** — serves `ui/dist/index.html`.
- **`GET /app/{ui_path:path}`** — serves the requested static asset from `ui/dist/`. If the exact path is not found, serves `index.html` (SPA fallback).
- **Path traversal protection:** any path containing `..` returns HTTP 400 `PATH_TRAVERSAL`.
- **UI not built:** if `ui/dist/` does not exist, returns HTTP 503 with `UI_NOT_BUILT` error and build instructions.

**Successful response:** Static HTML/CSS/JS files (not JSON).

**Error responses:**
```json
{"status": "error", "error": {"code": "UI_NOT_BUILT", "message": "UI not built. Run: cd ui && npm install && npm run build"}}
{"status": "error", "error": {"code": "PATH_TRAVERSAL", "message": "Path traversal detected"}}
```

**Building the UI:**
```bash
cd ui
npm install
npm run build
# ui/dist/ is now ready — served at GET /app
```

All existing API routes (`/health`, `/vaults`, `/summary`, etc.) remain fully functional whether or not `ui/dist/` is present.

---

## Error Reference

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `INVALID_FILTER` | 400 | Unknown or malformed filter field |
| `VALIDATION_ERROR` | 422 | Pydantic request validation error (field out of range, wrong type) |
| `NOT_FOUND` | 404 | Note path not found |
| `PATH_TRAVERSAL` | 400 | Path attempts to escape vault root |
| `INVALID_FIELD` | 400 | Field not known to vault schema |
| `MISSING_CONCEPTS_EMPTY` | 422 | `EXPECTED_CONCEPTS` not defined in schema |
| `PACKAGE_EXISTS` | 409 | Package directory already exists, `overwrite=false` |
| `SECURITY_SCAN_FAIL` | 400 | Security scan failed and `require_security_pass=true` |
| `RATE_LIMIT` | 429 | Too many requests (>50/sec) |
| `UI_NOT_BUILT` | 503 | `ui/dist/` not present — run `npm run build` in `ui/` |
| `INTERNAL` | 500 | Unexpected server error |
