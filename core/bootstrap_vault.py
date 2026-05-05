"""
bootstrap_vault.py — Interactive vault bootstrap command.

Prompts for domain name, note type, and canonical sections, then:
  1. Creates the vault directory structure.
  2. Writes a generated vault_schema.py.
  3. Updates config/config.yaml to point to the new vault.
  4. Generates canonical templates via generate_templates.

Entry point: main(repo_root: Path) -> int
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Python command detection (mirrors run.py — no cross-import)
# ---------------------------------------------------------------------------

def _python_cmd() -> str:
    if sys.platform == "win32" and shutil.which("py"):
        return "py"
    stem = Path(sys.executable).stem
    return stem if stem else "python"


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

_RESERVED_NAMES = frozenset({"vault files", "scripts", "templates"})


def _prompt(msg: str) -> str:
    """Print *msg* and return stripped user input."""
    print(msg, end="", flush=True)
    return input().strip()


def _slugify(text: str) -> str:
    """Convert *text* to a lowercase hyphenated slug."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def _title_case(text: str) -> str:
    return " ".join(w.capitalize() for w in text.split())


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _validate_domain(raw: str) -> tuple[str, str] | str:
    """Return ``(folder_name, slug)`` or an error string."""
    raw = raw.strip()
    if not raw:
        return "Domain name cannot be empty."
    if not re.match(r"^[A-Za-z][A-Za-z0-9 _-]*$", raw):
        return (
            "Domain name must start with a letter and contain only "
            "letters, digits, spaces, underscores, or hyphens."
        )
    if raw.lower() in _RESERVED_NAMES:
        return f"'{raw}' is a reserved name and cannot be used as a domain."
    folder = _title_case(raw)
    slug = _slugify(raw)
    if not slug:
        return "Domain name produces an empty slug after normalisation."
    return folder, slug


def _validate_note_type(raw: str) -> str | None:
    """Return cleaned note-type slug, or ``None`` if invalid."""
    raw = raw.strip().lower()
    if not raw:
        return None
    if not re.match(r"^[a-z][a-z0-9-]*$", raw):
        return None
    return raw


def _validate_sections(raw: str) -> list[str] | str:
    """Return list of section display names, or an error string."""
    parts = [p.strip() for p in raw.split(",")]
    sections = [p for p in parts if p]
    if len(sections) < 2:
        return "Please provide at least 2 sections (comma-separated)."
    seen: set[str] = set()
    duplicates: list[str] = []
    for s in sections:
        key = s.lower()
        if key in seen:
            duplicates.append(s)
        seen.add(key)
    if duplicates:
        return f"Duplicate sections: {', '.join(duplicates)}"
    return sections


# ---------------------------------------------------------------------------
# Interactive collection
# ---------------------------------------------------------------------------

def collect_input() -> tuple[
    list[tuple[str, str]],
    str,
    list[str],
    list[tuple[str, str, str]],
    list[tuple[str, str, str]],
    str,
]:
    """Prompt for and validate all bootstrap parameters.

    Returns:
        ``(all_domains, note_type, sections, subdomains, topics, vault_name)``

        - all_domains: list of ``(folder, slug)`` pairs
        - note_type:   slug string
        - sections:    list of section display names
        - subdomains:  list of ``(folder, slug, parent_domain_slug)``
        - topics:      list of ``(folder, slug, parent_subdomain_slug)``
        - vault_name:  derived from first domain slug

    Raises:
        KeyboardInterrupt: if the user presses Ctrl-C.
    """
    print()
    print("=== VAULT BOOTSTRAP ===")
    print()
    print("Create a blank vault with a custom schema and templates.")
    print("Press Ctrl+C to cancel.")
    print()

    # --- Primary domain --------------------------------------------------
    all_domains: list[tuple[str, str]] = []
    while True:
        raw = _prompt("Domain name (e.g. Dogs): ")
        result = _validate_domain(raw)
        if isinstance(result, str):
            print(f"  Error: {result}")
        else:
            all_domains.append(result)
            break

    # --- Additional domains ----------------------------------------------
    raw = _prompt("Add more domains? (y/n): ").lower()
    if raw == "y":
        while True:
            raw = _prompt("  Domain name (or Enter to stop): ")
            if not raw:
                break
            result = _validate_domain(raw)
            if isinstance(result, str):
                print(f"  Error: {result}")
            else:
                all_domains.append(result)

    # --- Note type -------------------------------------------------------
    note_type: str
    while True:
        raw = _prompt("Note type slug (e.g. breed-profile): ")
        note_type = _validate_note_type(raw)  # type: ignore[assignment]
        if note_type is None:
            print(
                "  Error: Note type must use only lowercase letters and "
                "hyphens, and start with a letter (e.g. breed-profile)."
            )
        else:
            break

    # --- Sections --------------------------------------------------------
    sections: list[str]
    while True:
        raw = _prompt(
            "Canonical sections, comma-separated (min 2, "
            "e.g. Overview, Examples, Trade-offs): "
        )
        result = _validate_sections(raw)
        if isinstance(result, str):
            print(f"  Error: {result}")
        else:
            sections = result
            break

    # --- Subdomains (optional) -------------------------------------------
    subdomains: list[tuple[str, str, str]] = []
    raw = _prompt("Add subdomains? (y/n): ").lower()
    if raw == "y":
        for d_folder, d_slug in all_domains:
            raw = _prompt(f"  Subdomains for {d_folder} (comma-separated, or Enter to skip): ")
            if not raw.strip():
                continue
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            for p in parts:
                result = _validate_domain(p)
                if isinstance(result, str):
                    print(f"    Skipping '{p}': {result}")
                else:
                    sub_folder, sub_slug = result
                    subdomains.append((sub_folder, sub_slug, d_slug))

    # --- Topics (optional, only if subdomains exist) ---------------------
    topics: list[tuple[str, str, str]] = []
    if subdomains:
        raw = _prompt("Add topics? (y/n): ").lower()
        if raw == "y":
            for sub_folder, sub_slug, _parent in subdomains:
                raw = _prompt(f"  Topics for {sub_folder} (comma-separated, or Enter to skip): ")
                if not raw.strip():
                    continue
                parts = [p.strip() for p in raw.split(",") if p.strip()]
                for p in parts:
                    result = _validate_domain(p)
                    if isinstance(result, str):
                        print(f"    Skipping '{p}': {result}")
                    else:
                        t_folder, t_slug = result
                        topics.append((t_folder, t_slug, sub_slug))

    vault_name = f"{all_domains[0][1]}-vault"
    return all_domains, note_type, sections, subdomains, topics, vault_name


# ---------------------------------------------------------------------------
# Vault creation helpers
# ---------------------------------------------------------------------------

def _create_vault_structure(
    repo_root: Path,
    vault_name: str,
    all_domains: list[tuple[str, str]],
    subdomains: list[tuple[str, str, str]],
) -> Path:
    """Create the skeleton directory layout for a new vault."""
    vault_path = repo_root / vault_name
    # Create domain directories
    for domain_folder, _slug in all_domains:
        (vault_path / domain_folder).mkdir(parents=True)
    # Create subdomain subdirectories under their parent domain folder
    # Build folder lookup: domain_slug -> domain_folder
    slug_to_folder = {slug: folder for folder, slug in all_domains}
    for sub_folder, _sub_slug, parent_domain_slug in subdomains:
        parent_folder = slug_to_folder.get(parent_domain_slug)
        if parent_folder:
            (vault_path / parent_folder / sub_folder).mkdir(parents=True, exist_ok=True)
    (vault_path / "Vault Files" / "Scripts").mkdir(parents=True, exist_ok=True)
    (vault_path / "Vault Files" / "Templates").mkdir(parents=True, exist_ok=True)
    return vault_path


def _update_config(repo_root: Path, vault_name: str) -> None:
    """Atomically update config/config.yaml to point to *vault_name*.

    Delegates to the shared bootstrap service so the config-update logic
    is defined in exactly one place.
    """
    from core.shared.bootstrap_service import update_config
    update_config(repo_root, vault_name)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(repo_root: Path) -> int:
    """Bootstrap a new vault interactively."""
    try:
        all_domains, note_type, sections, subdomains, topics, vault_name = (
            collect_input()
        )
    except KeyboardInterrupt:
        print("\nBootstrap cancelled.")
        return 1

    domain_folder = all_domains[0][0]
    domain_slug = all_domains[0][1]

    # ── Summary preview ──────────────────────────────────────────────────
    print()
    print(f"Creating vault   : {vault_name}/")
    for d_folder, d_slug in all_domains:
        print(f"  Domain         : {d_folder}/ ({d_slug})")
    for sub_folder, sub_slug, parent in subdomains:
        print(f"  Subdomain      : {sub_folder}/ ({sub_slug}) -> {parent}")
    for t_folder, t_slug, parent in topics:
        print(f"  Topic          : {t_folder} ({t_slug}) -> {parent}")
    print(f"  Note type      : {note_type}")
    print(f"  Sections       : {', '.join(sections)}")
    print()

    vault_path = repo_root / vault_name
    if vault_path.exists():
        print(f"Error: directory already exists: {vault_name}")
        return 1

    # ── 1. Directory structure ────────────────────────────────────────────
    try:
        _create_vault_structure(repo_root, vault_name, all_domains, subdomains)
    except OSError as exc:
        print(f"Error: could not create vault structure: {exc}")
        return 1

    # ── 2. Generate vault_schema.py ───────────────────────────────────────
    from core.generate_schema import generate_schema_content, write_schema

    schema_content = generate_schema_content(
        domain_folder,
        domain_slug,
        note_type,
        sections,
        extra_domains=all_domains[1:] if len(all_domains) > 1 else None,
        subdomains=subdomains if subdomains else None,
        topics=topics if topics else None,
    )
    schema_path = write_schema(vault_path, schema_content)
    print(f"Schema written   : {schema_path.relative_to(repo_root)}")

    # ── 3. Update config ──────────────────────────────────────────────────
    try:
        _update_config(repo_root, vault_name)
    except Exception as exc:
        print(f"Error: could not update config: {exc}")
        return 1
    print(f"Config updated   : config/config.yaml -> ./{vault_name}")

    # ── 4. Generate templates ─────────────────────────────────────────────
    from core.generate_templates import process_vault

    report = process_vault(vault_path, dry_run=False)
    created = report.get("created", [])
    print(f"Templates        : {len(created)} created  {created}")

    # ── 5. Next-steps summary ─────────────────────────────────────────────
    py = _python_cmd()
    print()
    print("Vault ready. Next steps:")
    print(f"  Add notes to         : {vault_name}/{domain_folder}/")
    print(f"  Inject frontmatter   : {py} run.py improve")
    print(f"  Validate             : {py} run.py validate")
    print(f"  Full report          : {py} run.py report")
    return 0
