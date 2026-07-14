"""
================================================================================
tests.test_competition_queries
================================================================================

CONTEXT
-------
BDD scenarios for Required Capability #4 (Competition Queries): standings
computed from match results, champions and relegation. Includes the well-known
2019 Brasileirão as a ground-truth check ("Who won the 2019 Brasileirão?").
================================================================================
"""


class TestCompetitionQueries:
    """Feature: Competition Queries."""

    def test_standings_are_well_formed(self, kg):
        # When I compute the 2019 Brasileirão table
        table = kg.standings("Brasileirão Série A", 2019)
        # Then it has 20 teams, ranked, with points consistent with W/D/L
        assert len(table) == 20
        assert [t["position"] for t in table] == list(range(1, 21))
        for t in table:
            assert t["points"] == t["wins"] * 3 + t["draws"]
            assert t["played"] == t["wins"] + t["draws"] + t["losses"]
        # And points are in non-increasing order
        pts = [t["points"] for t in table]
        assert pts == sorted(pts, reverse=True)

    def test_2019_brasileirao_champion_is_flamengo(self, kg):
        # Scenario: "Who won the 2019 Brasileirão?"
        champ = kg.champion("Brasileirão Série A", 2019)
        # Then Flamengo are champions with the historically correct 90 points
        assert champ["team"] == "Flamengo"
        assert champ["points"] == 90
        assert (champ["wins"], champ["draws"], champ["losses"]) == (28, 6, 4)

    def test_2019_relegation_zone(self, kg):
        # Scenario: "Which teams were relegated in 2019?"
        relegated = {t["team"] for t in kg.relegated("Brasileirão Série A", 2019)}
        # Then the four historically relegated clubs are present
        assert {"Cruzeiro", "Chapecoense", "CSA", "Avaí"} == relegated

    def test_champion_matches_top_of_standings(self, kg):
        table = kg.standings("Brasileirão Série A", 2018)
        champ = kg.champion("Brasileirão Série A", 2018)
        assert champ["team"] == table[0]["team"]

    def test_standings_empty_for_unknown_season(self, kg):
        assert kg.standings("Brasileirão Série A", 1900) == []
