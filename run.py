import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

COMMANDS = {
    "validate": "core.shared.validate_vault",
    "report": "core.shared.generate_report",
    "analyse": "core.shared.analyse_vault",
    "improve": "core.shared.upgrade_vault",
}

USAGE = """\
Usage: python run.py <command>

Commands:
  init <vault>   Create a new vault from the demo template
  validate       Check all notes against the vault schema
  analyse        Run seven structured analyses on vault metadata
  improve        Generate prioritised upgrade tasks
  report         Generate a markdown report
  templates      Generate canonical templates from vault schema
                 Use --dry-run to preview without writing"""


def _init_vault(repo_root: Path) -> None:
    if len(sys.argv) != 3 or not sys.argv[2].strip():
        print(USAGE)
        raise SystemExit(1)

    vault_name = sys.argv[2]

    if not re.match(r'^[A-Za-z0-9_\-][A-Za-z0-9_\- .]*$', vault_name):
        print(f"Error: invalid vault name: {vault_name}")
        raise SystemExit(1)

    target = repo_root / vault_name
    source = repo_root / "demo-vault"
    config_path = repo_root / "config" / "config.yaml"

    if target.exists():
        print(f"Error: directory already exists: {vault_name}")
        raise SystemExit(1)

    if not source.is_dir():
        print("Error: demo-vault not found")
        raise SystemExit(1)

    if not config_path.is_file():
        print("Error: config/config.yaml not found")
        raise SystemExit(1)

    # Deep copy demo-vault
    shutil.copytree(source, target)

    # Remove generated report if present
    report = target / "Vault Files" / "Vault Report.md"
    if report.is_file():
        report.unlink()

    # Atomic config update
    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    updated = re.sub(
        r'^(vault_root:\s*).*$',
        rf'\g<1>./{vault_name}',
        content,
        flags=re.MULTILINE,
    )

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=config_path.parent, suffix=".yaml"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp:
            tmp.write(updated)
        Path(tmp_path).replace(config_path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    print(f"Vault created: {vault_name}")
    print(f"Config updated: config/config.yaml")
    print(f"Ready to run: python run.py validate")


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        raise SystemExit(1)

    command = sys.argv[1]

    repo_root = Path(__file__).resolve().parent

    if command == "help":
        print(USAGE)
        return

    if command == "init":
        _init_vault(repo_root)
        return

    if command == "templates":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from core.generate_templates import main as templates_main
        raise SystemExit(templates_main())

    if command not in COMMANDS:
        print(f"Error: unknown command '{command}'")
        print(USAGE)
        raise SystemExit(1)

    config_path = repo_root / "config" / "config.yaml"
    if not config_path.is_file():
        print("Error: config/config.yaml not found")
        raise SystemExit(1)

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"Error: invalid config/config.yaml: {exc}")
        raise SystemExit(1)

    vault_rel = config.get("vault_root") if config else None
    if not vault_rel:
        print("Error: config/config.yaml missing 'vault_root' key")
        raise SystemExit(1)

    vault_root = (repo_root / vault_rel).resolve()
    if not vault_root.is_dir():
        print(f"Error: vault directory not found: {vault_root}")
        raise SystemExit(1)

    scripts_dir = vault_root / "Vault Files" / "Scripts"
    if not scripts_dir.is_dir():
        print(f"Error: vault scripts directory not found: {scripts_dir}")
        raise SystemExit(1)

    sys.path.insert(0, str(repo_root))

    sys.argv = sys.argv[:1]

    module = __import__(COMMANDS[command], fromlist=["main"])
    try:
        raise SystemExit(module.main(vault_root))
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)
    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)
    except Exception as exc:
        print(f"Error: unexpected failure in {command}: {exc}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
