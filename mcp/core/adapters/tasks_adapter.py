"""
Tasks adapter — structured upgrade tasks for MCP.

Delegates directly to core.shared.upgrade_vault.  No sys.modules
manipulation, no os.chdir, no importlib workarounds.
"""

from __future__ import annotations

from pathlib import Path

from mcp.core.vault_registry import get_vault_path, list_vaults
from core.shared.upgrade_vault import load_all, generate_tasks
from mcp.core.schema_loader import load_schema as _load_schema
from mcp.core.result_cache import get_cached, set_cached

_ENDPOINT = "tasks"


def get_tasks(vault_name: str | None = None, limit: int = 10) -> dict:
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
        if vault_name is None:
            vaults = list_vaults()
            if not vaults:
                return {"error": "No vaults registered"}
            vault_name = vaults[0]

        # Cache check — full task list is cached; limit applied on return
        cached = get_cached(vault_name, _ENDPOINT)
        if cached is not None:
            return {
                "total": cached["total"],
                "tasks": cached["tasks"][:limit],
            }

        vault_path = get_vault_path(vault_name)
        _schema = _load_schema(vault_path)

        records = load_all(vault_path, _schema)
        all_tasks = generate_tasks(records, _schema)

        # Build full transformed list (no early limit — enables correct caching)
        result_tasks: list[dict] = []
        for task in all_tasks:
            missing: list[str] = []
            actions: list[str] = []
            all_constraints: list[str] = []
            for issue in task["issues"]:
                missing.extend(issue["required_sections"])
                actions.append(issue["issue_type"])
                all_constraints.extend(issue.get("constraints", []))

            note_path = task["path"]
            posix_path = Path(note_path).as_posix()
            note_name = Path(note_path).stem

            result_tasks.append({
                "note": note_name,
                "path": posix_path,
                "priority": task["score"],
                "difficulty": task["difficulty"],
                "missing": missing,
                "action": ", ".join(actions),
                "constraints": all_constraints,
            })

        # Cache the complete result before applying limit
        full_result = {
            "total": len(all_tasks),
            "tasks": result_tasks,
        }
        set_cached(vault_name, _ENDPOINT, full_result)

        return {
            "total": len(all_tasks),
            "tasks": result_tasks[:limit],
        }

    except Exception as exc:
        return {"error": str(exc)}
