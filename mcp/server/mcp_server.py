"""
MCP Server — read-only API layer over multiple Obsidian vaults.

Endpoints:
    GET  /vaults  — list registered vault names
    POST /query   — query a vault with filters
    GET  /note    — retrieve a single note by vault + path
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
from fastapi.responses import JSONResponse
from starlette.requests import Request
from pydantic import BaseModel, Field

from mcp.core.vault_registry import list_vaults, get_vault_path, get_schema
from mcp.core.note_index import build_index, get_index, get_schema_hash, get_index_metadata
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
from core.shared.feedback import load_feedback as _load_feedback
from core.shared.context_package import export_context_package as _export_package


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
    """Query a vault with optional filters.

    Response data:
        status (str): ``"ok"`` or ``"partial"`` (partial = query timed out).
        count (int): Total matching notes before pagination.
        returned (int): Notes in this page.
        offset (int): Page offset applied.
        limit (int): Page size applied.
        results (list): Matching note objects with ``path`` and ``fields``.
    """
    err = _validate_vault(req.vault)
    if err:
        return err

    try:
        if req.filters:
            result = query(req.vault, req.filters, limit=req.limit,
                           offset=req.offset, strict=req.strict)
        else:
            result = list_notes(req.vault, limit=req.limit, offset=req.offset)

        # Forward engine-level error responses
        if result["status"] == "error":
            return JSONResponse(status_code=400, content=result)
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
def endpoint_summary():
    """Aggregate vault-level decision signals.

    Response data:
        total_notes (int): Total notes in the vault.
        complete (int): Notes with status ``"complete"``.
        partial (int): Notes not yet complete.
        coverage (int): Completion percentage (0–100).
    """
    try:
        result = get_all_notes()
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

    try:
        result = _generate_bundle(
            vault_name=req.vault,
            filters=req.filters,
            include_sections=req.include_sections,
            include_related=req.include_related,
            include_body=req.include_body,
            max_notes=req.max_notes,
            max_chars=req.max_chars,
            allow_partial=req.allow_partial,
        )
        if result.get("status") == "error":
            code = result.get("error", {}).get("code", "BUNDLE_FAILED")
            msg = result.get("error", {}).get("message", "Bundle generation failed")
            return _error(code, msg, 500)
        return result
    except Exception as exc:
        return _error("BUNDLE_FAILED", f"Bundle generation failed: {exc}", 500)


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
            "status": result["status"],
            "vault": vault,
            "entries": result["entries"],
            "warnings": result["warnings"],
            "errors": result["errors"],
        }
    except Exception as exc:
        return _error("FEEDBACK_ERROR", f"Feedback retrieval failed: {exc}", 500)


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

    try:
        bundle = _generate_bundle(
            vault_name=req.vault,
            filters=req.filters,
            include_sections=req.include_sections,
            include_related=req.include_related,
            include_body=req.include_body,
            max_notes=req.max_notes,
            max_chars=req.max_chars,
            allow_partial=req.allow_partial,
        )
        if bundle.get("status") == "error":
            code = bundle.get("error", {}).get("code", "BUNDLE_FAILED")
            msg = bundle.get("error", {}).get("message", "Bundle generation failed")
            return _error(code, msg, 500)

        result = _export_package(bundle, overwrite=req.overwrite)
        if result["status"] == "error":
            code = result["error"]["code"]
            msg = result["error"]["message"]
            status_code = 409 if code == "PACKAGE_EXISTS" else 500
            return _error(code, msg, status_code)

        return result

    except Exception as exc:
        return _error("EXPORT_FAILED", f"Export failed: {exc}", 500)


# ---------- Run ----------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
