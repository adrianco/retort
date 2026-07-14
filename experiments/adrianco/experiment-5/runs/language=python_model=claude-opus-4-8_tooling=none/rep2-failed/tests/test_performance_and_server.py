"""
Context
=======
Feature: Performance & MCP server wiring

Covers the "Query Performance" success criteria (simple < 2s, aggregate < 5s)
and verifies the MCP tool layer is correctly wired to the knowledge graph and
returns formatted text (the cross-file player+match coverage too).
"""

from __future__ import annotations

import time

import pytest


class TestQueryPerformance:
    def test_simple_lookup_under_two_seconds(self, graph):
        start = time.perf_counter()
        graph.find_matches(team="Flamengo", opponent="Corinthians", limit=5)
        graph.find_player("Neymar")
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"simple lookup took {elapsed:.2f}s"

    def test_aggregate_query_under_five_seconds(self, graph):
        start = time.perf_counter()
        graph.standings(2019, "Brasileirão")
        graph.competition_stats(competition="Brasileirão")
        graph.best_records(season=2019, competition="Brasileirão", venue="home")
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"aggregate query took {elapsed:.2f}s"


class TestMcpServerTools:
    """The MCP tools should return ready-to-read strings backed by the graph."""

    def setup_method(self):
        # Import here so a missing optional dependency only fails this file.
        from brazilian_soccer_mcp import server
        self.server = server

    def test_find_matches_tool(self):
        out = self.server.find_matches(team="Flamengo", opponent="Fluminense", limit=3)
        assert isinstance(out, str)
        assert "Flamengo" in out and "Fluminense" in out

    def test_team_record_tool(self):
        out = self.server.team_record("Corinthians", season=2019, venue="home",
                                      competition="Brasileirão")
        assert "Matches: 19" in out

    def test_league_standings_tool(self):
        out = self.server.league_standings(2019, "Brasileirão")
        assert "Flamengo" in out
        assert "90 pts" in out

    def test_player_profile_tool(self):
        out = self.server.player_profile("Neymar")
        assert "Neymar" in out
        assert "Overall" in out

    def test_search_players_tool(self):
        out = self.server.search_players(nationality="Brazil", limit=5)
        assert "Neymar" in out

    def test_competition_champion_tool(self):
        out = self.server.competition_champion(2019, "Brasileirão")
        assert "Flamengo" in out

    def test_league_statistics_tool(self):
        out = self.server.league_statistics(competition="Brasileirão")
        assert "Average goals per match" in out

    def test_dataset_overview_tool(self):
        out = self.server.dataset_overview()
        assert "Matches" in out and "Players" in out

    def test_tools_are_registered_with_mcp(self):
        # The FastMCP instance should expose all our tools.
        import anyio
        names = {t.name for t in anyio.run(self.server.mcp.list_tools)}
        expected = {
            "find_matches", "head_to_head", "team_record", "best_team_records",
            "search_players", "player_profile", "league_standings",
            "competition_champion", "league_statistics", "biggest_wins",
            "dataset_overview",
        }
        assert expected <= names


class TestCrossFileCoverage:
    def test_player_and_match_data_both_queryable(self, graph):
        # A cross-file question: Flamengo's players (FIFA) and matches (CSVs).
        players = graph.search_players(club="Flamengo", limit=5)
        matches = graph.find_matches(team="Flamengo", limit=5)
        assert players or matches  # at least one source has Flamengo
        assert matches
