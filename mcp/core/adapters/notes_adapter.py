"""
Notes adapter — structured note listing for MCP.

Delegates directly to the vault registry and schema.  No sys.modules
manipulation, no os.chdir, no importlib workarounds.
"""

from __future__ import annotations

from pathlib import Path

from mcp.core.vault_registry import get_vault_path, get_schema, list_vaults


def get_notes(vault_name: str | None = None) -> dict:
    """Enumerate all notes with metadata.

    Returns:
        {
            "notes": [
                {
                    "name": str,
                    "status": str,
                    "difficulty": str,
                    "missing": [str],
                    "path": str,
                    "source_type": str | None,
                    "trust_level": str | None
                }
            ]
        }

    The ``source_type`` and ``trust_level`` fields are derived directly from
    note frontmatter when present, and are ``None`` otherwise.  They are used
    by the Phase 26C import review workflow (Notes UI imported/draft filters
    and badges) to triage imported Markdown without an extra round-trip.
    """
    try:
        if vault_name is None:
            vaults = list_vaults()
            if not vaults:
                return {"error": "No vaults registered"}
            vault_name = vaults[0]

        vault_path = get_vault_path(vault_name)
        schema = get_schema(vault_name)

        files = schema.discover_files(vault_path)
        notes: list[dict] = []

        for filepath in files:
            content = schema.read_file_safe(filepath)
            fields, body = schema.parse_yaml_frontmatter(content)
            if fields is None:
                continue

            rel_path = filepath.relative_to(vault_path).as_posix()
            name = filepath.stem
            note_type = fields.get("type", "core-concept")

            missing: list[str] = []
            if note_type == "core-concept":
                if fields.get("has_key_principles") is not True:
                    missing.append("key_principles")
                if fields.get("has_how_it_works") is not True:
                    missing.append("how_it_works")
                if fields.get("has_tradeoffs") is not True:
                    missing.append("tradeoffs")
            else:
                present_headings = set(schema.find_headings(body))
                for section in schema.SECTION_MAP.get(note_type, ()):
                    if section not in present_headings:
                        slug = section.lstrip("#").strip().lower()
                        slug = slug.replace(" ", "_").replace("-", "_")
                        missing.append(slug)

            notes.append({
                "name": name,
                "status": fields.get("status", "unknown"),
                "difficulty": fields.get("difficulty", "unknown"),
                "missing": missing,
                "path": rel_path,
                "source_type": _normalise_optional_str(fields.get("source_type")),
                "trust_level": _normalise_optional_str(fields.get("trust_level")),
            })

        return {"notes": notes}

    except Exception as exc:
        return {"error": str(exc)}


def _normalise_optional_str(value):
    """Return a stripped string or None for absent/blank frontmatter values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
