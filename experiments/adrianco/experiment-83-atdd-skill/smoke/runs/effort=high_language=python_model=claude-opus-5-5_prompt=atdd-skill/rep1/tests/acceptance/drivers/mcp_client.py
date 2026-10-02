"""
Minimal MCP client used by the protocol driver: launches the server as a
subprocess and speaks JSON-RPC 2.0 over stdio, exactly as an LLM host would.
"""

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class McpError(AssertionError):
    pass


class McpClient:
    def __init__(self, data_dir, timeout=30):
        self._timeout = timeout
        env = dict(os.environ, SOCCER_DATA_DIR=str(data_dir), PYTHONIOENCODING="utf-8")
        self._process = subprocess.Popen(
            [sys.executable, "-m", "brazilian_soccer_mcp"], cwd=PROJECT_ROOT, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1)
        self._lines = queue.Queue()
        threading.Thread(target=self._read_stdout, daemon=True).start()
        self._next_id = 0
        self.server_info = self._request("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "acceptance-tests", "version": "1.0"}})
        self._notify("notifications/initialized")
        self.tools = {tool["name"] for tool in self._request("tools/list", {})["tools"]}

    def call_tool(self, name, arguments):
        if name not in self.tools:
            raise McpError(f"The server does not offer a '{name}' tool (it offers {sorted(self.tools)})")
        arguments = {k: v for k, v in arguments.items() if v is not None}
        return self._request("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        if self._process.poll() is None:
            self._process.stdin.close()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process.stdout.close()
        self._process.stderr.close()

    def _read_stdout(self):
        for line in self._process.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def _notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, **({"params": params} if params else {})})

    def _request(self, method, params):
        self._next_id += 1
        request_id = self._next_id
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while True:
            try:
                line = self._lines.get(timeout=self._timeout)
            except queue.Empty:
                raise McpError(f"No reply to '{method}' within {self._timeout}s")
            if line is None:
                raise McpError(f"Server exited while handling '{method}': {self._process.stderr.read()}")
            message = json.loads(line)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise McpError(f"'{method}' failed: {message['error']}")
            return message["result"]

    def _send(self, message):
        self._process.stdin.write(json.dumps(message) + "\n")
        self._process.stdin.flush()
