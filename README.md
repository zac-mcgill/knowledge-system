# Knowledge System


## What This Is

A schema-driven markdown knowledge base with deterministic validation, analysis, and improvement tooling. Every note in the vault carries structured YAML frontmatter governed by a single authoritative schema (`vault_schema.py`). Python scripts enforce that schema, analyse completeness, and generate prioritised upgrade tasks — all without manual judgement calls.

Includes a built-in vault initialisation command for rapid setup.

This is not Obsidian-specific tooling. It operates on plain markdown files with YAML frontmatter. Any editor or vault structure that follows the schema conventions will work.

## What It Does

- **Validation** — Checks every note against the schema: required fields, enum membership, type derivation from filename, domain derivation from path, and section-boolean consistency. Reports pass/fail per file.
- **Analysis** — Produces seven structured analyses from metadata: completeness by domain, subdomain weak points, difficulty vs completeness, critical gaps (advanced + partial), section deficiency heatmap, structural balance, and a scored action list.
- **Improvement** — Scores all partial notes by difficulty weight, missing section penalties, and domain priority. Outputs ranked upgrade tasks with per-note writing instructions and quality constraints.
- **Reporting** — Generates a markdown report with executive summary, domain analysis, key insights, critical gaps, section deficiencies, and priority actions. Written to the vault's `Vault Files/` directory.
- **API (MCP-based)** — Exposes structured knowledge signals (validation status, prioritised tasks, note metadata) for programmatic access and agent workflows.

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


## API (Brain Interface)

The system includes an HTTP API (MCP-based) that exposes structured, deterministic knowledge signals.

This is not raw note access — it provides:

- validation status
- prioritised improvement tasks
- structured note metadata

### Endpoints

| Endpoint | Description |
|--------|--------|
| `/health` | Server status |
| `/validation` | Schema validation result |
| `/tasks` | Ranked improvement tasks |
| `/tasks?limit=5` | Top N tasks |
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
python run.py init my-vault

# CLI pipeline
python run.py validate
python run.py analyse
python run.py improve
python run.py report

# API (optional)
python mcp/server/mcp_server.py
```

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
├── mcp/                            # MCP server integration (reads config/config.yaml)
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
└── scripts/                        # Standalone script wrappers
    ├── analyse_vault.py
    ├── compare_reports.py
    ├── drift_check.py
    ├── generate_report.py
    ├── inject_frontmatter.py
    ├── upgrade_vault.py
    └── validate_vault.py
```


## Creating a New Vault

Use the built-in initialisation command:

```bash
python run.py init my-vault
```

This command:

* copies the demo vault structure
* ensures a valid schema is present
* removes generated artefacts
* updates `config/config.yaml`

After initialisation, the system is immediately ready:

```bash
python run.py validate
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

The MCP server reads `config/config.yaml` — the same file used by the CLI pipeline. Whichever vault is configured as `vault_root` is automatically loaded, indexed, and served. After running `python run.py init my-vault`, the MCP server will serve `my-vault` with no additional steps.

### Usage

Install the MCP dependencies (in addition to PyYAML):

```bash
pip install fastapi uvicorn
```

Start the server:

```bash
python mcp/server/mcp_server.py
```

The server runs on `http://127.0.0.1:8000`.

### Endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/health` | GET | Server status and metrics |
| `/validation` | GET | Schema validation result |
| `/tasks` | GET | Ranked improvement tasks |
| `/tasks?limit=N` | GET | Top N tasks |
| `/notes` | GET | Structured note metadata |
| `/vaults` | GET | List the active vault |
| `/query` | POST | Query notes with filters |
| `/note` | GET | Retrieve a single note |
| `/stats` | GET | Aggregate a field across the vault |
| `/contract` | GET | Run system contract checks |

### Key Properties

- **Zero config** — reads `config/config.yaml` automatically, no manual edits required.
- **Single active vault** — serves whichever vault the CLI is configured to use.
- **Read-only** — no vault data is modified through the API.
- **Init compatible** — after `python run.py init <name>`, the server immediately serves the new vault.
- **Schema-aware** — validates notes against `vault_schema.py` at startup and periodically.


## Limitations

- **Single demo vault** — ships with one vault (`demo-vault/`) containing 19 notes in a single domain. The tooling supports multi-domain vaults but the demo does not exercise this.
- **Content generation model** — the system does not generate content itself. It provides constraints and prioritised tasks. Generation can be manual or handled by external models.

  Content generation is external and intentionally decoupled.

  This supports two workflows:

  - **Manual authoring** — users write and refine notes based on system feedback  
  - **LLM-assisted authoring** — external models (e.g. Copilot, ChatGPT) generate or improve notes using system-generated constraints and upgrade tasks  

  This enables fully automated pipelines:

  1. The system identifies gaps and prioritised improvements  
  2. An external model generates or updates content  
  3. The system re-validates and re-scores the result  

  The system remains deterministic, while generation is flexible and composable.
- **No watch mode** — the pipeline runs on demand. There is no file-watching or automatic re-validation.
- **Python dependency** — requires Python 3.10+ and PyYAML.
