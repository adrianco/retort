"""
Context
=======
Tests for bsoccer.data: verifies all six CSV files load, the unified match table
is well-formed, cross-file Brasileirão duplicates are removed in matches_dedup,
and the FIFA player table loads with normalized club keys.
"""

import pandas as pd
import pytest

from bsoccer.data import (BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES, get_data)


@pytest.fixture(scope="module")
def data():
    return get_data()


def test_all_match_files_loaded(data):
    sources = set(data.matches["source"].unique())
    assert {
        "Brasileirao_Matches",
        "Brazilian_Cup_Matches",
        "Libertadores_Matches",
        "BR-Football-Dataset",
        "novo_campeonato_brasileiro",
    } <= sources


def test_match_columns_present(data):
    expected = {"competition", "season", "date", "home_team", "away_team",
                "home_key", "away_key", "home_goal", "away_goal"}
    assert expected <= set(data.matches.columns)


def test_competitions_include_main_three(data):
    comps = set(data.matches["competition"].unique())
    assert BRASILEIRAO in comps
    assert COPA_DO_BRASIL in comps
    assert LIBERTADORES in comps


def test_goals_are_integers(data):
    # No NaN goals should survive into the cleaned table.
    assert data.matches["home_goal"].notna().all()
    assert data.matches["away_goal"].notna().all()


def test_dedup_removes_brasileirao_overlap(data):
    # 2019 appears in both Brasileirao_Matches and novo_campeonato; a 20-team
    # double round-robin is exactly 380 matches.
    dedup = data.matches_dedup
    sub = dedup[(dedup["competition"] == BRASILEIRAO) & (dedup["season"] == 2019)]
    assert len(sub) == 380


def test_dedup_smaller_than_raw(data):
    assert len(data.matches_dedup) < len(data.matches)


def test_dates_parsed(data):
    # The Brazilian DD/MM/YYYY format from novo_campeonato must parse.
    novo = data.matches[data.matches["source"] == "novo_campeonato_brasileiro"]
    assert novo["date"].notna().mean() > 0.9


def test_players_loaded(data):
    players = data.players
    assert len(players) > 18000
    assert "club_key" in players.columns
    assert "Overall" in players.columns


def test_team_directory(data):
    directory = data.team_directory()
    keys = set(directory)
    assert "flamengo" in keys
    assert "palmeiras" in keys
    assert "" not in keys
