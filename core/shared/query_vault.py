"""
Vault Query Engine

Query content notes by YAML frontmatter metadata.
Filters combine with AND logic.

Usage:
    python query_vault.py --status partial
    python query_vault.py --domain discrete-mathematics --status partial
    python query_vault.py --difficulty advanced --status partial
    python query_vault.py --type pattern-technique
    python query_vault.py --subdomain graph-theory --difficulty foundational
    python query_vault.py --report weak_hw
    python query_vault.py --report weak_tradeoffs
    python query_vault.py --report domain_stats
    python query_vault.py --report outliers
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from core.shared import load_schema as _load_schema, _resolve_vault_path

# Module-level globals (populated by _bind before use)
VALID_DIFFICULTIES = None
VALID_DOMAINS = None
VALID_STATUSES = None
VALID_SUBDOMAINS = None
VALID_TYPES = None
VAULT_ROOT = None
discover_files = None
extract_section_body = None
parse_yaml_frontmatter = None
read_file_safe = None


def _bind(vault_path: Path) -> None:
    """Load schema and bind all module-level globals."""
    global VALID_DIFFICULTIES, VALID_DOMAINS, VALID_STATUSES, VALID_SUBDOMAINS
    global VALID_TYPES, VAULT_ROOT, discover_files, extract_section_body
    global parse_yaml_frontmatter, read_file_safe

    _schema = _load_schema(vault_path)
    VALID_DIFFICULTIES = _schema.VALID_DIFFICULTIES
    VALID_DOMAINS = _schema.VALID_DOMAINS
    VALID_STATUSES = _schema.VALID_STATUSES
    VALID_SUBDOMAINS = _schema.VALID_SUBDOMAINS
    VALID_TYPES = _schema.VALID_TYPES
    VAULT_ROOT = _schema.VAULT_ROOT
    discover_files = _schema.discover_files
    extract_section_body = _schema.extract_section_body
    parse_yaml_frontmatter = _schema.parse_yaml_frontmatter
    read_file_safe = _schema.read_file_safe

# ============================================================================
# QUERY ENGINE
# ============================================================================


def load_all_metadata(root: Path) -> list[tuple[Path, dict]]:
    """Load and parse YAML metadata from all content files."""
    results: list[tuple[Path, dict]] = []
    for filepath in discover_files(root):
        content = read_file_safe(filepath)
        fields, _ = parse_yaml_frontmatter(content)
        if fields is not None:
            results.append((filepath, fields))
    return results


def load_all_with_body(root: Path) -> list[tuple[Path, dict, str]]:
    """Load YAML metadata and body text from all content files."""
    results: list[tuple[Path, dict, str]] = []
    for filepath in discover_files(root):
        content = read_file_safe(filepath)
        fields, body = parse_yaml_frontmatter(content)
        if fields is not None:
            results.append((filepath, fields, body))
    return results


def apply_filters(
    entries: list[tuple[Path, dict]],
    filters: dict[str, str],
) -> list[tuple[Path, dict]]:
    """Filter entries by AND-combining all active filters."""
    matched: list[tuple[Path, dict]] = []
    for filepath, fields in entries:
        if all(fields.get(key) == value for key, value in filters.items()):
            matched.append((filepath, fields))
    return matched


def print_results(
    matched: list[tuple[Path, dict]],
    root: Path,
    filters: dict[str, str],
) -> None:
    """Print query results with file list, counts, and grouped summary."""
    # Header
    if filters:
        filter_str = ", ".join(f"{k}={v}" for k, v in filters.items())
        print(f"Query: {filter_str}")
    else:
        print("Query: (all files)")
    print(f"{'='*60}")
    print()

    if not matched:
        print("No matching files.")
        return

    # File listing
    for filepath, _ in matched:
        rel = filepath.relative_to(root)
        print(f"  {rel}")
    print()

    # Count
    print(f"Total: {len(matched)}")
    print()

    # Grouped summary by domain
    by_domain: dict[str, int] = defaultdict(int)
    for _, fields in matched:
        by_domain[str(fields.get("domain", "unknown"))] += 1

    print("By domain:")
    for domain in sorted(by_domain):
        print(f"  {domain}: {by_domain[domain]}")
    print()

    # Grouped summary by status
    by_status: dict[str, int] = defaultdict(int)
    for _, fields in matched:
        by_status[str(fields.get("status", "unknown"))] += 1

    print("By status:")
    for status in sorted(by_status):
        print(f"  {status}: {by_status[status]}")
    print()

    # Grouped summary by difficulty
    by_diff: dict[str, int] = defaultdict(int)
    for _, fields in matched:
        by_diff[str(fields.get("difficulty", "unknown"))] += 1

    print("By difficulty:")
    for diff in sorted(by_diff):
        print(f"  {diff}: {by_diff[diff]}")


# ============================================================================
# QUALITY ANALYSIS HELPERS
# ============================================================================

_NUMBERED_STEP = re.compile(r"^\d+\.\s+")
_WEAK_HW_VERBS = re.compile(r"\b(understand|consider|note|analyse)\b", re.IGNORECASE)
_WEAK_TO_TERMS = re.compile(r"\b(simple|efficient|flexible|complex)\b", re.IGNORECASE)


def get_hw_step_count(body: str) -> int:
    """Count numbered steps in the How It Works section."""
    section = extract_section_body(body, "## How It Works")
    if section is None:
        return 0
    return sum(1 for line in section.split("\n") if _NUMBERED_STEP.match(line))


def get_tradeoff_row_count(body: str) -> int:
    """Count data rows in the Trade-offs table (excluding header and separator)."""
    section = extract_section_body(body, "## Trade-offs")
    if section is None:
        return 0
    table_lines = [
        line for line in section.split("\n")
        if line.strip().startswith("|")
    ]
    # Subtract header + separator
    return max(0, len(table_lines) - 2)


def _get_hw_steps_text(body: str) -> list[str]:
    """Return the text of each numbered step in HW."""
    section = extract_section_body(body, "## How It Works")
    if section is None:
        return []
    return [line for line in section.split("\n") if _NUMBERED_STEP.match(line)]


def _get_to_data_rows(body: str) -> list[str]:
    """Return the data rows of the Trade-offs table."""
    section = extract_section_body(body, "## Trade-offs")
    if section is None:
        return []
    table_lines = [
        line for line in section.split("\n")
        if line.strip().startswith("|")
    ]
    return table_lines[2:] if len(table_lines) > 2 else []


# ============================================================================
# REPORT GENERATORS
# ============================================================================


def _core_concept_entries(
    entries: list[tuple[Path, dict, str]],
) -> list[tuple[Path, dict, str]]:
    """Filter to core-concept notes only."""
    return [(p, f, b) for p, f, b in entries if f.get("type") == "core-concept"]


def report_weak_hw(root: Path, entries: list[tuple[Path, dict, str]]) -> None:
    """Report notes with weak How It Works sections."""
    print("[WEAK HOW IT WORKS]")
    print()
    flagged: list[tuple[str, int, list[str]]] = []

    for filepath, fields, body in _core_concept_entries(entries):
        steps = _get_hw_steps_text(body)
        count = len(steps)
        reasons: list[str] = []
        if count == 3:
            reasons.append("minimum threshold")
        weak_found = set()
        for step in steps:
            for match in _WEAK_HW_VERBS.finditer(step):
                weak_found.add(match.group(0).lower())
        if weak_found:
            reasons.append(f"weak verbs: {', '.join(sorted(weak_found))}")
        if reasons:
            name = filepath.stem
            flagged.append((name, count, reasons))

    flagged.sort(key=lambda x: x[0])
    if not flagged:
        print("  No weak How It Works sections found.")
    else:
        for name, count, reasons in flagged:
            reason_str = "; ".join(reasons)
            print(f"  - {name} ({count} steps) [{reason_str}]")
    print()
    print(f"Total flagged: {len(flagged)}")


def report_weak_tradeoffs(root: Path, entries: list[tuple[Path, dict, str]]) -> None:
    """Report notes with weak Trade-offs sections."""
    print("[WEAK TRADE-OFFS]")
    print()
    flagged: list[tuple[str, int, list[str]]] = []

    for filepath, fields, body in _core_concept_entries(entries):
        rows = _get_to_data_rows(body)
        count = len(rows)
        reasons: list[str] = []
        if count == 3:
            reasons.append("minimum threshold")
        vague_found = set()
        for row in rows:
            for match in _WEAK_TO_TERMS.finditer(row):
                vague_found.add(match.group(0).lower())
        if vague_found:
            reasons.append(f"vague terms: {', '.join(sorted(vague_found))}")
        if reasons:
            name = filepath.stem
            flagged.append((name, count, reasons))

    flagged.sort(key=lambda x: x[0])
    if not flagged:
        print("  No weak Trade-offs sections found.")
    else:
        for name, count, reasons in flagged:
            reason_str = "; ".join(reasons)
            print(f"  - {name} ({count} rows) [{reason_str}]")
    print()
    print(f"Total flagged: {len(flagged)}")


def report_domain_stats(root: Path, entries: list[tuple[Path, dict, str]]) -> None:
    """Report per-domain statistics for HW step counts and TO row counts."""
    print("[DOMAIN STATS]")
    print()

    # Group by top-level folder name
    domain_data: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for filepath, fields, body in _core_concept_entries(entries):
        rel = filepath.relative_to(root)
        folder = rel.parts[0]
        hw = get_hw_step_count(body)
        to = get_tradeoff_row_count(body)
        domain_data[folder].append((hw, to))

    for folder in sorted(domain_data):
        pairs = domain_data[folder]
        n = len(pairs)
        avg_hw = sum(hw for hw, _ in pairs) / n
        avg_to = sum(to for _, to in pairs) / n
        print(f"{folder}")
        print(f"  notes: {n}")
        print(f"  avg HW steps: {avg_hw:.1f}")
        print(f"  avg TO rows: {avg_to:.1f}")
        print()


def report_outliers(root: Path, entries: list[tuple[Path, dict, str]]) -> None:
    """Report notes with extreme HW step counts and TO row counts."""
    print("[OUTLIERS]")
    print()

    hw_scores: list[tuple[str, int]] = []
    to_scores: list[tuple[str, int]] = []

    for filepath, fields, body in _core_concept_entries(entries):
        name = filepath.stem
        hw_scores.append((name, get_hw_step_count(body)))
        to_scores.append((name, get_tradeoff_row_count(body)))

    hw_sorted = sorted(hw_scores, key=lambda x: (x[1], x[0]))
    to_sorted = sorted(to_scores, key=lambda x: (x[1], x[0]))

    n = 10  # top/bottom count

    print(f"Lowest HW step count (bottom {n}):")
    for name, count in hw_sorted[:n]:
        print(f"  - {name} ({count} steps)")
    print()

    print(f"Highest HW step count (top {n}):")
    for name, count in hw_sorted[-n:][::-1]:
        print(f"  - {name} ({count} steps)")
    print()

    print(f"Lowest TO row count (bottom {n}):")
    for name, count in to_sorted[:n]:
        print(f"  - {name} ({count} rows)")
    print()

    print(f"Highest TO row count (top {n}):")
    for name, count in to_sorted[-n:][::-1]:
        print(f"  - {name} ({count} rows)")


REPORT_DISPATCH: dict[str, callable] = {
    "weak_hw": report_weak_hw,
    "weak_tradeoffs": report_weak_tradeoffs,
    "domain_stats": report_domain_stats,
    "outliers": report_outliers,
}


# ============================================================================
# CLI
# ============================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query vault by YAML metadata.",
    )
    parser.add_argument("--type", choices=sorted(VALID_TYPES), help="Filter by note type")
    parser.add_argument("--domain", choices=sorted(VALID_DOMAINS), help="Filter by domain")
    parser.add_argument("--subdomain", choices=sorted(VALID_SUBDOMAINS), help="Filter by subdomain")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES), help="Filter by status")
    parser.add_argument("--difficulty", choices=sorted(VALID_DIFFICULTIES), help="Filter by difficulty")
    parser.add_argument(
        "--report",
        choices=sorted(REPORT_DISPATCH),
        help="Run a quality analysis report",
    )
    return parser


def main(vault_path: Path | None = None) -> int:
    if vault_path is None:
        vault_path = _resolve_vault_path()
    _bind(vault_path)

    parser = build_parser()
    args = parser.parse_args()

    # Build filter dict from provided flags
    filters: dict[str, str] = {}
    for key in ("type", "domain", "subdomain", "status", "difficulty"):
        value = getattr(args, key)
        if value is not None:
            filters[key] = value

    # Report mode
    if args.report:
        entries = load_all_with_body(VAULT_ROOT)
        REPORT_DISPATCH[args.report](VAULT_ROOT, entries)
        return 0

    # Standard query mode
    entries = load_all_metadata(VAULT_ROOT)
    matched = apply_filters(entries, filters)
    print_results(matched, VAULT_ROOT, filters)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
