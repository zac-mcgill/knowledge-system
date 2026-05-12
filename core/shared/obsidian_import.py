"""Obsidian-compatible Markdown import pipeline - Phase 26E.

Thin wrapper around the Phase 26A-D Markdown import pipeline that adds:

    - Obsidian vault aware source discovery (skips ``.obsidian/``,
      ``.trash/``, ``.git/``, ``node_modules/``, and other obvious
      system / hidden directories).
    - Markdown only filtering (no binary attachments, no ``.canvas``,
      no images, no PDFs, no audio / video).
    - Detection and reporting of Obsidian specific features per item:
      wikilinks, embeds, inline tags, YAML tags, aliases, callouts,
      attachment references.

All hardening (null byte rejection, oversize rejection, duplicate YAML
key detection, security scan, schema mapping, validation, atomic writes,
cache / index invalidation) is delegated to the existing
``import_markdown_folder`` orchestrator, so safety semantics stay
identical to Phase 26A-D.

Public API:
    is_obsidian_config_path(path) -> bool
    discover_obsidian_markdown_sources(source_dir) -> list[Path]
    extract_obsidian_features(markdown, frontmatter) -> dict
    build_obsidian_import_plan(...) -> dict
    import_obsidian_vault(...) -> dict

Scope boundary (Phase 26E):
    - Obsidian Markdown only. Binary attachments are never imported.
    - ``.canvas`` files are ignored as content.
    - No automatic wikilink rewriting; ``[[X]]`` is preserved verbatim in
      the body.
    - No LLM extraction, no semantic mapping, no automatic trust
      promotion. PDF, GitHub, browser article, chat transcript,
      semantic, and LLM extraction imports remain deferred.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger("import.obsidian")


# Default destination folder for Obsidian imports, relative to the vault root.
DEFAULT_OBSIDIAN_DESTINATION = "Imported/Obsidian"


# Folder names that must never be traversed when discovering Obsidian
# Markdown sources. Names are matched case-insensitively against each
# path part.
_SKIP_DIR_NAMES = frozenset(
    name.lower()
    for name in (
        ".obsidian",
        ".trash",
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".vscode",
        ".idea",
        "__pycache__",
        ".DS_Store",
    )
)


# Source label for items produced by this pipeline. Surfaced in the
# response data but never blindly written into the target frontmatter
# (the target schema's ``source_type`` enum controls what is written).
OBSIDIAN_SOURCE_TYPE_LABEL = "obsidian-vault"


# ---------------------------------------------------------------------------
# Path filters
# ---------------------------------------------------------------------------


def is_obsidian_config_path(path: Path) -> bool:
    """Return True if ``path`` lies inside an Obsidian config / system folder.

    Used by the discovery filter to skip ``.obsidian/``, ``.trash/``,
    ``.git/``, ``node_modules/`` and similar locations. Matching is
    case-insensitive on each path part. Hidden files at the vault root
    are also reported as config paths.
    """
    if not isinstance(path, Path):
        path = Path(path)
    for part in path.parts:
        if part.lower() in _SKIP_DIR_NAMES:
            return True
    return False


def discover_obsidian_markdown_sources(source_dir: Path) -> list[Path]:
    """List ``.md`` files under an Obsidian vault, filtered safely.

    - Returns absolute, resolved paths.
    - Skips ``.obsidian/`` and other config / system directories.
    - Skips dot-prefixed directories at every depth.
    - Returns Markdown files only (``.md``); binary attachments and
      ``.canvas`` files are excluded.
    - Sorted case-insensitively by full path for deterministic output.
    """
    if not isinstance(source_dir, Path):
        source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source folder not found: {source_dir}")

    source_resolved = source_dir.resolve()
    found: list[Path] = []

    for p in source_resolved.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() != ".md":
            continue
        try:
            rel = p.relative_to(source_resolved)
        except ValueError:
            continue
        # Skip any path that traverses a known config / hidden folder.
        skip = False
        for part in rel.parts[:-1]:
            lower = part.lower()
            if lower in _SKIP_DIR_NAMES or (part.startswith(".") and lower not in (".",)):
                skip = True
                break
        if skip:
            continue
        # Skip dot-prefixed file names (e.g. ``.template.md``).
        if rel.name.startswith("."):
            continue
        found.append(p)

    found.sort(key=lambda p: str(p).lower())
    return found


# ---------------------------------------------------------------------------
# Feature detection
# ---------------------------------------------------------------------------


_RE_EMBED = re.compile(r"!\[\[([^\]\n]+)\]\]")
_RE_WIKILINK = re.compile(r"(?<!\!)\[\[([^\]\n]+)\]\]")
_RE_MD_IMAGE = re.compile(r"!\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"\n]*\")?\)")
_RE_INLINE_TAG = re.compile(r"(?<![A-Za-z0-9_#/`])#([A-Za-z][\w/-]*)")
_RE_CALLOUT = re.compile(r"^\s*>\s*\[!([A-Za-z][\w-]*)\]", re.MULTILINE)
_RE_BLOCK_REF = re.compile(r"\^([A-Za-z0-9][\w-]*)")


_BINARY_ATTACHMENT_EXTS = frozenset(
    {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg",
        ".pdf", ".mp3", ".wav", ".ogg", ".m4a", ".flac",
        ".mp4", ".mov", ".webm", ".mkv", ".avi",
        ".zip", ".gz", ".tar", ".7z",
        ".canvas",
    }
)


def _strip_code_fences(text: str) -> str:
    """Remove fenced code blocks and inline code so feature regexes do
    not match Markdown samples inside ``` / `` regions."""
    # Strip triple-backtick fenced blocks (greedy across lines).
    no_fenced = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Strip inline code spans.
    no_inline = re.sub(r"`[^`\n]*`", "", no_fenced)
    return no_inline


def _is_heading_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return False
    i = 0
    while i < len(stripped) and stripped[i] == "#":
        i += 1
    if i > 6:
        return False
    return i == len(stripped) or stripped[i] == " "


def _collect_inline_tags(text: str) -> list[str]:
    tags: set[str] = set()
    for raw_line in text.splitlines():
        if _is_heading_line(raw_line):
            continue
        for match in _RE_INLINE_TAG.finditer(raw_line):
            tag = match.group(1)
            # Reject purely numeric trailing segments? Keep as-is for
            # determinism; pattern requires leading alpha so #123 is
            # already excluded.
            tags.add(tag)
    return sorted(tags)


def _coerce_list(value) -> list[str]:
    """Coerce a frontmatter scalar / list / comma string into a list of
    cleaned strings."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        out = []
        for v in value:
            if v is None:
                continue
            s = str(v).strip()
            if s:
                out.append(s)
        return out
    s = str(value).strip()
    if not s:
        return []
    # YAML inline list-ish? import_pipeline.split_frontmatter_and_body
    # coerces values to strings, so a real ``tags: [a, b]`` arrives here
    # as the text ``[a, b]``. Tolerate that shape.
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1]
        return [
            part.strip().strip("'\"")
            for part in inner.split(",")
            if part.strip()
        ]
    # Whitespace or comma separated fallback.
    if "," in s:
        return [part.strip() for part in s.split(",") if part.strip()]
    return [s]


def _looks_like_attachment(target: str) -> bool:
    """Return True if ``target`` looks like a binary attachment reference
    rather than a note link."""
    if not target:
        return False
    # Strip query / fragment / alias parts.
    core = target.split("|", 1)[0].split("#", 1)[0].split("?", 1)[0].strip()
    if not core:
        return False
    suffix = Path(core).suffix.lower()
    if suffix == ".md":
        return False
    if suffix in _BINARY_ATTACHMENT_EXTS:
        return True
    # Anything with an extension other than .md and not an obvious URL
    # is treated as an attachment reference. Bare wiki targets (no
    # extension) are notes.
    if suffix and not core.startswith(("http://", "https://")):
        return True
    return False


def _attachment_name(target: str) -> str:
    core = target.split("|", 1)[0].split("#", 1)[0].split("?", 1)[0].strip()
    return core


def extract_obsidian_features(markdown: str, frontmatter: dict | None) -> dict:
    """Detect Obsidian features in a Markdown body / frontmatter pair.

    Returns a deterministic dict with sorted, de-duplicated lists:

        wikilinks       list[str]   ["[[Note]]", "[[Note|Alias]]", ...]
        embeds          list[str]   ["![[image.png]]", ...]
        tags            list[str]   ["security", "security/labs", ...]
        aliases         list[str]   ["Net notes", ...]
        callouts        list[str]   ["note", "warning", ...]
        attachment_refs list[str]   ["diagram.png", ...]
        warnings        list[str]   advisory notes for the UI

    The function is pure: it never reads files, never touches the
    network, and never raises on unexpected input.
    """
    text = markdown or ""
    fm = frontmatter or {}

    body_for_scan = _strip_code_fences(text)

    embeds_full: set[str] = set()
    embed_targets: set[str] = set()
    for match in _RE_EMBED.finditer(body_for_scan):
        embeds_full.add(f"![[{match.group(1)}]]")
        embed_targets.add(match.group(1).strip())

    wikilinks_full: set[str] = set()
    for match in _RE_WIKILINK.finditer(body_for_scan):
        wikilinks_full.add(f"[[{match.group(1)}]]")

    md_image_targets: set[str] = set()
    for match in _RE_MD_IMAGE.finditer(body_for_scan):
        md_image_targets.add(match.group(1).strip())

    callouts: set[str] = set()
    for match in _RE_CALLOUT.finditer(body_for_scan):
        callouts.add(match.group(1).strip().lower())

    block_refs: set[str] = set()
    for match in _RE_BLOCK_REF.finditer(body_for_scan):
        block_refs.add(match.group(1))

    inline_tags = _collect_inline_tags(body_for_scan)

    yaml_tags: list[str] = []
    if "tags" in fm:
        yaml_tags = _coerce_list(fm["tags"])
    elif "tag" in fm:
        yaml_tags = _coerce_list(fm["tag"])

    yaml_aliases: list[str] = []
    if "aliases" in fm:
        yaml_aliases = _coerce_list(fm["aliases"])
    elif "alias" in fm:
        yaml_aliases = _coerce_list(fm["alias"])

    all_tags = sorted({t.lstrip("#") for t in inline_tags} | {t.lstrip("#") for t in yaml_tags})
    aliases_sorted = sorted({a for a in yaml_aliases if a})
    wikilinks_sorted = sorted(wikilinks_full)
    embeds_sorted = sorted(embeds_full)
    callouts_sorted = sorted(callouts)
    block_refs_sorted = sorted(block_refs)

    # Attachment references: any embed target that doesn't look like a
    # note, plus any Markdown image target.
    attachment_set: set[str] = set()
    for target in embed_targets:
        if _looks_like_attachment(target):
            attachment_set.add(_attachment_name(target))
    for target in md_image_targets:
        if _looks_like_attachment(target):
            attachment_set.add(_attachment_name(target))
    attachment_refs = sorted(a for a in attachment_set if a)

    warnings: list[str] = []
    if wikilinks_sorted or embeds_sorted:
        warnings.append(
            "Obsidian wikilinks were preserved and may not resolve outside Obsidian."
        )
    if attachment_refs:
        warnings.append(
            "Attachment references were detected but binary files were not imported."
        )
    if yaml_tags or yaml_aliases:
        warnings.append(
            "Obsidian YAML tags/aliases were detected; only schema-compatible fields are written."
        )

    return {
        "wikilinks": wikilinks_sorted,
        "embeds": embeds_sorted,
        "tags": all_tags,
        "aliases": aliases_sorted,
        "callouts": callouts_sorted,
        "block_refs": block_refs_sorted,
        "attachment_refs": attachment_refs,
        "warnings": warnings,
    }


def _empty_obsidian_block() -> dict:
    return {
        "wikilinks": [],
        "embeds": [],
        "tags": [],
        "aliases": [],
        "callouts": [],
        "block_refs": [],
        "attachment_refs": [],
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Source staging
# ---------------------------------------------------------------------------


def _stage_sources_to_temp(
    source_dir: Path, sources: list[Path]
) -> tuple[Path, dict[str, Path]]:
    """Copy discovered Markdown sources into a fresh temp directory,
    preserving their relative paths under ``source_dir``.

    Returns ``(staging_dir, mapping)`` where ``mapping`` maps the
    staged absolute path (string) to the original source ``Path``.
    """
    staging = Path(tempfile.mkdtemp(prefix="cvault_obsidian_"))
    source_resolved = source_dir.resolve()
    mapping: dict[str, Path] = {}
    for src in sources:
        try:
            rel = src.relative_to(source_resolved)
        except ValueError:
            rel = Path(src.name)
        dst = staging / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except OSError as exc:
            logger.warning("could not stage %s: %s", src, exc)
            continue
        mapping[str(dst.resolve())] = src
    return staging, mapping


def _safe_read_text(path: Path, max_bytes: int = 5 * 1024 * 1024) -> str | None:
    """Best-effort UTF-8 read for feature extraction.

    Returns ``None`` if the file cannot be read or exceeds ``max_bytes``.
    Never raises.
    """
    try:
        if not path.is_file():
            return None
        size = path.stat().st_size
        if size > max_bytes:
            return None
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        if b"\x00" in raw:
            return None
        text = raw.decode("utf-8", errors="replace")
        return text.replace("\r\n", "\n").replace("\r", "\n")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Plan / orchestrator
# ---------------------------------------------------------------------------


def build_obsidian_import_plan(
    vault_name: str,
    source_dir: str,
    destination: str = DEFAULT_OBSIDIAN_DESTINATION,
    overwrite: bool = False,
) -> dict:
    """Build a dry-run import plan for an Obsidian vault folder.

    Convenience wrapper around :func:`import_obsidian_vault` with
    ``dry_run=True``. Returns the same response shape.
    """
    return import_obsidian_vault(
        vault_name=vault_name,
        source_dir=source_dir,
        destination=destination,
        dry_run=True,
        overwrite=overwrite,
    )


def import_obsidian_vault(
    vault_name: str,
    source_dir: str,
    destination: str = DEFAULT_OBSIDIAN_DESTINATION,
    dry_run: bool = True,
    overwrite: bool = False,
) -> dict:
    """Top-level entry point for the Obsidian vault import pipeline.

    Discovers ``.md`` files under ``source_dir``, skips ``.obsidian/``
    and other config / hidden / system folders, copies the discovered
    Markdown into a temp staging directory, delegates the actual import
    to :func:`core.shared.import_pipeline.import_markdown_folder`, then
    enriches each item with Obsidian-specific metadata and summary
    counts.

    The function always returns a structured response dict suitable for
    use as the HTTP / CLI body. It never raises on user-facing input
    errors and never writes binary attachments.
    """
    from core.shared.import_pipeline import (
        _MAX_SOURCE_BYTES,
        import_markdown_folder,
        split_frontmatter_and_body,
    )

    # Validate source_dir up front (mirror import_markdown_folder's checks
    # so we can still build an obsidian-shaped error envelope).
    if source_dir is None or not str(source_dir).strip():
        return {
            "status": "error",
            "error": {"code": "INVALID_SOURCE", "message": "source_dir is required"},
        }
    if "\x00" in str(source_dir):
        return {
            "status": "error",
            "error": {
                "code": "INVALID_SOURCE",
                "message": "source_dir must not contain null bytes",
            },
        }

    src_path = Path(str(source_dir)).expanduser()
    try:
        src_resolved = src_path.resolve(strict=False)
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

    # Discover obsidian-filtered Markdown sources.
    try:
        obsidian_sources = discover_obsidian_markdown_sources(src_resolved)
    except FileNotFoundError as exc:
        return {
            "status": "error",
            "error": {"code": "INVALID_SOURCE", "message": str(exc)},
        }

    # Stage to a fresh temp directory so the existing pipeline sees only
    # the filtered set of Markdown files. This makes all Phase 26A-D
    # hardening apply unchanged.
    staging, mapping = _stage_sources_to_temp(src_resolved, obsidian_sources)

    try:
        result = import_markdown_folder(
            vault_name=vault_name,
            source_dir=str(staging),
            destination=destination,
            dry_run=dry_run,
            overwrite=overwrite,
        )
    finally:
        # Always clean up the temp staging dir, even if the underlying
        # pipeline raised. The result no longer references it.
        try:
            shutil.rmtree(staging, ignore_errors=True)
        except OSError:
            pass

    if result.get("status") != "ok":
        # Surface the underlying error verbatim, but tag the source_type
        # so callers can distinguish obsidian errors in the UI.
        if isinstance(result, dict) and "data" in result:
            result["data"]["source_type"] = OBSIDIAN_SOURCE_TYPE_LABEL
        return result

    data = result["data"]

    # Build a quick lookup from absolute staging path back to the
    # original Obsidian source path.
    items = data.get("items", [])

    # Pre-read each original source body so feature extraction is
    # deterministic and independent of the staged copy.
    summary_wikilinks = 0
    summary_embeds = 0
    summary_attachments = 0
    summary_extra_warnings = 0

    for item in items:
        staged_path = item.get("source_path") or ""
        original = mapping.get(str(Path(staged_path).resolve())) if staged_path else None
        if original is not None:
            # Point the item back at the original Obsidian path so the
            # UI shows the real source. Keep using POSIX style.
            item["source_path"] = str(original)

        if original is None:
            item["obsidian"] = _empty_obsidian_block()
            continue

        text = _safe_read_text(original, max_bytes=_MAX_SOURCE_BYTES)
        if text is None:
            item["obsidian"] = _empty_obsidian_block()
            continue

        try:
            fm, body = split_frontmatter_and_body(text)
        except Exception:  # noqa: BLE001 — feature extraction never fails the item
            fm, body = {}, text

        features = extract_obsidian_features(body, fm)
        item["obsidian"] = features

        # Surface obsidian feature warnings into the item-level warnings
        # list so the UI's existing warning rendering picks them up.
        for w in features.get("warnings", []):
            if w not in item.get("warnings", []):
                item.setdefault("warnings", []).append(w)
                summary_extra_warnings += 1

        summary_wikilinks += len(features.get("wikilinks", []))
        summary_embeds += len(features.get("embeds", []))
        summary_attachments += len(features.get("attachment_refs", []))

    # Augment summary counts with Obsidian aggregates.
    summary = data.setdefault("summary", {})
    summary.setdefault("blocked", sum(1 for i in items if i.get("status") == "blocked"))
    summary["wikilinks"] = summary_wikilinks
    summary["embeds"] = summary_embeds
    summary["attachment_refs"] = summary_attachments
    if summary_extra_warnings:
        summary["warnings"] = sum(1 for i in items if i.get("warnings"))

    # Overwrite the surfaced source_dir with the user supplied path
    # (not the temp staging path) so the UI / CLI shows the real
    # Obsidian location.
    data["source_dir"] = str(src_resolved)
    data["source_type"] = OBSIDIAN_SOURCE_TYPE_LABEL

    return result
