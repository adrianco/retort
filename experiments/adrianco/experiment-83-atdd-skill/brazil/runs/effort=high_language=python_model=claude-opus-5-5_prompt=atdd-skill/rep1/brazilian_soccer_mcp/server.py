"""The MCP server: JSON-RPC 2.0 messages, one per line, over stdin/stdout."""
import json
import logging
import sys
import traceback

from brazilian_soccer_mcp import __version__
from brazilian_soccer_mcp.knowledge import QuestionError
from brazilian_soccer_mcp.tools import TOOLS, TOOLS_BY_NAME

SUPPORTED_PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]
INSTRUCTIONS = ("Answers questions about Brazilian soccer from Kaggle datasets: Brasileirão, Série B/C, Copa do "
                "Brasil and Copa Libertadores matches, and the FIFA player database. Club names may be written "
                "in any common spelling, with or without accents or state suffixes.")

PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS = -32700, -32600, -32601, -32602

log = logging.getLogger("brazilian_soccer_mcp")


class RequestError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class McpServer:
    def __init__(self, knowledge):
        self.knowledge = knowledge

    def handle(self, message):
        """The response to one JSON-RPC message, or None for notifications."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or "method" not in message:
            return _error(message.get("id") if isinstance(message, dict) else None, INVALID_REQUEST,
                          "Not a JSON-RPC 2.0 request")
        if "id" not in message:
            return None
        try:
            return {"jsonrpc": "2.0", "id": message["id"],
                    "result": self._dispatch(message["method"], message.get("params") or {})}
        except RequestError as problem:
            return _error(message["id"], problem.code, str(problem))

    def _dispatch(self, method, params):
        if method == "initialize":
            requested = params.get("protocolVersion")
            return {"protocolVersion": requested if requested in SUPPORTED_PROTOCOL_VERSIONS
                    else SUPPORTED_PROTOCOL_VERSIONS[0],
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "brazilian-soccer", "title": "Brazilian Soccer Knowledge",
                                   "version": __version__},
                    "instructions": INSTRUCTIONS}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [tool.definition for tool in TOOLS]}
        if method == "tools/call":
            return self._call_tool(params.get("name"), params.get("arguments") or {})
        raise RequestError(METHOD_NOT_FOUND, f"Method not found: {method}")

    def _call_tool(self, name, arguments):
        tool = TOOLS_BY_NAME.get(name)
        if tool is None:
            raise RequestError(INVALID_PARAMS, f"Unknown tool: {name}")
        if not isinstance(arguments, dict):
            raise RequestError(INVALID_PARAMS, "Tool arguments must be an object")
        try:
            answer, text = tool.call(self.knowledge, arguments)
        except QuestionError as problem:
            return {"content": [{"type": "text", "text": str(problem)}], "isError": True}
        except Exception as problem:  # noqa: BLE001 - report to the assistant rather than crash the server
            log.error("Tool %s failed: %s", name, traceback.format_exc())
            return {"content": [{"type": "text", "text": f"Sorry, that question could not be answered: {problem}"}],
                    "isError": True}
        return {"content": [{"type": "text", "text": text}], "structuredContent": answer, "isError": False}


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def serve(server, reader=sys.stdin, writer=sys.stdout):
    for line in reader:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = _error(None, PARSE_ERROR, "Parse error")
        else:
            response = server.handle(message)
        if response is not None:
            writer.write(json.dumps(response, ensure_ascii=False) + "\n")
            writer.flush()
