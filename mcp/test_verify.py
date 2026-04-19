"""Verification tests for the MCP server hardening — all phases."""

import sys
import time
import threading
import concurrent.futures
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.vault_registry import list_vaults, get_vault_path, get_schema
from core.note_index import (
    build_index, get_index, get_schema_hash,
    get_index_metadata, _SCHEMA_COOLDOWN_SECONDS,
    _indices, _get_vault_lock,
)
from core.query_engine import query, list_notes, get_note, aggregate


# ============================================================
# Original hardening tests (preserved)
# ============================================================

def test_basic_functionality():
    """Sanity check: all vaults load and index correctly."""
    print("=== Test 1: Basic Functionality ===")
    vaults = list_vaults()
    expected = {
        "Core Engineering", "Cyber Security", "Databases", "Foundations",
        "Integration", "Mathematics for Computing", "Networking",
        "Operations", "Systems", "Tooling",
    }
    assert set(vaults) == expected, f"Unexpected: {vaults}"
    print(f"  Vaults: {vaults}")

    for v in vaults:
        idx = build_index(v)
        print(f"  {v}: {len(idx)} notes indexed")
        assert len(idx) > 0, f"Empty index for {v}"


def test_deterministic_ordering():
    """Index and query results are sorted deterministically."""
    print("\n=== Test 2: Deterministic Ordering ===")
    for v in list_vaults():
        idx1 = build_index(v)
        idx2 = build_index(v)
        paths1 = [n["path"] for n in idx1]
        paths2 = [n["path"] for n in idx2]
        assert paths1 == paths2, f"Non-deterministic index for {v}"
        assert paths1 == sorted(paths1, key=str.lower), f"Index not sorted for {v}"
        print(f"  {v}: deterministic and sorted ({len(paths1)} notes)")


def test_concurrent_queries():
    """Concurrent access produces consistent results, no crashes."""
    print("\n=== Test 3: Concurrent Queries ===")
    errors = []

    def worker(vault, i):
        try:
            result = list_notes(vault)
            assert result["status"] == "ok"
            assert result["count"] > 0
        except Exception as e:
            errors.append(f"Worker {i} ({vault}): {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = []
        vaults = list_vaults()
        for i in range(20):
            vault = vaults[i % len(vaults)]
            futures.append(pool.submit(worker, vault, i))
        concurrent.futures.wait(futures)

    assert not errors, f"Concurrent errors: {errors}"
    print(f"  20 concurrent queries completed without error")


def test_schema_hash_tracking():
    """Schema hash is stored and retrievable after build."""
    print("\n=== Test 4: Schema Hash Tracking ===")
    for v in list_vaults():
        build_index(v)
        h = get_schema_hash(v)
        assert h is not None, f"No schema hash for {v}"
        assert len(h) == 64, f"Invalid hash length for {v}: {len(h)}"
        print(f"  {v}: schema_hash={h[:16]}...")


def test_pagination_stable():
    """Pagination returns stable, bounded, non-overlapping results."""
    print("\n=== Test 5: Pagination ===")
    for v in list_vaults():
        full = list_notes(v, limit=500)
        total = full["count"]

        page1 = list_notes(v, limit=5, offset=0)
        page2 = list_notes(v, limit=5, offset=5)

        assert page1["returned"] == min(5, total)
        assert page1["offset"] == 0
        assert page1["limit"] == 5

        paths1 = {n["path"] for n in page1["results"]}
        paths2 = {n["path"] for n in page2["results"]}
        assert not paths1 & paths2, "Pages overlap"

        full2 = list_notes(v, limit=500)
        assert ([n["path"] for n in full["results"]]
                == [n["path"] for n in full2["results"]])
        print(f"  {v}: total={total}, page1={page1['returned']}, page2={page2['returned']}")


def test_path_traversal_blocked():
    """Path traversal attempts are rejected."""
    print("\n=== Test 6: Path Traversal Blocked ===")
    attacks = [
        "../../../etc/passwd",
        "..\\..\\..\\Windows\\System32\\config\\SAM",
        "subdir/../../outside.md",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ]
    for path in attacks:
        result = get_note("Cyber Security", path)
        assert result["status"] == "error", f"Should block: {path}"
        assert result["error"]["code"] == "PATH_TRAVERSAL", f"Wrong code for: {path}"
        print(f"  Blocked: {path}")


def test_strict_mode():
    """Strict mode rejects unknown fields; non-strict ignores them."""
    print("\n=== Test 7: Strict Mode ===")

    result = query("Cyber Security", {"fake_field": "value"}, strict=False)
    assert result["status"] == "ok", "Non-strict should succeed"
    print(f"  Non-strict with unknown field: ok ({result['count']} results)")

    result = query("Cyber Security", {"fake_field": "value"}, strict=True)
    assert result["status"] == "error", "Strict should reject"
    assert result["error"]["code"] == "INVALID_FIELDS"
    print(f"  Strict with unknown field: rejected ({result['error']['message']})")


def test_limit_and_timeout():
    """Large queries respect limit; max limit is clamped."""
    print("\n=== Test 8: Limit + Timeout ===")

    result = query("Cyber Security", {}, limit=5)
    assert result["returned"] <= 5, f"Returned {result['returned']} > limit 5"
    assert result["limit"] == 5
    print(f"  Cyber Security: {result['count']} total, {result['returned']} returned (limit=5)")

    result = query("Cyber Security", {}, limit=9999)
    assert result["limit"] == 500, f"Limit not clamped: {result['limit']}"
    print(f"  Limit clamped to 500: ok")


def test_typed_responses():
    """All responses follow the typed contract."""
    print("\n=== Test 9: Typed Response Contract ===")

    result = list_notes("Cyber Security", limit=1)
    assert result["status"] == "ok"
    for key in ("count", "returned", "offset", "limit", "results"):
        assert key in result, f"Missing key: {key}"
    print(f"  list_notes: ok, has pagination keys")

    first_path = result["results"][0]["path"]
    result = get_note("Cyber Security", first_path)
    assert result["status"] == "ok"
    assert "data" in result
    print(f"  get_note: ok, has data")

    result = aggregate("Cyber Security", "type")
    assert result["status"] == "ok"
    assert "data" in result
    print(f"  aggregate: ok, has data")

    result = get_note("Cyber Security", "../escape")
    assert result["status"] == "error"
    assert "error" in result
    assert "code" in result["error"]
    assert "message" in result["error"]
    print(f"  error response: has code + message")


def test_cross_vault_queries():
    """Cross-vault aggregate works with typed response format."""
    print("\n=== Test 10: Cross-vault Queries ===")
    for v in list_vaults():
        result = aggregate(v, "type")
        assert result["status"] == "ok"
        print(f"  {v} type distribution: {result['data']['stats']}")

    result = aggregate("Cyber Security", "nonexistent")
    assert result["status"] == "error"
    assert result["error"]["code"] == "INVALID_FIELD"
    print(f"  aggregate unknown field: correctly rejected")


# ============================================================
# New operational resilience tests (Phase 9)
# ============================================================

def test_rate_limiter():
    """Phase 1: Rate limiter triggers under burst load."""
    print("\n=== Test 11: Rate Limiter ===")
    from server.mcp_server import _rate_limiter, _RateLimiter

    # Create a fresh limiter with low threshold for testing
    test_limiter = _RateLimiter(max_per_second=10)

    accepted = 0
    rejected = 0
    for _ in range(20):
        if test_limiter.allow():
            accepted += 1
        else:
            rejected += 1

    assert accepted == 10, f"Expected 10 accepted, got {accepted}"
    assert rejected == 10, f"Expected 10 rejected, got {rejected}"
    assert test_limiter.rejected_count == 10
    print(f"  Burst of 20: accepted={accepted}, rejected={rejected}")
    print(f"  Rejected count tracked: {test_limiter.rejected_count}")


def test_schema_refresh_cooldown():
    """Phase 2: Rapid schema checks are suppressed by cooldown."""
    print("\n=== Test 12: Schema Refresh Cooldown ===")
    vault = "Cyber Security"

    # Build initial index
    build_index(vault)

    # Record initial build time
    meta1 = get_index_metadata(vault)
    initial_build = meta1["last_build_time"]

    # Rapid get_index calls should NOT rebuild (cooldown active)
    for _ in range(5):
        get_index(vault)

    meta2 = get_index_metadata(vault)
    assert meta2["last_build_time"] == initial_build, (
        "Index was rebuilt during cooldown window"
    )
    print(f"  5 rapid get_index calls: no rebuild (cooldown active)")
    print(f"  Cooldown window: {_SCHEMA_COOLDOWN_SECONDS}s")


def test_index_metadata():
    """Phase 6/8: Index metadata is populated with all expected fields."""
    print("\n=== Test 13: Index Metadata ===")
    for v in list_vaults():
        build_index(v)
        meta = get_index_metadata(v)
        assert meta is not None, f"No metadata for {v}"

        for key in ("notes", "schema_hash", "last_build_time",
                     "last_schema_check", "index_size_bytes", "baseline_size_bytes"):
            assert key in meta, f"Missing metadata key {key!r} for {v}"

        assert meta["notes"] > 0
        assert meta["index_size_bytes"] > 0
        assert meta["baseline_size_bytes"] > 0
        print(f"  {v}: notes={meta['notes']}, size={meta['index_size_bytes']} bytes, "
              f"baseline={meta['baseline_size_bytes']} bytes")


def test_config_validation():
    """Phase 5: Config validation catches required functions."""
    print("\n=== Test 14: Config Validation ===")
    for v in list_vaults():
        schema = get_schema(v)
        assert hasattr(schema, "discover_files"), f"Missing discover_files in {v}"
        assert hasattr(schema, "parse_yaml_frontmatter"), f"Missing parse_yaml_frontmatter in {v}"
        assert callable(schema.discover_files)
        assert callable(schema.parse_yaml_frontmatter)
        print(f"  {v}: discover_files ✓, parse_yaml_frontmatter ✓")

    from pathlib import Path
    _SCHEMA_RELATIVE_PATH = Path("Vault Files") / "Scripts" / "vault_schema.py"
    for v in list_vaults():
        vault_path = get_vault_path(v)
        assert vault_path.is_dir(), f"Vault path missing: {vault_path}"
        schema_file = vault_path / _SCHEMA_RELATIVE_PATH
        assert schema_file.is_file(), f"Schema file missing: {schema_file}"
        print(f"  {v}: vault path ✓, schema file ✓")


def test_structured_logging():
    """Phase 7: Structured logging emits key=value format."""
    print("\n=== Test 15: Structured Logging ===")
    from server.mcp_server import _StructuredFormatter
    import logging

    formatter = _StructuredFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="test_event key1=val1 key2=val2", args=(), exc_info=None,
    )
    output = formatter.format(record)
    assert "ts=" in output
    assert "level=INFO" in output
    assert "logger=test" in output
    assert "msg=test_event key1=val1 key2=val2" in output
    print(f"  Formatted: {output}")
    print(f"  Contains ts=, level=, logger=, msg= keys: ✓")


def test_concurrent_build_and_query():
    """Concurrent builds + queries don't crash or produce partial results."""
    print("\n=== Test 16: Concurrent Build + Query ===")
    errors = []

    def builder(vault, i):
        try:
            idx = build_index(vault)
            assert len(idx) > 0, "Empty index from build"
        except Exception as e:
            errors.append(f"Builder {i} ({vault}): {e}")

    def reader(vault, i):
        try:
            result = list_notes(vault, limit=10)
            assert result["status"] == "ok"
            assert result["count"] > 0
        except Exception as e:
            errors.append(f"Reader {i} ({vault}): {e}")

    vaults = list_vaults()
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futures = []
        for i in range(30):
            vault = vaults[i % len(vaults)]
            if i % 3 == 0:
                futures.append(pool.submit(builder, vault, i))
            else:
                futures.append(pool.submit(reader, vault, i))
        concurrent.futures.wait(futures)

    assert not errors, f"Concurrent build+query errors: {errors}"
    print(f"  30 concurrent build+query operations: no errors")


# ============================================================
# Contract & Invariant Tests (Phase 7)
# ============================================================

def test_contract_runner_pass():
    """Test 17: Full contract runner returns PASS on a healthy system."""
    from core.contract_runner import run_all_checks

    result = run_all_checks(include_vault_scripts=False)
    assert result["status"] == "pass", f"Expected pass, got: {result['violations']}"
    assert result["total_violations"] == 0
    assert isinstance(result["vaults"], dict)
    assert len(result["vaults"]) > 0

    # Every vault should pass
    for vault_name, vault_data in result["vaults"].items():
        assert vault_data["status"] == "pass", f"{vault_name}: {vault_data}"

    print(f"  Contract runner: PASS across {len(result['vaults'])} vaults "
          f"({result['duration_ms']:.1f} ms)")


def test_contract_schema_interface():
    """Test 18: Missing schema symbol is detected."""
    from core.system_contract import check_schema_interface, REQUIRED_CONSTANTS
    from core.vault_registry import list_vaults, get_schema

    vault_name = list_vaults()[0]
    schema = get_schema(vault_name)

    # Temporarily remove a required constant
    sentinel = REQUIRED_CONSTANTS[0]
    original = getattr(schema, sentinel, None)
    if original is not None:
        delattr(schema, sentinel)
        try:
            violations = check_schema_interface(vault_name)
            assert any(sentinel in v for v in violations), (
                f"Expected violation for missing {sentinel}, got: {violations}"
            )
            print(f"  Missing schema symbol ({sentinel}) detected correctly")
        finally:
            setattr(schema, sentinel, original)
    else:
        # Should already show as missing
        violations = check_schema_interface(vault_name)
        assert any(sentinel in v for v in violations)
        print(f"  Schema symbol {sentinel} was already missing — violation detected")


def test_contract_index_integrity():
    """Test 19: Index integrity check works on valid index."""
    from core.system_contract import check_index_integrity
    from core.vault_registry import list_vaults

    vault_name = list_vaults()[0]
    violations = check_index_integrity(vault_name)
    assert violations == [], f"Unexpected violations: {violations}"
    print(f"  Index integrity: PASS for {vault_name}")


def test_contract_query_determinism():
    """Test 20: Identical queries produce identical results."""
    from core.system_contract import check_query_determinism
    from core.vault_registry import list_vaults

    vault_name = list_vaults()[0]
    violations = check_query_determinism(vault_name)
    assert violations == [], f"Non-deterministic: {violations}"
    print(f"  Query determinism: PASS for {vault_name}")


def test_contract_lightweight():
    """Test 21: Lightweight recheck runs and passes."""
    from core.contract_runner import run_lightweight_checks

    result = run_lightweight_checks()
    assert result["status"] == "pass", f"Expected pass, got: {result['violations']}"
    assert result["total_violations"] == 0
    print(f"  Lightweight recheck: PASS ({result['duration_ms']:.1f} ms)")


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("MCP SERVER HARDENING — FULL VERIFICATION SUITE")
    print("=" * 60)

    # Original tests
    test_basic_functionality()
    test_deterministic_ordering()
    test_concurrent_queries()
    test_schema_hash_tracking()
    test_pagination_stable()
    test_path_traversal_blocked()
    test_strict_mode()
    test_limit_and_timeout()
    test_typed_responses()
    test_cross_vault_queries()

    # Operational resilience tests
    test_rate_limiter()
    test_schema_refresh_cooldown()
    test_index_metadata()
    test_config_validation()
    test_structured_logging()
    test_concurrent_build_and_query()

    # Contract & invariant tests
    test_contract_runner_pass()
    test_contract_schema_interface()
    test_contract_index_integrity()
    test_contract_query_determinism()
    test_contract_lightweight()

    print()
    print("=" * 60)
    print("ALL 21 VERIFICATION TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
