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

# Ensure project root is on sys.path so core.* imports work
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from starlette.requests import Request
from pydantic import BaseModel, Field

from core.vault_registry import list_vaults, get_vault_path, get_schema
from core.note_index import build_index, get_index, get_schema_hash, get_index_metadata
from core.query_engine import query, list_notes, get_note, aggregate
from core.contract_runner import run_all_checks, run_lightweight_checks


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
    vault: str
    filters: dict = {}
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    strict: bool = False


# ---------- Error helpers (Phase 10) ----------

def _error(code: str, message: str, status_code: int = 400) -> JSONResponse:
    logger.error("error_response code=%s message=%s status=%d", code, message, status_code)
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error": {"code": code, "message": message},
        },
    )


def _validate_vault(vault_name: str) -> JSONResponse | None:
    """Return an error response if the vault is invalid, else None."""
    try:
        get_vault_path(vault_name)
    except KeyError as exc:
        return _error("INVALID_VAULT", str(exc), 404)
    return None


# ---------- Endpoints ----------

@app.get("/vaults")
def endpoint_vaults():
    """List all registered vault names."""
    try:
        return {"status": "ok", "data": {"vaults": list_vaults()}}
    except Exception as exc:
        return _error("INTERNAL", f"Failed to list vaults: {exc}", 500)


@app.post("/query")
def endpoint_query(req: QueryRequest):
    """Query a vault with optional filters."""
    err = _validate_vault(req.vault)
    if err:
        return err

    try:
        if req.filters:
            result = query(req.vault, req.filters, limit=req.limit,
                           offset=req.offset, strict=req.strict)
        else:
            result = list_notes(req.vault, limit=req.limit, offset=req.offset)

        # Forward error responses from query engine
        if result["status"] == "error":
            return JSONResponse(status_code=400, content=result)
        return result
    except Exception as exc:
        return _error("QUERY_FAILED", f"Query failed: {exc}", 500)


@app.get("/note")
def endpoint_note(
    vault: str = Query(..., description="Vault name"),
    path: str = Query(..., description="Relative note path"),
):
    """Retrieve a single note by vault and path."""
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
    """Aggregate distinct values for a field across a vault."""
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
    """Health endpoint with real metrics (Phase 11 + Phase 6 expansion)."""
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
            health = {
                "status": "ok",
                "vaults": vaults_info,
                "uptime_seconds": int(time.monotonic() - _start_time),
                "requests_served": _request_count,
                "rate_limit_status": {
                    "max_per_second": 50,
                    "current_window": _rate_limiter.current_window_count,
                    "total_rejected": _rate_limiter.rejected_count,
                },
                "metrics": {
                    "per_endpoint": dict(_endpoint_counts),
                    "avg_response_time_ms": round(avg_response * 1000, 2),
                },
            }

        return health
    except Exception as exc:
        return _error("HEALTH_FAILED", f"Health check failed: {exc}", 500)


@app.get("/contract")
def endpoint_contract(
    full: bool = Query(False, description="Run full checks including vault scripts"),
):
    """Run system contract checks and return results."""
    try:
        if full:
            result = run_all_checks(include_vault_scripts=True)
        else:
            result = run_all_checks(include_vault_scripts=False)
        status_code = 200 if result["status"] == "pass" else 500
        return JSONResponse(status_code=status_code, content=result)
    except Exception as exc:
        return _error("CONTRACT_FAILED", f"Contract check failed: {exc}", 500)


# ---------- Run ----------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
