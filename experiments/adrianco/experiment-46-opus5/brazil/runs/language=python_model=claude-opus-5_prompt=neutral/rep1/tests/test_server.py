"""Feature: The MCP server surface.

  Scenario: An MCP client lists and calls the tools
    Given the server is configured
    When the tool list is requested
    Then every documented tool is advertised with a schema
    And calling one returns readable text rather than raw data
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("mcp.server.fastmcp", reason="the MCP SDK is not installed")

from brazilian_soccer import server  # noqa: E402

EXPECTED_TOOLS = {
    "search_matches", "last_meeting", "head_to_head", "derbies",
    "team_statistics", "team_profile", "compare_teams", "home_away_split",
    "find_teams", "search_players", "player_profile", "club_squad",
    "players_by_club", "standings", "competition_summary", "knockout_bracket",
    "list_competitions", "biggest_wins", "team_rankings", "compare_seasons",
    "dataset_statistics",
}


@pytest.fixture(scope="module", autouse=True)
def loaded_server(request):
    """Point the server at the real data and warm the graph once."""
    server.get_graph()
    return server


class TestToolRegistration:

    def test_all_tools_are_advertised(self):
        """
        Given an MCP client connecting to the server
        When it lists the tools
        Then every capability in the specification is present
        """
        tools = asyncio.run(server.mcp.list_tools())
        names = {tool.name for tool in tools}

        assert EXPECTED_TOOLS <= names

    def test_tools_document_their_arguments(self):
        """
        Given tools an LLM has to call unaided
        When their schemas are inspected
        Then each has a description and typed parameters
        """
        tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
        search = tools["search_matches"]

        assert search.description
        assert "team" in search.inputSchema["properties"]
        assert "season" in search.inputSchema["properties"]
        for tool in tools.values():
            assert tool.description, tool.name

    def test_resources_are_registered(self):
        resources = asyncio.run(server.mcp.list_resources())
        uris = {str(resource.uri) for resource in resources}

        assert {"soccer://overview", "soccer://teams"} <= uris


class TestToolBehaviour:

    def test_tools_return_readable_text(self):
        """
        Given a tool call an LLM would make
        When it runs
        Then it returns text a model can quote directly
        """
        text = server.standings(competition="Brasileirão", season=2019)

        assert isinstance(text, str)
        assert "Flamengo" in text and "Champion" in text

    def test_match_search_tool(self):
        text = server.search_matches(team="Flamengo", opponent="Fluminense",
                                     limit=5)

        assert "Flamengo vs Fluminense" in text
        assert text.count("\n- ") >= 5

    def test_player_tools(self):
        text = server.search_players(nationality="Brazil", limit=3)

        assert "Neymar" in text
        assert "Overall:" in text

    def test_unknown_team_returns_guidance_not_an_exception(self):
        """
        Given an LLM guessing a club name
        When the club does not exist
        Then the tool answers with an explanation instead of raising
        """
        text = server.team_statistics(team="Sporting Lisbon")

        assert "No team matching" in text

    def test_unknown_competition_returns_guidance(self):
        text = server.standings(competition="La Liga", season=2019)

        assert "Unknown competition" in text

    def test_invalid_metric_returns_guidance(self):
        text = server.team_rankings(metric="magic")

        assert "Cannot answer that" in text

    def test_resource_bodies_are_populated(self):
        overview = server.overview_resource()
        teams = server.teams_resource()

        assert "Competitions:" in overview
        assert "Flamengo" in teams

    def test_graph_is_shared_between_tools(self):
        assert server.get_graph() is server.get_graph()


class TestEdgeCases:
    """Feature: Odd arguments produce an answer, never a stack trace."""

    @pytest.mark.parametrize(
        "call, marker",
        [
            (lambda: server.search_matches(team="Flamengo", season=-5),
             "No matches found"),
            (lambda: server.standings(competition="Brasileirão", season=0),
             "no table can be calculated"),
            (lambda: server.biggest_wins(limit=0), "no matches in the dataset"),
            (lambda: server.team_rankings(min_matches=100_000),
             "no clubs meet that filter"),
            (lambda: server.compare_seasons(competition="Brasileirão", seasons=[]),
             "no seasons given"),
            (lambda: server.derbies(season=1999), "No derby matches"),
            (lambda: server.find_teams(query="ZZZZ"), "No clubs matching"),
            (lambda: server.knockout_bracket(competition="Copa do Brasil",
                                             season=1800), "in the dataset"),
            (lambda: server.head_to_head(team_a="Santos", team_b="Santos"),
             "two different teams"),
            (lambda: server.club_squad(club="zzzz"), "No FIFA player records"),
        ],
    )
    def test_empty_and_invalid_inputs_are_explained(self, call, marker):
        """
        Given an empty result or an impossible argument
        When the tool runs
        Then the answer explains the situation in words
        """
        text = call()

        assert marker in text

    def test_blank_team_name_does_not_suggest_random_clubs(self):
        """
        Given a blank club name
        When it fails to resolve
        Then the answer does not pad itself out with unrelated suggestions
        """
        text = server.team_statistics(team="   ")

        assert "No team matching" in text
        assert "Did you mean" not in text
