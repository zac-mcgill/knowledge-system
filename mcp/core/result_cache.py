"""
Result cache — per-vault, per-endpoint in-memory cache.

Invalidation triggers:
    - Schema file changes (SHA-256 of schema bytes, same mechanism as note_index.py)
    - Any vault .md file changes (fingerprint of sorted path+mtime_ns+size tuples)

Thread-safe.  Only successful, complete results are cached.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path

from mcp.core.vault_registry import get_vault_path

logger = logging.getLogger("mcp.result_cache")

_SCHEMA_RELATIVE_PATH = Path("Vault Files") / "Scripts" / "vault_schema.py"

_lock = threading.Lock()

# (vault_name, endpoint) -> {
#     "result":           dict,
#     "schema_hash":      str,
#     "vault_fingerprint": str,
# }
_cache: dict[tuple[str, str], dict] = {}


# ---------- Fingerprint helpers ----------

def _schema_hash(vault_name: str) -> str:
    """SHA-256 of the vault schema file bytes (replicates note_index strategy)."""
    schema_file = get_vault_path(vault_name) / _SCHEMA_RELATIVE_PATH
    return hashlib.sha256(schema_file.read_bytes()).hexdigest()


def _vault_fingerprint(vault_name: str) -> str:
    """Cheap fingerprint of all .md files: sorted (path, mtime_ns, size) — no content reads."""
    vault_path = get_vault_path(vault_name)
    parts: list[str] = []
    for p in sorted(vault_path.rglob("*.md"), key=lambda x: x.as_posix().lower()):
        st = p.stat()
        parts.append(
            f"{p.relative_to(vault_path).as_posix()}:{st.st_mtime_ns}:{st.st_size}"
        )
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


# ---------- Public API ----------

def get_cached(vault_name: str, endpoint: str) -> dict | None:
    """Return cached result if schema and vault content are unchanged, else None.

    Fast-path: quick existence check under lock, then cheap I/O fingerprint
    verification outside lock, then final validation under lock.
    """
    # Fast check: does an entry exist?
    with _lock:
        if (vault_name, endpoint) not in _cache:
            return None

    # Compute fingerprints outside the lock (I/O, but much cheaper than recomputation)
    try:
        current_schema = _schema_hash(vault_name)
        current_vault = _vault_fingerprint(vault_name)
    except Exception as exc:
        logger.debug("cache_fingerprint_error vault=%s endpoint=%s error=%s", vault_name, endpoint, exc)
        return None

    # Validate entry under lock
    with _lock:
        entry = _cache.get((vault_name, endpoint))
        if entry is None:
            return None
        if (
            entry["schema_hash"] == current_schema
            and entry["vault_fingerprint"] == current_vault
        ):
            logger.debug("cache_hit vault=%s endpoint=%s", vault_name, endpoint)
            return entry["result"]

        # Entry is stale — evict
        del _cache[(vault_name, endpoint)]
        logger.debug("cache_invalidated vault=%s endpoint=%s", vault_name, endpoint)
        return None


def set_cached(vault_name: str, endpoint: str, result: dict) -> None:
    """Store a successful, complete result with current fingerprints.

    Does nothing if fingerprinting fails (no partial/error results cached).
    """
    try:
        schema = _schema_hash(vault_name)
        vault_fp = _vault_fingerprint(vault_name)
    except Exception as exc:
        logger.debug("cache_store_skip vault=%s endpoint=%s error=%s", vault_name, endpoint, exc)
        return

    with _lock:
        _cache[(vault_name, endpoint)] = {
            "result": result,
            "schema_hash": schema,
            "vault_fingerprint": vault_fp,
        }
    logger.debug("cache_stored vault=%s endpoint=%s", vault_name, endpoint)


def clear_vault_cache(vault_name: str) -> int:
    """Evict all cached entries for vault_name.

    Safe to call at any time — does nothing if the vault has no entries.

    Returns
    -------
    int
        Number of cache entries removed.
    """
    with _lock:
        keys = [k for k in _cache if k[0] == vault_name]
        for k in keys:
            del _cache[k]
    if keys:
        logger.info("cache_cleared vault=%s entries_removed=%d", vault_name, len(keys))
    return len(keys)
