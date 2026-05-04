# Quickstart

> On Windows, use `py run.py ...` (the Python launcher).  
> On macOS/Linux, use `python3 run.py ...` if `python` is not available.

## 1. Clone

```bash
git clone <repo-url> knowledge-system
cd knowledge-system
pip install -r requirements.txt
```

---

## 2. Create a Custom Vault (Recommended)

```bash
py run.py bootstrap
```

You will be prompted for:

- domain name (e.g. `Dogs`)
- note type slug (e.g. `breed-profile`)
- canonical sections (comma-separated, minimum 2)

This generates:

- a fully valid vault under `<domain-slug>-vault/`
- a domain-specific `vault_schema.py`
- matching canonical templates
- updated `config/config.yaml`

After this, the system is ready:

```bash
py run.py validate
```

---

## 3. Initialise Demo Vault (Optional)

```bash
py run.py init my-vault
```

This copies the predefined demo schema (19 core-concept notes, `fundamentals` domain). Use this to explore the system with an existing dataset. For a clean start with your own domain, use `bootstrap` instead.

---

## 4. Generate Templates (Optional but Recommended)

```bash
py run.py templates
```

Templates are derived from the schema and ensure structural consistency.

---

## 5. Run the Pipeline

```bash
py run.py validate
py run.py analyse
py run.py improve
py run.py report
```

---

## 5b. Generate a Context Bundle (Phase 2)

```bash
py run.py bundle
```

Prints a JSON context bundle to stdout. The bundle packages selected notes with metadata, section extracts, validation state, and budget information.

**Output shape:**
```json
{
  "status": "ok",
  "bundle_id": "a1b2c3d4e5f6a7b8",
  "vault": "demo-vault",
  "filters": {"status": "complete"},
  "created_at": "2026-05-04T12:00:00+00:00",
  "validation_status": "pass",
  "notes": [...],
  "graph": {"related": {}},
  "budget": {"max_chars": 20000, "used_chars": 8500, "note_count": 5, "truncated": false},
  "warnings": [],
  "manifest": {"source_paths": [...], "schema_version": null}
}
```

**Defaults:** selects `status=complete` notes (falls back to all notes with a warning if none exist), extracts `Key Principles`, `How It Works`, `Trade-offs` sections, max 10 notes, 20 000-char budget.

`max_notes` caps the candidate pool first; `max_chars` then stops adding notes once the character budget is exhausted. `budget.truncated` is `true` only when notes were excluded by the character budget (not by `max_notes`). A `warnings` entry names the first note that was excluded by budget.

---

## 5c. Feedback Loop (Phase 3)

**View vault feedback:**
```bash
py run.py feedback
```

Prints the contents of `Vault Files/feedback.md` as structured JSON. Exits 0 if valid, exits 1 if the feedback file has errors.

**Output shape:**
```json
{
  "status": "ok",
  "vault": "demo-vault",
  "entries": [
    {
      "path": "Fundamentals/Algorithms.md",
      "source": "human",
      "signal": "unclear",
      "severity": "medium",
      "comment": "The How It Works section needs a clearer description.",
      "created_at": "2026-05-04T12:00:00Z"
    }
  ],
  "warnings": [],
  "errors": []
}
```

**Add feedback** by editing `demo-vault/Vault Files/feedback.md` directly. Valid signals:
- Negative (raise priority): `unclear`, `incomplete`, `outdated`, `incorrect`, `agent_failed`, `needs_example`, `needs_constraints`
- Positive (lower priority): `useful`, `agent_succeeded`

Valid sources: `human`, `agent`, `system`. Valid severities: `low`, `medium`, `high`, `critical`.

**Get tasks with feedback-adjusted priorities:**
```bash
GET /tasks?vault=demo-vault&include_feedback=true
```

Each task gains a `feedback_weight` field showing the score delta and contributing entries. The response includes `feedback_status` and `feedback_errors`.

**Important:** feedback never modifies notes. It only adjusts which notes the task engine recommends working on next.

---

## 5d. Export Context Package (Phase 4)

**Export the default bundle to disk:**
```bash
py run.py export
```

Generates the same default bundle as `run.py bundle` and writes it to `dist/context-bundles/<bundle-id>/`. Prints structured JSON to stdout. Returns exit code 1 if the package already exists (use `--overwrite` to replace it).

```bash
py run.py export --overwrite
```

**Output shape:**
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

**Package files written:**

| File | Purpose |
|------|---------|
| `context.json` | Full bundle JSON |
| `context.md` | Human-readable Markdown rendering |
| `manifest.json` | SHA-256 hashes + metadata for all other files |
| `validation.json` | Validation status and warnings |
| `graph.json` | Graph relationships for selected notes |
| `feedback-summary.json` | Feedback entries relevant to selected notes |

**Overwrite behaviour:**
- Without `--overwrite`: exits 1 with `PACKAGE_EXISTS` error if the package directory already exists.
- With `--overwrite`: removes and recreates the package directory atomically.

**Note:** generated packages are build artefacts. The `dist/` directory is gitignored.

---

## 6. Start API Server (Optional)

Requires the MCP dependencies (fastapi + uvicorn):

```bash
pip install -r mcp/requirements.txt
py mcp/server/mcp_server.py
```

---

## 7. Query the System

**Vault overview**
* http://127.0.0.1:8000/summary
* http://127.0.0.1:8000/vaults

**Validation, tasks, notes, quality, missing** — all accept an optional `?vault=<name>` query parameter:
* http://127.0.0.1:8000/validation
* http://127.0.0.1:8000/validation?vault=demo-vault
* http://127.0.0.1:8000/tasks
* http://127.0.0.1:8000/tasks?limit=5
* http://127.0.0.1:8000/tasks?vault=demo-vault&limit=5&min_priority=2
* http://127.0.0.1:8000/tasks?vault=demo-vault&include_feedback=true
* http://127.0.0.1:8000/notes
* http://127.0.0.1:8000/notes?vault=demo-vault
* http://127.0.0.1:8000/quality
* http://127.0.0.1:8000/missing
* http://127.0.0.1:8000/gaps
* http://127.0.0.1:8000/feedback
* http://127.0.0.1:8000/feedback?vault=demo-vault

**Context bundle** (POST with JSON body):
```json
POST /context/bundle
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
All fields except `vault` are optional — the defaults above apply.

**Context export** (POST with JSON body — same fields as bundle, plus `overwrite`):
```json
POST /context/export
{
  "vault": "demo-vault",
  "filters": {"status": "complete"},
  "overwrite": false
}
```
Writes a portable package to `dist/context-bundles/<bundle-id>/`. Returns `PACKAGE_EXISTS` (HTTP 409) if the package already exists and `overwrite` is false.

**Compare** (POST with JSON body):
```json
POST /compare
{"before": "Vault Files/Vault Report.md"}
```

**Relationship graph** — two forms, both accept a vault name:
* http://127.0.0.1:8000/graph?vault=demo-vault  *(query-param form)*
* http://127.0.0.1:8000/graph/demo-vault  *(path-param form)*
* http://127.0.0.1:8000/graph/demo-vault/related?node_id=note::Fundamentals/Algorithms.md
* http://127.0.0.1:8000/graph/demo-vault/missing?node_id=note::Fundamentals/Algorithms.md

**Query filter rules (POST /query)**
- Only schema-defined fields are accepted. Unknown fields, unsupported operators (e.g. `status__gt`), and `__in` with a non-list value all return `{"status": "error", "error": "INVALID_FILTER", ...}` with zero results.
- Supported operators: `field` (equality), `field__in` (list), `field__contains` (substring).

**Task output format**

Each task from `/tasks` includes:
- `path` — full vault-relative POSIX path (e.g. `Fundamentals/Algorithms.md`)
- `constraints` — writing constraints from the task engine
- `missing` — list of missing section names
- `instruction` — human-readable action

**Missing concepts note**

`/missing` requires `EXPECTED_CONCEPTS` to be defined in `vault_schema.py`. If it is empty or undefined, the endpoint returns a `MISSING_CONCEPTS_EMPTY` error (HTTP 422) rather than a silent success.

**Index freshness**
After editing, adding, or deleting a note file, the next API call automatically reflects the change (within a 2-second cooldown window). No server restart is needed.

---

## 8. Run Verification Tests (Optional)

Core tests (requires only `requirements.txt`):

```bash
py mcp/test_verify.py
```

Tests 11 and 15 (rate limiter, structured logging) import from the MCP server and require the API dependencies:

```bash
pip install -r mcp/requirements.txt
py mcp/test_verify.py
```
