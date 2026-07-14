"""BDD: the MCP server exposes working tools.

Skipped automatically if the ``mcp`` package is not installed (the core logic
is tested independently in the other modules).
"""

import pytest

pytest.importorskip("mcp")

from brazilian_soccer_mcp import server  # noqa: E402


def test_server_has_expected_tools():
    names = {t.name for t in server.mcp._tool_manager.list_tools()}
    expected = {
        "find_matches", "head_to_head", "team_record", "compare_teams",
        "standings", "champion", "match_statistics", "biggest_wins",
        "best_record", "search_players", "top_brazilian_players",
        "players_at_club",
    }
    assert expected.issubset(names)


def test_standings_tool_returns_text():
    out = server.standings("Brasileirão", 2019)
    assert isinstance(out, str)
    assert "Flamengo" in out
    assert "Champion" in out


def test_search_players_tool_returns_text():
    out = server.search_players(name="Neymar", limit=1)
    assert "Neymar" in out


def test_head_to_head_tool():
    out = server.head_to_head("Flamengo", "Fluminense")
    assert "Head-to-head" in out
