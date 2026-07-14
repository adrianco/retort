import datetime
from pathlib import Path

import pandas as pd

from brazilian_soccer_mcp.data_loader import DATA_DIR, load_matches, load_players

REQUIRED_MATCH_COLUMNS = {
    "date", "season", "round", "stage", "competition", "source",
    "home_team_raw", "away_team_raw", "home_team", "away_team",
    "home_team_display", "away_team_display", "home_goal", "away_goal",
}


def test_data_dir_exists():
    assert Path(DATA_DIR).is_dir()


def test_load_matches_has_expected_columns():
    df = load_matches()
    assert REQUIRED_MATCH_COLUMNS.issubset(set(df.columns))


def test_load_matches_row_count_per_source():
    df = load_matches()
    counts = df["source"].value_counts().to_dict()
    assert counts["brasileirao"] == 4180
    assert counts["copa_do_brasil"] == 1337
    assert counts["libertadores"] == 1255
    assert counts["br_football_dataset"] == 10296
    # novo_campeonato_brasileiro overlaps with brasileirao for seasons 2012-2022;
    # only the seasons unique to it (pre-2012) should be kept to avoid double-counting.
    assert counts["novo_campeonato_brasileiro"] < 6886


def test_novo_campeonato_does_not_duplicate_brasileirao_seasons():
    df = load_matches()
    brasileirao_seasons = set(df[df["source"] == "brasileirao"]["season"].unique())
    novo_seasons = set(df[df["source"] == "novo_campeonato_brasileiro"]["season"].unique())
    assert brasileirao_seasons.isdisjoint(novo_seasons)


def test_load_matches_dates_are_parsed():
    df = load_matches()
    sample = df[df["source"] == "brasileirao"].iloc[0]
    assert isinstance(sample["date"], datetime.date)


def test_load_matches_team_keys_are_normalized():
    df = load_matches()
    brasileirao = df[df["source"] == "brasileirao"]
    flamengo_rows = brasileirao[
        (brasileirao["home_team"] == "flamengo") | (brasileirao["away_team"] == "flamengo")
    ]
    assert len(flamengo_rows) > 0


def test_load_matches_goals_are_numeric():
    df = load_matches()
    assert pd.api.types.is_numeric_dtype(df["home_goal"])
    assert pd.api.types.is_numeric_dtype(df["away_goal"])
    assert (df["home_goal"].dropna() >= 0).all()


def test_load_players_row_count():
    df = load_players()
    assert len(df) == 18207


def test_load_players_has_expected_columns():
    df = load_players()
    for col in ["name", "age", "nationality", "overall", "potential", "club", "position", "club_key"]:
        assert col in df.columns


def test_load_players_finds_known_player():
    df = load_players()
    messi = df[df["name"].str.contains("Messi", case=False, na=False)]
    assert len(messi) == 1
    assert messi.iloc[0]["nationality"] == "Argentina"


def test_load_players_club_key_normalized():
    df = load_players()
    cruzeiro_players = df[df["club_key"] == "cruzeiro"]
    assert len(cruzeiro_players) > 0
