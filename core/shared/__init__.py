"""
core.shared — centralised vault scripts.

Provides load_schema() for explicit, path-based resolution of a vault's
vault_schema.py.  No CWD, no sys.argv, no global key collisions.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import yaml

_SCHEMA_REL = Path("Vault Files") / "Scripts" / "vault_schema.py"
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_schema(vault_path: "str | Path", vault_name: str = "") -> ModuleType:
    """Load vault_schema.py for a vault by its absolute path.

    Args:
        vault_path: Absolute path to the vault root directory.
        vault_name: Short identifier used to namespace the cached module.
                    Defaults to the vault directory name.

    Returns:
        The loaded vault_schema module (cached per vault_name).

    Raises:
        FileNotFoundError: If vault_schema.py does not exist.
        ImportError: If the module cannot be loaded.
    """
    vault_path = Path(vault_path)
    schema_file = vault_path / _SCHEMA_REL

    if not schema_file.is_file():
        raise FileNotFoundError(
            f"vault_schema.py not found: {schema_file}"
        )

    name = vault_name or vault_path.name.replace(" ", "_").replace("-", "_")
    module_key = f"vault_schema_{name}"

    if module_key in sys.modules:
        return sys.modules[module_key]

    spec = importlib.util.spec_from_file_location(module_key, str(schema_file))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {schema_file}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_key] = mod
    spec.loader.exec_module(mod)
    return mod


def _resolve_vault_path() -> Path:
    """Resolve the active vault path from config/config.yaml.

    Used by standalone (non-CLI) invocations of core/shared/*.py scripts.
    Raises FileNotFoundError or ValueError on any configuration error.
    """
    config_path = _REPO_ROOT / "config" / "config.yaml"

    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    vault_rel = config.get("vault_root") if config else None
    if not vault_rel:
        raise ValueError("config.yaml missing 'vault_root' key")

    vault_path = (_REPO_ROOT / vault_rel).resolve()
    if not vault_path.is_dir():
        raise FileNotFoundError(f"Vault directory not found: {vault_path}")

    return vault_path
