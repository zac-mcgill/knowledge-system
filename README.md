# Context Vault Engine

Context Vault Engine is a local-first system for turning structured Markdown vaults into validated, queryable, packageable, and agent-consumable context. It treats context as an engineered artefact — validated against an explicit schema, analysed for quality and gaps, packaged as deterministic build artefacts, scanned for security issues, and improved through a feedback loop. This is not a generic AI-agent framework, a RAG wrapper, a replacement for Obsidian, or a cloud platform.

---

## What It Does

| Phase | Capability |
|-------|-----------|
| **Validate** | Checks every note against the vault schema (frontmatter, required fields, section presence, derived-field consistency). |
| **Analyse** | Runs structured analyses: completeness by domain, difficulty/completeness distribution, section deficiency heatmap, scored action list. |
| **Improve** | Scores partial notes by difficulty weight, missing section penalties, and domain priority. Outputs ranked upgrade tasks with per-note writing constraints. |
| **Bundle** | Generates a deterministic context bundle — a JSON package of selected notes with metadata, section extracts, validation state, graph relationships, and budget information. |
| **Export** | Writes a portable context package to ``dist/context-bundles/<bundle-id>/`` with SHA-256 hashes, a manifest, and a Markdown rendering. |
| **Security** | Scans a context bundle for secrets, prompt injection patterns, suspicious code blocks, and external links using deterministic regex rules. |
| **Feedback** | Parses vault feedback entries and adjusts task priorities when requested. Does not rewrite notes. |
| **API** | Serves all of the above through a FastAPI HTTP interface for programmatic and agent use. |

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
```

On Windows, use ``py run.py ...``. On macOS/Linux, use ``python3 run.py ...``.

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
| ``manifest.json`` | SHA-256 hashes + metadata |
| ``validation.json`` | Validation status and warnings |
| ``graph.json`` | Graph relationships for selected notes |
| ``feedback-summary.json`` | Feedback entries relevant to selected notes |

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
