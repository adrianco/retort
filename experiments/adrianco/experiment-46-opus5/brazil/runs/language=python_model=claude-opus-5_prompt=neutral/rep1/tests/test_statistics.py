"""Feature: Statistical analysis across the whole dataset.

  Scenario: Aggregate statistics
    Given the match data is loaded
    When I ask for goals per match, home advantage or the biggest wins
    Then the numbers are calculated from the merged match data
"""

from __future__ import annotations

from brazilian_soccer import queries as q
from brazilian_soccer.formatting import (
    format_biggest_wins,
    format_compare_seasons,
    format_overall_statistics,
)


class TestBiggestWins:

    def test_biggest_wins_are_ordered_by_margin(self, graph):
        """
        Given every result in the dataset
        When I ask for the biggest victories
        Then they are ordered by margin and each margin matches the score
        """
        result = q.biggest_wins(graph, limit=10)
        margins = [m["margin"] for m in result["matches"]]

        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 7
        for match in result["matches"]:
            assert abs(match["home_goals"] - match["away_goals"]) == match["margin"]

    def test_biggest_wins_for_one_team_are_all_wins(self, graph):
        """
        Given a club
        When I ask for its biggest wins
        Then every listed match was won by that club
        """
        result = q.biggest_wins(graph, team="Flamengo", limit=5)

        assert all(m["winner"] == "Flamengo" for m in result["matches"])

    def test_biggest_wins_can_be_scoped_to_a_competition_and_season(self, graph):
        result = q.biggest_wins(graph, competition="Brasileirão", season=2019,
                                limit=5)

        assert all(m["season"] == 2019 for m in result["matches"])
        assert all(m["competition"] == "Brasileirão Série A"
                   for m in result["matches"])
        assert "Biggest victories" in format_biggest_wins(result)


class TestOverallStatistics:

    def test_dataset_wide_aggregates_are_plausible(self, graph):
        """
        Given the whole merged dataset
        When overall statistics are calculated
        Then goals per match and home win rate land in realistic ranges
        And the coverage spans 2003 to 2023
        """
        result = q.overall_statistics(graph)

        assert 2.0 < result["goals_per_match"] < 3.0
        assert 40 < result["home_win_rate"] < 60
        assert result["played_matches"] > 16_000
        assert result["coverage"]["first_match"].startswith("2003")
        assert result["coverage"]["last_match"].startswith("2023")
        assert result["nodes"] > result["matches"]
        assert result["edges"] > result["nodes"]

    def test_goals_per_match_equals_total_goals_over_matches(self, graph):
        result = q.overall_statistics(graph)
        expected = result["total_goals"] / result["played_matches"]

        assert abs(result["goals_per_match"] - expected) < 0.01
        assert "Average goals per match" in format_overall_statistics(result)


class TestSeasonComparison:

    def test_two_seasons_can_be_compared(self, graph):
        """
        Given the 2018 and 2019 Brasileirão seasons
        When they are compared
        Then each season reports its own totals
        """
        result = q.compare_seasons(graph, "Brasileirão", [2018, 2019])
        seasons = result["seasons"]

        assert [row["season"] for row in seasons] == [2018, 2019]
        assert all(row["played"] >= 375 for row in seasons)
        assert seasons[0]["goals"] != seasons[1]["goals"]
        assert "season comparison" in format_compare_seasons(result)


class TestHomeAdvantage:

    def test_home_teams_win_more_often_than_away_teams(self, graph):
        """
        Given every played match in the dataset
        When home and away win rates are compared
        Then home advantage is clearly visible
        """
        summary = q.competition_summary(graph, "Brasileirão")

        assert summary["home_win_rate"] > summary["away_win_rate"] + 10

    def test_competition_totals_add_up(self, graph):
        """
        Given a competition summary
        When its parts are added together
        Then results account for every played match and the scorers rank down
        """
        summary = q.competition_summary(graph, "Copa Libertadores")

        assert (summary["home_wins"] + summary["away_wins"] + summary["draws"]
                == summary["played"])
        scorers = [row["goals"] for row in summary["top_scoring_teams"]]
        assert scorers == sorted(scorers, reverse=True)
        assert sum(scorers) < summary["goals"] * 2
