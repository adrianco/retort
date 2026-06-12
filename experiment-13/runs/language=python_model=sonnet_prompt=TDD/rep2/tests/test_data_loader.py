import datetime
import pytest
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "kaggle"


# ─── Cycle 1: Team name normalization ─────────────────────────────────────────

from data_loader import normalize_team_name, teams_match


def test_normalize_removes_state_suffix_with_dash():
    assert normalize_team_name("Palmeiras-SP") == "Palmeiras"


def test_normalize_removes_state_suffix_flamengo():
    assert normalize_team_name("Flamengo-RJ") == "Flamengo"


def test_normalize_no_suffix_unchanged():
    assert normalize_team_name("Flamengo") == "Flamengo"


def test_normalize_removes_state_suffix_with_spaces():
    assert normalize_team_name("América - MG") == "América"


def test_teams_match_same_team_different_suffix():
    assert teams_match("Palmeiras-SP", "Palmeiras") is True


def test_teams_match_different_teams():
    assert teams_match("Flamengo-RJ", "Santos-SP") is False


# ─── Cycle 2: Date parsing ─────────────────────────────────────────────────────

from data_loader import parse_date


def test_parse_date_iso_format():
    assert parse_date("2023-09-24") == datetime.date(2023, 9, 24)


def test_parse_date_br_format():
    assert parse_date("29/03/2003") == datetime.date(2003, 3, 29)


def test_parse_date_datetime_string():
    assert parse_date("2012-05-19 18:30:00") == datetime.date(2012, 5, 19)


def test_parse_date_none():
    assert parse_date(None) is None


# ─── Cycle 3: Data loading ─────────────────────────────────────────────────────

from data_loader import DataLoader


@pytest.fixture(scope="module")
def loader():
    return DataLoader(DATA_DIR)


def test_load_brasileirao_returns_nonempty(loader):
    df = loader.load_brasileirao()
    assert len(df) > 0
    for col in ["home_team", "away_team", "home_goal", "away_goal", "season"]:
        assert col in df.columns, f"Missing column: {col}"


def test_load_cup_returns_nonempty(loader):
    df = loader.load_cup()
    assert len(df) > 0
    for col in ["home_team", "away_team", "home_goal", "away_goal", "season"]:
        assert col in df.columns, f"Missing column: {col}"


def test_load_libertadores_returns_nonempty(loader):
    df = loader.load_libertadores()
    assert len(df) > 0
    for col in ["home_team", "away_team", "home_goal", "away_goal", "season"]:
        assert col in df.columns, f"Missing column: {col}"


def test_load_historical_returns_normalized_columns(loader):
    df = loader.load_historical()
    assert len(df) > 0
    for col in ["home_team", "away_team", "home_goal", "away_goal", "season"]:
        assert col in df.columns, f"Missing column: {col}"


def test_load_extended_returns_nonempty(loader):
    df = loader.load_extended()
    assert len(df) > 0
    for col in ["home_team", "away_team", "home_goal", "away_goal"]:
        assert col in df.columns, f"Missing column: {col}"


def test_load_players_returns_nonempty(loader):
    df = loader.load_players()
    assert len(df) > 0
    for col in ["Name", "Nationality", "Overall", "Club", "Position"]:
        assert col in df.columns, f"Missing column: {col}"


def test_load_all_matches_has_competition_column(loader):
    df = loader.load_all_matches()
    assert len(df) > 0
    assert "competition" in df.columns
    for col in ["home_team", "away_team", "home_goal", "away_goal"]:
        assert col in df.columns, f"Missing column: {col}"
