import asyncio
import pytest


EXPECTED_TOOLS = {
    "find_matches",
    "head_to_head",
    "get_team_stats",
    "find_players",
    "get_standings",
    "get_biggest_wins",
    "competition_averages",
}


@pytest.fixture(scope="module")
def mcp_server():
    """Import the FastMCP server instance from server.py."""
    import server as srv
    return srv.mcp


def test_server_has_list_tools_method(mcp_server):
    assert hasattr(mcp_server, "list_tools"), "Server must have a list_tools method"
    assert callable(mcp_server.list_tools)


def test_all_seven_tools_registered(mcp_server):
    tools = asyncio.run(mcp_server.list_tools())
    registered = {t.name for t in tools}
    for tool_name in EXPECTED_TOOLS:
        assert tool_name in registered, f"Tool '{tool_name}' not registered"


def test_no_extra_tools(mcp_server):
    tools = asyncio.run(mcp_server.list_tools())
    registered = {t.name for t in tools}
    assert registered == EXPECTED_TOOLS, (
        f"Extra or missing tools. Expected: {EXPECTED_TOOLS}, Got: {registered}"
    )
