"""Verification tests for the MCP server hardening — all phases."""

import sys
import tempfile
import time
import threading
import concurrent.futures
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.core.vault_registry import list_vaults, get_vault_path, get_schema
from mcp.core.note_index import (
    build_index, get_index, get_schema_hash,
    get_index_metadata, _SCHEMA_COOLDOWN_SECONDS,
    _indices, _get_vault_lock,
)
from mcp.core.query_engine import query, list_notes, get_note, aggregate


# ============================================================
# Original hardening tests (preserved)
# ============================================================

def test_basic_functionality():
    """Sanity check: all vaults load and index correctly."""
    print("=== Test 1: Basic Functionality ===")
    vaults = list_vaults()
    assert len(vaults) > 0, "No vaults configured"
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
    vault = list_vaults()[0]
    attacks = [
        "../../../etc/passwd",
        "..\\..\\..\\Windows\\System32\\config\\SAM",
        "subdir/../../outside.md",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ]
    for path in attacks:
        result = get_note(vault, path)
        assert result["status"] == "error", f"Should block: {path}"
        assert result["error"]["code"] == "PATH_TRAVERSAL", f"Wrong code for: {path}"
        print(f"  Blocked: {path}")


def test_strict_mode():
    """Both strict and non-strict modes now reject unknown fields (Phase 0 fix).

    Pre-fix: non-strict silently ignored unknown fields and returned all notes.
    Post-fix: all modes return a structured INVALID_FILTER error with zero results.
    The `strict` parameter is preserved for backwards compatibility.
    """
    print("\n=== Test 7: Strict Mode / Filter Validation ===")
    vault = list_vaults()[0]

    # Non-strict must also reject unknown fields (Phase 0 correctness fix)
    result = query(vault, {"fake_field": "value"}, strict=False)
    assert result["status"] == "error", "Non-strict must reject unknown fields"
    assert result["error"] == "INVALID_FILTER", f"Wrong error code: {result['error']}"
    assert result["results"] == [], "Must return empty results on error"
    assert len(result["details"]) > 0, "Must include details"
    print(f"  Non-strict with unknown field: correctly rejected (INVALID_FILTER)")

    result = query(vault, {"fake_field": "value"}, strict=True)
    assert result["status"] == "error", "Strict must reject unknown fields"
    assert result["error"] == "INVALID_FILTER", f"Wrong error code: {result['error']}"
    assert result["results"] == [], "Must return empty results on error"
    assert len(result["details"]) > 0, "Must include details"
    print(f"  Strict with unknown field: correctly rejected (INVALID_FILTER)")


def test_limit_and_timeout():
    """Large queries respect limit; max limit is clamped."""
    print("\n=== Test 8: Limit + Timeout ===")
    vault = list_vaults()[0]

    result = query(vault, {}, limit=5)
    assert result["returned"] <= 5, f"Returned {result['returned']} > limit 5"
    assert result["limit"] == 5
    print(f"  {vault}: {result['count']} total, {result['returned']} returned (limit=5)")

    result = query(vault, {}, limit=9999)
    assert result["limit"] == 500, f"Limit not clamped: {result['limit']}"
    print(f"  Limit clamped to 500: ok")


def test_typed_responses():
    """All responses follow the typed contract."""
    print("\n=== Test 9: Typed Response Contract ===")
    vault = list_vaults()[0]

    result = list_notes(vault, limit=1)
    assert result["status"] == "ok"
    for key in ("count", "returned", "offset", "limit", "results"):
        assert key in result, f"Missing key: {key}"
    print(f"  list_notes: ok, has pagination keys")

    first_path = result["results"][0]["path"]
    result = get_note(vault, first_path)
    assert result["status"] == "ok"
    assert "data" in result
    print(f"  get_note: ok, has data")

    result = aggregate(vault, "type")
    assert result["status"] == "ok"
    assert "data" in result
    print(f"  aggregate: ok, has data")

    result = get_note(vault, "../escape")
    assert result["status"] == "error"
    assert "error" in result
    assert "code" in result["error"]
    assert "message" in result["error"]
    print(f"  error response: has code + message")


def test_cross_vault_queries():
    """Aggregate works with typed response format across all vaults."""
    print("\n=== Test 10: Vault Queries ===")
    vault = list_vaults()[0]
    for v in list_vaults():
        result = aggregate(v, "type")
        assert result["status"] == "ok"
        print(f"  {v} type distribution: {result['data']['stats']}")

    result = aggregate(vault, "nonexistent")
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
    vault = list_vaults()[0]

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
    from mcp.core.contract_runner import run_all_checks

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
    from mcp.core.system_contract import check_schema_interface, REQUIRED_CONSTANTS
    from mcp.core.vault_registry import list_vaults, get_schema

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
    from mcp.core.system_contract import check_index_integrity
    from mcp.core.vault_registry import list_vaults

    vault_name = list_vaults()[0]
    violations = check_index_integrity(vault_name)
    assert violations == [], f"Unexpected violations: {violations}"
    print(f"  Index integrity: PASS for {vault_name}")


def test_contract_query_determinism():
    """Test 20: Identical queries produce identical results."""
    from mcp.core.system_contract import check_query_determinism
    from mcp.core.vault_registry import list_vaults

    vault_name = list_vaults()[0]
    violations = check_query_determinism(vault_name)
    assert violations == [], f"Non-deterministic: {violations}"
    print(f"  Query determinism: PASS for {vault_name}")


def test_contract_lightweight():
    """Test 21: Lightweight recheck runs and passes."""
    from mcp.core.contract_runner import run_lightweight_checks

    result = run_lightweight_checks()
    assert result["status"] == "pass", f"Expected pass, got: {result['violations']}"
    assert result["total_violations"] == 0
    print(f"  Lightweight recheck: PASS ({result['duration_ms']:.1f} ms)")


# ============================================================
# Phase 0 — Query Filter Safety Tests
# ============================================================

def test_unknown_field_returns_error():
    """P0-Q1: Unknown filter field returns structured INVALID_FILTER error."""
    print("\n=== Test P0-Q1: Unknown Field Returns Error ===")
    vault = list_vaults()[0]

    result = query(vault, {"nonexistent_field": "value"})
    assert result["status"] == "error", "Unknown field must return error"
    assert result["error"] == "INVALID_FILTER"
    assert isinstance(result["details"], list)
    assert len(result["details"]) > 0
    assert result["results"] == []
    detail = result["details"][0]
    assert "filter" in detail and "reason" in detail
    print(f"  Unknown field: INVALID_FILTER returned, details={result['details']}")


def test_unknown_field_does_not_return_all_notes():
    """P0-Q2: A query using only unknown fields must NOT return all notes."""
    print("\n=== Test P0-Q2: Unknown Field Does Not Return All Notes ===")
    vault = list_vaults()[0]

    # Build index to have notes available
    build_index(vault)
    total_notes = list_notes(vault)["count"]
    assert total_notes > 0, "Vault must have notes for this test"

    result = query(vault, {"totally_fake": "anything"})
    assert result["status"] == "error", "Must return error, not results"
    assert result["results"] == [], "Must return empty results, not all notes"
    # Explicitly verify it is NOT the full note list
    assert len(result["results"]) != total_notes
    print(f"  Total notes: {total_notes}, result.results: [] — correctly NOT returning all notes")


def test_malformed_in_returns_error():
    """P0-Q3: __in operator with a string value returns INVALID_FILTER error."""
    print("\n=== Test P0-Q3: Malformed __in Returns Error ===")
    vault = list_vaults()[0]

    # status__in with a string (should be a list)
    result = query(vault, {"status__in": "complete"})
    assert result["status"] == "error", "__in with string must return error"
    assert result["error"] == "INVALID_FILTER"
    assert result["results"] == []
    assert any("__in" in d["filter"] for d in result["details"])
    print(f"  status__in='complete' (string): INVALID_FILTER — {result['details']}")

    # Also verify a dict value fails
    result = query(vault, {"status__in": {"a": "b"}})
    assert result["status"] == "error"
    assert result["error"] == "INVALID_FILTER"
    print(f"  status__in={{dict}}: INVALID_FILTER — {result['details']}")


def test_unsupported_operator_returns_error():
    """P0-Q4: Unsupported operator (e.g. __gt) returns INVALID_FILTER error."""
    print("\n=== Test P0-Q4: Unsupported Operator Returns Error ===")
    vault = list_vaults()[0]

    result = query(vault, {"difficulty__gt": "basic"})
    assert result["status"] == "error", "__gt is unsupported, must return error"
    assert result["error"] == "INVALID_FILTER"
    assert result["results"] == []
    print(f"  difficulty__gt: INVALID_FILTER — {result['details']}")

    result = query(vault, {"status__lt": "complete"})
    assert result["status"] == "error"
    assert result["error"] == "INVALID_FILTER"
    print(f"  status__lt: INVALID_FILTER — {result['details']}")


def test_valid_equality_query():
    """P0-Q5: Valid equality filter returns matching notes."""
    print("\n=== Test P0-Q5: Valid Equality Query ===")
    vault = list_vaults()[0]
    build_index(vault)

    result = query(vault, {"type": "core-concept"})
    assert result["status"] == "ok", f"Valid equality query failed: {result}"
    assert result["count"] > 0, "Expected at least one core-concept note"
    assert all(n["fields"].get("type") == "core-concept" for n in result["results"])
    print(f"  type=core-concept: {result['count']} results returned")

    # Non-matching equality should return zero
    result = query(vault, {"type": "nonexistent-type-xyz"})
    assert result["status"] == "ok"
    assert result["count"] == 0
    print(f"  type=nonexistent-type-xyz: 0 results (correct)")


def test_valid_in_query():
    """P0-Q6: Valid __in filter with a list value returns matching notes."""
    print("\n=== Test P0-Q6: Valid __in Query ===")
    vault = list_vaults()[0]
    build_index(vault)

    result = query(vault, {"type__in": ["core-concept"]})
    assert result["status"] == "ok", f"Valid __in query failed: {result}"
    assert result["count"] > 0, "Expected results for type__in=['core-concept']"
    assert all(n["fields"].get("type") in ["core-concept"] for n in result["results"])
    print(f"  type__in=['core-concept']: {result['count']} results returned")

    # Empty list should match nothing
    result = query(vault, {"type__in": []})
    assert result["status"] == "ok"
    assert result["count"] == 0
    print(f"  type__in=[]: 0 results (correct)")


def test_valid_contains_query():
    """P0-Q7: Valid __contains filter returns matching notes."""
    print("\n=== Test P0-Q7: Valid __contains Query ===")
    vault = list_vaults()[0]
    build_index(vault)

    # 'core' is a substring of 'core-concept'
    result = query(vault, {"type__contains": "core"})
    assert result["status"] == "ok", f"Valid __contains query failed: {result}"
    # All results should have 'core' in their type field
    for note in result["results"]:
        assert "core" in (note["fields"].get("type") or ""), \
            f"Note {note['path']} does not match __contains filter"
    print(f"  type__contains='core': {result['count']} results returned")


def test_pagination_preserved_after_fix():
    """P0-Q8: Pagination still works correctly after query safety fixes."""
    print("\n=== Test P0-Q8: Pagination Preserved ===")
    vault = list_vaults()[0]
    build_index(vault)

    full = query(vault, {"type": "core-concept"}, limit=500)
    total = full["count"]
    assert full["status"] == "ok"

    page1 = query(vault, {"type": "core-concept"}, limit=3, offset=0)
    page2 = query(vault, {"type": "core-concept"}, limit=3, offset=3)

    assert page1["status"] == "ok"
    assert page1["returned"] == min(3, total)
    assert page1["offset"] == 0
    assert page1["limit"] == 3

    paths1 = {n["path"] for n in page1["results"]}
    paths2 = {n["path"] for n in page2["results"]}
    assert not paths1 & paths2, "Pages must not overlap"

    print(f"  total={total}, page1={page1['returned']}, page2={page2['returned']}, no overlap")


# ============================================================
# Phase 0 — Index Freshness Tests
# ============================================================

def _expire_cooldown(vault_name: str) -> None:
    """Force the index cooldown to expire so get_index() will re-check content."""
    lock = _get_vault_lock(vault_name)
    with lock:
        if vault_name in _indices:
            _indices[vault_name]["last_schema_check"] = 0.0


def test_note_edit_reflected_in_index():
    """P0-I1: Editing a note's frontmatter is reflected in get_index() after cooldown."""
    print("\n=== Test P0-I1: Note Edit Reflected in Index ===")
    vault = list_vaults()[0]
    vault_path = get_vault_path(vault)

    # Find a real indexed note to edit
    build_index(vault)
    idx = get_index(vault)
    assert len(idx) > 0
    target = idx[0]
    target_path = vault_path / target["path"]

    # Read current content
    original_content = target_path.read_text(encoding="utf-8")
    # Append a harmless comment to the body to change mtime/size
    modified_content = original_content.rstrip("\n") + "\n<!-- test-edit-marker -->\n"

    try:
        target_path.write_text(modified_content, encoding="utf-8")

        # Expire the cooldown so get_index() will detect the change
        _expire_cooldown(vault)

        # get_index() should detect changed mtime and rebuild
        new_idx = get_index(vault)
        target_note = next((n for n in new_idx if n["path"] == target["path"]), None)
        assert target_note is not None, "Edited note should still be in index"
        assert "test-edit-marker" in target_note["body"], \
            "Edited note body must be reflected in refreshed index"
        print(f"  Edited {target['path']}: body change detected and indexed")
    finally:
        # Restore original content
        target_path.write_text(original_content, encoding="utf-8")
        _expire_cooldown(vault)
        build_index(vault)


def test_note_add_reflected_in_index():
    """P0-I2: A new note added to the vault is reflected in get_index() after cooldown."""
    print("\n=== Test P0-I2: Note Add Reflected in Index ===")
    vault = list_vaults()[0]
    vault_path = get_vault_path(vault)

    build_index(vault)
    before_count = len(get_index(vault))

    # Write a minimal valid-looking note in the indexed area
    new_note_path = vault_path / "Fundamentals" / "_test_temp_note.md"
    new_content = (
        "---\n"
        "type: core-concept\n"
        "domain: fundamentals\n"
        "status: partial\n"
        "has_key_principles: false\n"
        "has_how_it_works: false\n"
        "has_tradeoffs: false\n"
        "difficulty: intermediate\n"
        "---\n\n"
        "Temporary test note for index freshness test.\n"
    )

    try:
        new_note_path.write_text(new_content, encoding="utf-8")

        _expire_cooldown(vault)
        new_idx = get_index(vault)
        after_count = len(new_idx)

        assert after_count == before_count + 1, \
            f"Expected {before_count + 1} notes after add, got {after_count}"
        paths = [n["path"] for n in new_idx]
        assert any("_test_temp_note" in p for p in paths), \
            "New note must appear in refreshed index"
        print(f"  Notes before: {before_count}, after add+refresh: {after_count} (+1 correct)")
    finally:
        if new_note_path.exists():
            new_note_path.unlink()
        _expire_cooldown(vault)
        build_index(vault)


def test_note_delete_reflected_in_index():
    """P0-I3: A deleted note is removed from get_index() after cooldown."""
    print("\n=== Test P0-I3: Note Delete Reflected in Index ===")
    vault = list_vaults()[0]
    vault_path = get_vault_path(vault)

    # Create a temp note first
    new_note_path = vault_path / "Fundamentals" / "_test_temp_del.md"
    new_content = (
        "---\n"
        "type: core-concept\n"
        "domain: fundamentals\n"
        "status: partial\n"
        "has_key_principles: false\n"
        "has_how_it_works: false\n"
        "has_tradeoffs: false\n"
        "difficulty: intermediate\n"
        "---\n\n"
        "Temporary test note for deletion test.\n"
    )
    new_note_path.write_text(new_content, encoding="utf-8")
    _expire_cooldown(vault)
    idx_with = get_index(vault)
    assert any("_test_temp_del" in n["path"] for n in idx_with), \
        "Temp note should appear after add"
    count_with = len(idx_with)

    # Now delete it
    new_note_path.unlink()
    _expire_cooldown(vault)
    idx_without = get_index(vault)
    count_without = len(idx_without)

    assert count_without == count_with - 1, \
        f"Expected {count_with - 1} notes after delete, got {count_without}"
    assert not any("_test_temp_del" in n["path"] for n in idx_without), \
        "Deleted note must not appear in refreshed index"
    print(f"  Notes with temp: {count_with}, after delete+refresh: {count_without} (-1 correct)")

    # Cleanup (rebuild to stable state)
    _expire_cooldown(vault)
    build_index(vault)


def test_get_note_reflects_edit():
    """P0-I4: get_note() returns updated body after a note edit and index refresh."""
    print("\n=== Test P0-I4: get_note() Reflects Edit ===")
    vault = list_vaults()[0]
    vault_path = get_vault_path(vault)

    build_index(vault)
    idx = get_index(vault)
    target = idx[0]
    target_path = vault_path / target["path"]

    original_content = target_path.read_text(encoding="utf-8")
    modified_content = original_content.rstrip("\n") + "\n<!-- get_note_test_marker -->\n"

    try:
        target_path.write_text(modified_content, encoding="utf-8")
        _expire_cooldown(vault)

        result = get_note(vault, target["path"])
        assert result["status"] == "ok", f"get_note failed: {result}"
        assert "get_note_test_marker" in result["data"]["body"], \
            "get_note must return updated body after index refresh"
        print(f"  get_note({target['path']}): edited body reflected after refresh")
    finally:
        target_path.write_text(original_content, encoding="utf-8")
        _expire_cooldown(vault)
        build_index(vault)


def test_query_reflects_frontmatter_edit():
    """P0-I5: POST /query reflects edited frontmatter after index refresh."""
    print("\n=== Test P0-I5: query() Reflects Frontmatter Edit ===")
    vault = list_vaults()[0]
    vault_path = get_vault_path(vault)

    build_index(vault)
    idx = get_index(vault)
    # Find a note with status=complete to edit
    target = next((n for n in idx if n["fields"].get("status") == "complete"), None)
    if target is None:
        print("  SKIP: no note with status=complete found")
        return

    target_path = vault_path / target["path"]
    original_content = target_path.read_text(encoding="utf-8")

    # Change status: complete -> partial in frontmatter
    modified_content = original_content.replace(
        "status: complete", "status: partial", 1
    )
    assert modified_content != original_content, "Content must change"

    try:
        target_path.write_text(modified_content, encoding="utf-8")
        _expire_cooldown(vault)

        # After refresh, query for status=partial should include this note
        result = query(vault, {"status": "partial"})
        assert result["status"] == "ok"
        paths = [n["path"] for n in result["results"]]
        assert target["path"] in paths, \
            f"Edited note ({target['path']}) must appear in query after frontmatter change"
        print(f"  Edited {target['path']} status: complete→partial, query reflects change")
    finally:
        target_path.write_text(original_content, encoding="utf-8")
        _expire_cooldown(vault)
        build_index(vault)


def test_schema_hash_rebuild_still_works():
    """P0-I6: Schema hash change still triggers a rebuild (existing behaviour preserved)."""
    print("\n=== Test P0-I6: Schema Hash Rebuild Still Works ===")
    vault = list_vaults()[0]
    vault_path = get_vault_path(vault)
    schema_file = vault_path / "Vault Files" / "Scripts" / "vault_schema.py"

    build_index(vault)
    meta_before = get_index_metadata(vault)
    build_time_before = meta_before["last_build_time"]

    # Append a harmless comment to the schema file to change its hash
    original_schema = schema_file.read_text(encoding="utf-8")
    modified_schema = original_schema + "\n# test-schema-change-marker\n"

    try:
        schema_file.write_text(modified_schema, encoding="utf-8")
        _expire_cooldown(vault)

        get_index(vault)  # Should detect schema change and rebuild
        meta_after = get_index_metadata(vault)
        assert meta_after["last_build_time"] > build_time_before, \
            "Index must be rebuilt when schema changes"
        print(f"  Schema change detected, index rebuilt (build_time advanced)")
    finally:
        schema_file.write_text(original_schema, encoding="utf-8")
        _expire_cooldown(vault)
        build_index(vault)


def test_deterministic_ordering_after_rebuild():
    """P0-I7: Deterministic ordering is preserved after a note edit + rebuild."""
    print("\n=== Test P0-I7: Deterministic Ordering After Rebuild ===")
    vault = list_vaults()[0]
    vault_path = get_vault_path(vault)

    build_index(vault)
    idx = get_index(vault)
    target = idx[0]
    target_path = vault_path / target["path"]
    original_content = target_path.read_text(encoding="utf-8")
    modified_content = original_content.rstrip("\n") + "\n<!-- ordering_test -->\n"

    try:
        target_path.write_text(modified_content, encoding="utf-8")
        _expire_cooldown(vault)

        new_idx = get_index(vault)
        paths = [n["path"] for n in new_idx]
        assert paths == sorted(paths, key=str.lower), \
            "Index must remain sorted case-insensitively after rebuild"
        print(f"  {len(paths)} notes, sorted correctly after rebuild")
    finally:
        target_path.write_text(original_content, encoding="utf-8")
        _expire_cooldown(vault)
        build_index(vault)


# ============================================================
# Phase 0 — inject_frontmatter Fix Test
# ============================================================

def test_inject_frontmatter_domain_validation():
    """P0-F1: validate_metadata uses schema.VALID_DOMAINS, not schema.schema.VALID_DOMAINS."""
    print("\n=== Test P0-F1: inject_frontmatter Domain Validation ===")
    from core.shared.inject_frontmatter import validate_metadata
    vault = list_vaults()[0]
    schema = get_schema(vault)
    vault_path = get_vault_path(vault)

    # Build a minimal metadata dict with a valid domain
    valid_domain = next(iter(schema.VALID_DOMAINS))
    metadata = {
        "type": "core-concept",
        "domain": valid_domain,
        "subdomain": None,
        "status": "partial",
        "difficulty": "intermediate",
        "has_key_principles": False,
        "has_how_it_works": False,
        "has_tradeoffs": False,
    }

    # path_parts: [domain_dir, filename]
    domain_dir = next(iter(schema.DOMAIN_MAP.keys()))
    path_parts = [domain_dir, "Test Note.md"]
    content = ""  # empty body

    errors = validate_metadata(metadata, path_parts, content, "Test Note.md", schema)
    domain_errors = [e for e in errors if "V-02" in e]
    assert len(domain_errors) == 0, \
        f"Valid domain '{valid_domain}' must not produce V-02 errors; got: {domain_errors}"
    print(f"  Valid domain '{valid_domain}': no V-02 error (schema.VALID_DOMAINS accessed correctly)")

    # Also verify an invalid domain IS caught
    metadata_bad = {**metadata, "domain": "invalid-domain-xyz"}
    errors_bad = validate_metadata(metadata_bad, path_parts, content, "Test Note.md", schema)
    v02_errors = [e for e in errors_bad if "V-02" in e]
    assert len(v02_errors) > 0, "Invalid domain must produce V-02 error"
    print(f"  Invalid domain: V-02 error raised correctly — {v02_errors}")


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

    # Phase 0 — Query filter safety regression tests
    test_unknown_field_returns_error()
    test_unknown_field_does_not_return_all_notes()
    test_malformed_in_returns_error()
    test_unsupported_operator_returns_error()
    test_valid_equality_query()
    test_valid_in_query()
    test_valid_contains_query()
    test_pagination_preserved_after_fix()

    # Phase 0 — Index freshness regression tests
    test_note_edit_reflected_in_index()
    test_note_add_reflected_in_index()
    test_note_delete_reflected_in_index()
    test_get_note_reflects_edit()
    test_query_reflects_frontmatter_edit()
    test_schema_hash_rebuild_still_works()
    test_deterministic_ordering_after_rebuild()

    # Phase 0 — inject_frontmatter fix test
    test_inject_frontmatter_domain_validation()

    print()
    print("=" * 60)
    print("ALL VERIFICATION TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
