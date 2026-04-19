"""
Query engine — filter, list, retrieve, and aggregate over indexed notes.

Operates ONLY on in-memory indexed data. Field names are validated against
each vault's schema.ALL_KNOWN_FIELDS.

Hardening:
    - Path normalisation + traversal rejection (Phase 5)
    - Deterministic pagination with limit/offset (Phase 6)
    - Stable sort on filtered results before pagination (Phase 7)
    - Strict field validation mode (Phase 8)
    - Soft timeout guard on query processing (Phase 9)
    - Typed response contract on all returns (Phase 10)
"""

import os
import time
import urllib.parse
from collections import Counter

from core.vault_registry import get_schema, get_vault_path
from core.note_index import get_index

_QUERY_TIMEOUT_MS = 200
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 500


def _valid_fields(vault_name: str) -> frozenset[str]:
    """Return the set of known fields for a vault's schema."""
    schema = get_schema(vault_name)
    return schema.ALL_KNOWN_FIELDS


def _parse_filter_key(key: str) -> tuple[str, str]:
    """Split a filter key into (field, operator).

    Supported suffixes: __in, __contains
    No suffix means equality.
    """
    for suffix in ("__in", "__contains"):
        if key.endswith(suffix):
            return key[: -len(suffix)], suffix.lstrip("_")
        
    return key, "eq"


def _match(note: dict, filters: dict, known: frozenset[str]) -> bool:
    """Return True if a note matches all valid filters."""
    fields = note["fields"]

    for key, value in filters.items():
        field, op = _parse_filter_key(key)

        # Skip unknown fields (strict validation done at query level)
        if field not in known:
            continue

        note_val = fields.get(field)

        if op == "eq":
            if note_val != value:
                return False
        elif op == "in":
            if not isinstance(value, list):
                continue
            if note_val not in value:
                return False
        elif op == "contains":
            if note_val is None or not isinstance(note_val, str):
                return False
            if str(value) not in note_val:
                return False

    return True


def query(vault_name: str, filters: dict, *, limit: int = _DEFAULT_LIMIT,
          offset: int = 0, strict: bool = False) -> dict:
    """Query a vault's index with the given filters.

    Returns a structured response dict with pagination metadata.
    """
    known = _valid_fields(vault_name)

    # Phase 8: strict field validation
    if strict:
        invalid = []
        for key in filters:
            field, _ = _parse_filter_key(key)
            if field not in known:
                invalid.append(field)
        if invalid:
            return {
                "status": "error",
                "error": {
                    "code": "INVALID_FIELDS",
                    "message": f"Unknown fields: {invalid}",
                },
            }

    # Clamp pagination parameters
    limit = max(1, min(limit, _MAX_LIMIT))
    offset = max(0, offset)

    index = get_index(vault_name)

    # Phase 9: timeout guard
    start = time.monotonic()
    deadline = start + (_QUERY_TIMEOUT_MS / 1000.0)
    timed_out = False

    results = []
    for note in index:
        if time.monotonic() > deadline:
            timed_out = True
            break
        if _match(note, filters, known):
            results.append({
                "path": note["path"],
                "fields": note["fields"],
            })

    # Phase 7: stable sort by path (case-insensitive)
    results.sort(key=lambda n: n["path"].lower())

    total = len(results)

    # Phase 6: pagination applied after filtering + sorting
    paginated = results[offset: offset + limit]

    response = {
        "status": "partial" if timed_out else "ok",
        "count": total,
        "returned": len(paginated),
        "offset": offset,
        "limit": limit,
        "results": paginated,
    }

    if timed_out:
        response["warning"] = "query timeout"

    return response


def list_notes(vault_name: str, *, limit: int = _DEFAULT_LIMIT,
               offset: int = 0) -> dict:
    """List all notes in a vault with pagination.

    Returns a structured response dict matching query() format.
    """
    index = get_index(vault_name)

    all_notes = [{"path": n["path"], "fields": n["fields"]} for n in index]

    # Phase 7: deterministic sort
    all_notes.sort(key=lambda n: n["path"].lower())

    total = len(all_notes)
    limit = max(1, min(limit, _MAX_LIMIT))
    offset = max(0, offset)
    paginated = all_notes[offset: offset + limit]

    return {
        "status": "ok",
        "count": total,
        "returned": len(paginated),
        "offset": offset,
        "limit": limit,
        "results": paginated,
    }


def get_note(vault_name: str, path: str) -> dict:
    """Retrieve a single note by relative path, with path traversal protection.

    Returns structured response dict.
    """
    vault_root = get_vault_path(vault_name)

    # Phase 5: normalise and validate path
    decoded = urllib.parse.unquote(path)
    normed = os.path.normpath(decoded)

    # Reject absolute paths outright
    if os.path.isabs(normed):
        return {
            "status": "error",
            "error": {
                "code": "PATH_TRAVERSAL",
                "message": "Absolute paths are not allowed",
            },
        }

    # Resolve to absolute and verify containment within vault
    resolved = (vault_root / normed).resolve()
    vault_resolved = vault_root.resolve()

    try:
        rel_path = resolved.relative_to(vault_resolved).as_posix()
    except ValueError:
        return {
            "status": "error",
            "error": {
                "code": "PATH_TRAVERSAL",
                "message": "Path escapes vault root",
            },
        }

    index = get_index(vault_name)
    for note in index:
        if note["path"] == rel_path:
            return {"status": "ok", "data": note}

    return {
        "status": "error",
        "error": {
            "code": "NOT_FOUND",
            "message": f"Note not found: {rel_path!r}",
        },
    }


def aggregate(vault_name: str, field: str) -> dict:
    """Count distinct values for a field across all notes in a vault.

    Returns structured response dict.
    """
    known = _valid_fields(vault_name)
    if field not in known:
        return {
            "status": "error",
            "error": {
                "code": "INVALID_FIELD",
                "message": f"Unknown field: {field!r}. Known: {sorted(known)}",
            },
        }

    index = get_index(vault_name)
    counter: Counter[str] = Counter()

    for note in index:
        val = note["fields"].get(field)
        if val is not None:
            counter[str(val)] += 1

    return {
        "status": "ok",
        "data": {
            "field": field,
            "stats": dict(counter.most_common()),
        },
    }
