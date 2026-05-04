# Context Vault Engine — Roadmap

This document describes the phased development plan for Context Vault Engine. Phases 0–6 are complete. Phases 7 and 8 are future work and are **not implemented**.

> **Historical diagnostic reports** (e.g. `Vault Report.md`, `Vault Delta Report.md`) were generated during development as diagnostic snapshots. They are not permanent truth. When they conflict with live code, live code wins.

---

## Completed Phases

### Phase 0 — Stabilise Correctness

**Status: Complete**

**Purpose:** Fix correctness issues before expanding the system.

**Completed:**
- Unknown query fields now return `INVALID_FILTER` error with zero results (both strict and non-strict mode).
- Malformed query operators reject safely.
- Note index reflects edits within a 2-second cooldown window. No server restart needed.
- Regression tests added for each fix.
- CLI and API behaviour verified to be intentionally aligned.

---

### Phase 1 — Expose Existing Capabilities

**Status: Complete**

**Purpose:** Route existing engine capabilities through the API.

**Completed:**
- `GET /validation` — schema validation result.
- `GET /tasks` — prioritised improvement tasks with full POSIX paths and writing constraints.
- `GET /notes` — all vault notes with metadata and full paths.
- `GET /quality` — content quality audit.
- `GET /missing` — missing concept detection.
- `POST /compare` — vault delta comparison.
- `GET /graph/{vault}` — vault relationship graph (path-param form).
- `GET /graph/{vault}/related` — notes related to a node via shared group hub.
- `GET /graph/{vault}/missing` — expected concepts missing near a node.
- All paths use vault-relative POSIX forward slashes.
- Graph routes registered in correct order to avoid path conflicts.

---

### Phase 2 — Context Bundle Generation

**Status: Complete**

**Purpose:** Make context bundles the first major CDLC artefact.

**Completed:**
- `core/shared/context_bundle.py` — deterministic bundle engine.
- `POST /context/bundle` — generate a context bundle via API.
- `py run.py bundle` — generate a context bundle via CLI (JSON to stdout).
- Bundle fields: `bundle_id` (deterministic SHA-256), `vault`, `filters`, `created_at`, `validation_status`, `notes`, `graph`, `budget`, `warnings`, `manifest`, `feedback`.
- `max_notes` caps the candidate pool first; `max_chars` stops adding once budget exhausted.
- `budget.truncated` is `true` only when notes were excluded by the character budget.
- Schema-invalid notes always excluded. `allow_partial=false` by default.
- Bundles are JSON responses — not written to disk at this layer (see Phase 4).

---

### Phase 3 — Feedback Loop

**Status: Complete**

**Purpose:** Add the Observe and Adapt layer.

**Completed:**
- `core/shared/feedback.py` — feedback parser, validator, weight calculator.
- `demo-vault/Vault Files/feedback.md` — feedback file (excluded from validation).
- `GET /feedback` — load and validate vault feedback entries via API.
- `py run.py feedback` — load and print feedback via CLI.
- `GET /tasks?include_feedback=true` — tasks with feedback-adjusted priorities.
- Bundle includes a `feedback` block with entries and warnings.
- Feedback signals: `unclear`, `incomplete`, `outdated`, `incorrect`, `agent_failed`, `needs_example`, `needs_constraints` (negative), `useful`, `agent_succeeded` (positive).
- Missing `feedback.md` is treated as empty (no error). Malformed YAML is an error.
- **Feedback never rewrites notes.** It only adjusts task priority scores.

---

### Phase 4 — Export and Packaging

**Status: Complete**

**Purpose:** Make context portable.

**Completed:**
- `core/shared/context_package.py` — export engine with atomic write and SHA-256 hashing.
- `POST /context/export` — export a context bundle as a portable package via API.
- `py run.py export` / `py run.py export --overwrite` — export via CLI.
- Package written to `dist/context-bundles/<bundle-id>/`.
- Package files: `context.json`, `context.md`, `manifest.json`, `validation.json`, `graph.json`, `feedback-summary.json`.
- `manifest.json` includes SHA-256 hashes of all other package files + metadata.
- `PACKAGE_EXISTS` error (HTTP 409) when package exists and `overwrite=false`.
- Atomic write: write to temp dir, rename to final dir, cleanup on failure.
- `dist/` directory is gitignored.

---

### Phase 5 — Context Security Checks

**Status: Complete**

**Purpose:** Add security controls for context before packaging or serving.

**Completed:**
- `core/shared/context_security.py` — deterministic rule-based scanner (~620 lines).
- `POST /context/security` — scan a context bundle via API.
- `py run.py security` / `py run.py security --fail-on-warning` — scan via CLI.
- `require_security_pass: true` on `POST /context/export` — abort export on `fail` status.
- Status levels: `pass` (no findings), `warning` (findings, none blocking), `fail` (blocking finding).
- Blocking rules: private key, API key patterns, bearer token, password pattern.
- Non-blocking rules: external links, suspicious code blocks, HTML/script blocks, prompt injection patterns.
- Scanner is regex-based. No LLM calls, no network calls, no cloud dependency.

---

## Current Phase

### Phase 6 — Documentation and Positioning

**Status: Complete**

**Purpose:** Bring documentation into alignment with the implemented system and CDLC direction.

**Deliverables:**
- [x] README.md — project overview, workflow, API table, non-goals, principles
- [x] QUICKSTART.md — end-to-end setup guide with troubleshooting
- [x] ARCHITECTURE.md — system layers, data flow, determinism principles
- [x] ROADMAP.md — this file
- [x] CONTEXT_BUNDLE_SPEC.md — context bundle specification
- [x] API.md — all routes with request/response shapes
- [x] TESTING.md — test categories and commands

---

## Future Phases

> The following phases are **not yet implemented**. Do not claim these features are available.

### Phase 7 — Optional Semantic Retrieval

**Status: Future — not implemented**

**Purpose:** Add semantic retrieval only after deterministic context bundles work.

**Potential additions:**
- Embedding index
- Semantic search endpoint
- Hybrid search (filter + embedding)
- Local embedding model support

**Rules:**
- Semantic retrieval must not bypass schema validation.
- Semantic results must include source paths.
- Deterministic filters should run before semantic ranking.
- Invalid notes must be excluded unless explicitly allowed.
- The system must work without embeddings.

---

### Phase 8 — Registry and Reuse Layer

**Status: Future — not implemented**

**Purpose:** Add reusable context package management after packages are stable.

**Potential additions:**
- Local context bundle registry
- Bundle versioning and tags
- Bundle dependency metadata
- Bundle compatibility checks
- Bundle signing or hashing
- Conflict detection between packages

**Rules:**
- Registry stores generated packages, not source notes.
- Registry can list, verify, and remove packages.
- Registry can detect stale packages.

---

## Testing Strategy

Every phase includes tests in `mcp/test_verify.py`. See [TESTING.md](TESTING.md) for categories and commands.

---

## Implementation Discipline

Before implementing any roadmap item:

1. Verify the current code against this roadmap.
2. Check whether older reports are still accurate.
3. Identify the smallest safe change.
4. Add or update tests.
5. Run tests.
6. Update docs if behaviour changes.

Do not implement from old reports blindly. Prefer small composable changes.
