"""
Vault Validation Engine

Enforces full schema integrity across all content files.
Read-only — never modifies files.

Usage:
    python validate_vault.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from mcp.core.schema_loader import load_schema as _load_schema
from core.shared import _resolve_vault_path

# ============================================================================
# STRICT SECTION QUALITY VALIDATORS
# ============================================================================

_NUMBERED_STEP = re.compile(r"^\d+\.\s+")

# ISO date pattern for Phase 25 trust metadata validation
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_trust_fields(fields: dict, errors: list, schema) -> None:
    """Validate optional Phase 25 trust/staleness metadata fields.

    These fields are optional; validation only runs if a field is present
    and non-empty. Missing fields are always accepted (backwards-compatible).
    """
    # trust_level — if present, must be a valid value
    trust_level = fields.get("trust_level")
    if trust_level is not None and str(trust_level).strip():
        valid_levels = getattr(schema, "VALID_TRUST_LEVELS", None) or frozenset({
            "verified", "working", "draft", "external", "deprecated",
        })
        if str(trust_level).strip().lower() not in valid_levels:
            errors.append(
                f"Invalid trust_level: {trust_level!r}. "
                f"Allowed: {sorted(valid_levels)}"
            )

    # source_type — if present, must be a valid value
    source_type = fields.get("source_type")
    if source_type is not None and str(source_type).strip():
        valid_types = getattr(schema, "VALID_SOURCE_TYPES", None) or frozenset({
            "authored", "imported", "generated", "agent_suggested",
        })
        if str(source_type).strip().lower() not in valid_types:
            errors.append(
                f"Invalid source_type: {source_type!r}. "
                f"Allowed: {sorted(valid_types)}"
            )

    # last_reviewed — if present, must be ISO YYYY-MM-DD
    last_reviewed = fields.get("last_reviewed")
    if last_reviewed is not None and str(last_reviewed).strip():
        s = str(last_reviewed).strip()
        if not _ISO_DATE_RE.match(s):
            errors.append(
                f"Invalid last_reviewed date: {last_reviewed!r}. "
                "Expected format: YYYY-MM-DD"
            )
        else:
            try:
                from datetime import date
                date.fromisoformat(s)
            except ValueError:
                errors.append(
                    f"Invalid last_reviewed date value: {last_reviewed!r}"
                )

    # review_after — if present, must be ISO YYYY-MM-DD
    review_after = fields.get("review_after")
    if review_after is not None and str(review_after).strip():
        s = str(review_after).strip()
        if not _ISO_DATE_RE.match(s):
            errors.append(
                f"Invalid review_after date: {review_after!r}. "
                "Expected format: YYYY-MM-DD"
            )
        else:
            try:
                from datetime import date
                date.fromisoformat(s)
            except ValueError:
                errors.append(
                    f"Invalid review_after date value: {review_after!r}"
                )


def validate_how_it_works(body: str, schema) -> str | None:
    """Return an error string if ## How It Works fails strict validation."""
    section = schema.extract_section_body(body, "## How It Works")
    if section is None:
        return "Missing section: ## How It Works"
    steps = [line for line in section.split("\n") if _NUMBERED_STEP.match(line)]
    if len(steps) == 0:
        return "How It Works contains no numbered steps"
    if len(steps) < 3:
        return f"How It Works has only {len(steps)} numbered step(s) (minimum 3)"
    return None


def validate_tradeoffs(body: str, schema) -> str | None:
    """Return an error string if ## Trade-offs fails strict validation."""
    section = schema.extract_section_body(body, "## Trade-offs")
    if section is None:
        return "Missing section: ## Trade-offs"
    lines = [line for line in section.split("\n") if line.strip()]
    table_lines = [l for l in lines if l.strip().startswith("|")]
    if len(table_lines) < 5:
        return (
            f"Trade-offs table has {max(0, len(table_lines) - 2)} data row(s) "
            f"(minimum 3)"
        )
    header = table_lines[0]
    cells = [c.strip().lower() for c in header.split("|")]
    cells = [c for c in cells if c]
    if cells != ["aspect", "benefit", "cost"]:
        return (
            f"Trade-offs header must be '| Aspect | Benefit | Cost |', "
            f"got: {header.strip()}"
        )
    separator = table_lines[1]
    if not re.match(r"^\|[\s\-:|]+\|[\s\-:|]+\|[\s\-:|]+\|$", separator.strip()):
        return f"Trade-offs separator row is malformed: {separator.strip()}"
    return None


# ============================================================================
# VALIDATION ENGINE
# ============================================================================


def validate_file(filepath: Path, root: Path, schema) -> list[str]:
    """Run all validation checks on a single file. Returns list of errors."""
    errors: list[str] = []
    rel = filepath.relative_to(root)
    path_parts = list(rel.parts)
    filename = path_parts[-1]

    # Read
    try:
        content = schema.read_file_safe(filepath)
    except Exception as e:
        return [f"Read error: {e}"]

    # ── YAML existence and integrity ──
    try:
        fields, body = schema.parse_yaml_frontmatter(content)
    except ValueError as exc:
        return [str(exc)]  # "Malformed YAML: <reason>"
    if fields is None:
        return ["Missing or invalid YAML frontmatter"]

    # ── Unknown fields ──
    unknown = set(fields.keys()) - schema.ALL_KNOWN_FIELDS
    if unknown:
        errors.append(f"Unknown fields: {sorted(unknown)}")

    # ── Type ──
    note_type = fields.get("type")
    if note_type is None:
        errors.append("Missing field: type")
        return errors
    if note_type not in schema.VALID_TYPES:
        errors.append(f"Invalid type: '{note_type}'")
        return errors

    # ── Required fields check ──
    depth = len(path_parts)
    if note_type == "core-concept":
        expected_fields = schema.CORE_CONCEPT_FIELDS_WITH_TOPIC if depth >= 4 else schema.CORE_CONCEPT_FIELDS
    else:
        expected_fields = schema.PATTERN_TECHNIQUE_FIELDS

    for field_name in expected_fields:
        if field_name == "subdomain" and depth < 3:
            continue
        if field_name not in fields:
            errors.append(f"Missing required field: {field_name}")

    # Fields that MUST NOT be present
    if note_type != "core-concept":
        for banned in ("has_key_principles", "has_how_it_works", "has_tradeoffs"):
            if banned in fields:
                errors.append(f"Field '{banned}' must not exist on {note_type}")
    if depth < 4 and "topic" in fields:
        errors.append("Field 'topic' must not exist on depth-3 file")
    if depth >= 4 and "topic" not in fields:
        errors.append("Field 'topic' must exist on depth-4 file")

    # ── Enum validation ──
    domain = fields.get("domain")
    if domain is not None and domain not in schema.VALID_DOMAINS:
        errors.append(f"Invalid domain: '{domain}'")

    subdomain = fields.get("subdomain")
    if subdomain is not None and subdomain not in schema.VALID_SUBDOMAINS:
        errors.append(f"Invalid subdomain: '{subdomain}'")

    topic = fields.get("topic")
    if topic is not None and topic not in schema.VALID_TOPICS:
        errors.append(f"Invalid topic: '{topic}'")

    status = fields.get("status")
    if status is not None and status not in schema.VALID_STATUSES:
        errors.append(f"Invalid status: '{status}'")

    difficulty = fields.get("difficulty")
    if difficulty is not None and difficulty not in schema.VALID_DIFFICULTIES:
        errors.append(f"Invalid difficulty: '{difficulty}'")

    # ── Phase 25: optional trust metadata field validation ──
    # These fields are optional; if present they must have valid values.
    _validate_trust_fields(fields, errors, schema)

    # ── Derivation consistency ──

    # Type derivation
    expected_type = schema.derive_type(filename)
    if note_type != expected_type:
        errors.append(f"Type mismatch: YAML='{note_type}', derived='{expected_type}'")

    # Domain derivation
    try:
        expected_domain = schema.derive_domain(path_parts)
        if domain != expected_domain:
            errors.append(f"Domain mismatch: YAML='{domain}', derived='{expected_domain}'")
    except ValueError as e:
        errors.append(f"Domain derivation error: {e}")

    # Subdomain derivation + parent constraint
    try:
        subdomain_result = schema.derive_subdomain(path_parts)
        if subdomain_result is not None:
            expected_sub, expected_parent_domain = subdomain_result
            if subdomain != expected_sub:
                errors.append(f"Subdomain mismatch: YAML='{subdomain}', derived='{expected_sub}'")
            if domain != expected_parent_domain:
                errors.append(f"Domain-subdomain parent mismatch: domain='{domain}', expected parent='{expected_parent_domain}'")
        else:
            if subdomain is not None:
                errors.append(f"Subdomain should be None for L1-only file, got '{subdomain}'")
    except ValueError as e:
        errors.append(f"Subdomain derivation error: {e}")

    # Topic derivation + parent constraint
    try:
        topic_result = schema.derive_topic(path_parts)
        if topic_result is not None:
            expected_topic, expected_parent_sub = topic_result
            if topic != expected_topic:
                errors.append(f"Topic mismatch: YAML='{topic}', derived='{expected_topic}'")
            if subdomain != expected_parent_sub:
                errors.append(f"Subdomain-topic parent mismatch: subdomain='{subdomain}', expected parent='{expected_parent_sub}'")
    except ValueError as e:
        errors.append(f"Topic derivation error: {e}")

    # Difficulty derivation
    try:
        expected_diff = schema.derive_difficulty(
            str(subdomain) if subdomain else None,
            str(topic) if topic else None,
        )
        if difficulty != expected_diff:
            errors.append(f"Difficulty mismatch: YAML='{difficulty}', derived='{expected_diff}'")
    except ValueError as e:
        errors.append(f"Difficulty derivation error: {e}")

    # ── Boolean field validation (core-concept only) ──
    if note_type == "core-concept":
        for heading, field_name in [
            ("## Key Principles", "has_key_principles"),
            ("## How It Works", "has_how_it_works"),
            ("## Trade-offs", "has_tradeoffs"),
        ]:
            expected = schema.detect_section_content(body, heading)
            actual = fields.get(field_name)
            if actual is not None and actual != expected:
                errors.append(
                    f"{field_name} mismatch: YAML={actual}, detected={expected}"
                )

        # Status derivation
        kp = fields.get("has_key_principles", False)
        hw = fields.get("has_how_it_works", False)
        to = fields.get("has_tradeoffs", False)
        expected_status = "complete" if (kp and hw and to) else "partial"
        if status != expected_status:
            errors.append(f"Status mismatch: YAML='{status}', derived='{expected_status}'")
    else:
        if status not in schema.VALID_STATUSES:
            errors.append(f"{note_type} status must be in VALID_STATUSES, got '{status}'")

    # ── Structural validation: canonical sections ──
    headings_in_file = schema.find_headings(body)
    expected_sections = schema.SECTION_MAP.get(note_type, ())
    optional_sections = schema.OPTIONAL_SECTION_MAP.get(note_type, ())

    for section in expected_sections:
        if section not in headings_in_file:
            errors.append(f"Missing canonical section: '{section}'")

    # Check for non-canonical headings
    canonical_set = set(expected_sections) | set(optional_sections)
    for h in headings_in_file:
        if h not in canonical_set:
            errors.append(f"Non-canonical heading: '{h}'")

    # ── Strict section quality (core-concept only) ──
    if note_type == "core-concept":
        hw_err = validate_how_it_works(body, schema)
        if hw_err:
            errors.append(hw_err)
        to_err = validate_tradeoffs(body, schema)
        if to_err:
            errors.append(to_err)

    # ── Configurable minimum section content ──
    if schema.MIN_SECTION_CONTENT_CHARS > 0:
        for section_heading in schema.SECTION_MAP.get(note_type, ()):
            section_body = schema.extract_section_body(body, section_heading)
            if section_body is not None and len(section_body.strip()) < schema.MIN_SECTION_CONTENT_CHARS:
                errors.append(
                    f"Section '{section_heading}' has fewer than "
                    f"{schema.MIN_SECTION_CONTENT_CHARS} character(s) of content"
                )

    return errors


# ============================================================================
# MAIN
# ============================================================================


def main(vault_path: Path | None = None) -> int:
    if vault_path is None:
        vault_path = _resolve_vault_path()
    _schema = _load_schema(vault_path)

    print(f"{'='*60}")
    print("Vault Validation Engine")
    print(f"Schema: v3.0.0 (Unified)")
    print(f"Vault:  {_schema.VAULT_ROOT}")
    print(f"{'='*60}")
    print()

    files = _schema.discover_files(_schema.VAULT_ROOT)
    print(f"Files discovered: {len(files)}")
    print()

    valid_count = 0
    invalid_count = 0
    all_errors: list[tuple[str, list[str]]] = []

    for filepath in files:
        rel = str(filepath.relative_to(_schema.VAULT_ROOT))
        errors = validate_file(filepath, _schema.VAULT_ROOT, _schema)
        if errors:
            invalid_count += 1
            all_errors.append((rel, errors))
        else:
            valid_count += 1

    # Report
    print(f"{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"  Total checked: {len(files)}")
    print(f"  Valid:          {valid_count}")
    print(f"  Invalid:        {invalid_count}")
    print()

    if all_errors:
        print(f"FAILURES ({invalid_count}):")
        print()
        for rel_path, errors in all_errors:
            print(f"  {rel_path}")
            for err in errors:
                print(f"    - {err}")
            print()

    if invalid_count > 0:
        print("Validation FAILED.")
        return 1

    print("Validation PASSED. All files are schema-compliant.")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
