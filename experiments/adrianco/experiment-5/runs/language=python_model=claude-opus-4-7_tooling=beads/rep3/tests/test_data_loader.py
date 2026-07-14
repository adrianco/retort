"""BDD-style tests for the CSV data loader.

Feature: Loading the bundled datasets
  In order to answer questions about Brazilian soccer
  All six provided CSV files must load into a unified DataStore
  And produce sensible row counts, columns, and normalized team names.
"""

from __future__ import annotations

import pandas as pd


class TestDataStoreLoading:
    def test_matches_dataframe_loaded(self, store):
        # Given a fresh load
        # When inspecting the matches dataframe
        df = store.matches
        # Then it has thousands of rows and the required columns
        assert len(df) > 5000
        required = {
            "date", "home_team", "away_team", "home_goals", "away_goals",
            "season", "competition", "source",
            "home_team_norm", "away_team_norm",
            "home_team_short", "away_team_short",
        }
        assert required.issubset(set(df.columns))

    def test_players_dataframe_loaded(self, store):
        df = store.players
        assert len(df) > 10000
        assert {"name", "club", "nationality", "overall", "club_norm", "club_short"}.issubset(df.columns)

    def test_competitions_cover_required_tournaments(self, store):
        comps = set(store.competitions())
        assert "Brasileirão" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps

    def test_normalized_team_names_are_nonempty(self, store):
        # Every loaded match must have non-empty normalized team keys
        df = store.matches
        assert (df["home_team_norm"].str.len() > 0).all()
        assert (df["away_team_norm"].str.len() > 0).all()

    def test_overlapping_brasileirao_sources_are_deduped(self, store):
        # For 2019, only one source (the modern brasileirao file) should remain
        # so the standings table is not double-counted.
        df = store.matches
        sub = df[(df["season"] == 2019) & (df["competition"] == "Brasileirão")]
        assert sub["source"].nunique() == 1
        # 20 teams * 38 rounds / 2 sides = 380 matches.
        assert len(sub) == 380
