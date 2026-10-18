"""Minimal Model Context Protocol server over stdio (JSON-RPC 2.0).

Implements the parts of MCP a tool-only server needs: ``initialize``,
``ping``, ``tools/list`` and ``tools/call``. Requests are handled one per
line on stdin and answered on stdout; notifications get no reply.
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from .store import SoccerData
from .tools import TOOLS, call_tool

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "brazilian-soccer-mcp", "version": "1.0.0"}

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


class MCPServer:
    def __init__(self, data: SoccerData):
        self.data = data

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Return the JSON-RPC response for ``message``, or None for notifications."""
        method = message.get("method")
        request_id = message.get("id")
        is_notification = "id" not in message
        if not isinstance(method, str):
            return _error(request_id, INVALID_REQUEST, "missing method")

        try:
            result = self._dispatch(method, message.get("params") or {})
        except _RpcError as exc:
            return None if is_notification else _error(request_id, exc.code, exc.message)
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "initialize":
            return {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [
                {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
                for t in TOOLS
            ]}
        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str):
                raise _RpcError(INVALID_PARAMS, "tools/call requires a tool name")
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise _RpcError(INVALID_PARAMS, "arguments must be an object")
            text, is_error = call_tool(self.data, name, arguments)
            return {"content": [{"type": "text", "text": text}], "isError": is_error}
        if method.startswith("notifications/"):
            return {}
        raise _RpcError(METHOD_NOT_FOUND, f"method not found: {method}")

    def serve(self, reader: TextIO, writer: TextIO) -> None:
        for line in reader:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                response = _error(None, PARSE_ERROR, f"parse error: {exc.msg}")
            else:
                if not isinstance(message, dict):
                    response = _error(None, INVALID_REQUEST, "expected a JSON object")
                else:
                    response = self.handle(message)
            if response is not None:
                writer.write(json.dumps(response, ensure_ascii=False) + "\n")
                writer.flush()


class _RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def run(data: SoccerData, reader: TextIO = sys.stdin, writer: TextIO = sys.stdout) -> None:
    MCPServer(data).serve(reader, writer)
