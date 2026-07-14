"""Feature: every provided CSV is loadable and yields the expected coverage."""

import pandas as pd
import pytest

from brazilian_soccer_mcp.loaders import load_data


class TestDataLoading:
    """
    Scenario: All six datasets load into a single matches table and a
    players table with the expected sizes and competitions.
    """

    @pytest.fixture(scope="class")
    def data(self):
        return load_data("data/kaggle")

    def test_matches_loaded(self, data):
        assert len(data.matches) > 10_000

    def test_players_loaded(self, data):
        assert len(data.players) == 18_207

    def test_expected_competitions_present(self, data):
        comps = set(data.matches["competition"].dropna().unique())
        assert "Brasileirão Série A" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps

    def test_seasons_span_expected_range(self, data):
        seasons = data.seasons
        assert min(seasons) <= 2003
        assert max(seasons) >= 2022

    def test_canonical_team_columns_populated(self, data):
        assert (data.matches["home_team"] != "").all()
        assert (data.matches["away_team"] != "").all()

    def test_no_self_play_rows(self, data):
        assert (
            data.matches["home_team"] != data.matches["away_team"]
        ).all()

    def test_flamengo_2019_serie_a_has_38_matches(self, data):
        df = data.matches
        sub = df[
            (df["season"] == 2019)
            & (df["competition"] == "Brasileirão Série A")
            & ((df["home_team"] == "flamengo") | (df["away_team"] == "flamengo"))
        ]
        assert len(sub) == 38

    def test_player_columns(self, data):
        for col in ["name", "nationality", "overall", "club", "position"]:
            assert col in data.players.columns

    def test_dates_parsed(self, data):
        # At least 80% of matches have a parsable date
        rate = data.matches["date"].notna().mean()
        assert rate > 0.8

    def test_missing_data_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_data(tmp_path)
