"""Transport-adapter tests without requiring a live stdio subprocess."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys

import pytest

from brazilian_soccer_mcp.fallback_mcp import FallbackMCP
from brazilian_soccer_mcp.server import create_server


class FakeMCP:
    """Small FastMCP-compatible registry used to assert server wiring."""

    def __init__(self, name: str, *, instructions: str) -> None:
        self.name = name
        self.instructions = instructions
        self.tools: dict[str, object] = {}
        self.resources: dict[str, object] = {}

    def tool(self, *, name: str, **_: object):
        def decorator(function):
            self.tools[name] = function
            return function

        return decorator

    def resource(self, uri: str, **_: object):
        def decorator(function):
            self.resources[uri] = function
            return function

        return decorator


def test_given_server_factory_when_constructed_then_all_query_capabilities_are_registered() -> None:
    server = create_server(mcp_factory=FakeMCP)
    expected_tools = {
        "data_summary",
        "knowledge_graph",
        "search_matches",
        "team_statistics",
        "compare_teams",
        "search_players",
        "competition_standings",
        "competition_statistics",
        "ask_brazilian_soccer",
    }
    assert expected_tools <= set(server.tools)
    assert "soccer://datasets" in server.resources
    assert server.tools["search_matches"](team="Flamengo", limit=1)["matches"]
    assert server.tools["ask_brazilian_soccer"]("Who is L. Messi?")["intent"] == "search_players"


def test_given_real_server_factory_when_sdk_import_is_broken_then_stdio_fallback_remains_usable() -> None:
    try:
        import mcp  # noqa: F401
    except ImportError:
        server = create_server()
        assert isinstance(server, FallbackMCP)
        tool_names = {tool.name for tool in asyncio.run(server.list_tools())}
        assert "ask_brazilian_soccer" in tool_names
        return

    server = create_server()
    tool_names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert "ask_brazilian_soccer" in tool_names


def test_given_fallback_server_when_client_uses_stdio_protocol_then_initialize_list_and_call_work() -> None:
    if not isinstance(create_server(), FallbackMCP):
        pytest.skip("The official SDK is installed; its own transport implementation is used instead.")

    process = subprocess.Popen(
        [sys.executable, "-m", "brazilian_soccer_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    try:
        def request(request_id: int, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
            process.stdin.write(
                json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
                + "\n"
            )
            process.stdin.flush()
            line = process.stdout.readline()
            assert line
            return json.loads(line)

        initialized = request(1, "initialize", {"protocolVersion": "2024-11-05"})
        assert initialized["result"]["serverInfo"]["name"] == "Brazilian Soccer Knowledge Graph"
        tools = request(2, "tools/list")
        names = {tool["name"] for tool in tools["result"]["tools"]}
        assert "search_matches" in names
        answer = request(3, "tools/call", {"name": "ask_brazilian_soccer", "arguments": {"question": "Who is L. Messi?"}})
        assert answer["result"]["structuredContent"]["intent"] == "search_players"
    finally:
        process.stdin.close()
        process.wait(timeout=10)
