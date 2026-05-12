"""Trust, Staleness, and Evidence Metadata — Phase 25

Deterministic trust/staleness/evidence signalling for local LLMs and MCP clients.

Design principles:
- All rules are transparent, deterministic, and locally computed.
- No external service calls, no embeddings, no autonomous rewriting.
- Metadata is user/system-provided — not factual verification.
- Backwards-compatible: notes without trust fields continue to work.
- Confidence is symbolic, not statistical: high/medium/low/deprecated/unknown.

Optional frontmatter fields supported:
  trust_level:   verified | working | draft | external | deprecated
  source_type:   authored | imported | generated | agent_suggested
  last_reviewed: YYYY-MM-DD (ISO date)
  review_after:  YYYY-MM-DD (ISO date)

Staleness rules:
  review_after before today          => stale=True
  missing review_after               => freshness_unknown=True, stale=False
  missing last_reviewed              => review_unknown=True

Confidence mapping (symbolic):
  deprecated trust_level             => deprecated
  verified + not stale               => high
  verified + stale                   => medium
  working + not stale                => medium
  working + stale                    => low
  authored source_type (no level)    => medium
  draft/external/generated/agent_suggested => low or unknown
  stale with unknown level           => low
  missing all trust metadata         => unknown

Trust score (numeric, used for deterministic sort):
  verified:  80   deprecated: -100  working:  40
  draft:     10   external:   20    (missing): 25
  authored:  +10 bonus   generated: -5    agent_suggested: -10
  stale:     -20 penalty
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger("mcp.trust_metadata")

# ---------------------------------------------------------------------------
# Constants / config
# ---------------------------------------------------------------------------

VALID_TRUST_LEVELS: frozenset[str] = frozenset({
    "verified", "working", "draft", "external", "deprecated",
})

VALID_SOURCE_TYPES: frozenset[str] = frozenset({
    "authored", "imported", "generated", "agent_suggested",
})

_TRUST_LEVEL_SCORE: dict[str, int] = {
    "verified":   80,
    "working":    40,
    "external":   20,
    "draft":      10,
    "deprecated": -100,
}

_SOURCE_TYPE_BONUS: dict[str, int] = {
    "authored":        10,
    "imported":         0,
    "generated":       -5,
    "agent_suggested": -10,
}

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Config helper
# ---------------------------------------------------------------------------

def get_trust_config() -> dict[str, Any]:
    """Return the trust metadata configuration values."""
    return {
        "valid_trust_levels": sorted(VALID_TRUST_LEVELS),
        "valid_source_types": sorted(VALID_SOURCE_TYPES),
        "trust_level_scores": dict(_TRUST_LEVEL_SCORE),
        "source_type_bonuses": dict(_SOURCE_TYPE_BONUS),
        "stale_penalty": -20,
        "date_format": "YYYY-MM-DD",
        "confidence_levels": ["high", "medium", "low", "deprecated", "unknown"],
    }


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_iso_date(value: Any) -> date | None:
    """Parse an ISO YYYY-MM-DD string into a date object.

    Returns None if value is None, empty, or whitespace.
    Raises ValueError if value is present but not a valid ISO date.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if not _ISO_DATE_RE.match(s):
        raise ValueError(f"Invalid ISO date (expected YYYY-MM-DD): {value!r}")
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise ValueError(f"Invalid ISO date value: {value!r}")


def _today_utc() -> date:
    """Return today's date in UTC (deterministic server behaviour)."""
    return datetime.now(tz=timezone.utc).date()


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def normalise_trust_level(value: Any) -> str | None:
    """Normalise and validate a trust_level value.

    Returns the normalised string or None if value is None/empty.
    Raises ValueError if value is present but not a valid trust level.
    """
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    if s not in VALID_TRUST_LEVELS:
        raise ValueError(
            f"Invalid trust_level {value!r}. "
            f"Allowed: {sorted(VALID_TRUST_LEVELS)}"
        )
    return s


def normalise_source_type(value: Any) -> str | None:
    """Normalise and validate a source_type value.

    Returns the normalised string or None if value is None/empty.
    Raises ValueError if value is present but not a valid source type.
    """
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    if s not in VALID_SOURCE_TYPES:
        raise ValueError(
            f"Invalid source_type {value!r}. "
            f"Allowed: {sorted(VALID_SOURCE_TYPES)}"
        )
    return s


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def extract_trust_metadata(note: dict) -> dict[str, Any]:
    """Extract trust/staleness fields from a note's fields dict.

    Returns a dict with:
      trust_level     (str | None)
      source_type     (str | None)
      last_reviewed   (str | None) — original string from frontmatter
      review_after    (str | None) — original string from frontmatter
      parse_errors    (list[str])  — any parse/validation errors found

    Note: never raises; errors are collected in parse_errors.
    """
    fields = note.get("fields") or {}
    errors: list[str] = []

    # trust_level
    raw_trust = fields.get("trust_level")
    trust_level: str | None = None
    if raw_trust is not None and str(raw_trust).strip():
        try:
            trust_level = normalise_trust_level(raw_trust)
        except ValueError as exc:
            errors.append(str(exc))

    # source_type
    raw_source = fields.get("source_type")
    source_type: str | None = None
    if raw_source is not None and str(raw_source).strip():
        try:
            source_type = normalise_source_type(raw_source)
        except ValueError as exc:
            errors.append(str(exc))

    # last_reviewed
    raw_last = fields.get("last_reviewed")
    last_reviewed: str | None = None
    if raw_last is not None and str(raw_last).strip():
        try:
            parse_iso_date(raw_last)  # validates format
            last_reviewed = str(raw_last).strip()
        except ValueError as exc:
            errors.append(str(exc))

    # review_after
    raw_after = fields.get("review_after")
    review_after: str | None = None
    if raw_after is not None and str(raw_after).strip():
        try:
            parse_iso_date(raw_after)
            review_after = str(raw_after).strip()
        except ValueError as exc:
            errors.append(str(exc))

    return {
        "trust_level": trust_level,
        "source_type": source_type,
        "last_reviewed": last_reviewed,
        "review_after": review_after,
        "parse_errors": errors,
    }


# ---------------------------------------------------------------------------
# Staleness computation
# ---------------------------------------------------------------------------

def compute_staleness(metadata: dict, today: date | None = None) -> dict[str, Any]:
    """Compute staleness flags from trust metadata.

    Args:
        metadata:  Output of extract_trust_metadata().
        today:     Override today's date (use for deterministic tests).

    Returns dict with:
      stale                (bool)
      freshness_unknown    (bool) — review_after missing
      review_unknown       (bool) — last_reviewed missing
      review_after         (str | None)
      last_reviewed        (str | None)
      days_overdue         (int | None) — if stale, how many days past review_after
    """
    if today is None:
        today = _today_utc()

    review_after_str = metadata.get("review_after")
    last_reviewed_str = metadata.get("last_reviewed")

    stale = False
    freshness_unknown = False
    days_overdue: int | None = None

    if review_after_str:
        try:
            ra_date = parse_iso_date(review_after_str)
            if ra_date is not None and ra_date < today:
                stale = True
                days_overdue = (today - ra_date).days
        except ValueError:
            # Invalid date — not stale, but parse error surfaced elsewhere
            freshness_unknown = True
    else:
        freshness_unknown = True

    review_unknown = not bool(last_reviewed_str)

    return {
        "stale": stale,
        "freshness_unknown": freshness_unknown,
        "review_unknown": review_unknown,
        "review_after": review_after_str,
        "last_reviewed": last_reviewed_str,
        "days_overdue": days_overdue,
    }


# ---------------------------------------------------------------------------
# Confidence computation
# ---------------------------------------------------------------------------

def compute_confidence(metadata: dict, staleness: dict | None = None) -> str:
    """Return symbolic confidence: high | medium | low | deprecated | unknown.

    Rules (in priority order):
    1. deprecated trust_level => 'deprecated'
    2. verified + not stale   => 'high'
    3. verified + stale       => 'medium'
    4. working + not stale    => 'medium'
    5. working + stale        => 'low'
    6. authored source_type (no trust level) + not stale => 'medium'
    7. draft / external       => 'low'
    8. generated / agent_suggested => 'low'
    9. stale with no trust_level  => 'low'
    10. missing all metadata      => 'unknown'

    IMPORTANT: confidence is metadata-based signalling only.
    It does NOT indicate factual correctness.
    """
    trust_level = metadata.get("trust_level")
    source_type = metadata.get("source_type")

    stale = False
    if staleness is not None:
        stale = bool(staleness.get("stale"))

    # Rule 1: deprecated always => deprecated
    if trust_level == "deprecated":
        return "deprecated"

    # Rule 2-3: verified
    if trust_level == "verified":
        return "high" if not stale else "medium"

    # Rule 4-5: working
    if trust_level == "working":
        return "medium" if not stale else "low"

    # Rule 6: authored source_type acts as implicit 'working'
    if source_type == "authored" and trust_level is None:
        return "medium" if not stale else "low"

    # Rule 7-8: draft / external / generated / agent_suggested
    if trust_level in ("draft", "external") or source_type in (
        "imported", "generated", "agent_suggested"
    ):
        return "low"

    # Rule 9: stale with unknown trust
    if stale:
        return "low"

    # Rule 10: no trust metadata at all
    return "unknown"


# ---------------------------------------------------------------------------
# Trust scoring (for deterministic sort)
# ---------------------------------------------------------------------------

def score_note_trust(metadata: dict, staleness: dict | None = None) -> int:
    """Return a numeric trust score for deterministic ordering.

    Higher score = preferred in evidence queries.
    Stale notes are penalised by 20 points.
    """
    trust_level = metadata.get("trust_level")
    source_type = metadata.get("source_type")

    score = _TRUST_LEVEL_SCORE.get(trust_level, 25) if trust_level else 25
    score += _SOURCE_TYPE_BONUS.get(source_type, 0) if source_type else 0

    if staleness and staleness.get("stale"):
        score -= 20

    return score


# ---------------------------------------------------------------------------
# Note annotation
# ---------------------------------------------------------------------------

def annotate_notes_with_trust(
    notes: list[dict],
    today: date | None = None,
) -> list[dict]:
    """Add trust_metadata block to each note (non-destructive).

    Each note gets a 'trust_metadata' key added. Original data is preserved.
    """
    if today is None:
        today = _today_utc()
    annotated = []
    for note in notes:
        n = dict(note)
        meta = extract_trust_metadata(note)
        staleness = compute_staleness(meta, today=today)
        confidence = compute_confidence(meta, staleness)
        trust_score = score_note_trust(meta, staleness)
        n["trust_metadata"] = {
            "trust_level": meta["trust_level"],
            "source_type": meta["source_type"],
            "last_reviewed": meta["last_reviewed"],
            "review_after": meta["review_after"],
            "stale": staleness["stale"],
            "freshness_unknown": staleness["freshness_unknown"],
            "review_unknown": staleness["review_unknown"],
            "days_overdue": staleness["days_overdue"],
            "confidence": confidence,
            "trust_score": trust_score,
        }
        annotated.append(n)
    return annotated


# ---------------------------------------------------------------------------
# Vault-level trust summary
# ---------------------------------------------------------------------------

def list_trust_summary(vault_name: str) -> dict[str, Any]:
    """Return vault-level trust/source/staleness summary.

    Returns a dict with:
      status
      vault
      counts_by_trust_level  (dict)
      counts_by_source_type  (dict)
      confidence_distribution (dict)
      missing_metadata_count (int)
      deprecated_count       (int)
      stale_count            (int)
      freshness_unknown_count (int)
      review_unknown_count   (int)
      notes                  (list) — each note with path and trust_metadata
    """
    try:
        from mcp.core.vault_registry import list_vaults
        from mcp.core.note_index import get_index, build_index

        if vault_name not in list_vaults():
            return {
                "status": "error",
                "error": {"code": "INVALID_VAULT", "message": f"Vault not found: {vault_name!r}"},
            }

        build_index(vault_name)
        notes = get_index(vault_name)
        today = _today_utc()
        annotated = annotate_notes_with_trust(notes, today=today)

        counts_trust: dict[str, int] = {}
        counts_source: dict[str, int] = {}
        confidence_dist: dict[str, int] = {}
        missing_meta = 0
        deprecated_count = 0
        stale_count = 0
        freshness_unknown_count = 0
        review_unknown_count = 0

        note_summaries: list[dict] = []
        for note in annotated:
            tm = note["trust_metadata"]
            tl = tm["trust_level"] or "missing"
            st = tm["source_type"] or "missing"
            conf = tm["confidence"]

            counts_trust[tl] = counts_trust.get(tl, 0) + 1
            counts_source[st] = counts_source.get(st, 0) + 1
            confidence_dist[conf] = confidence_dist.get(conf, 0) + 1

            if tm["trust_level"] is None and tm["source_type"] is None:
                missing_meta += 1
            if tm["trust_level"] == "deprecated":
                deprecated_count += 1
            if tm["stale"]:
                stale_count += 1
            if tm["freshness_unknown"]:
                freshness_unknown_count += 1
            if tm["review_unknown"]:
                review_unknown_count += 1

            note_summaries.append({
                "path": note["path"],
                "trust_metadata": tm,
            })

        # Deterministic sort: by path
        note_summaries.sort(key=lambda n: n["path"].lower())

        return {
            "status": "ok",
            "vault": vault_name,
            "counts_by_trust_level": counts_trust,
            "counts_by_source_type": counts_source,
            "confidence_distribution": confidence_dist,
            "missing_metadata_count": missing_meta,
            "deprecated_count": deprecated_count,
            "stale_count": stale_count,
            "freshness_unknown_count": freshness_unknown_count,
            "review_unknown_count": review_unknown_count,
            "notes": note_summaries,
        }
    except Exception as exc:
        logger.exception("list_trust_summary vault=%s", vault_name)
        return {
            "status": "error",
            "error": {"code": "TRUST_SUMMARY_FAILED", "message": str(exc)},
        }


# ---------------------------------------------------------------------------
# Stale notes list
# ---------------------------------------------------------------------------

def list_stale_notes(
    vault_name: str,
    today: date | None = None,
) -> dict[str, Any]:
    """Return stale/review information for a vault.

    Returns a dict with:
      status
      vault
      today (ISO string used for calculation)
      stale_notes       (list)
      freshness_unknown (list)
      review_unknown    (list)
      deprecated_notes  (list)
    """
    try:
        from mcp.core.vault_registry import list_vaults
        from mcp.core.note_index import get_index, build_index

        if vault_name not in list_vaults():
            return {
                "status": "error",
                "error": {"code": "INVALID_VAULT", "message": f"Vault not found: {vault_name!r}"},
            }

        if today is None:
            today = _today_utc()

        build_index(vault_name)
        notes = get_index(vault_name)
        annotated = annotate_notes_with_trust(notes, today=today)

        stale: list[dict] = []
        freshness_unknown: list[dict] = []
        review_unknown: list[dict] = []
        deprecated: list[dict] = []

        for note in annotated:
            tm = note["trust_metadata"]
            entry = {"path": note["path"], "trust_metadata": tm}
            if tm["stale"]:
                stale.append(entry)
            if tm["freshness_unknown"]:
                freshness_unknown.append(entry)
            if tm["review_unknown"]:
                review_unknown.append(entry)
            if tm["trust_level"] == "deprecated":
                deprecated.append(entry)

        # Deterministic sort
        for lst in (stale, freshness_unknown, review_unknown, deprecated):
            lst.sort(key=lambda n: n["path"].lower())

        return {
            "status": "ok",
            "vault": vault_name,
            "today": today.isoformat(),
            "stale_notes": stale,
            "freshness_unknown": freshness_unknown,
            "review_unknown": review_unknown,
            "deprecated_notes": deprecated,
        }
    except Exception as exc:
        logger.exception("list_stale_notes vault=%s", vault_name)
        return {
            "status": "error",
            "error": {"code": "STALE_NOTES_FAILED", "message": str(exc)},
        }


# ---------------------------------------------------------------------------
# Evidence status summary
# ---------------------------------------------------------------------------

def evidence_status_summary(vault_name: str) -> dict[str, Any]:
    """Return a brief evidence status summary for the vault."""
    trust = list_trust_summary(vault_name)
    if trust.get("status") == "error":
        return trust
    stale = list_stale_notes(vault_name)
    if stale.get("status") == "error":
        return stale
    return {
        "status": "ok",
        "vault": vault_name,
        "total_notes": len(trust.get("notes", [])),
        "deprecated_count": trust.get("deprecated_count", 0),
        "stale_count": trust.get("stale_count", 0),
        "missing_metadata_count": trust.get("missing_metadata_count", 0),
        "confidence_distribution": trust.get("confidence_distribution", {}),
    }


# ---------------------------------------------------------------------------
# Evidence builder
# ---------------------------------------------------------------------------

def _make_evidence_id(
    vault_name: str,
    filters: dict,
    q: str | None,
    profile: str | None,
    mode: str | None,
    prefer_verified: bool,
    include_deprecated: bool,
    include_stale: bool,
    max_notes: int,
) -> str:
    """Return a deterministic 16-char hex evidence ID from effective request params."""
    params = json.dumps(
        {
            "vault": vault_name,
            "filters": sorted(filters.items()) if filters else [],
            "q": q or "",
            "profile": profile or "",
            "mode": mode or "",
            "prefer_verified": prefer_verified,
            "include_deprecated": include_deprecated,
            "include_stale": include_stale,
            "max_notes": max_notes,
        },
        sort_keys=True,
    )
    return hashlib.sha256(params.encode()).hexdigest()[:16]


def _extract_sections(note: dict, include_sections: list[str] | None) -> dict[str, str]:
    """Extract requested sections from note body."""
    if not include_sections:
        return {}
    body = note.get("body") or ""
    sections: dict[str, str] = {}
    lines = body.split("\n")
    for section_name in include_sections:
        # Try to find "## <section_name>" heading
        heading = f"## {section_name}"
        found_idx: int | None = None
        for i, line in enumerate(lines):
            if line.rstrip() == heading:
                found_idx = i
                break
        if found_idx is None:
            sections[section_name] = ""
            continue
        body_lines: list[str] = []
        for j in range(found_idx + 1, len(lines)):
            if lines[j].startswith("## ") and not lines[j].startswith("### "):
                break
            body_lines.append(lines[j])
        sections[section_name] = "\n".join(body_lines).strip()
    return sections


def build_evidence(
    vault_name: str,
    filters: dict | None = None,
    q: str | None = None,
    profile: str | None = None,
    mode: str | None = None,
    include_sections: list[str] | None = None,
    max_notes: int = 20,
    prefer_verified: bool = True,
    include_deprecated: bool = False,
    include_stale: bool = True,
    today: date | None = None,
) -> dict[str, Any]:
    """Build an evidence response for a vault query.

    Returns structured evidence with:
      evidence_id       (deterministic 16-char hex)
      vault
      query_params      (echoed effective request)
      notes             (list, sorted by trust score then path)
      warnings          (list)
      summary           (dict)

    Each note includes:
      path, fields, trust_metadata, confidence, stale, sections, evidence_refs

    Does NOT:
      - call external services
      - use embeddings or semantic retrieval
      - claim factual correctness
    """
    try:
        from mcp.core.vault_registry import list_vaults
        from mcp.core.note_index import get_index, build_index

        if vault_name not in list_vaults():
            return {
                "status": "error",
                "error": {"code": "INVALID_VAULT", "message": f"Vault not found: {vault_name!r}"},
            }

        if filters is None:
            filters = {}
        if today is None:
            today = _today_utc()

        # Validate max_notes
        if not isinstance(max_notes, int) or max_notes < 1 or max_notes > 100:
            return {
                "status": "error",
                "error": {
                    "code": "INVALID_EVIDENCE_REQUEST",
                    "message": "max_notes must be an integer between 1 and 100",
                },
            }

        build_index(vault_name)
        notes = get_index(vault_name)

        # Apply frontmatter filters
        if filters:
            try:
                notes = _apply_filters(notes, filters)
            except ValueError as exc:
                return {
                    "status": "error",
                    "error": {"code": "INVALID_FILTER", "message": str(exc)},
                }

        # Apply lexical query
        if q:
            q_stripped = q.strip()
            if len(q_stripped) > 1000:
                return {
                    "status": "error",
                    "error": {
                        "code": "INVALID_QUERY",
                        "message": "q exceeds maximum length of 1000 characters",
                    },
                }
            notes = _apply_lexical_q(notes, q_stripped)

        # Annotate with trust metadata
        annotated = annotate_notes_with_trust(notes, today=today)

        # Filter deprecated
        if not include_deprecated:
            annotated = [
                n for n in annotated
                if n["trust_metadata"]["trust_level"] != "deprecated"
            ]

        # Filter stale
        if not include_stale:
            annotated = [
                n for n in annotated
                if not n["trust_metadata"]["stale"]
            ]

        # Sort: higher trust_score first, then by path (deterministic tiebreak)
        if prefer_verified:
            annotated.sort(
                key=lambda n: (-n["trust_metadata"]["trust_score"], n["path"].lower())
            )
        else:
            annotated.sort(key=lambda n: n["path"].lower())

        # Apply max_notes limit
        warnings: list[str] = []
        total_before_limit = len(annotated)
        annotated = annotated[:max_notes]
        if total_before_limit > max_notes:
            warnings.append(
                f"{total_before_limit - max_notes} note(s) excluded by max_notes={max_notes} limit"
            )

        # Deprecated exclusion warning
        if not include_deprecated:
            all_notes_raw = get_index(vault_name)
            dep_count = sum(
                1 for n in all_notes_raw
                if (n.get("fields") or {}).get("trust_level") == "deprecated"
            )
            if dep_count > 0:
                warnings.append(
                    f"{dep_count} deprecated note(s) excluded (include_deprecated=False)"
                )

        # Build evidence note list
        evidence_notes: list[dict] = []
        for note in annotated:
            tm = note["trust_metadata"]
            secs = _extract_sections(note, include_sections)
            # Build evidence_refs (section references)
            evidence_refs: list[dict] = []
            path = note["path"]
            if include_sections:
                for sec_name, sec_body in secs.items():
                    if sec_body:
                        evidence_refs.append({
                            "path": path,
                            "section": sec_name,
                        })
            # If no sections, add a path-only reference
            if not evidence_refs:
                evidence_refs.append({"path": path, "section": None})

            evidence_notes.append({
                "path": path,
                "fields": note.get("fields") or {},
                "trust_metadata": tm,
                "confidence": tm["confidence"],
                "stale": tm["stale"],
                "sections": secs,
                "evidence_refs": evidence_refs,
            })

        evidence_id = _make_evidence_id(
            vault_name, filters, q, profile, mode,
            prefer_verified, include_deprecated, include_stale, max_notes,
        )

        summary = {
            "total_notes": len(evidence_notes),
            "high_confidence": sum(1 for n in evidence_notes if n["confidence"] == "high"),
            "medium_confidence": sum(1 for n in evidence_notes if n["confidence"] == "medium"),
            "low_confidence": sum(1 for n in evidence_notes if n["confidence"] == "low"),
            "unknown_confidence": sum(1 for n in evidence_notes if n["confidence"] == "unknown"),
            "stale_included": sum(1 for n in evidence_notes if n["stale"]),
        }

        confidence_disclaimer = (
            "Confidence reflects note maintenance metadata (review schedule, "
            "trust level, source type), not factual correctness. Always verify "
            "claims against authoritative sources before acting on this evidence."
        )

        return {
            "status": "ok",
            "evidence_id": evidence_id,
            "vault": vault_name,
            "confidence_disclaimer": confidence_disclaimer,
            "query_params": {
                "filters": filters,
                "q": q,
                "profile": profile,
                "mode": mode,
                "prefer_verified": prefer_verified,
                "include_deprecated": include_deprecated,
                "include_stale": include_stale,
                "max_notes": max_notes,
                "include_sections": include_sections,
            },
            "notes": evidence_notes,
            "warnings": warnings,
            "summary": summary,
        }
    except Exception as exc:
        logger.exception("build_evidence vault=%s", vault_name)
        return {
            "status": "error",
            "error": {"code": "EVIDENCE_BUILD_FAILED", "message": str(exc)},
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_filters(notes: list[dict], filters: dict) -> list[dict]:
    """Apply simple equality filters on note fields."""
    result = []
    for note in notes:
        fields = note.get("fields") or {}
        match = True
        for key, value in filters.items():
            if fields.get(key) != value:
                match = False
                break
        if match:
            result.append(note)
    return result


def _apply_lexical_q(notes: list[dict], q: str) -> list[dict]:
    """Filter notes to those whose body or path contains any query term."""
    if not q:
        return notes
    tokens = re.findall(r"[a-z0-9]+", q.lower())
    if not tokens:
        return notes
    result = []
    for note in notes:
        text = " ".join([
            note.get("path") or "",
            note.get("body") or "",
            " ".join(str(v) for v in (note.get("fields") or {}).values()),
        ]).lower()
        if any(t in text for t in tokens):
            result.append(note)
    return result
