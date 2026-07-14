"""
Context
=======
Feature: Competition Queries  (TASK.md section 4)

Scenario: Calculate final league standings from match results
Scenario: Determine the champion of a season
Scenario: Standings are de-duplicated to a realistic single season
"""

from __future__ import annotations


class TestStandings:
    def test_2019_brasileirao_table_matches_known_result(self, graph):
        # WHEN I compute the 2019 Brasileirão final table
        rows = graph.standings(2019, "Brasileirão")
        assert rows
        champ = rows[0]
        # THEN Flamengo are champions with the historically correct 90 points
        # and 28W-6D-4L record (TASK.md example).
        assert "Flamengo" in champ["team"]
        assert champ["points"] == 90
        assert (champ["wins"], champ["draws"], champ["losses"]) == (28, 6, 4)

    def test_standings_are_ordered_by_points(self, graph):
        rows = graph.standings(2019, "Brasileirão")
        pts = [r["points"] for r in rows]
        assert pts == sorted(pts, reverse=True)
        # Positions are assigned 1..N
        assert [r["position"] for r in rows] == list(range(1, len(rows) + 1))

    def test_each_team_plays_a_full_38_game_season(self, graph):
        # A 20-team double round-robin = 38 games each.
        rows = graph.standings(2019, "Brasileirão")
        assert len(rows) == 20
        assert all(r["played"] == 38 for r in rows)

    def test_points_reconcile_with_results(self, graph):
        rows = graph.standings(2019, "Brasileirão")
        for r in rows:
            assert r["points"] == r["wins"] * 3 + r["draws"]
            assert r["wins"] + r["draws"] + r["losses"] == r["played"]


class TestChampion:
    def test_champion_helper_returns_table_leader(self, graph):
        champ = graph.champion(2019, "Brasileirão")
        assert champ is not None
        assert "Flamengo" in champ["team"]

    def test_champion_for_other_season(self, graph):
        # 2017 Brasileirão was won by Corinthians.
        champ = graph.champion(2017, "Brasileirão")
        assert champ is not None
        assert "Corinthians" in champ["team"]
