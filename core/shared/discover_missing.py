"""Coverage Derivation Engine — detect missing concepts in a vault."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from core.shared import load_schema, _resolve_vault_path

# Module-level globals (populated by _bind before use)
VAULT_ROOT: Path = None
discover_files = None
derive_domain = None
derive_subdomain = None
DOMAIN_MAP: dict[str, str] = None
SUBDOMAIN_MAP: dict = None
EXPECTED_CONCEPTS: dict[str, frozenset[str]] = None
SUBDOMAIN_DIFFICULTY: dict[str, str] = None
DOMAIN_PRIORITY_WEIGHT: dict[str, float] = None
CONCEPT_PRIORITY: dict[str, float] = None


def _bind(vault_path: Path) -> None:
    """Load schema and bind all module-level globals."""
    global VAULT_ROOT, discover_files, derive_domain, derive_subdomain
    global DOMAIN_MAP, SUBDOMAIN_MAP, EXPECTED_CONCEPTS
    global SUBDOMAIN_DIFFICULTY, DOMAIN_PRIORITY_WEIGHT, CONCEPT_PRIORITY

    _schema = load_schema(vault_path)
    VAULT_ROOT = _schema.VAULT_ROOT
    discover_files = _schema.discover_files
    derive_domain = _schema.derive_domain
    derive_subdomain = _schema.derive_subdomain
    DOMAIN_MAP = _schema.DOMAIN_MAP
    SUBDOMAIN_MAP = _schema.SUBDOMAIN_MAP
    EXPECTED_CONCEPTS = _schema.EXPECTED_CONCEPTS
    SUBDOMAIN_DIFFICULTY = _schema.SUBDOMAIN_DIFFICULTY
    DOMAIN_PRIORITY_WEIGHT = _schema.DOMAIN_PRIORITY_WEIGHT
    CONCEPT_PRIORITY = _schema.CONCEPT_PRIORITY

DIFFICULTY_SCORE: dict[str, float] = {
    "advanced": 3.0,
    "intermediate": 2.0,
    "foundational": 1.0,
}


# ── Normalisation ───────────────────────────────────────────────


def normalise_filename(name: str) -> str:
    stem = name.removesuffix(".md")
    slug = stem.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


# ── Schema resolution ──────────────────────────────────────────


def build_subdomain_to_domain() -> dict[str, str]:
    mapping: dict[str, str] = {}
    domains_with_subdomains: set[str] = set()
    for value in SUBDOMAIN_MAP.values():
        if isinstance(value, tuple):
            sub_slug, domain_slug = value[0], value[1]
        else:
            sub_slug, domain_slug = value, value
        mapping[sub_slug] = domain_slug
        domains_with_subdomains.add(domain_slug)
    for domain_slug in DOMAIN_MAP.values():
        if domain_slug not in domains_with_subdomains:
            mapping[domain_slug] = domain_slug
    return mapping


# ── Validation ─────────────────────────────────────────────────


def validate_expected_keys(
    expected: dict[str, frozenset[str]],
    valid_subdomains: set[str],
) -> list[str]:
    errors: list[str] = []
    for key in sorted(expected):
        if key not in valid_subdomains:
            errors.append(
                f"EXPECTED_CONCEPTS key '{key}' is not a valid subdomain slug"
            )
    return errors


def validate_expected_slugs(
    expected: dict[str, frozenset[str]],
) -> list[str]:
    errors: list[str] = []
    for key in sorted(expected):
        for slug in sorted(expected[key]):
            canonical = normalise_filename(slug)
            if slug != canonical:
                errors.append(
                    f"EXPECTED_CONCEPTS['{key}']: '{slug}' "
                    f"is not normalised (expected '{canonical}')"
                )
    return errors


def validate_concept_uniqueness(
    expected: dict[str, frozenset[str]],
) -> None:
    seen: dict[str, str] = {}
    for sub in sorted(expected):
        for c in sorted(expected[sub]):
            if c in seen:
                raise ValueError(
                    f"Concept '{c}' defined in both '{seen[c]}' and '{sub}'"
                )
            seen[c] = sub


# ── Data loading ───────────────────────────────────────────────


def load_actual_concepts(root: Path) -> dict[str, set[str]]:
    actual: dict[str, set[str]] = {}
    for filepath in discover_files(root):
        rel = filepath.relative_to(root)
        parts = list(rel.parts)

        try:
            sub = derive_subdomain(parts)
        except ValueError:
            sub = None
        if isinstance(sub, tuple):
            sub = sub[0]

        if sub is not None:
            key = sub
        else:
            try:
                dom = derive_domain(parts)
            except ValueError:
                continue
            if isinstance(dom, tuple):
                dom = dom[0]
            key = dom

        slug = normalise_filename(filepath.name)
        actual.setdefault(key, set()).add(slug)
    return actual


# ── Gap detection ──────────────────────────────────────────────


def detect_gaps(
    expected: dict[str, frozenset[str]],
    actual: dict[str, set[str]],
) -> dict[str, list[str]]:
    gaps: dict[str, list[str]] = {}
    for key in sorted(expected):
        missing = expected[key] - actual.get(key, set())
        if missing:
            gaps[key] = sorted(missing)
    return gaps


# ── Scoring ────────────────────────────────────────────────────


def score_concept(
    concept_slug: str,
    subdomain_slug: str,
    subdomain_to_domain: dict[str, str],
) -> float:
    difficulty = SUBDOMAIN_DIFFICULTY.get(subdomain_slug, "intermediate")
    base = DIFFICULTY_SCORE.get(difficulty, 2.0)
    domain_slug = subdomain_to_domain.get(subdomain_slug, subdomain_slug)
    weight = DOMAIN_PRIORITY_WEIGHT.get(domain_slug, 1.0)
    priority = CONCEPT_PRIORITY.get(concept_slug, 1.0)
    return round(base * weight * priority, 1)


def score_gaps(
    gaps: dict[str, list[str]],
    subdomain_to_domain: dict[str, str],
) -> dict[str, list[tuple[str, float]]]:
    scored: dict[str, list[tuple[str, float]]] = {}
    for sub in sorted(gaps):
        entries: list[tuple[str, float]] = []
        for c in gaps[sub]:
            s = score_concept(c, sub, subdomain_to_domain)
            entries.append((c, s))
        entries.sort(key=lambda x: (-x[1], x[0]))
        scored[sub] = entries
    return scored


# ── Rendering ──────────────────────────────────────────────────


def table(
    headers: list[str],
    rows: list[list[str]],
    *,
    align: list[str] | None = None,
) -> str:
    if align is None:
        align = ["<"] * len(headers)
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    parts: list[str] = []
    hdr = []
    for i, h in enumerate(headers):
        fmt = ">" if align[i] == ">" else "<"
        hdr.append(f"{h:{fmt}{widths[i]}}")
    parts.append("  ".join(hdr))
    parts.append("  ".join("─" * w for w in widths))
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            fmt = ">" if align[i] == ">" else "<"
            cells.append(f"{cell:{fmt}{widths[i]}}")
        parts.append("  ".join(cells))
    return "\n".join(parts)


def pct(n: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{n / total * 100:.1f}%"


def render_summary(
    expected: dict[str, frozenset[str]],
    actual: dict[str, set[str]],
    scored_gaps: dict[str, list[tuple[str, float]]],
    subdomain_to_domain: dict[str, str],
) -> None:
    total_expected = sum(len(v) for v in expected.values())
    total_actual = sum(len(v) for v in actual.values())
    total_missing = sum(len(v) for v in scored_gaps.values())
    covered = total_expected - total_missing
    domains = {subdomain_to_domain.get(s, s) for s in expected}
    w = 18
    print("══════════════════════════════════════════════════════════")
    print("  COVERAGE DERIVATION ENGINE")
    print("══════════════════════════════════════════════════════════")
    print()
    print(f"  {'Expected concepts':<{w}}: {total_expected}")
    print(f"  {'Actual notes':<{w}}: {total_actual}")
    print(
        f"  {'Missing concepts':<{w}}: {total_missing}"
        f"  ({pct(covered, total_expected)} coverage)"
    )
    print(f"  {'Domains assessed':<{w}}: {len(domains)}")
    print(f"  {'Subdomains':<{w}}: {len(expected)}")
    print()


def render_domain_coverage(
    expected: dict[str, frozenset[str]],
    scored_gaps: dict[str, list[tuple[str, float]]],
    subdomain_to_domain: dict[str, str],
) -> None:
    domain_stats: dict[str, dict[str, int]] = {}
    for sub, concepts in expected.items():
        domain = subdomain_to_domain.get(sub, sub)
        stats = domain_stats.setdefault(domain, {"expected": 0, "missing": 0})
        stats["expected"] += len(concepts)
        if sub in scored_gaps:
            stats["missing"] += len(scored_gaps[sub])
    rows: list[list[str]] = []
    for domain in sorted(domain_stats):
        s = domain_stats[domain]
        exp, miss = s["expected"], s["missing"]
        act = exp - miss
        rows.append([domain, str(exp), str(act), str(miss), pct(act, exp)])
    rows.sort(key=lambda r: (-int(r[3]), r[0]))
    print("──────────────────────────────────────────────────────────")
    print("  DOMAIN COVERAGE")
    print("──────────────────────────────────────────────────────────")
    print()
    print(table(
        ["Domain", "Expected", "Actual", "Missing", "Coverage"],
        rows,
        align=["<", ">", ">", ">", ">"],
    ))
    print()


def render_subdomain_gaps(
    scored_gaps: dict[str, list[tuple[str, float]]],
    subdomain_to_domain: dict[str, str],
) -> None:
    if not scored_gaps:
        return
    print("──────────────────────────────────────────────────────────")
    print("  MISSING CONCEPTS BY SUBDOMAIN")
    print("──────────────────────────────────────────────────────────")
    print()
    for sub in sorted(scored_gaps):
        domain = subdomain_to_domain.get(sub, sub)
        print(f"  [{sub}] ({domain})")
        print()
        for i, (concept, score) in enumerate(scored_gaps[sub], 1):
            print(f"    {i}. {concept:<40s} score: {score:.1f}")
        print()


def render_ranked_list(
    scored_gaps: dict[str, list[tuple[str, float]]],
    subdomain_to_domain: dict[str, str],
    top_n: int | None,
) -> None:
    all_entries: list[tuple[float, str, str]] = []
    for sub, entries in scored_gaps.items():
        for concept, score in entries:
            all_entries.append((score, concept, sub))
    all_entries.sort(key=lambda x: (-x[0], x[1]))
    if top_n is not None:
        display = all_entries[:top_n]
    else:
        display = all_entries
    rows: list[list[str]] = []
    for rank, (score, concept, sub) in enumerate(display, 1):
        rows.append([str(rank), f"{score:.1f}", sub, concept])
    print("──────────────────────────────────────────────────────────")
    print("  TOP MISSING CONCEPTS (RANKED)")
    print("──────────────────────────────────────────────────────────")
    print()
    print(table(
        ["Rank", "Score", "Subdomain", "Concept"],
        rows,
        align=[">", ">", "<", "<"],
    ))
    total = sum(len(v) for v in scored_gaps.values())
    domain_count = len({subdomain_to_domain.get(s, s) for s in scored_gaps})
    print()
    print(f"  Total missing: {total} concepts across {domain_count} domains")
    print()


# ── Entry point ────────────────────────────────────────────────


def main(vault_path: Path | None = None) -> int:
    if vault_path is None:
        vault_path = _resolve_vault_path()
    _bind(vault_path)

    parser = argparse.ArgumentParser(
        description="Coverage Derivation Engine",
    )
    parser.add_argument(
        "--top", type=int, default=None,
        help="Limit ranked output to top N missing concepts",
    )
    parser.add_argument(
        "--domain", type=str, default=None,
        help="Filter output to a specific domain slug",
    )
    args = parser.parse_args()

    if not EXPECTED_CONCEPTS:
        print("ERROR: EXPECTED_CONCEPTS not defined or empty in vault_schema.py")
        return 1

    subdomain_to_domain = build_subdomain_to_domain()
    valid_subdomains = set(subdomain_to_domain.keys())

    key_errors = validate_expected_keys(EXPECTED_CONCEPTS, valid_subdomains)
    if key_errors:
        for e in key_errors:
            print(f"  SCHEMA ERROR: {e}")
        return 1

    slug_errors = validate_expected_slugs(EXPECTED_CONCEPTS)
    if slug_errors:
        for e in slug_errors:
            print(f"  SCHEMA ERROR: {e}")
        return 1

    try:
        validate_concept_uniqueness(EXPECTED_CONCEPTS)
    except ValueError as exc:
        print(f"  SCHEMA ERROR: {exc}")
        return 1

    actual = load_actual_concepts(VAULT_ROOT)

    for sub in sorted(EXPECTED_CONCEPTS):
        if sub not in actual:
            print(
                f"  WARNING: subdomain '{sub}' has expected concepts "
                f"but no actual notes"
            )

    raw_gaps = detect_gaps(EXPECTED_CONCEPTS, actual)
    scored_gaps = score_gaps(raw_gaps, subdomain_to_domain)

    if args.domain:
        matching = {
            s for s, d in subdomain_to_domain.items()
            if d == args.domain
        }
        scored_gaps = {k: v for k, v in scored_gaps.items() if k in matching}
        filtered_expected = {
            k: v for k, v in EXPECTED_CONCEPTS.items() if k in matching
        }
        filtered_actual = {k: v for k, v in actual.items() if k in matching}
    else:
        filtered_expected = dict(EXPECTED_CONCEPTS)
        filtered_actual = actual

    render_summary(
        filtered_expected, filtered_actual, scored_gaps, subdomain_to_domain,
    )
    render_domain_coverage(filtered_expected, scored_gaps, subdomain_to_domain)
    render_subdomain_gaps(scored_gaps, subdomain_to_domain)
    render_ranked_list(scored_gaps, subdomain_to_domain, args.top)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
