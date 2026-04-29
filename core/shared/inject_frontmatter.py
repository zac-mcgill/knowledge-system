"""
YAML Frontmatter Injection Pipeline

Schema: v3.0.0 (Unified)
Python: 3.13+ (stdlib only)

Deterministic transformation engine.
Every field is derived from file path and content.
No external dependencies. No data loss. Full idempotency.

Usage:
    python inject_frontmatter.py                # live run
    python inject_frontmatter.py --dry-run      # preview only
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from core.shared import load_schema as _load_schema, _resolve_vault_path

# ============================================================================
# PHASE 2 — PARSING (strip existing YAML)
# ============================================================================


def strip_existing_yaml(content: str) -> str:
    """Remove existing YAML frontmatter block if present."""
    if not content.startswith("---\n"):
        return content

    close_idx = content.find("\n---\n", 4)
    if close_idx == -1:
        if content.endswith("\n---"):
            close_idx = len(content) - 4
        else:
            return content

    remainder_start = close_idx + len("\n---\n")
    if close_idx == len(content) - 4:
        remainder_start = len(content)

    remainder = content[remainder_start:]
    if remainder.startswith("\n"):
        remainder = remainder[1:]
    return remainder


# ============================================================================
# PHASE 4 — VALIDATION
# ============================================================================


def validate_metadata(
    metadata: dict,
    path_parts: list[str],
    content: str,
    filename: str,
    schema,
) -> list[str]:
    """Validate all schema rules. Returns list of violation descriptions."""
    errors: list[str] = []

    note_type = metadata["type"]
    domain = metadata["domain"]
    subdomain = metadata["subdomain"]
    topic = metadata.get("topic")
    status = metadata["status"]
    difficulty = metadata["difficulty"]

    # V-01: type enum
    if note_type not in schema.VALID_TYPES:
        errors.append(f"V-01: type '{note_type}' not in enum")
    # V-02: domain enum
    if domain not in schema.schema.VALID_DOMAINS:
        errors.append(f"V-02: domain '{domain}' not in enum")
    # V-03: subdomain enum
    if subdomain is not None and subdomain not in schema.VALID_SUBDOMAINS:
        errors.append(f"V-03: subdomain '{subdomain}' not in enum")
    # V-04: topic presence/absence and enum
    depth = len(path_parts)
    if depth >= 4:
        if topic is None:
            errors.append("V-04: topic MUST be present for depth-4 file")
        elif topic not in schema.VALID_TOPICS:
            errors.append(f"V-04: topic '{topic}' not in enum")
    else:
        if topic is not None:
            errors.append("V-04: topic MUST NOT be present for depth-3 file")
    # V-05: status enum
    if status not in schema.VALID_STATUSES:
        errors.append(f"V-05: status '{status}' not in enum")
    # V-09: difficulty enum
    if difficulty not in schema.VALID_DIFFICULTIES:
        errors.append(f"V-09: difficulty '{difficulty}' not in enum")

    # V-06, V-07, V-08: boolean field presence
    if note_type == "core-concept":
        for field_name in ("has_key_principles", "has_how_it_works", "has_tradeoffs"):
            if field_name not in metadata:
                errors.append(f"{field_name} MUST exist for core-concept")
            elif metadata[field_name] not in (True, False):
                errors.append(f"{field_name} must be bool, got {type(metadata[field_name])}")
    else:
        for field_name in ("has_key_principles", "has_how_it_works", "has_tradeoffs"):
            if field_name in metadata:
                errors.append(f"{field_name} MUST NOT exist for {note_type}")

    # C-01: type derivation consistency
    derived_type = schema.derive_type(filename)
    if note_type != derived_type:
        errors.append(f"C-01: type mismatch: got '{note_type}', expected '{derived_type}'")

    # C-02: domain derivation
    try:
        expected_domain = schema.derive_domain(path_parts)
        if domain != expected_domain:
            errors.append(f"C-02: domain mismatch: got '{domain}', expected '{expected_domain}'")
    except ValueError as e:
        errors.append(f"C-02: {e}")

    # C-03 + C-04: subdomain derivation and parent constraint
    try:
        subdomain_result = schema.derive_subdomain(path_parts)
        if subdomain_result is not None:
            expected_subdomain, expected_parent_domain = subdomain_result
            if subdomain != expected_subdomain:
                errors.append(f"C-03: subdomain mismatch: got '{subdomain}', expected '{expected_subdomain}'")
            if expected_parent_domain != domain:
                errors.append(f"C-04: domain-subdomain parent mismatch: subdomain parent='{expected_parent_domain}', domain='{domain}'")
        else:
            if subdomain is not None:
                errors.append(f"C-03: subdomain should be None for L1-only file, got '{subdomain}'")
    except ValueError as e:
        errors.append(f"C-03: {e}")

    # C-05 + C-06: topic derivation and parent constraint
    try:
        topic_result = schema.derive_topic(path_parts)
        if topic_result is not None:
            expected_topic, expected_parent_sub = topic_result
            if topic != expected_topic:
                errors.append(f"C-05: topic mismatch: got '{topic}', expected '{expected_topic}'")
            if expected_parent_sub != subdomain:
                errors.append(f"C-06: subdomain-topic parent mismatch: topic parent='{expected_parent_sub}', subdomain='{subdomain}'")
        elif topic is not None:
            errors.append(f"C-05: topic present but file depth < 4")
    except ValueError as e:
        errors.append(f"C-05: {e}")

    # C-07, C-08, C-09, C-10, C-11: section detection + status consistency
    if note_type == "core-concept":
        expected_kp = schema.detect_section_content(content, "## Key Principles")
        expected_hw = schema.detect_section_content(content, "## How It Works")
        expected_to = schema.detect_section_content(content, "## Trade-offs")
        if metadata.get("has_key_principles") != expected_kp:
            errors.append(f"C-07: has_key_principles mismatch: got {metadata.get('has_key_principles')}, expected {expected_kp}")
        if metadata.get("has_how_it_works") != expected_hw:
            errors.append(f"C-08: has_how_it_works mismatch: got {metadata.get('has_how_it_works')}, expected {expected_hw}")
        if metadata.get("has_tradeoffs") != expected_to:
            errors.append(f"C-09: has_tradeoffs mismatch: got {metadata.get('has_tradeoffs')}, expected {expected_to}")
        expected_status = "complete" if (expected_kp and expected_hw and expected_to) else "partial"
        if status != expected_status:
            errors.append(f"C-10: status mismatch: got '{status}', expected '{expected_status}'")
    else:
        if status != "complete":
            errors.append(f"C-11: {note_type} status must be 'complete', got '{status}'")

    # C-12: difficulty derivation
    try:
        expected_diff = schema.derive_difficulty(subdomain, topic)
        if difficulty != expected_diff:
            errors.append(f"C-12: difficulty mismatch: got '{difficulty}', expected '{expected_diff}'")
    except ValueError as e:
        errors.append(f"C-12: {e}")

    return errors


# ============================================================================
# PHASE 5 — YAML GENERATION
# ============================================================================


def build_yaml_block(metadata: dict) -> str:
    """Assemble the YAML frontmatter block as a string."""
    lines = ["---"]
    lines.append(f"type: {metadata['type']}")
    lines.append(f"domain: {metadata['domain']}")
    if metadata.get("subdomain") is not None:
        lines.append(f"subdomain: {metadata['subdomain']}")
    if "topic" in metadata:
        lines.append(f"topic: {metadata['topic']}")
    lines.append(f"status: {metadata['status']}")
    if metadata["type"] == "core-concept":
        lines.append(f"has_key_principles: {str(metadata['has_key_principles']).lower()}")
        lines.append(f"has_how_it_works: {str(metadata['has_how_it_works']).lower()}")
        lines.append(f"has_tradeoffs: {str(metadata['has_tradeoffs']).lower()}")
    lines.append(f"difficulty: {metadata['difficulty']}")
    lines.append("---")
    return "\n".join(lines)


# ============================================================================
# PHASE 6 — SAFE WRITE
# ============================================================================


def atomic_write(filepath: Path, content: str) -> None:
    """Write content to file atomically via temp file + rename."""
    encoded = content.encode("utf-8")
    dir_path = filepath.parent
    fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
    try:
        os.write(fd, encoded)
        os.close(fd)
        fd = -1
        os.replace(tmp_path, str(filepath))
    except BaseException:
        if fd != -1:
            os.close(fd)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ============================================================================
# PIPELINE ORCHESTRATOR
# ============================================================================


def process_file(
    filepath: Path,
    root: Path,
    dry_run: bool,
    warnings: list[str],
    schema,
) -> tuple[str, str | None]:
    """Process a single file through the full pipeline.

    Returns:
        ("modified", None)    — file was written (or would be in dry-run)
        ("unchanged", None)   — file already has correct frontmatter
        ("error", message)    — file skipped due to error
    """
    rel = filepath.relative_to(root)
    path_parts = list(rel.parts)
    filename = path_parts[-1]

    # --- Phase 2: Read & parse ---
    try:
        raw_content = schema.read_file_safe(filepath)
    except Exception as e:
        return ("error", f"Read failed: {e}")

    content_body = strip_existing_yaml(raw_content)

    # --- Phase 3: Derive metadata ---
    try:
        note_type = schema.derive_type(filename)
        domain = schema.derive_domain(path_parts)
        subdomain_result = schema.derive_subdomain(path_parts)

        subdomain_val: str | None = None
        if subdomain_result is not None:
            subdomain_val, subdomain_parent = subdomain_result
            if subdomain_parent != domain:
                return ("error", f"C-04: subdomain parent '{subdomain_parent}' != domain '{domain}'")

        topic_result = schema.derive_topic(path_parts)
        topic_val: str | None = None
        if topic_result is not None:
            topic_val, topic_parent = topic_result
            if topic_parent != subdomain_val:
                return ("error", f"C-06: topic parent '{topic_parent}' != subdomain '{subdomain_val}'")

        difficulty = schema.derive_difficulty(subdomain_val, topic_val)

    except ValueError as e:
        return ("error", f"Derivation failed: {e}")

    # Section detection (core-concept only)
    metadata: dict = {
        "type": note_type,
        "domain": domain,
        "subdomain": subdomain_val,
        "status": "",
        "difficulty": difficulty,
    }

    if topic_val is not None:
        metadata["topic"] = topic_val

    if note_type == "core-concept":
        kp = schema.detect_section_content(content_body, "## Key Principles")
        hw = schema.detect_section_content(content_body, "## How It Works")
        to = schema.detect_section_content(content_body, "## Trade-offs")
        metadata["has_key_principles"] = kp
        metadata["has_how_it_works"] = hw
        metadata["has_tradeoffs"] = to
        metadata["status"] = "complete" if (kp and hw and to) else "partial"

        for heading_name, heading_str in [
            ("Key Principles", "## Key Principles"),
            ("How It Works", "## How It Works"),
            ("Trade-offs", "## Trade-offs"),
        ]:
            lines = content_body.split("\n")
            found = any(line.rstrip() == heading_str for line in lines)
            if not found:
                warnings.append(f"  WARN: {rel} — heading '{heading_str}' not found in file")
    else:
        metadata["status"] = "complete"

    # --- Phase 4: Validate ---
    errors = validate_metadata(metadata, path_parts, content_body, filename, schema)
    if errors:
        return ("error", "; ".join(errors))

    # --- Phase 5: Generate YAML ---
    yaml_block = build_yaml_block(metadata)

    # --- Assemble output ---
    output = yaml_block + "\n\n" + content_body

    # File ends with single trailing newline
    output = output.rstrip("\n") + "\n"

    # --- Idempotency check ---
    if output == raw_content:
        return ("unchanged", None)

    # --- Phase 6: Write ---
    if not dry_run:
        atomic_write(filepath, output)

    return ("modified", None)


def main(vault_path: Path | None = None) -> int:
    if vault_path is None:
        vault_path = _resolve_vault_path()
    _schema = _load_schema(vault_path)

    dry_run = "--dry-run" in sys.argv

    mode_label = "DRY RUN" if dry_run else "LIVE RUN"
    print(f"{'='*60}")
    print(f"YAML Frontmatter Injection Pipeline — {mode_label}")
    print(f"Schema: v3.0.0 (Unified)")
    print(f"Vault:  {_schema.VAULT_ROOT}")
    print(f"{'='*60}")
    print()

    files = _schema.discover_files(_schema.VAULT_ROOT)
    print(f"Files discovered: {len(files)}")
    print()

    modified = 0
    unchanged = 0
    errored = 0
    error_details: list[str] = []
    warnings: list[str] = []

    for filepath in files:
        rel = filepath.relative_to(_schema.VAULT_ROOT)
        result, detail = process_file(filepath, _schema.VAULT_ROOT, dry_run, warnings, _schema)

        if result == "modified":
            modified += 1
        elif result == "unchanged":
            unchanged += 1
        elif result == "error":
            errored += 1
            error_details.append(f"  FAIL: {rel} — {detail}")

    print(f"{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"  Total files:  {len(files)}")
    print(f"  Modified:     {modified}")
    print(f"  Unchanged:    {unchanged}")
    print(f"  Errors:       {errored}")
    print()

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(w)
        print()

    if error_details:
        print(f"ERRORS ({errored}):")
        for e in error_details:
            print(e)
        print()

    if errored > 0:
        print("Pipeline completed with errors. No files were modified for failed entries.")
        return 1

    verb = "would be modified" if dry_run else "modified"
    print(f"Pipeline completed successfully. {modified} files {verb}, {unchanged} unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
