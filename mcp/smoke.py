"""Deterministic local MCP stdio smoke test (Phase 39).

Spawns ``py run.py mcp`` as a subprocess, sends a minimal JSON-RPC 2.0
sequence, and verifies the responses. Used by ``py run.py mcp-smoke`` and by
deterministic tests in ``mcp/test_verify.py``.

The smoke test exists so a local user can verify that the MCP stdio server
starts, handshakes, advertises tools/resources/prompts, and answers a single
safe tool call without an external MCP client. It does NOT mutate any vault
note. It does NOT accept any pending change. It does NOT exercise the safe
pending-change proposal or revalidation tools.

Standard library only.

The server uses stdin/stdout for JSON-RPC; any non-JSON text emitted on
stdout by the server is treated as contamination and fails the smoke test.
Server logs are written to stderr and are not parsed.

Exit status:
  0 - all smoke checks passed
  1 - any smoke check failed
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


class SmokeError(Exception):
    """Raised when a smoke-test invariant is violated."""


def parse_jsonrpc_line(line: str) -> dict:
    """Parse a single line of stdout as a JSON-RPC 2.0 message.

    Raises:
        SmokeError: if the line is empty, not valid JSON, not an object,
            or missing the ``jsonrpc: "2.0"`` field.
    """
    stripped = line.strip()
    if not stripped:
        raise SmokeError("empty line")
    try:
        msg = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise SmokeError(
            f"non-JSON stdout contamination: {stripped[:200]!r}: {exc}"
        )
    if not isinstance(msg, dict):
        raise SmokeError(
            f"JSON-RPC message must be an object: {stripped[:200]!r}"
        )
    if msg.get("jsonrpc") != "2.0":
        raise SmokeError(
            f"missing or invalid 'jsonrpc' field: {msg!r}"
        )
    return msg


def check_stdout_clean(stdout_text: str) -> list[dict]:
    """Verify every non-empty stdout line parses as a JSON-RPC 2.0 message.

    Returns the parsed messages in the order they were received.
    Raises SmokeError on the first contaminated line.
    """
    parsed: list[dict] = []
    for line in stdout_text.splitlines():
        if not line.strip():
            continue
        parsed.append(parse_jsonrpc_line(line))
    return parsed


def _build_requests() -> list[dict]:
    """Build the deterministic JSON-RPC sequence sent to the server."""
    return [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "cve-smoke", "version": "0.1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "resources/list"},
        {"jsonrpc": "2.0", "id": 4, "method": "prompts/list"},
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "cve_list_vaults", "arguments": {}},
        },
    ]


def run_smoke(repo_root: Path | None = None, python_cmd: str | None = None,
              timeout: int = 60) -> int:
    """Run the deterministic MCP stdio smoke test.

    Args:
        repo_root: Repository root containing ``run.py``. Defaults to the
            parent of this module.
        python_cmd: Python executable used to spawn the subprocess.
            Defaults to ``sys.executable`` for deterministic invocation.
        timeout: Subprocess timeout in seconds.

    Returns:
        0 on success, 1 on failure. Failure diagnostics are written to
        stderr.
    """
    repo_root = repo_root or Path(__file__).resolve().parent.parent
    python_cmd = python_cmd or sys.executable

    cmd = [python_cmd, str(repo_root / "run.py"), "mcp"]
    requests = _build_requests()
    stdin_text = "".join(
        json.dumps(r, ensure_ascii=False) + "\n" for r in requests
    )

    print(f"[mcp-smoke] starting MCP stdio server: {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(repo_root),
        )
    except subprocess.TimeoutExpired as exc:
        print(
            f"[mcp-smoke] FAIL: subprocess timed out after {timeout}s: {exc}",
            file=sys.stderr,
        )
        return 1
    except FileNotFoundError as exc:
        print(f"[mcp-smoke] FAIL: cannot launch subprocess: {exc}",
              file=sys.stderr)
        return 1

    if proc.returncode != 0:
        print(
            f"[mcp-smoke] FAIL: server exited non-zero ({proc.returncode})",
            file=sys.stderr,
        )
        if proc.stderr:
            print(
                f"[mcp-smoke] stderr tail:\n{proc.stderr[-1000:]}",
                file=sys.stderr,
            )
        return 1

    try:
        messages = check_stdout_clean(proc.stdout)
    except SmokeError as exc:
        print(
            f"[mcp-smoke] FAIL: stdout not clean JSON-RPC: {exc}",
            file=sys.stderr,
        )
        return 1

    by_id: dict = {m["id"]: m for m in messages if "id" in m}

    # 1. initialize result
    init = by_id.get(1)
    if not init or "result" not in init:
        print(f"[mcp-smoke] FAIL: initialize missing or errored: {init!r}",
              file=sys.stderr)
        return 1
    init_result = init["result"]
    for required in ("protocolVersion", "serverInfo", "capabilities"):
        if required not in init_result:
            print(
                f"[mcp-smoke] FAIL: initialize result missing {required!r}: "
                f"{init_result!r}",
                file=sys.stderr,
            )
            return 1
    print(
        "[mcp-smoke] initialize ok "
        f"(protocolVersion={init_result['protocolVersion']!r})"
    )

    # 2. tools/list
    tools_resp = by_id.get(2)
    if (not tools_resp
            or "result" not in tools_resp
            or "tools" not in tools_resp["result"]):
        print(f"[mcp-smoke] FAIL: tools/list invalid: {tools_resp!r}",
              file=sys.stderr)
        return 1
    tools = tools_resp["result"]["tools"]
    if not isinstance(tools, list) or not tools:
        print(
            f"[mcp-smoke] FAIL: tools/list returned empty or non-list: "
            f"{tools!r}",
            file=sys.stderr,
        )
        return 1
    for tool in tools:
        if not isinstance(tool, dict) or "name" not in tool:
            print(
                f"[mcp-smoke] FAIL: tool entry missing 'name': {tool!r}",
                file=sys.stderr,
            )
            return 1
    print(f"[mcp-smoke] tools/list ok ({len(tools)} tools)")

    # 3. resources/list
    res_resp = by_id.get(3)
    if (not res_resp
            or "result" not in res_resp
            or "resources" not in res_resp["result"]):
        print(f"[mcp-smoke] FAIL: resources/list invalid: {res_resp!r}",
              file=sys.stderr)
        return 1
    resources = res_resp["result"]["resources"]
    if not isinstance(resources, list):
        print(
            f"[mcp-smoke] FAIL: resources/list not a list: {resources!r}",
            file=sys.stderr,
        )
        return 1
    print(f"[mcp-smoke] resources/list ok ({len(resources)} resources)")

    # 4. prompts/list
    pr_resp = by_id.get(4)
    if (not pr_resp
            or "result" not in pr_resp
            or "prompts" not in pr_resp["result"]):
        print(f"[mcp-smoke] FAIL: prompts/list invalid: {pr_resp!r}",
              file=sys.stderr)
        return 1
    prompts = pr_resp["result"]["prompts"]
    if not isinstance(prompts, list):
        print(
            f"[mcp-smoke] FAIL: prompts/list not a list: {prompts!r}",
            file=sys.stderr,
        )
        return 1
    print(f"[mcp-smoke] prompts/list ok ({len(prompts)} prompts)")

    # 5. tools/call cve_list_vaults
    call_resp = by_id.get(5)
    if not call_resp or "result" not in call_resp:
        print(
            f"[mcp-smoke] FAIL: cve_list_vaults call invalid: {call_resp!r}",
            file=sys.stderr,
        )
        return 1
    print("[mcp-smoke] cve_list_vaults ok")

    print("[mcp-smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_smoke())
