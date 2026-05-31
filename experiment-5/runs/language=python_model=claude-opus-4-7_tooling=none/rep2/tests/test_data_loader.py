"""BDD: data loader coverage.

Feature: Data loader
  As an MCP server
  I want to load every provided CSV file
  So that all the spec's queries have data to operate on
"""

from __future__ import annotations

import pandas as pd

from brazilian_soccer_mcp.data_loader import DataStore


class TestAllSourcesLoaded:
    """Scenario: every CSV in data/kaggle is represented in the store."""

    def test_all_five_match_sources_present(self, store: DataStore) -> None:
        # Given the default data directory
        # When we look at which source files contributed rows
        sources = set(store.matches["source"].unique())
        # Then every CSV is represented
        assert sources == {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
        }

    def test_fifa_players_loaded(self, store: DataStore) -> None:
        # The FIFA dataset ships ~18k players; we should load all of them.
        assert len(store.players) >= 18_000


class TestSchemaShape:
    """Scenario: the unified match table has the columns queries depend on."""

    def test_match_columns(self, store: DataStore) -> None:
        required = {
            "date",
            "season",
            "competition",
            "home_team",
            "away_team",
            "home_team_norm",
            "away_team_norm",
            "home_goal",
            "away_goal",
            "source",
        }
        assert required.issubset(set(store.matches.columns))

    def test_goals_are_integers(self, store: DataStore) -> None:
        # Goal aggregation breaks if these are still floats with NaN.
        assert pd.api.types.is_integer_dtype(store.matches["home_goal"])
        assert pd.api.types.is_integer_dtype(store.matches["away_goal"])


class TestCompetitionsLabelled:
    """Scenario: each canonical competition has matches."""

    def test_expected_competitions(self, store: DataStore) -> None:
        comps = set(store.matches["competition"].unique())
        assert {"Brasileirão Serie A", "Copa do Brasil", "Copa Libertadores"} <= comps


class TestDedup:
    """Scenario: matches recorded in multiple sources are deduplicated."""

    def test_no_duplicate_same_day_fixtures(self, store: DataStore) -> None:
        # Given the deduped store
        # When we count rows per (date, home, away, goals)
        dup_mask = store.matches.duplicated(
            subset=[
                "date",
                "home_team_norm",
                "away_team_norm",
                "home_goal",
                "away_goal",
            ]
        )
        # Then no exact duplicates remain
        assert not dup_mask.any()

    def test_2019_brasileirao_count_is_realistic(self, store: DataStore) -> None:
        # The real 2019 Brasileirão has 20 teams * 38 rounds / 2 = 380 matches.
        df = store.matches[
            (store.matches["season"] == 2019)
            & (store.matches["competition"] == "Brasileirão Serie A")
        ]
        # Allow some slack for the BR-Football source's UTC dates that
        # weren't perfectly dedupable, but should be well under 2x.
        assert 360 <= len(df) <= 420
