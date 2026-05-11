"""
Private Cloud Configuration — mcp/core/private_cloud.py

Provides deterministic helpers for reading private-cloud settings from
environment variables.  No external dependencies; pure standard library.

Environment variables (all opt-in, safe defaults for local mode):

    CVE_PRIVATE_CLOUD_ENABLED  — Enable private cloud mode. Default: false.
    CVE_AUTH_TOKEN             — Bearer token for API authentication (secret).
                                  Read from environment only; never printed/logged.
    CVE_REQUIRE_AUTH           — Require authentication for all non-health routes.
                                  Default: false in local mode, true when private
                                  cloud is enabled and a token is configured.
    CVE_REMOTE_READ_ONLY       — Block all mutating HTTP methods. Default: true.
    CVE_PUBLIC_BASE_URL        — Public base URL for status/doc display only.
    CVE_DEPLOYMENT_MODE        — Deployment mode tag (local | vps | tunnel).
                                  Default: local.

Safety rules:
    - The token value is never written to logs or status responses.
    - If CVE_PRIVATE_CLOUD_ENABLED=true and no token is configured:
        auth is FORCED ON and the status endpoint reports a warning.
        The server continues in a locked-down, write-blocking state.
    - All helpers are stateless; they re-read environment variables on each
      call so that tests can use monkeypatching safely.
"""

import os
import secrets
from typing import Any


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _env_bool(name: str, default: bool) -> bool:
    """Read an environment variable as a boolean (true/1/yes/on → True)."""
    val = os.environ.get(name, "").strip().lower()
    if val in ("true", "1", "yes", "on"):
        return True
    if val in ("false", "0", "no", "off"):
        return False
    return default


def _env_str(name: str, default: str = "") -> str:
    """Read an environment variable as a stripped string."""
    return os.environ.get(name, default).strip()


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def load_private_cloud_config() -> dict[str, Any]:
    """Load and normalise the full private cloud configuration.

    Returns a dict with all relevant settings.  The raw token value is
    **never** included; only ``token_configured`` (bool) is exposed.

    Returns:
        dict with keys:
            enabled (bool): True if CVE_PRIVATE_CLOUD_ENABLED=true.
            deployment_mode (str): Value of CVE_DEPLOYMENT_MODE.
            require_auth (bool): Effective require-auth setting.
            token_configured (bool): True if a non-empty token is set.
            remote_read_only (bool): True if mutating routes are blocked.
            public_base_url (str): Display-only public base URL.
            warnings (list[str]): Configuration warnings (no secrets).
    """
    enabled = _env_bool("CVE_PRIVATE_CLOUD_ENABLED", default=False)
    raw_token = os.environ.get("CVE_AUTH_TOKEN", "")
    token_configured = bool(raw_token and raw_token.strip())
    deployment_mode = _env_str("CVE_DEPLOYMENT_MODE", "local")
    public_base_url = _env_str("CVE_PUBLIC_BASE_URL", "")
    remote_read_only = _env_bool("CVE_REMOTE_READ_ONLY", default=True)

    # Determine effective require_auth:
    # - If private cloud is NOT enabled: false by default (local mode unchanged).
    # - If private cloud IS enabled: true by default, unless explicitly disabled.
    if enabled:
        require_auth_default = True
    else:
        require_auth_default = False
    require_auth = _env_bool("CVE_REQUIRE_AUTH", default=require_auth_default)

    warnings: list[str] = []

    if enabled and not token_configured:
        warnings.append(
            "CVE_PRIVATE_CLOUD_ENABLED=true but CVE_AUTH_TOKEN is not set. "
            "Authentication is forced on; all API requests will return 401 until "
            "a token is configured."
        )
        # Force auth on when private cloud is enabled but no token provided.
        require_auth = True

    if enabled and deployment_mode == "local":
        warnings.append(
            "Private cloud mode is enabled but CVE_DEPLOYMENT_MODE=local. "
            "Set CVE_DEPLOYMENT_MODE=vps or CVE_DEPLOYMENT_MODE=tunnel for "
            "remote deployments."
        )

    if enabled and not public_base_url:
        warnings.append(
            "CVE_PUBLIC_BASE_URL is not set. Set it for accurate status reporting "
            "when running behind a reverse proxy or tunnel."
        )

    return {
        "enabled": enabled,
        "deployment_mode": deployment_mode,
        "require_auth": require_auth,
        "token_configured": token_configured,
        "remote_read_only": remote_read_only,
        "public_base_url": public_base_url,
        "warnings": warnings,
    }


def is_private_cloud_enabled() -> bool:
    """Return True if private cloud mode is active."""
    return _env_bool("CVE_PRIVATE_CLOUD_ENABLED", default=False)


def is_remote_read_only() -> bool:
    """Return True if mutating routes should be blocked.

    Defaults to True when private cloud is enabled.  Local mode is unaffected
    (returns False when private cloud is disabled and CVE_REMOTE_READ_ONLY
    is not explicitly set).
    """
    if not is_private_cloud_enabled():
        # When private cloud is disabled, respect the env var or default False.
        return _env_bool("CVE_REMOTE_READ_ONLY", default=False)
    return _env_bool("CVE_REMOTE_READ_ONLY", default=True)


def get_expected_token() -> str:
    """Return the configured auth token, or empty string if not set.

    This value must never be written to logs, responses, or status output.
    """
    return os.environ.get("CVE_AUTH_TOKEN", "").strip()


def require_auth() -> bool:
    """Return True if authentication is required for API requests.

    Rules:
    - Local mode (private cloud disabled): False by default.
    - Private cloud enabled with token: True by default.
    - Private cloud enabled without token: True (forced on, server locked down).
    - CVE_REQUIRE_AUTH env var can override in all cases.
    """
    cfg = load_private_cloud_config()
    return cfg["require_auth"]


def auth_status_summary() -> dict[str, Any]:
    """Return a safe auth status summary (no token values).

    Returns:
        dict with:
            require_auth (bool)
            token_configured (bool)
            private_cloud_enabled (bool)
            remote_read_only (bool)
    """
    cfg = load_private_cloud_config()
    return {
        "require_auth": cfg["require_auth"],
        "token_configured": cfg["token_configured"],
        "private_cloud_enabled": cfg["enabled"],
        "remote_read_only": is_remote_read_only(),
    }


def private_cloud_status() -> dict[str, Any]:
    """Return a full private cloud status dict for the /private/status endpoint.

    Includes configuration summary, warnings, and protected route information.
    Never includes the raw token value.
    """
    cfg = load_private_cloud_config()

    protected_methods = ["PUT", "POST", "DELETE"] if cfg["remote_read_only"] else []

    return {
        "enabled": cfg["enabled"],
        "deployment_mode": cfg["deployment_mode"],
        "require_auth": cfg["require_auth"],
        "token_configured": cfg["token_configured"],
        "remote_read_only": cfg["remote_read_only"],
        "public_base_url": cfg["public_base_url"] or None,
        "warnings": cfg["warnings"],
        "protected_methods": protected_methods,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Token comparison (constant-time to resist timing attacks)
# ──────────────────────────────────────────────────────────────────────────────

def verify_token(candidate: str) -> bool:
    """Return True if the candidate token matches the configured token.

    Uses ``secrets.compare_digest`` to prevent timing-based side-channel
    attacks.  Returns False immediately if no token is configured.

    Args:
        candidate: The token presented by the caller.

    Returns:
        True only if the candidate is non-empty AND matches the configured token.
    """
    expected = get_expected_token()
    if not expected:
        return False
    if not candidate:
        return False
    # Both arguments to compare_digest must be the same type (str here).
    return secrets.compare_digest(candidate, expected)
