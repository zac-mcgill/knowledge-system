"""
Tasks adapter — structured upgrade tasks for MCP.

Reuses core.shared.upgrade_vault scoring and task generation.
Returns JSON-serialisable dict.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import yaml


def _resolve_config() -> tuple[Path, Path]:
    """Resolve repo root and vault path from config.

    Returns (repo_root, vault_path).
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    config_path = repo_root / "config" / "config.yaml"

    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    vault_rel = data.get("vault_root")
    if not vault_rel:
        raise ValueError("config.yaml missing 'vault_root'")

    vault_path = (repo_root / vault_rel).resolve()
    if not vault_path.is_dir():
        raise FileNotFoundError(f"Vault directory not found: {vault_path}")

    return repo_root, vault_path


def _prepare_env(repo_root: Path, vault_path: Path) -> None:
    """Set CWD and sys.path so core.shared imports resolve correctly."""
    scripts_dir = vault_path / "Vault Files" / "Scripts"
    if not scripts_dir.is_dir():
        raise FileNotFoundError(f"Scripts directory not found: {scripts_dir}")

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    sys.modules.pop("vault_schema", None)
    sys.modules.pop("core.shared.upgrade_vault", None)

    os.chdir(scripts_dir)


def get_tasks(limit: int = 10) -> dict:
    """Generate prioritised upgrade tasks.

    Returns:
        {
            "total": int,
            "tasks": [
                {
                    "note": str,
                    "priority": float,
                    "difficulty": str,
                    "missing": [str],
                    "action": str
                }
            ]
        }
    """
    try:
        repo_root, vault_path = _resolve_config()
        _prepare_env(repo_root, vault_path)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}

    try:
        upgrade_mod_path = repo_root / "core" / "shared" / "upgrade_vault.py"
        spec = importlib.util.spec_from_file_location(
            "_adapter_upgrade_vault", str(upgrade_mod_path)
        )
        upgrade_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upgrade_mod)

        records = upgrade_mod.load_all(vault_path)
        all_tasks = upgrade_mod.generate_tasks(records)

        result_tasks: list[dict] = []
        for task in all_tasks[:limit]:
            missing: list[str] = []
            actions: list[str] = []
            for issue in task["issues"]:
                missing.extend(issue["required_sections"])
                actions.append(issue["issue_type"])

            note_path = task["path"]
            note_name = Path(note_path).stem

            result_tasks.append({
                "note": note_name,
                "priority": task["score"],
                "difficulty": task["difficulty"],
                "missing": missing,
                "action": ", ".join(actions),
            })

        return {
            "total": len(all_tasks),
            "tasks": result_tasks,
        }

    except Exception as exc:
        return {"error": str(exc)}
