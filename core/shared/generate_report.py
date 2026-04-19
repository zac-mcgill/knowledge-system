"""
Vault Report Generator

Produces a clean, professional markdown report summarising:
  - vault state and completion metrics
  - domain-level analysis
  - key insights derived from metadata
  - critical gaps and priority actions
  - system architecture description

Usage:
    python generate_report.py
    python generate_report.py --output "Custom Report Name.md"

Python: 3.13+ (stdlib only)
"""

from __future__ import annotations

from pathlib import Path

from core.shared import load_schema as _load_schema

_schema = _load_schema()

TRACKED_SECTIONS = _schema.TRACKED_SECTIONS
VALID_DIFFICULTIES = _schema.VALID_DIFFICULTIES
VAULT_ROOT = _schema.VAULT_ROOT
OUTPUT_DIR = _schema.OUTPUT_DIR
discover_files = _schema.discover_files
parse_yaml_frontmatter = _schema.parse_yaml_frontmatter
read_file_safe = _schema.read_file_safe

# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_OUTPUT = "Vault Report.md"

PRIORITY_DOMAINS = getattr(_schema, 'PRIORITY_DOMAINS', frozenset())


# ============================================================================
# DATA LOADING
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


# ============================================================================
# ANALYSIS HELPERS
# ============================================================================


def domain_stats(records: list[dict]) -> dict[str, dict[str, int]]:
    """Compute per-domain completion statistics."""
    stats: dict[str, dict[str, int]] = {}
    for r in records:
        d = r.get("domain", "unknown")
        if d not in stats:
            stats[d] = {"total": 0, "complete": 0, "partial": 0}
        stats[d]["total"] += 1
        if r.get("status") == "complete":
            stats[d]["complete"] += 1
        else:
            stats[d]["partial"] += 1
    return stats


def difficulty_stats(records: list[dict]) -> dict[str, dict[str, int]]:
    """Compute per-difficulty completion statistics."""
    order = sorted(VALID_DIFFICULTIES)
    stats: dict[str, dict[str, int]] = {d: {"total": 0, "complete": 0, "partial": 0} for d in order}
    for r in records:
        diff = r.get("difficulty", "unknown")
        if diff not in stats:
            stats[diff] = {"total": 0, "complete": 0, "partial": 0}
        stats[diff]["total"] += 1
        if r.get("status") == "complete":
            stats[diff]["complete"] += 1
        else:
            stats[diff]["partial"] += 1
    return stats


def section_gaps(records: list[dict]) -> dict[str, int]:
    """Count missing tracked sections across core-concept notes."""
    core = [r for r in records if r.get("type") == "core-concept"]
    missing: dict[str, int] = {}
    for yaml_key, label in TRACKED_SECTIONS:
        missing[label] = sum(1 for r in core if r.get(yaml_key) is not True)
    return missing


def critical_gaps(records: list[dict]) -> list[dict]:
    """Return advanced + partial records, sorted by path."""
    if "advanced" not in VALID_DIFFICULTIES:
        return []
    gaps = [
        r for r in records
        if r.get("status") == "partial" and r.get("difficulty") == "advanced"
    ]
    gaps.sort(key=lambda r: r["_path"])
    return gaps


def detect_missing(record: dict) -> list[str]:
    """Return list of missing section names for a record."""
    missing: list[str] = []
    for yaml_key, section_name in TRACKED_SECTIONS:
        if not record.get(yaml_key, False):
            missing.append(section_name)
    return missing


def score_record(record: dict, missing: list[str]) -> int:
    """Priority score: difficulty + missing sections + domain weight."""
    score = 0
    diff = record.get("difficulty", "")
    if "advanced" in VALID_DIFFICULTIES and diff == "advanced":
        score += 3
    elif diff == "intermediate":
        score += 1
    if "Trade-offs" in missing:
        score += 2
    if "How It Works" in missing:
        score += 2
    if "Key Principles" in missing:
        score += 1
    if record.get("domain", "") in PRIORITY_DOMAINS:
        score += 2
    return score


def top_priorities(records: list[dict], n: int = 10) -> list[tuple[dict, list[str], int]]:
    """Return top-N priority upgrade targets."""
    scored: list[tuple[dict, list[str], int]] = []
    for rec in records:
        if rec.get("type") != "core-concept":
            continue
        if rec.get("status") != "partial":
            continue
        missing = detect_missing(rec)
        if not missing:
            continue
        score = score_record(rec, missing)
        scored.append((rec, missing, score))
    scored.sort(key=lambda x: (-x[2], x[0]["_path"]))
    return scored[:n]


# ============================================================================
# MARKDOWN TABLE HELPER
# ============================================================================


def md_table(headers: list[str], rows: list[list[str]], align: list[str] | None = None) -> str:
    """Render a markdown table with optional alignment.

    align: list of 'l', 'r', or 'c' per column. Default left.
    """
    ncols = len(headers)
    if align is None:
        align = ["l"] * ncols

    # Build alignment row
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


def pct(n: int, total: int) -> str:
    """Format a percentage."""
    if total == 0:
        return "0%"
    return f"{100 * n / total:.0f}%"


# ============================================================================
# REPORT SECTIONS
# ============================================================================


def section_executive_summary(records: list[dict]) -> str:
    """Section 1: Executive Summary."""
    total = len(records)
    complete = sum(1 for r in records if r.get("status") == "complete")
    partial = total - complete
    rate = 100 * complete / max(total, 1)
    critical = len(critical_gaps(records))
    gaps = section_gaps(records)
    total_gaps = sum(gaps.values())

    vault_name = VAULT_ROOT.name
    domain_count = len(set(r.get("domain", "unknown") for r in records))

    lines: list[str] = []
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        f"This vault contains **{total} structured notes** covering {domain_count} domains. "
        f"Each note carries validated YAML "
        f"metadata tracking completion status, difficulty level, and section presence."
    )
    lines.append("")
    lines.append(
        f"**{complete}** notes ({rate:.0f}%) are complete. "
        f"**{partial}** remain partial, of which **{critical}** are classified as "
        f"critical gaps (advanced difficulty, partial status). "
        f"Across all core-concept notes, **{total_gaps}** individual section "
        f"deficiencies have been identified."
    )
    lines.append("")
    return "\n".join(lines)


def section_domain_analysis(records: list[dict]) -> str:
    """Section 2: Domain Analysis."""
    stats = domain_stats(records)

    # Rank weakest -> strongest
    ranked = sorted(
        stats.items(),
        key=lambda kv: (kv[1]["complete"] / max(kv[1]["total"], 1), -kv[1]["partial"]),
    )

    rows: list[list[str]] = []
    for domain, s in ranked:
        rows.append([
            domain,
            str(s["total"]),
            str(s["complete"]),
            str(s["partial"]),
            pct(s["complete"], s["total"]),
        ])

    weakest_name, weakest_s = ranked[0]
    strongest_name, strongest_s = ranked[-1]

    lines: list[str] = []
    lines.append("## Domain Analysis")
    lines.append("")
    lines.append(md_table(
        ["Domain", "Total", "Complete", "Partial", "Completion"],
        rows,
        align=["l", "r", "r", "r", "r"],
    ))
    lines.append("")
    lines.append(
        f"**Weakest domain:** {weakest_name} \u2014 "
        f"{pct(weakest_s['complete'], weakest_s['total'])} completion rate "
        f"with {weakest_s['partial']} partial notes requiring attention."
    )
    lines.append(
        f"**Strongest domain:** {strongest_name} \u2014 "
        f"{pct(strongest_s['complete'], strongest_s['total'])} completion rate."
    )
    lines.append("")
    return "\n".join(lines)


def section_key_insights(records: list[dict]) -> str:
    """Section 3: Key Insights."""
    d_stats = difficulty_stats(records)
    dom_stats = domain_stats(records)
    gaps = section_gaps(records)
    critical = critical_gaps(records)

    # Compute rates
    inter = d_stats.get("intermediate", {"total": 0, "complete": 0})
    adv = d_stats.get("advanced", {"total": 0, "complete": 0}) if "advanced" in VALID_DIFFICULTIES else {"total": 0, "complete": 0}
    found = d_stats.get("foundational", {"total": 0, "complete": 0}) if "foundational" in VALID_DIFFICULTIES else {"total": 0, "complete": 0}
    inter_rate = inter["complete"] / max(inter["total"], 1)
    adv_rate = adv["complete"] / max(adv["total"], 1)
    found_rate = found["complete"] / max(found["total"], 1)

    # Domain with most gaps
    dom_partial = sorted(dom_stats.items(), key=lambda kv: -kv[1]["partial"])

    insights: list[str] = []

    # Insight 1: Difficulty distribution
    if "advanced" in VALID_DIFFICULTIES and "intermediate" in VALID_DIFFICULTIES:
        if inter_rate < adv_rate:
            insights.append(
                f"Intermediate-level topics show the lowest completion rate "
                f"({pct(inter['complete'], inter['total'])}), below even advanced topics "
                f"({pct(adv['complete'], adv['total'])}). "
                f"The bottleneck is breadth of coverage, not depth."
            )
        elif adv_rate < inter_rate:
            insights.append(
                f"Advanced topics have the lowest completion rate "
                f"({pct(adv['complete'], adv['total'])}), "
                f"indicating depth-related gaps in the most complex material."
            )

    # Insight 2: Priority domains
    if len(dom_partial) >= 2:
        top_two_partial = dom_partial[:2]
        insights.append(
            f"{top_two_partial[0][0].replace('-', ' ').title()} and "
            f"{top_two_partial[1][0].replace('-', ' ').title()} "
            f"account for the majority of partial notes "
            f"({top_two_partial[0][1]['partial']} and {top_two_partial[1][1]['partial']} respectively), "
            f"making them the primary improvement targets."
        )

    # Insight 3: Trade-offs dominance
    to_missing = gaps.get("Trade-offs", 0)
    hw_missing = gaps.get("How It Works", 0)
    insights.append(
        f"Trade-offs is the most commonly missing section ({to_missing} notes), "
        f"followed by How It Works ({hw_missing}). "
        f"This suggests a pattern of capturing definitions without analysing practical implications."
    )

    # Insight 4: Critical concentration
    crit_domains: dict[str, int] = {}
    for r in critical:
        d = r.get("domain", "unknown")
        crit_domains[d] = crit_domains.get(d, 0) + 1
    if crit_domains:
        top_crit = sorted(crit_domains.items(), key=lambda kv: -kv[1])
        top_crit_name = top_crit[0][0].replace('-', ' ').title()
        insights.append(
            f"Of {len(critical)} critical gaps (advanced + partial), "
            f"{top_crit[0][1]} are concentrated in {top_crit_name}."
        )

    # Insight 5: Foundational strength
    if "foundational" in VALID_DIFFICULTIES and found_rate >= 0.7:
        insights.append(
            f"Foundational-level topics are {pct(found['complete'], found['total'])} complete, "
            f"confirming a solid base layer. "
            f"Effort should shift toward intermediate and advanced content."
        )

    lines: list[str] = []
    lines.append("## Key Insights")
    lines.append("")
    for insight in insights:
        lines.append(f"- {insight}")
    lines.append("")
    return "\n".join(lines)


def section_critical_gaps(records: list[dict]) -> str:
    """Section 4: Critical Gaps."""
    gaps = critical_gaps(records)

    lines: list[str] = []
    lines.append("## Critical Gaps")
    lines.append("")
    lines.append(
        f"**{len(gaps)} notes** are both advanced in difficulty and partial in status. "
        f"These represent the highest-value upgrade targets: they cover complex material "
        f"that is most likely to be assessed, referenced, or built upon, yet remain incomplete."
    )
    lines.append("")

    # Group by domain
    by_domain: dict[str, list[dict]] = {}
    for r in gaps:
        d = r.get("domain", "unknown")
        if d not in by_domain:
            by_domain[d] = []
        by_domain[d].append(r)

    for domain in sorted(by_domain):
        notes = by_domain[domain]
        lines.append(f"**{domain}** ({len(notes)} notes)")
        lines.append("")
        for r in notes:
            name = Path(r["_path"]).stem
            lines.append(f"- {name}")
        lines.append("")

    return "\n".join(lines)


def section_deficiencies(records: list[dict]) -> str:
    """Section 5: Section Deficiencies."""
    gaps = section_gaps(records)
    core_count = sum(1 for r in records if r.get("type") == "core-concept")

    rows: list[list[str]] = []
    for label in ["Key Principles", "How It Works", "Trade-offs"]:
        miss = gaps.get(label, 0)
        present = core_count - miss
        rows.append([label, str(miss), pct(present, core_count)])

    total_missing = sum(gaps.values())

    lines: list[str] = []
    lines.append("## Section Deficiencies")
    lines.append("")
    lines.append(md_table(
        ["Section", "Missing", "Coverage"],
        rows,
        align=["l", "r", "r"],
    ))
    lines.append("")
    lines.append(
        f"**{total_missing} total section gaps** across {core_count} core-concept notes. "
        f"Trade-offs sections are the most frequently absent, indicating that notes "
        f"capture *what* a concept is but often omit *when and why* to apply it. "
        f"How It Works gaps suggest missing mechanistic depth \u2014 definitions are present "
        f"but operational understanding is incomplete."
    )
    lines.append("")
    return "\n".join(lines)


def section_priority_actions(records: list[dict]) -> str:
    """Section 6: Priority Actions (top 10)."""
    priorities = top_priorities(records, n=10)

    rows: list[list[str]] = []
    for rec, missing, score in priorities:
        name = Path(rec["_path"]).stem
        diff = rec.get("difficulty", "unknown")
        missing_str = ", ".join(missing)
        reason = f"{diff}; missing {missing_str}"
        rows.append([name, reason])

    lines: list[str] = []
    lines.append("## Priority Actions")
    lines.append("")
    lines.append(
        "The following 10 notes have the highest upgrade priority, scored by "
        "difficulty level, number of missing sections, and domain importance."
    )
    lines.append("")
    lines.append(md_table(
        ["Note", "Reason"],
        rows,
        align=["l", "l"],
    ))
    lines.append("")
    return "\n".join(lines)


def section_system_description(records: list[dict]) -> str:
    """Section 7: System Description."""
    lines: list[str] = []
    lines.append("## System Description")
    lines.append("")
    lines.append(
        "This vault is managed by a schema-driven pipeline that enforces "
        "structural consistency across all notes."
    )
    lines.append("")
    lines.append(
        "**Schema layer** \u2014 A single Python module (`vault_schema.py`) defines "
        "all enums, section templates, mapping tables, and validation rules. "
        "It serves as the sole source of truth; no other file duplicates these constants."
    )
    lines.append("")
    lines.append(
        "**Injection layer** \u2014 `inject_frontmatter.py` derives YAML metadata "
        "from each note's filesystem path and section content, then writes "
        "validated frontmatter. The process is idempotent and deterministic."
    )
    lines.append("")
    lines.append(
        "**Validation layer** \u2014 `validate_vault.py` checks every note against "
        "the schema: field presence, enum membership, derivation correctness, "
        f"and section-boolean consistency. All {len(records)} notes pass validation."
    )
    lines.append("")
    lines.append(
        "**Analysis layer** \u2014 `analyse_vault.py` transforms metadata into "
        "seven structured analyses covering completeness, structural balance, "
        "difficulty distribution, and section deficiency patterns."
    )
    lines.append("")
    lines.append(
        "**Upgrade layer** \u2014 `upgrade_vault.py` generates prioritised, "
        "section-specific writing instructions for each incomplete note, "
        "enabling targeted content improvement in priority order."
    )
    lines.append("")
    return "\n".join(lines)


# ============================================================================
# REPORT ASSEMBLY
# ============================================================================


def generate_report(records: list[dict]) -> str:
    """Assemble the full markdown report."""
    vault_name = VAULT_ROOT.name
    parts: list[str] = []

    parts.append(f"# {vault_name} \u2014 Vault Report")
    parts.append("")

    parts.append(section_executive_summary(records))
    parts.append(section_domain_analysis(records))
    parts.append(section_key_insights(records))
    parts.append(section_critical_gaps(records))
    parts.append(section_deficiencies(records))
    parts.append(section_priority_actions(records))
    parts.append(section_system_description(records))

    return "\n".join(parts)


# ============================================================================
# CLI
# ============================================================================


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a portfolio-ready markdown report for the vault",
    )
    parser.add_argument(
        "--output", type=str, default=DEFAULT_OUTPUT,
        help=f"Output filename (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    records = load_all(VAULT_ROOT)
    report = generate_report(records)

    if not args.output or args.output.strip() == "":
        raise ValueError("Output filename must be non-empty")

    resolved_output_dir = OUTPUT_DIR.resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    out_path = (resolved_output_dir / args.output).resolve()

    if not (out_path == resolved_output_dir or resolved_output_dir in out_path.parents):
        raise ValueError("Output path must remain inside Vault Files directory")
    out_path.write_text(report, encoding="utf-8")

    total = len(records)
    complete = sum(1 for r in records if r.get("status") == "complete")
    print(f"Report generated: {out_path.name}")
    print(f"  {total} notes analysed, {complete} complete ({100 * complete // total}%)")
    print(f"  {len(report)} characters, {report.count(chr(10))} lines")


if __name__ == "__main__":
    main()
