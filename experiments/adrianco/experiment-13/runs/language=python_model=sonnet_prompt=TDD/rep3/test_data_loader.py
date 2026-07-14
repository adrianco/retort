"""Tests for data_loader.py - TDD for Brazilian Soccer MCP Server."""
import os
import pytest
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "kaggle")


# ─── Cycle 1: normalize_team_name ────────────────────────────────────────────

def test_normalize_strips_state_suffix():
    from data_loader import normalize_team_name
    assert normalize_team_name("Palmeiras-SP") == "Palmeiras"


def test_normalize_no_suffix_unchanged():
    from data_loader import normalize_team_name
    assert normalize_team_name("Flamengo") == "Flamengo"


def test_normalize_strips_state_with_dash_and_space():
    from data_loader import normalize_team_name
    assert normalize_team_name("Sport-PE") == "Sport"


def test_normalize_handles_none():
    from data_loader import normalize_team_name
    assert normalize_team_name(None) is None


def test_normalize_strips_location_suffix_parenthetical():
    """Copa do Brasil teams have long names like 'Boavista Sport Club ... - RJ'"""
    from data_loader import normalize_team_name
    result = normalize_team_name("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
    assert result == "Boavista Sport Club (antigo Esporte Clube Barreira)"


# ─── Cycle 2: parse_date ─────────────────────────────────────────────────────

def test_parse_date_iso():
    from data_loader import parse_date
    result = parse_date("2023-09-24")
    assert result.year == 2023 and result.month == 9 and result.day == 24


def test_parse_date_with_time():
    from data_loader import parse_date
    result = parse_date("2012-05-19 18:30:00")
    assert result.year == 2012 and result.month == 5 and result.day == 19


def test_parse_date_brazilian_format():
    from data_loader import parse_date
    result = parse_date("29/03/2003")
    assert result.year == 2003 and result.month == 3 and result.day == 29


def test_parse_date_returns_none_for_invalid():
    from data_loader import parse_date
    assert parse_date("not-a-date") is None


# ─── Cycle 3: Load Brasileirão matches ───────────────────────────────────────

def test_load_brasileirao_returns_dataframe():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.brasileirao
    assert isinstance(df, pd.DataFrame)


def test_load_brasileirao_row_count():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    assert len(loader.brasileirao) > 4000


def test_load_brasileirao_has_required_columns():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.brasileirao
    for col in ("home_team", "away_team", "home_goal", "away_goal", "season"):
        assert col in df.columns, f"Missing column: {col}"


def test_load_brasileirao_has_normalized_team_names():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.brasileirao
    # No raw "Palmeiras-SP" style entries should remain in home_team_norm
    assert "home_team_norm" in df.columns
    assert not (df["home_team_norm"].str.contains(r"-[A-Z]{2}$", regex=True).any())


# ─── Cycle 4: Load Copa do Brasil matches ────────────────────────────────────

def test_load_cup_returns_dataframe():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.cup
    assert isinstance(df, pd.DataFrame)


def test_load_cup_row_count():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    assert len(loader.cup) > 1000


def test_load_cup_has_required_columns():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.cup
    for col in ("home_team", "away_team", "home_goal", "away_goal", "season"):
        assert col in df.columns


# ─── Cycle 5: Load Libertadores matches ──────────────────────────────────────

def test_load_libertadores_returns_dataframe():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.libertadores
    assert isinstance(df, pd.DataFrame)


def test_load_libertadores_row_count():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    assert len(loader.libertadores) > 1000


def test_load_libertadores_has_stage_column():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    assert "stage" in loader.libertadores.columns


# ─── Cycle 6: Load BR-Football-Dataset ───────────────────────────────────────

def test_load_extended_stats_returns_dataframe():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.extended_stats
    assert isinstance(df, pd.DataFrame)


def test_load_extended_stats_row_count():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    assert len(loader.extended_stats) > 10000


def test_load_extended_stats_has_corner_data():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.extended_stats
    assert "home_corner" in df.columns and "away_corner" in df.columns


# ─── Cycle 7: Load historical Brasileirão ────────────────────────────────────

def test_load_historical_returns_dataframe():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.historical
    assert isinstance(df, pd.DataFrame)


def test_load_historical_row_count():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    assert len(loader.historical) > 6000


def test_load_historical_has_english_column_names():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.historical
    for col in ("home_team", "away_team", "home_goal", "away_goal", "season", "winner"):
        assert col in df.columns, f"Missing column: {col}"


# ─── Cycle 8: Load FIFA data ──────────────────────────────────────────────────

def test_load_fifa_returns_dataframe():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.fifa
    assert isinstance(df, pd.DataFrame)


def test_load_fifa_row_count():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    assert len(loader.fifa) > 18000


def test_load_fifa_has_key_columns():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df = loader.fifa
    for col in ("Name", "Nationality", "Overall", "Club", "Position"):
        assert col in df.columns, f"Missing column: {col}"


# ─── Cycle 9: DataLoader caches DataFrames ───────────────────────────────────

def test_dataloader_caches_brasileirao():
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    df1 = loader.brasileirao
    df2 = loader.brasileirao
    assert df1 is df2


def test_dataloader_all_datasets_property():
    """all_matches combines brasileirao, cup, libertadores, historical."""
    from data_loader import DataLoader
    loader = DataLoader(DATA_DIR)
    all_m = loader.all_matches
    assert isinstance(all_m, pd.DataFrame)
    assert len(all_m) > 10000
    assert "competition" in all_m.columns
