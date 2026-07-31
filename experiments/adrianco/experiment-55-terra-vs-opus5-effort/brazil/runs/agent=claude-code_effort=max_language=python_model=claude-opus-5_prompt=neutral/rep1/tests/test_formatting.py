"""Rendering of results as text.

Context
-------
Feature: Readable answers

  Scenario: An answer is quoted back to a user
    Given a query result
    When it is formatted
    Then it follows the layouts shown in the specification
    And partial data (missing score, missing round) never breaks rendering
"""

from __future__ import annotations

import pytest

from brazilian_soccer import formatting, queries


class TestMatchRendering:
    """Scenario: Match lists follow the specification's layout."""

    def test_given_matches_when_formatted_then_each_line_has_date_score_context(self, graph):
        """
        Given a list of matches
        When it is formatted
        Then every line reads "date: Home X-Y Away (competition, round)"
        """
        text = formatting.format_matches(
            queries.find_matches(graph, team="Flamengo", opponent="Fluminense", limit=3)
        )
        lines = [line for line in text.splitlines() if line.startswith("- ")]

        assert len(lines) == 3
        for line in lines:
            assert line[2:12].count("-") == 2  # ISO date
            assert "Flamengo" in line and "Fluminense" in line
            assert "(" in line and ")" in line

    def test_given_a_match_without_a_score_when_formatted_then_it_says_so(self):
        """
        Given a fixture whose score is missing from the dataset
        When it is formatted
        Then the line says the score is unavailable instead of showing 0-0
        """
        line = formatting.match_line(
            {
                "date": "2016-12-11",
                "home_team": "Chapecoense",
                "away_team": "Atlético Mineiro",
                "home_goals": None,
                "away_goals": None,
                "competition": "Brasileirão Série A",
                "season": 2016,
            }
        )

        assert "no score in dataset" in line
        assert "0-0" not in line

    def test_given_a_head_to_head_when_formatted_then_the_summary_line_appears(self, graph):
        """
        Given two clubs
        When their matches are formatted
        Then the specification's head-to-head summary line is included
        """
        text = formatting.format_matches(
            queries.find_matches(graph, team="Gremio", opponent="Internacional", limit=2)
        )

        assert "Head-to-head in dataset:" in text
        assert "wins" in text and "draws" in text


class TestTableRendering:
    """Scenario: Tables and statistics follow the specification's layout."""

    def test_given_standings_when_formatted_then_rows_match_the_spec_shape(self, graph):
        """
        Given a calculated league table
        When it is formatted
        Then rows read "1. Flamengo - 90 pts (28W, 6D, 4L) ... - Champion"
        """
        text = formatting.format_standings(queries.standings(graph, "Serie A", 2019))
        first = text.splitlines()[1]

        assert first.startswith("1. Flamengo")
        assert "90 pts" in first
        assert "(28W, 6D, 4L)" in first
        assert first.endswith("Champion")

    def test_given_team_stats_when_formatted_then_the_spec_fields_are_present(self, graph):
        """
        Given a club's record for a season
        When it is formatted
        Then matches, wins/draws/losses, goals and win rate are all shown
        """
        text = formatting.format_team_stats(
            queries.team_stats(
                graph, "Corinthians", season=2022, competition="Serie A", home_away="home"
            )
        )

        assert "- Matches: 19" in text
        assert "Wins:" in text and "Draws:" in text and "Losses:" in text
        assert "Goals For:" in text and "Goals Against:" in text
        assert "win rate:" in text.lower()

    def test_given_players_when_formatted_then_they_are_numbered_with_ratings(self, graph):
        """
        Given a player search result
        When it is formatted
        Then players are numbered with rating, position and club
        """
        text = formatting.format_players(
            queries.search_players(graph, nationality="Brazil", limit=3)
        )

        assert "1. Neymar Jr - Overall: 92" in text
        assert "Position:" in text and "Club:" in text

    def test_given_a_bracket_when_formatted_then_ties_show_aggregates(self, graph):
        """
        Given a cup bracket
        When it is formatted
        Then each tie shows its aggregate and who advanced
        """
        text = formatting.format_bracket(
            queries.knockout_bracket(graph, "Libertadores", 2018)
        )

        assert "Final" in text
        assert "aggregate" in text
        assert "Winner: River Plate" in text


class TestErrorRendering:
    """Scenario: Failures are explained, not raised."""

    def test_given_an_error_result_when_formatted_then_suggestions_are_offered(self, graph):
        """
        Given a query for a club that does not exist
        When the result is formatted
        Then the message explains the miss and offers alternatives
        """
        text = formatting.format_team_stats(queries.team_stats(graph, "Real Madrid"))

        assert "No team" in text

    def test_given_an_unknown_kind_when_dispatching_then_it_fails_loudly(self):
        """
        Given a formatter name that does not exist
        When it is dispatched
        Then a KeyError names the missing formatter
        """
        with pytest.raises(KeyError):
            formatting.format_result("nope", {})

    @pytest.mark.parametrize(
        "kind, result",
        [
            ("matches", {"error": "boom", "suggestions": ["a", "b"]}),
            ("standings", {"error": "boom", "suggestions": []}),
            ("players", {"error": "boom", "suggestions": ["x"]}),
            ("bracket", {"error": "boom", "suggestions": []}),
            ("team_squad", {"error": "boom", "suggestions": []}),
        ],
    )
    def test_given_any_formatter_when_given_an_error_then_it_renders_text(self, kind, result):
        """
        Given any formatter
        When it receives an error payload
        Then it renders a short message rather than raising
        """
        text = formatting.format_result(kind, result)

        assert "boom" in text
