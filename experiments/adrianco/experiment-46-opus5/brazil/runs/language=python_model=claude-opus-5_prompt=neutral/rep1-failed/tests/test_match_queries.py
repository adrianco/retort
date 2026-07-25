"""Feature: Match queries.

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
"""

from __future__ import annotations

import pytest

from brazilian_soccer import queries as q
from brazilian_soccer.formatting import format_head_to_head, format_matches
from brazilian_soccer.normalization import BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES


class TestSearchMatches:

    def test_matches_between_two_teams(self, graph):
        """
        Given the match data is loaded
        When I search for matches between Flamengo and Fluminense
        Then I receive matches that all involve exactly those two clubs
        And each has a date, a score and a competition
        """
        result = q.search_matches(graph, team="Flamengo", opponent="Fluminense",
                                  limit=50)

        assert result["total"] > 20
        for match in result["matches"]:
            assert {match["home_team"], match["away_team"]} == {"Flamengo", "Fluminense"}
            assert match["date"] is not None
            assert match["score"] is not None
            assert match["competition"] in {BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES}

    def test_matches_for_a_team_in_a_season(self, graph):
        """
        Given the match data is loaded
        When I ask what matches Palmeiras played in 2023
        Then every result is from 2023 and involves Palmeiras
        """
        result = q.search_matches(graph, team="Palmeiras", season=2023, limit=100)

        assert result["total"] >= 38
        for match in result["matches"]:
            assert match["season"] == 2023
            assert "Palmeiras" in (match["home_team"], match["away_team"])

    def test_team_name_variations_resolve_to_the_same_club(self, graph):
        """
        Given the datasets spell clubs in several ways
        When I search using each spelling
        Then the same matches are returned
        """
        totals = {
            spelling: q.search_matches(graph, team=spelling, season=2019)["total"]
            for spelling in ("Palmeiras", "palmeiras-sp", "PALMEIRAS", "Palmeiras-SP")
        }

        assert len(set(totals.values())) == 1
        assert all(total > 0 for total in totals.values())

    def test_filter_by_competition_and_venue(self, graph):
        """
        Given the match data is loaded
        When I ask for Corinthians' home Brasileirão matches in 2022
        Then I get 19 matches, all played at home
        """
        result = q.search_matches(graph, team="Corinthians", season=2022,
                                  competition="Brasileirão", venue="home", limit=50)

        assert result["total"] == 19
        assert all(m["home_team"] == "Corinthians" for m in result["matches"])

    def test_filter_by_date_range(self, graph):
        """
        Given the match data is loaded
        When I ask for matches in a date window
        Then every match falls inside it
        """
        result = q.search_matches(graph, team="Santos", date_from="2019-01-01",
                                  date_to="2019-12-31", limit=100)

        assert result["total"] > 0
        assert all("2019-01-01" <= m["date"] <= "2019-12-31"
                   for m in result["matches"])

    def test_cup_finals_are_not_confused_with_semifinals(self, graph):
        """
        Given cup rounds named "final" and "semifinals"
        When I ask for Copa do Brasil finals
        Then only finals are returned, two legs per season
        """
        result = q.search_matches(graph, competition="Copa do Brasil",
                                  stage="final", limit=50)

        assert result["total"] > 0
        assert all(m["stage"] == "final" for m in result["matches"])
        seasons = [m["season"] for m in result["matches"]]
        assert all(seasons.count(season) == 2 for season in set(seasons))

    def test_a_stage_filter_never_matches_everything(self, graph):
        """
        Given round numbers are stored alongside stage names
        When I filter by the bare word "round"
        Then only matches with a named round-of-N stage come back, not the lot
        And a numbered query still finds that round
        """
        everything = q.search_matches(graph, team="Flamengo")["total"]
        bare = q.search_matches(graph, team="Flamengo", stage="round")
        numbered = q.search_matches(graph, team="Flamengo", stage="round 22",
                                    limit=100)

        assert 0 < bare["total"] < everything
        assert all("round of" in m["stage"] for m in bare["matches"])
        assert numbered["total"] > 0
        assert all(m["round"] == "22" for m in numbered["matches"])

    def test_negative_limit_does_not_corrupt_the_result(self, graph):
        """
        Given a client passing a nonsensical limit
        When the search runs
        Then the total is still right and no matches are silently dropped
        """
        result = q.search_matches(graph, team="Flamengo", limit=-3)

        assert result["total"] > 0
        assert result["returned"] == 0
        assert result["matches"] == []

    def test_venue_without_a_team_is_refused(self, graph):
        """
        Given "home" only means something relative to a team
        When a venue is given without one
        Then the query is refused instead of quietly ignoring the filter
        """
        with pytest.raises(ValueError):
            q.search_matches(graph, venue="home")

    def test_unknown_team_is_reported_with_suggestions(self, graph):
        """
        Given a club name that does not exist
        When I search for it
        Then an UnknownTeamError explains the problem
        """
        with pytest.raises(q.UnknownTeamError):
            q.search_matches(graph, team="Manchester Rovers")

    def test_unknown_competition_is_rejected(self, graph):
        with pytest.raises(q.UnknownCompetitionError):
            q.search_matches(graph, competition="Premier League")

    def test_formatted_output_reads_like_the_specification(self, graph):
        """
        Given a match search
        When the result is formatted
        Then it lists dates, scores and the competition in one line per match
        """
        text = format_matches(q.search_matches(graph, team="Flamengo",
                                               opponent="Fluminense", limit=3))

        assert "Flamengo vs Fluminense" in text
        assert text.count("\n- ") >= 3
        assert "more in dataset" in text or "match(es) found" in text


class TestLastMeeting:

    def test_when_two_clubs_last_played(self, graph):
        """
        Given the match data is loaded
        When I ask when Flamengo last played Corinthians
        Then the most recent meeting and its score are returned
        """
        result = q.last_meeting(graph, "Flamengo", "Corinthians")

        assert result["found"] is True
        assert result["total_meetings"] > 30
        match = result["match"]
        assert match["score"] is not None
        assert {match["home_team"], match["away_team"]} == {"Flamengo", "Corinthians"}
        latest = max(m["date"] for m in q.search_matches(
            graph, team="Flamengo", opponent="Corinthians", limit=200)["matches"])
        assert match["date"] == latest


class TestHeadToHead:

    def test_head_to_head_totals_add_up(self, graph):
        """
        Given the match data is loaded
        When I request the Fla-Flu head-to-head
        Then wins, draws and losses sum to the number of played matches
        """
        result = q.head_to_head(graph, "Flamengo", "Fluminense")

        assert result["played_matches"] == (
            result["team_a_wins"] + result["team_b_wins"] + result["draws"]
        )
        assert result["team_a_goals"] > 0 and result["team_b_goals"] > 0
        assert set(result["by_competition"]) <= {BRASILEIRAO, COPA_DO_BRASIL,
                                                 LIBERTADORES}

    def test_head_to_head_is_symmetric(self, graph):
        """
        Given a head-to-head between two clubs
        When the clubs are swapped
        Then the wins swap with them
        """
        one = q.head_to_head(graph, "Grêmio", "Internacional")
        other = q.head_to_head(graph, "Internacional", "Grêmio")

        assert one["team_a_wins"] == other["team_b_wins"]
        assert one["draws"] == other["draws"]
        assert one["total_matches"] == other["total_matches"]

    def test_head_to_head_can_be_scoped_to_a_competition(self, graph):
        result = q.head_to_head(graph, "Palmeiras", "Santos",
                                competition="Brasileirão")

        assert set(result["by_competition"]) == {BRASILEIRAO}

    def test_same_team_twice_is_rejected(self, graph):
        with pytest.raises(ValueError):
            q.head_to_head(graph, "Santos", "santos-sp")

    def test_formatted_head_to_head_reports_the_tally(self, graph):
        text = format_head_to_head(q.head_to_head(graph, "Flamengo", "Fluminense"))

        assert "Head-to-head:" in text
        assert "wins" in text and "draws" in text


class TestDerbies:

    def test_derbies_carry_their_traditional_name(self, graph):
        """
        Given a list of traditional rivalries
        When I ask for derbies in 2023
        Then every match is between rivals and is labelled with the derby name
        """
        result = q.derbies(graph, season=2023)

        assert result["total"] > 10
        names = {row["derby"] for row in result["matches"]}
        assert {"Fla-Flu", "Grenal", "Derby Paulista"} & names
        for row in result["matches"]:
            assert row["season"] == 2023
            assert row["derby"]
