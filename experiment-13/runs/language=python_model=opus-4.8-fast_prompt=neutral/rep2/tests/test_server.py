"""
Context
=======
Tests for bsoccer.server (the MCP layer) and bsoccer.format. Confirms the MCP
tools are registered, return the dual text+data shape, and that the formatters
render the structured results into the prose shapes shown in the spec.
"""

import asyncio

import pytest

import bsoccer.format as fmt
from bsoccer import server


def test_tools_registered():
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "find_matches", "team_record", "head_to_head", "search_players",
        "players_by_club", "standings", "champion", "list_seasons",
        "competition_stats", "biggest_wins", "top_scoring_teams",
    }
    assert expected <= names


def test_find_matches_tool_shape():
    out = server.find_matches(team="Flamengo", opponent="Fluminense", limit=5)
    assert set(out) == {"text", "data"}
    assert isinstance(out["text"], str)
    assert out["data"]["count"] > 0


def test_champion_tool():
    out = server.champion(competition="Brasileirão", season=2019)
    assert "Flamengo" in out["text"]
    assert out["data"]["champion"] == "Flamengo"


def test_search_players_tool():
    out = server.search_players(name="Neymar", limit=3)
    assert out["data"]["count"] >= 1
    assert "Neymar" in out["text"]


# ----- formatter unit tests ----------------------------------------------

def test_format_matches_empty():
    assert fmt.format_matches({"count": 0, "matches": []}) == "No matches found."


def test_format_matches_error():
    assert fmt.format_matches({"error": "boom"}) == "boom"


def test_format_record():
    rec = {
        "team": "Corinthians", "matches": 19, "wins": 11, "draws": 5,
        "losses": 3, "goals_for": 28, "goals_against": 15,
        "goal_difference": 13, "points": 38, "win_rate": 57.9,
        "competition": "Brasileirão", "season": 2022, "venue": "home",
    }
    text = fmt.format_record(rec)
    assert "Corinthians" in text
    assert "Wins: 11" in text
    assert "57.9%" in text


def test_format_standings():
    result = {
        "competition": "Brasileirão", "season": 2019,
        "table": [{"position": 1, "team": "Flamengo", "points": 90,
                   "wins": 28, "draws": 6, "losses": 4,
                   "goals_for": 86, "goals_against": 37}],
    }
    text = fmt.format_standings(result)
    assert "2019 Brasileirão" in text
    assert "1. Flamengo - 90 pts" in text
