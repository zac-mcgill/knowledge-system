"""
drift_check.py — Integrity Baseline Drift Detector

Compares SHA-256 hashes of critical vault scripts against the locked
baseline. Also performs TYPE_REGISTRY and section heading drift checks.

Usage:
    python drift_check.py          Check all vaults
    python drift_check.py -v       Verbose (show per-file results)

Exit codes:
    0  PASS — no drift detected
    1  FAIL — one or more checks failed

Python: 3.10+ (stdlib only)
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path

# ============================================================================
# BASELINE — updated after SE decomposition (10-vault system)
# ============================================================================

VAULT_ROOT = Path(__file__).resolve().parent.parent / "demo-vault"

VAULT_NAMES: tuple[str, ...] = (
    "Databases", "Cyber Security", "Networking", "Mathematics for Computing",
    "Foundations", "Core Engineering", "Systems", "Integration",
    "Operations", "Tooling",
)

TRACKED_FILES: tuple[str, ...] = (
    "vault_schema.py",
    "validate_vault.py",
    "inject_frontmatter.py",
    "generate_report.py",
    "analyse_vault.py",
    "compare_reports.py",
    "upgrade_vault.py",
    "query_vault.py",
    "discover_missing.py",
)

BASELINE: dict[str, dict[str, str]] = {
    "Databases": {
        "vault_schema.py":       "BCAEAEB739ABA7F7457265C736D059E57FC9C6B4DE35432A2578DFFF410F883A",
        "validate_vault.py":     "347D7F98C8602D0D95A61BBF83D5119D969D445650579033AB27DE14BFBCEF21",
        "inject_frontmatter.py": "8F340F963339BA3CE122A64B5E735635DAC6FAA569899687133B2014338728DF",
        "generate_report.py":    "E5D5965B2EECB7502C9680604CFA34B5AB969E99112468836089F54EDC833131",
        "analyse_vault.py":      "C1E943169D7D7A9AA28CBDBFC6B7275787E872675741B90D291AE8E5A55CCF47",
        "compare_reports.py":    "DB38700CF7E7B03A22A6A1D9492DE4246A199A178DFD71FA48ECD2744F5FB637",
        "upgrade_vault.py":      "5A9C03C01CE5C18AA152CCF611C4C5044F7AD9B330B089980C0D243237DA94A4",
        "query_vault.py":        "C51FBA09D873AB9BB7CA019032E6915C67154038D29A17A7ED9911123773B6C9",
        "discover_missing.py":   "6E4FAFE3DBE6565A73831A748A0AB073EC2F76ED8038AAF84F5FF89F62274E06",
    },
    "Cyber Security": {
        "vault_schema.py":       "64504234085CE4DE0B3BA4B83D8F87C0922C0685F1CF668D2EA6339240FF26F9",
        "validate_vault.py":     "347D7F98C8602D0D95A61BBF83D5119D969D445650579033AB27DE14BFBCEF21",
        "inject_frontmatter.py": "8F340F963339BA3CE122A64B5E735635DAC6FAA569899687133B2014338728DF",
        "generate_report.py":    "E5D5965B2EECB7502C9680604CFA34B5AB969E99112468836089F54EDC833131",
        "analyse_vault.py":      "C1E943169D7D7A9AA28CBDBFC6B7275787E872675741B90D291AE8E5A55CCF47",
        "compare_reports.py":    "DB38700CF7E7B03A22A6A1D9492DE4246A199A178DFD71FA48ECD2744F5FB637",
        "upgrade_vault.py":      "5A9C03C01CE5C18AA152CCF611C4C5044F7AD9B330B089980C0D243237DA94A4",
        "query_vault.py":        "C51FBA09D873AB9BB7CA019032E6915C67154038D29A17A7ED9911123773B6C9",
        "discover_missing.py":   "6E4FAFE3DBE6565A73831A748A0AB073EC2F76ED8038AAF84F5FF89F62274E06",
    },
    "Networking": {
        "vault_schema.py":       "BA8F1C8A7896FE5B28AD5731925CD18B7A19F25284E724A2FE04EE07C38F7983",
        "validate_vault.py":     "347D7F98C8602D0D95A61BBF83D5119D969D445650579033AB27DE14BFBCEF21",
        "inject_frontmatter.py": "8F340F963339BA3CE122A64B5E735635DAC6FAA569899687133B2014338728DF",
        "generate_report.py":    "E5D5965B2EECB7502C9680604CFA34B5AB969E99112468836089F54EDC833131",
        "analyse_vault.py":      "C1E943169D7D7A9AA28CBDBFC6B7275787E872675741B90D291AE8E5A55CCF47",
        "compare_reports.py":    "DB38700CF7E7B03A22A6A1D9492DE4246A199A178DFD71FA48ECD2744F5FB637",
        "upgrade_vault.py":      "5A9C03C01CE5C18AA152CCF611C4C5044F7AD9B330B089980C0D243237DA94A4",
        "query_vault.py":        "C51FBA09D873AB9BB7CA019032E6915C67154038D29A17A7ED9911123773B6C9",
        "discover_missing.py":   "6E4FAFE3DBE6565A73831A748A0AB073EC2F76ED8038AAF84F5FF89F62274E06",
    },
    "Mathematics for Computing": {
        "vault_schema.py":       "33950991C69B35570FF3F3D12A3F8010DEFAC853669115ACC672A97A088CA942",
        "validate_vault.py":     "347D7F98C8602D0D95A61BBF83D5119D969D445650579033AB27DE14BFBCEF21",
        "inject_frontmatter.py": "8F340F963339BA3CE122A64B5E735635DAC6FAA569899687133B2014338728DF",
        "generate_report.py":    "E5D5965B2EECB7502C9680604CFA34B5AB969E99112468836089F54EDC833131",
        "analyse_vault.py":      "C1E943169D7D7A9AA28CBDBFC6B7275787E872675741B90D291AE8E5A55CCF47",
        "compare_reports.py":    "DB38700CF7E7B03A22A6A1D9492DE4246A199A178DFD71FA48ECD2744F5FB637",
        "upgrade_vault.py":      "5A9C03C01CE5C18AA152CCF611C4C5044F7AD9B330B089980C0D243237DA94A4",
        "query_vault.py":        "C51FBA09D873AB9BB7CA019032E6915C67154038D29A17A7ED9911123773B6C9",
        "discover_missing.py":   "6E4FAFE3DBE6565A73831A748A0AB073EC2F76ED8038AAF84F5FF89F62274E06",
    },
    "Foundations": {
        "vault_schema.py":       "282094CFF04B4FE21E0FD7E6F4ACD148A67C823AF2E77BF74886CB5A186B5FE0",
        "validate_vault.py":     "347D7F98C8602D0D95A61BBF83D5119D969D445650579033AB27DE14BFBCEF21",
        "inject_frontmatter.py": "8F340F963339BA3CE122A64B5E735635DAC6FAA569899687133B2014338728DF",
        "generate_report.py":    "E5D5965B2EECB7502C9680604CFA34B5AB969E99112468836089F54EDC833131",
        "analyse_vault.py":      "C1E943169D7D7A9AA28CBDBFC6B7275787E872675741B90D291AE8E5A55CCF47",
        "compare_reports.py":    "DB38700CF7E7B03A22A6A1D9492DE4246A199A178DFD71FA48ECD2744F5FB637",
        "upgrade_vault.py":      "5A9C03C01CE5C18AA152CCF611C4C5044F7AD9B330B089980C0D243237DA94A4",
        "query_vault.py":        "C51FBA09D873AB9BB7CA019032E6915C67154038D29A17A7ED9911123773B6C9",
        "discover_missing.py":   "6E4FAFE3DBE6565A73831A748A0AB073EC2F76ED8038AAF84F5FF89F62274E06",
    },
    "Core Engineering": {
        "vault_schema.py":       "9FCFFF2BE2DD6AC0B5AAA3F9379C6C9ADDA4BBA91AB3ECDB2EBF7D46726A1AFC",
        "validate_vault.py":     "347D7F98C8602D0D95A61BBF83D5119D969D445650579033AB27DE14BFBCEF21",
        "inject_frontmatter.py": "8F340F963339BA3CE122A64B5E735635DAC6FAA569899687133B2014338728DF",
        "generate_report.py":    "E5D5965B2EECB7502C9680604CFA34B5AB969E99112468836089F54EDC833131",
        "analyse_vault.py":      "C1E943169D7D7A9AA28CBDBFC6B7275787E872675741B90D291AE8E5A55CCF47",
        "compare_reports.py":    "DB38700CF7E7B03A22A6A1D9492DE4246A199A178DFD71FA48ECD2744F5FB637",
        "upgrade_vault.py":      "5A9C03C01CE5C18AA152CCF611C4C5044F7AD9B330B089980C0D243237DA94A4",
        "query_vault.py":        "C51FBA09D873AB9BB7CA019032E6915C67154038D29A17A7ED9911123773B6C9",
        "discover_missing.py":   "6E4FAFE3DBE6565A73831A748A0AB073EC2F76ED8038AAF84F5FF89F62274E06",
    },
    "Systems": {
        "vault_schema.py":       "CED4078FA7BDC72D871CC9D26F0C82493F2CB63BE0353C37EFB74EAECA69847A",
        "validate_vault.py":     "347D7F98C8602D0D95A61BBF83D5119D969D445650579033AB27DE14BFBCEF21",
        "inject_frontmatter.py": "8F340F963339BA3CE122A64B5E735635DAC6FAA569899687133B2014338728DF",
        "generate_report.py":    "E5D5965B2EECB7502C9680604CFA34B5AB969E99112468836089F54EDC833131",
        "analyse_vault.py":      "C1E943169D7D7A9AA28CBDBFC6B7275787E872675741B90D291AE8E5A55CCF47",
        "compare_reports.py":    "DB38700CF7E7B03A22A6A1D9492DE4246A199A178DFD71FA48ECD2744F5FB637",
        "upgrade_vault.py":      "5A9C03C01CE5C18AA152CCF611C4C5044F7AD9B330B089980C0D243237DA94A4",
        "query_vault.py":        "C51FBA09D873AB9BB7CA019032E6915C67154038D29A17A7ED9911123773B6C9",
        "discover_missing.py":   "6E4FAFE3DBE6565A73831A748A0AB073EC2F76ED8038AAF84F5FF89F62274E06",
    },
    "Integration": {
        "vault_schema.py":       "80749271E202D85092282BD14AD16A3DFF5A5AD5737933FAEFC256B234C5448F",
        "validate_vault.py":     "347D7F98C8602D0D95A61BBF83D5119D969D445650579033AB27DE14BFBCEF21",
        "inject_frontmatter.py": "8F340F963339BA3CE122A64B5E735635DAC6FAA569899687133B2014338728DF",
        "generate_report.py":    "E5D5965B2EECB7502C9680604CFA34B5AB969E99112468836089F54EDC833131",
        "analyse_vault.py":      "C1E943169D7D7A9AA28CBDBFC6B7275787E872675741B90D291AE8E5A55CCF47",
        "compare_reports.py":    "DB38700CF7E7B03A22A6A1D9492DE4246A199A178DFD71FA48ECD2744F5FB637",
        "upgrade_vault.py":      "5A9C03C01CE5C18AA152CCF611C4C5044F7AD9B330B089980C0D243237DA94A4",
        "query_vault.py":        "C51FBA09D873AB9BB7CA019032E6915C67154038D29A17A7ED9911123773B6C9",
        "discover_missing.py":   "6E4FAFE3DBE6565A73831A748A0AB073EC2F76ED8038AAF84F5FF89F62274E06",
    },
    "Operations": {
        "vault_schema.py":       "46D0E871E861132C3BAF3ECDBF8C94C34C66671AEDA430333DBD6AEC382E6C70",
        "validate_vault.py":     "347D7F98C8602D0D95A61BBF83D5119D969D445650579033AB27DE14BFBCEF21",
        "inject_frontmatter.py": "8F340F963339BA3CE122A64B5E735635DAC6FAA569899687133B2014338728DF",
        "generate_report.py":    "E5D5965B2EECB7502C9680604CFA34B5AB969E99112468836089F54EDC833131",
        "analyse_vault.py":      "C1E943169D7D7A9AA28CBDBFC6B7275787E872675741B90D291AE8E5A55CCF47",
        "compare_reports.py":    "DB38700CF7E7B03A22A6A1D9492DE4246A199A178DFD71FA48ECD2744F5FB637",
        "upgrade_vault.py":      "5A9C03C01CE5C18AA152CCF611C4C5044F7AD9B330B089980C0D243237DA94A4",
        "query_vault.py":        "C51FBA09D873AB9BB7CA019032E6915C67154038D29A17A7ED9911123773B6C9",
        "discover_missing.py":   "6E4FAFE3DBE6565A73831A748A0AB073EC2F76ED8038AAF84F5FF89F62274E06",
    },
    "Tooling": {
        "vault_schema.py":       "73CE7B999C5542DA0EAF0524B68ED5F502722F81731C00B8AF3FD3AC2917C212",
        "validate_vault.py":     "347D7F98C8602D0D95A61BBF83D5119D969D445650579033AB27DE14BFBCEF21",
        "inject_frontmatter.py": "8F340F963339BA3CE122A64B5E735635DAC6FAA569899687133B2014338728DF",
        "generate_report.py":    "E5D5965B2EECB7502C9680604CFA34B5AB969E99112468836089F54EDC833131",
        "analyse_vault.py":      "C1E943169D7D7A9AA28CBDBFC6B7275787E872675741B90D291AE8E5A55CCF47",
        "compare_reports.py":    "DB38700CF7E7B03A22A6A1D9492DE4246A199A178DFD71FA48ECD2744F5FB637",
        "upgrade_vault.py":      "5A9C03C01CE5C18AA152CCF611C4C5044F7AD9B330B089980C0D243237DA94A4",
        "query_vault.py":        "C51FBA09D873AB9BB7CA019032E6915C67154038D29A17A7ED9911123773B6C9",
        "discover_missing.py":   "6E4FAFE3DBE6565A73831A748A0AB073EC2F76ED8038AAF84F5FF89F62274E06",
    },
}

SHARED_ROOT = VAULT_ROOT / "Vault Files" / "Scripts" / "_core" / "shared"

SHARED_FILES: tuple[str, ...] = (
    "validate_vault.py",
    "analyse_vault.py",
    "inject_frontmatter.py",
    "upgrade_vault.py",
    "generate_report.py",
    "compare_reports.py",
    "query_vault.py",
    "discover_missing.py",
)

SHARED_BASELINE: dict[str, str] = {
    "validate_vault.py":       "E2F310857D408EF3854F391461C3E5907BC3F2AE0145E19AF088EED3FFC626B0",
    "analyse_vault.py":        "6F31DEAD17B60A300519ACC7B6213634C3F200BFE0DF18AAC2A3F7171EA425D3",
    "inject_frontmatter.py":   "E05B1B53DEA89A36D2EE16E1805FC154D9AC910D971F65BDA7B0BCFA9E8182F3",
    "upgrade_vault.py":        "693B9956BF7D7691D677638D65F818C656F8A5F95E522772914423DCA10094AF",
    "generate_report.py":      "EE3908B57D0B64CE2090940674CA9D09700D6BF3340804C4ABEAD4D4001A6644",
    "compare_reports.py":      "F63FE336F7F6C6F1655667E87FD60816694563F1C4F499B5B0FBFD117696CDAE",
    "query_vault.py":          "F7826E329F362AB713A0F565EA1DE18C4ABE794579E88D3C03B9B5FF2A576803",
    "discover_missing.py":     "DF1089E6317D155CD81E84C3BA0016DB108B308E66BA860A50605673B7DDB178",
}


# ============================================================================
# HASH COMPUTATION
# ============================================================================


def sha256_file(path: Path) -> str:
    """Return uppercase hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest().upper()


# ============================================================================
# DRIFT CHECK
# ============================================================================


def check_drift(verbose: bool = False) -> int:
    """Compare current hashes against baseline. Return exit code."""
    total = 0
    drifted: list[str] = []
    missing: list[str] = []

    for vault_name, file_hashes in BASELINE.items():
        scripts_dir = VAULT_ROOT / vault_name / "Vault Files" / "Scripts"
        if verbose:
            print(f"\n{'=' * 60}")
            print(f"  {vault_name}")
            print(f"{'=' * 60}")

        for filename, expected_hash in file_hashes.items():
            total += 1
            filepath = scripts_dir / filename
            label = f"  {vault_name}/{filename}"

            if not filepath.exists():
                missing.append(label)
                if verbose:
                    print(f"  MISSING  {filename}")
                continue

            actual_hash = sha256_file(filepath)
            if actual_hash == expected_hash:
                if verbose:
                    print(f"  OK       {filename}")
            else:
                drifted.append(label)
                if verbose:
                    print(f"  CHANGED  {filename}")
                    print(f"           expected: {expected_hash}")
                    print(f"           actual:   {actual_hash}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  HASH DRIFT CHECK")
    print(f"{'=' * 60}")
    print(f"  Files checked: {total}")
    print(f"  OK:            {total - len(drifted) - len(missing)}")
    print(f"  Changed:       {len(drifted)}")
    print(f"  Missing:       {len(missing)}")
    print()

    if drifted:
        print("  DRIFTED FILES:")
        for f in drifted:
            print(f"    {f}")
        print()

    if missing:
        print("  MISSING FILES:")
        for f in missing:
            print(f"    {f}")
        print()

    if drifted or missing:
        print("  RESULT: FAIL — hash drift detected")
        return 1

    print("  RESULT: PASS — no hash drift detected")
    return 0


# ============================================================================
# SHARED IMPLEMENTATION DRIFT CHECK
# ============================================================================


def check_shared_drift(verbose: bool = False) -> int:
    """Compare shared implementation hashes against baseline. Return exit code."""
    total = 0
    drifted: list[str] = []
    missing: list[str] = []

    for filename, expected_hash in SHARED_BASELINE.items():
        total += 1
        filepath = SHARED_ROOT / filename
        label = f"  core/shared/{filename}"

        if not filepath.exists():
            missing.append(label)
            if verbose:
                print(f"  MISSING  {filename}")
            continue

        actual_hash = sha256_file(filepath)
        if actual_hash == expected_hash:
            if verbose:
                print(f"  OK       {filename}")
        else:
            drifted.append(label)
            if verbose:
                print(f"  CHANGED  {filename}")
                print(f"           expected: {expected_hash}")
                print(f"           actual:   {actual_hash}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  SHARED IMPLEMENTATION CHECK")
    print(f"{'=' * 60}")
    print(f"  Files checked: {total}")
    print(f"  OK:            {total - len(drifted) - len(missing)}")
    print(f"  Changed:       {len(drifted)}")
    print(f"  Missing:       {len(missing)}")
    print()

    if drifted:
        print("  DRIFTED FILES:")
        for f in drifted:
            print(f"    {f}")
        print()

    if missing:
        print("  MISSING FILES:")
        for f in missing:
            print(f"    {f}")
        print()

    if drifted or missing:
        print("  RESULT: FAIL — shared implementation drift detected")
        return 1

    print("  RESULT: PASS — all shared implementations intact")
    return 0


# ============================================================================
# TYPE REGISTRY DRIFT CHECK
# ============================================================================


def _load_schema(vault_name: str):
    """Import a vault's vault_schema.py and return the module."""
    sp = VAULT_ROOT / vault_name / "Vault Files" / "Scripts" / "vault_schema.py"
    spec = importlib.util.spec_from_file_location(
        "vs_" + vault_name.replace(" ", "_"), str(sp)
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check_type_registry(verbose: bool = False) -> int:
    """Verify every file's YAML type matches derive_type() for all vaults."""
    total_files = 0
    mismatches: list[str] = []

    for vault_name in VAULT_NAMES:
        m = _load_schema(vault_name)
        root = VAULT_ROOT / vault_name
        files = m.discover_files(root)
        vault_mismatches = 0

        for f in files:
            total_files += 1
            fn = f.name
            derived = m.derive_type(fn)
            txt = f.read_text(encoding="utf-8")
            actual = None
            if txt.startswith("---\n"):
                end = txt.find("\n---\n", 4)
                if end > 0:
                    for line in txt[4:end].splitlines():
                        if line.startswith("type:"):
                            actual = line.split(":", 1)[1].strip()
            if actual and actual != derived:
                vault_mismatches += 1
                mismatches.append(
                    f"  {vault_name}/{fn}: actual={actual} derived={derived}"
                )

        if verbose:
            status = "OK" if vault_mismatches == 0 else f"{vault_mismatches} MISMATCH"
            print(f"  {vault_name}: {len(files)} files — {status}")

    print(f"\n{'=' * 60}")
    print(f"  TYPE REGISTRY CHECK")
    print(f"{'=' * 60}")
    print(f"  Files checked: {total_files}")
    print(f"  Mismatches:    {len(mismatches)}")
    print()

    if mismatches:
        for m2 in mismatches:
            print(m2)
        print()
        print("  RESULT: FAIL — type registry drift detected")
        return 1

    print("  RESULT: PASS — all types consistent")
    return 0


# ============================================================================
# SECTION HEADING DRIFT CHECK
# ============================================================================


def check_sections(verbose: bool = False) -> int:
    """Verify every file's headings match SECTION_MAP for its type."""
    total_files = 0
    violations: list[str] = []

    for vault_name in VAULT_NAMES:
        m = _load_schema(vault_name)
        root = VAULT_ROOT / vault_name
        section_map = m.SECTION_MAP
        optional_map = getattr(m, "OPTIONAL_SECTION_MAP", {})
        files = m.discover_files(root)
        vault_violations = 0

        for f in files:
            total_files += 1
            txt = f.read_text(encoding="utf-8")
            body = txt
            if txt.startswith("---\n"):
                end = txt.find("\n---\n", 4)
                if end > 0:
                    body = txt[end + 5:]

            note_type = None
            if txt.startswith("---\n"):
                end2 = txt.find("\n---\n", 4)
                if end2 > 0:
                    for line in txt[4:end2].splitlines():
                        if line.startswith("type:"):
                            note_type = line.split(":", 1)[1].strip()

            if not note_type:
                continue

            expected = set(section_map.get(note_type, ()))
            optional = set(optional_map.get(note_type, ()))
            canonical = expected | optional
            headings = [
                line.strip()
                for line in body.splitlines()
                if line.startswith("## ") and not line.startswith("### ")
            ]

            for h in headings:
                if h not in canonical:
                    vault_violations += 1
                    violations.append(
                        f"  {vault_name}/{f.name}: NON-CANONICAL \"{h}\" (type={note_type})"
                    )
            for req in expected:
                if req not in headings:
                    vault_violations += 1
                    violations.append(
                        f"  {vault_name}/{f.name}: MISSING \"{req}\" (type={note_type})"
                    )

        if verbose:
            status = "OK" if vault_violations == 0 else f"{vault_violations} VIOLATION"
            print(f"  {vault_name}: {len(files)} files — {status}")

    print(f"\n{'=' * 60}")
    print(f"  SECTION HEADING CHECK")
    print(f"{'=' * 60}")
    print(f"  Files checked: {total_files}")
    print(f"  Violations:    {len(violations)}")
    print()

    if violations:
        for v in violations[:30]:
            print(v)
        if len(violations) > 30:
            print(f"  ... and {len(violations) - 30} more")
        print()
        print("  RESULT: FAIL — section heading drift detected")
        return 1

    print("  RESULT: PASS — all sections compliant")
    return 0


# ============================================================================
# CLI
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check critical vault scripts against integrity baseline."
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show per-file check results")
    parser.add_argument("--hash-only", action="store_true",
                        help="Only run hash baseline check")
    parser.add_argument("--type-only", action="store_true",
                        help="Only run TYPE_REGISTRY check")
    parser.add_argument("--section-only", action="store_true",
                        help="Only run section heading check")
    args = parser.parse_args()

    run_all = not (args.hash_only or args.type_only or args.section_only)
    failures = 0

    if run_all or args.hash_only:
        failures += check_drift(verbose=args.verbose)
        failures += check_shared_drift(verbose=args.verbose)
    if run_all or args.type_only:
        failures += check_type_registry(verbose=args.verbose)
    if run_all or args.section_only:
        failures += check_sections(verbose=args.verbose)

    if failures:
        print(f"\n  OVERALL: FAIL — {failures} check(s) failed")
    else:
        print(f"\n  OVERALL: PASS — all checks clean")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
