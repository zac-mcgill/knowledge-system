"""
Validation adapter — structured validation results for MCP.

Delegates directly to core.shared.validate_vault.  No sys.modules
manipulation, no os.chdir, no importlib workarounds.
"""

from __future__ import annotations

import core.shared.validate_vault as _validate_mod
from mcp.core.vault_registry import get_vault_path, list_vaults
from mcp.core.result_cache import get_cached, set_cached

_ENDPOINT = "validation"


def get_validation(vault_name: str | None = None) -> dict:
    """Run validation and return structured results.

    Returns:
        {
            "status": "pass" | "fail",
            "invalid_count": int,
            "invalid_notes": [str]
        }
    """
    try:
        if vault_name is None:
            vaults = list_vaults()
            if not vaults:
                return {"error": "No vaults registered"}
            vault_name = vaults[0]

        # Cache check — skip full recomputation if vault + schema unchanged
        cached = get_cached(vault_name, _ENDPOINT)
        if cached is not None:
            return cached

        vault_path = get_vault_path(vault_name)
        _validate_mod._bind(vault_path)

        files = _validate_mod.discover_files(vault_path)
        invalid_notes: list[str] = []

        for filepath in files:
            errors = _validate_mod.validate_file(filepath, vault_path)
            if errors:
                rel = str(filepath.relative_to(vault_path))
                invalid_notes.append(rel)

        result = {
            "status": "fail" if invalid_notes else "pass",
            "invalid_count": len(invalid_notes),
            "invalid_notes": invalid_notes,
        }

        # Cache the successful, complete result
        set_cached(vault_name, _ENDPOINT, result)
        return result

    except Exception as exc:
        return {"error": str(exc)}
