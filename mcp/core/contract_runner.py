"""
Contract runner — executes all system invariant checks across all vaults.

Returns structured results: PASS or FAIL with detailed violations.
"""

import time
import logging

from mcp.core.vault_registry import list_vaults
from mcp.core.system_contract import (
    check_vault_integrity,
    check_schema_interface,
    check_index_integrity,
    check_query_determinism,
    check_index_consistency,
    check_schema_consistency,
)

logger = logging.getLogger("mcp.contract")


def run_all_checks(*, include_vault_scripts: bool = True) -> dict:
    """Run all contract checks across all vaults.

    Args:
        include_vault_scripts: If True, run vault_schema --audit,
            validate_vault.py, and inject_frontmatter --dry-run.
            Set False for lightweight mode.

    Returns:
        {
            "status": "pass" | "fail",
            "duration_ms": float,
            "vaults": {
                "vault_name": {
                    "status": "pass" | "fail",
                    "checks": {
                        "check_name": {
                            "status": "pass" | "fail",
                            "violations": [...]
                        }
                    }
                }
            },
            "total_violations": int,
            "violations": [...]   # flat list of all violation strings
        }
    """
    start = time.monotonic()
    vaults = list_vaults()

    all_violations: list[str] = []
    vault_results: dict[str, dict] = {}

    for vault_name in vaults:
        checks: dict[str, dict] = {}

        # Define which checks to run
        check_suite = [
            ("schema_interface", check_schema_interface),
            ("index_integrity", check_index_integrity),
            ("query_determinism", check_query_determinism),
        ]

        if include_vault_scripts:
            check_suite.insert(0, ("vault_integrity", check_vault_integrity))

        vault_violations: list[str] = []

        for check_name, check_fn in check_suite:
            logger.info("contract_check vault=%s check=%s", vault_name, check_name)
            try:
                violations = check_fn(vault_name)
            except Exception as exc:
                violations = [f"{vault_name}: {check_name} raised: {exc}"]

            checks[check_name] = {
                "status": "pass" if not violations else "fail",
                "violations": violations,
            }

            vault_violations.extend(violations)

        all_violations.extend(vault_violations)

        vault_results[vault_name] = {
            "status": "pass" if not vault_violations else "fail",
            "checks": checks,
        }

    duration = (time.monotonic() - start) * 1000

    result = {
        "status": "pass" if not all_violations else "fail",
        "duration_ms": round(duration, 1),
        "vaults": vault_results,
        "total_violations": len(all_violations),
        "violations": all_violations,
    }

    if all_violations:
        logger.warning(
            "contract_result status=fail violations=%d duration_ms=%.1f",
            len(all_violations), duration,
        )
    else:
        logger.info(
            "contract_result status=pass vaults=%d duration_ms=%.1f",
            len(vaults), duration,
        )

    return result


def run_lightweight_checks() -> dict:
    """Run only index + schema consistency checks (fast, no subprocesses).

    Suitable for periodic background recheck.
    """
    start = time.monotonic()
    vaults = list_vaults()

    all_violations: list[str] = []
    vault_results: dict[str, dict] = {}

    for vault_name in vaults:
        checks: dict[str, dict] = {}
        vault_violations: list[str] = []

        for check_name, check_fn in [
            ("schema_consistency", check_schema_consistency),
            ("index_consistency", check_index_consistency),
        ]:
            try:
                violations = check_fn(vault_name)
            except Exception as exc:
                violations = [f"{vault_name}: {check_name} raised: {exc}"]

            checks[check_name] = {
                "status": "pass" if not violations else "fail",
                "violations": violations,
            }
            vault_violations.extend(violations)

        all_violations.extend(vault_violations)
        vault_results[vault_name] = {
            "status": "pass" if not vault_violations else "fail",
            "checks": checks,
        }

    duration = (time.monotonic() - start) * 1000

    return {
        "status": "pass" if not all_violations else "fail",
        "duration_ms": round(duration, 1),
        "vaults": vault_results,
        "total_violations": len(all_violations),
        "violations": all_violations,
    }
