"""Feature: Team queries.

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
"""

from __future__ import annotations

import pytest

from brazilian_soccer import queries as q
from brazilian_soccer.formatting import (
    format_home_away,
    format_team_profile,
    format_team_stats,
)
from brazilian_soccer.normalization import BRASILEIRAO


class TestTeamStatistics:

    def test_statistics_for_a_team_in_a_season(self, graph):
        """
        Given the match data is loaded
        When I request statistics for Palmeiras in season 2023
        Then wins, draws, losses and goals are returned and are consistent
        """
        result = q.team_stats(graph, "Palmeiras", season=2023,
                              competition="Brasileirão")

        assert result["matches"] == result["wins"] + result["draws"] + result["losses"]
        assert result["matches"] >= 37
        assert result["goals_for"] > 0
        assert result["points"] == result["wins"] * 3 + result["draws"]
        assert 0 <= result["win_rate"] <= 100

    def test_home_record_matches_the_specification_example(self, graph):
        """
        Given the 2022 Brasileirão
        When I ask for Corinthians' home record
        Then it covers the 19 home matches of a 38-round season
        """
        result = q.team_stats(graph, "Corinthians", season=2022,
                              competition="Brasileirão", venue="home")

        assert result["matches"] == 19
        assert result["wins"] + result["draws"] + result["losses"] == 19
        assert result["competitions"] == [BRASILEIRAO]

    def test_home_and_away_records_sum_to_the_season_record(self, graph):
        """
        Given a season record
        When it is split into home and away
        Then the two halves add back up to the whole
        """
        overall = q.team_stats(graph, "São Paulo", season=2019,
                               competition="Brasileirão")
        split = q.home_away_split(graph, "São Paulo", season=2019,
                                  competition="Brasileirão")

        assert split["home"]["matches"] + split["away"]["matches"] == overall["matches"]
        assert split["home"]["wins"] + split["away"]["wins"] == overall["wins"]
        assert split["home"]["goals_for"] + split["away"]["goals_for"] == overall["goals_for"]

    def test_home_advantage_is_visible(self, graph):
        """
        Given Brazilian football's strong home advantage
        When a big club's home and away win rates are compared
        Then the home rate is clearly higher
        """
        split = q.home_away_split(graph, "Grêmio", competition="Brasileirão")

        assert split["home"]["win_rate"] > split["away"]["win_rate"] + 10

    def test_biggest_win_is_always_a_win(self, graph):
        """
        Given a club that won nothing in the season asked about
        When its statistics are calculated
        Then no "biggest win" is offered, rather than its least-bad draw
        """
        winless = q.team_stats(graph, "Brasiliense", season=2022)

        assert winless["wins"] == 0
        assert winless["biggest_win"] is None

        winner = q.team_stats(graph, "Flamengo", season=2019,
                              competition="Brasileirão")
        assert winner["biggest_win"]["winner"] == "Flamengo"

    def test_formatted_stats_follow_the_specification_layout(self, graph):
        text = format_team_stats(q.team_stats(graph, "Corinthians", season=2022,
                                              competition="Brasileirão",
                                              venue="home"))

        assert "Corinthians record" in text
        assert "- Matches: 19" in text
        assert "Win rate:" in text

    def test_unknown_team_raises_with_a_hint(self, graph):
        with pytest.raises(q.UnknownTeamError) as error:
            q.team_stats(graph, "Barcelona SC de Nowhere")
        assert "No team matching" in str(error.value)


class TestTeamProfile:

    def test_profile_lists_every_competition_the_club_played(self, graph):
        """
        Given the match data is loaded
        When I ask what competitions Palmeiras has played in
        Then all three national/continental competitions are listed with records
        """
        result = q.team_profile(graph, "Palmeiras")

        assert result["team"] == "Palmeiras"
        assert set(result["competitions"]) >= {BRASILEIRAO, "Copa do Brasil",
                                               "Copa Libertadores"}
        for row in result["competitions"].values():
            assert row["matches"] > 0
            assert row["seasons"]
        assert result["first_match"] < result["last_match"]

    def test_profile_mentions_the_most_played_opponents(self, graph):
        result = q.team_profile(graph, "Flamengo")
        opponents = [row["team"] for row in result["most_played_opponents"]]

        assert len(opponents) == 5
        assert "Flamengo" not in opponents

    def test_formatted_profile_is_readable(self, graph):
        text = format_team_profile(q.team_profile(graph, "Santos"))

        assert text.startswith("Santos")
        assert "By competition:" in text
        assert "Most played opponents:" in text


class TestCompareTeams:

    def test_comparison_includes_both_records_and_the_head_to_head(self, graph):
        """
        Given two clubs
        When I compare them
        Then I get each club's record plus their head-to-head
        """
        result = q.compare_teams(graph, "Palmeiras", "Santos")

        assert result["team_a"]["team"] == "Palmeiras"
        assert result["team_b"]["team"] == "Santos"
        h2h = result["head_to_head"]
        assert h2h["total_matches"] > 20
        assert h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"] == h2h["played_matches"]


class TestTeamRankings:

    def test_best_home_record_is_a_big_club(self, graph):
        """
        Given every Brasileirão match in the data
        When teams are ranked by home win rate
        Then the leaders are established clubs with a high win rate
        """
        result = q.team_rankings(graph, metric="win_rate", venue="home",
                                 competition="Brasileirão", min_matches=100,
                                 limit=5)

        assert len(result["rows"]) == 5
        rates = [row["win_rate"] for row in result["rows"]]
        assert rates == sorted(rates, reverse=True)
        assert rates[0] > 50

    def test_away_rankings_are_lower_than_home_rankings(self, graph):
        home = q.team_rankings(graph, metric="win_rate", venue="home",
                               competition="Brasileirão", min_matches=100, limit=1)
        away = q.team_rankings(graph, metric="win_rate", venue="away",
                               competition="Brasileirão", min_matches=100, limit=1)

        assert home["rows"][0]["win_rate"] > away["rows"][0]["win_rate"]

    def test_top_scorers_of_a_season(self, graph):
        """
        Given the 2023 Série A
        When teams are ranked by goals scored
        Then the top team scored the most goals of anybody that season
        """
        result = q.team_rankings(graph, metric="goals_for",
                                 competition="Brasileirão", season=2023, limit=20)
        goals = [row["goals_for"] for row in result["rows"]]

        assert goals == sorted(goals, reverse=True)
        assert goals[0] >= 50

    def test_unknown_metric_is_rejected(self, graph):
        with pytest.raises(ValueError):
            q.team_rankings(graph, metric="vibes")


class TestTeamDirectory:

    def test_searching_the_club_list(self, graph):
        """
        Given clubs whose names collide
        When I search for "atletico"
        Then several distinct clubs are listed with their ids and states
        """
        result = q.list_teams(graph, "atletico", limit=30)
        ids = {row["team_id"] for row in result["teams"]}

        assert {"atletico-mineiro", "athletico-paranaense",
                "atletico-goianiense"} <= ids

    def test_the_club_list_reports_the_real_total(self, graph):
        """
        Given far more clubs than fit in one page of results
        When the list is requested with a small limit
        Then the total reflects every match, not just the page
        """
        result = q.list_teams(graph, "", limit=25)

        assert result["returned"] == 25
        assert result["total"] > 900

    def test_home_away_formatting(self, graph):
        text = format_home_away(q.home_away_split(graph, "Flamengo",
                                                  competition="Brasileirão"))

        assert "Home:" in text and "Away:" in text
