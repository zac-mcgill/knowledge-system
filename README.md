# Knowledge System


## What This Is

A schema-driven markdown knowledge base with deterministic validation, analysis, and improvement tooling. Every note in the vault carries structured YAML frontmatter governed by a single authoritative schema (`vault_schema.py`). Python scripts enforce that schema, analyse completeness, and generate prioritised upgrade tasks — all without manual judgement calls.

Supports user-defined domains via a `bootstrap` command that generates a complete schema and templates for any domain. The system is domain-agnostic — all validation, analysis, and reporting behaviour is derived from the active `vault_schema.py`, not hardcoded assumptions.

This is not Obsidian-specific tooling. It operates on plain markdown files with YAML frontmatter. Any editor or vault structure that follows the schema conventions will work.

## System Guarantees

These properties are enforced at runtime and have been verified through fault injection testing:

- **YAML frontmatter is mandatory.** Every note must begin with a valid `---`-delimited YAML block. A note without frontmatter fails validation immediately.
- **Missing or malformed YAML causes explicit failure.** The system uses strict YAML parsing. Syntax errors are reported with the exact parse reason, not silently swallowed.
- **Validation cannot be bypassed.** There is no fallback, no default, and no soft-fail path. A file either passes fully or is rejected with a specific error.
- **Invalid files are always surfaced.** Files that fail validation are excluded from analysis and reporting, but are always identified with explicit warnings. The system never silently drops invalid data.
- **Report insights are derived strictly from computed data.** No narrative is hardcoded. Every statement in the generated report is produced from the actual metadata of the vault being analysed.
- **CLI adapts to the environment.** The `run.py` entry point automatically detects the correct Python executable (`py` on Windows, `python3` elsewhere). All printed instructions reflect the actual runtime command.
- **No hardcoded domain or section assumptions.** All behaviour is schema-driven. Canonical sections, required fields, and tracked section names are read from the active `vault_schema.py` at runtime.

## What It Does

- **Validation** — Checks every note against the schema using strict YAML parsing. Fails on: missing YAML frontmatter, malformed YAML, missing required fields, enum violations, and structural section gaps. Reports pass/fail per file with the specific error. Invalid files are never silently ignored — they either fail validation or are surfaced with explicit warnings in downstream commands. Validation is schema-driven and domain-agnostic — all rules are derived from the active `vault_schema.py`, including canonical sections and required fields.
- **Analysis** — Produces seven structured analyses from metadata: completeness by domain, subdomain weak points, difficulty vs completeness, critical gaps (advanced + partial), section deficiency heatmap, structural balance, and a scored action list. Files that fail validation are excluded but always reported with explicit warnings. All analyses dynamically adapt to the schema — section deficiency heatmaps and task scoring operate on the schema's defined sections, not fixed assumptions.
- **Improvement** — Scores all partial notes by difficulty weight, missing section penalties, and domain priority. Outputs ranked upgrade tasks with per-note writing instructions and quality constraints.
- **Reporting** — Generates a markdown report with executive summary, domain analysis, key insights, critical gaps, section deficiencies, and priority actions. Written to the vault's `Vault Files/` directory. All insights are derived from computed data — no hardcoded narrative.
- **Template generation** — Derives canonical note templates directly from the schema (no manual templates). Templates are generated from the active schema, including schemas created via bootstrap. No assumptions about section names are hardcoded.
- **API (decision layer)** — Exposes validation status, prioritised tasks, gaps, and structured note metadata for programmatic and agent use.

The system is designed to integrate with external content generation workflows, including LLM-assisted pipelines, while remaining fully deterministic in evaluation.

## How It Works

All four commands are routed through `run.py`, which reads `config/config.yaml` for the vault root path, resolves the vault's schema, and dispatches to the appropriate module.

```
validate → analyse → improve → report
```

1. **validate** reads every markdown file, parses YAML frontmatter, and checks it against `vault_schema.py`. Fields are verified for presence, valid enum values, and consistency with values derived from the file's path and name. Section-boolean fields (`has_key_principles`, `has_how_it_works`, `has_tradeoffs`) are checked against actual heading content. Returns exit code 0 if all files pass, 1 otherwise.

2. **analyse** loads all metadata and runs seven analyses. Each analysis prints a fixed-width table to stdout with computed statistics — completion rates, distribution metrics, gap counts, and a scored priority list. No files are modified.

3. **improve** loads metadata and note bodies, inspects section quality (e.g. minimum 3 numbered steps in How It Works, minimum 3 data rows in Trade-offs table), scores each partial note, and outputs a ranked task list with specific writing constraints per issue type. No files are modified.

4. **report** assembles the analysis into a single markdown file (`Vault Report.md`) written to the vault's `Vault Files/` directory. The report includes all major metrics and is suitable for portfolio presentation.

The schema (`vault_schema.py`) lives inside the vault itself at `Vault Files/Scripts/vault_schema.py` and defines all enums, field lists, section maps, and derivation logic. It is the single source of truth — no other file duplicates these definitions.


## Bootstrap (Custom Domains)

The system supports user-defined domains via:

```bash
py run.py bootstrap
```

This interactive command:

- creates a new vault
- generates a complete `vault_schema.py` for the specified domain and note type
- generates matching canonical templates
- configures the system automatically

After bootstrap, the system behaves identically to the demo vault:

```text
validate → analyse → improve → report
```

All validation remains strict. Bootstrap only defines the schema — it does not relax enforcement.

**Current limitation:** the bootstrap command supports one note type per vault. Multi-type schemas may be added in future iterations.


## Template System

Templates are not manually authored.

They are generated directly from `vault_schema.py`, which is the single source of truth for:

- note structure
- required sections
- validation rules

Generate templates with:

```bash
py run.py templates
```

This ensures all templates remain consistent with the schema.

Manual template editing is not supported.


## API (Decision Layer)

The system includes an HTTP API (MCP-based) that exposes structured, deterministic knowledge signals.

This is not raw note access — it provides:

- validation status
- prioritised improvement tasks with writing constraints
- gaps and coverage signals
- structured note metadata with full vault-relative paths
- relationship graph (deterministic, schema-driven)

### Endpoints

All adapter endpoints accept an optional `vault` query parameter. If omitted, the first registered vault is used.

| Endpoint | Description |
|--------|--------|
| `GET /vaults` | List registered vault names |
| `GET /summary` | Overall vault state |
| `GET /validation[?vault=]` | Schema validation result |
| `GET /tasks[?vault=&limit=&min_priority=]` | Prioritised improvement tasks with constraints |
| `GET /gaps` | High-impact incomplete notes |
| `GET /notes[?vault=]` | Structured note metadata with full paths |
| `GET /quality[?vault=]` | Content quality audit |
| `GET /missing[?vault=]` | Missing concept coverage gaps |
| `POST /compare` | Delta comparison between two vault snapshots |
| `GET /graph[?vault=]` | Full vault relationship graph |
| `GET /graph/{vault}` | Vault relationship graph (path-param form) |
| `GET /graph/{vault}/related?node_id=` | Notes related to a given node via shared group hub |
| `GET /graph/{vault}/missing?node_id=` | Expected concepts missing near a given node |
| `GET /graph/related?node=&vault=` | Related nodes (query-param form) |
| `GET /graph/missing?node=&vault=` | Missing neighbors (query-param form) |
| `POST /query` | Filtered note query |
| `GET /note?vault=&path=` | Single note by path |
| `GET /stats?vault=&field=` | Field-value frequency aggregation |
| `POST /context/bundle` | Generate a deterministic context bundle |
| `POST /context/export` | Export a context bundle as a portable package to disk |
| `GET /feedback[?vault=]` | Load and validate vault feedback entries |
| `GET /health` | Server health and metrics |
| `GET /contract` | System contract check |

### Context Bundles (Phase 2)

`POST /context/bundle` generates a deterministic package of selected notes for use in external workflows and LLM pipelines.

**Minimal request:**
```json
POST /context/bundle
{
  "vault": "demo-vault"
}
```

**Full request:**
```json
POST /context/bundle
{
  "vault": "demo-vault",
  "filters": {"domain": "fundamentals", "status": "complete"},
  "include_sections": ["Key Principles", "How It Works", "Trade-offs"],
  "include_related": true,
  "include_body": true,
  "max_notes": 10,
  "max_chars": 20000,
  "allow_partial": false
}
```

**Response shape:**
```json
{
  "status": "ok",
  "bundle_id": "a1b2c3d4e5f6a7b8",
  "vault": "demo-vault",
  "filters": {},
  "created_at": "2026-05-04T12:00:00+00:00",
  "validation_status": "pass",
  "notes": [
    {
      "path": "Fundamentals/Algorithms.md",
      "fields": {},
      "sections": {"Key Principles": "..."},
      "body": "..."
    }
  ],
  "graph": {"related": {}},
  "budget": {"max_chars": 20000, "used_chars": 8500, "note_count": 5, "truncated": false},
  "warnings": [],
  "manifest": {"source_paths": ["Fundamentals/Algorithms.md"], "schema_version": null}
}
```

**Defaults:** `include_sections=["Key Principles","How It Works","Trade-offs"]`, `include_body=true`, `max_notes=10`, `max_chars=20000`, `allow_partial=false`.

`max_notes` caps the candidate pool first; `max_chars` then stops adding notes once the character budget is exhausted. `budget.truncated` is `true` only when notes were excluded by the character budget (not by `max_notes`). A `warnings` entry names the first note excluded by budget.

**Note:** `run.py bundle` and `POST /context/bundle` print the bundle as JSON to stdout only. To write the bundle to disk as a portable package, use `run.py export` or `POST /context/export` (see [Export and Packaging](#export-and-packaging-phase-4) below).

**CLI equivalent:**
```bash
py run.py bundle
```

Prints a default bundle as JSON to stdout. Uses `status=complete` notes if any exist; falls back to partial notes with a warning.

### Export and Packaging (Phase 4)

Context bundles can be exported to disk as portable packages using `POST /context/export` or `py run.py export`.

**Package directory:** `dist/context-bundles/<bundle-id>/`

**Package files:**

| File | Purpose |
|------|---------|
| `context.json` | Full bundle JSON |
| `context.md` | Human-readable Markdown rendering of selected notes |
| `manifest.json` | Package manifest with SHA-256 hashes for all other files |
| `validation.json` | Validation status and warnings |
| `graph.json` | Graph relationships for selected notes |
| `feedback-summary.json` | Feedback entries relevant to selected notes |

**CLI:**
```bash
py run.py export
```
Exports the default bundle (same defaults as `bundle`) to `dist/context-bundles/<bundle-id>/`. Prints structured JSON to stdout. Returns exit code 1 if the package already exists.

```bash
py run.py export --overwrite
```
Replaces an existing package for the same bundle ID.

**API (minimal request):**
```json
POST /context/export
{
  "vault": "demo-vault"
}
```

**API (full request):**
```json
POST /context/export
{
  "vault": "demo-vault",
  "filters": {"status": "complete"},
  "include_sections": ["Key Principles", "How It Works", "Trade-offs"],
  "include_related": false,
  "include_body": true,
  "max_notes": 10,
  "max_chars": 20000,
  "allow_partial": false,
  "overwrite": false
}
```

**Response shape:**
```json
{
  "status": "ok",
  "bundle_id": "a1b2c3d4e5f6a7b8",
  "package_dir": "dist/context-bundles/a1b2c3d4e5f6a7b8",
  "files": {
    "context.json":          {"sha256": "...", "bytes": 1234},
    "context.md":            {"sha256": "...", "bytes": 1234},
    "manifest.json":         {"sha256": "...", "bytes": 1234},
    "validation.json":       {"sha256": "...", "bytes": 1234},
    "graph.json":            {"sha256": "...", "bytes": 1234},
    "feedback-summary.json": {"sha256": "...", "bytes": 1234}
  },
  "warnings": []
}
```

**manifest.json shape:**
```json
{
  "bundle_id": "a1b2c3d4e5f6a7b8",
  "vault": "demo-vault",
  "schema_version": null,
  "created_at": "2026-05-04T12:00:00+00:00",
  "source_notes": ["Fundamentals/Algorithms.md"],
  "validation_status": "pass",
  "warnings": [],
  "files": {
    "context.json": {"sha256": "...", "bytes": 1234},
    "context.md":   {"sha256": "...", "bytes": 1234},
    "...": "..."
  }
}
```

The manifest hashes cover all five non-manifest files. `manifest.json` does not include its own hash (circular dependency). The return value from the API and CLI does include the manifest hash.

**Overwrite behaviour:**
- `overwrite=false` (default): Returns `PACKAGE_EXISTS` error (HTTP 409) if a package with the same bundle ID already exists.
- `overwrite=true`: Removes the existing package directory and replaces it atomically.

**Generated packages are build artefacts.** The `dist/` directory is ignored by git. Do not commit generated packages.

### Feedback Loop (Phase 3)

The feedback loop is a signal-collection layer that captures human or agent observations about specific notes and feeds them into the task priority engine. It does not modify notes — it only adjusts which notes the system recommends working on next.

#### feedback.md

Feedback is stored in `Vault Files/feedback.md` inside the vault. This file is excluded from note discovery, validation, graph nodes, and context bundles — it is treated as a vault metadata file, not a knowledge note.

**Schema:**
```yaml
feedback:
  - path: Fundamentals/Algorithms.md   # vault-relative POSIX path
    source: human                      # human | agent | system
    signal: unclear                    # see valid signals below
    severity: medium                   # low | medium | high | critical
    comment: "Optional free-text note."
    created_at: "2026-05-04T12:00:00Z"
```

**Valid signals:**
- Negative (increase priority): `unclear`, `incomplete`, `outdated`, `incorrect`, `agent_failed`, `needs_example`, `needs_constraints`
- Positive (decrease priority): `useful`, `agent_succeeded`

**Severity multipliers:** `low` × 0.5, `medium` × 1.0, `high` × 1.5, `critical` × 2.0

**Validation behaviour:**
- Missing `feedback.md` → `status: ok`, empty entries (not an error)
- Malformed YAML → `status: error`, `MALFORMED_YAML`
- Unknown `source` / `signal` / `severity` → entry excluded, `status: error`
- Path references a non-existent note → entry kept, warning added

#### Task priority weighting

When `include_feedback=true`, each task's priority is adjusted by the sum of `signal_delta × severity_multiplier` across all feedback entries for that note. Tasks are re-sorted after adjustment. The base task cache is never modified — feedback is applied on top at query time.

```text
GET /tasks?vault=demo-vault&include_feedback=true
```

Each task in the response gains a `feedback_weight` field:
```json
{
  "feedback_weight": {
    "score_delta": 0.75,
    "entry_count": 2,
    "summary": ["unclear/medium (+0.50)", "needs_example/low (+0.25)"]
  }
}
```

The response also includes `feedback_status` (`ok` or `error`) and `feedback_errors` (list of structured errors from loading feedback.md).

#### GET /feedback

Returns the raw parsed feedback for a vault:

```text
GET /feedback?vault=demo-vault
```

Response:
```json
{
  "status": "ok",
  "vault": "demo-vault",
  "entries": [...],
  "warnings": [...],
  "errors": [...]
}
```

Returns HTTP 404 with `INVALID_VAULT` for unknown vaults. Returns HTTP 200 with `status: error` for malformed feedback.md.

#### CLI

```bash
py run.py feedback
```

Prints parsed feedback as JSON to stdout. Exits 0 if `status: ok`, exits 1 if `status: error`.

#### Context bundle feedback

`POST /context/bundle` includes a `feedback` key in the response. Entries are filtered to only those referencing notes selected for the bundle:

```json
{
  "feedback": {
    "entries": [...],
    "warnings": [...]
  }
}
```

### Task Output

`GET /tasks` returns normalised task objects. Each task includes:

- `note` — stem name of the note
- `path` — full vault-relative POSIX path (e.g. `Fundamentals/Algorithms.md`)
- `priority` — computed priority score
- `missing` — list of missing section names
- `instruction` — human-readable action string
- `constraints` — writing constraints for the primary issue (from the task engine)

### Example

```text
GET /tasks?vault=demo-vault&limit=5
```

Returns the top 5 prioritised upgrade tasks with full paths and writing constraints.

```text
GET /graph/demo-vault/related?node_id=note::Fundamentals/Algorithms.md
```

Returns notes related to Algorithms via shared domain/subdomain/topic hubs.

### Agent Loop

This enables closed-loop automation:

1. GET `/tasks`
2. Select highest priority task — use `path` for the full file location, `constraints` for writing rules
3. Generate or update content
4. GET `/validation`
5. Repeat

The system enforces structure; generation is external.


## Example Workflow

```bash
# Initialise
py run.py init my-vault

# Generate templates (recommended)
py run.py templates

# CLI pipeline
py run.py validate
py run.py analyse
py run.py improve
py run.py report

# API (optional)
py mcp/server/mcp_server.py
```

## Example: Validation Failure

A note with missing YAML frontmatter produces:

```text
Fundamentals/Recursion.md
  - Missing or invalid YAML frontmatter
```

A note with malformed YAML produces:

```text
Fundamentals/Recursion.md
  - Malformed YAML: could not find expected ':'
```

Validation exits with code 1 and no valid file is reported as failing.

## Repository Structure

```
knowledge-system/
├── run.py                          # CLI entry point — routes commands to modules
├── config/
│   └── config.yaml                 # vault_root path configuration
├── core/
│   ├── __init__.py
│   ├── drift_check.py              # Schema drift detection
│   ├── generate_templates.py       # Template generation
│   ├── Vault Improvement Cycle.md  # Process documentation
│   └── shared/
│       ├── __init__.py             # Schema loader (resolves vault_schema.py)
│       ├── analyse_vault.py        # 7-analysis engine
│       ├── compare_reports.py      # Report comparison
│       ├── context_bundle.py       # Deterministic context bundle generation
│       ├── context_package.py      # Context package export (Phase 4)
│       ├── discover_missing.py     # Missing note discovery
│       ├── feedback.py             # Feedback parser, validator, and weight calculator
│       ├── generate_report.py      # Markdown report generator
│       ├── inject_frontmatter.py   # YAML frontmatter injection
│       ├── quality_audit.py        # Quality audit checks
│       ├── query_vault.py          # Vault querying
│       ├── upgrade_vault.py        # Scored upgrade task engine
│       └── validate_vault.py       # Schema validation engine
├── demo-vault/
│   ├── Fundamentals/               # 19 core-concept notes
│   └── Vault Files/
│       ├── feedback.md             # Feedback entries (excluded from note discovery)
│       ├── Vault Report.md         # Generated report output
│       └── Scripts/
│           └── vault_schema.py     # Single source of truth for schema
├── mcp/                            # API server (MCP-based), reads config/config.yaml
│   ├── core/
│   │   ├── adapters/
│   │   │   ├── validation_adapter.py
│   │   │   ├── tasks_adapter.py
│   │   │   └── notes_adapter.py
│   │   ├── contract_runner.py
│   │   ├── note_index.py
│   │   ├── query_engine.py
│   │   ├── schema_loader.py
│   │   ├── system_contract.py
│   │   └── vault_registry.py
│   ├── server/
│   │   └── mcp_server.py
│   ├── contract_check.py
│   ├── requirements.txt
│   └── test_verify.py
```


## Creating a New Vault

Use the built-in initialisation command:

```bash
py run.py init my-vault
```

This command:

* copies the demo vault structure
* ensures a valid schema is present
* removes generated artefacts
* updates `config/config.yaml`

After initialisation, the system is immediately ready:

```bash
py run.py validate
```

### Requirements

All vaults must follow:

```
<Vault>/
  Vault Files/
    Scripts/
      vault_schema.py
```

The schema defines all rules and is required for system operation.
* This system is editor-agnostic. The included vault can be opened in Obsidian for editing, but validation and analysis are performed via the CLI.

## Key Concepts

### Schema enforcement

Every note must conform to `vault_schema.py`. This file defines valid types, domains, subdomains, topics, statuses, difficulties, required fields per note type, and canonical section headings. Fields like `domain` and `type` are not free-text — they are derived deterministically from the file's path and name, then validated against the schema's enum sets.

### Deterministic execution

All derivation and validation logic is pure. Given the same vault state, every command produces the same output. There is no randomness, no LLM inference in the pipeline, and no configuration beyond `config.yaml`. Scoring in the upgrade engine uses fixed weights: advanced difficulty = +3, intermediate = +1, missing Trade-offs = +3, missing How It Works = +2, missing Key Principles = +1, multiplied by domain priority weight.

### Improvement cycle

The system implements a closed-loop improvement cycle: **validate** confirms structural integrity, **analyse** identifies where gaps exist, **improve** produces specific writing tasks ranked by impact, and **report** captures the current state. After manually addressing the highest-priority tasks, rerunning the pipeline surfaces the next set of targets.

## MCP Integration

The MCP server provides a read-only HTTP API over the active vault. It is optional and requires no configuration beyond what `run.py init` already sets up.

### How It Works

The MCP server reads `config/config.yaml` — the same file used by the CLI pipeline. Whichever vault is configured as `vault_root` is automatically loaded, indexed, and served. After running `py run.py init my-vault`, the MCP server will serve `my-vault` with no additional steps.

### Usage

Install the MCP dependencies (in addition to PyYAML):

```bash
pip install fastapi uvicorn
```

Start the server:

```bash
py mcp/server/mcp_server.py
```

The server runs on `http://127.0.0.1:8000`.

### Endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/health` | GET | Server status and metrics |
| `/validation` | GET | Schema validation result |
| `/tasks` | GET | Ranked improvement tasks |
| `/tasks?limit=N` | GET | Top N tasks |
| `/tasks?min_priority=N` | GET | Filter tasks by priority threshold |
| `/notes` | GET | Structured note metadata |
| `/summary` | GET | Coverage and completeness overview |
| `/gaps` | GET | High-impact incomplete notes |
| `/vaults` | GET | List the active vault |
| `/query` | POST | Query notes with filters |
| `/note` | GET | Retrieve a single note |
| `/stats` | GET | Aggregate a field across the vault |
| `/contract` | GET | Run system contract checks |

### Key Properties

- **Zero config** — reads `config/config.yaml` automatically, no manual edits required.
- **Single active vault** — serves whichever vault the CLI is configured to use.
- **Read-only** — no vault data is modified through the API.
- **Init compatible** — after `py run.py init <name>`, the server immediately serves the new vault.
- **Schema-aware** — validates notes against `vault_schema.py` at startup and periodically.
- **Fail-closed query filters** — `POST /query` validates all filter fields and operators before executing. Unknown fields, unsupported operators (e.g. `__gt`), and malformed `__in` values (non-list) return a structured `INVALID_FILTER` error with zero results rather than silently returning all notes. Supported operators: equality (no suffix), `__in` (list value), `__contains` (substring).
- **Live index freshness** — the note index detects changes to any indexed `.md` file (additions, edits, deletions) as well as schema changes. After a short cooldown window (2 s), the next `POST /query` or `GET /note` request automatically rebuilds the index to reflect current note state. No server restart is required after editing notes.


## Agent Workflow Example

The API supports closed-loop automation with external agents:

1. `GET /tasks` — fetch prioritised upgrade tasks
2. Select the highest priority task
3. Generate or update the note content (external)
4. `GET /validation` — confirm schema compliance
5. Repeat

Use `GET /summary` for coverage tracking and `GET /gaps` to target high-impact incomplete notes.

See [examples/agent_loop.md](examples/agent_loop.md) for full details.


## Limitations

- **Single demo vault** — ships with one vault (`demo-vault/`) containing 19 notes in a single domain. The tooling supports multi-domain vaults but the demo does not exercise this.
- **Content generation model** — the system does not generate content itself. It produces constraints, validation, and prioritised tasks. Content can be authored manually or generated via external tools.
- **No watch mode** — the pipeline runs on demand. There is no file-watching or automatic re-validation.
- **Python dependency** — requires Python 3.10+ and PyYAML. On Windows, the `py` launcher is recommended. On macOS/Linux, use `python3` if `python` is not available.
