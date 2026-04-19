"""
Notes adapter — structured note listing for MCP.

Reuses vault schema discovery and frontmatter parsing.
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

    os.chdir(scripts_dir)


def get_notes() -> dict:
    """Enumerate all notes with metadata.

    Returns:
        {
            "notes": [
                {
                    "name": str,
                    "status": str,
                    "difficulty": str,
                    "missing": [str],
                    "path": str
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
        # Load vault_schema directly from the vault
        schema_file = vault_path / "Vault Files" / "Scripts" / "vault_schema.py"
        if not schema_file.is_file():
            return {"error": f"Schema not found: {schema_file}"}

        spec = importlib.util.spec_from_file_location(
            "_adapter_vault_schema", str(schema_file)
        )
        schema = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema)

        files = schema.discover_files(vault_path)
        notes: list[dict] = []

        for filepath in files:
            content = schema.read_file_safe(filepath)
            fields, _ = schema.parse_yaml_frontmatter(content)
            if fields is None:
                continue

            rel_path = filepath.relative_to(vault_path).as_posix()
            name = filepath.stem

            missing: list[str] = []
            if fields.get("has_key_principles") is not True:
                missing.append("key_principles")
            if fields.get("has_how_it_works") is not True:
                missing.append("how_it_works")
            if fields.get("has_tradeoffs") is not True:
                missing.append("tradeoffs")

            notes.append({
                "name": name,
                "status": fields.get("status", "unknown"),
                "difficulty": fields.get("difficulty", "unknown"),
                "missing": missing,
                "path": rel_path,
            })

        return {"notes": notes}

    except Exception as exc:
        return {"error": str(exc)}
