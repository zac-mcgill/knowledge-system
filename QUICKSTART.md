# Context Vault Engine — Quickstart

This guide walks through an end-to-end session with Context Vault Engine: install, validate, analyse, generate a context bundle, export a package, run security scans, and use the API.

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
  "manifest": {"source_paths": [...], "schema_version": "3.0.0"}
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

**Add feedback** by editing `demo-vault/Vault Files/feedback.md` directly, or via the API (Phase 14A). Valid signals:
- Negative (raise priority): `unclear`, `incomplete`, `outdated`, `incorrect`, `agent_failed`, `needs_example`, `needs_constraints`
- Positive (lower priority): `useful`, `agent_succeeded`

Valid sources: `human`, `agent`, `system`. Valid severities: `low`, `medium`, `high`, `critical`.

**Add feedback via API (Phase 14A):**
```bash
POST /feedback
{
  "vault": "demo-vault",
  "path": "Fundamentals/Algorithms.md",
  "source": "human",
  "signal": "unclear",
  "severity": "medium",
  "comment": "How It Works needs a clearer explanation."
}
```

The server generates `id` and `created_at`. Returns the new entry and updated feedback summary.

**Update feedback:** `PUT /feedback/{id}` — provide same fields as POST plus vault. Preserves `created_at`.

**Delete feedback:** `DELETE /feedback/{id}?vault=demo-vault`

**Normalise (assign IDs to existing entries):** `POST /feedback/normalise?vault=demo-vault`

Manual editing of `Vault Files/feedback.md` remains fully supported. Entries without IDs are still readable; IDs are assigned on next write or explicit normalise.

**Get tasks with feedback-adjusted priorities:**
```bash
GET /tasks?vault=demo-vault&include_feedback=true
```

Each task gains a `feedback_weight` field showing the score delta and contributing entries. The response includes `feedback_status` and `feedback_errors`.

**Important:** feedback never modifies notes. It only adjusts which notes the task engine recommends working on next.

---

## 4e. Update a Note via API (Phase 15B)

The backend provides a `PUT /note` endpoint for safe, atomic updates to existing notes. The endpoint validates all fields and body content against the vault schema before writing.

**Update an existing note:**
```bash
curl -X PUT http://127.0.0.1:8000/note \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

On success returns the updated note's `path`, `fields`, `body`, and `validation` (always `{"status": "pass", "errors": []}`). Validation failures return HTTP 400 with `VALIDATION_FAILED` and a `details` list — the file on disk is unchanged.

> **Note:** The note edit UI is not yet implemented. The backend API is complete.

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

## 5e. Security Scan (Phase 5)

Scan the default context bundle for security issues before delivering notes to an agent or LLM.

**CLI:**
```bash
py run.py security
```

Scans the same default bundle as `run.py bundle`. Prints structured JSON to stdout. Exit code 0 for `pass`/`warning`, exit code 1 for `fail` or error.

```bash
py run.py security --fail-on-warning
```
Also exits 1 when status is `warning`.

**Output shape:**
```json
{
  "status": "pass",
  "findings": [],
  "summary": {"fail": 0, "warning": 0, "info": 0},
  "scanned": {
    "note_count": 7,
    "source_paths": [
      "Fundamentals/Algorithms.md",
      "Fundamentals/Data Structures.md"
    ]
  }
}
```

**Status levels:**

| Status | Meaning |
|--------|---------|
| `pass` | No findings |
| `warning` | Findings exist but none are blocking-severity |
| `fail` | Blocking finding detected (private key, cloud API key, bearer token, password) |

**API:**
```json
POST /context/security
{
  "vault": "demo-vault",
  "max_notes": 10
}
```

Full request body fields (all optional except `vault`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `vault` | string | required | Registered vault name |
| `filters` | object | `{}` | Equality filters on frontmatter fields |
| `include_sections` | array | `["Key Principles", "How It Works", "Trade-offs"]` | Section names to scan |
| `include_body` | bool | `true` | Scan full note body |
| `max_notes` | int | `10` | Maximum notes (1–100) |
| `max_chars` | int | `20000` | Character budget |
| `allow_partial` | bool | `false` | Include status=partial notes |

**API response:**
```json
{
  "status": "ok",
  "data": {
    "status": "warning",
    "findings": [
      {
        "path": "Fundamentals/Networking Fundamentals.md",
        "severity": "low",
        "rule": "external-link",
        "field": "body",
        "detail": "https://example.com"
      }
    ],
    "summary": {"fail": 0, "warning": 1, "info": 0},
    "scanned": {"note_count": 7, "source_paths": ["..."]}
  }
}
```

**Export gate:** pass `require_security_pass: true` to `POST /context/export` to abort export when the bundle would fail the security scan:
```json
POST /context/export
{
  "vault": "demo-vault",
  "overwrite": true,
  "require_security_pass": true
}
```
Returns HTTP 400 `SECURITY_SCAN_FAIL` if the scan status is `fail`. Default is `false` (backward-compatible).

---

## 6. Start API Server (Optional)

Requires the MCP dependencies (fastapi + uvicorn):

```bash
pip install -r mcp/requirements.txt
py mcp/server/mcp_server.py
```

---

## 6b. Local Web UI (Phase 10)

A browser dashboard is available for viewing vault status without the CLI.

### Development workflow

```bash
# Terminal 1 — backend (must be running)
pip install -r mcp/requirements.txt
py mcp/server/mcp_server.py

# Terminal 2 — Astro dev server
cd ui
npm install
npm run dev
# Open: http://localhost:4321/app
```

The dev server hot-reloads on UI file changes. API calls go directly to `http://127.0.0.1:8000`. Set `PUBLIC_API_BASE_URL` in `ui/.env` to override.

### Production build

```bash
cd ui
npm install
npm run build
# Output: ui/dist/

# The existing FastAPI server now serves the UI
py mcp/server/mcp_server.py
# Open: http://127.0.0.1:8000/app
```

`GET /app` serves the compiled Astro frontend from `ui/dist`. If `ui/dist` does not exist, it returns `503 UI_NOT_BUILT` with instructions — no other API routes are affected.

**Stack:** Astro 5 · TypeScript · Tailwind CSS 4 · Svelte 5 islands

### Dashboard panels (Phase 12A)

The Dashboard shows a complete vault health overview loaded in parallel from all relevant API endpoints:

| Panel | Source |
|---|---|
| API health (uptime, requests, latency) | `GET /health` |
| Vault coverage (total, complete, partial) | `GET /summary` |
| Validation status + invalid note list | `GET /validation` |
| Top 5 tasks (priority, note, missing sections) | `GET /tasks` |
| Missing expected concepts | `GET /missing` |
| Feedback entries (errors, warnings, info) | `GET /feedback` |
| Vault index info (notes indexed, schema hash) | `GET /health` vaults map |
| Security scan findings | `POST /context/security` |

### Dashboard Issue Review (Phase 12B)

An **Issue Review** section below the overview cards provides tabbed drill-down inspection of all issue categories without leaving the Dashboard:

| Tab | Shows |
|---|---|
| Validation | Status badge, invalid note paths, pass state, raw JSON |
| Tasks | Expandable rows — instruction, missing sections, constraints, feedback weighting, raw task JSON |
| Security | Status, severity counts, full findings table (path/severity/rule/field/detail), pass state, raw JSON |
| Missing Concepts | Expected/present/missing/domains counts, full ranked list with scores, raw JSON |
| Feedback | Entry count, all entries (path/source/signal/severity/comment/created\_at), warnings/errors, raw JSON |

A compact **cross-panel summary row** above the tabs shows issue counts from all categories at a glance. All raw JSON blocks are collapsed by default.

Select a vault from the dropdown to load all panels simultaneously. Click **Refresh** to reload.

---

## 6c. API-based Vault Bootstrap (Phase 11A)

As an alternative to `py run.py bootstrap`, you can create a new vault via the API:

```bash
# Start the server first
py mcp/server/mcp_server.py

# Create a vault via HTTP
curl -X POST http://127.0.0.1:8000/vault/bootstrap \
  -H "Content-Type: application/json" \
  -d '{
    "vault_name": "dogs-vault",
    "domain": "Dogs",
    "note_type": "breed-profile",
    "sections": ["Overview", "Care Requirements", "Health Risks"]
  }'
```

The API bootstrap creates the vault directory, writes `vault_schema.py`, updates `config/config.yaml` atomically, and generates canonical templates. The running server's vault registry is refreshed immediately.

The CLI flow `py run.py bootstrap` is unchanged and remains fully supported.

**Note:** The guided UI form for vault creation is planned for Phase 11B.

---

## 6d. Guided Vault Bootstrap UI (Phase 11B)

A browser-based guided setup form is available in the local web UI.

1. Start the backend server and build the UI (see section 6b above).
2. Open [http://127.0.0.1:8000/app/vault-setup](http://127.0.0.1:8000/app/vault-setup).
3. Fill in:
   - **Vault Name** — slug-style directory name (letters, numbers, underscores, hyphens)
   - **Domain** — human-readable domain label
   - **Note Type** — slug for the primary note type (e.g. `breed-profile`)
   - **Required Sections** — canonical section headings (minimum 2, defaults pre-filled)
   - **Expected Concepts** — optional named concepts (accepted with a backend warning; not yet written to schema)
4. The live validation panel and preview update as you type.
5. Click **Create Vault** to call `POST /vault/bootstrap`.
6. On success the page shows created file paths and any backend warnings.
7. Use **Go to Dashboard** to return to the vault overview.

The CLI flow `py run.py bootstrap` remains unchanged and is still the recommended path for automation.

**Expected concepts limitation:** The backend accepts `expected_concepts` in the request and echoes them in the response warnings, but does not yet write them into `vault_schema.py`. This is a known limitation noted in the UI.

---

## 6e. Bundle Builder UI (Phase 13A)

A browser-based Bundle Builder is available for interactively generating and previewing context bundles.

1. Start the backend server and build the UI (see section 6b above).
2. Open [http://127.0.0.1:8000/app/bundles](http://127.0.0.1:8000/app/bundles).
3. Configure the bundle:
   - **Vault** — select from registered vaults
   - **Filters** — status (complete / partial / all), domain, type, difficulty
   - **Sections** — default: Key Principles, How It Works, Trade-offs. Add or remove custom sections.
   - **Content Options** — include body, include related, allow partial
   - **Budget** — max notes (1–100), max chars (100–500,000)
4. Click **Generate Preview** to call `POST /context/bundle`.
5. The result panel shows:
   - **Bundle Overview** — bundle ID, vault, validation status, schema version, created_at, note count, warning count, feedback count, source path count
   - **Character Budget** — used/max bar, truncation badge, warnings
   - **Notes** — expandable list per note: fields, included sections (collapsible), body preview (collapsible), related IDs
   - **Feedback** — feedback entries linked to selected notes
   - **Graph Relationships** — related node counts (visible only when include_related=true)
   - **Raw JSON** — full bundle JSON, hidden by default

The Bundle Builder does not write packages to disk. To export a bundle as a portable package, use `py run.py export`, `POST /context/export`, or the Export Package UI at `/app/exports` (Phase 13B).

---

## 6f. Export Package UI (Phase 13B)

The Export Package UI at `/app/exports` lets you configure and export a context bundle as a portable package written to disk with a SHA-256 manifest.

**To export a package:**
1. Navigate to **Exports** in the sidebar.
2. Select a **Vault** from the dropdown.
3. Configure **Filters** — status (complete / partial / all), optional domain / type / difficulty.
4. Configure **Sections to Extract** — defaults are Key Principles, How It Works, Trade-offs. Add or remove as needed.
5. Configure **Content Options** — include body, include related notes, allow partial notes.
6. Set **Budget** — max notes (1–100), max chars (100–500,000).
7. Set **Export Options**:
   - **Overwrite existing package** — if the same deterministic bundle ID already exists on disk, enable this to replace it. If off and the package exists, the export will return a conflict error.
   - **Require security pass** — abort export if the security scan detects a blocking finding. Nothing is written to disk on failure.
8. Review the **Request Preview** panel to confirm settings and expected output path.
9. Click **Export Package** to call `POST /context/export`.
10. The result panel shows:
    - **Export Overview** — bundle ID, package directory, file count, total bytes, warnings, overwrite used, security gate status badges
    - **Files** — table of all written files with filename, size, and SHA-256 hash (expandable to full hash)
    - **Warnings** — any warnings returned by the backend
    - **Raw Export JSON** — full response, hidden by default

**Conflict handling:** If the export returns `PACKAGE_EXISTS`, a conflict panel explains that the package already exists and prompts you to enable the overwrite option.

**Security gate failure:** If the export returns `SECURITY_SCAN_FAIL`, a security gate panel explains that nothing was written and directs you to review the security findings in the Dashboard.

Packages are written to `dist/context-bundles/<bundle-id>/` under the repo root. The `dist/` directory is gitignored.

---

## 6g. Security Scan UI (Phase 13C)

The Security Scan UI at `/app/security` lets you run a fully configurable `POST /context/security` scan and inspect results interactively.

**To run a security scan:**
1. Navigate to **Security** in the sidebar.
2. Select a **Vault** from the dropdown.
3. Configure **Filters** — status (complete / partial / all), optional domain / type / difficulty.
4. Configure **Sections to Scan** — defaults are Key Principles, How It Works, Trade-offs. Add or remove as needed.
5. Configure **Content Options** — include body, allow partial notes.
6. Set **Budget** — max notes (1–100), max chars (100–500,000).
7. Review the **Request Preview** panel to confirm your request before submitting.
8. Click **Run security scan** to call `POST /context/security`.
9. The result panel shows:
    - **Scan Overview** — overall status badge (pass / warning / fail), total findings, fail / warning / info counts, notes scanned, source path count
    - **Findings** — expandable finding cards filterable by severity (fail / warning / info) and text search over path / rule / detail; each card shows severity, path, rule, field, and detail
    - **Scanned Notes** — all source paths with per-path finding counts and severity breakdown (F / W / I)
    - **Rule Summary** — client-side rule breakdown showing rule name, count, and highest severity
    - **Raw JSON** — full security response, hidden by default

**Pass state:** When the vault is clean, a strong pass indicator is shown with no empty broken panels.

**Error handling:** Network errors and backend errors are displayed with structured error panels. If the backend is unavailable, a clear message prompts you to start the server.

---

## 6h. Feedback Workflow UI (Phase 14B)

The Feedback Workflow UI at `/app/feedback` lets you view, add, edit, delete, and normalise feedback entries, and see how feedback affects task priority.

**To use the Feedback Workflow:**
1. Navigate to **Feedback** in the sidebar.
2. Select a **Vault** from the dropdown. Feedback and feedback-adjusted tasks load automatically.
3. **Summary cards** at the top show: entry count, warning count, error count, task count, feedback-adjusted task count, and highest-priority task.

**Feedback list**
- All feedback entries are listed, sorted by newest first.
- Filter by path text, signal, severity, or source using the filter controls.
- Click **Clear filters** to reset all filters.
- Each entry shows: id, path, source, signal, severity, comment, created_at.
- Entries without an id cannot be edited or deleted until you run Normalise IDs.

**Add feedback**
1. Fill in **Path** (vault-relative, e.g. `Fundamentals/Algorithms.md`), **Source**, **Signal**, **Severity**, and **Comment**.
2. Inline validation prevents submission if path is blank, contains `..`, or if the comment exceeds 2000 characters.
3. Click **Add feedback** to call `POST /feedback`.
4. On success, the feedback list and task panel refresh automatically. The form clears only on success.

**Edit feedback**
1. Click **Edit** on any entry that has an id.
2. An inline edit form opens pre-filled with the entry's current values.
3. Modify fields and click **Save changes** to call `PUT /feedback/{id}`.
4. Click **Cancel** to discard changes.
5. The list and task panel refresh on success.

**Delete feedback**
1. Click **Delete** on any entry that has an id.
2. A confirmation panel appears — click **Confirm Delete** to proceed with `DELETE /feedback/{id}?vault=<vault>`.
3. Deletion cannot be undone. The list and task panel refresh on success.

**Normalise feedback IDs**
- Located in the **Maintenance** panel at the bottom of the left column.
- Calls `POST /feedback/normalise?vault=<vault>` to assign stable hex IDs to any entries that lack them.
- Entries that already have IDs are unchanged.
- The feedback list refreshes after normalisation.

**Task priority panel**
- The right column shows improvement tasks weighted by feedback (`GET /tasks?include_feedback=true&limit=10`).
- Each task shows: priority badge, path, note, instruction, missing sections, constraints, and feedback_weight (expandable raw JSON behind a details element).
- The panel refreshes automatically after any feedback write operation.

**Error handling:**
- Network errors, backend validation errors (`INVALID_INPUT`, `NOTE_NOT_FOUND`, etc.), and write failures are shown in structured error panels.
- Backend warnings and errors from the feedback file are displayed above the entry list.
- Raw response JSON is hidden by default behind `<details>` expanders.

---

## 6i. Note Browser UI (Phase 15A)

The Note Browser at `/app/notes` lets you browse, filter, search, and inspect vault notes in read-only mode.

**To use the Note Browser:**
1. Navigate to **Notes** in the sidebar.
2. Select a **Vault** from the dropdown. The note list loads automatically.
3. Use the **Filters** panel to narrow the list:
   - Text search over note name and path.
   - Status dropdown (complete / partial / stub / all).
   - Difficulty dropdown.
   - "Missing sections only" checkbox.
   - Click **Clear** to reset all filters.
4. Click any note in the list to load its full detail on the right.

**Note detail panel** (read-only):
- **Header** — note title (from frontmatter), vault-relative path, and status / difficulty / domain / type badges.
- **Frontmatter Fields** — all YAML frontmatter key/value pairs in a table.
- **Section Outline** — headings extracted client-side from the Markdown body with heading level and line number.
- **Markdown Body** — raw Markdown text in a scrollable read-only panel.
- **Validation** — shows a warning if the note appears in the invalid notes list (`GET /validation`), or a pass badge if valid.
- **Improvement Task** — shows the highest-priority improvement task for the note from `GET /tasks?include_feedback=true`, including priority, missing sections, constraints, and optional feedback weight. Shows "No active improvement task" if none exists.
- **Raw JSON** — note detail and query responses hidden behind `<details>` expanders.

**Query Search panel (POST /query):**
1. Click **Query Search** in the left column to expand the panel.
2. Enter a free-text query in the **Free text (q)** field.
3. Select which fields to search: body, path, frontmatter.
4. Optionally add filters: status, difficulty, domain, type.
5. Set the result limit (1–500, default 50).
6. Click **Search** — results replace the note list and show relevance scores.
7. Click a result to load its note detail.
8. Click **Clear search** to return to the base note list.

**Note:** This page is read-only. Note editing is not available in Phase 15A.

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
* http://127.0.0.1:8000/graph/neighbors?node=note::Fundamentals/Algorithms.md&vault=demo-vault
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

A passing run ends with:

```
============================================================
ALL VERIFICATION TESTS PASSED
============================================================
```

---

## 9. Troubleshooting

**Package already exists error**

```
{"status": "error", "error": {"code": "PACKAGE_EXISTS", ...}}
```

Use `--overwrite` to replace an existing package:

```bash
py run.py export --overwrite
```

**FastAPI / httpx not found**

Some tests (11, 15) and the API server require the MCP dependencies:

```bash
pip install -r mcp/requirements.txt
```

**/missing returns MISSING_CONCEPTS_EMPTY (HTTP 422)**

The endpoint returns this error only when `EXPECTED_CONCEPTS` is not defined or is empty in `vault_schema.py`. The demo vault defines `EXPECTED_CONCEPTS` with example gap data for the Fundamentals domain, so `/missing` returns real results. If your vault schema does not yet define `EXPECTED_CONCEPTS`, use `bootstrap` to generate a schema that includes this field.

**Security scan warns on URLs or code blocks**

The security scanner uses deterministic regex rules. Content that describes security concepts (e.g. example API key formats in documentation) may produce `warning`-severity findings. Review findings manually — only `fail`-severity findings block export when `require_security_pass: true` is set.

**`/missing` or `/tasks` return wrong vault**

All adapter endpoints accept a `?vault=<name>` query parameter. If omitted, the first registered vault is used. Check `config/config.yaml` for the configured `vault_root`.
