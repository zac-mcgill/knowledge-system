"""Markdown folder import pipeline — Phase 26A.

Safe, deterministic, local import of an external folder of Markdown notes
into an existing registered vault.

Design rules:
    - Local-first, deterministic-first.
    - No semantic retrieval, no LLM extraction, no PDF / browser / GitHub
      / Obsidian-specific import (deferred to later Phase 26 slices).
    - No path traversal: source paths must be regular files; destination
      paths must resolve inside the target vault and outside
      ``Vault Files/``.
    - No silent overwrite: existing destination files are skipped unless
      the caller passes ``overwrite=True``.
    - Imported notes are marked as drafts:
        status        -> "draft" if the schema supports it, else "partial".
        source_type   -> "imported" if ``VALID_SOURCE_TYPES`` exists.
        trust_level   -> "draft"    if ``VALID_TRUST_LEVELS`` exists.
    - Unknown source frontmatter fields are dropped from the written
      note and surfaced as warnings.
    - Section boolean fields (``has_key_principles`` / ``has_how_it_works``
      / ``has_tradeoffs``) are computed from body content, never trusted
      from the source.
    - Every source file is security-scanned before any write.  A finding
      with severity high or critical against a blocking rule (see
      ``core.shared.context_security``) blocks the write of that file;
      lower-severity findings are returned as warnings.
    - Each candidate note is serialised and validated via the project's
      existing ``validate_file`` logic before any write.  Validation
      failures block the write for that file.

Public API:
    discover_markdown_sources(source_dir) -> list[Path]
    normalise_import_slug(name) -> str
    read_markdown_source(path) -> dict
    split_frontmatter_and_body(content) -> tuple[dict, str]
    map_fields_to_schema(source_fields, body, schema, destination_path)
        -> tuple[dict, list[str]]
    build_import_plan(vault_path, source_dir, schema, options) -> dict
    execute_import_plan(plan, vault_name, vault_path, schema,
                        overwrite=False) -> dict
    import_markdown_folder(vault_name, source_dir, destination="Imported",
                           dry_run=True, overwrite=False) -> dict
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from core.shared.context_security import (
    _BLOCKING_RULES,
    _SEVERITY_RANK,
    scan_text,
)

logger = logging.getLogger("import.pipeline")

# Maximum length of a slugified path segment.  Keeps generated filenames
# readable while still allowing reasonable uniqueness via prefix.
_SLUG_MAX_LEN = 80

# Maximum source file size accepted by the importer (bytes).  Markdown
# notes are tiny in practice; this guards against accidentally pointing
# at huge binary blobs.
_MAX_SOURCE_BYTES = 5 * 1024 * 1024  # 5 MB

# Default destination folder relative to the vault root.
DEFAULT_DESTINATION = "Imported"

# Folder name reserved for generated / system files.  Imports must never
# write here, regardless of caller input.
_RESERVED_FOLDER = "Vault Files"


# ---------------------------------------------------------------------------
# Path / slug helpers
# ---------------------------------------------------------------------------


def normalise_import_slug(name: str) -> str:
    """Return a safe, deterministic slug for a path segment.

    - Strips any trailing ``.md`` extension.
    - Lowercases.
    - Replaces every non-alphanumeric run with a single ``-``.
    - Strips leading and trailing ``-``.
    - Caps length at ``_SLUG_MAX_LEN``.
    - Falls back to ``"untitled"`` if the result is empty.
    """
    if name is None:
        return "untitled"

    s = str(name).strip()
    if s.lower().endswith(".md"):
        s = s[:-3]
    s = s.lower()

    out_chars: list[str] = []
    prev_hyphen = False
    for ch in s:
        if ch.isalnum():
            out_chars.append(ch)
            prev_hyphen = False
        else:
            if not prev_hyphen:
                out_chars.append("-")
                prev_hyphen = True
    slug = "".join(out_chars).strip("-")

    if not slug:
        return "untitled"

    if len(slug) > _SLUG_MAX_LEN:
        slug = slug[:_SLUG_MAX_LEN].rstrip("-") or "untitled"

    return slug


def _is_safe_relative_destination(dest: str) -> tuple[bool, str | None]:
    """Validate the user-supplied destination folder.

    Rejects absolute paths, traversal segments, null bytes, and any
    destination that begins with ``Vault Files``.
    """
    if dest is None:
        return False, "destination is required"
    if "\x00" in dest:
        return False, "destination must not contain null bytes"

    raw = dest.replace("\\", "/").strip().strip("/")
    if not raw:
        return False, "destination must not be empty"

    if os.path.isabs(dest) or Path(dest).is_absolute():
        return False, "destination must be a vault-relative path"

    parts = raw.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            return False, "destination must not contain '.' or '..' segments"
        if "\x00" in part:
            return False, "destination must not contain null bytes"

    if parts[0] == _RESERVED_FOLDER:
        return False, (
            f"destination must not be inside '{_RESERVED_FOLDER}/' "
            "(reserved for generated files)"
        )

    return True, None


def _safe_destination_path(
    vault_path: Path,
    destination: str,
    relative_source: Path,
    source_filename: str,
) -> tuple[str | None, str | None]:
    """Compute a safe vault-relative destination path for a source file.

    Returns ``(rel_posix_path, error_message)``.  If ``error_message`` is
    not None, the caller MUST treat the item as an error.
    """
    # Sanitise each segment of the destination folder.
    dest_segments_raw = destination.replace("\\", "/").strip("/").split("/")
    dest_segments = [normalise_import_slug(seg) for seg in dest_segments_raw]

    # Sanitise relative source sub-folders (excluding the filename itself).
    rel_parts = list(relative_source.parts[:-1])
    sub_segments = [normalise_import_slug(seg) for seg in rel_parts]

    # Sanitise filename stem.
    filename_slug = normalise_import_slug(source_filename) + ".md"

    all_parts = dest_segments + sub_segments + [filename_slug]
    rel = "/".join(all_parts)

    # Resolve and confirm containment in vault root.
    vault_resolved = vault_path.resolve()
    candidate = (vault_path / rel).resolve()
    try:
        rel_check = candidate.relative_to(vault_resolved)
    except ValueError:
        return None, "destination escapes vault root"

    if rel_check.parts and rel_check.parts[0] == _RESERVED_FOLDER:
        return None, (
            f"destination must not be inside '{_RESERVED_FOLDER}/'"
        )

    return rel_check.as_posix(), None


# ---------------------------------------------------------------------------
# Source discovery / reading
# ---------------------------------------------------------------------------


def discover_markdown_sources(source_dir: Path) -> list[Path]:
    """Recursively list ``.md`` files under ``source_dir``.

    - Returns absolute, resolved paths.
    - Sorted case-insensitive by full path string for deterministic order.
    - Non-Markdown files and directories named exactly like Markdown files
      are ignored.
    """
    if not isinstance(source_dir, Path):
        source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source folder not found: {source_dir}")

    found: list[Path] = []
    for p in source_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() != ".md":
            continue
        found.append(p.resolve())
    found.sort(key=lambda p: str(p).lower())
    return found


class _SourceTooLargeError(ValueError):
    """Raised when a source markdown file exceeds the size cap."""


class _NullByteError(ValueError):
    """Raised when a source markdown file contains a null byte."""


def read_markdown_source(path: Path) -> dict:
    """Read a markdown source file and return its raw content metadata.

    Returns a dict with ``path``, ``size``, ``content`` keys.  Raises
    ``_SourceTooLargeError`` if the file exceeds ``_MAX_SOURCE_BYTES``,
    ``_NullByteError`` if the raw bytes contain a NUL byte, and
    ``FileNotFoundError`` if the path is not a regular file.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Source markdown file not found: {path}")
    size = path.stat().st_size
    if size > _MAX_SOURCE_BYTES:
        raise _SourceTooLargeError(
            f"Source markdown file too large ({size} bytes > "
            f"{_MAX_SOURCE_BYTES}): {path}"
        )
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    if b"\x00" in raw:
        raise _NullByteError(
            f"Source markdown file contains a null byte: {path}"
        )
    text = raw.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return {"path": str(path), "size": size, "content": text}


class _DuplicateYAMLKeyError(ValueError):
    """Raised when YAML frontmatter contains a duplicate mapping key."""


class _DuplicateKeySafeLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate keys in mappings.

    PyYAML's default SafeLoader silently keeps the last value for a
    duplicated mapping key.  For import frontmatter we want to refuse
    such input so that ambiguous source files do not silently overwrite
    fields during import.
    """


def _construct_mapping_no_duplicates(loader, node, deep=False):  # type: ignore[no-untyped-def]
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise _DuplicateYAMLKeyError(
                f"duplicate YAML key in frontmatter: {key!r}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_DuplicateKeySafeLoader.add_constructor(  # type: ignore[arg-type]
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_no_duplicates,
)


def split_frontmatter_and_body(content: str) -> tuple[dict, str]:
    """Split a Markdown string into ``(frontmatter_fields, body)``.

    - If no leading ``---`` YAML frontmatter block is present, returns
      ``({}, content)``.
    - If an opening ``---`` marker is present without a closing marker,
      raises ``ValueError`` (the file is structurally malformed).
    - Malformed YAML or non-mapping frontmatter raises ``ValueError``.
    - Duplicate mapping keys raise ``_DuplicateYAMLKeyError`` (subclass
      of ``ValueError``).
    - All field values are coerced to strings or bools, matching the
      project's existing ``parse_yaml_frontmatter`` semantics.
    """
    if not content.startswith("---\n"):
        return {}, content

    close_idx = content.find("\n---\n", 4)
    if close_idx == -1:
        if content.endswith("\n---"):
            close_idx = len(content) - 4
        else:
            raise ValueError(
                "Malformed YAML frontmatter: opening '---' marker has no "
                "matching closing '---' marker"
            )

    yaml_text = content[4:close_idx]
    remainder_start = close_idx + len("\n---\n")
    if close_idx == len(content) - 4:
        remainder_start = len(content)
    body = content[remainder_start:]
    if body.startswith("\n"):
        body = body[1:]

    try:
        parsed = yaml.load(yaml_text, Loader=_DuplicateKeySafeLoader)
    except _DuplicateYAMLKeyError:
        raise
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML frontmatter: {exc}") from exc

    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError(
            "Malformed YAML frontmatter: expected mapping, "
            f"got {type(parsed).__name__}"
        )

    fields: dict[str, Any] = {}
    for key, value in parsed.items():
        if isinstance(value, bool):
            fields[str(key)] = value
        elif value is None:
            fields[str(key)] = ""
        else:
            fields[str(key)] = str(value)
    return fields, body


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------


def _safe_derive(callable_fn, *args, default=None):
    """Call a schema derive_* helper, returning ``default`` on ValueError."""
    try:
        return callable_fn(*args)
    except Exception:  # noqa: BLE001 — derivation helpers raise ValueError
        return default


def _choose_status(schema: Any, section_bools: dict[str, bool]) -> str:
    """Pick the safest status value for an imported note.

    Rules:
        - ``"draft"`` when the schema's ``VALID_STATUSES`` contains it.
        - Otherwise, fall back to the schema's status derivation rule when
          known (booleans -> ``"complete"`` / ``"partial"``).  This keeps
          imports compatible with strict schemas that couple status to
          section content.  The draft signal is preserved by setting
          ``trust_level=draft`` and ``source_type=imported`` separately.
        - If only one status value exists at all, use it.
        - Default: ``"partial"``.
    """
    valid = getattr(schema, "VALID_STATUSES", frozenset())
    if "draft" in valid:
        return "draft"
    kp = section_bools.get("has_key_principles", False)
    hw = section_bools.get("has_how_it_works", False)
    to = section_bools.get("has_tradeoffs", False)
    if kp and hw and to and "complete" in valid:
        return "complete"
    if "partial" in valid:
        return "partial"
    if valid:
        return sorted(valid)[0]
    return "partial"


def map_fields_to_schema(
    source_fields: dict,
    body: str,
    schema: Any,
    destination_path: str,
) -> tuple[dict[str, Any], list[str]]:
    """Map source frontmatter + body onto the target vault schema.

    Returns ``(fields, warnings)``.

    - Unknown source fields are dropped and recorded as warnings.
    - Section boolean fields are recomputed from the body, never trusted
      from the source.
    - Trust metadata is set to draft / imported when supported by the
      schema.
    - Domain / subdomain / topic / difficulty are derived from the
      destination path; failures become warnings, not exceptions.
    """
    warnings: list[str] = []
    rel_parts = list(Path(destination_path).parts)
    filename = rel_parts[-1] if rel_parts else "untitled.md"

    known_fields: frozenset[str] = getattr(
        schema, "ALL_KNOWN_FIELDS", frozenset()
    )
    valid_trust = getattr(schema, "VALID_TRUST_LEVELS", frozenset())
    valid_source_types = getattr(schema, "VALID_SOURCE_TYPES", frozenset())

    # Detect unknown frontmatter fields in the source.
    for key in sorted(source_fields.keys()):
        if known_fields and key not in known_fields:
            warnings.append(
                f"Source frontmatter field {key!r} is not in the target "
                "schema; dropped from imported note."
            )

    fields: dict[str, Any] = {}

    # type — defer to schema derivation
    note_type = _safe_derive(
        getattr(schema, "derive_type", lambda *a, **k: "core-concept"),
        filename,
        default="core-concept",
    )
    fields["type"] = note_type

    # domain / subdomain / topic from destination path
    domain = _safe_derive(getattr(schema, "derive_domain", None), rel_parts[:-1])
    if domain is None and len(rel_parts) >= 2:
        warnings.append(
            "Could not derive 'domain' from destination path "
            f"{destination_path!r}; field omitted."
        )
    if domain is not None:
        fields["domain"] = domain

    subdomain_result = _safe_derive(
        getattr(schema, "derive_subdomain", None), rel_parts[:-1]
    )
    if subdomain_result is not None:
        slug, _parent = subdomain_result
        fields["subdomain"] = slug

    topic_result = _safe_derive(
        getattr(schema, "derive_topic", None), rel_parts[:-1]
    )
    if topic_result is not None:
        slug, _parent = topic_result
        fields["topic"] = slug

    # section booleans — computed from body content only (computed before
    # status so strict schemas that derive status from booleans validate).
    tracked = getattr(schema, "TRACKED_SECTIONS", ())
    detect = getattr(schema, "detect_section_content", None)
    section_bools: dict[str, bool] = {}
    if detect is not None and tracked:
        for boolean_field, section_name in tracked:
            heading = section_name
            if not heading.startswith("## "):
                heading = f"## {section_name}"
            section_bools[boolean_field] = bool(detect(body, heading))
            fields[boolean_field] = section_bools[boolean_field]

    # status — draft if supported, else derived from booleans
    fields["status"] = _choose_status(schema, section_bools)

    # difficulty — derived
    difficulty = _safe_derive(
        getattr(schema, "derive_difficulty", None),
        fields.get("subdomain"),
        fields.get("topic"),
    )
    if difficulty is not None:
        fields["difficulty"] = difficulty

    # Trust metadata — only set when the schema accepts these values.
    if "trust_level" in known_fields and "draft" in valid_trust:
        fields["trust_level"] = "draft"
    if "source_type" in known_fields and "imported" in valid_source_types:
        fields["source_type"] = "imported"

    return fields, warnings


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------


def _scan_source(content: str, source_label: str) -> dict:
    """Run the deterministic security scanner on a single source body.

    Returns ``{"status": pass|warning|fail, "findings": [...]}``.
    """
    findings = scan_text(content, path=source_label, field="body")
    findings.sort(
        key=lambda f: (
            -_SEVERITY_RANK.get(f["severity"], 0),
            f["rule"],
            f["detail"],
        )
    )

    status = "pass"
    for f in findings:
        rule = f.get("rule", "")
        sev = f.get("severity", "")
        rank = _SEVERITY_RANK.get(sev, 0)
        if rule in _BLOCKING_RULES and rank >= _SEVERITY_RANK["high"]:
            status = "fail"
            break
        if rank >= _SEVERITY_RANK["medium"]:
            status = "warning"
    return {"status": status, "findings": findings}


# ---------------------------------------------------------------------------
# Plan construction
# ---------------------------------------------------------------------------


def _serialise_candidate(fields: dict[str, Any], body: str) -> str:
    """Serialise a candidate imported note to canonical Markdown."""
    # Reuse the project's canonical serialiser to stay byte-compatible
    # with PUT /note.
    from mcp.core.note_write import serialise_note_markdown
    return serialise_note_markdown(fields, body)


def _validate_candidate(
    candidate_content: str,
    rel_path: str,
    schema: Any,
) -> list[str]:
    """Validate candidate content as if it lived at ``rel_path``.

    Builds a temporary directory tree mirroring ``rel_path`` so that
    depth-based derivation in ``validate_file`` works correctly.
    """
    from core.shared.validate_vault import validate_file as _validate_file

    parts = Path(rel_path).parts
    with tempfile.TemporaryDirectory(prefix="cvault_import_validate_") as tmpdir:
        tmp_root = Path(tmpdir)
        tmp_note_dir = tmp_root
        for part in parts[:-1]:
            tmp_note_dir = tmp_note_dir / part
        tmp_note_dir.mkdir(parents=True, exist_ok=True)
        tmp_note_path = tmp_note_dir / parts[-1]
        tmp_note_path.write_text(candidate_content, encoding="utf-8")
        return _validate_file(tmp_note_path, tmp_root, schema)


def build_import_plan(
    vault_path: Path,
    source_dir: Path,
    schema: Any,
    options: dict | None = None,
) -> dict:
    """Build a deterministic import plan from ``source_dir`` into ``vault_path``.

    The plan never touches the filesystem of the vault.  It contains one
    item per discovered Markdown file describing the proposed write and
    its safety / validation outcomes.
    """
    options = options or {}
    destination = options.get("destination") or DEFAULT_DESTINATION

    ok, err = _is_safe_relative_destination(destination)
    if not ok:
        return {
            "status": "error",
            "error": {"code": "UNSAFE_DESTINATION", "message": err},
        }

    if not source_dir.exists() or not source_dir.is_dir():
        return {
            "status": "error",
            "error": {
                "code": "INVALID_SOURCE",
                "message": f"Source folder not found or not a directory: {source_dir}",
            },
        }

    try:
        sources = discover_markdown_sources(source_dir)
    except Exception as exc:
        return {
            "status": "error",
            "error": {"code": "INVALID_SOURCE", "message": str(exc)},
        }

    items: list[dict] = []
    used_dest_paths: set[str] = set()

    for source_path in sources:
        try:
            rel_source = source_path.relative_to(source_dir.resolve())
        except ValueError:
            rel_source = Path(source_path.name)

        rel_dest, dest_err = _safe_destination_path(
            vault_path=vault_path,
            destination=destination,
            relative_source=rel_source,
            source_filename=source_path.name,
        )

        item: dict[str, Any] = {
            "source_path": str(source_path),
            "destination_path": rel_dest or "",
            "action": "create",
            "status": "planned",
            "fields": {},
            "warnings": [],
            "errors": [],
            "security": {"status": "pass", "findings": []},
            "validation": {"status": "pass", "errors": []},
        }

        if dest_err is not None:
            item["status"] = "error"
            item["action"] = "skip"
            item["errors"].append({"code": "UNSAFE_DESTINATION", "message": dest_err})
            items.append(item)
            continue

        # Resolve collisions deterministically by appending -1, -2, ... but
        # only within the *plan*.  Existing on-disk files trigger
        # DESTINATION_EXISTS at execution time when overwrite=False.
        original_dest = rel_dest
        suffix_idx = 1
        while rel_dest in used_dest_paths:
            stem = original_dest[:-3] if original_dest.endswith(".md") else original_dest
            rel_dest = f"{stem}-{suffix_idx}.md"
            suffix_idx += 1
        used_dest_paths.add(rel_dest)
        item["destination_path"] = rel_dest

        # Read content
        try:
            read = read_markdown_source(source_path)
        except _SourceTooLargeError as exc:
            item["status"] = "blocked"
            item["action"] = "skip"
            item["errors"].append(
                {"code": "SOURCE_TOO_LARGE", "message": str(exc)}
            )
            items.append(item)
            continue
        except _NullByteError as exc:
            item["status"] = "blocked"
            item["action"] = "skip"
            item["errors"].append(
                {"code": "NULL_BYTE", "message": str(exc)}
            )
            items.append(item)
            continue
        except Exception as exc:
            item["status"] = "error"
            item["action"] = "skip"
            item["errors"].append({"code": "READ_FAILED", "message": str(exc)})
            items.append(item)
            continue

        content = read["content"]

        # Security scan (against actual source content)
        security = _scan_source(content, str(source_path))
        item["security"] = security
        if security["status"] == "fail":
            item["status"] = "blocked"
            item["action"] = "skip"
            item["errors"].append(
                {
                    "code": "SECURITY_FAIL",
                    "message": "Source file contains high/critical security findings.",
                }
            )
            items.append(item)
            continue
        if security["status"] == "warning":
            for f in security["findings"]:
                item["warnings"].append(
                    f"security: {f.get('rule')} ({f.get('severity')}) {f.get('detail')}"
                )

        # Split source frontmatter and body
        try:
            source_fields, body = split_frontmatter_and_body(content)
        except _DuplicateYAMLKeyError as exc:
            item["status"] = "blocked"
            item["action"] = "skip"
            item["errors"].append(
                {"code": "DUPLICATE_YAML_KEY", "message": str(exc)}
            )
            items.append(item)
            continue
        except ValueError as exc:
            code = "INVALID_FRONTMATTER"
            msg = str(exc)
            if "expected mapping" in msg:
                code = "FRONTMATTER_NOT_OBJECT"
            item["status"] = "blocked"
            item["action"] = "skip"
            item["errors"].append({"code": code, "message": msg})
            items.append(item)
            continue

        # Map to schema
        mapped, map_warnings = map_fields_to_schema(
            source_fields=source_fields,
            body=body,
            schema=schema,
            destination_path=rel_dest,
        )
        item["fields"] = mapped
        item["warnings"].extend(map_warnings)

        # Serialise + validate candidate
        try:
            candidate_md = _serialise_candidate(mapped, body)
        except Exception as exc:
            item["status"] = "blocked"
            item["action"] = "skip"
            item["errors"].append(
                {"code": "SERIALISE_FAILED", "message": str(exc)}
            )
            items.append(item)
            continue

        validation_errors = _validate_candidate(candidate_md, rel_dest, schema)
        if validation_errors:
            item["validation"] = {"status": "fail", "errors": validation_errors}
            item["status"] = "blocked"
            item["action"] = "skip"
            for err_msg in validation_errors:
                item["errors"].append(
                    {"code": "VALIDATION_FAILED", "message": err_msg}
                )
        else:
            item["validation"] = {"status": "pass", "errors": []}

        # Hold candidate content under a private key for executor use.
        item["_candidate_content"] = candidate_md

        # Pre-detect collisions on disk for nicer plan output.
        target_abs = (vault_path / rel_dest)
        if target_abs.exists():
            item["action"] = "overwrite"

        items.append(item)

    summary = {
        "discovered": len(sources),
        "planned": sum(1 for i in items if i["status"] == "planned"),
        "written": 0,
        "skipped": sum(1 for i in items if i["status"] == "skipped"),
        "errors": sum(1 for i in items if i["status"] in ("error", "blocked")),
        "warnings": sum(1 for i in items if i["warnings"]),
    }

    return {
        "status": "ok",
        "summary": summary,
        "items": items,
        "destination": destination,
    }


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def execute_import_plan(
    plan: dict,
    vault_name: str,
    vault_path: Path,
    schema: Any,
    overwrite: bool = False,
) -> dict:
    """Apply a plan returned by ``build_import_plan`` to the vault.

    Only items with ``status == "planned"`` are considered.  Each item
    is written atomically via temp-file-then-rename.  Note caches are
    invalidated once after the loop if any file was actually written.
    """
    if plan.get("status") != "ok":
        return plan

    vault_resolved = vault_path.resolve()
    written = 0

    for item in plan["items"]:
        if item.get("status") != "planned":
            continue
        rel_dest = item.get("destination_path") or ""
        candidate = item.pop("_candidate_content", None)
        if not rel_dest or candidate is None:
            item["status"] = "error"
            item["action"] = "skip"
            item["errors"].append(
                {"code": "INTERNAL", "message": "missing candidate content"}
            )
            continue

        target_abs = (vault_path / rel_dest).resolve()
        try:
            target_abs.relative_to(vault_resolved)
        except ValueError:
            item["status"] = "error"
            item["action"] = "skip"
            item["errors"].append(
                {
                    "code": "UNSAFE_DESTINATION",
                    "message": "destination escapes vault root",
                }
            )
            continue

        if target_abs.exists():
            if not overwrite:
                item["status"] = "skipped"
                item["action"] = "skip"
                item["errors"].append(
                    {
                        "code": "DESTINATION_EXISTS",
                        "message": f"destination already exists: {rel_dest}",
                    }
                )
                continue
            item["action"] = "overwrite"

        # Ensure parent directory exists (within vault root).
        try:
            target_abs.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            item["status"] = "error"
            item["action"] = "skip"
            item["errors"].append(
                {"code": "WRITE_FAILED", "message": f"mkdir failed: {exc}"}
            )
            continue

        tmp_path: Path | None = None
        try:
            fd, tmp_str = tempfile.mkstemp(
                prefix=".import-", suffix=".tmp", dir=str(target_abs.parent)
            )
            tmp_path = Path(tmp_str)
            try:
                os.write(fd, candidate.encode("utf-8"))
            finally:
                os.close(fd)
            tmp_path.replace(target_abs)
            tmp_path = None
            item["status"] = "written"
            written += 1
        except OSError as exc:
            item["status"] = "error"
            item["action"] = "skip"
            item["errors"].append(
                {"code": "WRITE_FAILED", "message": f"write failed: {exc}"}
            )
        finally:
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    if written > 0:
        # Invalidate index cooldown + result cache so subsequent reads see the
        # new files immediately.
        try:
            from mcp.core.note_write import invalidate_note_caches
            invalidate_note_caches(vault_name)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("invalidate_note_caches failed: %s", exc)
        try:
            from mcp.core.result_cache import clear_vault_cache
            clear_vault_cache(vault_name)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("clear_vault_cache failed: %s", exc)

    # Recompute summary counts now that writes have happened.
    summary = plan["summary"]
    summary["written"] = written
    summary["skipped"] = sum(
        1 for i in plan["items"] if i["status"] == "skipped"
    )
    summary["errors"] = sum(
        1 for i in plan["items"] if i["status"] in ("error", "blocked")
    )
    summary["planned"] = sum(
        1 for i in plan["items"] if i["status"] == "planned"
    )
    summary["warnings"] = sum(1 for i in plan["items"] if i["warnings"])

    return plan


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def import_markdown_folder(
    vault_name: str,
    source_dir: str,
    destination: str = DEFAULT_DESTINATION,
    dry_run: bool = True,
    overwrite: bool = False,
) -> dict:
    """Top-level entry point for the markdown folder import pipeline.

    Always returns a structured response dict suitable for use as the
    HTTP / CLI body.  Never raises on user-facing input errors; raises
    only on truly unexpected internal failures.
    """
    from mcp.core.vault_registry import get_vault_path, get_schema

    try:
        vault_path = get_vault_path(vault_name)
    except KeyError as exc:
        return {
            "status": "error",
            "error": {"code": "INVALID_VAULT", "message": str(exc)},
        }

    schema = get_schema(vault_name)

    src = Path(source_dir).expanduser()
    if "\x00" in str(source_dir):
        return {
            "status": "error",
            "error": {
                "code": "INVALID_SOURCE",
                "message": "source_dir must not contain null bytes",
            },
        }
    try:
        src_resolved = src.resolve(strict=False)
    except OSError as exc:
        return {
            "status": "error",
            "error": {"code": "INVALID_SOURCE", "message": str(exc)},
        }

    if not src_resolved.exists() or not src_resolved.is_dir():
        return {
            "status": "error",
            "error": {
                "code": "INVALID_SOURCE",
                "message": f"source folder not found: {src_resolved}",
            },
        }

    # Disallow importing the vault into itself (catches obvious foot-guns).
    vault_resolved = vault_path.resolve()
    try:
        src_resolved.relative_to(vault_resolved)
        return {
            "status": "error",
            "error": {
                "code": "UNSAFE_SOURCE",
                "message": "source folder must not be inside the target vault",
            },
        }
    except ValueError:
        pass  # source is outside vault — expected.

    plan = build_import_plan(
        vault_path=vault_path,
        source_dir=src_resolved,
        schema=schema,
        options={"destination": destination},
    )
    if plan.get("status") != "ok":
        return plan

    if not dry_run:
        plan = execute_import_plan(
            plan=plan,
            vault_name=vault_name,
            vault_path=vault_path,
            schema=schema,
            overwrite=overwrite,
        )

    # Drop the internal candidate-content key from every item before
    # returning to the caller.
    for item in plan.get("items", []):
        item.pop("_candidate_content", None)

    return {
        "status": "ok",
        "data": {
            "vault": vault_name,
            "source_dir": str(src_resolved),
            "destination": destination,
            "dry_run": bool(dry_run),
            "overwrite": bool(overwrite),
            "summary": plan["summary"],
            "items": plan["items"],
        },
    }
