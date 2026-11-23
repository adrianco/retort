"""Read-only Brazilian soccer tools over MCP's UTF-8 stdio transport."""
import inspect
import json
import sys
from typing import get_args

from soccer import Soccer

PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
STRUCTURED_PROTOCOLS = PROTOCOLS[:2]
TOOL_NAMES = (
    "search_matches", "team_stats", "head_to_head", "search_players", "standings",
    "tournament_bracket", "match_statistics", "team_rankings", "club_profile",
    "top_scorers", "coverage",
)
TYPES = {str: "string", int: "integer", bool: "boolean", type(None): "null"}


def parameter_types(parameter):
    return get_args(parameter.annotation) or (parameter.annotation,)


def tool_schema(tool):
    properties = {}
    required = []
    for name, parameter in inspect.signature(tool).parameters.items():
        types = [TYPES[kind] for kind in parameter_types(parameter)]
        properties[name] = {"type": types[0] if len(types) == 1 else types}
        if parameter.default is inspect.Parameter.empty:
            required.append(name)
        else:
            properties[name]["default"] = parameter.default
    return {"name": tool.__name__, "description": inspect.getdoc(tool),
            "annotations": {"readOnlyHint": True, "openWorldHint": False},
            "inputSchema": {"type": "object", "properties": properties,
                            "required": required, "additionalProperties": False}}


class RPCError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class Server:
    def __init__(self, data):
        self.tools = {name: getattr(data, name) for name in TOOL_NAMES}
        self.descriptions = [tool_schema(tool) for tool in self.tools.values()]
        self.protocol = None
        self.ready = False

    def call_tool(self, params):
        name = params.get("name")
        if not isinstance(name, str) or name not in self.tools:
            raise RPCError(-32602, "Unknown tool")
        tool = self.tools[name]
        arguments = params.get("arguments", {})
        try:
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be an object.")
            signature = inspect.signature(tool)
            signature.bind(**arguments)
            for key, value in arguments.items():
                if type(value) not in parameter_types(signature.parameters[key]):
                    raise ValueError(f"Invalid type for {key}")
            result = tool(**arguments)
        except (ValueError, TypeError) as error:
            return {"content": [{"type": "text", "text": str(error)}], "isError": True}
        response = {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
        if self.protocol in STRUCTURED_PROTOCOLS:
            response["structuredContent"] = result
        return response

    def dispatch(self, method, params):
        if method == "initialize":
            requested = params.get("protocolVersion")
            if not isinstance(requested, str):
                raise RPCError(-32602, "Expected protocolVersion")
            self.protocol = requested if requested in PROTOCOLS else PROTOCOLS[0]
            self.ready = False
            return {
                "protocolVersion": self.protocol, "capabilities": {"tools": {}},
                "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"},
                "instructions": (
                    "Use the tools to answer questions about the included soccer datasets. "
                    "Use search_matches with limit=1 for the latest fixture. Check standings "
                    "coverage before declaring champions or relegation. Use next_offset to page. "
                    "FIFA clubs and ratings describe a historical snapshot."
                ),
            }
        if method == "ping":
            return {}
        if not self.ready:
            raise RPCError(-32002, "Server has not been initialized")
        if method == "tools/list":
            return {"tools": self.descriptions}
        if method == "tools/call":
            return self.call_tool(params)
        raise RPCError(-32601, "Method not found")

    def receive(self, line):
        request_id = None
        try:
            try:
                message = json.loads(line)
            except (ValueError, UnicodeError) as error:
                raise RPCError(-32700, "Invalid JSON") from error
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                raise RPCError(-32600, "Invalid request")
            method = message.get("method")
            if not isinstance(method, str):
                if "id" in message and ("result" in message or "error" in message):
                    return None
                raise RPCError(-32600, "Invalid request")
            if "id" not in message:
                if method == "notifications/initialized" and self.protocol:
                    self.ready = True
                return None
            request_id = message["id"]
            if type(request_id) not in (int, str):
                request_id = None
                raise RPCError(-32600, "Invalid request ID")
            params = message.get("params", {})
            if not isinstance(params, dict):
                raise RPCError(-32602, "Expected an object for params")
            payload = {"result": self.dispatch(method, params)}
        except RPCError as error:
            payload = {"error": {"code": error.code, "message": str(error)}}
        return {"jsonrpc": "2.0", "id": request_id, **payload}


def main():
    server = Server(Soccer())
    for line in sys.stdin.buffer:
        response = server.receive(line)
        if response is not None:
            encoded = json.dumps(response, ensure_ascii=False).encode("utf-8")
            sys.stdout.buffer.write(encoded + b"\n")
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
