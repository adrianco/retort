"""Minimal stdio MCP fallback for environments with an incompatible SDK install.

The project normally uses the official Python MCP SDK.  Some hosts ship an MCP
package alongside an incompatible Pydantic major version; this compact adapter
keeps the server usable over the core JSON-RPC stdio operations until the clean
project environment declared in ``pyproject.toml`` is installed.
"""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import json
import sys
import types
from typing import Any, Callable, Mapping, Union, get_args, get_origin, get_type_hints


@dataclass(frozen=True, slots=True)
class FallbackTool:
    """A registered MCP tool and the metadata required by ``tools/list``."""

    name: str
    function: Callable[..., Any]
    description: str
    input_schema: dict[str, Any]

    def as_protocol_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass(frozen=True, slots=True)
class FallbackResource:
    """A static MCP resource registration."""

    uri: str
    function: Callable[..., Any]
    name: str
    description: str
    mime_type: str

    def as_protocol_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


class FallbackMCP:
    """Core MCP ``initialize``/tools/resources support over line-delimited stdio."""

    def __init__(self, name: str, *, instructions: str | None = None, **_: Any) -> None:
        self.name = name
        self.instructions = instructions or ""
        self.tools: dict[str, FallbackTool] = {}
        self.resources: dict[str, FallbackResource] = {}

    def tool(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        **_: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a tool using the same decorator shape used by FastMCP."""

        def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or function.__name__
            self.tools[tool_name] = FallbackTool(
                name=tool_name,
                function=function,
                description=description or inspect.getdoc(function) or "",
                input_schema=_function_input_schema(function),
            )
            return function

        return decorator

    def resource(
        self,
        uri: str,
        *,
        name: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
        **_: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a static resource using the FastMCP decorator shape."""

        def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
            self.resources[uri] = FallbackResource(
                uri=uri,
                function=function,
                name=name or function.__name__,
                description=description or inspect.getdoc(function) or "",
                mime_type=mime_type or "application/json",
            )
            return function

        return decorator

    async def list_tools(self) -> list[FallbackTool]:
        """Mirror FastMCP's coroutine surface for tests and in-process callers."""

        return list(self.tools.values())

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a registered tool directly, validating the tool name."""

        try:
            tool = self.tools[name]
        except KeyError as error:
            raise KeyError(f"Unknown MCP tool: {name}") from error
        result = tool.function(**arguments)
        if not isinstance(result, dict):
            return {"result": result}
        return result

    def run(self, transport: str = "stdio", **_: Any) -> None:
        """Serve the core MCP JSON-RPC operations over stdio."""

        if transport != "stdio":
            raise ValueError(
                "The fallback MCP adapter supports only stdio. Install project dependencies "
                "in a clean environment for SSE or streamable HTTP."
            )
        for line in sys.stdin:
            raw = line.strip()
            if not raw:
                continue
            try:
                request = json.loads(raw)
            except json.JSONDecodeError:
                self._write_error(None, -32700, "Parse error")
                continue
            self._handle_request(request)

    def _handle_request(self, request: dict[str, Any]) -> None:
        request_id = request.get("id")
        method = request.get("method")
        parameters = request.get("params") or {}
        if not isinstance(method, str):
            self._write_error(request_id, -32600, "Invalid Request")
            return

        # JSON-RPC notifications deliberately have no id and no response.
        if method == "notifications/initialized":
            return
        try:
            result = self._dispatch(method, parameters)
        except KeyError as error:
            self._write_error(request_id, -32601, str(error))
        except (TypeError, ValueError) as error:
            self._write_error(request_id, -32602, str(error))
        except Exception as error:  # pragma: no cover - defensive protocol boundary
            self._write_error(request_id, -32603, f"Internal error: {error}")
        else:
            if request_id is not None:
                self._write({"jsonrpc": "2.0", "id": request_id, "result": result})

    def _dispatch(self, method: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if method == "initialize":
            return {
                "protocolVersion": parameters.get("protocolVersion", "2024-11-05"),
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": {"name": self.name, "version": "0.1.0"},
                "instructions": self.instructions,
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [tool.as_protocol_dict() for tool in self.tools.values()]}
        if method == "tools/call":
            name = parameters.get("name")
            arguments = parameters.get("arguments") or {}
            if not isinstance(name, str) or not isinstance(arguments, dict):
                raise ValueError("tools/call requires a string name and an object arguments value.")
            result = self.tools[name].function(**arguments)
            return {
                "content": [
                    {"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}
                ],
                "structuredContent": result,
            }
        if method == "resources/list":
            return {"resources": [resource.as_protocol_dict() for resource in self.resources.values()]}
        if method == "resources/read":
            uri = parameters.get("uri")
            if not isinstance(uri, str):
                raise ValueError("resources/read requires a string uri.")
            resource = self.resources[uri]
            content = resource.function()
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": resource.mime_type,
                        "text": json.dumps(content, ensure_ascii=False, default=str),
                    }
                ]
            }
        raise KeyError(f"Method not found: {method}")

    @staticmethod
    def _write(message: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(message, ensure_ascii=False, default=str) + "\n")
        sys.stdout.flush()

    def _write_error(self, request_id: Any, code: int, message: str) -> None:
        self._write(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": code, "message": message},
            }
        )


def _function_input_schema(function: Callable[..., Any]) -> dict[str, Any]:
    """Produce a conservative JSON Schema for registered Python tool functions."""

    signature = inspect.signature(function)
    hints = get_type_hints(function)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for parameter in signature.parameters.values():
        if parameter.kind in {parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD}:
            continue
        annotation = hints.get(parameter.name, Any)
        schema = _json_schema_for(annotation)
        if parameter.default is not inspect.Parameter.empty:
            schema["default"] = parameter.default
        else:
            required.append(parameter.name)
        properties[parameter.name] = schema
    result: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        result["required"] = required
    return result


def _json_schema_for(annotation: Any) -> dict[str, Any]:
    if annotation is Any or annotation is inspect.Parameter.empty:
        return {}
    origin = get_origin(annotation)
    if origin in {Union, types.UnionType}:
        members = [member for member in get_args(annotation) if member is not type(None)]
        if len(members) == 1:
            return _json_schema_for(members[0])
        return {"anyOf": [_json_schema_for(member) for member in members]}
    if origin in {list, tuple, set, frozenset}:
        arguments = get_args(annotation)
        return {"type": "array", "items": _json_schema_for(arguments[0]) if arguments else {}}
    if origin in {dict, Mapping}:
        return {"type": "object"}
    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    return {}
