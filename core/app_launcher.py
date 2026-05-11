"""
Local app launcher for Context Vault Engine.

Implements ``py run.py app``:

1. Checks whether the local FastAPI server is already running.
2. If running and compatible — reuses it and opens the browser.
3. If the port is occupied by an unrecognised process — exits with an error.
4. If no server is running — starts ``mcp/server/mcp_server.py``, waits for it
   to become reachable, then opens the browser.
5. Handles missing ``ui/dist`` gracefully by printing build instructions.

Standard library only.  No external dependencies are added.
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
BASE_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"
APP_URL = f"{BASE_URL}/app"
HEALTH_URL = f"{BASE_URL}/health"

_STARTUP_TIMEOUT = 30.0   # seconds to wait for server to become reachable
_POLL_INTERVAL = 0.25     # seconds between health-check attempts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_ui_built(repo_root: Path) -> bool:
    """Return True when ``ui/dist/index.html`` exists."""
    dist = repo_root / "ui" / "dist"
    return dist.is_dir() and (dist / "index.html").is_file()


def probe_server() -> object:
    """
    Attempt a GET request to ``HEALTH_URL``.

    Returns the parsed JSON payload (a ``dict``) on success.
    Returns ``None`` when the connection is refused or the host is unreachable.
    Returns ``False`` when the server responds but returns invalid JSON.
    """
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=3) as resp:
            body = resp.read()
        try:
            return json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return False
    except urllib.error.URLError:
        return None
    except OSError:
        return None


def is_context_vault_health_response(payload: object) -> bool:
    """
    Return ``True`` when *payload* looks like a Context Vault Engine health
    response (``{"status": "ok", "data": {"vaults": ...}}``).
    """
    if not isinstance(payload, dict):
        return False
    if payload.get("status") != "ok":
        return False
    data = payload.get("data")
    if not isinstance(data, dict):
        return False
    return "vaults" in data


def wait_for_server(timeout: float = _STARTUP_TIMEOUT) -> bool:
    """
    Poll ``HEALTH_URL`` until a valid Context Vault Engine health response
    is received, or *timeout* seconds have elapsed.

    Returns ``True`` when the server is ready, ``False`` on timeout.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        payload = probe_server()
        if payload is not None and payload is not False:
            if is_context_vault_health_response(payload):
                return True
        time.sleep(_POLL_INTERVAL)
    return False


def open_browser() -> None:
    """Open ``APP_URL`` in the default system browser."""
    webbrowser.open(APP_URL)


def launch_server(repo_root: Path) -> "subprocess.Popen[bytes]":
    """
    Start ``mcp/server/mcp_server.py`` as a child process.

    The process is attached to the current terminal; Ctrl+C will propagate
    normally.  Returns the ``Popen`` handle so the caller can wait on it.
    """
    server_script = repo_root / "mcp" / "server" / "mcp_server.py"
    return subprocess.Popen(
        [sys.executable, str(server_script)],
        cwd=str(repo_root),
    )


def _print_ui_build_instructions() -> None:
    """Print human-readable instructions for building the frontend."""
    print()
    print("  The UI has not been built yet.  Run these commands first:")
    print()
    print("      cd ui")
    print("      npm install")
    print("      npm run build")
    print("      cd ..")
    print("      py run.py app")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(repo_root: Path) -> int:
    """
    Entry point called by ``run.py`` for the ``app`` command.

    Returns 0 on success (server running, browser opened) or when handing
    off to an already-running server.  Returns 1 on unrecoverable error.
    """
    ui_built = check_ui_built(repo_root)

    # --- Step 1: probe the port -------------------------------------------------
    payload = probe_server()

    if payload is not None:
        # Something is listening on port DEFAULT_PORT.
        if is_context_vault_health_response(payload):
            # Case A: compatible Context Vault Engine server already running.
            print(f"Context Vault Engine server already running at {BASE_URL}")
            if not ui_built:
                print(f"Warning: UI has not been built.")
                _print_ui_build_instructions()
                return 0
            print(f"Opening {APP_URL}")
            open_browser()
            return 0
        else:
            # Case B: port occupied by an unrecognised process.
            print(
                f"Error: port {DEFAULT_PORT} is in use by an unrecognised process."
            )
            print("Stop the other process and try again.")
            return 1

    # --- Step 2: no server running — warn about missing UI before starting ------
    if not ui_built:
        print(f"Warning: UI has not been built.")
        _print_ui_build_instructions()
        print("Starting the API server anyway (API endpoints will work;")
        print(f"  {APP_URL} will return a UI_NOT_BUILT error until you build the UI).")
        print()

    # --- Step 3: start the server -----------------------------------------------
    print(f"Starting Context Vault Engine server...")
    proc = launch_server(repo_root)

    print(f"Waiting for server at {HEALTH_URL} ...")
    ready = wait_for_server()

    if not ready:
        proc.terminate()
        print(
            f"Error: server did not become reachable within "
            f"{int(_STARTUP_TIMEOUT)} seconds."
        )
        print("Check for error output above and ensure uvicorn is installed.")
        return 1

    print(f"Server ready at {BASE_URL}")

    if ui_built:
        print(f"Opening {APP_URL}")
        open_browser()

    print("Press Ctrl+C to stop the server.")

    # --- Step 4: keep server attached to terminal until Ctrl+C -----------------
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nStopping server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    return 0
