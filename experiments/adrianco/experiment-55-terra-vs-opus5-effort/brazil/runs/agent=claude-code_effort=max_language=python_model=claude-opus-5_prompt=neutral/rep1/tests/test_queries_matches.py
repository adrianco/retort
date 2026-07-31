"""Match and team queries (specification sections 1, 2 and 5).

Context
-------
Feature: Match Queries

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
"""

from __future__ import annotations

import pytest

from brazilian_soccer import queries


class TestFindMatches:
    """Scenario: Find matches by team, competition, season or date."""

    def test_given_two_teams_when_searching_then_every_match_is_described(self, graph):
        """
        Given the match data is loaded
        When I search for matches between "Flamengo" and "Fluminense"
        Then I receive a list of matches
        And each match has a date, both scores and its competition
        """
        result = queries.find_matches(graph, team="Flamengo", opponent="Fluminense", limit=50)

        assert result["total"] > 30
        assert result["derby"] == "Fla-Flu"
        for match in result["matches"]:
            assert match["date"]
            assert match["home_goals"] is not None and match["away_goals"] is not None
            assert match["competition"]
            assert {match["home_team_id"], match["away_team_id"]} == {"flamengo", "fluminense"}

    def test_given_a_team_and_season_when_searching_then_only_that_season_returns(self, graph):
        """
        Given the match data is loaded
        When I ask what matches Palmeiras played in 2023
        Then every returned match is from 2023 and involves Palmeiras
        """
        result = queries.find_matches(graph, team="Palmeiras", season=2023, limit=100)

        assert result["total"] > 30
        assert all(match["season"] == 2023 for match in result["matches"])
        assert all(
            "palmeiras" in (match["home_team_id"], match["away_team_id"])
            for match in result["matches"]
        )

    def test_given_a_stage_filter_when_searching_for_finals_then_only_finals_return(self, graph):
        """
        Given the Copa do Brasil rounds are numbered, not named
        When I ask for all Copa do Brasil finals
        Then only matches whose derived stage is the final are returned
        And semi-finals are not included by accident
        """
        result = queries.find_matches(
            graph, competition="Copa do Brasil", stage="Final", limit=100
        )

        assert result["total"] == 18  # nine two-legged finals, 2012-2020
        assert all(match["stage"] == "Final" for match in result["matches"])

    def test_given_a_date_range_when_searching_then_matches_are_bounded(self, graph):
        """
        Given a date range
        When I search for Libertadores matches inside it
        Then no match outside the range is returned
        """
        result = queries.find_matches(
            graph,
            competition="Libertadores",
            date_from="2019-03-01",
            date_to="2019-05-31",
            limit=200,
        )

        assert result["total"] > 50
        assert all("2019-03-01" <= match["date"] <= "2019-05-31" for match in result["matches"])

    def test_given_home_only_when_searching_then_away_matches_are_excluded(self, graph):
        """
        Given a club plays home and away
        When I restrict the search to home matches
        Then the club is the home team in every result
        """
        result = queries.find_matches(
            graph, team="Corinthians", season=2022, competition="Serie A",
            home_away="home", limit=50,
        )

        assert result["total"] == 19
        assert all(match["home_team_id"] == "corinthians" for match in result["matches"])

    @pytest.mark.parametrize(
        "kwargs, fragment",
        [
            ({"team": "Santos", "home_away": "sideways"}, "home_away"),
            ({"team": "Santos", "date_from": "not-a-date"}, "date"),
            ({"team": "Santos", "date_to": "31/31/2020"}, "date"),
        ],
    )
    def test_given_a_nonsense_filter_when_searching_then_it_is_rejected(
        self, graph, kwargs, fragment
    ):
        """
        Given a filter value that cannot be honoured
        When matches are searched
        Then the filter is rejected rather than silently ignored, which would
        answer a different question than the one that was asked
        """
        result = queries.find_matches(graph, **kwargs)

        assert "error" in result
        assert fragment in result["error"]

    def test_given_an_unknown_team_when_searching_then_suggestions_are_returned(self, graph):
        """
        Given a club name that does not exist
        When I search for its matches
        Then an explanatory error with suggestions comes back instead of an exception
        """
        result = queries.find_matches(graph, team="Manchester United")

        assert "error" in result
        assert "suggestions" in result

    def test_given_results_when_limited_then_the_total_is_still_reported(self, graph):
        """
        Given a query with many results
        When a small limit is applied
        Then the response reports how many matches exist in total
        """
        result = queries.find_matches(graph, team="Santos", limit=3)

        assert len(result["matches"]) == 3
        assert result["total"] > 3

    @pytest.mark.parametrize("limit", [0, -1, 100_000])
    def test_given_an_extreme_limit_when_searching_then_the_answer_stays_bounded(
        self, graph, limit
    ):
        """
        Given a caller asking for everything (or passing a nonsense limit)
        When matches are searched
        Then the returned list is capped so a model's context is not flooded
        And the true total is still reported
        """
        result = queries.find_matches(graph, team="Flamengo", limit=limit)

        assert 0 < len(result["matches"]) <= queries._MAX_LIMIT
        assert result["total"] > len(result["matches"])
        assert result["record"]["played"] > len(result["matches"])  # stats use everything


class TestHeadToHead:
    """Scenario: Compare two clubs."""

    def test_given_two_rivals_when_compared_then_the_record_balances(self, graph):
        """
        Given two clubs that have met many times
        When their head-to-head is requested
        Then wins, draws and losses add up to the matches played
        """
        result = queries.head_to_head(graph, "Palmeiras", "Santos")
        summary = result["summary"]

        assert summary["matches"] == (
            summary["team_a_wins"] + summary["team_b_wins"] + summary["draws"]
        )
        assert result["derby"] == "Clássico da Saudade"
        assert result["last_meeting"]["date"] > result["first_meeting"]["date"]

    def test_given_a_head_to_head_when_split_by_competition_then_totals_agree(self, graph):
        """
        Given two clubs that met in several competitions
        When the record is broken down by competition
        Then the per-competition matches sum to the overall total
        """
        result = queries.head_to_head(graph, "Flamengo", "Corinthians")
        per_competition = sum(
            record["played"] for record in result["by_competition"].values()
        )

        assert per_competition == result["summary"]["matches"]

    def test_given_the_same_club_twice_when_compared_then_it_is_rejected(self, graph):
        """
        Given a request comparing a club with itself
        When the head-to-head is computed
        Then it is rejected with an explanation
        """
        result = queries.head_to_head(graph, "Flamengo", "Fla")

        assert "error" in result

    def test_given_a_competition_filter_when_comparing_then_only_it_counts(self, graph):
        """
        Given two clubs that met in league and cup
        When the comparison is restricted to one competition
        Then only matches from that competition are counted
        """
        overall = queries.head_to_head(graph, "Gremio", "Internacional")
        league = queries.head_to_head(
            graph, "Gremio", "Internacional", competition="Serie A"
        )

        assert league["summary"]["matches"] < overall["summary"]["matches"]
        assert set(league["by_competition"]) == {"Brasileirão Série A"}


class TestDerbies:
    """Scenario: Find traditional rivalries."""

    def test_given_a_season_when_asking_for_derbies_then_classics_are_returned(self, graph):
        """
        Given the rivalry definitions
        When I ask for all derbies in 2023
        Then classic fixtures are returned with their popular names
        """
        result = queries.derbies(graph, season=2023)

        assert result["total"] > 20
        names = {item["derby"] for item in result["by_derby"]}
        assert "Fla-Flu" in names
        assert "Derby Paulista" in names
        assert all(match["season"] == 2023 for match in result["matches"])

    def test_given_a_team_when_asking_for_derbies_then_only_its_rivalries_return(self, graph):
        """
        Given one club
        When I ask for its derbies
        Then every match involves that club
        """
        result = queries.derbies(graph, team="Gremio", limit=200)

        assert result["total"] > 0
        assert all(
            "gremio" in (match["home_team_id"], match["away_team_id"])
            for match in result["matches"]
        )


class TestStatisticalAnalysis:
    """Scenario: Aggregate statistics across the dataset."""

    def test_given_all_matches_when_aggregated_then_averages_are_plausible(self, graph):
        """
        Given every match in the dataset
        When aggregate statistics are computed
        Then goals per match and home win rate are in a realistic range
        """
        result = queries.competition_stats(graph)

        assert result["matches"] > 16_000
        assert 2.0 < result["goals_per_match"] < 3.0
        assert 40 < result["home_win_rate"] < 60
        assert (
            round(result["home_win_rate"] + result["draw_rate"] + result["away_win_rate"]) == 100
        )

    def test_given_biggest_wins_when_listed_then_they_are_sorted_by_margin(self, graph):
        """
        Given every match in the dataset
        When the biggest wins are requested
        Then they are ordered by winning margin, largest first
        """
        result = queries.biggest_wins(graph, limit=10)
        margins = [
            abs(match["home_goals"] - match["away_goals"]) for match in result["matches"]
        ]

        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 6

    def test_given_a_team_when_asking_for_its_biggest_wins_then_it_always_won(self, graph):
        """
        Given one club
        When its biggest wins are requested
        Then every returned match was won by that club
        """
        result = queries.biggest_wins(graph, team="Flamengo", limit=5)

        for match in result["matches"]:
            if match["home_team_id"] == "flamengo":
                assert match["home_goals"] > match["away_goals"]
            else:
                assert match["away_goals"] > match["home_goals"]

    def test_given_two_seasons_when_compared_then_both_are_summarised(self, graph):
        """
        Given two seasons of the same competition
        When they are compared
        Then each is summarised with goals, results split and champion
        """
        result = queries.compare_seasons(graph, "Serie A", [2018, 2019])

        assert [entry["season"] for entry in result["comparison"]] == [2018, 2019]
        assert result["comparison"][1]["champion"].startswith("Flamengo")
        assert result["comparison"][0]["champion"].startswith("Palmeiras")

    def test_given_a_single_season_when_compared_then_it_is_rejected(self, graph):
        """
        Given only one season
        When a comparison is requested
        Then it is rejected with an explanation
        """
        assert "error" in queries.compare_seasons(graph, "Serie A", [2019])

    def test_given_an_unfinished_season_when_compared_then_no_champion_is_claimed(
        self, graph
    ):
        """
        Given 2023 is truncated in the source data
        When it is compared with a finished season
        Then the finished season has a champion and the truncated one only a leader
        """
        result = queries.compare_seasons(graph, "Serie A", [2022, 2023])
        finished, partial = result["comparison"]

        assert finished["champion"].startswith("Palmeiras")
        assert "champion" not in partial
        assert partial["leader"] and partial["complete"] is False
