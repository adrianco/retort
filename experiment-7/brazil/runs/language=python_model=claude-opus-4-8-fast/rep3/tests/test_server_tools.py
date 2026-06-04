"""
================================================================================
Context
================================================================================
Test module: test_server_tools.py
Project:     Brazilian Soccer MCP Server
Feature:     The MCP tool layer end-to-end, plus the spec's "at least 20 sample
             questions can be answered" coverage requirement.
Style:       BDD Given-When-Then.

Each sample question is exercised through the same tool functions the MCP server
exposes, asserting a sensible, non-empty, correctly-shaped answer comes back.
================================================================================
"""

import pytest

import server


@pytest.fixture(scope="module", autouse=True)
def _warm_graph():
    # Given the server's knowledge graph is loaded once
    server.get_graph()


class TestServerConstruction:
    def test_mcp_app_builds_with_all_tools(self):
        # Given the mcp package is installed
        # When the server app is built
        # Then it exists and is named
        assert server.mcp is not None
        assert server.mcp.name == "brazilian-soccer"


class TestSampleQuestions:
    """Twenty+ natural-language sample questions mapped to tool calls."""

    def test_q01_when_did_flamengo_last_play_corinthians(self):
        out = server.tool_find_matches(team="Flamengo", opponent="Corinthians", limit=1)
        assert "Flamengo" in out and "Corinthians" in out

    def test_q02_flamengo_vs_fluminense_matches(self):
        out = server.tool_head_to_head("Flamengo", "Fluminense")
        assert "head-to-head" in out and "wins" in out

    def test_q03_what_matches_did_palmeiras_play_in_2019(self):
        out = server.tool_find_matches(team="Palmeiras", season=2019, competition="brasileirao")
        assert "Palmeiras" in out

    def test_q04_copa_do_brasil_matches(self):
        out = server.tool_find_matches(competition="Copa do Brasil", season=2019, limit=5)
        assert "Copa do Brasil" in out

    def test_q05_corinthians_home_record_2022(self):
        out = server.tool_team_record("Corinthians", season=2022,
                                      competition="brasileirao", venue="home")
        assert "home record" in out and "Win rate" in out

    def test_q06_team_with_most_goals_serie_a_2019(self):
        out = server.tool_best_record(venue="either", competition="brasileirao",
                                      season=2019, limit=5)
        assert "win rate" in out

    def test_q07_compare_palmeiras_and_santos(self):
        out = server.tool_compare_teams("Palmeiras", "Santos")
        assert "Palmeiras" in out and "Santos" in out

    def test_q08_find_all_brazilian_players(self):
        out = server.tool_search_players(nationality="Brazil", limit=10)
        assert "Brazil" in out

    def test_q09_highest_rated_players_at_flamengo(self):
        out = server.tool_top_players(club="Flamengo", limit=5)
        assert "Top-rated players" in out

    def test_q10_who_is_neymar(self):
        out = server.tool_search_players(name="Neymar", limit=1)
        assert "Neymar" in out

    def test_q11_who_won_2019_brasileirao(self):
        out = server.tool_season_champion("brasileirao", 2019)
        assert "Flamengo" in out and "90 pts" in out

    def test_q12_2019_brasileirao_standings(self):
        out = server.tool_standings("brasileirao", 2019, limit=5)
        assert "Champion" in out and "Flamengo" in out

    def test_q13_average_goals_per_match(self):
        out = server.tool_average_goals("brasileirao")
        assert "Average goals per match" in out

    def test_q14_best_away_record(self):
        out = server.tool_best_record(venue="away", competition="brasileirao",
                                      season=2019, limit=5)
        assert "away" in out

    def test_q15_biggest_wins(self):
        out = server.tool_biggest_wins(limit=5)
        assert "Biggest victories" in out

    def test_q16_libertadores_matches_for_flamengo(self):
        out = server.tool_find_matches(team="Flamengo", competition="libertadores", limit=5)
        assert "Libertadores" in out

    def test_q17_top_brazilian_players(self):
        out = server.tool_top_players(nationality="Brazil", limit=5)
        assert "Neymar" in out

    def test_q18_forwards_search(self):
        out = server.tool_search_players(nationality="Brazil", position="ST", limit=5)
        assert "Players" in out

    def test_q19_list_seasons(self):
        out = server.tool_list_seasons("brasileirao")
        assert "2019" in out and "2003" in out

    def test_q20_list_competitions(self):
        out = server.tool_list_competitions()
        assert "Copa Libertadores" in out

    def test_q21_palmeiras_vs_santos_head_to_head(self):
        out = server.tool_head_to_head("Palmeiras", "Santos")
        assert "Palmeiras" in out and "Santos" in out

    def test_q22_historic_2010_champion(self):
        out = server.tool_season_champion("brasileirao", 2010)
        assert "Fluminense" in out


class TestGracefulEmptyResults:
    def test_unknown_team_returns_friendly_message(self):
        out = server.tool_head_to_head("Nonexistent FC", "Phantom United")
        assert "No matches found" in out

    def test_unknown_player_returns_friendly_message(self):
        out = server.tool_search_players(name="Zzzzqqq Noname", limit=5)
        assert "No players found" in out
