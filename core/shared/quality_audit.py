"""
Content Quality Audit Engine

Deterministic analysis of explanatory quality for core-concept notes.
Read-only — never modifies files.

Analyses:
    Q-01  Missing or insufficient causal sequence    (+4)
    Q-02  Non-mechanistic steps                      (+3)
    Q-03  Definition leakage                         (+2)
    Q-04  Missing execution model                    (+2)
    Q-05  Missing constraints or failure modes       (+1)

Usage:
    python quality_audit.py
    python quality_audit.py --top 10

Exit codes:
    0  success
    1  failure (schema load / no files)

Python: 3.10+ (stdlib only)
"""

from __future__ import annotations

import argparse
import re
import string
import sys
from pathlib import Path

from core.shared import load_schema as _load_schema, _resolve_vault_path

# Module-level globals (populated by _bind before use)
VAULT_ROOT = None
derive_type = None
discover_files = None
parse_yaml_frontmatter = None
read_file_safe = None


def _bind(vault_path: Path) -> None:
    """Load schema and bind all module-level globals."""
    global VAULT_ROOT, derive_type, discover_files, parse_yaml_frontmatter, read_file_safe

    _schema = _load_schema(vault_path)
    VAULT_ROOT = _schema.VAULT_ROOT
    derive_type = _schema.derive_type
    discover_files = _schema.discover_files
    parse_yaml_frontmatter = _schema.parse_yaml_frontmatter
    read_file_safe = _schema.read_file_safe

# ============================================================================
# CONSTANTS
# ============================================================================

ACTION_VERBS: frozenset[str] = frozenset({
    "execute", "allocate", "resolve", "propagate", "transform", "evaluate",
    "dispatch", "route", "schedule", "store", "retrieve", "compute",
    "iterate", "validate",
})

EXECUTION_KEYWORDS: frozenset[str] = frozenset({
    "runtime", "memory", "state", "flow", "data", "input", "output",
    "process", "execution", "thread", "call", "stack", "queue", "pipeline",
})

CONSTRAINT_KEYWORDS: frozenset[str] = frozenset({
    "limit", "constraint", "failure", "error", "edge case", "bottleneck",
    "degrade", "risk", "contention", "overflow", "latency",
})

_NUMBERED_STEP = re.compile(r"^\d+\.")
_HEADING_L2 = re.compile(r"^## ")

# ============================================================================
# SEVERITY CLASSIFICATION
# ============================================================================


def classify_severity(score: int) -> str:
    """Derive severity label strictly from score."""
    if score >= 6:
        return "HIGH PRIORITY"
    if score >= 3:
        return "NEEDS IMPROVEMENT"
    return "ACCEPTABLE"

# ============================================================================
# SECTION EXTRACTION
# ============================================================================


def extract_sections(text: str) -> dict[str, str]:
    """Extract ## sections from body text (after frontmatter removal).

    Returns dict mapping heading (e.g. '## How It Works') to body text.
    Ignores ### subheadings — they are part of the parent section body.
    """
    lines = text.split("\n")
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.rstrip()
        if _HEADING_L2.match(stripped) and not stripped.startswith("### "):
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = stripped
            current_lines = []
        else:
            if current_heading is not None:
                current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()

    return sections

# ============================================================================
# TEXT HELPERS
# ============================================================================


def _tokenise(text: str) -> set[str]:
    """Lowercase, strip punctuation, split into token set."""
    lowered = text.lower()
    cleaned = lowered.translate(str.maketrans("", "", string.punctuation))
    return set(cleaned.split())


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def _text_lower(text: str) -> str:
    """Return lowercased text for keyword matching."""
    return text.lower()

# ============================================================================
# RULE CHECKS
# ============================================================================


def check_q01(sections: dict[str, str]) -> tuple[bool, str]:
    """Q-01: Missing or insufficient causal sequence (+4).

    Triggers if How It Works is missing or has fewer than 3 numbered steps.
    """
    body = sections.get("## How It Works")
    if body is None:
        return True, "## How It Works section is missing"

    steps = [ln for ln in body.split("\n") if _NUMBERED_STEP.match(ln.strip())]
    count = len(steps)
    if count < 3:
        return True, f"## How It Works has {count} numbered step(s) (minimum 3)"

    return False, ""


def check_q02(sections: dict[str, str]) -> tuple[bool, str]:
    """Q-02: Non-mechanistic steps (+3).

    Triggers if <50% of numbered steps contain action verbs.
    """
    body = sections.get("## How It Works")
    if body is None:
        return False, ""

    steps = [ln for ln in body.split("\n") if _NUMBERED_STEP.match(ln.strip())]
    if not steps:
        return False, ""

    hits = 0
    for step in steps:
        words = set(step.lower().split())
        if words & ACTION_VERBS:
            hits += 1

    ratio = hits / len(steps)
    if ratio < 0.5:
        return True, (
            f"{hits}/{len(steps)} steps contain action verbs "
            f"({ratio:.0%} < 50% threshold)"
        )

    return False, ""


def check_q03(sections: dict[str, str]) -> tuple[bool, str]:
    """Q-03: Definition leakage (+2).

    Triggers if Jaccard similarity >= 0.6 between How It Works and
    (Definition + Key Principles).
    """
    hiw = sections.get("## How It Works")
    if hiw is None:
        return False, ""

    combined_parts: list[str] = []
    defn = sections.get("## Definition")
    if defn:
        combined_parts.append(defn)
    kp = sections.get("## Key Principles")
    if kp:
        combined_parts.append(kp)

    if not combined_parts:
        return False, ""

    tokens_hiw = _tokenise(hiw)
    tokens_combined = _tokenise(" ".join(combined_parts))
    sim = _jaccard(tokens_hiw, tokens_combined)

    if sim >= 0.6:
        return True, (
            f"Jaccard similarity {sim:.2f} between ## How It Works and "
            f"## Definition / ## Key Principles (threshold 0.6)"
        )

    return False, ""


def check_q04(sections: dict[str, str]) -> tuple[bool, str]:
    """Q-04: Missing execution model (+2).

    Triggers if none of the execution keywords appear in How It Works.
    """
    body = sections.get("## How It Works")
    if body is None:
        return False, ""

    lower = _text_lower(body)
    for kw in sorted(EXECUTION_KEYWORDS):
        if kw in lower:
            return False, ""

    return True, "## How It Works contains no execution-model keywords"


def check_q05(sections: dict[str, str]) -> tuple[bool, str]:
    """Q-05: Missing constraints or failure modes (+1).

    Triggers if none of the constraint keywords appear in
    How It Works or Trade-offs.
    """
    combined_parts: list[str] = []
    hiw = sections.get("## How It Works")
    if hiw:
        combined_parts.append(hiw)
    tradeoffs = sections.get("## Trade-offs")
    if tradeoffs:
        combined_parts.append(tradeoffs)

    if not combined_parts:
        return False, ""

    lower = _text_lower(" ".join(combined_parts))
    for kw in sorted(CONSTRAINT_KEYWORDS):
        if kw in lower:
            return False, ""

    return True, (
        "No constraint/failure-mode keywords found in "
        "## How It Works or ## Trade-offs"
    )

# ============================================================================
# RULE TABLE
# ============================================================================

RULES: tuple[tuple[str, int, object], ...] = (
    ("Q-01", 4, check_q01),
    ("Q-02", 3, check_q02),
    ("Q-03", 2, check_q03),
    ("Q-04", 2, check_q04),
    ("Q-05", 1, check_q05),
)

# ============================================================================
# SCORING
# ============================================================================


def score_note(
    filepath: Path,
    sections: dict[str, str],
) -> dict:
    """Run all rules against a note's sections and return result dict."""
    issues: list[tuple[str, int, str]] = []
    for rule_id, weight, fn in RULES:
        triggered, explanation = fn(sections)
        if triggered:
            issues.append((rule_id, weight, explanation))

    total = sum(w for _, w, _ in issues)
    return {
        "file": filepath,
        "score": total,
        "severity": classify_severity(total),
        "issues": issues,
    }

# ============================================================================
# FIX GUIDANCE
# ============================================================================


def _fix_guidance(issues: list[tuple[str, int, str]]) -> list[str]:
    """Generate concrete fix guidance for each triggered rule."""
    fixes: list[str] = []
    rule_ids = {rid for rid, _, _ in issues}

    if "Q-01" in rule_ids:
        fixes.append(
            "Add numbered steps (1. 2. 3. ...) to ## How It Works describing "
            "the causal execution sequence. Minimum 3 steps required."
        )
    if "Q-02" in rule_ids:
        fixes.append(
            "Rewrite numbered steps in ## How It Works to use action verbs "
            "(e.g. execute, allocate, resolve, propagate, transform, evaluate, "
            "dispatch, route, schedule, store, retrieve, compute, iterate, validate). "
            "At least 50% of steps must contain action verbs."
        )
    if "Q-03" in rule_ids:
        fixes.append(
            "Reduce overlap between ## How It Works and ## Definition / "
            "## Key Principles. How It Works should describe mechanics, "
            "not restate definitions."
        )
    if "Q-04" in rule_ids:
        fixes.append(
            "Add execution-model language to ## How It Works. Include references "
            "to runtime behaviour (e.g. runtime, memory, state, flow, data, "
            "process, execution, thread, call, stack, queue, pipeline)."
        )
    if "Q-05" in rule_ids:
        fixes.append(
            "Add constraint or failure-mode language to ## How It Works or "
            "## Trade-offs (e.g. limit, constraint, failure, error, edge case, "
            "bottleneck, degrade, risk, contention, overflow, latency)."
        )

    return fixes

# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def format_summary(results: list[dict]) -> str:
    """Format the summary block."""
    total = len(results)
    flagged = [r for r in results if r["score"] > 0]
    num_flagged = len(flagged)
    highest = max((r["score"] for r in results), default=0)
    avg = sum(r["score"] for r in results) / total if total else 0.0

    lines = [
        "=" * 72,
        f"CONTENT QUALITY AUDIT — {VAULT_ROOT.name}",
        "=" * 72,
        "",
        f"Total notes analysed: {total}",
        f"Notes with issues:   {num_flagged}",
        f"Highest score:       {highest}",
        f"Average score:       {avg:.1f}",
        "",
    ]
    return "\n".join(lines)


def format_ranked_table(results: list[dict], top_n: int | None) -> str:
    """Format the ranked issues table."""
    flagged = [r for r in results if r["score"] > 0]
    flagged.sort(key=lambda r: (-r["score"], str(r["file"]).lower()))

    if top_n is not None:
        flagged = flagged[:top_n]

    if not flagged:
        return "No quality issues detected.\n"

    lines = [
        "-" * 72,
        "RANKED ISSUES",
        "-" * 72,
        "",
        f"{'Rank':<6} {'Score':<7} {'Severity':<20} {'Issues':<22} {'File'}",
        f"{'----':<6} {'-----':<7} {'--------':<20} {'------':<22} {'----'}",
    ]

    for i, r in enumerate(flagged, 1):
        issue_ids = ", ".join(rid for rid, _, _ in r["issues"])
        rel_path = str(r["file"].relative_to(VAULT_ROOT))
        lines.append(
            f"{i:<6} {r['score']:<7} {r['severity']:<20} "
            f"{issue_ids:<22} {rel_path}"
        )

    lines.append("")
    return "\n".join(lines)


def format_details(results: list[dict], top_n: int | None) -> str:
    """Format detailed findings per note."""
    flagged = [r for r in results if r["score"] > 0]
    flagged.sort(key=lambda r: (-r["score"], str(r["file"]).lower()))

    if top_n is not None:
        flagged = flagged[:top_n]

    if not flagged:
        return ""

    lines = [
        "-" * 72,
        "DETAILED FINDINGS",
        "-" * 72,
    ]

    for r in flagged:
        rel_path = str(r["file"].relative_to(VAULT_ROOT))
        lines.append("")
        lines.append(f"File:     {rel_path}")
        lines.append(f"Score:    {r['score']}")
        lines.append(f"Severity: {r['severity']}")
        lines.append("Issues:")
        for rule_id, weight, explanation in r["issues"]:
            lines.append(f"  - {rule_id} (+{weight}): {explanation}")
        fixes = _fix_guidance(r["issues"])
        lines.append("Fix:")
        for fix in fixes:
            lines.append(f"  - {fix}")

    lines.append("")
    return "\n".join(lines)

# ============================================================================
# MAIN
# ============================================================================


def main(vault_path: Path | None = None) -> int:
    if vault_path is None:
        vault_path = _resolve_vault_path()
    _bind(vault_path)

    parser = argparse.ArgumentParser(
        description="Content Quality Audit — deterministic analysis of "
                    "explanatory quality for core-concept notes.",
    )
    parser.add_argument(
        "--top", type=int, default=None, metavar="N",
        help="Limit output to top N scored notes (does not affect scoring).",
    )
    args = parser.parse_args()

    files = discover_files(VAULT_ROOT)
    if not files:
        print("FATAL: No files discovered.", file=sys.stderr)
        return 1

    results: list[dict] = []
    for filepath in files:
        if derive_type(filepath.name) != "core-concept":
            continue

        content = read_file_safe(filepath)
        _, body = parse_yaml_frontmatter(content)
        sections = extract_sections(body)
        result = score_note(filepath, sections)
        results.append(result)

    if not results:
        print("FATAL: No core-concept notes discovered.", file=sys.stderr)
        return 1

    print(format_summary(results))
    print(format_ranked_table(results, args.top))
    print(format_details(results, args.top))

    return 0


if __name__ == "__main__":
    sys.exit(main())
