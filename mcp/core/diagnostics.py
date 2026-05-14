"""
Diagnostics — mcp/core/diagnostics.py

Phase 37: Local Diagnostics and Support Report.

Produces a deterministic, redacted, JSON-serialisable diagnostics report
suitable for local support and debugging.  The report intentionally
omits:

    - note bodies
    - prompt contents
    - context bundle contents
    - pending-change proposed content
    - feedback comment text
    - authentication tokens
    - API keys / passwords / bearer tokens
    - raw values of secret environment variables
    - full ``.env`` contents
    - private key material
    - filesystem listings outside the repository / vault roots

Reports are produced locally and are never uploaded anywhere.  The CVE
auth token (``CVE_AUTH_TOKEN``) value is never present in the output.
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Any

from mcp.core.private_cloud import private_cloud_status


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

APP_NAME = "Context Vault Engine"

# App version mirrors the FastAPI ``version=`` attribute in
# ``mcp/server/mcp_server.py``.  Kept in sync manually; not parsed from
# the server module to avoid importing FastAPI when generating the
# report from the CLI.
APP_VERSION = "0.3.0"

# Stable marker used in place of every redacted value.
REDACTED_MARKER = "<redacted>"

# Case-insensitive substring/key tokens whose values must be redacted.
SENSITIVE_KEY_TOKENS: tuple[str, ...] = (
    "token",
    "secret",
    "password",
    "passwd",
    "pwd",
    "api_key",
    "apikey",
    "auth",
    "credential",
    "bearer",
    "private",
    "client_secret",
    "access_token",
    "refresh_token",
    "session",
    "cookie",
    # Bare "key" is matched separately so it does not redact safe keys
    # like "monkeypatch_key" — see :func:`_is_sensitive_key`.
)

# Bare "key" — matched as a *whole* segment so that benign keys such as
# ``schema_hash`` or ``vault_key_count`` are not redacted.  A key is
# considered sensitive on a bare "key" match only when one of its
# whitespace/underscore-separated segments equals "key" exactly.
_BARE_SENSITIVE_SEGMENTS: tuple[str, ...] = ("key",)

# CVE-prefixed environment variables that may be safely *summarised*
# (presence only, never raw value) in the report.
_CVE_ENV_VARS: tuple[str, ...] = (
    "CVE_AUTH_TOKEN",
    "CVE_PRIVATE_CLOUD_ENABLED",
    "CVE_REQUIRE_AUTH",
    "CVE_REMOTE_READ_ONLY",
    "CVE_PUBLIC_BASE_URL",
    "CVE_DEPLOYMENT_MODE",
)


# ──────────────────────────────────────────────────────────────────────────────
# Redaction helpers
# ──────────────────────────────────────────────────────────────────────────────

def _is_sensitive_key(key: str) -> bool:
    """Return True if ``key`` matches a sensitive key pattern.

    Matching is case-insensitive.  A key is sensitive when:

    - it contains any of :data:`SENSITIVE_KEY_TOKENS` as a substring, OR
    - any whitespace/underscore-separated segment equals one of the
      :data:`_BARE_SENSITIVE_SEGMENTS` (currently just ``"key"``).
    """
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    for token in SENSITIVE_KEY_TOKENS:
        if token in lowered:
            return True
    segments = lowered.replace("-", "_").split("_")
    for seg in segments:
        if seg in _BARE_SENSITIVE_SEGMENTS:
            return True
    return False


def redact_value(key: str, value: Any) -> Any:
    """Return ``value`` unchanged unless ``key`` is sensitive.

    Sensitive *string* values become the stable marker
    :data:`REDACTED_MARKER`.  Booleans, integers, and ``None`` are
    treated as safe summaries (e.g. ``token_configured: true``) and
    are returned unchanged so reports retain useful structure.  The
    redaction is deterministic and never partially reveals the
    underlying value.
    """
    if not _is_sensitive_key(key):
        return value
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, str):
        if value == "":
            return value
        return REDACTED_MARKER
    if isinstance(value, (list, tuple)):
        # Replace any string entries in the list to avoid leaking a
        # secret stored as e.g. ["abc123"]. Non-string entries are
        # preserved structurally.
        return [REDACTED_MARKER if isinstance(item, str) and item else item for item in value]
    return REDACTED_MARKER


def redact_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``mapping`` with sensitive values redacted.

    Only top-level keys are inspected; nested dicts are redacted
    recursively.  Lists are walked but their items are not key-redacted
    (no key context is available).
    """
    redacted: dict[str, Any] = {}
    for key, value in mapping.items():
        if isinstance(value, dict):
            redacted[key] = redact_mapping(value)
        else:
            redacted[key] = redact_value(key, value)
    return redacted


# ──────────────────────────────────────────────────────────────────────────────
# Collectors
# ──────────────────────────────────────────────────────────────────────────────

def _repo_root() -> Path:
    """Return the resolved repository root directory."""
    return Path(__file__).resolve().parent.parent.parent


def collect_environment_summary() -> dict[str, Any]:
    """Return a redacted summary of CVE-related environment variables.

    Only an allowlisted subset is reported and only as booleans or
    safe display values.  Raw secret values are never included.
    """
    summary: dict[str, Any] = {}
    for name in _CVE_ENV_VARS:
        raw = os.environ.get(name, "")
        if name == "CVE_AUTH_TOKEN":
            summary[name] = {"set": bool(raw and raw.strip())}
        elif name == "CVE_PUBLIC_BASE_URL":
            summary[name] = {"set": bool(raw and raw.strip())}
        else:
            summary[name] = {"set": bool(raw and raw.strip()), "value": raw.strip() or None}
    return summary


def collect_repository_summary() -> dict[str, Any]:
    """Return repository-root status and a clearly-labelled local path."""
    repo = _repo_root()
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "repository_root": {
            "present": repo.is_dir(),
            "local_path": str(repo),
        },
    }


def collect_runtime_summary() -> dict[str, Any]:
    """Return Python version, OS, platform, and labelled cwd."""
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "os": platform.system(),
        "cwd": {"local_path": os.getcwd()},
        "executable": {"local_path": sys.executable},
    }


def collect_ui_build_summary() -> dict[str, Any]:
    """Return UI build status without reading any built file contents."""
    repo = _repo_root()
    ui_dir = repo / "ui"
    dist = ui_dir / "dist"
    pkg = ui_dir / "package.json"
    index = dist / "index.html"
    return {
        "ui_dir_present": ui_dir.is_dir(),
        "package_json_present": pkg.is_file(),
        "dist_present": dist.is_dir(),
        "index_present": index.is_file(),
        "build_hint": "Run 'cd ui && npm run build' to produce ui/dist/.",
    }


def _safe_note_count(vault_name: str) -> int | None:
    """Return note count for a vault, or ``None`` on any failure.

    Uses the existing index builder; never reads note body content.
    """
    try:
        from mcp.core.note_index import build_index

        idx = build_index(vault_name)
        return len(idx)
    except Exception:
        return None


def collect_vault_summary() -> dict[str, Any]:
    """Return per-vault status (counts/paths/schema), never note bodies."""
    repo = _repo_root()
    config_path = repo / "config" / "config.yaml"

    summary: dict[str, Any] = {
        "config_present": config_path.is_file(),
        "vault_count": 0,
        "vaults": [],
    }

    try:
        from mcp.core.vault_registry import list_vaults, get_vault_path
    except Exception:
        return summary

    try:
        names = list_vaults()
    except Exception:
        return summary

    summary["vault_count"] = len(names)
    for name in names:
        try:
            path = get_vault_path(name)
        except Exception:
            summary["vaults"].append({
                "name": name,
                "path_present": False,
                "schema_present": False,
                "note_count": None,
                "state_dir_present": False,
            })
            continue
        schema = path / "Vault Files" / "Scripts" / "vault_schema.py"
        state = path / "Vault Files" / "State"
        summary["vaults"].append({
            "name": name,
            "path_present": path.is_dir(),
            "schema_present": schema.is_file(),
            "note_count": _safe_note_count(name),
            "state_dir_present": state.is_dir(),
        })
    return summary


def collect_command_summary() -> dict[str, Any]:
    """Return availability flags for the headline CLI/API capabilities."""
    repo = _repo_root()
    run_py = repo / "run.py"
    run_py_text = ""
    if run_py.is_file():
        try:
            run_py_text = run_py.read_text(encoding="utf-8")
        except Exception:
            run_py_text = ""

    def cmd_token_present(token: str) -> bool:
        return f'command == "{token}"' in run_py_text

    return {
        "validate": {"available": cmd_token_present("validate") or "validate" in run_py_text},
        "security": {"available": cmd_token_present("security")},
        "feedback": {"available": cmd_token_present("feedback")},
        "export": {"available": cmd_token_present("export")},
        "mcp": {"available": cmd_token_present("mcp")},
        "app": {"available": cmd_token_present("app")},
        "diagnostics": {"available": cmd_token_present("diagnostics")},
    }


def collect_private_cloud_summary() -> dict[str, Any]:
    """Return the private cloud status dict with sensitive keys redacted.

    The :func:`mcp.core.private_cloud.private_cloud_status` helper
    already omits the raw token, but the report is run through the
    redaction pass as defence-in-depth.
    """
    status = private_cloud_status()
    return redact_mapping(status)


def collect_recent_error_summary() -> list[dict[str, Any]]:
    """Return a list of recently captured structured errors.

    Phase 37 does not introduce a persistent error store.  Only
    in-process errors that may already be tracked elsewhere are
    surfaced.  In the default configuration this is always an empty
    list; the field is reserved for future use.
    """
    return []


def _redaction_rules() -> dict[str, Any]:
    """Return the documented redaction rules used to build this report."""
    return {
        "note_bodies_included": False,
        "secret_values_included": False,
        "content_included": False,
        "sensitive_key_tokens": list(SENSITIVE_KEY_TOKENS),
        "bare_sensitive_segments": list(_BARE_SENSITIVE_SEGMENTS),
        "redaction_marker": REDACTED_MARKER,
        "rules": [
            "Values for keys containing token/secret/password/key/auth/"
            "credential/bearer/cookie/session/private/client_secret/"
            "access_token/refresh_token (case-insensitive) are replaced "
            "with the stable marker '<redacted>'.",
            "Only an allowlisted subset of CVE_-prefixed environment "
            "variables is reported, and CVE_AUTH_TOKEN is reported as a "
            "boolean ('set') only.",
            "Note bodies, prompt contents, context bundle contents, and "
            "pending-change proposed content are never included.",
            "Absolute local paths are labelled with the key 'local_path' "
            "so consumers can identify them before sharing the report.",
            "The diagnostics report is generated locally and is not "
            "uploaded anywhere.",
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def build_diagnostics_report(
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the full, redacted diagnostics report.

    Args:
        generated_at: Optional deterministic timestamp string.  Tests
            should pass a fixed value to keep output reproducible.
            When ``None`` the field is the literal string ``"local"``
            so the report stays deterministic by default.

    Returns:
        A JSON-serialisable diagnostics report.  Never contains note
        bodies or secret environment values.
    """
    warnings: list[str] = []

    app = collect_repository_summary()
    runtime = collect_runtime_summary()
    ui = collect_ui_build_summary()
    config = collect_vault_summary()
    commands = collect_command_summary()
    private_cloud = collect_private_cloud_summary()
    environment = collect_environment_summary()
    recent_errors = collect_recent_error_summary()

    if not ui["dist_present"]:
        warnings.append(
            "UI build artefacts not found at ui/dist; run 'cd ui && npm run build'."
        )
    if config["vault_count"] == 0:
        warnings.append("No vaults are configured in config/config.yaml.")
    if private_cloud.get("enabled") and not private_cloud.get("token_configured"):
        warnings.append(
            "Private cloud mode is enabled but no auth token is configured; "
            "all API requests will be rejected with 401."
        )

    checks = {
        "validation_available": bool(commands["validate"]["available"]),
        "security_available": bool(commands["security"]["available"]),
        "feedback_available": bool(commands["feedback"]["available"]),
        "export_available": bool(commands["export"]["available"]),
    }

    report: dict[str, Any] = {
        "generated_at": generated_at if generated_at is not None else "local",
        "app": app,
        "runtime": runtime,
        "ui": ui,
        "config": config,
        "commands": commands,
        "private_cloud": private_cloud,
        "environment": environment,
        "checks": checks,
        "recent_errors": recent_errors,
        "redaction": _redaction_rules(),
        "warnings": warnings,
    }

    return report
