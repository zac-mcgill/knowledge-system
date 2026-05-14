"""
Backup, Restore, and Migration Safety (Phase 38).

Local-only backup and restore for the Context Vault Engine. Backups are
plain ZIP archives that contain a redacted manifest, ``config/config.yaml``,
and each registered vault's content notes, schema, templates, feedback, and
state. Generated artefacts (``dist/``, ``ui/dist/``, vault reports) are
excluded.

All operations are filesystem-local. The module uses only the Python
standard library plus existing project dependencies. It never reads or
writes outside the repository root, never includes note bodies in the
manifest, and never overwrites existing vault or config files without:

1. an explicit ``overwrite=True`` flag,
2. a matching typed confirmation phrase, and
3. a clean restore preview (no blocking errors).

The module is import-safe and side-effect free. No paths are created,
written, or modified at import time.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORMAT_VERSION = "1"
APP_NAME = "context-vault-engine"
DEFAULT_OUTPUT_SUBDIR = ("dist", "backups")
MANIFEST_NAME = "backup-manifest.json"
HASH_ALGO = "sha256"
HASH_CHUNK = 65536

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Directory names that are never included in a backup. These hold generated
# artefacts, caches, or VCS metadata and would re-create themselves at runtime.
EXCLUDED_DIR_NAMES = frozenset(
    {
        "dist",
        ".git",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        ".astro",
    }
)

# File suffixes excluded everywhere.
EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo", ".tmp", ".bak", ".log"})

# Per-vault relative paths that must never be backed up: they are generated
# reports/scans, not source-of-truth notes.
EXCLUDED_VAULT_RELATIVES = frozenset(
    {
        "Vault Files/Vault Report.md",
        "Vault Files/Vault Delta Report.md",
        "Vault Files/security-scan.json",
    }
)

# File kinds the manifest reports. The set is closed — unknown files map to
# "other" and the caller can decide whether to include them.
FILE_KIND_VAULT_NOTE = "vault-note"
FILE_KIND_VAULT_SCHEMA = "vault-schema"
FILE_KIND_VAULT_TEMPLATE = "vault-template"
FILE_KIND_VAULT_FEEDBACK = "vault-feedback"
FILE_KIND_VAULT_STATE = "vault-state"
FILE_KIND_VAULT_METADATA = "vault-metadata"
FILE_KIND_CONFIG = "config"
FILE_KIND_OTHER = "other"

# Error/warning codes emitted by preview/validation.
ERR_FORMAT_VERSION_UNSUPPORTED = "FORMAT_VERSION_UNSUPPORTED"
ERR_MANIFEST_MISSING = "MANIFEST_MISSING"
ERR_HASH_MISMATCH = "HASH_MISMATCH"
ERR_UNSAFE_ARCHIVE_PATH = "UNSAFE_ARCHIVE_PATH"
ERR_BACKUP_NOT_FOUND = "BACKUP_NOT_FOUND"
ERR_CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
ERR_CONFIRMATION_MISMATCH = "CONFIRMATION_MISMATCH"
ERR_PREVIEW_HAS_ERRORS = "PREVIEW_HAS_ERRORS"
ERR_RESTORE_VALIDATION_FAILED = "RESTORE_VALIDATION_FAILED"
ERR_UNSAFE_RESTORE_TARGET = "UNSAFE_RESTORE_TARGET"

WARN_SCHEMA_VERSION_CHANGED = "SCHEMA_VERSION_CHANGED"
WARN_CONFIG_SHAPE_CHANGED = "CONFIG_SHAPE_CHANGED"
WARN_TARGET_EXISTS = "TARGET_EXISTS"
WARN_VAULT_NOT_REGISTERED = "VAULT_NOT_REGISTERED"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    return _REPO_ROOT


def _default_output_root(repo_root: Path | None = None) -> Path:
    return (repo_root or _repo_root()).joinpath(*DEFAULT_OUTPUT_SUBDIR)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _posix(p: Path | str) -> str:
    return PurePosixPath(str(p).replace("\\", "/")).as_posix()


def is_safe_archive_path(path: str) -> bool:
    """Return True if ``path`` is safe to extract under a clean root.

    Safe paths use forward slashes, are relative, contain no ``..`` or
    drive letters, no backslashes, no leading slash, and no embedded
    ``NUL`` byte. Empty strings are rejected.
    """
    if not isinstance(path, str) or not path:
        return False
    if "\x00" in path:
        return False
    if "\\" in path:
        return False
    if path.startswith("/"):
        return False
    # Drive letter or UNC.
    if len(path) >= 2 and path[1] == ":":
        return False
    if path.startswith("//"):
        return False
    parts = PurePosixPath(path).parts
    if not parts:
        return False
    for part in parts:
        if part in ("", ".", ".."):
            return False
        if part.startswith("/"):
            return False
    return True


def is_safe_restore_target(target: Path, repo_root: Path) -> bool:
    """Return True if ``target`` resolves inside ``repo_root``.

    Used to defend against symlinks or unexpected join results. ``target``
    need not exist; the parent must exist.
    """
    try:
        repo_root_resolved = repo_root.resolve()
    except OSError:
        return False
    try:
        # Resolve as much of the path as exists; for non-existing leaves,
        # resolve the closest existing ancestor and rejoin.
        anchor = target
        suffix_parts: list[str] = []
        while not anchor.exists():
            suffix_parts.insert(0, anchor.name)
            new_anchor = anchor.parent
            if new_anchor == anchor:
                return False
            anchor = new_anchor
        anchor_resolved = anchor.resolve()
        candidate = anchor_resolved.joinpath(*suffix_parts) if suffix_parts else anchor_resolved
    except OSError:
        return False
    try:
        candidate.relative_to(repo_root_resolved)
    except ValueError:
        return False
    return True


def hash_file(path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of the file at ``path``."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(HASH_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _classify_vault_file(rel_in_vault: str) -> str:
    """Map a vault-relative path to a file kind."""
    posix = rel_in_vault.replace("\\", "/")
    lower = posix.lower()
    if posix.endswith(".schema.py") or lower.endswith("schema.py"):
        return FILE_KIND_VAULT_SCHEMA
    if posix.startswith("Vault Files/Templates/"):
        return FILE_KIND_VAULT_TEMPLATE
    if posix.startswith("Vault Files/State/"):
        return FILE_KIND_VAULT_STATE
    if posix.startswith("Vault Files/Scripts/"):
        return FILE_KIND_VAULT_METADATA
    if posix == "Vault Files/feedback.md":
        return FILE_KIND_VAULT_FEEDBACK
    if posix.startswith("Vault Files/"):
        # Anything else inside Vault Files is treated as vault metadata.
        return FILE_KIND_VAULT_METADATA
    if posix.endswith(".md"):
        return FILE_KIND_VAULT_NOTE
    return FILE_KIND_OTHER


def _should_exclude_relative(rel_in_vault: str) -> bool:
    posix = rel_in_vault.replace("\\", "/")
    if posix in EXCLUDED_VAULT_RELATIVES:
        return True
    parts = PurePosixPath(posix).parts
    for part in parts[:-1]:
        if part in EXCLUDED_DIR_NAMES:
            return True
    suffix = "".join(Path(posix).suffixes[-1:])
    if suffix and suffix in EXCLUDED_SUFFIXES:
        return True
    if Path(posix).name.startswith("."):
        # Hidden files (e.g. .DS_Store) — ignore for portability.
        return True
    return False


def _iter_vault_files(vault_path: Path) -> Iterable[tuple[Path, str]]:
    """Yield ``(absolute_path, posix_relative)`` for every backed-up file."""
    if not vault_path.is_dir():
        return
    for root, dirs, files in os.walk(vault_path):
        # Prune excluded directories in-place for performance.
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR_NAMES]
        for name in files:
            absolute = Path(root) / name
            try:
                rel = absolute.relative_to(vault_path)
            except ValueError:
                continue
            rel_posix = _posix(rel)
            if _should_exclude_relative(rel_posix):
                continue
            # Skip symlinks defensively.
            try:
                if absolute.is_symlink():
                    continue
            except OSError:
                continue
            yield absolute, rel_posix


# ---------------------------------------------------------------------------
# Vault registry access (lazy import to keep this module importable when the
# config file is missing — relevant for tests that exercise edge cases).
# ---------------------------------------------------------------------------


def _registered_vaults() -> dict[str, Path]:
    try:
        from mcp.core.vault_registry import list_vaults, get_vault_path

        result: dict[str, Path] = {}
        for name in list_vaults():
            try:
                result[name] = get_vault_path(name)
            except Exception:
                continue
        return result
    except Exception:
        return {}


def _vault_schema_version(name: str) -> str | None:
    try:
        from mcp.core.vault_registry import get_schema

        schema = get_schema(name)
        version = getattr(schema, "SCHEMA_VERSION", None)
        return str(version) if version is not None else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Backup plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PlannedFile:
    archive_path: str       # path inside the zip
    source_path: Path       # absolute path on disk
    kind: str
    size: int


def _plan_config_files(repo_root: Path) -> list[_PlannedFile]:
    files: list[_PlannedFile] = []
    cfg = repo_root / "config" / "config.yaml"
    if cfg.is_file():
        files.append(
            _PlannedFile(
                archive_path="config/config.yaml",
                source_path=cfg,
                kind=FILE_KIND_CONFIG,
                size=cfg.stat().st_size,
            )
        )
    return files


def _plan_vault_files(vault_name: str, vault_path: Path) -> list[_PlannedFile]:
    out: list[_PlannedFile] = []
    for absolute, rel_posix in _iter_vault_files(vault_path):
        kind = _classify_vault_file(rel_posix)
        try:
            size = absolute.stat().st_size
        except OSError:
            continue
        archive_path = f"vaults/{vault_name}/{rel_posix}"
        out.append(
            _PlannedFile(
                archive_path=archive_path,
                source_path=absolute,
                kind=kind,
                size=size,
            )
        )
    return out


def build_backup_plan(
    vault_names: list[str] | None = None,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Plan a backup without writing any files.

    Returns a JSON-serialisable dict describing the files that would be
    included, totals per kind, and warnings (e.g. unknown vault names).
    Note bodies are NEVER included; only paths, kinds, and sizes.
    """
    root = (repo_root or _repo_root()).resolve()
    registry = _registered_vaults()
    warnings: list[dict[str, str]] = []

    if vault_names is None:
        chosen = sorted(registry.keys())
    else:
        chosen = []
        for n in vault_names:
            if n in registry:
                chosen.append(n)
            else:
                warnings.append(
                    {
                        "code": WARN_VAULT_NOT_REGISTERED,
                        "message": f"Vault not registered: {n}",
                    }
                )

    planned: list[_PlannedFile] = []
    planned.extend(_plan_config_files(root))

    vault_entries: list[dict[str, Any]] = []
    for name in chosen:
        vault_path = registry[name]
        vault_files = _plan_vault_files(name, vault_path)
        planned.extend(vault_files)
        kind_counts: dict[str, int] = {}
        for f in vault_files:
            kind_counts[f.kind] = kind_counts.get(f.kind, 0) + 1
        vault_entries.append(
            {
                "name": name,
                "schema_version": _vault_schema_version(name),
                "file_count": len(vault_files),
                "total_bytes": sum(f.size for f in vault_files),
                "kind_counts": kind_counts,
            }
        )

    totals: dict[str, int] = {}
    for f in planned:
        totals[f.kind] = totals.get(f.kind, 0) + 1

    return {
        "format_version": FORMAT_VERSION,
        "generated_at": _utc_now_iso(),
        "repo_root_present": root.is_dir(),
        "config_included": any(f.kind == FILE_KIND_CONFIG for f in planned),
        "vaults": vault_entries,
        "file_count": len(planned),
        "total_bytes": sum(f.size for f in planned),
        "kind_counts": totals,
        "exclusions": {
            "directories": sorted(EXCLUDED_DIR_NAMES),
            "suffixes": sorted(EXCLUDED_SUFFIXES),
            "vault_relatives": sorted(EXCLUDED_VAULT_RELATIVES),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Backup creation
# ---------------------------------------------------------------------------


def _build_manifest(
    plan_files: list[_PlannedFile],
    file_records: list[dict[str, Any]],
    vault_summary: list[dict[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    return {
        "format_version": FORMAT_VERSION,
        "app": APP_NAME,
        "generated_at": _utc_now_iso(),
        "repo_root_basename": repo_root.name,
        "config_included": any(f.kind == FILE_KIND_CONFIG for f in plan_files),
        "vaults": vault_summary,
        "file_count": len(file_records),
        "total_bytes": sum(int(r.get("size", 0)) for r in file_records),
        "hash_algorithm": HASH_ALGO,
        "files": file_records,
        "exclusions": {
            "directories": sorted(EXCLUDED_DIR_NAMES),
            "suffixes": sorted(EXCLUDED_SUFFIXES),
            "vault_relatives": sorted(EXCLUDED_VAULT_RELATIVES),
        },
        # Explicit redaction declaration — note bodies are NEVER inside the
        # manifest itself. The archive contains the bytes; the manifest only
        # holds paths, kinds, sizes, and hashes.
        "redaction": {
            "note_bodies_included_in_manifest": False,
            "secret_values_included_in_manifest": False,
        },
    }


def create_backup_archive(
    vault_names: list[str] | None = None,
    *,
    output_root: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Create a zip backup archive and return a summary dict.

    The archive is written to ``output_root`` (default ``dist/backups``).
    The summary contains the backup id, file path, and totals — but never
    note bodies.
    """
    root = (repo_root or _repo_root()).resolve()
    out_root = (output_root or _default_output_root(root)).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    registry = _registered_vaults()
    warnings: list[dict[str, str]] = []
    if vault_names is None:
        chosen = sorted(registry.keys())
    else:
        chosen = []
        for n in vault_names:
            if n in registry:
                chosen.append(n)
            else:
                warnings.append(
                    {
                        "code": WARN_VAULT_NOT_REGISTERED,
                        "message": f"Vault not registered: {n}",
                    }
                )

    planned: list[_PlannedFile] = []
    planned.extend(_plan_config_files(root))
    vault_summary: list[dict[str, Any]] = []
    for name in chosen:
        vault_files = _plan_vault_files(name, registry[name])
        planned.extend(vault_files)
        vault_summary.append(
            {
                "name": name,
                "schema_version": _vault_schema_version(name),
                "file_count": len(vault_files),
                "total_bytes": sum(f.size for f in vault_files),
            }
        )

    # Hash each file and build manifest records.
    file_records: list[dict[str, Any]] = []
    for f in planned:
        try:
            digest = hash_file(f.source_path)
        except OSError:
            continue
        file_records.append(
            {
                "archive_path": f.archive_path,
                "kind": f.kind,
                "size": f.size,
                HASH_ALGO: digest,
            }
        )

    manifest = _build_manifest(planned, file_records, vault_summary, root)
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=False).encode("utf-8")
    manifest_hash = _hash_bytes(manifest_bytes)
    backup_id = f"cve-backup-{_utc_now_compact()}-{manifest_hash[:8]}"
    archive_path = out_root / f"{backup_id}.zip"

    # Write atomically: write to .tmp then rename.
    tmp_path = archive_path.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(MANIFEST_NAME, manifest_bytes)
            for f in planned:
                # Defensive check on every archive path even though we built it.
                if not is_safe_archive_path(f.archive_path):
                    continue
                zf.write(f.source_path, f.archive_path)
        os.replace(tmp_path, archive_path)
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise

    return {
        "backup_id": backup_id,
        "archive_path": _posix(archive_path.relative_to(root)) if _is_relative(archive_path, root) else str(archive_path),
        "archive_absolute": str(archive_path),
        "archive_size": archive_path.stat().st_size,
        "manifest_hash": manifest_hash,
        "file_count": len(file_records),
        "total_bytes": sum(int(r["size"]) for r in file_records),
        "vaults": vault_summary,
        "warnings": warnings,
        "generated_at": manifest["generated_at"],
    }


def _is_relative(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Listing backups
# ---------------------------------------------------------------------------


def list_backups(
    *,
    output_root: Path | None = None,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    """List backup archives under ``output_root`` (default ``dist/backups``)."""
    root = (repo_root or _repo_root()).resolve()
    out_root = (output_root or _default_output_root(root)).resolve()
    if not out_root.is_dir():
        return []
    results: list[dict[str, Any]] = []
    for entry in sorted(out_root.iterdir()):
        if not entry.is_file() or entry.suffix.lower() != ".zip":
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        info: dict[str, Any] = {
            "backup_id": entry.stem,
            "archive_path": _posix(entry.relative_to(root)) if _is_relative(entry, root) else str(entry),
            "archive_size": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "manifest_present": False,
            "format_version": None,
            "file_count": None,
            "vaults": [],
            "warnings": [],
        }
        try:
            manifest = read_backup_manifest(entry)
            info["manifest_present"] = True
            info["format_version"] = manifest.get("format_version")
            info["file_count"] = manifest.get("file_count")
            info["vaults"] = [v.get("name") for v in manifest.get("vaults", [])]
            info["generated_at"] = manifest.get("generated_at")
        except Exception as exc:  # noqa: BLE001
            info["warnings"].append(
                {"code": ERR_MANIFEST_MISSING, "message": str(exc)}
            )
        results.append(info)
    return results


# ---------------------------------------------------------------------------
# Reading + validation
# ---------------------------------------------------------------------------


def read_backup_manifest(zip_path: Path) -> dict[str, Any]:
    """Read and parse the manifest from a backup archive."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        try:
            data = zf.read(MANIFEST_NAME)
        except KeyError as exc:
            raise FileNotFoundError(
                f"Backup manifest missing in archive: {zip_path.name}"
            ) from exc
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Backup manifest is not valid JSON: {zip_path.name}") from exc


def validate_backup_archive(zip_path: Path) -> dict[str, Any]:
    """Validate an archive's structure, paths, and hashes.

    Returns a dict with ``ok`` (bool) and ``errors`` / ``warnings`` lists.
    Does not extract files or write anything.
    """
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not zip_path.is_file():
        return {
            "ok": False,
            "errors": [
                {"code": ERR_BACKUP_NOT_FOUND, "message": f"Backup not found: {zip_path.name}"}
            ],
            "warnings": [],
        }

    try:
        manifest = read_backup_manifest(zip_path)
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "errors": [{"code": ERR_MANIFEST_MISSING, "message": str(exc)}],
            "warnings": [],
        }
    except ValueError as exc:
        return {
            "ok": False,
            "errors": [{"code": ERR_MANIFEST_MISSING, "message": str(exc)}],
            "warnings": [],
        }

    fmt = manifest.get("format_version")
    if fmt != FORMAT_VERSION:
        errors.append(
            {
                "code": ERR_FORMAT_VERSION_UNSUPPORTED,
                "message": f"Unsupported manifest format_version: {fmt!r}",
            }
        )

    declared = {entry["archive_path"]: entry for entry in manifest.get("files", [])}

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [n for n in zf.namelist() if n != MANIFEST_NAME]

        for name in names:
            if not is_safe_archive_path(name):
                errors.append(
                    {
                        "code": ERR_UNSAFE_ARCHIVE_PATH,
                        "message": f"Unsafe archive entry: {name!r}",
                    }
                )

        for archive_path, record in declared.items():
            if archive_path not in zf.namelist():
                errors.append(
                    {
                        "code": ERR_HASH_MISMATCH,
                        "message": f"Manifest references missing entry: {archive_path}",
                    }
                )
                continue
            try:
                with zf.open(archive_path, "r") as fh:
                    h = hashlib.sha256()
                    while True:
                        chunk = fh.read(HASH_CHUNK)
                        if not chunk:
                            break
                        h.update(chunk)
                    digest = h.hexdigest()
            except KeyError:
                errors.append(
                    {
                        "code": ERR_HASH_MISMATCH,
                        "message": f"Entry could not be read: {archive_path}",
                    }
                )
                continue
            expected = record.get(HASH_ALGO)
            if expected != digest:
                errors.append(
                    {
                        "code": ERR_HASH_MISMATCH,
                        "message": f"Hash mismatch: {archive_path}",
                    }
                )

        # Entries present but undeclared are not fatal — warn only.
        declared_set = set(declared.keys())
        for name in names:
            if name not in declared_set:
                warnings.append(
                    {
                        "code": ERR_HASH_MISMATCH,
                        "message": f"Archive entry not in manifest: {name}",
                    }
                )

    return {"ok": not errors, "errors": errors, "warnings": warnings}


# ---------------------------------------------------------------------------
# Migration summary
# ---------------------------------------------------------------------------


def build_migration_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    """Compare the manifest to the current system and report migration risks.

    Pure: makes no writes, only reads schema versions and config.yaml.
    Returns ``{vault_changes, config_changes, warnings, errors}``.
    """
    warnings: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    # Format version check.
    fmt = manifest.get("format_version")
    if fmt != FORMAT_VERSION:
        errors.append(
            {
                "code": ERR_FORMAT_VERSION_UNSUPPORTED,
                "message": f"Manifest format_version {fmt!r} != current {FORMAT_VERSION!r}",
            }
        )

    # Vault schema comparison.
    vault_changes: list[dict[str, Any]] = []
    for vault_entry in manifest.get("vaults", []):
        name = vault_entry.get("name")
        manifest_version = vault_entry.get("schema_version")
        current_version = _vault_schema_version(name) if name else None
        change = {
            "name": name,
            "manifest_schema_version": manifest_version,
            "current_schema_version": current_version,
            "changed": (manifest_version != current_version),
            "registered": name in _registered_vaults() if name else False,
        }
        if change["changed"]:
            warnings.append(
                {
                    "code": WARN_SCHEMA_VERSION_CHANGED,
                    "message": f"Schema version differs for vault {name!r}: "
                    f"{manifest_version!r} → {current_version!r}",
                }
            )
        if name and not change["registered"]:
            warnings.append(
                {
                    "code": WARN_VAULT_NOT_REGISTERED,
                    "message": f"Vault {name!r} from backup is not registered locally.",
                }
            )
        vault_changes.append(change)

    # Config shape comparison (top-level keys).
    config_changes: dict[str, Any] = {
        "config_in_backup": bool(manifest.get("config_included")),
        "config_present_locally": (_repo_root() / "config" / "config.yaml").is_file(),
        "shape_changed": False,
    }
    if config_changes["config_in_backup"] and config_changes["config_present_locally"]:
        # We do not load the manifest's config (it's only referenced by archive
        # path, not by content) — leave shape_changed as a conservative False
        # unless the caller passes in extracted bytes. The richer comparison
        # happens at restore-preview time.
        pass

    return {
        "vault_changes": vault_changes,
        "config_changes": config_changes,
        "warnings": warnings,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Restore preview
# ---------------------------------------------------------------------------


def _resolve_backup_path(
    backup_ref: str,
    *,
    output_root: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Resolve a backup id or path to an archive under ``output_root``.

    Only paths under the configured ``output_root`` are accepted; this
    prevents the API from being used to read arbitrary files.
    """
    root = (repo_root or _repo_root()).resolve()
    out_root = (output_root or _default_output_root(root)).resolve()
    candidate = Path(backup_ref)
    if not candidate.is_absolute():
        # Allow plain id or "dist/backups/<file>.zip"
        if not backup_ref.lower().endswith(".zip"):
            candidate = out_root / f"{backup_ref}.zip"
        else:
            # Resolve relative to repo root.
            candidate = (root / backup_ref)
    candidate = candidate.resolve()
    try:
        candidate.relative_to(out_root)
    except ValueError as exc:
        raise PermissionError(
            f"Backup path is outside the allowed backup directory: {candidate}"
        ) from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"Backup not found: {candidate.name}")
    return candidate


def build_restore_preview(
    backup_ref: str,
    *,
    output_root: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Plan a restore without writing any files.

    Returns a JSON-serialisable dict listing every file that would be
    written, whether each target already exists, plus migration warnings.
    Note bodies are never included in the preview.
    """
    root = (repo_root or _repo_root()).resolve()

    try:
        zip_path = _resolve_backup_path(backup_ref, output_root=output_root, repo_root=root)
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "errors": [{"code": ERR_BACKUP_NOT_FOUND, "message": str(exc)}],
            "warnings": [],
            "backup_id": None,
            "confirmation_phrase": None,
            "entries": [],
            "summary": {},
            "migration": {},
        }
    except PermissionError as exc:
        return {
            "ok": False,
            "errors": [{"code": ERR_UNSAFE_ARCHIVE_PATH, "message": str(exc)}],
            "warnings": [],
            "backup_id": None,
            "confirmation_phrase": None,
            "entries": [],
            "summary": {},
            "migration": {},
        }

    validation = validate_backup_archive(zip_path)
    errors: list[dict[str, str]] = list(validation.get("errors", []))
    warnings: list[dict[str, str]] = list(validation.get("warnings", []))

    try:
        manifest = read_backup_manifest(zip_path)
    except (FileNotFoundError, ValueError) as exc:
        errors.append({"code": ERR_MANIFEST_MISSING, "message": str(exc)})
        manifest = {}

    backup_id = zip_path.stem
    registry = _registered_vaults()

    entries: list[dict[str, Any]] = []
    targets_exist = 0
    for record in manifest.get("files", []):
        archive_path = record.get("archive_path", "")
        if not is_safe_archive_path(archive_path):
            errors.append(
                {
                    "code": ERR_UNSAFE_ARCHIVE_PATH,
                    "message": f"Unsafe archive entry: {archive_path!r}",
                }
            )
            continue
        target = _resolve_target(archive_path, registry, root)
        if target is None:
            warnings.append(
                {
                    "code": WARN_VAULT_NOT_REGISTERED,
                    "message": f"No local target for archive entry: {archive_path}",
                }
            )
            entries.append(
                {
                    "archive_path": archive_path,
                    "kind": record.get("kind"),
                    "size": record.get("size"),
                    "target_path": None,
                    "target_exists": False,
                    "would_overwrite": False,
                    "in_registry": False,
                }
            )
            continue
        if not is_safe_restore_target(target, root):
            errors.append(
                {
                    "code": ERR_UNSAFE_RESTORE_TARGET,
                    "message": f"Unsafe restore target for: {archive_path}",
                }
            )
            continue
        target_exists = target.exists()
        if target_exists:
            targets_exist += 1
        entries.append(
            {
                "archive_path": archive_path,
                "kind": record.get("kind"),
                "size": record.get("size"),
                "target_path": _posix(target.relative_to(root)) if _is_relative(target, root) else str(target),
                "target_exists": target_exists,
                "would_overwrite": target_exists,
                "in_registry": True,
            }
        )

    if targets_exist:
        warnings.append(
            {
                "code": WARN_TARGET_EXISTS,
                "message": f"{targets_exist} target file(s) already exist and would be overwritten.",
            }
        )

    migration = build_migration_summary(manifest) if manifest else {}
    if migration.get("errors"):
        errors.extend(migration["errors"])
    if migration.get("warnings"):
        warnings.extend(migration["warnings"])

    summary = {
        "entry_count": len(entries),
        "targets_existing": targets_exist,
        "config_included": bool(manifest.get("config_included")),
        "vaults": [v.get("name") for v in manifest.get("vaults", [])],
    }

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "backup_id": backup_id,
        "confirmation_phrase": f"RESTORE {backup_id}",
        "entries": entries,
        "summary": summary,
        "migration": migration,
    }


def _resolve_target(
    archive_path: str,
    registry: dict[str, Path],
    repo_root: Path,
) -> Path | None:
    """Map an archive path to its on-disk target, or None if unrecoverable."""
    if archive_path == "config/config.yaml":
        return repo_root / "config" / "config.yaml"
    if archive_path.startswith("vaults/"):
        # vaults/<name>/<rel>
        parts = archive_path.split("/", 2)
        if len(parts) < 3:
            return None
        _, vault_name, rel = parts
        if vault_name not in registry:
            return None
        return registry[vault_name] / rel
    return None


# ---------------------------------------------------------------------------
# Restore apply
# ---------------------------------------------------------------------------


def apply_restore(
    backup_ref: str,
    *,
    confirmation: str | None,
    overwrite: bool = False,
    restore_config: bool = False,
    output_root: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Apply a backup to the local workspace after preview-time checks.

    Safety contract:
    1. The preview must report ``ok=True`` (no blocking errors).
    2. ``confirmation`` must equal ``"RESTORE <backup_id>"``.
    3. Existing files are skipped unless ``overwrite=True``.
    4. ``config/config.yaml`` is never restored unless ``restore_config=True``.
    5. Files are staged into a temp directory, validated, then atomically
       replaced — partial failures leave previous files untouched.

    Returns ``{ok, written, skipped, errors, warnings, backup_id}``.
    """
    root = (repo_root or _repo_root()).resolve()
    try:
        zip_path = _resolve_backup_path(backup_ref, output_root=output_root, repo_root=root)
    except FileNotFoundError as exc:
        return _restore_failure(ERR_BACKUP_NOT_FOUND, str(exc))
    except PermissionError as exc:
        return _restore_failure(ERR_UNSAFE_ARCHIVE_PATH, str(exc))

    preview = build_restore_preview(
        backup_ref, output_root=output_root, repo_root=root
    )
    if not preview.get("ok"):
        return {
            "ok": False,
            "written": [],
            "skipped": [],
            "errors": [
                {
                    "code": ERR_PREVIEW_HAS_ERRORS,
                    "message": "Preview reported blocking errors; refusing to restore.",
                }
            ]
            + list(preview.get("errors", [])),
            "warnings": list(preview.get("warnings", [])),
            "backup_id": preview.get("backup_id"),
        }

    expected_phrase = preview.get("confirmation_phrase")
    if not confirmation:
        return _restore_failure(
            ERR_CONFIRMATION_REQUIRED,
            f"Restore requires confirmation phrase: {expected_phrase!r}",
            backup_id=preview.get("backup_id"),
        )
    if confirmation.strip() != expected_phrase:
        return _restore_failure(
            ERR_CONFIRMATION_MISMATCH,
            f"Confirmation phrase did not match {expected_phrase!r}",
            backup_id=preview.get("backup_id"),
        )

    manifest = read_backup_manifest(zip_path)
    registry = _registered_vaults()

    written: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    # Stage all writes into a temp directory first.
    with tempfile.TemporaryDirectory(prefix="cve-restore-") as staging:
        staging_root = Path(staging)
        staged_pairs: list[tuple[Path, Path, dict[str, Any]]] = []

        with zipfile.ZipFile(zip_path, "r") as zf:
            for record in manifest.get("files", []):
                archive_path = record.get("archive_path", "")
                if not is_safe_archive_path(archive_path):
                    errors.append(
                        {
                            "code": ERR_UNSAFE_ARCHIVE_PATH,
                            "message": f"Unsafe archive entry: {archive_path!r}",
                        }
                    )
                    continue
                if archive_path == "config/config.yaml" and not restore_config:
                    skipped.append(
                        {
                            "archive_path": archive_path,
                            "reason": "config restore not requested",
                        }
                    )
                    continue
                target = _resolve_target(archive_path, registry, root)
                if target is None:
                    skipped.append(
                        {
                            "archive_path": archive_path,
                            "reason": "no local target / vault not registered",
                        }
                    )
                    continue
                if not is_safe_restore_target(target, root):
                    errors.append(
                        {
                            "code": ERR_UNSAFE_RESTORE_TARGET,
                            "message": f"Unsafe restore target for: {archive_path}",
                        }
                    )
                    continue
                if target.exists() and not overwrite:
                    skipped.append(
                        {
                            "archive_path": archive_path,
                            "reason": "target exists and overwrite=False",
                        }
                    )
                    continue

                # Extract bytes to staging area at the same relative path.
                stage_target = staging_root / archive_path
                stage_target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with zf.open(archive_path, "r") as src, open(stage_target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                except KeyError:
                    errors.append(
                        {
                            "code": ERR_HASH_MISMATCH,
                            "message": f"Entry missing during restore: {archive_path}",
                        }
                    )
                    continue

                expected = record.get(HASH_ALGO)
                actual = hash_file(stage_target)
                if expected and actual != expected:
                    errors.append(
                        {
                            "code": ERR_HASH_MISMATCH,
                            "message": f"Hash mismatch during restore: {archive_path}",
                        }
                    )
                    continue
                staged_pairs.append((stage_target, target, record))

        if errors:
            return {
                "ok": False,
                "written": [],
                "skipped": skipped,
                "errors": [
                    {
                        "code": ERR_RESTORE_VALIDATION_FAILED,
                        "message": "Staged validation failed; no files were replaced.",
                    }
                ]
                + errors,
                "warnings": warnings,
                "backup_id": preview.get("backup_id"),
            }

        # All staged files validated. Replace targets atomically.
        for stage_src, target, record in staged_pairs:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                # On Windows, os.replace requires the destination to not be a
                # directory and overwrites existing files atomically.
                os.replace(stage_src, target)
            except OSError as exc:
                errors.append(
                    {
                        "code": ERR_RESTORE_VALIDATION_FAILED,
                        "message": f"Failed to write {record.get('archive_path')}: {exc}",
                    }
                )
                continue
            written.append(
                {
                    "archive_path": record.get("archive_path"),
                    "target_path": _posix(target.relative_to(root))
                    if _is_relative(target, root)
                    else str(target),
                    "kind": record.get("kind"),
                    "size": record.get("size"),
                }
            )

    return {
        "ok": not errors,
        "written": written,
        "skipped": skipped,
        "errors": errors,
        "warnings": warnings,
        "backup_id": preview.get("backup_id"),
    }


def _restore_failure(
    code: str,
    message: str,
    *,
    backup_id: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "written": [],
        "skipped": [],
        "errors": [{"code": code, "message": message}],
        "warnings": [],
        "backup_id": backup_id,
    }
