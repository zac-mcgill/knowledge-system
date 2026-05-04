"""
Context Package Export — Phase 4

Writes a context bundle to disk as a portable, reproducible package.

Package layout:
    dist/context-bundles/<bundle-id>/
        context.json          Full bundle JSON
        context.md            Human-readable Markdown rendering
        manifest.json         Package manifest with SHA-256 file hashes
        validation.json       Validation status and warnings from bundle
        graph.json            Graph relationships from bundle
        feedback-summary.json Feedback entries relevant to bundle notes

Rules:
- Uses full vault-relative POSIX paths.
- Does not overwrite an existing package directory unless overwrite=True.
- Hashes all generated artefacts using SHA-256.
- Manifest hashes match actual written files (manifest.json excludes its own hash).
- Uses atomic-ish write strategy: files are written to a temp directory under
  the output root, then the temp directory is renamed to the final location.
  On failure, the temp directory is cleaned up.
- Does not write temporary or partial packages on failure.
- Does not include secrets scanning (Phase 5 concern).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Repo root is three levels up from this file:
#   core/shared/context_package.py → core/shared/ → core/ → <repo root>
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_OUTPUT_ROOT = _REPO_ROOT / "dist" / "context-bundles"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_info(data: bytes) -> dict:
    """Return sha256 hex digest and byte count for a bytes object."""
    return {"sha256": _sha256_bytes(data), "bytes": len(data)}


def _render_context_md(bundle: dict) -> str:
    """Render a human-readable Markdown representation of the bundle.

    Renders only structured data present in the bundle.  No prose is invented
    beyond fixed headings and labels.
    """
    lines: list[str] = []

    bundle_id = bundle.get("bundle_id", "unknown")
    vault = bundle.get("vault", "unknown")
    created_at = bundle.get("created_at", "")
    validation_status = bundle.get("validation_status", "unknown")
    budget = bundle.get("budget", {})
    warnings = bundle.get("warnings", [])
    notes = bundle.get("notes", [])
    source_paths = bundle.get("manifest", {}).get("source_paths", [])

    lines.append(f"# Context Bundle: {bundle_id}")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| Vault | {vault} |")
    lines.append(f"| Created | {created_at} |")
    lines.append(f"| Validation Status | {validation_status} |")
    lines.append(f"| Notes | {budget.get('note_count', len(notes))} |")
    used = budget.get("used_chars", 0)
    max_c = budget.get("max_chars", 0)
    truncated = budget.get("truncated", False)
    lines.append(f"| Budget Used | {used} / {max_c} chars |")
    lines.append(f"| Truncated | {str(truncated).lower()} |")
    lines.append("")

    lines.append("## Warnings")
    lines.append("")
    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("(none)")
    lines.append("")

    lines.append("## Source Notes")
    lines.append("")
    if source_paths:
        for p in source_paths:
            lines.append(f"- {p}")
    else:
        lines.append("(none)")
    lines.append("")

    for note in notes:
        path = note.get("path", "")
        fields = note.get("fields", {})
        sections = note.get("sections", {})
        body = note.get("body", "")

        lines.append("---")
        lines.append("")
        lines.append(f"## {path}")
        lines.append("")

        if fields:
            lines.append("**Fields:**")
            lines.append("")
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")
            for k, v in sorted(fields.items()):
                lines.append(f"| {k} | {v} |")
            lines.append("")

        for sec_name, sec_body in sections.items():
            lines.append(f"### {sec_name}")
            lines.append("")
            if sec_body:
                lines.append(sec_body.strip())
            else:
                lines.append("*(section not found)*")
            lines.append("")

        if body:
            lines.append("### Full Body")
            lines.append("")
            lines.append(body.strip())
            lines.append("")

    return "\n".join(lines)


def _build_validation_json(bundle: dict) -> dict:
    """Build validation.json content from bundle."""
    return {
        "validation_status": bundle.get("validation_status", "unknown"),
        "source_note_count": len(bundle.get("notes", [])),
        "warnings": bundle.get("warnings", []),
    }


def _build_graph_json(bundle: dict) -> dict:
    """Build graph.json content from bundle."""
    graph = bundle.get("graph", {})
    related = graph.get("related", {})
    return {"related": related}


def _build_feedback_summary_json(bundle: dict) -> dict:
    """Build feedback-summary.json content from bundle."""
    feedback = bundle.get("feedback", {})
    return {
        "entries": feedback.get("entries", []),
        "warnings": feedback.get("warnings", []),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_context_package(
    bundle: dict,
    output_root: str | Path | None = None,
    overwrite: bool = False,
) -> dict:
    """Write a context bundle to disk as a portable package.

    Args:
        bundle:      Bundle dict as returned by generate_bundle().
                     If the bundle has status="error", returns a structured
                     error immediately without writing any files.
        output_root: Root directory for packages.
                     Defaults to dist/context-bundles/ under the repo root.
                     The full package is written to:
                         <output_root>/<bundle_id>/
        overwrite:   If True, replace an existing package directory.
                     If False (default), return a structured error when the
                     package directory already exists.

    Returns:
        On success:
        {
            "status": "ok",
            "bundle_id": "<bundle_id>",
            "package_dir": "dist/context-bundles/<bundle_id>",
            "files": {
                "context.json":          {"sha256": "...", "bytes": N},
                "context.md":            {"sha256": "...", "bytes": N},
                "manifest.json":         {"sha256": "...", "bytes": N},
                "validation.json":       {"sha256": "...", "bytes": N},
                "graph.json":            {"sha256": "...", "bytes": N},
                "feedback-summary.json": {"sha256": "...", "bytes": N}
            },
            "warnings": [...]
        }

        On error:
        {
            "status": "error",
            "error": {"code": "...", "message": "..."}
        }

        Error codes:
            BUNDLE_ERROR      — The input bundle itself has status="error".
            MISSING_BUNDLE_ID — The bundle has no bundle_id field.
            PACKAGE_EXISTS    — Package already exists and overwrite=False.
    """
    # Reject bundles that are already error results.
    if bundle.get("status") == "error":
        return {
            "status": "error",
            "error": {
                "code": "BUNDLE_ERROR",
                "message": bundle.get("error", {}).get(
                    "message", "Bundle has error status"
                ),
            },
        }

    bundle_id = bundle.get("bundle_id")
    if not bundle_id:
        return {
            "status": "error",
            "error": {
                "code": "MISSING_BUNDLE_ID",
                "message": "Bundle has no bundle_id field",
            },
        }

    if output_root is None:
        out_root = _DEFAULT_OUTPUT_ROOT
    else:
        out_root = Path(output_root)

    final_dir = out_root / bundle_id

    # Check for an existing package.
    if final_dir.exists():
        if not overwrite:
            return {
                "status": "error",
                "error": {
                    "code": "PACKAGE_EXISTS",
                    "message": (
                        f"Package already exists at '{final_dir}'. "
                        "Use overwrite=True to replace it."
                    ),
                },
            }
        # Will overwrite — existing directory removed after successful write.

    # ------------------------------------------------------------------
    # Build all file contents in memory first (fail-fast before any I/O).
    # ------------------------------------------------------------------
    context_json_bytes = json.dumps(
        bundle, indent=2, ensure_ascii=False
    ).encode("utf-8")
    context_md_bytes = _render_context_md(bundle).encode("utf-8")
    validation_json_bytes = json.dumps(
        _build_validation_json(bundle), indent=2, ensure_ascii=False
    ).encode("utf-8")
    graph_json_bytes = json.dumps(
        _build_graph_json(bundle), indent=2, ensure_ascii=False
    ).encode("utf-8")
    feedback_json_bytes = json.dumps(
        _build_feedback_summary_json(bundle), indent=2, ensure_ascii=False
    ).encode("utf-8")

    # Compute file info (sha256 + size) for the five non-manifest files.
    files_info: dict[str, dict] = {
        "context.json": _file_info(context_json_bytes),
        "context.md": _file_info(context_md_bytes),
        "validation.json": _file_info(validation_json_bytes),
        "graph.json": _file_info(graph_json_bytes),
        "feedback-summary.json": _file_info(feedback_json_bytes),
    }

    # Build manifest (manifest.json does not include its own hash — circular).
    manifest: dict = {
        "bundle_id": bundle_id,
        "vault": bundle.get("vault", ""),
        "schema_version": bundle.get("manifest", {}).get("schema_version"),
        "created_at": bundle.get(
            "created_at", datetime.now(timezone.utc).isoformat()
        ),
        "source_notes": bundle.get("manifest", {}).get("source_paths", []),
        "validation_status": bundle.get("validation_status", "unknown"),
        "warnings": bundle.get("warnings", []),
        "files": files_info,
    }
    manifest_json_bytes = json.dumps(
        manifest, indent=2, ensure_ascii=False
    ).encode("utf-8")

    # ------------------------------------------------------------------
    # Atomic-ish write: write to temp dir, then rename to final_dir.
    # ------------------------------------------------------------------
    out_root.mkdir(parents=True, exist_ok=True)

    # Create temp dir in same parent so rename stays on same filesystem.
    tmp_dir_path: Path | None = None
    try:
        tmp_dir_str = tempfile.mkdtemp(
            dir=out_root, prefix=f"._tmp_{bundle_id}_"
        )
        tmp_dir_path = Path(tmp_dir_str)

        (tmp_dir_path / "context.json").write_bytes(context_json_bytes)
        (tmp_dir_path / "context.md").write_bytes(context_md_bytes)
        (tmp_dir_path / "validation.json").write_bytes(validation_json_bytes)
        (tmp_dir_path / "graph.json").write_bytes(graph_json_bytes)
        (tmp_dir_path / "feedback-summary.json").write_bytes(feedback_json_bytes)
        (tmp_dir_path / "manifest.json").write_bytes(manifest_json_bytes)

        # Remove existing final_dir if overwriting, then rename temp → final.
        if final_dir.exists():
            shutil.rmtree(final_dir)
        tmp_dir_path.rename(final_dir)
        tmp_dir_path = None  # Successfully moved — no cleanup needed.

    except BaseException:
        if tmp_dir_path is not None and tmp_dir_path.exists():
            shutil.rmtree(tmp_dir_path, ignore_errors=True)
        raise

    # ------------------------------------------------------------------
    # Build return value.
    # ------------------------------------------------------------------
    # Compute relative path for display (repo-relative POSIX).
    try:
        package_dir_display = (
            str(final_dir.relative_to(_REPO_ROOT)).replace("\\", "/")
        )
    except ValueError:
        package_dir_display = str(final_dir).replace("\\", "/")

    # Include manifest.json hash in the returned files dict.
    all_files_info = {
        **files_info,
        "manifest.json": _file_info(manifest_json_bytes),
    }

    return {
        "status": "ok",
        "bundle_id": bundle_id,
        "package_dir": package_dir_display,
        "files": all_files_info,
        "warnings": bundle.get("warnings", []),
    }
