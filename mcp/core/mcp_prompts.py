"""MCP Prompt definitions for Context Vault Engine.

Prompts are reusable templates that guide agents through vault workflows.
All prompts are read-only and include safety language to prevent
unauthorised mutations.

Safety rule embedded in all prompts:
  "Do not edit notes unless the user explicitly asks and a safe
   note-edit tool is available."

Required prompts:
  cve.vault_review
  cve.security_review
  cve.context_handoff
  cve.quality_plan
"""

from __future__ import annotations

import logging

logger = logging.getLogger("mcp.prompts")

# ---------------------------------------------------------------------------
# Prompt catalogue — alphabetical by name for deterministic listing
# ---------------------------------------------------------------------------

PROMPTS = [
    {
        "name": "cve.context_handoff",
        "description": (
            "Guide an agent through reading the controller plan and building "
            "a context bundle."
        ),
        "arguments": [
            {
                "name": "vault",
                "description": "The vault name to use.",
                "required": True,
            },
            {
                "name": "intent",
                "description": "The controller intent (default: agent-context).",
                "required": False,
            },
        ],
    },
    {
        "name": "cve.quality_plan",
        "description": (
            "Guide an agent through tasks, missing concepts, and quality signals."
        ),
        "arguments": [
            {
                "name": "vault",
                "description": "The vault name to use.",
                "required": True,
            },
        ],
    },
    {
        "name": "cve.resume_work",
        "description": (
            "Resume work by reading the current session summary and project state. "
            "Answers 'where was I up to?' deterministically from stored state."
        ),
        "arguments": [
            {
                "name": "vault",
                "description": "The vault name to use.",
                "required": True,
            },
        ],
    },
    {
        "name": "cve.security_review",
        "description": (
            "Guide an agent through reviewing deterministic security findings."
        ),
        "arguments": [
            {
                "name": "vault",
                "description": "The vault name to use.",
                "required": True,
            },
        ],
    },
    {
        "name": "cve.vault_review",
        "description": (
            "Guide an agent through reviewing vault state, blockers, tasks, "
            "missing concepts, and security status."
        ),
        "arguments": [
            {
                "name": "vault",
                "description": "The vault name to use.",
                "required": True,
            },
        ],
    },
]

_PROMPT_NAMES: frozenset[str] = frozenset(p["name"] for p in PROMPTS)

# ---------------------------------------------------------------------------
# Safety footer included in all prompts
# ---------------------------------------------------------------------------

_SAFETY_FOOTER = (
    "\n\n---\n"
    "SAFETY: Do not edit notes unless the user explicitly asks and a safe "
    "note-edit tool is available. All tool calls in this session are "
    "read-only by default."
)


# ---------------------------------------------------------------------------
# Prompt message generators
# ---------------------------------------------------------------------------

def get_prompt(name: str, arguments: dict | None = None) -> dict | None:
    """Return the prompt content for a named prompt.

    Returns a dict with 'description' and 'messages', or None if not found.
    """
    if arguments is None:
        arguments = {}

    vault = arguments.get("vault", "<vault>")

    if name == "cve.vault_review":
        return _prompt_vault_review(vault)
    if name == "cve.security_review":
        return _prompt_security_review(vault)
    if name == "cve.context_handoff":
        intent = arguments.get("intent", "agent-context")
        return _prompt_context_handoff(vault, intent)
    if name == "cve.quality_plan":
        return _prompt_quality_plan(vault)
    if name == "cve.resume_work":
        return _prompt_resume_work(vault)

    return None


def _prompt_vault_review(vault: str) -> dict:
    text = (
        f"You are reviewing the vault: {vault!r}\n\n"
        "Follow these steps to produce a comprehensive review:\n\n"
        "1. Call `cve.get_context_state` with `vault={vault!r}` to get the "
        "current state snapshot including readiness, blockers, and warnings.\n\n"
        "2. Review `readiness` flags:\n"
        "   - `valid`: whether all notes pass schema validation\n"
        "   - `security_passed`: whether the security scan passes\n"
        "   - `has_tasks`: whether improvement tasks are pending\n"
        "   - `has_missing_concepts`: whether expected concepts are absent\n"
        "   - `ready_to_export`: whether the vault is ready for export\n"
        "   - `ready_for_agent_context`: whether the vault is safe for agent use\n\n"
        "3. If there are `blockers`, report them clearly and suggest the user "
        "resolve them before continuing.\n\n"
        "4. Call `cve.get_tasks` with `vault={vault!r}` to see the prioritised "
        "improvement task list.\n\n"
        "5. Call `cve.get_missing_concepts` with `vault={vault!r}` to identify "
        "knowledge gaps.\n\n"
        "6. Call `cve.security_scan` with `vault={vault!r}` to review any "
        "security findings.\n\n"
        "7. Summarise your findings and recommend the top 3 next actions.\n"
        "   Present these as numbered steps with clear rationale.\n"
        f"{_SAFETY_FOOTER}"
    )
    return {
        "description": "Vault review workflow",
        "messages": [
            {"role": "user", "content": {"type": "text", "text": text}},
        ],
    }


def _prompt_security_review(vault: str) -> dict:
    text = (
        f"You are reviewing security findings for the vault: {vault!r}\n\n"
        "Follow these steps:\n\n"
        "1. Call `cve.security_scan` with `vault={vault!r}` to retrieve "
        "deterministic security scan results.\n\n"
        "2. Review the `status` field:\n"
        "   - `pass`: no findings detected\n"
        "   - `warning`: findings present but none are blocking\n"
        "   - `fail`: one or more critical or high-severity findings\n\n"
        "3. For each finding, note:\n"
        "   - `path`: which note contains the finding\n"
        "   - `rule`: which security rule was triggered\n"
        "   - `severity`: critical / high / medium / low\n"
        "   - `detail`: the specific matched content\n\n"
        "4. Summarise the findings by severity level.\n\n"
        "5. For `fail` or `warning` status:\n"
        "   - Identify which notes need attention.\n"
        "   - Describe what kind of content triggered the finding.\n"
        "   - Recommend corrective action for the note author.\n\n"
        "6. Do NOT attempt to edit or delete notes directly. "
        "Recommend changes to the user only.\n"
        f"{_SAFETY_FOOTER}"
    )
    return {
        "description": "Security review workflow",
        "messages": [
            {"role": "user", "content": {"type": "text", "text": text}},
        ],
    }


def _prompt_context_handoff(vault: str, intent: str) -> dict:
    text = (
        f"You are preparing a context handoff for the vault: {vault!r}\n"
        f"Intent: {intent!r}\n\n"
        "Follow these steps:\n\n"
        "1. Call `cve.get_context_plan` with `vault={vault!r}` and "
        f"`intent={intent!r}` to get the deterministic recommendation plan.\n\n"
        "2. Review the `recommendations` list:\n"
        "   - `rank`: priority order\n"
        "   - `action`: what to do\n"
        "   - `severity`: urgency\n"
        "   - `title`: short label\n"
        "   - `reason`: why this is recommended\n\n"
        "3. If there are `blockers`, report them before proceeding.\n\n"
        "4. Call `cve.build_context_bundle` with `vault={vault!r}` to build "
        "a deterministic in-memory context bundle. "
        "Use `allow_partial=True` if notes are still in progress.\n\n"
        "5. Report the bundle summary:\n"
        "   - how many notes were included\n"
        "   - the budget used vs. available\n"
        "   - the `validation_status`\n"
        "   - any `warnings`\n\n"
        "6. Present the `next_best_action` from the plan as the recommended "
        "next step for the agent or user.\n"
        f"{_SAFETY_FOOTER}"
    )
    return {
        "description": "Context handoff workflow",
        "messages": [
            {"role": "user", "content": {"type": "text", "text": text}},
        ],
    }


def _prompt_quality_plan(vault: str) -> dict:
    text = (
        f"You are assessing quality and planning improvements for the vault: {vault!r}\n\n"
        "Follow these steps:\n\n"
        "1. Call `cve.get_tasks` with `vault={vault!r}` to get the prioritised "
        "improvement task list.\n\n"
        "2. For each task note:\n"
        "   - `path`: which note needs work\n"
        "   - `priority`: how important this task is (higher = more urgent)\n"
        "   - `missing`: which required sections are absent\n"
        "   - `action`: what kind of update is needed\n"
        "   - `constraints`: content writing guidelines to follow\n\n"
        "3. Call `cve.get_missing_concepts` with `vault={vault!r}` to identify "
        "knowledge gaps (topics expected but not yet present).\n\n"
        "4. Call `cve.validate_vault` with `vault={vault!r}` to check for "
        "schema validation errors.\n\n"
        "5. Prioritise your recommendations:\n"
        "   - First: fix any validation errors (they block export)\n"
        "   - Second: address the top-priority incomplete notes\n"
        "   - Third: suggest new notes for the highest-priority missing concepts\n\n"
        "6. Present a numbered quality improvement plan with clear actions.\n"
        "   For each action, reference the specific note path or concept name.\n"
        f"{_SAFETY_FOOTER}"
    )
    return {
        "description": "Quality planning workflow",
        "messages": [
            {"role": "user", "content": {"type": "text", "text": text}},
        ],
    }

def _prompt_resume_work(vault: str) -> dict:
    text = (
        f"You are resuming work on the vault: {vault!r}\n\n"
        "Follow these steps to reconstruct where work was up to:\n\n"
        "1. Call `cve.summarise_session` with `vault={vault!r}` to read the "
        "most recently active session summary.\n"
        "   The summary includes: session_id, active_vault, current_project, "
        "current_topic, user_goal, recent_notes, status, and timestamps.\n\n"
        "2. Call `cve.get_project_state` with `vault={vault!r}` to read the "
        "current project state.\n"
        "   The state includes: current_phase, completed_work, next_actions, "
        "blockers, decisions, and risks.\n\n"
        "3. If a session is found:\n"
        "   - Report the session ID and when it was last active.\n"
        "   - Report the user_goal if set.\n"
        "   - List the recent_notes (the last few files worked on).\n\n"
        "4. Report project state:\n"
        "   - Report current_phase.\n"
        "   - List next_actions (what was planned).\n"
        "   - List any blockers.\n\n"
        "5. If no session exists, call `cve.get_context_state` with "
        f"`vault={vault!r}` and report the vault readiness and blockers.\n\n"
        "6. Recommend the immediate next step based on the above information.\n\n"
        "PRIVACY NOTE: Session state may contain user goals or project details. "
        "Do not share session content outside this conversation without user consent.\n"
        f"{_SAFETY_FOOTER}"
    )
    return {
        "description": "Resume work from stored session and project state",
        "messages": [
            {"role": "user", "content": {"type": "text", "text": text}},
        ],
    }