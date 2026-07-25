"""Feature: Competition queries.

  Scenario: Calculate a season's standings from match results
    Given the match data is loaded
    When I request the 2019 Brasileirão table
    Then Flamengo are champions on 90 points
    And the bottom four are marked as relegated
"""

from __future__ import annotations

from brazilian_soccer import queries as q
from brazilian_soccer.formatting import (
    format_bracket,
    format_competition_summary,
    format_competitions,
    format_standings,
)
from brazilian_soccer.normalization import BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES


class TestStandings:

    def test_2019_brasileirao_matches_the_real_table(self, graph):
        """
        Given the 2019 Série A results
        When the table is calculated from them
        Then it reproduces the real final standings
        """
        result = q.standings(graph, "Brasileirão", 2019)
        table = result["table"]

        assert result["complete"] is True
        assert result["champion"] == "Flamengo"
        assert table[0]["points"] == 90
        assert table[0]["wins"] == 28
        assert [row["team"] for row in table[:3]] == ["Flamengo", "Santos", "Palmeiras"]
        assert table[-1]["team"] == "Avaí"
        assert result["relegated"] == ["Cruzeiro", "CSA", "Chapecoense", "Avaí"]

    def test_every_champion_from_2003_to_2022_is_correct(self, graph):
        """
        Given the real Série A champions of twenty seasons
        When each table is calculated from the merged match data
        Then the calculated champion matches history every time

        This is the strongest single check that de-duplication, team-name
        resolution and season attribution are all working.
        """
        real_champions = {
            2003: "Cruzeiro", 2004: "Santos", 2005: "Corinthians",
            2006: "São Paulo", 2007: "São Paulo", 2008: "São Paulo",
            2009: "Flamengo", 2010: "Fluminense", 2011: "Corinthians",
            2012: "Fluminense", 2013: "Cruzeiro", 2014: "Cruzeiro",
            2015: "Corinthians", 2016: "Palmeiras", 2017: "Corinthians",
            2018: "Palmeiras", 2019: "Flamengo", 2020: "Flamengo",
            2021: "Atlético Mineiro", 2022: "Palmeiras",
        }

        calculated = {
            season: q.standings(graph, "Brasileirão", season)["champion"]
            for season in real_champions
        }

        assert calculated == real_champions

    def test_2020_relegation(self, graph):
        """
        Given the pandemic-shifted 2020 season, which ran into February 2021
        When the table is calculated
        Then the four relegated clubs are correct despite the season spillover
        """
        result = q.standings(graph, "Brasileirão", 2020)

        assert result["champion"] == "Flamengo"
        assert set(result["relegated"]) == {"Vasco da Gama", "Goiás", "Coritiba",
                                            "Botafogo"}

    def test_table_arithmetic_is_internally_consistent(self, graph):
        """
        Given any calculated table
        When each row is checked
        Then points, matches and goals agree with each other and with the season
        """
        result = q.standings(graph, "Brasileirão", 2015)
        table = result["table"]

        assert len(table) == 20
        for row in table:
            assert row["points"] == row["wins"] * 3 + row["draws"]
            assert row["matches"] == row["wins"] + row["draws"] + row["losses"]
            assert row["goal_difference"] == row["goals_for"] - row["goals_against"]
        assert sum(row["goals_for"] for row in table) == sum(
            row["goals_against"] for row in table)
        assert sum(row["wins"] for row in table) == sum(
            row["losses"] for row in table)

    def test_ties_are_broken_by_wins_then_goal_difference(self, graph):
        """
        Given Santos and Palmeiras both finished 2019 on 74 points
        When the table is ordered
        Then Santos are placed higher because they won more matches
        """
        table = q.standings(graph, "Brasileirão", 2019)["table"]
        santos = next(row for row in table if row["team"] == "Santos")
        palmeiras = next(row for row in table if row["team"] == "Palmeiras")

        assert santos["points"] == palmeiras["points"] == 74
        assert santos["wins"] > palmeiras["wins"]
        assert santos["position"] < palmeiras["position"]

    def test_incomplete_season_is_not_declared(self, graph):
        """
        Given a season the dataset only covers partially
        When the table is calculated
        Then no champion or relegation is claimed
        """
        result = q.standings(graph, "Série C", 2014)

        assert result["complete"] is False
        assert result["champion"] is None
        assert result["relegated"] == []

    def test_no_champion_is_named_when_fixtures_are_missing(self, graph):
        """
        Given the 2023 Série A is three matches short in the source data
        And those matches could change who finishes top
        When the table is calculated
        Then it is reported as partial with the gap spelled out
        """
        result = q.standings(graph, "Brasileirão", 2023)

        assert result["complete"] is False
        assert result["champion"] is None
        assert result["missing_matches"] == 3
        assert "no champion is declared" in format_standings(result)

    def test_mislabelled_source_rows_are_kept_out_of_the_table(self, graph):
        """
        Given two state-league clubs mislabelled as Série A in one source file
        When the 2015 table is calculated
        Then they are excluded and a 20-team table is produced
        """
        result = q.standings(graph, "Brasileirão", 2015)

        assert result["teams"] == 20
        assert result["complete"] is True
        assert result["champion"] == "Corinthians"
        assert "Brasília" in result["excluded_teams"]

    def test_season_without_data_returns_an_empty_table(self, graph):
        result = q.standings(graph, "Brasileirão", 1994)

        assert result["table"] == []
        assert "no table can be calculated" in format_standings(result)

    def test_formatted_standings_follow_the_specification(self, graph):
        text = format_standings(q.standings(graph, "Brasileirão", 2019))

        assert "2019 Brasileirão Série A Final Standings" in text
        assert "1. Flamengo - 90 pts (28W, 6D, 4L)" in text
        assert "Champion" in text
        assert "Relegated:" in text


class TestCompetitionSummaries:

    def test_summary_of_a_single_season(self, graph):
        result = q.competition_summary(graph, "Copa do Brasil", season=2019)

        assert result["competition"] == COPA_DO_BRASIL
        assert result["matches"] > 100
        assert 1.5 < result["goals_per_match"] < 4.0
        assert 0 < result["home_win_rate"] < 100
        assert result["top_scoring_teams"]

    def test_summary_across_all_seasons(self, graph):
        """
        Given every Brasileirão match in the data
        When aggregate statistics are calculated
        Then goals per match and home win rate sit in plausible ranges
        """
        result = q.competition_summary(graph, "Brasileirão")

        assert result["seasons"][0] == 2003
        assert result["seasons"][-1] == 2023
        assert 2.0 < result["goals_per_match"] < 3.0
        assert 40 < result["home_win_rate"] < 60
        assert round(result["home_win_rate"] + result["draw_rate"]
                     + result["away_win_rate"]) == 100

    def test_list_of_competitions_covers_all_five(self, graph):
        result = q.list_competitions(graph)
        names = {row["competition"] for row in result["competitions"]}

        assert {BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES} <= names
        assert len(names) == 5
        text = format_competitions(result)
        assert "Knowledge graph:" in text
        assert "Source files:" in text

    def test_formatted_summary(self, graph):
        text = format_competition_summary(
            q.competition_summary(graph, "Brasileirão", season=2019))

        assert "Brasileirão Série A 2019" in text
        assert "per match" in text


class TestKnockoutBracket:

    def test_libertadores_bracket_is_grouped_by_stage(self, graph):
        """
        Given a Libertadores season
        When I ask for its bracket
        Then matches are grouped by stage, ordered from group stage to final
        """
        result = q.knockout_bracket(graph, "Libertadores", 2018)
        stages = list(result["stages"])

        assert stages[0] == "group stage"
        assert stages[-1] == "final"
        assert "quarterfinals" in stages and "semifinals" in stages
        assert all(m["competition"] == LIBERTADORES
                   for matches in result["stages"].values() for m in matches)

    def test_copa_do_brasil_bracket_names_its_rounds(self, graph):
        result = q.knockout_bracket(graph, "Copa do Brasil", 2019)

        assert "final" in result["stages"]
        assert len(result["stages"]["final"]) == 2

    def test_formatted_bracket_truncates_long_stages(self, graph):
        text = format_bracket(q.knockout_bracket(graph, "Libertadores", 2018))

        assert "Group Stage (96 matches):" in text
        assert "more)" in text
        assert "Final (" in text
