"""Competition queries: standings, brackets and aggregates (spec section 4).

Context
-------
Feature: Competition Queries

  Scenario: Calculate a final league table
    Given the match data is loaded
    When I ask who won the 2019 Brasileirão
    Then a table calculated from results is returned
    And the champion and the relegated clubs are identified

Every champion and relegation set asserted here matches the real historical
record, which is the strongest available check that name resolution and
cross-file de-duplication are both correct: a single duplicated fixture or a
split club node would move the table.
"""

from __future__ import annotations

import pytest

from brazilian_soccer import queries

#: (season, champion, relegated) as they really happened.
KNOWN_SEASONS = [
    (2003, "Cruzeiro", {"Juventude", "Fluminense", "Fortaleza", "Bahia"}),
    (2009, "Flamengo", {"Coritiba", "Santo André", "Náutico", "Sport Recife"}),
    (2016, "Palmeiras", {"Internacional", "Figueirense", "Santa Cruz", "América-MG"}),
    (2019, "Flamengo", {"Cruzeiro", "Chapecoense", "CSA", "Avaí"}),
    (2022, "Palmeiras", {"Ceará", "Atlético Goianiense", "Avaí", "Juventude"}),
]


def _name(entry: str) -> str:
    """Strip the "(SP)" state suffix used in display names."""
    return entry.split(" (")[0]


class TestStandings:
    """Scenario: League tables calculated from match results."""

    def test_given_2019_when_the_table_is_calculated_then_flamengo_won_with_90_points(
        self, graph
    ):
        """
        Given the match data is loaded
        When I ask who won the 2019 Brasileirão
        Then Flamengo top the table with 90 points from 28 wins
        And the four relegated clubs are identified
        """
        result = queries.standings(graph, "Brasileirão", 2019)
        champion = result["table"][0]

        assert result["matches"] == 380
        assert result["complete"] is True
        assert _name(champion["team"]) == "Flamengo"
        assert champion["points"] == 90
        assert (champion["wins"], champion["draws"], champion["losses"]) == (28, 6, 4)
        assert champion["goals_for"] == 86 and champion["goals_against"] == 37
        assert {_name(team) for team in result["relegated"]} == {
            "Cruzeiro", "Chapecoense", "CSA", "Avaí",
        }

    @pytest.mark.parametrize("season, champion, relegated", KNOWN_SEASONS)
    def test_given_a_finished_season_when_calculated_then_history_is_reproduced(
        self, graph, season, champion, relegated
    ):
        """
        Given a completed Série A season
        When its table is calculated from the merged match data
        Then the champion and the relegated clubs match the historical record
        """
        result = queries.standings(graph, "Serie A", season)

        assert _name(result["champion"]) == champion
        assert {_name(team) for team in result["relegated"]} == relegated

    def test_given_a_table_when_calculated_then_points_and_matches_are_consistent(self, graph):
        """
        Given a calculated league table
        When it is checked
        Then points follow the 3-1-0 rule and goals scored equal goals conceded
        """
        result = queries.standings(graph, "Serie A", 2021)
        rows = result["table"]

        assert len(rows) == 20
        assert sum(row["played"] for row in rows) == 2 * result["matches"]
        assert sum(row["goals_for"] for row in rows) == sum(row["goals_against"] for row in rows)
        for row in rows:
            assert row["points"] == row["wins"] * 3 + row["draws"]
            assert row["played"] == row["wins"] + row["draws"] + row["losses"]
        points = [row["points"] for row in rows]
        assert points == sorted(points, reverse=True)

    def test_given_an_incomplete_season_when_calculated_then_no_champion_is_asserted(
        self, graph
    ):
        """
        Given the 2023 season is truncated in the source data
        When its table is calculated
        Then the table is still returned but no champion is claimed
        """
        result = queries.standings(graph, "Serie A", 2023)

        assert result["complete"] is False
        assert "champion" not in result
        assert any("incomplete" in note for note in result["notes"])

    def test_given_a_mislabelled_fixture_when_calculating_then_outliers_are_dropped(
        self, graph
    ):
        """
        Given the extended statistics file mislabels one Campeonato Brasiliense
        match as Série A
        When the 2015 table is calculated
        Then Brasília and Taguatinga are excluded as outliers, with a note
        """
        result = queries.standings(graph, "Serie A", 2015)
        teams = {_name(row["team"]) for row in result["table"]}

        assert len(result["table"]) == 20
        assert "Brasília" not in teams and "Taguatinga" not in teams
        assert any("outlier" in note for note in result["notes"])

    def test_given_a_cup_when_a_table_is_requested_then_it_is_refused(self, graph):
        """
        Given a knockout competition has no league table
        When standings are requested for the Copa do Brasil
        Then the request is refused and the bracket tool is suggested
        """
        result = queries.standings(graph, "Copa do Brasil", 2019)

        assert "error" in result
        assert "knockout_bracket" in result["suggestions"]

    def test_given_a_season_without_data_when_requested_then_options_are_offered(self, graph):
        """
        Given a season that is not covered
        When standings are requested
        Then the available seasons are listed
        """
        result = queries.standings(graph, "Serie A", 1975)

        assert "error" in result
        assert "2019" in result["suggestions"]

    def test_given_serie_b_when_calculated_then_it_also_works(self, graph):
        """
        Given the extended statistics file also covers Série B
        When its 2017 table is calculated
        Then a complete 20 team table is produced
        """
        result = queries.standings(graph, "Serie B", 2017)

        assert len(result["table"]) == 20
        assert result["complete"] is True

    def test_given_a_season_missing_a_fixture_when_calculated_then_it_says_which(self, graph):
        """
        Given Série B 2022 is missing the CRB v Sampaio Corrêa fixture
        When its table is calculated
        Then the season is not declared complete
        And the note names the clubs that are short of matches
        """
        result = queries.standings(graph, "Serie B", 2022)

        assert len(result["table"]) == 20
        assert result["complete"] is False
        note = next(note for note in result["notes"] if "incomplete" in note)
        assert "CRB" in note and "Sampaio" in note

    def test_given_the_wins_tiebreak_when_ordering_then_it_beats_goal_difference(self, graph):
        """
        Given the CBF ranks equal-point clubs on wins before goal difference
        When the 2019 table is calculated
        Then Santos (22 wins) finish above Palmeiras (21 wins) on 74 points each
        And the same criterion sends Luverdense down instead of Guarani in 2017
        """
        table = queries.standings(graph, "Serie A", 2019)["table"]
        second, third = table[1], table[2]

        assert second["points"] == third["points"] == 74
        assert _name(second["team"]) == "Santos" and second["wins"] == 22
        assert _name(third["team"]) == "Palmeiras" and third["wins"] == 21

        relegated = queries.standings(graph, "Serie B", 2017)["relegated"]
        assert "Luverdense" in {_name(team) for team in relegated}
        assert "Guarani" not in {_name(team) for team in relegated}


class TestKnockoutBracket:
    """Scenario: Cup brackets with aggregated ties."""

    def test_given_the_2018_libertadores_when_bracketed_then_river_plate_won(self, graph):
        """
        Given the question "show the 2018 Copa Libertadores bracket"
        When the bracket is built
        Then every stage appears in order and the winner is identified
        """
        result = queries.knockout_bracket(graph, "Libertadores", 2018)
        stages = [stage["stage"] for stage in result["stages"]]

        assert stages == [
            "Group stage", "Round of 16", "Quarterfinals", "Semifinals", "Final",
        ]
        assert result["champion"] == "River Plate"

    def test_given_a_two_legged_tie_when_aggregated_then_the_winner_is_derived(self, graph):
        """
        Given ties played over two legs
        When the bracket aggregates them
        Then each tie shows both legs, the aggregate score and who advanced
        """
        result = queries.knockout_bracket(graph, "Copa do Brasil", 2019)
        final = next(stage for stage in result["stages"] if stage["stage"] == "Final")
        tie = final["ties"][0]

        assert len(tie["legs"]) == 2
        assert sum(tie["aggregate"].values()) > 0
        assert _name(result["champion"]) == "Athletico Paranaense"

    def test_given_a_level_tie_when_aggregated_then_no_winner_is_invented(self, graph):
        """
        Given the datasets contain no penalty shootouts
        When a tie finishes level on aggregate
        Then no winner is claimed, the away goals split is shown for context,
        And the notes explain why away goals cannot simply be applied -- the 2015
        final finished 2-2 with Santos ahead on away goals, yet Palmeiras won it
        """
        result = queries.knockout_bracket(graph, "Copa do Brasil", 2015)
        final = next(stage for stage in result["stages"] if stage["stage"] == "Final")
        tie = final["ties"][0]

        assert tie["winner"] is None
        assert tie["aggregate"] == {"Palmeiras (SP)": 2, "Santos (SP)": 2}
        assert tie["away_goals"]["Santos (SP)"] > tie["away_goals"]["Palmeiras (SP)"]
        assert "not derivable" in tie["note"]
        assert any("penalties" in note for note in result["notes"])

    def test_given_a_decided_tie_when_aggregated_then_the_winner_is_named(self, graph):
        """
        Given a tie that the aggregate score settles
        When the bracket is built
        Then the winner is named and the reason is recorded
        """
        result = queries.knockout_bracket(graph, "Libertadores", 2018)
        final = next(stage for stage in result["stages"] if stage["stage"] == "Final")
        tie = final["ties"][0]

        assert tie["winner"] == "River Plate"
        assert tie["decided_by"] == "aggregate"

    def test_given_a_league_when_a_bracket_is_requested_then_it_is_refused(self, graph):
        """
        Given a league is a round robin, not a bracket
        When a bracket is requested for Série A
        Then the request is refused and the standings tool is suggested
        """
        result = queries.knockout_bracket(graph, "Serie A", 2019)

        assert "error" in result
        assert "standings" in result["suggestions"]

    def test_given_a_season_without_round_labels_when_bracketed_then_it_says_so(self, graph):
        """
        Given the 2022 Copa do Brasil only exists in the file with no round column
        When a bracket is requested
        Then the ties are still aggregated correctly
        And the answer explains that they are not arranged by stage
        """
        result = queries.knockout_bracket(graph, "Copa do Brasil", 2022)

        assert result["stages"] and result["stages"][0]["ties"]
        assert result["champion"] is None
        assert any("no round or stage labels" in note.lower() for note in result["notes"])

    def test_given_a_missing_season_when_bracketed_then_options_are_offered(self, graph):
        """
        Given a cup season that is not in the data
        When a bracket is requested
        Then the available seasons are listed
        """
        result = queries.knockout_bracket(graph, "Libertadores", 1999)

        assert "error" in result
        assert result["suggestions"]


class TestCompetitionStats:
    """Scenario: Aggregate competition statistics."""

    def test_given_a_competition_when_summarised_then_averages_are_reported(self, graph):
        """
        Given the question "what's the average goals per match in the Brasileirão?"
        When the competition is summarised
        Then goals per match, home advantage and biggest wins are reported
        """
        result = queries.competition_stats(graph, "Serie A")

        assert result["matches"] > 8_000
        assert 2.0 < result["goals_per_match"] < 3.0
        assert result["biggest_wins"]
        assert result["common_scorelines"][0]["score"]
        assert result["top_scoring_teams"]

    def test_given_a_season_when_summarised_then_only_it_is_counted(self, graph):
        """
        Given one season of a competition
        When it is summarised
        Then only that season's 380 matches are aggregated
        """
        result = queries.competition_stats(graph, "Serie A", 2019)

        assert result["matches"] == 380
        assert result["season"] == 2019

    def test_given_no_scorer_data_when_summarised_then_the_gap_is_declared(self, graph):
        """
        Given the files contain no goalscorer information
        When a competition is summarised
        Then the answer says top scorers cannot be derived
        """
        result = queries.competition_stats(graph, "Serie A", 2019)

        assert any("top" in note and "scorer" in note for note in result["notes"])

    def test_given_an_unknown_competition_when_summarised_then_options_are_offered(
        self, graph
    ):
        """
        Given a competition that is not in the data
        When statistics are requested
        Then the known competitions are listed
        """
        result = queries.competition_stats(graph, "Premier League")

        assert "error" in result
        assert "Copa do Brasil" in result["suggestions"]


class TestOverview:
    """Scenario: Describe the coverage of the datasets."""

    def test_given_the_graph_when_described_then_all_files_are_accounted_for(self, graph):
        """
        Given the six provided CSVs
        When the dataset overview is requested
        Then every competition, its seasons and the file list are reported
        """
        result = queries.dataset_overview(graph)
        competitions = {item["competition"] for item in result["competitions"]}

        assert competitions == {
            "Brasileirão Série A",
            "Brasileirão Série B",
            "Brasileirão Série C",
            "Copa do Brasil",
            "Copa Libertadores",
        }
        assert len(result["summary"]["source_files"]) == 6
        assert result["linked_fifa_clubs"]
        assert result["top_nationalities"][0]["players"] > 100

    def test_given_rows_the_loader_refused_when_described_then_it_owns_up(self, graph):
        """
        Given two cup rows name the same club on both sides and are dropped
        When the dataset overview is requested
        Then the discarded rows are declared rather than quietly disappearing
        """
        result = queries.dataset_overview(graph)

        assert result["summary"]["dropped_rows"] == {"club listed as its own opponent": 2}
        assert any("dropped as impossible" in note for note in result["notes"])
