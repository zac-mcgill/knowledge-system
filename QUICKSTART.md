# Quickstart

## 1. Clone

```bash
git clone <repo-url> knowledge-system
cd knowledge-system
pip install pyyaml
```

## 2. Initialise a Vault

```bash
python run.py init my-vault
```

## 3. Run the Pipeline

```bash
python run.py validate
python run.py analyse
python run.py improve
python run.py report
```

| Command | What it does |
| --- | --- |
| `python run.py validate` | Checks every markdown note against the vault schema. Prints pass/fail per file. Exits 0 if all files pass, 1 if any fail. |
| `python run.py analyse` | Prints seven structured analyses to stdout: completeness by domain, subdomain weak points, difficulty vs completeness, critical gaps, section deficiency heatmap, structural balance, and a prioritised action list. |
| `python run.py improve` | Scans all partial notes, scores them by difficulty and missing sections, and prints ranked upgrade tasks with specific writing instructions per note. |
| `python run.py report` | Generates `Vault Report.md` inside the vault's `Vault Files/` directory. Contains executive summary, domain analysis, key insights, critical gaps, section deficiencies, and priority actions. |
| `python run.py init <name>` | Creates a new vault by copying the demo vault, removes generated files, and updates configuration automatically. |

`validate`, `analyse`, and `improve` are read-only — they never modify files. `report` writes one markdown file.

## 4. Start API Server (Optional)

```bash
pip install fastapi uvicorn
python mcp/server/mcp_server.py
```

The server starts on `http://127.0.0.1:8000` and automatically loads whichever vault is set in `config/config.yaml`. No manual config edits are needed.

## 5. Query the System

Examples:

* http://127.0.0.1:8000/validation
* http://127.0.0.1:8000/tasks
* http://127.0.0.1:8000/tasks?limit=5
* http://127.0.0.1:8000/notes
