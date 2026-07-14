"""
================================================================================
Feature: Competition Queries
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Gherkin scenarios: standings calculated from match results, champions, and
season/competition listings. Verified against real historical results.
================================================================================
"""

from data_loader import SERIE_A


class TestStandings:
    """Scenario: Who won the 2019 Brasileirão?"""

    def test_2019_champion_is_flamengo_with_90_points(self, graph):
        # Given the 2019 Série A match data
        # When standings are computed (3 pts win, 1 draw)
        table = graph.standings(SERIE_A, 2019)
        # Then Flamengo are champions with the historically correct 90 points
        assert table[0]["team"].lower().startswith("flamengo")
        assert table[0]["points"] == 90
        assert (table[0]["wins"], table[0]["draws"], table[0]["losses"]) == (28, 6, 4)

    def test_2022_champion_is_palmeiras(self, graph):
        # Scenario: Who won the 2022 Brasileirão? -> Palmeiras
        table = graph.standings(SERIE_A, 2022)
        assert table[0]["team"].lower().startswith("palmeiras")

    def test_table_is_20_teams_ranked_by_points(self, graph):
        table = graph.standings(SERIE_A, 2020)
        # Then there are 20 teams, positions 1..20, sorted by points desc
        assert len(table) == 20
        assert [r["position"] for r in table] == list(range(1, 21))
        pts = [r["points"] for r in table]
        assert pts == sorted(pts, reverse=True)

    def test_points_match_results(self, graph):
        # Then each row's points equal 3*wins + draws
        for r in graph.standings(SERIE_A, 2021):
            assert r["points"] == r["wins"] * 3 + r["draws"]
            assert r["played"] == r["wins"] + r["draws"] + r["losses"]


class TestChampion:
    def test_champion_helper_matches_table_top(self, graph):
        champ = graph.champion(SERIE_A, 2019)
        assert champ["position"] == 1
        assert champ["team"].lower().startswith("flamengo")


class TestListings:
    def test_list_competitions(self, graph):
        comps = graph.list_competitions()
        assert SERIE_A in comps
        assert len(comps) == 5

    def test_list_seasons_ascending(self, graph):
        seasons = graph.list_seasons(SERIE_A)
        assert seasons == sorted(seasons)
        assert 2019 in seasons and 2003 in seasons
