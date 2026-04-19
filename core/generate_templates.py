"""
generate_templates.py — Derive templates from vault_schema.py

Templates are GENERATED, not authored.
vault_schema.py is the ONLY source of truth.

Usage:
    python generate_templates.py             Generate all templates
    python generate_templates.py --dry-run   Preview changes without writing

Exit codes:
    0  All templates generated and validated
    1  HARD FAIL — schema mismatch, missing mapping, or validation error

Python: 3.10+ (stdlib only)
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

# ============================================================================
# CONSTANTS
# ============================================================================

VAULT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_REL = Path("Vault Files") / "Scripts" / "vault_schema.py"
TEMPLATE_REL = Path("Vault Files") / "Templates"

# Explicit type → section-constant name mapping.
# Every type that can appear in any vault's VALID_TYPES MUST be listed here.
# Pattern: <type> → <TYPE>_SECTIONS  (hyphens → underscores, upper-cased)
TYPE_TO_CONSTANT: dict[str, str] = {
    "core-concept":              "CORE_CONCEPT_SECTIONS",
    "pattern-technique":         "PATTERN_TECHNIQUE_SECTIONS",
    "pattern-light":             "PATTERN_LIGHT_SECTIONS",
    "technology-implementation": "TECHNOLOGY_IMPLEMENTATION_SECTIONS",
    "technology-concept":        "TECHNOLOGY_CONCEPT_SECTIONS",
    "system-architecture":       "SYSTEM_ARCHITECTURE_SECTIONS",
    "system-overview":           "SYSTEM_OVERVIEW_SECTIONS",
    "technology-pattern":        "TECHNOLOGY_PATTERN_SECTIONS",
    "system-pattern":            "SYSTEM_PATTERN_SECTIONS",
}


# ============================================================================
# HELPERS
# ============================================================================

def discover_vaults() -> list[Path]:
    """Return sorted list of vault directories containing a vault_schema.py."""
    vaults: list[Path] = []
    for child in sorted(VAULT_ROOT.iterdir()):
        if child.is_dir() and (child / SCHEMA_REL).is_file():
            vaults.append(child)
    return vaults


def load_schema(vault: Path) -> ModuleType:
    """Dynamically import a vault's vault_schema.py without side-effects."""
    schema_path = vault / SCHEMA_REL
    spec = importlib.util.spec_from_file_location(
        f"vault_schema_{vault.name.replace(' ', '_')}",
        schema_path,
    )
    if spec is None or spec.loader is None:
        print(f"HARD FAIL: cannot load spec from {schema_path}", file=sys.stderr)
        sys.exit(1)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_type_section_map(
    schema: ModuleType, vault_name: str
) -> dict[str, tuple[str, ...]]:
    """
    Build type → sections mapping from a schema module.

    For each type in VALID_TYPES, look up the corresponding section constant
    using the explicit TYPE_TO_CONSTANT mapping.  HARD FAIL if any type has
    no mapping or the constant is missing from the schema.
    """
    valid_types: frozenset[str] = getattr(schema, "VALID_TYPES", None)
    if valid_types is None:
        print(
            f"HARD FAIL [{vault_name}]: VALID_TYPES not found in vault_schema.py",
            file=sys.stderr,
        )
        sys.exit(1)

    section_map: dict[str, tuple[str, ...]] = {}

    for note_type in sorted(valid_types):
        # 1. Check explicit mapping exists
        constant_name = TYPE_TO_CONSTANT.get(note_type)
        if constant_name is None:
            print(
                f"HARD FAIL [{vault_name}]: type '{note_type}' has no entry in "
                f"TYPE_TO_CONSTANT — cannot derive section constant name. "
                f"Add the mapping before re-running.",
                file=sys.stderr,
            )
            sys.exit(1)

        # 2. Check the constant exists in the schema module
        sections = getattr(schema, constant_name, None)
        if sections is None:
            print(
                f"HARD FAIL [{vault_name}]: type '{note_type}' → "
                f"constant '{constant_name}' not found in vault_schema.py",
                file=sys.stderr,
            )
            sys.exit(1)

        if not isinstance(sections, (tuple, list)) or len(sections) == 0:
            print(
                f"HARD FAIL [{vault_name}]: {constant_name} is empty or not a "
                f"sequence",
                file=sys.stderr,
            )
            sys.exit(1)

        section_map[note_type] = tuple(sections)

    # Cross-check against schema's own SECTION_MAP if present
    schema_section_map: dict | None = getattr(schema, "SECTION_MAP", None)
    if schema_section_map is not None:
        for note_type in sorted(valid_types):
            if note_type not in schema_section_map:
                print(
                    f"HARD FAIL [{vault_name}]: type '{note_type}' in VALID_TYPES "
                    f"but missing from schema SECTION_MAP",
                    file=sys.stderr,
                )
                sys.exit(1)
            if tuple(schema_section_map[note_type]) != section_map[note_type]:
                print(
                    f"HARD FAIL [{vault_name}]: SECTION_MAP['{note_type}'] differs "
                    f"from {TYPE_TO_CONSTANT[note_type]}",
                    file=sys.stderr,
                )
                sys.exit(1)

    return section_map


def render_template(note_type: str, sections: tuple[str, ...]) -> str:
    """
    Render a canonical template string for a given type.

    Format:
        # {{Title}}
        <blank>
        ## Section 1
        <blank>
        ## Section 2
        ...
        <final newline>
    """
    lines: list[str] = ["# {{Title}}", ""]
    for section in sections:
        lines.append(section)
        lines.append("")
    return "\n".join(lines) + "\n"


def template_filename(note_type: str) -> str:
    """Return the canonical template filename for a type."""
    return f"{note_type}.md"


def parse_headings(content: str) -> list[str]:
    """Extract all markdown headings (## level) from template content."""
    return [line for line in content.splitlines() if re.match(r"^## ", line)]


# ============================================================================
# CORE PIPELINE
# ============================================================================

def process_vault(
    vault: Path, *, dry_run: bool = False
) -> dict[str, object]:
    """
    Generate templates for a single vault.

    Returns a report dict with counts and status.
    """
    vault_name = vault.name
    schema = load_schema(vault)
    section_map = build_type_section_map(schema, vault_name)

    template_dir = vault / TEMPLATE_REL
    valid_filenames: set[str] = set()
    created: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []

    # ── Phase 3: Generate templates ──────────────────────────────────────
    for note_type in sorted(section_map):
        sections = section_map[note_type]
        filename = template_filename(note_type)
        valid_filenames.add(filename)
        filepath = template_dir / filename
        content = render_template(note_type, sections)

        if filepath.is_file():
            existing = filepath.read_text(encoding="utf-8")
            if existing == content:
                unchanged.append(filename)
                continue
            else:
                updated.append(filename)
        else:
            created.append(filename)

        if not dry_run:
            template_dir.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8", newline="\n")

    # ── Phase 4: Cleanup ─────────────────────────────────────────────────
    removed: list[str] = []
    if template_dir.is_dir():
        for child in sorted(template_dir.iterdir()):
            if child.is_file() and child.name not in valid_filenames:
                removed.append(child.name)
                if not dry_run:
                    child.unlink()

    # ── Phase 6: Validation ──────────────────────────────────────────────
    validation_pass = True
    validation_errors: list[str] = []

    if not dry_run:
        for note_type in sorted(section_map):
            expected = list(section_map[note_type])
            filepath = template_dir / template_filename(note_type)

            if not filepath.is_file():
                validation_errors.append(
                    f"  {note_type}: template file missing after generation"
                )
                validation_pass = False
                continue

            content = filepath.read_text(encoding="utf-8")
            actual = parse_headings(content)

            if actual != expected:
                validation_errors.append(
                    f"  {note_type}: heading mismatch\n"
                    f"    expected: {expected}\n"
                    f"    actual:   {actual}"
                )
                validation_pass = False

        if not validation_pass:
            print(
                f"HARD FAIL [{vault_name}]: template validation failed:",
                file=sys.stderr,
            )
            for err in validation_errors:
                print(err, file=sys.stderr)
            sys.exit(1)

    return {
        "vault_name": vault_name,
        "types_detected": sorted(section_map),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "removed": removed,
        "validation": "PASS" if validation_pass else "FAIL",
    }


# ============================================================================
# REPORTING
# ============================================================================

def print_report(reports: list[dict[str, object]], *, dry_run: bool) -> None:
    """Print the final generation report."""
    mode = " (DRY RUN)" if dry_run else ""
    print(f"\n=== TEMPLATE GENERATION REPORT{mode} ===\n")
    for r in reports:
        print(f"Vault: {r['vault_name']}")
        print(f"  Types detected: {len(r['types_detected'])}  {r['types_detected']}")
        print(f"  Templates created:   {len(r['created'])}  {r['created']}")
        print(f"  Templates updated:   {len(r['updated'])}  {r['updated']}")
        print(f"  Templates unchanged: {len(r['unchanged'])}  {r['unchanged']}")
        print(f"  Templates removed:   {len(r['removed'])}  {r['removed']}")
        print(f"  Validation: {r['validation']}")
        print()


# ============================================================================
# ENTRY POINT
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate canonical templates from vault_schema.py",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview planned changes without writing files",
    )
    args = parser.parse_args()

    vaults = discover_vaults()
    if not vaults:
        print("HARD FAIL: no vaults found under", VAULT_ROOT, file=sys.stderr)
        sys.exit(1)

    reports: list[dict[str, object]] = []
    for vault in vaults:
        report = process_vault(vault, dry_run=args.dry_run)
        reports.append(report)

    print_report(reports, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
