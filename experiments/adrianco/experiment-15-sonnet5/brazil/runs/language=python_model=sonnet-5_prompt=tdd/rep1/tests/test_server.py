import asyncio
import math

import pytest

from brazilian_soccer_mcp.server import _match_line, mcp


def call_tool(name: str, arguments: dict) -> str:
    async def _run():
        content, _structured = await mcp.call_tool(name, arguments)
        return "\n".join(block.text for block in content if hasattr(block, "text"))

    return asyncio.run(_run())


def test_lists_expected_tools():
    async def _run():
        return await mcp.list_tools()

    tools = asyncio.run(_run())
    names = {t.name for t in tools}
    expected = {
        "find_matches", "head_to_head", "team_record", "standings",
        "biggest_wins", "average_goals_per_match", "home_win_rate",
        "search_players", "top_players",
    }
    assert expected.issubset(names)


def test_find_matches_tool_returns_readable_text():
    text = call_tool("find_matches", {"team": "Flamengo", "opponent": "Fluminense"})
    assert "Flamengo" in text
    assert "Fluminense" in text


def test_head_to_head_tool_reports_record():
    text = call_tool("head_to_head", {"team_a": "Palmeiras", "team_b": "Santos"})
    assert "Palmeiras" in text and "Santos" in text
    assert "wins" in text.lower()


def test_standings_tool_reports_2019_champion():
    text = call_tool("standings", {"competition": "Brasileirao", "season": 2019})
    lines = text.strip().splitlines()
    assert "Flamengo" in lines[0]


def test_team_record_tool_reports_stats():
    text = call_tool("team_record", {"team": "Corinthians", "competition": "Brasileirao", "season": 2022})
    assert "Corinthians" in text
    assert "Wins" in text


def test_search_players_tool_finds_messi():
    text = call_tool("search_players", {"name": "Messi"})
    assert "Messi" in text
    assert "Argentina" in text


def test_top_players_tool_ranks_by_overall():
    text = call_tool("top_players", {"nationality": "Brazil", "n": 3})
    assert "Neymar" in text


def test_biggest_wins_tool_returns_results():
    text = call_tool("biggest_wins", {"n": 3})
    assert text.strip() != ""


def test_match_line_handles_missing_scores():
    match = {
        "date": "2020-06-01", "home_team_display": "Cuiaba", "away_team_display": "Flamengo",
        "home_goal": math.nan, "away_goal": math.nan, "competition": "Brasileirao",
    }
    line = _match_line(match)
    assert "Cuiaba" in line and "Flamengo" in line
    assert "nan" not in line.lower()


def test_find_matches_tool_does_not_crash_on_missing_scores():
    text = call_tool("find_matches", {"team": "Palmeiras"})
    assert text.strip() != ""


def test_average_goals_tool_returns_number():
    text = call_tool("average_goals_per_match", {"competition": "Brasileirao"})
    assert any(ch.isdigit() for ch in text)
