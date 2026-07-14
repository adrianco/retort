"""Tests for data_loader.py — red/green/refactor cycle."""
import pytest
import pandas as pd
from data_loader import DataLoader, normalize_team_name, parse_date


DATA_DIR = "data/kaggle"


@pytest.fixture(scope="module")
def loader():
    dl = DataLoader(DATA_DIR)
    dl.load_all()
    return dl


# --- normalize_team_name ---

def test_normalize_strips_state_suffix():
    assert normalize_team_name("Palmeiras-SP") == "Palmeiras"


def test_normalize_strips_dash_state():
    assert normalize_team_name("Flamengo-RJ") == "Flamengo"


def test_normalize_no_suffix_unchanged():
    assert normalize_team_name("Flamengo") == "Flamengo"


def test_normalize_handles_complex_name():
    assert normalize_team_name("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ") == "Boavista Sport Club (antigo Esporte Clube Barreira)"


def test_normalize_strips_space_dash_state():
    assert normalize_team_name("América - MG") == "América"


# --- parse_date ---

def test_parse_date_iso():
    d = parse_date("2023-09-24")
    assert d.year == 2023 and d.month == 9 and d.day == 24


def test_parse_date_with_time():
    d = parse_date("2012-05-19 18:30:00")
    assert d.year == 2012 and d.month == 5 and d.day == 19


def test_parse_date_brazilian_format():
    d = parse_date("29/03/2003")
    assert d.year == 2003 and d.month == 3 and d.day == 29


def test_parse_date_returns_none_for_empty():
    assert parse_date("") is None


# --- DataLoader.load_all ---

def test_brasileirao_matches_loaded(loader):
    assert loader.brasileirao is not None
    assert len(loader.brasileirao) > 4000


def test_cup_matches_loaded(loader):
    assert loader.copa_brasil is not None
    assert len(loader.copa_brasil) > 1300


def test_libertadores_matches_loaded(loader):
    assert loader.libertadores is not None
    assert len(loader.libertadores) > 1200


def test_br_football_dataset_loaded(loader):
    assert loader.br_football is not None
    assert len(loader.br_football) > 10000


def test_historical_brasileirao_loaded(loader):
    assert loader.historical is not None
    assert len(loader.historical) > 6800


def test_fifa_data_loaded(loader):
    assert loader.fifa is not None
    assert len(loader.fifa) > 18000


# --- Normalized column presence ---

def test_brasileirao_has_normalized_teams(loader):
    assert "home_team_norm" in loader.brasileirao.columns
    assert "away_team_norm" in loader.brasileirao.columns


def test_brasileirao_normalization_removes_suffix(loader):
    row = loader.brasileirao.iloc[0]
    # raw has state suffix like "Palmeiras-SP"
    assert "-SP" not in row["home_team_norm"]
    assert "-RJ" not in row["home_team_norm"]


def test_brasileirao_has_parsed_date(loader):
    assert "date_parsed" in loader.brasileirao.columns
    assert pd.api.types.is_datetime64_any_dtype(loader.brasileirao["date_parsed"])


def test_historical_has_normalized_teams(loader):
    assert "home_team_norm" in loader.historical.columns
    assert "away_team_norm" in loader.historical.columns


def test_historical_has_parsed_date(loader):
    assert "date_parsed" in loader.historical.columns


def test_fifa_has_nationality_column(loader):
    assert "Nationality" in loader.fifa.columns


def test_all_competitions_reachable_via_property(loader):
    comps = loader.all_match_dfs
    assert len(comps) == 5  # 5 match CSV files
