"""Feature: Team Queries.

Context
-------
Implements the second Gherkin scenario from ``TASK.md``::

    Scenario: Get team statistics
      Given the match data is loaded
      When I request statistics for "Palmeiras" in season "2023"
      Then I should receive wins, losses, draws, and goals

plus home/away splits, per-competition breakdowns, season trends and the
side-by-side comparison.  The arithmetic itself is verified against the
deterministic ``tiny_graph`` fixture as well as the real data.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.formatting import format_record, format_team_profile
from brazilian_soccer.models import BRASILEIRAO
from brazilian_soccer.queries import SoccerQueries


class TestTeamStatistics:
    def test_palmeiras_2023(self, queries: SoccerQueries) -> None:
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2023"
        record = queries.team_record("Palmeiras", season=2023)
        # Then I should receive wins, losses, draws and goals
        assert record.played > 0
        assert record.wins + record.draws + record.losses == record.played
        assert record.goals_for > 0
        assert record.goals_against >= 0
        assert record.points == record.wins * 3 + record.draws
        assert 0 <= record.win_rate <= 100

    def test_corinthians_home_record_2022(self, queries: SoccerQueries) -> None:
        # When I ask for Corinthians' 2022 Brasileirão home record
        record = queries.team_record(
            "Corinthians", season=2022, competition=BRASILEIRAO, venue="home"
        )
        # Then it is exactly one half of a 38-round season
        assert record.played == 19
        assert record.wins + record.draws + record.losses == 19
        # And the formatted answer matches the layout in the spec
        text = format_record(record, "Corinthians home record (2022 Brasileirão)")
        assert "- Matches: 19" in text
        assert f"- Wins: {record.wins}, Draws: {record.draws}, Losses: {record.losses}" in text
        assert f"- Goals For: {record.goals_for}" in text
        assert "Win rate:" in text

    def test_home_and_away_split_covers_everything(self, queries: SoccerQueries) -> None:
        overall = queries.team_record("Santos", season=2019)
        home = queries.team_record("Santos", season=2019, venue="home")
        away = queries.team_record("Santos", season=2019, venue="away")
        assert home.played + away.played == overall.played
        assert home.wins + away.wins == overall.wins
        assert home.goals_for + away.goals_for == overall.goals_for

    def test_arithmetic_on_a_known_dataset(self, tiny_queries: SoccerQueries) -> None:
        # Given the deterministic three-team league from conftest
        alpha = tiny_queries.team_record("Alpha", competition=BRASILEIRAO)
        gamma = tiny_queries.team_record("Gamma", competition=BRASILEIRAO)
        # Then the record is exactly as hand-computed
        assert (alpha.played, alpha.wins, alpha.draws, alpha.losses) == (2, 1, 0, 1)
        assert (alpha.goals_for, alpha.goals_against) == (3, 3)
        assert alpha.points == 3
        assert (gamma.played, gamma.wins, gamma.draws, gamma.losses) == (2, 1, 1, 0)
        assert gamma.points == 4
        assert gamma.goal_difference == 2

    def test_record_for_a_team_with_no_matches_is_empty(
        self, tiny_queries: SoccerQueries
    ) -> None:
        record = tiny_queries.team_record("Alpha", season=1999)
        assert record.played == 0
        assert "No matches with recorded scores" in format_record(record)


class TestTeamProfile:
    def test_profile_lists_every_competition(self, queries: SoccerQueries) -> None:
        # When I ask what competitions Palmeiras has played in
        profile = queries.team_profile("Palmeiras")
        # Then all three are listed with their own records
        assert set(profile["competitions"]) >= {
            BRASILEIRAO,
            "Copa do Brasil",
            "Copa Libertadores",
        }
        assert profile["overall"]["played"] == sum(
            record["played"] for record in profile["competitions"].values()
        )
        assert profile["seasons"]
        assert profile["first_match"] < profile["last_match"]

    def test_profile_renders(self, queries: SoccerQueries) -> None:
        text = format_team_profile(queries.team_profile("Flamengo"))
        assert "All competitions:" in text
        assert "Home:" in text and "Away:" in text
        assert "Competitions played:" in text

    def test_profile_reports_linked_fifa_squad(self, queries: SoccerQueries) -> None:
        # Given a club present in both the match data and the FIFA file
        profile = queries.team_profile("Gremio")
        # Then the cross-file link is reported
        assert profile["fifa_players"] >= 15


class TestCompareTeams:
    def test_palmeiras_versus_santos(self, queries: SoccerQueries) -> None:
        comparison = queries.compare_teams("Palmeiras", "Santos")
        assert comparison["team_a"]["team"].startswith("Palmeiras")
        assert comparison["team_b"]["team"].startswith("Santos")
        h2h = comparison["head_to_head"]
        assert h2h["matches_found"] > 10
        assert h2h["Palmeiras_wins"] + h2h["Santos-SP_wins"] + h2h["draws"] == (
            h2h["matches_found"]
        )

    def test_comparison_can_be_scoped_to_a_competition(
        self, queries: SoccerQueries
    ) -> None:
        comparison = queries.compare_teams("Gremio", "Internacional", competition=BRASILEIRAO)
        assert comparison["competition"] == BRASILEIRAO
        assert comparison["team_a"]["played"] > 0


class TestSeasonTrend:
    def test_trend_is_ordered_and_complete(self, queries: SoccerQueries) -> None:
        trend = queries.team_season_trend("Flamengo", competition=BRASILEIRAO)
        seasons = [row["season"] for row in trend]
        assert seasons == sorted(seasons)
        assert len(seasons) > 10
        for row in trend:
            assert row["wins"] + row["draws"] + row["losses"] == row["played"]

    def test_best_and_worst_season_can_be_derived(self, queries: SoccerQueries) -> None:
        trend = queries.team_season_trend("Flamengo", competition=BRASILEIRAO)
        best = max(trend, key=lambda row: row["points"])
        # Flamengo's record Brasileirão haul was the 90-point 2019 title
        assert best["season"] == 2019
        assert best["points"] == 90


class TestTeamSearch:
    @pytest.mark.parametrize(
        "query,expected_key",
        [("flamengo", "flamengo-rj"), ("gremio", "gremio"), ("sao paulo", "sao-paulo")],
    )
    def test_search_returns_best_first(
        self, queries: SoccerQueries, query: str, expected_key: str
    ) -> None:
        assert queries.search_teams(query)[0].key == expected_key

    def test_search_records_every_spelling(self, queries: SoccerQueries) -> None:
        team = queries.resolve_team("Athletico Paranaense")
        # The club appears under at least three different spellings in the CSVs
        assert team.key == "atletico-pr"
        assert len(team.match_indexes) > 500
