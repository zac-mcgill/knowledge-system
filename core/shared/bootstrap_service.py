"""
bootstrap_service.py — Non-interactive vault bootstrap service.

Provides safe, API-callable vault creation used by both the CLI bootstrap
command and the POST /vault/bootstrap API route.

Public API:
    validate_bootstrap_request(repo_root, vault_name, domain, note_type,
                               sections, expected_concepts) -> list[str]
    bootstrap_vault_noninteractive(repo_root, vault_name, domain, note_type,
                                   sections, expected_concepts) -> dict
    update_config(repo_root, vault_name) -> None

The update_config() function is also importable by core/bootstrap_vault.py to
eliminate duplicate config-update logic between the CLI and service paths.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Validation patterns
# ---------------------------------------------------------------------------

_VAULT_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_NOTE_TYPE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_DOMAIN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 _-]*$")

_RESERVED_NAMES = frozenset({"vault files", "scripts", "templates"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert text to a lowercase hyphenated slug."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def _title_case(text: str) -> str:
    return " ".join(w.capitalize() for w in text.split())


# ---------------------------------------------------------------------------
# Public: config update (shared with bootstrap_vault.py)
# ---------------------------------------------------------------------------


def update_config(repo_root: Path, vault_name: str) -> None:
    """Atomically update config/config.yaml to point to *vault_name*.

    Uses a temp-file + atomic replace strategy so a partial write never
    corrupts the config file.

    Raises:
        FileNotFoundError: If config/config.yaml is missing.
        OSError: If the atomic write fails.
    """
    config_path = repo_root / "config" / "config.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(f"config/config.yaml not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    updated = re.sub(
        r"^(vault_root:\s*).*$",
        rf"\g<1>./{vault_name}",
        content,
        flags=re.MULTILINE,
    )

    tmp_fd, tmp_path = tempfile.mkstemp(dir=config_path.parent, suffix=".yaml")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp:
            tmp.write(updated)
        Path(tmp_path).replace(config_path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Public: input validation
# ---------------------------------------------------------------------------


def validate_bootstrap_request(
    repo_root: Path,
    vault_name: str,
    domain: str,
    note_type: str,
    sections: list[str],
    expected_concepts: list[str] | None = None,
) -> list[str]:
    """Strictly validate bootstrap request parameters.

    Returns a list of error strings.  An empty list means all inputs are valid.
    Does not write any files.

    Security rules enforced:
    - vault_name: alphanumeric / underscore / hyphen only; no path separators;
      must not be '.' or '..'; resolved path must stay within repo_root;
      must not refer to an already-existing directory.
    - domain: must start with a letter; letters/digits/spaces/underscores/hyphens
      only; no path separators; no control characters; not a reserved name.
    - note_type: lowercase slug pattern ^[a-z0-9]+(?:-[a-z0-9]+)*$.
    - sections: list of ≥2 non-empty strings; no duplicates (case-insensitive);
      no control characters; no path-traversal markers.
    - expected_concepts: optional list; no control characters; no duplicates.
    """
    errors: list[str] = []
    repo_root_resolved = repo_root.resolve()

    # --- vault_name -------------------------------------------------------
    vn = vault_name.strip() if isinstance(vault_name, str) else ""
    if not vn:
        errors.append("vault_name: must not be empty")
    elif vn in (".", ".."):
        errors.append("vault_name: must not be '.' or '..'")
    elif "/" in vn or "\\" in vn:
        errors.append("vault_name: must not contain path separators")
    elif not _VAULT_NAME_RE.match(vn):
        errors.append(
            "vault_name: only letters, digits, underscores, and hyphens are allowed "
            "(pattern: ^[A-Za-z0-9_-]+$)"
        )
    else:
        # Boundary check: resolved path must stay within repo_root
        try:
            resolved = (repo_root / vn).resolve()
            repo_str = str(repo_root_resolved)
            resolved_str = str(resolved)
            # Allow exact match (repo root itself) or a direct child
            if not (resolved_str == repo_str or resolved_str.startswith(repo_str + os.sep)):
                errors.append(
                    "vault_name: resolves outside repository root (path traversal blocked)"
                )
            else:
                # Existence check (only when path is safe)
                vault_path = repo_root / vn
                if vault_path.exists():
                    errors.append(f"vault_name: vault '{vn}' already exists")
        except Exception:
            errors.append("vault_name: could not resolve path safely")

    # --- domain -----------------------------------------------------------
    dom = domain.strip() if isinstance(domain, str) else ""
    if not dom:
        errors.append("domain: must not be empty")
    elif "/" in dom or "\\" in dom:
        errors.append("domain: must not contain path separators")
    elif _CONTROL_CHAR_RE.search(dom):
        errors.append("domain: must not contain control characters")
    elif not _DOMAIN_RE.match(dom):
        errors.append(
            "domain: must start with a letter and contain only letters, digits, "
            "spaces, underscores, or hyphens"
        )
    elif dom.lower() in _RESERVED_NAMES:
        errors.append(f"domain: '{dom}' is a reserved name and cannot be used")
    else:
        slug = _slugify(dom)
        if not slug:
            errors.append("domain: produces an empty slug after normalisation")

    # --- note_type --------------------------------------------------------
    nt = note_type.strip() if isinstance(note_type, str) else ""
    if not nt:
        errors.append("note_type: must not be empty")
    elif not _NOTE_TYPE_RE.match(nt):
        errors.append(
            "note_type: must be a lowercase slug like 'breed-profile' "
            "(pattern: ^[a-z0-9]+(?:-[a-z0-9]+)*$)"
        )

    # --- sections ---------------------------------------------------------
    if not isinstance(sections, list):
        errors.append("sections: must be a list")
    else:
        clean_sections = [
            s.strip() for s in sections if isinstance(s, str) and s.strip()
        ]
        if len(clean_sections) < 2:
            errors.append("sections: must have at least 2 non-empty sections")
        else:
            section_error = False
            for s in clean_sections:
                if _CONTROL_CHAR_RE.search(s):
                    errors.append(
                        f"sections: entry contains control characters: {s!r}"
                    )
                    section_error = True
                    break
                # Detect path traversal in section names
                if ".." in s and ("/" in s or "\\" in s):
                    errors.append(
                        f"sections: entry contains path traversal markers: {s!r}"
                    )
                    section_error = True
                    break

            if not section_error:
                seen: set[str] = set()
                for s in clean_sections:
                    key = s.lower()
                    if key in seen:
                        errors.append(
                            f"sections: duplicate section after normalisation: {s!r}"
                        )
                        break
                    seen.add(key)

    # --- expected_concepts ------------------------------------------------
    if expected_concepts is not None:
        if not isinstance(expected_concepts, list):
            errors.append("expected_concepts: must be a list")
        else:
            clean_ec = [
                c.strip()
                for c in expected_concepts
                if isinstance(c, str) and c.strip()
            ]
            ec_error = False
            for c in clean_ec:
                if _CONTROL_CHAR_RE.search(c):
                    errors.append(
                        f"expected_concepts: entry contains control characters: {c!r}"
                    )
                    ec_error = True
                    break

            if not ec_error:
                seen_ec: set[str] = set()
                for c in clean_ec:
                    key = c.lower()
                    if key in seen_ec:
                        errors.append(
                            f"expected_concepts: duplicate entry after normalisation: {c!r}"
                        )
                        break
                    seen_ec.add(key)

    return errors


# ---------------------------------------------------------------------------
# Private: filesystem helpers
# ---------------------------------------------------------------------------


def _create_vault_structure(vault_path: Path, domain_folder: str) -> None:
    """Create skeleton vault directories for a single-domain vault.

    Creates:
        <vault_path>/<domain_folder>/
        <vault_path>/Vault Files/Scripts/
        <vault_path>/Vault Files/Templates/
    """
    (vault_path / domain_folder).mkdir(parents=True, exist_ok=False)
    (vault_path / "Vault Files" / "Scripts").mkdir(parents=True, exist_ok=True)
    (vault_path / "Vault Files" / "Templates").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Public: non-interactive bootstrap
# ---------------------------------------------------------------------------


def bootstrap_vault_noninteractive(
    repo_root: Path,
    vault_name: str,
    domain: str,
    note_type: str,
    sections: list[str],
    expected_concepts: list[str] | None = None,
) -> dict:
    """Create a new vault non-interactively.

    Validates inputs, creates directory structure, writes vault_schema.py,
    updates config/config.yaml atomically, and generates canonical templates.

    Args:
        repo_root:         Absolute path to the repository root.
        vault_name:        New vault directory name (e.g. "dogs-vault").
        domain:            Primary domain display name (e.g. "Dogs").
        note_type:         Note type slug (e.g. "breed-profile").
        sections:          List of canonical section names (min 2).
        expected_concepts: Optional list of expected concept names.

    Returns::

        {
            "vault":      <vault_name>,
            "vault_path": <absolute path string>,
            "created":    [<relative file paths created>],
            "warnings":   [<warning strings>],
        }

    Raises:
        ValueError:      Any input fails validation (message lists all errors).
        FileExistsError: Vault directory already exists.
        RuntimeError:    Vault creation, config update, or template generation fails.
    """
    # 1. Validate all inputs first
    errors = validate_bootstrap_request(
        repo_root, vault_name, domain, note_type, sections, expected_concepts
    )
    if errors:
        raise ValueError(
            "Validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    # Normalise after validation passes
    vault_name = vault_name.strip()
    domain = domain.strip()
    note_type = note_type.strip()
    sections = [s.strip() for s in sections if s.strip()]
    expected_concepts_clean: list[str] = (
        [c.strip() for c in expected_concepts if c.strip()]
        if expected_concepts
        else []
    )

    domain_folder = _title_case(domain)
    domain_slug = _slugify(domain)
    vault_path = repo_root / vault_name

    warnings: list[str] = []
    created_files: list[str] = []

    # 2. Final existence check after normalisation
    if vault_path.exists():
        raise FileExistsError(f"Vault directory already exists: {vault_name}")

    # 3. Create directory structure (rollback on failure)
    try:
        _create_vault_structure(vault_path, domain_folder)
    except OSError as exc:
        raise RuntimeError(
            f"Could not create vault directory structure: {exc}"
        ) from exc

    # Everything from here may need rollback on failure.
    # Save old vault_root for potential config rollback.
    config_path = repo_root / "config" / "config.yaml"
    _old_config_content: str | None = None
    if config_path.is_file():
        try:
            _old_config_content = config_path.read_text(encoding="utf-8")
        except OSError:
            pass  # Can't read → can't rollback config, but proceed

    config_updated = False

    try:
        # 4. Write vault_schema.py
        from core.generate_schema import generate_schema_content, write_schema

        schema_content = generate_schema_content(
            domain_folder,
            domain_slug,
            note_type,
            sections,
        )
        schema_path = write_schema(vault_path, schema_content)
        try:
            created_files.append(str(schema_path.relative_to(repo_root)))
        except ValueError:
            created_files.append(str(schema_path))

        # 5. Update config/config.yaml atomically
        update_config(repo_root, vault_name)
        config_updated = True

        # 6. Generate canonical templates
        try:
            from core.generate_templates import process_vault

            report = process_vault(vault_path, dry_run=False)
            template_dir = vault_path / "Vault Files" / "Templates"
            for fname in report.get("created", []):
                template_path = template_dir / fname
                try:
                    created_files.append(str(template_path.relative_to(repo_root)))
                except ValueError:
                    created_files.append(str(template_path))
        except SystemExit as exc:
            # process_vault calls sys.exit(1) on hard schema/template mismatch
            raise RuntimeError(
                "Template generation failed: schema validation error. "
                "Check vault_schema.py for consistency."
            ) from exc
        except Exception as exc:
            # Template generation is best-effort; warn rather than fail hard
            warnings.append(f"Template generation warning: {exc}")

        # 7. expected_concepts: accepted but not yet written into schema
        if expected_concepts_clean:
            warnings.append(
                "expected_concepts were accepted but not written into "
                "vault_schema.py. The schema generator does not currently "
                "support EXPECTED_CONCEPTS injection via the bootstrap API. "
                "Add them manually to vault_schema.py after bootstrap."
            )

        # 8. Registry cache notice
        warnings.append(
            "Vault registry cache may be stale in a running API server. "
            "Call reload_config() on vault_registry or restart the server "
            "to activate the new vault."
        )

        return {
            "vault": vault_name,
            "vault_path": str(vault_path),
            "created": created_files,
            "warnings": warnings,
        }

    except Exception:
        # --- Rollback ---
        # Attempt to restore old config if we already updated it
        if config_updated and _old_config_content is not None:
            try:
                tmp_fd, tmp_path = tempfile.mkstemp(
                    dir=config_path.parent, suffix=".yaml"
                )
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp:
                    tmp.write(_old_config_content)
                Path(tmp_path).replace(config_path)
            except OSError:
                pass  # Best-effort rollback

        # Remove partially-created vault directory
        if vault_path.exists():
            try:
                shutil.rmtree(vault_path)
            except OSError:
                pass

        raise
