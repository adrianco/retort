import asyncio
import sys
from pathlib import Path

import server
from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_TOOLS = {
    "dataset_info", "find_team", "search_matches", "head_to_head", "team_record", "team_overview", "team_trend",
    "standings", "team_rankings", "competition_stats", "compare_seasons", "biggest_wins", "knockout_results",
    "derby_matches", "search_players", "player_profile", "player_club_summary",
}


def _run(coro):
    return asyncio.run(coro)


def test_tools_are_listed_with_descriptions_and_schemas():
    async def go():
        async with Client(server.mcp) as c:
            return (await c.list_tools()).tools
    tools = _run(go())
    assert {t.name for t in tools} == EXPECTED_TOOLS
    for t in tools:
        assert t.description and t.input_schema["type"] == "object"
    schema = next(t for t in tools if t.name == "head_to_head").input_schema
    assert set(schema["required"]) == {"team_a", "team_b"}


def test_invalid_input_returns_tool_error():
    async def go():
        async with Client(server.mcp) as c:
            unknown = await c.call_tool("team_record", {"team": "Zzzz Qqqq United"})
            bad_comp = await c.call_tool("standings", {"season": 2019, "competition": "Bundesliga"})
            bad_type = await c.call_tool("standings", {"season": "not a year"})
            return unknown, bad_comp, bad_type
    unknown, bad_comp, bad_type = _run(go())
    assert unknown.is_error and "not found" in unknown.content[0].text
    assert bad_comp.is_error and "Unknown competition" in bad_comp.content[0].text
    assert bad_type.is_error


def test_dataset_resource():
    async def go():
        async with Client(server.mcp) as c:
            return await c.read_resource("soccer://dataset-info")
    res = _run(go())
    assert "Brazilian soccer knowledge base" in res.contents[0].text


def test_stdio_transport_end_to_end():
    """Launch `python server.py` as a subprocess and talk MCP over stdio."""
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=str(ROOT))

    async def go():
        async with Client(params) as c:
            tools = await c.list_tools()
            res = await c.call_tool("standings", {"season": 2019, "top": 1})
            return tools, res
    tools, res = _run(go())
    assert len(tools.tools) == len(EXPECTED_TOOLS)
    assert "1. Flamengo - 90 pts" in res.content[0].text
