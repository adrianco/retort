"""Tests for player query functions."""
import pytest
import pandas as pd
from data_loader import DataLoader
from player_queries import (
    search_players_by_name,
    search_players_by_nationality,
    search_players_by_club,
    search_players_by_position,
    get_top_rated_players,
    format_player_info,
    get_players_at_brazilian_clubs,
)

DATA_DIR = "data/kaggle"


@pytest.fixture(scope="module")
def loader():
    return DataLoader(DATA_DIR)


class TestSearchPlayersByName:
    def test_finds_neymar(self, loader):
        results = search_players_by_name(loader.fifa_players, "Neymar")
        assert len(results) > 0

    def test_case_insensitive(self, loader):
        r1 = search_players_by_name(loader.fifa_players, "neymar")
        r2 = search_players_by_name(loader.fifa_players, "NEYMAR")
        assert len(r1) == len(r2)

    def test_partial_match(self, loader):
        results = search_players_by_name(loader.fifa_players, "Gabr")
        assert len(results) > 0

    def test_returns_dataframe(self, loader):
        results = search_players_by_name(loader.fifa_players, "Neymar")
        assert isinstance(results, pd.DataFrame)

    def test_no_result_for_unknown(self, loader):
        results = search_players_by_name(loader.fifa_players, "XYZUnknownPlayer999")
        assert len(results) == 0


class TestSearchPlayersByNationality:
    def test_finds_brazilian_players(self, loader):
        results = search_players_by_nationality(loader.fifa_players, "Brazil")
        assert len(results) > 0

    def test_all_correct_nationality(self, loader):
        results = search_players_by_nationality(loader.fifa_players, "Brazil")
        assert all(results["Nationality"].str.contains("Brazil", case=False, na=False))

    def test_case_insensitive(self, loader):
        r1 = search_players_by_nationality(loader.fifa_players, "brazil")
        r2 = search_players_by_nationality(loader.fifa_players, "Brazil")
        assert len(r1) == len(r2)

    def test_returns_dataframe(self, loader):
        results = search_players_by_nationality(loader.fifa_players, "Brazil")
        assert isinstance(results, pd.DataFrame)


class TestSearchPlayersByClub:
    def test_finds_fluminense_players(self, loader):
        results = search_players_by_club(loader.fifa_players, "Fluminense")
        assert len(results) > 0

    def test_all_correct_club(self, loader):
        results = search_players_by_club(loader.fifa_players, "Fluminense")
        assert all(results["Club"].str.contains("Fluminense", case=False, na=False))

    def test_case_insensitive(self, loader):
        r1 = search_players_by_club(loader.fifa_players, "fluminense")
        r2 = search_players_by_club(loader.fifa_players, "Fluminense")
        assert len(r1) == len(r2)


class TestSearchPlayersByPosition:
    def test_finds_goalkeepers(self, loader):
        results = search_players_by_position(loader.fifa_players, "GK")
        assert len(results) > 0

    def test_all_correct_position(self, loader):
        results = search_players_by_position(loader.fifa_players, "GK")
        assert all(results["Position"].str.contains("GK", case=False, na=False))

    def test_case_insensitive(self, loader):
        r1 = search_players_by_position(loader.fifa_players, "st")
        r2 = search_players_by_position(loader.fifa_players, "ST")
        assert len(r1) == len(r2)


class TestGetTopRatedPlayers:
    def test_returns_dataframe(self, loader):
        results = get_top_rated_players(loader.fifa_players, limit=10)
        assert isinstance(results, pd.DataFrame)

    def test_correct_number(self, loader):
        results = get_top_rated_players(loader.fifa_players, limit=5)
        assert len(results) <= 5

    def test_sorted_by_overall(self, loader):
        results = get_top_rated_players(loader.fifa_players, limit=10)
        ratings = list(results["Overall"])
        assert ratings == sorted(ratings, reverse=True)

    def test_nationality_filter(self, loader):
        results = get_top_rated_players(loader.fifa_players, nationality="Brazil", limit=10)
        assert all(results["Nationality"].str.contains("Brazil", case=False, na=False))

    def test_club_filter(self, loader):
        results = get_top_rated_players(loader.fifa_players, club="Flamengo", limit=10)
        assert all(results["Club"].str.contains("Flamengo", case=False, na=False))


class TestFormatPlayerInfo:
    def test_returns_string(self, loader):
        player = loader.fifa_players.iloc[0]
        result = format_player_info(player)
        assert isinstance(result, str)

    def test_contains_name(self, loader):
        player = loader.fifa_players.iloc[0]
        result = format_player_info(player)
        assert str(player["Name"]) in result

    def test_contains_overall(self, loader):
        player = loader.fifa_players.iloc[0]
        result = format_player_info(player)
        assert str(int(player["Overall"])) in result


class TestGetPlayersAtBrazilianClubs:
    def test_returns_dict(self, loader):
        result = get_players_at_brazilian_clubs(loader.fifa_players)
        assert isinstance(result, dict)

    def test_has_known_clubs(self, loader):
        result = get_players_at_brazilian_clubs(loader.fifa_players)
        club_names = " ".join(result.keys()).lower()
        assert any(c in club_names for c in ["fluminense", "santos", "grêmio", "cruzeiro", "internacional"])

    def test_values_are_dicts_with_stats(self, loader):
        result = get_players_at_brazilian_clubs(loader.fifa_players)
        for club, stats in result.items():
            assert "count" in stats
            assert "avg_rating" in stats
