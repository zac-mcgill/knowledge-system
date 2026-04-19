"""
Delta Comparison Report Generator

Quantifies measurable improvement between two vault states.

Input modes:
    1. Two markdown reports:
             python compare_reports.py --before BEFORE.md --after AFTER.md
    2. Baseline report + live vault re-analysis:
             python compare_reports.py --before BEFORE.md

Output:
    Vault Delta Report.md

Python: 3.13+ (stdlib only)
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from core.shared import load_schema as _load_schema

_schema = _load_schema()

TRACKED_SECTIONS = _schema.TRACKED_SECTIONS
VAULT_ROOT = _schema.VAULT_ROOT
OUTPUT_DIR = _schema.OUTPUT_DIR
discover_files = _schema.discover_files
parse_yaml_frontmatter = _schema.parse_yaml_frontmatter
read_file_safe = _schema.read_file_safe

# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_OUTPUT = "Vault Delta Report.md"


# ============================================================================
# SNAPSHOT — structured vault state
# ============================================================================

class VaultSnapshot:
    """All measurable metrics for a single vault state."""

    def __init__(
        self,
        total: int,
        complete: int,
        partial: int,
        critical_gap_count: int,
        section_missing: dict[str, int],
        core_concept_count: int,
        domain_stats: dict[str, dict[str, int]],
        partial_notes: set[str],
        complete_notes: set[str],
    ) -> None:
        self.total = total
        self.complete = complete
        self.partial = partial
        self.critical_gap_count = critical_gap_count
        self.section_missing = section_missing          # label -> missing count
        self.core_concept_count = core_concept_count
        self.domain_stats = domain_stats                # domain -> {total, complete, partial}
        self.partial_notes = partial_notes              # set of note names
        self.complete_notes = complete_notes             # set of note names

    @property
    def completion_pct(self) -> float:
        if self.total == 0:
            return 0.0
        return 100.0 * self.complete / self.total

    @property
    def total_section_gaps(self) -> int:
        return sum(self.section_missing.values())


# ============================================================================
# LIVE ANALYSIS — build snapshot from vault on disk
# ============================================================================

def load_all(root: Path) -> list[dict]:
    """Load metadata + relative path for every content file."""
    records: list[dict] = []
    for filepath in discover_files(root):
        content = read_file_safe(filepath)
        fields, _ = parse_yaml_frontmatter(content)
        if fields is None:
            continue
        fields["_path"] = str(filepath.relative_to(root))
        records.append(fields)
    return records


def snapshot_from_records(records: list[dict]) -> VaultSnapshot:
    """Build a VaultSnapshot from loaded records."""
    total = len(records)
    complete = sum(1 for r in records if r.get("status") == "complete")
    partial = total - complete

    # Critical gaps: advanced + partial
    critical = sum(
        1 for r in records
        if r.get("status") == "partial" and r.get("difficulty") == "advanced"
    )

    # Section deficiencies (core-concept notes only)
    core = [r for r in records if r.get("type") == "core-concept"]
    section_missing: dict[str, int] = {}
    for yaml_key, label in TRACKED_SECTIONS:
        section_missing[label] = sum(1 for r in core if r.get(yaml_key) is not True)

    # Domain stats
    domain_stats: dict[str, dict[str, int]] = {}
    for r in records:
        d = r.get("domain", "unknown")
        if d not in domain_stats:
            domain_stats[d] = {"total": 0, "complete": 0, "partial": 0}
        domain_stats[d]["total"] += 1
        if r.get("status") == "complete":
            domain_stats[d]["complete"] += 1
        else:
            domain_stats[d]["partial"] += 1

    # Note name sets
    partial_notes = {Path(r["_path"]).stem for r in records if r.get("status") == "partial"}
    complete_notes = {Path(r["_path"]).stem for r in records if r.get("status") == "complete"}

    return VaultSnapshot(
        total=total,
        complete=complete,
        partial=partial,
        critical_gap_count=critical,
        section_missing=section_missing,
        core_concept_count=len(core),
        domain_stats=domain_stats,
        partial_notes=partial_notes,
        complete_notes=complete_notes,
    )


def snapshot_from_vault(root: Path) -> VaultSnapshot:
    """Analyse the live vault and return a snapshot."""
    return snapshot_from_records(load_all(root))


# ============================================================================
# REPORT PARSER — build snapshot from a markdown report
# ============================================================================

def _extract_bold_int(text: str, pattern: str) -> int | None:
    """Extract an integer from a bold-delimited pattern in text."""
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


def _parse_domain_table(text: str) -> dict[str, dict[str, int]]:
    """Parse the Domain Analysis markdown table."""
    stats: dict[str, dict[str, int]] = {}
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Domain"):
            in_table = True
            continue
        if in_table and line.startswith("| ---"):
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 4:
                domain = cells[0].strip()
                total = int(cells[1].strip())
                comp = int(cells[2].strip())
                part = int(cells[3].strip())
                stats[domain] = {"total": total, "complete": comp, "partial": part}
        elif in_table and not line.startswith("|"):
            in_table = False
    return stats


def _parse_section_deficiency_table(text: str) -> dict[str, int]:
    """Parse the Section Deficiencies markdown table."""
    missing: dict[str, int] = {}
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Section"):
            in_table = True
            continue
        if in_table and line.startswith("| ---"):
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                label = cells[0].strip()
                miss = int(cells[1].strip())
                missing[label] = miss
        elif in_table and not line.startswith("|"):
            in_table = False
    return missing


def _parse_critical_gap_notes(text: str) -> set[str]:
    """Extract note names listed under Critical Gaps."""
    notes: set[str] = set()
    in_section = False
    for line in text.splitlines():
        if line.startswith("## Critical Gaps"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith("- "):
            name = line[2:].strip()
            if name:
                notes.add(name)
    return notes


def _parse_all_partial_notes(text: str) -> set[str]:
    """Best-effort extraction of partial note names from Critical Gaps + context."""
    return _parse_critical_gap_notes(text)


def snapshot_from_report(report_path: Path) -> VaultSnapshot:
    """Parse a vault report markdown file into a VaultSnapshot."""
    text = report_path.read_text(encoding="utf-8")

    # Executive Summary extraction
    total = _extract_bold_int(text, r"\*\*(\d+) structured notes\*\*")
    complete = _extract_bold_int(text, r"\*\*(\d+)\*\* notes \(\d+%\) are complete")
    partial = _extract_bold_int(text, r"\*\*(\d+)\*\* remain partial")
    critical = _extract_bold_int(text, r"\*\*(\d+)\*\* are classified as critical gaps")
    total_section_gaps = _extract_bold_int(text, r"\*\*(\d+) total section gaps?\*\*")

    if total is None or complete is None:
        raise ValueError(f"Cannot parse executive summary from {report_path}")
    if partial is None:
        partial = total - complete
    if critical is None:
        critical = 0

    # Domain table
    domain_stats = _parse_domain_table(text)

    # Section deficiencies
    section_missing = _parse_section_deficiency_table(text)
    if not section_missing:
        # Fallback defaults
        section_missing = {"Key Principles": 0, "How It Works": 0, "Trade-offs": 0}

    # Core concept count from section deficiency text
    core_match = re.search(r"across (\d+) core-concept notes", text)
    core_count = int(core_match.group(1)) if core_match else total

    # Partial note names (from critical gaps — partial list, not exhaustive)
    critical_notes = _parse_critical_gap_notes(text)

    # Build approximate complete/partial sets from domain table
    # We can't recover individual note names from the report alone,
    # so partial_notes will only contain critical gap names.
    partial_notes = set(critical_notes)
    complete_notes: set[str] = set()  # not recoverable from report

    return VaultSnapshot(
        total=total,
        complete=complete,
        partial=partial,
        critical_gap_count=critical,
        section_missing=section_missing,
        core_concept_count=core_count,
        domain_stats=domain_stats,
        partial_notes=partial_notes,
        complete_notes=complete_notes,
    )


# ============================================================================
# MARKDOWN HELPERS
# ============================================================================

def md_table(headers: list[str], rows: list[list[str]], align: list[str] | None = None) -> str:
    """Render a markdown table with optional alignment."""
    ncols = len(headers)
    if align is None:
        align = ["l"] * ncols

    align_row: list[str] = []
    for a in align:
        if a == "r":
            align_row.append("---:")
        elif a == "c":
            align_row.append(":---:")
        else:
            align_row.append("---")

    lines: list[str] = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(align_row) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def fmt_pct(value: float) -> str:
    """Format a float as a percentage string."""
    return f"{value:.0f}%"


def fmt_delta(value: float, suffix: str = "") -> str:
    """Format a numeric delta with sign."""
    if value > 0:
        return f"+{value:.0f}{suffix}"
    if value < 0:
        return f"{value:.0f}{suffix}"
    return f"0{suffix}"


def fmt_delta_f(value: float, suffix: str = "") -> str:
    """Format a float delta with sign and one decimal."""
    if value > 0:
        return f"+{value:.1f}{suffix}"
    if value < 0:
        return f"{value:.1f}{suffix}"
    return f"0.0{suffix}"


# ============================================================================
# DELTA REPORT GENERATION
# ============================================================================

def section_summary_delta(before: VaultSnapshot, after: VaultSnapshot) -> str:
    """Section 1: Summary Delta."""
    completion_delta = after.completion_pct - before.completion_pct
    partial_delta = after.partial - before.partial
    critical_delta = after.critical_gap_count - before.critical_gap_count
    section_delta = after.total_section_gaps - before.total_section_gaps

    lines: list[str] = []
    lines.append("## Summary Delta")
    lines.append("")
    lines.append(md_table(
        ["Metric", "Before", "After", "Delta"],
        [
            [
                "Completion %",
                fmt_pct(before.completion_pct),
                fmt_pct(after.completion_pct),
                fmt_delta_f(completion_delta, "%"),
            ],
            [
                "Partial notes",
                str(before.partial),
                str(after.partial),
                fmt_delta(partial_delta),
            ],
            [
                "Critical gaps",
                str(before.critical_gap_count),
                str(after.critical_gap_count),
                fmt_delta(critical_delta),
            ],
            [
                "Section deficiencies",
                str(before.total_section_gaps),
                str(after.total_section_gaps),
                fmt_delta(section_delta),
            ],
        ],
        align=["l", "r", "r", "r"],
    ))
    lines.append("")
    return "\n".join(lines)


def section_domain_improvement(before: VaultSnapshot, after: VaultSnapshot) -> str:
    """Section 2: Domain Improvement."""
    all_domains = sorted(set(before.domain_stats) | set(after.domain_stats))

    rows: list[list[str]] = []
    for domain in all_domains:
        b = before.domain_stats.get(domain, {"total": 0, "complete": 0, "partial": 0})
        a = after.domain_stats.get(domain, {"total": 0, "complete": 0, "partial": 0})
        b_pct = 100.0 * b["complete"] / max(b["total"], 1)
        a_pct = 100.0 * a["complete"] / max(a["total"], 1)
        delta = a_pct - b_pct
        rows.append([
            domain,
            fmt_pct(b_pct),
            fmt_pct(a_pct),
            fmt_delta_f(delta, "%"),
        ])

    # Sort by delta descending to highlight biggest gains
    rows.sort(key=lambda r: float(r[3].replace("%", "").replace("+", "")), reverse=True)

    lines: list[str] = []
    lines.append("## Domain Improvement")
    lines.append("")
    lines.append(md_table(
        ["Domain", "Before", "After", "Delta"],
        rows,
        align=["l", "r", "r", "r"],
    ))
    lines.append("")
    return "\n".join(lines)


def section_critical_gap_reduction(before: VaultSnapshot, after: VaultSnapshot) -> str:
    """Section 3: Critical Gap Reduction."""
    b = before.critical_gap_count
    a = after.critical_gap_count
    reduced = b - a
    pct_reduction = 100.0 * reduced / max(b, 1) if b > 0 else 0.0

    lines: list[str] = []
    lines.append("## Critical Gap Reduction")
    lines.append("")
    lines.append(md_table(
        ["Metric", "Value"],
        [
            ["Before count", str(b)],
            ["After count", str(a)],
            ["Reduced", str(reduced)],
            ["% reduction", fmt_pct(pct_reduction)],
        ],
        align=["l", "r"],
    ))
    lines.append("")
    return "\n".join(lines)


def section_deficiency_reduction(before: VaultSnapshot, after: VaultSnapshot) -> str:
    """Section 4: Section Deficiency Reduction."""
    labels = ["Key Principles", "How It Works", "Trade-offs"]

    rows: list[list[str]] = []
    for label in labels:
        b = before.section_missing.get(label, 0)
        a = after.section_missing.get(label, 0)
        delta = a - b
        rows.append([label, str(b), str(a), fmt_delta(delta)])

    # Totals
    b_total = before.total_section_gaps
    a_total = after.total_section_gaps
    rows.append(["**Total**", f"**{b_total}**", f"**{a_total}**", f"**{fmt_delta(a_total - b_total)}**"])

    lines: list[str] = []
    lines.append("## Section Deficiency Reduction")
    lines.append("")
    lines.append(md_table(
        ["Section", "Before", "After", "Delta"],
        rows,
        align=["l", "r", "r", "r"],
    ))
    lines.append("")
    return "\n".join(lines)


def section_top_improvements(before: VaultSnapshot, after: VaultSnapshot) -> str:
    """Section 5: Top Improvements — notes that moved partial -> complete."""
    # Notes that were partial in before and complete in after
    promoted: set[str] = set()

    if before.partial_notes and after.complete_notes:
        promoted = before.partial_notes & after.complete_notes

    # If we can't determine individual notes (parsed reports with limited data),
    # fall back to computing the count from aggregate numbers.
    if not promoted:
        # Estimate from critical gap names that disappeared
        before_critical = before.partial_notes
        after_critical = after.partial_notes
        resolved = before_critical - after_critical
        if resolved:
            promoted = resolved

    lines: list[str] = []
    lines.append("## Top Improvements")
    lines.append("")

    if promoted:
        lines.append(f"**{len(promoted)} notes** moved from partial \u2192 complete:")
        lines.append("")
        for name in sorted(promoted):
            lines.append(f"- {name}")
        lines.append("")
    else:
        net_completed = after.complete - before.complete
        if net_completed > 0:
            lines.append(
                f"**{net_completed} notes** moved from partial \u2192 complete. "
                f"Individual note names are not available from report-level comparison; "
                f"re-run with live vault analysis for full detail."
            )
            lines.append("")
        else:
            lines.append("No notes moved from partial \u2192 complete in this delta.")
            lines.append("")

    return "\n".join(lines)


def section_interpretation(before: VaultSnapshot, after: VaultSnapshot) -> str:
    """Section 6: Interpretation."""
    completion_delta = after.completion_pct - before.completion_pct
    critical_reduced = before.critical_gap_count - after.critical_gap_count
    section_reduced = before.total_section_gaps - after.total_section_gaps
    net_completed = after.complete - before.complete

    # Identify domains with largest gains
    gains: list[tuple[str, float]] = []
    for domain in set(before.domain_stats) | set(after.domain_stats):
        b = before.domain_stats.get(domain, {"total": 0, "complete": 0})
        a = after.domain_stats.get(domain, {"total": 0, "complete": 0})
        b_pct = 100.0 * b["complete"] / max(b["total"], 1)
        a_pct = 100.0 * a["complete"] / max(a["total"], 1)
        if a_pct - b_pct > 0:
            gains.append((domain, a_pct - b_pct))
    gains.sort(key=lambda x: -x[1])

    # Identify domains still incomplete
    remaining: list[tuple[str, int]] = []
    for domain, s in after.domain_stats.items():
        if s["partial"] > 0:
            remaining.append((domain, s["partial"]))
    remaining.sort(key=lambda x: -x[1])

    lines: list[str] = []
    lines.append("## Interpretation")
    lines.append("")

    parts: list[str] = []

    # What improved
    if net_completed > 0:
        parts.append(
            f"Vault completion rose from {fmt_pct(before.completion_pct)} "
            f"to {fmt_pct(after.completion_pct)} ({fmt_delta_f(completion_delta, '%')}), "
            f"with {net_completed} notes upgraded to complete status"
        )
    else:
        parts.append(
            f"Vault completion remained at {fmt_pct(after.completion_pct)} "
            f"with no net change in complete note count"
        )

    if critical_reduced > 0:
        parts.append(f"critical gaps were reduced by {critical_reduced}")
    if section_reduced > 0:
        parts.append(f"section deficiencies decreased by {section_reduced}")

    # Where gains were concentrated
    if gains:
        top_gain_names = [g[0] for g in gains[:3]]
        parts.append(
            f"gains were concentrated in {', '.join(top_gain_names)}"
        )

    # What remains
    if remaining:
        remain_parts = [f"{d} ({n} partial)" for d, n in remaining[:3]]
        parts.append(
            f"remaining work centres on {', '.join(remain_parts)}"
        )
    elif after.partial > 0:
        parts.append(f"{after.partial} partial notes remain across the vault")
    else:
        parts.append("the vault has reached full completion")

    # Assemble paragraph
    paragraph = ". ".join(p[0].upper() + p[1:] for p in parts) + "."
    lines.append(paragraph)
    lines.append("")

    return "\n".join(lines)


# ============================================================================
# REPORT ASSEMBLY
# ============================================================================

def generate_delta_report(before: VaultSnapshot, after: VaultSnapshot) -> str:
    """Assemble the full delta comparison report."""
    vault_name = VAULT_ROOT.name
    parts: list[str] = []

    parts.append(f"# {vault_name} \u2014 Vault Delta Report")
    parts.append("")

    parts.append(section_summary_delta(before, after))
    parts.append(section_domain_improvement(before, after))
    parts.append(section_critical_gap_reduction(before, after))
    parts.append(section_deficiency_reduction(before, after))
    parts.append(section_top_improvements(before, after))
    parts.append(section_interpretation(before, after))

    return "\n".join(parts)


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a delta comparison report between two vault states",
    )
    parser.add_argument(
        "--before", type=str, required=True,
        help="Path to the BEFORE (baseline) report markdown file",
    )
    parser.add_argument(
        "--after", type=str, default=None,
        help="Path to the AFTER report markdown file. "
             "If omitted, the current vault state is analysed as the AFTER snapshot.",
    )
    parser.add_argument(
        "--output", type=str, default=DEFAULT_OUTPUT,
        help=f"Output filename (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    # Build BEFORE snapshot
    before_path = Path(args.before)
    if not before_path.is_absolute():
        before_path = VAULT_ROOT / before_path
    before = snapshot_from_report(before_path)
    print(f"BEFORE: {before_path.name}  ({before.complete}/{before.total} complete)")

    # Build AFTER snapshot
    if args.after:
        after_path = Path(args.after)
        if not after_path.is_absolute():
            after_path = VAULT_ROOT / after_path
        after = snapshot_from_report(after_path)
        print(f"AFTER:  {after_path.name}  ({after.complete}/{after.total} complete)")
    else:
        after = snapshot_from_vault(VAULT_ROOT)
        print(f"AFTER:  live vault analysis  ({after.complete}/{after.total} complete)")

    # Generate and write
    report = generate_delta_report(before, after)

    if not args.output or args.output.strip() == "":
        raise ValueError("Output filename must be non-empty")

    resolved_output_dir = OUTPUT_DIR.resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    out_path = (resolved_output_dir / args.output).resolve()

    if not (out_path == resolved_output_dir or resolved_output_dir in out_path.parents):
        raise ValueError("Output path must remain inside Vault Files directory")
    out_path.write_text(report, encoding="utf-8")
    print(f"\nDelta report written to: {out_path.name}")


if __name__ == "__main__":
    main()
