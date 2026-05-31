"""
================================================================================
BDD Feature: Competition Queries
================================================================================

CONTEXT
-------
Covers specification capability #4: season standings computed from match
results, season champion, relegation zone and top-scoring team. Exact
assertions use ``synthetic_kg``; integration checks compute a real Brasileirão
table and sanity-check it.
================================================================================
"""

from brazilian_soccer_mcp.normalize import COMP_BRASILEIRAO


class TestStandings:
    """Feature: Compute a league table from matches."""

    def test_standings_order_and_points(self, synthetic_kg):
        # Given a known mini-season
        # When I compute the 2023 standings
        table = synthetic_kg.standings(2023, COMP_BRASILEIRAO)
        # Then teams are ranked by points
        assert [r["team"] for r in table] == ["Flamengo", "Palmeiras", "Santos"]
        assert [r["points"] for r in table] == [8, 7, 1]
        assert table[0]["position"] == 1

    def test_standings_goal_accounting(self, synthetic_kg):
        table = synthetic_kg.standings(2023, COMP_BRASILEIRAO)
        flamengo = table[0]
        assert flamengo["goals_for"] == 6
        assert flamengo["goals_against"] == 2
        assert flamengo["goal_difference"] == 4
        assert flamengo["played"] == 4


class TestChampion:
    """Feature: Determine the season champion."""

    def test_champion_is_top_of_table(self, synthetic_kg):
        # When I ask who won 2023
        champ = synthetic_kg.champion(2023, COMP_BRASILEIRAO)
        # Then Flamengo is champion
        assert champ["team"] == "Flamengo"
        assert champ["position"] == 1


class TestRelegationAndScoring:
    """Feature: Relegation zone and top scorers."""

    def test_relegated_returns_bottom(self, synthetic_kg):
        # When I ask for the bottom team
        relegated = synthetic_kg.relegated(2023, COMP_BRASILEIRAO, count=1)
        # Then Santos is in the relegation zone
        assert relegated[-1]["team"] == "Santos"

    def test_top_scoring_team(self, synthetic_kg):
        # When I ask which team scored most
        top = synthetic_kg.top_scoring_team(2023, COMP_BRASILEIRAO)
        # Then it is Flamengo (6 goals)
        assert top["team"] == "Flamengo"
        assert top["goals_for"] == 6


class TestRealCompetitionQueries:
    """Feature: Standings against the real Brasileirão data."""

    def test_real_standings_have_teams(self, kg, real_brasileirao_season):
        table = kg.standings(real_brasileirao_season, COMP_BRASILEIRAO)
        assert len(table) >= 16
        # Positions are contiguous starting at 1
        assert [r["position"] for r in table] == list(range(1, len(table) + 1))

    def test_real_standings_sorted_by_points(self, kg, real_brasileirao_season):
        table = kg.standings(real_brasileirao_season, COMP_BRASILEIRAO)
        pts = [r["points"] for r in table]
        assert pts == sorted(pts, reverse=True)

    def test_real_champion_exists(self, kg, real_brasileirao_season):
        champ = kg.champion(real_brasileirao_season, COMP_BRASILEIRAO)
        assert champ is not None
        assert champ["position"] == 1
        assert champ["points"] > 0

    def test_no_double_counting(self, kg, real_brasileirao_season):
        # A team should not appear to have played an implausible number of
        # league games (de-dup across modern + historic sources).
        table = kg.standings(real_brasileirao_season, COMP_BRASILEIRAO)
        assert all(r["played"] <= 50 for r in table)
