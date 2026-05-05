"""Note write service — safe, atomic updates to existing vault notes.

Safety guarantees:
    - Only updates existing notes (no creation, no deletion).
    - Path traversal protection: absolute paths, .., Vault Files/ all rejected.
    - Schema validation: candidate content validated before any file write.
    - Atomic write: temp file in same directory → validate → rename to original.
    - Index invalidation: index cooldown expired after successful write so the
      next get_index() call detects the mtime change and rebuilds immediately.
    - Body integrity: null bytes rejected, None rejected, line endings normalised.

Public API:
    update_note(vault_name, path, fields, body) -> dict
    serialise_note_markdown(fields, body) -> str
    validate_note_update_request(vault_path, path, fields, body, schema) -> list[dict]
    invalidate_note_caches(vault_name) -> None
"""

from __future__ import annotations

import logging
import os
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any

logger = logging.getLogger("mcp.note_write")

# Field serialisation order — matches vault_schema.py conventions.
# Fields absent from this list are appended in insertion order.
_FIELD_ORDER: tuple[str, ...] = (
    "type",
    "domain",
    "subdomain",
    "topic",
    "status",
    "has_key_principles",
    "has_how_it_works",
    "has_tradeoffs",
    "difficulty",
)


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _yaml_field_line(key: str, value: Any) -> str | None:
    """Return a ``key: value`` YAML line string, or None to skip the field.

    - None and empty-string values are skipped (represent absent fields).
    - Booleans are serialised as ``true`` / ``false`` (YAML 1.1 style).
    - All other values are converted to str.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return f"{key}: {'true' if value else 'false'}"
    return f"{key}: {value}"


def serialise_note_markdown(fields: dict[str, Any], body: str) -> str:
    """Return canonical Markdown-with-frontmatter content for ``fields`` + ``body``.

    Rules:
    - YAML frontmatter enclosed in ``---`` lines.
    - Field order follows ``_FIELD_ORDER``; unknown fields appended at the end.
    - None / empty-string values are omitted from the YAML block.
    - Booleans serialised as ``true`` / ``false``.
    - Body line endings normalised to ``\\n``.
    - File always ends with a single trailing newline.
    """
    yaml_lines: list[str] = []

    # Known fields in canonical order
    for key in _FIELD_ORDER:
        if key not in fields:
            continue
        line = _yaml_field_line(key, fields[key])
        if line is not None:
            yaml_lines.append(line)

    # Any remaining fields not in the predefined order
    for key, value in fields.items():
        if key in _FIELD_ORDER:
            continue
        line = _yaml_field_line(key, value)
        if line is not None:
            yaml_lines.append(line)

    yaml_block = "\n".join(yaml_lines) + "\n"

    # Normalise body line endings and ensure trailing newline
    body_normed = body.replace("\r\n", "\n").replace("\r", "\n")
    if body_normed and not body_normed.endswith("\n"):
        body_normed += "\n"

    return f"---\n{yaml_block}---\n\n{body_normed}"


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


def _check_path_safety(
    vault_path: Path,
    path: str,
) -> tuple[str | None, str | None]:
    """Check path safety.

    Returns ``(error_code, error_message)`` on failure or ``(None, None)``
    on success.  NOT_FOUND is returned when the path is otherwise valid but
    the note does not exist on disk.
    """
    # Null bytes in path
    if "\x00" in path:
        return "INVALID_INPUT", "path must not contain null bytes"

    # URL-decode to catch %2e%2e%2f and similar encoding tricks
    decoded = urllib.parse.unquote(path)

    # Reject absolute paths
    if Path(decoded).is_absolute() or os.path.isabs(decoded):
        return "PATH_TRAVERSAL", "Absolute paths are not allowed"

    # Must end with .md
    if not decoded.lower().endswith(".md"):
        return "INVALID_NOTE_PATH", "path must end with '.md'"

    # Normalise separators and resolve traversal components
    normalised = os.path.normpath(decoded.replace("\\", "/"))

    # After normpath, a path that escapes the root starts with ".."
    if normalised.startswith(".."):
        return "PATH_TRAVERSAL", "path must not contain traversal sequences"

    # Resolve and verify containment within vault root
    vault_resolved = vault_path.resolve()
    candidate = (vault_path / normalised).resolve()
    try:
        rel = candidate.relative_to(vault_resolved)
    except ValueError:
        return "PATH_TRAVERSAL", "Path escapes vault root"

    rel_posix = rel.as_posix()

    # Must not be inside Vault Files/
    if rel.parts and rel.parts[0] == "Vault Files":
        return "INVALID_NOTE_PATH", "path must not be inside 'Vault Files/'"

    # Must exist (existing-note-only rule)
    if not candidate.is_file():
        return "NOT_FOUND", f"Note does not exist: {rel_posix!r}"

    return None, None


# ---------------------------------------------------------------------------
# Body validation
# ---------------------------------------------------------------------------


def _validate_body(body: Any) -> str | None:
    """Return an error string if body is invalid, else None."""
    if body is None:
        return "body must not be None"
    if not isinstance(body, str):
        return "body must be a string"
    if "\x00" in body:
        return "body must not contain null bytes"
    return None


# ---------------------------------------------------------------------------
# Request validation (structural; content validation via validate_file)
# ---------------------------------------------------------------------------


def validate_note_update_request(
    vault_path: Path,
    path: str,
    fields: Any,
    body: Any,
    schema: Any,
) -> list[dict]:
    """Validate structural constraints for a note update request.

    Returns a list of structured error dicts.  An empty list means the
    request passes structural checks; schema / content validation is handled
    later via ``validate_file``.

    Each error dict: ``{"code": str, "message": str}``.
    """
    errors: list[dict] = []

    # 1. Path safety (includes NOT_FOUND when file doesn't exist)
    code, msg = _check_path_safety(vault_path, path)
    if code is not None:
        errors.append({"code": code, "message": msg})
        return errors  # further checks require a valid path

    # 2. fields must be a dict
    if not isinstance(fields, dict):
        errors.append({"code": "INVALID_INPUT", "message": "fields must be an object"})
        return errors

    # 3. Unknown fields check against schema.ALL_KNOWN_FIELDS
    unknown = set(fields.keys()) - schema.ALL_KNOWN_FIELDS
    if unknown:
        errors.append({
            "code": "INVALID_INPUT",
            "message": f"Unknown frontmatter field(s): {sorted(unknown)}",
        })

    # 4. Body integrity
    body_err = _validate_body(body)
    if body_err:
        errors.append({"code": "INVALID_INPUT", "message": body_err})

    return errors


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------


def invalidate_note_caches(vault_name: str) -> None:
    """Expire the note index cooldown for ``vault_name``.

    After this call, the next ``get_index()`` call will detect the mtime
    change from the write and rebuild the index immediately, ensuring that
    subsequent GET /note and POST /query return fresh content.

    The result_cache auto-invalidates on its next access via fingerprinting,
    so no explicit action is needed there.
    """
    # Import here to avoid circular import at module load time
    from mcp.core.note_index import expire_index_cooldown  # added in this phase
    expire_index_cooldown(vault_name)
    logger.info("note_caches_invalidated vault=%s", vault_name)


# ---------------------------------------------------------------------------
# Main update function
# ---------------------------------------------------------------------------


def update_note(
    vault_name: str,
    path: str,
    fields: dict[str, Any],
    body: str,
) -> dict:
    """Atomically update an existing note in ``vault_name``.

    Validates the request, serialises the candidate content, validates it
    via the schema, writes atomically via temp-file-then-rename, and expires
    the index cooldown.

    Returns:
        On success:  ``{"status": "ok", "data": {...}}``
        On failure:  ``{"status": "error", "error": {"code": ...,
                        "message": ..., "details": [...]}}``.

    HTTP callers should map:
        NOT_FOUND     → 404
        PATH_TRAVERSAL, INVALID_NOTE_PATH, INVALID_INPUT,
        VALIDATION_FAILED                                   → 400
        WRITE_FAILED                                        → 500
    """
    from mcp.core.vault_registry import get_vault_path, get_schema
    from core.shared.validate_vault import validate_file as _validate_file

    vault_path = get_vault_path(vault_name)
    schema = get_schema(vault_name)

    # Structural pre-validation
    pre_errors = validate_note_update_request(vault_path, path, fields, body, schema)
    if pre_errors:
        first = pre_errors[0]
        return _error_response(first["code"], first["message"], pre_errors)

    # Resolve normalised path (mirrors query_engine.get_note logic)
    decoded = urllib.parse.unquote(path)
    normalised = os.path.normpath(decoded.replace("\\", "/"))
    vault_resolved = vault_path.resolve()
    note_abs = (vault_path / normalised).resolve()
    rel_posix = note_abs.relative_to(vault_resolved).as_posix()

    # Serialise candidate content
    try:
        candidate_content = serialise_note_markdown(fields, body)
    except Exception as exc:
        return _error_response("INVALID_INPUT", f"Serialisation failed: {exc}", [])

    # Schema / content validation: write candidate to a temp directory that
    # mirrors the same relative path so depth-based derivation is accurate.
    rel_path = Path(rel_posix)
    validation_errors = _validate_candidate(
        candidate_content, rel_path, schema
    )
    if validation_errors:
        details = [{"code": "VALIDATION_FAILED", "message": e} for e in validation_errors]
        return {
            "status": "error",
            "error": {
                "code": "VALIDATION_FAILED",
                "message": "Updated note failed schema validation.",
                "details": validation_errors,
            },
        }

    # Atomic write: temp file in same directory → rename to original
    note_dir = note_abs.parent
    tmp_path: Path | None = None
    try:
        fd, tmp_str = tempfile.mkstemp(suffix=".tmp", dir=str(note_dir))
        tmp_path = Path(tmp_str)
        try:
            os.write(fd, candidate_content.encode("utf-8"))
        finally:
            os.close(fd)
        # Atomic replace (works on same filesystem on both POSIX and Windows)
        tmp_path.replace(note_abs)
        tmp_path = None  # rename succeeded; no cleanup needed
    except OSError as exc:
        logger.error("note_write_failed path=%s error=%s", rel_posix, exc)
        return _error_response("WRITE_FAILED", f"Failed to write note: {exc}", [])
    except Exception as exc:
        logger.error("note_write_unexpected path=%s error=%s", rel_posix, exc)
        return _error_response("WRITE_FAILED", f"Unexpected write error: {exc}", [])
    finally:
        # Ensure temp file is cleaned up on any failure path
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    # Expire index cooldown — next get_index() will detect mtime change and rebuild
    invalidate_note_caches(vault_name)

    # Re-read the written content (canonical round-trip)
    try:
        updated_content = note_abs.read_text(encoding="utf-8")
        updated_fields, updated_body = schema.parse_yaml_frontmatter(updated_content)
    except Exception:
        # Fallback to what we wrote if re-read fails
        updated_fields = fields
        updated_body = body

    logger.info(
        "note_updated vault=%s path=%s",
        vault_name, rel_posix,
    )
    return {
        "status": "ok",
        "data": {
            "path": rel_posix,
            "fields": updated_fields or {},
            "body": updated_body,
            "validation": {
                "status": "pass",
                "errors": [],
            },
            "warnings": [],
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_candidate(
    candidate_content: str,
    rel_path: Path,
    schema: Any,
) -> list[str]:
    """Validate candidate note content without touching the original file.

    Creates a temporary directory mirroring ``rel_path``'s structure so that
    depth-based derivation in ``validate_file`` works correctly (e.g. domain
    from path_parts[0], subdomain from path_parts[1]).

    Returns a list of error strings.  Empty list = valid.
    """
    from core.shared.validate_vault import validate_file as _validate_file

    with tempfile.TemporaryDirectory(prefix="cvault_validate_") as tmpdir:
        tmp_root = Path(tmpdir)

        # Recreate the directory structure
        tmp_note_dir = tmp_root
        for part in rel_path.parts[:-1]:
            tmp_note_dir = tmp_note_dir / part
        tmp_note_dir.mkdir(parents=True, exist_ok=True)

        tmp_note_path = tmp_note_dir / rel_path.name
        tmp_note_path.write_text(candidate_content, encoding="utf-8")

        return _validate_file(tmp_note_path, tmp_root, schema)


def _error_response(
    code: str,
    message: str,
    details: list,
) -> dict:
    """Return a structured error response dict."""
    err: dict = {"code": code, "message": message}
    if details:
        err["details"] = details
    return {"status": "error", "error": err}
