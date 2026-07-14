"""BDD: MCP server wiring.

Feature: MCP tool surface
  Scenario: The server lists tools and dispatches them to the query layer
    Given a constructed MCP server
    When  a tool is invoked through the dispatcher
    Then  the result matches a direct query-layer call
"""

from __future__ import annotations

from brazilian_soccer_mcp import queries
from brazilian_soccer_mcp.server import (
    _TOOL_DISPATCH,
    _tool_definitions,
    build_server,
    dispatch_tool,
)


def test_all_tools_have_definitions():
    # Given the tool registry
    defs = {t.name for t in _tool_definitions()}
    handlers = set(_TOOL_DISPATCH.keys())
    # Then every advertised tool has a handler and vice versa
    assert defs == handlers


def test_dispatch_champion_matches_direct_call(dataset):
    # Given a dataset
    # When  we call the champion tool via dispatch
    via_tool = dispatch_tool(
        dataset, "champion", {"competition": "Brasileirão", "season": 2019}
    )
    # Then  it returns the same payload as the direct query function
    direct = queries.champion(dataset, "Brasileirão", 2019)
    assert via_tool == direct
    assert via_tool["team"] == "flamengo"


def test_dispatch_unknown_tool_raises(dataset):
    # Given an unknown tool name
    # When  we dispatch
    try:
        dispatch_tool(dataset, "does_not_exist", {})
    except ValueError as exc:
        assert "unknown tool" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown tool")


def test_build_server_constructs_without_errors(dataset):
    # Given the dataset is already loaded
    # When  we build the MCP Server
    server, ds = build_server(dataset)
    # Then  it has the expected name and reuses the supplied dataset
    assert server.name == "brazilian-soccer-mcp"
    assert ds is dataset


def test_find_matches_tool_returns_dicts(dataset):
    # Given the dataset
    # When  we ask via dispatch for matches between two teams with a limit
    rows = dispatch_tool(
        dataset,
        "find_matches",
        {"team": "Flamengo", "opponent": "Palmeiras", "limit": 5},
    )
    # Then  we get up to five plain-dict matches
    assert isinstance(rows, list)
    assert 0 < len(rows) <= 5
    for r in rows:
        assert isinstance(r, dict)
        assert "competition" in r and "date" in r
