# Context Vault Engine

[![Verify](https://github.com/zac-mcgill/context-vault-engine/actions/workflows/verify.yml/badge.svg)](https://github.com/zac-mcgill/context-vault-engine/actions/workflows/verify.yml)

Context Vault Engine is a local-first Python pipeline for validating, scanning, and securely packaging structured Markdown content. It enforces a schema contract on every note, scans content for credential leaks, prompt-injection patterns, and suspicious executable/script blocks, then exports integrity-verified packages with SHA-256 manifests. All security rules are deterministic and regex-based, so every finding is explainable, reproducible, and auditable without an LLM or cloud dependency.

**Local-first Python pipeline: credential leak scanning, prompt-injection detection, schema enforcement, rate-limited API, path-traversal blocking, SHA-256 artefact integrity, MCP stdio compatibility layer, private cloud mode. 396 tests.**

---

## Capabilities

- Schema validation on every note — required fields, section presence, derived-field consistency
- Credential leak detection: private keys, AWS/GitHub/Slack token patterns, bearer tokens, password assignments
- Prompt-injection pattern detection
- Suspicious HTML, script-tag, and executable-code-block detection
- Path-traversal rejection on all file-path inputs
- Rate-limited FastAPI API (50 req/s, structured `RATE_LIMIT` error responses)
- SHA-256 manifest on every exported package
- Optional export security gate: `require_security_pass: true` aborts export on `fail`-severity findings
- Relationship graph, quality audit, missing-concept detection
- MCP stdio compatibility for read-only vault inspection and deterministic context planning
- Private Cloud Mode: token-authenticated, read-only remote API access — self-hosted, no cloud accounts required
- 396 deterministic tests

---

## Why this matters

Most content pipelines either trust their input or delegate scanning to an external service. Context Vault Engine validates, scans, and gates export at the pipeline level — deterministically, without network calls, and with structured JSON output that can be reviewed or piped into other tools. Every finding references the specific note and field that triggered it, and every exported package carries a SHA-256 hash for integrity verification.

---

## Review in 5 minutes

```bash
# Schema compliance — validates all notes against the schema contract
python run.py validate

# Security scan — checks for credential leaks, injection patterns, suspicious code
python run.py security

# Export — writes integrity-verified package to dist/ with SHA-256 manifest
python run.py export --overwrite

# Full test suite — 382 tests covering all pipeline stages
python mcp/test_verify.py
```

Each command exits `0` on success, `1` on failure, and writes structured JSON output where applicable.

---

## Security Controls Demonstrated

| Control | Implementation |
|---------|---------------|
| Credential leak scanning | Regex patterns for: PEM private key blocks, AWS `AKIA` keys, GitHub `ghp_` tokens, Slack `xox` tokens, bearer tokens, password assignments |
| Prompt-injection detection | Matches instruction-override phrases and tool-misuse patterns in note content |
| Suspicious content detection | Flags `<script>` tags, executable code blocks, and inline executable references |
| Path-traversal rejection | User-supplied file paths validated against vault root; `..` sequences rejected with structured error |
| Rate limiting | 50 requests/second enforced in API middleware; excess returns `{"code": "RATE_LIMIT", ...}` |
| Structured error responses | All error paths return machine-readable JSON with a `code` field |
| SHA-256 artefact integrity | `manifest.json` in every exported package contains SHA-256 hashes of all package files |
| Export security gate | `require_security_pass: true` aborts package write when `fail`-severity findings exist |

> **Scope:** This is a rule-based static scanner demonstrating common detection patterns. It is not a full DLP system, production-grade secret scanner, or malware analyser. Treat findings as review signals.

---

## What It Does

| Phase | Capability |
|-------|-----------|
| **Validate** | Checks every note against the vault schema (frontmatter, required fields, section presence, derived-field consistency). |
| **Analyse** | Runs structured analyses: completeness by domain, difficulty/completeness distribution, section deficiency heatmap, scored action list. |
| **Improve** | Scores partial notes by difficulty weight, missing section penalties, and domain priority. Outputs ranked upgrade tasks with per-note writing constraints. |
| **Bundle** | Generates a deterministic context bundle — a JSON package of selected notes with metadata, section extracts, validation state, graph relationships, and budget information. |
| **Export** | Writes a portable context package to ``dist/context-bundles/<bundle-id>/`` with SHA-256 hashes, a manifest, a Markdown rendering, and a static HTML rendering. |
| **Security** | Scans a context bundle for secrets, prompt injection patterns, suspicious code blocks, and external links using deterministic regex rules. |
| **Feedback** | Parses vault feedback entries and adjusts task priorities when requested. Does not rewrite notes. |
| **API** | Serves all of the above through a rate-limited FastAPI HTTP interface for programmatic use. |
| **MCP** | Exposes vault capabilities as JSON-RPC tools, resources, and prompts over stdio for use with MCP-compatible local clients. Read-only, deterministic. |
| **Private Cloud** | Optional token-authenticated read-only remote access mode. Self-hosted, no cloud dependencies. Mutating routes blocked by default in remote mode. See `DEPLOYMENT.md`. |

---

## Principles

- **Local-first.** No cloud dependency, no external services, no embeddings required.
- **Deterministic-first.** Given the same vault state and command, the system returns the same result. Every core operation is repeatable and explainable.
- **Markdown is the source of truth.** Notes are plain Markdown with YAML frontmatter. Generated artefacts (bundles, packages) are derived outputs, not editable sources.
- **Schema is the contract.** All validation, analysis, and template behaviour is derived from ``vault_schema.py``. No domain knowledge is hardcoded in the engine.
- **Context bundles are build artefacts.** They are generated from the vault on demand, carry their validation status, and are not the primary editing surface.
- **Feedback adjusts priority, not content.** Feedback signals raise or lower task scores. They do not automatically rewrite notes.

---

## Non-Goals

This project is not:

- A generic AI-agent framework
- A generic RAG application
- A replacement for Obsidian
- A fully autonomous content writer
- A cloud-first platform
- A database-heavy enterprise system
- A semantic search engine (no embeddings in current implementation)

---

## Quick Workflow

```
# Install
pip install -r requirements.txt

# Use the demo vault or initialise your own
py run.py init my-vault           # copy demo vault
py run.py bootstrap               # create a custom vault interactively

# Core pipeline
py run.py validate                # check all notes against schema
py run.py analyse                 # run structured analyses
py run.py improve                 # generate prioritised upgrade tasks

# Context lifecycle
py run.py bundle                  # generate a context bundle (JSON to stdout)
py run.py feedback                # load and print vault feedback
py run.py export                  # export bundle as portable package to dist/
py run.py export --overwrite      # replace existing package
py run.py security                # scan bundle for security issues
py run.py security --fail-on-warning  # exit 1 for warning results too

# MCP stdio server (Phase 20)
py run.py mcp                     # start MCP JSON-RPC stdio server

# Private Cloud Mode (Phase 21) — opt-in, local mode unchanged
# See DEPLOYMENT.md for full setup
CVE_PRIVATE_CLOUD_ENABLED=true CVE_AUTH_TOKEN=<token> py run.py app

# Local app launcher (Phase 17)
py run.py app                     # start server + open browser UI
```

On Windows, use ``py run.py ...``. On macOS/Linux, use ``python3 run.py ...``.

---

## Local Web UI (Phase 10)

A local browser UI is available alongside the CLI and API. The UI is built with **Astro + TypeScript + Tailwind CSS + Svelte** and served by the same FastAPI backend.

### Development

```bash
# 1. Start the backend (required)
py mcp/server/mcp_server.py

# 2. In a separate terminal — start the UI dev server
cd ui
npm install
npm run dev
# → http://localhost:4321/app
```

### Production (build once, served by FastAPI)

```bash
cd ui
npm install
npm run build
# Compiled output written to ui/dist/

# Serve via the existing FastAPI server
py mcp/server/mcp_server.py
# → http://127.0.0.1:8000/app
```

`GET /app` serves the compiled frontend. If `ui/dist` has not been built, it returns a structured `503 UI_NOT_BUILT` response with build instructions. No other API routes are affected.

### Local App Launcher (Phase 17)

One command opens the local app:

```bash
cd ui && npm install && npm run build && cd ..
py run.py app
# → opens http://127.0.0.1:8000/app in the default browser
```

`py run.py app` starts the FastAPI server if it is not already running, waits until it is reachable, then opens the browser. If a compatible server is already running, it reuses it. Press Ctrl+C to stop the server.

**Stack:** Astro 5, TypeScript, Tailwind CSS 4, Svelte 5 islands.  
**UI scope (Phase 10):** server health, vault list, vault selector, completion summary, validation status, security scan status, navigation shell for future pages.  
**CLI and API:** remain fully supported and unchanged.

---

## API Overview

Start the server:

```
pip install -r mcp/requirements.txt
py mcp/server/mcp_server.py
```

| Method | Path | Purpose |
|--------|------|---------|
| ``GET`` | ``/vaults`` | List registered vault names |
| ``GET`` | ``/health`` | Server health and request metrics |
| ``GET`` | ``/contract`` | System contract check |
| ``GET`` | ``/summary`` | Vault-level completion summary |
| ``POST`` | ``/query`` | Filtered note query |
| ``GET`` | ``/note`` | Single note by vault + path |
| ``GET`` | ``/stats`` | Field-value frequency aggregation |
| ``GET`` | ``/validation`` | Schema validation result |
| ``GET`` | ``/tasks`` | Prioritised improvement tasks |
| ``GET`` | ``/notes`` | All notes with metadata |
| ``GET`` | ``/quality`` | Content quality audit |
| ``GET`` | ``/missing`` | Missing concept detection |
| ``GET`` | ``/gaps`` | High-priority incomplete notes |
| ``GET`` | ``/feedback`` | Vault feedback entries |
| ``POST`` | ``/compare`` | Delta comparison between two vault states |
| ``GET`` | ``/graph`` | Full vault relationship graph |
| ``GET`` | ``/graph/neighbors`` | Nodes directly connected to a given node |
| ``GET`` | ``/graph/related`` | Notes related to a node (query-param form) |
| ``GET`` | ``/graph/missing`` | Missing concepts near a node (query-param form) |
| ``GET`` | ``/graph/{vault}`` | Graph by vault (path-param form) |
| ``GET`` | ``/graph/{vault}/related`` | Notes related to a given node |
| ``GET`` | ``/graph/{vault}/missing`` | Expected concepts missing near a node |
| ``POST`` | ``/context/bundle`` | Generate a context bundle |
| ``POST`` | ``/context/export`` | Export a context bundle as a package |
| ``POST`` | ``/context/security`` | Scan a context bundle for security issues |

See [API.md](API.md) for full route documentation with request/response shapes.

---

## Package Artefact

``py run.py export`` writes a portable package to ``dist/context-bundles/<bundle-id>/``:

| File | Purpose |
|------|---------|
| ``context.json`` | Full bundle JSON |
| ``context.md`` | Human-readable Markdown rendering |
| ``context.html`` | Deterministic static HTML rendering for human review |
| ``manifest.json`` | SHA-256 hashes + metadata |
| ``validation.json`` | Validation status and warnings |
| ``graph.json`` | Graph relationships for selected notes |
| ``feedback-summary.json`` | Feedback entries relevant to selected notes |

``context.html`` is a deterministic static rendering for human review; Markdown vault notes remain the source of truth.

The ``dist/`` directory is gitignored. Packages are build artefacts — regenerate them from the vault.

---

## Security Scanner

The security scanner (``run.py security``, ``POST /context/security``) uses deterministic regex rules to detect:

- Secrets: API keys, bearer tokens, private keys, password patterns
- Prompt injection: instruction-override phrases, tool misuse patterns
- Suspicious content: external links, executable code blocks, HTML/script blocks

**This is a rule-based static scanner, not a DLP system or malware analyser.** It will produce false positives on documentation that describes security concepts. Use findings as review signals, not blocking verdicts (unless ``fail``-severity findings are present).

Export gate: pass ``require_security_pass: true`` to ``POST /context/export`` to abort export when the bundle has a ``fail``-severity finding.

---

## Feedback

Feedback entries live in ``demo-vault/Vault Files/feedback.md``. Valid signals:

- **Negative** (raises task priority): ``unclear``, ``incomplete``, ``outdated``, ``incorrect``, ``agent_failed``, ``needs_example``, ``needs_constraints``
- **Positive** (lowers priority): ``useful``, ``agent_succeeded``

Use ``GET /tasks?include_feedback=true`` or review the ``feedback_weight`` field on tasks. Feedback **never** modifies notes.

---

## Further Reading

- [QUICKSTART.md](QUICKSTART.md) — end-to-end setup and workflow
- [ARCHITECTURE.md](ARCHITECTURE.md) — system layers and data flow
- [ROADMAP.md](ROADMAP.md) — completed and planned phases
- [CONTEXT_BUNDLE_SPEC.md](CONTEXT_BUNDLE_SPEC.md) — context bundle specification
- [API.md](API.md) — all API routes with examples
- [TESTING.md](TESTING.md) — how to run and interpret tests

---

## Forensic Reports

The ``demo-vault/Vault Files/`` directory may contain historical diagnostic reports generated during development (e.g. ``Vault Report.md``, ``Vault Delta Report.md``). These are **dated diagnostic snapshots**, not permanent truth. As the project evolves, they become less accurate. When they conflict with live code, live code wins.
