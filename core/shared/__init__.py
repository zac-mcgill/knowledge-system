"""
core.shared — centralised vault scripts.

Provides load_schema() for explicit, sys.path-independent resolution
of the calling vault's vault_schema.py.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_schema():
    """Locate vault_schema.py from CWD / script dir and load via importlib.

    Search order:
        1. Path.cwd()
        2. Directory containing sys.argv[0] (the wrapper script)
        3. Walk parent directories from each candidate

    The loaded module is cached in sys.modules['vault_schema'] so that
    subsequent imports resolve without a second search.

    Returns the loaded vault_schema module.
    """
    if "vault_schema" in sys.modules:
        return sys.modules["vault_schema"]

    roots: list[Path] = [Path.cwd().resolve()]
    if sys.argv and sys.argv[0]:
        script_dir = Path(sys.argv[0]).resolve().parent
        if script_dir not in roots:
            roots.append(script_dir)

    for start in roots:
        cursor = start
        while True:
            candidate = cursor / "vault_schema.py"
            if candidate.is_file():
                spec = importlib.util.spec_from_file_location(
                    "vault_schema", str(candidate),
                )
                mod = importlib.util.module_from_spec(spec)
                sys.modules["vault_schema"] = mod
                spec.loader.exec_module(mod)
                return mod
            parent = cursor.parent
            if parent == cursor:
                break
            cursor = parent

    raise FileNotFoundError(
        "vault_schema.py not found from CWD or script directory. "
        f"Searched from: {', '.join(str(r) for r in roots)}"
    )
