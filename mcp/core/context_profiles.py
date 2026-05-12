"""Context Profile Service — Phase 24

Provides built-in device/context profiles and bundle modes for deterministic,
bounded context generation targeted at constrained clients (small LLMs on phones,
desktop agents, MCP-compatible tools, etc.).

Design principles:
- All profiles are deterministic, local, and human-readable.
- No secrets, no arbitrary file paths, no network calls.
- Hard caps are always enforced after any profile merge.
- Unknown profile/mode names return INVALID_PROFILE.
- If both profile and mode are supplied, profile takes precedence (more specific).
- Existing explicit bundle requests without profile/mode are unaffected.

Hard caps:
  max_notes     <= 100
  max_chars     <= 500_000
  include_sections list length <= 20

Built-in modes:
  tiny, small, medium, large, agent

Built-in device profiles:
  phone-local-llm, desktop-agent, full-review
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Hard caps — enforced after any merge; cannot be exceeded by any profile
# ---------------------------------------------------------------------------

HARD_MAX_NOTES: int = 100
HARD_MAX_CHARS: int = 500_000
HARD_MAX_SECTIONS: int = 20

# ---------------------------------------------------------------------------
# Allowed profile keys — unknown keys are rejected by validate_context_profile
# ---------------------------------------------------------------------------

_ALLOWED_PROFILE_KEYS: frozenset[str] = frozenset({
    "name",
    "label",
    "description",
    "max_notes",
    "max_chars",
    "include_body",
    "include_related",
    "include_sections",
    "allow_partial",
    "require_security_scan",
    "prefer_complete",
})

# Keys that are merged into requests (not cosmetic/metadata-only)
_MERGEABLE_FIELDS: tuple[str, ...] = (
    "max_notes",
    "max_chars",
    "include_body",
    "include_related",
    "include_sections",
    "allow_partial",
)

# ---------------------------------------------------------------------------
# Built-in bundle modes
# ---------------------------------------------------------------------------

_BUILTIN_MODES: dict[str, dict[str, Any]] = {
    "tiny": {
        "name": "tiny",
        "label": "Tiny",
        "description": "Minimal context for very constrained local LLMs (≤4 K chars).",
        "max_notes": 3,
        "max_chars": 4_000,
        "include_body": False,
        "include_related": False,
        "include_sections": ["Key Principles"],
        "allow_partial": False,
        "require_security_scan": True,
        "prefer_complete": True,
    },
    "small": {
        "name": "small",
        "label": "Small",
        "description": "Compact context for phone-class local LLMs (≤8 K chars).",
        "max_notes": 5,
        "max_chars": 8_000,
        "include_body": False,
        "include_related": False,
        "include_sections": ["Key Principles", "How It Works"],
        "allow_partial": False,
        "require_security_scan": True,
        "prefer_complete": True,
    },
    "medium": {
        "name": "medium",
        "label": "Medium",
        "description": "Balanced context for mid-range clients (≤20 K chars).",
        "max_notes": 10,
        "max_chars": 20_000,
        "include_body": True,
        "include_related": False,
        "include_sections": ["Key Principles", "How It Works", "Trade-offs"],
        "allow_partial": False,
        "require_security_scan": True,
        "prefer_complete": True,
    },
    "large": {
        "name": "large",
        "label": "Large",
        "description": "Full context for high-capacity clients (≤50 K chars).",
        "max_notes": 25,
        "max_chars": 50_000,
        "include_body": True,
        "include_related": True,
        "include_sections": ["Key Principles", "How It Works", "Trade-offs"],
        "allow_partial": True,
        "require_security_scan": True,
        "prefer_complete": True,
    },
    "agent": {
        "name": "agent",
        "label": "Agent",
        "description": "Context for desktop agents with full graph data (≤100 K chars).",
        "max_notes": 15,
        "max_chars": 100_000,
        "include_body": True,
        "include_related": True,
        "include_sections": ["Key Principles", "How It Works", "Trade-offs"],
        "allow_partial": False,
        "require_security_scan": True,
        "prefer_complete": True,
    },
}

# ---------------------------------------------------------------------------
# Built-in device profiles
# ---------------------------------------------------------------------------

_BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "phone-local-llm": {
        "name": "phone-local-llm",
        "label": "Phone Local LLM",
        "description": "Bounded context for local LLMs running on mobile devices.",
        "max_notes": 5,
        "max_chars": 8_000,
        "include_body": False,
        "include_related": False,
        "include_sections": ["Key Principles", "How It Works"],
        "allow_partial": False,
        "require_security_scan": True,
        "prefer_complete": True,
    },
    "desktop-agent": {
        "name": "desktop-agent",
        "label": "Desktop Agent",
        "description": "Full agent context for desktop-class LLM agents.",
        "max_notes": 15,
        "max_chars": 30_000,
        "include_body": True,
        "include_related": True,
        "include_sections": ["Key Principles", "How It Works", "Trade-offs"],
        "allow_partial": False,
        "require_security_scan": True,
        "prefer_complete": True,
    },
    "full-review": {
        "name": "full-review",
        "label": "Full Review",
        "description": "Maximum context for review workflows with full graph.",
        "max_notes": 25,
        "max_chars": 50_000,
        "include_body": True,
        "include_related": True,
        "include_sections": ["Key Principles", "How It Works", "Trade-offs"],
        "allow_partial": True,
        "require_security_scan": True,
        "prefer_complete": True,
    },
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_builtin_modes() -> dict[str, dict[str, Any]]:
    """Return a copy of built-in mode definitions (keyed by mode name)."""
    return {k: dict(v) for k, v in _BUILTIN_MODES.items()}


def get_builtin_profiles() -> dict[str, dict[str, Any]]:
    """Return a copy of built-in device profile definitions (keyed by profile name)."""
    return {k: dict(v) for k, v in _BUILTIN_PROFILES.items()}


def normalise_profile_name(name: str) -> str:
    """Normalise a profile or mode name: strip whitespace, lowercase."""
    return name.strip().lower()


def list_context_profiles() -> dict:
    """Return all available profiles, modes, and defaults.

    Returns::

        {
            "profiles": {name: {...}},
            "modes":    {name: {...}},
            "defaults": {"mode": "medium", "profile": None},
        }
    """
    return {
        "profiles": get_builtin_profiles(),
        "modes": get_builtin_modes(),
        "defaults": {"mode": "medium", "profile": None},
    }


def get_context_profile(profile_name: str) -> dict:
    """Get a single named profile (device profile or mode).

    Checks device profiles first, then modes.

    Returns::

        # success
        {"status": "ok", "profile": {...}, "source": "builtin"}
        # error
        {"status": "error", "error": {"code": "INVALID_PROFILE", "message": ...}}
    """
    name = normalise_profile_name(profile_name)

    if name in _BUILTIN_PROFILES:
        profile = dict(_BUILTIN_PROFILES[name])
        return {"status": "ok", "profile": profile, "source": "builtin"}

    if name in _BUILTIN_MODES:
        profile = dict(_BUILTIN_MODES[name])
        return {"status": "ok", "profile": profile, "source": "builtin"}

    known = sorted(_BUILTIN_PROFILES) + sorted(_BUILTIN_MODES)
    return {
        "status": "error",
        "error": {
            "code": "INVALID_PROFILE",
            "message": (
                f"Unknown profile or mode: {profile_name!r}. "
                f"Known: {known}"
            ),
        },
    }


def resolve_context_profile(
    profile_name: str | None = None,
    mode: str | None = None,
) -> dict:
    """Resolve a profile_name and/or mode to a concrete profile dict.

    If both profile_name and mode are supplied, profile_name takes precedence
    (device profile is more specific than a generic mode).  This means the
    caller should not silently ignore a supplied mode; it is documented that
    profile overrides mode when both are present.

    Returns::

        # success — profile found
        {
            "status": "ok",
            "profile": {...},
            "profile_used": str | None,
            "mode_used": str | None,
            "profile_source": "builtin" | "config" | "none",
        }
        # success — neither profile nor mode supplied
        {
            "status": "ok",
            "profile": None,
            "profile_used": None,
            "mode_used": None,
            "profile_source": "none",
        }
        # error
        {"status": "error", "error": {"code": "INVALID_PROFILE", "message": ...}}
    """
    if profile_name:
        name = normalise_profile_name(profile_name)
        if name in _BUILTIN_PROFILES:
            profile = dict(_BUILTIN_PROFILES[name])
            return {
                "status": "ok",
                "profile": profile,
                "profile_used": name,
                "mode_used": None,
                "profile_source": "builtin",
            }
        return {
            "status": "error",
            "error": {
                "code": "INVALID_PROFILE",
                "message": (
                    f"Unknown profile: {profile_name!r}. "
                    f"Known profiles: {sorted(_BUILTIN_PROFILES)}"
                ),
            },
        }

    if mode:
        m = normalise_profile_name(mode)
        if m in _BUILTIN_MODES:
            profile = dict(_BUILTIN_MODES[m])
            return {
                "status": "ok",
                "profile": profile,
                "profile_used": None,
                "mode_used": m,
                "profile_source": "builtin",
            }
        return {
            "status": "error",
            "error": {
                "code": "INVALID_PROFILE",
                "message": (
                    f"Unknown mode: {mode!r}. "
                    f"Known modes: {sorted(_BUILTIN_MODES)}"
                ),
            },
        }

    # Neither profile nor mode supplied — no-op, return sentinel
    return {
        "status": "ok",
        "profile": None,
        "profile_used": None,
        "mode_used": None,
        "profile_source": "none",
    }


def validate_context_profile(profile: dict) -> list[str]:
    """Validate a profile dict (used for custom/config profiles).

    Returns:
        List of error message strings.  Empty list means valid.
    """
    errors: list[str] = []

    # Reject unknown keys
    unknown = set(profile.keys()) - _ALLOWED_PROFILE_KEYS
    if unknown:
        errors.append(f"Unknown profile keys: {sorted(unknown)}")

    max_chars = profile.get("max_chars")
    if max_chars is not None:
        if not isinstance(max_chars, int) or max_chars < 1:
            errors.append("max_chars must be a positive integer")
        elif max_chars > HARD_MAX_CHARS:
            errors.append(f"max_chars {max_chars} exceeds hard cap of {HARD_MAX_CHARS}")

    max_notes = profile.get("max_notes")
    if max_notes is not None:
        if not isinstance(max_notes, int) or max_notes < 1:
            errors.append("max_notes must be a positive integer")
        elif max_notes > HARD_MAX_NOTES:
            errors.append(f"max_notes {max_notes} exceeds hard cap of {HARD_MAX_NOTES}")

    include_sections = profile.get("include_sections")
    if include_sections is not None:
        if not isinstance(include_sections, list):
            errors.append("include_sections must be a list")
        elif len(include_sections) == 0:
            errors.append("include_sections must not be empty")
        elif len(include_sections) > HARD_MAX_SECTIONS:
            errors.append(
                f"include_sections length {len(include_sections)} "
                f"exceeds maximum of {HARD_MAX_SECTIONS}"
            )

    return errors


def apply_context_profile_to_request(
    request: dict,
    profile_name: str | None = None,
    mode: str | None = None,
    _resolved_profile: dict | None = None,
    _profile_used: str | None = None,
    _mode_used: str | None = None,
    _profile_source: str = "none",
) -> dict:
    """Merge profile/mode defaults into a sparse request dict.

    Profile values are used as *defaults* only — explicit request fields
    always override profile defaults.  Hard caps are enforced after merge
    regardless of source.

    Args:
        request:           Dict with explicit request fields (may be sparse).
        profile_name:      Named device profile to resolve and apply.
        mode:              Bundle mode to apply (ignored if profile_name given).
        _resolved_profile: Pre-resolved profile dict (skips resolution step).
        _profile_used:     For pre-resolved profiles — name to record.
        _mode_used:        For pre-resolved modes — name to record.
        _profile_source:   For pre-resolved profiles — source label.

    Returns::

        {
            "request": {...merged and capped fields...},
            "profile_metadata": {
                "profile_used": str | None,
                "mode_used": str | None,
                "profile_source": "builtin" | "config" | "none",
                "effective_budget": {"max_notes": int | None, "max_chars": int | None},
                "require_security_scan": bool,
            },
            "warnings": [...],
            "error": None | {"code": ..., "message": ...},
        }
    """
    warnings: list[str] = []

    # Resolve profile if not pre-supplied
    if _resolved_profile is None:
        resolved = resolve_context_profile(profile_name=profile_name, mode=mode)
        if resolved["status"] == "error":
            return {
                "request": request,
                "profile_metadata": _empty_profile_metadata(),
                "warnings": warnings,
                "error": resolved["error"],
            }
        profile = resolved.get("profile")
        profile_used = resolved.get("profile_used")
        mode_used = resolved.get("mode_used")
        profile_source = resolved.get("profile_source", "none")
    else:
        profile = _resolved_profile
        profile_used = _profile_used
        mode_used = _mode_used
        profile_source = _profile_source

    if profile is None:
        # No profile/mode — pass request through unchanged
        return {
            "request": request,
            "profile_metadata": _empty_profile_metadata(),
            "warnings": warnings,
            "error": None,
        }

    # Validate profile (guards against future config-file profiles)
    errs = validate_context_profile(profile)
    if errs:
        return {
            "request": request,
            "profile_metadata": _empty_profile_metadata(),
            "warnings": warnings,
            "error": {"code": "INVALID_PROFILE", "message": "; ".join(errs)},
        }

    # Merge: profile values fill in only fields absent from the request
    merged = dict(request)
    overrides_applied: list[str] = []

    for field in _MERGEABLE_FIELDS:
        if field not in merged and field in profile:
            merged[field] = profile[field]
        elif field in merged and field in profile and merged[field] != profile[field]:
            overrides_applied.append(field)

    if overrides_applied:
        warnings.append(
            f"Explicit request fields override profile defaults: "
            f"{sorted(overrides_applied)}"
        )

    # Enforce hard caps after merge
    if "max_notes" in merged:
        if isinstance(merged["max_notes"], int) and merged["max_notes"] > HARD_MAX_NOTES:
            warnings.append(
                f"max_notes capped from {merged['max_notes']} to {HARD_MAX_NOTES}"
            )
            merged["max_notes"] = HARD_MAX_NOTES

    if "max_chars" in merged:
        if isinstance(merged["max_chars"], int) and merged["max_chars"] > HARD_MAX_CHARS:
            warnings.append(
                f"max_chars capped from {merged['max_chars']} to {HARD_MAX_CHARS}"
            )
            merged["max_chars"] = HARD_MAX_CHARS

    require_security_scan = bool(profile.get("require_security_scan", True))

    profile_metadata = {
        "profile_used": profile_used,
        "mode_used": mode_used,
        "profile_source": profile_source,
        "effective_budget": {
            "max_notes": merged.get("max_notes"),
            "max_chars": merged.get("max_chars"),
        },
        "require_security_scan": require_security_scan,
    }

    return {
        "request": merged,
        "profile_metadata": profile_metadata,
        "warnings": warnings,
        "error": None,
    }


def profile_status_summary() -> dict:
    """Return a compact summary of profile service state for health/status endpoints."""
    return {
        "builtin_modes": sorted(_BUILTIN_MODES.keys()),
        "builtin_profiles": sorted(_BUILTIN_PROFILES.keys()),
        "hard_caps": {
            "max_notes": HARD_MAX_NOTES,
            "max_chars": HARD_MAX_CHARS,
            "max_sections": HARD_MAX_SECTIONS,
        },
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _empty_profile_metadata() -> dict:
    """Empty profile metadata sentinel (used when no profile is active)."""
    return {
        "profile_used": None,
        "mode_used": None,
        "profile_source": "none",
        "effective_budget": {"max_notes": None, "max_chars": None},
        "require_security_scan": False,
    }
