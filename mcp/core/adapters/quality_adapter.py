"""
Quality adapter — content quality audit results for MCP.

Delegates directly to core.shared.quality_audit.  No business logic.
"""

from __future__ import annotations

from mcp.core.schema_loader import load_schema as _load_schema
from mcp.core.vault_registry import get_vault_path, list_vaults
from mcp.core.result_cache import get_cached, set_cached
from core.shared.quality_audit import extract_sections, score_note

_ENDPOINT = "quality"


def get_quality(vault_name: str | None = None) -> dict:
    """Run content quality audit and return structured results.

    Returns:
        {
            "total": int,
            "flagged": int,
            "highest_score": int,
            "average_score": float,
            "notes": [
                {
                    "file": str,
                    "score": int,
                    "severity": str,
                    "issues": [
                        {"rule": str, "weight": int, "explanation": str}
                    ]
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

        cached = get_cached(vault_name, _ENDPOINT)
        if cached is not None:
            return cached

        vault_path = get_vault_path(vault_name)
        _schema = _load_schema(vault_path)

        results: list[dict] = []
        for filepath in _schema.discover_files(_schema.VAULT_ROOT):
            if _schema.derive_type(filepath.name) != "core-concept":
                continue

            content = _schema.read_file_safe(filepath)
            _, body = _schema.parse_yaml_frontmatter(content)
            sections = extract_sections(body)
            raw = score_note(filepath, sections)

            results.append({
                "file": filepath.relative_to(vault_path).as_posix(),
                "score": raw["score"],
                "severity": raw["severity"],
                "issues": [
                    {"rule": rule_id, "weight": weight, "explanation": explanation}
                    for rule_id, weight, explanation in raw["issues"]
                ],
            })

        # Sort matches CLI: descending score, then ascending file name
        results.sort(key=lambda r: (-r["score"], r["file"].lower()))

        total = len(results)
        flagged = sum(1 for r in results if r["score"] > 0)
        highest = max((r["score"] for r in results), default=0)
        avg = sum(r["score"] for r in results) / total if total else 0.0

        result = {
            "total": total,
            "flagged": flagged,
            "highest_score": highest,
            "average_score": round(avg, 1),
            "notes": results,
        }

        set_cached(vault_name, _ENDPOINT, result)
        return result

    except Exception as exc:
        return {"error": str(exc)}
