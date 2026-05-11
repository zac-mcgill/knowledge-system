"""
vault_schema.py — Single Source of Truth
Animals Vault

Schema: v1.0.0
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
EXCLUDE_FILENAMES = frozenset({"Index.md"})

# Minimum non-whitespace characters required in each canonical section body.
# Set to 0 to disable (header presence is still enforced).
MIN_SECTION_CONTENT_CHARS: int = 0

# ============================================================================
# TYPE REGISTRY — maps filename → note type for non-default types
# ============================================================================

TYPE_REGISTRY: dict[str, str] = {}

# ============================================================================
# FROZEN LOOKUP TABLES — domain / subdomain / topic
# ============================================================================

DOMAIN_MAP: dict[str, str] = {
    "Animals": "animals",
}

SUBDOMAIN_MAP: dict[str, tuple[str, str]] = {}
TOPIC_MAP: dict[str, tuple[str, str]] = {}

# ============================================================================
# DERIVED ENUM SETS
# ============================================================================

VALID_TYPES: frozenset[str] = frozenset({
    "breed-profile",
})

VALID_DOMAINS: frozenset[str] = frozenset(DOMAIN_MAP.values())
VALID_SUBDOMAINS: frozenset[str] = frozenset(slug for slug, _ in SUBDOMAIN_MAP.values())
VALID_TOPICS: frozenset[str] = frozenset(slug for slug, _ in TOPIC_MAP.values())
VALID_STATUSES: frozenset[str] = frozenset({"complete", "partial"})
VALID_DIFFICULTIES: frozenset[str] = frozenset({"intermediate"})

# No boolean section tracking for this note type.
TRACKED_SECTIONS: tuple[tuple[str, str], ...] = ()

# ============================================================================
# FIELD DEFINITIONS
# ============================================================================

# Used by validate_vault when note_type != "core-concept"
PATTERN_TECHNIQUE_FIELDS: tuple[str, ...] = (
    "type", "domain", "status", "difficulty",
)

# Retained for schema-loader compatibility (not used when VALID_TYPES has no core-concept)
CORE_CONCEPT_FIELDS: tuple[str, ...] = (
    "type", "domain", "subdomain", "status", "difficulty",
)
CORE_CONCEPT_FIELDS_WITH_TOPIC: tuple[str, ...] = (
    "type", "domain", "subdomain", "topic", "status", "difficulty",
)

ALL_KNOWN_FIELDS: frozenset[str] = frozenset({
    "type", "domain", "subdomain", "topic", "status", "difficulty",
})

# No indicator headings (not a core-concept schema).
INDICATOR_HEADINGS: tuple[str, ...] = ()

_HEADING_L2 = re.compile(r"^## [^#]")

# ============================================================================
# SECTION DEFINITIONS — canonical sections per note type
# ============================================================================

BREED_PROFILE_SECTIONS: tuple[str, ...] = (
    "## Overview",
    "## Breed Characteristics",
    "## Common Health Issues",
    "## Catchy Names",
)

SECTION_MAP: dict[str, tuple[str, ...]] = {
    "breed-profile": BREED_PROFILE_SECTIONS,
}

OPTIONAL_SECTION_MAP: dict[str, tuple[str, ...]] = {}

# ============================================================================
# PRIORITY / WEIGHT TABLES — must be explicitly defined (no silent defaults)
# ============================================================================

DOMAIN_PRIORITY_WEIGHT: dict[str, float] = {}
SUBDOMAIN_DIFFICULTY: dict[str, str] = {}
EXPECTED_CONCEPTS: dict[str, frozenset[str]] = {}
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
    return TYPE_REGISTRY.get(filename, "breed-profile")


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
        try:
            fields, body = parse_yaml_frontmatter(content)
        except ValueError:
            continue
        if fields is None:
            continue
        note_type = fields.get("type", "breed-profile")
        canonical = set(SECTION_MAP.get(note_type, ()))
        optional = set(OPTIONAL_SECTION_MAP.get(note_type, ()))
        allowed = canonical | optional
        rel = str(filepath.relative_to(vault_path))
        for heading in find_headings(body):
            if heading not in allowed:
                mismatches.append((rel, heading))
    return mismatches
