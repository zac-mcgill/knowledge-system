"""
Note index — scans each vault once and builds an in-memory index.

Uses the vault's own schema to discover files and parse frontmatter.
Index is built once per process per vault (no file watching).

Hardening:
    - Deterministic sort by path (case-insensitive) after every build
    - Per-vault threading.Lock for concurrency safety
    - Schema hash tracking with auto-refresh on mismatch
    - Schema refresh cooldown (2s) to suppress rebuild spam
    - Index build timeout guard (2s) with fallback to previous index
    - Memory guard: warns if index grows >2x baseline
"""

import hashlib
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path

from core.vault_registry import get_vault_path, get_schema

logger = logging.getLogger("mcp.index")

_SCHEMA_RELATIVE_PATH = Path("Vault Files") / "Scripts" / "vault_schema.py"
_SCHEMA_COOLDOWN_SECONDS = 2.0
_BUILD_TIMEOUT_SECONDS = 2.0

# Per-vault locks for concurrency safety
_locks: dict[str, threading.Lock] = {}
_global_lock = threading.Lock()

# vault_name -> {"index": list[dict], "schema_hash": str,
#                 "last_build_time": float, "last_schema_check": float,
#                 "baseline_size": int}
_indices: dict[str, dict] = {}


def _get_vault_lock(vault_name: str) -> threading.Lock:
    """Get or create a per-vault lock (double-checked locking)."""
    if vault_name not in _locks:
        with _global_lock:
            if vault_name not in _locks:
                _locks[vault_name] = threading.Lock()
    return _locks[vault_name]


def _compute_schema_hash(vault_name: str) -> str:
    """Compute SHA-256 hash of the vault's schema file contents."""
    vault_path = get_vault_path(vault_name)
    schema_file = vault_path / _SCHEMA_RELATIVE_PATH
    content = schema_file.read_bytes()
    return hashlib.sha256(content).hexdigest()


def _estimate_index_size(index: list[dict]) -> int:
    """Rough byte estimate of an index for memory tracking."""
    total = sys.getsizeof(index)
    for note in index:
        total += sys.getsizeof(note)
        total += len(note.get("body", ""))
        for v in note.get("fields", {}).values():
            total += sys.getsizeof(v)
    return total


def _do_build(vault_name: str) -> list[dict]:
    """Actual index build logic (no lock, no timeout wrapping)."""
    vault_path = get_vault_path(vault_name)
    schema = get_schema(vault_name)

    files = schema.discover_files(vault_path)
    index: list[dict] = []

    for filepath in files:
        content = schema.read_file_safe(filepath)
        fields, body = schema.parse_yaml_frontmatter(content)

        rel_path = Path(filepath).relative_to(vault_path).as_posix()

        index.append({
            "path": rel_path,
            "fields": fields if fields is not None else {},
            "body": body,
        })

    # Deterministic sort by path (case-insensitive)
    index.sort(key=lambda n: n["path"].lower())
    return index


def _build_index_internal(vault_name: str, *, timeout: bool = True) -> list[dict]:
    """Build index with timeout guard. Caller must hold the vault lock.

    If build exceeds _BUILD_TIMEOUT_SECONDS and a previous index exists,
    the previous index is kept and a warning is logged.
    """
    now = time.monotonic()
    schema_hash = _compute_schema_hash(vault_name)

    if timeout:
        # Run build in a thread with a timeout
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_do_build, vault_name)
            try:
                index = future.result(timeout=_BUILD_TIMEOUT_SECONDS)
            except FuturesTimeout:
                logger.warning(
                    "index_build_timeout vault=%s timeout_s=%.1f",
                    vault_name, _BUILD_TIMEOUT_SECONDS,
                )
                # Keep previous index if available
                if vault_name in _indices:
                    logger.warning(
                        "index_build_fallback vault=%s keeping_previous=true notes=%d",
                        vault_name, len(_indices[vault_name]["index"]),
                    )
                    return list(_indices[vault_name]["index"])
                raise RuntimeError(
                    f"Index build for {vault_name!r} timed out with no fallback"
                )
            except Exception:
                if vault_name in _indices:
                    logger.exception(
                        "index_build_error vault=%s keeping_previous=true", vault_name,
                    )
                    return list(_indices[vault_name]["index"])
                raise
    else:
        index = _do_build(vault_name)

    # Memory guard: check for unexpected growth
    current_size = _estimate_index_size(index)
    prev = _indices.get(vault_name)
    baseline = prev["baseline_size"] if prev and "baseline_size" in prev else current_size

    if prev and current_size > 2 * baseline:
        logger.warning(
            "memory_guard vault=%s current_bytes=%d baseline_bytes=%d ratio=%.1f",
            vault_name, current_size, baseline, current_size / baseline,
        )

    # Atomic swap into cache
    _indices[vault_name] = {
        "index": index,
        "schema_hash": schema_hash,
        "last_build_time": now,
        "last_schema_check": now,
        "baseline_size": baseline,
        "index_size_bytes": current_size,
    }

    logger.info(
        "index_built vault=%s notes=%d schema_hash=%s size_bytes=%d duration_ms=%.0f",
        vault_name, len(index), schema_hash[:16],
        current_size, (time.monotonic() - now) * 1000,
    )

    return index


def build_index(vault_name: str) -> list[dict]:
    """Scan a vault and build its note index (thread-safe, atomic swap).

    Each entry:
        {
            "path": str,       # relative to vault root
            "fields": dict,    # parsed YAML frontmatter
            "body": str        # markdown body after frontmatter
        }

    Returns:
        The built index (also cached internally).
    """
    lock = _get_vault_lock(vault_name)
    with lock:
        return _build_index_internal(vault_name, timeout=False)


def refresh_index(vault_name: str) -> list[dict]:
    """Force rebuild of a vault's index (thread-safe, with timeout guard)."""
    lock = _get_vault_lock(vault_name)
    with lock:
        return _build_index_internal(vault_name, timeout=True)


def get_index(vault_name: str) -> list[dict]:
    """Return the cached index for a vault, building it if necessary.

    Auto-refreshes if the schema file has changed since last build,
    subject to a cooldown window to prevent rebuild spam.
    Returns a shallow copy to prevent external mutation of the cache.
    """
    lock = _get_vault_lock(vault_name)
    with lock:
        now = time.monotonic()

        if vault_name in _indices:
            entry = _indices[vault_name]
            last_check = entry.get("last_schema_check", 0.0)

            # Cooldown: skip schema check if checked recently
            if (now - last_check) < _SCHEMA_COOLDOWN_SECONDS:
                return list(entry["index"])

            # Check schema hash
            current_hash = _compute_schema_hash(vault_name)
            entry["last_schema_check"] = now

            if entry["schema_hash"] == current_hash:
                return list(entry["index"])

            # Schema changed — rebuild with timeout guard
            logger.info(
                "schema_mismatch vault=%s old_hash=%s new_hash=%s",
                vault_name, entry["schema_hash"][:16], current_hash[:16],
            )
            _build_index_internal(vault_name, timeout=True)
            return list(_indices[vault_name]["index"])

        # First build — no timeout (must succeed)
        _build_index_internal(vault_name, timeout=False)
        return list(_indices[vault_name]["index"])


def get_schema_hash(vault_name: str) -> str | None:
    """Return the stored schema hash for a vault, or None if not indexed."""
    lock = _get_vault_lock(vault_name)
    with lock:
        entry = _indices.get(vault_name)
        return entry["schema_hash"] if entry else None


def get_index_metadata(vault_name: str) -> dict | None:
    """Return metadata for a vault's index (for health endpoint)."""
    lock = _get_vault_lock(vault_name)
    with lock:
        entry = _indices.get(vault_name)
        if not entry:
            return None
        return {
            "notes": len(entry["index"]),
            "schema_hash": entry["schema_hash"],
            "last_build_time": entry.get("last_build_time", 0.0),
            "last_schema_check": entry.get("last_schema_check", 0.0),
            "index_size_bytes": entry.get("index_size_bytes", 0),
            "baseline_size_bytes": entry.get("baseline_size", 0),
        }
