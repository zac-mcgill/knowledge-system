"""Safe Memory Write Queue — Phase 23.

Stores proposed note changes as reviewable pending objects.
Nothing writes to note files until an explicit accept operation validates
and applies the change through the existing safe note edit path.

Core rule:
  LLMs may propose changes.  They must not directly rewrite notes by default.

Storage layout::

    <vault>/Vault Files/State/pending-changes/
        <change_id>.json        — active pending changes
        archive/
            <change_id>.json    — accepted / rejected changes (retained for audit)

Change IDs are ``<yyyymmddTHHMMSS>-<8-hex>`` (UTC timestamp + 4 random bytes).
They are always filesystem-safe and do not embed raw user content.

Design constraints:
- Python standard library only (no third-party dependencies).
- Atomic writes via temp-file + ``Path.replace()``.
- JSON output is pretty-printed with sorted keys and stable indentation.
- Path traversal blocked.  Absolute paths rejected.
- Writes inside ``Vault Files/`` as a target note path are blocked.
- No secrets or auth tokens are stored.
- Pending changes are NOT included in context bundles.
- Nothing is auto-accepted.
- Private-cloud read-only enforcement is the responsibility of HTTP/MCP callers.

Accepted/rejected changes are archived and retained for audit.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import os
import re
import tempfile
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("mcp.pending_changes")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STATE_SUBDIR = Path("Vault Files") / "State"
_PENDING_SUBDIR = _STATE_SUBDIR / "pending-changes"
_ARCHIVE_SUBDIR = _PENDING_SUBDIR / "archive"

# Change ID: yyyymmddTHHMMSS-<8 hex chars>
_CHANGE_ID_RE = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{8}$")

CHANGE_TYPES: frozenset[str] = frozenset({
    "create_note_draft",
    "suggest_note_update",
    "update_note_section_draft",
})

VALID_STATUSES: frozenset[str] = frozenset({
    "pending", "accepted", "rejected", "invalid",
})

VALID_VALIDATION_STATUSES: frozenset[str] = frozenset({
    "pass", "fail", "not_checked",
})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_change_id() -> str:
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    rand_hex = os.urandom(4).hex()
    return f"{ts}-{rand_hex}"


def _error(code: str, message: str) -> dict:
    return {"status": "error", "error": {"code": code, "message": message}}


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write data as pretty-printed JSON to path atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    tmp_fd, tmp_path_str = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def _get_vault_and_schema(vault_name: str) -> tuple[Path, Any]:
    """Return (vault_path, schema) or raise KeyError for invalid vault."""
    from mcp.core.vault_registry import get_vault_path, get_schema
    vault_path = get_vault_path(vault_name)
    schema = get_schema(vault_name)
    return vault_path, schema


def _validate_content(content: str, norm_path: str, schema: Any) -> list[str]:
    """Validate serialised note content against schema.

    Returns a list of error strings.  Empty list = valid.
    """
    from core.shared.validate_vault import validate_file as _validate_file

    rel_path = Path(norm_path)
    with tempfile.TemporaryDirectory(prefix="cvault_pending_") as tmpdir:
        tmp_root = Path(tmpdir)
        tmp_note_dir = tmp_root
        for part in rel_path.parts[:-1]:
            tmp_note_dir = tmp_note_dir / part
            tmp_note_dir.mkdir(parents=True, exist_ok=True)
        tmp_note = tmp_note_dir / rel_path.name
        try:
            tmp_note.write_text(content, encoding="utf-8")
        except OSError as exc:
            return [f"Cannot write temp file for validation: {exc}"]
        try:
            # validate_file expects pathlib.Path arguments (it calls
            # .relative_to() on the filepath internally).  Passing strings
            # previously surfaced an opaque AttributeError to the user.
            errors = _validate_file(tmp_note, tmp_root, schema)
        except Exception as exc:
            logger.exception("validate_file raised for pending change")
            return [f"Schema validator raised an internal error: {exc}"]
        if not errors:
            return []
        return [str(e) for e in errors] if isinstance(errors, list) else [str(errors)]


def _check_pending_target_path(
    vault_path: Path,
    path: str,
    must_exist: bool = False,
) -> tuple[str | None, str | None]:
    """Validate a target note path for a pending change.

    Returns ``(error_code, error_message)`` on failure, ``(None, None)`` on success.
    """
    if not path or not path.strip():
        return "INVALID_NOTE_PATH", "path must not be empty"

    if "\x00" in path:
        return "INVALID_INPUT", "path must not contain null bytes"

    decoded = urllib.parse.unquote(path)

    if Path(decoded).is_absolute() or os.path.isabs(decoded):
        return "PATH_TRAVERSAL", "Absolute paths are not allowed"

    if not decoded.lower().endswith(".md"):
        return "INVALID_NOTE_PATH", "path must end with '.md'"

    normalised = os.path.normpath(decoded.replace("\\", "/"))

    if normalised.startswith(".."):
        return "PATH_TRAVERSAL", "path must not contain traversal sequences"

    vault_resolved = vault_path.resolve()
    candidate = (vault_path / normalised).resolve()
    try:
        rel = candidate.relative_to(vault_resolved)
    except ValueError:
        return "PATH_TRAVERSAL", "Path escapes vault root"

    if rel.parts and rel.parts[0] == "Vault Files":
        return "INVALID_NOTE_PATH", "path must not be inside 'Vault Files/'"

    if must_exist and not candidate.is_file():
        return "NOTE_NOT_FOUND", f"Note does not exist: {rel.as_posix()!r}"

    return None, None


def _normalise_path(path: str) -> str:
    """Return normalised POSIX-style relative path string."""
    decoded = urllib.parse.unquote(path)
    normed = os.path.normpath(decoded.replace("\\", "/"))
    return normed.replace("\\", "/")


def _find_and_replace_section(
    body: str,
    section: str,
    new_section_content: str,
) -> tuple[str | None, str]:
    """Find a section in a markdown body and replace its content.

    Args:
        body: Full body text (without frontmatter).
        section: Section name without '## ' prefix.
        new_section_content: New content for the section body (without header line).

    Returns:
        (error_message_or_None, new_body_string)
    """
    header = f"## {section}"
    lines = body.splitlines(keepends=False)

    start_idx = None
    for i, line in enumerate(lines):
        if line.rstrip() == header:
            start_idx = i
            break

    if start_idx is None:
        return f"Section {section!r} not found in note body", body

    # Find end of this section (next ## header or end of body)
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith("## "):
            end_idx = i
            break

    # Build new section lines: header + new content
    new_content_lines = new_section_content.rstrip("\n").splitlines() if new_section_content else []
    new_section_lines = [header] + new_content_lines

    new_lines = lines[:start_idx] + new_section_lines + lines[end_idx:]
    return None, "\n".join(new_lines)


# ---------------------------------------------------------------------------
# Public path utilities
# ---------------------------------------------------------------------------

def get_pending_root(vault_name: str) -> Path:
    """Return the pending-changes directory path for a vault."""
    from mcp.core.vault_registry import get_vault_path
    vault_path = get_vault_path(vault_name)
    return vault_path / _PENDING_SUBDIR


def get_archive_root(vault_name: str) -> Path:
    """Return the archive directory path for a vault."""
    from mcp.core.vault_registry import get_vault_path
    vault_path = get_vault_path(vault_name)
    return vault_path / _ARCHIVE_SUBDIR


# ---------------------------------------------------------------------------
# Hash and diff utilities
# ---------------------------------------------------------------------------

def compute_content_hash(text: str) -> str:
    """Return SHA-256 hex digest of text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_diff(
    original: str,
    proposed: str,
    fromfile: str = "original",
    tofile: str = "proposed",
) -> list[str]:
    """Build a human-readable unified diff.

    Returns a list of lines (no trailing newlines).  Deterministic for
    identical inputs.
    """
    orig_lines = original.splitlines(keepends=True)
    prop_lines = proposed.splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(
        orig_lines,
        prop_lines,
        fromfile=fromfile,
        tofile=tofile,
        lineterm="",
    ))
    return diff_lines


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def _is_valid_change_id(change_id: str) -> bool:
    return bool(_CHANGE_ID_RE.match(change_id))


def load_pending_change(vault_name: str, change_id: str) -> dict | None:
    """Load a pending change by ID.

    Checks the pending directory first, then the archive.
    Returns None if not found or change_id is invalid.
    """
    if not _is_valid_change_id(change_id):
        return None

    pending_root = get_pending_root(vault_name)
    pending_file = pending_root / f"{change_id}.json"
    if pending_file.is_file():
        try:
            return json.loads(pending_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    archive_root = get_archive_root(vault_name)
    archive_file = archive_root / f"{change_id}.json"
    if archive_file.is_file():
        try:
            return json.loads(archive_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    return None


def write_pending_change(vault_name: str, change: dict) -> None:
    """Write a pending change JSON file atomically to the pending directory."""
    pending_root = get_pending_root(vault_name)
    change_id = change["id"]
    _atomic_write_json(pending_root / f"{change_id}.json", change)


def archive_pending_change(vault_name: str, change: dict) -> None:
    """Move a pending change to the archive directory (atomic write + unlink original)."""
    pending_root = get_pending_root(vault_name)
    archive_root = get_archive_root(vault_name)
    change_id = change["id"]

    _atomic_write_json(archive_root / f"{change_id}.json", change)

    pending_file = pending_root / f"{change_id}.json"
    if pending_file.is_file():
        try:
            pending_file.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Default pending change shape
# ---------------------------------------------------------------------------

def _default_change(
    change_id: str,
    change_type: str,
    vault_name: str,
    norm_path: str,
    section: str | None,
    proposed_content: str,
    reason: str,
    source: str,
    session_id: str | None,
    project: str | None,
    original_content_hash: str | None,
    diff: list[str],
    validation_status: str,
    validation_errors: list[str],
) -> dict:
    now = _utcnow()
    status = "invalid" if validation_errors else "pending"
    return {
        "applied_at": None,
        "audit_note": None,
        "created_at": now,
        "diff": diff,
        "id": change_id,
        "original_content_hash": original_content_hash,
        "path": norm_path,
        "project": project,
        "proposed_content": proposed_content,
        "proposed_content_hash": compute_content_hash(proposed_content) if proposed_content else None,
        "reason": reason,
        "rejected_at": None,
        "reviewer": None,
        "section": section,
        "session_id": session_id,
        "source": source,
        "status": status,
        "type": change_type,
        "updated_at": now,
        "validation_errors": validation_errors,
        "validation_status": validation_status,
        "vault": vault_name,
    }


# ---------------------------------------------------------------------------
# Create / propose operations
# ---------------------------------------------------------------------------

def create_note_draft(
    vault_name: str,
    path: str,
    fields: dict[str, Any],
    body: str,
    reason: str = "",
    source: str = "agent",
    session_id: str | None = None,
    project: str | None = None,
) -> dict:
    """Create a pending draft for a new note.

    The target path must not already exist at propose time.
    The proposal will be marked invalid/fail if schema validation fails,
    but can still be stored for review.
    Accept is blocked until validation passes and the path does not exist.
    """
    try:
        vault_path, schema = _get_vault_and_schema(vault_name)
    except KeyError:
        return _error("INVALID_VAULT", f"Vault not registered: {vault_name!r}")

    code, msg = _check_pending_target_path(vault_path, path, must_exist=False)
    if code:
        return _error(code, msg)

    norm_path = _normalise_path(path)
    full_path = (vault_path / norm_path).resolve()

    if full_path.is_file():
        return _error("NOTE_EXISTS", f"Note already exists: {norm_path!r}")

    if not isinstance(fields, dict):
        return _error("INVALID_PENDING_CHANGE", "fields must be an object")
    if not isinstance(body, str):
        return _error("INVALID_PENDING_CHANGE", "body must be a string")

    from mcp.core.note_write import serialise_note_markdown
    try:
        proposed_content = serialise_note_markdown(fields, body)
    except Exception as exc:
        return _error("INVALID_PENDING_CHANGE", f"Serialisation failed: {exc}")

    diff = build_diff("", proposed_content, fromfile="original (new file)", tofile="proposed")

    validation_errors = _validate_content(proposed_content, norm_path, schema)
    validation_status = "fail" if validation_errors else "pass"

    change_id = _make_change_id()
    change = _default_change(
        change_id=change_id,
        change_type="create_note_draft",
        vault_name=vault_name,
        norm_path=norm_path,
        section=None,
        proposed_content=proposed_content,
        reason=reason,
        source=source,
        session_id=session_id,
        project=project,
        original_content_hash=None,
        diff=diff,
        validation_status=validation_status,
        validation_errors=validation_errors,
    )

    try:
        write_pending_change(vault_name, change)
    except OSError as exc:
        return _error("WRITE_FAILED", f"Failed to write pending change: {exc}")

    logger.info(
        "pending_change_created vault=%s type=create_note_draft id=%s path=%s",
        vault_name, change_id, norm_path,
    )
    return {"status": "ok", "data": {"change": change}}


def suggest_note_update(
    vault_name: str,
    path: str,
    fields: dict[str, Any] | None = None,
    body: str | None = None,
    reason: str = "",
    source: str = "agent",
    session_id: str | None = None,
    project: str | None = None,
) -> dict:
    """Create a pending suggestion to update an existing note.

    ``fields`` and ``body`` are merged with the original note content.
    Pass ``fields=None`` to keep original fields unchanged.
    Pass ``body=None`` to keep original body unchanged.
    """
    try:
        vault_path, schema = _get_vault_and_schema(vault_name)
    except KeyError:
        return _error("INVALID_VAULT", f"Vault not registered: {vault_name!r}")

    code, msg = _check_pending_target_path(vault_path, path, must_exist=True)
    if code:
        return _error(code, msg)

    norm_path = _normalise_path(path)
    full_path = (vault_path / norm_path).resolve()

    try:
        original_content = full_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _error("NOTE_NOT_FOUND", f"Cannot read note: {exc}")

    original_hash = compute_content_hash(original_content)

    try:
        orig_fields, orig_body = schema.parse_yaml_frontmatter(original_content)
    except Exception as exc:
        return _error("INVALID_PENDING_CHANGE", f"Cannot parse original note: {exc}")

    orig_fields = orig_fields or {}
    orig_body = orig_body or ""

    merged_fields = dict(orig_fields)
    if fields is not None:
        merged_fields.update(fields)

    candidate_body = body if body is not None else orig_body

    from mcp.core.note_write import serialise_note_markdown
    try:
        proposed_content = serialise_note_markdown(merged_fields, candidate_body)
    except Exception as exc:
        return _error("INVALID_PENDING_CHANGE", f"Serialisation failed: {exc}")

    diff = build_diff(original_content, proposed_content)

    validation_errors = _validate_content(proposed_content, norm_path, schema)
    validation_status = "fail" if validation_errors else "pass"

    change_id = _make_change_id()
    change = _default_change(
        change_id=change_id,
        change_type="suggest_note_update",
        vault_name=vault_name,
        norm_path=norm_path,
        section=None,
        proposed_content=proposed_content,
        reason=reason,
        source=source,
        session_id=session_id,
        project=project,
        original_content_hash=original_hash,
        diff=diff,
        validation_status=validation_status,
        validation_errors=validation_errors,
    )

    try:
        write_pending_change(vault_name, change)
    except OSError as exc:
        return _error("WRITE_FAILED", f"Failed to write pending change: {exc}")

    logger.info(
        "pending_change_created vault=%s type=suggest_note_update id=%s path=%s",
        vault_name, change_id, norm_path,
    )
    return {"status": "ok", "data": {"change": change}}


def update_note_section_draft(
    vault_name: str,
    path: str,
    section: str,
    proposed_content: str,
    reason: str = "",
    source: str = "agent",
    session_id: str | None = None,
    project: str | None = None,
) -> dict:
    """Create a pending proposal to update one section of an existing note.

    Only the target section is replaced; all other sections are preserved.
    ``proposed_content`` is the new section body (without the '## Header' line).
    The stored ``proposed_content`` in the change record is the full proposed note.
    """
    try:
        vault_path, schema = _get_vault_and_schema(vault_name)
    except KeyError:
        return _error("INVALID_VAULT", f"Vault not registered: {vault_name!r}")

    if not section or not section.strip():
        return _error("INVALID_PENDING_CHANGE", "section must not be empty")

    code, msg = _check_pending_target_path(vault_path, path, must_exist=True)
    if code:
        return _error(code, msg)

    norm_path = _normalise_path(path)
    full_path = (vault_path / norm_path).resolve()

    try:
        original_content = full_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _error("NOTE_NOT_FOUND", f"Cannot read note: {exc}")

    original_hash = compute_content_hash(original_content)

    try:
        orig_fields, orig_body = schema.parse_yaml_frontmatter(original_content)
    except Exception as exc:
        return _error("INVALID_PENDING_CHANGE", f"Cannot parse original note: {exc}")

    orig_fields = orig_fields or {}
    orig_body = orig_body or ""

    # Replace the section in the body
    section_error, new_body = _find_and_replace_section(orig_body, section, proposed_content)

    validation_errors: list[str] = []
    if section_error:
        validation_errors.append(section_error)

    candidate_full: str = ""
    if not section_error:
        from mcp.core.note_write import serialise_note_markdown
        try:
            candidate_full = serialise_note_markdown(orig_fields, new_body)
        except Exception as exc:
            validation_errors.append(f"Serialisation failed: {exc}")

    if not validation_errors and candidate_full:
        schema_errors = _validate_content(candidate_full, norm_path, schema)
        validation_errors.extend(schema_errors)

    validation_status = "fail" if validation_errors else "pass"

    # For the stored proposed_content: use the full candidate (for accept)
    # Fall back to the raw section content only if candidate could not be built
    stored_content = candidate_full if candidate_full else proposed_content
    diff_result = build_diff(original_content, candidate_full) if candidate_full else []

    change_id = _make_change_id()
    change = _default_change(
        change_id=change_id,
        change_type="update_note_section_draft",
        vault_name=vault_name,
        norm_path=norm_path,
        section=section,
        proposed_content=stored_content,
        reason=reason,
        source=source,
        session_id=session_id,
        project=project,
        original_content_hash=original_hash,
        diff=diff_result,
        validation_status=validation_status,
        validation_errors=validation_errors,
    )

    try:
        write_pending_change(vault_name, change)
    except OSError as exc:
        return _error("WRITE_FAILED", f"Failed to write pending change: {exc}")

    logger.info(
        "pending_change_created vault=%s type=update_note_section_draft id=%s path=%s section=%s",
        vault_name, change_id, norm_path, section,
    )
    return {"status": "ok", "data": {"change": change}}


# ---------------------------------------------------------------------------
# List / review operations
# ---------------------------------------------------------------------------

def list_pending_changes(
    vault_name: str,
    status: str | None = "pending",
    limit: int = 50,
) -> dict:
    """List pending changes for a vault.

    Args:
        vault_name: Vault name.
        status: Filter by status (``"pending"``, ``"accepted"``, ``"rejected"``,
            ``"invalid"``).  Pass ``None`` to list all (active and archived).
        limit: Maximum number of results to return (most-recent first).

    Phase 44B: when ``status`` is ``"accepted"``, ``"rejected"``, or ``None``
    (all), records archived under ``pending-changes/archive/`` are included
    in addition to active records under ``pending-changes/``. Each returned
    record is decorated with a transient ``archived`` boolean indicating
    whether it lives in the archive directory. The ``archived`` flag is
    computed at list time and is never persisted to disk.
    """
    try:
        pending_root = get_pending_root(vault_name)
        archive_root = get_archive_root(vault_name)
    except KeyError:
        return _error("INVALID_VAULT", f"Vault not registered: {vault_name!r}")

    include_active = status in (None, "pending", "invalid", "all")
    include_archive = status in (None, "accepted", "rejected", "all")

    changes: list[dict] = []

    if include_active and pending_root.is_dir():
        for f in pending_root.glob("*.json"):
            if f.stem.startswith(".") or not _is_valid_change_id(f.stem):
                continue
            try:
                change = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if status is None or status == "all" or change.get("status") == status:
                change["archived"] = False
                changes.append(change)

    if include_archive and archive_root.is_dir():
        for f in archive_root.glob("*.json"):
            if f.stem.startswith(".") or not _is_valid_change_id(f.stem):
                continue
            try:
                change = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if status is None or status == "all" or change.get("status") == status:
                change["archived"] = True
                changes.append(change)

    # Sort: most-recent first (created_at desc), then id desc for determinism
    changes.sort(key=lambda c: (c.get("created_at", ""), c.get("id", "")), reverse=True)
    changes = changes[:limit]

    return {
        "status": "ok",
        "data": {
            "changes": changes,
            "count": len(changes),
            "status_filter": status,
        },
    }


def _is_archived_on_disk(vault_name: str, change_id: str) -> bool:
    """Return True when the change record currently lives in the archive directory."""
    try:
        archive_root = get_archive_root(vault_name)
    except KeyError:
        return False
    return (archive_root / f"{change_id}.json").is_file()


def review_pending_change(vault_name: str, change_id: str) -> dict:
    """Return the full pending change object (including diff and validation status).

    Checks the pending directory first, then the archive.

    Phase 44B: the returned record is decorated with a transient
    ``archived`` boolean reflecting whether the record currently lives in
    the archive directory. The flag is never persisted.
    """
    if not _is_valid_change_id(change_id):
        return _error(
            "INVALID_PENDING_CHANGE",
            f"change_id format is invalid: {change_id!r}",
        )

    try:
        _get_vault_and_schema(vault_name)  # Validate vault exists
    except KeyError:
        return _error("INVALID_VAULT", f"Vault not registered: {vault_name!r}")

    change = load_pending_change(vault_name, change_id)
    if change is None:
        return _error(
            "PENDING_CHANGE_NOT_FOUND",
            f"Pending change not found: {change_id!r}",
        )

    change["archived"] = _is_archived_on_disk(vault_name, change_id)
    return {"status": "ok", "data": {"change": change}}


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------

def accept_pending_change(
    vault_name: str,
    change_id: str,
    reviewer: str | None = None,
    audit_note: str | None = None,
) -> dict:
    """Accept and apply a pending change.

    Safety guarantees:
    - Only ``pending`` status changes can be accepted.
    - Invalid changes (validation_status=fail) cannot be accepted.
    - Revalidates before writing.
    - For update types: checks original_content_hash against current disk content.
      If the note changed since the proposal, returns STALE_PENDING_CHANGE.
    - For create_note_draft: target path must not exist at accept time.
    - Writes via the existing safe note edit path (update_note) for updates,
      or via atomic write for new-note creation.
    - Accepted changes are archived for audit.
    """
    if not _is_valid_change_id(change_id):
        return _error(
            "INVALID_PENDING_CHANGE",
            f"change_id format is invalid: {change_id!r}",
        )

    try:
        vault_path, schema = _get_vault_and_schema(vault_name)
    except KeyError:
        return _error("INVALID_VAULT", f"Vault not registered: {vault_name!r}")

    change = load_pending_change(vault_name, change_id)
    if change is None:
        return _error(
            "PENDING_CHANGE_NOT_FOUND",
            f"Pending change not found: {change_id!r}",
        )

    if change["status"] != "pending":
        return _error(
            "INVALID_PENDING_CHANGE",
            f"Change cannot be accepted (status={change['status']!r}). "
            "Only 'pending' changes can be accepted.",
        )

    if change.get("validation_status") == "fail":
        return _error(
            "VALIDATION_FAILED",
            "Change has validation errors and cannot be accepted. "
            f"Errors: {'; '.join(change.get('validation_errors', []))}",
        )

    change_type = change["type"]
    norm_path = change["path"]
    full_path = (vault_path / norm_path).resolve()
    now = _utcnow()

    if change_type == "create_note_draft":
        # Target must not exist
        if full_path.is_file():
            change["status"] = "invalid"
            change["validation_status"] = "fail"
            change["validation_errors"] = [f"Target note already exists: {norm_path!r}"]
            change["updated_at"] = now
            try:
                write_pending_change(vault_name, change)
            except OSError:
                pass
            return _error(
                "NOTE_EXISTS",
                f"Target note already exists: {norm_path!r}. Create a new proposal.",
            )

        # Revalidate proposed content
        validation_errors = _validate_content(change["proposed_content"], norm_path, schema)
        if validation_errors:
            change["status"] = "invalid"
            change["validation_status"] = "fail"
            change["validation_errors"] = validation_errors
            change["updated_at"] = now
            try:
                write_pending_change(vault_name, change)
            except OSError:
                pass
            return _error(
                "VALIDATION_FAILED",
                f"Revalidation failed: {'; '.join(validation_errors)}",
            )

        # Atomic write of new file
        note_dir = full_path.parent
        try:
            note_dir.mkdir(parents=True, exist_ok=True)
            tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".tmp", dir=str(note_dir))
            tmp_path = Path(tmp_path_str)
            try:
                os.write(tmp_fd, change["proposed_content"].encode("utf-8"))
            finally:
                os.close(tmp_fd)
            tmp_path.replace(full_path)
        except OSError as exc:
            return _error("WRITE_FAILED", f"Failed to write new note: {exc}")

        # Invalidate caches so next index build picks up the new file
        try:
            from mcp.core.note_write import invalidate_note_caches
            invalidate_note_caches(vault_name)
        except Exception:
            pass

    else:
        # suggest_note_update / update_note_section_draft
        if not full_path.is_file():
            return _error("NOTE_NOT_FOUND", f"Note no longer exists: {norm_path!r}")

        try:
            current_content = full_path.read_text(encoding="utf-8")
        except OSError as exc:
            return _error("NOTE_NOT_FOUND", f"Cannot read note: {exc}")

        current_hash = compute_content_hash(current_content)
        stored_hash = change.get("original_content_hash")

        if stored_hash and current_hash != stored_hash:
            return _error(
                "STALE_PENDING_CHANGE",
                "The note has changed since this proposal was created. "
                "The original content hash does not match the current file. "
                "Create a new proposal.",
            )

        # Revalidate proposed content before writing
        validation_errors = _validate_content(change["proposed_content"], norm_path, schema)
        if validation_errors:
            change["status"] = "invalid"
            change["validation_status"] = "fail"
            change["validation_errors"] = validation_errors
            change["updated_at"] = now
            try:
                write_pending_change(vault_name, change)
            except OSError:
                pass
            return _error(
                "VALIDATION_FAILED",
                f"Revalidation failed: {'; '.join(validation_errors)}",
            )

        # Parse proposed content → fields + body → apply via safe note edit path
        try:
            proposed_fields, proposed_body = schema.parse_yaml_frontmatter(
                change["proposed_content"]
            )
        except Exception as exc:
            return _error(
                "INVALID_PENDING_CHANGE",
                f"Cannot parse proposed content: {exc}",
            )

        from mcp.core.note_write import update_note as _update_note
        result = _update_note(
            vault_name,
            norm_path,
            proposed_fields or {},
            proposed_body or "",
        )
        if result.get("status") == "error":
            return result

    # Mark accepted and archive
    change["status"] = "accepted"
    change["applied_at"] = now
    change["updated_at"] = now
    change["reviewer"] = reviewer
    change["audit_note"] = audit_note
    change["validation_status"] = "pass"
    change["validation_errors"] = []

    try:
        archive_pending_change(vault_name, change)
    except OSError as exc:
        logger.error(
            "pending_change_archive_failed vault=%s id=%s error=%s",
            vault_name, change_id, exc,
        )

    logger.info(
        "pending_change_accepted vault=%s id=%s type=%s path=%s",
        vault_name, change_id, change_type, norm_path,
    )
    return {"status": "ok", "data": {"change": change}}


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------

def reject_pending_change(
    vault_name: str,
    change_id: str,
    reviewer: str | None = None,
    audit_note: str | None = None,
) -> dict:
    """Reject a pending or invalid change and archive it for audit.

    Rejected changes are never deleted — they are retained in the archive.
    """
    if not _is_valid_change_id(change_id):
        return _error(
            "INVALID_PENDING_CHANGE",
            f"change_id format is invalid: {change_id!r}",
        )

    try:
        _get_vault_and_schema(vault_name)  # Validate vault
    except KeyError:
        return _error("INVALID_VAULT", f"Vault not registered: {vault_name!r}")

    change = load_pending_change(vault_name, change_id)
    if change is None:
        return _error(
            "PENDING_CHANGE_NOT_FOUND",
            f"Pending change not found: {change_id!r}",
        )

    if change["status"] not in ("pending", "invalid"):
        return _error(
            "INVALID_PENDING_CHANGE",
            f"Change cannot be rejected (status={change['status']!r}). "
            "Only 'pending' or 'invalid' changes can be rejected.",
        )

    now = _utcnow()
    change["status"] = "rejected"
    change["rejected_at"] = now
    change["updated_at"] = now
    change["reviewer"] = reviewer
    change["audit_note"] = audit_note

    try:
        archive_pending_change(vault_name, change)
    except OSError as exc:
        logger.error(
            "pending_change_archive_failed vault=%s id=%s error=%s",
            vault_name, change_id, exc,
        )
        return _error("WRITE_FAILED", f"Failed to archive rejected change: {exc}")

    logger.info(
        "pending_change_rejected vault=%s id=%s",
        vault_name, change_id,
    )
    return {"status": "ok", "data": {"change": change}}


# ---------------------------------------------------------------------------
# Validate (standalone re-check)
# ---------------------------------------------------------------------------

def validate_pending_change(vault_name: str, change: dict) -> dict:
    """Re-validate a pending change against the current vault schema.

    Returns an updated change dict with fresh ``validation_status`` and
    ``validation_errors``.  Does NOT write to disk.
    """
    try:
        _, schema = _get_vault_and_schema(vault_name)
    except KeyError:
        return dict(change, validation_status="fail", validation_errors=["INVALID_VAULT"])

    norm_path = change.get("path", "")
    proposed_content = change.get("proposed_content", "")

    if not proposed_content:
        return dict(
            change,
            validation_status="fail",
            validation_errors=["No proposed content stored"],
        )

    validation_errors = _validate_content(proposed_content, norm_path, schema)
    validation_status = "fail" if validation_errors else "pass"
    return dict(change, validation_status=validation_status, validation_errors=validation_errors)


# ---------------------------------------------------------------------------
# Revalidate (Phase 44B): public service action
# ---------------------------------------------------------------------------

def revalidate_pending_change(vault_name: str, change_id: str) -> dict:
    """Re-run schema validation for a single pending change.

    Phase 44B safety contract:
    - Never writes to the target vault note.
    - Never accepts the proposal.
    - Does not bypass stale-hash protection at acceptance time.
    - Refuses revalidation for archived (accepted/rejected) records and
      returns a documented ``ARCHIVED_NOT_REVALIDATABLE`` error.
    - Refreshes ``validation_status`` and ``validation_errors`` on the
      persisted pending record.
    - Appends a deterministic entry to ``revalidation_history`` so the
      previous validation state is preserved for audit.
    - Updates ``status`` between ``pending`` and ``invalid`` based on the
      fresh validation result. ``accepted`` and ``rejected`` records are
      never mutated.
    """
    if not _is_valid_change_id(change_id):
        return _error(
            "INVALID_PENDING_CHANGE",
            f"change_id format is invalid: {change_id!r}",
        )

    try:
        _get_vault_and_schema(vault_name)
    except KeyError:
        return _error("INVALID_VAULT", f"Vault not registered: {vault_name!r}")

    change = load_pending_change(vault_name, change_id)
    if change is None:
        return _error(
            "PENDING_CHANGE_NOT_FOUND",
            f"Pending change not found: {change_id!r}",
        )

    current_status = change.get("status")
    if current_status in ("accepted", "rejected"):
        return _error(
            "ARCHIVED_NOT_REVALIDATABLE",
            (
                "Archived records cannot be revalidated. "
                f"Change {change_id!r} has status {current_status!r} and is "
                "retained for audit only."
            ),
        )

    previous_validation_status = change.get("validation_status")
    previous_validation_errors = list(change.get("validation_errors", []))
    previous_status = current_status

    revalidated = validate_pending_change(vault_name, change)
    new_validation_status = revalidated.get("validation_status", "fail")
    new_validation_errors = list(revalidated.get("validation_errors", []))

    now = _utcnow()
    change["validation_status"] = new_validation_status
    change["validation_errors"] = new_validation_errors
    change["validated_at"] = now
    change["updated_at"] = now

    if new_validation_status == "fail":
        change["status"] = "invalid"
    else:
        change["status"] = "pending"

    history = list(change.get("revalidation_history", []))
    history.append({
        "at": now,
        "previous_status": previous_status,
        "previous_validation_status": previous_validation_status,
        "previous_validation_errors": previous_validation_errors,
        "new_status": change["status"],
        "new_validation_status": new_validation_status,
    })
    change["revalidation_history"] = history

    try:
        write_pending_change(vault_name, change)
    except OSError as exc:
        logger.error(
            "pending_change_revalidate_write_failed vault=%s id=%s error=%s",
            vault_name, change_id, exc,
        )
        return _error("WRITE_FAILED", f"Failed to persist revalidated change: {exc}")

    logger.info(
        "pending_change_revalidated vault=%s id=%s previous=%s new=%s",
        vault_name, change_id, previous_validation_status, new_validation_status,
    )

    change["archived"] = False
    return {
        "status": "ok",
        "data": {
            "change": change,
            "revalidated": True,
            "previous_validation_status": previous_validation_status,
            "previous_validation_errors": previous_validation_errors,
            "new_validation_status": new_validation_status,
        },
    }
