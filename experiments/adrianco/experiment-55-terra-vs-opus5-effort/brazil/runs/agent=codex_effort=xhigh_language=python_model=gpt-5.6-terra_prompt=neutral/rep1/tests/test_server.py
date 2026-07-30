"""Tests for MCP tool registration without requiring an external MCP runtime."""

from __future__ import annotations

import sys
from types import ModuleType

from soccer_mcp.server import create_mcp_server


class _FakeFastMCP:
    def __init__(self, name: str, instructions: str) -> None:
        self.name = name
        self.instructions = instructions
        self.tools: dict[str, object] = {}

    def tool(self):  # type: ignore[no-untyped-def]
        def register(function):  # type: ignore[no-untyped-def]
            self.tools[function.__name__] = function
            return function

        return register


def test_mcp_adapter_registers_all_query_tools(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    mcp_module = ModuleType("mcp")
    server_module = ModuleType("mcp.server")
    fastmcp_module = ModuleType("mcp.server.fastmcp")
    fastmcp_module.FastMCP = _FakeFastMCP  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_module)

    server = create_mcp_server()

    assert server.name == "Brazilian Soccer"
    assert set(server.tools) == {
        "data_summary", "search_matches", "team_statistics", "head_to_head", "team_overview",
        "competition_standings", "competition_statistics", "search_players", "answer_question",
    }
    assert server.tools["search_matches"](team="Flamengo", limit=1)["returned"] == 1
