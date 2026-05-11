"""
vault_delete.py — Safe, conservative vault deletion service.

Provides a small, testable service layer for deleting non-demo vaults.

Safety model:
  - Deletion is identified by vault NAME (not path).
  - demo-vault is unconditionally protected.
  - The last remaining vault cannot be deleted.
  - The vault path is resolved from the registry only (never from user input).
  - The resolved path must sit inside the repo root (path-traversal guard).
  - An exact confirmation phrase "DELETE <vault-name>" is required.
  - Config is updated atomically (temp-file + replace) AFTER directory deletion
    succeeds, to avoid leaving a missing directory in the registry.

Order of operations:
  1. validate_delete_request() — all checks, no side effects.
  2. assert_safe_vault_path()  — path-boundary check.
  3. delete vault directory from disk (shutil.rmtree).
  4. update_config_after_delete() — atomic config rewrite.
  5. Reload vault registry (caller's responsibility via reload_config()).
  6. Clear note-index and result-cache entries for the deleted vault.

If step 3 fails the config is untouched and the caller gets DELETE_FAILED.
If step 4 fails the directory is already gone; the caller gets
CONFIG_UPDATE_FAILED with a description so the operator can repair manually.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import yaml

# Protected vault that can never be deleted via the API.
_PROTECTED_VAULT = "demo-vault"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class VaultDeleteError(Exception):
    """Raised when vault deletion cannot proceed.

    Attributes:
        code (str): Machine-readable error code (one of the constants below).
        message (str): Human-readable description.
        http_status (int): Suggested HTTP status code.
    """

    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


# Error codes
INVALID_VAULT = "INVALID_VAULT"
PROTECTED_VAULT = "PROTECTED_VAULT"
LAST_VAULT = "LAST_VAULT"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
CONFIRMATION_MISMATCH = "CONFIRMATION_MISMATCH"
PATH_TRAVERSAL = "PATH_TRAVERSAL"
DELETE_FAILED = "DELETE_FAILED"
CONFIG_UPDATE_FAILED = "CONFIG_UPDATE_FAILED"


def validate_delete_request(vault_name: str, confirm: str, all_vaults: list[str]) -> None:
    """Validate a vault delete request.  Raises VaultDeleteError on any failure.

    Parameters
    ----------
    vault_name:
        The vault to delete (name only, no path).
    confirm:
        The user-supplied confirmation string.
    all_vaults:
        Current list of registered vault names (from registry).

    Raises
    ------
    VaultDeleteError
        With a specific code if any safety check fails.
    """
    # 1. Confirmation required
    if not confirm or not isinstance(confirm, str) or not confirm.strip():
        raise VaultDeleteError(
            CONFIRMATION_REQUIRED,
            "Confirmation phrase is required. "
            f"Send {{\"confirm\": \"DELETE {vault_name}\"}} to proceed.",
            400,
        )

    # 2. Confirmation must be the exact phrase
    expected = f"DELETE {vault_name}"
    if confirm.strip() != expected:
        raise VaultDeleteError(
            CONFIRMATION_MISMATCH,
            f"Confirmation mismatch. Expected exactly: \"{expected}\". "
            f"Received: \"{confirm.strip()}\".",
            400,
        )

    # 3. Protected vault
    if vault_name == _PROTECTED_VAULT:
        raise VaultDeleteError(
            PROTECTED_VAULT,
            f"'{vault_name}' is a protected vault and cannot be deleted via the API.",
            403,
        )

    # 4. Vault must exist in registry
    if vault_name not in all_vaults:
        raise VaultDeleteError(
            INVALID_VAULT,
            f"Unknown vault: '{vault_name}'. Available: {sorted(all_vaults)}.",
            404,
        )

    # 5. Cannot delete the last remaining vault
    if len(all_vaults) <= 1:
        raise VaultDeleteError(
            LAST_VAULT,
            "Cannot delete the last remaining vault. At least one vault must remain.",
            400,
        )

    # 6. After deletion at least one vault must survive
    remaining = [v for v in all_vaults if v != vault_name]
    if not remaining:
        raise VaultDeleteError(
            LAST_VAULT,
            "Cannot delete the last remaining vault. At least one vault must remain.",
            400,
        )


def assert_safe_vault_path(vault_path: Path, repo_root: Path) -> None:
    """Confirm that vault_path is inside repo_root.

    This is a secondary safety check: the primary check is that the path comes
    from the registry (not user input).  This guard catches edge-cases where a
    registered path has been manually set to an external location.

    Raises
    ------
    VaultDeleteError
        With code PATH_TRAVERSAL if the path escapes repo_root.
    """
    try:
        resolved_vault = vault_path.resolve()
        resolved_repo = repo_root.resolve()
        resolved_vault.relative_to(resolved_repo)
    except ValueError:
        raise VaultDeleteError(
            PATH_TRAVERSAL,
            f"Vault path '{vault_path}' is outside the repository root '{repo_root}'. "
            "Deletion refused.",
            400,
        )


def update_config_after_delete(
    config_path: Path,
    deleted_vault: str,
    fallback_vault: str,
) -> dict:
    """Atomically update config.yaml after a vault has been deleted.

    Removes deleted_vault from vault_roots.  If vault_root pointed at
    deleted_vault, replaces it with fallback_vault.

    Returns the updated data dict for caller inspection.

    Raises
    ------
    VaultDeleteError
        With code CONFIG_UPDATE_FAILED on any I/O or YAML error.
    """
    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        raise VaultDeleteError(
            CONFIG_UPDATE_FAILED,
            f"Failed to read config.yaml before update: {exc}",
            500,
        )

    deleted_rel = f"./{deleted_vault}"
    fallback_rel = f"./{fallback_vault}"

    # Update vault_root if it pointed at the deleted vault
    current_root = data.get("vault_root", "")
    if current_root == deleted_rel or current_root == deleted_vault:
        data["vault_root"] = fallback_rel

    # Remove the deleted vault from vault_roots, deduplicate
    existing: list[str] = data.get("vault_roots") or []
    filtered = [
        r for r in existing
        if r not in (deleted_rel, deleted_vault)
    ]
    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for r in filtered:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    data["vault_roots"] = deduped

    updated_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False)

    tmp_fd, tmp_path = tempfile.mkstemp(dir=config_path.parent, suffix=".yaml")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp:
            tmp.write(updated_yaml)
        Path(tmp_path).replace(config_path)
    except BaseException as exc:
        Path(tmp_path).unlink(missing_ok=True)
        raise VaultDeleteError(
            CONFIG_UPDATE_FAILED,
            f"Failed to write updated config.yaml: {exc}",
            500,
        )

    return data


def delete_vault(vault_name: str, confirm: str, repo_root: Path) -> dict:
    """Delete a non-demo vault from disk and update config.

    This is the main entry-point used by the API endpoint.

    Steps performed:
      1. Validate the delete request (no side-effects).
      2. Resolve vault path from registry.
      3. Assert the path is inside repo_root.
      4. Remove the vault directory (shutil.rmtree).
      5. Update config.yaml atomically.
      6. Return result dict with remaining_vaults and active_vault.

    After this function returns the caller must:
      - Call reload_config() to refresh the vault registry.
      - Call clear_vault_caches(vault_name) to evict stale cache entries.

    Parameters
    ----------
    vault_name:
        Name of the vault to delete.
    confirm:
        Must be exactly "DELETE <vault_name>".
    repo_root:
        Absolute path to the repository root.

    Returns
    -------
    dict
        {
          "deleted": vault_name,
          "remaining_vaults": [...],
          "active_vault": "<fallback>",
        }

    Raises
    ------
    VaultDeleteError
        On any validation, safety, or I/O failure.
    """
    from mcp.core.vault_registry import list_vaults, get_vault_path

    all_vaults = list_vaults()

    # Step 1: Full validation (raises on any failure)
    validate_delete_request(vault_name, confirm, all_vaults)

    # Step 2: Resolve path from registry only
    vault_path = get_vault_path(vault_name)

    # Step 3: Path boundary check
    assert_safe_vault_path(vault_path, repo_root)

    # Determine fallback vault before deletion
    remaining = [v for v in all_vaults if v != vault_name]
    # Prefer demo-vault as fallback; otherwise use first remaining vault
    if _PROTECTED_VAULT in remaining:
        fallback = _PROTECTED_VAULT
    else:
        fallback = remaining[0]

    # Step 4: Remove vault directory
    try:
        shutil.rmtree(vault_path)
    except OSError as exc:
        raise VaultDeleteError(
            DELETE_FAILED,
            f"Failed to delete vault directory '{vault_path}': {exc}",
            500,
        )

    # Step 5: Update config.yaml
    config_path = repo_root / "config" / "config.yaml"
    update_config_after_delete(config_path, vault_name, fallback)

    return {
        "deleted": vault_name,
        "remaining_vaults": sorted(remaining),
        "active_vault": fallback,
    }
