"""
Vault Analysis Engine

Transforms YAML metadata into actionable insights:
  - completeness gaps
  - structural imbalances
  - prioritised improvement targets

Usage:
    python analyse_vault.py

Python: 3.13+ (stdlib only)
"""

from __future__ import annotations

import io
import sys
from collections import defaultdict
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

from core.shared import load_schema as _load_schema, _resolve_vault_path

# ============================================================================
# DATA LOADING
# ============================================================================


def load_all(root: Path, schema) -> list[dict]:
    """Load metadata + relative path for every content file.

    Files with missing or malformed YAML frontmatter are skipped with an
    explicit warning printed to stdout so the operator is never silently
    misled by a reduced file count.
    """
    records: list[dict] = []
    for filepath in schema.discover_files(root):
        content = schema.read_file_safe(filepath)
        try:
            fields, _ = schema.parse_yaml_frontmatter(content)
        except ValueError as exc:
            print(f"  WARN: {filepath.relative_to(root)} — {exc}")
            continue
        if fields is None:
            print(f"  WARN: {filepath.relative_to(root)} — Missing or invalid YAML frontmatter (file skipped)")
            continue
        fields["_path"] = str(filepath.relative_to(root))
        records.append(fields)
    return records


# ============================================================================
# TABLE RENDERING
# ============================================================================


def table(
    headers: list[str],
    rows: list[list[str]],
    *,
    align: list[str] | None = None,
) -> str:
    """Render a fixed-width CLI table.

    align: list of 'l' or 'r' per column. Default left.
    """
    ncols = len(headers)
    if align is None:
        align = ["l"] * ncols

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells: list[str]) -> str:
        parts: list[str] = []
        for i, cell in enumerate(cells):
            if align[i] == "r":
                parts.append(cell.rjust(widths[i]))
            else:
                parts.append(cell.ljust(widths[i]))
        return "  ".join(parts)

    sep = "  ".join("-" * w for w in widths)
    lines = [fmt_row(headers), sep]
    for row in rows:
        lines.append(fmt_row(row))
    return "\n".join(lines)


def pct(n: int, total: int) -> str:
    if total == 0:
        return "  -"
    return f"{100 * n / total:.0f}%"


def bar(n: int, total: int, width: int = 20) -> str:
    if total == 0:
        return " " * width
    filled = round(width * n / total)
    return "\u2588" * filled + "\u2591" * (width - filled)


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================


def analysis_1_completeness_by_domain(records: list[dict]) -> None:
    """Completeness by domain, ranked weakest \u2192 strongest."""
    print("=" * 72)
    print("ANALYSIS 1 \u2014 COMPLETENESS BY DOMAIN (weakest \u2192 strongest)")
    print("=" * 72)
    print()

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
            bar(s["complete"], s["total"]),
        ])

    # Totals
    t_total = sum(s["total"] for s in stats.values())
    t_comp = sum(s["complete"] for s in stats.values())
    t_part = sum(s["partial"] for s in stats.values())
    rows.append(["TOTAL", str(t_total), str(t_comp), str(t_part),
                 pct(t_comp, t_total), bar(t_comp, t_total)])

    print(table(
        ["Domain", "Total", "Done", "Partial", "Rate", "Progress"],
        rows,
        align=["l", "r", "r", "r", "r", "l"],
    ))
    print()

    weakest = ranked[0]
    print(f"  \u25b8 Weakest domain: {weakest[0]} "
          f"({pct(weakest[1]['complete'], weakest[1]['total'])} complete, "
          f"{weakest[1]['partial']} notes need work)")
    print()


def analysis_2_subdomain_weak_points(records: list[dict]) -> None:
    """Top 10 weakest subdomains."""
    print("=" * 72)
    print("ANALYSIS 2 \u2014 SUBDOMAIN WEAK POINTS (top 10)")
    print("=" * 72)
    print()

    stats: dict[str, dict[str, int]] = {}
    sub_to_domain: dict[str, str] = {}
    for r in records:
        sub = r.get("subdomain") or "N/A"
        dom = r.get("domain", "unknown")
        sub_to_domain[sub] = dom
        if sub not in stats:
            stats[sub] = {"total": 0, "complete": 0, "partial": 0}
        stats[sub]["total"] += 1
        if r.get("status") == "complete":
            stats[sub]["complete"] += 1
        else:
            stats[sub]["partial"] += 1

    # Rank by: lowest completion rate, then highest partial count
    ranked = sorted(
        stats.items(),
        key=lambda kv: (kv[1]["complete"] / max(kv[1]["total"], 1), -kv[1]["partial"]),
    )[:10]

    rows: list[list[str]] = []
    for sub, s in ranked:
        rows.append([
            sub,
            sub_to_domain.get(sub, "?"),
            str(s["total"]),
            str(s["partial"]),
            pct(s["complete"], s["total"]),
        ])

    print(table(
        ["Subdomain", "Domain", "Total", "Partial", "Rate"],
        rows,
        align=["l", "l", "r", "r", "r"],
    ))
    print()

    # Insight
    zero_complete = [sub for sub, s in ranked if s["complete"] == 0]
    if zero_complete:
        print(f"  \u25b8 {len(zero_complete)} subdomain(s) have ZERO complete notes:")
        for sub in zero_complete:
            print(f"      - {sub}")
    print()


def analysis_3_difficulty_vs_completeness(records: list[dict], schema) -> None:
    """Difficulty \u00d7 completeness cross-tabulation."""
    print("=" * 72)
    print("ANALYSIS 3 \u2014 DIFFICULTY vs COMPLETENESS")
    print("=" * 72)
    print()

    order = sorted(schema.VALID_DIFFICULTIES)
    stats: dict[str, dict[str, int]] = {
        d: {"total": 0, "complete": 0, "partial": 0} for d in order
    }
    for r in records:
        diff = r.get("difficulty", "unknown")
        if diff not in stats:
            stats[diff] = {"total": 0, "complete": 0, "partial": 0}
        stats[diff]["total"] += 1
        if r.get("status") == "complete":
            stats[diff]["complete"] += 1
        else:
            stats[diff]["partial"] += 1

    rows: list[list[str]] = []
    for diff in order:
        s = stats[diff]
        rows.append([
            diff,
            str(s["total"]),
            str(s["complete"]),
            str(s["partial"]),
            pct(s["complete"], s["total"]),
            bar(s["complete"], s["total"]),
        ])

    print(table(
        ["Difficulty", "Total", "Done", "Partial", "Rate", "Progress"],
        rows,
        align=["l", "r", "r", "r", "r", "l"],
    ))
    print()

    # Insight: is advanced disproportionately incomplete?
    if "advanced" in schema.VALID_DIFFICULTIES and "foundational" in schema.VALID_DIFFICULTIES:
        found = stats["foundational"]
        inter = stats["intermediate"]
        adv = stats["advanced"]

        found_rate = found["complete"] / max(found["total"], 1)
        inter_rate = inter["complete"] / max(inter["total"], 1)
        adv_rate = adv["complete"] / max(adv["total"], 1)

        if adv_rate < inter_rate and adv_rate < found_rate:
            gap = inter_rate - adv_rate
            print(f"  \u25b8 Advanced topics ARE disproportionately incomplete.")
            print(f"    Completion rate gap: advanced ({pct(adv['complete'], adv['total'])}) "
                  f"vs intermediate ({pct(inter['complete'], inter['total'])}) "
                  f"= {gap * 100:.0f} percentage points behind.")
        elif adv_rate >= inter_rate:
            print(f"  \u25b8 Advanced topics are NOT disproportionately incomplete "
                  f"({pct(adv['complete'], adv['total'])} vs "
                  f"intermediate {pct(inter['complete'], inter['total'])}).")
    print()


def analysis_4_critical_gaps(records: list[dict], schema) -> None:
    """Notes that are partial + advanced = highest-value upgrade targets."""
    print("=" * 72)
    print("ANALYSIS 4 \u2014 CRITICAL GAPS (partial + advanced)")
    print("=" * 72)
    print()

    gaps = [
        r for r in records
        if r.get("status") == "partial" and r.get("difficulty") == "advanced"
    ]
    gaps.sort(key=lambda r: r["_path"])

    if "advanced" not in schema.VALID_DIFFICULTIES or not gaps:
        print("  No critical gaps found.")
        print()
        return

    print(f"  {len(gaps)} notes are PARTIAL and ADVANCED \u2014 highest-value targets:")
    print()

    # Group by domain for readability
    by_domain: dict[str, list[dict]] = defaultdict(list)
    for r in gaps:
        by_domain[r.get("domain", "unknown")].append(r)

    for domain in sorted(by_domain):
        notes = by_domain[domain]
        print(f"  [{domain}] ({len(notes)} notes)")
        for r in notes:
            print(f"    {r['_path']}")
        print()

    print(f"  Total critical gaps: {len(gaps)}")
    print()


def analysis_5_section_deficiency_heatmap(records: list[dict], schema) -> None:
    """Missing tracked sections by domain \u2014 driven by TRACKED_SECTIONS from schema."""
    print("=" * 72)
    print("ANALYSIS 5 \u2014 SECTION DEFICIENCY HEATMAP")
    print("=" * 72)
    print()

    fields = list(schema.TRACKED_SECTIONS)  # list of (yaml_key, label)

    if not fields:
        print("  No tracked sections defined in this vault schema.")
        print("  (TRACKED_SECTIONS is empty \u2014 skipping heatmap.)")
        print()
        return

    # Only core-concept notes carry these boolean fields
    core = [r for r in records if r.get("type") == "core-concept"]
    total_core = len(core)

    # Global counts
    global_missing: dict[str, int] = {label: 0 for _, label in fields}
    for r in core:
        for field, label in fields:
            if r.get(field) is not True:
                global_missing[label] += 1

    print("  GLOBAL (across all core-concept notes):")
    print()
    rows_g: list[list[str]] = []
    for _, label in fields:
        miss = global_missing[label]
        rows_g.append([
            label,
            str(miss),
            pct(total_core - miss, total_core),
            bar(total_core - miss, total_core),
        ])
    print(table(
        ["Section", "Missing", "Present %", "Coverage"],
        rows_g,
        align=["l", "r", "r", "l"],
    ))
    print()

    if not core:
        print("  No core-concept notes \u2014 per-domain breakdown not available.")
        print()
        return

    # Per-domain breakdown \u2014 dynamic columns from TRACKED_SECTIONS
    domain_missing: dict[str, dict[str, int]] = {}
    domain_total: dict[str, int] = {}
    for r in core:
        dom = r.get("domain", "unknown")
        if dom not in domain_missing:
            domain_missing[dom] = {label: 0 for _, label in fields}
            domain_total[dom] = 0
        domain_total[dom] += 1
        for field, label in fields:
            if r.get(field) is not True:
                domain_missing[dom][label] += 1

    print("  PER DOMAIN:")
    print()

    short_labels = [label[:10] for _, label in fields]
    headers_d = ["Domain", "Notes"] + [f"No {sl}" for sl in short_labels] + ["Total Gaps"]
    rows_d: list[list[str]] = []
    for dom in sorted(domain_missing):
        t = domain_total[dom]
        per_section = [str(domain_missing[dom][label]) for _, label in fields]
        total_gaps = sum(domain_missing[dom][label] for _, label in fields)
        rows_d.append([dom, str(t)] + per_section + [str(total_gaps)])

    print(table(headers_d, rows_d, align=["l", "r"] + ["r"] * (len(fields) + 1)))
    print()

    # Insight: worst domain \u00d7 section pairs
    worst_pairs: list[tuple[int, str, str]] = []
    for dom, section_counts in domain_missing.items():
        for label, count in section_counts.items():
            worst_pairs.append((count, dom, label))
    worst_pairs.sort(reverse=True)

    print("  \u25b8 Worst domain\u00d7section gaps:")
    for count, dom, section in worst_pairs[:5]:
        if count > 0:
            print(f"    {count:3d} missing \u2014 {dom} / {section}")
    print()


def analysis_6_structural_balance(records: list[dict]) -> None:
    """Distribution of notes across domains."""
    print("=" * 72)
    print("ANALYSIS 6 \u2014 STRUCTURAL BALANCE")
    print("=" * 72)
    print()

    counts: dict[str, int] = defaultdict(int)
    for r in records:
        counts[r.get("domain", "unknown")] += 1

    total = len(records)
    expected = total / max(len(counts), 1)

    ranked = sorted(counts.items(), key=lambda kv: -kv[1])

    rows: list[list[str]] = []
    for domain, count in ranked:
        deviation = count - expected
        dev_pct = 100 * deviation / expected if expected else 0
        marker = ""
        if dev_pct > 40:
            marker = "\u25b2 OVER"
        elif dev_pct < -40:
            marker = "\u25bc UNDER"
        rows.append([
            domain,
            str(count),
            pct(count, total),
            bar(count, max(c for _, c in ranked), width=25),
            f"{dev_pct:+.0f}%",
            marker,
        ])

    print(table(
        ["Domain", "Notes", "Share", "Distribution", "vs Avg", "Flag"],
        rows,
        align=["l", "r", "r", "l", "r", "l"],
    ))
    print()
    print(f"  Average per domain: {expected:.1f} notes")
    print()

    over = [(d, c) for d, c in ranked if (c - expected) / expected > 0.40]
    under = [(d, c) for d, c in ranked if (expected - c) / expected > 0.40]

    if over:
        print("  \u25b8 Overrepresented:")
        for d, c in over:
            print(f"    {d}: {c} notes ({pct(c, total)} of vault)")
    if under:
        print("  \u25b8 Underrepresented:")
        for d, c in under:
            print(f"    {d}: {c} notes ({pct(c, total)} of vault)")
    if not over and not under:
        print("  \u25b8 Distribution is reasonably balanced (no domain >40% off average).")
    print()


def analysis_7_prioritised_action_list(records: list[dict], schema) -> None:
    """Top 20 notes to improve, scored and ranked."""
    print("=" * 72)
    print("ANALYSIS 7 \u2014 PRIORITISED ACTION LIST (top 20)")
    print("=" * 72)
    print()
    print("  Scoring: difficulty(advanced=3,intermediate=1) + missing_tradeoffs(+3)")
    print("           + missing_how_it_works(+2) + missing_key_principles(+1)")
    print("           \u00d7 domain_weight(default=1.0)")
    print()

    # Only partial notes are candidates
    candidates = [r for r in records if r.get("status") == "partial"]

    scored: list[tuple[float, dict]] = []
    for r in candidates:
        diff = r.get("difficulty", sorted(schema.VALID_DIFFICULTIES)[0])
        base = 0.0

        # Difficulty score
        if "advanced" in schema.VALID_DIFFICULTIES and diff == "advanced":
            base += 3.0
        elif diff == "intermediate":
            base += 1.0

        # Missing section penalties
        if r.get("has_tradeoffs") is not True:
            base += 3.0
        if r.get("has_how_it_works") is not True:
            base += 2.0
        if r.get("has_key_principles") is not True:
            base += 1.0

        # Domain weight
        dom = r.get("domain", "foundations")
        weight = schema.DOMAIN_PRIORITY_WEIGHT.get(dom, 1.0)
        score = base * weight

        scored.append((score, r))

    scored.sort(key=lambda t: -t[0])
    top = scored[:20]

    rows: list[list[str]] = []
    for rank, (score, r) in enumerate(top, 1):
        missing: list[str] = []
        if r.get("has_key_principles") is not True:
            missing.append("KP")
        if r.get("has_how_it_works") is not True:
            missing.append("HW")
        if r.get("has_tradeoffs") is not True:
            missing.append("TO")

        rows.append([
            f"#{rank}",
            f"{score:.1f}",
            r.get("difficulty", "?"),
            ", ".join(missing) if missing else "-",
            r["_path"],
        ])

    print(table(
        ["Rank", "Score", "Difficulty", "Missing", "File"],
        rows,
        align=["r", "r", "l", "l", "l"],
    ))
    print()
    print(f"  {len(candidates)} total partial notes. "
          f"Improving the top 20 addresses the highest-impact gaps first.")
    print()


# ============================================================================
# EXECUTIVE SUMMARY
# ============================================================================


def executive_summary(records: list[dict], schema) -> None:
    """One-screen overview printed at the top."""
    total = len(records)
    complete = sum(1 for r in records if r.get("status") == "complete")
    partial = total - complete
    advanced_partial = sum(
        1 for r in records
        if r.get("status") == "partial" and r.get("difficulty") == "advanced"
    ) if "advanced" in schema.VALID_DIFFICULTIES else 0

    core = [r for r in records if r.get("type") == "core-concept"]
    missing_kp = sum(1 for r in core if r.get("has_key_principles") is not True)
    missing_hw = sum(1 for r in core if r.get("has_how_it_works") is not True)
    missing_to = sum(1 for r in core if r.get("has_tradeoffs") is not True)
    total_section_gaps = missing_kp + missing_hw + missing_to

    vault_name = schema.VAULT_ROOT.name
    print("=" * 72)
    print(f"VAULT ANALYSIS \u2014 {vault_name}")
    print(f"Source: vault_schema.py v3.0.0 | {total} notes analysed")
    print("=" * 72)
    print()
    print(f"  Completion:   {complete}/{total} ({pct(complete, total)})  "
          f"{bar(complete, total, 30)}")
    print(f"  Partial:      {partial} notes need work")
    print(f"  Critical:     {advanced_partial} advanced + partial (highest priority)")
    print(f"  Section gaps: {total_section_gaps} missing sections across {len(core)} core notes")
    print()


# ============================================================================
# MAIN
# ============================================================================


def main(vault_path: Path | None = None) -> int:
    if vault_path is None:
        vault_path = _resolve_vault_path()
    _schema = _load_schema(vault_path)

    records = load_all(_schema.VAULT_ROOT, _schema)
    if not records:
        print("ERROR: No records loaded.")
        return 1

    executive_summary(records, _schema)
    analysis_1_completeness_by_domain(records)
    analysis_2_subdomain_weak_points(records)
    analysis_3_difficulty_vs_completeness(records, _schema)
    analysis_4_critical_gaps(records, _schema)
    analysis_5_section_deficiency_heatmap(records, _schema)
    analysis_6_structural_balance(records)
    analysis_7_prioritised_action_list(records, _schema)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
