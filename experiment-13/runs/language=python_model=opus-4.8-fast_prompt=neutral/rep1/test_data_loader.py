"""Tests that every provided CSV loads into the unified schema correctly."""

import pandas as pd

from data_loader import (
    MATCH_COLUMNS,
    load_matches,
    load_players,
    load_dataset,
)


def test_all_match_sources_present():
    m = load_matches()
    sources = set(m["source"].unique())
    assert sources == {
        "Brasileirao_Matches.csv",
        "novo_campeonato_brasileiro.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
    }


def test_unified_schema_columns():
    m = load_matches()
    assert list(m.columns) == MATCH_COLUMNS


def test_row_counts_match_source_files():
    # Row counts equal the data rows (header excluded) of each CSV.
    m = load_matches()
    by_source = m["source"].value_counts().to_dict()
    assert by_source["Brasileirao_Matches.csv"] == 4180
    assert by_source["Brazilian_Cup_Matches.csv"] == 1337
    assert by_source["Libertadores_Matches.csv"] == 1255
    assert by_source["novo_campeonato_brasileiro.csv"] == 6886
    assert by_source["BR-Football-Dataset.csv"] == 10296


def test_competitions_mapped():
    m = load_matches()
    comps = set(m["competition"].unique())
    assert "Brasileirão Série A" in comps
    assert "Copa do Brasil" in comps
    assert "Copa Libertadores" in comps
    assert "Série B" in comps and "Série C" in comps


def test_dates_parsed_across_formats():
    m = load_matches()
    # Brazilian DD/MM/YYYY source
    novo = m[m["source"] == "novo_campeonato_brasileiro.csv"]
    assert novo["date"].notna().mean() > 0.99
    # ISO datetime source
    bra = m[m["source"] == "Brasileirao_Matches.csv"]
    assert bra["date"].notna().mean() > 0.99
    assert pd.api.types.is_datetime64_any_dtype(m["date"])


def test_goals_are_nullable_integers():
    m = load_matches()
    assert str(m["home_goal"].dtype) == "Int64"
    # Some Brasileirão 2022 fixtures were unplayed at capture time -> <NA>.
    assert m["home_goal"].isna().any()


def test_players_loaded_with_brazilian_subset():
    p = load_players()
    assert len(p) == 18207
    assert "Name" in p.columns and "Overall" in p.columns
    assert (p["nationality_lower"] == "brazil").sum() > 500


def test_load_dataset_bundles_both():
    ds = load_dataset()
    assert not ds.matches.empty
    assert not ds.players.empty
