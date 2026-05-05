# Context Vault Engine — Testing

All tests live in `mcp/test_verify.py`. There are 188 test functions covering all implemented phases.

---

## Running the Tests

### Full verification suite (recommended)

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

Any failure prints the test name, assertion message, and a traceback, then exits with code 1.

### Core tests only (no API dependencies)

The majority of tests (excluding tests 11 and 15) run without FastAPI:

```bash
pip install -r requirements.txt
py mcp/test_verify.py
```

Tests 11 (`test_rate_limiter`), 15 (`test_structured_logging`), and `test_p6_docs_consistency` (documentation coverage check) import from the MCP server and require the full API dependencies.

### CLI smoke commands

These can be run independently to verify core commands work:

```bash
py run.py validate              # exit 0 = all notes pass schema
py run.py analyse               # prints seven structured analyses
py run.py improve               # prints ranked upgrade tasks
py run.py bundle                # prints JSON bundle to stdout
py run.py feedback              # prints feedback entries as JSON
py run.py export --overwrite    # exports bundle to dist/; exit 0 = ok
py run.py security              # prints security scan as JSON; exit 0 = pass/warning
```

---

## Test Dependencies

- Core tests: `requirements.txt` (PyYAML, etc.)
- API and HTTP tests: `mcp/requirements.txt` (FastAPI, httpx, uvicorn)

Install both for the full suite:

```bash
pip install -r requirements.txt
pip install -r mcp/requirements.txt
```

---

## Test Categories by Phase

### Original Hardening Tests (Tests 1–16)

Basic correctness and server behaviour:

- **Test 1** `test_basic_functionality` — all vaults load and index correctly.
- **Test 2** `test_deterministic_ordering` — index and query results are sorted deterministically.
- **Test 3** `test_concurrent_queries` — 20 concurrent queries produce consistent results.
- **Test 4** `test_schema_hash_tracking` — schema hash is stored and retrievable.
- **Test 5** `test_pagination_stable` — pages are bounded, non-overlapping, and stable.
- **Test 6** `test_path_traversal_blocked` — path traversal attacks are rejected.
- **Test 7** `test_strict_mode` / filter validation — unknown fields rejected in both strict and non-strict mode.
- **Test 8** `test_limit_and_timeout` — limits are respected; max limit is clamped to 500.
- **Test 9** `test_typed_responses` — all responses follow the typed contract.
- **Test 10** `test_cross_vault_queries` — aggregate works across all vaults.
- **Test 11** `test_rate_limiter` — in-memory rate limiter enforces 50 req/s *(requires mcp/requirements.txt)*.
- **Test 12** `test_schema_refresh_cooldown` — schema reload respects 2-second cooldown.
- **Test 13** `test_index_metadata` — index metadata is populated after build.
- **Test 14** `test_config_validation` — startup config validation catches missing vaults.
- **Test 15** `test_structured_logging` — structured logging is active *(requires mcp/requirements.txt)*.
- **Test 16** `test_concurrent_build_and_query` — concurrent build + query does not crash.

### Contract Tests

- `test_contract_runner_pass` — contract checks pass for demo vault.
- `test_contract_schema_interface` — schema exposes required functions.
- `test_contract_index_integrity` — index fields match expected shape.
- `test_contract_query_determinism` — repeated queries return identical results.
- `test_contract_lightweight` — lightweight contract check completes without error.

### Phase 0 — Query Correctness Tests

Regression tests for correctness fixes:

- Unknown field → `INVALID_FILTER` error with zero results (both strict and non-strict mode).
- `field__in` with non-list value → `INVALID_FILTER`.
- Unsupported operator (e.g. `status__gt`) → `INVALID_FILTER`.
- Valid equality, `__in`, `__contains` queries → correct results.
- Pagination preserved after index rebuild.
- Note edit reflected in index within cooldown window.
- `get_note` reflects edits.
- Query reflects frontmatter edits.
- Schema hash rebuild still works.
- Deterministic ordering preserved after rebuild.

### Phase 1 — API Route Tests

- `test_p1_http_smoke` — HTTP server starts and responds.
- `test_p1_validation_adapter` — `GET /validation` returns structured result.
- `test_p1_tasks_full_path` — each task includes a full vault-relative POSIX path.
- `test_p1_tasks_constraints` — each task includes writing constraints.
- `test_p1_notes_full_paths` — each note includes a full vault-relative POSIX path.
- `test_p1_quality_adapter` — `GET /quality` returns structured result.
- `test_p1_missing_adapter` — `GET /missing` returns gap data for demo vault (`EXPECTED_CONCEPTS` populated with 5 Fundamentals concepts).
- `test_p1_compare_missing_file` — `POST /compare` with non-existent file returns error.
- `test_p1_graph_build` — `GET /graph/{vault}` returns nodes and edges.
- `test_p1_graph_related` — `GET /graph/{vault}/related` returns related nodes.
- `test_p1_graph_missing_neighbors` — `GET /graph/{vault}/missing` returns missing concepts.
- `test_p1_unknown_vault_structured_error` — unknown vault returns structured 404.
- Vault param tests: validation, tasks, notes, quality, missing all accept `?vault=` param.

### Phase 2 — Bundle Generation Tests

20 tests covering bundle engine behaviour:

- Basic bundle shape and field presence.
- POSIX paths in bundle notes.
- `max_notes` and `max_chars` budget enforcement.
- `allow_partial=false` excludes partial notes; `allow_partial=true` includes them.
- Section extraction (present and missing sections).
- `include_body=false` excludes body field.
- `include_related=true` populates graph relationships.
- `validation_status` reflects invalid note state.
- `bundle_id` is deterministic across identical requests.
- Unknown vault → 404 structured error.
- Empty filter returns notes.
- CLI bundle: `py run.py bundle` returns valid JSON.
- HTTP bundle: `POST /context/bundle` returns valid response.
- Budget: high `max_chars` → no truncation.
- Budget: low `max_chars` → `truncated=True` + warning.
- Budget: `max_notes` cap vs `max_chars` truncation are distinguishable.

### Phase 3 — Feedback Tests

28 tests:

- Missing `feedback.md` → ok, empty entries.
- Valid `feedback.md` → entries parsed and validated.
- Empty `feedback.md` → ok, empty list.
- Malformed YAML → error.
- Unknown signal/severity/source → entry excluded with error.
- Feedback for missing note path → warning.
- `feedback.md` excluded from notes, query, graph, and bundle note selection.
- Task weighting: `include_feedback=false` → no `feedback_weight`.
- Task weighting: `include_feedback=true` → `feedback_weight` present.
- Score change: negative signals raise priority; positive signals lower it.
- `useful`/`agent_succeeded` signals do not raise priority.
- Task ordering is deterministic with feedback applied.
- `GET /feedback` returns structured response.
- `GET /feedback` with unknown vault returns 404.
- `GET /tasks?include_feedback=true` returns `feedback_weight` on tasks.
- Bundle includes `feedback` block.
- Bundle feedback only includes entries for selected notes.
- Bundle with feedback is deterministic.
- `py run.py feedback` returns valid JSON.

### Phase 4 — Export Tests

21 tests:

- Export writes all six required package files.
- `context.json` is valid bundle JSON.
- `context.md` contains required fields.
- `manifest.json` lists all six files with hashes.
- Manifest hashes match actual file content.
- Return value hashes match manifest.
- `validation.json` is structured.
- `graph.json` is structured.
- `feedback-summary.json` is structured.
- `overwrite=False` with existing package → `PACKAGE_EXISTS` error.
- `overwrite=True` replaces package.
- Error bundle returns structured error.
- No extra files in package directory.
- CLI export returns valid JSON.
- CLI export writes package directory.
- CLI export conflict without `--overwrite` → exits 1.
- CLI export with `--overwrite` → exits 0.
- `POST /context/export` → ok.
- `POST /context/export` conflict → 409.
- `POST /context/export` with `overwrite=true` → ok.
- `POST /context/export` unknown vault → 404.

### Phase 5 — Security Scan Tests

39 tests:

- Safe text → no findings.
- Private key pattern → detected as `fail`.
- AWS API key → detected.
- GitHub token → detected.
- Slack token → detected.
- Password placeholder → not flagged.
- Real password assignment → flagged.
- Prompt injection phrase → detected.
- External link → detected.
- Script tag → detected.
- Executable code block → detected.
- Findings are in deterministic order.
- Broad agent instruction → detected.
- Empty text → no crash.
- Bundle scan returns correct shape.
- Bundle scan uses POSIX source paths.
- Empty bundle → no crash.
- Bundle finding includes path.
- Error bundle input → no crash.
- Section content is scanned.
- `scan_vault_context` works end-to-end.
- Unknown vault → structured error.
- CLI security: returns valid JSON.
- CLI security: demo vault → exit 0.
- CLI `--fail-on-warning` flag works.
- `POST /context/security` works.
- Unknown vault → 404.
- Invalid filter → 400.
- Empty filter → no crash.
- Synthetic `fail` result blocked by export gate.
- `require_security_pass=false` → export unchanged.
- `require_security_pass=true` + clean bundle → export succeeds.
- `require_security_pass=true` + fail bundle → export blocked with 400.

### Phase 6 — Documentation Consistency Test

- `test_p6_docs_consistency` — all 7 required docs files exist; README mentions correct project name; QUICKSTART has no stale naming; API.md covers all registered routes.

### Phase 7 — Deterministic Lexical Query Search Tests

23 tests covering lexical search on `POST /query`:

- `test_p7_q_omitted_preserves_behaviour` — `q` omitted produces identical results to plain query.
- `test_p7_q_blank_preserves_behaviour` — `q=""` and `q="   "` behave the same as `q` omitted; no `score` key in results.
- `test_p7_q_returns_positive_score_results` — `q="recursion"` returns only notes with `score > 0`.
- `test_p7_q_no_match_returns_empty` — `q` with no matches returns `count=0` and empty results.
- `test_p7_q_combined_with_filters` — `q` combined with filters applies both constraints; all results satisfy both.
- `test_p7_q_deterministic_repeated` — three identical calls return identical results.
- `test_p7_q_ranking_deterministic` — results are in non-increasing score order.
- `test_p7_q_score_range` — all scores in `(0.0, 1.0]`.
- `test_p7_q_overlong_rejected` — `q` > 1000 chars returns `INVALID_QUERY`.
- `test_p7_q_fields_invalid_rejected` — unsupported `q_fields` value returns `INVALID_QUERY` with offending field listed.
- `test_p7_q_fields_body` — `q_fields=["body"]` searches note body text.
- `test_p7_q_fields_path` — `q_fields=["path"]` searches note path.
- `test_p7_q_fields_frontmatter` — `q_fields=["frontmatter"]` searches frontmatter field values.
- `test_p7_q_http_api` — `POST /query` with `q` works over HTTP TestClient; results include `score`.
- `test_p7_q_http_no_match` — HTTP `POST /query` no-match returns `count=0`.
- `test_p7_q_http_invalid_q_fields` — HTTP invalid `q_fields` returns HTTP 400 `INVALID_QUERY`.
- `test_p7_q_http_overlong_q` — HTTP overlong `q` returns HTTP 400 `INVALID_QUERY`.
- `test_p7_q_no_score_when_q_absent` — no `score` key in results when `q` is absent.
- `test_p7_tiebreak_by_path` — equal-score notes are sorted by path ascending.
- `test_p7_lexical_timeout_returns_partial` — lexical scoring loop timeout returns `status='partial'` with `warning='query timeout'`.
- `test_p7_partial_lexical_results_sorted_deterministically` — partial lexical results are still sorted deterministically (score desc, then path asc).
- `test_p7_q_omitted_timeout_unchanged` — `q` omitted with a near-zero timeout still returns `partial` or `ok`; no `score` key in results.
- `test_p7_q_fields_empty_returns_invalid_query` — `q_fields=[]` returns `INVALID_QUERY`.

### Phase 9 — Schema Data Tests

4 tests covering `SCHEMA_VERSION` and `EXPECTED_CONCEPTS`:

- `test_p9_schema_version_defined` — `vault_schema.py` exposes `SCHEMA_VERSION = '3.0.0'`.
- `test_p9_bundle_manifest_schema_version` — bundle `manifest.schema_version` equals `'3.0.0'`.
- `test_p9_export_manifest_schema_version` — exported `manifest.json` contains `schema_version = '3.0.0'`.
- `test_p9_missing_returns_concept_gaps` — `GET /missing` returns `total_expected=5`, `total_missing=5`, one subdomain, and a ranked gap list.

### Phase 10 — Local Web UI Foundation Tests

8 tests verifying the `/app` endpoint and that it does not break existing API routes:

- `test_p10_app_no_500_when_ui_not_built` — `GET /app` returns 503 with `UI_NOT_BUILT` error (not 500) when `ui/dist` has not been built.
- `test_p10_app_does_not_break_health` — `GET /health` remains functional after hitting `/app`.
- `test_p10_app_does_not_break_vaults` — `GET /vaults` remains functional after hitting `/app`.
- `test_p10_app_does_not_break_summary` — `GET /summary?vault=<name>` works after hitting `/app`.
- `test_p10_app_does_not_break_validation` — `GET /validation?vault=<name>` works after hitting `/app`.
- `test_p10_app_does_not_break_security` — `POST /context/security` works after hitting `/app`.
- `test_p10_app_path_traversal_blocked` — `/app/<traversal>` returns 400 `PATH_TRAVERSAL` (or safe SPA fallback); no sensitive file content leaks.
- `test_p10_summary_accepts_vault_param` — `GET /summary?vault=<name>` returns valid summary; `GET /summary` (no param) is backwards-compatible; `GET /summary?vault=__nonexistent__` returns 404 `INVALID_VAULT`.

### Phase 11A — Guided Vault Bootstrap Backend API Tests

14 tests covering the `POST /vault/bootstrap` endpoint, `core/shared/bootstrap_service.py`, and CLI compatibility:

- `test_p11a_valid_bootstrap_creates_vault` — Valid inputs create a vault directory with files listed in `created`.
- `test_p11a_path_traversal_rejected` — `vault_name` values containing `..` or path separators are rejected before any file write.
- `test_p11a_absolute_path_rejected` — Absolute paths as `vault_name` are rejected.
- `test_p11a_duplicate_vault_rejected` — Requesting a `vault_name` that already exists returns a validation error.
- `test_p11a_empty_domain_rejected` — Empty or whitespace-only `domain` is rejected with an error mentioning `domain`.
- `test_p11a_invalid_note_type_rejected` — `note_type` values that don't match the slug pattern (e.g. uppercase, underscore, space) are rejected.
- `test_p11a_too_few_sections_rejected` — Fewer than 2 non-whitespace sections are rejected.
- `test_p11a_duplicate_sections_rejected` — Duplicate sections (case-insensitive) are rejected.
- `test_p11a_config_updated_atomically` — After bootstrap `config/config.yaml` is valid YAML with `vault_root` pointing to the new vault.
- `test_p11a_vault_has_schema` — Bootstrapped vault contains `Vault Files/Scripts/vault_schema.py` with `VALID_TYPES` and `DOMAIN_MAP`.
- `test_p11a_vault_has_templates` — Bootstrapped vault contains at least one `.md` template file with section headers.
- `test_p11a_cli_bootstrap_still_importable` — `core.bootstrap_vault` is importable and exports `main`, `collect_input`, `_create_vault_structure`, and `_update_config`.
- `test_p11a_api_bootstrap_success_envelope` — `POST /vault/bootstrap` with valid inputs returns HTTP 200 with standard `status/data` envelope, and `data` contains `vault`, `created`, and `warnings`.
- `test_p11a_api_bootstrap_invalid_input_errors` — Various invalid inputs return structured `status/error/code/message` responses with 400 or 422 status.

### Phase 13C — Security Scan UI

Phase 13C is a frontend-only phase. No new backend tests were added (all 202 backend tests still pass).

**Verification steps for Phase 13C:**

```bash
# Frontend build verification
cd ui
npm run build      # must produce no TypeScript errors (SecurityScan.svelte built cleanly)

# Backend suite (unchanged — 202 tests)
py mcp/test_verify.py

# Vault validation and security scan
py run.py validate
py run.py security
```

**What was added:**
- `ui/src/lib/api.ts` — added `SecurityScanned` interface, `ContextSecurityResponse` type alias, `ContextSecurityRequest` interface, and `scanContextSecurity()` function calling `POST /context/security`
- `ui/src/components/SecurityScan.svelte` — full Security Scan island: vault selector, filter controls (status/domain/type/difficulty), section tag editor with duplicate/empty validation, content option checkboxes (include_body/allow_partial), budget number inputs, request preview panel, Run security scan button; result panel with Scan Overview (status badge, total findings, fail/warning/info counts, notes scanned, source path count), Findings (expandable cards with severity/path/rule/field/detail, severity filter buttons, text filter), Scanned Notes panel (per-path finding counts and F/W/I severity badges), Rule Summary panel (client-side rule breakdown), Raw JSON toggle
- `ui/src/pages/security.astro` — replaced PlaceholderPage with SecurityScan island
- `ui/src/layouts/AppLayout.astro` — removed "soon" badge from Security nav item; footer updated to Phase 13C

**Manual acceptance checks:**
- `/app/security` loads the Security Scan form
- Vault dropdown populates from `GET /vaults`
- Status buttons toggle between complete / partial / all
- Domain, type, difficulty inputs accept optional values
- Default sections (Key Principles, How It Works, Trade-offs) pre-filled as tags
- Adding a duplicate section shows an error; adding empty shows an error
- Sections can be removed with the X button
- include_body and allow_partial checkboxes work
- Partial-status conflict warning appears when status=partial + allow_partial=false
- max_notes and max_chars inputs accept values in range
- Request preview panel shows vault, filters, sections, include_body, allow_partial, max_notes, max_chars, and scope note
- Run security scan button POSTs `POST /context/security` with correct request shape
- Loading spinner shown while request is in flight
- Pass result: Scan Overview shows "pass" badge (emerald), zero findings, strong pass message panel
- Fail/warning result: Overview shows correct status badge (red/amber), finding counts, finding cards expandable
- Findings severity filter (all/fail/warning/info) and text filter work; total counts shown in buttons regardless of filter
- Scanned Notes panel shows source paths with finding counts and severity badges; clean notes show "clean"
- Rule Summary panel shows rule name, count, and highest severity
- Structured backend errors show error title and message
- Network failure shows "Backend Unavailable" panel with server address hint
- Raw JSON is hidden by default; toggle reveals full response
- Navigation sidebar: Security no longer shows "soon" badge

---

### Phase 13B — Export Package UI

Phase 13B is a frontend-only phase. No new backend tests were added (all 202 backend tests still pass).

**Verification steps for Phase 13B:**

```bash
# Frontend build verification
cd ui
npm run build      # must produce no TypeScript errors (ExportPackage.svelte built cleanly)

# Backend suite (unchanged — 202 tests)
py mcp/test_verify.py

# Vault validation and security scan
py run.py validate
py run.py security
```

**What was added:**
- `ui/src/lib/api.ts` — export types (`ExportFileInfo`, `ContextExportRequest`, `ContextExportResponse`) and `exportContextPackage()` function calling `POST /context/export`
- `ui/src/components/ExportPackage.svelte` — full Export Package island: vault selector, filter controls (status/domain/type/difficulty), section tag editor with duplicate/empty validation, content option checkboxes (include_body/include_related/allow_partial), budget number inputs, export options (overwrite/require_security_pass), Export Package button; result panel with Export Overview, Files/Manifest table (filename/bytes/SHA-256), Warnings panel, Raw JSON toggle; conflict panel for PACKAGE_EXISTS; security gate failure panel for SECURITY_SCAN_FAIL; request preview panel before export
- `ui/src/pages/exports.astro` — replaced PlaceholderPage with ExportPackage island
- `ui/src/layouts/AppLayout.astro` — removed "soon" badge from Exports nav item; footer updated to Phase 13B

**Manual acceptance checks:**
- `/app/exports` loads the Export Package form
- Vault dropdown populates from `GET /vaults`
- Status buttons toggle between complete / partial / all
- Domain, type, difficulty inputs accept optional values
- Default sections (Key Principles, How It Works, Trade-offs) pre-filled as tags
- Adding a duplicate section shows an error
- Adding an empty section shows an error
- Sections can be removed with the X button
- include_body, include_related, allow_partial checkboxes work
- Overwrite and require_security_pass checkboxes work
- Partial-status conflict warning appears when status=partial + allow_partial=false
- max_notes and max_chars inputs accept values in range
- Request preview panel updates reactively as form is edited
- Export Package button POSTs `POST /context/export` with correct request shape (including overwrite and require_security_pass)
- Loading spinner shown while request is in flight
- Success: Export Overview (bundle_id, package_dir, file count, total bytes, warnings, overwrite flag, security gate flag), Files table (filename/bytes/SHA-256 with expandable full hash), Warnings panel, Raw JSON toggle all render
- PACKAGE_EXISTS error shows amber conflict panel with instructions to enable overwrite
- SECURITY_SCAN_FAIL error shows red security gate panel explaining nothing was written to disk
- Other structured backend errors show generic error panel with error title and message
- Network failure shows "Backend Unavailable" error panel
- Raw JSON is hidden by default; Show button reveals it
- Navigation sidebar: Exports no longer shows "soon" badge

---

### Phase 13A — Bundle Builder UI

Phase 13A is a frontend-only phase. No new backend tests were added (all 202 backend tests still pass).

**Verification steps for Phase 13A:**

```bash
# Frontend build verification
cd ui
npm run build      # must produce no TypeScript errors (BundleBuilder.svelte ~32 kB)

# Backend suite (unchanged — 202 tests)
py mcp/test_verify.py

# Vault validation and security scan
py run.py validate
py run.py security
```

**What was added:**
- `ui/src/lib/api.ts` — bundle types (`ContextBundleRequest`, `ContextBundleResponse`, `BundleNote`, `BundleBudget`, `BundleManifest`, `BundleFeedback`, `BundleGraph`) and `generateContextBundle()` function calling `POST /context/bundle`
- `ui/src/components/BundleBuilder.svelte` — full Bundle Builder island: vault selector, filter controls (status/domain/type/difficulty), section tag editor with duplicate/empty validation, content option checkboxes (include_body/include_related/allow_partial), budget number inputs, Generate Preview button; result panel with Overview, Budget bar, Notes list (expandable per note with sections/body/related/raw JSON), Feedback block, Graph Relationships summary, Raw JSON toggle
- `ui/src/pages/bundles.astro` — replaced PlaceholderPage with BundleBuilder island
- `ui/src/layouts/AppLayout.astro` — removed "soon" badge from Bundles nav item; footer updated to Phase 13A

**Manual acceptance checks:**
- `/app/bundles` loads the Bundle Builder form
- Vault dropdown populates from `GET /vaults`
- Status buttons toggle between complete / partial / all
- Domain, type, difficulty inputs accept optional values
- Default sections (Key Principles, How It Works, Trade-offs) pre-filled as tags
- Adding a duplicate section shows an error
- Adding an empty section shows an error
- Sections can be removed with the X button
- include_body, include_related, allow_partial checkboxes work
- Partial-status conflict warning appears when status=partial + allow_partial=false
- max_notes and max_chars number inputs accept values in range
- Generate Preview button POSTs `POST /context/bundle` with correct request shape
- Loading spinner shown while request is in flight
- Success: overview panel, budget bar, notes list, feedback panel, graph panel, raw JSON toggle all render
- Budget truncation shows amber bar and warning callout
- Each note row expands to show fields, sections (collapsible), body (collapsible), raw note JSON toggle
- Graph panel shows disabled message when include_related=false
- Raw JSON is hidden by default; Show button reveals it
- Error panel shown on network failure or structured backend error
- Navigation sidebar: Bundles no longer shows "soon" badge

---

### Phase 12B — Dashboard Issue Review Drill-Down

Phase 12B is a frontend-only phase. No new backend tests were added (all 202 backend tests still pass).

**Verification steps for Phase 12B:**

```bash
# Frontend build verification
cd ui
npm run build      # must produce no TypeScript errors

# Backend suite (unchanged — 202 tests)
py mcp/test_verify.py

# Vault validation and security scan
py run.py validate
py run.py security
```

**What was added:**
- `ui/src/components/Dashboard.svelte` — Issue Review section below overview: cross-panel summary row, five tabs (Validation, Tasks, Security, Missing Concepts, Feedback), expandable task rows, full findings/entries lists, raw JSON blocks hidden by default; `expandedTaskIds` Set + `toggleTask` helper; `activeIssueTab` state
- `ui/src/layouts/AppLayout.astro` — footer updated to Phase 12B

**Manual acceptance checks:**
- Issue Review section appears below the dashboard card grid
- All five tabs render without errors (even when vault has no data)
- Cross-panel summary row shows correct counts
- Validation tab: shows invalid note paths or pass state
- Tasks tab: task rows are clickable; expansion shows instruction, missing sections, constraints, feedback weight, raw task JSON
- Security tab: shows findings table or clean pass state
- Missing Concepts tab: shows ranked list or MISSING_CONCEPTS_EMPTY warning
- Feedback tab: shows all entries or empty state
- Raw JSON is collapsed by default on all tabs

---

### Phase 12A — Dashboard Data Completeness and API Coverage

Phase 12A is a frontend-only phase. No new backend tests were added (all 202 Phase 11A tests still pass).

**Verification steps for Phase 12A:**

```bash
# Frontend build verification
cd ui
npm run build      # must produce no TypeScript errors

# Backend suite (unchanged — 202 tests)
py mcp/test_verify.py

# Vault validation and security scan
py run.py validate
py run.py security
```

**What was added:**
- `ui/src/lib/api.ts` — `fetchTasks`, `fetchMissing`, `fetchFeedback`; updated `fetchSecurity`; new types `Task`, `TasksData`, `MissingConcept`, `MissingData`, `FeedbackEntry`, `FeedbackData`
- `ui/src/components/Dashboard.svelte` — full rewrite: parallel loading via `Promise.all`, top health row (4 mini-cards), 8 data cards (health, summary, validation, tasks, missing concepts, feedback, index info, security), loading skeletons, raw JSON expanders
- `ui/src/layouts/AppLayout.astro` — footer updated to Phase 12A

---

### Phase 11B — Guided Vault Bootstrap UI Form

Phase 11B is a frontend-only phase. No new backend tests were added (all 202 Phase 11A tests still pass).

**Verification steps for Phase 11B:**

```bash
# Frontend build verification (run from repo root)
cd ui
npm install        # if node_modules absent
npm run build      # must produce ui/dist/ with no TypeScript errors

# Backend suite (unchanged — 202 tests)
py mcp/test_verify.py

# Vault validation
py run.py validate

# Security scan
py run.py security
```

**What was added:**
- `ui/src/components/VaultSetup.svelte` — Svelte island with full form, live validation, preview panel, submit, success/error/warning handling
- `ui/src/pages/vault-setup.astro` — replaced PlaceholderPage with `<VaultSetup client:load />`
- `ui/src/lib/api.ts` — `VaultBootstrapRequest`, `VaultBootstrapResponse` types and `bootstrapVault()` function
- `ui/src/layouts/AppLayout.astro` — Vault Setup no longer shows "soon" badge; phase footer updated

**Manual verification checklist (no automated frontend unit tests in this phase):**
- Vault Setup page loads at `/app/vault-setup`
- All five fields render correctly
- Validation panel updates live as fields change
- Preview panel reflects current field values
- Sections can be added and removed
- Expected Concepts can be added and removed
- Submit button disabled when form is invalid or loading
- On success: created file list and warnings shown
- On error: error code and message shown with friendly title
- Network failure displays backend-unavailable message
- Dashboard link works from success panel
- `npm run build` completes with zero TypeScript errors

---

## Interpreting Failures

### `AssertionError` with test name printed

The test assertion failed. The printed message explains what was expected vs what was received. Most failures indicate a regression in the affected feature.

### `ImportError` or `ModuleNotFoundError`

Missing dependency. Install with:
```bash
pip install -r requirements.txt
pip install -r mcp/requirements.txt
```

### `PACKAGE_EXISTS` during CLI export tests

A previous test run left a package in `dist/`. The test suite cleans up after export tests. If residue remains, delete `dist/` manually:
```bash
rmdir /s /q dist
```
The `dist/` directory is gitignored — this is safe.

### HTTP tests fail on connection refused

The test suite starts a `TestClient` (in-process ASGI client) — it does not require a running server. If tests fail on import of `TestClient`, install `mcp/requirements.txt`.

---

## Generated Artefacts in Tests

Export tests write to `dist/context-bundles/` and clean up after themselves using `shutil.rmtree`. Module-level export tests use `tempfile.mkdtemp()` for isolation. Neither creates permanent state in the repository.

The `dist/` directory is gitignored and should not be committed.

---

## Adding New Tests

1. Add test functions to `mcp/test_verify.py` following the existing naming convention.
2. Add the function call to the `if __name__ == "__main__":` block at the bottom of the file.
3. Run the full suite to confirm all tests pass.
4. Update this document if adding a new test category.
