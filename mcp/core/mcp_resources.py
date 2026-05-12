"""MCP Resource definitions and reading for Context Vault Engine.

Resources are read-only, deterministic, and addressable by URI.

URI scheme: cve://...

Supported URIs:
  cve://vaults
  cve://vault/{vault}/summary
  cve://vault/{vault}/state
  cve://vault/{vault}/plan/review
  cve://vault/{vault}/notes
  cve://vault/{vault}/tasks
  cve://vault/{vault}/missing
  cve://vault/{vault}/security
  cve://vault/{vault}/graph
  cve://vault/{vault}/trust
  cve://vault/{vault}/stale

Path safety: vault names are validated against the registered vault list.
No raw filesystem paths are accepted from callers.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse

logger = logging.getLogger("mcp.resources")

_MIME_JSON = "application/json"

# ---------------------------------------------------------------------------
# Resource catalogue (static for listing)
# ---------------------------------------------------------------------------

# These are template URIs. The listing returns the static templates;
# individual vaults are filled in at read time.
_STATIC_RESOURCES = [
    {
        "uri": "cve://vaults",
        "name": "Registered Vaults",
        "description": "List all registered vaults.",
        "mimeType": _MIME_JSON,
    },
    {
        "uri": "cve://context/profiles",
        "name": "Context Profiles",
        "description": "List all built-in context profiles and bundle modes.",
        "mimeType": _MIME_JSON,
    },
]

_VAULT_RESOURCE_TEMPLATES = [
    ("cve://vault/{vault}/summary", "Vault Summary", "High-level vault summary."),
    ("cve://vault/{vault}/state", "Vault State", "Full deterministic vault state."),
    ("cve://vault/{vault}/plan/review", "Vault Review Plan", "Review plan for the vault."),
    ("cve://vault/{vault}/notes", "Vault Notes", "List of all notes in the vault."),
    ("cve://vault/{vault}/tasks", "Vault Tasks", "Improvement tasks for the vault."),
    ("cve://vault/{vault}/missing", "Missing Concepts", "Missing expected concepts."),
    ("cve://vault/{vault}/security", "Security Scan", "Security scan results."),
    ("cve://vault/{vault}/graph", "Vault Graph", "Knowledge graph nodes and edges."),
    ("cve://vault/{vault}/session/current", "Current Session", "Latest active session summary."),
    ("cve://vault/{vault}/project-state", "Project State", "Project phase, tasks, blockers, and decisions."),
    ("cve://vault/{vault}/pending-changes", "Pending Changes", "Pending change proposals awaiting review."),
    # Phase 25 — trust/staleness resources
    ("cve://vault/{vault}/trust", "Trust Summary", "Trust/staleness/evidence metadata summary."),
    ("cve://vault/{vault}/stale", "Stale Notes", "Notes with staleness information."),
]

# Static profile resource templates (not per-vault)
_PROFILE_RESOURCE_TEMPLATES = [
    ("cve://context/profile/{profile_name}", "Context Profile", "Individual context profile or mode definition."),
]


def list_resources() -> list[dict]:
    """Return a deterministic list of all available MCP resources.

    Enumerates registered vaults and builds concrete resource entries.
    """
    try:
        from mcp.core.vault_registry import list_vaults  # noqa: PLC0415
        vaults = list_vaults()
    except Exception:
        vaults = []

    resources = list(_STATIC_RESOURCES)

    # Profile resource templates (not per-vault — enumerate known profiles/modes)
    try:
        from mcp.core import context_profiles as _cp  # noqa: PLC0415
        profile_data = _cp.list_context_profiles()
        all_profile_names = (
            list(profile_data["profiles"].keys()) + list(profile_data["modes"].keys())
        )
        for pname in sorted(all_profile_names):
            uri = f"cve://context/profile/{urllib.parse.quote(pname, safe='')}"
            resources.append({
                "uri": uri,
                "name": f"Context Profile — {pname}",
                "description": f"Context profile or mode: {pname}",
                "mimeType": _MIME_JSON,
            })
    except Exception:
        pass

    for vault in sorted(vaults):
        for uri_template, name_template, description in _VAULT_RESOURCE_TEMPLATES:
            uri = uri_template.replace("{vault}", urllib.parse.quote(vault, safe=""))
            name = f"{vault} — {name_template}"
            resources.append({
                "uri": uri,
                "name": name,
                "description": description,
                "mimeType": _MIME_JSON,
            })

    return resources


# ---------------------------------------------------------------------------
# Resource reading
# ---------------------------------------------------------------------------

def _parse_vault_resource_uri(uri: str) -> tuple[str | None, str | None]:
    """Parse a vault resource URI into (vault_name, resource_path).

    e.g. 'cve://vault/demo-vault/state' -> ('demo-vault', 'state')
    Returns (None, None) if the URI does not match the vault pattern.
    """
    # Strip scheme
    if not uri.startswith("cve://vault/"):
        return None, None

    rest = uri[len("cve://vault/"):]
    # rest = "<encoded_vault>/<resource_path>"
    slash_pos = rest.find("/")
    if slash_pos == -1:
        return None, None

    encoded_vault = rest[:slash_pos]
    resource_path = rest[slash_pos + 1:]

    try:
        vault_name = urllib.parse.unquote(encoded_vault)
    except Exception:
        return None, None

    return vault_name, resource_path


def _validate_vault(vault_name: str) -> bool:
    """Check that vault_name is in the registered list (prevents path traversal)."""
    try:
        from mcp.core.vault_registry import list_vaults  # noqa: PLC0415
        return vault_name in list_vaults()
    except Exception:
        return False


def _resource_error(uri: str, message: str) -> dict:
    return {
        "contents": [
            {
                "uri": uri,
                "mimeType": _MIME_JSON,
                "text": json.dumps({"error": message}, ensure_ascii=False),
            }
        ]
    }


def _resource_ok(uri: str, data: dict) -> dict:
    return {
        "contents": [
            {
                "uri": uri,
                "mimeType": _MIME_JSON,
                "text": json.dumps(data, ensure_ascii=False, indent=2),
            }
        ]
    }


def read_resource(uri: str) -> dict:
    """Read a resource by URI.

    Returns MCP resources/read response shape:
        {"contents": [{"uri": ..., "mimeType": ..., "text": ...}]}

    Errors are returned as JSON in the text field, not as protocol errors.
    """
    try:
        if uri == "cve://vaults":
            return _read_vaults(uri)

        if uri == "cve://context/profiles":
            return _read_context_profiles(uri)

        # cve://context/profile/{profile_name}
        if uri.startswith("cve://context/profile/"):
            encoded_name = uri[len("cve://context/profile/"):]
            try:
                profile_name = urllib.parse.unquote(encoded_name)
            except Exception:
                return _resource_error(uri, f"Invalid profile name encoding in URI: {uri!r}")
            return _read_context_profile(uri, profile_name)

        vault_name, resource_path = _parse_vault_resource_uri(uri)
        if vault_name is None:
            return _resource_error(uri, f"Unknown resource URI: {uri!r}")

        # Validate vault against registered list (no path traversal)
        if not _validate_vault(vault_name):
            return _resource_error(uri, f"INVALID_VAULT: Vault not found: {vault_name!r}")

        return _read_vault_resource(uri, vault_name, resource_path or "")

    except Exception as exc:
        logger.exception("error reading resource %s", uri)
        return _resource_error(uri, f"INTERNAL_ERROR: {exc}")


def _read_vaults(uri: str) -> dict:
    from mcp.core.vault_registry import list_vaults  # noqa: PLC0415
    vaults = list_vaults()
    return _resource_ok(uri, {"vaults": vaults, "count": len(vaults)})


def _read_context_profiles(uri: str) -> dict:
    """Read the full context profiles listing."""
    from mcp.core import context_profiles as _cp  # noqa: PLC0415
    data = _cp.list_context_profiles()
    return _resource_ok(uri, data)


def _read_context_profile(uri: str, profile_name: str) -> dict:
    """Read a single context profile or mode by name."""
    from mcp.core import context_profiles as _cp  # noqa: PLC0415
    result = _cp.get_context_profile(profile_name)
    if result.get("status") == "error":
        err = result["error"]
        return _resource_error(uri, f"{err['code']}: {err['message']}")
    return _resource_ok(uri, {"profile": result["profile"], "source": result["source"]})


def _read_vault_resource(uri: str, vault_name: str, resource_path: str) -> dict:
    """Dispatch to the appropriate vault sub-resource reader."""
    if resource_path == "summary":
        return _read_summary(uri, vault_name)
    if resource_path == "state":
        return _read_state(uri, vault_name)
    if resource_path == "plan/review":
        return _read_plan(uri, vault_name, "review")
    if resource_path == "notes":
        return _read_notes(uri, vault_name)
    if resource_path == "tasks":
        return _read_tasks(uri, vault_name)
    if resource_path == "missing":
        return _read_missing(uri, vault_name)
    if resource_path == "security":
        return _read_security(uri, vault_name)
    if resource_path == "graph":
        return _read_graph(uri, vault_name)
    if resource_path == "session/current":
        return _read_session_current(uri, vault_name)
    if resource_path == "project-state":
        return _read_project_state(uri, vault_name)
    if resource_path == "pending-changes":
        return _read_pending_changes(uri, vault_name)
    # Phase 25 — trust/staleness
    if resource_path == "trust":
        return _read_trust(uri, vault_name)
    if resource_path == "stale":
        return _read_stale(uri, vault_name)

    return _resource_error(uri, f"Unknown vault resource path: {resource_path!r}")


def _read_summary(uri: str, vault_name: str) -> dict:
    from mcp.core.context_controller import get_context_state  # noqa: PLC0415
    state = get_context_state(vault_name)
    if state.get("status") == "error":
        return _resource_error(uri, f"{state['error']['code']}: {state['error']['message']}")
    summary = {
        "vault": vault_name,
        "summary": state["state"]["summary"],
        "readiness": state["readiness"],
        "blockers": state["blockers"],
        "warnings": state["warnings"],
    }
    return _resource_ok(uri, summary)


def _read_state(uri: str, vault_name: str) -> dict:
    from mcp.core.context_controller import get_context_state  # noqa: PLC0415
    state = get_context_state(vault_name)
    if state.get("status") == "error":
        return _resource_error(uri, f"{state['error']['code']}: {state['error']['message']}")
    return _resource_ok(uri, state)


def _read_plan(uri: str, vault_name: str, intent: str) -> dict:
    from mcp.core.context_controller import build_context_plan  # noqa: PLC0415
    plan = build_context_plan(vault_name, intent=intent)
    if plan.get("status") == "error":
        return _resource_error(uri, f"{plan['error']['code']}: {plan['error']['message']}")
    return _resource_ok(uri, plan)


def _read_notes(uri: str, vault_name: str) -> dict:
    from mcp.core.adapters.notes_adapter import get_notes  # noqa: PLC0415
    result = get_notes(vault_name=vault_name)
    if "error" in result:
        return _resource_error(uri, f"NOTES_ERROR: {result['error']}")
    return _resource_ok(uri, result)


def _read_tasks(uri: str, vault_name: str) -> dict:
    from mcp.core.adapters.tasks_adapter import get_tasks  # noqa: PLC0415
    result = get_tasks(vault_name=vault_name, limit=50)
    if "error" in result:
        return _resource_error(uri, f"TASKS_ERROR: {result['error']}")
    return _resource_ok(uri, result)


def _read_missing(uri: str, vault_name: str) -> dict:
    from mcp.core.adapters.missing_adapter import get_missing  # noqa: PLC0415
    result = get_missing(vault_name=vault_name)
    if "error" in result:
        return _resource_error(uri, f"MISSING_ERROR: {result['error']}")
    return _resource_ok(uri, result)


def _read_security(uri: str, vault_name: str) -> dict:
    from mcp.core.note_index import build_index  # noqa: PLC0415
    from core.shared.context_security import scan_vault_context  # noqa: PLC0415
    build_index(vault_name)
    result = scan_vault_context(
        vault_name=vault_name,
        filters={},
        include_sections=["Key Principles", "How It Works", "Trade-offs"],
        include_body=True,
        max_notes=1000,
        max_chars=10_000_000,
        allow_partial=True,
    )
    if result.get("status") == "error":
        return _resource_error(uri, f"SECURITY_ERROR: {result.get('error', 'unknown')}")
    return _resource_ok(uri, result)


def _read_graph(uri: str, vault_name: str) -> dict:
    from mcp.core.graph_builder import build_graph  # noqa: PLC0415
    result = build_graph(vault_name=vault_name)
    if "error" in result:
        return _resource_error(uri, f"GRAPH_ERROR: {result['error']}")
    return _resource_ok(uri, result)


def _read_session_current(uri: str, vault_name: str) -> dict:
    """Read the latest active session summary for a vault."""
    from mcp.core import session_state as _ss  # noqa: PLC0415
    result = _ss.summarise_session(vault_name)
    if result.get("status") == "error":
        err = result["error"]
        return _resource_error(uri, f"{err['code']}: {err['message']}")
    return _resource_ok(uri, result)


def _read_project_state(uri: str, vault_name: str) -> dict:
    """Read the project state for a vault."""
    from mcp.core import session_state as _ss  # noqa: PLC0415
    result = _ss.get_project_state(vault_name)
    if result.get("status") == "error":
        err = result["error"]
        return _resource_error(uri, f"{err['code']}: {err['message']}")
    return _resource_ok(uri, result)


def _read_pending_changes(uri: str, vault_name: str) -> dict:
    """Read the pending change queue (status=pending) for a vault."""
    from mcp.core import pending_changes as _pc  # noqa: PLC0415
    result = _pc.list_pending_changes(vault_name, status="pending", limit=100)
    if result.get("status") == "error":
        err = result["error"]
        return _resource_error(uri, f"{err['code']}: {err['message']}")
    return _resource_ok(uri, result)


# Phase 25 — trust/staleness resource readers

def _read_trust(uri: str, vault_name: str) -> dict:
    """Read vault-level trust/source/confidence summary."""
    from mcp.core import trust_metadata as _tm  # noqa: PLC0415
    result = _tm.list_trust_summary(vault_name)
    if result.get("status") == "error":
        err = result["error"]
        return _resource_error(uri, f"{err['code']}: {err['message']}")
    return _resource_ok(uri, result)


def _read_stale(uri: str, vault_name: str) -> dict:
    """Read stale/review metadata for all notes in a vault."""
    from mcp.core import trust_metadata as _tm  # noqa: PLC0415
    result = _tm.list_stale_notes(vault_name)
    if result.get("status") == "error":
        err = result["error"]
        return _resource_error(uri, f"{err['code']}: {err['message']}")
    return _resource_ok(uri, result)
