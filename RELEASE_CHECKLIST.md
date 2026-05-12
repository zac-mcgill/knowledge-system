# Release Checklist

Use this checklist before tagging a release. All steps are local and deterministic.

---

## Pre-release Verification

- [ ] `python mcp/test_verify.py` passes, all 625 tests green (no skips, no failures)
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
- [ ] ROADMAP.md Phase 26 entry reflects Phase 26A, Phase 26B, and Phase 26C as complete, with other import sources still deferred

---

## Documentation Consistency

- [ ] No obsolete active-phase references outside historical changelog sections
- [ ] No stale test counts in onboarding sections (Review in 5 minutes, capability summary)
- [ ] No stale "Expected Concepts not written to schema" wording in QUICKSTART
- [ ] API route table in README is a subset of, or matches, API.md

---

## Versioning

- [ ] Version tag chosen (e.g. `v0.25.0`)
- [ ] Changelog or release notes drafted
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
