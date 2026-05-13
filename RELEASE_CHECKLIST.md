# Release Checklist

Use this checklist before tagging a release. All steps are local and deterministic.

---

## Pre-release Verification

- [ ] `python mcp/test_verify.py` passes, all 985 tests green (no skips, no failures)
- [ ] `python run.py validate` passes, all notes valid
- [ ] `python run.py security` passes, status is `pass` or `warning` only (no `fail`)
- [ ] `python run.py feedback` passes, exits 0, valid JSON
- [ ] `python run.py export --overwrite` passes, package written to `dist/`
- [ ] `cd ui; npm run build` passes (run if any UI files changed)
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
