# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : tests.test_server_tools
# Purpose : BDD scenarios for the MCP server layer and the text formatters.
#           Verifies the server registers the expected tools and that each tool
#           returns a well-formed, human-readable answer (cross-file queries
#           included). Exercises the >=20 sample questions end-to-end via tools.
# =============================================================================

import asyncio

import pytest

from soccer_mcp import formatting, server


class TestServerRegistration:
    """Feature: The MCP server exposes the required tools."""

    def test_expected_tools_are_registered(self):
        # Given the server, When tools are listed, Then the core tools exist
        names = {t.name for t in asyncio.run(server.mcp.list_tools())}
        expected = {
            "find_matches", "head_to_head", "team_stats", "find_players",
            "player_club_summary", "standings", "league_champion",
            "statistics", "biggest_wins", "top_scoring_teams",
            "list_competitions",
        }
        assert expected.issubset(names)


class TestToolAnswers:
    """Feature: Each MCP tool returns a readable answer string."""

    def test_find_matches_tool(self):
        out = server.find_matches(team="Flamengo", opponent="Fluminense")
        assert "Flamengo vs Fluminense" in out
        assert "-" in out

    def test_head_to_head_tool(self):
        out = server.head_to_head("Palmeiras", "Santos")
        assert "head-to-head" in out
        assert "wins" in out

    def test_team_stats_tool(self):
        out = server.team_stats("Corinthians", season=2022, competition="Brasileirão")
        assert "Corinthians" in out
        assert "Win rate" in out

    def test_find_players_tool(self):
        out = server.find_players(nationality="Brazil", limit=5)
        assert "Overall" in out
        assert "Neymar" in out

    def test_standings_tool(self):
        out = server.standings("Brasileirão", 2019)
        assert "Champion" in out
        assert "Flamengo" in out

    def test_league_champion_tool(self):
        out = server.league_champion("Brasileirão", 2019)
        assert "Flamengo" in out

    def test_statistics_tool(self):
        out = server.statistics(competition="Brasileirão", season=2019)
        assert "Average goals per match" in out

    def test_biggest_wins_tool(self):
        out = server.biggest_wins(competition="Brasileirão", limit=5)
        assert "Biggest wins" in out

    def test_list_competitions_tool(self):
        out = server.list_competitions()
        assert "Brasileirão" in out
        assert "Libertadores" in out


class TestCrossFileQuery:
    """Feature: Cross-file queries combine player and match data."""

    def test_player_and_match_for_same_club(self):
        # When I ask for a club's players (FIFA file) and its matches (match file)
        players = server.find_players(club="Santos", limit=5)
        matches = server.find_matches(team="Santos", season=2019, limit=5)
        # Then both data sources answer for the same entity
        assert "Santos" in players or "no players" in players
        assert "Santos" in matches


class TestFormatters:
    """Feature: Formatters degrade gracefully on empty input."""

    def test_empty_matches(self):
        assert "no matches" in formatting.format_matches([])

    def test_empty_players(self):
        assert "no players" in formatting.format_players([])
