"""Session and Project State Layer — Phase 22.

Provides deterministic, file-backed, human-readable session and project
state for the Context Vault Engine.  All state is stored as pretty-printed
JSON with sorted keys inside the vault's ``Vault Files/State/`` directory.

Storage layout::

    <vault>/Vault Files/State/
        sessions/
            <session_id>.json
        project-state.json

Session IDs are ``<yyyymmddTHHMMSS>-<8-hex>`` (UTC timestamp + 4 random bytes),
generated with ``datetime`` + ``secrets``/``os.urandom``.  They are always
filesystem-safe.

Design constraints:
- Python standard library only (no third-party dependencies).
- Atomic writes via temp-file + ``Path.replace()``.
- All list fields are normalised to lists of strings.
- No secrets, auth tokens, or vault content are stored.
- Write operations respect vault boundaries; path traversal is rejected.
- This module does NOT enforce private-cloud read-only — that is the
  responsibility of callers (HTTP endpoints, MCP tools).
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

logger = logging.getLogger("mcp.session_state")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STATE_SUBDIR = Path("Vault Files") / "State"
_SESSIONS_SUBDIR = _STATE_SUBDIR / "sessions"
_PROJECT_STATE_FILE = _STATE_SUBDIR / "project-state.json"

# Allowed fields for project state updates — unknown fields are rejected.
_ALLOWED_PROJECT_FIELDS: frozenset[str] = frozenset({
    "current_phase",
    "completed_work",
    "next_actions",
    "blockers",
    "decisions",
    "risks",
})

# Session ID pattern: yyyymmddTHHMMSS-<8 hex chars>
_SESSION_ID_RE = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{8}$")

# Maximum recent_notes / recent_bundle_ids stored per session.
_MAX_RECENT_NOTES = 50
_MAX_RECENT_BUNDLE_IDS = 20


# ---------------------------------------------------------------------------
# Session / project-state default shapes
# ---------------------------------------------------------------------------

def _default_session(session_id: str, vault_name: str) -> dict:
    now = _utcnow()
    return {
        "active_vault": vault_name,
        "closed_at": None,
        "created_at": now,
        "current_project": None,
        "current_topic": None,
        "last_activity": now,
        "open_tasks": [],
        "recent_bundle_ids": [],
        "recent_notes": [],
        "session_id": session_id,
        "status": "active",
        "summary": None,
        "user_goal": None,
    }


def _default_project_state(vault_name: str) -> dict:
    return {
        "blockers": [],
        "completed_work": [],
        "current_phase": None,
        "decisions": [],
        "next_actions": [],
        "risks": [],
        "updated_at": _utcnow(),
        "vault": vault_name,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    """Return current UTC time as an ISO-8601 string (no microseconds)."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_session_id() -> str:
    """Generate a filesystem-safe, human-readable session ID."""
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    rand_hex = os.urandom(4).hex()
    return f"{ts}-{rand_hex}"


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write *data* as pretty-printed JSON to *path* atomically.

    Uses a sibling temp file in the same directory so that ``replace()`` is
    always on the same filesystem.  Keys are sorted for determinism.
    """
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


def _load_json_file(path: Path) -> dict | None:
    """Load JSON from *path*.  Returns None if file does not exist."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("session_state_load_error path=%s error=%s", path, exc)
        return None


def _normalise_list(value: Any) -> list[str]:
    """Ensure *value* is a list of strings; return empty list on None/invalid."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _slugify_session_id(candidate: str) -> str | None:
    """Return *candidate* if it matches the expected session ID pattern.

    Returns None if the candidate is invalid (path traversal guard).
    """
    candidate = candidate.strip()
    if _SESSION_ID_RE.match(candidate):
        return candidate
    return None


# ---------------------------------------------------------------------------
# Public API — path resolution
# ---------------------------------------------------------------------------

def get_state_root(vault_name: str, _vault_path: Path | None = None) -> Path:
    """Return the State directory path for *vault_name*.

    If *_vault_path* is provided it is used directly (intended for tests).
    Otherwise the vault path is resolved from the registered vault registry.

    Does not create the directory.
    """
    if _vault_path is not None:
        vault_path = _vault_path
    else:
        from mcp.core.vault_registry import get_vault_path  # noqa: PLC0415
        vault_path = get_vault_path(vault_name)
    return vault_path / _STATE_SUBDIR


def _session_path(state_root: Path, session_id: str) -> Path:
    return state_root / "sessions" / f"{session_id}.json"


def _project_state_path(state_root: Path) -> Path:
    return state_root / "project-state.json"


# ---------------------------------------------------------------------------
# Public API — session operations
# ---------------------------------------------------------------------------

def start_session(
    vault_name: str,
    *,
    current_project: str | None = None,
    current_topic: str | None = None,
    user_goal: str | None = None,
    active_vault: str | None = None,
    _vault_path: Path | None = None,
) -> dict:
    """Create and persist a new active session.

    Returns the new session record as a dict.
    Raises ``KeyError`` if *vault_name* is not registered.
    Raises ``OSError`` on write failure.
    """
    state_root = get_state_root(vault_name, _vault_path)
    sessions_dir = state_root / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    session_id = _make_session_id()
    session = _default_session(session_id, active_vault or vault_name)

    if current_project is not None:
        session["current_project"] = str(current_project)[:200]
    if current_topic is not None:
        session["current_topic"] = str(current_topic)[:200]
    if user_goal is not None:
        session["user_goal"] = str(user_goal)[:1000]

    path = _session_path(state_root, session_id)
    _atomic_write_json(path, session)
    logger.info(
        "session_started vault=%s session_id=%s", vault_name, session_id
    )
    return {"status": "ok", "session": dict(session)}


def resume_session(
    vault_name: str,
    session_id: str | None = None,
    _vault_path: Path | None = None,
) -> dict:
    """Return the most recent active session or a session by explicit ID.

    If *session_id* is None, returns the most recently created active session.
    Returns ``{"status": "error", ...}`` if no session is found.
    """
    state_root = get_state_root(vault_name, _vault_path)
    sessions_dir = state_root / "sessions"

    if session_id is not None:
        clean_id = _slugify_session_id(session_id)
        if clean_id is None:
            return _state_error("INVALID_SESSION", f"Invalid session ID format: {session_id!r}")
        path = _session_path(state_root, clean_id)
        data = _load_json_file(path)
        if data is None:
            return _state_error("SESSION_NOT_FOUND", f"Session not found: {clean_id!r}")
        return {"status": "ok", "session": data}

    # No ID: find most recently created active session
    if not sessions_dir.is_dir():
        return _state_error("SESSION_NOT_FOUND", "No sessions found for this vault")

    candidates = []
    for f in sessions_dir.glob("*.json"):
        data = _load_json_file(f)
        if data and data.get("status") == "active":
            candidates.append(data)

    if not candidates:
        return _state_error("SESSION_NOT_FOUND", "No active sessions found for this vault")

    # Sort by created_at descending then by session_id descending (deterministic tiebreak)
    candidates.sort(key=lambda s: (s.get("created_at", ""), s.get("session_id", "")), reverse=True)
    return {"status": "ok", "session": candidates[0]}


def summarise_session(
    vault_name: str,
    session_id: str | None = None,
    _vault_path: Path | None = None,
) -> dict:
    """Return a compact, deterministic summary of a session.

    Suitable for inclusion in local LLM context.  If *session_id* is None,
    uses the most recently active session.
    """
    result = resume_session(vault_name, session_id=session_id, _vault_path=_vault_path)
    if result.get("status") == "error":
        return result

    session = result["session"]
    summary = {
        "active_vault": session.get("active_vault"),
        "closed_at": session.get("closed_at"),
        "created_at": session.get("created_at"),
        "current_project": session.get("current_project"),
        "current_topic": session.get("current_topic"),
        "last_activity": session.get("last_activity"),
        "open_tasks_count": len(_normalise_list(session.get("open_tasks"))),
        "recent_notes": _normalise_list(session.get("recent_notes"))[:5],
        "session_id": session.get("session_id"),
        "status": session.get("status"),
        "user_goal": session.get("user_goal"),
    }
    return {"status": "ok", "summary": summary}


def attach_note_to_session(
    vault_name: str,
    session_id: str,
    note_path: str,
    _vault_path: Path | None = None,
) -> dict:
    """Attach a vault note to the session's recent_notes list.

    *note_path* must be a vault-relative POSIX path.  The function validates:
    - Path does not traverse outside the vault.
    - Note file exists in the vault.

    Returns the updated session record.
    """
    # Validate session ID format
    clean_id = _slugify_session_id(session_id)
    if clean_id is None:
        return _state_error("INVALID_SESSION", f"Invalid session ID format: {session_id!r}")

    state_root = get_state_root(vault_name, _vault_path)

    # Load session
    path = _session_path(state_root, clean_id)
    session = _load_json_file(path)
    if session is None:
        return _state_error("SESSION_NOT_FOUND", f"Session not found: {clean_id!r}")

    # Validate note_path
    if not note_path or not isinstance(note_path, str):
        return _state_error("INVALID_NOTE_PATH", "note_path must be a non-empty string")

    # Resolve vault path for traversal check
    if _vault_path is not None:
        vault_base = _vault_path
    else:
        try:
            from mcp.core.vault_registry import get_vault_path  # noqa: PLC0415
            vault_base = get_vault_path(vault_name)
        except KeyError:
            return _state_error("INVALID_VAULT", f"Vault not registered: {vault_name!r}")

    # Path traversal check
    note_path_stripped = note_path.strip()
    try:
        candidate = (vault_base / note_path_stripped).resolve()
        vault_resolved = vault_base.resolve()
        candidate.relative_to(vault_resolved)
    except (ValueError, OSError):
        return _state_error("INVALID_NOTE_PATH", f"Path traversal rejected: {note_path!r}")

    # Note existence check
    if not candidate.is_file():
        return _state_error("NOTE_NOT_FOUND", f"Note does not exist: {note_path!r}")

    # Normalise to POSIX relative path
    posix_path = candidate.relative_to(vault_base.resolve()).as_posix()

    # De-duplicate and prepend (most-recent-first)
    recent = _normalise_list(session.get("recent_notes"))
    if posix_path in recent:
        recent.remove(posix_path)
    recent.insert(0, posix_path)
    recent = recent[:_MAX_RECENT_NOTES]

    session["recent_notes"] = recent
    session["last_activity"] = _utcnow()

    _atomic_write_json(path, session)
    logger.info(
        "note_attached vault=%s session_id=%s path=%s",
        vault_name, clean_id, posix_path,
    )
    return {"status": "ok", "session": session}


def close_session(
    vault_name: str,
    session_id: str,
    _vault_path: Path | None = None,
) -> dict:
    """Mark a session as closed.  Does not delete the file."""
    clean_id = _slugify_session_id(session_id)
    if clean_id is None:
        return _state_error("INVALID_SESSION", f"Invalid session ID format: {session_id!r}")

    state_root = get_state_root(vault_name, _vault_path)
    path = _session_path(state_root, clean_id)
    session = _load_json_file(path)
    if session is None:
        return _state_error("SESSION_NOT_FOUND", f"Session not found: {clean_id!r}")

    session["status"] = "closed"
    session["closed_at"] = _utcnow()
    session["last_activity"] = session["closed_at"]

    _atomic_write_json(path, session)
    logger.info("session_closed vault=%s session_id=%s", vault_name, clean_id)
    return {"status": "ok", "session": session}


def list_sessions(
    vault_name: str,
    limit: int = 20,
    _vault_path: Path | None = None,
) -> dict:
    """Return a list of sessions sorted most-recently-created first."""
    state_root = get_state_root(vault_name, _vault_path)
    sessions_dir = state_root / "sessions"

    if not sessions_dir.is_dir():
        return {"status": "ok", "sessions": [], "count": 0}

    sessions = []
    for f in sessions_dir.glob("*.json"):
        data = _load_json_file(f)
        if data:
            sessions.append(data)

    sessions.sort(key=lambda s: (s.get("created_at", ""), s.get("session_id", "")), reverse=True)
    sessions = sessions[:limit]
    return {"status": "ok", "sessions": sessions, "count": len(sessions)}


# ---------------------------------------------------------------------------
# Public API — project state operations
# ---------------------------------------------------------------------------

def get_project_state(
    vault_name: str,
    _vault_path: Path | None = None,
) -> dict:
    """Return project state, creating a default if none exists."""
    state_root = get_state_root(vault_name, _vault_path)
    path = _project_state_path(state_root)
    data = _load_json_file(path)
    if data is None:
        return {"status": "ok", "project_state": _default_project_state(vault_name)}
    return {"status": "ok", "project_state": data}


def update_project_state(
    vault_name: str,
    updates: dict,
    _vault_path: Path | None = None,
) -> dict:
    """Merge *updates* into the project state, writing atomically.

    Only fields in ``_ALLOWED_PROJECT_FIELDS`` are accepted.  Unknown fields
    cause the entire update to be rejected with ``INVALID_PROJECT_STATE``.

    List fields (completed_work, next_actions, blockers, decisions, risks)
    are normalised to lists of strings.

    Returns the updated project state.
    """
    if not isinstance(updates, dict):
        return _state_error("INVALID_PROJECT_STATE", "updates must be a dict")

    unknown = set(updates.keys()) - _ALLOWED_PROJECT_FIELDS
    if unknown:
        return _state_error(
            "INVALID_PROJECT_STATE",
            f"Unknown project state field(s): {sorted(unknown)}. "
            f"Allowed: {sorted(_ALLOWED_PROJECT_FIELDS)}",
        )

    state_root = get_state_root(vault_name, _vault_path)
    path = _project_state_path(state_root)
    existing = _load_json_file(path) or _default_project_state(vault_name)

    _LIST_FIELDS = frozenset({
        "completed_work", "next_actions", "blockers", "decisions", "risks"
    })

    for field, value in updates.items():
        if field in _LIST_FIELDS:
            existing[field] = _normalise_list(value)
        else:
            # current_phase: string or None
            existing[field] = str(value)[:500] if value is not None else None

    existing["updated_at"] = _utcnow()
    existing.setdefault("vault", vault_name)

    _atomic_write_json(path, existing)
    logger.info("project_state_updated vault=%s fields=%s", vault_name, sorted(updates.keys()))
    return {"status": "ok", "project_state": existing}


# ---------------------------------------------------------------------------
# Internal error helper
# ---------------------------------------------------------------------------

def _state_error(code: str, message: str) -> dict:
    return {"status": "error", "error": {"code": code, "message": message}}
