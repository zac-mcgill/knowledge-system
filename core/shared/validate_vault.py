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

from core.shared import load_schema as _load_schema

_schema = _load_schema()

ALL_KNOWN_FIELDS = _schema.ALL_KNOWN_FIELDS
CORE_CONCEPT_FIELDS = _schema.CORE_CONCEPT_FIELDS
CORE_CONCEPT_FIELDS_WITH_TOPIC = _schema.CORE_CONCEPT_FIELDS_WITH_TOPIC
OPTIONAL_SECTION_MAP = _schema.OPTIONAL_SECTION_MAP
PATTERN_TECHNIQUE_FIELDS = _schema.PATTERN_TECHNIQUE_FIELDS
SECTION_MAP = _schema.SECTION_MAP
VALID_DIFFICULTIES = _schema.VALID_DIFFICULTIES
VALID_DOMAINS = _schema.VALID_DOMAINS
VALID_STATUSES = _schema.VALID_STATUSES
VALID_SUBDOMAINS = _schema.VALID_SUBDOMAINS
VALID_TOPICS = _schema.VALID_TOPICS
VALID_TYPES = _schema.VALID_TYPES
VAULT_ROOT = _schema.VAULT_ROOT
derive_difficulty = _schema.derive_difficulty
derive_domain = _schema.derive_domain
derive_subdomain = _schema.derive_subdomain
derive_topic = _schema.derive_topic
derive_type = _schema.derive_type
detect_section_content = _schema.detect_section_content
discover_files = _schema.discover_files
extract_section_body = _schema.extract_section_body
find_headings = _schema.find_headings
parse_yaml_frontmatter = _schema.parse_yaml_frontmatter
read_file_safe = _schema.read_file_safe

# ============================================================================
# STRICT SECTION QUALITY VALIDATORS
# ============================================================================

_NUMBERED_STEP = re.compile(r"^\d+\.\s+")


def validate_how_it_works(body: str) -> str | None:
    """Return an error string if ## How It Works fails strict validation."""
    section = extract_section_body(body, "## How It Works")
    if section is None:
        return "Missing section: ## How It Works"
    steps = [line for line in section.split("\n") if _NUMBERED_STEP.match(line)]
    if len(steps) == 0:
        return "How It Works contains no numbered steps"
    if len(steps) < 3:
        return f"How It Works has only {len(steps)} numbered step(s) (minimum 3)"
    return None


def validate_tradeoffs(body: str) -> str | None:
    """Return an error string if ## Trade-offs fails strict validation."""
    section = extract_section_body(body, "## Trade-offs")
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


def validate_file(filepath: Path, root: Path) -> list[str]:
    """Run all validation checks on a single file. Returns list of errors."""
    errors: list[str] = []
    rel = filepath.relative_to(root)
    path_parts = list(rel.parts)
    filename = path_parts[-1]

    # Read
    try:
        content = read_file_safe(filepath)
    except Exception as e:
        return [f"Read error: {e}"]

    # ── YAML existence ──
    fields, body = parse_yaml_frontmatter(content)
    if fields is None:
        return ["No YAML frontmatter found"]

    # ── Unknown fields ──
    unknown = set(fields.keys()) - ALL_KNOWN_FIELDS
    if unknown:
        errors.append(f"Unknown fields: {sorted(unknown)}")

    # ── Type ──
    note_type = fields.get("type")
    if note_type is None:
        errors.append("Missing field: type")
        return errors
    if note_type not in VALID_TYPES:
        errors.append(f"Invalid type: '{note_type}'")
        return errors

    # ── Required fields check ──
    depth = len(path_parts)
    if note_type == "core-concept":
        expected_fields = CORE_CONCEPT_FIELDS_WITH_TOPIC if depth >= 4 else CORE_CONCEPT_FIELDS
    else:
        expected_fields = PATTERN_TECHNIQUE_FIELDS

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
    if domain is not None and domain not in VALID_DOMAINS:
        errors.append(f"Invalid domain: '{domain}'")

    subdomain = fields.get("subdomain")
    if subdomain is not None and subdomain not in VALID_SUBDOMAINS:
        errors.append(f"Invalid subdomain: '{subdomain}'")

    topic = fields.get("topic")
    if topic is not None and topic not in VALID_TOPICS:
        errors.append(f"Invalid topic: '{topic}'")

    status = fields.get("status")
    if status is not None and status not in VALID_STATUSES:
        errors.append(f"Invalid status: '{status}'")

    difficulty = fields.get("difficulty")
    if difficulty is not None and difficulty not in VALID_DIFFICULTIES:
        errors.append(f"Invalid difficulty: '{difficulty}'")

    # ── Derivation consistency ──

    # Type derivation
    expected_type = derive_type(filename)
    if note_type != expected_type:
        errors.append(f"Type mismatch: YAML='{note_type}', derived='{expected_type}'")

    # Domain derivation
    try:
        expected_domain = derive_domain(path_parts)
        if domain != expected_domain:
            errors.append(f"Domain mismatch: YAML='{domain}', derived='{expected_domain}'")
    except ValueError as e:
        errors.append(f"Domain derivation error: {e}")

    # Subdomain derivation + parent constraint
    try:
        subdomain_result = derive_subdomain(path_parts)
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
        topic_result = derive_topic(path_parts)
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
        expected_diff = derive_difficulty(
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
            expected = detect_section_content(body, heading)
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
        if status not in VALID_STATUSES:
            errors.append(f"{note_type} status must be in VALID_STATUSES, got '{status}'")

    # ── Structural validation: canonical sections ──
    headings_in_file = find_headings(body)
    expected_sections = SECTION_MAP.get(note_type, ())
    optional_sections = OPTIONAL_SECTION_MAP.get(note_type, ())

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
        hw_err = validate_how_it_works(body)
        if hw_err:
            errors.append(hw_err)
        to_err = validate_tradeoffs(body)
        if to_err:
            errors.append(to_err)

    return errors


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:
    print(f"{'='*60}")
    print("Vault Validation Engine")
    print(f"Schema: v3.0.0 (Unified)")
    print(f"Vault:  {VAULT_ROOT}")
    print(f"{'='*60}")
    print()

    files = discover_files(VAULT_ROOT)
    print(f"Files discovered: {len(files)}")
    print()

    valid_count = 0
    invalid_count = 0
    all_errors: list[tuple[str, list[str]]] = []

    for filepath in files:
        rel = str(filepath.relative_to(VAULT_ROOT))
        errors = validate_file(filepath, VAULT_ROOT)
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
