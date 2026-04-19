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

from core.shared import load_schema as _load_schema

_schema = _load_schema()

VALID_DIFFICULTIES = _schema.VALID_DIFFICULTIES
VAULT_ROOT = _schema.VAULT_ROOT
discover_files = _schema.discover_files
parse_yaml_frontmatter = _schema.parse_yaml_frontmatter
read_file_safe = _schema.read_file_safe
DOMAIN_PRIORITY_WEIGHT = getattr(_schema, 'DOMAIN_PRIORITY_WEIGHT', {})

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
        sub = r.get("subdomain", "unknown")
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


def analysis_3_difficulty_vs_completeness(records: list[dict]) -> None:
    """Difficulty \u00d7 completeness cross-tabulation."""
    print("=" * 72)
    print("ANALYSIS 3 \u2014 DIFFICULTY vs COMPLETENESS")
    print("=" * 72)
    print()

    order = sorted(VALID_DIFFICULTIES)
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
    if "advanced" in VALID_DIFFICULTIES and "foundational" in VALID_DIFFICULTIES:
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


def analysis_4_critical_gaps(records: list[dict]) -> None:
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

    if "advanced" not in VALID_DIFFICULTIES or not gaps:
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


def analysis_5_section_deficiency_heatmap(records: list[dict]) -> None:
    """Missing boolean sections by domain."""
    print("=" * 72)
    print("ANALYSIS 5 \u2014 SECTION DEFICIENCY HEATMAP")
    print("=" * 72)
    print()

    fields = [
        ("has_key_principles", "Key Principles"),
        ("has_how_it_works", "How It Works"),
        ("has_tradeoffs", "Trade-offs"),
    ]

    # Only core-concept notes have these fields
    core = [r for r in records if r.get("type") == "core-concept"]

    # Global counts
    global_missing: dict[str, int] = {label: 0 for _, label in fields}
    total_core = len(core)

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

    # Per-domain breakdown
    domain_stats: dict[str, dict[str, dict[str, int]]] = {}
    for r in core:
        dom = r.get("domain", "unknown")
        if dom not in domain_stats:
            domain_stats[dom] = {
                "total": 0,
                "missing_kp": 0,
                "missing_hw": 0,
                "missing_to": 0,
            }
        domain_stats[dom]["total"] += 1
        if r.get("has_key_principles") is not True:
            domain_stats[dom]["missing_kp"] += 1
        if r.get("has_how_it_works") is not True:
            domain_stats[dom]["missing_hw"] += 1
        if r.get("has_tradeoffs") is not True:
            domain_stats[dom]["missing_to"] += 1

    print("  PER DOMAIN:")
    print()

    rows_d: list[list[str]] = []
    for dom in sorted(domain_stats):
        s = domain_stats[dom]
        t = s["total"]
        rows_d.append([
            dom,
            str(t),
            f"{s['missing_kp']}",
            f"{s['missing_hw']}",
            f"{s['missing_to']}",
            str(s["missing_kp"] + s["missing_hw"] + s["missing_to"]),
        ])

    print(table(
        ["Domain", "Notes", "No KeyPrin", "No HowWork", "No Tradeoff", "Total Gaps"],
        rows_d,
        align=["l", "r", "r", "r", "r", "r"],
    ))
    print()

    # Insight: which domain \u00d7 section combos are worst
    worst_pairs: list[tuple[int, str, str]] = []
    for dom, s in domain_stats.items():
        worst_pairs.append((s["missing_kp"], dom, "Key Principles"))
        worst_pairs.append((s["missing_hw"], dom, "How It Works"))
        worst_pairs.append((s["missing_to"], dom, "Trade-offs"))
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


def analysis_7_prioritised_action_list(records: list[dict]) -> None:
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
        diff = r.get("difficulty", sorted(VALID_DIFFICULTIES)[0])
        base = 0.0

        # Difficulty score
        if "advanced" in VALID_DIFFICULTIES and diff == "advanced":
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
        weight = DOMAIN_PRIORITY_WEIGHT.get(dom, 1.0)
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


def executive_summary(records: list[dict]) -> None:
    """One-screen overview printed at the top."""
    total = len(records)
    complete = sum(1 for r in records if r.get("status") == "complete")
    partial = total - complete
    advanced_partial = sum(
        1 for r in records
        if r.get("status") == "partial" and r.get("difficulty") == "advanced"
    ) if "advanced" in VALID_DIFFICULTIES else 0

    core = [r for r in records if r.get("type") == "core-concept"]
    missing_kp = sum(1 for r in core if r.get("has_key_principles") is not True)
    missing_hw = sum(1 for r in core if r.get("has_how_it_works") is not True)
    missing_to = sum(1 for r in core if r.get("has_tradeoffs") is not True)
    total_section_gaps = missing_kp + missing_hw + missing_to

    vault_name = VAULT_ROOT.name
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


def main() -> int:
    records = load_all(VAULT_ROOT)
    if not records:
        print("ERROR: No records loaded.")
        return 1

    executive_summary(records)
    analysis_1_completeness_by_domain(records)
    analysis_2_subdomain_weak_points(records)
    analysis_3_difficulty_vs_completeness(records)
    analysis_4_critical_gaps(records)
    analysis_5_section_deficiency_heatmap(records)
    analysis_6_structural_balance(records)
    analysis_7_prioritised_action_list(records)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
