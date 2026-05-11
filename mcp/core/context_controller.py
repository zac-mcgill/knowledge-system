"""
Context Controller — deterministic vault state aggregation.

Aggregates data from all existing adapters and services to produce:
  - A vault state snapshot (GET /context/state)
  - An intent-scoped recommendation plan (POST /context/plan)

This module is READ-ONLY.  It never mutates files, indices, caches, or
feedback entries.  All outputs are derived deterministically from the
current state of the vault at call time.

Supported intents: review, export, agent-context, quality, security
"""

from __future__ import annotations

_VALID_INTENTS = frozenset({"review", "export", "agent-context", "quality", "security"})

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_context_state(vault_name: str) -> dict:
    """Return a full deterministic state snapshot for *vault_name*.

    Response shape::

        {
          "vault": str,
          "state": {
            "summary": {...},
            "validation": {...},
            "security": {...},
            "tasks": {...},
            "missing": {...},
            "feedback": {...},
            "graph": {...},
          },
          "readiness": {
            "valid": bool,
            "security_passed": bool,
            "has_tasks": bool,
            "has_missing_concepts": bool,
            "has_feedback_warnings": bool,
            "ready_to_export": bool,
            "ready_for_agent_context": bool,
          },
          "blockers": [str],
          "warnings": [str],
        }

    Errors are returned as ``{"status": "error", "error": {"code": ..., "message": ...}}``.
    """
    try:
        from mcp.core.vault_registry import list_vaults, get_vault_path  # noqa: PLC0415

        vaults = list_vaults()
        if vault_name not in vaults:
            return {
                "status": "error",
                "error": {"code": "INVALID_VAULT", "message": f"Vault not found: {vault_name!r}"},
            }

        validation = _summarise_validation(vault_name)
        security = _summarise_security(vault_name)
        tasks = _summarise_tasks(vault_name)
        missing = _summarise_missing(vault_name)
        feedback = _summarise_feedback(vault_name)
        graph = _summarise_graph(vault_name)

        readiness = _compute_readiness(validation, security, tasks, missing, feedback)
        blockers = _build_blockers(validation, security, readiness)
        warnings = _build_warnings(tasks, missing, feedback)

        return {
            "vault": vault_name,
            "state": {
                "summary": {
                    "validation_status": validation.get("status", "unknown"),
                    "security_status": security.get("status", "unknown"),
                    "total_tasks": tasks.get("total", 0),
                    "total_missing": missing.get("total_missing", 0),
                    "feedback_entry_count": feedback.get("entry_count", 0),
                    "graph_node_count": graph.get("node_count", 0),
                },
                "validation": validation,
                "security": security,
                "tasks": tasks,
                "missing": missing,
                "feedback": feedback,
                "graph": graph,
            },
            "readiness": readiness,
            "blockers": blockers,
            "warnings": warnings,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": {"code": "CONTROLLER_FAILED", "message": str(exc)},
        }


def build_context_plan(vault_name: str, intent: str = "review") -> dict:
    """Build a deterministic recommendation plan for *intent*.

    Response shape::

        {
          "vault": str,
          "intent": str,
          "readiness": {...},
          "recommendations": [
            {
              "rank": int,
              "action": str,
              "severity": str,
              "title": str,
              "reason": str,
              "source": str,
              "links": {"ui": str, "api": str},
            }
          ],
          "blockers": [str],
          "warnings": [str],
          "next_best_action": {"action": str, "title": str} | None,
        }

    Returns an error dict if the vault is unknown or the intent is invalid.
    """
    if intent not in _VALID_INTENTS:
        return {
            "status": "error",
            "error": {
                "code": "INVALID_INTENT",
                "message": (
                    f"Unknown intent: {intent!r}. "
                    f"Valid intents: {sorted(_VALID_INTENTS)}"
                ),
            },
        }

    state = get_context_state(vault_name)
    if state.get("status") == "error":
        return state

    validation = state["state"]["validation"]
    security = state["state"]["security"]
    tasks = state["state"]["tasks"]
    missing = state["state"]["missing"]
    feedback = state["state"]["feedback"]
    readiness = state["readiness"]
    blockers = state["blockers"]
    warnings = state["warnings"]

    recommendations = _build_recommendations(
        intent=intent,
        vault_name=vault_name,
        validation=validation,
        security=security,
        tasks=tasks,
        missing=missing,
        feedback=feedback,
        readiness=readiness,
    )

    next_best = (
        {"action": recommendations[0]["action"], "title": recommendations[0]["title"]}
        if recommendations
        else None
    )

    return {
        "vault": vault_name,
        "intent": intent,
        "readiness": readiness,
        "recommendations": recommendations,
        "blockers": blockers,
        "warnings": warnings,
        "next_best_action": next_best,
    }


# ---------------------------------------------------------------------------
# Private helpers — data summarisation
# ---------------------------------------------------------------------------


def _summarise_validation(vault_name: str) -> dict:
    """Return a compact validation summary."""
    try:
        from mcp.core.adapters.validation_adapter import get_validation  # noqa: PLC0415

        result = get_validation(vault_name=vault_name)
        if "error" in result:
            return {"status": "error", "error": result["error"], "invalid_count": 0, "invalid_notes": []}
        return result
    except Exception as exc:
        return {"status": "error", "error": str(exc), "invalid_count": 0, "invalid_notes": []}


def _summarise_security(vault_name: str) -> dict:
    """Return a compact security summary (no file scan — uses adapter pattern)."""
    try:
        from core.shared.context_security import scan_vault_context  # noqa: PLC0415

        result = scan_vault_context(vault_name=vault_name)
        return {
            "status": result.get("status", "unknown"),
            "finding_count": len(result.get("findings", [])),
            "summary": result.get("summary", {}),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "finding_count": 0, "summary": {}}


def _summarise_tasks(vault_name: str) -> dict:
    """Return a compact tasks summary."""
    try:
        from mcp.core.adapters.tasks_adapter import get_tasks  # noqa: PLC0415

        result = get_tasks(vault_name=vault_name, limit=9999, include_feedback=False)
        if "error" in result:
            return {"total": 0, "top_tasks": [], "error": result["error"]}
        top = result.get("tasks", [])[:5]
        return {
            "total": result.get("total", 0),
            "top_tasks": [
                {"path": t["path"], "priority": t.get("priority", 0), "action": t.get("action", "")}
                for t in top
            ],
        }
    except Exception as exc:
        return {"total": 0, "top_tasks": [], "error": str(exc)}


def _summarise_missing(vault_name: str) -> dict:
    """Return a compact missing-concepts summary."""
    try:
        from mcp.core.adapters.missing_adapter import get_missing  # noqa: PLC0415

        result = get_missing(vault_name=vault_name)
        if "error" in result:
            # EXPECTED_CONCEPTS not defined is not a hard error for the controller
            return {"total_missing": 0, "available": False, "error": result["error"]}
        return {
            "available": True,
            "total_expected": result.get("total_expected", 0),
            "total_actual": result.get("total_actual", 0),
            "total_missing": result.get("total_missing", 0),
            "top_gaps": result.get("ranked", [])[:5],
        }
    except Exception as exc:
        return {"total_missing": 0, "available": False, "error": str(exc)}


def _summarise_feedback(vault_name: str) -> dict:
    """Return a compact feedback summary."""
    try:
        from mcp.core.vault_registry import get_vault_path  # noqa: PLC0415
        from core.shared.feedback import load_feedback  # noqa: PLC0415

        vault_path = get_vault_path(vault_name)
        result = load_feedback(vault_path)
        entries = result.get("entries", [])
        warnings_list = result.get("warnings", [])
        errors_list = result.get("errors", [])
        has_warnings = bool(warnings_list or errors_list)
        return {
            "status": result.get("status", "ok"),
            "entry_count": len(entries),
            "has_warnings": has_warnings,
            "warning_count": len(warnings_list),
            "error_count": len(errors_list),
        }
    except Exception as exc:
        return {"status": "error", "entry_count": 0, "has_warnings": False,
                "warning_count": 0, "error_count": 0, "error": str(exc)}


def _summarise_graph(vault_name: str) -> dict:
    """Return a compact graph summary."""
    try:
        from mcp.core.graph_builder import build_graph  # noqa: PLC0415

        graph = build_graph(vault_name=vault_name)
        return {
            "node_count": len(graph.get("nodes", [])),
            "edge_count": len(graph.get("edges", [])),
        }
    except Exception as exc:
        return {"node_count": 0, "edge_count": 0, "error": str(exc)}


# ---------------------------------------------------------------------------
# Private helpers — readiness / blockers / warnings / recommendations
# ---------------------------------------------------------------------------


def _compute_readiness(
    validation: dict,
    security: dict,
    tasks: dict,
    missing: dict,
    feedback: dict,
) -> dict:
    valid = validation.get("status") == "pass"
    security_passed = security.get("status") in ("pass", "warning")
    has_tasks = tasks.get("total", 0) > 0
    has_missing_concepts = missing.get("available", False) and missing.get("total_missing", 0) > 0
    has_feedback_warnings = feedback.get("has_warnings", False)
    ready_to_export = valid and security_passed
    ready_for_agent_context = valid and security_passed
    return {
        "valid": valid,
        "security_passed": security_passed,
        "has_tasks": has_tasks,
        "has_missing_concepts": has_missing_concepts,
        "has_feedback_warnings": has_feedback_warnings,
        "ready_to_export": ready_to_export,
        "ready_for_agent_context": ready_for_agent_context,
    }


def _build_blockers(validation: dict, security: dict, readiness: dict) -> list[str]:
    blockers = []
    if not readiness["valid"]:
        count = validation.get("invalid_count", 0)
        blockers.append(
            f"Validation failed: {count} invalid note(s). Fix frontmatter errors before exporting."
        )
    if security.get("status") == "fail":
        count = security.get("finding_count", 0)
        blockers.append(
            f"Security scan failed: {count} critical/high finding(s). "
            "Remove secrets or sensitive content before exporting."
        )
    return blockers


def _build_warnings(tasks: dict, missing: dict, feedback: dict) -> list[str]:
    warnings_list = []
    if tasks.get("total", 0) > 0:
        warnings_list.append(
            f"{tasks['total']} note(s) have incomplete sections and are candidates for upgrade."
        )
    if missing.get("available") and missing.get("total_missing", 0) > 0:
        warnings_list.append(
            f"{missing['total_missing']} expected concept(s) are missing from the vault."
        )
    if feedback.get("has_warnings"):
        warnings_list.append(
            f"Feedback file contains {feedback.get('warning_count', 0)} warning(s) "
            f"and {feedback.get('error_count', 0)} error(s)."
        )
    return warnings_list


def _build_recommendations(
    *,
    intent: str,
    vault_name: str,
    validation: dict,
    security: dict,
    tasks: dict,
    missing: dict,
    feedback: dict,
    readiness: dict,
) -> list[dict]:
    """Build a ranked list of recommendations for *intent*.

    Recommendations are deterministic: same inputs always produce same outputs.
    Rank 1 = most urgent.
    """
    recs: list[dict] = []
    rank = 1

    # --- Blockers always appear first regardless of intent ---
    if not readiness["valid"]:
        count = validation.get("invalid_count", 0)
        recs.append({
            "rank": rank,
            "action": "fix-validation",
            "severity": "critical",
            "title": "Fix validation errors",
            "reason": (
                f"{count} note(s) have invalid frontmatter. "
                "Validation must pass before the vault can be exported or used as agent context."
            ),
            "source": "validation",
            "links": {
                "ui": f"/app/validation?vault={vault_name}",
                "api": f"/validation?vault={vault_name}",
            },
        })
        rank += 1

    if security.get("status") == "fail":
        count = security.get("finding_count", 0)
        recs.append({
            "rank": rank,
            "action": "fix-security",
            "severity": "critical",
            "title": "Resolve security findings",
            "reason": (
                f"{count} critical/high security finding(s) detected. "
                "Secrets and sensitive content must be removed before exporting."
            ),
            "source": "security",
            "links": {
                "ui": f"/app/security?vault={vault_name}",
                "api": f"/context/security",
            },
        })
        rank += 1

    # --- Intent-specific recommendations ---
    if intent in ("review", "quality"):
        if tasks.get("total", 0) > 0:
            recs.append({
                "rank": rank,
                "action": "upgrade-notes",
                "severity": "medium",
                "title": "Complete incomplete notes",
                "reason": (
                    f"{tasks['total']} note(s) have missing sections. "
                    "Completing them improves vault coverage and quality scores."
                ),
                "source": "tasks",
                "links": {
                    "ui": f"/app/tasks?vault={vault_name}",
                    "api": f"/tasks?vault={vault_name}",
                },
            })
            rank += 1

        if missing.get("available") and missing.get("total_missing", 0) > 0:
            recs.append({
                "rank": rank,
                "action": "add-missing-concepts",
                "severity": "low",
                "title": "Add missing concepts",
                "reason": (
                    f"{missing['total_missing']} expected concept(s) are absent. "
                    "Adding them improves vault completeness."
                ),
                "source": "missing",
                "links": {
                    "ui": f"/app/notes?vault={vault_name}",
                    "api": f"/missing?vault={vault_name}",
                },
            })
            rank += 1

        if security.get("status") == "warning":
            recs.append({
                "rank": rank,
                "action": "review-security-warnings",
                "severity": "low",
                "title": "Review security warnings",
                "reason": (
                    "Security scan returned warnings (e.g. external links or code blocks). "
                    "Review findings before sharing the vault externally."
                ),
                "source": "security",
                "links": {
                    "ui": f"/app/security?vault={vault_name}",
                    "api": f"/context/security",
                },
            })
            rank += 1

    elif intent == "export":
        if readiness["ready_to_export"]:
            recs.append({
                "rank": rank,
                "action": "export-now",
                "severity": "info",
                "title": "Vault is ready to export",
                "reason": "Validation passed and security scan passed/warned. You may export now.",
                "source": "controller",
                "links": {
                    "ui": f"/app/exports?vault={vault_name}",
                    "api": "/context/export",
                },
            })
            rank += 1
        if tasks.get("total", 0) > 0:
            recs.append({
                "rank": rank,
                "action": "upgrade-notes-before-export",
                "severity": "low",
                "title": "Consider upgrading notes before export",
                "reason": (
                    f"{tasks['total']} note(s) are incomplete. "
                    "Completing them will improve the quality of the exported bundle."
                ),
                "source": "tasks",
                "links": {
                    "ui": f"/app/tasks?vault={vault_name}",
                    "api": f"/tasks?vault={vault_name}",
                },
            })
            rank += 1

    elif intent == "agent-context":
        if readiness["ready_for_agent_context"]:
            recs.append({
                "rank": rank,
                "action": "generate-bundle",
                "severity": "info",
                "title": "Vault is ready for agent context",
                "reason": (
                    "Validation passed and security scan passed/warned. "
                    "Generate a context bundle for use with an LLM agent."
                ),
                "source": "controller",
                "links": {
                    "ui": f"/app/bundles?vault={vault_name}",
                    "api": "/context/bundle",
                },
            })
            rank += 1
        if missing.get("available") and missing.get("total_missing", 0) > 0:
            recs.append({
                "rank": rank,
                "action": "add-missing-concepts",
                "severity": "low",
                "title": "Improve context coverage",
                "reason": (
                    f"{missing['total_missing']} expected concept(s) are absent. "
                    "Adding them will improve agent context completeness."
                ),
                "source": "missing",
                "links": {
                    "ui": f"/app/notes?vault={vault_name}",
                    "api": f"/missing?vault={vault_name}",
                },
            })
            rank += 1

    elif intent == "security":
        sec_status = security.get("status", "unknown")
        if sec_status == "pass":
            recs.append({
                "rank": rank,
                "action": "security-ok",
                "severity": "info",
                "title": "No security issues found",
                "reason": "The security scan found no findings. The vault is clean.",
                "source": "security",
                "links": {
                    "ui": f"/app/security?vault={vault_name}",
                    "api": "/context/security",
                },
            })
            rank += 1
        elif sec_status == "warning":
            recs.append({
                "rank": rank,
                "action": "review-security-warnings",
                "severity": "medium",
                "title": "Review security warnings",
                "reason": (
                    f"{security.get('finding_count', 0)} warning(s) found. "
                    "Review and address any external links or code blocks before sharing."
                ),
                "source": "security",
                "links": {
                    "ui": f"/app/security?vault={vault_name}",
                    "api": "/context/security",
                },
            })
            rank += 1

    # --- Universal low-priority recommendation: add feedback ---
    if feedback.get("entry_count", 0) == 0 and intent in ("review", "quality", "agent-context"):
        recs.append({
            "rank": rank,
            "action": "add-feedback",
            "severity": "info",
            "title": "No feedback recorded",
            "reason": (
                "Adding feedback entries helps the task prioritiser surface "
                "notes that need the most attention."
            ),
            "source": "feedback",
            "links": {
                "ui": f"/app/feedback?vault={vault_name}",
                "api": f"/feedback?vault={vault_name}",
            },
        })
        rank += 1

    return recs
