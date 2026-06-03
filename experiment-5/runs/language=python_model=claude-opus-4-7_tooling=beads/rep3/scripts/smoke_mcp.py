"""End-to-end smoke test: speak MCP JSON-RPC over stdio to the installed server.

Sends initialize -> initialized -> tools/list -> tools/call(standings) and
prints a short summary so it's clear the server is alive.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys


def send(proc: subprocess.Popen, payload: dict) -> None:
    line = json.dumps(payload) + "\n"
    assert proc.stdin is not None
    proc.stdin.write(line)
    proc.stdin.flush()


def recv(proc: subprocess.Popen) -> dict:
    assert proc.stdout is not None
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("MCP server closed stdout unexpectedly")
    return json.loads(line)


def main() -> int:
    # Prefer the venv-installed entrypoint if available, otherwise launch the
    # module directly via the current Python interpreter.
    exe = shutil.which("brazilian-soccer-mcp")
    if exe:
        cmd = [exe]
    else:
        cmd = [sys.executable, "-m", "brazilian_soccer_mcp.server"]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        send(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke", "version": "0.0.0"},
            },
        })
        init_response = recv(proc)
        assert "result" in init_response, init_response

        send(proc, {
            "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
        })

        send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_response = recv(proc)
        tool_names = [t["name"] for t in tools_response["result"]["tools"]]
        print(f"tools registered: {len(tool_names)}")

        send(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "standings", "arguments": {"season": 2019, "competition": "Brasileirão"}},
        })
        call_response = recv(proc)
        structured = call_response["result"].get("structuredContent")
        rows = structured["result"] if structured else None
        if rows is None:
            text = call_response["result"]["content"][0]["text"]
            rows = [json.loads(text)]
        print(f"standings rows: {len(rows)}; champion: {rows[0]['team']} ({rows[0]['points']} pts)")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
