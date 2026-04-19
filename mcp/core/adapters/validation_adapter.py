"""
Validation adapter — structured validation results for MCP.

Reuses core.shared.validate_vault logic. Returns JSON-serialisable dict.
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

    # Clear cached schema so load_schema() re-discovers from new CWD
    sys.modules.pop("vault_schema", None)
    sys.modules.pop("core.shared.validate_vault", None)

    os.chdir(scripts_dir)


def get_validation() -> dict:
    """Run validation and return structured results.

    Returns:
        {
            "status": "pass" | "fail",
            "invalid_count": int,
            "invalid_notes": [str]
        }
    """
    try:
        repo_root, vault_path = _resolve_config()
        _prepare_env(repo_root, vault_path)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}

    try:
        # Load validate_vault by file path to avoid sys.path conflicts
        # with mcp/core/ vs repo core/
        validate_mod_path = repo_root / "core" / "shared" / "validate_vault.py"
        spec = importlib.util.spec_from_file_location(
            "_adapter_validate_vault", str(validate_mod_path)
        )
        validate_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validate_mod)

        discover_files = validate_mod.discover_files
        validate_file = validate_mod.validate_file

        files = discover_files(vault_path)
        invalid_notes: list[str] = []

        for filepath in files:
            errors = validate_file(filepath, vault_path)
            if errors:
                rel = str(filepath.relative_to(vault_path))
                invalid_notes.append(rel)

        return {
            "status": "fail" if invalid_notes else "pass",
            "invalid_count": len(invalid_notes),
            "invalid_notes": invalid_notes,
        }

    except Exception as exc:
        return {"error": str(exc)}
