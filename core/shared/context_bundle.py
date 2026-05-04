"""
Context Bundle Engine — Phase 2

Generates deterministic context bundles from vault notes.

A bundle packages selected notes with metadata, optional section extracts,
optional full bodies, optional graph relationships, validation state, and
budget information.

Rules:
- Deterministic note ordering (path, case-insensitive).
- Full vault-relative POSIX paths only.
- Schema-invalid notes are always excluded.
- Notes with status=partial are excluded unless allow_partial=True.
- max_notes is respected (applied after filtering, before budget check).
- max_chars is respected (stop adding notes once budget is exhausted).
- Missing sections produce empty strings and warnings.
- bundle_id is deterministic from request parameters (timestamp excluded).
- Source notes are never mutated.
- Bundle files are not written (Phase 4 concern).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from mcp.core.vault_registry import get_vault_path, get_schema
from mcp.core.note_index import build_index, get_index
from mcp.core.adapters.validation_adapter import get_validation
from mcp.core.graph_builder import build_graph
from mcp.core.graph_query import get_related_nodes


def _make_bundle_id(
    vault: str,
    filters: dict,
    include_sections: list[str],
    include_related: bool,
    include_body: bool,
    max_notes: int,
    max_chars: int,
    allow_partial: bool,
) -> str:
    """Return a 16-char hex deterministic bundle ID.

    Derived from all request parameters that affect content selection.
    Timestamp is excluded so the ID is stable across repeated calls.
    """
    params = json.dumps(
        {
            "vault": vault,
            "filters": sorted(filters.items()),
            "sections": sorted(include_sections),
            "include_related": include_related,
            "include_body": include_body,
            "max_notes": max_notes,
            "max_chars": max_chars,
            "allow_partial": allow_partial,
        },
        sort_keys=True,
    )
    return hashlib.sha256(params.encode()).hexdigest()[:16]


def generate_bundle(
    vault_name: str,
    filters: dict | None = None,
    include_sections: list[str] | None = None,
    include_related: bool = False,
    include_body: bool = True,
    max_notes: int = 10,
    max_chars: int = 20000,
    allow_partial: bool = False,
) -> dict:
    """Generate a deterministic context bundle from vault notes.

    Args:
        vault_name:       Registered vault name.
        filters:          Equality filters on frontmatter fields.
                          Example: {"domain": "fundamentals", "status": "complete"}
        include_sections: Section heading names to extract (without "## " prefix).
                          Missing sections produce empty strings and warnings.
        include_related:  If True, include graph relationship IDs per note.
        include_body:     If True, include full note body text.
        max_notes:        Maximum number of notes to include.
        max_chars:        Character budget across all note content.
        allow_partial:    If True, include notes with status=partial.

    Returns:
        Bundle dict with status, bundle_id, vault, filters, created_at,
        validation_status, notes, graph, budget, warnings, and manifest.
        On vault lookup failure, returns {"status": "error", "error": {...}}.
    """
    if filters is None:
        filters = {}
    if include_sections is None:
        include_sections = []

    warnings: list[str] = []

    # ------------------------------------------------------------------
    # 1. Resolve vault
    # ------------------------------------------------------------------
    try:
        get_vault_path(vault_name)   # validates vault is registered
        schema = get_schema(vault_name)
    except KeyError as exc:
        return {
            "status": "error",
            "error": {"code": "INVALID_VAULT", "message": str(exc)},
        }

    # ------------------------------------------------------------------
    # 2. Build / refresh index (body is included in each index entry)
    # ------------------------------------------------------------------
    build_index(vault_name)
    index = get_index(vault_name)

    # ------------------------------------------------------------------
    # 3. Get validation result (warm cache after build_index)
    # ------------------------------------------------------------------
    val_result = get_validation(vault_name=vault_name)
    invalid_paths: set[str] = set(val_result.get("invalid_notes", []))

    # ------------------------------------------------------------------
    # 4. Filter notes
    # ------------------------------------------------------------------

    # a) Equality filters on frontmatter fields
    filtered: list[dict] = []
    for note in index:
        match = True
        for k, v in filters.items():
            if note["fields"].get(k) != v:
                match = False
                break
        if match:
            filtered.append(note)

    # b) Always exclude schema-invalid notes
    filtered = [n for n in filtered if n["path"] not in invalid_paths]

    # c) Exclude partial-status notes unless allow_partial=True
    if not allow_partial:
        filtered = [n for n in filtered if n["fields"].get("status") != "partial"]

    # d) Deterministic sort by path (case-insensitive)
    filtered.sort(key=lambda n: n["path"].lower())

    # e) Apply max_notes cap
    if len(filtered) > max_notes:
        filtered = filtered[:max_notes]

    if not filtered:
        warnings.append("No notes matched the given filters and constraints")

    # ------------------------------------------------------------------
    # 5. Build note objects with budget tracking
    # ------------------------------------------------------------------
    used_chars = 0
    truncated = False
    notes_out: list[dict] = []

    for note in filtered:
        if truncated:
            break

        path = note["path"]
        fields = note["fields"]
        body = note.get("body", "")

        # Extract requested sections
        sections: dict[str, str] = {}
        for sec_name in include_sections:
            heading = f"## {sec_name}"
            content = schema.extract_section_body(body, heading)
            if content is None:
                sections[sec_name] = ""
                warnings.append(f"Section '{sec_name}' not found in '{path}'")
            else:
                sections[sec_name] = content

        # Compute chars this note contributes to budget.
        # Count body chars (if include_body) plus section chars independently.
        # Sections are subsets of the body, but the caller receives both
        # as separate output fields, so both are counted.
        note_chars = 0
        if include_body:
            note_chars += len(body)
        if include_sections:
            note_chars += sum(len(v) for v in sections.values())

        # Only enforce budget if this note contributes content.
        if note_chars > 0 and used_chars + note_chars > max_chars:
            warnings.append(
                f"Budget limit reached before '{path}' "
                f"({used_chars}/{max_chars} chars used)"
            )
            truncated = True
            break

        used_chars += note_chars

        notes_out.append(
            {
                "path": path,
                "fields": fields,
                "sections": sections,
                "body": body if include_body else "",
            }
        )

    # ------------------------------------------------------------------
    # 6. Build graph relationships (optional)
    # ------------------------------------------------------------------
    graph_related: dict[str, list[str]] = {}
    if include_related and notes_out:
        try:
            graph = build_graph(vault_name=vault_name)
            for note_obj in notes_out:
                node_id = note_obj["path"]
                try:
                    result = get_related_nodes(graph, node_id)
                    related_ids = sorted(r["id"] for r in result.get("related", []))
                    graph_related[node_id] = related_ids
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"Graph lookup failed for '{node_id}': {exc}")
                    graph_related[node_id] = []
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Graph build failed: {exc}")

    # ------------------------------------------------------------------
    # 7. Validation status for selected notes
    # ------------------------------------------------------------------
    selected_paths = {n["path"] for n in notes_out}
    has_invalid = bool(selected_paths & invalid_paths)
    validation_status = "fail" if has_invalid else "pass"

    # ------------------------------------------------------------------
    # 8. Schema version (null if not defined in schema)
    # ------------------------------------------------------------------
    schema_version: str | None = getattr(schema, "SCHEMA_VERSION", None)

    # ------------------------------------------------------------------
    # 9. Bundle ID and timestamp
    # ------------------------------------------------------------------
    bundle_id = _make_bundle_id(
        vault_name,
        filters,
        include_sections,
        include_related,
        include_body,
        max_notes,
        max_chars,
        allow_partial,
    )
    created_at = datetime.now(timezone.utc).isoformat()

    return {
        "status": "ok",
        "bundle_id": bundle_id,
        "vault": vault_name,
        "filters": filters,
        "created_at": created_at,
        "validation_status": validation_status,
        "notes": notes_out,
        "graph": {"related": graph_related},
        "budget": {
            "max_chars": max_chars,
            "used_chars": used_chars,
            "note_count": len(notes_out),
            "truncated": truncated,
        },
        "warnings": warnings,
        "manifest": {
            "source_paths": sorted(n["path"] for n in notes_out),
            "schema_version": schema_version,
        },
    }
