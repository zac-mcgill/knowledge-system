"""
vault_schema.py — Single Source of Truth
Demo Vault

Schema: v3.0.0 (Unified)
Python: 3.10+ (requires PyYAML)

This file is the ONLY authoritative definition of:
  - all enums
  - all section name lists
  - all mapping tables
  - all validation rules
  - all derivation logic

No other file may define, duplicate, or override these constants.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

# ============================================================================
# CONFIGURATION
# ============================================================================

_SCRIPTS_DIR = Path(__file__).resolve().parent        # Vault Files/Scripts/
_VAULT_FILES_DIR = _SCRIPTS_DIR.parent                # Vault Files/
VAULT_ROOT = _VAULT_FILES_DIR.parent                  # <vault root>/
OUTPUT_DIR = _VAULT_FILES_DIR                         # Vault Files/

EXCLUDE_DIRS = frozenset({"Vault Files"})
EXCLUDE_FILENAMES = frozenset({"Index.md", "Demo Vault Report.md"})

# Minimum non-whitespace characters required in each canonical section body.
# Set to 0 to disable (header presence is still enforced).
# Set to a positive integer to require substantive content per section.
MIN_SECTION_CONTENT_CHARS: int = 0

# Schema version — exposed in bundle manifests and exported packages.
SCHEMA_VERSION: str = "3.0.0"

# ============================================================================
# TYPE REGISTRY — maps filename → note type for non-default types
# ============================================================================

TYPE_REGISTRY: dict[str, str] = {}

# ============================================================================
# FROZEN LOOKUP TABLES — domain / subdomain / topic
# ============================================================================

DOMAIN_MAP: dict[str, str] = {
    "Fundamentals": "fundamentals",
}

SUBDOMAIN_MAP: dict[str, tuple[str, str]] = {}

TOPIC_MAP: dict[str, tuple[str, str]] = {}

# ============================================================================
# DERIVED ENUM SETS
# ============================================================================

VALID_TYPES: frozenset[str] = frozenset({
    "core-concept",
})

VALID_DOMAINS: frozenset[str] = frozenset(DOMAIN_MAP.values())
VALID_SUBDOMAINS: frozenset[str] = frozenset(slug for slug, _ in SUBDOMAIN_MAP.values())
VALID_TOPICS: frozenset[str] = frozenset(slug for slug, _ in TOPIC_MAP.values())
VALID_STATUSES: frozenset[str] = frozenset({"complete", "partial"})
VALID_DIFFICULTIES: frozenset[str] = frozenset({"intermediate"})

TRACKED_SECTIONS: tuple[tuple[str, str], ...] = (
    ("has_key_principles", "Key Principles"),
    ("has_how_it_works", "How It Works"),
    ("has_tradeoffs", "Trade-offs"),
)

# ============================================================================
# FIELD DEFINITIONS
# ============================================================================

CORE_CONCEPT_FIELDS: tuple[str, ...] = (
    "type", "domain", "subdomain", "status",
    "has_key_principles", "has_how_it_works", "has_tradeoffs", "difficulty",
)
CORE_CONCEPT_FIELDS_NO_SUBDOMAIN: tuple[str, ...] = (
    "type", "domain", "status",
    "has_key_principles", "has_how_it_works", "has_tradeoffs", "difficulty",
)
CORE_CONCEPT_FIELDS_WITH_TOPIC: tuple[str, ...] = (
    "type", "domain", "subdomain", "topic", "status",
    "has_key_principles", "has_how_it_works", "has_tradeoffs", "difficulty",
)

PATTERN_TECHNIQUE_FIELDS: tuple[str, ...] = (
    "type", "domain", "subdomain", "status", "difficulty",
)

ALL_KNOWN_FIELDS: frozenset[str] = frozenset({
    "type", "domain", "subdomain", "topic", "status",
    "has_key_principles", "has_how_it_works", "has_tradeoffs", "difficulty",
    # Phase 25 — optional trust/staleness/evidence metadata fields
    "trust_level", "source_type", "last_reviewed", "review_after",
})

# Phase 25 — optional trust metadata enum values (for validation when present)
VALID_TRUST_LEVELS: frozenset[str] = frozenset({
    "verified", "working", "draft", "external", "deprecated",
})

VALID_SOURCE_TYPES: frozenset[str] = frozenset({
    "authored", "imported", "generated", "agent_suggested",
})

INDICATOR_HEADINGS: tuple[str, ...] = (
    "## Key Principles",
    "## How It Works",
    "## Trade-offs",
)

_HEADING_L2 = re.compile(r"^## [^#]")

# ============================================================================
# SECTION DEFINITIONS — canonical sections per note type
# ============================================================================

CORE_CONCEPT_SECTIONS: tuple[str, ...] = (
    "## Definition",
    "## Why It Matters",
    "## Key Principles",
    "## How It Works",
    "## Examples",
    "## Common Pitfalls",
    "## Trade-offs",
    "## Related Concepts",
    "## Further Exploration",
)

SECTION_MAP: dict[str, tuple[str, ...]] = {
    "core-concept": CORE_CONCEPT_SECTIONS,
}

OPTIONAL_SECTION_MAP: dict[str, tuple[str, ...]] = {}

# ============================================================================
# PRIORITY / WEIGHT TABLES — must be explicitly defined (no silent defaults)
# ============================================================================

DOMAIN_PRIORITY_WEIGHT: dict[str, float] = {}
SUBDOMAIN_DIFFICULTY: dict[str, str] = {}
EXPECTED_CONCEPTS: dict[str, frozenset[str]] = {
    # Demo gap data — concepts expected in the Fundamentals domain but not yet added as notes.
    "fundamentals": frozenset({
        "sorting-algorithms",
        "graph-theory",
        "distributed-systems",
        "compiler-design",
        "regular-expressions",
    }),
}
PRIORITY_DOMAINS: frozenset[str] = frozenset()
CONCEPT_PRIORITY: dict[str, float] = {}

# ============================================================================
# FILE DISCOVERY
# ============================================================================


def discover_files(root: Path) -> list[Path]:
    """Recursively find all content files. Deterministic case-insensitive sort."""
    content_files: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        if rel.parts and rel.parts[0] in EXCLUDE_DIRS:
            continue
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            if fn in EXCLUDE_FILENAMES:
                continue
            content_files.append(Path(dirpath) / fn)
    content_files.sort(key=lambda p: str(p).lower())
    return content_files


# ============================================================================
# FILE READING
# ============================================================================


def read_file_safe(filepath: Path) -> str:
    """Read file as UTF-8, strip BOM, normalise line endings to LF."""
    raw = filepath.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n")


# ============================================================================
# YAML PARSING
# ============================================================================


def parse_yaml_frontmatter(content: str) -> tuple[dict[str, str | bool] | None, str]:
    """Parse YAML frontmatter from file content.

    Returns (None, content) if no YAML frontmatter block is detected.
    Raises ValueError("Malformed YAML: <reason>") if the block exists but
    cannot be parsed or is not a YAML mapping.
    """
    if not content.startswith("---\n"):
        return None, content

    close_idx = content.find("\n---\n", 4)
    if close_idx == -1:
        if content.endswith("\n---"):
            close_idx = len(content) - 4
        else:
            return None, content

    yaml_text = content[4:close_idx]
    remainder_start = close_idx + len("\n---\n")
    if close_idx == len(content) - 4:
        remainder_start = len(content)
    body = content[remainder_start:]
    if body.startswith("\n"):
        body = body[1:]

    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML: {exc}") from exc

    if parsed is None:
        parsed = {}

    if not isinstance(parsed, dict):
        raise ValueError(
            f"Malformed YAML: frontmatter must be a YAML mapping, got {type(parsed).__name__}"
        )

    fields: dict[str, str | bool] = {}
    for key, value in parsed.items():
        if isinstance(value, bool):
            fields[str(key)] = value
        elif value is None:
            fields[str(key)] = ""
        else:
            fields[str(key)] = str(value)

    return fields, body


# ============================================================================
# SECTION DETECTION
# ============================================================================


def detect_section_content(content: str, heading: str) -> bool:
    """Determine if a level-2 heading section has non-empty body text."""
    lines = content.split("\n")
    found_idx: int | None = None
    for i, line in enumerate(lines):
        if line.rstrip() == heading:
            found_idx = i
            break

    if found_idx is None:
        return False

    body_lines: list[str] = []
    for j in range(found_idx + 1, len(lines)):
        if _HEADING_L2.match(lines[j]):
            break
        body_lines.append(lines[j])

    return len("\n".join(body_lines).strip()) > 0


def extract_section_body(content: str, heading: str) -> str | None:
    """Return the body text of a level-2 section, or None if heading absent."""
    lines = content.split("\n")
    found_idx: int | None = None
    for i, line in enumerate(lines):
        if line.rstrip() == heading:
            found_idx = i
            break
    if found_idx is None:
        return None
    body_lines: list[str] = []
    for j in range(found_idx + 1, len(lines)):
        if _HEADING_L2.match(lines[j]):
            break
        body_lines.append(lines[j])
    return "\n".join(body_lines).strip()


def find_headings(content: str) -> list[str]:
    """Extract all level-2 headings from content."""
    headings: list[str] = []
    for line in content.split("\n"):
        stripped = line.rstrip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            headings.append(stripped)
    return headings


# ============================================================================
# DERIVATION HELPERS
# ============================================================================


def derive_type(filename: str, existing_type: str | None = None) -> str:
    if existing_type is not None and existing_type in VALID_TYPES:
        return existing_type
    return TYPE_REGISTRY.get(filename, "core-concept")


def derive_domain(path_parts: list[str]) -> str:
    folder = path_parts[0]
    if folder not in DOMAIN_MAP:
        raise ValueError(f"Unknown domain folder: '{folder}'")
    return DOMAIN_MAP[folder]


def derive_subdomain(path_parts: list[str]) -> tuple[str, str] | None:
    if len(path_parts) < 3:
        return None
    folder = path_parts[1]
    if folder not in SUBDOMAIN_MAP:
        raise ValueError(f"Unknown subdomain folder: '{folder}'")
    return SUBDOMAIN_MAP[folder]


def derive_topic(path_parts: list[str]) -> tuple[str, str] | None:
    if len(path_parts) < 4:
        return None
    folder = path_parts[2]
    if folder not in TOPIC_MAP:
        raise ValueError(f"Unknown topic folder: '{folder}'")
    return TOPIC_MAP[folder]


def derive_difficulty(subdomain: str | None, topic: str | None) -> str:
    return "intermediate"


# ============================================================================
# REVERSE MAPPING TABLES
# ============================================================================

DOMAIN_TO_SUBDOMAINS: dict[str, list[str]] = {}
for _folder, (_slug, _parent) in SUBDOMAIN_MAP.items():
    DOMAIN_TO_SUBDOMAINS.setdefault(_parent, []).append(_slug)
for _k in DOMAIN_TO_SUBDOMAINS:
    DOMAIN_TO_SUBDOMAINS[_k].sort()

SUBDOMAIN_TO_TOPICS: dict[str, list[str]] = {}
for _folder, (_slug, _parent) in TOPIC_MAP.items():
    SUBDOMAIN_TO_TOPICS.setdefault(_parent, []).append(_slug)
for _k in SUBDOMAIN_TO_TOPICS:
    SUBDOMAIN_TO_TOPICS[_k].sort()


# ============================================================================
# SCHEMA SELF-VALIDATION
# ============================================================================


def validate_schema_consistency() -> list[str]:
    errors: list[str] = []

    for folder, (slug, parent_domain) in SUBDOMAIN_MAP.items():
        if parent_domain not in VALID_DOMAINS:
            errors.append(
                f"SUBDOMAIN_MAP['{folder}']: parent domain '{parent_domain}' "
                f"not in VALID_DOMAINS"
            )

    for folder, (slug, parent_sub) in TOPIC_MAP.items():
        if parent_sub not in VALID_SUBDOMAINS:
            errors.append(
                f"TOPIC_MAP['{folder}']: parent subdomain '{parent_sub}' "
                f"not in VALID_SUBDOMAINS"
            )

    sub_slugs = [slug for slug, _ in SUBDOMAIN_MAP.values()]
    if len(sub_slugs) != len(set(sub_slugs)):
        seen: set[str] = set()
        for s in sub_slugs:
            if s in seen:
                errors.append(f"Duplicate subdomain slug: '{s}'")
            seen.add(s)

    topic_pairs: list[tuple[str, str]] = []
    for _folder, (slug, parent) in TOPIC_MAP.items():
        pair = (parent, slug)
        if pair in topic_pairs:
            errors.append(f"Duplicate topic within subdomain: {pair}")
        topic_pairs.append(pair)

    domain_slugs = list(DOMAIN_MAP.values())
    if len(domain_slugs) != len(set(domain_slugs)):
        seen_d: set[str] = set()
        for d in domain_slugs:
            if d in seen_d:
                errors.append(f"Duplicate domain slug: '{d}'")
            seen_d.add(d)

    for entry in TYPE_REGISTRY:
        if not entry.endswith(".md"):
            errors.append(f"TYPE_REGISTRY: '{entry}' does not end with .md")

    for entry, note_type in TYPE_REGISTRY.items():
        if note_type not in VALID_TYPES:
            errors.append(
                f"TYPE_REGISTRY['{entry}']: type '{note_type}' not in VALID_TYPES"
            )

    if "core-concept" in SECTION_MAP:
        cc_set = set(SECTION_MAP["core-concept"])
        for h in INDICATOR_HEADINGS:
            if h not in cc_set:
                errors.append(
                    f"INDICATOR_HEADINGS: '{h}' not in CORE_CONCEPT_SECTIONS"
                )

    for t in VALID_TYPES:
        if t not in SECTION_MAP:
            errors.append(f"SECTION_MAP: missing entry for type '{t}'")

    return errors


def validate_section_registry_against_files(
    vault_path: Path,
) -> list[tuple[str, str]]:
    mismatches: list[tuple[str, str]] = []

    for filepath in discover_files(vault_path):
        content = read_file_safe(filepath)
        fields, body = parse_yaml_frontmatter(content)
        if fields is None:
            continue

        note_type = fields.get("type", "core-concept")
        canonical = set(SECTION_MAP.get(note_type, ()))
        optional = set(OPTIONAL_SECTION_MAP.get(note_type, ()))
        allowed = canonical | optional
        rel = str(filepath.relative_to(vault_path))

        for heading in find_headings(body):
            if heading not in allowed:
                mismatches.append((rel, heading))

    return mismatches
