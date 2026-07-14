"""BDD-style tests for competition standings and summaries.

Feature: Competition Queries
  Scenario: Compute standings from match data
    Given the 2019 Brasileirão Serie A is loaded
    When I request the season standings
    Then Flamengo is champion with 90 points from 38 matches.
"""

from __future__ import annotations

from brazilian_soccer_mcp import queries as Q


class TestStandings:
    def test_2019_brasileirao_champion_is_flamengo(self, store):
        # Well-known result: Flamengo took the 2019 title with 90 points.
        table = Q.standings(store, season=2019, competition="Brasileirão")
        assert table, "expected at least one team in the table"
        champion = table[0]
        assert "Flamengo" in champion["team"]
        assert champion["points"] == 90
        assert champion["matches"] == 38

    def test_standings_rows_have_consistent_totals(self, store):
        table = Q.standings(store, season=2017, competition="Brasileirão")
        for row in table:
            assert row["wins"] + row["draws"] + row["losses"] == row["matches"]
            assert row["points"] == 3 * row["wins"] + row["draws"]
            assert row["goal_difference"] == row["goals_for"] - row["goals_against"]

    def test_standings_are_sorted_by_points(self, store):
        table = Q.standings(store, season=2018, competition="Brasileirão")
        for prev, nxt in zip(table, table[1:]):
            assert prev["points"] >= nxt["points"]


class TestSeasonSummary:
    def test_summary_includes_champion_and_standings(self, store):
        summary = Q.season_summary(store, season=2019, competition="Brasileirão")
        assert summary["matches"] == 380
        assert "Flamengo" in summary["champion"]
        assert summary["standings"][0]["points"] == 90
