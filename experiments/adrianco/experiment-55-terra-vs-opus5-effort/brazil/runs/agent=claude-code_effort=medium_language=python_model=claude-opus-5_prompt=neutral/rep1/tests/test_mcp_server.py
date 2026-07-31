"""Feature: The MCP tool surface.

Context
-------
Drives the server the way an MCP client would: list the tools, check their
schemas, then call each one through ``call_tool`` and assert on the text the
LLM would receive.  Also covers the failure paths -- an unknown club must come
back as a "did you mean" sentence, never as a protocol error.

The MCP SDK is optional for the rest of the package, so the whole module skips
if it is not installed.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("mcp", reason="the MCP SDK is not installed")

from brazilian_soccer import server  # noqa: E402

EXPECTED_TOOLS = {
    "search_matches",
    "head_to_head",
    "last_meeting",
    "find_derbies",
    "team_statistics",
    "team_profile",
    "compare_teams",
    "team_season_trend",
    "search_teams",
    "search_players",
    "get_player",
    "club_squad",
    "players_by_club",
    "standings",
    "season_champion",
    "relegated_teams",
    "competition_bracket",
    "competition_statistics",
    "biggest_wins",
    "team_rankings",
    "compare_seasons",
    "dataset_overview",
}


def call(name: str, arguments: dict | None = None) -> str:
    """Invoke a tool through the MCP layer and return its text content."""
    result = asyncio.run(server.mcp.call_tool(name, arguments or {}))
    content = result.content if hasattr(result, "content") else result[0]
    if isinstance(content, list):
        return "\n".join(getattr(block, "text", str(block)) for block in content)
    return getattr(content, "text", str(content))


@pytest.fixture(scope="module")
def tools():
    return {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}


class TestToolRegistration:
    def test_every_capability_group_has_tools(self, tools) -> None:
        # Given the server is built
        # Then all documented tools are registered
        assert EXPECTED_TOOLS <= set(tools)

    def test_tools_are_documented(self, tools) -> None:
        for name in EXPECTED_TOOLS:
            assert tools[name].description, f"{name} has no description"

    def test_schemas_survive_the_error_guard(self, tools) -> None:
        # The @_guard decorator must not erase the real signature
        schema = tools["search_matches"].input_schema
        assert {"team", "opponent", "competition", "season", "venue"} <= set(
            schema["properties"]
        )
        assert tools["standings"].input_schema["required"] == ["season"]


class TestMatchTools:
    def test_search_matches(self) -> None:
        text = call("search_matches", {"team": "Flamengo", "season": 2019, "limit": 5})
        assert "Flamengo" in text
        assert "2019-" in text

    def test_head_to_head(self) -> None:
        text = call("head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"})
        assert "Head-to-head in dataset:" in text

    def test_last_meeting(self) -> None:
        text = call("last_meeting", {"team_a": "Flamengo", "team_b": "Corinthians"})
        assert "Most recent meeting:" in text

    def test_find_derbies(self) -> None:
        text = call("find_derbies", {"season": 2023, "limit": 5})
        assert "[" in text and "]" in text


class TestTeamTools:
    def test_team_statistics(self) -> None:
        text = call(
            "team_statistics",
            {
                "team": "Corinthians",
                "season": 2022,
                "competition": "Brasileirao",
                "venue": "home",
            },
        )
        assert "- Matches: 19" in text
        assert "Win rate:" in text

    def test_team_profile(self) -> None:
        text = call("team_profile", {"team": "Palmeiras"})
        assert "Competitions played:" in text
        assert "Copa Libertadores" in text

    def test_compare_teams(self) -> None:
        text = call("compare_teams", {"team_a": "Palmeiras", "team_b": "Santos"})
        assert "Comparison" in text
        assert "Head-to-head in dataset:" in text

    def test_team_season_trend(self) -> None:
        text = call("team_season_trend", {"team": "Flamengo", "competition": "Serie A"})
        assert "2019:" in text

    def test_search_teams(self) -> None:
        text = call("search_teams", {"query": "atletico"})
        assert "atletico-mg" in text and "atletico-pr" in text


class TestPlayerTools:
    def test_search_players_by_nationality(self) -> None:
        text = call("search_players", {"nationality": "Brazil", "limit": 5})
        assert "Neymar Jr" in text
        assert "Overall:" in text

    def test_get_player(self) -> None:
        text = call("get_player", {"name": "Neymar"})
        assert "Neymar Jr" in text
        assert "Top attributes:" in text

    def test_get_player_flags_inexact_matches(self) -> None:
        text = call("get_player", {"name": "Gabriel Barbosa"})
        assert "No exact match" in text
        assert "Closest match" in text

    def test_club_squad(self) -> None:
        text = call("club_squad", {"club": "Gremio", "limit": 5})
        assert "squad in the FIFA dataset" in text
        assert "average overall" in text

    def test_players_by_club(self) -> None:
        text = call("players_by_club", {"nationality": "Brazil", "limit": 3})
        assert "players:" in text


class TestCompetitionTools:
    def test_standings(self) -> None:
        text = call("standings", {"season": 2019})
        assert "1. Flamengo-RJ - 90 pts" in text
        assert "Champion" in text

    def test_season_champion(self) -> None:
        text = call("season_champion", {"season": 2019})
        assert "champion: Flamengo-RJ" in text

    def test_season_champion_for_a_cup(self) -> None:
        text = call(
            "season_champion", {"season": 2019, "competition": "Copa Libertadores"}
        )
        assert "Flamengo-RJ" in text

    def test_relegated_teams(self) -> None:
        text = call("relegated_teams", {"season": 2020})
        assert "relegation zone" in text.lower()
        assert "Botafogo-RJ" in text

    def test_competition_bracket(self) -> None:
        text = call(
            "competition_bracket", {"season": 2019, "competition": "Libertadores"}
        )
        assert "group stage" in text
        assert "final" in text


class TestStatisticsTools:
    def test_competition_statistics(self) -> None:
        text = call("competition_statistics", {"competition": "Brasileirao"})
        assert "Average goals per match:" in text

    def test_biggest_wins(self) -> None:
        text = call("biggest_wins", {"limit": 3})
        assert "Biggest victories" in text

    def test_team_rankings(self) -> None:
        text = call("team_rankings", {"venue": "away", "min_matches": 100, "limit": 5})
        assert "Top teams by points_per_game" in text

    def test_compare_seasons(self) -> None:
        text = call(
            "compare_seasons", {"seasons": [2018, 2019], "competition": "Brasileirao"}
        )
        assert text.count("Average goals per match:") == 2

    def test_dataset_overview(self) -> None:
        text = call("dataset_overview", {})
        assert "Matches (de-duplicated):" in text
        assert "duplicates merged across files" in text
        assert "no goal-scorer" in text


class TestErrorHandling:
    def test_unknown_team_returns_suggestions_not_an_error(self) -> None:
        text = call("team_statistics", {"team": "Flamngo"})
        assert "Flamengo" in text or "No team matching" in text

    def test_completely_unknown_team_is_reported(self) -> None:
        text = call("team_statistics", {"team": "Manchester United Reserves XI"})
        assert "No team matching" in text

    def test_unknown_competition_is_reported(self) -> None:
        text = call("standings", {"season": 2019, "competition": "Premier League"})
        assert "Unknown competition" in text

    def test_season_without_data_is_reported(self) -> None:
        text = call("standings", {"season": 1899})
        assert "No " in text
