# Context Vault Engine - API Reference

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

## Authentication (Private Cloud Mode)

When `CVE_PRIVATE_CLOUD_ENABLED=true`, authentication is required for all non-health API routes.

**Token header formats (either is accepted):**

```
Authorization: Bearer <token>
X-CVE-Token: <token>
```

**Unauthenticated request returns HTTP 401:**
```json
{"status": "error", "error": {"code": "AUTH_REQUIRED", "message": "Authentication required. ..."}}
```

**Mutating route in read-only mode returns HTTP 403:**
```json
{"status": "error", "error": {"code": "REMOTE_READ_ONLY", "message": "Remote read-only mode blocks this operation."}}
```

**Auth-exempt routes (always accessible without a token):**
- `GET /health`
- `GET /private/status`

**Environment variables controlling auth:**

| Variable | Purpose | Default |
|----------|---------|---------|
| `CVE_PRIVATE_CLOUD_ENABLED` | Enable private cloud mode | `false` |
| `CVE_AUTH_TOKEN` | Secret bearer token (never committed or logged) | _(empty)_ |
| `CVE_REQUIRE_AUTH` | Require auth for API routes | `false` locally; `true` when private cloud enabled |
| `CVE_REMOTE_READ_ONLY` | Block all mutating HTTP routes | `true` when private cloud enabled |
| `CVE_PUBLIC_BASE_URL` | Public base URL for status display only | _(empty)_ |
| `CVE_DEPLOYMENT_MODE` | Deployment mode tag: `local`, `vps`, `tunnel` | `local` |

**Local mode is unchanged.** When `CVE_PRIVATE_CLOUD_ENABLED` is not set (or set to `false`), all existing behaviour is identical - no auth is required and no routes are blocked.

See `DEPLOYMENT.md` for full deployment and VPS setup guidance.

---

## Route Index

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/vaults` | List registered vault names |
| `GET` | `/health` | Server health and request metrics |
| `GET` | `/private/status` | Private cloud mode configuration status (Phase 21) |
| `GET` | `/contract` | System contract check |
| `GET` | `/summary` | Vault-level completion summary |
| `POST` | `/query` | Filtered note query |
| `GET` | `/note` | Single note by vault + path |
| `PUT` | `/note` | Safely update an existing note (Phase 15B) |
| `GET` | `/stats` | Field-value frequency aggregation |
| `GET` | `/validation` | Schema validation result |
| `GET` | `/tasks` | Prioritised improvement tasks |
| `GET` | `/notes` | All notes with metadata |
| `GET` | `/quality` | Content quality audit |
| `GET` | `/missing` | Missing concept detection |
| `GET` | `/gaps` | High-priority incomplete notes |
| `GET` | `/feedback` | Vault feedback entries |
| `POST` | `/feedback` | Add a new feedback entry (Phase 14A) |
| `PUT` | `/feedback/{feedback_id}` | Update an existing feedback entry (Phase 14A) |
| `DELETE` | `/feedback/{feedback_id}` | Delete a feedback entry (Phase 14A) |
| `POST` | `/feedback/normalise` | Assign IDs to id-less entries (Phase 14A) |
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
| `GET` | `/context/profiles` | List all built-in context profiles and modes |
| `GET` | `/context/profiles/{profile_name}` | Get a single profile or mode definition |
| `GET` | `/trust` | Vault-level trust/confidence/staleness summary (Phase 25) |
| `GET` | `/stale` | Vault staleness breakdown - stale, freshness_unknown, deprecated notes (Phase 25) |
| `POST` | `/evidence` | Build trust-ranked evidence with source paths and section excerpts (Phase 25) |
| `GET` | `/app` | Serve compiled local web UI (index.html) |
| `GET` | `/app/{ui_path:path}` | Serve compiled local web UI static assets |
| `POST` | `/vault/bootstrap` | Create a new vault (Phase 11A) |
| `DELETE` | `/vault/{vault_name}` | Permanently delete a non-demo vault (Phase 18C) |
| `GET` | `/context/state` | Current context controller state (Phase 19) |
| `POST` | `/context/plan` | Plan a deterministic context fetch (Phase 19) |
| `POST` | `/session/start` | Start a new session (Phase 22) |
| `GET` | `/session/resume` | Resume an existing session by id (Phase 22) |
| `GET` | `/session/summary` | Summary of the current/active session (Phase 22) |
| `POST` | `/session/attach-note` | Attach a note path to the active session (Phase 22) |
| `POST` | `/session/close` | Close a session (Phase 22) |
| `GET` | `/project/state` | Project state for the active vault (Phase 22) |
| `PUT` | `/project/state` | Update project state for the active vault (Phase 22) |
| `GET` | `/memory/pending` | List pending change proposals (Phase 23) |
| `GET` | `/memory/pending/{change_id}` | Get a single pending change proposal (Phase 23) |
| `POST` | `/memory/create-note-draft` | Propose a new note as a pending change (Phase 23) |
| `POST` | `/memory/suggest-note-update` | Propose an update to a whole note (Phase 23) |
| `POST` | `/memory/update-section-draft` | Propose an update to a single section (Phase 23) |
| `POST` | `/memory/pending/{change_id}/accept` | Accept a pending change and write it (Phase 23) |
| `POST` | `/memory/pending/{change_id}/reject` | Reject a pending change (Phase 23) |

Route groups, for orientation:

- **Core:** `/vaults`, `/health`, `/private/status`, `/contract`
- **Notes and query:** `/note` (GET/PUT), `/notes`, `/query`, `/stats`, `/compare`
- **Validation, tasks, quality, feedback:** `/validation`, `/tasks`, `/quality`, `/missing`, `/gaps`, `/feedback` (GET/POST), `/feedback/{id}` (PUT/DELETE), `/feedback/normalise`, `/summary`
- **Graph:** `/graph`, `/graph/neighbors`, `/graph/related`, `/graph/missing`, `/graph/{vault}` and its `/related` and `/missing` forms
- **Context, profiles, controller:** `/context/bundle`, `/context/export`, `/context/security`, `/context/profiles`, `/context/profiles/{name}`, `/context/state`, `/context/plan`
- **Trust and evidence:** `/trust`, `/stale`, `/evidence`
- **App and vault lifecycle:** `/app`, `/app/{ui_path:path}`, `/vault/bootstrap`, `/vault/{vault_name}` (DELETE)
- **Session and project state:** `/session/start`, `/session/resume`, `/session/summary`, `/session/attach-note`, `/session/close`, `/project/state` (GET/PUT)
- **Safe memory write queue:** `/memory/pending`, `/memory/pending/{change_id}`, `/memory/create-note-draft`, `/memory/suggest-note-update`, `/memory/update-section-draft`, `/memory/pending/{change_id}/accept`, `/memory/pending/{change_id}/reject`

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
- `vaults` - per-vault index stats (notes, schema_hash, last_index_time).
- `uptime_seconds` - seconds since server started.
- `requests_served` - total requests handled.
- `rate_limit_status` - current rate-limiter counters.
- `metrics` - per-endpoint request counts and average response time.

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

### GET /private/status

Return private cloud mode configuration status. Always accessible without authentication - even when `CVE_REQUIRE_AUTH=true`.

**Response data:**
- `enabled` (bool) - True if `CVE_PRIVATE_CLOUD_ENABLED=true`.
- `deployment_mode` (str) - Value of `CVE_DEPLOYMENT_MODE` (`local`, `vps`, `tunnel`).
- `require_auth` (bool) - True if authentication is currently required.
- `token_configured` (bool) - True if `CVE_AUTH_TOKEN` is set. Never exposes the token value.
- `remote_read_only` (bool) - True if mutating routes are blocked.
- `public_base_url` (str | null) - Value of `CVE_PUBLIC_BASE_URL` if set.
- `warnings` (list[str]) - Configuration warnings (no secrets).
- `protected_methods` (list[str]) - HTTP methods blocked in read-only mode.

**Example response (private cloud enabled):**
```json
{
  "status": "ok",
  "data": {
    "enabled": true,
    "deployment_mode": "vps",
    "require_auth": true,
    "token_configured": true,
    "remote_read_only": true,
    "public_base_url": "https://vault.example.com",
    "warnings": [],
    "protected_methods": ["PUT", "POST", "DELETE"]
  }
}
```

**Example response (local mode):**
```json
{
  "status": "ok",
  "data": {
    "enabled": false,
    "deployment_mode": "local",
    "require_auth": false,
    "token_configured": false,
    "remote_read_only": false,
    "public_base_url": null,
    "warnings": [],
    "protected_methods": []
  }
}
```

---

### GET /contract

Run system contract checks.

**Query parameters:**
- `full` (bool, default `false`) - if `true`, includes vault script checks.

**Response data:**
- `status` - `"pass"` or `"fail"`.
- `duration_ms` - time taken.
- `total_violations` - total violation count.
- `violations` - list of violation descriptions.

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
- `INVALID_FILTER` - unknown field or invalid operator (HTTP 400).
- `INVALID_QUERY` - `q` exceeds 1000 characters, `q_fields` contains an unsupported field name, or `q_fields` is an empty list (HTTP 400).

---

### GET /note

Retrieve a single note by vault and path.

**Query parameters:**
- `vault` (required) - vault name.
- `path` (required) - vault-relative path.

**Response data:** `path`, `fields` (all frontmatter fields).

**Error codes:**
- `NOT_FOUND` - no note at that path (HTTP 404).
- `PATH_TRAVERSAL` - path attempts to escape vault root (HTTP 400).

---

### PUT /note

Safely update an existing Markdown note in a vault. The note must already exist; this endpoint does not create new notes. Writes are atomic (temp-file + rename), and the note is fully validated against the vault schema before any disk change is made. The in-memory index and result cache are invalidated on success.

**Request body:**
```json
{
  "vault": "demo-vault",
  "path": "Fundamentals/Algorithms.md",
  "fields": {
    "type": "core-concept",
    "domain": "fundamentals",
    "status": "complete",
    "has_key_principles": true,
    "has_how_it_works": true,
    "has_tradeoffs": true,
    "difficulty": "intermediate"
  },
  "body": "## Definition\n\nAn algorithm is a finite sequence...\n"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `path` | string | yes | Vault-relative POSIX path (must be an existing `.md` file, not inside `Vault Files/`) |
| `fields` | object | yes | All frontmatter fields. Only known schema fields are accepted. Booleans as JSON `true`/`false`. |
| `body` | string | yes | Markdown body (everything after the frontmatter block). No null bytes. |

**Safety guarantees:**
- Path traversal is rejected at both service and HTTP layers.
- Null bytes in path or body are rejected.
- All known schema enum values are validated (`status`, `domain`, `difficulty`, `type`).
- Section boolean fields (`has_key_principles`, `has_how_it_works`, `has_tradeoffs`) are reconciled against actual body content.
- If validation fails, the disk file is never modified (pre-validation before write).
- Write uses `mkstemp` + `os.replace` (atomic rename) to prevent partial writes.
- On success, `expire_index_cooldown` is called so the next query rebuilds the index.

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "path": "Fundamentals/Algorithms.md",
    "fields": {"type": "core-concept", "domain": "fundamentals", ...},
    "body": "## Definition\n\n...",
    "validation": {"status": "pass", "errors": []},
    "warnings": []
  }
}
```

**Error codes:**
- `INVALID_INPUT` - unknown field, null byte, non-string body, or missing required request field (HTTP 400).
- `PATH_TRAVERSAL` - path escapes vault root or is absolute (HTTP 400).
- `INVALID_NOTE_PATH` - path is not `.md` or is inside `Vault Files/` (HTTP 400).
- `NOT_FOUND` - note does not exist (HTTP 404).
- `INVALID_VAULT` - vault not registered (HTTP 404).
- `VALIDATION_FAILED` - note content fails schema validation (HTTP 400). Includes `details` list.
- `WRITE_FAILED` - disk write or atomic rename failed (HTTP 500).

---

### POST /import/markdown-folder

Safely import a folder of Markdown files into a vault (Phase 26A). The pipeline is local-only, deterministic, and dry-run by default. It discovers `.md` files in the source folder, scans each body via the project security scanner, drops unknown source frontmatter, recomputes section booleans from body content, marks imports with `trust_level: draft` and `source_type: imported` when the schema supports those fields, serialises candidate notes, validates each candidate against the vault schema, and only writes when validation passes. Default destination is `Imported/` inside the vault. Writes inside `Vault Files/` are always rejected. The note index and result cache are invalidated after any successful write. Blocked in remote read-only mode.

**Request body:**
```json
{
  "vault": "demo-vault",
  "source_dir": "C:/path/to/markdown/folder",
  "destination": "Imported",
  "dry_run": true,
  "overwrite": false
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `vault` | string | yes | - | Registered vault name |
| `source_dir` | string | yes | - | Absolute filesystem path to the folder of Markdown sources |
| `destination` | string | no | `"Imported"` | Vault-relative POSIX subfolder for imports; rejected if it traverses the vault, is absolute, or lands inside `Vault Files/` |
| `dry_run` | bool | no | `true` | When true, no files are written; the response shows the plan |
| `overwrite` | bool | no | `false` | When true, existing destination notes are replaced atomically |

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "vault": "demo-vault",
    "source_dir": "C:/path/to/markdown/folder",
    "destination": "Imported",
    "dry_run": true,
    "overwrite": false,
    "summary": {
      "discovered": 3,
      "planned": 2,
      "written": 0,
      "skipped": 1,
      "errors": 0,
      "warnings": 1
    },
    "items": [
      {
        "source_path": "C:/path/to/markdown/folder/algos.md",
        "destination_path": "Imported/algos.md",
        "action": "create",
        "status": "planned",
        "fields": {"type": "core-concept", "trust_level": "draft", "source_type": "imported"},
        "warnings": ["dropped unknown frontmatter key: legacy_id"],
        "errors": [],
        "security": {"status": "pass", "findings": []},
        "validation": {"status": "pass", "errors": []}
      }
    ]
  }
}
```

`status` per item is one of `planned`, `written`, `skipped`, `blocked`, or `error`. `action` is one of `create`, `overwrite`, or `skip`.

**Error codes:**
- `INVALID_VAULT` - vault not registered (HTTP 404).
- `INVALID_SOURCE` - `source_dir` missing, not a directory, or contains null bytes (HTTP 400).
- `UNSAFE_SOURCE` - source folder rejected by safety checks (HTTP 400).
- `UNSAFE_DESTINATION` - destination traverses the vault, is absolute, or lands in `Vault Files/` (HTTP 400).
- `READ_FAILED` - source file unreadable for an unexpected reason (per-item; surfaced in item `errors`).
- `SOURCE_TOO_LARGE` - source file exceeds the 5 MB size cap (per-item; Phase 26D).
- `NULL_BYTE` - source file contains a NUL byte (per-item; Phase 26D).
- `SECURITY_FAIL` - blocking security finding (high or critical severity) in a source body (per-item).
- `INVALID_FRONTMATTER` - malformed YAML in source frontmatter, including an orphan opening `---` marker with no closing marker (per-item).
- `FRONTMATTER_NOT_OBJECT` - YAML frontmatter parsed to a non-mapping value (list, scalar, null) (per-item; Phase 26D).
- `DUPLICATE_YAML_KEY` - YAML frontmatter contains a duplicated mapping key (per-item; Phase 26D).
- `SERIALISE_FAILED` - candidate note could not be serialised (per-item).
- `VALIDATION_FAILED` - candidate failed schema validation (per-item; `validation.errors` populated).
- `DESTINATION_EXISTS` - destination already exists and `overwrite=false` (per-item).
- `WRITE_FAILED` - atomic write failed (per-item; HTTP 200 returned with item-level error).
- `READ_ONLY` - remote read-only mode forbids writes (HTTP 403).
- `IMPORT_FAILED` - unexpected pipeline error (HTTP 500).

Phase 26D guarantees: dry-run is deterministic for repeated identical inputs, one bad file does not crash the batch (other items still get planned), summary counts (`discovered`, `planned`, `written`, `skipped`, `errors`, `warnings`) match per-item statuses exactly, and repeated writes with `overwrite=false` skip existing destinations deterministically with `DESTINATION_EXISTS`. Phase 26D does not add any new import sources; PDF, browser article, GitHub repo, Obsidian-specific, chat transcript, semantic mapping, and LLM extraction imports remain deferred.

---

### POST /import/obsidian-vault

Safely import Markdown notes from an Obsidian vault folder into a Context Vault Engine vault (Phase 26E). This endpoint accepts the root of an Obsidian vault, skips Obsidian config (`.obsidian/`) and binary attachments, preserves Obsidian wikilinks verbatim in note bodies, and reports Obsidian-specific features (wikilinks, embeds, tags, aliases, callouts, attachment references) as deterministic per-item metadata. The Phase 26A-D safety pipeline applies in full: null-byte rejection, oversize rejection (5 MB cap), duplicate YAML key detection, malformed-frontmatter detection, security scan before write, schema validation before write, destination safety checks, atomic writes, and cache and index invalidation. Default destination is `Imported/Obsidian/`. Dry-run by default; no overwrite by default. Blocked in remote read-only mode.

**Request body:**
```json
{
  "vault": "demo-vault",
  "source_dir": "C:/Users/Zach/Documents/My Obsidian Vault",
  "destination": "Imported/Obsidian",
  "dry_run": true,
  "overwrite": false
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `vault` | string | yes | - | Registered vault name |
| `source_dir` | string | yes | - | Absolute filesystem path to an Obsidian vault folder |
| `destination` | string | no | `"Imported/Obsidian"` | Vault-relative POSIX subfolder for imports; rejected if it traverses the vault, is absolute, or lands inside `Vault Files/` |
| `dry_run` | bool | no | `true` | When true, no files are written; the response shows the plan |
| `overwrite` | bool | no | `false` | When true, existing destination notes are replaced atomically |

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "vault": "demo-vault",
    "source_dir": "C:/Users/Zach/Documents/My Obsidian Vault",
    "destination": "Imported/Obsidian",
    "dry_run": true,
    "overwrite": false,
    "source_type": "obsidian-vault",
    "summary": {
      "discovered": 12,
      "planned": 12,
      "written": 0,
      "skipped": 0,
      "errors": 0,
      "warnings": 8,
      "wikilinks": 27,
      "embeds": 3,
      "attachment_refs": 5
    },
    "items": [
      {
        "source_path": "C:/Users/Zach/Documents/My Obsidian Vault/Networking.md",
        "destination_path": "Imported/Obsidian/Networking.md",
        "action": "create",
        "status": "planned",
        "fields": {"type": "core-concept", "trust_level": "draft", "source_type": "imported"},
        "warnings": [
          "Obsidian wikilinks were preserved verbatim and are not rewritten in this phase.",
          "Attachment references were detected but binary attachments are not imported."
        ],
        "errors": [],
        "security": {"status": "pass", "findings": []},
        "validation": {"status": "pass", "errors": []},
        "obsidian": {
          "wikilinks": ["[[Algorithms|Algo]]", "[[Networking]]"],
          "embeds": ["![[diagram.png]]"],
          "tags": ["networking", "security/labs"],
          "aliases": ["Net notes"],
          "callouts": ["warning"],
          "block_refs": [],
          "attachment_refs": ["diagram.png"],
          "warnings": []
        }
      }
    ]
  }
}
```

`source_type` at the data level is always `"obsidian-vault"` for this endpoint. The `obsidian` block on each item is deterministic: every list is sorted and de-duplicated, tags have their leading `#` stripped, and callout types are lowercased.

**Discovery and skip rules:**
- Only `.md` files are imported.
- `.obsidian/` (and other obvious config / hidden directories such as `.trash/`, `.git/`, `.hg/`, `.svn/`, `node_modules/`, `.vscode/`, `.idea/`, `__pycache__/`) are skipped during discovery.
- Binary attachments (PNG, JPG, JPEG, GIF, WEBP, SVG, PDF, MP3, MP4, MOV, WAV, ZIP, etc.) and `.canvas` files are never imported.
- Obsidian wikilinks (`[[Note]]`, `[[Note|Alias]]`, `[[Note#Heading]]`, `[[Note#^block-id]]`) are preserved verbatim in the body. There is no automatic wikilink rewriting.

**Error codes:**

Returns the same error code set as `POST /import/markdown-folder` (`INVALID_VAULT`, `INVALID_SOURCE`, `UNSAFE_SOURCE`, `UNSAFE_DESTINATION`, `READ_FAILED`, `SOURCE_TOO_LARGE`, `NULL_BYTE`, `SECURITY_FAIL`, `INVALID_FRONTMATTER`, `FRONTMATTER_NOT_OBJECT`, `DUPLICATE_YAML_KEY`, `SERIALISE_FAILED`, `VALIDATION_FAILED`, `DESTINATION_EXISTS`, `WRITE_FAILED`, `READ_ONLY`, `IMPORT_FAILED`). Phase 26E adds no new top-level error codes; Obsidian-specific advisories are surfaced as item `warnings` only.

Phase 26E does not add PDF, GitHub repo, browser article, chat transcript, semantic mapping, or LLM-extraction imports; those remain deferred. There is no automatic trust promotion: imported Obsidian notes still land as `trust_level: draft` and `source_type: imported`.

---

### GET /stats

Aggregate distinct values for a field across a vault.

**Query parameters:**
- `vault` (required) - vault name.
- `field` (required) - field to aggregate.

**Response data:** `field`, `stats` (mapping of value → count, ordered by frequency).

**Error codes:**
- `INVALID_FIELD` - field not known to vault schema (HTTP 400).

---

## Analysis Endpoints

### GET /validation

Run vault validation and return structured results.

**Query parameters:**
- `vault` (optional)

**Response data:**
- `status` - `"pass"` or `"fail"`.
- `invalid_count` - number of notes that failed.
- `invalid_notes` - sorted list of vault-relative paths of invalid notes.

---

### GET /tasks

Return prioritised upgrade tasks.

**Query parameters:**
- `vault` (optional)
- `limit` (int, default `10`) - max tasks to return.
- `min_priority` (float, optional) - minimum priority threshold.
- `include_feedback` (bool, default `false`) - adjust scores by feedback signals.

**Response data:**
- `total` - total tasks available.
- `tasks` - normalised task objects.

**Each task:**
- `note` - note stem name.
- `path` - vault-relative POSIX path.
- `priority` - computed priority score.
- `type` - always `"missing_section"`.
- `target` - primary missing section.
- `missing` - all missing sections.
- `instruction` - human-readable action.
- `constraints` - writing constraints for the primary issue.
- `feedback_weight` - score delta and entry summary (only when `include_feedback=true`).

When `include_feedback=true`, response also includes:
- `feedback_status` - `"ok"` or `"error"`.
- `feedback_errors` - structured errors from feedback parser.

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
- `notes` - per-note audit results sorted descending by score.

**Each note entry:** `file`, `score`, `severity`, `issues` (list of `{rule, weight, explanation}`).

---

### GET /missing

Detect missing concepts across expected subdomains.

**Query parameters:**
- `vault` (optional)

**Response data:**
- `total_expected`, `total_actual`, `total_missing`, `domains_assessed`, `subdomains`.
- `gaps` - mapping of subdomain → list of missing concept objects.
- `ranked` - all missing concepts ranked by score.

**Note:** Returns `MISSING_CONCEPTS_EMPTY` (HTTP 422) if `EXPECTED_CONCEPTS` is not defined or empty in `vault_schema.py`. The demo vault defines `EXPECTED_CONCEPTS` with example gap data for the Fundamentals domain.

---

### GET /gaps

Return high-priority incomplete notes (priority >= 2).

**Response data:** `gaps` - list of `{note, priority, missing}`, sorted descending by priority.

---

### GET /feedback

Return vault feedback entries from `Vault Files/feedback.md`.

**Query parameters:**
- `vault` (optional)

**Response data:**
- `status` - `"ok"` or `"error"`.
- `vault` - resolved vault name.
- `entries` - validated feedback entries.
- `warnings` - non-fatal issues (e.g. feedback for a missing note path).
- `errors` - structured validation errors (empty when `status="ok"`).

**Each feedback entry:** `path`, `source`, `signal`, `severity`, `comment`, `created_at`. After Phase 14A normalisation, entries also include `id`.

**Error codes:**
- `FEEDBACK_ERROR` - feedback file is malformed (HTTP 500).

---

### POST /feedback

Add a new feedback entry to the vault's `Vault Files/feedback.md`.

**Request body:**
```json
{
  "vault": "demo-vault",
  "path": "Fundamentals/Algorithms.md",
  "source": "human",
  "signal": "unclear",
  "severity": "medium",
  "comment": "How It Works needs a clearer explanation."
}
```

| Field | Type | Required | Valid values |
|-------|------|----------|--------------|
| `vault` | string | yes | registered vault name |
| `path` | string | yes | vault-relative POSIX path to an existing note |
| `source` | string | yes | `human`, `agent`, `system` |
| `signal` | string | yes | `unclear`, `incomplete`, `outdated`, `incorrect`, `useful`, `agent_failed`, `agent_succeeded`, `needs_example`, `needs_constraints` |
| `severity` | string | yes | `low`, `medium`, `high`, `critical` |
| `comment` | string | yes | non-blank, max 2000 chars, no control characters |

Server generates `id` (12–16 lowercase hex) and `created_at` (UTC ISO-8601).

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "entry": {"id": "a1b2c3d4e5f6", "path": "...", "source": "human", "signal": "unclear", "severity": "medium", "comment": "...", "created_at": "2026-05-05T12:00:00Z"},
    "feedback": {"status": "ok", "entries": [...], "warnings": [], "errors": []}
  }
}
```

**Error codes:**
- `INVALID_VAULT` - vault not registered (HTTP 404).
- `INVALID_INPUT` - field validation failed (HTTP 400).
- `PATH_TRAVERSAL` - path escapes vault root (HTTP 400).
- `NOTE_NOT_FOUND` - note does not exist in vault (HTTP 404).
- `FEEDBACK_WRITE_FAILED` - file write error (HTTP 500).

---

### PUT /feedback/{feedback_id}

Update an existing feedback entry by id. Preserves `created_at`. Does not change `id`.

**Path parameter:** `feedback_id` - 12–16 lowercase hex characters.

**Request body:** Same fields as `POST /feedback` (all required, `vault` included).

**Success response (HTTP 200):** Same shape as `POST /feedback` response.

**Error codes:**
- `INVALID_INPUT` - `feedback_id` format invalid or field validation failed (HTTP 400).
- `INVALID_VAULT` - vault not registered (HTTP 404).
- `PATH_TRAVERSAL` - path escapes vault root (HTTP 400).
- `NOTE_NOT_FOUND` - note does not exist in vault (HTTP 404).
- `FEEDBACK_NOT_FOUND` - id not found in feedback file (HTTP 404).
- `FEEDBACK_WRITE_FAILED` - file write error (HTTP 500).

---

### DELETE /feedback/{feedback_id}

Delete a feedback entry by id.

**Path parameter:** `feedback_id` - 12–16 lowercase hex characters.

**Query parameter:** `vault` (required) - vault name.

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "deleted": "a1b2c3d4e5f6",
    "feedback": {"status": "ok", "entries": [...], "warnings": [], "errors": []}
  }
}
```

**Error codes:**
- `INVALID_INPUT` - `feedback_id` format invalid (HTTP 400).
- `INVALID_VAULT` - vault not registered (HTTP 404).
- `FEEDBACK_NOT_FOUND` - id not found in feedback file (HTTP 404).
- `FEEDBACK_WRITE_FAILED` - file write error (HTTP 500).

---

### POST /feedback/normalise

Assign stable IDs to any feedback entries that lack them, and rewrite `feedback.md` atomically. Entries that already carry valid IDs are unchanged.

**Query parameter:** `vault` (required) - vault name.

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "normalised": 3,
    "feedback": {"status": "ok", "entries": [...], "warnings": [], "errors": []}
  }
}
```

**`normalised`** - count of entries that were assigned a new ID in this call.

**Error codes:**
- `INVALID_VAULT` - vault not registered (HTTP 404).
- `FEEDBACK_WRITE_FAILED` - file write error (HTTP 500).

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
- `INVALID_INPUT` - `before` is blank (HTTP 400).
- `COMPARE_FAILED` - report file not found or comparison error (HTTP 500).

---

## Graph Endpoints

All graph endpoints derive relationships from schema-defined hierarchy (domain / subdomain / topic) and frontmatter fields. No LLMs, no embeddings.

### GET /graph

Return full vault relationship graph.

**Query parameters:**
- `vault` (optional)

**Response data:**
- `nodes` - all graph nodes, sorted ascending by id. Each: `id`, `type`, `label`.
- `edges` - all graph edges, sorted ascending by (from, to, type). Each: `from`, `to`, `type`.

Node types: `note`, `domain`, `subdomain`, `topic`, `expected_concept`.
Edge types: `parent`, `same_domain`, `same_subdomain`, `same_topic`, `expected_coverage`.

---

### GET /graph/neighbors

Return all nodes directly connected to a given node (both edge directions).

**Query parameters:**
- `node` (required) - node id to query (e.g. `note::Fundamentals/Algorithms.md`).
- `vault` (optional)

**Response data:** `node_id`, `found`, `neighbors` (list sorted ascending by id).

Each neighbor: `id`, `type`, `label`, `edge_type` (the type of the connecting edge).

---

### GET /graph/related

Return notes related to a node via shared group hubs.

**Query parameters:**
- `node` (required) - node id to query.
- `vault` (optional)
- `min_strength` (string, default `"domain"`) - minimum relationship strength: `topic` | `subdomain` | `domain`.

**Response data:** `node_id`, `found`, `related` (list sorted by strength desc, then id asc).

Each related entry: `id`, `type`, `label`, `via` (strongest shared group node), `strength`.

---

### GET /graph/missing

Return expected concepts missing near a node's group hubs.

**Query parameters:**
- `node` (required) - node id to query.
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
- `node_id` (required) - node id to query.
- `min_strength` (optional, default `"domain"`)

---

### GET /graph/{vault}/missing

Same as `GET /graph/missing?node={node_id}&vault={vault}`.

**Query parameters:**
- `node_id` (required) - node id to query.

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
- `INVALID_VAULT` - vault not registered (HTTP 404).
- `INVALID_FILTER` - unknown filter field (HTTP 400).
- `VALIDATION_ERROR` - `max_notes` or `max_chars` out of range (HTTP 422).
- `BUNDLE_FAILED` - unexpected error (HTTP 500).

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
    "context.html":          {"sha256": "...", "bytes": 9876},
    "manifest.json":         {"sha256": "...", "bytes": 890},
    "validation.json":       {"sha256": "...", "bytes": 234},
    "graph.json":            {"sha256": "...", "bytes": 56},
    "feedback-summary.json": {"sha256": "...", "bytes": 78}
  },
  "warnings": []
}
```

**Error codes:**
- `INVALID_VAULT` - vault not registered (HTTP 404).
- `INVALID_FILTER` - unknown filter field (HTTP 400).
- `PACKAGE_EXISTS` - package exists and `overwrite=false` (HTTP 409).
- `SECURITY_SCAN_FAIL` - scan status is `fail` and `require_security_pass=true` (HTTP 400).
- `BUNDLE_FAILED` / `EXPORT_FAILED` - unexpected error (HTTP 500).

**Notes:**
- Packages are written to `dist/context-bundles/<bundle_id>/` under the repo root.
- `manifest.json` contains SHA-256 hashes of all six non-manifest files, plus metadata.
- `context.html` is a deterministic static HTML rendering generated from bundle data. It contains no remote scripts or external assets. Markdown vault notes remain the source of truth.
- The `dist/` directory is gitignored.

---

### POST /context/security

Scan vault notes for security issues using deterministic regex rules.

**Default behaviour:** Scans all content notes in the vault (generated/system files under `Vault Files/` are automatically excluded by the vault index). Use `filters`, `max_notes`, and `max_chars` to restrict the scan to a subset.

**Request body:**
```json
{
  "vault": "demo-vault",
  "filters": {},
  "include_sections": ["Key Principles", "How It Works", "Trade-offs"],
  "include_body": true,
  "max_notes": 200,
  "max_chars": 10000000,
  "allow_partial": true
}
```

All fields except `vault` are optional.

| Field | Default | Description |
|-------|---------|-------------|
| `filters` | `{}` | Frontmatter filters (e.g. `{"status":"complete"}`). Empty = no filter (all notes). |
| `max_notes` | `200` | Maximum notes to include (up to 1000). |
| `max_chars` | `10000000` | Maximum total characters (up to 50,000,000). |
| `allow_partial` | `true` | Include notes with `status=partial`. |

**Response:**
```json
{
  "status": "ok",
  "data": {
    "status": "pass",
    "findings": [],
    "summary": {"fail": 0, "warning": 0, "info": 0},
    "scanned": {
      "note_count": 19,
      "source_paths": ["Fundamentals/Algorithms.md", "..."],
      "total_notes": 19,
      "coverage": 100,
      "truncated": false
    }
  }
}
```

**Coverage fields in `scanned`:**
| Field | Description |
|-------|-------------|
| `total_notes` | Total content notes in the vault (before filters/limits). |
| `coverage` | Percentage of vault content notes that were scanned (0–100). |
| `truncated` | `true` if `max_notes` or `max_chars` limits cut the scan short. |

**Scan status levels:**

| Status | Meaning |
|--------|---------|
| `pass` | No findings |
| `warning` | Findings present, none blocking-severity |
| `fail` | Blocking finding detected (private key, API key, bearer token, password pattern) |

**Each finding:** `path`, `severity` (`low`/`medium`/`high`/`critical`), `rule`, `field`, `detail`.

**Error codes:**
- `INVALID_VAULT` - vault not registered (HTTP 404).
- `INVALID_FILTER` - unknown filter field (HTTP 400).
- `SECURITY_SCAN_FAILED` - unexpected error (HTTP 500).

**Important:** This is a rule-based static scanner. It may produce false positives on documentation that describes security concepts. Review findings manually.

---

### GET /context/profiles

List all built-in context profiles and bundle modes.

**No parameters required.**

**Response:**
```json
{
  "status": "ok",
  "data": {
    "profiles": {
      "phone-local-llm": {
        "name": "phone-local-llm",
        "label": "Phone Local LLM",
        "description": "Offline phone with 4-bit quantised model",
        "max_notes": 2,
        "max_chars": 2000,
        "include_body": false,
        "include_related": false,
        "include_sections": ["Key Principles"],
        "allow_partial": false,
        "require_security_scan": false,
        "prefer_complete": true
      },
      "desktop-agent": { "..." : "..." },
      "full-review": { "..." : "..." }
    },
    "modes": {
      "tiny":   { "max_notes": 2,  "max_chars": 2000   },
      "small":  { "max_notes": 5,  "max_chars": 8000   },
      "medium": { "max_notes": 10, "max_chars": 20000  },
      "large":  { "max_notes": 25, "max_chars": 80000  },
      "agent":  { "max_notes": 50, "max_chars": 200000 }
    },
    "defaults": { "mode": "medium", "profile": null }
  }
}
```

Available in private-cloud read-only mode. No authentication required beyond the normal token check.

---

### GET /context/profiles/{profile_name}

Get a single profile or mode definition by name.

**Path parameter:** `profile_name` - profile name (e.g. `phone-local-llm`) or mode name (e.g. `tiny`).

**Response:**
```json
{
  "status": "ok",
  "data": {
    "profile": { "name": "tiny", "max_notes": 2, "max_chars": 2000, "..." : "..." },
    "source": "builtin"
  }
}
```

**Error codes:**
- `INVALID_PROFILE` - name not found (HTTP 404).

---

### Profile / Mode fields in context endpoints (Phase 24)

`POST /context/bundle`, `POST /context/export`, and `POST /context/security` all accept two new optional fields:

| Field | Type | Description |
|-------|------|-------------|
| `profile` | string \| null | Apply a device profile by name (e.g. `phone-local-llm`). Profile takes precedence over `mode`. |
| `mode` | string \| null | Apply a bundle mode by name: `tiny` / `small` / `medium` / `large` / `agent`. |

**Resolution order:**
1. If `profile` is set and valid, its settings are used as defaults.
2. Else if `mode` is set and valid, its settings are used as defaults.
3. Explicit request fields (e.g. `max_notes`, `max_chars`) always override profile/mode defaults.
4. Hard caps are enforced regardless: `max_notes ≤ 100`, `max_chars ≤ 500,000`.

**`profile_metadata` in responses:**

When a profile or mode is used, the response includes a `profile_metadata` object:
```json
{
  "profile_metadata": {
    "profile_used": "phone-local-llm",
    "mode_used": null,
    "profile_source": "builtin",
    "effective_budget": { "max_notes": 2, "max_chars": 2000 },
    "require_security_scan": false
  }
}
```

For `/context/export`: if the resolved profile has `require_security_scan: true`, the export enforces `require_security_pass: true` (the export is aborted if the security scan fails). For `/context/bundle`: a warning is added to the response instead.

---

## Phase 25: Trust, Staleness, and Evidence Endpoints

### GET /trust

Return a vault-level trust/confidence/staleness summary. All fields reflect user-provided frontmatter metadata - they do **not** verify factual correctness.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vault` | string | Yes | Registered vault name |

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `vault` | string | Vault name |
| `total_notes` | integer | Total note count |
| `by_trust_level` | object | Count by trust_level value |
| `by_source_type` | object | Count by source_type value |
| `by_confidence` | object | Count by computed confidence level |
| `missing_trust_metadata` | integer | Notes with no trust_level set |
| `deprecated_count` | integer | Notes with trust_level=deprecated |
| `stale_count` | integer | Notes past their review_after date |
| `notes` | array | Per-note trust summary objects |

**Error codes:** `INVALID_VAULT` (404), `TRUST_ERROR` (500)

---

### GET /stale

Return a staleness breakdown for all notes in a vault.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vault` | string | Yes | Registered vault name |

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `vault` | string | Vault name |
| `total_notes` | integer | Total note count |
| `stale` | array | Notes where review_after < today |
| `freshness_unknown` | array | Notes with no review_after set |
| `review_unknown` | array | Notes with no last_reviewed set |
| `deprecated` | array | Notes with trust_level=deprecated |

**Error codes:** `INVALID_VAULT` (404), `STALE_ERROR` (500)

---

### POST /evidence

Build a trust-ranked evidence response with source note paths, section excerpts, and confidence metadata. Use this to generate cite-able responses from vault notes.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | Yes | Registered vault name |
| `filters` | object | No | Frontmatter filter key/value map |
| `q` | string | No | Lexical query string |
| `include_sections` | array | No | Section names to include in excerpts |
| `max_notes` | integer | No | Max notes to return (1–100, default 20) |
| `prefer_verified` | boolean | No | Sort verified notes first (default true) |
| `include_deprecated` | boolean | No | Include deprecated notes (default false) |
| `include_stale` | boolean | No | Include stale notes (default true) |

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `vault` | string | Vault name |
| `query` | string\|null | Echo of `q` if provided |
| `evidence` | array | Trust-ranked evidence note objects |
| `summary` | object | Counts by confidence, excluded counts |
| `confidence_disclaimer` | string | Standard disclaimer text |

Each evidence note includes: `evidence_id`, `path`, `title`, `trust_level`, `source_type`, `last_reviewed`, `review_after`, `confidence`, `trust_score`, `stale`, `sections`, `body_excerpt`.

**Confidence disclaimer:** Confidence levels reflect note maintenance status based on user-provided metadata. They do **not** indicate factual correctness.

**Error codes:** `INVALID_VAULT` (404), `EVIDENCE_ERROR` (500)

---

### GET /context/state

Return a deterministic snapshot of the current vault state, aggregated from all services. This endpoint is read-only and makes no changes to the vault.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vault` | string | Yes | Registered vault name |

**Response:**
```json
{
  "status": "ok",
  "data": {
    "vault": "demo-vault",
    "state": {
      "summary": {
        "validation_status": "pass",
        "security_status": "pass",
        "total_tasks": 3,
        "total_missing": 2,
        "feedback_entry_count": 1,
        "graph_node_count": 19
      },
      "validation": { "...": "..." },
      "security": { "...": "..." },
      "tasks": { "...": "..." },
      "missing": { "...": "..." },
      "feedback": { "...": "..." },
      "graph": { "...": "..." }
    },
    "readiness": {
      "valid": true,
      "security_passed": true,
      "has_tasks": true,
      "has_missing_concepts": false,
      "has_feedback_warnings": false,
      "ready_to_export": true,
      "ready_for_agent_context": true
    },
    "blockers": [],
    "warnings": ["3 pending tasks"]
  }
}
```

**Readiness flags:**

| Flag | Description |
|------|-------------|
| `valid` | Vault passed the last validation run |
| `security_passed` | Security scan status is `pass` or `warning` |
| `has_tasks` | There is at least one pending/in-progress task |
| `has_missing_concepts` | At least one expected concept is missing a note |
| `has_feedback_warnings` | Feedback file has at least one entry |
| `ready_to_export` | `valid` and `security_passed` - safe to call `/context/export` |
| `ready_for_agent_context` | `valid` and `security_passed` - safe to use as LLM context |

**Error codes:**
- `INVALID_VAULT` - vault not registered (HTTP 404).

---

### POST /context/plan

Build a prioritised recommendation plan for a specific intent. All recommendations are derived deterministically from the current vault state - no LLM is involved.

**Request body:**
```json
{
  "vault": "demo-vault",
  "intent": "review"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `vault` | string | - | Registered vault name |
| `intent` | string | `"review"` | Planning intent (see table below) |

**Valid intent values:**

| Intent | Description |
|--------|-------------|
| `review` | General vault health and completeness |
| `export` | Readiness for context bundle export |
| `agent-context` | Readiness for use as LLM agent context |
| `quality` | Content quality and coverage gaps |
| `security` | Security findings and risks |

**Response:**
```json
{
  "status": "ok",
  "data": {
    "vault": "demo-vault",
    "intent": "review",
    "readiness": { "...": true },
    "recommendations": [
      {
        "rank": 1,
        "action": "fix_validation",
        "severity": "critical",
        "title": "Fix validation errors",
        "reason": "Vault has validation errors that block export and agent use.",
        "source": "validation",
        "links": {
          "ui": "/app/validation",
          "api": "/validate"
        }
      }
    ],
    "blockers": [],
    "warnings": ["3 pending tasks"],
    "next_best_action": {
      "action": "fix_validation",
      "title": "Fix validation errors"
    }
  }
}
```

`next_best_action` is the first (rank-1) recommendation, or `null` if there are no recommendations.

**Error codes:**
- `INVALID_VAULT` - vault not registered (HTTP 404).
- `INVALID_INTENT` - `intent` is not one of the five valid values (HTTP 400).

---

## Local Web UI

### GET /app

### GET /app/{ui_path:path}

Serve the compiled local web UI static files from `ui/dist/`.

- **`GET /app`** - serves `ui/dist/index.html`.
- **`GET /app/{ui_path:path}`** - serves the requested static asset from `ui/dist/`. If the exact path is not found, serves `index.html` (SPA fallback).
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
# ui/dist/ is now ready - served at GET /app
```

All existing API routes (`/health`, `/vaults`, `/summary`, etc.) remain fully functional whether or not `ui/dist/` is present.

---

## Vault Management

### POST /vault/bootstrap

Create a new vault from a structured request.  This is the backend foundation
for guided vault creation (Phase 11A).  The CLI `py run.py bootstrap` flow
remains supported and is unaffected.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault_name` | string | yes | New vault directory name. Pattern: `^[A-Za-z0-9_-]+$`. Must not already exist. |
| `domain` | string | yes | Primary domain display name (e.g. `"Dogs"`). |
| `note_type` | string | yes | Note type slug (e.g. `"breed-profile"`). Pattern: `^[a-z0-9]+(?:-[a-z0-9]+)*$`. |
| `sections` | list[string] | yes | Canonical section names (minimum 2, no duplicates). |
| `expected_concepts` | list[string] | no | Optional expected concept names. Each entry is normalised to a lowercase slug and written into `EXPECTED_CONCEPTS` in the generated `vault_schema.py`. `GET /missing` works immediately after bootstrap. |

**Expected concepts validation rules:**
- Optional; omit or provide an empty list to skip.
- Each entry: trimmed, non-empty, no control characters.
- Duplicate entries (case-insensitive) are rejected by validation.
- After slug normalisation, duplicate slugs are silently deduplicated.
- Each slug is rendered with `repr()` in the generated file - no Python code injection is possible.

**Example request:**
```json
{
  "vault_name": "dogs-vault",
  "domain": "Dogs",
  "note_type": "breed-profile",
  "sections": ["Overview", "Care Requirements", "Health Risks"],
  "expected_concepts": ["Labrador Retriever", "German Shepherd"]
}
```

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "vault": "dogs-vault",
    "created": [
      "dogs-vault/Vault Files/Scripts/vault_schema.py",
      "dogs-vault/Vault Files/Templates/breed-profile.md"
    ],
    "warnings": [],
    "expected_concepts": {
      "requested": 2,
      "written": 2
    }
  }
}
```

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_INPUT` | 422 | One or more fields fail domain validation |
| `VAULT_EXISTS` | 409 | A vault with `vault_name` already exists |
| `PATH_TRAVERSAL` | 400 | `vault_name` resolves outside the repository root |
| `BOOTSTRAP_FAILED` | 500 | Vault creation or template generation error |
| `CONFIG_UPDATE_FAILED` | 500 | Config write failed (vault rolled back where safe) |

**Security rules:**
- `vault_name` must match `^[A-Za-z0-9_-]+$` - no path separators, no `..`
- Resolved vault path must remain within the repository root
- No overwrite of existing directories
- `config/config.yaml` is updated atomically (temp-file + replace)

**Registry behaviour:**  
The in-process vault registry is refreshed automatically after a successful bootstrap so the new vault is immediately queryable without a server restart.

---

### DELETE /vault/{vault_name}

Permanently delete a non-demo vault. Requires explicit typed confirmation. Removes all vault files from disk, updates `config/config.yaml`, and clears in-process caches.

**Path parameter:**
- `vault_name` - registered vault name to delete.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `confirm` | string | yes | Exact phrase `"DELETE {vault_name}"` - case-sensitive, no extra whitespace. |

**Example request:**
```json
{"confirm": "DELETE dogs-vault"}
```

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "deleted": "dogs-vault",
    "remaining_vaults": ["demo-vault"],
    "active_vault": "demo-vault"
  }
}
```

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `CONFIRMATION_REQUIRED` | 400 | `confirm` field is blank or whitespace |
| `CONFIRMATION_MISMATCH` | 400 | `confirm` does not match `"DELETE {vault_name}"` exactly |
| `INVALID_VAULT` | 404 | `vault_name` is not registered |
| `PROTECTED_VAULT` | 403 | Attempted deletion of `demo-vault` |
| `LAST_VAULT` | 409 | Deleting would leave zero vaults |
| `PATH_TRAVERSAL` | 400 | Resolved vault path is outside the repository root |
| `DELETE_FAILED` | 500 | `shutil.rmtree` failed (filesystem error) |
| `CONFIG_UPDATE_FAILED` | 500 | Config write failed after directory was already deleted |

**Safety design:**
- Vault path is resolved only from the registry - never from user-supplied paths.
- `demo-vault` is permanently protected and cannot be deleted via the API.
- The last remaining vault cannot be deleted.
- Directory is deleted first; config is updated only after successful deletion. If config write fails after deletion, the error code `CONFIG_UPDATE_FAILED` is returned with the fallback vault in `active_vault`.
- After a successful delete, `vault_registry.reload_config()`, `clear_vault_index()`, and `clear_vault_cache()` are called to evict stale data.

---

## Session and Project State (Phase 22)

File-backed session and project state layer. All state is stored as pretty-printed, sorted-key JSON inside `<vault>/Vault Files/State/`. Writes are atomic (temp-file + replace). No database, no cloud sync, no embeddings.

Write endpoints are blocked when `CVE_REMOTE_READ_ONLY=true`.

### POST /session/start

Start a new work session.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `current_project` | string | no | Project name for this session |
| `current_topic` | string | no | Topic being worked on |
| `user_goal` | string | no | Freeform goal description |
| `active_vault` | string | no | Active vault name (defaults to `vault`) |

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "session": {
      "session_id": "20240115T143022-a1b2c3d4",
      "status": "active",
      "active_vault": "demo-vault",
      "current_project": "Phase 22",
      "current_topic": "Testing",
      "user_goal": "Verify session state",
      "recent_notes": [],
      "created_at": "2024-01-15T14:30:22Z",
      "last_activity": "2024-01-15T14:30:22Z"
    }
  }
}
```

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `REMOTE_READ_ONLY` | 403 | `CVE_REMOTE_READ_ONLY=true` |
| `WRITE_FAILED` | 500 | Atomic file write failed |

---

### GET /session/resume

Fetch the most-recent active session. Optionally specify a session_id to resume a specific session.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `session_id` | string | no | Specific session ID to resume |

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "session": { "session_id": "...", "status": "active", ... }
  }
}
```

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `SESSION_NOT_FOUND` | 404 | No active session found (or specified ID not found) |

---

### GET /session/summary

Return a compact LLM-ready summary of the most-recent active session.

**Query parameters:** same as `/session/resume`

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "summary": {
      "session_id": "...",
      "status": "active",
      "current_project": "...",
      "user_goal": "...",
      "recent_notes": [...],
      "created_at": "...",
      "last_activity": "..."
    }
  }
}
```

---

### POST /session/attach-note

Record a recently-accessed note in the current session. De-duplicates; most-recent entry moves to the front.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `session_id` | string | yes | Session ID to attach the note to |
| `note_path` | string | yes | Vault-relative path to the note (e.g. `Fundamentals/Algorithms.md`) |

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `SESSION_NOT_FOUND` | 404 | Session ID not found |
| `INVALID_SESSION` | 400 | Session is closed |
| `INVALID_NOTE_PATH` | 400 | Path contains `..` or is absolute |
| `NOTE_NOT_FOUND` | 404 | Note file does not exist in vault |
| `REMOTE_READ_ONLY` | 403 | `CVE_REMOTE_READ_ONLY=true` |

---

### POST /session/close

Close an active session. The session file is preserved with `status: closed` and `closed_at` timestamp.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `session_id` | string | yes | Session ID to close |

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `SESSION_NOT_FOUND` | 404 | Session ID not found |
| `REMOTE_READ_ONLY` | 403 | `CVE_REMOTE_READ_ONLY=true` |

---

### GET /project/state

Read the current project state. Returns default values if no state file exists.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "project_state": {
      "vault": "demo-vault",
      "current_phase": "",
      "completed_work": [],
      "next_actions": [],
      "blockers": [],
      "decisions": [],
      "risks": [],
      "updated_at": "2024-01-15T14:30:22Z"
    }
  }
}
```

---

### PUT /project/state

Update one or more project state fields. Only the following fields may be updated: `current_phase`, `completed_work`, `next_actions`, `blockers`, `decisions`, `risks`.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `updates` | object | yes | Map of allowed field names to new values |

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `INVALID_PROJECT_STATE` | 400 | `updates` contains unknown or forbidden fields |
| `REMOTE_READ_ONLY` | 403 | `CVE_REMOTE_READ_ONLY=true` |
| `WRITE_FAILED` | 500 | Atomic file write failed |

---

## Safe Memory Write Queue (Phase 23)

File-backed pending change queue for LLM-proposed note modifications. All proposals are stored as JSON objects for human review - **nothing is written to vault notes until explicitly accepted**. Writes are atomic (temp-file + replace). Accepted/rejected changes are archived for audit.

Write endpoints are blocked when `CVE_REMOTE_READ_ONLY=true`.

### GET /memory/pending

List pending change proposals.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `status` | string | no | Filter: `pending` (default), `accepted`, `rejected`, `all` |
| `limit` | integer | no | Max results (default 50) |

**Success response (HTTP 200):**
```json
{
  "status": "ok",
  "data": {
    "vault": "demo-vault",
    "status": "pending",
    "count": 1,
    "changes": [
      {
        "id": "20260511T120000-a1b2c3d4",
        "type": "suggest_note_update",
        "vault": "demo-vault",
        "path": "Fundamentals/Algorithms.md",
        "section": null,
        "status": "pending",
        "validation_status": "pass",
        "reason": "Add missing complexity section",
        "source": "agent",
        "created_at": "2026-05-11T12:00:00Z"
      }
    ]
  }
}
```

---

### POST /memory/create-note-draft

Propose creating a new vault note. Validates that the target path does not already exist.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `path` | string | yes | Target note path (relative to vault root) |
| `fields` | object | yes | YAML frontmatter fields |
| `body` | string | yes | Note body (Markdown) |
| `reason` | string | no | Why this change is proposed |
| `source` | string | no | Who proposed it (default: `agent`) |
| `session_id` | string | no | Associated session ID |
| `project` | string | no | Project name |

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `INVALID_NOTE_PATH` | 400 | Path contains `..`, is absolute, or is inside `Vault Files/` |
| `NOTE_EXISTS` | 409 | A note at that path already exists |
| `REMOTE_READ_ONLY` | 403 | `CVE_REMOTE_READ_ONLY=true` |

---

### POST /memory/suggest-note-update

Propose an update to an existing vault note. Merges provided fields with the original; replaces body if provided.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `path` | string | yes | Existing note path |
| `fields` | object | no | Fields to merge (override originals) |
| `body` | string | no | New body (replaces original) |
| `reason` | string | no | Why this change is proposed |
| `source` | string | no | Who proposed it |
| `session_id` | string | no | Associated session ID |
| `project` | string | no | Project name |

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `INVALID_NOTE_PATH` | 400 | Path safety violation |
| `NOTE_NOT_FOUND` | 404 | Source note does not exist |
| `REMOTE_READ_ONLY` | 403 | `CVE_REMOTE_READ_ONLY=true` |

---

### POST /memory/update-section-draft

Propose replacing one Markdown section (`## Heading`) in an existing vault note. All other content is preserved.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `path` | string | yes | Existing note path |
| `section` | string | yes | Exact section heading (without `## `) |
| `proposed_content` | string | yes | New section body (without the heading line) |
| `reason` | string | no | Why this change is proposed |
| `source` | string | no | Who proposed it |

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `NOTE_NOT_FOUND` | 404 | Source note does not exist |
| `VALIDATION_FAILED` | 422 | Section heading not found in note |
| `REMOTE_READ_ONLY` | 403 | `CVE_REMOTE_READ_ONLY=true` |

---

### GET /memory/pending/{change_id}

Get the full detail of a single pending change (active or archived).

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `PENDING_CHANGE_NOT_FOUND` | 404 | Change ID not found |

---

### POST /memory/pending/{change_id}/accept

Accept a pending change and apply it to the vault. Re-validates the proposal; checks staleness; calls safe note-write path. Change is archived after application.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `reviewer` | string | no | Name of reviewer |
| `audit_note` | string | no | Reason for decision |

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `PENDING_CHANGE_NOT_FOUND` | 404 | Change ID not found |
| `INVALID_PENDING_CHANGE` | 400 | Change status is not `pending` |
| `VALIDATION_FAILED` | 422 | Schema validation fails at accept time |
| `STALE_PENDING_CHANGE` | 409 | Source note was modified after proposal |
| `REMOTE_READ_ONLY` | 403 | `CVE_REMOTE_READ_ONLY=true` |
| `WRITE_FAILED` | 500 | Note write or archive write failed |

---

### POST /memory/pending/{change_id}/reject

Reject a pending change and archive it. Never deletes; always preserves for audit.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault` | string | yes | Registered vault name |
| `reviewer` | string | no | Name of reviewer |
| `audit_note` | string | no | Reason for rejection |

**Error responses:**

| Code | HTTP Status | Trigger |
|------|-------------|---------|
| `INVALID_VAULT` | 404 | Vault name is not registered |
| `PENDING_CHANGE_NOT_FOUND` | 404 | Change ID not found |
| `INVALID_PENDING_CHANGE` | 400 | Change status is not `pending` |
| `REMOTE_READ_ONLY` | 403 | `CVE_REMOTE_READ_ONLY=true` |
| `WRITE_FAILED` | 500 | Archive write failed |

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
| `UI_NOT_BUILT` | 503 | `ui/dist/` not present - run `npm run build` in `ui/` |
| `VAULT_EXISTS` | 409 | Vault directory already exists (bootstrap) |
| `BOOTSTRAP_FAILED` | 500 | Vault creation or template generation error (bootstrap) |
| `CONFIG_UPDATE_FAILED` | 500 | Config write failed during bootstrap or vault deletion |
| `FEEDBACK_NOT_FOUND` | 404 | Feedback entry ID not found in feedback file |
| `FEEDBACK_WRITE_FAILED` | 500 | Feedback file write error (atomic write failed) |
| `PROTECTED_VAULT` | 403 | Deletion of demo-vault refused |
| `LAST_VAULT` | 409 | Deletion refused - would leave zero vaults |
| `CONFIRMATION_REQUIRED` | 400 | Delete confirm field is blank |
| `CONFIRMATION_MISMATCH` | 400 | Delete confirm phrase does not match exactly |
| `DELETE_FAILED` | 500 | Vault directory deletion failed (filesystem error) |
| `INTERNAL` | 500 | Unexpected server error |
| `INVALID_SESSION` | 400 | Session is closed and cannot be modified |
| `SESSION_NOT_FOUND` | 404 | Session ID not found or no active sessions |
| `INVALID_NOTE_PATH` | 400 | Note path contains `..` or is absolute |
| `NOTE_NOT_FOUND` | 404 | Note file does not exist in vault |
| `NOTE_EXISTS` | 409 | Note file already exists (create_note_draft target) |
| `INVALID_PROJECT_STATE` | 400 | Project state update contains unknown or forbidden fields |
| `WRITE_FAILED` | 500 | Atomic session/project-state file write failed |
| `INVALID_PENDING_CHANGE` | 400 | Pending change JSON is malformed |
| `PENDING_CHANGE_NOT_FOUND` | 404 | Change ID not found in pending or archive |
| `VALIDATION_FAILED` | 422 | Schema validation failed for proposed note content |
| `STALE_PENDING_CHANGE` | 409 | Source note was modified after proposal; re-propose |

---

## MCP Compatibility Layer (Phase 20)

Context Vault Engine also exposes its vault capabilities as a **read-only MCP stdio server**. This is separate from the HTTP REST API above.

### Transport

JSON-RPC 2.0 over stdin/stdout (newline-delimited). One request per line, one response per line. Log output goes to stderr.

```bash
py run.py mcp
```

### Protocol version

`2025-11-25`

### Supported methods

| Method | Description |
|--------|-------------|
| `initialize` | Handshake - returns `protocolVersion`, `serverInfo`, `capabilities` |
| `notifications/initialized` | Client notification - no response |
| `ping` | Liveness check - returns `{}` |
| `tools/list` | List all 10 CVE tools |
| `tools/call` | Call a named CVE tool |
| `resources/list` | List all resource URIs |
| `resources/read` | Read a resource by URI |
| `prompts/list` | List all 4 CVE prompts |
| `prompts/get` | Get a rendered prompt |

### JSON-RPC error codes

| Code | Meaning |
|------|---------|
| `-32700` | Parse error (invalid JSON) |
| `-32600` | Invalid request |
| `-32601` | Method not found |
| `-32602` | Invalid params (e.g. unknown prompt name) |
| `-32603` | Internal error |

### Safety

All MCP tools and prompts are **read-only**. No tool can create, edit, or delete notes, feedback entries, or export packages. Vault names in resource URIs are validated against the registry - path traversal attempts return `INVALID_VAULT` errors.
