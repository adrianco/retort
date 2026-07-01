"""Tests for the MCP server tools — red/green/refactor cycle."""
import json
import pytest
from server import create_server


@pytest.fixture(scope="module")
def mcp_server():
    return create_server("data/kaggle")


# ------------------------------------------------------------------ server creation

def test_server_is_created(mcp_server):
    assert mcp_server is not None


def test_server_has_name(mcp_server):
    assert mcp_server.name == "brazilian-soccer"


# ------------------------------------------------------------------ tool listing

def test_server_exposes_tools(mcp_server):
    tools = mcp_server._tool_manager.list_tools()
    tool_names = [t.name for t in tools]
    assert len(tool_names) > 0


def test_search_matches_tool_exists(mcp_server):
    tools = mcp_server._tool_manager.list_tools()
    names = [t.name for t in tools]
    assert "search_matches" in names


def test_get_team_stats_tool_exists(mcp_server):
    tools = mcp_server._tool_manager.list_tools()
    names = [t.name for t in tools]
    assert "get_team_stats" in names


def test_search_players_tool_exists(mcp_server):
    tools = mcp_server._tool_manager.list_tools()
    names = [t.name for t in tools]
    assert "search_players" in names


def test_get_head_to_head_tool_exists(mcp_server):
    tools = mcp_server._tool_manager.list_tools()
    names = [t.name for t in tools]
    assert "get_head_to_head" in names


def test_get_standings_tool_exists(mcp_server):
    tools = mcp_server._tool_manager.list_tools()
    names = [t.name for t in tools]
    assert "get_standings" in names


def test_get_biggest_wins_tool_exists(mcp_server):
    tools = mcp_server._tool_manager.list_tools()
    names = [t.name for t in tools]
    assert "get_biggest_wins" in names


# ------------------------------------------------------------------ tool call integration

@pytest.mark.anyio
async def test_search_matches_tool_returns_json(mcp_server):
    result = await mcp_server._tool_manager.call_tool("search_matches", {"team": "Flamengo", "limit": 5})
    data = json.loads(result)
    assert isinstance(data, list)
    assert len(data) <= 5


@pytest.mark.anyio
async def test_get_team_stats_tool_returns_json(mcp_server):
    result = await mcp_server._tool_manager.call_tool("get_team_stats", {"team": "Santos"})
    data = json.loads(result)
    assert "matches" in data
    assert data["matches"] > 0


@pytest.mark.anyio
async def test_search_players_tool_returns_json(mcp_server):
    result = await mcp_server._tool_manager.call_tool("search_players", {"name": "Neymar"})
    data = json.loads(result)
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.anyio
async def test_get_head_to_head_tool_returns_json(mcp_server):
    result = await mcp_server._tool_manager.call_tool(
        "get_head_to_head", {"team1": "Flamengo", "team2": "Fluminense"}
    )
    data = json.loads(result)
    assert "total_matches" in data
    assert data["total_matches"] > 0


@pytest.mark.anyio
async def test_get_standings_tool_returns_json(mcp_server):
    result = await mcp_server._tool_manager.call_tool("get_standings", {"season": 2019})
    data = json.loads(result)
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.anyio
async def test_get_biggest_wins_tool_returns_json(mcp_server):
    result = await mcp_server._tool_manager.call_tool("get_biggest_wins", {"limit": 5})
    data = json.loads(result)
    assert isinstance(data, list)
    assert len(data) <= 5
