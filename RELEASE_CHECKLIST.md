# Release Checklist

Use this checklist before tagging a release. All steps are local and deterministic.

---

## Pre-release Verification

- [ ] `python mcp/test_verify.py` passes — all 272 tests green
- [ ] `python run.py validate` passes — all notes valid
- [ ] `python run.py security` passes — status `pass` or `warning` only (no `fail`)
- [ ] `python run.py feedback` passes — exits 0, valid JSON
- [ ] `python run.py export --overwrite` passes — package written to `dist/`
- [ ] `cd ui && npm run build` passes — if UI changes were made
- [ ] Generated artefacts (`dist/`, `ui/dist/`) are **not** committed — confirm with `git status --short`
- [ ] README reflects current capabilities and test count
- [ ] QUICKSTART is current
- [ ] API.md is current — if any API routes changed
- [ ] TESTING.md is current — test count and phase sections up to date
- [ ] ROADMAP.md is current — active phase and status table correct

---

## Versioning

- [ ] Version tag chosen (e.g. `v0.18.0`)
- [ ] Changelog or release notes drafted
- [ ] Breaking changes documented — API contracts, CLI flags, schema fields
- [ ] Licence reviewed

---

## GitHub Release

- [ ] Clean working tree — `git status --short` shows no uncommitted changes
- [ ] Tag pushed — `git push origin <tag>`
- [ ] GitHub release created at the tag
- [ ] Release notes include a verification summary (test count, commands run)
- [ ] Known limitations listed
