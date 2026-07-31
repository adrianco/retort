"""Feature: Statistical Analysis.

Context
-------
Aggregates required by the spec: goals per match, home/away splits,
head-to-head records, biggest wins and cross-season comparison.  Where a real
value is publicly checkable (Brazilian league home-win rate near 50%, ~2.5
goals per game) the test asserts a plausible band rather than an exact number,
so it catches an arithmetic regression without pinning to a data revision.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.formatting import format_ranking, format_stats
from brazilian_soccer.models import BRASILEIRAO, LIBERTADORES
from brazilian_soccer.queries import SoccerQueries


class TestCompetitionStatistics:
    def test_brasileirao_aggregates_are_plausible(self, queries: SoccerQueries) -> None:
        # When I ask for the Brasileirão average goals per match
        stats = queries.competition_stats(BRASILEIRAO)
        # Then the aggregate is in the historically expected band
        assert 2.2 <= stats["goals_per_match"] <= 2.9
        assert 44 <= stats["home_win_rate"] <= 55
        assert stats["matches"] == stats["matches_with_scores"]
        assert stats["seasons_covered"] == [2003, 2023]

    def test_percentages_sum_to_one_hundred(self, queries: SoccerQueries) -> None:
        stats = queries.competition_stats(BRASILEIRAO, season=2019)
        total = stats["home_win_rate"] + stats["draw_rate"] + stats["away_win_rate"]
        assert abs(total - 100) < 0.2
        assert stats["home_wins"] + stats["draws"] + stats["away_wins"] == 380

    def test_goal_total_is_the_sum_of_the_matches(self, queries: SoccerQueries) -> None:
        matches = queries.search_matches(
            competition=BRASILEIRAO, season=2018, limit=None
        )
        stats = queries.competition_stats(BRASILEIRAO, season=2018)
        assert stats["total_goals"] == sum(m.total_goals for m in matches)

    def test_home_advantage_exists(self, queries: SoccerQueries) -> None:
        stats = queries.competition_stats(BRASILEIRAO)
        assert stats["home_win_rate"] > stats["away_win_rate"]

    def test_statistics_render(self, queries: SoccerQueries) -> None:
        text = format_stats(queries.competition_stats(BRASILEIRAO, 2019))
        assert "Average goals per match:" in text
        assert "Home wins:" in text


class TestSeasonComparison:
    def test_two_seasons_side_by_side(self, queries: SoccerQueries) -> None:
        # When I compare the 2018 and 2019 seasons
        rows = queries.compare_seasons([2018, 2019], BRASILEIRAO)
        # Then both are returned with the same shape
        assert [row["season"] for row in rows] == [2018, 2019]
        assert all(row["matches"] == 380 for row in rows)
        assert rows[0]["goals_per_match"] != rows[1]["goals_per_match"]

    def test_every_season_can_be_aggregated(self, queries: SoccerQueries) -> None:
        seasons = queries.graph.seasons_for(BRASILEIRAO)
        rows = queries.compare_seasons(seasons, BRASILEIRAO)
        assert len(rows) == len(seasons)
        assert all(row["goals_per_match"] > 1.5 for row in rows)


class TestRankings:
    def test_best_away_record(self, queries: SoccerQueries) -> None:
        # When I ask which team has the best away record
        records = queries.best_records(venue="away", min_matches=100, limit=5)
        # Then the leaders are the historically strong clubs and the metric sorts
        assert records
        values = [record.points_per_game for record in records]
        assert values == sorted(values, reverse=True)
        assert {r.team_key for r in records} & {"palmeiras", "flamengo-rj", "sao-paulo"}

    def test_best_home_record_beats_best_away_record(
        self, queries: SoccerQueries
    ) -> None:
        home = queries.best_records(venue="home", min_matches=100, limit=1)[0]
        away = queries.best_records(venue="away", min_matches=100, limit=1)[0]
        assert home.points_per_game > away.points_per_game

    @pytest.mark.parametrize(
        "metric",
        ["points", "win_rate", "wins", "goals_for", "goals_per_game", "goal_difference"],
    )
    def test_every_metric_sorts(self, queries: SoccerQueries, metric: str) -> None:
        records = queries.best_records(
            competition=BRASILEIRAO, season=2019, metric=metric, limit=6
        )
        values = [
            getattr(record, metric if metric != "wins" else "wins") for record in records
        ]
        assert values == sorted(values, reverse=True)

    def test_min_matches_filters_small_samples(self, queries: SoccerQueries) -> None:
        records = queries.best_records(min_matches=300, limit=50)
        assert all(record.played >= 300 for record in records)

    def test_top_scoring_team_of_a_season(self, queries: SoccerQueries) -> None:
        # When I ask which team scored the most in the 2023 Série A
        top = queries.top_scoring_teams(BRASILEIRAO, 2023, limit=3)
        table = queries.standings(BRASILEIRAO, 2023)
        # Then it agrees with the goals-for column of the calculated table
        assert top[0].goals_for == max(record.goals_for for record in table)

    def test_ranking_renders(self, queries: SoccerQueries) -> None:
        records = queries.best_records(competition=BRASILEIRAO, season=2019, limit=3)
        text = format_ranking(records, "Best 2019 sides:", "points_per_game")
        assert "1. " in text and "pts/game" in text


class TestBiggestWins:
    def test_biggest_wins_are_sorted_by_margin(self, queries: SoccerQueries) -> None:
        matches = queries.biggest_wins(limit=10)
        margins = [match.goal_difference for match in matches]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 7

    def test_biggest_wins_can_be_scoped(self, queries: SoccerQueries) -> None:
        matches = queries.biggest_wins(competition=LIBERTADORES, season=2020, limit=5)
        assert matches
        assert all(m.competition == LIBERTADORES and m.season == 2020 for m in matches)

    def test_biggest_wins_for_one_team(self, queries: SoccerQueries) -> None:
        matches = queries.biggest_wins(team="Flamengo", limit=5)
        assert all(m.involves("flamengo-rj") for m in matches)
        assert matches[0].goal_difference >= 5


class TestOverview:
    def test_overview_reports_dedup_and_coverage(self, queries: SoccerQueries) -> None:
        overview = queries.dataset_overview()
        assert overview["matches"] > 17000
        assert overview["duplicate_rows_merged"] > 5000
        assert overview["players"] == 18207
        assert len(overview["competitions"]) == 5
        assert overview["load_seconds"] < 10
