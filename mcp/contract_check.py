"""
Contract check CLI — runs all system invariant checks from the command line.

Usage:
    python contract_check.py            # full check (including vault scripts)
    python contract_check.py --fast     # lightweight checks only

Exit codes:
    0 = PASS
    1 = FAIL
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path so mcp.* and core.* imports work
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp.core.contract_runner import run_all_checks, run_lightweight_checks


def main() -> int:
    fast_mode = "--fast" in sys.argv

    print("=" * 60)
    if fast_mode:
        print("SYSTEM CONTRACT CHECK (lightweight)")
    else:
        print("SYSTEM CONTRACT CHECK (full)")
    print("=" * 60)

    if fast_mode:
        result = run_lightweight_checks()
    else:
        result = run_all_checks(include_vault_scripts=True)

    # Per-vault status
    for vault_name, vault_data in result["vaults"].items():
        status = vault_data["status"].upper()
        icon = "PASS" if status == "PASS" else "FAIL"
        print(f"\n  [{icon}] {vault_name}")

        for check_name, check_data in vault_data["checks"].items():
            check_icon = "+" if check_data["status"] == "pass" else "X"
            print(f"    [{check_icon}] {check_name}")
            for v in check_data["violations"]:
                print(f"        ! {v}")

    # Summary
    print()
    print("-" * 60)
    print(f"Status:     {result['status'].upper()}")
    print(f"Violations: {result['total_violations']}")
    print(f"Duration:   {result['duration_ms']:.1f} ms")
    print("=" * 60)

    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
