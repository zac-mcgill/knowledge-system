# Release Checklist

Use this checklist before tagging a release. All steps are local and deterministic.

---

## Phase 31A - Release Candidate Verification

Phase 30 is complete. Phase 31A is release-candidate verification only. It does not start Phase 27 (Registry and Reuse Layer) or Phase 28 (Optional Semantic Retrieval); both remain Deferred. No new feature work, no backend route changes, no API contract changes, no schema changes, no MCP changes, no new dependencies, no UI redesign, and no new write actions are introduced by Phase 31A. Phase 30F automated source-level tests do not replace manual visual QA or screen-reader QA; those remain manual and are tracked below.

### A. Automated Verification Commands

Run these commands locally, in order, on a clean working tree. All must pass before tagging a release candidate.

```bash
py mcp/test_verify.py
py run.py validate
py run.py security
py run.py feedback
py run.py export --overwrite
cd ui && npm run build
git status --short
```

- [ ] `py mcp/test_verify.py` exits 0 and prints `ALL VERIFICATION TESTS PASSED` (current target: all tests green; the suite is sized in the hundreds of tests and is the source of truth, not this checklist)
- [ ] `py run.py validate` reports all notes valid
- [ ] `py run.py security` exits 0 with status `pass` or `warning` only (never `fail`)
- [ ] `py run.py feedback` exits 0 and prints valid JSON
- [ ] `py run.py export --overwrite` writes a fresh package to `dist/`
- [ ] `cd ui && npm run build` completes with zero errors
- [ ] `git status --short` is clean except for expected untracked artefacts (`dist/`, `ui/dist/`, generated state files) which must remain untracked

### B. Browser Visual QA Matrix (Manual)

This matrix is manual unless actually performed. The deterministic Phase 30F source-level checks do not replace this pass. Mark a row only after performing the check in a real browser.

Routes to inspect:

- [ ] /app/
- [ ] /app/vault-setup
- [ ] /app/notes
- [ ] /app/graph
- [ ] /app/import
- [ ] /app/bundles
- [ ] /app/exports
- [ ] /app/security
- [ ] /app/validation
- [ ] /app/tasks
- [ ] /app/raw
- [ ] /app/pending
- [ ] /app/trust
- [ ] /app/feedback
- [ ] /app/controller

Viewports to inspect (each route should be sampled at each width):

- [ ] 3440x1440 or ultrawide equivalent
- [ ] 2560x1440
- [ ] 1920x1080
- [ ] 1366x768
- [ ] narrow mobile/tablet width (around 480 to 768 px)

Per-route checks:

- [ ] no horizontal overflow on the page shell
- [ ] no cramped panel padding
- [ ] no excessive unused blank space
- [ ] internal scroll works on workspace pages (workbench rails and inspectors scroll, the page shell does not)
- [ ] light mode is readable
- [ ] dark mode remains readable
- [ ] tables and raw viewers stay bounded
- [ ] slide-over panels fit narrow screens
- [ ] destructive actions remain visually separated
- [ ] theme toggle persists after a full page reload (`cve-theme` localStorage key respected)

### C. Keyboard QA Checklist (Manual)

This pass is manual unless actually performed. The Phase 30F automated tests assert source-level shape only.

- [ ] Tab order reaches the sidebar/nav, the theme toggle, toolbar actions, form controls, tables, details blocks, and slide-over controls
- [ ] `:focus-visible` is visible in both light and dark themes on every interactive control
- [ ] Escape or an explicit close control closes slide-overs where supported, without trapping focus
- [ ] disabled destructive buttons are either skipped in the tab order or announced as disabled by the browser
- [ ] typed confirmations (`OVERWRITE`, `DELETE <vault>`, `ACCEPT`, `REJECT`) can be completed with the keyboard only

### D. Screen-reader QA Checklist (Manual)

Screen-reader QA is manual unless actually performed. Do not mark any row checked unless the check was actually carried out with a screen reader (for example NVDA, JAWS, VoiceOver, or Narrator). If the pass has not been performed, leave every row unchecked and record that fact in the release notes.

- [ ] App shell landmarks (`header`, `nav`, `main`, `aside`, `footer`) are announced
- [ ] page heading is meaningful for every `/app/*` route
- [ ] theme toggle has an accessible name and announces its current state
- [ ] every form control has an associated label
- [ ] status badges convey meaning through text or an icon, not colour alone
- [ ] slide-overs have an accessible name and an accessible close control
- [ ] dangerous actions explain their consequences before requiring typed confirmation

State explicitly: this checklist has not been performed automatically by Phase 30F or Phase 31A. The boxes above are intended to be ticked only by a human running an assistive technology.

### E. Release Artefact Hygiene

- [ ] no `dist/` directory committed
- [ ] no `ui/dist/` directory committed
- [ ] no runtime-generated artefacts committed (pending change snapshots, exported packages, security report dumps)
- [ ] no screenshots committed
- [ ] no local reports committed
- [ ] no temporary files committed (`.tmp`, `.bak`, editor swap files)
- [ ] `git status --short` shows a clean working tree once these directories are excluded

---

## Pre-release Verification

- [ ] `python mcp/test_verify.py` passes, all 1166 tests green (no skips, no failures) - up from 1152 after Phase 39 ROADMAP deep normalisation drift guards (historical totals: 1081, 1103, 1135, 1143, 1152)
- [ ] `python run.py validate` passes, all notes valid
- [ ] `python run.py security` passes, status is `pass` or `warning` only (no `fail`)
- [ ] `python run.py feedback` passes, exits 0, valid JSON
- [ ] `python run.py export --overwrite` passes, package written to `dist/`
- [ ] `cd ui; npm run build` passes (run if any UI files changed)
- [ ] `python run.py mcp-smoke` passes (Phase 39 deterministic MCP stdio connection test; does not verify the rendered web UI and does not exercise pending-change accept paths)
- [ ] Generated artefacts (`dist/`, `ui/dist/`) are not committed, confirm with `git status --short`
- [ ] README reflects current capabilities, route summary, and test count
- [ ] QUICKSTART is current
- [ ] API.md documents every route registered in `mcp/server/mcp_server.py`
- [ ] TESTING.md current test count and phase sections up to date
- [ ] ROADMAP.md active phase, status table, and Phase 25 entry correct
- [ ] ROADMAP.md Phase 26 entry reflects Phase 26A, Phase 26B, Phase 26C, Phase 26D, Phase 26E, and Phase 26F as complete, the Phase 26 status table row reads Complete, and other import sources still deferred
- [ ] UI changes require `cd ui; npm run build` before release; the command must complete with zero errors
- [ ] Generated artefacts under `ui/dist/` and `dist/` remain untracked and are absent from `git status --short`
- [ ] UI/UX phase docs (ROADMAP Phase 29 section, UI_UX_AUDIT.md, TESTING.md Phase 29 entries) must not claim Phase 27 (Registry and Reuse Layer) or Phase 28 (Optional Semantic Retrieval) are implemented

---

## UI Release-Readiness

The UI is not release-quality today. Phase 30A (consolidated in `UI_UX_AUDIT.md` sections 18 and 19) confirmed this and scheduled Phase 30B through Phase 30F to close the gap. Phase 30D1 is complete: `/app/validation`, `/app/tasks`, and `/app/raw` now mount real Svelte islands. Phase 30D2 is complete: `/app/notes` and `/app/graph` are now split-pane workspace redesigns. Phase 30D3 (Import, Bundles, Exports, Security) remains planned, as do Phase 30E and Phase 30F. Until all of Phase 30 is complete, the following items must all be checked before tagging a release that claims a release-quality UI:

- [ ] Dark mode and light mode both verified; every `--cve-*` semantic token has a value under both `data-theme="dark"` and `data-theme="light"`; `color-scheme: dark light` declared at the root
- [ ] No placeholder routes remain in primary workflow navigation; `/app/validation`, `/app/tasks`, and `/app/raw` mount real Svelte islands, not `PlaceholderPage.astro`
- [ ] Destructive actions visually separated and gated: vault delete moved off the onboarding page; Import Write physically separated from Preview; Export overwrite uses the destructive button variant with typed confirmation; Security scan defaults to a full-vault scan with sampling under an explicit Advanced scope disclosure; Pending accept and reject use the shared typed-confirmation primitive
- [ ] Raw JSON disclosures are available under the Developer route (`/app/raw`); workflow pages do not embed `Show raw JSON` blocks inline
- [ ] Keyboard pass: every interactive control is reachable; `:focus-visible` renders a tokenised, visible outline in both themes; no keyboard trap on slide-overs, dialogs, or workbench panes
- [ ] Screen-reader pass: landmarks (`header`, `nav`, `main`, `aside`) present; form fields associated with labels; status badges paired with text or an icon; icon-only buttons carry `aria-label`
- [ ] Responsive pass at ultrawide (3440+ px), 1440p, 1080p, 1366x768, and narrow (mobile / tablet) breakpoints; workflow pages use internal scroll, not whole-page scroll, on long lists or long detail bodies
- [ ] No raw Tailwind dark palette literals (`bg-zinc-*`, `text-zinc-*`, `border-zinc-*`, `bg-emerald-9*`, `bg-amber-9*`, `bg-rose-9*`, `bg-sky-9*`) remain on migrated pages
- [ ] Generated artefact hygiene unchanged: `ui/dist/` and `dist/` remain untracked and are absent from `git status --short`

---

## Phase 31B - Header Consistency Visual Check

Phase 31B normalises the `cve-toolbar` page header contract across all migrated /app routes. Source-level guardrails are tested automatically; the following manual visual check is required for each /app route before tagging a release that claims a consistent header system.

Manual visual check across all 15 /app routes (`/app/`, `/app/vault-setup`, `/app/notes`, `/app/graph`, `/app/import`, `/app/bundles`, `/app/exports`, `/app/security`, `/app/validation`, `/app/tasks`, `/app/raw`, `/app/pending`, `/app/trust`, `/app/feedback`, `/app/controller`):

- [ ] Page title typography is consistent across all 15 routes (size, weight, line height, colour)
- [ ] Status pill placement, when present, is adjacent to the title and aligned to the same baseline
- [ ] Vault selector size and position is consistent across routes that expose a vault selector
- [ ] Action group ordering follows: utility nav (Validation, Tasks, Raw) -> Refresh -> page-specific primary action
- [ ] Refresh actions render as buttons, never as links
- [ ] Toolbar wraps cleanly at 1366x768 and narrow tablet/mobile widths with no horizontal overflow
- [ ] Header consistency verified in both dark and light themes

---

## Phase 31C - Release Candidate Visual QA and Defect Triage

Phase 31C is the release-candidate visual QA and defect-triage pass. It is not feature work and introduces no backend route, API contract, schema, MCP, or runtime dependency changes; no UI redesign, no new write actions, no route removal, and no page consolidation. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain Deferred.

The automated agent that executed Phase 31C performed only automated source-level verification (`py mcp/test_verify.py`, `py run.py validate`, `py run.py security`, `py run.py feedback`, `py run.py export --overwrite`, `cd ui && npm run build`) plus a static source review of `ui/src/layouts/AppLayout.astro`, `ui/src/styles/global.css`, every `ui/src/pages/*.astro`, and every `ui/src/components/*.svelte`. The agent did not open a browser, did not perform live keyboard traversal, and did not run a screen reader. The static review found no new defects beyond what Phase 30F and Phase 31B already address, and no source fixes were applied.

The manual visual QA matrix (Section B), keyboard QA checklist (Section C), and screen-reader QA checklist (Section D) above remain manual. They must be performed by a human running a real browser and, where applicable, a real assistive technology before any release tag claims those passes. Phase 31C does not tick those rows.

---

## Documentation Consistency

- [ ] No obsolete active-phase references outside historical changelog sections
- [ ] No stale test counts in onboarding sections (Review in 5 minutes, capability summary)
- [ ] No stale "Expected Concepts not written to schema" wording in QUICKSTART
- [ ] API route table in README is a subset of, or matches, API.md

---

## Versioning

- [ ] Version tag chosen according to the current release line:
  - Patch/fix after `v1.0.0`: `v1.0.1`, `v1.0.2`, etc.
  - Non-breaking feature release after `v1.0.0`: `v1.1.0`, `v1.2.0`, etc.
  - Breaking API/schema/config change: `v2.0.0`.
  - Historical baseline tags may remain descriptive, for example `v0.6.0-deterministic-cdlc-baseline`.
- [ ] Release notes or CHANGELOG entry added for the tag.
- [ ] Breaking changes documented: API contracts, CLI flags, schema fields
- [ ] Licence reviewed (`LICENCE.md`)

---

## Security and Deployment Notes

- [ ] Private cloud mode disabled by default (`CVE_PRIVATE_CLOUD_ENABLED` unset)
- [ ] DEPLOYMENT.md unchanged unless deployment guidance changed
- [ ] No instruction in docs exposes an unauthenticated public API
- [ ] No example commits a real `CVE_AUTH_TOKEN`

---

## GitHub Release

- [ ] Clean working tree, `git status --short` shows no uncommitted changes
- [ ] Tag pushed, `git push origin <tag>`
- [ ] GitHub Release created at the tag
- [ ] Release notes include the verification summary (test count, commands run)
- [ ] Known limitations listed (no semantic retrieval, no registry, no autonomous note writing)
