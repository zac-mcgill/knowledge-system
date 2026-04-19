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

USAGE = "Usage: python run.py [validate|analyse|improve|report|init <vault-name>]"


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

    if command == "init":
        _init_vault(repo_root)
        return

    if command not in COMMANDS:
        print(USAGE)
        raise SystemExit(1)

    with open(repo_root / "config" / "config.yaml") as f:
        config = yaml.safe_load(f)

    vault_root = (repo_root / config["vault_root"]).resolve()
    scripts_dir = vault_root / "Vault Files" / "Scripts"

    sys.path.insert(0, str(repo_root))
    os.chdir(scripts_dir)

    sys.argv = sys.argv[:1]

    module = __import__(COMMANDS[command], fromlist=["main"])
    raise SystemExit(module.main())

if __name__ == "__main__":
    main()
