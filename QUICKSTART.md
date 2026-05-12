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

## 5d. Export Context Package (Phase 4 / Phase 17A)

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
    "context.html":          {"sha256": "...", "bytes": 9876},
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
| `context.html` | Deterministic static HTML rendering for human review (Phase 17A) |
| `manifest.json` | SHA-256 hashes + metadata for all other files |
| `validation.json` | Validation status and warnings |
| `graph.json` | Graph relationships for selected notes |
| `feedback-summary.json` | Feedback entries relevant to selected notes |

**`context.html` notes:**
- Generated from `context.json` / bundle data using Python standard library only.
- Contains no remote scripts, remote CSS, or external assets of any kind.
- All note content is HTML-escaped; note Markdown is not parsed into raw HTML.
- Output is deterministic: identical bundle input produces identical HTML.
- `context.html` is a generated artefact — Markdown vault notes remain the source of truth.

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

### Local App Launcher (Phase 17)

The `py run.py app` command starts or reuses the local server and opens the browser in one step.

**First-time setup (build the UI once):**

```bash
cd ui
npm install
npm run build
cd ..
```

**Launch the app:**

```bash
py run.py app
# → opens http://127.0.0.1:8000/app in the default browser
```

**What happens:**

1. If the server is not running, it starts `mcp/server/mcp_server.py` automatically.
2. It waits until `http://127.0.0.1:8000/health` responds with a valid Context Vault Engine response.
3. It opens `http://127.0.0.1:8000/app` in the default system browser.
4. The server remains attached to the terminal. Press **Ctrl+C** to stop it.

**If the server is already running:**

`py run.py app` detects it via the `/health` endpoint, reuses it, and opens the browser — no duplicate server is started.

**If `ui/dist` has not been built:**

The launcher prints clear build instructions and starts the API server anyway (API endpoints work; the `/app` route returns `UI_NOT_BUILT` until you build the UI).

**The direct server command remains unchanged:**

```bash
py mcp/server/mcp_server.py   # same as before — start server directly
```

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
6. On success the page shows created file paths, expected concepts written, and any backend warnings.
7. Use **Go to Dashboard** to return to the vault overview.

The CLI flow `py run.py bootstrap` remains unchanged and is still the recommended path for automation.

**Expected concepts:**  
Enter concept names in the **Expected Concepts** field during vault setup — one per line or one at a time.
Each concept is normalised to a lowercase slug (e.g. `"Patent Licensing"` → `"patent-licensing"`)
and written into `EXPECTED_CONCEPTS` in the generated `vault_schema.py`.
The **Missing Concepts** page (`/app/missing`) can use them immediately after bootstrap,
without any manual schema editing.

Example:
```json
{
  "expected_concepts": [
    "patent licensing",
    "open licensing",
    "royalty exemption"
  ]
}
```
Generated schema will contain:
```python
EXPECTED_CONCEPTS: dict[str, frozenset[str]] = {
    "patent-law": frozenset({
        "open-licensing",
        "patent-licensing",
        "royalty-exemption",
    }),
}
```

---

## 6e-delete. Deleting a Vault (Phase 18C)

Vaults can be permanently deleted through the API or the UI.

> **Warning:** Deletion removes the entire vault folder from disk. There is no undo in the app. Back up your notes manually (e.g. copy the folder or commit to version control) before proceeding.

### Via API

```bash
curl -X DELETE http://127.0.0.1:8000/vault/my-vault \
  -H "Content-Type: application/json" \
  -d '{"confirm": "DELETE my-vault"}'
```

The `confirm` field must be the exact phrase `DELETE <vault-name>` — case-sensitive, no extra whitespace.

**Success response:**
```json
{
  "status": "ok",
  "data": {
    "deleted": "my-vault",
    "remaining_vaults": ["demo-vault"],
    "active_vault": "demo-vault"
  }
}
```

**Rules:**
- `demo-vault` is permanently protected and cannot be deleted.
- The last registered vault cannot be deleted.
- `config/config.yaml` is updated atomically after deletion.

### Via UI

1. Open [http://127.0.0.1:8000/app/vault-setup](http://127.0.0.1:8000/app/vault-setup).
2. Scroll to the **Danger Zone** section at the bottom of the page.
3. Select the vault to delete from the dropdown. `demo-vault` is shown but disabled.
4. Read the warning banner, then type the confirmation phrase: `DELETE <vault-name>`.
5. Click **Delete \<vault-name\>** (enabled only when phrase matches exactly).
6. On success, the active vault in localStorage is updated to the fallback vault.

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

## 6j. Safe Note Editing UI (Phase 15C)

The Note Browser at `/app/notes` includes a safe in-place editor for existing notes. Edit mode is backed by the `PUT /note` backend API (Phase 15B) which validates all changes before writing.

**Entering edit mode:**
1. Navigate to **Notes** in the sidebar.
2. Select a vault and then click any note in the list to load its detail.
3. Click **Edit note** in the note header action bar.
4. The page switches to edit mode — the header border turns blue and an **EDIT MODE** badge appears.

**Editing frontmatter fields:**
- All existing frontmatter fields are displayed in an editable form.
- Boolean fields use a checkbox. String and numeric fields use a text input.
- Complex values (arrays, nested objects) are shown as read-only JSON — backend validation remains authoritative for these.
- No new arbitrary fields can be added; the backend will reject unknown fields with `VALIDATION_FAILED`.

**Editing the Markdown body:**
- A resizable textarea replaces the read-only body view.
- Character count is shown in the panel header.
- The **Section Outline** panel updates live to reflect the edited body.
- Advisory warnings appear if the expected sections (Key Principles, How It Works, Trade-offs) are absent from the edited body. These are client-side hints only — backend validation is authoritative.

**Saving changes:**
1. Click **Save changes** to call `PUT /note` with the current edits.
2. A spinner and disabled buttons show while the request is in flight.
3. On success: a green confirmation panel appears, the note detail updates with the server's canonical round-trip values, and edit mode exits. The notes list, validation context, and task context all refresh automatically.

**Handling validation failures:**
- If the server returns `VALIDATION_FAILED` (HTTP 400), the page stays in edit mode and shows a structured error panel listing each validation detail.
- Local edits are not discarded — you can fix the issue and retry.
- Click **Cancel** at any time to discard all local edits and return to inspect mode.

**Unsaved changes badge:**
- An **Unsaved changes** badge appears in the header when edited data differs from the loaded values. No navigation guard blocks page navigation.

**Reset to loaded version:**
- While in edit mode, click **Reset to loaded** to restore the form to the last successfully loaded note values without exiting edit mode.

**Cancel:**
- Click **Cancel** to discard all local edits and return to inspect mode.

**Raw JSON expanders** (all hidden by default):
- **Note detail response (GET /note)** — the current loaded note response.
- **Last update response (PUT /note)** — the most recent save response (success or error), available after a save attempt.
- **Current edit payload preview** — the exact JSON that will be submitted to `PUT /note` when you click Save (visible only in edit mode).

**Safety guarantees:**
- `PUT /note` only updates existing notes — it cannot create new notes or delete notes.
- Path traversal is blocked server-side.
- `Vault Files/` is protected from writes.
- The original file is unchanged if validation or write fails.
- Client-side: null bytes and empty body are blocked before the request is sent.

---

## 6k. Graph Explorer UI (Phase 16)

The **Graph** page (`/app/graph`) provides a browser-based view of the vault's
schema-derived relationship graph and missing expected concepts.

> **Important:** All graph relationships are schema-derived and deterministic.
> They are **not** semantic links, AI-inferred connections, or similarity scores.

**Opening the Graph page:**
1. Start the backend server: `py mcp/server/mcp_server.py`
2. Start the Astro UI: `cd ui && npm run dev`
3. Click **Graph** in the sidebar.

**Vault selection:**
- Use the **Vault** dropdown to choose a registered vault.
- Click **Reload** to refresh both the graph and the missing concepts data.
- Switching vaults automatically reloads both datasets.

**What the Graph tab shows:**
- Total nodes and total edges across the whole graph.
- Per-type node counts (note, domain, subdomain, topic, expected_concept).
- Per-type edge counts (parent, member_of, expected_coverage).
- A grouped, searchable node list for every node in the graph.
- Node type filter toggles and edge type filter toggles — click to hide/show groups.
- A text search box to find nodes by label or id.

**Node types:**
| Type | Meaning |
|---|---|
| `note` | A vault note (Markdown file) |
| `domain` | Schema-defined domain hub |
| `subdomain` | Schema-defined subdomain hub |
| `topic` | Schema-defined topic hub |
| `expected_concept` | Concept declared in `EXPECTED_CONCEPTS` but absent from vault |

**Edge types:**
| Type | Meaning |
|---|---|
| `parent` | Hierarchy link (subdomain → domain, topic → subdomain) |
| `member_of` | Note belongs to a domain/subdomain/topic hub |
| `expected_coverage` | Note satisfies, or group declares, an expected concept slot |

**Selecting a node:**
- Click any node row in the Graph tab to select it and switch to the **Inspector** tab automatically.

**Inspector tab:**
- Shows node id, type, and label.
- Shows all direct neighbours (filtered by the active node/edge type filters).
- For `note` nodes only:
  - **Related notes** — notes that share a domain, subdomain, or topic hub with this note (strength shown as `topic > subdomain > domain`).
  - **Missing expected concepts near this note** — expected concepts the schema declares near this note's group hubs that are not yet in the vault.
- Click **inspect →** on any neighbour to navigate to that node.
- Raw JSON (neighbours, related, missing) is hidden by default behind a `<details>` expander.

**Missing Concepts tab:**
- Shows summary cards: expected, present, missing, and domains assessed.
- Lists all missing expected concepts in a ranked table (rank, concept name, subdomain, score).
- Score is derived from schema-defined priority weighting — higher score = higher priority gap.
- Click **Draft action** on any row to generate a non-destructive action card.

**Non-destructive action card:**
- Click **Draft action** next to any missing concept.
- The action card generates a copyable instruction block — it **does not create any files** and **does not call any write API**.
- The card shows: proposed title, proposed path, domain, subdomain, suggested sections, and a full copyable instruction.
- Click **Copy** to copy the instruction to the clipboard.
- Use the copied instruction with your editor, CLI, or Copilot to create the note manually.
- The card is labelled: **Draft action only — no file has been created**.

**Raw JSON panels:**
- All raw JSON panels (graph, inspector, missing concepts, action card) are hidden behind collapsed `<details>` elements by default.

---

## 6l. Context Controller UI (Phase 19)

The **Controller** page (`/app/controller`) provides a real-time deterministic snapshot of your vault's state and a prioritised action plan.

> **Important:** The controller does not call an LLM or make semantic judgements.
> All output is derived from the current state of your vault.

**Opening the Controller page:**
1. Start the backend server: `py mcp/server/mcp_server.py`
2. Start the Astro UI: `cd ui && npm run dev`
3. Click **Controller** in the sidebar.

**Vault and intent selection:**
- Use the **Vault** dropdown to choose a registered vault.
- Use the **Planning Intent** dropdown to select one of five intents:
  - `Review` — general vault health and completeness.
  - `Export` — readiness for context bundle export.
  - `Agent Context` — readiness for LLM agent use.
  - `Quality` — content quality and coverage gaps.
  - `Security` — security findings and risks.
- Click **Refresh** to reload both the state snapshot and the plan.

**Readiness cards:**
- Seven boolean flags derived from validation and security status.
- `ready_to_export` and `ready_for_agent_context` are `true` only when validation passes and the security scan is `pass` or `warning`.

**Recommendations:**
- Ranked list of actions for the selected intent.
- Each recommendation shows its severity (`critical`, `high`, `medium`, `low`, `info`), title, reason, and links to the relevant UI page.
- The top recommendation is highlighted as the **Next Best Action**.

**API equivalents:**

```bash
# State snapshot
curl "http://127.0.0.1:8000/context/state?vault=demo-vault"

# Recommendation plan
curl -X POST http://127.0.0.1:8000/context/plan \
  -H "Content-Type: application/json" \
  -d '{"vault": "demo-vault", "intent": "review"}'
```

---



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

## 6m. MCP Stdio Server (Phase 20)

Context Vault Engine exposes its vault capabilities as a **read-only MCP stdio server** for use with MCP-compatible local clients (e.g. Claude Desktop, Cursor, custom agent loops).

> The MCP server communicates entirely over **stdin/stdout** using newline-delimited JSON-RPC 2.0. All tool calls are deterministic and read-only — no notes are created, edited, or deleted.

### Start the MCP server

```bash
py run.py mcp
```

The server reads JSON-RPC messages from stdin and writes responses to stdout. Log output goes to stderr. Press `Ctrl+C` or close stdin to exit.

### MCP Tools (10 tools, all prefixed `cve.`)

| Tool | Purpose |
|------|---------|
| `cve.list_vaults` | List all registered vault names |
| `cve.get_context_state` | Deterministic readiness snapshot for a vault |
| `cve.get_context_plan` | Prioritised recommendations for a vault + intent |
| `cve.query_notes` | Lexical search across vault notes |
| `cve.get_note` | Read a single note by vault-relative path (path traversal blocked) |
| `cve.validate_vault` | Schema validation result for a vault |
| `cve.get_tasks` | Prioritised improvement tasks |
| `cve.get_missing_concepts` | Concepts expected but absent from the vault |
| `cve.security_scan` | Full-vault security scan (secrets, injection, suspicious content) |
| `cve.build_context_bundle` | Generate a context bundle in-memory (no files written) |

### MCP Resources (9 URI patterns)

| URI | Content |
|-----|---------|
| `cve://vaults` | List of all registered vaults |
| `cve://vault/{vault}/summary` | Completion summary |
| `cve://vault/{vault}/state` | Context state (readiness flags) |
| `cve://vault/{vault}/plan/review` | Review plan |
| `cve://vault/{vault}/notes` | All notes with metadata |
| `cve://vault/{vault}/tasks` | Prioritised tasks |
| `cve://vault/{vault}/missing` | Missing concepts |
| `cve://vault/{vault}/security` | Security scan result |
| `cve://vault/{vault}/graph` | Relationship graph |

### MCP Prompts (4 prompts, all prefixed `cve.`)

| Prompt | Purpose |
|--------|---------|
| `cve.vault_review` | Guide an agent through a complete vault review |
| `cve.security_review` | Focus an agent on security findings and remediation |
| `cve.context_handoff` | Prepare a context handoff document for another agent |
| `cve.quality_plan` | Generate a quality improvement plan |

All prompts include a safety footer: agents are reminded that all tool calls in the session are read-only by default.

### Example session

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | py run.py mcp
```

---

## 6n. Private Cloud Mode (Phase 21)

Run Context Vault Engine on a personal VPS or private server and access it from trusted clients with token-based authentication. All local behaviour is unchanged by default.

> **Security:** Never expose the API port directly on a public IP. Use Tailscale, WireGuard, Cloudflare Tunnel, or a TLS reverse proxy. See `DEPLOYMENT.md`.

### Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `CVE_PRIVATE_CLOUD_ENABLED` | Enable private cloud mode | `false` |
| `CVE_AUTH_TOKEN` | Bearer token (keep secret, never commit) | _(empty)_ |
| `CVE_REQUIRE_AUTH` | Require auth for all non-health routes | `false` locally; `true` when private cloud enabled |
| `CVE_REMOTE_READ_ONLY` | Block mutating routes | `true` when private cloud enabled |
| `CVE_PUBLIC_BASE_URL` | Public URL for status display | _(empty)_ |
| `CVE_DEPLOYMENT_MODE` | `local`, `vps`, or `tunnel` | `local` |

### Local test of private mode

```bash
# Generate a token
TOKEN=$(python -c "import secrets; print(secrets.token_hex(32))")

# Start with private cloud mode
CVE_PRIVATE_CLOUD_ENABLED=true CVE_AUTH_TOKEN="$TOKEN" py run.py app

# Check status (no auth required)
curl http://localhost:8000/private/status

# Authenticated read
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/vaults
# or
curl -H "X-CVE-Token: $TOKEN" http://localhost:8000/vaults

# Unauthenticated → 401 AUTH_REQUIRED
curl http://localhost:8000/vaults

# Write in read-only mode → 403 REMOTE_READ_ONLY
curl -X PUT -H "Authorization: Bearer $TOKEN" http://localhost:8000/note
```

For full VPS deployment instructions, systemd service example, reverse proxy config, backup guidance, and firewall rules, see **`DEPLOYMENT.md`**.

---

## 6o. Session and Project State (Phase 22)

Context Vault Engine tracks where you are in a project via two complementary stores:

- **Session state** — a per-session JSON file recording the current topic, goal, and recently worked-on notes.
- **Project state** — a single JSON file recording the current phase, completed work, next actions, blockers, decisions, and risks.

All state is stored as human-readable JSON inside `<vault>/Vault Files/State/`. Writes are atomic (temp-file + replace). No database, no cloud sync.

### CLI commands

```bash
# Print current session summary (or list recent sessions if none is active)
py run.py session

# Print project state (returns defaults if no state file exists)
py run.py project-state
```

### HTTP API (summary)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/session/start` | Start a new session |
| GET | `/session/resume` | Fetch latest active session (or by `session_id`) |
| GET | `/session/summary` | Compact LLM-ready session summary |
| POST | `/session/attach-note` | Record a recently-accessed note |
| POST | `/session/close` | Close the current session |
| GET | `/project/state` | Read project state |
| PUT | `/project/state` | Update project state fields |

Write routes (`POST /session/start`, `POST /session/attach-note`, `POST /session/close`, `PUT /project/state`) are blocked when `CVE_REMOTE_READ_ONLY=true`.

### MCP tools

The MCP stdio server exposes 7 new tools: `cve.start_session`, `cve.resume_session`, `cve.summarise_session`, `cve.attach_note_to_session`, `cve.close_session`, `cve.get_project_state`, `cve.update_project_state`.

A new `cve.resume_work` prompt guides an LLM through reading the current session summary and project state to answer "where was I up to?".

### Session file location

```
<vault>/Vault Files/State/sessions/<YYYYMMDDTHHMMSS-xxxxxxxx>.json
<vault>/Vault Files/State/project-state.json
```

---

## 6p. Safe Memory Write Queue (Phase 23)

LLM-proposed note changes are stored as **pending change proposals** for human review. Nothing is written to vault notes without explicit acceptance.

### Core principle

> "LLMs may propose changes. They must not directly rewrite notes by default."

A proposal includes:
- The full proposed note content
- A unified diff against the original
- Schema validation status
- Source (agent / human / system), reason, and session context
- A SHA-256 content hash for staleness detection

### Change lifecycle

1. LLM calls `cve.create_note_draft`, `cve.suggest_note_update`, or `cve.update_note_section_draft`
2. Proposal is validated and stored as JSON under `Vault Files/State/pending-changes/`
3. Human reviews via UI, CLI, API, or MCP
4. Human explicitly accepts (→ applies to vault, archived) or rejects (→ archived)

### CLI command

```bash
# List pending proposals
py run.py pending
```

### HTTP API (summary)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/memory/pending` | List pending change proposals |
| POST | `/memory/create-note-draft` | Propose creating a new note |
| POST | `/memory/suggest-note-update` | Propose updating an existing note |
| POST | `/memory/update-section-draft` | Propose replacing one section |
| GET | `/memory/pending/{id}` | Get full change detail |
| POST | `/memory/pending/{id}/accept` | Accept and apply a change |
| POST | `/memory/pending/{id}/reject` | Reject and archive a change |

Write routes are blocked when `CVE_REMOTE_READ_ONLY=true`.

### MCP tools

Seven new tools: `cve.create_note_draft`, `cve.suggest_note_update`, `cve.update_note_section_draft`, `cve.list_pending_changes`, `cve.review_pending_change`, `cve.accept_pending_change`, `cve.reject_pending_change`.

A new `cve.review_pending_change` prompt guides a reviewer through examining a diff and deciding to accept or reject.

### Storage

```
<vault>/Vault Files/State/pending-changes/<YYYYMMDDTHHMMSS-xxxxxxxx>.json
<vault>/Vault Files/State/pending-changes/archive/<YYYYMMDDTHHMMSS-xxxxxxxx>.json
```

---

## 6q. Context Profiles and Budget Modes (Phase 24)

Context profiles let you target a specific client device or LLM context window without manually tuning every budget parameter.

### Built-in modes

| Mode | Max notes | Max chars | Notes |
|------|-----------|-----------|-------|
| `tiny` | 3 | 4,000 | Minimal: fits 4-bit phone LLMs |
| `small` | 5 | 8,000 | Compact: fits 7B models |
| `medium` | 10 | 20,000 | Default balanced mode |
| `large` | 25 | 50,000 | Extended: fits 70B+ models |
| `agent` | 15 | 100,000 | Full agent context window |

### Built-in device profiles

| Profile | Mode base | Description |
|---------|-----------|-------------|
| `phone-local-llm` | tiny | Offline phone with 4-bit quantised LLM |
| `desktop-agent` | large | On-device agent with 128K context |
| `full-review` | agent | Full human review session |

### CLI usage

```bash
# List all profiles and modes
py run.py profiles

# Example output excerpt
{
  "modes": { "tiny": { "max_notes": 3, "max_chars": 4000, ... }, ... },
  "profiles": { "phone-local-llm": { ... }, ... },
  "defaults": { "mode": "medium", "profile": null }
}
```

### HTTP API

```bash
# List all profiles and modes
GET /context/profiles

# Get a specific profile or mode
GET /context/profiles/tiny
GET /context/profiles/phone-local-llm

# Generate a bundle using a profile
POST /context/bundle
{
  "vault": "my-vault",
  "profile": "phone-local-llm",
  "include_sections": ["Key Principles"]
}

# Generate a bundle using a mode
POST /context/bundle
{
  "vault": "my-vault",
  "mode": "small",
  "include_sections": ["Key Principles"]
}
```

Profile precedence: when both `profile` and `mode` are supplied, `profile` wins. Explicit request fields (e.g., `max_notes: 5`) always override profile defaults. Hard caps (`max_notes ≤ 100`, `max_chars ≤ 500,000`) are always enforced.

The response includes a `profile_metadata` object describing which profile/mode was applied and the effective budget used.

### MCP tools

- `cve.list_context_profiles` — list all profiles and modes (no vault required)
- `cve.build_context_bundle` now accepts `profile` and `mode` parameters

### Bundle Builder UI

The Bundle Builder at `/app/bundles` now shows a **Context Profile / Mode** panel above the filters. Click a mode badge (tiny / small / medium / large / agent) or device profile badge to apply its defaults to the budget controls. Manual overrides are labelled with ⚠. The result panel shows profile metadata when a profile was used.

---

## 6r. Trust, Staleness, and Evidence Metadata (Phase 25)

Notes can carry optional trust and freshness metadata as frontmatter fields.

### Optional frontmatter fields

```yaml
trust_level: verified        # verified | working | draft | external | deprecated
source_type: authored        # authored | imported | generated | agent_suggested
last_reviewed: "2025-06-01"  # ISO date YYYY-MM-DD
review_after: "2026-06-01"   # ISO date YYYY-MM-DD
```

All fields are optional and backward-compatible. Existing notes without them continue to validate and export normally.

**Allowed values:**
- `trust_level`: `verified`, `working`, `draft`, `external`, `deprecated`
- `source_type`: `authored`, `imported`, `generated`, `agent_suggested`
- `last_reviewed` / `review_after`: ISO date format `YYYY-MM-DD`

### Confidence scoring

Confidence is computed from `trust_level` and `source_type`. It indicates how thoroughly a note has been reviewed and maintained — **not factual correctness**.

| trust_level | source_type | confidence |
|---|---|---|
| verified | authored | high |
| working | authored | medium |
| draft / external / generated | — | low |
| deprecated | — | deprecated |
| (none) | — | unknown |

### CLI commands

```bash
# Trust summary for the default vault
py run.py trust

# Staleness summary for the default vault
py run.py stale
```

### API endpoints

```
GET /trust?vault=<vault>            # trust/confidence summary
GET /stale?vault=<vault>            # staleness breakdown
POST /evidence                      # build trust-ranked evidence response
```

Evidence request body:
```json
{
  "vault": "demo-vault",
  "q": "sorting algorithms",
  "prefer_verified": true,
  "include_deprecated": false,
  "include_stale": true,
  "max_notes": 20
}
```

### Trust & Evidence UI

Visit `/app/trust` in the browser UI to:
- View trust/confidence summary cards
- Browse stale and deprecated notes
- Build evidence responses with the interactive form

### MCP tools

- `cve.get_trust_summary` — vault-level trust/confidence summary
- `cve.get_stale_notes` — stale and freshness-unknown notes
- `cve.build_evidence` — trust-ranked evidence with source paths and section excerpts

### MCP resources

- `cve://vault/{vault}/trust` — trust summary as a resource
- `cve://vault/{vault}/stale` — staleness summary as a resource

### MCP prompt

- `cve.evidence_review` — guides an agent to cite source paths, state confidence levels, include a factual accuracy disclaimer, and not auto-edit notes

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

The endpoint returns this error only when `EXPECTED_CONCEPTS` is not defined or is empty in `vault_schema.py`. The demo vault defines `EXPECTED_CONCEPTS` with example gap data for the Fundamentals domain, so `/missing` returns real results. When bootstrapping a new vault, supply `expected_concepts` in the bootstrap request so that `EXPECTED_CONCEPTS` is written into the generated schema automatically — no manual editing required.

**Security scan warns on URLs or code blocks**

The security scanner uses deterministic regex rules. Content that describes security concepts (e.g. example API key formats in documentation) may produce `warning`-severity findings. Review findings manually — only `fail`-severity findings block export when `require_security_pass: true` is set.

**`/missing` or `/tasks` return wrong vault**

All adapter endpoints accept a `?vault=<name>` query parameter. If omitted, the first registered vault is used. Check `config/config.yaml` for the configured `vault_root`.
