"""Feature: Loading the six CSV files into one consistent dataset.

These scenarios use the synthetic fixture data, where the expected result of
every merge is known by construction, plus a few coverage checks against the
real files.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.loader import (
    BRASILEIRAO_FILE,
    BR_FOOTBALL_FILE,
    CUP_FILE,
    DataLoadError,
    FIFA_FILE,
    LIBERTADORES_FILE,
    NOVO_FILE,
    load_dataset,
)
from brazilian_soccer.normalization import BRASILEIRAO, COPA_DO_BRASIL, SERIE_B


def find_match(dataset, home, away, season=None):
    registry = dataset.registry
    for match in dataset.matches:
        if (registry.name_of(match.home_team) == home
                and registry.name_of(match.away_team) == away
                and (season is None or match.season == season)):
            return match
    return None


class TestCrossFileMerging:
    """Feature: The same fixture in several files becomes one match."""

    def test_duplicate_fixture_is_merged_not_repeated(self, synthetic_dataset):
        """
        Given the same Flamengo v São Paulo fixture in three source files
        When the dataset is loaded
        Then exactly one match exists and it lists all three sources
        """
        matches = [m for m in synthetic_dataset.matches
                   if m.competition == BRASILEIRAO and m.season == 2019
                   and synthetic_dataset.registry.name_of(m.home_team) == "Flamengo"]

        assert len(matches) == 1
        match = matches[0]
        assert set(match.sources) == {BRASILEIRAO_FILE, NOVO_FILE, BR_FOOTBALL_FILE}

    def test_merging_keeps_the_richest_fields(self, synthetic_dataset):
        """
        Given one file with the round, one with the stadium and one with shots
        When the records are merged
        Then the merged match carries all three
        """
        match = find_match(synthetic_dataset, "Flamengo", "São Paulo", 2019)

        assert match.round == "1"
        assert match.venue == "Maracanã"          # only novo_campeonato has it
        assert match.stats["home_shots"] == 12    # only BR-Football has it
        assert (match.home_goals, match.away_goals) == (2, 1)

    def test_distinct_fixtures_are_not_merged(self, synthetic_dataset):
        """
        Given the home and away legs of the same pairing
        When the dataset is loaded
        Then both matches are kept
        """
        first = find_match(synthetic_dataset, "Flamengo", "São Paulo", 2019)
        second = find_match(synthetic_dataset, "São Paulo", "Flamengo", 2019)

        assert first is not None and second is not None
        assert first.match_id != second.match_id


class TestSeasonHandling:
    """Feature: Seasons are derived correctly for date-only sources."""

    def test_january_league_match_belongs_to_the_previous_season(self, synthetic_dataset):
        """
        Given a Série B match played in January 2020
        When the season is derived from the date
        Then it counts towards the 2019 season, which ran into the new year
        """
        match = find_match(synthetic_dataset, "Vitória", "Ceará")

        assert match.competition == SERIE_B
        assert match.date.year == 2020
        assert match.season == 2019

    def test_explicit_season_columns_win(self, synthetic_dataset):
        match = find_match(synthetic_dataset, "Grêmio", "Atlético Mineiro", 2005)
        assert match.season == 2005


class TestUnplayedAndMissingData:
    """Feature: Rows with missing scores or dates do not break loading."""

    def test_match_without_a_score_is_kept_but_marked_unplayed(self, synthetic_dataset):
        """
        Given a Libertadores row with "-" scores and no date
        When the dataset is loaded
        Then the match exists but reports itself as not played
        """
        match = find_match(synthetic_dataset, "Palmeiras", "Boca Juniors")

        assert match is not None
        assert match.played is False
        assert match.result is None
        assert match.winner is None


class TestPlayerLoading:
    """Feature: FIFA players are linked to clubs in the graph."""

    def test_players_are_linked_to_canonical_clubs(self, synthetic_dataset):
        """
        Given FIFA records whose Club column matches a club in the match data
        When players are loaded
        Then the player carries the canonical team id
        """
        players = {p.name: p for p in synthetic_dataset.players}

        assert players["Ronaldinho"].club_team_id == "flamengo"
        assert players["João Silva"].club_team_id == "gremio"
        assert players["Ronaldinho"].skills["Dribbling"] == 94
        assert players["Ronaldinho"].jersey_number == 10
        assert players["Ronaldinho"].preferred_foot == "Right"


class TestRealDataCoverage:
    """Feature: All six provided files are loaded and queryable."""

    def test_every_source_file_contributes_rows(self, dataset):
        """
        Given the six Kaggle files
        When the dataset is loaded
        Then each file contributes the number of rows documented in the spec
        """
        counts = dataset.source_counts

        assert counts[BRASILEIRAO_FILE] == 4180
        assert counts[CUP_FILE] == 1337
        assert counts[LIBERTADORES_FILE] == 1255
        assert counts[BR_FOOTBALL_FILE] == 10296
        assert counts[NOVO_FILE] == 6886
        assert counts[FIFA_FILE] == 18207

    def test_overlapping_rows_are_deduplicated(self, dataset):
        """
        Given 23,954 match rows across five files with heavy overlap
        When they are merged
        Then far fewer unique matches remain and no fixture is listed twice

        A pairing can legitimately recur inside one season (Libertadores group
        stage then knockout), so the identity of a match includes its date.
        """
        rows = sum(count for name, count in dataset.source_counts.items()
                   if name != FIFA_FILE)
        assert 15_000 < len(dataset.matches) < rows - 5_000

        seen = set()
        for match in dataset.matches:
            key = (match.competition, match.season, match.home_team,
                   match.away_team, match.date)
            assert key not in seen, f"duplicate fixture: {key}"
            seen.add(key)

    def test_a_serie_a_season_has_no_repeated_pairing(self, dataset):
        """
        Given a league season where each pairing is played once per venue
        When the 2019 Série A fixtures are listed
        Then every (home, away) pair appears exactly once
        """
        pairs = [(m.home_team, m.away_team) for m in dataset.matches
                 if m.competition == BRASILEIRAO and m.season == 2019]

        assert len(pairs) == 380
        assert len(set(pairs)) == 380

    def test_serie_a_seasons_have_the_expected_number_of_matches(self, dataset):
        """
        Given the 20-team Série A format used since 2006
        When matches are counted per season
        Then each season has ~380 matches, proving de-duplication worked
        """
        counts = {}
        for match in dataset.matches:
            if match.competition == BRASILEIRAO and match.season:
                counts[match.season] = counts.get(match.season, 0) + 1

        for season in range(2006, 2023):
            assert 375 <= counts[season] <= 385, (season, counts[season])

    def test_cup_stages_are_named(self, dataset):
        """
        Given a Copa do Brasil file that only numbers its rounds
        When the data is loaded
        Then the late rounds are named final/semifinals/quarterfinals
        """
        stages = {m.stage for m in dataset.matches
                  if m.competition == COPA_DO_BRASIL and m.stage}

        assert {"final", "semifinals", "quarterfinals", "round of 16"} <= stages
        finals = [m for m in dataset.matches
                  if m.competition == COPA_DO_BRASIL and m.stage == "final"]
        # Two-legged finals: an even number, at most two per season.
        assert len(finals) % 2 == 0
        for season in {m.season for m in finals}:
            assert sum(1 for m in finals if m.season == season) == 2

    def test_no_club_plays_itself(self, dataset):
        """
        Given one cup row names the same club home and away
        When the data is loaded
        Then that row is dropped, because it would count twice for the club
        """
        assert [m for m in dataset.matches if m.home_team == m.away_team] == []

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(DataLoadError):
            load_dataset(tmp_path / "nope")
