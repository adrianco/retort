from functools import lru_cache
from pathlib import Path

import pandas as pd

from brazilian_soccer_mcp.normalize import canonical_team_key, display_team_name, parse_date

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

MATCH_COLUMNS = [
    "date", "season", "round", "stage", "competition", "source",
    "home_team_raw", "away_team_raw", "home_team", "away_team",
    "home_team_display", "away_team_display", "home_goal", "away_goal",
]


def _with_team_keys(df: pd.DataFrame, home_col: str, away_col: str) -> pd.DataFrame:
    df["home_team_raw"] = df[home_col]
    df["away_team_raw"] = df[away_col]
    df["home_team"] = df[home_col].map(canonical_team_key)
    df["away_team"] = df[away_col].map(canonical_team_key)
    df["home_team_display"] = df[home_col].map(display_team_name)
    df["away_team_display"] = df[away_col].map(display_team_name)
    return df


def _load_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv")
    df = _with_team_keys(df, "home_team", "away_team")
    df["date"] = df["datetime"].map(parse_date)
    df["competition"] = "Brasileirao"
    df["stage"] = None
    df["source"] = "brasileirao"
    return df[MATCH_COLUMNS]


def _load_copa_do_brasil() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv")
    df = _with_team_keys(df, "home_team", "away_team")
    df["date"] = df["datetime"].map(parse_date)
    df["competition"] = "Copa do Brasil"
    df["stage"] = None
    df["source"] = "copa_do_brasil"
    return df[MATCH_COLUMNS]


def _load_libertadores() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv")
    df = _with_team_keys(df, "home_team", "away_team")
    df["date"] = df["datetime"].map(parse_date)
    df["competition"] = "Copa Libertadores"
    df["round"] = None
    df["source"] = "libertadores"
    return df[MATCH_COLUMNS]


def _load_br_football_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv")
    df = _with_team_keys(df, "home", "away")
    df["date"] = df["date"].map(parse_date)
    df["competition"] = df["tournament"]
    df["season"] = df["date"].map(lambda d: d.year if d else None)
    df["round"] = None
    df["stage"] = None
    df["source"] = "br_football_dataset"
    return df[MATCH_COLUMNS]


def _load_novo_campeonato() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv")
    # Seasons 2012-2019 are also covered by Brasileirao_Matches.csv; keep only
    # the seasons unique to this source so Brasileirao matches aren't double-counted.
    df = df[df["Ano"] < 2012]
    df = _with_team_keys(df, "Equipe_mandante", "Equipe_visitante")
    df["date"] = df["Data"].map(parse_date)
    df["season"] = df["Ano"]
    df["round"] = df["Rodada"]
    df["home_goal"] = df["Gols_mandante"]
    df["away_goal"] = df["Gols_visitante"]
    df["competition"] = "Brasileirao"
    df["stage"] = None
    df["source"] = "novo_campeonato_brasileiro"
    return df[MATCH_COLUMNS]


_LOADERS = [
    _load_brasileirao,
    _load_copa_do_brasil,
    _load_libertadores,
    _load_br_football_dataset,
    _load_novo_campeonato,
]


@lru_cache(maxsize=1)
def load_matches() -> pd.DataFrame:
    frames = [loader() for loader in _LOADERS]
    df = pd.concat(frames, ignore_index=True)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


@lru_cache(maxsize=1)
def load_players() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "fifa_data.csv", encoding="utf-8-sig")
    df = df.rename(columns={
        "Name": "name",
        "Age": "age",
        "Nationality": "nationality",
        "Overall": "overall",
        "Potential": "potential",
        "Club": "club",
        "Position": "position",
        "Jersey Number": "jersey_number",
        "Height": "height",
        "Weight": "weight",
    })
    df["club_key"] = df["club"].map(lambda c: canonical_team_key(c) if isinstance(c, str) else None)
    return df
