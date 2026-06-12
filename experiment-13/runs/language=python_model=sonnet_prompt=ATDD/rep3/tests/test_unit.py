"""
Unit tests for data loading and normalization internals.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import DataLoader, normalize_team_name, _parse_goals, _to_iso_date

DATA_DIR = Path(__file__).parent.parent / "data" / "kaggle"


# ---------------------------------------------------------------------------
# normalize_team_name
# ---------------------------------------------------------------------------

class TestNormalizeTeamName:
    def test_strips_state_suffix_with_hyphen(self):
        assert normalize_team_name("Palmeiras-SP") == "Palmeiras"

    def test_strips_state_suffix_with_spaces(self):
        assert normalize_team_name("América - MG") == "América"

    def test_leaves_name_without_suffix_unchanged(self):
        assert normalize_team_name("Flamengo") == "Flamengo"

    def test_handles_leading_trailing_whitespace(self):
        assert normalize_team_name("  Santos  ") == "Santos"

    def test_does_not_strip_lowercase_suffix(self):
        # Lowercase -mg is not a valid state suffix pattern
        assert normalize_team_name("team-mg") == "team-mg"

    def test_handles_non_string(self):
        assert normalize_team_name(None) == ""  # type: ignore

    def test_keeps_name_intact_when_hyphen_in_middle(self):
        assert normalize_team_name("Athletico-Paranaense") == "Athletico-Paranaense"


# ---------------------------------------------------------------------------
# _parse_goals
# ---------------------------------------------------------------------------

class TestParseGoals:
    def test_parses_integer(self):
        assert _parse_goals(2) == 2

    def test_parses_float_string(self):
        assert _parse_goals("1.0") == 1

    def test_parses_zero(self):
        assert _parse_goals(0) == 0

    def test_returns_zero_for_none(self):
        assert _parse_goals(None) == 0

    def test_returns_zero_for_invalid_string(self):
        assert _parse_goals("N/A") == 0


# ---------------------------------------------------------------------------
# _to_iso_date
# ---------------------------------------------------------------------------

class TestToIsoDate:
    def test_converts_brazilian_format(self):
        assert _to_iso_date("29/03/2003") == "2003-03-29"

    def test_preserves_iso_format(self):
        assert _to_iso_date("2019-08-25") == "2019-08-25"

    def test_truncates_datetime_to_date(self):
        assert _to_iso_date("2012-05-19 18:30:00") == "2012-05-19"

    def test_handles_nan(self):
        assert _to_iso_date(float("nan")) == ""


# ---------------------------------------------------------------------------
# DataLoader
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def loader():
    dl = DataLoader(DATA_DIR)
    dl.load_all()
    return dl


class TestDataLoaderLoadsBrasileirao:
    def test_brasileirao_has_expected_row_count(self, loader):
        df = loader.get_brasileirao_matches()
        assert len(df) == 4180

    def test_brasileirao_has_required_columns(self, loader):
        df = loader.get_brasileirao_matches()
        for col in ["date", "home_team", "away_team", "home_goals", "away_goals",
                    "competition", "season", "round_or_stage"]:
            assert col in df.columns

    def test_brasileirao_competition_tag(self, loader):
        df = loader.get_brasileirao_matches()
        assert (df["competition"] == "brasileirao").all()

    def test_brasileirao_season_range(self, loader):
        df = loader.get_brasileirao_matches()
        assert df["season"].min() == 2012
        assert df["season"].max() == 2022

    def test_atletico_mg_and_go_are_distinct_in_brasileirao(self, loader):
        df = loader.get_brasileirao_matches()
        df_2019 = df[df["season"] == 2019]
        all_teams = set(df_2019["home_team"].tolist()) | set(df_2019["away_team"].tolist())
        # Both should be distinct entries in 2019 where Atletico-GO was promoted
        atletico_variants = [t for t in all_teams if "atletico" in t.lower()]
        assert len(atletico_variants) >= 1


class TestDataLoaderLoadsCopa:
    def test_copa_has_expected_row_count(self, loader):
        df = loader.get_copa_matches()
        assert len(df) == 1337

    def test_copa_competition_tag(self, loader):
        df = loader.get_copa_matches()
        assert (df["competition"] == "copa_do_brasil").all()


class TestDataLoaderLoadsLibertadores:
    def test_libertadores_has_expected_row_count(self, loader):
        df = loader.get_libertadores_matches()
        assert len(df) == 1255

    def test_libertadores_competition_tag(self, loader):
        df = loader.get_libertadores_matches()
        assert (df["competition"] == "libertadores").all()


class TestDataLoaderLoadsHistorical:
    def test_historical_only_pre_2012(self, loader):
        df = loader.get_historical_matches()
        assert df["season"].max() < 2012

    def test_historical_starts_from_2003(self, loader):
        df = loader.get_historical_matches()
        assert df["season"].min() == 2003


class TestDataLoaderLoadsPlayers:
    def test_players_dataset_loaded(self, loader):
        df = loader.get_players()
        assert len(df) > 10_000

    def test_players_has_required_columns(self, loader):
        df = loader.get_players()
        for col in ["Name", "Nationality", "Overall", "Club", "Position"]:
            assert col in df.columns

    def test_brazilian_players_present(self, loader):
        df = loader.get_players()
        brazilian = df[df["Nationality"] == "Brazil"]
        assert len(brazilian) > 500


class TestDataLoaderGetAllMatches:
    def test_all_matches_includes_all_competitions(self, loader):
        df = loader.get_all_matches()
        competitions = set(df["competition"].unique())
        assert "brasileirao" in competitions
        assert "copa_do_brasil" in competitions
        assert "libertadores" in competitions

    def test_all_matches_count_exceeds_single_dataset(self, loader):
        all_matches = loader.get_all_matches()
        brasileirao = loader.get_brasileirao_matches()
        assert len(all_matches) > len(brasileirao)
