"""
upgrade_vault.py — Vault Upgrade Task Engine

Analyses all content notes via metadata + section quality inspection.
Generates deterministic, prioritised upgrade tasks — NOT content.

Scoring model:
  - difficulty weight:  advanced = +3, intermediate = +1
  - section gap:        Trade-offs missing/weak = +3
                        How It Works missing/weak = +2
                        Key Principles missing = +1
  - domain priority:    multiplied by DOMAIN_PRIORITY_WEIGHT (default 1.0)

Quality thresholds:
  - How It Works: must contain >= 3 numbered steps (1. 2. 3. ...)
  - Trade-offs:   must contain >= 3 data rows in | Aspect | Benefit | Cost | table

Family B notes (non-core-concept) are scored by missing canonical sections
from SECTION_MAP rather than the three tracked boolean fields.

Usage:
    python upgrade_vault.py              # default top 20
    python upgrade_vault.py --top 30     # top 30

Python: 3.13+ (stdlib only)
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

from core.shared import load_schema as _load_schema, _resolve_vault_path

# ============================================================================
# QUALITY THRESHOLDS
# ============================================================================

_NUMBERED_STEP = re.compile(r"^\d+\.\s+")

MIN_HW_STEPS = 3
MIN_TO_ROWS = 3
TO_EXPECTED_HEADER = ["aspect", "benefit", "cost"]

# ============================================================================
# WRITING CONSTRAINTS (per issue type)
# ============================================================================

WRITING_CONSTRAINTS: dict[str, list[str]] = {
    "weak-how-it-works": [
        "Must contain \u2265 3 numbered steps (1. / 2. / 3. \u2026)",
        "Each step: one concrete action or state change",
        "No vague verbs (understand, consider, note)",
        "Steps must form a logical causal sequence",
    ],
    "weak-tradeoffs": [
        "Must be a markdown table: | Aspect | Benefit | Cost |",
        "Minimum 3 data rows (excluding header + separator)",
        "Each row: specific, measurable Benefit and Cost",
        "No generic terms without qualification (simple, efficient, flexible)",
    ],
    "missing-how-it-works": [
        "Add ## How It Works section",
        "Must contain \u2265 3 numbered steps (1. / 2. / 3. \u2026)",
        "Each step: one concrete action or state change",
        "Steps must form a logical causal sequence",
    ],
    "missing-tradeoffs": [
        "Add ## Trade-offs section",
        "Must be a markdown table: | Aspect | Benefit | Cost |",
        "Minimum 3 data rows (excluding header + separator)",
        "Each row: specific, measurable Benefit and Cost",
    ],
    "missing-key-principles": [
        "Add ## Key Principles section",
        "Bullet list of 3\u20135 foundational principles",
        "Each principle: bold term + concise explanation",
    ],
    "missing-section": [
        "Add the listed missing canonical section(s)",
        "Follow section conventions from vault schema",
        "Do not duplicate content already in other sections",
    ],
}

# ============================================================================
# DATA LOADING
# ============================================================================


def load_all(root: Path, schema) -> list[dict]:
    """Load metadata + body + relative path for every content file."""
    records: list[dict] = []
    for filepath in schema.discover_files(root):
        content = schema.read_file_safe(filepath)
        try:
            fields, body = schema.parse_yaml_frontmatter(content)
        except ValueError as exc:
            print(f"  WARN: {filepath.relative_to(root)} — {exc}")
            continue
        if fields is None:
            continue
        fields["_path"] = str(filepath.relative_to(root))
        fields["_body"] = body
        fields["_abs"] = str(filepath)
        records.append(fields)
    return records


# ============================================================================
# SECTION QUALITY CHECKS
# ============================================================================


def check_how_it_works(body: str, schema) -> tuple[str | None, int]:
    """Return (issue_type | None, step_count)."""
    section = schema.extract_section_body(body, "## How It Works")
    if section is None:
        return "missing-how-it-works", 0
    steps = [line for line in section.split("\n") if _NUMBERED_STEP.match(line)]
    if len(steps) < MIN_HW_STEPS:
        return "weak-how-it-works", len(steps)
    return None, len(steps)


def check_tradeoffs(body: str, schema) -> tuple[str | None, int]:
    """Return (issue_type | None, data_row_count)."""
    section = schema.extract_section_body(body, "## Trade-offs")
    if section is None:
        return "missing-tradeoffs", 0
    table_lines = [
        line for line in section.split("\n")
        if line.strip().startswith("|")
    ]
    data_rows = max(0, len(table_lines) - 2)
    if data_rows < MIN_TO_ROWS:
        return "weak-tradeoffs", data_rows
    # Validate header structure
    if table_lines:
        header = table_lines[0]
        cells = [c.strip().lower() for c in header.split("|") if c.strip()]
        if cells != TO_EXPECTED_HEADER:
            return "weak-tradeoffs", data_rows
    return None, data_rows


def check_key_principles(fields: dict) -> str | None:
    """Return issue type if Key Principles is missing."""
    if fields.get("has_key_principles") is not True:
        return "missing-key-principles"
    return None


def check_family_b_sections(body: str, note_type: str, schema) -> list[str]:
    """Return list of missing canonical sections for Family B notes."""
    expected = schema.SECTION_MAP.get(note_type, ())
    if not expected:
        return []
    present = set(schema.find_headings(body))
    missing: list[str] = []
    for heading in expected:
        if heading not in present:
            missing.append(heading.replace("## ", ""))
    return missing


# ============================================================================
# SCORING ENGINE
# ============================================================================


def score_core_concept(fields: dict, issues: list[dict], schema) -> float:
    """Score a core-concept note based on difficulty + section gaps + domain weight."""
    base = 0.0

    # Difficulty component
    diff = fields.get("difficulty", "")
    if "advanced" in schema.VALID_DIFFICULTIES and diff == "advanced":
        base += 3.0
    elif diff == "intermediate":
        base += 1.0

    # Section gap penalties
    for issue in issues:
        itype = issue["issue_type"]
        if itype in ("missing-tradeoffs", "weak-tradeoffs"):
            base += 3.0
        elif itype in ("missing-how-it-works", "weak-how-it-works"):
            base += 2.0
        elif itype == "missing-key-principles":
            base += 1.0

    # Domain weight multiplier
    dom = fields.get("domain", "foundations")
    weight = schema.DOMAIN_PRIORITY_WEIGHT.get(dom, 1.0)

    return base * weight


def score_family_b(fields: dict, missing_sections: list[str], schema) -> float:
    """Score a Family B note based on difficulty + missing sections + domain weight."""
    base = 0.0

    diff = fields.get("difficulty", "")
    if "advanced" in schema.VALID_DIFFICULTIES and diff == "advanced":
        base += 3.0
    elif diff == "intermediate":
        base += 1.0

    # Each missing section adds weight
    base += len(missing_sections) * 1.5

    dom = fields.get("domain", "foundations")
    weight = schema.DOMAIN_PRIORITY_WEIGHT.get(dom, 1.0)

    return base * weight


# ============================================================================
# TASK GENERATION
# ============================================================================


def generate_tasks(records: list[dict], schema) -> list[dict]:
    """Analyse all records and produce scored upgrade tasks."""
    tasks: list[dict] = []

    for rec in records:
        if rec.get("status") != "partial":
            continue

        note_type = rec.get("type", "core-concept")
        body = rec.get("_body", "")
        path = rec["_path"]
        diff = rec.get("difficulty", "unknown")
        domain = rec.get("domain", "unknown")

        if note_type == "core-concept":
            issues: list[dict] = []

            # Check How It Works
            hw_issue, hw_steps = check_how_it_works(body, schema)
            if hw_issue:
                issues.append({
                    "issue_type": hw_issue,
                    "detail": f"{hw_steps} steps found (need \u2265 {MIN_HW_STEPS})",
                    "required_sections": ["How It Works"],
                    "constraints": WRITING_CONSTRAINTS.get(hw_issue, []),
                })

            # Check Trade-offs
            to_issue, to_rows = check_tradeoffs(body, schema)
            if to_issue:
                issues.append({
                    "issue_type": to_issue,
                    "detail": f"{to_rows} data rows found (need \u2265 {MIN_TO_ROWS})",
                    "required_sections": ["Trade-offs"],
                    "constraints": WRITING_CONSTRAINTS.get(to_issue, []),
                })

            # Check Key Principles
            kp_issue = check_key_principles(rec)
            if kp_issue:
                issues.append({
                    "issue_type": kp_issue,
                    "detail": "Section missing or empty",
                    "required_sections": ["Key Principles"],
                    "constraints": WRITING_CONSTRAINTS.get(kp_issue, []),
                })

            if not issues:
                continue

            score = score_core_concept(rec, issues, schema)

            tasks.append({
                "path": path,
                "note_type": note_type,
                "difficulty": diff,
                "domain": domain,
                "score": score,
                "issues": issues,
            })

        else:
            # Family B — check for missing canonical sections
            missing = check_family_b_sections(body, note_type, schema)
            if not missing:
                continue

            score = score_family_b(rec, missing, schema)

            tasks.append({
                "path": path,
                "note_type": note_type,
                "difficulty": diff,
                "domain": domain,
                "score": score,
                "issues": [{
                    "issue_type": "missing-section",
                    "detail": f"{len(missing)} canonical section(s) absent",
                    "required_sections": missing,
                    "constraints": WRITING_CONSTRAINTS["missing-section"],
                }],
            })

    # Deterministic sort: score descending, then path ascending
    tasks.sort(key=lambda t: (-t["score"], t["path"]))
    return tasks


# ============================================================================
# TABLE RENDERER
# ============================================================================


def table(
    headers: list[str],
    rows: list[list[str]],
    *,
    align: list[str] | None = None,
) -> str:
    """Render a fixed-width CLI table."""
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


# ============================================================================
# OUTPUT
# ============================================================================


def render_summary(records: list[dict], tasks: list[dict], top_n: int, schema) -> None:
    """Print executive summary."""
    total = len(records)
    partial = sum(1 for r in records if r.get("status") == "partial")
    core = [r for r in records if r.get("type") == "core-concept"]
    core_partial = [r for r in core if r.get("status") == "partial"]

    vault_name = schema.VAULT_ROOT.name
    print("=" * 78)
    print(f"VAULT UPGRADE ENGINE \u2014 {vault_name}")
    print(f"Source: vault_schema.py v3.0.0 | {total} notes scanned")
    print("=" * 78)
    print()
    print(f"  Total notes:        {total}")
    print(f"  Partial notes:      {partial}")
    print(f"  Core-concept:       {len(core)} ({len(core_partial)} partial)")
    print(f"  Upgrade targets:    {len(tasks)}")
    print(f"  Displaying:         top {min(top_n, len(tasks))}")
    print()


def render_scoring(tasks: list[dict]) -> None:
    """Print scoring model reference."""
    print("-" * 78)
    print("SCORING MODEL")
    print("-" * 78)
    print("  Difficulty:    advanced = +3, intermediate = +1")
    print("  Section gaps:  Trade-offs = +3, How It Works = +2, Key Principles = +1")
    print("  Domain weight: multiplied by DOMAIN_PRIORITY_WEIGHT (default 1.0)")
    print("  Family B:      +1.5 per missing canonical section")
    print()


def render_tasks(tasks: list[dict], top_n: int) -> None:
    """Print the prioritised task list."""
    display = tasks[:top_n]

    print("=" * 78)
    print(f"PRIORITISED UPGRADE TASKS (top {len(display)})")
    print("=" * 78)
    print()

    # Summary table
    rows: list[list[str]] = []
    for rank, task in enumerate(display, 1):
        issue_codes = ", ".join(i["issue_type"] for i in task["issues"])
        rows.append([
            f"#{rank}",
            f"{task['score']:.1f}",
            task["difficulty"],
            task["domain"],
            issue_codes,
            task["path"],
        ])

    print(table(
        ["Rank", "Score", "Difficulty", "Domain", "Issues", "File"],
        rows,
        align=["r", "r", "l", "l", "l", "l"],
    ))
    print()

    # Detailed task cards
    print("=" * 78)
    print("DETAILED TASK INSTRUCTIONS")
    print("=" * 78)

    for rank, task in enumerate(display, 1):
        print()
        print(f"\u2500\u2500\u2500 Task #{rank}  (score: {task['score']:.1f}) "
              f"{'\u2500' * max(1, 50 - len(str(rank)) - len(f'{task["score"]:.1f}'))}")
        print(f"  File:       {task['path']}")
        print(f"  Type:       {task['note_type']}")
        print(f"  Difficulty: {task['difficulty']}")
        print(f"  Domain:     {task['domain']}")

        for issue in task["issues"]:
            print()
            print(f"  Issue:      {issue['issue_type']}")
            print(f"  Detail:     {issue['detail']}")
            print(f"  Sections:   {', '.join(issue['required_sections'])}")
            if issue["constraints"]:
                print(f"  Constraints:")
                for c in issue["constraints"]:
                    print(f"    - {c}")

    print()


def render_domain_breakdown(tasks: list[dict]) -> None:
    """Print issue counts by domain."""
    domain_counts: dict[str, dict[str, int]] = {}
    for task in tasks:
        dom = task["domain"]
        if dom not in domain_counts:
            domain_counts[dom] = {"total": 0, "hw": 0, "to": 0, "kp": 0, "other": 0}
        domain_counts[dom]["total"] += 1
        for issue in task["issues"]:
            it = issue["issue_type"]
            if "how-it-works" in it:
                domain_counts[dom]["hw"] += 1
            elif "tradeoffs" in it:
                domain_counts[dom]["to"] += 1
            elif "key-principles" in it:
                domain_counts[dom]["kp"] += 1
            else:
                domain_counts[dom]["other"] += 1

    print("-" * 78)
    print("ISSUE DISTRIBUTION BY DOMAIN")
    print("-" * 78)
    print()

    rows: list[list[str]] = []
    for dom in sorted(domain_counts, key=lambda d: -domain_counts[d]["total"]):
        c = domain_counts[dom]
        rows.append([
            dom, str(c["total"]), str(c["hw"]), str(c["to"]),
            str(c["kp"]), str(c["other"]),
        ])

    print(table(
        ["Domain", "Tasks", "HW Issues", "TO Issues", "KP Issues", "Other"],
        rows,
        align=["l", "r", "r", "r", "r", "r"],
    ))
    print()


# ============================================================================
# MAIN
# ============================================================================


def main(vault_path: Path | None = None) -> int:
    if vault_path is None:
        vault_path = _resolve_vault_path()
    _schema = _load_schema(vault_path)

    parser = argparse.ArgumentParser(
        description="Vault Upgrade Task Engine \u2014 generates prioritised upgrade tasks."
    )
    parser.add_argument(
        "--top", type=int, default=20,
        help="Number of top-priority tasks to display (default: 20)."
    )
    args = parser.parse_args()

    records = load_all(_schema.VAULT_ROOT, _schema)
    if not records:
        print("ERROR: No records loaded from vault.")
        return 1

    tasks = generate_tasks(records, _schema)

    render_summary(records, tasks, args.top, _schema)
    render_scoring(tasks)
    render_domain_breakdown(tasks)
    render_tasks(tasks, args.top)

    print("=" * 78)
    print(f"Engine complete. {len(tasks)} upgrade targets identified.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
