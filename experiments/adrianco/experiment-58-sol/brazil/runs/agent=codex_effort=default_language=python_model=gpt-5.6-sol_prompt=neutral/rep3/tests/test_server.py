from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from types import ModuleType


def _install_sdk_stub_when_dependency_is_unavailable() -> None:
    """Let the protocol contract tests run in an offline, dependency-free checkout."""
    if importlib.util.find_spec("mcp") is not None:
        return

    class Message:
        def __init__(self, **values):
            self.__dict__.update(values)

    class StubServer:
        def __init__(self, name):
            self.name = name
            self.handlers = {}

        def _decorator(self, method):
            def register(function):
                self.handlers[method] = function
                return function

            return register

        def list_tools(self):
            return self._decorator("tools/list")

        def call_tool(self):
            return self._decorator("tools/call")

        def list_resources(self):
            return self._decorator("resources/list")

        def read_resource(self):
            return self._decorator("resources/read")

    mcp_module = ModuleType("mcp")
    mcp_module.__path__ = []
    server_module = ModuleType("mcp.server")
    server_module.__path__ = []
    stdio_module = ModuleType("mcp.server.stdio")
    models_module = ModuleType("mcp.server.models")
    lowlevel_module = ModuleType("mcp.server.lowlevel")
    types_module = ModuleType("mcp.types")

    lowlevel_module.Server = StubServer
    lowlevel_module.NotificationOptions = Message
    models_module.InitializationOptions = Message
    types_module.Tool = Message
    types_module.TextContent = Message
    types_module.Resource = Message
    server_module.stdio = stdio_module
    mcp_module.server = server_module
    mcp_module.types = types_module

    sys.modules.update(
        {
            "mcp": mcp_module,
            "mcp.server": server_module,
            "mcp.server.stdio": stdio_module,
            "mcp.server.models": models_module,
            "mcp.server.lowlevel": lowlevel_module,
            "mcp.types": types_module,
        }
    )


_install_sdk_stub_when_dependency_is_unavailable()

from brazilian_soccer_mcp import server as protocol  # noqa: E402


def test_given_mcp_server_when_tools_listed_then_all_required_handlers_are_registered():
    tools = asyncio.run(protocol.list_tools())
    names = {tool.name for tool in tools}
    assert {
        "search_matches",
        "team_statistics",
        "head_to_head",
        "search_players",
        "standings",
        "competition_statistics",
        "biggest_victories",
        "dataset_status",
    } <= names
    assert all(tool.inputSchema["type"] == "object" for tool in tools)


def test_given_mcp_resource_when_listed_then_dataset_inventory_is_registered():
    resources = asyncio.run(protocol.list_resources())
    assert len(resources) == 1
    assert str(resources[0].uri) == protocol.DATASET_URI


def test_given_tool_call_when_dispatched_then_json_content_contains_real_data(service, monkeypatch):
    monkeypatch.setattr(protocol, "get_service", lambda: service)
    content = asyncio.run(protocol.call_tool("dataset_status", {}))
    result = json.loads(content[0].text)
    assert result["all_datasets_loaded"] is True
    assert result["total_matches"] > 23_000


def test_given_unknown_tool_when_dispatched_then_it_is_rejected(service):
    try:
        protocol.dispatch_tool("not_a_tool", service=service)
    except ValueError as error:
        assert "Unknown MCP tool" in str(error)
    else:  # pragma: no cover - documents the fail-closed contract
        raise AssertionError("unknown tools must not be accepted")
