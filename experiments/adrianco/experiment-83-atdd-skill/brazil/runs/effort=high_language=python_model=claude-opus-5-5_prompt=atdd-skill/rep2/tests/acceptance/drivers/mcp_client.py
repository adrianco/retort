"""
Protocol driver plumbing: a minimal MCP client speaking JSON-RPC over stdio.

The system under test is an MCP server, so the acceptance tests talk to it
exactly as an LLM host would: launch it as a subprocess, perform the MCP
initialize handshake, then call tools. Hand-rolling the wire protocol (rather
than reusing the server's own SDK) means the tests also verify the server
speaks standard MCP.

Responses are awaited with poll-with-timeout (a reader thread feeding a
queue), never with sleeps, so a hung server fails fast with a clear message.
"""
import itertools
import json
import os
import pathlib
import queue
import subprocess
import sys
import threading

PROTOCOL_VERSION = "2025-06-18"


class McpError(AssertionError):
    pass


class McpStdioClient:
    def __init__(self, command, env=None, cwd=None, timeout_seconds=60):
        self._timeout = timeout_seconds
        self._ids = itertools.count(1)
        self._messages = queue.Queue()
        self._process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, **(env or {})}, cwd=cwd, text=True, encoding="utf-8", bufsize=1,
        )
        self._stderr = []
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        self.server_info = self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "acceptance-tests", "version": "1.0"},
        })
        self._notify("notifications/initialized")

    def list_tools(self):
        return self._request("tools/list", {})["tools"]

    def call_tool(self, name, arguments):
        return self._request("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        if self._process.poll() is None:
            self._process.stdin.close()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()

    def _notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, **({"params": params} if params else {})})

    def _request(self, method, params):
        request_id = next(self._ids)
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while True:
            try:
                message = self._messages.get(timeout=self._timeout)
            except queue.Empty:
                raise McpError(f"The soccer server did not answer {method} within {self._timeout}s."
                               f"{self._diagnostics()}") from None
            if message is None:
                raise McpError(f"The soccer server stopped while answering {method}.{self._diagnostics()}")
            if message.get("id") != request_id:
                continue  # notifications and log messages
            if "error" in message:
                raise McpError(f"The soccer server rejected {method}: {message['error']}")
            return message["result"]

    def _send(self, message):
        try:
            self._process.stdin.write(json.dumps(message) + "\n")
            self._process.stdin.flush()
        except BrokenPipeError:
            raise McpError(f"The soccer server is not running.{self._diagnostics()}") from None

    def _read_stdout(self):
        for line in self._process.stdout:
            line = line.strip()
            if line:
                try:
                    self._messages.put(json.loads(line))
                except json.JSONDecodeError:
                    self._stderr.append(f"(non-JSON on stdout) {line}")
        self._messages.put(None)

    def _read_stderr(self):
        for line in self._process.stderr:
            self._stderr.append(line.rstrip())

    def _diagnostics(self):
        tail = "\n".join(self._stderr[-20:])
        return f"\nServer stderr:\n{tail}" if tail else ""


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]


def soccer_server_command(data_dir):
    return [sys.executable, "-m", "brazilian_soccer_mcp", "--data-dir", str(data_dir)]


def soccer_server_environment():
    return {"PYTHONPATH": os.pathsep.join(filter(None, [str(PROJECT_ROOT), os.environ.get("PYTHONPATH")]))}
