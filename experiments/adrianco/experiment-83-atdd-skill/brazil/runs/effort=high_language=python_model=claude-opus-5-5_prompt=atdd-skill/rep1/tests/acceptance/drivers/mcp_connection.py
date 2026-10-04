"""A minimal MCP client: launches the server as a subprocess and speaks JSON-RPC over stdio,
exactly as an AI assistant's host application would."""
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESPONSE_TIMEOUT_SECONDS = 60


@dataclass
class Answer:
    text: str
    data: dict
    is_error: bool
    seconds: float


class McpConnection:
    def __init__(self, data_directory):
        self._data_directory = data_directory
        self._process = None
        self._lines = queue.Queue()
        self._next_id = 0
        self.last_answer = None

    def start(self):
        self._log = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        environment = dict(os.environ, PYTHONIOENCODING="utf-8")
        self._process = subprocess.Popen(
            [sys.executable, "-m", "brazilian_soccer_mcp", "--data-dir", str(self._data_directory)],
            cwd=PROJECT_ROOT, env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self._log, text=True, encoding="utf-8")
        threading.Thread(target=self._read_lines, daemon=True).start()
        result = self.request("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "acceptance-tests", "version": "1.0"}})
        assert "tools" in result.get("capabilities", {}), "The server did not offer any tools"
        self.notify("notifications/initialized")
        return result

    def close(self):
        if self._process and self._process.poll() is None:
            self._process.stdin.close()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()

    def list_tools(self):
        return self.request("tools/list", {})["tools"]

    def call_tool(self, name, arguments):
        arguments = {key: value for key, value in arguments.items() if value is not None}
        started = time.perf_counter()
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        seconds = time.perf_counter() - started
        text = "\n".join(item["text"] for item in result.get("content", []) if item.get("type") == "text")
        self.last_answer = Answer(text=text, data=result.get("structuredContent") or {},
                                  is_error=bool(result.get("isError")), seconds=seconds)
        return self.last_answer

    def notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, **({"params": params} if params else {})})

    def request(self, method, params):
        self._next_id += 1
        request_id = self._next_id
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while True:
            message = self._receive(method)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise AssertionError(f"The server rejected '{method}': {message['error']}")
            return message["result"]

    def _send(self, message):
        self._process.stdin.write(json.dumps(message) + "\n")
        self._process.stdin.flush()

    def _receive(self, method):
        try:
            line = self._lines.get(timeout=RESPONSE_TIMEOUT_SECONDS)
        except queue.Empty:
            raise AssertionError(f"The server did not answer '{method}' within {RESPONSE_TIMEOUT_SECONDS}s")
        if line is None:
            self._log.seek(0)
            raise AssertionError(f"The server stopped while answering '{method}':\n{self._log.read()}")
        return json.loads(line)

    def _read_lines(self):
        for line in self._process.stdout:
            if line.strip():
                self._lines.put(line)
        self._lines.put(None)
