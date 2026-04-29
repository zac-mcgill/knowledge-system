"""
System contract — formally verifiable invariants for the MCP + vault system.

Each check function returns a list of violation strings.
Empty list == PASS.
"""

import subprocess
import sys
from pathlib import Path
from types import ModuleType

from mcp.core.vault_registry import list_vaults, get_vault_path, get_schema
from mcp.core.note_index import build_index, get_index

_SCHEMA_RELATIVE_PATH = Path("Vault Files") / "Scripts" / "vault_schema.py"
_VALIDATE_SCRIPT = Path("Vault Files") / "Scripts" / "validate_vault.py"
_INJECT_SCRIPT = Path("Vault Files") / "Scripts" / "inject_frontmatter.py"

# --- Schema interface contract ---

REQUIRED_CONSTANTS = (
    "DOMAIN_MAP",
    "SUBDOMAIN_MAP",
    "VALID_TYPES",
    "SECTION_MAP",
    "ALL_KNOWN_FIELDS",
)

REQUIRED_FUNCTIONS = (
    "derive_type",
    "derive_domain",
    "derive_subdomain",
    "discover_files",
    "parse_yaml_frontmatter",
)


# ============================================================
# Invariant 1 — Vault integrity (via vault scripts)
# ============================================================

def check_vault_audit(vault_name: str) -> list[str]:
    """Run vault_schema.py --audit for a vault. Returns violations."""
    vault_path = get_vault_path(vault_name)
    schema_file = vault_path / _SCHEMA_RELATIVE_PATH
    violations = []

    if not schema_file.is_file():
        return [f"{vault_name}: vault_schema.py not found at {schema_file}"]

    try:
        result = subprocess.run(
            [sys.executable, str(schema_file), "--audit"],
            capture_output=True, text=True, timeout=30,
            cwd=str(vault_path),
        )
        if result.returncode != 0:
            violations.append(
                f"{vault_name}: vault_schema.py --audit failed (exit {result.returncode}): "
                f"{result.stdout.strip() or result.stderr.strip()}"
            )
    except subprocess.TimeoutExpired:
        violations.append(f"{vault_name}: vault_schema.py --audit timed out")
    except Exception as exc:
        violations.append(f"{vault_name}: vault_schema.py --audit error: {exc}")

    return violations


def check_vault_validate(vault_name: str) -> list[str]:
    """Run validate_vault.py for a vault. Returns violations."""
    vault_path = get_vault_path(vault_name)
    script = vault_path / _VALIDATE_SCRIPT
    violations = []

    if not script.is_file():
        return [f"{vault_name}: validate_vault.py not found at {script}"]

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=60,
            cwd=str(vault_path),
        )
        if result.returncode != 0:
            violations.append(
                f"{vault_name}: validate_vault.py failed (exit {result.returncode}): "
                f"{result.stdout.strip() or result.stderr.strip()}"
            )
    except subprocess.TimeoutExpired:
        violations.append(f"{vault_name}: validate_vault.py timed out")
    except Exception as exc:
        violations.append(f"{vault_name}: validate_vault.py error: {exc}")

    return violations


def check_vault_inject_dry(vault_name: str) -> list[str]:
    """Run inject_frontmatter.py --dry-run for a vault. Returns violations."""
    vault_path = get_vault_path(vault_name)
    script = vault_path / _INJECT_SCRIPT
    violations = []

    if not script.is_file():
        return [f"{vault_name}: inject_frontmatter.py not found at {script}"]

    try:
        result = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            capture_output=True, text=True, timeout=60,
            cwd=str(vault_path),
        )
        if result.returncode != 0:
            violations.append(
                f"{vault_name}: inject_frontmatter.py --dry-run failed "
                f"(exit {result.returncode}): "
                f"{result.stdout.strip() or result.stderr.strip()}"
            )
    except subprocess.TimeoutExpired:
        violations.append(f"{vault_name}: inject_frontmatter.py --dry-run timed out")
    except Exception as exc:
        violations.append(f"{vault_name}: inject_frontmatter.py --dry-run error: {exc}")

    return violations


def check_vault_integrity(vault_name: str) -> list[str]:
    """Run all three vault integrity checks."""
    violations = []
    violations.extend(check_vault_audit(vault_name))
    violations.extend(check_vault_validate(vault_name))
    violations.extend(check_vault_inject_dry(vault_name))
    return violations


# ============================================================
# Invariant 2 — Schema interface
# ============================================================

def check_schema_interface(vault_name: str) -> list[str]:
    """Verify schema exposes all required constants and functions."""
    violations = []

    try:
        schema = get_schema(vault_name)
    except Exception as exc:
        return [f"{vault_name}: failed to load schema: {exc}"]

    for name in REQUIRED_CONSTANTS:
        if not hasattr(schema, name):
            violations.append(f"{vault_name}: schema missing constant {name!r}")

    for name in REQUIRED_FUNCTIONS:
        if not hasattr(schema, name):
            violations.append(f"{vault_name}: schema missing function {name!r}")
        elif not callable(getattr(schema, name)):
            violations.append(f"{vault_name}: schema.{name} is not callable")

    return violations


# ============================================================
# Invariant 3 — Index integrity
# ============================================================

def check_index_integrity(vault_name: str) -> list[str]:
    """Verify index count matches discover_files and records are well-formed."""
    violations = []

    try:
        vault_path = get_vault_path(vault_name)
        schema = get_schema(vault_name)
    except Exception as exc:
        return [f"{vault_name}: setup error: {exc}"]

    discovered = schema.discover_files(vault_path)
    index = get_index(vault_name)

    if len(index) != len(discovered):
        violations.append(
            f"{vault_name}: index count ({len(index)}) != "
            f"discover_files count ({len(discovered)})"
        )

    required_keys = {"path", "fields", "body"}
    for i, record in enumerate(index):
        missing = required_keys - set(record.keys())
        if missing:
            violations.append(
                f"{vault_name}: index[{i}] missing keys: {missing}"
            )
            break  # one example is enough

    return violations


# ============================================================
# Invariant 4 — Query determinism
# ============================================================

def check_query_determinism(vault_name: str) -> list[str]:
    """Run identical queries twice and verify results are identical."""
    from mcp.core.query_engine import query as run_query, list_notes

    violations = []

    # Test 1: list_notes determinism
    r1 = list_notes(vault_name, limit=500)
    r2 = list_notes(vault_name, limit=500)

    paths1 = [n["path"] for n in r1["results"]]
    paths2 = [n["path"] for n in r2["results"]]

    if paths1 != paths2:
        violations.append(
            f"{vault_name}: list_notes non-deterministic "
            f"(run1={len(paths1)} vs run2={len(paths2)} results)"
        )

    # Test 2: filtered query determinism
    r3 = run_query(vault_name, {"type": "core-concept"}, limit=500)
    r4 = run_query(vault_name, {"type": "core-concept"}, limit=500)

    paths3 = [n["path"] for n in r3.get("results", [])]
    paths4 = [n["path"] for n in r4.get("results", [])]

    if paths3 != paths4:
        violations.append(
            f"{vault_name}: filtered query non-deterministic "
            f"(run1={len(paths3)} vs run2={len(paths4)} results)"
        )

    return violations


# ============================================================
# Lightweight checks (for periodic recheck)
# ============================================================

def check_index_consistency(vault_name: str) -> list[str]:
    """Lightweight: verify index count still matches discover_files."""
    violations = []
    try:
        vault_path = get_vault_path(vault_name)
        schema = get_schema(vault_name)
        discovered = schema.discover_files(vault_path)
        index = get_index(vault_name)

        if len(index) != len(discovered):
            violations.append(
                f"{vault_name}: index drift — indexed={len(index)}, "
                f"discovered={len(discovered)}"
            )
    except Exception as exc:
        violations.append(f"{vault_name}: consistency check error: {exc}")

    return violations


def check_schema_consistency(vault_name: str) -> list[str]:
    """Lightweight: verify schema still exposes required interface."""
    return check_schema_interface(vault_name)
