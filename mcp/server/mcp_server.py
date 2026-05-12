"""
MCP Server — read-mostly API layer over multiple Obsidian vaults.

Endpoints:
    GET  /vaults  — list registered vault names
    POST /query   — query a vault with filters
    GET  /note    — retrieve a single note by vault + path
    PUT  /note    — safely update an existing note (Phase 15B)
    GET  /stats   — aggregate a field across a vault
    GET  /health  — server health and metrics

Hardening:
    - Preload all schemas + indexes at startup; abort on failure (Phase 4)
    - Typed response contract on all endpoints (Phase 10)
    - Health endpoint with real metrics (Phase 11)
    - Request metrics tracking (Phase 12)
    - In-memory rate limiting (50 req/s global)
    - Graceful shutdown with signal handling
    - Config validation at startup (paths, schemas, required functions)
    - Structured JSON logging
"""

import signal
import sys
import time
import logging
import threading
from collections import deque
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure repo root is on sys.path so both mcp.* and core.* imports work
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, Response
from starlette.requests import Request
from pydantic import BaseModel, Field
from typing import Any
import mimetypes

from mcp.core.vault_registry import list_vaults, get_vault_path, get_schema, reload_config
from mcp.core.note_index import build_index, get_index, get_schema_hash, get_index_metadata, clear_vault_index
from mcp.core.result_cache import clear_vault_cache
from mcp.core.query_engine import query, list_notes, get_note, aggregate
from mcp.core.contract_runner import run_all_checks, run_lightweight_checks
from mcp.core.adapters.validation_adapter import get_validation
from mcp.core.adapters.tasks_adapter import get_tasks
from mcp.core.adapters.notes_adapter import get_notes as get_all_notes
from mcp.core.adapters.quality_adapter import get_quality
from mcp.core.adapters.missing_adapter import get_missing
from mcp.core.adapters.compare_adapter import get_compare
from mcp.core.graph_builder import build_graph
from mcp.core.graph_query import get_neighbors, get_related_nodes, get_missing_neighbors
from core.shared.context_bundle import generate_bundle as _generate_bundle
from core.shared.feedback import (
    load_feedback as _load_feedback,
    add_feedback_entry as _add_feedback_entry,
    update_feedback_entry as _update_feedback_entry,
    delete_feedback_entry as _delete_feedback_entry,
    normalise_feedback as _normalise_feedback,
    validate_feedback_write as _validate_feedback_write,
    is_valid_feedback_id as _is_valid_feedback_id,
)
from core.shared.context_package import export_context_package as _export_package
from core.shared.context_security import scan_vault_context as _scan_vault_context
from core.shared.context_security import scan_context_bundle as _scan_context_bundle
from mcp.core.note_write import update_note as _update_note
from mcp.core.context_controller import get_context_state, build_context_plan
from mcp.core.private_cloud import (
    load_private_cloud_config,
    private_cloud_status,
    require_auth,
    is_remote_read_only,
    verify_token,
)
from mcp.core import session_state as _session_state
from mcp.core import pending_changes as _pending_changes
from mcp.core import context_profiles as _context_profiles
from mcp.core import trust_metadata as _trust_metadata


# ---------- Structured Logging (Phase 7) ----------

class _StructuredFormatter(logging.Formatter):
    """Emit log records as key=value structured lines."""

    def format(self, record: logging.LogRecord) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
        base = f"ts={ts} level={record.levelname} logger={record.name}"
        msg = record.getMessage()
        if record.exc_info and record.exc_info[1]:
            exc = self.formatException(record.exc_info)
            return f"{base} msg={msg} exception={exc}"
        return f"{base} msg={msg}"


_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(_StructuredFormatter())
logging.root.handlers.clear()
logging.root.addHandler(_handler)
logging.root.setLevel(logging.INFO)

logger = logging.getLogger("mcp.server")


# ---------- Rate Limiter (Phase 1) ----------

class _RateLimiter:
    """Simple sliding-window rate limiter (global, in-memory)."""

    def __init__(self, max_per_second: int = 50):
        self._max = max_per_second
        self._lock = threading.Lock()
        self._timestamps: deque[float] = deque()
        self._rejected: int = 0

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            # Purge timestamps older than 1 second
            while self._timestamps and (now - self._timestamps[0]) > 1.0:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._max:
                self._rejected += 1
                return False
            self._timestamps.append(now)
            return True

    @property
    def rejected_count(self) -> int:
        with self._lock:
            return self._rejected

    @property
    def current_window_count(self) -> int:
        now = time.monotonic()
        with self._lock:
            while self._timestamps and (now - self._timestamps[0]) > 1.0:
                self._timestamps.popleft()
            return len(self._timestamps)

    def reset(self) -> None:
        """Reset state — used by the lifespan to isolate test clients."""
        with self._lock:
            self._timestamps.clear()
            self._rejected = 0


_rate_limiter = _RateLimiter(max_per_second=50)


# ---------- Metrics (Phase 12) ----------

_start_time: float = 0.0
_request_count: int = 0
_endpoint_counts: dict[str, int] = {}
_response_times: deque[float] = deque(maxlen=10000)
_metrics_lock = threading.Lock()
_shutting_down: bool = False


def _record_request(endpoint: str, duration: float) -> None:
    with _metrics_lock:
        global _request_count
        _request_count += 1
        _endpoint_counts[endpoint] = _endpoint_counts.get(endpoint, 0) + 1
        _response_times.append(duration)


# ---------- Config Validation (Phase 5) ----------

_SCHEMA_RELATIVE_PATH = Path("Vault Files") / "Scripts" / "vault_schema.py"
_REQUIRED_SCHEMA_FUNCTIONS = ("discover_files", "parse_yaml_frontmatter")


def _validate_config() -> None:
    """Validate all vaults at startup. Raises on any failure."""
    vaults = list_vaults()
    if not vaults:
        raise RuntimeError("No vaults configured")

    for vault_name in vaults:
        vault_path = get_vault_path(vault_name)

        # Check vault directory exists
        if not vault_path.is_dir():
            raise RuntimeError(
                f"Vault directory missing: {vault_path} (vault={vault_name!r})"
            )

        # Check schema file exists
        schema_file = vault_path / _SCHEMA_RELATIVE_PATH
        if not schema_file.is_file():
            raise RuntimeError(
                f"Schema file missing: {schema_file} (vault={vault_name!r})"
            )

        # Load schema and check required functions
        schema = get_schema(vault_name)
        for func_name in _REQUIRED_SCHEMA_FUNCTIONS:
            if not hasattr(schema, func_name) or not callable(getattr(schema, func_name)):
                raise RuntimeError(
                    f"Schema for vault {vault_name!r} missing required function: {func_name}"
                )

        logger.info(
            "config_validated vault=%s path=%s schema=%s",
            vault_name, vault_path, schema_file,
        )


# ---------- Periodic Recheck (Phase 6) ----------

_RECHECK_INTERVAL_SECONDS = 300  # 5 minutes
_recheck_stop = threading.Event()


def _periodic_recheck_loop() -> None:
    """Background thread: run lightweight contract checks every 5 minutes."""
    while not _recheck_stop.wait(timeout=_RECHECK_INTERVAL_SECONDS):
        try:
            result = run_lightweight_checks()
            if result["status"] != "pass":
                logger.warning(
                    "periodic_recheck status=drift violations=%d details=%s",
                    result["total_violations"],
                    result["violations"],
                )
            else:
                logger.info(
                    "periodic_recheck status=ok duration_ms=%.1f",
                    result["duration_ms"],
                )
        except Exception:
            logger.exception("periodic_recheck_error")


# ---------- Startup / Shutdown (Phases 4 + 5) ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload all schemas and indexes at startup. Abort on any failure."""
    global _start_time, _shutting_down
    _start_time = time.monotonic()
    _shutting_down = False
    _rate_limiter.reset()

    # Phase 5: validate config before anything else
    logger.info("startup_config_validation")
    _validate_config()

    # Phase 4: preload all indexes
    vaults = list_vaults()
    for vault_name in vaults:
        logger.info("startup_building_index vault=%s", vault_name)
        build_index(vault_name)
        meta = get_index_metadata(vault_name)
        logger.info(
            "startup_vault_ready vault=%s notes=%d schema_hash=%s",
            vault_name, meta["notes"] if meta else 0,
            (meta["schema_hash"][:16] if meta else "unknown"),
        )

    # Startup contract enforcement (lightweight — no subprocess calls)
    logger.info("startup_contract_check")
    contract = run_all_checks(include_vault_scripts=False)
    if contract["status"] != "pass":
        for v in contract["violations"]:
            logger.error("startup_contract_violation detail=%s", v)
        raise RuntimeError(
            f"Contract check failed at startup: {contract['total_violations']} violations"
        )
    logger.info(
        "startup_contract_passed duration_ms=%.1f", contract["duration_ms"],
    )

    logger.info("startup_complete vaults=%d", len(vaults))

    # Phase 21: Private cloud mode startup checks
    _check_private_cloud_config()

    # Graceful shutdown: register signal handlers
    _install_signal_handlers()

    # Start periodic recheck background thread
    _recheck_stop.clear()
    recheck_thread = threading.Thread(
        target=_periodic_recheck_loop, daemon=True, name="contract-recheck",
    )
    recheck_thread.start()
    logger.info("periodic_recheck_started interval_s=%d", _RECHECK_INTERVAL_SECONDS)

    yield

    # Shutdown path
    _shutting_down = True
    _recheck_stop.set()
    logger.info(
        "shutdown_summary uptime_s=%d requests_served=%d",
        int(time.monotonic() - _start_time), _request_count,
    )


# ---------- Phase 21: Private Cloud Mode helpers ----------

# Mutating routes that are blocked when CVE_REMOTE_READ_ONLY=true.
# Matched by (method, path_prefix).  Order is checked most-specific first.
_WRITE_PATH_PREFIXES: tuple[tuple[str, str], ...] = (
    ("PUT", "/note"),
    ("POST", "/feedback/normalise"),
    ("POST", "/feedback"),
    ("PUT", "/feedback/"),
    ("DELETE", "/feedback/"),
    ("POST", "/vault/bootstrap"),
    ("DELETE", "/vault/"),
    ("POST", "/context/export"),
    # Phase 22: session and project state mutating routes
    ("POST", "/session/start"),
    ("POST", "/session/attach-note"),
    ("POST", "/session/close"),
    ("PUT", "/project/state"),
    # Phase 23: safe memory write queue mutating routes
    ("POST", "/memory/create-note-draft"),
    ("POST", "/memory/suggest-note-update"),
    ("POST", "/memory/update-section-draft"),
    ("POST", "/memory/pending/"),  # covers /memory/pending/{id}/accept and /reject
)

# Paths always allowed without auth (even when CVE_REQUIRE_AUTH=true).
_AUTH_EXEMPT_PATHS: frozenset[str] = frozenset({"/health", "/private/status"})


def _is_write_path(method: str, path: str) -> bool:
    """Return True if this method+path targets a mutating route."""
    method = method.upper()
    for m, prefix in _WRITE_PATH_PREFIXES:
        if method == m and path.startswith(prefix):
            return True
    return False


def _check_private_cloud_config() -> None:
    """Log a startup summary for private cloud mode.

    Does not raise; warnings are emitted to the structured log only.
    """
    cfg = load_private_cloud_config()
    if cfg["enabled"]:
        logger.info(
            "private_cloud_mode enabled=true deployment_mode=%s "
            "require_auth=%s token_configured=%s remote_read_only=%s",
            cfg["deployment_mode"],
            cfg["require_auth"],
            cfg["token_configured"],
            cfg["remote_read_only"],
        )
        for w in cfg["warnings"]:
            logger.warning("private_cloud_config_warning msg=%s", w)
    else:
        logger.info("private_cloud_mode enabled=false (local mode)")


def _install_signal_handlers() -> None:
    """Install handlers for SIGINT/SIGTERM for graceful shutdown logging."""
    def _handler(signum, frame):
        global _shutting_down
        sig_name = signal.Signals(signum).name
        logger.info(
            "shutdown_signal_received signal=%s requests_served=%d",
            sig_name, _request_count,
        )
        _shutting_down = True
        # Re-raise to let uvicorn handle actual shutdown
        raise SystemExit(0)

    try:
        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)
    except (OSError, ValueError):
        # signal handlers can only be set in main thread
        logger.warning("signal_handler_install_failed reason=not_main_thread")


app = FastAPI(
    title="Vault MCP Server",
    description="Read-only API over multiple Obsidian vaults",
    version="0.3.0",
    lifespan=lifespan,
)

# ---------- CORS (Phase 10) ----------
# Allow the Astro dev server (localhost:4321/4322) to call the API during
# development.  Production requests come from the same origin (/app on :8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4321",
        "http://127.0.0.1:4321",
        "http://localhost:4322",
        "http://127.0.0.1:4322",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-CVE-Token"],
    allow_credentials=False,
)

# Path to the compiled Astro frontend (relative to this file)
_UI_DIST: Path = Path(__file__).resolve().parent.parent.parent / "ui" / "dist"


# ---------- Exception Handlers ----------

@app.exception_handler(RequestValidationError)
async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic request-validation errors to the standard error envelope.

    Prevents FastAPI's default ``{"detail": [...]}`` shape from leaking out.
    """
    errors = exc.errors()
    msg = "; ".join(
        f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in errors
    )
    logger.warning("validation_error path=%s msg=%s", request.url.path, msg)
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error": {"code": "VALIDATION_ERROR", "message": msg},
        },
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all safety net: prevent raw tracebacks reaching the client."""
    logger.exception("unhandled_exception path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": {"code": "INTERNAL", "message": "An unexpected error occurred"},
        },
    )


# ---------- Middleware (Rate Limiting + Metrics) ----------

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    # Phase 1: rate limiting
    if not _rate_limiter.allow():
        logger.warning("rate_limit_exceeded path=%s", request.url.path)
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "error": {
                    "code": "RATE_LIMIT",
                    "message": "Too many requests",
                },
            },
        )

    # Phase 21: authentication check
    path = request.url.path
    if path not in _AUTH_EXEMPT_PATHS and require_auth():
        # Extract token from Authorization: Bearer <token> or X-CVE-Token: <token>
        token_candidate = ""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token_candidate = auth_header[7:].strip()
        if not token_candidate:
            token_candidate = request.headers.get("X-CVE-Token", "").strip()

        if not verify_token(token_candidate):
            logger.warning(
                "auth_required_rejected method=%s path=%s", request.method, path
            )
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "error": {
                        "code": "AUTH_REQUIRED",
                        "message": (
                            "Authentication required. "
                            "Provide a valid token via 'Authorization: Bearer <token>' "
                            "or 'X-CVE-Token: <token>' header."
                        ),
                    },
                },
            )

    # Phase 21: remote read-only enforcement
    if _is_write_path(request.method, path) and is_remote_read_only():
        logger.warning(
            "read_only_blocked method=%s path=%s", request.method, path
        )
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "error": {
                    "code": "REMOTE_READ_ONLY",
                    "message": "Remote read-only mode blocks this operation.",
                },
            },
        )

    # Phase 7: structured request logging
    start = time.monotonic()
    logger.info("request_start method=%s path=%s", request.method, request.url.path)

    response = await call_next(request)

    duration = time.monotonic() - start
    _record_request(request.url.path, duration)

    logger.info(
        "request_end method=%s path=%s status=%d duration_ms=%.1f",
        request.method, request.url.path, response.status_code, duration * 1000,
    )
    return response


# ---------- Request / Response models ----------

class QueryRequest(BaseModel):
    """Request body for POST /query."""

    vault: str = Field(..., description="Vault name to query")
    filters: dict = Field(default_factory=dict, description="Key/value filters; supports __in and __contains suffixes")
    limit: int = Field(default=50, ge=1, le=500, description="Page size (1–500)")
    offset: int = Field(default=0, ge=0, description="Page offset")
    strict: bool = Field(default=False, description="Reject unknown filter fields when True")
    q: str | None = Field(default=None, description="Free-text lexical search string (max 1000 chars)")
    q_fields: list[str] | None = Field(default=None, description="Fields to search: body, path, frontmatter (default: [body])")


class CompareRequest(BaseModel):
    before: str = Field(..., min_length=1, description="Path to BEFORE report (relative to vault root or absolute)")
    after: str | None = Field(None, description="Path to AFTER report (omit for live vault analysis)")
    vault: str | None = Field(None, description="Vault name (defaults to first registered vault)")


class BundleRequest(BaseModel):
    """Request body for POST /context/bundle."""

    vault: str = Field(..., description="Vault name")
    filters: dict = Field(
        default_factory=dict,
        description="Equality filters on frontmatter fields (e.g. {\"domain\": \"fundamentals\"})",
    )
    include_sections: list[str] = Field(
        default_factory=lambda: ["Key Principles", "How It Works", "Trade-offs"],
        description="Section names to extract (without '## ' prefix)",
    )
    include_related: bool = Field(
        default=False,
        description="Include graph relationship IDs for each note",
    )
    include_body: bool = Field(
        default=True,
        description="Include full note body text",
    )
    max_notes: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum notes to include (1–100)",
    )
    max_chars: int = Field(
        default=20000,
        ge=100,
        le=500000,
        description="Character budget (100–500000)",
    )
    allow_partial: bool = Field(
        default=False,
        description="Include notes with status=partial",
    )
    profile: str | None = Field(
        default=None,
        description=(
            "Named device profile (e.g. 'phone-local-llm', 'desktop-agent'). "
            "Profile values are applied as defaults; explicit fields take precedence. "
            "If both profile and mode are provided, profile takes precedence."
        ),
    )
    mode: str | None = Field(
        default=None,
        description=(
            "Named bundle mode (e.g. 'tiny', 'small', 'medium', 'large', 'agent'). "
            "Mode values are applied as defaults; explicit fields take precedence. "
            "Ignored when profile is also supplied."
        ),
    )


class ExportRequest(BaseModel):
    """Request body for POST /context/export."""

    vault: str = Field(..., description="Vault name")
    filters: dict = Field(
        default_factory=dict,
        description="Equality filters on frontmatter fields (e.g. {\"domain\": \"fundamentals\"})",
    )
    include_sections: list[str] = Field(
        default_factory=lambda: ["Key Principles", "How It Works", "Trade-offs"],
        description="Section names to extract (without '## ' prefix)",
    )
    include_related: bool = Field(
        default=False,
        description="Include graph relationship IDs for each note",
    )
    include_body: bool = Field(
        default=True,
        description="Include full note body text",
    )
    max_notes: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum notes to include (1–100)",
    )
    max_chars: int = Field(
        default=20000,
        ge=100,
        le=500000,
        description="Character budget (100–500000)",
    )
    allow_partial: bool = Field(
        default=False,
        description="Include notes with status=partial",
    )
    overwrite: bool = Field(
        default=False,
        description="Overwrite an existing package for this bundle_id",
    )
    require_security_pass: bool = Field(
        default=False,
        description="If True, abort export when security scan status is 'fail'",
    )
    profile: str | None = Field(
        default=None,
        description=(
            "Named device profile (e.g. 'phone-local-llm', 'desktop-agent'). "
            "Profile values are applied as defaults; explicit fields take precedence. "
            "If profile requires_security_scan, require_security_pass is enforced."
        ),
    )
    mode: str | None = Field(
        default=None,
        description=(
            "Named bundle mode (e.g. 'tiny', 'small', 'medium', 'large', 'agent'). "
            "Ignored when profile is also supplied."
        ),
    )


class SecurityRequest(BaseModel):
    """Request body for POST /context/security."""

    vault: str = Field(..., description="Vault name")
    filters: dict = Field(
        default_factory=dict,
        description="Equality filters on frontmatter fields (e.g. {\"status\": \"complete\"})",
    )
    include_sections: list[str] = Field(
        default_factory=lambda: ["Key Principles", "How It Works", "Trade-offs"],
        description="Section names to scan (without '## ' prefix)",
    )
    include_body: bool = Field(
        default=True,
        description="Include full note body text in scan scope",
    )
    max_notes: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum notes to include (1–1000). Default 200 covers typical full-vault scans.",
    )
    max_chars: int = Field(
        default=10_000_000,
        ge=100,
        le=50_000_000,
        description="Character budget (100–50000000). Default 10 000 000 covers typical full-vault scans.",
    )
    allow_partial: bool = Field(
        default=True,
        description=(
            "Include notes with status=partial. Defaults to True so that a "
            "vault-level security scan does not silently exclude partial notes, "
            "which can still contain secrets or injection phrases."
        ),
    )
    profile: str | None = Field(
        default=None,
        description=(
            "Named device profile — applies as defaults for max_notes, max_chars, "
            "include_body, include_sections. Profile takes precedence over mode."
        ),
    )
    mode: str | None = Field(
        default=None,
        description=(
            "Named bundle mode (e.g. 'tiny', 'small', 'medium', 'large', 'agent'). "
            "Ignored when profile is also supplied."
        ),
    )


class FeedbackCreateRequest(BaseModel):
    """Request body for POST /feedback."""

    vault: str = Field(..., description="Vault name")
    path: str = Field(..., description="Vault-relative note path (POSIX forward slashes)")
    source: str = Field(..., description="Feedback source: human | agent | system")
    signal: str = Field(..., description="Feedback signal (e.g. unclear, incomplete, useful)")
    severity: str = Field(..., description="Severity: low | medium | high | critical")
    comment: str = Field(..., description="Human-readable feedback comment (max 2000 chars)")


class FeedbackUpdateRequest(BaseModel):
    """Request body for PUT /feedback/{feedback_id}."""

    vault: str = Field(..., description="Vault name")
    path: str = Field(..., description="Vault-relative note path (POSIX forward slashes)")
    source: str = Field(..., description="Feedback source: human | agent | system")
    signal: str = Field(..., description="Feedback signal (e.g. unclear, incomplete, useful)")
    severity: str = Field(..., description="Severity: low | medium | high | critical")
    comment: str = Field(..., description="Human-readable feedback comment (max 2000 chars)")


class VaultBootstrapRequest(BaseModel):
    """Request body for POST /vault/bootstrap."""

    vault_name: str = Field(..., description="New vault directory name (e.g. 'dogs-vault')")
    domain: str = Field(..., description="Primary domain display name (e.g. 'Dogs')")
    note_type: str = Field(..., description="Note type slug (e.g. 'breed-profile')")
    sections: list[str] = Field(..., description="Canonical section names (minimum 2)")
    expected_concepts: list[str] = Field(
        default_factory=list,
        description="Optional expected concept names. Written into EXPECTED_CONCEPTS in vault_schema.py.",
    )


class NoteUpdateRequest(BaseModel):
    """Request body for PUT /note."""

    vault: str = Field(..., description="Vault name")
    path: str = Field(..., description="Vault-relative POSIX path to the note (e.g. 'Fundamentals/Algorithms.md')")
    fields: dict[str, Any] = Field(..., description="Complete frontmatter fields for the updated note")
    body: str = Field(..., description="Markdown body text (without frontmatter)")


# ---------- Error helpers ----------

def _error(code: str, message: str, status_code: int = 400) -> JSONResponse:
    """Return a standard error envelope as a JSONResponse.

    Shape: ``{"status": "error", "error": {"code": ..., "message": ...}}``
    """
    logger.error("error_response code=%s message=%s status=%d", code, message, status_code)
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error": {"code": code, "message": message},
        },
    )


def _validate_vault(vault_name: str) -> JSONResponse | None:
    """Return a 404 error response if the vault is not registered, else None."""
    try:
        get_vault_path(vault_name)
    except KeyError as exc:
        return _error("INVALID_VAULT", str(exc), 404)
    return None


# ---------- Endpoints ----------

@app.get("/vaults")
def endpoint_vaults():
    """List all registered vault names.

    Response data:
        vaults (list[str]): Sorted list of registered vault names.
    """
    try:
        return {"status": "ok", "data": {"vaults": sorted(list_vaults())}}
    except Exception as exc:
        return _error("INTERNAL", f"Failed to list vaults: {exc}", 500)


@app.post("/query")
def endpoint_query(req: QueryRequest):
    """Query a vault with optional filters and optional lexical search.

    Response data:
        status (str): ``"ok"`` or ``"partial"`` (partial = query timed out).
        count (int): Total matching notes before pagination.
        returned (int): Notes in this page.
        offset (int): Page offset applied.
        limit (int): Page size applied.
        results (list): Matching note objects with ``path``, ``fields``,
            and (when ``q`` is supplied) ``score``.
    """
    err = _validate_vault(req.vault)
    if err:
        return err

    try:
        q_active = bool(req.q and req.q.strip())
        if req.filters or q_active:
            result = query(
                req.vault,
                req.filters,
                limit=req.limit,
                offset=req.offset,
                strict=req.strict,
                q=req.q,
                q_fields=req.q_fields,
            )
        else:
            result = list_notes(req.vault, limit=req.limit, offset=req.offset)

        # Forward engine-level error responses
        if result["status"] == "error":
            return JSONResponse(status_code=400, content=result)
        # Phase 25: annotate query results with trust metadata (non-breaking)
        if "results" in result and isinstance(result["results"], list):
            result["results"] = _trust_metadata.annotate_notes_with_trust(result["results"])
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("QUERY_FAILED", f"Query failed: {exc}", 500)


@app.get("/note")
def endpoint_note(
    vault: str = Query(..., description="Vault name"),
    path: str = Query(..., description="Relative note path"),
):
    """Retrieve a single note by vault and path.

    Response data:
        path (str): Vault-relative path to the note.
        fields (dict): All parsed frontmatter fields.

    Error codes:
        NOT_FOUND: No note exists at the given path.
        PATH_TRAVERSAL: Path attempts to escape the vault root.
    """
    err = _validate_vault(vault)
    if err:
        return err

    try:
        result = get_note(vault, path)
        if result["status"] == "error":
            code = result["error"].get("code", "UNKNOWN")
            status_code = 404 if code == "NOT_FOUND" else 400
            return JSONResponse(status_code=status_code, content=result)
        return result
    except Exception as exc:
        return _error("RETRIEVAL_FAILED", f"Retrieval failed: {exc}", 500)


@app.put("/note")
def endpoint_note_update(req: NoteUpdateRequest):
    """Safely update an existing Markdown note.

    Validates path safety, field schema, and body integrity before writing.
    Writes atomically via temp-file-then-rename in the same directory.
    Expires the index cooldown after a successful write so that subsequent
    GET /note and POST /query reflect the updated content immediately.

    Request body:
        vault (str, required): Vault name.
        path (str, required): Vault-relative POSIX path (e.g. ``Fundamentals/Algorithms.md``).
        fields (dict, required): Complete frontmatter fields for the updated note.
        body (str, required): Markdown body text (without frontmatter).

    Response data on success:
        path (str): Vault-relative path of the updated note.
        fields (dict): Parsed frontmatter fields as written.
        body (str): Markdown body as written.
        validation (dict): ``{"status": "pass", "errors": []}``.
        warnings (list): Non-fatal notices (empty in most cases).

    Error codes:
        INVALID_VAULT:        Vault is not registered (HTTP 404).
        INVALID_INPUT:        Request body fails Pydantic or structural validation (HTTP 400).
        PATH_TRAVERSAL:       path escapes the vault root (HTTP 400).
        NOT_FOUND:            Note does not exist (HTTP 404).
        INVALID_NOTE_PATH:    path is absolute, not ``.md``, or inside ``Vault Files/`` (HTTP 400).
        VALIDATION_FAILED:    Candidate note fails schema validation (HTTP 400).
        WRITE_FAILED:         Atomic write to disk failed (HTTP 500).

    Safety:
        - PUT /note only updates existing notes.  It cannot create new notes.
        - PUT /note cannot write outside the vault root.
        - PUT /note cannot write into ``Vault Files/``.
        - On any validation or write failure the original file is left unchanged.
    """
    err = _validate_vault(req.vault)
    if err:
        return err

    result = _update_note(req.vault, req.path, req.fields, req.body)

    if result["status"] == "error":
        code = result["error"].get("code", "UNKNOWN")
        if code in ("NOT_FOUND", "INVALID_VAULT"):
            status_code = 404
        elif code == "WRITE_FAILED":
            status_code = 500
        else:
            status_code = 400
        return JSONResponse(status_code=status_code, content=result)

    return result


@app.get("/stats")
def endpoint_stats(
    vault: str = Query(..., description="Vault name"),
    field: str = Query(..., description="Field to aggregate"),
):
    """Aggregate distinct values for a field across a vault.

    Response data:
        field (str): The aggregated field name.
        stats (dict): Mapping of field value → note count, ordered by frequency.

    Error codes:
        INVALID_FIELD: The requested field is not known to the vault schema.
    """
    err = _validate_vault(vault)
    if err:
        return err

    try:
        result = aggregate(vault, field)
        if result["status"] == "error":
            return JSONResponse(status_code=400, content=result)
        return result
    except Exception as exc:
        return _error("AGGREGATION_FAILED", f"Aggregation failed: {exc}", 500)


@app.get("/health")
def endpoint_health():
    """Server health, vault metrics, and request statistics.

    Always returns HTTP 200 if the endpoint itself is reachable.

    Response data:
        vaults (dict): Per-vault index stats (notes, schema_hash, last_index_time).
        uptime_seconds (int): Seconds since server started.
        requests_served (int): Total requests handled.
        rate_limit_status (dict): Current rate-limiter counters.
        metrics (dict): Per-endpoint request counts and average response time.
    """
    try:
        vaults_info = {}
        for vault_name in list_vaults():
            meta = get_index_metadata(vault_name)
            if meta:
                vaults_info[vault_name] = {
                    "notes": meta["notes"],
                    "schema_hash": meta["schema_hash"],
                    "last_index_time": meta["last_build_time"],
                    "index_size_bytes": meta["index_size_bytes"],
                    "schema_last_checked": meta["last_schema_check"],
                }
            else:
                idx = get_index(vault_name)
                vaults_info[vault_name] = {
                    "notes": len(idx),
                    "schema_hash": get_schema_hash(vault_name) or "unknown",
                }

        with _metrics_lock:
            avg_response = (
                sum(_response_times) / len(_response_times)
                if _response_times else 0.0
            )
            health_data = {
                "vaults": vaults_info,
                "uptime_seconds": int(time.monotonic() - _start_time),
                "requests_served": _request_count,
                "rate_limit_status": {
                    "max_per_second": 50,
                    "current_window": _rate_limiter.current_window_count,
                    "total_rejected": _rate_limiter.rejected_count,
                },
                "metrics": {
                    "per_endpoint": dict(sorted(_endpoint_counts.items())),
                    "avg_response_time_ms": round(avg_response * 1000, 2),
                },
            }

        return {"status": "ok", "data": health_data}
    except Exception as exc:
        return _error("HEALTH_FAILED", f"Health check failed: {exc}", 500)


@app.get("/private/status")
def endpoint_private_status():
    """Return private cloud mode configuration status.

    Always returns HTTP 200 when reachable.  Never includes the raw auth token.

    Response data:
        enabled (bool): True if CVE_PRIVATE_CLOUD_ENABLED=true.
        deployment_mode (str): Value of CVE_DEPLOYMENT_MODE (local/vps/tunnel).
        require_auth (bool): True if authentication is currently required.
        token_configured (bool): True if a non-empty CVE_AUTH_TOKEN is set.
        remote_read_only (bool): True if mutating routes are blocked.
        public_base_url (str | null): Value of CVE_PUBLIC_BASE_URL if set.
        warnings (list[str]): Configuration warnings (no secrets).
        protected_methods (list[str]): HTTP methods blocked in read-only mode.

    Note:
        /private/status is accessible without authentication even when
        CVE_REQUIRE_AUTH=true, so operators can verify configuration.
    """
    try:
        return {"status": "ok", "data": private_cloud_status()}
    except Exception as exc:
        return _error("STATUS_FAILED", f"Status check failed: {exc}", 500)


@app.get("/contract")
def endpoint_contract(
    full: bool = Query(False, description="Run full checks including vault scripts"),
):
    """Run system contract checks and return results.

    Response data:
        status (str): ``"pass"`` or ``"fail"`` — the contract result.
        duration_ms (float): Time taken to run all checks.
        vaults (dict): Per-vault check results with per-check breakdown.
        total_violations (int): Total number of violations found.
        violations (list[str]): Flat list of all violation descriptions.

    Note:
        A ``data.status`` of ``"fail"`` means contract violations were found.
        The HTTP status is always 200 when the check completes successfully.
    """
    try:
        if full:
            result = run_all_checks(include_vault_scripts=True)
        else:
            result = run_all_checks(include_vault_scripts=False)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("CONTRACT_FAILED", f"Contract check failed: {exc}", 500)


# ---------- Adapter Endpoints (Phase 2) ----------


@app.get("/validation")
def endpoint_validation(
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
):
    """Run vault validation and return structured results.

    Response data:
        status (str): ``"pass"`` or ``"fail"``.
        invalid_count (int): Number of notes that failed validation.
        invalid_notes (list[str]): Sorted vault-relative paths of invalid notes.
    """
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err
    try:
        result = get_validation(vault_name=vault)
        if "error" in result:
            return _error("VALIDATION_FAILED", result["error"], 500)
        result["invalid_notes"] = sorted(result.get("invalid_notes", []))
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("VALIDATION_FAILED", f"Validation failed: {exc}", 500)


@app.get("/summary")
def endpoint_summary(
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
):
    """Aggregate vault-level decision signals.

    Response data:
        total_notes (int): Total notes in the vault.
        complete (int): Notes with status ``"complete"``.
        partial (int): Notes not yet complete.
        coverage (int): Completion percentage (0–100).
    """
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err
    try:
        result = get_all_notes(vault_name=vault)
        if "error" in result:
            return _error("SUMMARY_FAILED", result["error"], 500)

        notes = result["notes"]
        total = len(notes)
        complete = sum(1 for n in notes if n["status"] == "complete")
        partial = total - complete
        coverage = int((complete / total) * 100) if total > 0 else 0

        return {
            "status": "ok",
            "data": {
                "total_notes": total,
                "complete": complete,
                "partial": partial,
                "coverage": coverage,
            },
        }
    except Exception as exc:
        return _error("SUMMARY_FAILED", f"Summary failed: {exc}", 500)


def _normalise_task(task: dict, include_feedback: bool = False) -> dict:
    """Transform a raw adapter task into a normalised decision-ready structure."""
    missing = task.get("missing", [])
    target = missing[0] if missing else ""
    result = {
        "note": task["note"],
        "path": task.get("path", ""),
        "priority": task["priority"],
        "type": "missing_section",
        "target": target,
        "missing": missing,
        "instruction": f"Add missing section: {target}" if target else "Review note",
        "constraints": task.get("constraints", []),
    }
    if include_feedback and "feedback_weight" in task:
        result["feedback_weight"] = task["feedback_weight"]
    return result


@app.get("/tasks")
def endpoint_tasks(
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
    limit: int = Query(10, ge=1, description="Maximum number of tasks to return"),
    min_priority: float = Query(None, description="Minimum priority threshold"),
    include_feedback: bool = Query(False, description="Adjust task scores by feedback signals"),
):
    """Return prioritised upgrade tasks, optionally filtered by min_priority.

    Response data:
        total (int): Total tasks available before filtering.
        tasks (list): Normalised task objects, sorted descending by priority.

    Each task object:
        note (str): Note stem name.
        path (str): Vault-relative POSIX path to the note.
        priority (float): Computed priority score (adjusted by feedback when include_feedback=true).
        type (str): Always ``"missing_section"``.
        target (str): Primary missing section.
        missing (list[str]): All missing sections.
        instruction (str): Human-readable action.
        constraints (list[str]): Writing constraints for the primary issue.
        feedback_weight (dict): Score delta, entry count, and summary (only when include_feedback=true).

    When include_feedback=true:
        feedback_status (str): ``"ok"`` or ``"error"`` from feedback parser.
        feedback_errors (list): Structured errors from feedback parser (if any).
    """
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err
    try:
        # Fetch all tasks (no limit at adapter level when filtering)
        result = get_tasks(vault_name=vault, limit=9999, include_feedback=include_feedback)
        if "error" in result:
            return _error("TASKS_FAILED", result["error"], 500)

        tasks = result["tasks"]

        # Filter by min_priority if provided
        if min_priority is not None:
            tasks = [t for t in tasks if t["priority"] >= min_priority]

        # Sort descending by priority, then ascending by note name for stability
        tasks.sort(key=lambda t: (-t["priority"], t["note"].lower()))

        # Apply limit after filtering
        tasks = tasks[:limit]

        # Normalise
        normalised = [_normalise_task(t, include_feedback=include_feedback) for t in tasks]

        response_data: dict = {
            "total": len(result["tasks"]),
            "tasks": normalised,
        }

        if include_feedback:
            response_data["feedback_status"] = result.get("feedback_status", "ok")
            response_data["feedback_errors"] = result.get("feedback_errors", [])

        return {
            "status": "ok",
            "data": response_data,
        }
    except Exception as exc:
        return _error("TASKS_FAILED", f"Tasks retrieval failed: {exc}", 500)


@app.get("/gaps")
def endpoint_gaps():
    """Return high-impact incomplete notes (priority >= 2).

    Response data:
        gaps (list): Incomplete notes sorted descending by priority.

    Each gap object:
        note (str): Note stem name.
        priority (float): Task priority score.
        missing (list[str]): Missing section slugs.
    """
    try:
        result = get_tasks(limit=9999)
        if "error" in result:
            return _error("GAPS_FAILED", result["error"], 500)

        notes_result = get_all_notes()
        if "error" in notes_result:
            return _error("GAPS_FAILED", notes_result["error"], 500)

        partial_names = {
            n["name"] for n in notes_result["notes"] if n["status"] == "partial"
        }

        gaps = []
        for task in result["tasks"]:
            if task["note"] in partial_names and task["priority"] >= 2:
                gaps.append({
                    "note": task["note"],
                    "priority": task["priority"],
                    "missing": task["missing"],
                })

        # Sort descending by priority, then ascending by note name for stability
        gaps.sort(key=lambda g: (-g["priority"], g["note"].lower()))

        return {"status": "ok", "data": {"gaps": gaps}}
    except Exception as exc:
        return _error("GAPS_FAILED", f"Gaps retrieval failed: {exc}", 500)


@app.get("/notes")
def endpoint_notes(
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
):
    """List all notes with metadata, sorted alphabetically by name.

    Response data:
        notes (list): All vault notes, sorted ascending by name (case-insensitive).

    Each note object:
        name (str): Note stem (filename without extension).
        status (str): Frontmatter status field (e.g. ``"complete"``, ``"partial"``).
        difficulty (str): Frontmatter difficulty field.
        missing (list[str]): Missing required section slugs.
        path (str): Vault-relative POSIX path.
    """
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err
    try:
        result = get_all_notes(vault_name=vault)
        if "error" in result:
            return _error("NOTES_FAILED", result["error"], 500)
        result["notes"].sort(key=lambda n: n["name"].lower())
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("NOTES_FAILED", f"Notes retrieval failed: {exc}", 500)


# ---------- Phase 4A: Completion endpoints ----------


@app.get("/quality")
def endpoint_quality(
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
):
    """Run content quality audit and return structured results.

    Response data:
        total (int): Total notes audited.
        flagged (int): Notes with at least one quality issue.
        highest_score (int): Highest quality penalty score found.
        average_score (float): Mean penalty score across all notes.
        notes (list): Per-note audit results, sorted descending by score.

    Each note entry:
        file (str): Vault-relative file path.
        score (int): Total penalty score (higher = more issues).
        severity (str): Severity band (e.g. ``"low"``, ``"high"``).
        issues (list): Per-rule violations with ``rule``, ``weight``, ``explanation``.
    """
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err
    try:
        result = get_quality(vault_name=vault)
        if "error" in result:
            return _error("QUALITY_FAILED", result["error"], 500)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("QUALITY_FAILED", f"Quality audit failed: {exc}", 500)


@app.get("/missing")
def endpoint_missing(
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
):
    """Detect missing concepts across all expected subdomains.

    Response data:
        total_expected (int): Total concepts expected across all subdomains.
        total_actual (int): Concepts currently present in the vault.
        total_missing (int): Concepts not yet present.
        domains_assessed (int): Number of top-level domains covered.
        subdomains (int): Number of subdomains assessed.
        gaps (dict): Mapping of subdomain → list of missing concept objects.
        ranked (list): All missing concepts ranked by score, highest first.

    Each ranked entry:
        rank (int): 1-based rank.
        score (float): Importance score.
        subdomain (str): Subdomain name.
        concept (str): Missing concept name.

    Note:
        Returns a structured MISSING_CONCEPTS_EMPTY error if
        EXPECTED_CONCEPTS is not defined or empty in vault_schema.py.
    """
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err
    try:
        result = get_missing(vault_name=vault)
        if "error" in result:
            code = (
                "MISSING_CONCEPTS_EMPTY"
                if "EXPECTED_CONCEPTS" in result["error"]
                else "MISSING_FAILED"
            )
            return _error(code, result["error"], 422 if code == "MISSING_CONCEPTS_EMPTY" else 500)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("MISSING_FAILED", f"Missing concepts detection failed: {exc}", 500)


@app.post("/compare")
def endpoint_compare(req: CompareRequest):
    """Compare two vault states and return a structured delta report.

    Request body:
        before (str, required): Path to the BEFORE report (relative to vault root
            or absolute). Must be non-empty.
        after (str, optional): Path to the AFTER report. Omit to use the live
            vault state as the AFTER snapshot.
        vault (str, optional): Vault name; defaults to the first registered vault.

    Response data:
        before (dict): Snapshot metrics from the BEFORE report.
        after (dict): Snapshot metrics from the AFTER (report or live vault).
        delta (dict): Differences between before and after snapshots.
        report (str): Full markdown delta report.

    Error codes:
        INVALID_INPUT: ``before`` is blank or whitespace-only.
        COMPARE_FAILED: Report file not found or comparison error.
    """
    if not req.before.strip():
        return _error("INVALID_INPUT", "'before' must not be blank or whitespace-only")
    try:
        result = get_compare(
            before=req.before,
            after=req.after,
            vault_name=req.vault,
        )
        if "error" in result:
            return _error("COMPARE_FAILED", result["error"], 500)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("COMPARE_FAILED", f"Compare failed: {exc}", 500)


# ---------- Phase 5: Relationship Graph ----------


@app.get("/graph")
def endpoint_graph(
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
):
    """Return a deterministic relationship graph of all vault notes.

    Relationships are derived solely from schema-defined hierarchy
    (domain / subdomain / topic) and note frontmatter fields.
    No LLMs, no embeddings, no natural-language parsing.

    Response data:
        nodes (list): All graph nodes, sorted ascending by id.
        edges (list): All graph edges, sorted ascending by (from, to, type).

    Each node:
        id (str): Unique node identifier.
        type (str): One of ``note``, ``domain``, ``subdomain``, ``topic``,
            ``expected_concept``.
        label (str): Human-readable name.

    Each edge:
        from (str): Source node id.
        to (str): Target node id.
        type (str): One of ``parent``, ``same_domain``, ``same_subdomain``,
            ``same_topic``, ``expected_coverage``.
    """
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err
    try:
        graph = build_graph(vault_name=vault)
        return {
            "status": "ok",
            "data": graph,
        }
    except Exception as exc:
        return _error("GRAPH_FAILED", f"Graph build failed: {exc}", 500)


# ---------- Phase 6: Graph Query Layer ----------


@app.get("/graph/neighbors")
def endpoint_graph_neighbors(
    node: str = Query(..., description="Node id to query"),
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
):
    """Return all nodes directly connected to the given node (both edge directions).

    Response data:
        node_id (str): The queried node id.
        found (bool): Whether the node exists in the graph.
        neighbors (list): Directly connected nodes, sorted ascending by id.

    Each neighbor:
        id (str): Node id.
        type (str): Node type.
        label (str): Human-readable name.
        edge_type (str): The type of the connecting edge.
    """
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err
    try:
        graph = build_graph(vault_name=vault)
        result = get_neighbors(graph, node)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("GRAPH_QUERY_FAILED", f"Neighbors query failed: {exc}", 500)


@app.get("/graph/related")
def endpoint_graph_related(
    node: str = Query(..., description="Node id to query"),
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
    min_strength: str = Query("domain", description="Minimum relationship strength: topic | subdomain | domain"),
):
    """Return notes that share a group hub (domain/subdomain/topic) with the given node.

    Traversal: note → group node → all other notes in that group.
    Strength is derived from the type of the strongest shared hub:
      topic (strongest) > subdomain > domain (weakest).

    Response data:
        node_id (str): The queried node id.
        found (bool): Whether the node exists in the graph.
        related (list): Related notes, sorted by strength desc then id asc.

    Each related entry:
        id (str): Note id (vault-relative path).
        type (str): Node type.
        label (str): Human-readable name.
        via (str): The strongest group node id through which the relationship was found.
        strength (str): "topic" | "subdomain" | "domain".

    Query parameters:
        min_strength: Exclude relationships weaker than this level.
                      Accepts "topic", "subdomain", or "domain" (default).
    """
    from mcp.core.graph_query import VALID_STRENGTHS
    if min_strength not in VALID_STRENGTHS:
        return _error(
            "INVALID_PARAM",
            f"min_strength must be one of: {sorted(VALID_STRENGTHS)}",
            400,
        )
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err
    try:
        graph = build_graph(vault_name=vault)
        result = get_related_nodes(graph, node, min_strength=min_strength)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("GRAPH_QUERY_FAILED", f"Related query failed: {exc}", 500)


@app.get("/graph/missing")
def endpoint_graph_missing(
    node: str = Query(..., description="Node id to query"),
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
):
    """Return expected concepts missing from this note's group hubs.

    These are concepts the schema declares as expected (EXPECTED_CONCEPTS)
    near this note's domain/subdomain/topic cluster that are not yet present
    in the vault.

    Response data:
        node_id (str): The queried node id.
        found (bool): Whether the node exists in the graph.
        missing (list): Missing expected concepts, sorted ascending by id.

    Each missing entry:
        id (str): expected_concept node id.
        label (str): Concept name.
        via (str): The group node that declared this expected concept.
    """
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err
    try:
        graph = build_graph(vault_name=vault)
        result = get_missing_neighbors(graph, node)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("GRAPH_QUERY_FAILED", f"Missing neighbors query failed: {exc}", 500)


# ---------- Phase 1: Vault-Parameterised Graph Routes ----------
#
# These routes mirror the existing /graph, /graph/related, and /graph/missing
# endpoints but accept the vault name as a URL path segment rather than a
# query parameter.  The literal-path routes above are registered first, so
# FastAPI resolves /graph/related → endpoint_graph_related (not this group).


@app.get("/graph/{vault}")
def endpoint_graph_by_vault(vault: str):
    """Return a deterministic relationship graph of the specified vault.

    Identical to GET /graph?vault=<vault> but with the vault name in the path.

    Response data:
        nodes (list): All graph nodes, sorted ascending by id.
        edges (list): All graph edges, sorted ascending by (from, to, type).
    """
    err = _validate_vault(vault)
    if err:
        return err
    try:
        graph = build_graph(vault_name=vault)
        return {"status": "ok", "data": graph}
    except Exception as exc:
        return _error("GRAPH_FAILED", f"Graph build failed: {exc}", 500)


@app.get("/graph/{vault}/related")
def endpoint_graph_vault_related(
    vault: str,
    node_id: str = Query(..., description="Node id to query"),
    min_strength: str = Query(
        "domain",
        description="Minimum relationship strength: topic | subdomain | domain",
    ),
):
    """Return notes that share a group hub with the given node in the specified vault.

    Traversal: note → group node → all other notes in that group.
    Strength is derived from the type of the strongest shared hub:
      topic (strongest) > subdomain > domain (weakest).

    Response data:
        node_id (str): The queried node id.
        found (bool): Whether the node exists in the graph.
        related (list): Related notes, sorted by strength desc then id asc.

    Each related entry:
        id (str): Note id (vault-relative POSIX path).
        type (str): Node type.
        label (str): Human-readable name.
        via (str): The strongest group node id through which the relationship was found.
        strength (str): "topic" | "subdomain" | "domain".
    """
    from mcp.core.graph_query import VALID_STRENGTHS
    err = _validate_vault(vault)
    if err:
        return err
    if min_strength not in VALID_STRENGTHS:
        return _error(
            "INVALID_PARAM",
            f"min_strength must be one of: {sorted(VALID_STRENGTHS)}",
            400,
        )
    try:
        graph = build_graph(vault_name=vault)
        result = get_related_nodes(graph, node_id, min_strength=min_strength)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("GRAPH_QUERY_FAILED", f"Related query failed: {exc}", 500)


@app.get("/graph/{vault}/missing")
def endpoint_graph_vault_missing(
    vault: str,
    node_id: str = Query(..., description="Node id to query"),
):
    """Return expected concepts missing from this note's group hubs in the specified vault.

    These are concepts the schema declares as expected (EXPECTED_CONCEPTS)
    near this note's domain/subdomain/topic cluster that are not yet present
    in the vault.

    Response data:
        node_id (str): The queried node id.
        found (bool): Whether the node exists in the graph.
        missing (list): Missing expected concepts, sorted ascending by id.

    Each missing entry:
        id (str): expected_concept node id.
        label (str): Concept name.
        via (str): The group node that declared this expected concept.
    """
    err = _validate_vault(vault)
    if err:
        return err
    try:
        graph = build_graph(vault_name=vault)
        result = get_missing_neighbors(graph, node_id)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("GRAPH_QUERY_FAILED", f"Missing neighbors query failed: {exc}", 500)


# ---------- Phase 2: Context Bundle ----------


@app.post("/context/bundle")
def endpoint_context_bundle(req: BundleRequest):
    """Generate a deterministic context bundle of selected vault notes.

    A bundle packages selected notes with frontmatter, optional section
    extracts, optional full bodies, optional graph relationships, validation
    state, and budget information.

    Request body:
        vault (str, required): Vault name.
        filters (dict): Equality filters on frontmatter fields.
        include_sections (list[str]): Section names to extract (without '## ').
            Defaults to ['Key Principles', 'How It Works', 'Trade-offs'].
        include_related (bool): Include graph relationship IDs per note.
        include_body (bool): Include full note body text. Default True.
        max_notes (int): Maximum notes (1–100). Default 10.
        max_chars (int): Character budget (100–500000). Default 20000.
        allow_partial (bool): Include status=partial notes. Default False.

    Response:
        status (str): ``"ok"`` on success.
        bundle_id (str): Deterministic 16-char hex ID (excludes timestamp).
        vault (str): Vault name used.
        filters (dict): Filters applied.
        created_at (str): ISO-8601 UTC timestamp.
        validation_status (str): ``"pass"`` or ``"fail"`` for selected notes.
        notes (list): Selected note objects (path, fields, sections, body).
        graph (dict): ``{"related": {path: [related_ids]}}`` if include_related.
        budget (dict): max_chars, used_chars, note_count, truncated.
        warnings (list[str]): Non-fatal issues (missing sections, budget, etc.).
        manifest (dict): source_paths list and schema_version.

    Error codes:
        INVALID_VAULT: Vault name is not registered.
        INVALID_FILTER: Filter key is not a known schema field.
        BUNDLE_FAILED: Unexpected error during bundle generation.

    Note:
        Bundle files are not written to disk in this phase.
        Export / packaging belongs to Phase 4.
    """
    err = _validate_vault(req.vault)
    if err:
        return err

    # Validate filter field names against the vault's known schema fields.
    if req.filters:
        schema = get_schema(req.vault)
        known_fields = schema.ALL_KNOWN_FIELDS
        invalid_filters = [k for k in req.filters if k not in known_fields]
        if invalid_filters:
            return _error(
                "INVALID_FILTER",
                f"Unknown filter field(s): {sorted(invalid_filters)}. "
                f"Known fields: {sorted(known_fields)}",
            )

    # Phase 24: resolve profile/mode and merge as defaults.
    # Only pass fields that the user explicitly set (not model defaults) so that
    # profile defaults can fill in unset fields.
    _profile_mergeable = ("include_sections", "include_related", "include_body",
                          "max_notes", "max_chars", "allow_partial")
    _explicit: dict = {
        f: getattr(req, f)
        for f in _profile_mergeable
        if f in req.model_fields_set
    }

    profile_result = _context_profiles.apply_context_profile_to_request(
        _explicit,
        profile_name=req.profile,
        mode=req.mode,
    )
    if profile_result["error"]:
        err_obj = profile_result["error"]
        return _error(err_obj["code"], err_obj["message"], 400)

    merged_req = profile_result["request"]
    profile_meta = profile_result["profile_metadata"]
    profile_warnings = profile_result["warnings"]

    try:
        result = _generate_bundle(
            vault_name=req.vault,
            filters=req.filters,
            include_sections=merged_req.get("include_sections", req.include_sections),
            include_related=merged_req.get("include_related", req.include_related),
            include_body=merged_req.get("include_body", req.include_body),
            max_notes=merged_req.get("max_notes", req.max_notes),
            max_chars=merged_req.get("max_chars", req.max_chars),
            allow_partial=merged_req.get("allow_partial", req.allow_partial),
        )
        if result.get("status") == "error":
            code = result.get("error", {}).get("code", "BUNDLE_FAILED")
            msg = result.get("error", {}).get("message", "Bundle generation failed")
            return _error(code, msg, 500)

        # Inject profile metadata into response
        result["profile_metadata"] = profile_meta
        result.setdefault("warnings", [])
        result["warnings"] = profile_warnings + result["warnings"]

        # Warn if profile requires_security_scan but no scan was performed
        if profile_meta.get("require_security_scan"):
            result["warnings"].append(
                "Profile requires security scan. Run POST /context/security "
                "to verify content before use."
            )
        # Inject profile metadata into manifest
        if "manifest" in result and isinstance(result["manifest"], dict):
            result["manifest"]["profile_metadata"] = profile_meta

        # Phase 25: annotate bundle notes with trust metadata
        if "notes" in result and isinstance(result["notes"], list):
            result["notes"] = _trust_metadata.annotate_notes_with_trust(result["notes"])

        return result
    except Exception as exc:
        return _error("BUNDLE_FAILED", f"Bundle generation failed: {exc}", 500)


# ---------- Phase 24: Context Profiles ----------


@app.get("/context/profiles")
def endpoint_context_profiles():
    """List all available context profiles and bundle modes.

    Read-only. Works in private-cloud read-only mode with valid auth.

    Response data:
        profiles (dict): Named device profiles (phone-local-llm, desktop-agent, etc.).
        modes (dict): Named bundle modes (tiny, small, medium, large, agent).
        defaults (dict): Default mode/profile selection.

    Error codes:
        PROFILES_FAILED: Unexpected error.
    """
    try:
        data = _context_profiles.list_context_profiles()
        return {"status": "ok", "data": data}
    except Exception as exc:
        return _error("PROFILES_FAILED", f"Failed to list profiles: {exc}", 500)


@app.get("/context/profiles/{profile_name}")
def endpoint_context_profile_by_name(profile_name: str):
    """Return a single context profile or mode by name.

    Read-only. Works in private-cloud read-only mode with valid auth.
    Checks device profiles first, then bundle modes.

    Path parameter:
        profile_name (str): Device profile or mode name (e.g. 'phone-local-llm', 'tiny').

    Response data:
        profile (dict): Full profile definition.
        source (str): ``"builtin"`` for all built-in profiles.

    Error codes:
        INVALID_PROFILE: Profile name is not known (HTTP 404).
    """
    try:
        result = _context_profiles.get_context_profile(profile_name)
        if result.get("status") == "error":
            return _error(
                result["error"]["code"],
                result["error"]["message"],
                404,
            )
        return {"status": "ok", "data": {"profile": result["profile"], "source": result["source"]}}
    except Exception as exc:
        return _error("PROFILES_FAILED", f"Failed to get profile: {exc}", 500)


# ---------- Phase 25: Trust, Staleness, and Evidence Metadata ----------


@app.get("/trust")
def endpoint_trust(
    vault: str = Query(..., description="Vault name"),
):
    """Return vault-level trust/source/staleness summary.

    Query parameters:
        vault (str, required): Vault name.

    Response data:
        status (str): 'ok' or 'error'.
        vault (str): Vault name.
        counts_by_trust_level (dict): Counts per trust_level value (including 'missing').
        counts_by_source_type (dict): Counts per source_type value (including 'missing').
        confidence_distribution (dict): Counts per confidence level.
        missing_metadata_count (int): Notes with no trust_level or source_type.
        deprecated_count (int): Notes with trust_level=deprecated.
        stale_count (int): Notes where review_after is before today.
        freshness_unknown_count (int): Notes missing review_after.
        review_unknown_count (int): Notes missing last_reviewed.
        notes (list): All notes with their trust_metadata, sorted by path.

    Error codes:
        INVALID_VAULT: Vault not registered (HTTP 404).

    Private-cloud: allowed in read-only mode with valid auth.
    """
    err = _validate_vault(vault)
    if err:
        return err
    try:
        result = _trust_metadata.list_trust_summary(vault)
        if result.get("status") == "error":
            code = result["error"]["code"]
            msg = result["error"]["message"]
            return _error(code, msg, 404 if code == "INVALID_VAULT" else 500)
        return result
    except Exception as exc:
        return _error("TRUST_SUMMARY_FAILED", f"Trust summary failed: {exc}", 500)


@app.get("/stale")
def endpoint_stale(
    vault: str = Query(..., description="Vault name"),
):
    """Return stale/review information for a vault.

    Query parameters:
        vault (str, required): Vault name.

    Response data:
        status (str): 'ok' or 'error'.
        vault (str): Vault name.
        today (str): ISO date used for staleness calculation (UTC).
        stale_notes (list): Notes where review_after is before today.
        freshness_unknown (list): Notes with no review_after set.
        review_unknown (list): Notes with no last_reviewed set.
        deprecated_notes (list): Notes with trust_level=deprecated.

    Error codes:
        INVALID_VAULT: Vault not registered (HTTP 404).

    Private-cloud: allowed in read-only mode with valid auth.
    """
    err = _validate_vault(vault)
    if err:
        return err
    try:
        result = _trust_metadata.list_stale_notes(vault)
        if result.get("status") == "error":
            code = result["error"]["code"]
            msg = result["error"]["message"]
            return _error(code, msg, 404 if code == "INVALID_VAULT" else 500)
        return result
    except Exception as exc:
        return _error("STALE_NOTES_FAILED", f"Stale notes failed: {exc}", 500)


class EvidenceRequest(BaseModel):
    """Request body for POST /evidence."""

    vault: str = Field(..., description="Vault name")
    filters: dict = Field(
        default_factory=dict,
        description="Equality filters on frontmatter fields",
    )
    q: str | None = Field(
        default=None,
        description="Free-text lexical search string (max 1000 chars)",
    )
    profile: str | None = Field(
        default=None,
        description="Named context profile (informational; used in evidence_id)",
    )
    mode: str | None = Field(
        default=None,
        description="Named bundle mode (informational; used in evidence_id)",
    )
    include_sections: list[str] | None = Field(
        default=None,
        description="Section names to include as evidence extracts",
    )
    max_notes: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum notes to include (1–100)",
    )
    prefer_verified: bool = Field(
        default=True,
        description="Sort by trust score (verified notes first) when True",
    )
    include_deprecated: bool = Field(
        default=False,
        description="Include deprecated notes in results (excluded by default)",
    )
    include_stale: bool = Field(
        default=True,
        description="Include stale notes in results",
    )


@app.post("/evidence")
def endpoint_evidence(req: EvidenceRequest):
    """Build a structured evidence response with trust metadata and source refs.

    Evidence mode returns source note paths, sections, confidence metadata,
    and trust/staleness status so that local LLMs can cite sources and
    prefer higher-trust notes.

    IMPORTANT: trust metadata is user/system-provided metadata.
    It does NOT indicate factual correctness.

    Request body:
        vault (str): Vault name.
        filters (dict): Equality filters on frontmatter fields.
        q (str|None): Free-text lexical search.
        profile (str|None): Profile name (informational).
        mode (str|None): Bundle mode (informational).
        include_sections (list|None): Section names to extract.
        max_notes (int): Max notes to return (1-100, default 20).
        prefer_verified (bool): Sort by trust score (default True).
        include_deprecated (bool): Include deprecated notes (default False).
        include_stale (bool): Include stale notes (default True).

    Response data:
        evidence_id (str): Deterministic 16-char hex ID.
        vault (str): Vault name.
        query_params (dict): Echoed effective request parameters.
        notes (list): Evidence notes sorted by trust score then path.
        warnings (list): Non-fatal notices.
        summary (dict): Counts by confidence level.

    Each note includes:
        path, fields, trust_metadata, confidence, stale, sections, evidence_refs

    error_refs contain path + section for each extracted section.

    Error codes:
        INVALID_VAULT: Vault not registered (HTTP 404).
        INVALID_FILTER: Unknown filter field (HTTP 400).
        INVALID_QUERY: q is too long (HTTP 400).
        INVALID_EVIDENCE_REQUEST: Invalid request parameter (HTTP 400).

    Private-cloud: allowed in read-only mode with valid auth.
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = _trust_metadata.build_evidence(
            vault_name=req.vault,
            filters=req.filters,
            q=req.q,
            profile=req.profile,
            mode=req.mode,
            include_sections=req.include_sections,
            max_notes=req.max_notes,
            prefer_verified=req.prefer_verified,
            include_deprecated=req.include_deprecated,
            include_stale=req.include_stale,
        )
        if result.get("status") == "error":
            code = result["error"]["code"]
            msg = result["error"]["message"]
            if code == "INVALID_VAULT":
                return _error(code, msg, 404)
            if code in ("INVALID_FILTER", "INVALID_QUERY", "INVALID_EVIDENCE_REQUEST"):
                return _error(code, msg, 400)
            return _error(code, msg, 500)
        return result
    except Exception as exc:
        return _error("EVIDENCE_BUILD_FAILED", f"Evidence build failed: {exc}", 500)


# ---------- Phase 3: Feedback ----------


@app.get("/feedback")
def endpoint_feedback(
    vault: str = Query(None, description="Vault name (defaults to first registered vault)"),
):
    """Return feedback entries from the vault's feedback file.

    Feedback is stored in ``<vault>/Vault Files/feedback.md``.
    The file is optional; a missing file returns ok with empty entries.

    Response data:
        status (str): ``"ok"`` if no errors, ``"error"`` if feedback is malformed.
        vault (str): Resolved vault name.
        entries (list): Validated feedback entries.
        warnings (list[str]): Non-fatal issues (e.g. feedback for a missing note).
        errors (list): Structured validation errors (empty on ok).

    Each feedback entry:
        path (str): Vault-relative POSIX path to the referenced note.
        source (str): One of ``"human"``, ``"agent"``, ``"system"``.
        signal (str): One of the supported signal values.
        severity (str): One of ``"low"``, ``"medium"``, ``"high"``, ``"critical"``.
        comment (str): Human-readable comment (may be empty).
        created_at (str): ISO-8601 timestamp string (may be empty).

    Error codes:
        INVALID_VAULT: Vault is not registered.
        FEEDBACK_ERROR: Feedback file is malformed (structured errors included in response).
    """
    if vault is not None:
        err = _validate_vault(vault)
        if err:
            return err

    try:
        if vault is None:
            vaults = list_vaults()
            if not vaults:
                return _error("NO_VAULTS", "No vaults registered", 500)
            vault = vaults[0]

        vault_path = get_vault_path(vault)
        result = _load_feedback(vault_path)

        return {
            "status": "ok",
            "data": {
                "status": result["status"],
                "vault": vault,
                "entries": result["entries"],
                "warnings": result["warnings"],
                "errors": result["errors"],
            },
        }
    except Exception as exc:
        return _error("FEEDBACK_ERROR", f"Feedback retrieval failed: {exc}", 500)


@app.post("/feedback/normalise")
def endpoint_feedback_normalise(
    vault: str = Query(..., description="Vault name"),
):
    """Normalise the vault feedback file by assigning IDs to id-less entries.

    Reads the existing feedback file, generates stable hex IDs for any entry
    that lacks one, and rewrites the file atomically.  Entries that already
    carry valid IDs are preserved unchanged.

    Response data:
        normalised (int): Count of entries that were assigned a new id.
        feedback (dict): Updated ``load_feedback`` result.

    Error codes:
        INVALID_VAULT:         Vault is not registered.
        FEEDBACK_WRITE_FAILED: File write error.
        FEEDBACK_ERROR:        Unexpected error.
    """
    err = _validate_vault(vault)
    if err:
        return err

    vault_path = get_vault_path(vault)
    try:
        result = _normalise_feedback(vault_path)
        return {
            "status": "ok",
            "data": {
                "normalised": result["normalised"],
                "feedback": result["feedback"],
            },
        }
    except OSError as exc:
        return _error("FEEDBACK_WRITE_FAILED", f"Failed to write feedback file: {exc}", 500)
    except Exception as exc:
        return _error("FEEDBACK_ERROR", f"Feedback normalisation failed: {exc}", 500)


@app.post("/feedback")
def endpoint_feedback_create(req: FeedbackCreateRequest):
    """Add a new feedback entry to the vault's feedback file.

    Validates all fields, generates a server-side id and created_at timestamp,
    appends the entry, and rewrites the file atomically.

    Request body:
        vault (str, required): Vault name.
        path (str, required): Vault-relative note path (POSIX forward slashes).
        source (str, required): ``"human"``, ``"agent"``, or ``"system"``.
        signal (str, required): One of the supported signal values.
        severity (str, required): ``"low"``, ``"medium"``, ``"high"``, or ``"critical"``.
        comment (str, required): Human-readable comment (max 2000 chars).

    Response data:
        entry (dict): The newly created entry (includes id and created_at).
        feedback (dict): Updated ``load_feedback`` result.

    Error codes:
        INVALID_VAULT:         Vault is not registered (HTTP 404).
        INVALID_INPUT:         One or more fields are invalid (HTTP 400).
        PATH_TRAVERSAL:        path escapes vault root (HTTP 400).
        NOTE_NOT_FOUND:        Note does not exist in vault (HTTP 404).
        FEEDBACK_WRITE_FAILED: File write error (HTTP 500).
        FEEDBACK_ERROR:        Unexpected error (HTTP 500).
    """
    err = _validate_vault(req.vault)
    if err:
        return err

    vault_path = get_vault_path(req.vault)
    validation_errors = _validate_feedback_write(
        vault_path, req.path, req.source, req.signal, req.severity, req.comment,
    )
    if validation_errors:
        first = validation_errors[0]
        code = first["code"]
        messages = "; ".join(e["message"] for e in validation_errors)
        status_code = 404 if code == "NOTE_NOT_FOUND" else 400
        return _error(code, messages, status_code)

    try:
        result = _add_feedback_entry(
            vault_path, req.path, req.source, req.signal, req.severity, req.comment,
        )
        return {"status": "ok", "data": {"entry": result["entry"], "feedback": result["feedback"]}}
    except OSError as exc:
        return _error("FEEDBACK_WRITE_FAILED", f"Failed to write feedback file: {exc}", 500)
    except Exception as exc:
        return _error("FEEDBACK_ERROR", f"Feedback operation failed: {exc}", 500)


@app.put("/feedback/{feedback_id}")
def endpoint_feedback_update(feedback_id: str, req: FeedbackUpdateRequest):
    """Update an existing feedback entry by id.

    Locates the entry by feedback_id, applies the new field values, preserves
    the original ``created_at``, and rewrites the file atomically.

    Path parameter:
        feedback_id (str): 12–16 lowercase hex characters.

    Request body:
        vault (str, required): Vault name.
        path (str, required): Vault-relative note path.
        source (str, required): ``"human"``, ``"agent"``, or ``"system"``.
        signal (str, required): One of the supported signal values.
        severity (str, required): ``"low"``, ``"medium"``, ``"high"``, or ``"critical"``.
        comment (str, required): Human-readable comment (max 2000 chars).

    Response data:
        entry (dict): The updated entry.
        feedback (dict): Updated ``load_feedback`` result.

    Error codes:
        INVALID_INPUT:         feedback_id format invalid, or field validation failed (HTTP 400).
        INVALID_VAULT:         Vault is not registered (HTTP 404).
        PATH_TRAVERSAL:        path escapes vault root (HTTP 400).
        NOTE_NOT_FOUND:        Note does not exist in vault (HTTP 404).
        FEEDBACK_NOT_FOUND:    feedback_id not found in the file (HTTP 404).
        FEEDBACK_WRITE_FAILED: File write error (HTTP 500).
        FEEDBACK_ERROR:        Unexpected error (HTTP 500).
    """
    if not _is_valid_feedback_id(feedback_id):
        return _error(
            "INVALID_INPUT",
            "feedback_id must be 12–16 lowercase hex characters",
            400,
        )

    err = _validate_vault(req.vault)
    if err:
        return err

    vault_path = get_vault_path(req.vault)
    validation_errors = _validate_feedback_write(
        vault_path, req.path, req.source, req.signal, req.severity, req.comment,
    )
    if validation_errors:
        first = validation_errors[0]
        code = first["code"]
        messages = "; ".join(e["message"] for e in validation_errors)
        status_code = 404 if code == "NOTE_NOT_FOUND" else 400
        return _error(code, messages, status_code)

    try:
        result = _update_feedback_entry(
            vault_path,
            feedback_id,
            req.path,
            req.source,
            req.signal,
            req.severity,
            req.comment,
        )
        return {"status": "ok", "data": {"entry": result["entry"], "feedback": result["feedback"]}}
    except KeyError as exc:
        return _error("FEEDBACK_NOT_FOUND", str(exc), 404)
    except OSError as exc:
        return _error("FEEDBACK_WRITE_FAILED", f"Failed to write feedback file: {exc}", 500)
    except Exception as exc:
        return _error("FEEDBACK_ERROR", f"Feedback operation failed: {exc}", 500)


@app.delete("/feedback/{feedback_id}")
def endpoint_feedback_delete(
    feedback_id: str,
    vault: str = Query(..., description="Vault name"),
):
    """Delete a feedback entry by id.

    Removes the entry with the given feedback_id and rewrites the file atomically.

    Path parameter:
        feedback_id (str): 12–16 lowercase hex characters.

    Query parameter:
        vault (str, required): Vault name.

    Response data:
        deleted (str): The deleted feedback_id.
        feedback (dict): Updated ``load_feedback`` result.

    Error codes:
        INVALID_INPUT:         feedback_id format invalid (HTTP 400).
        INVALID_VAULT:         Vault is not registered (HTTP 404).
        FEEDBACK_NOT_FOUND:    feedback_id not found in the file (HTTP 404).
        FEEDBACK_WRITE_FAILED: File write error (HTTP 500).
        FEEDBACK_ERROR:        Unexpected error (HTTP 500).
    """
    if not _is_valid_feedback_id(feedback_id):
        return _error(
            "INVALID_INPUT",
            "feedback_id must be 12–16 lowercase hex characters",
            400,
        )

    err = _validate_vault(vault)
    if err:
        return err

    vault_path = get_vault_path(vault)
    try:
        result = _delete_feedback_entry(vault_path, feedback_id)
        return {
            "status": "ok",
            "data": {"deleted": feedback_id, "feedback": result["feedback"]},
        }
    except KeyError as exc:
        return _error("FEEDBACK_NOT_FOUND", str(exc), 404)
    except OSError as exc:
        return _error("FEEDBACK_WRITE_FAILED", f"Failed to write feedback file: {exc}", 500)
    except Exception as exc:
        return _error("FEEDBACK_ERROR", f"Feedback operation failed: {exc}", 500)


# ---------- Phase 4: Context Export ----------


@app.post("/context/export")
def endpoint_context_export(req: ExportRequest):
    """Generate a context bundle and write it to disk as a portable package.

    Combines bundle generation (same logic as POST /context/bundle) with
    package export.  The package is written to:
        dist/context-bundles/<bundle_id>/

    Request body:
        vault (str, required): Vault name.
        filters (dict): Equality filters on frontmatter fields.
        include_sections (list[str]): Section names to extract (without '## ').
            Defaults to ['Key Principles', 'How It Works', 'Trade-offs'].
        include_related (bool): Include graph relationship IDs per note.
        include_body (bool): Include full note body text. Default True.
        max_notes (int): Maximum notes (1–100). Default 10.
        max_chars (int): Character budget (100–500000). Default 20000.
        allow_partial (bool): Include status=partial notes. Default False.
        overwrite (bool): Replace existing package. Default False.

    Response:
        status (str): ``"ok"`` on success.
        bundle_id (str): Deterministic 16-char hex bundle ID.
        package_dir (str): Relative path to the written package directory.
        files (dict): Per-file sha256 and byte count for all six package files.
        warnings (list[str]): Non-fatal issues propagated from bundle generation.

    Error codes:
        INVALID_VAULT:    Vault name is not registered.
        INVALID_FILTER:   Filter key is not a known schema field.
        PACKAGE_EXISTS:   Package already exists and overwrite=False (HTTP 409).
        BUNDLE_FAILED:    Unexpected error during bundle generation.
        EXPORT_FAILED:    Unexpected error during package export.

    Package files written:
        context.json          Full bundle JSON
        context.md            Human-readable Markdown rendering
        manifest.json         Manifest with SHA-256 hashes for all other files
        validation.json       Validation status and warnings
        graph.json            Graph relationships
        feedback-summary.json Feedback entries for selected notes
    """
    err = _validate_vault(req.vault)
    if err:
        return err

    # Validate filter field names against the vault's known schema fields.
    if req.filters:
        schema = get_schema(req.vault)
        known_fields = schema.ALL_KNOWN_FIELDS
        invalid_filters = [k for k in req.filters if k not in known_fields]
        if invalid_filters:
            return _error(
                "INVALID_FILTER",
                f"Unknown filter field(s): {sorted(invalid_filters)}. "
                f"Known fields: {sorted(known_fields)}",
            )

    # Phase 24: resolve profile/mode and merge as defaults
    _profile_mergeable_exp = ("include_sections", "include_related", "include_body",
                              "max_notes", "max_chars", "allow_partial")
    _explicit_export: dict = {
        f: getattr(req, f)
        for f in _profile_mergeable_exp
        if f in req.model_fields_set
    }

    profile_result_exp = _context_profiles.apply_context_profile_to_request(
        _explicit_export,
        profile_name=req.profile,
        mode=req.mode,
    )
    if profile_result_exp["error"]:
        err_obj = profile_result_exp["error"]
        return _error(err_obj["code"], err_obj["message"], 400)

    merged_exp = profile_result_exp["request"]
    profile_meta_exp = profile_result_exp["profile_metadata"]

    # If profile requires security scan, enforce require_security_pass
    effective_require_security = req.require_security_pass
    if profile_meta_exp.get("require_security_scan"):
        effective_require_security = True

    try:
        bundle = _generate_bundle(
            vault_name=req.vault,
            filters=req.filters,
            include_sections=merged_exp.get("include_sections", req.include_sections),
            include_related=merged_exp.get("include_related", req.include_related),
            include_body=merged_exp.get("include_body", req.include_body),
            max_notes=merged_exp.get("max_notes", req.max_notes),
            max_chars=merged_exp.get("max_chars", req.max_chars),
            allow_partial=merged_exp.get("allow_partial", req.allow_partial),
        )
        if bundle.get("status") == "error":
            code = bundle.get("error", {}).get("code", "BUNDLE_FAILED")
            msg = bundle.get("error", {}).get("message", "Bundle generation failed")
            return _error(code, msg, 500)

        # Inject profile metadata into bundle manifest
        if "manifest" in bundle and isinstance(bundle["manifest"], dict):
            bundle["manifest"]["profile_metadata"] = profile_meta_exp

        # Security gate (enforced when profile.require_security_scan=true OR
        # caller explicitly set require_security_pass=true)
        if effective_require_security:
            sec_result = _scan_context_bundle(bundle)
            if sec_result.get("status") == "fail":
                finding_count = len(sec_result.get("findings", []))
                return _error(
                    "SECURITY_SCAN_FAIL",
                    f"Security scan failed with {finding_count} finding(s); "
                    "export blocked (require_security_pass=true or profile.require_security_scan=true)",
                    400,
                )

        result = _export_package(bundle, overwrite=req.overwrite)
        if result["status"] == "error":
            code = result["error"]["code"]
            msg = result["error"]["message"]
            status_code = 409 if code == "PACKAGE_EXISTS" else 500
            return _error(code, msg, status_code)

        # Inject profile metadata into export result
        result["profile_metadata"] = profile_meta_exp
        result.setdefault("warnings", [])
        result["warnings"] = profile_result_exp["warnings"] + result["warnings"]

        # Phase 25: inject trust/staleness summary into export manifest
        try:
            trust_summary = _trust_metadata.evidence_status_summary(req.vault)
            if trust_summary.get("status") == "ok":
                result["trust_summary"] = trust_summary
                if "manifest" in result and isinstance(result["manifest"], dict):
                    result["manifest"]["trust_summary"] = {
                        "deprecated_count": trust_summary.get("deprecated_count", 0),
                        "stale_count": trust_summary.get("stale_count", 0),
                        "missing_metadata_count": trust_summary.get("missing_metadata_count", 0),
                        "confidence_distribution": trust_summary.get("confidence_distribution", {}),
                    }
        except Exception:
            pass  # Non-blocking: trust summary failure should not block export

        return result

    except Exception as exc:
        return _error("EXPORT_FAILED", f"Export failed: {exc}", 500)


# ---------- Run ----------


# ---------- Phase 5: Context Security Scanning ----------


@app.post("/context/security")
def endpoint_context_security(req: SecurityRequest):
    """Scan selected vault notes for security issues.

    Runs deterministic, local, rule-based checks against note body text and
    section content.  No LLM.  No network calls.  All rules are regex-based.

    By default this is a vault-level scan: all content notes are included
    (``allow_partial=True``, high ``max_notes``/``max_chars`` limits, no
    status filter).  Generated/system files under ``Vault Files/`` are always
    excluded by the vault index.

    To run a bundle-style filtered scan, pass explicit ``filters``,
    ``allow_partial=False``, or reduced ``max_notes``/``max_chars``.

    Request body:
        vault (str, required): Vault name.
        filters (dict): Equality filters on frontmatter fields.
        include_sections (list[str]): Section names to scan.
            Defaults to [\'Key Principles\', \'How It Works\', \'Trade-offs\'].
        include_body (bool): Include full note body text in scan. Default True.
        max_notes (int): Maximum notes (1–1000). Default 200.
        max_chars (int): Character budget (100–50000000). Default 10000000.
        allow_partial (bool): Include status=partial notes. Default True.

    Response data:
        status (str): ``"pass"``, ``"warning"``, or ``"fail"``.
        findings (list): Per-finding objects with path, severity, rule, field, detail.
        summary (dict): Counts by severity group: fail, warning, info.
        scanned (dict): note_count, source_paths, total_notes, coverage, truncated.

    Status levels:
        pass     No findings.
        warning  Findings exist but none meet the fail threshold.
        fail     One or more findings with severity high/critical for a blocking rule
                 (private-key, api-key-*, bearer-token, password-pattern).

    Error codes:
        INVALID_VAULT:          Vault name is not registered.
        INVALID_FILTER:         Filter key is not a known schema field.
        SECURITY_SCAN_FAILED:   Unexpected error during scan.
    """
    err = _validate_vault(req.vault)
    if err:
        return err

    # Validate filter field names against vault schema
    if req.filters:
        schema = get_schema(req.vault)
        known_fields = schema.ALL_KNOWN_FIELDS
        invalid_filters = [k for k in req.filters if k not in known_fields]
        if invalid_filters:
            return _error(
                "INVALID_FILTER",
                f"Unknown filter field(s): {sorted(invalid_filters)}. "
                f"Known fields: {sorted(known_fields)}",
            )

    # Phase 24: resolve profile/mode and merge as defaults
    _profile_mergeable_sec = ("include_sections", "include_body", "max_notes", "max_chars", "allow_partial")
    _explicit_sec: dict = {
        f: getattr(req, f)
        for f in _profile_mergeable_sec
        if f in req.model_fields_set
    }

    profile_result_sec = _context_profiles.apply_context_profile_to_request(
        _explicit_sec,
        profile_name=req.profile,
        mode=req.mode,
    )
    if profile_result_sec["error"]:
        err_obj = profile_result_sec["error"]
        return _error(err_obj["code"], err_obj["message"], 400)

    merged_sec = profile_result_sec["request"]
    profile_meta_sec = profile_result_sec["profile_metadata"]

    try:
        result = _scan_vault_context(
            vault_name=req.vault,
            filters=req.filters,
            include_sections=merged_sec.get("include_sections", req.include_sections),
            include_body=merged_sec.get("include_body", req.include_body),
            max_notes=merged_sec.get("max_notes", req.max_notes),
            max_chars=merged_sec.get("max_chars", req.max_chars),
            allow_partial=merged_sec.get("allow_partial", req.allow_partial),
        )
        if result.get("status") == "error":
            code = result.get("error", {}).get("code", "SECURITY_SCAN_FAILED")
            msg = result.get("error", {}).get("message", "Security scan failed")
            return _error(code, msg, 500)

        response_data = dict(result)
        response_data["profile_metadata"] = profile_meta_sec
        response_data.setdefault("warnings", [])
        response_data["warnings"] = profile_result_sec["warnings"] + response_data["warnings"]

        return {"status": "ok", "data": response_data}
    except Exception as exc:
        return _error("SECURITY_SCAN_FAILED", f"Security scan failed: {exc}", 500)


# ---------- Phase 11A: Vault Bootstrap ----------

# Module-level override for the bootstrap repository root.
# Set to a Path in tests to redirect vault creation to a temp directory
# without restarting the server process.
_BOOTSTRAP_REPO_ROOT: Path | None = None


def _get_bootstrap_repo_root() -> Path:
    """Return the effective repository root used by POST /vault/bootstrap."""
    return _BOOTSTRAP_REPO_ROOT if _BOOTSTRAP_REPO_ROOT is not None else Path(_project_root)


@app.post("/vault/bootstrap")
def endpoint_vault_bootstrap(req: VaultBootstrapRequest):
    """Create a new vault from a structured request.

    Validates all inputs strictly before writing any files.  On success,
    creates the vault directory, writes vault_schema.py, updates
    config/config.yaml atomically, and generates canonical templates.
    The in-process vault registry is refreshed after a successful bootstrap.

    Request body:
        vault_name (str, required): New vault directory name.
            Must match ^[A-Za-z0-9_-]+$. Must not already exist.
        domain (str, required): Primary domain display name (e.g. 'Dogs').
        note_type (str, required): Note type slug (e.g. 'breed-profile').
            Must match ^[a-z0-9]+(?:-[a-z0-9]+)*$.
        sections (list[str], required): Canonical section names (min 2,
            no duplicates).
        expected_concepts (list[str]): Optional expected concept names.
            Each entry is normalised to a lowercase slug and written into
            EXPECTED_CONCEPTS in the generated vault_schema.py.
            GET /missing works immediately for the new vault.

    Response data on success:
        vault (str): Created vault name.
        created (list[str]): Relative paths of files written.
        warnings (list[str]): Non-fatal notices (e.g. registry refresh advisory).
        expected_concepts (dict): ``{"requested": N, "written": N}``.

    Error codes:
        INVALID_INPUT:       Request body fails Pydantic validation.
        VALIDATION_ERROR:    One or more fields fail domain validation.
        VAULT_EXISTS:        A vault with vault_name already exists.
        PATH_TRAVERSAL:      vault_name resolves outside the repository root.
        BOOTSTRAP_FAILED:    Vault creation or template generation error.
        CONFIG_UPDATE_FAILED: Config write failed after vault was created
                              (vault rolled back where possible).
    """
    repo_root = _get_bootstrap_repo_root()

    from core.shared.bootstrap_service import (
        validate_bootstrap_request,
        bootstrap_vault_noninteractive,
    )

    # Pre-validate to return structured errors with specific codes
    validation_errors = validate_bootstrap_request(
        repo_root,
        req.vault_name,
        req.domain,
        req.note_type,
        req.sections,
        req.expected_concepts if req.expected_concepts else None,
    )

    if validation_errors:
        # Map first error to a specific error code for caller convenience
        first = validation_errors[0].lower()
        if "already exists" in first:
            code = "VAULT_EXISTS"
            status_code = 409
        elif "path traversal" in first or "outside repository" in first:
            code = "PATH_TRAVERSAL"
            status_code = 400
        else:
            code = "INVALID_INPUT"
            status_code = 422
        return _error(
            code,
            "; ".join(validation_errors),
            status_code,
        )

    try:
        result = bootstrap_vault_noninteractive(
            repo_root=repo_root,
            vault_name=req.vault_name,
            domain=req.domain,
            note_type=req.note_type,
            sections=req.sections,
            expected_concepts=req.expected_concepts if req.expected_concepts else None,
        )
    except FileExistsError as exc:
        return _error("VAULT_EXISTS", str(exc), 409)
    except ValueError as exc:
        return _error("INVALID_INPUT", str(exc), 422)
    except RuntimeError as exc:
        msg = str(exc)
        if "config update failed" in msg.lower():
            return _error("CONFIG_UPDATE_FAILED", msg, 500)
        return _error("BOOTSTRAP_FAILED", msg, 500)
    except Exception as exc:
        logger.exception("vault_bootstrap_unhandled vault=%s", req.vault_name)
        return _error("BOOTSTRAP_FAILED", f"Unexpected bootstrap error: {exc}", 500)

    # Refresh in-process vault registry so the new vault is immediately
    # queryable without a server restart.
    try:
        reload_config()
        logger.info(
            "vault_registry_refreshed after_bootstrap vault=%s", req.vault_name
        )
        # Remove the generic registry-refresh warning since we did it in-process
        result["warnings"] = [
            w for w in result["warnings"]
            if "registry cache may be stale" not in w
        ]
    except Exception as exc:
        logger.warning(
            "vault_registry_refresh_failed vault=%s error=%s", req.vault_name, exc
        )
        # Warning is already in result["warnings"] from the service; leave it

    return {
        "status": "ok",
        "data": {
            "vault": result["vault"],
            "created": result["created"],
            "warnings": result["warnings"],
            "expected_concepts": result.get("expected_concepts", {"requested": 0, "written": 0}),
        },
    }


# ---------- Phase 18C: Safe Vault Deletion ----------


class VaultDeleteRequest(BaseModel):
    """Request body for DELETE /vault/{name}."""

    confirm: str = Field(
        ...,
        description=(
            "Confirmation phrase. Must be exactly: 'DELETE <vault-name>'. "
            "This prevents accidental deletion by vague or boolean confirmation."
        ),
    )


@app.delete("/vault/{vault_name}")
def endpoint_vault_delete(vault_name: str, req: VaultDeleteRequest):
    """Permanently delete a non-demo vault.

    Validates all safety rules, removes the vault directory, and updates
    config/config.yaml atomically.  The in-process vault registry and all
    caches for the deleted vault are refreshed immediately so no restart is
    required.

    Path parameter:
        vault_name (str): Name of the vault to delete (not a path).

    Request body:
        confirm (str, required): Must be exactly ``DELETE <vault-name>``.
            Boolean or vague confirmations are rejected to prevent accidental
            deletion by an automated tool calling this endpoint.

    Response data on success:
        deleted (str): Name of the deleted vault.
        remaining_vaults (list[str]): Vaults still registered after deletion.
        active_vault (str): Recommended fallback vault (prefer demo-vault).

    Error codes:
        INVALID_VAULT:        Vault name is not registered (HTTP 404).
        PROTECTED_VAULT:      Attempt to delete demo-vault (HTTP 403).
        LAST_VAULT:           Attempt to delete the last remaining vault (HTTP 400).
        CONFIRMATION_REQUIRED: confirm field is missing or blank (HTTP 400).
        CONFIRMATION_MISMATCH: confirm does not match "DELETE <vault-name>" (HTTP 400).
        PATH_TRAVERSAL:       Registered vault path is outside repo root (HTTP 400).
        DELETE_FAILED:        Directory removal failed (HTTP 500).
        CONFIG_UPDATE_FAILED: Config rewrite failed after directory was removed (HTTP 500).

    Safety:
        - Only named vaults in the registry can be deleted.
        - demo-vault is unconditionally protected.
        - The last vault cannot be deleted.
        - The vault path is resolved from the registry only (never from user input).
        - The resolved path must reside inside the repository root.
        - Deletion via GET is not possible.
    """
    from mcp.core.vault_delete import delete_vault, VaultDeleteError

    repo_root = _get_bootstrap_repo_root()

    try:
        result = delete_vault(vault_name, req.confirm, repo_root)
    except VaultDeleteError as exc:
        http_status_map = {
            "INVALID_VAULT": 404,
            "PROTECTED_VAULT": 403,
            "LAST_VAULT": 400,
            "CONFIRMATION_REQUIRED": 400,
            "CONFIRMATION_MISMATCH": 400,
            "PATH_TRAVERSAL": 400,
            "DELETE_FAILED": 500,
            "CONFIG_UPDATE_FAILED": 500,
        }
        status_code = http_status_map.get(exc.code, 400)
        return _error(exc.code, exc.message, status_code)
    except Exception as exc:
        logger.exception("vault_delete_unhandled vault=%s", vault_name)
        return _error("INTERNAL", f"Unexpected error during vault deletion: {exc}", 500)

    # Refresh in-process vault registry
    try:
        reload_config()
        logger.info("vault_registry_refreshed after_delete vault=%s", vault_name)
    except Exception as exc:
        logger.warning(
            "vault_registry_refresh_failed vault=%s error=%s", vault_name, exc
        )

    # Evict stale caches for the deleted vault
    try:
        clear_vault_index(vault_name)
        clear_vault_cache(vault_name)
        logger.info("vault_caches_cleared vault=%s", vault_name)
    except Exception as exc:
        logger.warning(
            "vault_cache_clear_failed vault=%s error=%s", vault_name, exc
        )

    return {
        "status": "ok",
        "data": {
            "deleted": result["deleted"],
            "remaining_vaults": result["remaining_vaults"],
            "active_vault": result["active_vault"],
        },
    }


# ---------- Phase 19: Context Controller ----------


class ContextPlanRequest(BaseModel):
    """Request body for POST /context/plan."""

    vault: str = Field(..., description="Vault name to plan for.")
    intent: str = Field(
        "review",
        description=(
            "Planning intent. One of: review, export, agent-context, quality, security."
        ),
    )


@app.get("/context/state")
def endpoint_context_state(vault: str = Query(...)):
    """Return a deterministic state snapshot for the given vault.

    The controller is deterministic. It does not call an LLM or make semantic
    judgements.  All output is derived from existing adapters and services.

    Query parameters:
        vault (str, required): Name of the registered vault.

    Response data on success:
        vault (str): Vault name.
        state (dict): Per-service summaries (validation, security, tasks,
            missing, feedback, graph).
        readiness (dict): Boolean flags indicating vault readiness.
        blockers (list[str]): Issues that prevent export or agent use.
        warnings (list[str]): Non-blocking issues to address.

    Error codes:
        INVALID_VAULT:     Vault is not registered (HTTP 404).
        CONTROLLER_FAILED: Unexpected error in the controller (HTTP 500).
    """
    err = _validate_vault(vault)
    if err:
        return err
    try:
        result = get_context_state(vault)
        if result.get("status") == "error":
            code = result["error"]["code"]
            msg = result["error"]["message"]
            http_code = 404 if code == "INVALID_VAULT" else 500
            return _error(code, msg, http_code)
        return {"status": "ok", "data": result}
    except Exception as exc:
        logger.exception("context_state_failed vault=%s", vault)
        return _error("CONTROLLER_FAILED", str(exc), 500)


@app.post("/context/plan")
def endpoint_context_plan(req: ContextPlanRequest):
    """Build a deterministic intent-scoped recommendation plan.

    The controller is deterministic. It does not call an LLM or make semantic
    judgements.  Recommendations are derived from validation, security, tasks,
    missing-concepts, and feedback state.

    Request body:
        vault (str, required): Name of the registered vault.
        intent (str, optional): Planning intent — one of: review, export,
            agent-context, quality, security.  Defaults to ``review``.

    Response data on success:
        vault (str): Vault name.
        intent (str): Intent used.
        readiness (dict): Boolean readiness flags.
        recommendations (list[dict]): Ranked list of actions.
        blockers (list[str]): Blocking issues.
        warnings (list[str]): Non-blocking issues.
        next_best_action (dict | None): Highest-ranked recommendation summary.

    Error codes:
        INVALID_VAULT:   Vault is not registered (HTTP 404).
        INVALID_INTENT:  Intent is not a recognised value (HTTP 400).
        CONTROLLER_FAILED: Unexpected error (HTTP 500).
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = build_context_plan(req.vault, req.intent)
        if result.get("status") == "error":
            code = result["error"]["code"]
            msg = result["error"]["message"]
            if code == "INVALID_VAULT":
                return _error(code, msg, 404)
            if code == "INVALID_INTENT":
                return _error(code, msg, 400)
            return _error(code, msg, 500)
        return {"status": "ok", "data": result}
    except Exception as exc:
        logger.exception("context_plan_failed vault=%s intent=%s", req.vault, req.intent)
        return _error("CONTROLLER_FAILED", str(exc), 500)


# ---------- Phase 10: Static UI Serving ----------


@app.get("/app", include_in_schema=False)
@app.get("/app/{ui_path:path}", include_in_schema=False)
def endpoint_app(ui_path: str = ""):
    """Serve the compiled Astro frontend from ui/dist.

    Requires a prior production build:
        cd ui
        npm install
        npm run build

    Returns HTTP 503 with instructions when ui/dist does not exist.
    Path traversal attempts outside ui/dist are rejected with HTTP 400.
    """
    if not _UI_DIST.is_dir():
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": {
                    "code": "UI_NOT_BUILT",
                    "message": (
                        "Frontend not built. "
                        "Run: cd ui && npm install && npm run build"
                    ),
                },
            },
        )

    # Resolve the requested file path, defaulting to index.html
    clean = ui_path.strip("/") if ui_path else ""
    if clean:
        candidate = _UI_DIST / clean
    else:
        candidate = _UI_DIST / "index.html"

    # Path traversal protection: resolved path must stay inside _UI_DIST
    try:
        candidate.resolve().relative_to(_UI_DIST.resolve())
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": {"code": "PATH_TRAVERSAL", "message": "Access denied"},
            },
        )

    # Astro static build emits each page as <route>/index.html.
    # When the candidate is a directory (e.g. ui/dist/notes/), serve its index.html.
    if candidate.is_dir():
        candidate = candidate / "index.html"

    # SPA fallback: unknown paths serve index.html
    if not candidate.is_file():
        candidate = _UI_DIST / "index.html"
        if not candidate.is_file():
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "error": {
                        "code": "UI_MISSING_INDEX",
                        "message": "index.html not found in ui/dist. Rebuild the frontend.",
                    },
                },
            )

    content = candidate.read_bytes()
    media_type, _ = mimetypes.guess_type(str(candidate))
    return Response(content=content, media_type=media_type or "application/octet-stream")


# ---------- Phase 23: Safe Memory Write Queue ----------


class CreateNoteDraftRequest(BaseModel):
    """Request body for POST /memory/create-note-draft."""

    vault: str = Field(..., description="Vault name")
    path: str = Field(..., description="Vault-relative POSIX path for the new note")
    fields: dict[str, Any] = Field(..., description="Frontmatter fields for the new note")
    body: str = Field(..., description="Markdown body text (without frontmatter)")
    reason: str = Field(default="", description="Reason for the proposal")
    source: str = Field(default="agent", description="Source of the proposal: agent | human | system")
    session_id: str | None = Field(default=None, description="Optional session ID")
    project: str | None = Field(default=None, description="Optional project name")


class SuggestNoteUpdateRequest(BaseModel):
    """Request body for POST /memory/suggest-note-update."""

    vault: str = Field(..., description="Vault name")
    path: str = Field(..., description="Vault-relative POSIX path of the existing note")
    fields: dict[str, Any] | None = Field(default=None, description="Fields to update (merged with original)")
    body: str | None = Field(default=None, description="New body text (replaces original body if provided)")
    reason: str = Field(default="", description="Reason for the proposal")
    source: str = Field(default="agent", description="Source of the proposal")
    session_id: str | None = Field(default=None, description="Optional session ID")
    project: str | None = Field(default=None, description="Optional project name")


class UpdateSectionDraftRequest(BaseModel):
    """Request body for POST /memory/update-section-draft."""

    vault: str = Field(..., description="Vault name")
    path: str = Field(..., description="Vault-relative POSIX path of the existing note")
    section: str = Field(..., description="Section name without '## ' prefix")
    proposed_content: str = Field(..., description="New content for the section body (without header line)")
    reason: str = Field(default="", description="Reason for the proposal")
    source: str = Field(default="agent", description="Source of the proposal")
    session_id: str | None = Field(default=None, description="Optional session ID")
    project: str | None = Field(default=None, description="Optional project name")


class PendingChangeActionRequest(BaseModel):
    """Request body for POST /memory/pending/{change_id}/accept and /reject."""

    vault: str = Field(..., description="Vault name")
    reviewer: str | None = Field(default=None, description="Reviewer identifier (optional)")
    audit_note: str | None = Field(default=None, description="Audit note (optional)")


@app.get("/memory/pending")
def endpoint_memory_pending_list(
    vault: str = Query(..., description="Vault name"),
    status: str = Query(default="pending", description="Status filter: pending | accepted | rejected | invalid | all"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum results (1–500)"),
):
    """List pending changes for a vault.

    Query parameters:
        vault (str, required): Vault name.
        status (str): Filter by status. Use 'all' to list all statuses. Default: 'pending'.
        limit (int): Maximum results (1–500). Default: 50.

    Response data:
        changes (list): Matching pending change objects.
        count (int): Number returned.
        status_filter (str): Status filter applied.

    Error codes:
        INVALID_VAULT: Vault is not registered (HTTP 404).
    """
    err = _validate_vault(vault)
    if err:
        return err
    status_arg = None if status == "all" else status
    try:
        result = _pending_changes.list_pending_changes(vault, status=status_arg, limit=limit)
        if result.get("status") == "error":
            code = result["error"]["code"]
            return JSONResponse(status_code=400, content=result)
        return result
    except Exception as exc:
        return _error("PENDING_CHANGES_FAILED", f"Failed to list pending changes: {exc}", 500)


@app.post("/memory/create-note-draft")
def endpoint_memory_create_note_draft(req: CreateNoteDraftRequest):
    """Propose creation of a new note (stored as a pending change).

    The proposed note is validated against the vault schema.  Nothing is
    written to the vault until a reviewer explicitly accepts the change
    via POST /memory/pending/{change_id}/accept.

    Request body:
        vault, path, fields, body, reason, source, session_id, project.

    Response data:
        change (dict): The created pending change object.

    Error codes:
        INVALID_VAULT: Vault not registered (HTTP 404).
        NOTE_EXISTS: Target path already exists (HTTP 409).
        INVALID_NOTE_PATH: Path is invalid or inside Vault Files/ (HTTP 400).
        PATH_TRAVERSAL: Path escapes vault root (HTTP 400).
        INVALID_PENDING_CHANGE: Fields/body invalid (HTTP 400).
        WRITE_FAILED: Cannot write pending change file (HTTP 500).
        REMOTE_READ_ONLY: Server is in remote read-only mode (HTTP 403).
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = _pending_changes.create_note_draft(
            req.vault, req.path, req.fields, req.body,
            reason=req.reason, source=req.source,
            session_id=req.session_id, project=req.project,
        )
        if result.get("status") == "error":
            code = result["error"]["code"]
            status_code = 404 if code == "INVALID_VAULT" else (409 if code == "NOTE_EXISTS" else 400)
            return JSONResponse(status_code=status_code, content=result)
        return result
    except Exception as exc:
        return _error("PENDING_CHANGES_FAILED", f"Failed to create note draft: {exc}", 500)


@app.post("/memory/suggest-note-update")
def endpoint_memory_suggest_note_update(req: SuggestNoteUpdateRequest):
    """Propose an update to an existing note (stored as a pending change).

    Fields and body are merged with the original note.  The proposed update
    is validated against the vault schema.  Nothing is written to the vault
    until a reviewer explicitly accepts the change.

    Request body:
        vault, path, fields (optional), body (optional), reason, source,
        session_id, project.

    Response data:
        change (dict): The created pending change object.

    Error codes:
        INVALID_VAULT: Vault not registered (HTTP 404).
        NOTE_NOT_FOUND: Target note does not exist (HTTP 404).
        INVALID_NOTE_PATH: Path is invalid (HTTP 400).
        PATH_TRAVERSAL: Path escapes vault root (HTTP 400).
        REMOTE_READ_ONLY: Server is in remote read-only mode (HTTP 403).
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = _pending_changes.suggest_note_update(
            req.vault, req.path,
            fields=req.fields,
            body=req.body,
            reason=req.reason,
            source=req.source,
            session_id=req.session_id,
            project=req.project,
        )
        if result.get("status") == "error":
            code = result["error"]["code"]
            status_code = 404 if code in ("INVALID_VAULT", "NOTE_NOT_FOUND") else 400
            return JSONResponse(status_code=status_code, content=result)
        return result
    except Exception as exc:
        return _error("PENDING_CHANGES_FAILED", f"Failed to create update proposal: {exc}", 500)


@app.post("/memory/update-section-draft")
def endpoint_memory_update_section_draft(req: UpdateSectionDraftRequest):
    """Propose a targeted section update for an existing note.

    Only the named section is replaced.  All other content is preserved.
    The proposed change is validated before storage.  Nothing is written to
    the vault until accepted.

    Request body:
        vault, path, section, proposed_content, reason, source,
        session_id, project.

    Response data:
        change (dict): The created pending change object.

    Error codes:
        INVALID_VAULT: Vault not registered (HTTP 404).
        NOTE_NOT_FOUND: Target note does not exist (HTTP 404).
        INVALID_PENDING_CHANGE: Section not found or serialisation failed (HTTP 400).
        REMOTE_READ_ONLY: Server is in remote read-only mode (HTTP 403).
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = _pending_changes.update_note_section_draft(
            req.vault, req.path, req.section, req.proposed_content,
            reason=req.reason,
            source=req.source,
            session_id=req.session_id,
            project=req.project,
        )
        if result.get("status") == "error":
            code = result["error"]["code"]
            status_code = 404 if code in ("INVALID_VAULT", "NOTE_NOT_FOUND") else 400
            return JSONResponse(status_code=status_code, content=result)
        return result
    except Exception as exc:
        return _error("PENDING_CHANGES_FAILED", f"Failed to create section draft: {exc}", 500)


@app.get("/memory/pending/{change_id}")
def endpoint_memory_pending_get(
    change_id: str,
    vault: str = Query(..., description="Vault name"),
):
    """Retrieve a single pending change by ID.

    Returns the full change object including diff, validation status,
    and all metadata.  Works for both pending and archived changes.

    Path parameter:
        change_id (str): Change ID (yyyymmddTHHMMSS-<8hex>).

    Query parameter:
        vault (str, required): Vault name.

    Response data:
        change (dict): Full pending change object.

    Error codes:
        INVALID_VAULT: Vault not registered (HTTP 404).
        PENDING_CHANGE_NOT_FOUND: Change not found (HTTP 404).
        INVALID_PENDING_CHANGE: change_id format invalid (HTTP 400).
    """
    err = _validate_vault(vault)
    if err:
        return err
    try:
        result = _pending_changes.review_pending_change(vault, change_id)
        if result.get("status") == "error":
            code = result["error"]["code"]
            status_code = 404 if code in ("PENDING_CHANGE_NOT_FOUND", "INVALID_VAULT") else 400
            return JSONResponse(status_code=status_code, content=result)
        return result
    except Exception as exc:
        return _error("PENDING_CHANGES_FAILED", f"Failed to retrieve pending change: {exc}", 500)


@app.post("/memory/pending/{change_id}/accept")
def endpoint_memory_pending_accept(change_id: str, req: PendingChangeActionRequest):
    """Accept and apply a pending change.

    Revalidates the change against the current vault schema before writing.
    For update proposals, checks that the original note has not changed since
    the proposal was created (stale protection).

    SAFETY: This is the only way a pending change can mutate vault notes.
    No auto-accept.  Requires explicit user/reviewer action.

    Path parameter:
        change_id (str): Change ID.

    Request body:
        vault (str, required): Vault name.
        reviewer (str, optional): Reviewer identifier.
        audit_note (str, optional): Audit note.

    Response data:
        change (dict): Updated change object (status=accepted).

    Error codes:
        INVALID_VAULT: Vault not registered (HTTP 404).
        PENDING_CHANGE_NOT_FOUND: Change not found (HTTP 404).
        INVALID_PENDING_CHANGE: Change is not pending or ID is invalid (HTTP 400).
        VALIDATION_FAILED: Revalidation failed (HTTP 400).
        STALE_PENDING_CHANGE: Note changed since proposal (HTTP 409).
        NOTE_EXISTS: Target already exists for create_note_draft (HTTP 409).
        NOTE_NOT_FOUND: Note no longer exists for update proposals (HTTP 404).
        WRITE_FAILED: Atomic write failed (HTTP 500).
        REMOTE_READ_ONLY: Server is in remote read-only mode (HTTP 403).
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = _pending_changes.accept_pending_change(
            req.vault, change_id,
            reviewer=req.reviewer,
            audit_note=req.audit_note,
        )
        if result.get("status") == "error":
            code = result["error"]["code"]
            if code in ("PENDING_CHANGE_NOT_FOUND", "NOTE_NOT_FOUND", "INVALID_VAULT"):
                status_code = 404
            elif code in ("NOTE_EXISTS", "STALE_PENDING_CHANGE"):
                status_code = 409
            elif code == "WRITE_FAILED":
                status_code = 500
            else:
                status_code = 400
            return JSONResponse(status_code=status_code, content=result)
        return result
    except Exception as exc:
        return _error("PENDING_CHANGES_FAILED", f"Failed to accept pending change: {exc}", 500)


@app.post("/memory/pending/{change_id}/reject")
def endpoint_memory_pending_reject(change_id: str, req: PendingChangeActionRequest):
    """Reject a pending change and archive it for audit.

    Rejected changes are never deleted.  They are retained in the archive
    directory at <vault>/Vault Files/State/pending-changes/archive/.

    Path parameter:
        change_id (str): Change ID.

    Request body:
        vault (str, required): Vault name.
        reviewer (str, optional): Reviewer identifier.
        audit_note (str, optional): Reason for rejection.

    Response data:
        change (dict): Updated change object (status=rejected).

    Error codes:
        INVALID_VAULT: Vault not registered (HTTP 404).
        PENDING_CHANGE_NOT_FOUND: Change not found (HTTP 404).
        INVALID_PENDING_CHANGE: Change is not pending/invalid (HTTP 400).
        WRITE_FAILED: Archive write failed (HTTP 500).
        REMOTE_READ_ONLY: Server is in remote read-only mode (HTTP 403).
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = _pending_changes.reject_pending_change(
            req.vault, change_id,
            reviewer=req.reviewer,
            audit_note=req.audit_note,
        )
        if result.get("status") == "error":
            code = result["error"]["code"]
            if code in ("PENDING_CHANGE_NOT_FOUND", "INVALID_VAULT"):
                status_code = 404
            elif code == "WRITE_FAILED":
                status_code = 500
            else:
                status_code = 400
            return JSONResponse(status_code=status_code, content=result)
        return result
    except Exception as exc:
        return _error("PENDING_CHANGES_FAILED", f"Failed to reject pending change: {exc}", 500)


# ---------- Phase 22: Session and Project State ----------


class SessionStartRequest(BaseModel):
    """Request body for POST /session/start."""

    vault: str = Field(..., description="Vault name")
    current_project: str | None = Field(None, description="Current project name (optional)")
    current_topic: str | None = Field(None, description="Current topic (optional)")
    user_goal: str | None = Field(None, description="User goal for this session (optional, max 1000 chars)")
    active_vault: str | None = Field(None, description="Active vault override (defaults to vault)")


class SessionAttachNoteRequest(BaseModel):
    """Request body for POST /session/attach-note."""

    vault: str = Field(..., description="Vault name")
    session_id: str = Field(..., description="Session ID to attach note to")
    note_path: str = Field(..., description="Vault-relative POSIX path of the note")


class SessionCloseRequest(BaseModel):
    """Request body for POST /session/close."""

    vault: str = Field(..., description="Vault name")
    session_id: str = Field(..., description="Session ID to close")


class ProjectStateUpdateRequest(BaseModel):
    """Request body for PUT /project/state."""

    vault: str = Field(..., description="Vault name")
    updates: dict[str, Any] = Field(
        ...,
        description=(
            "Project state fields to update. "
            "Allowed: current_phase, completed_work, next_actions, blockers, decisions, risks."
        ),
    )


@app.post("/session/start")
def endpoint_session_start(req: SessionStartRequest):
    """Create and persist a new active session for the given vault.

    Request body:
        vault (str, required): Vault name.
        current_project (str, optional): Current project name.
        current_topic (str, optional): Current topic.
        user_goal (str, optional): User goal description (max 1000 chars).
        active_vault (str, optional): Override for the active vault name.

    Response data:
        session (dict): The newly created session record.

    Error codes:
        INVALID_VAULT:  Vault is not registered (HTTP 404).
        WRITE_FAILED:   Failed to write session file (HTTP 500).
        REMOTE_READ_ONLY: Server is in remote read-only mode (HTTP 403).
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = _session_state.start_session(
            req.vault,
            current_project=req.current_project,
            current_topic=req.current_topic,
            user_goal=req.user_goal,
            active_vault=req.active_vault,
        )
        if result.get("status") == "error":
            err_info = result["error"]
            return _error(err_info["code"], err_info["message"], 400)
        return {"status": "ok", "data": {"session": result["session"]}}
    except OSError as exc:
        return _error("WRITE_FAILED", f"Failed to write session: {exc}", 500)
    except Exception as exc:
        return _error("WRITE_FAILED", f"Session start failed: {exc}", 500)


@app.get("/session/resume")
def endpoint_session_resume(
    vault: str = Query(..., description="Vault name"),
    session_id: str | None = Query(None, description="Session ID (omit to get latest active)"),
):
    """Return the most recent active session or a session by explicit ID.

    Query parameters:
        vault (str, required): Vault name.
        session_id (str, optional): Specific session ID. Omit for latest active.

    Response data:
        session (dict): Session record.

    Error codes:
        INVALID_VAULT:    Vault is not registered (HTTP 404).
        INVALID_SESSION:  Session ID format is invalid (HTTP 400).
        SESSION_NOT_FOUND: No matching session found (HTTP 404).
    """
    err = _validate_vault(vault)
    if err:
        return err
    try:
        result = _session_state.resume_session(vault, session_id=session_id)
        if result.get("status") == "error":
            err_data = result["error"]
            code = err_data["code"]
            status_code = 404 if code == "SESSION_NOT_FOUND" else 400
            return _error(code, err_data["message"], status_code)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("SESSION_FAILED", f"Session resume failed: {exc}", 500)


@app.get("/session/summary")
def endpoint_session_summary(
    vault: str = Query(..., description="Vault name"),
    session_id: str | None = Query(None, description="Session ID (omit for latest active)"),
):
    """Return a compact deterministic summary of a session.

    Suitable for local LLM context injection ("where was I up to?").

    Query parameters:
        vault (str, required): Vault name.
        session_id (str, optional): Specific session ID. Omit for latest active.

    Response data:
        summary (dict): Compact session summary with key fields.

    Error codes:
        INVALID_VAULT:    Vault is not registered (HTTP 404).
        SESSION_NOT_FOUND: No matching session found (HTTP 404).
    """
    err = _validate_vault(vault)
    if err:
        return err
    try:
        result = _session_state.summarise_session(vault, session_id=session_id)
        if result.get("status") == "error":
            err_data = result["error"]
            code = err_data["code"]
            status_code = 404 if code == "SESSION_NOT_FOUND" else 400
            return _error(code, err_data["message"], status_code)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("SESSION_FAILED", f"Session summary failed: {exc}", 500)


@app.post("/session/attach-note")
def endpoint_session_attach_note(req: SessionAttachNoteRequest):
    """Attach a vault note to a session's recent_notes list.

    Validates that the note exists and is inside the vault.
    Stores the vault-relative POSIX path.  De-duplicates recent_notes.

    Request body:
        vault (str, required): Vault name.
        session_id (str, required): Session ID.
        note_path (str, required): Vault-relative POSIX path of the note.

    Response data:
        session (dict): Updated session record.

    Error codes:
        INVALID_VAULT:     Vault is not registered (HTTP 404).
        INVALID_SESSION:   Session ID format is invalid (HTTP 400).
        SESSION_NOT_FOUND: Session not found (HTTP 404).
        INVALID_NOTE_PATH: Path is empty, absolute, or traverses outside vault (HTTP 400).
        NOTE_NOT_FOUND:    Note does not exist in the vault (HTTP 404).
        WRITE_FAILED:      Failed to write updated session (HTTP 500).
        REMOTE_READ_ONLY:  Server is in remote read-only mode (HTTP 403).
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = _session_state.attach_note_to_session(
            req.vault, req.session_id, req.note_path
        )
        if result.get("status") == "error":
            err_data = result["error"]
            code = err_data["code"]
            if code in ("SESSION_NOT_FOUND", "NOTE_NOT_FOUND"):
                status_code = 404
            else:
                status_code = 400
            return _error(code, err_data["message"], status_code)
        return {"status": "ok", "data": result}
    except OSError as exc:
        return _error("WRITE_FAILED", f"Failed to write session: {exc}", 500)
    except Exception as exc:
        return _error("SESSION_FAILED", f"Attach note failed: {exc}", 500)


@app.post("/session/close")
def endpoint_session_close(req: SessionCloseRequest):
    """Mark a session as closed without deleting it.

    Request body:
        vault (str, required): Vault name.
        session_id (str, required): Session ID to close.

    Response data:
        session (dict): Updated session record with status=closed.

    Error codes:
        INVALID_VAULT:    Vault is not registered (HTTP 404).
        INVALID_SESSION:  Session ID format is invalid (HTTP 400).
        SESSION_NOT_FOUND: Session not found (HTTP 404).
        WRITE_FAILED:     Failed to write updated session (HTTP 500).
        REMOTE_READ_ONLY: Server is in remote read-only mode (HTTP 403).
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = _session_state.close_session(req.vault, req.session_id)
        if result.get("status") == "error":
            err_data = result["error"]
            code = err_data["code"]
            status_code = 404 if code == "SESSION_NOT_FOUND" else 400
            return _error(code, err_data["message"], status_code)
        return {"status": "ok", "data": result}
    except OSError as exc:
        return _error("WRITE_FAILED", f"Failed to write session: {exc}", 500)
    except Exception as exc:
        return _error("SESSION_FAILED", f"Session close failed: {exc}", 500)


@app.get("/project/state")
def endpoint_project_state_get(
    vault: str = Query(..., description="Vault name"),
):
    """Return the project state for the given vault.

    Returns default state if no project-state.json exists yet.

    Query parameters:
        vault (str, required): Vault name.

    Response data:
        project_state (dict): Project state record (vault, current_phase,
            completed_work, next_actions, blockers, decisions, risks, updated_at).

    Error codes:
        INVALID_VAULT: Vault is not registered (HTTP 404).
    """
    err = _validate_vault(vault)
    if err:
        return err
    try:
        result = _session_state.get_project_state(vault)
        return {"status": "ok", "data": result}
    except Exception as exc:
        return _error("PROJECT_STATE_FAILED", f"Project state retrieval failed: {exc}", 500)


@app.put("/project/state")
def endpoint_project_state_update(req: ProjectStateUpdateRequest):
    """Merge updates into the vault's project state.

    Only the following fields are accepted in ``updates``:
        current_phase, completed_work, next_actions,
        blockers, decisions, risks.

    Unknown fields cause the request to be rejected.
    List fields are normalised to lists of strings.

    Request body:
        vault (str, required): Vault name.
        updates (dict, required): Fields to update.

    Response data:
        project_state (dict): Updated project state record.

    Error codes:
        INVALID_VAULT:          Vault is not registered (HTTP 404).
        INVALID_PROJECT_STATE:  Unknown fields or invalid update format (HTTP 400).
        WRITE_FAILED:           Failed to write project state (HTTP 500).
        REMOTE_READ_ONLY:       Server is in remote read-only mode (HTTP 403).
    """
    err = _validate_vault(req.vault)
    if err:
        return err
    try:
        result = _session_state.update_project_state(req.vault, req.updates)
        if result.get("status") == "error":
            err_data = result["error"]
            return _error(err_data["code"], err_data["message"], 400)
        return {"status": "ok", "data": result}
    except OSError as exc:
        return _error("WRITE_FAILED", f"Failed to write project state: {exc}", 500)
    except Exception as exc:
        return _error("PROJECT_STATE_FAILED", f"Project state update failed: {exc}", 500)


# ---------- Run ----------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
