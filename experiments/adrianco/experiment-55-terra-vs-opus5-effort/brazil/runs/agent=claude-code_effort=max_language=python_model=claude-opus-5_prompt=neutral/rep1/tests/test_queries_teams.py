"""Team statistics, profiles and rankings (specification section 2).

Context
-------
Feature: Team Queries

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals

  Rankings answer the "which team has the best home record" and "which team
  scored the most goals" style questions from the specification.
"""

from __future__ import annotations

import pytest

from brazilian_soccer import queries


class TestTeamStats:
    """Scenario: Statistics for one club."""

    def test_given_a_team_and_season_when_asked_then_the_record_is_complete(self, graph):
        """
        Given the match data is loaded
        When I request statistics for "Palmeiras" in season 2023
        Then I receive wins, losses, draws and goals that add up
        """
        result = queries.team_stats(graph, "Palmeiras", season=2023)
        record = result["record"]

        assert record["played"] == record["wins"] + record["draws"] + record["losses"]
        assert record["points"] == record["wins"] * 3 + record["draws"]
        assert record["goal_difference"] == record["goals_for"] - record["goals_against"]
        assert result["season"] == 2023

    def test_given_a_home_filter_when_asked_then_only_home_matches_count(self, graph):
        """
        Given Corinthians played 19 home league matches in 2022
        When I ask for their home record that season
        Then only home matches are counted
        """
        result = queries.team_stats(
            graph, "Corinthians", season=2022, competition="Serie A", home_away="home"
        )

        assert result["record"]["played"] == 19
        assert result["away"]["played"] == 0
        assert result["home"]["played"] == 19

    def test_given_no_filter_when_asked_then_home_and_away_split_sums_to_total(self, graph):
        """
        Given a club's whole history
        When statistics are requested without a venue filter
        Then the home and away splits sum to the overall record
        """
        result = queries.team_stats(graph, "Cruzeiro")

        assert (
            result["home"]["played"] + result["away"]["played"] == result["record"]["played"]
        )
        assert result["home"]["wins"] + result["away"]["wins"] == result["record"]["wins"]

    def test_given_a_club_when_asked_then_extremes_and_form_are_included(self, graph):
        """
        Given a club with a long history
        When statistics are requested
        Then the biggest win, heaviest defeat and recent form are included
        """
        result = queries.team_stats(graph, "Vasco", season=2020)

        assert result["biggest_win"] is not None
        assert result["heaviest_defeat"] is not None
        assert len(result["form"]) <= 5
        assert all(match["outcome"] in {"W", "D", "L"} for match in result["form"])

    def test_given_a_competition_breakdown_when_asked_then_totals_agree(self, graph):
        """
        Given a club that played in three competitions
        When statistics are requested for its whole history
        Then the per-competition breakdown sums to the overall record
        """
        result = queries.team_stats(graph, "Gremio")
        total = sum(record["played"] for record in result["by_competition"].values())

        assert total == result["record"]["played"]
        assert len(result["by_competition"]) >= 2

    def test_given_an_unknown_club_when_asked_then_an_error_with_hints_returns(self, graph):
        """
        Given a club that is not in the data
        When statistics are requested
        Then an error and suggestions are returned
        """
        result = queries.team_stats(graph, "Real Madrid")

        assert "error" in result
        assert isinstance(result["suggestions"], list)


class TestTeamProfile:
    """Scenario: Everything known about a club."""

    def test_given_a_club_when_profiled_then_competitions_and_titles_are_listed(self, graph):
        """
        Given the question "what competitions has Palmeiras played in?"
        When the club is profiled
        Then its competitions, seasons and calculated league titles are returned
        """
        result = queries.team_profile(graph, "Palmeiras")

        assert set(result["competitions"]) == {
            "Brasileirão Série A", "Copa do Brasil", "Copa Libertadores",
        }
        assert result["serie_a_titles"] == [2016, 2018, 2022]
        assert result["most_played_opponents"]
        assert result["record"]["played"] > 800

    def test_given_a_club_with_fifa_players_when_profiled_then_the_squad_appears(self, graph):
        """
        Given a club present in both the match data and the FIFA file
        When it is profiled
        Then its FIFA squad is attached to the same node
        """
        result = queries.team_profile(graph, "Santos")

        assert result["fifa_squad_size"] > 0
        assert result["fifa_squad_top"]
        assert result["fifa_squad_top"][0]["overall"] >= result["fifa_squad_top"][-1]["overall"]

    def test_given_a_club_when_profiled_then_its_name_variants_are_reported(self, graph):
        """
        Given a club spelled several ways across the files
        When it is profiled
        Then the unified spellings are reported for transparency
        """
        result = queries.team_profile(graph, "Athletico Paranaense")

        assert result["team"].startswith("Athletico Paranaense")
        assert result["matches"] > 500


class TestRankings:
    """Scenario: Rank clubs by a metric."""

    def test_given_a_season_when_ranking_by_goals_then_the_top_scorer_leads(self, graph):
        """
        Given the question "which team scored the most goals in Série A 2023?"
        When teams are ranked by goals scored
        Then the ranking is ordered and complete
        """
        result = queries.team_rankings(
            graph, metric="goals_for", competition="Serie A", season=2023, limit=5
        )
        goals = [row["goals_for"] for row in result["ranking"]]

        assert goals == sorted(goals, reverse=True)
        assert result["ranking"][0]["rank"] == 1

    def test_given_a_home_filter_when_ranking_then_only_home_matches_count(self, graph):
        """
        Given the question "which team has the best home record?"
        When teams are ranked by win rate over home matches only
        Then every ranked record contains only home matches
        """
        result = queries.team_rankings(
            graph, metric="win_rate", competition="Serie A", season=2022,
            home_away="home", limit=5,
        )

        assert result["home_away"] == "home"
        assert all(row["played"] == 19 for row in result["ranking"])
        rates = [row["win_rate"] for row in result["ranking"]]
        assert rates == sorted(rates, reverse=True)

    def test_given_ascending_order_when_ranking_then_the_smallest_value_leads(self, graph):
        """
        Given the question "which team conceded fewest goals?"
        When teams are ranked ascending by goals against
        Then the meanest defence comes first
        """
        result = queries.team_rankings(
            graph, metric="goals_against", competition="Serie A", season=2019,
            limit=3, ascending=True,
        )
        conceded = [row["goals_against"] for row in result["ranking"]]

        assert conceded == sorted(conceded)

    def test_given_a_minimum_when_ranking_then_small_samples_are_excluded(self, graph):
        """
        Given clubs with very few matches would distort a rate based ranking
        When a minimum number of matches is applied
        Then only clubs above the threshold are ranked
        """
        result = queries.team_rankings(graph, metric="win_rate", min_matches=100, limit=10)

        assert all(row["played"] >= 100 for row in result["ranking"])

    def test_given_no_competition_when_ranking_by_rate_then_small_samples_are_kept_out(
        self, graph
    ):
        """
        Given the question "which team has the best away record?" over everything
        When teams are ranked by points per game
        Then the qualification bar scales with the busiest club, so a side with a
        handful of away games cannot top the list
        """
        result = queries.team_rankings(
            graph, metric="points_per_game", home_away="away", limit=5
        )

        assert result["min_matches"] > 50
        assert all(row["played"] >= result["min_matches"] for row in result["ranking"])

    def test_given_a_single_league_season_when_ranking_then_every_team_qualifies(self, graph):
        """
        Given one league season where all clubs play the same number of matches
        When teams are ranked
        Then the scaled threshold excludes nobody
        """
        result = queries.team_rankings(
            graph, metric="win_rate", competition="Serie A", season=2019, limit=25
        )

        assert result["teams_considered"] == 20

    @pytest.mark.parametrize("venue", ["home", "away"])
    def test_given_a_bad_venue_when_ranking_then_it_is_rejected(self, graph, venue):
        """
        Given the venue filter only accepts home, away or any
        When a typo is passed
        Then it is rejected instead of silently ranking every match
        """
        assert "error" not in queries.team_rankings(graph, home_away=venue, season=2019)
        assert "error" in queries.team_rankings(graph, home_away="hoem", season=2019)

    def test_given_an_unknown_metric_when_ranking_then_options_are_offered(self, graph):
        """
        Given an unsupported metric
        When a ranking is requested
        Then the supported metrics are listed back
        """
        result = queries.team_rankings(graph, metric="corners")

        assert "error" in result
        assert "points" in result["suggestions"]


class TestSearchTeams:
    """Scenario: Explain how a name was resolved."""

    def test_given_a_nickname_when_searched_then_the_club_and_spellings_return(self, graph):
        """
        Given a nickname such as "Timão"
        When teams are searched
        Then the resolved club and the spellings it unifies are reported
        """
        result = queries.search_teams(graph, "Timão")

        assert result["resolved"]["team_id"] == "corinthians"
        assert result["resolved"]["matches"] > 500

    def test_given_an_ambiguous_name_when_searched_then_candidates_are_listed(self, graph):
        """
        Given a name shared by several clubs
        When teams are searched
        Then multiple candidates are offered
        """
        result = queries.search_teams(graph, "Botafogo")

        candidate_ids = {item["team_id"] for item in result["candidates"]}
        assert {"botafogo-rj", "botafogo-pb", "botafogo-sp"} <= candidate_ids
