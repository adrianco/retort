"""Unit tests for the data loader."""

import pandas as pd

from brazilian_soccer_mcp.data_loader import _FILES


class TestDataStoreLoads:
    def test_all_six_files_loaded(self, store):
        sources = store.sources
        assert "Brasileirao_Matches.csv" in sources
        assert "Brazilian_Cup_Matches.csv" in sources
        assert "Libertadores_Matches.csv" in sources
        assert "BR-Football-Dataset.csv" in sources
        assert "novo_campeonato_brasileiro.csv" in sources
        assert "fifa_data.csv" in sources

    def test_match_counts_reasonable(self, store):
        # The spec lists per-file counts; loader should at least see the right order of magnitude.
        assert store.sources["Brasileirao_Matches.csv"] == 4180
        assert store.sources["Brazilian_Cup_Matches.csv"] == 1337
        assert store.sources["Libertadores_Matches.csv"] == 1255
        assert store.sources["BR-Football-Dataset.csv"] == 10296
        assert store.sources["novo_campeonato_brasileiro.csv"] == 6886
        assert store.sources["fifa_data.csv"] == 18207

    def test_canonical_columns_present(self, store):
        required = {
            "competition", "season", "date", "home_team", "away_team",
            "home_goal", "away_goal", "home_team_norm", "away_team_norm",
        }
        assert required.issubset(store.matches.columns)

    def test_dates_are_parsed(self, store):
        assert pd.api.types.is_datetime64_any_dtype(store.matches["date"])

    def test_norm_columns_filled(self, store):
        # At least 99% of rows should have a normalized name (allow a few NaN team rows)
        assert (store.matches["home_team_norm"].str.len() > 0).mean() > 0.99
        assert (store.matches["away_team_norm"].str.len() > 0).mean() > 0.99
