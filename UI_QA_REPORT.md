# UI QA Stabilisation Report

## Summary

Full pre-Phase-19 QA and UX stabilisation pass across all 11 `/app/*` routes of the
Context Vault Engine UI. Six categories of stale/misleading UI text were identified and
corrected, six deterministic regression tests were added to the test suite (total now 284),
all backend CLI verifications passed, and the Astro build completed cleanly.

---

## Decision

**PROCEED** — All checks pass. UI stabilisation is ready for commit and Phase 19 can begin next.

---

## Audit Findings (per route)

| Route | Component | Finding | Action |
|---|---|---|---|
| `/` (Dashboard) | `Dashboard.svelte` | API envelope handling correct; raw JSON collapsed by default; independent panel loading | No change needed |
| `/notes` | `NoteBrowser.svelte` | Envelope correct; search/filter functional | No change needed |
| `/vault-setup` | `VaultSetup.svelte` | Envelope correct; stage-based UI working | No change needed |
| `/bundles` | `BundleBuilder.svelte` | Envelope correct; file list dynamic | No change needed |
| `/graph` | `GraphExplorer.svelte` | Stale `<!-- Graph Explorer — Phase 16 -->` comment | Updated comment |
| `/exports` | `ExportPackage.svelte` | `context.html` present in file table (API-driven); conflict gate working | No change needed |
| `/feedback` | `FeedbackWorkflow.svelte` | Envelope correct; `isOk(result)` / `result.data` pattern | No change needed |
| `/security` | `SecurityScan.svelte` | Envelope correct; threat-level colours functional | No change needed |
| `/validation` | `PlaceholderPage.astro` | Sidebar showed "soon" badge; stale "Planned for Phase 12" text; wrong `py run.py api-/-raw-output` CLI derivation | Fixed badge + text + CLI |
| `/tasks` | `PlaceholderPage.astro` | Same issues as `/validation` | Fixed badge + text + CLI |
| `/raw` | `PlaceholderPage.astro` | Same issues as `/validation`; CLI would have produced nonsense command | Fixed badge + text + CLI |

**Nav sidebar (AppLayout.astro):** Validation, Tasks, and API/Raw items displayed a `<span>soon</span>` badge with `opacity-60` despite all three routes being accessible. Footer read "Phase 16 — Graph Explorer" which was two phases stale. Both fixed.

---

## Files Changed

| File | Change |
|---|---|
| `ui/src/layouts/AppLayout.astro` | Removed conditional "soon" badge logic; updated footer to "Phase 18 — Stable" |
| `ui/src/components/PlaceholderPage.astro` | Removed `phase` prop and stale text; added `cliCommand` prop; new static body copy |
| `ui/src/pages/validation.astro` | `phase="12"` → `cliCommand="py run.py validate"` |
| `ui/src/pages/tasks.astro` | `phase="12"` → `cliCommand="py run.py improve"` |
| `ui/src/pages/raw.astro` | `phase="12"` → `cliCommand="# API available at http://127.0.0.1:8000 when the server is running"` |
| `ui/src/components/GraphExplorer.svelte` | HTML comment: "Graph Explorer — Phase 16" → "Graph Explorer" |
| `mcp/test_verify.py` | Added 6 PQAS tests; added `_UI_SRC` constant; updated `main()` dispatch |
| `README.md` | Test count badge: 272 → 284 |
| `TESTING.md` | Test count: 272 → 284; added "Phase QAS — UI QA Stabilisation" section |

---

## Behaviour Fixed

1. **"soon" badges on live routes** — Validation, Tasks, and API/Raw sidebar nav items displayed
   a "soon" badge and reduced opacity despite being navigable routes backed by working API
   endpoints. Removed entirely.

2. **Stale sidebar footer** — Footer read "Phase 16 — Graph Explorer". Updated to "Phase 18 — Stable".

3. **Stale placeholder text** — `PlaceholderPage` said "Planned for Phase 12. The backend API
   and CLI already support this functionality." which was misleading (Phase 12 shipped long ago).
   New copy: "Backend support is fully available. A dedicated UI view is planned for a future release."

4. **Broken CLI command derivation** — `PlaceholderPage` computed the CLI hint from `label.toLowerCase().replace(/ /g, '-')` which would produce `py run.py api-/-raw-output` for the Raw page. Replaced with an explicit `cliCommand` prop per page.

5. **Stale HTML comment** — `GraphExplorer.svelte` contained `<!-- Graph Explorer — Phase 16 -->`. Updated to `<!-- Graph Explorer -->`.

6. **Stale test counts** — README and TESTING.md both cited 272 tests; actual count was 278 before
   this session and is 284 after adding PQAS tests.

---

## Tests Added or Updated

Six new PQAS (Phase QA Stabilisation) tests added to `mcp/test_verify.py`:

| ID | Function | Assertion |
|---|---|---|
| PQAS-1 | `test_pqas_applayout_no_soon_badges` | `">soon<"` not present in `AppLayout.astro` |
| PQAS-2 | `test_pqas_applayout_footer_not_stale` | "Phase 16" / "Phase 15" / "Phase 14" not present in `AppLayout.astro` |
| PQAS-3 | `test_pqas_placeholderpage_no_stale_phase_text` | "Planned for Phase" not present in `PlaceholderPage.astro` |
| PQAS-4 | `test_pqas_all_routes_covered_in_route_test` | All 11 expected `.astro` page files exist in `ui/src/pages/` |
| PQAS-5 | `test_pqas_export_context_html_in_source` | `"context.html"` referenced in `core/shared/context_package.py` |
| PQAS-6 | `test_pqas_feedback_envelope_regression` | `GET /feedback` via TestClient returns `{status: "ok", data: {entries: [...]}}` |

**Total test count: 284** (was 278 before this session; pre-session docs cited 272 which was also stale).

---

## Verification Results

| Command | Result |
|---|---|
| `python mcp/test_verify.py` | **ALL VERIFICATION TESTS PASSED** (284 tests) |
| `python run.py validate` | Total: 19 / Valid: 19 / Invalid: 0 — **PASSED** |
| `python run.py security` | `status: pass` |
| `python run.py feedback` | `warnings: [], errors: []` |
| `python run.py export --overwrite` | `status: ok` — files: context.json, context.md, validation.json, graph.json, feedback-summary.json, **context.html**, manifest.json |
| `cd ui && npm run build` | **11 pages built in 5.13s — Complete!** |
| `git status --short` | Exactly 9 modified files; no untracked, no dist/ leakage |

---

## Manual Checks

The following were confirmed by source inspection during the audit:

- All Svelte components use `isOk(result)` / `result.data` from `ui/src/lib/api.ts` — no raw `.status` string comparisons
- Raw JSON panels are hidden by default (`<details>` closed / `showRaw = false`) across Dashboard, SecurityScan, and BundleBuilder
- Active nav state is baked at Astro build time (correct `aria-current="page"` per route, no runtime mismatch)
- `context.html` is produced by `context_html.py` and included in `context_package.py`; confirmed present in export output
- The `FeedbackWorkflow` `/feedback` POST correctly writes to vault and the GET response envelope matches `{status, data: {entries, warnings, errors}}`

---

## Issues Found

All issues found were resolved in this session. No deferred issues remain.

| # | Severity | Location | Description | Status |
|---|---|---|---|---|
| 1 | Medium | `AppLayout.astro` | "soon" badge on 3 live nav items | Fixed |
| 2 | Low | `AppLayout.astro` | Footer two phases stale | Fixed |
| 3 | Medium | `PlaceholderPage.astro` | Stale phase text misleads users about feature maturity | Fixed |
| 4 | Low | `PlaceholderPage.astro` | CLI command derived from label string (broken for Raw) | Fixed |
| 5 | Low | `GraphExplorer.svelte` | Stale HTML comment | Fixed |
| 6 | Low | `README.md` / `TESTING.md` | Test count stale by 6–12 | Fixed |

---

## Follow-up Needed

None required before Phase 19. The following are aspirational for future cycles:

- Full Svelte component views for Validation and Tasks routes (currently placeholder)
- E2E browser tests (Playwright) for the 11 routes
- API rate-limit and structured-logging tests decoupled from CWD so they pass under `pytest` as well as `python mcp/test_verify.py`

---

UI stabilisation is ready for commit and Phase 19 can begin next.
