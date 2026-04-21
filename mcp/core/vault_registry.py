"""
Vault registry — loads config, resolves paths, caches schemas.

Single source of truth for vault name → path → schema mappings.
Reads the active vault from config/config.yaml (shared with run.py).
"""

import yaml
from pathlib import Path
from types import ModuleType

from mcp.core.schema_loader import load_schema

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _REPO_ROOT / "config" / "config.yaml"

_vaults: dict[str, Path] = {}
_schemas: dict[str, ModuleType] = {}


def _load_config() -> None:
    """Parse config.yaml and resolve the active vault."""
    global _vaults

    if _vaults:
        return

    if not _CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Config not found: {_CONFIG_PATH}")

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    vault_root = data.get("vault_root")
    if not vault_root:
        raise ValueError(f"config.yaml missing 'vault_root': {_CONFIG_PATH}")

    p = Path(vault_root)
    if not p.is_absolute():
        p = (_REPO_ROOT / vault_root).resolve()

    if not p.is_dir():
        raise FileNotFoundError(f"Vault directory not found: {p}")

    vault_name = p.name
    _vaults[vault_name] = p


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
