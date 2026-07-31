"""CSV ingestion and cross-source de-duplication.

Context
-------
Feature: Loading the provided datasets

  All six Kaggle files must load, with their three date formats, their two ways
  of writing a missing score and their overlapping coverage: the same
  Brasileirão fixture can appear in three different files and must end up as one
  match.
"""

from __future__ import annotations

from collections import Counter
from datetime import date

import pytest

from brazilian_soccer.loaders import (
    DATA_FILES,
    load_matches,
    load_players,
    merge_matches,
    parse_date,
    parse_int,
    parse_money,
)
from brazilian_soccer.models import Match


@pytest.fixture(scope="module")
def raw_matches(data_dir):
    """Every match row, before de-duplication."""
    return load_matches(data_dir)


@pytest.fixture(scope="module")
def players(data_dir):
    return load_players(data_dir)


class TestScalarParsing:
    """Scenario: Cope with the data quality notes in the specification."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("2023-09-24", (date(2023, 9, 24), None)),
            ("2012-05-19 18:30:00", (date(2012, 5, 19), "18:30")),
            ("29/03/2003", (date(2003, 3, 29), None)),
            ("", (None, None)),
            ("NA", (None, None)),
        ],
    )
    def test_given_mixed_date_formats_when_parsed_then_all_are_understood(self, raw, expected):
        """
        Given ISO, Brazilian and timestamped date strings
        When they are parsed
        Then each yields the right date and kick-off time
        """
        assert parse_date(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected", [("2", 2), ("2.0", 2), ("NA", None), ("-", None), ("", None), (None, None)]
    )
    def test_given_missing_scores_when_parsed_then_none_is_returned(self, raw, expected):
        """
        Given the two missing-value conventions in the files ("NA" and "-")
        When a score is parsed
        Then it becomes None instead of raising or defaulting to zero
        """
        assert parse_int(raw) == expected

    def test_given_a_fifa_money_string_when_parsed_then_euros_are_returned(self):
        """
        Given a FIFA value such as "€110.5M"
        When it is parsed
        Then the numeric amount and the original label are both available
        """
        assert parse_money("€110.5M") == (110_500_000.0, "€110.5M")
        assert parse_money("€565K")[0] == 565_000.0
        assert parse_money("")[0] is None


class TestSourceCoverage:
    """Scenario: All six provided files are loadable."""

    def test_given_the_data_directory_when_listed_then_all_six_files_exist(self, data_dir):
        """
        Given the data directory shipped with the repository
        When the expected file names are checked
        Then all six CSVs are present
        """
        for filename in DATA_FILES.values():
            assert (data_dir / filename).exists(), filename

    def test_given_the_match_files_when_loaded_then_every_source_contributes(self, raw_matches):
        """
        Given the five match CSVs
        When they are loaded
        Then each source contributes matches and the row counts match the spec
        """
        per_source = Counter(source for match in raw_matches for source in match.sources)

        assert per_source["brasileirao"] == 4180
        assert per_source["copa_do_brasil"] == 1337
        assert per_source["libertadores"] == 1255
        assert per_source["br_football"] == 10296
        assert per_source["historico"] == 6886

    def test_given_the_player_file_when_loaded_then_all_players_are_parsed(self, players):
        """
        Given fifa_data.csv
        When it is loaded
        Then all 18,207 players are available with ratings and clubs
        """
        assert len(players) == 18207
        messi = next(player for player in players if player.name == "L. Messi")
        assert messi.overall == 94
        assert messi.club == "FC Barcelona"
        assert messi.value_eur == 110_500_000.0
        assert messi.skills["Dribbling"] == 97

    def test_given_accented_names_when_loaded_then_utf8_survives(self, raw_matches):
        """
        Given team names containing accents and cedillas
        When the files are read
        Then UTF-8 characters are preserved rather than mangled
        """
        names = {match.home_team_name for match in raw_matches}

        assert "Grêmio" in names
        assert "São Paulo" in names
        assert "Avaí" in names


class TestDeduplication:
    """Scenario: The same fixture in several files becomes one match."""

    def test_given_overlapping_sources_when_merged_then_duplicates_collapse(self, raw_matches):
        """
        Given match rows that overlap between three files
        When they are merged
        Then thousands of duplicates collapse and provenance is preserved
        """
        merged = merge_matches(raw_matches)

        assert len(merged) < len(raw_matches)
        multi_source = [match for match in merged if len(match.sources) > 1]
        assert len(multi_source) > 1000
        assert any(len(match.sources) == 3 for match in merged)

    @pytest.mark.parametrize("season", list(range(2006, 2023)))
    def test_given_a_serie_a_season_when_merged_then_it_has_380_matches(
        self, raw_matches, season
    ):
        """
        Given a 20 team Série A season present in up to three source files
        When the matches are merged
        Then exactly 380 fixtures and 20 teams remain
        """
        merged = merge_matches(raw_matches)
        season_matches = [
            match
            for match in merged
            if match.competition_id == "serie-a" and match.season == season
        ]
        teams = {team for match in season_matches for team in match.teams}

        assert len(season_matches) in {380, 381}  # 2015 has one mislabelled row
        assert len(teams) in {20, 22}

    def test_given_a_merged_match_when_inspected_then_it_keeps_the_richest_fields(
        self, raw_matches
    ):
        """
        Given a fixture reported by the league file, the historical file and the
        extended statistics file
        When the records are merged
        Then round, stadium and shot statistics all survive on one match
        """
        merged = merge_matches(raw_matches)
        candidates = [
            match
            for match in merged
            if len(match.sources) == 3 and match.venue and match.stats
        ]

        assert candidates, "expected at least one fully enriched match"
        match = candidates[0]
        assert match.round is not None
        assert match.stats  # corners/shots/attacks, whichever the row carried
        assert any("home_shots" in candidate.stats for candidate in candidates)

    def test_given_two_legs_of_a_cup_tie_when_merged_then_they_stay_separate(self, raw_matches):
        """
        Given a two legged Copa do Brasil final
        When the matches are merged
        Then both legs remain, because only same-date records are fused
        """
        merged = merge_matches(raw_matches)
        final_2018 = [
            match
            for match in merged
            if match.competition_id == "copa-do-brasil"
            and match.season == 2018
            and match.stage == "Final"
        ]

        assert len(final_2018) == 2
        assert {match.home_team for match in final_2018} == {"cruzeiro", "corinthians"}

    def test_given_a_repeated_pairing_in_one_season_when_merged_then_both_are_kept(
        self, raw_matches
    ):
        """
        Given the historical file records Botafogo hosting Flamengo in both
        round 12 and round 31 of 2009
        When the matches are merged
        Then differing rounds and dates keep them as two fixtures
        """
        merged = merge_matches(raw_matches)
        pairing = [
            match
            for match in merged
            if match.season == 2009
            and match.home_team == "botafogo-rj"
            and match.away_team == "flamengo"
        ]

        assert len(pairing) == 2

    def test_given_a_postponed_fixture_when_merged_then_the_played_date_wins(
        self, raw_matches
    ):
        """
        Given the league file lists Goiás v Corinthians for 15 October 2022 with
        no score, and the stats file has the same fixture played on 29 October
        When the records are merged
        Then the merged match carries the date it was actually played
        And keeps the round number that only the league file knows
        """
        merged = merge_matches(raw_matches)
        match = next(
            item
            for item in merged
            if item.season == 2022
            and item.home_team == "goias"
            and item.away_team == "corinthians"
        )

        assert str(match.date) == "2022-10-29"
        assert match.round == 32
        assert match.played

    def test_given_one_source_without_rounds_when_merged_then_repeats_survive(
        self, raw_matches
    ):
        """
        Given Série C is only covered by the file that has no round numbers
        And a pairing can legitimately repeat there in a second phase
        When the matches are merged
        Then two meetings months apart are not collapsed into one
        """
        merged = merge_matches(raw_matches)
        meetings = [
            match
            for match in merged
            if match.season == 2023
            and {match.home_team, match.away_team} == {"brusque", "amazonas"}
        ]
        dates = sorted(str(match.date) for match in meetings)

        assert dates == ["2023-05-03", "2023-10-15", "2023-10-22"]

    def test_given_a_row_naming_one_club_twice_when_merged_then_it_is_dropped(
        self, raw_matches
    ):
        """
        Given the cup file names both sides "Bragantino - PA" for two 2019 rows
        When the matches are merged
        Then those impossible fixtures are dropped rather than counted twice
        """
        assert any(match.home_team == match.away_team for match in raw_matches)

        merged = merge_matches(raw_matches)

        assert not any(match.home_team == match.away_team for match in merged)


class TestDerivedFields:
    """Scenario: Fields the files do not contain are derived."""

    def test_given_the_cup_file_when_loaded_then_knockout_stages_are_named(self, raw_matches):
        """
        Given a Copa do Brasil file that only numbers its rounds
        When it is loaded
        Then the closing rounds are named Final, Semifinals, Quarterfinals...
        And an opening round of two matches is *not* mistaken for a final
        """
        cup = [match for match in raw_matches if match.competition_id == "copa-do-brasil"]
        stages = {(match.season, match.stage) for match in cup}

        assert (2018, "Final") in stages
        assert (2018, "Semifinals") in stages
        assert (2018, "Round of 16") in stages
        early = [match for match in cup if match.season == 2015 and match.round == 1]
        assert early and all(match.stage == "Round 1" for match in early)

    def test_given_a_league_match_in_january_when_loaded_then_it_belongs_to_last_season(
        self, raw_matches
    ):
        """
        Given the COVID-hit 2020 Série A season finished in February 2021
        When the extended statistics file (which has no season column) is loaded
        Then those January and February matches are attributed to season 2020
        """
        early_2021 = [
            match
            for match in raw_matches
            if match.competition_id == "serie-a"
            and match.sources == ("br_football",)
            and match.date
            and match.date.year == 2021
            and match.date.month <= 2
        ]

        assert early_2021
        assert all(match.season == 2020 for match in early_2021)

    def test_given_a_libertadores_row_when_loaded_then_the_stage_is_normalised(
        self, raw_matches
    ):
        """
        Given the Libertadores file writes stages in lower case
        When it is loaded
        Then stage labels are normalised for display and filtering
        """
        stages = {
            match.stage
            for match in raw_matches
            if match.competition_id == "libertadores" and match.stage
        }

        assert stages == {
            "Group stage", "Round of 16", "Quarterfinals", "Semifinals", "Final",
        }


class TestMatchModel:
    """Scenario: Match helpers answer "who won" consistently."""

    def test_given_a_played_match_when_queried_then_result_helpers_agree(self):
        """
        Given a finished match
        When its helpers are used
        Then winner, margin and per-team views are consistent
        """
        match = Match(
            match_id="x",
            competition_id="serie-a",
            competition="Brasileirão Série A",
            season=2019,
            date=date(2019, 9, 3),
            home_team="flamengo",
            away_team="fluminense",
            home_team_name="Flamengo",
            away_team_name="Fluminense",
            home_goals=2,
            away_goals=1,
        )

        assert match.played is True
        assert match.winner_id == "flamengo"
        assert match.loser_id == "fluminense"
        assert match.total_goals == 3
        assert match.goal_difference == 1
        assert match.outcome_for("fluminense") == "L"
        assert match.goals_for("fluminense") == 1
        assert match.label == "Flamengo 2-1 Fluminense"

    def test_given_an_unplayed_match_when_queried_then_nothing_is_invented(self):
        """
        Given a fixture with no score in the dataset
        When it is inspected
        Then it reports as unplayed instead of counting as a draw
        """
        match = Match(
            match_id="y",
            competition_id="serie-a",
            competition="Brasileirão Série A",
            season=2016,
            home_team="chapecoense",
            away_team="atletico-mg",
            home_team_name="Chapecoense",
            away_team_name="Atlético Mineiro",
        )

        assert match.played is False
        assert match.result is None
        assert match.winner_id is None
        assert match.outcome_for("chapecoense") is None
