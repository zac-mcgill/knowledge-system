# Context Vault Engine - Testing

All tests live in `mcp/test_verify.py`. The suite currently has 985 test functions, all of which are executed by the manual runner in `main()` at the bottom of that file. A passing run prints `ALL VERIFICATION TESTS PASSED`. Historical test counts from earlier phases (272, 382, 429, 467, 507, 548, 553, 564, 587, 607, 625, 650, 675, 695, 706, 721, 740, 763, 787, 800, 818, 842, 866, 890, 913, 937) appear later in this document as part of the phase changelog and are not the current total.

## Current Verification Summary

A full local verification consists of:

```bash
py mcp/test_verify.py           # 985 tests, all must pass
py run.py validate              # vault schema-compliance
py run.py security              # status: pass (or warning, never fail)
py run.py feedback              # exits 0, valid JSON
py run.py export --overwrite    # status: ok; package written to dist/
cd ui; npm run build            # zero errors
```

Every release should pass all six steps.

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
py run.py app                   # starts server and opens browser (requires built UI)
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

- **Test 1** `test_basic_functionality` - all vaults load and index correctly.
- **Test 2** `test_deterministic_ordering` - index and query results are sorted deterministically.
- **Test 3** `test_concurrent_queries` - 20 concurrent queries produce consistent results.
- **Test 4** `test_schema_hash_tracking` - schema hash is stored and retrievable.
- **Test 5** `test_pagination_stable` - pages are bounded, non-overlapping, and stable.
- **Test 6** `test_path_traversal_blocked` - path traversal attacks are rejected.
- **Test 7** `test_strict_mode` / filter validation - unknown fields rejected in both strict and non-strict mode.
- **Test 8** `test_limit_and_timeout` - limits are respected; max limit is clamped to 500.
- **Test 9** `test_typed_responses` - all responses follow the typed contract.
- **Test 10** `test_cross_vault_queries` - aggregate works across all vaults.
- **Test 11** `test_rate_limiter` - in-memory rate limiter enforces 50 req/s *(requires mcp/requirements.txt)*.
- **Test 12** `test_schema_refresh_cooldown` - schema reload respects 2-second cooldown.
- **Test 13** `test_index_metadata` - index metadata is populated after build.
- **Test 14** `test_config_validation` - startup config validation catches missing vaults.
- **Test 15** `test_structured_logging` - structured logging is active *(requires mcp/requirements.txt)*.
- **Test 16** `test_concurrent_build_and_query` - concurrent build + query does not crash.

### Contract Tests

- `test_contract_runner_pass` - contract checks pass for demo vault.
- `test_contract_schema_interface` - schema exposes required functions.
- `test_contract_index_integrity` - index fields match expected shape.
- `test_contract_query_determinism` - repeated queries return identical results.
- `test_contract_lightweight` - lightweight contract check completes without error.

### Phase 0 - Query Correctness Tests

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

### Phase 1 - API Route Tests

- `test_p1_http_smoke` - HTTP server starts and responds.
- `test_p1_validation_adapter` - `GET /validation` returns structured result.
- `test_p1_tasks_full_path` - each task includes a full vault-relative POSIX path.
- `test_p1_tasks_constraints` - each task includes writing constraints.
- `test_p1_notes_full_paths` - each note includes a full vault-relative POSIX path.
- `test_p1_quality_adapter` - `GET /quality` returns structured result.
- `test_p1_missing_adapter` - `GET /missing` returns gap data for demo vault (`EXPECTED_CONCEPTS` populated with 5 Fundamentals concepts).
- `test_p1_compare_missing_file` - `POST /compare` with non-existent file returns error.
- `test_p1_graph_build` - `GET /graph/{vault}` returns nodes and edges.
- `test_p1_graph_related` - `GET /graph/{vault}/related` returns related nodes.
- `test_p1_graph_missing_neighbors` - `GET /graph/{vault}/missing` returns missing concepts.
- `test_p1_unknown_vault_structured_error` - unknown vault returns structured 404.
- Vault param tests: validation, tasks, notes, quality, missing all accept `?vault=` param.

### Phase 2 - Bundle Generation Tests

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

### Phase 3 - Feedback Tests

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

### Phase 4 - Export Tests

21 tests:

- Export writes the required package files (historical Phase 4: six files; Phase 17A added `context.html`, bringing the current package to seven files).
- `context.json` is valid bundle JSON.
- `context.md` contains required fields.
- `manifest.json` lists every package file with hashes (six at Phase 4, seven from Phase 17A onwards).
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

### Phase 5 - Security Scan Tests

49 tests (39 original + 10 coverage regression):

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

**Coverage regression tests (P5-COV):**
- `test_p5_cov_default_scan_covers_all_vault_notes` - default scan covers all content notes (note_count == total vault notes).
- `test_p5_cov_default_scan_includes_partial_notes` - notes with `status=partial` are included in default scan.
- `test_p5_cov_vault_files_excluded` - generated/system files under `Vault Files/` are never in `source_paths`.
- `test_p5_cov_coverage_metadata_present` - response `scanned` block includes `total_notes`, `coverage`, `truncated`.
- `test_p5_cov_filtered_scan_still_works` - explicit `filters={"status":"complete"}` still scans only complete notes.
- `test_p5_cov_api_default_scan_covers_all_notes` - `POST /context/security` with default args scans all vault notes.
- `test_p5_cov_cli_security_covers_all_notes` - `py run.py security` default scan covers all demo-vault content notes.
- `test_p5_cov_api_response_includes_coverage_metadata` - API response includes coverage metadata fields.
- `test_p5_cov_allow_partial_false_no_partial_in_scan` - `allow_partial=False` correctly excludes partial notes.
- `test_p5_cov_existing_response_fields_preserved` - `status`, `findings`, `summary`, `scanned.note_count`, `scanned.source_paths` all still present.

### Phase 6 - Documentation Consistency Test

- `test_p6_docs_consistency` - all 7 required docs files exist; README mentions correct project name; QUICKSTART has no stale naming; API.md covers all registered routes.

### Phase 7 - Deterministic Lexical Query Search Tests

23 tests covering lexical search on `POST /query`:

- `test_p7_q_omitted_preserves_behaviour` - `q` omitted produces identical results to plain query.
- `test_p7_q_blank_preserves_behaviour` - `q=""` and `q="   "` behave the same as `q` omitted; no `score` key in results.
- `test_p7_q_returns_positive_score_results` - `q="recursion"` returns only notes with `score > 0`.
- `test_p7_q_no_match_returns_empty` - `q` with no matches returns `count=0` and empty results.
- `test_p7_q_combined_with_filters` - `q` combined with filters applies both constraints; all results satisfy both.
- `test_p7_q_deterministic_repeated` - three identical calls return identical results.
- `test_p7_q_ranking_deterministic` - results are in non-increasing score order.
- `test_p7_q_score_range` - all scores in `(0.0, 1.0]`.
- `test_p7_q_overlong_rejected` - `q` > 1000 chars returns `INVALID_QUERY`.
- `test_p7_q_fields_invalid_rejected` - unsupported `q_fields` value returns `INVALID_QUERY` with offending field listed.
- `test_p7_q_fields_body` - `q_fields=["body"]` searches note body text.
- `test_p7_q_fields_path` - `q_fields=["path"]` searches note path.
- `test_p7_q_fields_frontmatter` - `q_fields=["frontmatter"]` searches frontmatter field values.
- `test_p7_q_http_api` - `POST /query` with `q` works over HTTP TestClient; results include `score`.
- `test_p7_q_http_no_match` - HTTP `POST /query` no-match returns `count=0`.
- `test_p7_q_http_invalid_q_fields` - HTTP invalid `q_fields` returns HTTP 400 `INVALID_QUERY`.
- `test_p7_q_http_overlong_q` - HTTP overlong `q` returns HTTP 400 `INVALID_QUERY`.
- `test_p7_q_no_score_when_q_absent` - no `score` key in results when `q` is absent.
- `test_p7_tiebreak_by_path` - equal-score notes are sorted by path ascending.
- `test_p7_lexical_timeout_returns_partial` - lexical scoring loop timeout returns `status='partial'` with `warning='query timeout'`.
- `test_p7_partial_lexical_results_sorted_deterministically` - partial lexical results are still sorted deterministically (score desc, then path asc).
- `test_p7_q_omitted_timeout_unchanged` - `q` omitted with a near-zero timeout still returns `partial` or `ok`; no `score` key in results.
- `test_p7_q_fields_empty_returns_invalid_query` - `q_fields=[]` returns `INVALID_QUERY`.

### Phase 9 - Schema Data Tests

4 tests covering `SCHEMA_VERSION` and `EXPECTED_CONCEPTS`:

- `test_p9_schema_version_defined` - `vault_schema.py` exposes `SCHEMA_VERSION = '3.0.0'`.
- `test_p9_bundle_manifest_schema_version` - bundle `manifest.schema_version` equals `'3.0.0'`.
- `test_p9_export_manifest_schema_version` - exported `manifest.json` contains `schema_version = '3.0.0'`.
- `test_p9_missing_returns_concept_gaps` - `GET /missing` returns `total_expected=5`, `total_missing=5`, one subdomain, and a ranked gap list.

### Phase 10 - Local Web UI Foundation Tests

8 tests verifying the `/app` endpoint and that it does not break existing API routes:

- `test_p10_app_no_500_when_ui_not_built` - `GET /app` returns 503 with `UI_NOT_BUILT` error (not 500) when `ui/dist` has not been built.
- `test_p10_app_does_not_break_health` - `GET /health` remains functional after hitting `/app`.
- `test_p10_app_does_not_break_vaults` - `GET /vaults` remains functional after hitting `/app`.
- `test_p10_app_does_not_break_summary` - `GET /summary?vault=<name>` works after hitting `/app`.
- `test_p10_app_does_not_break_validation` - `GET /validation?vault=<name>` works after hitting `/app`.
- `test_p10_app_does_not_break_security` - `POST /context/security` works after hitting `/app`.
- `test_p10_app_path_traversal_blocked` - `/app/<traversal>` returns 400 `PATH_TRAVERSAL` (or safe SPA fallback); no sensitive file content leaks.
- `test_p10_summary_accepts_vault_param` - `GET /summary?vault=<name>` returns valid summary; `GET /summary` (no param) is backwards-compatible; `GET /summary?vault=__nonexistent__` returns 404 `INVALID_VAULT`.

### Phase 11A - Guided Vault Bootstrap Backend API Tests

14 tests covering the `POST /vault/bootstrap` endpoint, `core/shared/bootstrap_service.py`, and CLI compatibility:

- `test_p11a_valid_bootstrap_creates_vault` - Valid inputs create a vault directory with files listed in `created`.
- `test_p11a_path_traversal_rejected` - `vault_name` values containing `..` or path separators are rejected before any file write.
- `test_p11a_absolute_path_rejected` - Absolute paths as `vault_name` are rejected.
- `test_p11a_duplicate_vault_rejected` - Requesting a `vault_name` that already exists returns a validation error.
- `test_p11a_empty_domain_rejected` - Empty or whitespace-only `domain` is rejected with an error mentioning `domain`.
- `test_p11a_invalid_note_type_rejected` - `note_type` values that don't match the slug pattern (e.g. uppercase, underscore, space) are rejected.
- `test_p11a_too_few_sections_rejected` - Fewer than 2 non-whitespace sections are rejected.
- `test_p11a_duplicate_sections_rejected` - Duplicate sections (case-insensitive) are rejected.
- `test_p11a_config_updated_atomically` - After bootstrap `config/config.yaml` is valid YAML with `vault_root` pointing to the new vault.
- `test_p11a_vault_has_schema` - Bootstrapped vault contains `Vault Files/Scripts/vault_schema.py` with `VALID_TYPES` and `DOMAIN_MAP`.
- `test_p11a_vault_has_templates` - Bootstrapped vault contains at least one `.md` template file with section headers.
- `test_p11a_cli_bootstrap_still_importable` - `core.bootstrap_vault` is importable and exports `main`, `collect_input`, `_create_vault_structure`, and `_update_config`.
- `test_p11a_api_bootstrap_success_envelope` - `POST /vault/bootstrap` with valid inputs returns HTTP 200 with standard `status/data` envelope, and `data` contains `vault`, `created`, and `warnings`.
- `test_p11a_api_bootstrap_invalid_input_errors` - Various invalid inputs return structured `status/error/code/message` responses with 400 or 422 status.

### Phase 15A - Note Browser Read-Only Inspector UI

Phase 15A is a frontend-only phase. No backend changes were made (all 222 backend tests still pass).

**Verification steps for Phase 15A:**

```bash
cd ui && npm run build     # must complete with 0 errors; NoteBrowser.svelte compiled
py mcp/test_verify.py      # 222 tests - all must pass
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
```

**Manual checks for Phase 15A:**

1. Start the backend: `py mcp/server/mcp_server.py`
2. Serve the built UI: `cd ui && npx serve dist`
3. Navigate to `http://localhost:3000/app/notes`
4. Confirm the vault selector loads vaults and selects the first one.
5. Confirm notes appear in the list with name, status badge, difficulty badge, and missing-sections badge.
6. Confirm the text filter narrows the list in real time.
7. Confirm the status and difficulty dropdowns filter correctly; confirm "Clear" resets all filters.
8. Confirm "Missing sections only" checkbox filters to notes with at least one missing section.
9. Click a note - confirm the detail panel loads on the right with path, frontmatter fields, section outline, body, validation context, and task context.
10. Confirm the validation panel shows WARN for a known-invalid note, or PASS for a valid note.
11. Confirm the improvement task panel shows task details (priority, missing sections, constraints) when a task exists, or "No active improvement task" when none.
12. Expand the Query Search panel; enter a search term; click **Search**; confirm results appear with relevance scores.
13. Click a search result and confirm note detail loads.
14. Click **Clear search** and confirm the base note list returns.
15. Confirm all raw JSON panels are hidden by default behind `<details>` expanders.
16. Confirm the Notes nav item no longer shows a "soon" badge.
17. Confirm no save buttons, edit inputs, or write controls are present anywhere on the page.

**What was added:**

- `ui/src/components/NoteBrowser.svelte` - full Note Browser island. Vault selector, filter controls (text/status/difficulty/missing-only + clear), collapsible Query Search panel (q, q_fields checkboxes, status/difficulty/domain/type filters, limit, search/clear), note list with status/difficulty/missing badges and selected highlight, two-column desktop layout, note detail panel (header with badges, frontmatter fields table, section outline from Markdown headings, read-only body, validation context, task/improvement context with feedback weight behind details), raw JSON expanders for note detail and query responses, notes list response expander in left column.
- `ui/src/lib/api.ts` - added `NoteListItem`, `NotesData`, `NoteFields`, `NoteDetail`, `NoteQueryRequest`, `QueryResultItem`, `NoteQueryResponse` types; added `fetchNotes`, `fetchNote`, `queryNotes` functions.
- `ui/src/pages/notes.astro` - replaced `PlaceholderPage` with `<NoteBrowser client:load />`.
- `ui/src/layouts/AppLayout.astro` - removed "Notes" from placeholder items; removed "soon" badge from Notes nav item; updated footer to "Phase 15A - Note Browser".
- `QUICKSTART.md` - added §6i Note Browser UI section.
- `TESTING.md` - added Phase 15A section (this entry).
- `ROADMAP.md` - added Phase 15A Complete row; Phase 15 moved to Partial/In Progress.

### Phase 15B - Safe Note Edit Backend API

Phase 15B added the `PUT /note` HTTP endpoint with path safety, schema validation, and atomic writes. No UI changes were made in Phase 15B itself; the safe note editing UI was added in Phase 15C.

**Verification steps for Phase 15B:**

```bash
py mcp/test_verify.py      # 242 tests - all must pass (20 new Phase 15B tests added)
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
```

**Tests added (20 total):**

- `test_p15b_serialise_note_markdown` - `serialise_note_markdown()` produces canonical YAML frontmatter + body, omits None/empty fields, renders booleans as `true`/`false`, output is re-parseable by vault schema.
- `test_p15b_service_layer_rejects_traversal` - `validate_note_update_request()` blocks path traversal, absolute paths, non-`.md` paths, and `Vault Files/` paths at the service layer.
- `test_p15b_expire_index_cooldown` - `expire_index_cooldown()` sets `last_schema_check` to `0.0` under the vault lock.
- `test_p15b_put_note_success` - `PUT /note` with a fully valid request returns HTTP 200 with `status: ok`, `path`, `fields`, `body`, and `validation: {status: pass, errors: []}`.
- `test_p15b_put_note_response_shape` - Response envelope includes all required keys: `path`, `fields`, `body`, `validation`, `warnings`.
- `test_p15b_get_note_reflects_put` - `GET /note` immediately returns the updated body after a successful `PUT /note`.
- `test_p15b_query_reflects_put` - `POST /query` finds the updated note in results after a successful `PUT /note`.
- `test_p15b_validation_reflects_put` - `GET /validation` does not list the note in `invalid_notes` after a valid `PUT /note`.
- `test_p15b_rejects_path_traversal` - HTTP 400/404 for path traversal attempts (multiple attack vectors including URL-encoded and backslash variants).
- `test_p15b_rejects_absolute_path` - HTTP 400 with `PATH_TRAVERSAL` or `INVALID_NOTE_PATH` for absolute path input.
- `test_p15b_rejects_non_md_path` - HTTP 400 `INVALID_NOTE_PATH` for paths not ending in `.md`.
- `test_p15b_rejects_vault_files_path` - HTTP 400 `INVALID_NOTE_PATH` for paths inside `Vault Files/`.
- `test_p15b_rejects_missing_note` - HTTP 404 `NOT_FOUND` for a note that does not exist on disk.
- `test_p15b_rejects_unknown_field` - HTTP 400 `INVALID_INPUT` when request `fields` contains an unknown schema field.
- `test_p15b_rejects_invalid_enum` - HTTP 400 `VALIDATION_FAILED` for an invalid enum value in `status`.
- `test_p15b_rejects_domain_mismatch` - HTTP 400 for a domain value that does not match the path-derived domain.
- `test_p15b_rejects_section_bool_mismatch` - HTTP 400 `VALIDATION_FAILED` when `has_key_principles: true` but the Key Principles section has no content.
- `test_p15b_rejects_null_byte_in_body` - HTTP 400 `INVALID_INPUT` when body contains a null byte.
- `test_p15b_failed_put_leaves_original_unchanged` - Disk file is identical to original when `PUT /note` fails validation.
- `test_p15b_no_temp_files_left_behind` - No temporary files remain in the note directory after a successful `PUT /note`.
- `test_p15b_existing_get_note_still_works` - `GET /note` for an existing note still returns correct data after Phase 15B changes.

**What was added:**

- `mcp/core/note_write.py` - new service module: `serialise_note_markdown`, `_check_path_safety`, `_validate_body`, `validate_note_update_request`, `_validate_candidate`, `update_note`, `invalidate_note_caches`, `_error_response`.
- `mcp/core/note_index.py` - added `expire_index_cooldown(vault_name)` function.
- `mcp/server/mcp_server.py` - added `NoteUpdateRequest` Pydantic model; added `PUT /note` endpoint.
- `mcp/test_verify.py` - added 21 Phase 15B test functions (3 service-layer + 18 HTTP-level).
- `API.md` - added `PUT /note` to Route Index and endpoint documentation.
- `QUICKSTART.md` - added §4e note update API usage.
- `TESTING.md` - added Phase 15B section (this entry).
- `ROADMAP.md` - marked Phase 15B Complete.

### Phase 17A - HTML Bundle Renderer

Phase 17A adds a deterministic static HTML rendering (`context.html`) to every exported context package. No UI framework changes were made. 12 new backend tests were added.

**Verification steps for Phase 17A:**

```bash
py mcp/test_verify.py      # all tests must pass (12 new Phase 17A tests added)
py run.py export --overwrite   # status: ok; context.html listed in files
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
cd ui && npm run build     # must complete with 0 errors
```

**New tests added (P17A-H*):**

- `test_p17a_export_includes_context_html` - export package includes `context.html`.
- `test_p17a_manifest_includes_context_html` - `manifest.json` lists `context.html` with sha256 and bytes.
- `test_p17a_manifest_html_hash_matches_file` - SHA-256 in manifest matches actual file content.
- `test_p17a_existing_files_unchanged` - `context.json`, `context.md`, and other files are unchanged.
- `test_p17a_html_is_deterministic` - identical bundle input produces byte-for-byte identical HTML.
- `test_p17a_html_escapes_script_injection` - `<script>alert(1)</script>` in note body is HTML-escaped.
- `test_p17a_html_escapes_frontmatter` - unsafe frontmatter/warning values are HTML-escaped.
- `test_p17a_html_no_remote_assets` - HTML contains no `http://`, `https://`, `<script`, `javascript:`, or `onclick=`.
- `test_p17a_html_contains_artefact_warning` - generated artefact warning is present.
- `test_p17a_html_contains_metadata` - bundle ID, vault, and created_at appear in HTML.
- `test_p17a_html_contains_notes` - note paths, fields, and sections appear in HTML.
- `test_p17a_html_contains_manifest_hashes` - manifest hash table is rendered when package_files provided.

**Updated existing tests (P4):**

- `test_p4_export_writes_all_seven_files` (was `all_six_files`) - expected set now includes `context.html`.
- `test_p4_manifest_contains_all_files` - expected manifest file set now includes `context.html`.
- `test_p4_no_extra_files_in_package` - expected set updated to 7 files.
- `test_p4_cli_export_returns_valid_json` - now asserts 7 files in return value.
- `test_p4_cli_export_writes_package_dir` - expected disk file set updated.
- `test_p4_api_export_ok` - now asserts 7 files in API response.

**Manual checks for Phase 17A:**

1. Run `py run.py export --overwrite`.
2. Locate the generated package under `dist/context-bundles/<bundle-id>/`.
3. Confirm these files exist: `context.json`, `context.md`, `context.html`, `manifest.json`, `validation.json`, `graph.json`, `feedback-summary.json`.
4. Open `context.html` locally in a browser - confirm it is readable.
5. Confirm the generated artefact warning appears at the top.
6. Confirm bundle metadata (ID, vault, created_at) is visible.
7. Confirm notes section renders (note paths and fields visible).
8. Confirm manifest hashes table shows file names and SHA-256 hashes.
9. Confirm no external network requests occur (check browser DevTools Network tab).
10. Confirm `manifest.json` includes a `context.html` entry with matching SHA-256.

**Security assertions:**

- All user-controlled content (note body, frontmatter values, warnings, graph labels) is HTML-escaped via `html.escape`.
- No `<script>` tags in generated HTML.
- No remote `http://` or `https://` URLs.
- No `javascript:` URLs.
- Note body/section text rendered in `<pre>` blocks (escaped text, not parsed Markdown).
- CSS is inline in a `<style>` block - no external stylesheet links.

**What was added:**

- `core/shared/context_html.py` - new module: `render_context_html()`, `_escape()`, `_render_*` helper functions. Python standard library only (`html`, `json`).
- `core/shared/context_package.py` - imports `render_context_html`; generates `context.html` bytes before manifest; adds `context.html` to `files_info` and `manifest["files"]`; writes `context.html` to package temp dir.
- `mcp/test_verify.py` - 12 new Phase 17A tests; 6 existing P4 tests updated for 7-file expectation.
- `README.md` - package artefact table includes `context.html`; Export capability description updated.
- `QUICKSTART.md` - export section updated to show `context.html` in output shape, file table, and notes.
- `TESTING.md` - added Phase 17A section (this entry); test count updated.
- `ROADMAP.md` - Phase 17A marked Complete.
- `API.md` - export package file list updated.

### Phase 17 - Distribution and Local App Launcher

Phase 17 adds the `py run.py app` command to start the local FastAPI server and open the browser UI in one step. No new external dependencies were added. 10 deterministic backend tests were added.

**Verification steps for Phase 17:**

```bash
py mcp/test_verify.py          # all tests must pass (10 new Phase 17 launcher tests)
py run.py validate             # 19/19 valid
py run.py security             # status: pass
py run.py feedback             # exits 0, valid JSON
py run.py export --overwrite   # status: ok; 7 files including context.html
cd ui && npm run build         # must complete with 0 errors
cd ..
py run.py app                  # starts server, opens browser to http://127.0.0.1:8000/app
```

**Server detection cases tested manually:**

1. No server running → server starts, browser opens.
2. Compatible server already running → reuses it, opens browser.
3. Port occupied by another process → clear error message, exits 1.
4. `ui/dist` missing → prints build instructions, starts API-only server.

**What was added:**

- `core/app_launcher.py` - new module: `check_ui_built()`, `probe_server()`, `is_context_vault_health_response()`, `wait_for_server()`, `open_browser()`, `launch_server()`, `main()`. Standard library only.
- `run.py` - `app` command added to `USAGE` string; dispatches to `core.app_launcher.main(repo_root)`.
- `mcp/test_verify.py` - 10 new Phase 17 launcher tests (constants, health validator, connection refused, UI build detection, command dispatch).
- `README.md` - `py run.py app` added to quick-start commands; Local App Launcher section added.
- `QUICKSTART.md` - Local App Launcher section added under Section 6.
- `TESTING.md` - added Phase 17 section (this entry); test count updated.
- `ROADMAP.md` - Phase 17 marked Complete; active phase updated to Phase 18.

### Phase 18 - CI and Release Hardening

Phase 18 adds GitHub Actions CI, a release checklist, artefact hygiene checks, and README badge. No new external dependencies were added. 7 deterministic backend tests were added.

**Verification steps for Phase 18:**

```bash
py mcp/test_verify.py      # 272 tests - all must pass (7 new Phase 18 tests added)

py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok; 7 files including context.html
cd ui && npm run build     # must complete with 0 errors
cd ..
git status --short         # no dist/ or ui/dist/ entries
```

**Tests added (7 total, P18-A through P18-G):**

- `test_p18_release_checklist_exists` - `RELEASE_CHECKLIST.md` exists in repository root.
- `test_p18_workflow_file_exists` - `.github/workflows/verify.yml` exists.
- `test_p18_workflow_triggers` - workflow `on:` block references both `push` and `pull_request`.
- `test_p18_workflow_required_commands` - workflow text contains `requirements.txt`, `mcp/requirements.txt`, `mcp/test_verify.py`, `run.py validate`, `run.py security`, `run.py feedback`, and `run.py export --overwrite`.
- `test_p18_gitignore_excludes_dist` - `.gitignore` contains both `dist/` and `ui/dist/`.
- `test_p18_readme_has_ci_badge` - `README.md` references the `verify.yml` badge.
- `test_p18_release_checklist_coverage` - `RELEASE_CHECKLIST.md` contains all required verification and release sections.

**What was added:**

- `.github/workflows/verify.yml` - GitHub Actions workflow: checkout, Python 3.12, install both requirements files, run test suite, validate, security, feedback, export, artefact hygiene check, Node 20 + `npm ci` + `npm run build`.
- `RELEASE_CHECKLIST.md` - concise pre-release checklist covering verification, versioning, and GitHub release steps.
- `.gitignore` - added `.pytest_cache/` entry.
- `README.md` - CI badge added below title; test count updated to 272.
- `mcp/test_verify.py` - 7 new Phase 18 tests.
- `TESTING.md` - added Phase 18 section (this entry); test count updated to 272.
- `ROADMAP.md` - Phase 18 marked Complete; active phase updated to Phase 19.

### Phase 19 - Context Controller Layer

Deterministic vault state aggregator and recommendation engine. Two new API endpoints and a full UI page. 19 tests added.

**Verification steps:**

```bash
py mcp/test_verify.py      # 341 tests - all must pass (19 new P19 tests added)
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok; 7 files including context.html
cd ui && npm run build     # must complete with 0 errors
```

**Tests added (19 total, P19-S1 through P19-S5, P19-P1 through P19-P8, P19-R1, P19-D1, P19-UI1 through P19-UI3):**

- `test_p19_context_state_basic_shape` - GET /context/state returns required top-level fields.
- `test_p19_context_state_readiness_flags` - readiness contains all seven expected boolean flags.
- `test_p19_context_state_service_sections` - state contains all six service-level sub-sections and summary.
- `test_p19_context_state_unknown_vault` - GET /context/state with unknown vault returns 404 INVALID_VAULT.
- `test_p19_context_state_deterministic` - two identical calls return the same readiness, blockers, warnings, and summary.
- `test_p19_context_plan_basic_shape` - POST /context/plan returns required top-level fields.
- `test_p19_context_plan_recommendation_shape` - each recommendation has rank, action, severity, title, reason, source, links.
- `test_p19_context_plan_all_intents_succeed` - all five valid intents return 200 ok.
- `test_p19_context_plan_invalid_intent` - POST /context/plan with unknown intent returns 400 INVALID_INTENT.
- `test_p19_context_plan_unknown_vault` - POST /context/plan with unknown vault returns 404 INVALID_VAULT.
- `test_p19_context_plan_default_intent` - POST /context/plan without intent defaults to `"review"`.
- `test_p19_context_plan_deterministic` - same vault+intent always produces same recommendation list.
- `test_p19_controller_read_only` - repeated state/plan calls leave the vault note count unchanged.
- `test_p19_controller_python_direct` - `get_context_state()` and `build_context_plan()` work without HTTP layer.
- `test_p19_controller_ui_files` - controller.astro and ContextController.svelte are present and contain correct symbols.
- `test_p19_controller_api_ts` - api.ts exports `fetchContextState`, `fetchContextPlan`, and four typed interfaces.
- `test_p19_controller_nav` - AppLayout.astro includes a Controller nav item linking to `/app/controller`.
- `test_p19_next_best_action_shape` - `next_best_action` is null or has `action` + `title` fields.

**Files changed:**

- `mcp/core/context_controller.py` (NEW) - `get_context_state(vault_name)` and `build_context_plan(vault_name, intent)`; aggregates validation, security, tasks, missing, feedback, and graph; computes readiness flags, blockers, warnings, and ranked recommendations.
- `mcp/server/mcp_server.py` - added `ContextPlanRequest` model, `GET /context/state`, and `POST /context/plan` endpoints.
- `ui/src/lib/api.ts` - added `fetchContextState()`, `fetchContextPlan()`, and interfaces `ContextStateData`, `ContextPlanData`, `ContextReadiness`, `ContextRecommendation`.
- `ui/src/pages/controller.astro` (NEW) - Astro page for `/app/controller`.
- `ui/src/components/ContextController.svelte` (NEW) - full UI component with vault/intent selectors, readiness grid, service summary table, recommendation list, and raw JSON toggles.
- `ui/src/layouts/AppLayout.astro` - added "Controller" nav item linking to `/app/controller`.
- `mcp/test_verify.py` - 19 new Phase 19 tests.
- `API.md` - added `GET /context/state` and `POST /context/plan` endpoint documentation.
- `ROADMAP.md` - Phase 19 marked Complete; active phase updated to 20.
- `TESTING.md` - added Phase 19 section (this entry).

### Phase 20 - MCP Compatibility Layer

MCP stdio server exposing all vault capabilities as JSON-RPC 2.0 tools, resources, and prompts. Read-only and deterministic. 41 tests added.

**Verification steps:**

```bash
py mcp/test_verify.py      # 382 tests - all must pass (41 new P20 tests added)
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok; 7 files including context.html
cd ui && npm run build     # must complete with 0 errors
```

**Tests added (41 total):**

Protocol tests:
- `test_p20_initialize_returns_correct_shape` - initialize returns protocolVersion, serverInfo, capabilities.
- `test_p20_notification_produces_no_response` - notifications/initialized produces no response.
- `test_p20_ping_returns_result` - ping returns valid result.
- `test_p20_unknown_method_returns_32601` - unknown method returns -32601.
- `test_p20_invalid_json_returns_32700` - invalid JSON returns -32700 parse error.
- `test_p20_logs_not_written_to_stdout` - logs go to stderr, only JSON-RPC on stdout.

Tools tests:
- `test_p20_tools_list_deterministic` - tools/list returns same alphabetically-sorted list on each call.
- `test_p20_tool_names_prefixed` - all tool names start with `cve.`.
- `test_p20_tools_list_required_tools` - all 10 required CVE tools present.
- `test_p20_tools_have_object_schema` - every tool has `inputSchema.type = "object"`.
- `test_p20_tools_call_unknown_returns_error` - unknown tool returns `isError=true`.
- `test_p20_tool_list_vaults_works` - `cve.list_vaults` returns vault list.
- `test_p20_tool_get_context_state_works` - `cve.get_context_state` returns state for demo-vault.
- `test_p20_tool_get_context_plan_works` - `cve.get_context_plan` returns plan for demo-vault.
- `test_p20_tool_query_notes_lexical` - `cve.query_notes` returns results for lexical query.
- `test_p20_tool_get_note_path_traversal_blocked` - `cve.get_note` blocks `../` traversal attempts.
- `test_p20_tool_security_scan_full_vault` - `cve.security_scan` covers all vault notes.
- `test_p20_tool_build_context_bundle_no_write` - `cve.build_context_bundle` builds in-memory, writes no files.

Resources tests:
- `test_p20_resources_list_deterministic` - resources/list returns same URIs on each call.
- `test_p20_resource_read_vaults` - `cve://vaults` returns vault list.
- `test_p20_resource_read_vault_state` - vault state resource returns valid state data.
- `test_p20_resource_read_unknown_returns_error` - unknown URI returns structured error in contents.
- `test_p20_resource_path_safety` - unregistered vault name in URI returns `INVALID_VAULT`.

Prompts tests:
- `test_p20_prompts_list_required` - prompts/list returns all 4 required CVE prompts.
- `test_p20_prompt_get_vault_review` - `cve.vault_review` returns messages referencing vault and CVE tools.
- `test_p20_prompt_get_unknown_returns_error` - unknown prompt name returns -32602.
- `test_p20_prompts_no_destructive_language` - all prompts include safety language.

Safety tests:
- `test_p20_no_destructive_tools` - no delete/edit/create/write tools exposed.
- `test_p20_tool_calls_deterministic` - repeated identical tool calls return the same result.

**Files changed:**

- `mcp/core/mcp_protocol.py` (NEW) - JSON-RPC 2.0 protocol handler: parse, dispatch, respond, error codes.
- `mcp/core/mcp_tools.py` (NEW) - 10 CVE tools: catalogue and dispatch using late imports.
- `mcp/core/mcp_resources.py` (NEW) - 9 resource URI patterns: list and read with vault validation.
- `mcp/core/mcp_prompts.py` (NEW) - 4 CVE prompts with safety footer.
- `mcp/server/mcp_stdio_server.py` (NEW) - Main MCP stdio server loop (stdin→stdout, logs→stderr).
- `run.py` - added `mcp` command; updates USAGE string.
- `mcp/test_verify.py` - 41 new Phase 20 tests.
- `API.md` - added MCP Compatibility Layer section.
- `QUICKSTART.md` - added section 6m covering MCP stdio server.
- `README.md` - updated capabilities summary and test count to 382.
- `TESTING.md` - added Phase 20 section (this entry).
- `ROADMAP.md` - Phase 20 marked Complete.

---

### Phase 21 - Private Cloud Mode

Self-hostable private cloud mode: token-based API authentication, read-only remote enforcement, and `/private/status` configuration endpoint. 14 tests added.

**Verification steps:**

```bash
py mcp/test_verify.py      # 396 tests - all must pass (14 new P21 tests added)
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok; 7 files including context.html
cd ui && npm run build     # must complete with 0 errors
```

**Tests added (14 total):**

- `test_p21_config_defaults_local_safe` - default config has `enabled=False`, `require_auth=False`, no warnings.
- `test_p21_private_mode_enabled_reports_correctly` - private mode enabled with token: `enabled=True`, `require_auth=True`, `token_configured=True`, `remote_read_only=True`.
- `test_p21_private_status_shape_no_token_leak` - `/private/status` response has correct shape; raw token never in response.
- `test_p21_read_route_without_token_returns_401` - `GET /vaults` returns 401 `AUTH_REQUIRED` when auth required and no token supplied.
- `test_p21_read_route_with_bearer_token_succeeds` - `Authorization: Bearer <token>` succeeds on read route.
- `test_p21_read_route_with_x_cve_token_succeeds` - `X-CVE-Token: <token>` succeeds on read route.
- `test_p21_invalid_token_returns_401` - wrong token returns 401 `AUTH_REQUIRED`.
- `test_p21_write_route_blocked_read_only` - mutating route returns 403 `REMOTE_READ_ONLY` in read-only mode (valid auth supplied).
- `test_p21_write_route_allowed_when_read_only_false` - mutating route is not blocked by read-only guard when `CVE_REMOTE_READ_ONLY=false`.
- `test_p21_health_no_token_leak` - `/health` response does not contain the configured token value.
- `test_p21_docs_mention_private_cloud` - `README.md`, `API.md`, and `DEPLOYMENT.md` all mention Private Cloud Mode.
- `test_p21_api_docs_error_codes` - `API.md` contains `AUTH_REQUIRED` and `REMOTE_READ_ONLY` error code documentation.
- `test_p21_deployment_md_complete` - `DEPLOYMENT.md` contains Tailscale, WireGuard, Cloudflare Tunnel, reverse proxy, backup, and token guidance.
- `test_p21_existing_tests_unaffected` - local mode (env vars unset) leaves existing test behaviour unchanged; no auth errors on normal routes.

**Files created:**

- `mcp/core/private_cloud.py` - private cloud configuration module: `load_private_cloud_config`, `is_private_cloud_enabled`, `is_remote_read_only`, `get_expected_token`, `require_auth`, `auth_status_summary`, `private_cloud_status`, `verify_token`. Pure stdlib.
- `DEPLOYMENT.md` - deployment guide: private cloud overview, access models (Tailscale, WireGuard, Cloudflare Tunnel, Nginx, Caddy), environment variable table, local example, VPS systemd service, firewall guidance, backup guidance, update procedure, verification commands.

**Files modified:**

- `mcp/server/mcp_server.py` - imported private cloud helpers; updated CORS to allow `Authorization` and `X-CVE-Token` headers; added `_WRITE_PATH_PREFIXES` set; added `_AUTH_EXEMPT_PATHS` set; added `_is_write_path()`, `_check_private_cloud_config()` helpers; updated `request_middleware` with auth check and read-only enforcement; added `GET /private/status` endpoint.
- `API.md` - added `/private/status` endpoint, `AUTH_REQUIRED` and `REMOTE_READ_ONLY` error codes, environment auth behaviour, token header formats.
- `README.md` - added Private Cloud Mode capability line; updated test count to 396.
- `QUICKSTART.md` - added Private Cloud Mode section.
- `TESTING.md` - added Phase 21 section (this entry); updated test count to 396.
- `ROADMAP.md` - Phase 21 marked Complete.
- `mcp/test_verify.py` - 14 new Phase 21 tests.

**Security model:**

- Token comparison uses `secrets.compare_digest` (constant-time, no timing oracle).
- Token never written to logs, responses, or status output.
- `/health` and `/private/status` are always accessible without authentication.
- Read-only enforcement is applied before route-level validation.
- Local mode (all env vars unset) is completely unchanged.

---

### Phase 22 - Session and Project State

File-backed session tracking and project state layer. Local LLMs can answer "where was I?" deterministically from stored state. No database, no cloud sync, no embeddings. 33 tests added.

**Verification steps:**

```bash
py mcp/test_verify.py      # 507 tests - all must pass (38 new P23 tests added)
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py session          # prints session summary as JSON
py run.py project-state    # prints project state as JSON
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok
cd ui && npm run build     # must complete with 0 errors
```

**Tests added (33 total, P22-1 through P22-33):**

*Service layer (P22-1 to P22-15):*
- `test_p22_start_session_returns_active` - `start_session` returns `status=active` with valid session_id.
- `test_p22_session_file_written` - session file written at `Vault Files/State/sessions/<id>.json` with correct content.
- `test_p22_resume_session_returns_latest_active` - `resume_session` (no ID) returns the most-recent active session.
- `test_p22_resume_session_by_id` - `resume_session` with explicit `session_id` returns the correct session.
- `test_p22_summarise_session_shape` - `summarise_session` returns compact dict with all required keys.
- `test_p22_attach_note_adds_to_recent_notes` - `attach_note_to_session` adds note to `recent_notes`.
- `test_p22_attach_note_deduplicates` - duplicate attach calls result in single entry in `recent_notes`.
- `test_p22_close_session_marks_closed` - `close_session` sets `status=closed` and writes `closed_at`.
- `test_p22_resume_no_active_after_close` - `resume_session` returns `SESSION_NOT_FOUND` when all sessions are closed.
- `test_p22_list_sessions_ordering` - `list_sessions` returns sessions most-recent-first.
- `test_p22_get_project_state_defaults` - `get_project_state` returns default dict with all required keys when no file exists.
- `test_p22_update_project_state_writes` - `update_project_state` persists and can be read back.
- `test_p22_update_project_state_rejects_unknown_fields` - unknown/forbidden fields return `INVALID_PROJECT_STATE`.
- `test_p22_session_id_format` - session_id matches `YYYYMMDDTHHMMSS-xxxxxxxx` regex.
- `test_p22_atomic_write_valid_json` - session file contains valid JSON with sorted keys.

*HTTP layer (P22-16 to P22-25):*
- `test_p22_http_start_session` - `POST /session/start` returns 200 with `session_id`.
- `test_p22_http_session_resume` - `GET /session/resume` returns active session.
- `test_p22_http_session_summary` - `GET /session/summary` returns compact summary.
- `test_p22_http_attach_note` - `POST /session/attach-note` attaches a note.
- `test_p22_http_close_session` - `POST /session/close` closes session with `status=closed`.
- `test_p22_http_get_project_state` - `GET /project/state` returns project state with required keys.
- `test_p22_http_update_project_state` - `PUT /project/state` updates and persists `current_phase`.
- `test_p22_http_update_project_state_rejects_bad_fields` - unknown fields return 400/422.
- `test_p22_http_write_routes_blocked_read_only` - `POST /session/start` returns 403 `REMOTE_READ_ONLY` in read-only mode.
- `test_p22_http_read_routes_allowed_read_only` - `GET /project/state` not blocked in read-only mode.

*MCP layer (P22-26 to P22-28):*
- `test_p22_mcp_session_tools_registered` - all 7 session/project-state tools listed by `tools/list`.
- `test_p22_mcp_resume_work_prompt_registered` - `cve.resume_work` listed by `prompts/list`.
- `test_p22_mcp_session_resources_registered` - `session/current` and `project-state` resource URIs listed by `resources/list`.

*Documentation tests (P22-29 to P22-32):*
- `test_p22_readme_mentions_session` - `README.md` mentions session state.
- `test_p22_quickstart_mentions_session` - `QUICKSTART.md` mentions session/project state.
- `test_p22_api_md_documents_session_endpoints` - `API.md` documents all 4 main session/project-state endpoints.
- `test_p22_testing_md_updated_count` - `TESTING.md` contains test count 429.

*Regression test (P22-33):*
- `test_p22_existing_tests_unaffected` - all original tools, prompts, and session_state API remain present.

**Files created:**

- `mcp/core/session_state.py` - session and project state service: `start_session`, `resume_session`, `summarise_session`, `attach_note_to_session`, `close_session`, `list_sessions`, `get_project_state`, `update_project_state`, `_atomic_write_json`. Pure stdlib. All functions accept `_vault_path` for test isolation.

**Files modified:**

- `mcp/server/mcp_server.py` - 4 new entries in `_WRITE_PATH_PREFIXES`; 4 new Pydantic request models; 7 new HTTP endpoints.
- `mcp/core/mcp_tools.py` - 7 new tools in `TOOLS` catalogue; tool implementations; `_check_remote_read_only()` helper.
- `mcp/core/mcp_resources.py` - 2 new resource templates; `_read_session_current` and `_read_project_state` handlers.
- `mcp/core/mcp_prompts.py` - `cve.resume_work` prompt added.
- `run.py` - `session` and `project-state` CLI commands; updated USAGE string.
- `README.md` - session/project state capability bullet; updated test count to 429.
- `QUICKSTART.md` - Phase 22 section added.
- `API.md` - Session and Project State section with all 7 endpoints; new error codes table entries.
- `TESTING.md` - added Phase 22 section (this entry); updated test count to 429.
- `ROADMAP.md` - Phase 22 marked Complete.
- `mcp/test_verify.py` - 33 new Phase 22 tests.

---

## Phase 23 - Safe Memory Write Queue

LLM-proposed note changes are stored as pending change proposals in a file-backed queue. Nothing is written to vault notes until a human explicitly accepts. Supports `create_note_draft`, `suggest_note_update`, and `update_note_section_draft`. Proposals carry a unified diff, schema validation, staleness hash protection, and a full audit trail. 38 tests added.

**Verification steps:**

```bash
py mcp/test_verify.py      # 507 tests - all must pass (38 new P23 tests added)
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py pending          # prints pending changes as JSON
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok
cd ui && npm run build     # must complete with 0 errors
```

**Tests added (38 total, P23-1 through P23-38):**

*Service layer (P23-1 to P23-17):*
- `test_p23_pending_changes_module_imports` - module imports without error; key functions present.
- `test_p23_pending_root_path` - pending root resolves to `Vault Files/State/pending-changes/`.
- `test_p23_path_traversal_blocked` - traversal paths return `INVALID_NOTE_PATH`.
- `test_p23_create_note_draft` - `create_note_draft` creates change JSON on disk.
- `test_p23_create_note_draft_rejects_existing` - draft for existing note path returns `NOTE_EXISTS`.
- `test_p23_suggest_note_update_diff` - `suggest_note_update` produces a non-empty diff.
- `test_p23_update_note_section_draft` - section draft replaces only the named section.
- `test_p23_missing_section` - missing section heading returns `VALIDATION_FAILED`.
- `test_p23_list_ordering` - `list_pending_changes` returns changes sorted newest-first.
- `test_p23_review_full_object` - `review_pending_change` returns all required fields.
- `test_p23_reject_archives` - `reject_pending_change` moves change to archive directory.
- `test_p23_accept_applies` - `accept_pending_change` writes note to vault.
- `test_p23_accept_revalidates` - accept revalidates before write; fails if validation fails.
- `test_p23_accept_stale_hash` - accept detects stale hash mismatch and returns `STALE_PENDING_CHANGE`.
- `test_p23_accepted_archived` - accepted change is moved to archive.
- `test_p23_invalid_cannot_be_accepted` - change with `validation_status=fail` cannot be accepted.
- `test_p23_json_sorted_keys` - pending change JSON files use sorted keys.

*HTTP layer (P23-18 to P23-27):*
- `test_p23_http_list_pending` - `GET /memory/pending` returns 200 with correct shape.
- `test_p23_http_create_note_draft` - `POST /memory/create-note-draft` returns 200 with change_id.
- `test_p23_http_suggest_note_update` - `POST /memory/suggest-note-update` returns change with diff.
- `test_p23_http_update_section_draft` - `POST /memory/update-section-draft` returns change.
- `test_p23_http_get_pending` - `GET /memory/pending/{id}` returns full change object.
- `test_p23_http_reject` - `POST /memory/pending/{id}/reject` archives the change.
- `test_p23_http_accept` - `POST /memory/pending/{id}/accept` applies change.
- `test_p23_http_missing_vault` - missing vault param returns 422/400.
- `test_p23_http_private_cloud_auth` - unauthenticated requests return 401 in private cloud mode.
- `test_p23_http_read_only_blocks_write` - mutating routes return 403 `REMOTE_READ_ONLY` in read-only mode.

*MCP layer (P23-28 to P23-31):*
- `test_p23_mcp_pending_tools_registered` - all 7 pending-change tools listed by `tools/list`.
- `test_p23_mcp_review_prompt_registered` - `cve.review_pending_change` listed by `prompts/list`.
- `test_p23_mcp_pending_resource_registered` - `pending-changes` resource URI listed by `resources/list`.
- `test_p23_mcp_pending_resource_read` - resource returns `status=ok` and `changes` array.

*UI build test (P23-32):*
- `test_p23_ui_build` - `npm run build` in `ui/` completes without errors.

*Documentation tests (P23-33 to P23-38):*
- `test_p23_readme_mentions_pending` - `README.md` mentions Safe Memory Write Queue.
- `test_p23_quickstart_mentions_pending` - `QUICKSTART.md` mentions pending changes.
- `test_p23_api_md_documents_pending_endpoints` - `API.md` documents pending-change endpoints.
- `test_p23_testing_md_updated_count` - `TESTING.md` mentions test count 467.
- `test_p23_roadmap_phase23_complete` - `ROADMAP.md` marks Phase 23 complete.
- `test_p23_existing_tests_unaffected` - all original tools, prompts, and note_write API remain present.

**Files created:**

- `mcp/core/pending_changes.py` - full pending-change service: `create_note_draft`, `suggest_note_update`, `update_note_section_draft`, `list_pending_changes`, `review_pending_change`, `accept_pending_change`, `reject_pending_change`, `validate_pending_change`. Pure stdlib. All functions accept `_vault_path` for test isolation.
- `ui/src/components/PendingChanges.svelte` - vault selector, change list, detail panel with diff display, accept/reject with confirmation.
- `ui/src/pages/pending.astro` - UI page for the Pending Changes view.

**Files modified:**

- `mcp/server/mcp_server.py` - 4 new entries in `_WRITE_PATH_PREFIXES`; 4 Pydantic models; 7 HTTP endpoints.
- `mcp/core/mcp_tools.py` - 7 new tools; Phase 23 `_tool_*` implementations; dispatch entries.
- `mcp/core/mcp_resources.py` - 1 new resource template; `_read_pending_changes` handler.
- `mcp/core/mcp_prompts.py` - `cve.review_pending_change` prompt added.
- `run.py` - `pending` CLI command; updated USAGE string.
- `ui/src/lib/api.ts` - `PendingChange` type and all 7 API functions.
- `ui/src/layouts/AppLayout.astro` - `Pending` nav item added.
- `README.md` - Safe Memory Write Queue capability bullet; updated test count to 467.
- `QUICKSTART.md` - Phase 23 section added.
- `API.md` - Safe Memory Write Queue section with all 7 endpoints.
- `TESTING.md` - added Phase 23 section (this entry); updated test count to 467.
- `ROADMAP.md` - Phase 23 marked Complete; Phase 24 set as next.
- `mcp/test_verify.py` - 38 new Phase 23 tests.

---

## Phase 24 - Context Profiles and Budget Modes

40 new tests (`test_p24_1` through `test_p24_40`).

**Key tests:**
- `test_p24_1` - `context_profiles` module imports without error.
- `test_p24_2` - built-in modes include tiny / small / medium / large / agent.
- `test_p24_3` - built-in device profiles include phone-local-llm / desktop-agent.
- `test_p24_4` - profile validation rejects unknown keys.
- `test_p24_5` - profile validation rejects empty include_sections.
- `test_p24_6` - profile validation enforces max_chars hard cap.
- `test_p24_7` - profile validation enforces max_notes hard cap.
- `test_p24_8` - `resolve_context_profile` returns deterministic data.
- `test_p24_9` - unknown profile name returns INVALID_PROFILE.
- `test_p24_10` - `GET /context/profiles` returns profiles and modes.
- `test_p24_11` - `GET /context/profiles/{name}` returns expected profile.
- `test_p24_12` - `POST /context/bundle` accepts mode=tiny.
- `test_p24_13` - `POST /context/bundle` accepts profile=phone-local-llm.
- `test_p24_14` - bundle response includes profile_metadata.
- `test_p24_15` - bundle ID is deterministic for identical profile request.
- `test_p24_16` - explicit non-profile bundle request remains backwards-compatible.
- `test_p24_17` - profile max_chars is enforced.
- `test_p24_18` - profile max_notes is enforced.
- `test_p24_19` - include_body=false profile excludes body.
- `test_p24_20` - include_related=true profile includes related.
- `test_p24_21` - include_sections in profile controls section extraction.
- `test_p24_22` - `POST /context/security` accepts profile/mode.
- `test_p24_23` - `POST /context/export` accepts profile/mode.
- `test_p24_24` - export manifest includes profile_metadata when used.
- `test_p24_25` - require_security_scan profile behaviour enforced/warned.
- `test_p24_26` - private-cloud auth protects profile endpoints when enabled.
- `test_p24_27` - private-cloud read-only does not block GET profile endpoints.
- `test_p24_28` - private-cloud read-only still blocks export writes.
- `test_p24_29` - MCP `cve.list_context_profiles` tool is listed.
- `test_p24_30` - MCP `cve.build_context_bundle` accepts profile/mode.
- `test_p24_31` - MCP `cve.security_scan` accepts profile/mode.
- `test_p24_32` - MCP resources expose profiles.
- `test_p24_33` - Bundle Builder UI builds with profile selector.
- `test_p24_34` - `API.md` documents profile endpoints.
- `test_p24_35` - `QUICKSTART.md` documents profile bundle usage.
- `test_p24_36` - `TESTING.md` mentions test count 507.
- `test_p24_37` - `ROADMAP.md` marks Phase 24 complete.
- `test_p24_38` - Existing Phase 21/22/23 tests still pass.
- `test_p24_39` - Existing CLI commands still pass.
- `test_p24_40` - No dist artefacts committed.

**Verification steps:**

```bash
py mcp/test_verify.py      # 507 tests - all must pass
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py profiles         # prints profiles/modes as JSON
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok
cd ui && npm run build     # must complete with 0 errors
```

**Files modified:**
- `mcp/core/context_profiles.py` - new profile service module.
- `mcp/server/mcp_server.py` - new endpoints; profile/mode on bundle/export/security.
- `mcp/core/mcp_tools.py` - `cve.list_context_profiles` tool; profile/mode on bundle/security tools.
- `mcp/core/mcp_resources.py` - `cve://context/profiles` resource and per-profile resources.
- `ui/src/lib/api.ts` - `ProfileMetadata` type; `fetchContextProfiles`; `fetchContextProfile`.
- `ui/src/components/BundleBuilder.svelte` - profile/mode selector; override labels; profile_metadata display.
- `run.py` - `profiles` CLI command.
- `README.md` - profiles endpoints table; CLI command.
- `QUICKSTART.md` - Phase 24 section added.
- `API.md` - Phase 24 endpoints documented.
- `TESTING.md` - added Phase 24 section (this entry); updated test count to 507.
- `ROADMAP.md` - Phase 24 marked Complete; Phase 25 set as next.
- `mcp/test_verify.py` - 40 new Phase 24 tests.

---

## Phase 24 - Context Profiles and Budget Modes

40 new tests (`test_p24_1` through `test_p24_40`).

**Key tests:**
- `test_p24_1` - `context_profiles` module imports without error.
- `test_p24_2` - built-in modes include tiny / small / medium / large / agent.
- `test_p24_3` - built-in device profiles include phone-local-llm / desktop-agent.
- `test_p24_4` - profile validation rejects unknown keys.
- `test_p24_5` - profile validation rejects empty include_sections.
- `test_p24_6` - profile validation enforces max_chars hard cap.
- `test_p24_7` - profile validation enforces max_notes hard cap.
- `test_p24_8` - `resolve_context_profile` returns deterministic data.
- `test_p24_9` - unknown profile name returns INVALID_PROFILE.
- `test_p24_10` - `GET /context/profiles` returns profiles and modes.
- `test_p24_11` - `GET /context/profiles/{name}` returns expected profile.
- `test_p24_12` - `POST /context/bundle` accepts mode=tiny.
- `test_p24_13` - `POST /context/bundle` accepts profile=phone-local-llm.
- `test_p24_14` - bundle response includes profile_metadata.
- `test_p24_15` - bundle ID is deterministic for identical profile request.
- `test_p24_16` - explicit non-profile bundle request remains backwards-compatible.
- `test_p24_17` - profile max_chars is enforced.
- `test_p24_18` - profile max_notes is enforced.
- `test_p24_19` - include_body=false profile excludes body.
- `test_p24_20` - include_related=true profile includes related.
- `test_p24_21` - include_sections in profile controls section extraction.
- `test_p24_22` - `POST /context/security` accepts profile/mode.
- `test_p24_23` - `POST /context/export` accepts profile/mode.
- `test_p24_24` - export manifest includes profile_metadata when used.
- `test_p24_25` - require_security_scan profile behaviour enforced/warned.
- `test_p24_26` - private-cloud auth protects profile endpoints when enabled.
- `test_p24_27` - private-cloud read-only does not block GET profile endpoints.
- `test_p24_28` - private-cloud read-only still blocks export writes.
- `test_p24_29` - MCP `cve.list_context_profiles` tool is listed.
- `test_p24_30` - MCP `cve.build_context_bundle` accepts profile/mode.
- `test_p24_31` - MCP `cve.security_scan` accepts profile/mode.
- `test_p24_32` - MCP resources expose profiles.
- `test_p24_33` - Bundle Builder UI builds with profile selector.
- `test_p24_34` - `API.md` documents profile endpoints.
- `test_p24_35` - `QUICKSTART.md` documents profile bundle usage.
- `test_p24_36` - `TESTING.md` mentions test count 507.
- `test_p24_37` - `ROADMAP.md` marks Phase 24 complete.
- `test_p24_38` - Existing Phase 21/22/23 tests still pass.
- `test_p24_39` - Existing CLI commands still pass.
- `test_p24_40` - No dist artefacts committed.

**Files modified:**
- `mcp/core/context_profiles.py` - new profile service module.
- `mcp/server/mcp_server.py` - new endpoints; profile/mode on bundle/export/security.
- `mcp/core/mcp_tools.py` - `cve.list_context_profiles` tool; profile/mode on bundle/security tools.
- `mcp/core/mcp_resources.py` - `cve://context/profiles` resource and per-profile resources.
- `ui/src/lib/api.ts` - `ProfileMetadata` type; `fetchContextProfiles`; `fetchContextProfile`.
- `ui/src/components/BundleBuilder.svelte` - profile/mode selector; override labels; profile_metadata display.
- `run.py` - `profiles` CLI command.
- `README.md` - profiles endpoints table; CLI command.
- `QUICKSTART.md` - Phase 24 section added.
- `API.md` - Phase 24 endpoints documented.
- `TESTING.md` - added Phase 24 section (this entry); updated test count to 507.
- `ROADMAP.md` - Phase 24 marked Complete; Phase 25 set as next.
- `mcp/test_verify.py` - 40 new Phase 24 tests.


## Phase 25 - Trust, Staleness, and Evidence Metadata

41 new tests (`test_p25_1` through `test_p25_41`).

**Key tests:**
- `test_p25_1` - `trust_metadata` module imports without error.
- `test_p25_2` - `extract_trust_metadata` returns all four trust fields from frontmatter.
- `test_p25_3` - `extract_trust_metadata` returns None for missing fields (backward compat).
- `test_p25_4` - `compute_staleness` returns True when review_after < today.
- `test_p25_5` - `compute_staleness` returns False when review_after >= today.
- `test_p25_6` - `compute_staleness` returns False when review_after is absent.
- `test_p25_7` - `compute_confidence` returns "high" for verified+authored.
- `test_p25_8` - `compute_confidence` returns "medium" for working level.
- `test_p25_9` - `compute_confidence` returns "low" for draft level.
- `test_p25_10` - `compute_confidence` returns "deprecated" for deprecated level.
- `test_p25_11` - `compute_confidence` returns "unknown" when trust_level is None.
- `test_p25_12` - `score_note_trust` returns higher score for verified+authored vs draft.
- `test_p25_13` - `score_note_trust` applies stale penalty when stale=True.
- `test_p25_14` - `annotate_notes_with_trust` attaches trust_metadata to each note dict.
- `test_p25_15` - `list_trust_summary` returns correct counts for demo vault.
- `test_p25_16` - `list_trust_summary` returns INVALID_VAULT for unknown vault.
- `test_p25_17` - `list_stale_notes` returns stale list for demo vault.
- `test_p25_18` - `list_stale_notes` returns INVALID_VAULT for unknown vault.
- `test_p25_19` - `build_evidence` returns notes sorted by trust score when prefer_verified=True.
- `test_p25_20` - `build_evidence` excludes deprecated notes when include_deprecated=False.
- `test_p25_21` - `build_evidence` includes deprecated notes when include_deprecated=True.
- `test_p25_22` - `build_evidence` result includes confidence_disclaimer.
- `test_p25_23` - `GET /trust` returns 200 with trust summary for demo vault.
- `test_p25_24` - `GET /trust` returns 404 for unknown vault.
- `test_p25_25` - `GET /stale` returns 200 with stale summary for demo vault.
- `test_p25_26` - `GET /stale` returns 404 for unknown vault.
- `test_p25_27` - `POST /evidence` returns 200 with evidence list.
- `test_p25_28` - `POST /evidence` with prefer_verified=True returns verified notes first.
- `test_p25_29` - `POST /evidence` with q filters notes by query string.
- `test_p25_30` - trust field validation in validate_vault accepts valid trust_level.
- `test_p25_31` - trust field validation rejects invalid trust_level.
- `test_p25_32` - trust field validation rejects invalid source_type.
- `test_p25_33` - trust field validation rejects malformed ISO date in last_reviewed.
- `test_p25_34` - trust field validation rejects malformed ISO date in review_after.
- `test_p25_35` - vault_schema.py has VALID_TRUST_LEVELS and VALID_SOURCE_TYPES.
- `test_p25_36` - MCP tool `cve.get_trust_summary` returns trust summary.
- `test_p25_37` - MCP tool `cve.get_stale_notes` returns stale data.
- `test_p25_38` - MCP tool `cve.build_evidence` returns evidence list.
- `test_p25_39` - MCP resource `cve://vault/{vault}/trust` readable.
- `test_p25_40` - MCP prompt `cve.evidence_review` includes cite-source instruction.
- `test_p25_41` - `ROADMAP.md` marks Phase 25 complete.

**Files modified:**
- `mcp/core/trust_metadata.py` - new service module: extract, score, annotate, summarise, stale, evidence.
- `demo-vault/Vault Files/Scripts/vault_schema.py` - VALID_TRUST_LEVELS, VALID_SOURCE_TYPES, trust fields in ALL_KNOWN_FIELDS.
- `core/shared/validate_vault.py` - _validate_trust_fields() called in validate_file().
- `mcp/server/mcp_server.py` - trust import; annotate on bundle/query; /trust /stale /evidence endpoints.
- `mcp/core/mcp_tools.py` - cve.get_trust_summary, cve.get_stale_notes, cve.build_evidence tools.
- `mcp/core/mcp_resources.py` - cve://vault/{vault}/trust and cve://vault/{vault}/stale resources.
- `mcp/core/mcp_prompts.py` - cve.evidence_review prompt with cite-source and disclaimer.
- `ui/src/lib/api.ts` - Trust/Stale/Evidence types and API functions.
- `ui/src/components/TrustEvidence.svelte` - new Trust & Evidence page component.
- `ui/src/pages/trust.astro` - new /app/trust page.
- `ui/src/layouts/AppLayout.astro` - Trust nav item added.
- `run.py` - trust and stale CLI commands.
- `README.md` - trust/evidence capability bullet; test count updated to 548.
- `QUICKSTART.md` - Phase 25 section added.
- `API.md` - /trust /stale /evidence endpoints documented.
- `TESTING.md` - added Phase 25 section (this entry); updated test count to 548.
- `ROADMAP.md` - Phase 25 marked Complete; Phase 26 set as next.
- `mcp/test_verify.py` - 41 new Phase 25 tests.

---

Safe vault deletion through API and UI. Users can permanently delete non-demo vaults via `DELETE /vault/{vault_name}` with explicit typed confirmation. A Danger Zone section was added to the Vault Setup page. 18 backend tests added.

**Verification steps:**

```bash
py mcp/test_verify.py      # 322 tests - all must pass (18 new P18C tests added)
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok; 7 files including context.html
cd ui && npm run build     # must complete with 0 errors
```

**Tests added (18 total, P18C-D1 through P18C-D15, P18C-UI1 through P18C-UI4):**

- `test_p18c_delete_requires_confirmation` - blank or whitespace confirm raises `CONFIRMATION_REQUIRED`.
- `test_p18c_delete_confirmation_mismatch` - wrong phrase raises `CONFIRMATION_MISMATCH`.
- `test_p18c_delete_unknown_vault` - unregistered vault name raises `INVALID_VAULT` (404).
- `test_p18c_delete_protected_vault` - `demo-vault` deletion raises `PROTECTED_VAULT` (403).
- `test_p18c_delete_last_vault` - deleting the only vault raises `LAST_VAULT`.
- `test_p18c_path_safety` - `assert_safe_vault_path` blocks paths outside the repo root with `PATH_TRAVERSAL`.
- `test_p18c_valid_delete_removes_directory` - `delete_vault()` removes the vault directory from disk.
- `test_p18c_valid_delete_updates_config` - deleted vault is removed from `vault_roots` in `config.yaml`.
- `test_p18c_valid_delete_updates_active_vault_in_config` - if deleted vault was `vault_root`, config falls back to `demo-vault`.
- `test_p18c_vaults_endpoint_does_not_list_deleted` - deleted vault is absent from `list_vaults()` after reload.
- `test_p18c_caches_cleared_after_delete` - `clear_vault_index()` and `clear_vault_cache()` evict stale entries.
- `test_p18c_path_name_abuse_rejected` - path-traversal names (`../demo-vault`, `..`) are rejected.
- `test_p18c_existing_bootstrap_flow_unaffected` - vault registry still works correctly after importing `vault_delete`.
- `test_p18c_demo_vault_unaffected` - `demo-vault` remains accessible, indexed, and populated after all delete tests.
- `test_p18c_api_delete_endpoint` - end-to-end `DELETE /vault/{name}` TestClient test covering all error cases and the happy path.
- `test_p18c_ui_has_danger_zone` - `VaultSetup.svelte` contains a Danger Zone section.
- `test_p18c_ui_no_delete_for_demo_vault` - `VaultSetup.svelte` marks demo-vault as protected.
- `test_p18c_api_has_delete_vault_helper` - `api.ts` exports `deleteVault`, `VaultDeleteRequest`, and `VaultDeleteResponse`.
- `test_p18c_vaultstate_has_clear` - `vaultState.ts` exports `clearStoredVault`.

**Files changed:**

- `mcp/core/vault_delete.py` (NEW) - service layer: `validate_delete_request()`, `assert_safe_vault_path()`, `update_config_after_delete()`, `delete_vault()`.
- `mcp/core/note_index.py` - added `clear_vault_index(vault_name)`.
- `mcp/core/result_cache.py` - added `clear_vault_cache(vault_name)`.
- `mcp/server/mcp_server.py` - added `VaultDeleteRequest` model and `DELETE /vault/{vault_name}` endpoint.
- `ui/src/lib/api.ts` - added `deleteVault()`, `VaultDeleteRequest`, `VaultDeleteResponse`.
- `ui/src/components/VaultSetup.svelte` - added Danger Zone section with vault selector, confirmation input, and delete button.
- `mcp/test_verify.py` - 18 new P18C tests.
- `API.md` - added `DELETE /vault/{vault_name}` endpoint documentation and error table entries.
- `QUICKSTART.md` - added "Deleting a Vault" section with API and UI instructions.
- `TESTING.md` - added Phase 18C section (this entry).
- `ROADMAP.md` - Phase 18C marked Complete.

### Phase 18B-U - Schema Builder UX Hardening

Bootstrap usability pass before Phase 19. Expected concepts are now written into generated `vault_schema.py` so that `GET /missing` works immediately after vault creation. 10 backend tests added.

**Verification steps:**

```bash
py mcp/test_verify.py      # 294 tests - all must pass (10 new P18BU tests added)
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok; 7 files including context.html
cd ui && npm run build     # must complete with 0 errors
```

**Tests added (10 total, P18BU-1 through P18BU-10):**

- `test_p18bu_expected_concepts_written_to_schema` - bootstrap with expected_concepts produces a `vault_schema.py` whose `EXPECTED_CONCEPTS` block contains the normalised slugs; result dict includes `expected_concepts.written`.
- `test_p18bu_expected_concepts_safe_repr` - malicious concept strings (shell injection, quote injection, null bytes, newlines) are safely escaped via `repr()`; generated schema compiles without syntax error.
- `test_p18bu_expected_concepts_deduplication` - duplicate concepts that produce the same slug after normalisation appear only once in the generated schema.
- `test_p18bu_schema_importable_with_concepts` - generated schema can be dynamically imported and exposes a `EXPECTED_CONCEPTS` dict with correct slug keys.
- `test_p18bu_no_concepts_still_works` - bootstrap without `expected_concepts` still generates a valid schema with `EXPECTED_CONCEPTS = {}`.
- `test_p18bu_api_response_reflects_concepts` - `POST /vault/bootstrap` API response includes `expected_concepts: {requested: N, written: N}`; no stale "not yet written" warning in response.
- `test_p18bu_missing_uses_bootstrapped_concepts` - `GET /missing?vault=<new-vault>` returns `total_expected=N, total_missing=N` immediately after bootstrap with expected concepts; no manual schema editing required.
- `test_p18bu_ui_no_stale_limitation_text` - `VaultSetup.svelte` source does not contain the stale "not yet written into" or "Backend limitation" warning text.
- `test_p18bu_generate_schema_deterministic` - identical inputs to `generate_schema_content()` produce byte-for-byte identical output across two calls.
- `test_p18bu_concepts_sorted_in_schema` - slugs appear in alphabetical order in the generated `EXPECTED_CONCEPTS` block.

**What was fixed:**

- `core/generate_schema.py` - added `_normalise_concept_slug()` and `_render_expected_concepts()` helpers; added `expected_concepts` parameter to `generate_schema_content()`; replaced hardcoded `EXPECTED_CONCEPTS = {}` template placeholder with `%EXPECTED_CONCEPTS%`.
- `core/shared/bootstrap_service.py` - `bootstrap_vault_noninteractive()` passes `expected_concepts_clean` to `generate_schema_content()`; removed stale "accepted but not written" warning; added `expected_concepts: {requested, written}` to result dict.
- `mcp/server/mcp_server.py` - updated `VaultBootstrapRequest.expected_concepts` description; updated `endpoint_vault_bootstrap` docstring; passes `expected_concepts` count through API response.
- `ui/src/components/VaultSetup.svelte` - removed amber "Backend limitation" warning box; updated helper text to explain concepts are written to schema; added success-panel info showing how many concepts were written.
- `ui/src/lib/api.ts` - added `expected_concepts?: {requested, written}` to `VaultBootstrapResponse`.
- `mcp/test_verify.py` - fixed `test_p11a_api_bootstrap_success_envelope` to remove stale assertion about "expected_concepts limitation" warning; added 10 new P18BU tests.
- `QUICKSTART.md`, `API.md`, `TESTING.md`, `ROADMAP.md` - updated to reflect new behaviour.

### Phase QAS - UI QA Stabilisation

UI QA pass before Phase 19. No new backend features. Targeted UI fixes and 6 source-level regression tests added.

**Verification steps:**

```bash
py mcp/test_verify.py      # 284 tests - all must pass (6 new PQAS tests added)
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok; 7 files including context.html
cd ui && npm run build     # must complete with 0 errors
```

**Tests added (6 total, PQAS-1 through PQAS-6):**

- `test_pqas_applayout_no_soon_badges` - AppLayout.astro must not contain `>soon<` nav badge spans.
- `test_pqas_applayout_footer_not_stale` - AppLayout.astro footer must not reference Phase 16 or older.
- `test_pqas_placeholderpage_no_stale_phase_text` - PlaceholderPage.astro must not contain "Planned for Phase" text.
- `test_pqas_all_routes_covered_in_route_test` - All 11 /app/* routes have corresponding Astro page files.
- `test_pqas_export_context_html_in_source` - context_package.py still includes context.html in the package.
- `test_pqas_feedback_envelope_regression` - GET /feedback returns standard `{status,data}` envelope, not flat response.

**What was fixed:**

- `ui/src/layouts/AppLayout.astro` - removed "soon" badge and opacity-60 from Validation, Tasks, API/Raw nav items; updated footer from "Phase 16 - Graph Explorer" to "Phase 18 - Stable".
- `ui/src/components/PlaceholderPage.astro` - replaced stale "Planned for Phase 12" text; added `cliCommand` prop for correct CLI references.
- `ui/src/pages/validation.astro` - updated PlaceholderPage to use `cliCommand="py run.py validate"`.
- `ui/src/pages/tasks.astro` - updated PlaceholderPage to use `cliCommand="py run.py improve"`.
- `ui/src/pages/raw.astro` - updated PlaceholderPage with correct API access note.
- `ui/src/components/GraphExplorer.svelte` - removed stale "Phase 16" from HTML comment.
- `README.md`, `TESTING.md` - test count updated to 284.

### Phase 16 - Visual Graph and Missing Concepts UI

Phase 16 is a frontend-only phase. No backend changes were made. All 242 backend tests still pass.

**Verification steps for Phase 16:**

```bash
cd ui && npm run build     # must complete with 0 errors; GraphExplorer.svelte ~31 kB
py mcp/test_verify.py      # 242 tests - all must pass
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
```

**Manual checks for Phase 16:**

1. Start the backend: `py mcp/server/mcp_server.py`
2. Serve the built UI: `cd ui && npx serve dist` (or `npm run dev` for dev server)
3. Navigate to the **Graph** link in the sidebar.
4. Confirm the page title "Graph Explorer" and the amber disclaimer appear.
5. Confirm the vault dropdown is pre-selected with the first registered vault.
6. Confirm graph summary cards load (total nodes, total edges, per-type counts).
7. Toggle node type filter buttons - confirm nodes of that type appear/disappear in the list.
8. Toggle edge type filter buttons - confirm the neighbour list in the Inspector respects them.
9. Type in the node search box - confirm the list filters by label/id.
10. Click any node in the Graph tab - confirm the Inspector tab activates automatically.
11. In the Inspector, confirm node id, type, and label are displayed.
12. Confirm direct neighbours are listed with their edge type badge.
13. Click **inspect →** on a neighbour - confirm the inspector updates to show that node.
14. Select a `note` node - confirm the **Related notes** and **Missing expected concepts near this note** sections appear.
15. Click the **Missing Concepts** tab - confirm summary cards load.
16. Confirm the ranked table shows concepts sorted by score descending.
17. Click **Draft action** on any ranked row - confirm the action card panel appears.
18. Confirm the action card header reads: **Draft action only - no file has been created**.
19. Click **Copy** - confirm the instruction text is copied to the clipboard.
20. Click **dismiss** - confirm the action card disappears without any file write.
21. Confirm all raw JSON panels are collapsed by default behind `<details>` elements.
22. Confirm the amber disclaimer on the page reads: *Schema-derived deterministic relationships, not semantic or AI-inferred links.*
23. Confirm existing Dashboard, Notes, Feedback, Bundles, Exports, and Security pages still load and route correctly.

**Known limitations:**

- The graph is displayed as a grouped node list, not as a visual network diagram. No heavy graph library (e.g. D3, Cytoscape) was added.
- The action card path suggestion (`Fundamentals/<title>.md`) is a conventional hint only. Users should verify the correct path against `vault_schema.py` before creating the note.
- `expected_concept` nodes selected in the Inspector show neighbours but not related/missing (those queries are note-scoped only).

**What was added:**

- `ui/src/components/GraphExplorer.svelte` - new component: vault selector, reload button, node type filters, edge type filters, graph summary metrics, grouped searchable node browser, node inspector (neighbours + related notes + missing neighbours), missing concepts panel with ranked table and action card generator.
- `ui/src/pages/graph.astro` - new Astro page mounting `GraphExplorer` at `/app/graph`.
- `ui/src/lib/api.ts` - added `GraphNode`, `GraphEdge`, `GraphData`, `GraphNeighborEntry`, `GraphNeighborsData`, `GraphRelatedEntry`, `GraphRelatedData`, `GraphMissingEntry`, `GraphMissingNeighborsData`, `RankedMissingConcept` interfaces; added `fetchGraph`, `fetchGraphNeighbors`, `fetchGraphRelated`, `fetchGraphMissing` functions; added `subdomains?: number` to `MissingData`.
- `ui/src/layouts/AppLayout.astro` - added **Graph** nav item at `/app/graph`; updated footer to "Phase 16 - Graph Explorer".
- `QUICKSTART.md` - added §6k Graph Explorer UI section.
- `TESTING.md` - added Phase 16 section (this entry).
- `ROADMAP.md` - marked Phase 16 Complete.

### Phase 15C - Safe Note Editing UI

Phase 15C is a frontend-only phase. The `PUT /note` backend API (Phase 15B) is unchanged. All 242 backend tests still pass.

**Verification steps for Phase 15C:**

```bash
cd ui && npm run build     # must complete with 0 errors; NoteBrowser.svelte ~40 kB
py mcp/test_verify.py      # 242 tests - all must pass
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
```

**Manual checks for Phase 15C:**

1. Start the backend: `py mcp/server/mcp_server.py`
2. Serve the built UI: `cd ui && npx serve dist`
3. Navigate to `http://localhost:3000/app/notes`
4. Confirm the existing inspect mode still works (all Phase 15A manual checks still apply).
5. Select a note - confirm the **Edit note** button appears in the note header.
6. Click **Edit note** - confirm the header border turns blue, an EDIT MODE badge appears, and Save / Reset / Cancel buttons replace the Edit button.
7. Confirm the **Frontmatter Fields** panel switches to an editable form with checkboxes for booleans and text inputs for strings.
8. Change a string field (e.g. `status`); confirm the **Unsaved changes** badge appears.
9. Click **Reset to loaded** - confirm the form resets to original values and the Unsaved badge disappears.
10. Confirm the **Section Outline** panel shows the live section outline from the editable body, updating as you type.
11. Add a section heading to the body; confirm the outline updates in real time.
12. Remove all text from the body textarea and click **Save changes** - confirm client-side validation blocks the save with "Body must not be empty."
13. Click **Cancel** - confirm edit mode exits and inspect mode is restored without any changes.
14. Enter edit mode again, make a valid change to a note, and click **Save changes** - confirm:
    - A spinner appears on the button during save.
    - On success: a green confirmation panel appears, the note detail updates, edit mode exits, and the note list / validation / task panels refresh.
15. Enter edit mode, set `status` to an invalid value (e.g. `invalid-status`), and click **Save changes** - confirm:
    - The page stays in edit mode.
    - A red error panel with `VALIDATION_FAILED` and the details list appears.
    - Local edits are preserved.
16. Confirm the **Raw JSON** section now includes an expander for "Last update response (PUT /note)" and "Current edit payload preview" (visible only in edit mode).
17. Confirm no note creation or deletion controls exist anywhere on the page.
18. Confirm switching to a different note while in edit mode exits edit mode cleanly.

**What was added:**

- `ui/src/components/NoteBrowser.svelte` - extended with inspect/edit mode: `enterEditMode`, `cancelEdit`, `resetToLoaded`, `saveNote` functions; structured frontmatter field editor (checkbox for booleans, text input for strings, read-only display for complex values); body textarea with character count; live section outline in edit mode with advisory missing-section warnings; save/cancel/reset action bar in note header; `EDIT MODE` badge and `Unsaved changes` badge; save success and error panels; additional raw JSON expanders for PUT /note response and edit payload preview; refresh of notes list, validation, and tasks after successful save; search results refresh if query was active.
- `ui/src/lib/api.ts` - added `NoteUpdateRequest`, `NoteUpdateValidation`, `NoteUpdateResponse` types; added `details?: unknown` to `ApiError`; added `updateNote(request: NoteUpdateRequest)` function using existing `put()` helper.
- `ui/src/layouts/AppLayout.astro` - updated footer from "Phase 15A - Note Browser" to "Phase 15C - Note Editing".
- `QUICKSTART.md` - added §6j Safe Note Editing UI section.
- `TESTING.md` - added Phase 15C section (this entry).
- `ROADMAP.md` - marked Phase 15C Complete and Phase 15 Complete.

Phase 14B is a frontend-only phase. No new backend tests were added (all 222 backend tests still pass).

**Verification steps for Phase 14B:**

```bash
cd ui && npm run build     # must complete with 0 errors; FeedbackWorkflow.svelte compiled
py mcp/test_verify.py      # 222 tests - all must pass
py run.py validate         # 19/19 valid
py run.py security         # status: pass
py run.py feedback         # exits 0, valid JSON
```

**Manual checks for Phase 14B:**

1. Start the backend: `py mcp/server/mcp_server.py`
2. Serve the built UI: `cd ui && npx serve dist`
3. Navigate to `http://localhost:3000/app/feedback`
4. Confirm the vault selector loads vaults and selects the first one.
5. Confirm feedback entries appear in the list (or an empty-state message).
6. Confirm the summary cards show correct counts (entries, warnings, errors, tasks, feedback-adjusted, top priority).
7. Confirm filters for path, signal, severity, and source work; confirm "Clear filters" resets them.
8. Add a new feedback entry via the Add Feedback form; confirm the list refreshes and shows the new entry.
9. Edit an entry (requires an id); confirm pre-fill, save, and list refresh.
10. Delete an entry; confirm the confirmation dialog and list refresh.
11. Run Normalise IDs from the Maintenance panel; confirm the success message and list refresh.
12. Confirm the Task Priority panel shows feedback-adjusted tasks.
13. Confirm raw JSON panels are hidden by default behind `<details>` expanders.
14. Confirm Feedback nav item no longer shows "soon" badge.

**What was added:**

- `ui/src/components/FeedbackWorkflow.svelte` - full Feedback Workflow island (32.70 kB built). Vault selector, summary cards (6 tiles), feedback list with 4-field filter + clear filters, backend warnings/errors panels, per-entry id/path/source/signal/severity/comment/created_at display, severity and signal badges, edit (inline expandable form) and delete (inline confirmation) actions with loading states, add feedback form with inline validation (path traversal check, required fields, 2000-char limit), Maintenance panel with Normalise IDs action, task priority panel (feedback-adjusted, expandable feedback_weight), raw JSON behind `<details>` expanders.
- `ui/src/lib/api.ts` - added `FeedbackSource`, `FeedbackSignal`, `FeedbackSeverity` type aliases; strengthened `FeedbackEntry` with optional `id` and `updated_at`; added `FeedbackResponse`, `FeedbackDeleteResponse`, `FeedbackNormaliseResponse`, `FeedbackCreateRequest`, `FeedbackUpdateRequest`; added `put` and `del` HTTP helpers; added `createFeedback`, `updateFeedback`, `deleteFeedback`, `normaliseFeedback` functions.
- `ui/src/pages/feedback.astro` - replaced `PlaceholderPage` with `<FeedbackWorkflow client:load />`.
- `ui/src/layouts/AppLayout.astro` - removed "Feedback" from placeholder items; removed "soon" badge from Feedback nav item; updated footer to "Phase 14B - Feedback Workflow".
- `QUICKSTART.md` - added §6h Feedback Workflow UI section.
- `TESTING.md` - added Phase 14B section (this entry).
- `ROADMAP.md` - marked Phase 14B Complete, Phase 14 Complete.

### Phase 14A - Feedback Write API and Task Workflow Backend Support

Phase 14A adds stable IDs and write operations to the feedback system. No UI changes were made.

**20 new tests added (222 total):**

- `test_p14a_idless_entries_still_parse` - Entries without an `id` field are still parsed successfully (backward compatibility).
- `test_p14a_normalise_adds_ids_without_dropping` - `normalise_entries()` adds IDs to id-less entries and preserves existing valid IDs, with no entries dropped.
- `test_p14a_post_feedback_adds_entry` - `POST /feedback` adds an entry; response contains `id`, all submitted fields, and valid `created_at`.
- `test_p14a_post_feedback_rejects_invalid_source` - `POST /feedback` with an unknown source returns HTTP 400 `INVALID_INPUT`.
- `test_p14a_post_feedback_rejects_invalid_signal` - `POST /feedback` with an unknown signal returns HTTP 400 `INVALID_INPUT`.
- `test_p14a_post_feedback_rejects_invalid_severity` - `POST /feedback` with an unknown severity returns HTTP 400 `INVALID_INPUT`.
- `test_p14a_post_feedback_rejects_empty_comment` - `POST /feedback` with blank or whitespace-only comment returns HTTP 400 `INVALID_INPUT`.
- `test_p14a_post_feedback_rejects_path_traversal` - `POST /feedback` with `../` in the path returns HTTP 400 `PATH_TRAVERSAL`.
- `test_p14a_post_feedback_rejects_unknown_note` - `POST /feedback` for a note file that doesn't exist returns HTTP 404 `NOTE_NOT_FOUND`.
- `test_p14a_put_feedback_updates_entry` - `PUT /feedback/{id}` updates signal and other fields on an existing entry.
- `test_p14a_put_feedback_preserves_id` - `PUT /feedback/{id}` does not change the entry's `id`.
- `test_p14a_put_feedback_preserves_created_at` - `PUT /feedback/{id}` does not change the entry's `created_at`.
- `test_p14a_put_feedback_rejects_unknown_id` - `PUT /feedback/{id}` with a non-existent ID returns HTTP 404 `FEEDBACK_NOT_FOUND`.
- `test_p14a_delete_feedback_removes_entry` - `DELETE /feedback/{id}` removes the entry; subsequent `GET /feedback` confirms it is absent.
- `test_p14a_delete_feedback_rejects_unknown_id` - `DELETE /feedback/{id}` with a non-existent ID returns HTTP 404 `FEEDBACK_NOT_FOUND`.
- `test_p14a_get_feedback_reflects_post` - `GET /feedback` reflects changes made by POST, PUT, and DELETE in sequence.
- `test_p14a_tasks_include_feedback_reflects_changes` - `GET /tasks?include_feedback=true` reflects feedback changes after a POST.
- `test_p14a_file_valid_and_readable_after_writes` - Feedback file is valid YAML parseable by `GET /feedback` after each write operation.
- `test_p14a_writes_confined_to_vault` - `validate_feedback_write` rejects path traversal attempts (`../`) with `PATH_TRAVERSAL` error code.
- `test_p14a_cli_feedback_still_works` - `py run.py feedback` still exits 0 and produces valid JSON after Phase 14A changes.

**Verification:**

```bash
py mcp/test_verify.py     # 222 tests - all must pass
py run.py validate        # 19/19 valid
py run.py security        # status: pass
py run.py feedback        # exits 0, valid JSON
```

**What was added:**

- `core/shared/feedback.py` - added ID generation (`_entry_id_digest`, `_unique_id`), `is_valid_feedback_id`, `_load_raw_entries`, `_serialise_entry`, `_write_feedback_atomic`, `normalise_entries`, `validate_feedback_write`, `add_feedback_entry`, `update_feedback_entry`, `delete_feedback_entry`, `normalise_feedback`; updated `_validate_entry` to preserve `id` in the clean dict
- `mcp/server/mcp_server.py` - added `PUT`/`DELETE` to CORS `allow_methods`; imported new feedback functions; added `FeedbackCreateRequest`/`FeedbackUpdateRequest` Pydantic models; added routes `POST /feedback/normalise`, `POST /feedback`, `PUT /feedback/{feedback_id}`, `DELETE /feedback/{feedback_id}`
- `API.md` - documented all four new endpoints and new error codes `FEEDBACK_NOT_FOUND` / `FEEDBACK_WRITE_FAILED`
- `QUICKSTART.md` - added feedback API quick-reference under §5c

### Phase 13C - Security Scan UI

Phase 13C is a frontend-only phase. No new backend tests were added (all 202 backend tests still pass).

**Verification steps for Phase 13C:**

```bash
# Frontend build verification
cd ui
npm run build      # must produce no TypeScript errors (SecurityScan.svelte built cleanly)

# Backend suite (unchanged - 202 tests)
py mcp/test_verify.py

# Vault validation and security scan
py run.py validate
py run.py security
```

**What was added:**
- `ui/src/lib/api.ts` - added `SecurityScanned` interface, `ContextSecurityResponse` type alias, `ContextSecurityRequest` interface, and `scanContextSecurity()` function calling `POST /context/security`
- `ui/src/components/SecurityScan.svelte` - full Security Scan island: vault selector, filter controls (status/domain/type/difficulty), section tag editor with duplicate/empty validation, content option checkboxes (include_body/allow_partial), budget number inputs, request preview panel, Run security scan button; result panel with Scan Overview (status badge, total findings, fail/warning/info counts, notes scanned, source path count), Findings (expandable cards with severity/path/rule/field/detail, severity filter buttons, text filter), Scanned Notes panel (per-path finding counts and F/W/I severity badges), Rule Summary panel (client-side rule breakdown), Raw JSON toggle
- `ui/src/pages/security.astro` - replaced PlaceholderPage with SecurityScan island
- `ui/src/layouts/AppLayout.astro` - removed "soon" badge from Security nav item; footer updated to Phase 13C

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

### Phase 13B - Export Package UI

Phase 13B is a frontend-only phase. No new backend tests were added (all 202 backend tests still pass).

**Verification steps for Phase 13B:**

```bash
# Frontend build verification
cd ui
npm run build      # must produce no TypeScript errors (ExportPackage.svelte built cleanly)

# Backend suite (unchanged - 202 tests)
py mcp/test_verify.py

# Vault validation and security scan
py run.py validate
py run.py security
```

**What was added:**
- `ui/src/lib/api.ts` - export types (`ExportFileInfo`, `ContextExportRequest`, `ContextExportResponse`) and `exportContextPackage()` function calling `POST /context/export`
- `ui/src/components/ExportPackage.svelte` - full Export Package island: vault selector, filter controls (status/domain/type/difficulty), section tag editor with duplicate/empty validation, content option checkboxes (include_body/include_related/allow_partial), budget number inputs, export options (overwrite/require_security_pass), Export Package button; result panel with Export Overview, Files/Manifest table (filename/bytes/SHA-256), Warnings panel, Raw JSON toggle; conflict panel for PACKAGE_EXISTS; security gate failure panel for SECURITY_SCAN_FAIL; request preview panel before export
- `ui/src/pages/exports.astro` - replaced PlaceholderPage with ExportPackage island
- `ui/src/layouts/AppLayout.astro` - removed "soon" badge from Exports nav item; footer updated to Phase 13B

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

### Phase 13A - Bundle Builder UI

Phase 13A is a frontend-only phase. No new backend tests were added (all 202 backend tests still pass).

**Verification steps for Phase 13A:**

```bash
# Frontend build verification
cd ui
npm run build      # must produce no TypeScript errors (BundleBuilder.svelte ~32 kB)

# Backend suite (unchanged - 202 tests)
py mcp/test_verify.py

# Vault validation and security scan
py run.py validate
py run.py security
```

**What was added:**
- `ui/src/lib/api.ts` - bundle types (`ContextBundleRequest`, `ContextBundleResponse`, `BundleNote`, `BundleBudget`, `BundleManifest`, `BundleFeedback`, `BundleGraph`) and `generateContextBundle()` function calling `POST /context/bundle`
- `ui/src/components/BundleBuilder.svelte` - full Bundle Builder island: vault selector, filter controls (status/domain/type/difficulty), section tag editor with duplicate/empty validation, content option checkboxes (include_body/include_related/allow_partial), budget number inputs, Generate Preview button; result panel with Overview, Budget bar, Notes list (expandable per note with sections/body/related/raw JSON), Feedback block, Graph Relationships summary, Raw JSON toggle
- `ui/src/pages/bundles.astro` - replaced PlaceholderPage with BundleBuilder island
- `ui/src/layouts/AppLayout.astro` - removed "soon" badge from Bundles nav item; footer updated to Phase 13A

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

### Phase 12B - Dashboard Issue Review Drill-Down

Phase 12B is a frontend-only phase. No new backend tests were added (all 202 backend tests still pass).

**Verification steps for Phase 12B:**

```bash
# Frontend build verification
cd ui
npm run build      # must produce no TypeScript errors

# Backend suite (unchanged - 202 tests)
py mcp/test_verify.py

# Vault validation and security scan
py run.py validate
py run.py security
```

**What was added:**
- `ui/src/components/Dashboard.svelte` - Issue Review section below overview: cross-panel summary row, five tabs (Validation, Tasks, Security, Missing Concepts, Feedback), expandable task rows, full findings/entries lists, raw JSON blocks hidden by default; `expandedTaskIds` Set + `toggleTask` helper; `activeIssueTab` state
- `ui/src/layouts/AppLayout.astro` - footer updated to Phase 12B

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

### Phase 12A - Dashboard Data Completeness and API Coverage

Phase 12A is a frontend-only phase. No new backend tests were added (all 202 Phase 11A tests still pass).

**Verification steps for Phase 12A:**

```bash
# Frontend build verification
cd ui
npm run build      # must produce no TypeScript errors

# Backend suite (unchanged - 202 tests)
py mcp/test_verify.py

# Vault validation and security scan
py run.py validate
py run.py security
```

**What was added:**
- `ui/src/lib/api.ts` - `fetchTasks`, `fetchMissing`, `fetchFeedback`; updated `fetchSecurity`; new types `Task`, `TasksData`, `MissingConcept`, `MissingData`, `FeedbackEntry`, `FeedbackData`
- `ui/src/components/Dashboard.svelte` - full rewrite: parallel loading via `Promise.all`, top health row (4 mini-cards), 8 data cards (health, summary, validation, tasks, missing concepts, feedback, index info, security), loading skeletons, raw JSON expanders
- `ui/src/layouts/AppLayout.astro` - footer updated to Phase 12A

---

### Phase 11B - Guided Vault Bootstrap UI Form

Phase 11B is a frontend-only phase. No new backend tests were added (all 202 Phase 11A tests still pass).

**Verification steps for Phase 11B:**

```bash
# Frontend build verification (run from repo root)
cd ui
npm install        # if node_modules absent
npm run build      # must produce ui/dist/ with no TypeScript errors

# Backend suite (unchanged - 202 tests)
py mcp/test_verify.py

# Vault validation
py run.py validate

# Security scan
py run.py security
```

**What was added:**
- `ui/src/components/VaultSetup.svelte` - Svelte island with full form, live validation, preview panel, submit, success/error/warning handling
- `ui/src/pages/vault-setup.astro` - replaced PlaceholderPage with `<VaultSetup client:load />`
- `ui/src/lib/api.ts` - `VaultBootstrapRequest`, `VaultBootstrapResponse` types and `bootstrapVault()` function
- `ui/src/layouts/AppLayout.astro` - Vault Setup no longer shows "soon" badge; phase footer updated

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
The `dist/` directory is gitignored - this is safe.

### HTTP tests fail on connection refused

The test suite starts a `TestClient` (in-process ASGI client) - it does not require a running server. If tests fail on import of `TestClient`, install `mcp/requirements.txt`.

---

## Generated Artefacts in Tests

Export tests write to `dist/context-bundles/` and clean up after themselves using `shutil.rmtree`. Module-level export tests use `tempfile.mkdtemp()` for isolation. Neither creates permanent state in the repository.

The `dist/` directory is gitignored and should not be committed.

---

## Phase 25 - Trust, Staleness, and Evidence Metadata

41 new tests (`test_p25_1` through `test_p25_41`), bringing the phase-test total to 548. Subsequent documentation passes added 16 drift guardrails (`test_doc_drift_*`), bringing the overall test count to 564.

**Highlights:**
- `test_p25_1` to `test_p25_22`: trust metadata service unit tests (extraction, staleness, confidence scoring, evidence builder, deprecated exclusion, confidence disclaimer).
- `test_p25_23` to `test_p25_29`: HTTP endpoints `GET /trust`, `GET /stale`, `POST /evidence` (shapes, 404 paths, prefer_verified ordering, q filter).
- `test_p25_30` to `test_p25_35`: schema validation for `trust_level`, `source_type`, `last_reviewed`, `review_after` field values and date formats.
- `test_p25_36` to `test_p25_38`: MCP tools `cve.get_trust_summary`, `cve.get_stale_notes`, `cve.build_evidence`.
- `test_p25_39`: MCP `trust` resource readable.
- `test_p25_40`: `cve.evidence_review` prompt includes cite instruction and safety footer.
- `test_p25_41`: ROADMAP marks Phase 25 Complete.

**Verification steps:**

```bash
py mcp/test_verify.py      # 587 tests, all must pass
py run.py validate         # all notes valid (trust fields accepted)
py run.py security         # status: pass
py run.py trust            # prints trust summary as JSON
py run.py stale            # prints stale list as JSON
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok
cd ui; npm run build       # zero errors
```

---

## Phase 26A - Markdown Folder Import Backend

23 new tests (`test_p26a_1` through `test_p26a_23`), bringing the phase-test total to 571. Combined with the 16 documentation drift guardrails, the overall test count is now 587.

**Highlights:**

- `test_p26a_1`: discovery is deterministic and ignores non-`.md` files.
- `test_p26a_2`: invalid or null-byte source paths are rejected with `INVALID_SOURCE`.
- `test_p26a_3`: traversal and absolute-path destinations are rejected with `UNSAFE_DESTINATION`.
- `test_p26a_4`: `Vault Files/` destinations are rejected.
- `test_p26a_5`: oversized source files are rejected with `READ_FAILED`.
- `test_p26a_6`: high-severity security findings produce `SECURITY_FAIL` and block writes.
- `test_p26a_7`: dry-run produces a complete plan but writes no files.
- `test_p26a_8`: write mode without `overwrite` refuses to clobber an existing note.
- `test_p26a_9`: `overwrite=True` replaces an existing note via atomic write.
- `test_p26a_10`: unknown source frontmatter keys are dropped and surfaced as warnings.
- `test_p26a_11`: imported notes carry `trust_level: draft` and `source_type: imported` when supported by the schema.
- `test_p26a_12`: section booleans are recomputed from body content rather than trusted from source frontmatter.
- `test_p26a_13`: slug normalisation produces deterministic, lowercase, hyphenated destination paths.
- `test_p26a_14`: warning-severity security findings are surfaced without blocking.
- `test_p26a_15`: invalid content returns `VALIDATION_FAILED` with actionable error details.
- `test_p26a_16`: HTTP `POST /import/markdown-folder` dry-run end-to-end.
- `test_p26a_17`: HTTP endpoint rejects unsafe destinations with structured error.
- `test_p26a_18`: CLI `py run.py import-markdown` dry-run prints JSON and writes no files.
- `test_p26a_19`: CLI `--write` mode performs the actual import.
- `test_p26a_20`: note index and result cache are invalidated after a successful write.
- `test_p26a_21`: every realised destination path stays inside the vault root.
- `test_p26a_22`: source paths under `Vault Files/` cannot be written into the reserved folder.
- `test_p26a_23`: response shape matches the documented contract (`status`, `data.summary`, `data.items[*]`).

**Verification steps:**

```bash
py mcp/test_verify.py      # 695 tests, all must pass
py run.py validate         # vault still valid
py run.py security         # status: pass
py run.py import-markdown <source_dir>            # dry-run by default
py run.py import-markdown <source_dir> --write    # actually writes
py run.py feedback         # exits 0, valid JSON
py run.py export --overwrite   # status: ok
cd ui; npm run build       # zero errors
```

---

## Phase 26B - Import Review UI

20 new tests (`test_p26b_1` through `test_p26b_20`), bringing the phase-test total to 591. Combined with the 16 documentation drift guardrails, the overall test count is now 607.

The Phase 26B suite is mostly static-content verification because the UI runs in a browser and exercises the Phase 26A backend through `POST /import/markdown-folder`. The single dynamic test confirms that `cd ui && npm run build` produces `ui/dist/import/index.html` containing the expected header text.

**Highlights:**

- `test_p26b_1`: `ui/src/pages/import.astro` exists, uses `AppLayout`, and hydrates `ImportReview`.
- `test_p26b_2`: `ui/src/components/ImportReview.svelte` exists with the page header.
- `test_p26b_3`: the app sidebar in `AppLayout.astro` lists an `Import` nav item at `/app/import`.
- `test_p26b_4`: `api.ts` exports an `importMarkdownFolder` helper that posts to `/import/markdown-folder`.
- `test_p26b_5`: `ImportMarkdownFolderRequest` declares `vault`, `source_dir`, `destination`, `dry_run`, `overwrite`.
- `test_p26b_6`: response types include `summary` and `items[]`, with `discovered`, `planned`, `written`, `skipped`, `errors`, `warnings`.
- `test_p26b_7`: the component defaults destination to `Imported`.
- `test_p26b_8`: the preview action posts `dry_run: true`.
- `test_p26b_9`: the write action posts `dry_run: false`.
- `test_p26b_10`: write is gated by both a successful preview and an explicit confirmation flag.
- `test_p26b_11`: preview is marked stale when vault, source folder, destination, or overwrite changes.
- `test_p26b_12`: the summary panel renders Discovered, Planned, Written, Skipped, Errors, Warnings.
- `test_p26b_13`: source folder and destination folder paths are surfaced in the summary panel.
- `test_p26b_14`: per-item view lists warnings and errors with counts.
- `test_p26b_15`: per-item view exposes security and validation status badges.
- `test_p26b_16`: write requires an explicit confirmation checkbox with the documented phrase.
- `test_p26b_17`: the form helper text explains that the source path is server-local.
- `test_p26b_18`: the page header states Markdown folder import only.
- `test_p26b_19`: deferred import sources (PDF, GitHub, browser article, semantic, LLM) are not advertised as buttons or actions.
- `test_p26b_20`: `ui/dist/import/index.html` exists after `npm run build` and contains the expected header.

**Verification steps:**

```bash
py mcp/test_verify.py            # 625 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds the /import page artefact
```

---

## Phase 26C - Import Post-Processing and Review Integration

18 new tests (`test_p26c_1` through `test_p26c_18`), bringing the phase-test total to 609. Combined with the 16 documentation drift guardrails, the overall test count is now 625.

Phase 26C extends the Phase 26B Import Review UI with a post-import review path and integrates imported notes into the existing Notes browsing surface. No new import sources are introduced, no LLM rewriting is performed, and no automatic trust promotion happens. Other import sources (PDF, browser article, GitHub repo, Obsidian-specific, chat transcript, semantic, LLM-extraction) remain deferred.

**Highlights:**

- `test_p26c_1`: after a successful import, the result panel renders vault-aware follow-up links to Notes, Validation, Tasks, Security, and the dashboard, plus the Trust page.
- `test_p26c_2`/`test_p26c_3`/`test_p26c_4`: the Phase 26B safety gates remain intact: preview required before write, explicit confirmation required before write, and preview marked stale when vault, source, destination, or overwrite changes.
- `test_p26c_5`/`test_p26c_6`: the Notes UI exposes an Imported-only filter (`filter-imported-only`) and a Draft-trust-only filter (`filter-draft-trust-only`).
- `test_p26c_7`: each note row carries `badge-imported` and `badge-draft` test ids when applicable, and Deprecated trust is also surfaced.
- `test_p26c_8`/`test_p26c_9`: the note detail renders a Trust and Import panel showing `source_type`, `trust_level`, `last_reviewed`, `review_after`, `confidence`, and `stale`, with the disclaimer that trust metadata reflects review and maintenance state only and does not prove factual correctness.
- `test_p26c_10`: `isImportedNote` helper exists in `api.ts` and the `/notes` adapter surfaces `source_type` and `trust_level` so the helper has real data to act on.
- `test_p26c_11`/`test_p26c_12`: the `ImportedReviewSummary` component and `buildImportedReviewSummary` helper expose imported total, imported draft, imported with validation issues, imported with tasks, imported stale, and imported deprecated counts, and the component renders a clear no-imported-notes message when the total is zero.
- `test_p26c_13`: no new import sources are advertised in `ImportReview.svelte`, `ImportedReviewSummary.svelte`, or `NoteBrowser.svelte`.
- `test_p26c_14`/`test_p26c_15`: the import UI still states the source path is server-local and the scope is Markdown folder import only.
- `test_p26c_16`: API client adds `buildNotesLink`, `isDraftTrustNote`, an `ImportedReviewSummary` interface, and extends `NoteListItem` with `source_type` and `trust_level`.
- `test_p26c_17`/`test_p26c_18`: README, QUICKSTART, TESTING, ROADMAP, and RELEASE_CHECKLIST mention Phase 26C, README and ROADMAP reaffirm that other import sources remain deferred, and no em dash regresses into project-authored docs.

**Verification steps:**

```bash
py mcp/test_verify.py            # 650 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds the /notes and /import page artefacts
```

---

## Phase 26D - Import Workflow Hardening and Edge-Case QA

25 new tests (`test_p26d_1` through `test_p26d_25`), bringing the phase-test total to 634. Combined with the 16 documentation drift guardrails, the overall test count is now 650.

Phase 26D does not add any new import sources. It hardens the existing Markdown folder import lifecycle against ugly, malformed, duplicated, large, oddly named, or structurally inconsistent input, and makes failure modes clearer, safer, and more deterministic. PDF, browser article, GitHub repo, Obsidian-specific, chat transcript, semantic mapping, and LLM extraction imports remain deferred. Imported content still requires human review and there is no automatic trust promotion or LLM rewriting.

**Highlights:**

- `test_p26d_1`: dry-run is deterministic across repeated calls with identical inputs (item destinations, statuses, and summary counts all match).
- `test_p26d_2`: nested source folders preserve their safe relative structure under the destination.
- `test_p26d_3`: duplicate source filenames in different folders produce distinct destinations.
- `test_p26d_4`: filename punctuation (commas, underscores, parentheses, non-ASCII) is slugged deterministically.
- `test_p26d_5`: filenames whose stem collapses to nothing after sanitisation fall back to `untitled`.
- `test_p26d_6`: destinations containing Windows backslashes are normalised into forward slashes.
- `test_p26d_7`: one blocked file does not crash the rest of the batch.
- `test_p26d_8`: summary counts (`discovered`, `planned`, `skipped`, `errors`, `warnings`) equal the per-item status counts exactly.
- `test_p26d_9`/`test_p26d_10`/`test_p26d_11`/`test_p26d_12`: malformed YAML, non-mapping YAML, orphan opening markers, and duplicate YAML keys are reported at item level as `INVALID_FRONTMATTER`, `FRONTMATTER_NOT_OBJECT`, `INVALID_FRONTMATTER`, and `DUPLICATE_YAML_KEY` respectively, without crashing the batch.
- `test_p26d_13`/`test_p26d_14`: source files containing a null byte are blocked with `NULL_BYTE`; source files exceeding the 5 MB cap are blocked with `SOURCE_TOO_LARGE`.
- `test_p26d_15`: invalid source enum values (such as a `status` field with an unknown value) are replaced with a schema-safe value rather than being written through.
- `test_p26d_16`/`test_p26d_17`: imported notes appear in `/query` results and `/validation` reflects them correctly.
- `test_p26d_18`: repeated writes with `overwrite=false` skip existing destinations deterministically with `DESTINATION_EXISTS`.
- `test_p26d_19`/`test_p26d_20`/`test_p26d_21`/`test_p26d_22`: the Import Review UI has a clear empty-items message, a dedicated `DESTINATION_EXISTS` collision banner, a dedicated malformed-frontmatter banner, and per-item plain-language labels for all Phase 26D error codes.
- `test_p26d_23`/`test_p26d_24`: README, QUICKSTART, TESTING, ROADMAP, and RELEASE_CHECKLIST mention Phase 26D; README, QUICKSTART, and ROADMAP state that Phase 26D adds no new import sources; deferred sources remain reaffirmed; no em dash regresses into project-authored docs.
- `test_p26d_25`: a smoke test drives the pipeline through every new edge case and confirms that `NULL_BYTE`, `INVALID_FRONTMATTER`, `FRONTMATTER_NOT_OBJECT`, `DUPLICATE_YAML_KEY`, and `SOURCE_TOO_LARGE` are actually surfaced.

**Verification steps:**

```bash
py mcp/test_verify.py            # 675 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds the /notes and /import page artefacts
```

---

## Phase 26E - Obsidian-Compatible Markdown Import

25 new tests (`test_p26e_1` through `test_p26e_25`), bringing the phase-test total to 659. Combined with the 16 documentation drift guardrails, the overall test count is now 675.

Phase 26E adds a safe, Obsidian-compatible Markdown import on top of the hardened Phase 26A-D pipeline. It is local-only, deterministic, security-scanned, dry-run by default, and reuses every Phase 26A-D safety control. PDF, GitHub repo, browser article, chat transcript, semantic mapping, and LLM-extraction imports remain deferred. Imported content still requires human review; trust metadata is never promoted automatically and no LLM rewriting is performed.

**Highlights:**

- `test_p26e_1`: discovery finds `.md` files deterministically and skips `.obsidian/`, binary attachments, and `.canvas` files.
- `test_p26e_2`: `is_obsidian_config_path` flags `.obsidian/`, `.trash/`, `.git/`, and `node_modules/` and leaves regular notes alone.
- `test_p26e_3`: dry-run uses the `Imported/Obsidian` default destination and writes no files.
- `test_p26e_4`: nested source folders preserve their relative structure under the destination.
- `test_p26e_5`: the feature extractor returns deterministic, sorted, de-duplicated lists across repeated calls.
- `test_p26e_6`: wikilink variants (`[[Note#Heading]]`, `[[Note|Alias]]`, `[[Note#^block-id]]`) are detected and block references are surfaced.
- `test_p26e_7`: Markdown image embeds are reported as attachment references; plain `.md` links are not.
- `test_p26e_8`: each item carries a deterministic `obsidian` metadata block (wikilinks, embeds, tags, aliases, callouts, attachment refs) plus warnings for preserved wikilinks and detected attachments.
- `test_p26e_9`: each item's `source_path` points back to the original Obsidian file (no staging-directory leakage).
- `test_p26e_10`: binary attachments and `.canvas` files are never imported.
- `test_p26e_11`: write mode actually creates the destination Markdown files.
- `test_p26e_12`/`test_p26e_13`: malformed YAML frontmatter and duplicate YAML keys are blocked exactly as in Phase 26A-D.
- `test_p26e_14`: high-severity security findings still block the write (`SECURITY_FAIL`).
- `test_p26e_15`: unknown Obsidian YAML fields are dropped from the written note and surfaced under the per-item `obsidian` metadata.
- `test_p26e_16`: imported Obsidian notes still land as `source_type: imported` and `trust_level: draft` when the schema supports them; the response carries `source_type: obsidian-vault` at the data level.
- `test_p26e_17`/`test_p26e_18`: the HTTP endpoint returns the Obsidian-shaped envelope on dry-run and rejects unsafe destinations (`Vault Files/...`) with `UNSAFE_DESTINATION`.
- `test_p26e_19`/`test_p26e_20`: `py run.py import-obsidian` dry-run prints valid JSON and `--write` actually creates files.
- `test_p26e_21`/`test_p26e_22`/`test_p26e_23`: the Import Review UI exposes a source-type selector, shows Phase 26E helper text (`.obsidian/` skipped, binary attachments not imported, wikilinks preserved, preview and explicit confirmation), surfaces the per-item Obsidian metadata section, and includes source-type changes in stale-preview detection.
- `test_p26e_24`: README, QUICKSTART, API, TESTING, ROADMAP, and RELEASE_CHECKLIST mention Phase 26E; API.md documents `/import/obsidian-vault`; QUICKSTART mentions `.obsidian`.
- `test_p26e_25`: the deferred sources (PDF, GitHub repo, browser article, chat transcript, semantic, LLM) are still explicitly called out in README, and no em dash regresses into project-authored docs.

**Verification steps:**

```bash
py mcp/test_verify.py            # 695 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds the /notes and /import page artefacts
```

---

## Phase 26F - Import Lifecycle Finalisation

20 new tests (`test_p26f_1` through `test_p26f_20`), bringing the phase-test total to 679. Combined with the 16 documentation drift guardrails, the overall test count is now 695.

Phase 26F finalises the Phase 26 Import Pipelines without adding any new import source. It proves end-to-end that imported content flows cleanly through the rest of the system and that the documentation set says exactly what Phase 26 ships and what is still deferred.

**Highlights:**

- `test_p26f_1`/`test_p26f_2`/`test_p26f_3`/`test_p26f_4`/`test_p26f_5`/`test_p26f_6`/`test_p26f_7`/`test_p26f_8`: after a Markdown folder write, the imported note shows up in `/notes`, is findable via `/query`, appears in `/validation`, does not break `/tasks`, surfaces `imported`/`draft` in `/trust`, can be filtered into `/context/bundle` with `source_type=imported`, and the vault still exports and graph-builds successfully.
- `test_p26f_9`/`test_p26f_10`/`test_p26f_11`/`test_p26f_12`/`test_p26f_13`/`test_p26f_14`: the same end-to-end coverage for Obsidian-compatible writes, plus an additional check that graph build and export both succeed against the Obsidian-imported state.
- `test_p26f_15`: Obsidian wikilinks are preserved verbatim in the body but Obsidian-specific YAML keys (`aliases:`, `tags:`) do not leak into the destination frontmatter; the per-item `obsidian` block surfaces the metadata.
- `test_p26f_16`: both import endpoints expose the documented per-item contract (`source_path`, `destination_path`, `action`, `status`, `fields`, `warnings`, `errors`, `security`, `validation`); the Obsidian endpoint adds `data.source_type: "obsidian-vault"` and a per-item `obsidian` block; the Markdown endpoint never claims an Obsidian source type.
- `test_p26f_17`: repeated dry-run for both source types yields byte-identical summaries and identical destination ordering.
- `test_p26f_18`: repeated write with `overwrite=false` skips existing destinations deterministically for both source types and surfaces `DESTINATION_EXISTS` per item.
- `test_p26f_19`: `overwrite=true` updates only the targeted destination file; unrelated notes are not touched (content and mtime unchanged).
- `test_p26f_20`: README announces Phase 26 complete, references Phase 26F, and does not claim PDF / GitHub repo / browser article / chat transcript / semantic / LLM imports are implemented; ROADMAP marks Phase 26 Complete in the status table and keeps Phase 27 and Phase 28 deferred; QUICKSTART documents both `import-markdown` and `import-obsidian`; API.md documents both `/import/markdown-folder` and `/import/obsidian-vault`; no em dashes leaked into any project-authored doc.

**Verification steps:**

```bash
py mcp/test_verify.py            # 695 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds the /notes and /import page artefacts
```

---

## Documentation Drift Guardrails

A small set of deterministic tests guards against the most common documentation drift:

- `test_p6_docs_consistency` (Phase 6) confirms every FastAPI route is documented in API.md.
- `test_p18_release_checklist_coverage` (Phase 18) confirms RELEASE_CHECKLIST covers the required commands.
- `test_p22_testing_md_updated_count`, `test_p23_testing_md_updated_count`, `test_p24_36` (historical) confirm prior test-count entries remain present in TESTING.md.
- `test_p18bu_ui_no_stale_limitation_text` (Phase 18BU) confirms VaultSetup.svelte no longer claims expected concepts are not written to schema.
- `test_doc_drift_*` (current pass) confirms README, TESTING, and RELEASE_CHECKLIST agree on the current test count and that QUICKSTART no longer carries the stale "Expected Concepts not yet written to schema" sentence.

---

## Phase 29A - UI/UX Quality Roadmap Formalisation and Audit

11 new tests (`test_p29a_1` through `test_p29a_11`), bringing the phase-test total to 690. Combined with the 16 documentation drift guardrails, the overall test count after Phase 29A was 706 test functions. (Phase 29B subsequently added 15 more tests, lifting the current total to 721.)

Phase 29A is documentation and audit only. No UI code, no CSS, no components, and no backend behaviour are changed in this phase. The new tests guard against drift between ROADMAP.md, UI_UX_AUDIT.md, TESTING.md, README.md, and the deferral status of Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval).

**Tests added:**

- `test_p29a_1_roadmap_contains_phase29` - ROADMAP.md contains a Phase 29 section header.
- `test_p29a_2_roadmap_contains_all_subphases` - ROADMAP.md mentions Phase 29A, 29B, 29C, 29D, and 29E.
- `test_p29a_3_roadmap_phase27_still_deferred` - ROADMAP.md status table row for Phase 27 still reads Deferred.
- `test_p29a_4_roadmap_phase28_still_deferred` - ROADMAP.md status table row for Phase 28 still reads Deferred.
- `test_p29a_5_roadmap_current_active_phase` - ROADMAP.md Current Active Phase references Phase 29A.
- `test_p29a_6_ui_ux_audit_exists` - UI_UX_AUDIT.md exists in the repository root.
- `test_p29a_7_ui_ux_audit_required_sections` - UI_UX_AUDIT.md includes screenshot findings, route inventory, component inventory, information architecture, design system, React decision, and non-goals.
- `test_p29a_8_no_em_dashes_in_p29_docs` - ROADMAP.md and UI_UX_AUDIT.md do not contain em dashes.
- `test_p29a_9_testing_documents_phase29a` - TESTING.md documents Phase 29A.
- `test_p29a_10_readme_no_phase29_implementation_claim` - README.md does not claim Phase 29 UI implementation is complete.
- `test_p29a_11_verification_commands_intact` - The standard verification command list (test_verify.py, validate, security, feedback, export, npm run build) is still documented.

**Verification steps:**

```bash
py mcp/test_verify.py            # 721 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

Phase 29A does not implement any UI change. Phase 29B (Navigation and information architecture redesign) is the first sub-phase that touches UI code, and it is not part of Phase 29A.

---

## Phase 29B - Navigation and Information Architecture Redesign

15 new tests (`test_p29b_1` through `test_p29b_15`), bringing the phase-test total to 705. Combined with the 16 documentation drift guardrails, the overall test count is now 721.

Phase 29B is the first Phase 29 sub-phase that touches UI code. It rewrites `ui/src/layouts/AppLayout.astro` with a data-driven, grouped sidebar, preserves every existing `/app/*` route, improves brand/header hierarchy, adds an `aria-current="page"` active state, and adds a visible `:focus-visible` ring for keyboard navigation. No backend behaviour, no API contracts, no route paths, and no dependencies are changed. Page consolidation is deferred to Phase 29D. The full design system is deferred to Phase 29C.

**Tests added:**

- `test_p29b_1_grouped_nav_labels_present` - AppLayout.astro contains the five group labels: Overview, Vault, Context, Review and Governance, Developer.
- `test_p29b_2_all_app_routes_linked` - AppLayout.astro links to every existing `/app` route (`/app/`, `/app/vault-setup`, `/app/notes`, `/app/validation`, `/app/tasks`, `/app/bundles`, `/app/security`, `/app/exports`, `/app/import`, `/app/feedback`, `/app/graph`, `/app/controller`, `/app/pending`, `/app/trust`, `/app/raw`).
- `test_p29b_3_nav_landmark_present` - AppLayout.astro uses a semantic `<nav aria-label="Primary">` landmark.
- `test_p29b_4_aria_current_page_used` - AppLayout.astro uses `aria-current="page"` for the active link.
- `test_p29b_5_focus_visible_styling_present` - AppLayout.astro defines a visible `:focus-visible` outline or box-shadow for nav links.
- `test_p29b_6_api_raw_under_developer` - The `API / Raw` label and `/app/raw` link appear after the Developer group label in source order.
- `test_p29b_7_pending_and_trust_under_governance` - `/app/pending` and `/app/trust` appear after the Review and Governance group label in source order.
- `test_p29b_8_context_group_items` - `/app/bundles`, `/app/exports`, `/app/graph`, and `/app/controller` all appear after the Context group label and before the Review and Governance group label.
- `test_p29b_9_roadmap_phase27_still_deferred` - ROADMAP.md status table still marks Phase 27 (Registry and Reuse Layer) Deferred.
- `test_p29b_10_roadmap_phase28_still_deferred` - ROADMAP.md status table still marks Phase 28 (Optional Semantic Retrieval) Deferred.
- `test_p29b_11_roadmap_marks_phase29b_complete` - ROADMAP.md records Phase 29B as Complete in its sub-phase block.
- `test_p29b_12_testing_documents_phase29b` - TESTING.md documents Phase 29B and states the new total of 721 test functions.
- `test_p29b_13_readme_no_phase29_complete_claim` - README.md does not claim Phase 29 is fully complete.
- `test_p29b_14_no_em_dashes_in_p29b_docs` - ROADMAP.md, UI_UX_AUDIT.md, TESTING.md, README.md, and RELEASE_CHECKLIST.md contain no em dashes.
- `test_p29b_15_verification_commands_intact` - The six standard verification commands (`py mcp/test_verify.py`, `py run.py validate`, `py run.py security`, `py run.py feedback`, `py run.py export --overwrite`, `npm run build`) remain documented in TESTING.md and RELEASE_CHECKLIST.md.

**Verification steps:**

```bash
py mcp/test_verify.py            # 721 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

Phase 29B does not implement the full design system. Phase 29C (Global design system and shared UI primitives) is the next sub-phase and is not part of Phase 29B.

---

## Phase 29C - Global Design System and Shared UI Primitives

19 new tests (`test_p29c_1` through `test_p29c_19`), bringing the phase-test total to 724. Combined with the 16 documentation drift guardrails, the overall test count is now 740 test functions.

Phase 29C introduces the design system foundation: CSS custom property tokens and reusable `cve-*` primitive classes defined in `ui/src/styles/global.css`. Tokens cover app background, elevated and muted surfaces, borders, strong/normal/muted/faint text, accent and accent-soft, success, warning, danger, info, and focus ring. Primitives cover typography, page shell, page header, content stack, card grid, card, button (primary/secondary/ghost/danger), badge (neutral/success/warning/danger/info/draft/deprecated), alert (info/success/warning/danger), form field/label/helper/input/select/textarea, table and list, empty/loading/error/success states, raw JSON and collapsible details, and dangerous action, warning, and trust-warning blocks. A single `:focus-visible` rule is applied to all interactive primitives. No backend behaviour, no API contracts, no route paths, and no dependencies are changed. Page-level migration is deferred to Phase 29D.

**Tests added:**

- `test_p29c_1_tokens_defined` - global.css defines design tokens for background, surface, border, text, muted text, accent, accent-soft, success, warning, danger, info, and focus.
- `test_p29c_2_card_primitive` - global.css defines reusable `.cve-card` styling that references the surface and border tokens.
- `test_p29c_3_button_variants` - global.css defines `.cve-btn`, `.cve-btn-primary`, `.cve-btn-secondary`, `.cve-btn-ghost`, and `.cve-btn-danger`.
- `test_p29c_4_badge_variants` - global.css defines `.cve-badge` plus neutral, success, warning, danger, info, draft, and deprecated variants.
- `test_p29c_5_alert_variants` - global.css defines `.cve-alert` plus info, success, warning, and danger variants.
- `test_p29c_6_form_primitives` - global.css defines `.cve-field`, `.cve-label`, `.cve-helper`, `.cve-input`, `.cve-select`, and `.cve-textarea`.
- `test_p29c_7_table_primitive` - global.css defines `.cve-table-wrap`, `.cve-table`, and `.cve-list`.
- `test_p29c_8_raw_json_details` - global.css defines `.cve-raw` and `.cve-details`.
- `test_p29c_9_dangerous_action_pattern` - global.css defines `.cve-danger-zone`, `.cve-warning-block`, and `.cve-trust-warning` and uses the `--cve-danger` token.
- `test_p29c_10_focus_visible_styling` - global.css includes a `:focus-visible` rule that references the `--cve-focus` token.
- `test_p29c_11_applayout_groups_preserved` - AppLayout.astro still contains the Phase 29B group labels Overview, Vault, Context, Review and Governance, and Developer.
- `test_p29c_12_applayout_api_raw_under_developer` - AppLayout.astro still links to `/app/raw` labelled API / Raw under Developer.
- `test_p29c_13_roadmap_phase27_still_deferred` - ROADMAP.md status table still marks Phase 27 Deferred.
- `test_p29c_14_roadmap_phase28_still_deferred` - ROADMAP.md status table still marks Phase 28 Deferred.
- `test_p29c_15_roadmap_marks_phase29c_complete` - ROADMAP.md records Phase 29C as Complete.
- `test_p29c_16_testing_documents_phase29c` - TESTING.md documents Phase 29C and states the new total of 740 test functions.
- `test_p29c_17_readme_no_phase29_complete_claim` - README.md does not claim Phase 29 is fully complete.
- `test_p29c_18_no_em_dashes_in_p29c_docs` - ROADMAP.md, TESTING.md, README.md, RELEASE_CHECKLIST.md, and UI_UX_AUDIT.md contain no em dashes.
- `test_p29c_19_verification_commands_intact` - The six standard verification commands remain documented in TESTING.md and RELEASE_CHECKLIST.md.

**Verification steps:**

```bash
py mcp/test_verify.py            # 740 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

Phase 29C is the design system foundation only. Page-level UX consistency, page consolidation, and migration of every existing page to the new primitives are deferred to Phase 29D.

---

## Phase 29D - Page-Level UX Consistency Pass

22 new tests (`test_p29d_1` through `test_p29d_22`), bringing the current total to 763 test functions.

Phase 29D migrates the existing UI pages and components onto the Phase 29C design system primitives. Every Astro page under `ui/src/pages/` continues to mount its existing Svelte island, and each major Svelte component (`Dashboard`, `VaultSetup`, `NoteBrowser`, `BundleBuilder`, `ExportPackage`, `SecurityScan`, `FeedbackWorkflow`, `GraphExplorer`, `ContextController`, `PendingChanges`, `TrustEvidence`, `ImportReview`) together with the `PlaceholderPage.astro` shim now adopts the `cve-*` primitives for the page shell, headers, cards, buttons, badges, forms, tables/lists, state blocks, raw JSON details, dangerous actions, and trust/security warnings. `VaultSetup.svelte` wraps its vault-delete surface in `cve-danger-zone` with a `cve-btn-danger` confirmation button; `TrustEvidence.svelte` carries a `cve-trust-warning` block that restates the standing disclaimer that trust metadata reflects review and maintenance state only and does not prove factual correctness; `ImportReview.svelte` highlights its write-confirmation block with `cve-warning-block`. Phase 29B's grouped sidebar in `AppLayout.astro` is unchanged, all 15 existing `/app/*` routes still resolve, and `/app/raw` is still labelled API / Raw under Developer. No backend route is added, renamed, or removed; no dependency is added.

**Tests added:**

- `test_p29d_1_every_app_page_renders_cve_shell` - Every page under `ui/src/pages/` either uses `cve-page*` directly or mounts a Svelte component that does.
- `test_p29d_2_major_components_use_cve_primitives` - Every Svelte component contains at least one `cve-*` primitive.
- `test_p29d_3_page_header_primitive_used` - At least one component renders `cve-page-header`.
- `test_p29d_4_page_title_primitive_used` - At least one component renders `cve-page-title`.
- `test_p29d_5_card_primitive_used` - At least one component renders `cve-card`.
- `test_p29d_6_button_primitive_used` - At least one component renders `cve-btn`.
- `test_p29d_7_badge_primitive_used` - At least one component renders `cve-badge`.
- `test_p29d_8_form_primitive_used` - At least one component renders `cve-input`, `cve-select`, or `cve-textarea`.
- `test_p29d_9_table_or_list_primitive_used` - At least one component renders `cve-table` or `cve-list`.
- `test_p29d_10_state_primitive_used` - At least one component renders a `cve-empty`, `cve-loading`, `cve-error`, or `cve-success` block.
- `test_p29d_11_details_and_raw_primitive_used` - Both `cve-details` and `cve-raw` are used by components.
- `test_p29d_12_dangerous_action_primitive_used` - A dangerous-action primitive (`cve-danger-zone` or `cve-warning-block`) is used, and `VaultSetup.svelte` uses `cve-danger-zone`.
- `test_p29d_13_trust_warning_primitive_used` - `TrustEvidence.svelte` uses `cve-trust-warning`.
- `test_p29d_14_applayout_groups_preserved` - `AppLayout.astro` still contains the Phase 29B grouped nav labels (Overview, Vault, Context, Review and Governance, Developer).
- `test_p29d_15_applayout_api_raw_under_developer` - `AppLayout.astro` still surfaces `/app/raw` as API / Raw under the Developer group.
- `test_p29d_16_roadmap_phase27_still_deferred` - `ROADMAP.md` still marks Phase 27 Deferred.
- `test_p29d_17_roadmap_phase28_still_deferred` - `ROADMAP.md` still marks Phase 28 Deferred.
- `test_p29d_18_roadmap_marks_phase29d_complete` - `ROADMAP.md` records Phase 29D as Complete.
- `test_p29d_19_testing_documents_phase29d` - `TESTING.md` documents Phase 29D.
- `test_p29d_20_readme_no_phase29_complete_claim` - `README.md` does not claim that Phase 29 is fully complete.
- `test_p29d_21_no_em_dashes_in_p29d_docs` - `ROADMAP.md`, `TESTING.md`, `README.md`, `RELEASE_CHECKLIST.md`, and `UI_UX_AUDIT.md` contain no em dashes.
- `test_p29d_22_verification_commands_intact` - The six standard verification commands remain documented in `TESTING.md` and `RELEASE_CHECKLIST.md`.

**Verification steps:**

```bash
py mcp/test_verify.py            # 763 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

Phase 29D migrates the existing pages onto the design system. Final polish, accessibility minimums, responsive review, and release-readiness documentation are deferred to Phase 29E.

---

## Phase 29E - Final Polish, Accessibility, and Release Readiness

24 new tests (`test_p29e_1` through `test_p29e_24`), bringing the current total to 787 test functions.

Phase 29E is the final UI/UX polish pass and the closure of Phase 29. It does not introduce features. It addresses the rough edges exposed by the Phase 29D primitive rollout: the `cve-details` summary now carries an explicit textual disclosure cue and chevron so users can tell a block expands; the `:focus-visible` rule now covers ordinary anchors and native buttons inside the page shell as well as the `cve-*` primitives; disabled buttons and disabled form controls share a clearly distinct visual state; raw JSON and table containers are pinned to `max-width: 100%` with internal scroll so wide payloads no longer push the page into horizontal overflow; a small responsive guard caps `.cve-page` at the viewport width and constrains descendant media; the `AppLayout.astro` footer label is refreshed from the stale "Phase 29B - Navigation" to "Phase 29 - Stable"; documentation is closed out across ROADMAP, TESTING, README, RELEASE_CHECKLIST, and UI_UX_AUDIT. No backend route, dependency, icon library, animation library, or business behaviour is added or changed. Phase 29B's grouped sidebar is preserved verbatim, every `/app/*` route still resolves, and `/app/raw` is still labelled API / Raw under Developer.

**Tests added:**

- `test_p29e_1_details_summary_has_disclosure_indicator` - `global.css` gives `cve-details > summary` a visible disclosure indicator (pseudo-element chevron and a textual Show details / Hide details cue).
- `test_p29e_2_focus_visible_styling_covers_primitives` - `global.css` defines `:focus-visible` styling for buttons, inputs, selects, textareas, details summaries, and links.
- `test_p29e_3_disabled_state_styling_present` - `global.css` defines a disabled-state rule for `cve-btn` and disabled form controls.
- `test_p29e_4_raw_block_protected_from_overflow` - `cve-raw` is constrained to `max-width: 100%` and scrolls internally rather than overflowing the page.
- `test_p29e_5_table_wrap_protected_from_overflow` - `cve-table-wrap` is constrained to `max-width: 100%` and scrolls internally rather than overflowing the page.
- `test_p29e_6_reduced_motion_guard_present` - `global.css` retains a `prefers-reduced-motion` guard.
- `test_p29e_7_danger_zone_styling_present` - `global.css` retains `cve-danger-zone` with explicit danger styling and a textual title class.
- `test_p29e_8_trust_warning_styling_present` - `global.css` retains `cve-trust-warning` and `cve-warning-block` styling.
- `test_p29e_9_applayout_grouped_nav_labels_present` - `AppLayout.astro` still contains the Phase 29B grouped nav labels.
- `test_p29e_10_applayout_api_raw_under_developer` - `AppLayout.astro` still links to `/app/raw` labelled API / Raw under Developer.
- `test_p29e_11_applayout_footer_phase_label_current` - `AppLayout.astro` footer label no longer claims an old Phase 29 sub-phase is active.
- `test_p29e_12_major_components_still_use_cve_primitives` - Every major Svelte component still contains at least one `cve-*` primitive after the polish pass.
- `test_p29e_13_all_app_routes_have_page_files` - Every `/app/*` route referenced by the AppLayout sidebar resolves to a page file in `ui/src/pages/`.
- `test_p29e_14_roadmap_marks_phase29e_complete` - `ROADMAP.md` records Phase 29E as Complete.
- `test_p29e_15_roadmap_marks_phase29_complete` - `ROADMAP.md` status table marks Phase 29 as Complete.
- `test_p29e_16_roadmap_phase27_still_deferred` - `ROADMAP.md` still marks Phase 27 Deferred.
- `test_p29e_17_roadmap_phase28_still_deferred` - `ROADMAP.md` still marks Phase 28 Deferred.
- `test_p29e_18_testing_documents_phase29e` - `TESTING.md` documents Phase 29E and states the new total of 787 test functions.
- `test_p29e_19_readme_states_phase29_complete` - `README.md` states Phase 29 is complete and keeps Phase 27 and Phase 28 deferred.
- `test_p29e_20_release_checklist_test_count_updated` - `RELEASE_CHECKLIST.md` references the new test count of 787.
- `test_p29e_21_ui_ux_audit_has_phase29e_note` - `UI_UX_AUDIT.md` includes a Phase 29E implementation note and a Phase 29 closure note.
- `test_p29e_22_no_em_dashes_in_p29e_docs` - No project-authored doc modified by Phase 29E contains em dashes.
- `test_p29e_23_no_em_dashes_in_modified_ui_sources` - The UI source files modified by Phase 29E contain no em dashes.
- `test_p29e_24_package_json_unchanged` - `ui/package.json` does not introduce any new dependency in Phase 29E.

**Verification steps:**

```bash
py mcp/test_verify.py            # 787 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

Phase 29E closes Phase 29. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain explicitly deferred.

---

## Adding New Tests

1. Add test functions to `mcp/test_verify.py` following the existing naming convention.
2. Add the function call to the `if __name__ == "__main__":` block at the bottom of the file.
3. Run the full suite to confirm all tests pass.
4. Update this document if adding a new test category.

---

## Phase 30A - UI Release Quality Pass: Audit Consolidation

Phase 30A is documentation only. It consolidates fourteen screenshot-driven per-page UX audits (`UIReport1.txt` through `UIReport14.txt`) into `UI_UX_AUDIT.md` sections 18 and 19, and records the planned Phase 30B through 30F slices in `ROADMAP.md`. No UI source file, no test, and no backend route is modified by Phase 30A. The current test total (787 functions) is unchanged.

The audit conclusion is recorded in `UI_UX_AUDIT.md` section 18.5 as a per-page verdict table. The Phase 30B foundation-only brief is recorded in `UI_UX_AUDIT.md` section 19. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain explicitly deferred.

**Verification steps for Phase 30A:**

```bash
py mcp/test_verify.py            # 787 tests, all must pass; no test added in 30A
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

### Planned Phase 30 UI Guardrail Tests

The following deterministic guardrail families are planned for Phase 30B through Phase 30F. They are listed here so the Phase 30B implementation prompt can target them precisely. They are not added by Phase 30A.

- **No raw Tailwind dark palette literals on migrated pages.** Once a page or component is migrated under Phase 30B / 30C / 30D / 30E, it must not reintroduce `bg-zinc-*`, `text-zinc-*`, `border-zinc-*`, `bg-emerald-9*`, `bg-amber-9*`, `bg-rose-9*`, `bg-sky-9*`, or other hard-coded dark palette literals. Tests scan the migrated source files and fail on any such literal.
- **Light and dark token coverage.** `global.css` must define both `data-theme="dark"` and `data-theme="light"` values for every `--cve-*` semantic token. Tests parse `global.css` and assert each token has a value in both blocks. A `color-scheme: dark light` declaration must be present on the root.
- **Workflow layout guardrails.** Pages flagged as workflow surfaces by the audit (Notes, Graph, Pending, Feedback, Bundles, Exports, Security, Validation, Tasks) must declare a layout mode that is not `standard` (typically `wide` or `workspace`). Tests assert the layout-mode contract on each page file.
- **Placeholder-removal guardrails for Validation, Tasks, and Raw.** Once Phase 30D lands, `/app/validation`, `/app/tasks`, and `/app/raw` must no longer render `PlaceholderPage.astro`. Tests assert that the page files mount real Svelte islands and consume the corresponding API helpers.
- **Accessibility checks.** Every interactive control must have a tokenised `:focus-visible` rule that resolves to a visible outline in both themes. Status badges must pair colour with text or an icon. Icon-only buttons must carry an `aria-label`. Form fields must associate a `<label>` with their control. Tests scan the migrated source for these patterns.
- **Large-list and large-payload fixtures.** Phase 30F adds fixtures that exercise large Feedback (200+ entries), large Pending (50+ pending changes), large Trust (100+ stale notes), and large raw JSON payloads (multi-MB). Tests assert the page consumes internal scroll and does not push horizontal overflow on the page shell.
- **Destructive / write-safety guardrails for Import, Exports, Security, Pending, and Vault Setup.** Tests assert that:
  - Import preview must run before the Write action enables.
  - Export overwrite triggers a distinct destructive variant on the action button and (when enabled) a typed-confirmation flow.
  - Security scan defaults render a full-vault scan; sampling lives under an explicit "Advanced scope" disclosure.
  - Pending accept and reject use the shared typed-confirmation primitive.
  - Vault Setup does not host vault deletion on the onboarding page.
- **Deterministic route and deep-link tests.** Every recommendation, "Open in raw", or "Open in UI" link generated by the UI must resolve to a real `/app/*` route. Tests scan the source and assert every static link target appears in `ui/src/pages/`.

These families are intentionally enforced incrementally per sub-phase so a partial migration is not blocked by guardrails targeting later sub-phases.

---

## Phase 30B - App Shell, Theme, Layout, and Primitive Foundation

Phase 30B is the first implementation slice under Phase 30. It is foundation-only: it ships the layout-mode contract, the dark/light token foundation, and the new CSS primitives that Phase 30C through 30F will consume. No page is redesigned beyond declaring its layout mode. PlaceholderPage on `/app/validation`, `/app/tasks`, and `/app/raw` is preserved for Phase 30D.

The Phase 30B work adds 13 deterministic guardrail tests in `mcp/test_verify.py`, bringing the total to 800.

| Test | Purpose |
|---|---|
| `test_p30b_1_applayout_declares_layout_mode_contract` | AppLayout exposes the four layout modes and emits `data-layout-mode` |
| `test_p30b_2_required_pages_declare_non_standard_layout` | Workflow pages opt out of `standard` per the audit |
| `test_p30b_3_raw_declares_developer_layout` | `/app/raw` uses the `developer` mode |
| `test_p30b_4_global_css_has_data_theme_blocks` | `html[data-theme="dark"]` and `html[data-theme="light"]` both exist |
| `test_p30b_5_token_parity_between_themes` | Every `--cve-*` token has a value in both themes |
| `test_p30b_6_color_scheme_declared` | `color-scheme: dark light` is declared |
| `test_p30b_7_required_primitive_classes_exist` | `cve-workbench`, `cve-toolbar`, `cve-status-strip`, `cve-table-empty`, `cve-banner*`, `cve-details--inspector`, `cve-details__developer-link`, `cve-slide-over*`, `cve-diff*` all present |
| `test_p30b_8_no_raw_tailwind_dark_literals_in_new_primitives` | New Phase 30B CSS uses tokens only, no `bg-zinc-*`, `text-zinc-*`, `border-zinc-*`, `bg-emerald-9*`, `bg-amber-9*`, `bg-rose-9*`, `bg-sky-9*` |
| `test_p30b_9_developer_nav_group_intact` | Sidebar keeps the Developer group with `/app/raw` |
| `test_p30b_10_roadmap_phase27_still_deferred` | Phase 27 stays deferred |
| `test_p30b_11_roadmap_phase28_still_deferred` | Phase 28 stays deferred |
| `test_p30b_12_placeholder_pages_not_removed` | Validation / Tasks / Raw keep `PlaceholderPage` (real impl is Phase 30D) |
| `test_p30b_13_package_json_no_new_runtime_deps` | No React / Vue / icon / animation / charting library introduced |

**Verification steps for Phase 30B:**

```bash
py mcp/test_verify.py            # 842 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

---

## Phase 30C - Dashboard Redesign

Phase 30C is the first page-level redesign on top of the Phase 30B foundation. It rewrites the `/app/` Dashboard around the new primitives: a `cve-toolbar` header, a single `cve-banner` readiness headline, a five-tile `cve-status-strip` (Validation, Security, Coverage, Missing concepts, Feedback) with deep links into the authoritative workflow routes, a two-column `cve-dashboard-grid` with Next best actions and Vault health, and a `cve-details--inspector` block whose `cve-details__developer-link` demotes raw JSON to `/app/raw`. No backend, API, schema, MCP, or dependency change.

The Phase 30C work adds 18 deterministic guardrail tests in `mcp/test_verify.py`, bringing the total to 818 at the time Phase 30C shipped (Phase 30D1 later raised it to 842).

| Test | Purpose |
|---|---|
| `test_p30c_1_index_declares_wide_layout` | `/app/` mounts AppLayout with `layoutMode="wide"` |
| `test_p30c_2_dashboard_uses_cve_toolbar` | Dashboard renders the `cve-toolbar` primitive |
| `test_p30c_3_dashboard_uses_cve_status_strip` | Dashboard renders the `cve-status-strip` with the five canonical tiles |
| `test_p30c_4_dashboard_uses_cve_banner` | Dashboard renders the `cve-banner` readiness headline with all four severities available |
| `test_p30c_5_dashboard_cta_validation_route` | Validation tile CTA deep-links to `/app/validation` |
| `test_p30c_6_dashboard_cta_security_route` | Security tile CTA deep-links to `/app/security` |
| `test_p30c_7_dashboard_cta_feedback_route` | Feedback tile CTA deep-links to `/app/feedback` |
| `test_p30c_8_dashboard_cta_coverage_or_missing_route` | Coverage / missing / tasks tile deep-links to `/app/graph`, `/app/notes`, or `/app/tasks` |
| `test_p30c_9_dashboard_no_inline_raw_json_block` | Dashboard has no inline raw JSON disclosure (no `Show raw JSON`, no `JSON.stringify`, no `cve-raw`) |
| `test_p30c_10_dashboard_developer_deep_link` | Dashboard exposes the `cve-details__developer-link` contract to `/app/raw` |
| `test_p30c_11_dashboard_no_tailwind_dark_literals` | Dashboard and `index.astro` use semantic tokens, not Tailwind dark literals |
| `test_p30c_12_dashboard_last_checked_text` | Dashboard surfaces deterministic last-checked text |
| `test_p30c_13_dashboard_status_tile_modifiers_in_css` | `global.css` defines Phase 30C status-tile / dashboard-grid / next-action primitives using tokens only |
| `test_p30c_14_no_dashboard_missing_concepts_duplicate_heading` | Old `Issue Review` duplication is removed |
| `test_p30c_15_roadmap_phase30c_complete_others_planned` | ROADMAP marks 30C complete; 30D/30E/30F planned; 27/28 deferred |
| `test_p30c_16_placeholder_pages_not_prematurely_removed` | Validation / Tasks / Raw keep `PlaceholderPage` (real impl is Phase 30D) |
| `test_p30c_17_no_new_runtime_dependencies` | No React / Vue / icon / animation / charting library introduced |
| `test_p30c_18_no_em_dashes_in_dashboard_files` | Phase 30C files contain no em dashes |

**Verification steps for Phase 30C:**

```bash
py mcp/test_verify.py            # 818 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

---

## Phase 30D1 - Validation, Tasks, and Raw Real Implementations

Phase 30D1 is the first sub-slice of Phase 30D. It replaces the placeholder pages at `/app/validation`, `/app/tasks`, and `/app/raw` with real, fully wired Svelte islands on top of the Phase 30B foundation and the Phase 30C primitives. It uses only the read-only API helpers already exported from `ui/src/lib/api.ts`. No backend route, schema, MCP, or runtime dependency was added. The parent Phase 30D remains In Progress; Phase 30D2 (Notes and Graph) and Phase 30D3 (Import, Bundles, Exports, Security) remain planned.

The Phase 30D1 work adds 24 deterministic guardrail tests in `mcp/test_verify.py`, bringing the total to 842.

| Test | Purpose |
|---|---|
| `test_p30d1_1_validation_page_drops_placeholder` | `/app/validation` no longer imports or renders `PlaceholderPage` |
| `test_p30d1_2_tasks_page_drops_placeholder` | `/app/tasks` no longer imports or renders `PlaceholderPage` |
| `test_p30d1_3_raw_page_drops_placeholder` | `/app/raw` no longer imports or renders `PlaceholderPage` |
| `test_p30d1_4_validation_mounts_real_component` | `validation.astro` mounts `ValidationReview.svelte` with a `client:` directive |
| `test_p30d1_5_tasks_mounts_real_component` | `tasks.astro` mounts `TaskReview.svelte` with a `client:` directive |
| `test_p30d1_6_raw_mounts_real_component` | `raw.astro` mounts `RawDeveloperExplorer.svelte` with a `client:` directive |
| `test_p30d1_7_validation_layout_mode_wide` | `validation.astro` keeps `layoutMode="wide"` |
| `test_p30d1_8_tasks_layout_mode_wide` | `tasks.astro` keeps `layoutMode="wide"` |
| `test_p30d1_9_raw_layout_mode_developer` | `raw.astro` keeps `layoutMode="developer"` |
| `test_p30d1_10_validation_uses_validation_helper` | `ValidationReview` consumes `fetchValidation` from `../lib/api` |
| `test_p30d1_11_tasks_uses_tasks_helper` | `TaskReview` consumes `fetchTasks` from `../lib/api` |
| `test_p30d1_12_raw_catalogue_is_safe_read_only` | Raw catalogue references only safe GET helpers; destructive helpers and non-GET methods are absent |
| `test_p30d1_13_validation_uses_phase30b_primitives` | `ValidationReview` uses `cve-toolbar` / `cve-banner` / `cve-status-strip` / `cve-table` |
| `test_p30d1_14_tasks_uses_phase30b_primitives` | `TaskReview` uses `cve-toolbar` / `cve-banner` / `cve-status-strip` / `cve-table` |
| `test_p30d1_15_raw_uses_toolbar_and_bounded_viewer` | `RawDeveloperExplorer` uses `cve-toolbar` and the bounded `cve-p30d1-raw-pre` viewer; `global.css` defines it with `max-height` + `overflow: auto` |
| `test_p30d1_16_no_tailwind_dark_literals_in_migrated_files` | The three Phase 30D1 pages and components avoid Tailwind dark palette literals |
| `test_p30d1_17_raw_no_unbounded_full_page_pre` | Every `<pre>` in the Raw component is annotated with `cve-raw` and `cve-p30d1-raw-pre` |
| `test_p30d1_18_developer_deep_link_contract_tolerated` | Validation/Tasks expose `cve-details__developer-link` to `/app/raw`; Raw tolerates `?vault`, `?endpoint`, `?source`, `?focus` |
| `test_p30d1_19_roadmap_phase27_still_deferred` | ROADMAP keeps Phase 27 Deferred |
| `test_p30d1_20_roadmap_phase28_still_deferred` | ROADMAP keeps Phase 28 Deferred |
| `test_p30d1_21_phase30d_not_marked_complete` | Parent Phase 30D is not marked Complete; 30D1 row added; 30D2 and 30D3 documented |
| `test_p30d1_22_phase30e_and_30f_planned` | Phase 30E and 30F remain Planned |
| `test_p30d1_23_no_new_runtime_dependencies` | `ui/package.json` introduces no React/Vue/icon/animation/charting/syntax-highlighter dependency |
| `test_p30d1_24_no_em_dashes_in_phase30d1_files` | Phase 30D1 files contain no em dashes |

**Verification steps for Phase 30D1:**

```bash
py mcp/test_verify.py            # 866 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

---

## Phase 30D2 - Notes and Graph Workspace Redesigns

Phase 30D2 is the second sub-slice of Phase 30D. It rebuilds `/app/notes` and `/app/graph` as split-pane workspaces on top of the Phase 30B primitives. The legacy `'graph' | 'inspector' | 'missing'` tab model in the Graph page is removed; missing concepts are surfaced inline in the inspector. Inline raw JSON disclosure panels for `/notes`, `/note`, `/query`, `/graph`, `/graph/neighbors`, `/graph/related`, `/graph/missing`, and `/missing` are removed from the primary inspector, and both pages link to `/app/raw` for full diagnostic JSON via a `cve-details--inspector` block with the `cve-details__developer-link` contract. All filters, badges, the trust-import panel, the imported/draft contract, the safe edit workflow on `/app/notes`, and the non-destructive ranked-missing-concept action card on `/app/graph` are preserved. No backend route, schema, MCP, or runtime dependency was added. Phase 30D3 (Import, Bundles, Exports, Security) has since landed and the parent Phase 30D is now Complete.

The Phase 30D2 work adds 24 deterministic guardrail tests in `mcp/test_verify.py`, bringing the total to 866.

| Test | Purpose |
|---|---|
| `test_p30d2_1_notes_layout_workspace` | `/app/notes` declares `layoutMode="workspace"` |
| `test_p30d2_2_graph_layout_workspace` | `/app/graph` declares `layoutMode="workspace"` |
| `test_p30d2_3_notes_uses_cve_toolbar` | `NoteBrowser` uses the `cve-toolbar` primitive |
| `test_p30d2_4_notes_uses_cve_workbench` | `NoteBrowser` uses `cve-workbench`, `cve-workbench__rail`, `cve-workbench__inspector` |
| `test_p30d2_5_notes_internal_scroll_regions` | `NoteBrowser` scrolls inside its panes via `cve-scroll-region` |
| `test_p30d2_6_notes_preserves_imported_and_draft_filters_and_badges` | Imported / draft filters, badges, trust-import panel preserved |
| `test_p30d2_7_notes_no_primary_inline_raw_json` | No raw JSON disclosure panels for `/notes`, `/note`, or `/query` in the primary inspector |
| `test_p30d2_8_notes_developer_deep_link` | `NoteBrowser` exposes a Developer deep-link to `/app/raw?endpoint=notes&source=notes` |
| `test_p30d2_9_graph_uses_cve_toolbar` | `GraphExplorer` uses the `cve-toolbar` primitive |
| `test_p30d2_10_graph_uses_cve_workbench` | `GraphExplorer` uses `cve-workbench`, `cve-workbench__rail`, `cve-workbench__inspector` |
| `test_p30d2_11_graph_internal_scroll_regions` | `GraphExplorer` scrolls inside its panes via `cve-scroll-region` |
| `test_p30d2_12_graph_no_old_tab_model` | `GraphExplorer` removes the tabbed graph/inspector/missing model |
| `test_p30d2_13_graph_inline_missing_concepts` | `GraphExplorer` surfaces missing concepts inline in the inspector |
| `test_p30d2_14_graph_uses_existing_api_helpers` | `GraphExplorer` consumes `fetchGraph`, `fetchGraphNeighbors`, `fetchGraphRelated`, `fetchGraphMissing`, `fetchMissing` |
| `test_p30d2_15_graph_developer_deep_link` | `GraphExplorer` exposes a Developer deep-link to `/app/raw?endpoint=graph&source=graph` |
| `test_p30d2_16_no_tailwind_dark_literals_in_migrated_files` | The four Phase 30D2 files avoid Tailwind dark palette literals |
| `test_p30d2_17_notes_graph_search_filter_labels` | Every text/search/number `<input>` has an associated `<label for>` or `aria-label` |
| `test_p30d2_18_notes_graph_static_links_resolve` | Every static `/app/<page>` link in the migrated components resolves to a real page file |
| `test_p30d2_19_phase27_still_deferred` | ROADMAP keeps Phase 27 Deferred |
| `test_p30d2_20_phase28_still_deferred` | ROADMAP keeps Phase 28 Deferred |
| `test_p30d2_21_phase30d2_complete_and_30d_not_complete` | ROADMAP marks Phase 30D2 Complete; parent 30D not Complete; 30D3 Planned |
| `test_p30d2_22_phase30e_and_30f_planned` | Phase 30E and 30F remain Planned |
| `test_p30d2_23_no_new_runtime_dependencies` | `ui/package.json` introduces no React/Vue/icon/animation/charting/syntax-highlighter dependency |
| `test_p30d2_24_no_em_dashes_in_phase30d2_files` | Phase 30D2 files contain no em dashes |

**Verification steps for Phase 30D2:**

```bash
py mcp/test_verify.py            # 890 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

---

## Phase 30D3 - Import, Bundles, Exports, and Security Workflow Redesigns

Phase 30D3 is the third and final sub-slice of Phase 30D. It rebuilds `/app/import`, `/app/bundles`, `/app/exports`, and `/app/security` on top of the Phase 30B primitives. All four pages now use `AppLayout layoutMode="wide"`, sectioned workflow cards (`cve-p30d3-section`), a `cve-toolbar` header with a state pill, banner-driven status messages (`cve-banner`), `cve-status-strip` summaries, and Developer deep-links to `/app/raw`. Raw JSON is confined to `cve-details--inspector` blocks - never a primary panel. ImportReview preserves all Phase 26 testids and source types (markdown + obsidian), separates Preview from Write behind a confirmation checkbox and stale-detection banner, and surfaces follow-up links to Notes, Validation, Tasks, Trust, and Security. BundleBuilder and ExportPackage share a new `ui/src/lib/bundleConfig.ts` helper so both workflows agree on filters, sections, and budgets. ExportPackage defaults the security gate to ON and gates Submit behind a typed `OVERWRITE` confirmation when overwrite is requested. SecurityScan defaults to a full-vault scan (no sampling) with a pre-run note count tile via `fetchNotes`; sampling, filters, sections, and per-note budgets are demoted to an Advanced scope `<details>` disclosure that is closed by default. Findings render in a bounded `cve-table` with severity / rule / path / field / detail columns inside an internal-scroll region. No backend route, schema, MCP, or runtime dependency was added. The parent Phase 30D is now Complete; Phases 30E and 30F remain Planned.

The Phase 30D3 work adds 24 deterministic guardrail tests in `mcp/test_verify.py`, bringing the total to 890.

| Test | Purpose |
|---|---|
| `test_p30d3_1_all_pages_layout_wide` | All four workflow pages declare `layoutMode="wide"` |
| `test_p30d3_2_all_components_use_cve_toolbar` | Each redesigned component renders a `cve-toolbar` header |
| `test_p30d3_3_all_components_use_cve_banner` | Each redesigned component renders at least one `cve-banner` |
| `test_p30d3_4_all_components_use_cve_status_strip` | Each redesigned component renders a `cve-status-strip` with `cve-status-tile` entries |
| `test_p30d3_5_import_preserves_existing_source_types` | ImportReview keeps the markdown + obsidian source types only |
| `test_p30d3_6_import_separates_preview_and_write` | ImportReview keeps Preview and Write as separate buttons with stale-banner and confirmation checkbox |
| `test_p30d3_7_bundles_uses_shared_helper` | BundleBuilder imports from the shared `bundleConfig` helper |
| `test_p30d3_8_bundles_sticky_action_and_state_pane` | BundleBuilder has a sticky Generate action and a state-aware right pane |
| `test_p30d3_9_exports_uses_shared_helper` | ExportPackage imports from the shared `bundleConfig` helper |
| `test_p30d3_10_exports_security_gate_default_on` | ExportPackage defaults `requireSecurityPass` to true |
| `test_p30d3_11_exports_overwrite_confirmation_gate` | ExportPackage gates Submit behind a typed `OVERWRITE` confirmation |
| `test_p30d3_12_exports_separate_route_from_bundles` | Exports lives on its own route distinct from Bundles |
| `test_p30d3_13_security_full_vault_default` | SecurityScan defaults to a full-vault scan with a pre-run note count tile |
| `test_p30d3_14_security_advanced_disclosure` | SecurityScan demotes sampling / filters / budgets to an Advanced scope disclosure |
| `test_p30d3_15_security_bounded_findings_table` | SecurityScan renders findings in a bounded `cve-table` inside `cve-p30d3-findings-table` |
| `test_p30d3_16_state_pills_present` | Each redesigned component exposes a state-pill testid |
| `test_p30d3_17_no_primary_inline_raw_json` | Raw JSON only appears inside `cve-details--inspector` blocks |
| `test_p30d3_18_developer_deep_links` | Each redesigned component exposes a Developer deep-link to `/app/raw` |
| `test_p30d3_19_no_tailwind_dark_literals` | Phase 30D3 files avoid Tailwind dark palette literals |
| `test_p30d3_20_form_labels` | Every text/search/number/email input has a `<label for>` or `aria-label` |
| `test_p30d3_21_static_links_resolve` | Every static `/app/<page>` link in 30D3 components resolves to a real page file |
| `test_p30d3_22_phase27_28_still_deferred` | ROADMAP keeps Phase 27 and 28 Deferred |
| `test_p30d3_23_phase30d3_and_30d_complete` | ROADMAP marks Phase 30D3 and the parent Phase 30D Complete; 30E/30F remain Planned |
| `test_p30d3_24_no_em_dashes_in_phase30d3_files` | Phase 30D3 files contain no em dashes and `ui/package.json` introduces no new runtime dependencies |

**Verification steps for Phase 30D3:**

```bash
py mcp/test_verify.py            # 890 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

---

## Phase 30E1 - Pending / Trust / Feedback Governance Polish

Phase 30E1 is the first sub-slice of Phase 30E. It rebuilds `/app/pending`, `/app/trust`, and `/app/feedback` on top of the Phase 30B primitives. All three pages now use a `cve-toolbar` header with a state pill, a `cve-status-strip` summary, and a Developer deep-link to `/app/raw` built by the shared helper in `ui/src/lib/phase30e1.ts`. PendingChanges renders a `cve-workbench` (queue rail + inspector) with `cve-diff` and gates Accept / Reject behind typed `ACCEPT` / `REJECT` confirmation; the inspector surfaces provenance, trust impact, and hash warnings. TrustEvidence leads with a stale and low-trust governance queue that links each row to Notes, Pending, and Feedback, demoting the legacy Evidence Builder into a closed `<details>` disclosure while keeping the `cve-trust-warning` disclaimer. FeedbackWorkflow uses a labelled filter rail and a `cve-table` triage view with deterministic severity-weighted sort, moves Add Feedback into the toolbar inside a `cve-slide-over`, and pins an Improvement Tasks panel with a deterministic empty state. Raw JSON stays confined to `cve-details--inspector`. No backend route, schema, MCP, or runtime dependency was added.

The Phase 30E1 work adds 23 deterministic guardrail tests in `mcp/test_verify.py`, taking the total from 890 to 913.

| Test | Purpose |
|---|---|
| `test_p30e1_1_pages_use_expected_layout_modes` | Governance pages declare the expected layout modes |
| `test_p30e1_2_components_use_cve_toolbar` | Each redesigned component renders a `cve-toolbar` header |
| `test_p30e1_3_components_use_banner_and_status_strip` | Each redesigned component renders `cve-banner` and `cve-status-strip` |
| `test_p30e1_4_pending_workbench_and_diff` | PendingChanges uses `cve-workbench` primitives and `cve-diff` |
| `test_p30e1_5_pending_internal_scroll_regions` | PendingChanges exposes queue + inspector internal-scroll testids |
| `test_p30e1_6_pending_typed_confirmation_gates` | PendingChanges requires typed `ACCEPT` / `REJECT` confirmation |
| `test_p30e1_7_pending_provenance_trust_hash` | PendingChanges inspector shows provenance, trust impact, and hash warning |
| `test_p30e1_8_trust_disclaimer_preserved` | TrustEvidence retains the `cve-trust-warning` disclaimer |
| `test_p30e1_9_trust_governance_queue_leads` | Trust governance queue precedes the Evidence Builder |
| `test_p30e1_10_trust_evidence_builder_demoted` | TrustEvidence Evidence Builder is demoted to a `<details>` disclosure |
| `test_p30e1_11_trust_row_links` | Trust rows link to `/app/notes` and governance routes |
| `test_p30e1_12_feedback_table_and_filters` | FeedbackWorkflow uses a `cve-table` triage view with labelled filters |
| `test_p30e1_13_feedback_add_action_and_slide_over` | Add Feedback lives in the toolbar and opens a `cve-slide-over` |
| `test_p30e1_14_feedback_severity_sort_and_tasks_panel` | FeedbackWorkflow uses the `severityWeight` sort and pins a tasks panel |
| `test_p30e1_15_state_pills_present` | Each redesigned component exposes a state-pill testid |
| `test_p30e1_16_no_primary_inline_raw_json` | Raw JSON only appears inside `cve-details--inspector` blocks |
| `test_p30e1_17_developer_deep_links` | Each redesigned component exposes a Developer deep-link to `/app/raw` |
| `test_p30e1_18_no_tailwind_dark_literals` | Phase 30E1 files avoid Tailwind dark palette literals |
| `test_p30e1_19_form_labels` | Every text/search input in 30E1 components is labelled |
| `test_p30e1_20_static_links_resolve` | Every static `/app/<page>` link in 30E1 components resolves to a real page file |
| `test_p30e1_21_phase27_28_still_deferred` | ROADMAP keeps Phase 27 and 28 Deferred |
| `test_p30e1_22_roadmap_phase_rows` | ROADMAP marks Phase 30E1 Complete, Phase 30E In Progress, 30E2 + 30F Planned |
| `test_p30e1_23_no_em_dashes_or_new_deps` | Phase 30E1 files contain no em dashes and `ui/package.json` introduces no new runtime dependencies |

**Verification steps for Phase 30E1:**

```bash
py mcp/test_verify.py            # 937 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

---

## Phase 30E2 - Controller and Vault Setup Polish

Phase 30E2 closes out Phase 30E. `/app/controller` is rebuilt as a two-column command-centre at xl+: the left column owns readiness, blockers, warnings, and the service summary; the right column owns ranked recommendations and the next-best action. Readiness polarity is corrected via `readinessPolarity()` so negative flags (`has_tasks`, `has_missing_concepts`, `has_feedback_warnings`) never render as positive. Recommendations sort deterministically and deep-link to authoritative `/app/*` routes via `recommendationRoute()`. Raw controller and plan responses are demoted to a `cve-details--inspector` disclosure with Developer deep-links into `/app/raw` built by `buildRawDeepLink()`. `/app/vault-setup` collapses scattered per-field cards into one grouped `cve-p30e2-form-grid` panel and preserves live validation plus the bootstrap preview. Destructive vault deletion is removed from the primary setup form and relocated into a dedicated management panel; the actual delete flow runs inside a `cve-slide-over` that names the target vault, explains the real backend semantics (files deleted from disk, `config/config.yaml` rewritten, action not reversible by the app) sourced from `VAULT_DELETE_SEMANTICS`, and requires a typed `DELETE <vault>` confirmation enforced by `isDeleteConfirmed()`. `demo-vault` is protected via `VAULT_DELETE_PROTECTED`. The shared helper `ui/src/lib/phase30e2.ts` re-exports `buildRawDeepLink` from `phase30e1` and exposes the readiness, recommendation, and deletion contracts. No backend route, schema, MCP, or runtime dependency was added. Phase 30E is now Complete; Phase 30F remains Planned. Phase 27 and Phase 28 remain Deferred.

The Phase 30E2 work adds 24 deterministic guardrail tests in `mcp/test_verify.py`, bringing the total from 913 to 937.

| Test | Purpose |
|---|---|
| `test_p30e2_1_pages_use_expected_layout_modes` | 30E2 pages declare the expected layout modes |
| `test_p30e2_2_controller_uses_cve_toolbar_banner_status_strip` | Controller renders `cve-toolbar`, `cve-banner`, and `cve-status-strip` |
| `test_p30e2_3_controller_two_column_command_grid_at_xl` | Controller uses the two-column command-centre grid at xl+ |
| `test_p30e2_4_controller_readiness_polarity_helper` | `readinessPolarity()` classifies negative flags correctly |
| `test_p30e2_5_controller_recommendations_deep_link_to_authoritative_routes` | `recommendationRoute()` covers the authoritative `/app/*` targets |
| `test_p30e2_6_controller_raw_json_not_primary_inline_ux` | Controller raw JSON appears only inside `cve-details--inspector` |
| `test_p30e2_7_controller_developer_deep_link_to_raw` | Controller exposes Developer deep-links to `/app/raw` |
| `test_p30e2_8_vault_setup_uses_cve_toolbar_and_banner` | VaultSetup renders `cve-toolbar` + `cve-banner` |
| `test_p30e2_9_vault_setup_grouped_form_panel` | VaultSetup uses one grouped form panel (no legacy Danger Zone wrapper) |
| `test_p30e2_10_vault_setup_preserves_validation_and_preview` | VaultSetup keeps live validation and the bootstrap preview |
| `test_p30e2_11_destructive_delete_not_in_primary_setup_form` | Destructive delete is not inside the primary setup form |
| `test_p30e2_12_destructive_delete_in_separate_management_and_slide_over` | Destructive delete lives in a management panel + `cve-slide-over` |
| `test_p30e2_13_destructive_delete_requires_typed_confirmation` | Destructive delete requires the typed `DELETE <vault>` phrase |
| `test_p30e2_14_delete_button_disabled_until_confirmed` | Delete submit is disabled until typed confirmation matches |
| `test_p30e2_15_delete_warning_explains_target_and_semantics` | Delete warning names target vault and real backend semantics |
| `test_p30e2_16_delete_protected_vault_disabled` | `demo-vault` delete trigger is disabled (protected vault) |
| `test_p30e2_17_no_tailwind_dark_literals` | Phase 30E2 files avoid Tailwind dark palette literals |
| `test_p30e2_18_form_labels` | Every text/search input in 30E2 components is labelled |
| `test_p30e2_19_static_links_resolve` | Every static `/app/<page>` link in 30E2 components resolves to a real page file |
| `test_p30e2_20_phase27_28_still_deferred` | ROADMAP keeps Phase 27 and 28 Deferred |
| `test_p30e2_21_roadmap_30e2_complete_parent_30e_complete` | ROADMAP marks 30E1+30E2+30E Complete, 30F Planned, 30 not Complete |
| `test_p30e2_22_state_pills_present` | Both 30E2 components expose a state-pill testid |
| `test_p30e2_23_no_em_dashes_and_no_new_deps` | Phase 30E2 files contain no em dashes and `ui/package.json` introduces no new runtime dependencies |
| `test_p30e2_24_global_css_has_phase30e2_block` | `global.css` declares the Phase 30E2 token primitives |

**Verification steps for Phase 30E2:**

```bash
py mcp/test_verify.py            # 937 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

---

## Phase 30F - Final QA, Light Mode, Accessibility, and Responsive Guardrails

Phase 30F is the closing slice of Phase 30 (UI Release Quality Pass). It delivers a user-facing light/dark theme toggle, completes the `--cve-*` token sweep across both `html[data-theme="dark"]` and `html[data-theme="light"]` so every primitive renders in either theme, tokenises the AppLayout chrome through new `cve-app-chrome-bg`, `cve-app-chrome-border`, `cve-app-chrome-text-strong`, `cve-app-chrome-text-muted`, and `cve-app-chrome-text-faint` classes, replaces the hard-coded raw block background with `var(--cve-raw-bg)`, and adds deterministic source-level guardrails covering accessibility (form labels, icon-only button names, status-badge text content, slide-over dialog wiring with role, modal flag, accessible name, and Close control), responsive layout (bounded `cve-raw` and `cve-diff` viewports, table overflow inside `cve-table-wrap` and `cve-p30d3-table-wrap`, narrow-viewport workbench fallback at under 900px, full-width slide-overs at under 640px), write-safety contracts on Import (preview/write separation), Export (typed `OVERWRITE`), Security (full-vault default + Advanced scope), Pending (typed Accept and Reject), Feedback (Add gated via slide-over), and Vault Setup (typed `DELETE <vault>` inside a dedicated slide-over with `demo-vault` protection), and route integrity (no stale `/app/api`, no invented `/app/registry`, `/app/semantic`, `/app/search`, `/app/settings`, `/app/manage`, or `/app/admin` routes anywhere in migrated UI).

The user-facing light-mode toggle is wired in `AppLayout.astro` on both the desktop and mobile top bars. An inline (non-hydrated) bootstrap script applies `data-theme` on `documentElement` before paint, defaulting to `dark` when no preference is saved. The toggle persists user preference under the `cve-theme` localStorage key, exposes accessible name and pressed state via `aria-label` and `aria-pressed`, and keeps a visible text label that stays in sync with the active theme.

Phase 30F does not perform browser visual verification or screen-reader traversal in the automated suite; those checks remain manual and are tracked in `RELEASE_CHECKLIST.md`. The Phase 30F work adds 48 deterministic guardrail tests (Phase 30F-1 through Phase 30F-48) in `mcp/test_verify.py`, bringing the total from 937 to 985. Phase 30F is Complete; parent Phase 30 (UI Release Quality Pass) is Complete. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain explicitly Deferred and are neither started nor implied.

**Verification steps for Phase 30F:**

```bash
py mcp/test_verify.py            # 985 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

---



## Phase 30F - Final QA, Light Mode, Accessibility, and Responsive Guardrails

Phase 30F is the closing slice of Phase 30 (UI Release Quality Pass). It delivers a user-facing light/dark theme toggle, completes the `--cve-*` token sweep across both `html[data-theme="dark"]` and `html[data-theme="light"]` so every primitive renders in either theme, tokenises the AppLayout chrome, and adds deterministic source-level guardrails covering accessibility (form labels, icon-only button names, status-badge text content, slide-over dialog wiring), responsive layout (bounded raw/diff viewports, table overflow wraps, narrow-viewport workbench fallback at under 900px, full-width slide-overs at under 640px), write-safety contracts on Import, Export, Security, Pending, Feedback, and Vault Setup, and route integrity (no stale `/app/api` and no invented `/app/registry`, `/app/semantic`, `/app/search`, `/app/settings`, `/app/manage`, or `/app/admin` routes). Phase 30F adds the user-facing light-mode toggle wired in `AppLayout.astro` with an inline pre-paint bootstrap script, persistence under the `cve-theme` localStorage key, accessible labelling that stays in sync with the active theme, and a default-dark fallback when no preference is saved. Phase 30F does not perform browser visual verification or screen-reader traversal in the automated suite; those checks remain manual and are tracked in `RELEASE_CHECKLIST.md`. The Phase 30F work adds 48 deterministic guardrail tests in `mcp/test_verify.py`, bringing the total from 937 to 985. Phase 30F is Complete; parent Phase 30 (UI Release Quality Pass) is Complete. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain explicitly Deferred and are neither started nor implied.

**Verification steps for Phase 30F:**

```bash
py mcp/test_verify.py            # 985 tests, all must pass
py run.py validate               # vault still valid
py run.py security               # status: pass
py run.py feedback               # exits 0, valid JSON
py run.py export --overwrite     # status: ok
cd ui; npm run build             # builds without errors
```

---
