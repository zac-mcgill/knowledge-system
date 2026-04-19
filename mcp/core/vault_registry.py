"""
Vault registry — loads config, resolves paths, caches schemas.

Single source of truth for vault name → path → schema mappings.
"""

import json
from pathlib import Path
from types import ModuleType

from core.schema_loader import load_schema

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "vaults.json"

_vaults: dict[str, Path] = {}
_schemas: dict[str, ModuleType] = {}


def _load_config() -> None:
    """Parse vaults.json and validate that all paths exist."""
    global _vaults

    if _vaults:
        return

    if not _CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Config not found: {_CONFIG_PATH}")

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for name, raw_path in data["vaults"].items():
        p = Path(raw_path)
        if not p.is_absolute():
            p = (_CONFIG_PATH.parent.parent.parent / raw_path).resolve()
        if not p.is_dir():
            raise FileNotFoundError(f"Vault directory not found: {p} (vault={name!r})")
        _vaults[name] = p


def list_vaults() -> list[str]:
    """Return sorted list of registered vault names."""
    _load_config()
    return sorted(_vaults.keys())


def get_vault_path(name: str) -> Path:
    """Return absolute path for a vault name.

    Raises:
        KeyError: If the vault name is not registered.
    """
    _load_config()
    if name not in _vaults:
        raise KeyError(f"Unknown vault: {name!r}. Available: {sorted(_vaults.keys())}")
    return _vaults[name]


def get_schema(name: str) -> ModuleType:
    """Return the cached schema module for a vault.

    Loads the schema on first call, then caches it.

    Raises:
        KeyError: If the vault name is not registered.
        FileNotFoundError: If the schema file is missing.
        ImportError: If the schema cannot be loaded.
    """
    _load_config()
    if name not in _vaults:
        raise KeyError(f"Unknown vault: {name!r}. Available: {sorted(_vaults.keys())}")

    if name not in _schemas:
        _schemas[name] = load_schema(_vaults[name], vault_name=name)

    return _schemas[name]
