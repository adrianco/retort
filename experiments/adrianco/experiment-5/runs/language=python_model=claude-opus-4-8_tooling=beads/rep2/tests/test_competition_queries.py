"""
================================================================================
test_competition_queries.py - BDD scenarios for standings & champions
================================================================================

Feature: Competition Queries
  Scenario: Compute final standings from match results
    Given the match data is loaded
    When I request the standings for a season
    Then I should receive a points-ranked table whose champion is correct.
================================================================================
"""


class TestStandings:
    def test_2019_brasileirao_champion_is_flamengo(self, engine):
        # When I compute the 2019 Brasileirão table
        table = engine.standings(2019, "serie_a")
        # Then Flamengo are champions with 90 points (known real-world result)
        assert table["champion"] == "Flamengo"
        top = table["table"][0]
        assert top["Pts"] == 90
        assert top["position"] == 1

    def test_standings_are_points_ranked(self, engine):
        table = engine.standings(2018, "serie_a")
        pts = [r["Pts"] for r in table["table"]]
        assert pts == sorted(pts, reverse=True)

    def test_twenty_team_league(self, engine):
        # The modern Série A has 20 teams
        table = engine.standings(2019, "serie_a")
        assert table["teams"] == 20

    def test_each_row_is_internally_consistent(self, engine):
        table = engine.standings(2017, "serie_a")
        for r in table["table"]:
            assert r["P"] == r["W"] + r["D"] + r["L"]
            assert r["Pts"] == 3 * r["W"] + r["D"]
            assert r["GD"] == r["GF"] - r["GA"]


class TestChampionAndRelegation:
    def test_competition_winner(self, engine):
        res = engine.competition_winner(2017, "serie_a")
        # Corinthians won the 2017 Brasileirão
        assert res["champion"] == "Corinthians"

    def test_relegated_returns_bottom_four(self, engine):
        res = engine.relegated(2019, "serie_a", count=4)
        assert len(res["relegated"]) == 4
        # Relegated teams are the lowest-placed
        positions = [r["position"] for r in res["relegated"]]
        assert max(positions) == 20
