"""
Tasks adapter — structured upgrade tasks for MCP.

Delegates directly to core.shared.upgrade_vault.  No sys.modules
manipulation, no os.chdir, no importlib workarounds.
"""

from __future__ import annotations

from pathlib import Path

from mcp.core.vault_registry import get_vault_path, list_vaults
from core.shared.upgrade_vault import _bind, load_all, generate_tasks


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

        vault_path = get_vault_path(vault_name)
        _bind(vault_path)

        records = load_all(vault_path)
        all_tasks = generate_tasks(records)

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
