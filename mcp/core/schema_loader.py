"""
Schema loader — dynamically imports vault_schema.py from each vault.

Uses importlib to load each vault's schema as an isolated module with a
unique name (vault_schema_{vault_name}) to prevent name collisions.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_SCHEMA_RELATIVE_PATH = Path("Vault Files") / "Scripts" / "vault_schema.py"


def load_schema(vault_path: str | Path, vault_name: str = "") -> ModuleType:
    """Load a vault's schema module by absolute vault path.

    Args:
        vault_path: Absolute path to the vault root directory.
        vault_name: Short name used to namespace the module (e.g. 'cyber').

    Returns:
        The loaded module object.

    Raises:
        FileNotFoundError: If the schema file does not exist.
        ImportError: If the module cannot be loaded.
    """
    vault_path = Path(vault_path)
    schema_file = vault_path / _SCHEMA_RELATIVE_PATH

    if not schema_file.is_file():
        raise FileNotFoundError(
            f"Schema not found: {schema_file}"
        )

    module_name = f"vault_schema_{vault_name}" if vault_name else f"vault_schema_{vault_path.stem}"

    # Return cached module if already loaded
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, str(schema_file))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {schema_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module
