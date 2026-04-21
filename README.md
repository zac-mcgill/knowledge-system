# Knowledge System


## What This Is

A schema-driven markdown knowledge base with deterministic validation, analysis, and improvement tooling. Every note in the vault carries structured YAML frontmatter governed by a single authoritative schema (`vault_schema.py`). Python scripts enforce that schema, analyse completeness, and generate prioritised upgrade tasks — all without manual judgement calls.

Includes a built-in vault initialisation command for rapid setup.

This is not Obsidian-specific tooling. It operates on plain markdown files with YAML frontmatter. Any editor or vault structure that follows the schema conventions will work.

## System Guarantees

These properties are enforced at runtime and have been verified through fault injection testing:

- **YAML frontmatter is mandatory.** Every note must begin with a valid `---`-delimited YAML block. A note without frontmatter fails validation immediately.
- **Missing or malformed YAML causes explicit failure.** The system uses strict YAML parsing. Syntax errors are reported with the exact parse reason, not silently swallowed.
- **Validation cannot be bypassed.** There is no fallback, no default, and no soft-fail path. A file either passes fully or is rejected with a specific error.
- **Invalid files are always surfaced.** Files that fail validation are excluded from analysis and reporting, but are always identified with explicit warnings. The system never silently drops invalid data.
- **Report insights are derived strictly from computed data.** No narrative is hardcoded. Every statement in the generated report is produced from the actual metadata of the vault being analysed.
- **CLI adapts to the environment.** The `run.py` entry point automatically detects the correct Python executable (`py` on Windows, `python3` elsewhere). All printed instructions reflect the actual runtime command.

## What It Does

- **Validation** — Checks every note against the schema using strict YAML parsing. Fails on: missing YAML frontmatter, malformed YAML, missing required fields, enum violations, and structural section gaps. Reports pass/fail per file with the specific error. Invalid files are never silently ignored — they either fail validation or are surfaced with explicit warnings in downstream commands.
- **Analysis** — Produces seven structured analyses from metadata: completeness by domain, subdomain weak points, difficulty vs completeness, critical gaps (advanced + partial), section deficiency heatmap, structural balance, and a scored action list. Files that fail validation are excluded but always reported with explicit warnings.
- **Improvement** — Scores all partial notes by difficulty weight, missing section penalties, and domain priority. Outputs ranked upgrade tasks with per-note writing instructions and quality constraints.
- **Reporting** — Generates a markdown report with executive summary, domain analysis, key insights, critical gaps, section deficiencies, and priority actions. Written to the vault's `Vault Files/` directory. All insights are derived from computed data — no hardcoded narrative.
- **Template generation** — Derives canonical note templates directly from the schema (no manual templates).
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
- prioritised improvement tasks
- gaps and coverage signals
- structured note metadata

### Endpoints

| Endpoint | Description |
|--------|--------|
| `/summary` | Overall vault state |
| `/validation` | Schema validation result |
| `/tasks` | Prioritised improvement tasks |
| `/tasks?limit=5` | Top N tasks |
| `/tasks?limit=5&min_priority=2` | Filtered tasks |
| `/gaps` | High-impact incomplete notes |
| `/notes` | Structured note metadata |

### Example

```text
GET /tasks
```

Returns prioritised upgrade tasks suitable for automated workflows.

### Agent Loop

This enables closed-loop automation:

1. GET `/tasks`
2. Select highest priority
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
│       ├── discover_missing.py     # Missing note discovery
│       ├── generate_report.py      # Markdown report generator
│       ├── inject_frontmatter.py   # YAML frontmatter injection
│       ├── quality_audit.py        # Quality audit checks
│       ├── query_vault.py          # Vault querying
│       ├── upgrade_vault.py        # Scored upgrade task engine
│       └── validate_vault.py       # Schema validation engine
├── demo-vault/
│   ├── Fundamentals/               # 19 core-concept notes
│   └── Vault Files/
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
