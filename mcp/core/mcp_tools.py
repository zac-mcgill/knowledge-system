"""MCP Tool definitions and dispatch for Context Vault Engine.

Read-only tools are prefixed first; controlled write tools (Phase 22 session
and project state) are clearly marked in their descriptions.

No destructive, vault-content-write, or arbitrary file-write tools are exposed.
Session and project state tools write only to <vault>/Vault Files/State/.
Path traversal is blocked in the service module.

Tool naming convention: cve_<action>
Tool ordering: alphabetical by name (deterministic listing).

Excluded tools (not exposed):
  - vault delete
  - vault bootstrap
  - note edit
  - feedback create/update/delete
  - export package write
  - schema mutation
  - template mutation
  - direct file write outside state directory
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger("mcp.tools")

# ---------------------------------------------------------------------------
# Tool catalogue — alphabetical order for deterministic listing
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "cve_accept_pending_change",
        "description": (
            "[WRITE — REQUIRES EXPLICIT REVIEW] Accept and apply a pending change "
            "proposal to a vault note. "
            "SAFETY: This is the ONLY way a pending change can mutate vault content. "
            "Revalidates the change before writing. "
            "Checks for stale content (hash mismatch) for update proposals. "
            "Writes only via the existing safe note edit path. "
            "Never auto-accepts. "
            "Requires an explicit call by a reviewer."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "change_id": {"type": "string"},
                "reviewer": {"type": "string"},
                "audit_note": {"type": "string"},
            },
            "required": ["vault", "change_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_attach_note_to_session",
        "description": (
            "[WRITE] Attach a vault note to the current session's recent_notes list. "
            "Validates that the note exists and is inside the vault. "
            "Stores a vault-relative POSIX path only. "
            "Path traversal is blocked. "
            "Writes only to <vault>/Vault Files/State/."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "session_id": {"type": "string"},
                "note_path": {"type": "string"},
            },
            "required": ["vault", "session_id", "note_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_build_context_bundle",
        "description": (
            "Build a deterministic context bundle in memory. "
            "Does not write export packages. "
            "Accepts an optional profile (device profile name) or mode (bundle mode name) "
            "to apply deterministic budget defaults for the target client. "
            "Explicit parameters override profile/mode defaults. "
            "Profile takes precedence over mode if both are supplied."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "filters": {"type": "object"},
                "include_body": {"type": "boolean"},
                "include_feedback": {"type": "boolean"},
                "include_graph": {"type": "boolean"},
                "max_notes": {"type": "integer", "minimum": 1, "maximum": 200},
                "max_chars": {"type": "integer", "minimum": 1000, "maximum": 1000000},
                "allow_partial": {"type": "boolean"},
                "profile": {
                    "type": "string",
                    "description": (
                        "Named device profile (e.g. 'phone-local-llm', 'desktop-agent'). "
                        "Takes precedence over mode."
                    ),
                },
                "mode": {
                    "type": "string",
                    "enum": ["tiny", "small", "medium", "large", "agent"],
                    "description": "Named bundle mode. Ignored when profile is also given.",
                },
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    # Phase 25 — Evidence tool (alphabetical: build_evidence after build_context_bundle)
    {
        "name": "cve_build_evidence",
        "description": (
            "Build a structured evidence response with trust metadata and source refs. "
            "Returns source note paths, sections, confidence metadata, and trust/staleness "
            "status so that local LLMs can cite sources and prefer higher-trust notes. "
            "Notes are sorted by trust score (verified first) when prefer_verified=True. "
            "Deprecated notes are excluded by default. "
            "IMPORTANT: confidence is based on user/system-provided metadata only. "
            "It does NOT indicate factual correctness."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "filters": {"type": "object"},
                "q": {"type": "string"},
                "include_sections": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "max_notes": {"type": "integer", "minimum": 1, "maximum": 100},
                "prefer_verified": {"type": "boolean"},
                "include_deprecated": {"type": "boolean"},
                "include_stale": {"type": "boolean"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_close_session",
        "description": (
            "[WRITE] Mark a session as closed (status=closed). "
            "Does not delete the session file. "
            "Writes only to <vault>/Vault Files/State/."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["vault", "session_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_create_note_draft",
        "description": (
            "[PROPOSAL - writes only to pending queue] "
            "Propose creation of a new vault note. "
            "Stores the proposal as a pending change object for human review. "
            "Nothing is written to vault note files until an explicit "
            "cve_accept_pending_change call is made by a reviewer. "
            "The proposal is validated against the active vault schema before "
            "storage. Invalid proposals are stored but cannot be accepted until "
            "corrected. "
            "SCHEMA GUIDANCE: use only frontmatter fields and values supported "
            "by the active vault schema. Do not invent fields. Common mistakes "
            "that cause validation_status='fail': (1) adding an unknown 'title' "
            "frontmatter field when the schema does not declare it; (2) setting "
            "'status: draft' when the schema's VALID_STATUSES does not include "
            "'draft'; (3) using non-canonical section headings such as "
            "'## Pitfalls' when the schema defines a different canonical heading; "
            "(4) omitting canonical headings required by the note type. Match "
            "the headings and required fields used by existing notes of the same "
            "type in the target vault before proposing a draft."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "path": {"type": "string"},
                "fields": {"type": "object"},
                "body": {"type": "string"},
                "reason": {"type": "string"},
                "source": {"type": "string"},
                "session_id": {"type": "string"},
                "project": {"type": "string"},
            },
            "required": ["vault", "path", "fields", "body"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_get_context_plan",
        "description": "Get deterministic next-action plan for a vault.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "intent": {
                    "type": "string",
                    "enum": ["review", "export", "agent-context", "quality", "security"],
                },
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_get_context_state",
        "description": "Get deterministic vault state and readiness.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_get_missing_concepts",
        "description": "Get missing expected concepts for a vault.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_get_note",
        "description": "Retrieve one note by vault-relative path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["vault", "path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_get_project_state",
        "description": (
            "Get the project state for a vault (current_phase, completed_work, "
            "next_actions, blockers, decisions, risks). "
            "Returns default state if none exists."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    # Phase 25 — Stale notes tool (alphabetical: get_stale_notes after get_project_state)
    {
        "name": "cve_get_stale_notes",
        "description": (
            "Return stale/review information for a vault. "
            "Lists notes where review_after is before today (stale), "
            "notes with no review_after (freshness_unknown), "
            "notes with no last_reviewed (review_unknown), "
            "and deprecated notes. "
            "Staleness is computed deterministically from note frontmatter "
            "using today's UTC date."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_get_tasks",
        "description": "Get deterministic improvement tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "min_priority": {"type": "number"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    # Phase 25 — Trust summary tool (alphabetical: get_trust_summary after get_tasks)
    {
        "name": "cve_get_trust_summary",
        "description": (
            "Return vault-level trust/source/staleness summary. "
            "Counts notes by trust_level, source_type, and confidence level. "
            "Reports missing metadata count, deprecated count, stale count. "
            "Trust metadata is user/system-provided: it signals confidence but "
            "does NOT verify factual correctness."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_list_context_profiles",
        "description": (
            "List all available context profiles and bundle modes. "
            "Profiles are named device configurations (e.g. phone-local-llm, desktop-agent). "
            "Modes are named budget presets (tiny, small, medium, large, agent). "
            "Use these names with cve_build_context_bundle profile/mode parameters."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_list_pending_changes",
        "description": (
            "List pending change proposals for a vault. "
            "Active records live under '<vault>/Vault Files/State/pending-changes/' "
            "and archived records live under "
            "'<vault>/Vault Files/State/pending-changes/archive/'. "
            "Phase 44B: when status is 'accepted', 'rejected', or 'all' the "
            "archive directory is also walked, so archived records are "
            "discoverable through this call. status='pending' (default) and "
            "status='invalid' return active records only. Each returned record "
            "carries a transient 'archived' boolean indicating which directory "
            "it lives in. Archived records are immutable: they cannot be "
            "accepted, rejected, or revalidated again. To inspect a single "
            "record (active or archived) by ID, use cve_review_pending_change. "
            "Use this tool to review the queue before calling accept, reject, "
            "or revalidate."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "accepted", "rejected", "invalid", "all"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 500},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_list_vaults",
        "description": "List registered vaults.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_query_notes",
        "description": "Run deterministic lexical/filter query over notes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "q": {"type": "string"},
                "q_fields": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["body", "path", "frontmatter"],
                    },
                },
                "filters": {"type": "object"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_reject_pending_change",
        "description": (
            "[WRITE — archives the change record] "
            "Reject a pending change proposal. "
            "The change is archived for audit. Rejected changes are never deleted. "
            "Does NOT write to vault note files. "
            "Only pending or invalid changes can be rejected."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "change_id": {"type": "string"},
                "reviewer": {"type": "string"},
                "audit_note": {"type": "string"},
            },
            "required": ["vault", "change_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_resume_session",
        "description": (
            "Return the most recent active session or a session by explicit ID. "
            "Use this to answer 'where was I up to?' for a vault."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_revalidate_pending_change",
        "description": (
            "[SAFE - does NOT write to the vault and does NOT accept the proposal] "
            "Re-run schema validation for a single pending change against the "
            "current active vault schema. Refreshes the persisted "
            "validation_status and validation_errors on the pending record and "
            "appends an audit entry to revalidation_history so the previous "
            "validation state is retained. "
            "Revalidation never writes to the target vault note and never "
            "accepts the proposal; acceptance still goes through "
            "cve_accept_pending_change, which re-runs validation and the stale "
            "hash check before any vault write. Archived (accepted, rejected) "
            "records cannot be revalidated and return "
            "ARCHIVED_NOT_REVALIDATABLE. Use this when a proposal was created "
            "before the schema or vault state changed and you want to re-check "
            "whether it would now pass validation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "change_id": {"type": "string"},
            },
            "required": ["vault", "change_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_review_pending_change",
        "description": (
            "Retrieve the full details of a single pending change proposal "
            "including diff, validation status, validation errors, and all "
            "metadata. Works for both active (pending or invalid) records and "
            "archived (accepted or rejected) records. "
            "The returned validation_status and validation_errors reflect the "
            "state persisted when the proposal was created or last revalidated; "
            "this call does not re-run validation against the current vault "
            "schema. To re-run validation on an active record, use "
            "cve_revalidate_pending_change. Acceptance still re-validates "
            "before any vault write. The returned record carries a transient "
            "'archived' boolean. Archived records are immutable and cannot be "
            "accepted, rejected, or revalidated again. "
            "Use this before deciding to accept, reject, or revalidate."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "change_id": {"type": "string"},
            },
            "required": ["vault", "change_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_security_scan",
        "description": (
            "Run deterministic security scan over vault notes. "
            "Accepts an optional profile or mode to apply budget constraints "
            "for scoped/bounded scanning."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "profile": {
                    "type": "string",
                    "description": "Named device profile to scope the scan. Takes precedence over mode.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["tiny", "small", "medium", "large", "agent"],
                    "description": "Named bundle mode to scope the scan. Ignored when profile is given.",
                },
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_start_session",
        "description": (
            "[WRITE] Create a new active session for a vault. "
            "Records active_vault, current_project, current_topic, and user_goal. "
            "Writes only to <vault>/Vault Files/State/."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "current_project": {"type": "string"},
                "current_topic": {"type": "string"},
                "user_goal": {"type": "string"},
                "active_vault": {"type": "string"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_suggest_note_update",
        "description": (
            "[PROPOSAL - writes only to pending queue] "
            "Propose an update to an existing vault note. "
            "Stores the proposal as a pending change object for human review. "
            "Nothing is written to vault note files until accepted. "
            "Provided fields are merged with original; body replaces the original "
            "body if provided. The proposal is validated against the active vault "
            "schema before storage. "
            "SCHEMA GUIDANCE: only supply frontmatter fields and values supported "
            "by the active vault schema. Do not introduce unknown fields (for "
            "example 'title' when the schema does not declare it) and do not "
            "introduce values outside the schema's VALID_STATUSES (for example "
            "'status: draft' when only 'complete' and 'partial' are allowed). "
            "Preserve canonical headings used by the existing note."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "path": {"type": "string"},
                "fields": {"type": "object"},
                "body": {"type": "string"},
                "reason": {"type": "string"},
                "source": {"type": "string"},
                "session_id": {"type": "string"},
                "project": {"type": "string"},
            },
            "required": ["vault", "path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_summarise_session",
        "description": (
            "Return a compact deterministic session summary suitable for LLM context. "
            "Answers 'where was I up to?' with session ID, vault, project, topic, goal, "
            "recent notes, and status."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_update_note_section_draft",
        "description": (
            "[PROPOSAL - writes only to pending queue] "
            "Propose a targeted update to one section of an existing vault note. "
            "Only the named section is replaced; all other content is preserved. "
            "Stores the proposal as a pending change for human review. "
            "Nothing is written to vault note files until accepted. "
            "proposed_content is the new section body without the '## Header' "
            "line. "
            "SCHEMA GUIDANCE: 'section' must be an existing canonical heading in "
            "the target note. Do not invent new section names. Do not change "
            "frontmatter fields or status values via this tool."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "path": {"type": "string"},
                "section": {"type": "string"},
                "proposed_content": {"type": "string"},
                "reason": {"type": "string"},
                "source": {"type": "string"},
                "session_id": {"type": "string"},
                "project": {"type": "string"},
            },
            "required": ["vault", "path", "section", "proposed_content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_update_project_state",
        "description": (
            "[WRITE] Update project state fields for a vault. "
            "Allowed fields only: current_phase, completed_work, next_actions, "
            "blockers, decisions, risks. "
            "Unknown fields are rejected. "
            "Writes only to <vault>/Vault Files/State/."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
                "updates": {
                    "type": "object",
                    "description": "Allowed keys: current_phase, completed_work, next_actions, blockers, decisions, risks.",
                    "additionalProperties": True,
                },
            },
            "required": ["vault", "updates"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cve_validate_vault",
        "description": "Run validation summary for a vault.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault": {"type": "string"},
            },
            "required": ["vault"],
            "additionalProperties": False,
        },
    },
]

_TOOL_NAMES: frozenset[str] = frozenset(t["name"] for t in TOOLS)
_TOOL_VALID_ARGS: dict[str, set[str]] = {
    t["name"]: set(t["inputSchema"].get("properties", {}).keys())
    for t in TOOLS
}
_TOOL_REQUIRED_ARGS: dict[str, set[str]] = {
    t["name"]: set(t["inputSchema"].get("required", []))
    for t in TOOLS
}

# ---------------------------------------------------------------------------
# Hidden compatibility aliases
# ---------------------------------------------------------------------------
# VS Code Copilot rejects tool names containing characters outside
# ``[a-z0-9_-]``. Advertised tool names use ``cve_<action>`` underscored form.
# Older dotted ``cve.<action>`` names remain accepted at dispatch time as
# deprecated, hidden aliases. Aliases are intentionally NOT included in
# ``tools/list`` output.
_TOOL_ALIASES: dict[str, str] = {
    f"cve.{name[len('cve_'):]}": name
    for name in _TOOL_NAMES
}


def _canonical_tool_name(tool_name: str) -> str:
    """Normalise an incoming tool name through the hidden alias map."""
    return _TOOL_ALIASES.get(tool_name, tool_name)


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _tool_error(text: str) -> dict:
    return {
        "content": [{"type": "text", "text": text}],
        "isError": True,
    }


def _tool_ok(data: dict, summary: str | None = None) -> dict:
    text = summary if summary else json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": data,
        "isError": False,
    }


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

def _validate_args(tool_name: str, args: dict) -> str | None:
    """Validate arguments for a tool.

    Returns an error message string if invalid, None if valid.
    """
    required = _TOOL_REQUIRED_ARGS.get(tool_name, set())
    valid = _TOOL_VALID_ARGS.get(tool_name, set())

    for key in required:
        if key not in args:
            return f"Missing required argument: {key!r}"

    for key in args:
        if valid and key not in valid:
            return f"Unknown argument: {key!r}"

    return None


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def dispatch_tool_call(tool_name: str, args: dict) -> dict:
    """Dispatch a tool call and return the tool result.

    Never raises — errors are returned as isError=True tool results.
    """
    tool_name = _canonical_tool_name(tool_name)
    if tool_name not in _TOOL_NAMES:
        return _tool_error(f"Unknown tool: {tool_name!r}")

    validation_error = _validate_args(tool_name, args)
    if validation_error:
        return _tool_error(f"INVALID_PARAMS: {validation_error}")

    try:
        return _execute_tool(tool_name, args)
    except Exception as exc:
        logger.exception("tool execution error: %s", tool_name)
        return _tool_error(f"INTERNAL_ERROR: {exc}")


def _execute_tool(tool_name: str, args: dict) -> dict:
    """Execute a named tool with pre-validated args."""
    dispatch = {
        "cve_accept_pending_change": _tool_accept_pending_change,
        "cve_attach_note_to_session": _tool_attach_note_to_session,
        "cve_build_context_bundle": _tool_build_context_bundle,
        "cve_build_evidence": _tool_build_evidence,
        "cve_close_session": _tool_close_session,
        "cve_create_note_draft": _tool_create_note_draft,
        "cve_get_context_plan": _tool_get_context_plan,
        "cve_get_context_state": _tool_get_context_state,
        "cve_get_missing_concepts": _tool_get_missing_concepts,
        "cve_get_note": _tool_get_note,
        "cve_get_project_state": _tool_get_project_state,
        "cve_get_stale_notes": _tool_get_stale_notes,
        "cve_get_tasks": _tool_get_tasks,
        "cve_get_trust_summary": _tool_get_trust_summary,
        "cve_list_context_profiles": _tool_list_context_profiles,
        "cve_list_pending_changes": _tool_list_pending_changes,
        "cve_list_vaults": _tool_list_vaults,
        "cve_query_notes": _tool_query_notes,
        "cve_reject_pending_change": _tool_reject_pending_change,
        "cve_resume_session": _tool_resume_session,
        "cve_revalidate_pending_change": _tool_revalidate_pending_change,
        "cve_review_pending_change": _tool_review_pending_change,
        "cve_security_scan": _tool_security_scan,
        "cve_start_session": _tool_start_session,
        "cve_suggest_note_update": _tool_suggest_note_update,
        "cve_summarise_session": _tool_summarise_session,
        "cve_update_note_section_draft": _tool_update_note_section_draft,
        "cve_update_project_state": _tool_update_project_state,
        "cve_validate_vault": _tool_validate_vault,
    }
    fn = dispatch.get(tool_name)
    if fn is None:
        return _tool_error(f"Unknown tool: {tool_name!r}")
    return fn(args)


# ---------------------------------------------------------------------------
# Individual tool implementations
# ---------------------------------------------------------------------------

def _tool_list_vaults(args: dict) -> dict:
    from mcp.core.vault_registry import list_vaults  # noqa: PLC0415
    vaults = list_vaults()
    data = {"vaults": vaults, "count": len(vaults)}
    return _tool_ok(data, f"Found {len(vaults)} vault(s): {', '.join(vaults)}")


def _tool_get_context_state(args: dict) -> dict:
    from mcp.core.context_controller import get_context_state  # noqa: PLC0415
    vault = args["vault"]
    result = get_context_state(vault)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


def _tool_get_context_plan(args: dict) -> dict:
    from mcp.core.context_controller import build_context_plan  # noqa: PLC0415
    vault = args["vault"]
    intent = args.get("intent", "review")
    result = build_context_plan(vault, intent=intent)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


def _tool_query_notes(args: dict) -> dict:
    from mcp.core.query_engine import query  # noqa: PLC0415
    vault = args["vault"]
    q = args.get("q")
    q_fields = args.get("q_fields")
    filters = args.get("filters") or {}
    limit = args.get("limit", 20)

    kwargs: dict = {}
    if q is not None:
        kwargs["q"] = q
    if q_fields is not None:
        kwargs["q_fields"] = q_fields

    result = query(vault, filters, limit=limit, **kwargs)
    if result.get("status") == "error":
        return _tool_error(f"QUERY_ERROR: {result.get('error', 'unknown')}")
    return _tool_ok(result)


def _tool_get_note(args: dict) -> dict:
    from mcp.core.query_engine import get_note  # noqa: PLC0415
    vault = args["vault"]
    path = args["path"]
    result = get_note(vault, path)
    if result.get("status") == "error":
        error = result.get("error", {})
        if isinstance(error, dict):
            code = error.get("code", "ERROR")
            msg = error.get("message", str(error))
        else:
            code = str(error)
            msg = str(error)
        return _tool_error(f"{code}: {msg}")
    return _tool_ok(result)


def _tool_validate_vault(args: dict) -> dict:
    from mcp.core.adapters.validation_adapter import get_validation  # noqa: PLC0415
    vault = args["vault"]
    result = get_validation(vault_name=vault)
    if "error" in result:
        return _tool_error(f"VALIDATION_ERROR: {result['error']}")
    return _tool_ok(result)


def _tool_get_tasks(args: dict) -> dict:
    from mcp.core.adapters.tasks_adapter import get_tasks  # noqa: PLC0415
    vault = args["vault"]
    min_priority = args.get("min_priority")
    result = get_tasks(vault_name=vault, limit=50)
    if "error" in result:
        return _tool_error(f"TASKS_ERROR: {result['error']}")
    if min_priority is not None:
        filtered = [t for t in result["tasks"] if t.get("priority", 0) >= min_priority]
        result = dict(result)
        result["tasks"] = filtered
        result["total"] = len(filtered)
    return _tool_ok(result)


def _tool_get_missing_concepts(args: dict) -> dict:
    from mcp.core.adapters.missing_adapter import get_missing  # noqa: PLC0415
    vault = args["vault"]
    result = get_missing(vault_name=vault)
    if "error" in result:
        return _tool_error(f"MISSING_ERROR: {result['error']}")
    return _tool_ok(result)


def _tool_list_context_profiles(args: dict) -> dict:
    from mcp.core import context_profiles as _cp  # noqa: PLC0415
    data = _cp.list_context_profiles()
    mode_count = len(data["modes"])
    profile_count = len(data["profiles"])
    summary = (
        f"Profiles: {sorted(data['profiles'])} | "
        f"Modes: {sorted(data['modes'])}"
    )
    return _tool_ok(data, summary)


def _tool_security_scan(args: dict) -> dict:
    from mcp.core.note_index import build_index  # noqa: PLC0415
    from core.shared.context_security import scan_vault_context  # noqa: PLC0415
    from mcp.core import context_profiles as _cp  # noqa: PLC0415
    vault = args["vault"]

    # Resolve profile/mode defaults for scoped scanning
    explicit: dict = {}
    profile_result = _cp.apply_context_profile_to_request(
        explicit,
        profile_name=args.get("profile"),
        mode=args.get("mode"),
    )
    if profile_result["error"]:
        err = profile_result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")

    merged = profile_result["request"]
    profile_meta = profile_result["profile_metadata"]

    # Full-vault scan defaults: include all content notes, allow partial
    build_index(vault)
    result = scan_vault_context(
        vault_name=vault,
        filters={},
        include_sections=merged.get(
            "include_sections", ["Key Principles", "How It Works", "Trade-offs"]
        ),
        include_body=merged.get("include_body", True),
        max_notes=merged.get("max_notes", 1000),
        max_chars=merged.get("max_chars", 10_000_000),
        allow_partial=merged.get("allow_partial", True),
    )
    if result.get("status") == "error":
        return _tool_error(f"SECURITY_SCAN_ERROR: {result.get('error', 'unknown')}")

    result["profile_metadata"] = profile_meta
    return _tool_ok(result)


def _tool_build_context_bundle(args: dict) -> dict:
    from core.shared.context_bundle import generate_bundle  # noqa: PLC0415
    from mcp.core import context_profiles as _cp  # noqa: PLC0415
    vault = args["vault"]
    filters = args.get("filters") or {}
    include_graph = args.get("include_graph", False)
    allow_partial = args.get("allow_partial", True)

    # Resolve profile/mode defaults; explicit args override them
    explicit: dict = {}
    if "include_body" in args:
        explicit["include_body"] = args["include_body"]
    if "max_notes" in args:
        explicit["max_notes"] = args["max_notes"]
    if "max_chars" in args:
        explicit["max_chars"] = args["max_chars"]
    if "include_related" in args:
        explicit["include_related"] = include_graph

    profile_result = _cp.apply_context_profile_to_request(
        explicit,
        profile_name=args.get("profile"),
        mode=args.get("mode"),
    )
    if profile_result["error"]:
        err = profile_result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")

    merged = profile_result["request"]
    profile_meta = profile_result["profile_metadata"]

    result = generate_bundle(
        vault_name=vault,
        filters=filters,
        include_body=merged.get("include_body", True),
        include_related=merged.get("include_related", include_graph),
        max_notes=merged.get("max_notes", 50),
        max_chars=merged.get("max_chars", 100_000),
        allow_partial=allow_partial,
    )
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")

    result["profile_metadata"] = profile_meta
    if profile_meta.get("require_security_scan"):
        result.setdefault("warnings", [])
        result["warnings"].append(
            "Profile requires security scan. Use cve_security_scan to verify content."
        )
    return _tool_ok(result)


# ---------------------------------------------------------------------------
# Phase 22: Session and Project State tool implementations
# ---------------------------------------------------------------------------

def _check_remote_read_only() -> dict | None:
    """Return a tool error if private cloud read-only mode is active."""
    try:
        from mcp.core.private_cloud import is_remote_read_only  # noqa: PLC0415
        if is_remote_read_only():
            return _tool_error("REMOTE_READ_ONLY: Remote read-only mode blocks this write operation.")
    except Exception:
        pass
    return None


def _tool_start_session(args: dict) -> dict:
    guard = _check_remote_read_only()
    if guard:
        return guard
    from mcp.core import session_state as _ss  # noqa: PLC0415
    vault = args["vault"]
    result = _ss.start_session(
        vault,
        current_project=args.get("current_project"),
        current_topic=args.get("current_topic"),
        user_goal=args.get("user_goal"),
        active_vault=args.get("active_vault"),
    )
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    session = result["session"]
    return _tool_ok({"session": session}, f"Session started: {session.get('session_id')}")


def _tool_resume_session(args: dict) -> dict:
    from mcp.core import session_state as _ss  # noqa: PLC0415
    vault = args["vault"]
    session_id = args.get("session_id")
    result = _ss.resume_session(vault, session_id=session_id)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


def _tool_summarise_session(args: dict) -> dict:
    from mcp.core import session_state as _ss  # noqa: PLC0415
    vault = args["vault"]
    session_id = args.get("session_id")
    result = _ss.summarise_session(vault, session_id=session_id)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


def _tool_attach_note_to_session(args: dict) -> dict:
    guard = _check_remote_read_only()
    if guard:
        return guard
    from mcp.core import session_state as _ss  # noqa: PLC0415
    vault = args["vault"]
    session_id = args["session_id"]
    note_path = args["note_path"]
    result = _ss.attach_note_to_session(vault, session_id, note_path)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


def _tool_close_session(args: dict) -> dict:
    guard = _check_remote_read_only()
    if guard:
        return guard
    from mcp.core import session_state as _ss  # noqa: PLC0415
    vault = args["vault"]
    session_id = args["session_id"]
    result = _ss.close_session(vault, session_id)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result, f"Session closed: {session_id}")


def _tool_get_project_state(args: dict) -> dict:
    from mcp.core import session_state as _ss  # noqa: PLC0415
    vault = args["vault"]
    result = _ss.get_project_state(vault)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


def _tool_update_project_state(args: dict) -> dict:
    guard = _check_remote_read_only()
    if guard:
        return guard
    from mcp.core import session_state as _ss  # noqa: PLC0415
    vault = args["vault"]
    updates = args.get("updates", {})
    if not isinstance(updates, dict):
        return _tool_error("INVALID_PARAMS: 'updates' must be an object")
    result = _ss.update_project_state(vault, updates)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


# ---------------------------------------------------------------------------
# Phase 23: Pending Changes tool implementations
# ---------------------------------------------------------------------------

def _tool_list_pending_changes(args: dict) -> dict:
    from mcp.core import pending_changes as _pc  # noqa: PLC0415
    vault = args["vault"]
    status = args.get("status", "pending")
    limit = args.get("limit", 50)
    status_arg = None if status == "all" else status
    result = _pc.list_pending_changes(vault, status=status_arg, limit=limit)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


def _tool_review_pending_change(args: dict) -> dict:
    from mcp.core import pending_changes as _pc  # noqa: PLC0415
    vault = args["vault"]
    change_id = args["change_id"]
    result = _pc.review_pending_change(vault, change_id)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


def _tool_create_note_draft(args: dict) -> dict:
    guard = _check_remote_read_only()
    if guard:
        return guard
    from mcp.core import pending_changes as _pc  # noqa: PLC0415
    vault = args["vault"]
    path = args["path"]
    fields = args.get("fields", {})
    body = args.get("body", "")
    reason = args.get("reason", "")
    source = args.get("source", "agent")
    session_id = args.get("session_id")
    project = args.get("project")
    result = _pc.create_note_draft(
        vault, path, fields, body,
        reason=reason, source=source,
        session_id=session_id, project=project,
    )
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    change = result["data"]["change"]
    return _tool_ok(
        result,
        f"Draft created: {change['id']} (status={change['status']}, validation={change['validation_status']})",
    )


def _tool_suggest_note_update(args: dict) -> dict:
    guard = _check_remote_read_only()
    if guard:
        return guard
    from mcp.core import pending_changes as _pc  # noqa: PLC0415
    vault = args["vault"]
    path = args["path"]
    fields = args.get("fields")
    body = args.get("body")
    reason = args.get("reason", "")
    source = args.get("source", "agent")
    session_id = args.get("session_id")
    project = args.get("project")
    result = _pc.suggest_note_update(
        vault, path, fields=fields, body=body,
        reason=reason, source=source,
        session_id=session_id, project=project,
    )
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    change = result["data"]["change"]
    return _tool_ok(
        result,
        f"Update proposal created: {change['id']} (status={change['status']}, validation={change['validation_status']})",
    )


def _tool_update_note_section_draft(args: dict) -> dict:
    guard = _check_remote_read_only()
    if guard:
        return guard
    from mcp.core import pending_changes as _pc  # noqa: PLC0415
    vault = args["vault"]
    path = args["path"]
    section = args["section"]
    proposed_content = args["proposed_content"]
    reason = args.get("reason", "")
    source = args.get("source", "agent")
    session_id = args.get("session_id")
    project = args.get("project")
    result = _pc.update_note_section_draft(
        vault, path, section, proposed_content,
        reason=reason, source=source,
        session_id=session_id, project=project,
    )
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    change = result["data"]["change"]
    return _tool_ok(
        result,
        f"Section draft created: {change['id']} (section={section!r}, validation={change['validation_status']})",
    )


def _tool_accept_pending_change(args: dict) -> dict:
    guard = _check_remote_read_only()
    if guard:
        return guard
    from mcp.core import pending_changes as _pc  # noqa: PLC0415
    vault = args["vault"]
    change_id = args["change_id"]
    reviewer = args.get("reviewer")
    audit_note = args.get("audit_note")
    result = _pc.accept_pending_change(
        vault, change_id, reviewer=reviewer, audit_note=audit_note,
    )
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    change = result["data"]["change"]
    return _tool_ok(result, f"Change accepted and applied: {change_id} → {change['path']}")


def _tool_reject_pending_change(args: dict) -> dict:
    guard = _check_remote_read_only()
    if guard:
        return guard
    from mcp.core import pending_changes as _pc  # noqa: PLC0415
    vault = args["vault"]
    change_id = args["change_id"]
    reviewer = args.get("reviewer")
    audit_note = args.get("audit_note")
    result = _pc.reject_pending_change(
        vault, change_id, reviewer=reviewer, audit_note=audit_note,
    )
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result, f"Change rejected and archived: {change_id}")


def _tool_revalidate_pending_change(args: dict) -> dict:
    """Phase 44B: re-run validation for a pending change without writing the vault."""
    guard = _check_remote_read_only()
    if guard:
        return guard
    from mcp.core import pending_changes as _pc  # noqa: PLC0415
    vault = args["vault"]
    change_id = args["change_id"]
    result = _pc.revalidate_pending_change(vault, change_id)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    change = result["data"]["change"]
    return _tool_ok(
        result,
        (
            f"Change revalidated: {change_id} "
            f"(status={change['status']}, validation={change['validation_status']}). "
            "No vault write."
        ),
    )


# ---------------------------------------------------------------------------
# Phase 25: Trust, Staleness, and Evidence tool implementations
# ---------------------------------------------------------------------------

def _tool_get_trust_summary(args: dict) -> dict:
    from mcp.core import trust_metadata as _tm  # noqa: PLC0415
    vault = args["vault"]
    result = _tm.list_trust_summary(vault)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


def _tool_get_stale_notes(args: dict) -> dict:
    from mcp.core import trust_metadata as _tm  # noqa: PLC0415
    vault = args["vault"]
    result = _tm.list_stale_notes(vault)
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    return _tool_ok(result)


def _tool_build_evidence(args: dict) -> dict:
    from mcp.core import trust_metadata as _tm  # noqa: PLC0415
    vault = args["vault"]
    filters = args.get("filters") or {}
    q = args.get("q")
    include_sections = args.get("include_sections")
    max_notes = args.get("max_notes", 20)
    prefer_verified = args.get("prefer_verified", True)
    include_deprecated = args.get("include_deprecated", False)
    include_stale = args.get("include_stale", True)
    result = _tm.build_evidence(
        vault_name=vault,
        filters=filters,
        q=q,
        include_sections=include_sections,
        max_notes=max_notes,
        prefer_verified=prefer_verified,
        include_deprecated=include_deprecated,
        include_stale=include_stale,
    )
    if result.get("status") == "error":
        err = result["error"]
        return _tool_error(f"{err['code']}: {err['message']}")
    summary = result.get("summary", {})
    total = summary.get("total_notes", 0)
    return _tool_ok(result, f"Evidence built: {total} note(s) from {vault!r}")
