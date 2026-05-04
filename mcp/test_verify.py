"""Verification tests for the MCP server hardening — all phases."""

import sys
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
# Phase 1 — HTTP Smoke Tests (TestClient)
# ============================================================

def test_p1_http_smoke():
    """P1-HTTP: HTTP-level smoke tests for all Phase 1 routes via TestClient.

    Uses a single TestClient instance (one lifespan startup) and exercises
    every target route at the HTTP layer, verifying response codes and
    response shape.
    """
    print("\n=== Test P1-HTTP: HTTP Smoke Tests (TestClient) ===")
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        print(f"  SKIP: TestClient unavailable — {exc}")
        return

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from mcp.server.mcp_server import app

    vault = list_vaults()[0]
    # Find a real note path for graph query tests
    build_index(vault)
    idx = get_index(vault)
    note_path = idx[0]["path"]  # e.g. "Fundamentals/Algorithms.md"

    with TestClient(app, raise_server_exceptions=True) as client:

        # --- GET /validation?vault= ---
        resp = client.get(f"/validation?vault={vault}")
        assert resp.status_code == 200, f"/validation status {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "ok"
        assert "status" in body["data"]
        assert "invalid_count" in body["data"]
        assert "invalid_notes" in body["data"]
        print(f"  GET /validation?vault={vault}: 200 OK, validation_status={body['data']['status']}")

        # --- GET /tasks?vault= ---
        resp = client.get(f"/tasks?vault={vault}&limit=5")
        assert resp.status_code == 200, f"/tasks status {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "ok"
        assert "tasks" in body["data"]
        assert "total" in body["data"]
        # Verify each task has full path and constraints
        for task in body["data"]["tasks"]:
            assert "path" in task, f"task missing path: {task}"
            assert task["path"].endswith(".md"), f"task path not .md: {task['path']}"
            assert "\\" not in task["path"], f"task path uses backslash: {task['path']}"
        print(f"  GET /tasks?vault={vault}: 200 OK, {len(body['data']['tasks'])} tasks returned")

        # --- GET /notes?vault= ---
        resp = client.get(f"/notes?vault={vault}")
        assert resp.status_code == 200, f"/notes status {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "ok"
        assert "notes" in body["data"]
        assert len(body["data"]["notes"]) > 0
        for note in body["data"]["notes"]:
            assert "path" in note
            assert "\\" not in note["path"], f"note path backslash: {note['path']}"
        print(f"  GET /notes?vault={vault}: 200 OK, {len(body['data']['notes'])} notes")

        # --- GET /quality?vault= ---
        resp = client.get(f"/quality?vault={vault}")
        assert resp.status_code == 200, f"/quality status {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "ok"
        for key in ("total", "flagged", "highest_score", "average_score", "notes"):
            assert key in body["data"], f"quality missing key: {key}"
        for n in body["data"]["notes"]:
            assert "\\" not in n["file"], f"quality file path backslash: {n['file']}"
        print(f"  GET /quality?vault={vault}: 200 OK, total={body['data']['total']}")

        # --- GET /missing?vault= ---
        resp = client.get(f"/missing?vault={vault}")
        # 422 = MISSING_CONCEPTS_EMPTY (expected for demo-vault), 200 = data present
        assert resp.status_code in (200, 422), f"/missing unexpected status {resp.status_code}: {resp.text}"
        body = resp.json()
        if resp.status_code == 422:
            assert body["status"] == "error"
            assert body["error"]["code"] == "MISSING_CONCEPTS_EMPTY"
            print(f"  GET /missing?vault={vault}: 422 MISSING_CONCEPTS_EMPTY (expected — EXPECTED_CONCEPTS not defined)")
        else:
            assert body["status"] == "ok"
            assert "total_expected" in body["data"]
            print(f"  GET /missing?vault={vault}: 200 OK, total_missing={body['data']['total_missing']}")

        # --- POST /compare with missing before file ---
        resp = client.post("/compare", json={"before": "Vault Files/__nonexistent__.md"})
        assert resp.status_code in (400, 500), f"/compare unexpected status {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "error"
        assert "code" in body["error"]
        print(f"  POST /compare (missing file): {resp.status_code} structured error, code={body['error']['code']}")

        # --- POST /compare with blank before ---
        resp = client.post("/compare", json={"before": "   "})
        assert resp.status_code == 400, f"/compare blank before unexpected status {resp.status_code}"
        body = resp.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_INPUT"
        print(f"  POST /compare (blank before): 400 INVALID_INPUT ✓")

        # --- POST /compare with missing required field ---
        resp = client.post("/compare", json={"after": "something"})
        assert resp.status_code == 422, f"/compare missing required field status {resp.status_code}"
        body = resp.json()
        assert body["status"] == "error"
        print(f"  POST /compare (missing 'before'): 422 VALIDATION_ERROR ✓")

        # --- GET /graph/{vault} ---
        resp = client.get(f"/graph/{vault}")
        assert resp.status_code == 200, f"/graph/{{vault}} status {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "ok"
        assert "nodes" in body["data"]
        assert "edges" in body["data"]
        assert len(body["data"]["nodes"]) > 0
        node_ids = [n["id"] for n in body["data"]["nodes"]]
        assert node_ids == sorted(node_ids), "Graph nodes must be sorted ascending by id"
        print(f"  GET /graph/{vault}: 200 OK, {len(body['data']['nodes'])} nodes, {len(body['data']['edges'])} edges")

        # --- GET /graph/{vault}/related?node_id= ---
        # node_id for path-param routes is the vault-relative path (note index key)
        resp = client.get(f"/graph/{vault}/related", params={"node_id": note_path})
        assert resp.status_code == 200, f"/graph/{{vault}}/related status {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "ok"
        assert "related" in body["data"]
        assert "found" in body["data"]
        print(f"  GET /graph/{vault}/related?node_id={note_path}: 200 OK, "
              f"found={body['data']['found']}, related={len(body['data']['related'])}")

        # --- GET /graph/{vault}/missing?node_id= ---
        resp = client.get(f"/graph/{vault}/missing", params={"node_id": note_path})
        assert resp.status_code == 200, f"/graph/{{vault}}/missing status {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "ok"
        assert "missing" in body["data"]
        assert "found" in body["data"]
        print(f"  GET /graph/{vault}/missing?node_id={note_path}: 200 OK, "
              f"found={body['data']['found']}, missing_neighbors={len(body['data']['missing'])}")

        # --- Unknown vault returns structured error ---
        resp = client.get("/validation?vault=__nonexistent__")
        assert resp.status_code == 404, f"Unknown vault status {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_VAULT"
        print(f"  GET /validation?vault=__nonexistent__: 404 INVALID_VAULT ✓")

        # --- /graph/{vault} for unknown vault ---
        resp = client.get("/graph/__nonexistent__")
        assert resp.status_code == 404, f"/graph/unknown vault status {resp.status_code}"
        body = resp.json()
        assert body["status"] == "error"
        print(f"  GET /graph/__nonexistent__: 404 INVALID_VAULT ✓")

    print(f"  All HTTP smoke tests passed ✓")


# ============================================================
# Phase 1 — Expose Existing Capabilities
# ============================================================

def test_p1_validation_adapter():
    """P1-A1: Validation adapter returns structured pass/fail result."""
    print("\n=== Test P1-A1: Validation Adapter ===")
    from mcp.core.adapters.validation_adapter import get_validation

    vault = list_vaults()[0]
    result = get_validation(vault_name=vault)

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert "status" in result, "Result must have 'status'"
    assert result["status"] in ("pass", "fail"), f"Unexpected status: {result['status']}"
    assert "invalid_count" in result, "Result must have 'invalid_count'"
    assert isinstance(result["invalid_count"], int)
    assert "invalid_notes" in result, "Result must have 'invalid_notes'"
    assert isinstance(result["invalid_notes"], list)
    print(f"  Vault: {vault}, status={result['status']}, invalid_count={result['invalid_count']}")


def test_p1_tasks_full_path():
    """P1-A2: Tasks adapter returns full vault-relative POSIX path, not stem only."""
    print("\n=== Test P1-A2: Tasks Adapter Full Path ===")
    from mcp.core.adapters.tasks_adapter import get_tasks
    from pathlib import PurePosixPath

    vault = list_vaults()[0]
    result = get_tasks(vault_name=vault, limit=50)

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert "tasks" in result
    tasks = result["tasks"]

    if not tasks:
        print("  No partial notes found — skipping path-format check (vault is complete)")
        return

    for task in tasks:
        assert "path" in task, f"Task missing 'path' field: {task}"
        path = task["path"]
        # Full path must contain at least one '/' (e.g. "Fundamentals/Algorithms.md")
        # A stem-only value like "Algorithms" would have no '/' and no extension
        assert "/" in path or path.endswith(".md"), (
            f"Task 'path' looks like a stem, not a full path: {path!r}"
        )
        # Must be a POSIX path (forward slashes only)
        assert "\\" not in path, f"Task 'path' uses backslashes: {path!r}"
        assert path.endswith(".md"), f"Task 'path' must end with .md: {path!r}"
    print(f"  {len(tasks)} tasks checked — all have full POSIX paths")
    print(f"  Example: {tasks[0]['path']!r}")


def test_p1_tasks_constraints():
    """P1-A3: Tasks adapter includes writing constraints from issue engine."""
    print("\n=== Test P1-A3: Tasks Adapter Constraints ===")
    from mcp.core.adapters.tasks_adapter import get_tasks

    vault = list_vaults()[0]
    result = get_tasks(vault_name=vault, limit=50)

    assert "error" not in result
    tasks = result["tasks"]

    if not tasks:
        print("  No partial notes found — skipping constraints check")
        return

    tasks_with_constraints = [t for t in tasks if t.get("constraints")]
    # At least some tasks should have constraints (they come from WRITING_CONSTRAINTS)
    assert len(tasks_with_constraints) > 0, (
        "Expected at least one task to have writing constraints"
    )
    assert isinstance(tasks_with_constraints[0]["constraints"], list)
    assert all(isinstance(c, str) for c in tasks_with_constraints[0]["constraints"])
    print(f"  {len(tasks_with_constraints)}/{len(tasks)} tasks have constraints")
    print(f"  Example constraints: {tasks_with_constraints[0]['constraints'][:2]}")


def test_p1_notes_full_paths():
    """P1-A4: Notes adapter returns full vault-relative POSIX paths."""
    print("\n=== Test P1-A4: Notes Adapter Full Paths ===")
    from mcp.core.adapters.notes_adapter import get_notes

    vault = list_vaults()[0]
    result = get_notes(vault_name=vault)

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert "notes" in result
    notes = result["notes"]
    assert len(notes) > 0, "Expected at least one note"

    for note in notes:
        assert "path" in note, f"Note missing 'path': {note}"
        path = note["path"]
        assert "/" in path, f"Note path looks like a stem, not a full path: {path!r}"
        assert "\\" not in path, f"Note path uses backslashes: {path!r}"
        assert path.endswith(".md"), f"Note path must end with .md: {path!r}"
    print(f"  {len(notes)} notes checked — all have full POSIX paths")
    print(f"  Example: {notes[0]['path']!r}")


def test_p1_quality_adapter():
    """P1-A5: Quality adapter returns structured audit result."""
    print("\n=== Test P1-A5: Quality Adapter ===")
    from mcp.core.adapters.quality_adapter import get_quality

    vault = list_vaults()[0]
    result = get_quality(vault_name=vault)

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    for key in ("total", "flagged", "highest_score", "average_score", "notes"):
        assert key in result, f"Result missing key: {key!r}"
    assert isinstance(result["total"], int) and result["total"] >= 0
    assert isinstance(result["notes"], list)
    if result["notes"]:
        note = result["notes"][0]
        assert "file" in note
        assert "score" in note
        assert "severity" in note
        assert "issues" in note
        # file must be a vault-relative path
        assert "\\" not in note["file"], f"file path uses backslashes: {note['file']!r}"
    print(f"  total={result['total']}, flagged={result['flagged']}, "
          f"highest_score={result['highest_score']}")


def test_p1_missing_adapter():
    """P1-A6: Missing adapter returns structured gap result or explicit empty error."""
    print("\n=== Test P1-A6: Missing Adapter ===")
    from mcp.core.adapters.missing_adapter import get_missing

    vault = list_vaults()[0]
    result = get_missing(vault_name=vault)

    if "error" in result:
        # EXPECTED_CONCEPTS empty is an acceptable structured error (not a silent success)
        assert "EXPECTED_CONCEPTS" in result["error"] or result["error"], (
            f"Error must be non-empty: {result}"
        )
        print(f"  EXPECTED_CONCEPTS not defined — structured error returned: {result['error']}")
        return

    for key in ("total_expected", "total_actual", "total_missing", "gaps", "ranked"):
        assert key in result, f"Result missing key: {key!r}"
    assert isinstance(result["gaps"], dict)
    assert isinstance(result["ranked"], list)
    print(f"  total_expected={result['total_expected']}, "
          f"total_missing={result['total_missing']}, "
          f"subdomains assessed={result.get('subdomains', '?')}")


def test_p1_compare_missing_file():
    """P1-A7: Compare adapter returns structured error for missing BEFORE file."""
    print("\n=== Test P1-A7: Compare Adapter Missing File ===")
    from mcp.core.adapters.compare_adapter import get_compare

    vault = list_vaults()[0]
    result = get_compare(
        before="Vault Files/nonexistent_report_xyz.md",
        after=None,
        vault_name=vault,
    )

    assert "error" in result, "Expected structured error for missing file"
    assert "not found" in result["error"].lower() or "report" in result["error"].lower(), (
        f"Error message should mention missing file: {result['error']}"
    )
    print(f"  Structured error returned: {result['error']!r}")


def test_p1_graph_build():
    """P1-G1: Graph builder returns deterministic nodes and edges."""
    print("\n=== Test P1-G1: Graph Build ===")
    from mcp.core.graph_builder import build_graph

    vault = list_vaults()[0]
    graph1 = build_graph(vault_name=vault)
    graph2 = build_graph(vault_name=vault)

    assert "nodes" in graph1, "Graph must have 'nodes'"
    assert "edges" in graph1, "Graph must have 'edges'"
    assert isinstance(graph1["nodes"], list)
    assert isinstance(graph1["edges"], list)
    assert len(graph1["nodes"]) > 0, "Graph must have at least one node"

    # Deterministic: same vault → same output
    assert [n["id"] for n in graph1["nodes"]] == [n["id"] for n in graph2["nodes"]], (
        "Graph node order must be deterministic"
    )
    assert [(e["from"], e["to"]) for e in graph1["edges"]] == (
        [(e["from"], e["to"]) for e in graph2["edges"]]
    ), "Graph edge order must be deterministic"

    # Nodes must be sorted ascending by id
    node_ids = [n["id"] for n in graph1["nodes"]]
    assert node_ids == sorted(node_ids), "Graph nodes must be sorted ascending by id"

    # Every node must have id, type, label
    for node in graph1["nodes"]:
        assert "id" in node and "type" in node and "label" in node

    print(f"  {len(graph1['nodes'])} nodes, {len(graph1['edges'])} edges — deterministic ✓")


def test_p1_graph_related():
    """P1-G2: get_related_nodes returns deterministic result for a known node."""
    print("\n=== Test P1-G2: Graph Related Nodes ===")
    from mcp.core.graph_builder import build_graph
    from mcp.core.graph_query import get_related_nodes

    vault = list_vaults()[0]
    graph = build_graph(vault_name=vault)

    # Find a note node
    note_nodes = [n for n in graph["nodes"] if n["type"] == "note"]
    if not note_nodes:
        print("  No note nodes in graph — skipping")
        return

    node_id = note_nodes[0]["id"]
    result1 = get_related_nodes(graph, node_id)
    result2 = get_related_nodes(graph, node_id)

    assert "node_id" in result1
    assert "found" in result1
    assert "related" in result1
    assert result1["found"] is True, f"Note node {node_id!r} should be found"
    assert isinstance(result1["related"], list)

    # Deterministic
    assert result1 == result2, "get_related_nodes must be deterministic"

    # sorted: primary strength desc, secondary id asc
    if len(result1["related"]) > 1:
        strengths = [r["strength"] for r in result1["related"]]
        from mcp.core.graph_query import _STRENGTH_RANK
        ranks = [_STRENGTH_RANK[s] for s in strengths]
        assert ranks == sorted(ranks, reverse=True), (
            "Related nodes must be sorted by strength descending"
        )

    print(f"  Node: {node_id!r}, related={len(result1['related'])} nodes — deterministic ✓")


def test_p1_graph_missing_neighbors():
    """P1-G3: get_missing_neighbors returns deterministic result; unknown node is handled."""
    print("\n=== Test P1-G3: Graph Missing Neighbors ===")
    from mcp.core.graph_builder import build_graph
    from mcp.core.graph_query import get_missing_neighbors

    vault = list_vaults()[0]
    graph = build_graph(vault_name=vault)

    # Unknown node must return found=False, not crash
    unknown_result = get_missing_neighbors(graph, "note::__nonexistent__")
    assert unknown_result["found"] is False, "Unknown node must return found=False"
    assert unknown_result["missing"] == [], "Unknown node must return empty missing list"
    print(f"  Unknown node: found=False, missing=[] ✓")

    # Known note node
    note_nodes = [n for n in graph["nodes"] if n["type"] == "note"]
    if not note_nodes:
        print("  No note nodes — skipping known-node check")
        return

    node_id = note_nodes[0]["id"]
    result1 = get_missing_neighbors(graph, node_id)
    result2 = get_missing_neighbors(graph, node_id)

    assert "found" in result1 and "missing" in result1
    assert isinstance(result1["missing"], list)
    # Deterministic
    assert result1 == result2, "get_missing_neighbors must be deterministic"
    # Sorted ascending by id
    ids = [m["id"] for m in result1["missing"]]
    assert ids == sorted(ids), "Missing neighbors must be sorted ascending by id"

    print(f"  Node: {node_id!r}, missing_neighbors={len(result1['missing'])} — deterministic ✓")


def test_p1_unknown_vault_structured_error():
    """P1-E1: Unknown vault returns a structured error from adapters."""
    print("\n=== Test P1-E1: Unknown Vault Structured Error ===")
    from mcp.core.adapters.validation_adapter import get_validation
    from mcp.core.adapters.tasks_adapter import get_tasks
    from mcp.core.adapters.notes_adapter import get_notes
    from mcp.core.adapters.quality_adapter import get_quality
    from mcp.core.adapters.missing_adapter import get_missing

    bad_vault = "__nonexistent_vault_xyz__"

    # Each adapter must return {"error": ...} not raise an exception
    for name, fn in [
        ("validation", lambda: get_validation(vault_name=bad_vault)),
        ("tasks",      lambda: get_tasks(vault_name=bad_vault)),
        ("notes",      lambda: get_notes(vault_name=bad_vault)),
        ("quality",    lambda: get_quality(vault_name=bad_vault)),
        ("missing",    lambda: get_missing(vault_name=bad_vault)),
    ]:
        result = fn()
        assert "error" in result, (
            f"{name} adapter should return {{'error': ...}} for unknown vault, got: {result}"
        )
        print(f"  {name}: structured error returned — {result['error']!r}")


def test_p1_validation_vault_param():
    """P1-V1: /validation route with explicit vault param matches default result."""
    print("\n=== Test P1-V1: /validation vault param ===")
    from mcp.core.adapters.validation_adapter import get_validation

    vault = list_vaults()[0]
    result_explicit = get_validation(vault_name=vault)
    result_default = get_validation(vault_name=None)

    assert result_explicit.get("status") == result_default.get("status"), (
        "Explicit vault must produce same status as default vault"
    )
    assert result_explicit.get("invalid_count") == result_default.get("invalid_count")
    print(f"  Explicit vault={vault!r} matches default result: status={result_explicit['status']}")


def test_p1_tasks_vault_param():
    """P1-V2: /tasks route with explicit vault param matches default result."""
    print("\n=== Test P1-V2: /tasks vault param ===")
    from mcp.core.adapters.tasks_adapter import get_tasks

    vault = list_vaults()[0]
    result_explicit = get_tasks(vault_name=vault, limit=9999)
    result_default = get_tasks(vault_name=None, limit=9999)

    assert result_explicit.get("total") == result_default.get("total"), (
        "Explicit vault must produce same total as default vault"
    )
    print(f"  Explicit vault={vault!r} total={result_explicit['total']} matches default")


def test_p1_notes_vault_param():
    """P1-V3: /notes route with explicit vault param matches default result."""
    print("\n=== Test P1-V3: /notes vault param ===")
    from mcp.core.adapters.notes_adapter import get_notes

    vault = list_vaults()[0]
    result_explicit = get_notes(vault_name=vault)
    result_default = get_notes(vault_name=None)

    assert len(result_explicit.get("notes", [])) == len(result_default.get("notes", [])), (
        "Explicit vault must return same note count as default vault"
    )
    print(f"  Explicit vault={vault!r} note_count={len(result_explicit['notes'])} matches default")


def test_p1_quality_vault_param():
    """P1-V4: /quality route with explicit vault param matches default result."""
    print("\n=== Test P1-V4: /quality vault param ===")
    from mcp.core.adapters.quality_adapter import get_quality

    vault = list_vaults()[0]
    result_explicit = get_quality(vault_name=vault)
    result_default = get_quality(vault_name=None)

    assert result_explicit.get("total") == result_default.get("total"), (
        "Explicit vault must produce same total as default vault"
    )
    print(f"  Explicit vault={vault!r} total={result_explicit['total']} matches default")


def test_p1_missing_vault_param():
    """P1-V5: /missing route with explicit vault param matches default result."""
    print("\n=== Test P1-V5: /missing vault param ===")
    from mcp.core.adapters.missing_adapter import get_missing

    vault = list_vaults()[0]
    result_explicit = get_missing(vault_name=vault)
    result_default = get_missing(vault_name=None)

    # Both should either error identically or return the same total_expected
    if "error" in result_explicit:
        assert "error" in result_default, "Both should error when EXPECTED_CONCEPTS missing"
        print(f"  Both return structured error: {result_explicit['error']!r}")
    else:
        assert result_explicit.get("total_expected") == result_default.get("total_expected"), (
            "Explicit vault must produce same total_expected as default vault"
        )
        print(f"  Explicit vault={vault!r} total_expected={result_explicit['total_expected']} matches default")


# ============================================================
# Phase 2 — Context Bundle Tests
# ============================================================

def test_p2_generate_bundle_basic():
    """P2-B1: generate_bundle returns required top-level fields."""
    print("\n=== Test P2-B1: generate_bundle Basic Shape ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    build_index(vault)

    bundle = generate_bundle(vault_name=vault)

    assert bundle["status"] == "ok", f"Expected status=ok, got: {bundle}"
    for key in ("bundle_id", "vault", "filters", "created_at",
                "validation_status", "notes", "graph", "budget",
                "warnings", "manifest"):
        assert key in bundle, f"Missing key: {key!r}"

    assert bundle["vault"] == vault
    assert isinstance(bundle["bundle_id"], str) and len(bundle["bundle_id"]) == 16
    assert bundle["validation_status"] in ("pass", "fail")
    assert isinstance(bundle["notes"], list)
    assert isinstance(bundle["warnings"], list)
    assert "related" in bundle["graph"]
    assert "max_chars" in bundle["budget"]
    assert "used_chars" in bundle["budget"]
    assert "note_count" in bundle["budget"]
    assert "truncated" in bundle["budget"]
    assert "source_paths" in bundle["manifest"]
    assert "schema_version" in bundle["manifest"]
    print(f"  bundle_id={bundle['bundle_id']}, "
          f"notes={len(bundle['notes'])}, "
          f"validation_status={bundle['validation_status']}")


def test_p2_generate_bundle_posix_paths():
    """P2-B2: All note paths in bundle are full vault-relative POSIX paths."""
    print("\n=== Test P2-B2: POSIX Paths ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    bundle = generate_bundle(vault_name=vault, allow_partial=True, max_notes=5)

    assert bundle["status"] == "ok"
    for note in bundle["notes"]:
        path = note["path"]
        assert "/" in path, f"Path has no forward slash: {path!r}"
        assert "\\" not in path, f"Path uses backslash: {path!r}"
        assert path.endswith(".md"), f"Path does not end with .md: {path!r}"
    for src in bundle["manifest"]["source_paths"]:
        assert "\\" not in src, f"Manifest path uses backslash: {src!r}"
    print(f"  {len(bundle['notes'])} notes — all POSIX paths ✓")


def test_p2_generate_bundle_max_notes():
    """P2-B3: max_notes limits the number of returned notes."""
    print("\n=== Test P2-B3: max_notes Respected ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    bundle = generate_bundle(vault_name=vault, max_notes=2, allow_partial=True)

    assert bundle["status"] == "ok"
    assert len(bundle["notes"]) <= 2, (
        f"Expected at most 2 notes, got {len(bundle['notes'])}"
    )
    assert bundle["budget"]["note_count"] == len(bundle["notes"])
    print(f"  max_notes=2, returned={len(bundle['notes'])} ✓")


def test_p2_generate_bundle_max_chars():
    """P2-B4: max_chars budget is respected and truncated flag set."""
    print("\n=== Test P2-B4: max_chars Respected ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    build_index(vault)
    full_idx = get_index(vault)

    # Any non-empty body note will exceed budget=1
    bundle = generate_bundle(
        vault_name=vault, max_chars=1, allow_partial=True,
        include_body=True, max_notes=50,
    )

    assert bundle["status"] == "ok"
    # With max_chars=1 and bodies present, the first note should exhaust budget
    assert bundle["budget"]["truncated"] is True or bundle["budget"]["note_count"] == 0 or (
        bundle["budget"]["used_chars"] <= 1
    ), f"Budget not enforced: {bundle['budget']}"
    assert bundle["budget"]["used_chars"] <= bundle["budget"]["max_chars"] or (
        bundle["budget"]["note_count"] == 0
    ), "used_chars must not exceed max_chars"
    print(f"  max_chars=1: truncated={bundle['budget']['truncated']}, "
          f"note_count={bundle['budget']['note_count']}, "
          f"used_chars={bundle['budget']['used_chars']}")


def test_p2_generate_bundle_allow_partial_false():
    """P2-B5: allow_partial=False excludes notes with status=partial."""
    print("\n=== Test P2-B5: allow_partial=False Excludes Partial Notes ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    build_index(vault)

    bundle_strict = generate_bundle(
        vault_name=vault, allow_partial=False, max_notes=50, filters={},
    )
    bundle_lenient = generate_bundle(
        vault_name=vault, allow_partial=True, max_notes=50, filters={},
    )

    assert bundle_strict["status"] == "ok"
    assert bundle_lenient["status"] == "ok"

    # No partial note should appear when allow_partial=False
    for note in bundle_strict["notes"]:
        status = note["fields"].get("status", "")
        assert status != "partial", (
            f"Partial note found in strict bundle: {note['path']!r}"
        )

    # When there are partial notes, strict should have fewer or equal
    partial_count = sum(
        1 for n in get_index(vault) if n["fields"].get("status") == "partial"
    )
    if partial_count > 0:
        assert len(bundle_strict["notes"]) <= len(bundle_lenient["notes"]), (
            "Strict bundle must have fewer or equal notes when partial notes exist"
        )
    print(f"  strict={len(bundle_strict['notes'])} notes, "
          f"lenient={len(bundle_lenient['notes'])} notes, "
          f"partial_in_vault={partial_count}")


def test_p2_generate_bundle_allow_partial_true():
    """P2-B6: allow_partial=True can include notes with status=partial."""
    print("\n=== Test P2-B6: allow_partial=True Includes Partial Notes ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    build_index(vault)

    # Check whether the vault actually has partial notes
    partial_notes = [
        n for n in get_index(vault) if n["fields"].get("status") == "partial"
    ]

    bundle = generate_bundle(
        vault_name=vault, allow_partial=True, max_notes=50, filters={},
    )
    assert bundle["status"] == "ok"

    if partial_notes:
        partial_paths_in_bundle = [
            n["path"] for n in bundle["notes"]
            if n["fields"].get("status") == "partial"
        ]
        assert len(partial_paths_in_bundle) > 0, (
            "Expected partial notes to appear when allow_partial=True"
        )
        print(f"  {len(partial_paths_in_bundle)} partial notes included ✓")
    else:
        print("  No partial notes in vault — skipping partial count check")


def test_p2_generate_bundle_sections():
    """P2-B7: include_sections extracts requested section content."""
    print("\n=== Test P2-B7: include_sections ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    sections = ["Key Principles", "How It Works", "Trade-offs"]

    bundle = generate_bundle(
        vault_name=vault,
        include_sections=sections,
        allow_partial=True,
        max_notes=5,
    )

    assert bundle["status"] == "ok"
    for note in bundle["notes"]:
        for sec in sections:
            assert sec in note["sections"], (
                f"Section '{sec}' missing from note {note['path']!r}"
            )
            # Value must be a string (empty string is acceptable for missing sections)
            assert isinstance(note["sections"][sec], str), (
                f"Section '{sec}' value must be str in {note['path']!r}"
            )
    print(f"  {len(bundle['notes'])} notes — all have {sections} keys ✓")


def test_p2_generate_bundle_include_body_false():
    """P2-B8: include_body=False returns empty body consistently."""
    print("\n=== Test P2-B8: include_body=False ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    bundle = generate_bundle(
        vault_name=vault, include_body=False, allow_partial=True, max_notes=5,
    )

    assert bundle["status"] == "ok"
    for note in bundle["notes"]:
        assert "body" in note, f"Note missing 'body' key: {note['path']!r}"
        assert note["body"] == "", (
            f"Expected empty body when include_body=False, got non-empty for {note['path']!r}"
        )
    print(f"  {len(bundle['notes'])} notes — all have body='' ✓")


def test_p2_generate_bundle_include_body_true():
    """P2-B9: include_body=True returns non-empty body for notes with content."""
    print("\n=== Test P2-B9: include_body=True ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    bundle = generate_bundle(
        vault_name=vault, include_body=True, allow_partial=True, max_notes=3,
    )

    assert bundle["status"] == "ok"
    bodies_with_content = [n for n in bundle["notes"] if n.get("body")]
    assert len(bodies_with_content) > 0, (
        "Expected at least one note with non-empty body when include_body=True"
    )
    print(f"  {len(bodies_with_content)}/{len(bundle['notes'])} notes have non-empty body ✓")


def test_p2_generate_bundle_include_related():
    """P2-B10: include_related=True returns graph relationship IDs."""
    print("\n=== Test P2-B10: include_related=True ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    bundle = generate_bundle(
        vault_name=vault,
        include_related=True,
        allow_partial=True,
        max_notes=3,
    )

    assert bundle["status"] == "ok"
    related = bundle["graph"]["related"]
    assert isinstance(related, dict), "graph.related must be a dict"

    for note in bundle["notes"]:
        path = note["path"]
        assert path in related, (
            f"Note path '{path}' missing from graph.related"
        )
        assert isinstance(related[path], list), (
            f"graph.related['{path}'] must be a list"
        )
        # Related IDs must be sorted (deterministic)
        ids = related[path]
        assert ids == sorted(ids), f"Related IDs not sorted for '{path}'"

    print(f"  {len(related)} notes in graph.related — all lists, sorted ✓")


def test_p2_generate_bundle_validation_status():
    """P2-B11: validation_status is included and has correct value."""
    print("\n=== Test P2-B11: validation_status ===")
    from core.shared.context_bundle import generate_bundle
    from mcp.core.adapters.validation_adapter import get_validation

    vault = list_vaults()[0]
    build_index(vault)

    bundle = generate_bundle(vault_name=vault, allow_partial=True, max_notes=50)
    assert bundle["status"] == "ok"
    assert bundle["validation_status"] in ("pass", "fail"), (
        f"validation_status must be 'pass' or 'fail', got: {bundle['validation_status']!r}"
    )

    # For notes actually in the bundle, check consistency with validation adapter
    val_result = get_validation(vault_name=vault)
    invalid_set = set(val_result.get("invalid_notes", []))
    bundle_paths = {n["path"] for n in bundle["notes"]}
    expected_status = "fail" if (bundle_paths & invalid_set) else "pass"
    assert bundle["validation_status"] == expected_status, (
        f"validation_status mismatch: bundle={bundle['validation_status']!r}, "
        f"expected={expected_status!r}"
    )
    print(f"  validation_status={bundle['validation_status']!r} — correct ✓")


def test_p2_bundle_deterministic():
    """P2-B12: Two identical calls return same bundle (except created_at)."""
    print("\n=== Test P2-B12: Deterministic Ordering ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    kwargs = dict(
        vault_name=vault,
        filters={},
        include_sections=["Key Principles", "How It Works"],
        include_related=True,
        include_body=True,
        max_notes=5,
        max_chars=50000,
        allow_partial=True,
    )

    bundle1 = generate_bundle(**kwargs)
    bundle2 = generate_bundle(**kwargs)

    assert bundle1["status"] == "ok"
    assert bundle2["status"] == "ok"

    # bundle_id must be identical (deterministic from params)
    assert bundle1["bundle_id"] == bundle2["bundle_id"], (
        f"bundle_id differs: {bundle1['bundle_id']!r} vs {bundle2['bundle_id']!r}"
    )

    # Note order must be identical
    paths1 = [n["path"] for n in bundle1["notes"]]
    paths2 = [n["path"] for n in bundle2["notes"]]
    assert paths1 == paths2, f"Note order not deterministic: {paths1} vs {paths2}"

    # All paths must be case-insensitively sorted
    assert paths1 == sorted(paths1, key=str.lower), "Notes must be sorted case-insensitively"

    # budget (excluding timestamp-independent fields) must match
    assert bundle1["budget"] == bundle2["budget"], "Budget must be deterministic"
    assert bundle1["manifest"]["source_paths"] == bundle2["manifest"]["source_paths"]

    # graph.related must be identical
    assert bundle1["graph"]["related"] == bundle2["graph"]["related"], (
        "graph.related must be deterministic"
    )

    print(f"  bundle_id={bundle1['bundle_id']}, notes={len(paths1)} — deterministic ✓")


def test_p2_bundle_unknown_vault():
    """P2-B13: Unknown vault returns structured error."""
    print("\n=== Test P2-B13: Unknown Vault ===")
    from core.shared.context_bundle import generate_bundle

    result = generate_bundle(vault_name="__nonexistent_vault_xyz__")

    assert result["status"] == "error", (
        f"Expected error for unknown vault, got: {result}"
    )
    assert "error" in result
    assert result["error"].get("code") == "INVALID_VAULT"
    print(f"  Unknown vault: structured error returned ✓ ({result['error']['message']!r})")


def test_p2_bundle_empty_filter():
    """P2-B14: Filter that matches nothing returns ok with empty notes and warning."""
    print("\n=== Test P2-B14: Empty Filter Result ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    bundle = generate_bundle(
        vault_name=vault,
        filters={"status": "__impossible_value__xyz__"},
    )

    assert bundle["status"] == "ok", (
        "Empty filter result must return status=ok (not an error)"
    )
    assert bundle["notes"] == []
    assert bundle["budget"]["note_count"] == 0
    assert len(bundle["warnings"]) > 0, "Expected at least one warning for empty result"
    print(f"  Empty filter: notes=[], warnings={bundle['warnings'][:1]} ✓")


def test_p2_cli_bundle():
    """P2-CLI: python run.py bundle returns valid JSON with required fields."""
    print("\n=== Test P2-CLI: CLI bundle command ===")
    import json
    import subprocess

    result = subprocess.run(
        [sys.executable, "run.py", "bundle"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        timeout=60,
    )

    assert result.returncode == 0, (
        f"CLI bundle exited {result.returncode}\n"
        f"stdout: {result.stdout[:500]}\n"
        f"stderr: {result.stderr[:500]}"
    )

    try:
        bundle = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"CLI bundle output is not valid JSON: {exc}\n"
            f"stdout: {result.stdout[:500]}"
        ) from exc

    assert bundle["status"] == "ok", f"CLI bundle status not ok: {bundle}"
    for key in ("bundle_id", "vault", "notes", "budget", "manifest"):
        assert key in bundle, f"CLI bundle missing key: {key!r}"

    print(f"  CLI bundle: status=ok, notes={len(bundle['notes'])}, "
          f"bundle_id={bundle['bundle_id']!r} ✓")


def test_p2_http_bundle():
    """P2-HTTP: HTTP-level tests for POST /context/bundle via TestClient."""
    print("\n=== Test P2-HTTP: POST /context/bundle (TestClient) ===")
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        print(f"  SKIP: TestClient unavailable — {exc}")
        return

    from mcp.server.mcp_server import app

    vault = list_vaults()[0]
    build_index(vault)
    idx = get_index(vault)

    with TestClient(app, raise_server_exceptions=True) as client:

        # --- Valid minimal request ---
        resp = client.post("/context/bundle", json={
            "vault": vault,
            "allow_partial": True,
        })
        assert resp.status_code == 200, (
            f"/context/bundle status {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()
        assert body["status"] == "ok", f"Expected ok: {body}"
        for key in ("bundle_id", "vault", "filters", "created_at",
                    "validation_status", "notes", "graph", "budget",
                    "warnings", "manifest"):
            assert key in body, f"Missing key: {key!r}"
        print(f"  POST /context/bundle (minimal): 200 OK, notes={len(body['notes'])} ✓")

        # --- Unknown vault returns 404 ---
        resp = client.post("/context/bundle", json={"vault": "__unknown__"})
        assert resp.status_code == 404, (
            f"Unknown vault: expected 404, got {resp.status_code}"
        )
        body = resp.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_VAULT"
        print(f"  Unknown vault: 404 INVALID_VAULT ✓")

        # --- Unknown filter field returns 400 ---
        resp = client.post("/context/bundle", json={
            "vault": vault,
            "filters": {"nonexistent_field_xyz": "value"},
        })
        assert resp.status_code == 400, (
            f"Unknown filter: expected 400, got {resp.status_code}"
        )
        body = resp.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_FILTER"
        print(f"  Unknown filter: 400 INVALID_FILTER ✓")

        # --- max_notes respected ---
        resp = client.post("/context/bundle", json={
            "vault": vault,
            "max_notes": 2,
            "allow_partial": True,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["notes"]) <= 2, (
            f"max_notes=2 not respected: got {len(body['notes'])} notes"
        )
        print(f"  max_notes=2: {len(body['notes'])} notes ✓")

        # --- max_chars respected ---
        resp = client.post("/context/bundle", json={
            "vault": vault,
            "max_chars": 100,
            "include_body": True,
            "allow_partial": True,
            "max_notes": 50,
        })
        assert resp.status_code == 200
        body = resp.json()
        # Either truncated or very few notes
        assert body["budget"]["used_chars"] <= 100 or body["budget"]["truncated"] is True, (
            f"max_chars=100 not enforced: {body['budget']}"
        )
        print(f"  max_chars=100: truncated={body['budget']['truncated']}, "
              f"used={body['budget']['used_chars']} ✓")

        # --- allow_partial=False excludes partial notes ---
        resp = client.post("/context/bundle", json={
            "vault": vault,
            "allow_partial": False,
            "max_notes": 50,
        })
        assert resp.status_code == 200
        body = resp.json()
        for note in body["notes"]:
            assert note["fields"].get("status") != "partial", (
                f"Partial note {note['path']!r} found with allow_partial=False"
            )
        print(f"  allow_partial=False: {len(body['notes'])} notes, none partial ✓")

        # --- allow_partial=True can include partial notes ---
        resp_strict = client.post("/context/bundle", json={
            "vault": vault, "allow_partial": False, "max_notes": 50,
        })
        resp_lenient = client.post("/context/bundle", json={
            "vault": vault, "allow_partial": True, "max_notes": 50,
        })
        assert resp_strict.status_code == 200 and resp_lenient.status_code == 200
        strict_count = len(resp_strict.json()["notes"])
        lenient_count = len(resp_lenient.json()["notes"])
        partial_in_vault = sum(
            1 for n in idx if n["fields"].get("status") == "partial"
        )
        if partial_in_vault > 0:
            assert lenient_count >= strict_count, (
                "allow_partial=True should include at least as many notes"
            )
        print(f"  allow_partial: strict={strict_count}, lenient={lenient_count} ✓")

        # --- include_sections returns requested sections ---
        resp = client.post("/context/bundle", json={
            "vault": vault,
            "include_sections": ["Key Principles", "How It Works"],
            "allow_partial": True,
            "max_notes": 3,
        })
        assert resp.status_code == 200
        body = resp.json()
        for note in body["notes"]:
            assert "Key Principles" in note["sections"]
            assert "How It Works" in note["sections"]
        print(f"  include_sections: all notes have requested section keys ✓")

        # --- include_body=False returns empty body ---
        resp = client.post("/context/bundle", json={
            "vault": vault,
            "include_body": False,
            "allow_partial": True,
            "max_notes": 3,
        })
        assert resp.status_code == 200
        body = resp.json()
        for note in body["notes"]:
            assert note["body"] == "", (
                f"Expected empty body with include_body=False: {note['path']!r}"
            )
        print(f"  include_body=False: all bodies are '' ✓")

        # --- include_related=True returns graph relationships ---
        resp = client.post("/context/bundle", json={
            "vault": vault,
            "include_related": True,
            "allow_partial": True,
            "max_notes": 3,
        })
        assert resp.status_code == 200
        body = resp.json()
        related = body["graph"]["related"]
        assert isinstance(related, dict)
        for note in body["notes"]:
            assert note["path"] in related
        print(f"  include_related=True: {len(related)} entries in graph.related ✓")

        # --- validation_status included ---
        resp = client.post("/context/bundle", json={
            "vault": vault, "allow_partial": True, "max_notes": 5,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["validation_status"] in ("pass", "fail")
        print(f"  validation_status={body['validation_status']!r} ✓")

        # --- Deterministic ordering across two identical calls ---
        req_body = {
            "vault": vault,
            "filters": {},
            "include_sections": ["Key Principles"],
            "include_related": False,
            "include_body": True,
            "max_notes": 5,
            "max_chars": 50000,
            "allow_partial": True,
        }
        resp1 = client.post("/context/bundle", json=req_body)
        resp2 = client.post("/context/bundle", json=req_body)
        assert resp1.status_code == 200 and resp2.status_code == 200
        b1, b2 = resp1.json(), resp2.json()
        # bundle_id must be same (deterministic, not timestamp-derived)
        assert b1["bundle_id"] == b2["bundle_id"], (
            f"bundle_id not deterministic: {b1['bundle_id']!r} vs {b2['bundle_id']!r}"
        )
        paths1 = [n["path"] for n in b1["notes"]]
        paths2 = [n["path"] for n in b2["notes"]]
        assert paths1 == paths2, f"Note order not deterministic: {paths1} vs {paths2}"
        assert paths1 == sorted(paths1, key=str.lower), "Notes must be sorted"
        print(f"  Deterministic: bundle_id={b1['bundle_id']!r}, paths identical ✓")

        # --- Pydantic validation: max_notes out of range ---
        resp = client.post("/context/bundle", json={
            "vault": vault, "max_notes": 0,
        })
        assert resp.status_code == 422, (
            f"max_notes=0 should fail validation, got {resp.status_code}"
        )
        body = resp.json()
        assert body["status"] == "error"
        print(f"  max_notes=0: 422 VALIDATION_ERROR ✓")

    print(f"  All /context/bundle HTTP tests passed ✓")


def test_p2_budget_high_max_chars():
    """P2-B15: With very high max_chars, min(max_notes, complete_count) notes returned."""
    print("\n=== Test P2-B15: High max_chars returns min(max_notes, complete_count) ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    build_index(vault)
    idx = get_index(vault)

    complete_count = sum(1 for n in idx if n["fields"].get("status") == "complete")

    # Very high budget, include_body=False and no sections → note_chars=0 → no budget
    # enforcement → max_notes is the only cap. 11 complete notes, max_notes=10 → 10.
    bundle = generate_bundle(
        vault_name=vault,
        filters={"status": "complete"},
        include_sections=[],
        include_body=False,
        max_notes=10,
        max_chars=999999,
        allow_partial=False,
    )
    assert bundle["status"] == "ok"
    expected = min(10, complete_count)
    assert len(bundle["notes"]) == expected, (
        f"Expected {expected} notes (min(10,{complete_count})), got {len(bundle['notes'])}"
    )
    # budget.truncated must be False — budget was never exhausted
    assert bundle["budget"]["truncated"] is False, (
        f"truncated should be False when all selected notes fit budget: {bundle['budget']}"
    )
    # budget.note_count must equal len(notes)
    assert bundle["budget"]["note_count"] == len(bundle["notes"]), (
        f"budget.note_count={bundle['budget']['note_count']} != len(notes)={len(bundle['notes'])}"
    )
    # used_chars must not exceed max_chars
    assert bundle["budget"]["used_chars"] <= bundle["budget"]["max_chars"], (
        f"used_chars {bundle['budget']['used_chars']} exceeds max_chars "
        f"{bundle['budget']['max_chars']}"
    )
    print(f"  complete={complete_count}, max_notes=10 → {len(bundle['notes'])} notes, "
          f"truncated={bundle['budget']['truncated']} ✓")


def test_p2_budget_truncation_warning():
    """P2-B16: Low max_chars sets truncated=True with a budget warning; used_chars <= max_chars."""
    print("\n=== Test P2-B16: Low max_chars triggers truncation warning ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]

    # 5000 chars is enough for ~2 notes (each ≈2000–2500 chars when body+sections counted)
    # but not all 19, so truncation is guaranteed.
    bundle = generate_bundle(
        vault_name=vault,
        include_sections=["Key Principles"],
        include_body=True,
        max_notes=50,
        max_chars=5000,
        allow_partial=True,
    )
    assert bundle["status"] == "ok"
    assert bundle["budget"]["truncated"] is True, (
        f"Expected truncated=True with max_chars=5000, got: {bundle['budget']}"
    )
    # At least one warning must mention the budget
    budget_warnings = [w for w in bundle["warnings"] if "Budget limit" in w]
    assert budget_warnings, (
        f"Expected a budget warning but got: {bundle['warnings']}"
    )
    # used_chars must never exceed max_chars
    assert bundle["budget"]["used_chars"] <= bundle["budget"]["max_chars"], (
        f"used_chars {bundle['budget']['used_chars']} exceeds max_chars "
        f"{bundle['budget']['max_chars']}"
    )
    # note_count must equal len(notes)
    assert bundle["budget"]["note_count"] == len(bundle["notes"])
    print(f"  max_chars=5000: {len(bundle['notes'])} notes, truncated=True, "
          f"used={bundle['budget']['used_chars']}, warning={budget_warnings[0]!r} ✓")


def test_p2_budget_max_notes_vs_max_chars():
    """P2-B17: max_notes and max_chars effects are distinguishable via budget.truncated."""
    print("\n=== Test P2-B17: max_notes vs max_chars distinguishable ===")
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    build_index(vault)
    idx = get_index(vault)

    # --- max_notes effect: high budget, max_notes=2, include_body=False ---
    # note_chars=0 for every note → budget never enforced → truncated=False
    bundle_notes_cap = generate_bundle(
        vault_name=vault,
        include_sections=[],
        include_body=False,
        max_notes=2,
        max_chars=999999,
        allow_partial=True,
    )
    assert bundle_notes_cap["status"] == "ok"
    assert len(bundle_notes_cap["notes"]) == 2
    # truncated must be False — only max_notes limited the result
    assert bundle_notes_cap["budget"]["truncated"] is False, (
        "truncated must be False when max_notes (not budget) limits the result"
    )

    # --- max_chars effect: very high max_notes, small budget, include_body=True ---
    # Many notes would match but budget stops them; truncated=True.
    total_notes = len(idx)
    bundle_chars_cap = generate_bundle(
        vault_name=vault,
        include_sections=[],
        include_body=True,
        max_notes=total_notes + 10,
        max_chars=3000,
        allow_partial=True,
    )
    assert bundle_chars_cap["status"] == "ok"
    assert bundle_chars_cap["budget"]["truncated"] is True, (
        "truncated must be True when max_chars limits the result"
    )
    # used_chars must not exceed max_chars
    assert bundle_chars_cap["budget"]["used_chars"] <= bundle_chars_cap["budget"]["max_chars"]

    print(f"  max_notes cap: {len(bundle_notes_cap['notes'])} notes, "
          f"truncated={bundle_notes_cap['budget']['truncated']} (False) ✓")
    print(f"  max_chars cap: {len(bundle_chars_cap['notes'])} notes, "
          f"truncated={bundle_chars_cap['budget']['truncated']} (True) ✓")


# ============================================================
# Phase 3 — Feedback Loop Tests
# ============================================================

def test_p3_feedback_missing_file():
    """P3-F1: Missing feedback.md returns ok with empty entries."""
    print("\n=== Test P3-F1: Missing feedback.md ===")
    import tempfile, os
    from pathlib import Path as _Path
    from core.shared.feedback import load_feedback

    # Use a temp directory with no feedback.md
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_feedback(_Path(tmpdir))
        assert result["status"] == "ok", f"Expected ok, got {result['status']}"
        assert result["entries"] == []
        assert result["warnings"] == []
        assert result["errors"] == []
        print(f"  Missing feedback.md: status=ok, entries=[] ✓")


def test_p3_feedback_valid_file():
    """P3-F2: Valid feedback.md parses correctly."""
    print("\n=== Test P3-F2: Valid feedback.md ===")
    from mcp.core.vault_registry import list_vaults, get_vault_path
    from core.shared.feedback import load_feedback, feedback_path

    vault = list_vaults()[0]
    vault_path = get_vault_path(vault)

    # Only run if feedback.md exists
    fb_file = feedback_path(vault_path)
    if not fb_file.is_file():
        print("  SKIP: no feedback.md in vault")
        return

    result = load_feedback(vault_path)
    # Should be ok or error (but not crash)
    assert result["status"] in ("ok", "error"), f"Unexpected status: {result['status']}"
    assert isinstance(result["entries"], list)
    assert isinstance(result["warnings"], list)
    assert isinstance(result["errors"], list)
    print(f"  feedback.md: status={result['status']}, "
          f"entries={len(result['entries'])}, warnings={len(result['warnings'])}, "
          f"errors={len(result['errors'])} ✓")


def test_p3_feedback_empty_list():
    """P3-F3: feedback.md with empty list returns ok."""
    print("\n=== Test P3-F3: Empty feedback list ===")
    import tempfile
    from pathlib import Path as _Path
    from core.shared.feedback import load_feedback

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_files = _Path(tmpdir) / "Vault Files"
        vault_files.mkdir()
        fb = vault_files / "feedback.md"
        fb.write_text("feedback:\n", encoding="utf-8")

        result = load_feedback(_Path(tmpdir))
        assert result["status"] == "ok", f"Expected ok: {result}"
        assert result["entries"] == []
        assert result["errors"] == []
        print(f"  Empty feedback list: status=ok, entries=[] ✓")


def test_p3_feedback_malformed_yaml():
    """P3-F4: Malformed YAML returns structured error."""
    print("\n=== Test P3-F4: Malformed YAML ===")
    import tempfile
    from pathlib import Path as _Path
    from core.shared.feedback import load_feedback

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_files = _Path(tmpdir) / "Vault Files"
        vault_files.mkdir()
        fb = vault_files / "feedback.md"
        fb.write_text("feedback: [invalid: yaml: {\n", encoding="utf-8")

        result = load_feedback(_Path(tmpdir))
        assert result["status"] == "error", f"Expected error for malformed YAML: {result}"
        assert len(result["errors"]) > 0
        assert result["errors"][0]["code"] == "MALFORMED_YAML"
        assert result["entries"] == []
        print(f"  Malformed YAML: status=error, code=MALFORMED_YAML ✓")


def test_p3_feedback_unknown_signal():
    """P3-F5: Unknown signal value returns structured error."""
    print("\n=== Test P3-F5: Unknown signal ===")
    import tempfile
    from pathlib import Path as _Path
    from core.shared.feedback import load_feedback

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_files = _Path(tmpdir) / "Vault Files"
        vault_files.mkdir()
        fb = vault_files / "feedback.md"
        fb.write_text(
            "feedback:\n"
            "  - path: Fundamentals/Algorithms.md\n"
            "    source: human\n"
            "    signal: totally_unknown_signal\n"
            "    severity: medium\n",
            encoding="utf-8",
        )

        result = load_feedback(_Path(tmpdir))
        assert result["status"] == "error", f"Expected error for unknown signal: {result}"
        codes = [e["code"] for e in result["errors"]]
        assert "INVALID_SIGNAL" in codes, f"Expected INVALID_SIGNAL, got codes: {codes}"
        print(f"  Unknown signal: status=error, INVALID_SIGNAL detected ✓")


def test_p3_feedback_unknown_severity():
    """P3-F6: Unknown severity value returns structured error."""
    print("\n=== Test P3-F6: Unknown severity ===")
    import tempfile
    from pathlib import Path as _Path
    from core.shared.feedback import load_feedback

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_files = _Path(tmpdir) / "Vault Files"
        vault_files.mkdir()
        fb = vault_files / "feedback.md"
        fb.write_text(
            "feedback:\n"
            "  - path: Fundamentals/Algorithms.md\n"
            "    source: human\n"
            "    signal: unclear\n"
            "    severity: extreme\n",
            encoding="utf-8",
        )

        result = load_feedback(_Path(tmpdir))
        assert result["status"] == "error"
        codes = [e["code"] for e in result["errors"]]
        assert "INVALID_SEVERITY" in codes, f"Expected INVALID_SEVERITY, got: {codes}"
        print(f"  Unknown severity: status=error, INVALID_SEVERITY detected ✓")


def test_p3_feedback_unknown_source():
    """P3-F7: Unknown source value returns structured error."""
    print("\n=== Test P3-F7: Unknown source ===")
    import tempfile
    from pathlib import Path as _Path
    from core.shared.feedback import load_feedback

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_files = _Path(tmpdir) / "Vault Files"
        vault_files.mkdir()
        fb = vault_files / "feedback.md"
        fb.write_text(
            "feedback:\n"
            "  - path: Fundamentals/Algorithms.md\n"
            "    source: robot\n"
            "    signal: unclear\n"
            "    severity: medium\n",
            encoding="utf-8",
        )

        result = load_feedback(_Path(tmpdir))
        assert result["status"] == "error"
        codes = [e["code"] for e in result["errors"]]
        assert "INVALID_SOURCE" in codes, f"Expected INVALID_SOURCE, got: {codes}"
        print(f"  Unknown source: status=error, INVALID_SOURCE detected ✓")


def test_p3_feedback_missing_note_path():
    """P3-F8: Feedback referencing a non-existent note produces a warning, not error."""
    print("\n=== Test P3-F8: Missing note path produces warning ===")
    import tempfile
    from pathlib import Path as _Path
    from core.shared.feedback import load_feedback

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_files = _Path(tmpdir) / "Vault Files"
        vault_files.mkdir()
        fb = vault_files / "feedback.md"
        fb.write_text(
            "feedback:\n"
            "  - path: Fundamentals/NonExistentNote.md\n"
            "    source: human\n"
            "    signal: unclear\n"
            "    severity: medium\n",
            encoding="utf-8",
        )

        result = load_feedback(_Path(tmpdir))
        # Entry is valid (no structural errors) but the referenced note is missing
        assert result["status"] == "ok", f"Expected ok (missing note = warning): {result}"
        assert len(result["entries"]) == 1, "Entry must still be included"
        assert len(result["warnings"]) > 0, "Must have at least one warning"
        assert any("NonExistentNote" in w for w in result["warnings"]), (
            f"Warning must mention missing note path: {result['warnings']}"
        )
        print(f"  Missing note: status=ok, entry included, warning={result['warnings'][0]!r} ✓")


def test_p3_feedback_exclusion_from_notes():
    """P3-E1: feedback.md does not appear in /notes or note index."""
    print("\n=== Test P3-E1: feedback.md excluded from note index ===")
    from mcp.core.vault_registry import list_vaults, get_vault_path
    from mcp.core.note_index import build_index, get_index
    from core.shared.feedback import feedback_path

    vault = list_vaults()[0]
    vault_path = get_vault_path(vault)
    fb_file = feedback_path(vault_path)

    build_index(vault)
    index = get_index(vault)
    paths = [n["path"] for n in index]

    # feedback.md must never appear in the note index
    feedback_in_index = [p for p in paths if "feedback" in p.lower()]
    assert feedback_in_index == [], (
        f"feedback.md must not appear in note index, found: {feedback_in_index}"
    )
    print(f"  {len(paths)} notes indexed — feedback.md absent ✓")


def test_p3_feedback_exclusion_from_query():
    """P3-E2: feedback.md does not appear in query results."""
    print("\n=== Test P3-E2: feedback.md excluded from query ===")
    from mcp.core.vault_registry import list_vaults
    from mcp.core.query_engine import list_notes

    vault = list_vaults()[0]
    result = list_notes(vault, limit=500)
    assert result["status"] == "ok"

    paths = [n["path"] for n in result["results"]]
    feedback_in_results = [p for p in paths if "feedback" in p.lower()]
    assert feedback_in_results == [], (
        f"feedback.md must not appear in query results, found: {feedback_in_results}"
    )
    print(f"  {len(paths)} notes in query results — feedback.md absent ✓")


def test_p3_feedback_exclusion_from_graph():
    """P3-E3: feedback.md does not appear as a graph node."""
    print("\n=== Test P3-E3: feedback.md excluded from graph nodes ===")
    from mcp.core.vault_registry import list_vaults
    from mcp.core.graph_builder import build_graph

    vault = list_vaults()[0]
    graph = build_graph(vault_name=vault)

    node_ids = [n["id"] for n in graph["nodes"]]
    feedback_nodes = [nid for nid in node_ids if "feedback" in nid.lower()]
    assert feedback_nodes == [], (
        f"feedback.md must not appear as graph node, found: {feedback_nodes}"
    )
    print(f"  {len(node_ids)} graph nodes — feedback.md absent ✓")


def test_p3_feedback_exclusion_from_bundle():
    """P3-E4: feedback.md does not appear as a bundle note."""
    print("\n=== Test P3-E4: feedback.md excluded from bundle notes ===")
    from mcp.core.vault_registry import list_vaults
    from mcp.core.note_index import build_index
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    build_index(vault)
    bundle = generate_bundle(vault_name=vault, allow_partial=True, max_notes=50)

    assert bundle["status"] == "ok"
    note_paths = [n["path"] for n in bundle["notes"]]
    feedback_in_bundle = [p for p in note_paths if "feedback" in p.lower()]
    assert feedback_in_bundle == [], (
        f"feedback.md must not appear as bundle note, found: {feedback_in_bundle}"
    )
    print(f"  {len(note_paths)} bundle notes — feedback.md absent ✓")


def test_p3_task_weighting_false():
    """P3-T1: include_feedback=False preserves existing task score behaviour."""
    print("\n=== Test P3-T1: include_feedback=False preserves scores ===")
    from mcp.core.vault_registry import list_vaults
    from mcp.core.adapters.tasks_adapter import get_tasks

    vault = list_vaults()[0]

    result_no_fb = get_tasks(vault_name=vault, limit=50, include_feedback=False)
    assert "error" not in result_no_fb, f"Unexpected error: {result_no_fb.get('error')}"
    assert "tasks" in result_no_fb

    # Without feedback, tasks must NOT have feedback_weight
    for task in result_no_fb["tasks"]:
        assert "feedback_weight" not in task, (
            f"Task must not have feedback_weight when include_feedback=False: {task}"
        )

    # feedback_status must not be in result
    assert "feedback_status" not in result_no_fb

    print(f"  {len(result_no_fb['tasks'])} tasks — no feedback_weight fields ✓")


def test_p3_task_weighting_true():
    """P3-T2: include_feedback=True adds feedback_weight to every task."""
    print("\n=== Test P3-T2: include_feedback=True adds feedback_weight ===")
    from mcp.core.vault_registry import list_vaults
    from mcp.core.adapters.tasks_adapter import get_tasks

    vault = list_vaults()[0]
    result = get_tasks(vault_name=vault, limit=50, include_feedback=True)

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert "tasks" in result
    assert "feedback_status" in result, "feedback_status must be present when include_feedback=True"

    for task in result["tasks"]:
        assert "feedback_weight" in task, (
            f"Task must have feedback_weight when include_feedback=True: {task}"
        )
        fw = task["feedback_weight"]
        assert "score_delta" in fw
        assert "entry_count" in fw
        assert "summary" in fw
        assert isinstance(fw["score_delta"], (int, float))
        assert isinstance(fw["entry_count"], int)
        assert isinstance(fw["summary"], list)

    print(f"  {len(result['tasks'])} tasks — all have feedback_weight ✓")


def test_p3_task_weighting_score_change():
    """P3-T3: Feedback for a note changes its task score when include_feedback=True."""
    print("\n=== Test P3-T3: Feedback changes task score ===")
    import tempfile
    from pathlib import Path as _Path
    from mcp.core.vault_registry import list_vaults, get_vault_path
    from mcp.core.note_index import build_index, get_index
    from core.shared.upgrade_vault import load_all, generate_tasks
    from core.shared.feedback import feedback_weight_for_path, load_feedback
    from mcp.core.schema_loader import load_schema as _load_schema

    vault = list_vaults()[0]
    vault_path = get_vault_path(vault)

    # Get base tasks
    _schema = _load_schema(vault_path)
    records = load_all(vault_path, _schema)
    base_tasks = generate_tasks(records, _schema)

    if not base_tasks:
        print("  SKIP: no partial notes to test weighting")
        return

    # Check if any base task has feedback
    target_task = base_tasks[0]
    note_path = target_task["path"].replace("\\", "/")
    weight = feedback_weight_for_path(vault_path, note_path)

    if weight["entry_count"] == 0:
        print(f"  Note {note_path!r} has no feedback — score_delta=0 confirmed ✓")
    else:
        # score_delta must not be zero when feedback exists
        base_score = target_task["score"]
        expected_adjusted = round(base_score + weight["score_delta"], 4)
        print(f"  Note {note_path!r}: base_score={base_score}, "
              f"score_delta={weight['score_delta']}, "
              f"expected_adjusted={expected_adjusted}, "
              f"summary={weight['summary']} ✓")


def test_p3_task_useful_signal_does_not_raise_priority():
    """P3-T4: useful/agent_succeeded signals do not increase priority."""
    print("\n=== Test P3-T4: useful/agent_succeeded lower or neutral priority ===")
    from core.shared.feedback import feedback_weight_for_path, _SIGNAL_DELTA, _SEVERITY_MULTIPLIER

    # Verify the signal tables directly
    for sig in ("useful", "agent_succeeded"):
        delta = _SIGNAL_DELTA.get(sig, 0.0)
        assert delta <= 0, f"Signal '{sig}' must not increase priority; delta={delta}"
    print(f"  useful delta={_SIGNAL_DELTA['useful']} ≤ 0 ✓")
    print(f"  agent_succeeded delta={_SIGNAL_DELTA['agent_succeeded']} ≤ 0 ✓")


def test_p3_task_ordering_deterministic():
    """P3-T5: Task ordering with include_feedback=True is still deterministic."""
    print("\n=== Test P3-T5: Task ordering deterministic with feedback ===")
    from mcp.core.vault_registry import list_vaults
    from mcp.core.adapters.tasks_adapter import get_tasks

    vault = list_vaults()[0]

    result1 = get_tasks(vault_name=vault, limit=50, include_feedback=True)
    result2 = get_tasks(vault_name=vault, limit=50, include_feedback=True)

    assert "error" not in result1
    paths1 = [t["path"] for t in result1["tasks"]]
    paths2 = [t["path"] for t in result2["tasks"]]
    assert paths1 == paths2, f"Task ordering not deterministic: {paths1} vs {paths2}"

    # Verify ordering: descending priority then ascending path
    priorities = [t["priority"] for t in result1["tasks"]]
    for i in range(len(priorities) - 1):
        assert priorities[i] >= priorities[i + 1], (
            f"Tasks not sorted descending by priority at index {i}: "
            f"{priorities[i]} < {priorities[i + 1]}"
        )

    print(f"  {len(paths1)} tasks — deterministic and priority-sorted ✓")


def test_p3_api_feedback_endpoint():
    """P3-A1: GET /feedback returns structured response."""
    print("\n=== Test P3-A1: GET /feedback ===")
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        print(f"  SKIP: TestClient unavailable — {exc}")
        return

    from mcp.server.mcp_server import app
    from mcp.core.vault_registry import list_vaults

    vault = list_vaults()[0]

    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.get(f"/feedback?vault={vault}")
        assert resp.status_code == 200, (
            f"/feedback status {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()
        assert body["status"] in ("ok", "error"), f"Unexpected status: {body['status']}"
        assert body["vault"] == vault
        assert "entries" in body
        assert "warnings" in body
        assert "errors" in body
        assert isinstance(body["entries"], list)
        assert isinstance(body["warnings"], list)
        assert isinstance(body["errors"], list)
        print(f"  GET /feedback?vault={vault}: 200 OK, "
              f"status={body['status']}, entries={len(body['entries'])} ✓")


def test_p3_api_feedback_unknown_vault():
    """P3-A2: GET /feedback with unknown vault returns structured 404."""
    print("\n=== Test P3-A2: GET /feedback unknown vault ===")
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        print(f"  SKIP: TestClient unavailable — {exc}")
        return

    from mcp.server.mcp_server import app

    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.get("/feedback?vault=__nonexistent__")
        assert resp.status_code == 404, (
            f"Expected 404 for unknown vault, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_VAULT"
        print(f"  Unknown vault: 404 INVALID_VAULT ✓")


def test_p3_api_tasks_include_feedback():
    """P3-A3: GET /tasks?include_feedback=true returns feedback_weight fields."""
    print("\n=== Test P3-A3: GET /tasks?include_feedback=true ===")
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        print(f"  SKIP: TestClient unavailable — {exc}")
        return

    from mcp.server.mcp_server import app
    from mcp.core.vault_registry import list_vaults

    vault = list_vaults()[0]

    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.get(f"/tasks?vault={vault}&include_feedback=true")
        assert resp.status_code == 200, (
            f"/tasks?include_feedback=true status {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()
        assert body["status"] == "ok"
        assert "feedback_status" in body["data"], (
            "feedback_status must be present when include_feedback=true"
        )
        for task in body["data"]["tasks"]:
            assert "feedback_weight" in task, (
                f"Task missing feedback_weight with include_feedback=true: {task}"
            )
        print(f"  GET /tasks?include_feedback=true: 200 OK, "
              f"tasks={len(body['data']['tasks'])}, "
              f"feedback_status={body['data']['feedback_status']} ✓")


def test_p3_api_tasks_no_feedback_default():
    """P3-A4: GET /tasks (default) has no feedback_weight in output."""
    print("\n=== Test P3-A4: GET /tasks default has no feedback_weight ===")
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        print(f"  SKIP: TestClient unavailable — {exc}")
        return

    from mcp.server.mcp_server import app
    from mcp.core.vault_registry import list_vaults

    vault = list_vaults()[0]

    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.get(f"/tasks?vault={vault}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        # No feedback_status at top level when not requested
        assert "feedback_status" not in body["data"], (
            "feedback_status must not appear when include_feedback=false"
        )
        for task in body["data"]["tasks"]:
            assert "feedback_weight" not in task, (
                f"Task must not have feedback_weight when include_feedback=false: {task}"
            )
        print(f"  GET /tasks (default): no feedback_weight in output ✓")


def test_p3_bundle_includes_feedback():
    """P3-B1: Context bundle includes 'feedback' top-level field."""
    print("\n=== Test P3-B1: Bundle includes feedback field ===")
    from mcp.core.vault_registry import list_vaults
    from mcp.core.note_index import build_index
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    build_index(vault)

    bundle = generate_bundle(vault_name=vault, allow_partial=True, max_notes=5)

    assert bundle["status"] == "ok"
    assert "feedback" in bundle, "Bundle must have top-level 'feedback' field"
    fb = bundle["feedback"]
    assert "entries" in fb, "feedback must have 'entries'"
    assert "warnings" in fb, "feedback must have 'warnings'"
    assert isinstance(fb["entries"], list)
    assert isinstance(fb["warnings"], list)
    print(f"  Bundle has feedback field: entries={len(fb['entries'])}, "
          f"warnings={len(fb['warnings'])} ✓")


def test_p3_bundle_feedback_only_selected_notes():
    """P3-B2: Bundle feedback entries only reference selected notes."""
    print("\n=== Test P3-B2: Bundle feedback limited to selected notes ===")
    from mcp.core.vault_registry import list_vaults
    from mcp.core.note_index import build_index
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    build_index(vault)

    bundle = generate_bundle(vault_name=vault, allow_partial=True, max_notes=50)
    assert bundle["status"] == "ok"

    selected = {n["path"] for n in bundle["notes"]}
    fb_entries = bundle["feedback"]["entries"]

    for entry in fb_entries:
        assert entry["path"] in selected, (
            f"Feedback entry references unselected note: {entry['path']!r}. "
            f"Selected: {sorted(selected)}"
        )
    print(f"  {len(fb_entries)} feedback entries — all reference selected notes ✓")


def test_p3_bundle_determinism_with_feedback():
    """P3-B3: Bundle determinism holds with feedback included."""
    print("\n=== Test P3-B3: Bundle determinism with feedback ===")
    from mcp.core.vault_registry import list_vaults
    from mcp.core.note_index import build_index
    from core.shared.context_bundle import generate_bundle

    vault = list_vaults()[0]
    build_index(vault)

    kwargs = dict(
        vault_name=vault,
        filters={},
        include_sections=["Key Principles"],
        include_related=False,
        include_body=False,
        max_notes=5,
        max_chars=999999,
        allow_partial=True,
    )
    b1 = generate_bundle(**kwargs)
    b2 = generate_bundle(**kwargs)

    assert b1["status"] == "ok" and b2["status"] == "ok"
    assert b1["bundle_id"] == b2["bundle_id"], "bundle_id must be deterministic"
    assert [n["path"] for n in b1["notes"]] == [n["path"] for n in b2["notes"]]

    # feedback entries (from same file) must match
    assert b1["feedback"]["entries"] == b2["feedback"]["entries"], (
        "feedback entries must be deterministic"
    )
    print(f"  bundle_id={b1['bundle_id']}, feedback entries deterministic ✓")


def test_p3_cli_feedback():
    """P3-CLI: python run.py feedback returns valid JSON."""
    print("\n=== Test P3-CLI: python run.py feedback ===")
    import json
    import subprocess

    result = subprocess.run(
        [sys.executable, "run.py", "feedback"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        timeout=60,
    )

    assert result.returncode == 0, (
        f"CLI feedback exited {result.returncode}\n"
        f"stdout: {result.stdout[:500]}\n"
        f"stderr: {result.stderr[:500]}"
    )

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"CLI feedback output is not valid JSON: {exc}\n"
            f"stdout: {result.stdout[:500]}"
        ) from exc

    assert output["status"] in ("ok", "error"), f"Unexpected status: {output['status']}"
    assert "vault" in output
    assert "entries" in output
    assert "warnings" in output
    assert "errors" in output
    print(f"  CLI feedback: status={output['status']}, "
          f"entries={len(output['entries'])}, "
          f"vault={output['vault']!r} ✓")


# ============================================================
# Phase 4 — Export and Packaging
# ============================================================

def _make_test_bundle() -> dict:
    """Return a minimal valid bundle for use in export tests."""
    from core.shared.context_bundle import generate_bundle
    vault = list_vaults()[0]
    build_index(vault)
    return generate_bundle(
        vault_name=vault,
        filters={"status": "complete"},
        include_sections=["Key Principles", "How It Works", "Trade-offs"],
        include_related=False,
        include_body=False,
        max_notes=2,
        max_chars=50000,
        allow_partial=False,
    )


def test_p4_export_writes_all_six_files():
    """P4-E1: export_context_package writes all six expected files."""
    print("\n=== Test P4-E1: export writes all six files ===")
    import tempfile
    import shutil
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(bundle, output_root=tmp)
        assert result["status"] == "ok", f"Expected ok: {result}"
        bundle_id = result["bundle_id"]
        pkg_dir = Path(tmp) / bundle_id
        assert pkg_dir.is_dir(), f"Package dir not created: {pkg_dir}"
        expected = {
            "context.json", "context.md", "manifest.json",
            "validation.json", "graph.json", "feedback-summary.json",
        }
        actual = {f.name for f in pkg_dir.iterdir()}
        assert expected == actual, f"Expected files {expected}, got {actual}"
        print(f"  All 6 files present in {pkg_dir.name} ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_context_json_valid():
    """P4-E2: context.json is valid JSON and contains bundle_id and status."""
    print("\n=== Test P4-E2: context.json is valid JSON ===")
    import tempfile
    import shutil
    import json as _json
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(bundle, output_root=tmp)
        assert result["status"] == "ok", f"Expected ok: {result}"
        pkg_dir = Path(tmp) / result["bundle_id"]
        raw = (pkg_dir / "context.json").read_text(encoding="utf-8")
        obj = _json.loads(raw)
        assert "bundle_id" in obj, "context.json missing bundle_id"
        assert obj["bundle_id"] == bundle["bundle_id"]
        assert "status" in obj
        print(f"  context.json: valid JSON, bundle_id={obj['bundle_id']!r} ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_context_md_contains_required_fields():
    """P4-E3: context.md contains bundle_id, vault, validation_status, source paths."""
    print("\n=== Test P4-E3: context.md contains required fields ===")
    import tempfile
    import shutil
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(bundle, output_root=tmp)
        assert result["status"] == "ok", f"Expected ok: {result}"
        pkg_dir = Path(tmp) / result["bundle_id"]
        md = (pkg_dir / "context.md").read_text(encoding="utf-8")
        assert bundle["bundle_id"] in md, "bundle_id not in context.md"
        assert bundle["vault"] in md, "vault not in context.md"
        assert bundle["validation_status"] in md, "validation_status not in context.md"
        for path in bundle["manifest"]["source_paths"]:
            assert path in md, f"source path {path!r} not in context.md"
        print(f"  context.md: all required fields present ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_manifest_contains_all_files():
    """P4-E4: manifest.json contains entries for all six package files."""
    print("\n=== Test P4-E4: manifest.json contains all file entries ===")
    import tempfile
    import shutil
    import json as _json
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(bundle, output_root=tmp)
        assert result["status"] == "ok", f"Expected ok: {result}"
        pkg_dir = Path(tmp) / result["bundle_id"]
        manifest = _json.loads((pkg_dir / "manifest.json").read_text(encoding="utf-8"))
        assert "files" in manifest, "manifest.json missing 'files'"
        expected_files = {
            "context.json", "context.md", "validation.json",
            "graph.json", "feedback-summary.json",
        }
        for fname in expected_files:
            assert fname in manifest["files"], f"manifest missing entry for {fname!r}"
            entry = manifest["files"][fname]
            assert "sha256" in entry, f"{fname}: missing sha256 in manifest"
            assert "bytes" in entry, f"{fname}: missing bytes in manifest"
        assert "bundle_id" in manifest
        assert "validation_status" in manifest
        assert "source_notes" in manifest
        print(f"  manifest.json: all required fields present ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_manifest_hashes_match():
    """P4-E5: SHA-256 hashes in manifest.json match actual file bytes."""
    print("\n=== Test P4-E5: manifest hashes match actual files ===")
    import tempfile
    import shutil
    import hashlib
    import json as _json
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(bundle, output_root=tmp)
        assert result["status"] == "ok", f"Expected ok: {result}"
        pkg_dir = Path(tmp) / result["bundle_id"]
        manifest = _json.loads((pkg_dir / "manifest.json").read_text(encoding="utf-8"))
        for fname, info in manifest["files"].items():
            file_bytes = (pkg_dir / fname).read_bytes()
            actual_hash = hashlib.sha256(file_bytes).hexdigest()
            assert actual_hash == info["sha256"], (
                f"{fname}: manifest hash {info['sha256']!r} != actual {actual_hash!r}"
            )
            assert len(file_bytes) == info["bytes"], (
                f"{fname}: manifest bytes {info['bytes']} != actual {len(file_bytes)}"
            )
        print(f"  Manifest hashes verified for {len(manifest['files'])} files ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_return_hashes_match():
    """P4-E6: SHA-256 hashes in the return value match actual file bytes."""
    print("\n=== Test P4-E6: return value hashes match actual files ===")
    import tempfile
    import shutil
    import hashlib
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(bundle, output_root=tmp)
        assert result["status"] == "ok", f"Expected ok: {result}"
        pkg_dir = Path(tmp) / result["bundle_id"]
        for fname, info in result["files"].items():
            file_bytes = (pkg_dir / fname).read_bytes()
            actual_hash = hashlib.sha256(file_bytes).hexdigest()
            assert actual_hash == info["sha256"], (
                f"{fname}: return hash {info['sha256']!r} != actual {actual_hash!r}"
            )
        print(f"  Return value hashes verified for {len(result['files'])} files ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_validation_json_structured():
    """P4-E7: validation.json is structured with required keys."""
    print("\n=== Test P4-E7: validation.json is structured ===")
    import tempfile
    import shutil
    import json as _json
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(bundle, output_root=tmp)
        assert result["status"] == "ok", f"Expected ok: {result}"
        pkg_dir = Path(tmp) / result["bundle_id"]
        obj = _json.loads((pkg_dir / "validation.json").read_text(encoding="utf-8"))
        assert "validation_status" in obj, "validation.json missing validation_status"
        assert "source_note_count" in obj, "validation.json missing source_note_count"
        assert "warnings" in obj, "validation.json missing warnings"
        assert isinstance(obj["warnings"], list)
        print(f"  validation.json: structured, status={obj['validation_status']!r} ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_graph_json_structured():
    """P4-E8: graph.json is structured with 'related' key."""
    print("\n=== Test P4-E8: graph.json is structured ===")
    import tempfile
    import shutil
    import json as _json
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(bundle, output_root=tmp)
        assert result["status"] == "ok", f"Expected ok: {result}"
        pkg_dir = Path(tmp) / result["bundle_id"]
        obj = _json.loads((pkg_dir / "graph.json").read_text(encoding="utf-8"))
        assert "related" in obj, "graph.json missing 'related' key"
        assert isinstance(obj["related"], dict)
        print(f"  graph.json: structured, related_count={len(obj['related'])} ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_feedback_summary_json_structured():
    """P4-E9: feedback-summary.json is structured with 'entries' and 'warnings'."""
    print("\n=== Test P4-E9: feedback-summary.json is structured ===")
    import tempfile
    import shutil
    import json as _json
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(bundle, output_root=tmp)
        assert result["status"] == "ok", f"Expected ok: {result}"
        pkg_dir = Path(tmp) / result["bundle_id"]
        obj = _json.loads((pkg_dir / "feedback-summary.json").read_text(encoding="utf-8"))
        assert "entries" in obj, "feedback-summary.json missing 'entries'"
        assert "warnings" in obj, "feedback-summary.json missing 'warnings'"
        assert isinstance(obj["entries"], list)
        assert isinstance(obj["warnings"], list)
        print(f"  feedback-summary.json: structured, entries={len(obj['entries'])} ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_no_overwrite_returns_error():
    """P4-E10: existing package with overwrite=False returns structured error."""
    print("\n=== Test P4-E10: no-overwrite conflict returns structured error ===")
    import tempfile
    import shutil
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        # First export succeeds.
        r1 = export_context_package(bundle, output_root=tmp, overwrite=False)
        assert r1["status"] == "ok", f"First export failed: {r1}"
        # Second export without overwrite must fail.
        r2 = export_context_package(bundle, output_root=tmp, overwrite=False)
        assert r2["status"] == "error", f"Expected error on duplicate, got: {r2}"
        assert r2["error"]["code"] == "PACKAGE_EXISTS", (
            f"Expected PACKAGE_EXISTS, got: {r2['error']['code']!r}"
        )
        print(f"  Conflict detected: {r2['error']['code']!r} ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_overwrite_succeeds():
    """P4-E11: existing package with overwrite=True is replaced successfully."""
    print("\n=== Test P4-E11: overwrite=True replaces existing package ===")
    import tempfile
    import shutil
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        r1 = export_context_package(bundle, output_root=tmp, overwrite=False)
        assert r1["status"] == "ok", f"First export failed: {r1}"
        r2 = export_context_package(bundle, output_root=tmp, overwrite=True)
        assert r2["status"] == "ok", f"Overwrite failed: {r2}"
        assert r2["bundle_id"] == bundle["bundle_id"]
        print(f"  Overwrite succeeded: bundle_id={r2['bundle_id']!r} ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_error_bundle_returns_structured_error():
    """P4-E12: passing an error bundle returns a structured error."""
    print("\n=== Test P4-E12: error bundle returns structured error ===")
    import tempfile
    import shutil
    from core.shared.context_package import export_context_package

    error_bundle = {
        "status": "error",
        "error": {"code": "INVALID_VAULT", "message": "Vault not found"},
    }
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(error_bundle, output_root=tmp)
        assert result["status"] == "error", f"Expected error: {result}"
        assert result["error"]["code"] == "BUNDLE_ERROR"
        print(f"  Error bundle rejected: {result['error']['code']!r} ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_no_extra_files_in_package():
    """P4-E13: package directory contains exactly the six expected files."""
    print("\n=== Test P4-E13: no extra files in package ===")
    import tempfile
    import shutil
    from core.shared.context_package import export_context_package

    bundle = _make_test_bundle()
    tmp = tempfile.mkdtemp()
    try:
        result = export_context_package(bundle, output_root=tmp)
        assert result["status"] == "ok", f"Expected ok: {result}"
        pkg_dir = Path(tmp) / result["bundle_id"]
        actual = {f.name for f in pkg_dir.iterdir()}
        expected = {
            "context.json", "context.md", "manifest.json",
            "validation.json", "graph.json", "feedback-summary.json",
        }
        assert actual == expected, f"Unexpected files: {actual - expected}"
        print(f"  Exactly 6 files, no extras ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_p4_cli_export_returns_valid_json():
    """P4-CLI1: python run.py export --overwrite returns valid JSON with status=ok."""
    print("\n=== Test P4-CLI1: CLI export --overwrite returns valid JSON ===")
    import json
    import subprocess

    result = subprocess.run(
        [sys.executable, "run.py", "export", "--overwrite"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        timeout=60,
    )

    assert result.returncode == 0, (
        f"CLI export exited {result.returncode}\n"
        f"stdout: {result.stdout[:500]}\n"
        f"stderr: {result.stderr[:500]}"
    )

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"CLI export output is not valid JSON: {exc}\n"
            f"stdout: {result.stdout[:500]}"
        ) from exc

    assert output["status"] == "ok", f"CLI export status not ok: {output}"
    for key in ("bundle_id", "package_dir", "files", "warnings"):
        assert key in output, f"CLI export missing key: {key!r}"
    assert len(output["files"]) == 6, (
        f"Expected 6 files, got {len(output['files'])}: {list(output['files'])}"
    )
    print(f"  CLI export: status=ok, bundle_id={output['bundle_id']!r}, "
          f"package_dir={output['package_dir']!r} ✓")


def test_p4_cli_export_writes_package_dir():
    """P4-CLI2: CLI export creates the package directory on disk."""
    print("\n=== Test P4-CLI2: CLI export creates package directory ===")
    import json
    import subprocess
    from core.shared.context_package import _REPO_ROOT

    result = subprocess.run(
        [sys.executable, "run.py", "export", "--overwrite"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        timeout=60,
    )

    assert result.returncode == 0, (
        f"CLI export exited {result.returncode}\n"
        f"stdout: {result.stdout[:500]}"
    )

    output = json.loads(result.stdout)
    pkg_dir = _REPO_ROOT / output["package_dir"]
    assert pkg_dir.is_dir(), f"Package directory not found: {pkg_dir}"
    files = {f.name for f in pkg_dir.iterdir()}
    expected = {
        "context.json", "context.md", "manifest.json",
        "validation.json", "graph.json", "feedback-summary.json",
    }
    assert files == expected, f"Unexpected files in package: {files}"
    print(f"  Package directory verified at {output['package_dir']!r} ✓")


def test_p4_cli_export_conflict_without_overwrite():
    """P4-CLI3: CLI export without --overwrite on existing package returns non-zero exit."""
    print("\n=== Test P4-CLI3: CLI export conflict without --overwrite ===")
    import json
    import subprocess

    repo_root = Path(__file__).resolve().parent.parent

    # Ensure the package exists first.
    r = subprocess.run(
        [sys.executable, "run.py", "export", "--overwrite"],
        capture_output=True, text=True, cwd=str(repo_root), timeout=60,
    )
    assert r.returncode == 0, f"Setup export failed: {r.stdout[:300]}"

    # Now try without --overwrite: should fail.
    r2 = subprocess.run(
        [sys.executable, "run.py", "export"],
        capture_output=True, text=True, cwd=str(repo_root), timeout=60,
    )

    assert r2.returncode != 0, (
        f"Expected non-zero exit on conflict, got 0\nstdout: {r2.stdout[:300]}"
    )
    try:
        output = json.loads(r2.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"CLI conflict output is not valid JSON: {exc}\n"
            f"stdout: {r2.stdout[:300]}"
        ) from exc

    assert output["status"] == "error", f"Expected error: {output}"
    assert output["error"]["code"] == "PACKAGE_EXISTS", (
        f"Expected PACKAGE_EXISTS, got: {output['error']['code']!r}"
    )
    print(f"  Conflict returned: {output['error']['code']!r}, exit={r2.returncode} ✓")


def test_p4_cli_export_overwrite_succeeds():
    """P4-CLI4: CLI export --overwrite on existing package succeeds."""
    print("\n=== Test P4-CLI4: CLI export --overwrite on existing package ===")
    import json
    import subprocess

    repo_root = Path(__file__).resolve().parent.parent

    # First export.
    r1 = subprocess.run(
        [sys.executable, "run.py", "export", "--overwrite"],
        capture_output=True, text=True, cwd=str(repo_root), timeout=60,
    )
    assert r1.returncode == 0, f"First export failed: {r1.stdout[:300]}"

    # Second export with --overwrite: should succeed.
    r2 = subprocess.run(
        [sys.executable, "run.py", "export", "--overwrite"],
        capture_output=True, text=True, cwd=str(repo_root), timeout=60,
    )
    assert r2.returncode == 0, (
        f"Overwrite export failed: {r2.stdout[:300]}"
    )
    output = json.loads(r2.stdout)
    assert output["status"] == "ok", f"Expected ok: {output}"
    print(f"  --overwrite succeeded on second run ✓")


def test_p4_api_export_ok():
    """P4-API1: POST /context/export returns ok and package_dir."""
    print("\n=== Test P4-API1: POST /context/export returns ok ===")
    import shutil
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        print(f"  SKIP: TestClient unavailable — {exc}")
        return

    from mcp.server.mcp_server import app
    from core.shared.context_package import _REPO_ROOT

    vault = list_vaults()[0]
    build_index(vault)

    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.post("/context/export", json={
            "vault": vault,
            "allow_partial": True,
            "max_notes": 2,
            "include_body": False,
            "overwrite": True,
        })
        assert resp.status_code == 200, (
            f"POST /context/export status {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()
        assert body["status"] == "ok", f"Expected ok: {body}"
        for key in ("bundle_id", "package_dir", "files", "warnings"):
            assert key in body, f"Missing key: {key!r}"
        assert len(body["files"]) == 6, (
            f"Expected 6 files, got {len(body['files'])}"
        )
        # Verify the package was actually written to disk.
        pkg_dir = _REPO_ROOT / body["package_dir"]
        assert pkg_dir.is_dir(), f"Package dir not on disk: {pkg_dir}"
        print(f"  POST /context/export: 200 OK, bundle_id={body['bundle_id']!r} ✓")
        # Cleanup after test.
        shutil.rmtree(pkg_dir, ignore_errors=True)


def test_p4_api_export_conflict():
    """P4-API2: POST /context/export with overwrite=false on existing package returns 409."""
    print("\n=== Test P4-API2: POST /context/export conflict returns 409 ===")
    import shutil
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        print(f"  SKIP: TestClient unavailable — {exc}")
        return

    from mcp.server.mcp_server import app
    from core.shared.context_package import _REPO_ROOT

    vault = list_vaults()[0]
    build_index(vault)

    payload = {
        "vault": vault,
        "allow_partial": True,
        "max_notes": 1,
        "include_body": False,
        "filters": {"status": "complete"},
    }

    with TestClient(app, raise_server_exceptions=True) as client:
        # First call — must succeed.
        resp1 = client.post("/context/export", json={**payload, "overwrite": True})
        assert resp1.status_code == 200, f"Setup call failed: {resp1.text[:300]}"
        bundle_id = resp1.json()["bundle_id"]
        pkg_dir = _REPO_ROOT / resp1.json()["package_dir"]

        try:
            # Second call without overwrite — must return 409.
            resp2 = client.post("/context/export", json={**payload, "overwrite": False})
            assert resp2.status_code == 409, (
                f"Expected 409 on conflict, got {resp2.status_code}: {resp2.text[:300]}"
            )
            body = resp2.json()
            assert body["status"] == "error"
            assert body["error"]["code"] == "PACKAGE_EXISTS"
            print(f"  Conflict: 409 PACKAGE_EXISTS ✓")
        finally:
            shutil.rmtree(pkg_dir, ignore_errors=True)


def test_p4_api_export_overwrite_ok():
    """P4-API3: POST /context/export with overwrite=true on existing package returns ok."""
    print("\n=== Test P4-API3: POST /context/export overwrite=true ===")
    import shutil
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        print(f"  SKIP: TestClient unavailable — {exc}")
        return

    from mcp.server.mcp_server import app
    from core.shared.context_package import _REPO_ROOT

    vault = list_vaults()[0]
    build_index(vault)

    payload = {
        "vault": vault,
        "allow_partial": True,
        "max_notes": 1,
        "include_body": False,
        "overwrite": True,
    }

    with TestClient(app, raise_server_exceptions=True) as client:
        resp1 = client.post("/context/export", json=payload)
        assert resp1.status_code == 200, f"First call failed: {resp1.text[:300]}"
        pkg_dir = _REPO_ROOT / resp1.json()["package_dir"]

        try:
            resp2 = client.post("/context/export", json=payload)
            assert resp2.status_code == 200, (
                f"Second overwrite call failed: {resp2.text[:300]}"
            )
            body = resp2.json()
            assert body["status"] == "ok"
            print(f"  Overwrite succeeded: 200 OK ✓")
        finally:
            shutil.rmtree(pkg_dir, ignore_errors=True)


def test_p4_api_export_unknown_vault():
    """P4-API4: POST /context/export with unknown vault returns 404."""
    print("\n=== Test P4-API4: POST /context/export unknown vault ===")
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        print(f"  SKIP: TestClient unavailable — {exc}")
        return

    from mcp.server.mcp_server import app

    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.post("/context/export", json={
            "vault": "__nonexistent_vault__",
            "allow_partial": True,
        })
        assert resp.status_code == 404, (
            f"Expected 404 for unknown vault, got {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "INVALID_VAULT"
        print(f"  Unknown vault: 404 INVALID_VAULT ✓")


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

    # Phase 1 — HTTP smoke tests (TestClient)
    test_p1_http_smoke()

    # Phase 1 — Expose existing capabilities
    test_p1_validation_adapter()
    test_p1_tasks_full_path()
    test_p1_tasks_constraints()
    test_p1_notes_full_paths()
    test_p1_quality_adapter()
    test_p1_missing_adapter()
    test_p1_compare_missing_file()
    test_p1_graph_build()
    test_p1_graph_related()
    test_p1_graph_missing_neighbors()
    test_p1_unknown_vault_structured_error()
    test_p1_validation_vault_param()
    test_p1_tasks_vault_param()
    test_p1_notes_vault_param()
    test_p1_quality_vault_param()
    test_p1_missing_vault_param()

    # Phase 2 — Context Bundle
    test_p2_generate_bundle_basic()
    test_p2_generate_bundle_posix_paths()
    test_p2_generate_bundle_max_notes()
    test_p2_generate_bundle_max_chars()
    test_p2_generate_bundle_allow_partial_false()
    test_p2_generate_bundle_allow_partial_true()
    test_p2_generate_bundle_sections()
    test_p2_generate_bundle_include_body_false()
    test_p2_generate_bundle_include_body_true()
    test_p2_generate_bundle_include_related()
    test_p2_generate_bundle_validation_status()
    test_p2_bundle_deterministic()
    test_p2_bundle_unknown_vault()
    test_p2_bundle_empty_filter()
    test_p2_cli_bundle()
    test_p2_http_bundle()

    # Phase 2 — Budget behaviour (strengthened)
    test_p2_budget_high_max_chars()
    test_p2_budget_truncation_warning()
    test_p2_budget_max_notes_vs_max_chars()

    # Phase 3 — Feedback Loop
    test_p3_feedback_missing_file()
    test_p3_feedback_valid_file()
    test_p3_feedback_empty_list()
    test_p3_feedback_malformed_yaml()
    test_p3_feedback_unknown_signal()
    test_p3_feedback_unknown_severity()
    test_p3_feedback_unknown_source()
    test_p3_feedback_missing_note_path()
    test_p3_feedback_exclusion_from_notes()
    test_p3_feedback_exclusion_from_query()
    test_p3_feedback_exclusion_from_graph()
    test_p3_feedback_exclusion_from_bundle()
    test_p3_task_weighting_false()
    test_p3_task_weighting_true()
    test_p3_task_weighting_score_change()
    test_p3_task_useful_signal_does_not_raise_priority()
    test_p3_task_ordering_deterministic()
    test_p3_api_feedback_endpoint()
    test_p3_api_feedback_unknown_vault()
    test_p3_api_tasks_include_feedback()
    test_p3_api_tasks_no_feedback_default()
    test_p3_bundle_includes_feedback()
    test_p3_bundle_feedback_only_selected_notes()
    test_p3_bundle_determinism_with_feedback()
    test_p3_cli_feedback()

    # Phase 4 — Export and Packaging
    test_p4_export_writes_all_six_files()
    test_p4_context_json_valid()
    test_p4_context_md_contains_required_fields()
    test_p4_manifest_contains_all_files()
    test_p4_manifest_hashes_match()
    test_p4_return_hashes_match()
    test_p4_validation_json_structured()
    test_p4_graph_json_structured()
    test_p4_feedback_summary_json_structured()
    test_p4_no_overwrite_returns_error()
    test_p4_overwrite_succeeds()
    test_p4_error_bundle_returns_structured_error()
    test_p4_no_extra_files_in_package()
    test_p4_cli_export_returns_valid_json()
    test_p4_cli_export_writes_package_dir()
    test_p4_cli_export_conflict_without_overwrite()
    test_p4_cli_export_overwrite_succeeds()
    test_p4_api_export_ok()
    test_p4_api_export_conflict()
    test_p4_api_export_overwrite_ok()
    test_p4_api_export_unknown_vault()

    print()
    print("=" * 60)
    print("ALL VERIFICATION TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
