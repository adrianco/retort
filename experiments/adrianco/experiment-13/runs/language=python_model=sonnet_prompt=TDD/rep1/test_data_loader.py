"""Tests for data loading and normalization."""
import pytest
import pandas as pd
from data_loader import (
    normalize_team_name,
    load_brasileirao,
    load_copa_brasil,
    load_libertadores,
    load_br_football,
    load_historico_brasileiro,
    load_fifa_players,
    get_all_matches,
    DataLoader,
)

DATA_DIR = "data/kaggle"


class TestTeamNameNormalization:
    def test_converts_dash_state_to_space(self):
        assert normalize_team_name("Palmeiras-SP") == "Palmeiras SP"

    def test_converts_rj_suffix_to_space(self):
        assert normalize_team_name("Flamengo-RJ") == "Flamengo RJ"

    def test_no_suffix_unchanged(self):
        assert normalize_team_name("Flamengo") == "Flamengo"

    def test_strips_whitespace(self):
        assert normalize_team_name("  Santos  ") == "Santos"

    def test_preserves_accents(self):
        assert normalize_team_name("Grêmio-RS") == "Grêmio RS"

    def test_converts_dash_state_with_space(self):
        assert normalize_team_name("São Paulo - SP") == "São Paulo SP"

    def test_empty_string(self):
        assert normalize_team_name("") == ""

    def test_none_returns_empty(self):
        assert normalize_team_name(None) == ""

    def test_preserves_disambiguation(self):
        assert normalize_team_name("Atletico-MG") != normalize_team_name("Atletico-PR")


class TestLoadBrasileiraoMatches:
    @pytest.fixture(scope="class")
    def df(self):
        return load_brasileirao(DATA_DIR)

    def test_returns_dataframe(self, df):
        assert isinstance(df, pd.DataFrame)

    def test_has_expected_columns(self, df):
        assert "home_team" in df.columns
        assert "away_team" in df.columns
        assert "home_goal" in df.columns
        assert "away_goal" in df.columns
        assert "season" in df.columns
        assert "date" in df.columns

    def test_has_normalized_team_names(self, df):
        # Palmeiras-SP should become "Palmeiras SP" (no hyphen before state code)
        assert not df["home_team"].str.contains(r"-[A-Z]{2}$", regex=True).any()

    def test_not_empty(self, df):
        assert len(df) > 0

    def test_competition_column(self, df):
        assert "competition" in df.columns
        assert (df["competition"] == "Brasileirão Serie A").all()

    def test_date_is_datetime(self, df):
        assert pd.api.types.is_datetime64_any_dtype(df["date"])


class TestLoadCopaBrasilMatches:
    @pytest.fixture(scope="class")
    def df(self):
        return load_copa_brasil(DATA_DIR)

    def test_returns_dataframe(self, df):
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self, df):
        for col in ["home_team", "away_team", "home_goal", "away_goal", "season", "date"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_not_empty(self, df):
        assert len(df) > 0

    def test_competition_column(self, df):
        assert "competition" in df.columns
        assert (df["competition"] == "Copa do Brasil").all()


class TestLoadLibertadoresMatches:
    @pytest.fixture(scope="class")
    def df(self):
        return load_libertadores(DATA_DIR)

    def test_returns_dataframe(self, df):
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self, df):
        for col in ["home_team", "away_team", "home_goal", "away_goal", "season", "date"]:
            assert col in df.columns

    def test_not_empty(self, df):
        assert len(df) > 0

    def test_competition_column(self, df):
        assert "competition" in df.columns
        assert (df["competition"] == "Copa Libertadores").all()


class TestLoadBRFootball:
    @pytest.fixture(scope="class")
    def df(self):
        return load_br_football(DATA_DIR)

    def test_returns_dataframe(self, df):
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self, df):
        for col in ["home_team", "away_team", "home_goal", "away_goal", "date"]:
            assert col in df.columns

    def test_not_empty(self, df):
        assert len(df) > 0


class TestLoadHistoricoBrasileiro:
    @pytest.fixture(scope="class")
    def df(self):
        return load_historico_brasileiro(DATA_DIR)

    def test_returns_dataframe(self, df):
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self, df):
        for col in ["home_team", "away_team", "home_goal", "away_goal", "season", "date"]:
            assert col in df.columns

    def test_not_empty(self, df):
        assert len(df) > 0

    def test_date_parsed_from_brazilian_format(self, df):
        assert pd.api.types.is_datetime64_any_dtype(df["date"])


class TestLoadFIFAPlayers:
    @pytest.fixture(scope="class")
    def df(self):
        return load_fifa_players(DATA_DIR)

    def test_returns_dataframe(self, df):
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self, df):
        for col in ["Name", "Nationality", "Overall", "Club", "Position"]:
            assert col in df.columns

    def test_not_empty(self, df):
        assert len(df) > 0

    def test_has_brazilian_players(self, df):
        br = df[df["Nationality"] == "Brazil"]
        assert len(br) > 0


class TestGetAllMatches:
    @pytest.fixture(scope="class")
    def df(self):
        return get_all_matches(DATA_DIR)

    def test_returns_dataframe(self, df):
        assert isinstance(df, pd.DataFrame)

    def test_has_common_columns(self, df):
        for col in ["home_team", "away_team", "home_goal", "away_goal", "date", "competition"]:
            assert col in df.columns

    def test_has_data_from_multiple_competitions(self, df):
        comps = df["competition"].unique()
        assert len(comps) >= 3

    def test_not_empty(self, df):
        assert len(df) > 1000


class TestDataLoader:
    @pytest.fixture(scope="class")
    def loader(self):
        return DataLoader(DATA_DIR)

    def test_brasileirao_loaded(self, loader):
        assert loader.brasileirao is not None
        assert len(loader.brasileirao) > 0

    def test_copa_brasil_loaded(self, loader):
        assert loader.copa_brasil is not None
        assert len(loader.copa_brasil) > 0

    def test_libertadores_loaded(self, loader):
        assert loader.libertadores is not None
        assert len(loader.libertadores) > 0

    def test_br_football_loaded(self, loader):
        assert loader.br_football is not None
        assert len(loader.br_football) > 0

    def test_historico_loaded(self, loader):
        assert loader.historico is not None
        assert len(loader.historico) > 0

    def test_fifa_players_loaded(self, loader):
        assert loader.fifa_players is not None
        assert len(loader.fifa_players) > 0

    def test_all_matches_loaded(self, loader):
        assert loader.all_matches is not None
        assert len(loader.all_matches) > 1000
