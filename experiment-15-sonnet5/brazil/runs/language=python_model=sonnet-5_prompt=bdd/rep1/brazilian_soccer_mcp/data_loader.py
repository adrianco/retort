"""Loads the six provided Kaggle CSV files into two unified, normalized
pandas DataFrames: `matches` (all competitions) and `players` (FIFA data).

Every match source has different column names, date formats and team
name spellings; this module maps each source onto a single common
schema so the rest of the package (graph, queries, MCP server) never
has to know which CSV a row came from.
"""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass

import pandas as pd

from .normalize import (
    build_known_club_states,
    disambiguate_key,
    display_name_for_key,
    normalize_key,
    parse_datetime_column,
    parse_goal_column,
    strip_state_suffix,
)

# Sources that only contain unambiguous, single-club-per-name top-flight
# data. Used to learn each big club's "home" state so that same-named
# lower-league clubs from noisier sources (e.g. Copa do Brasil) don't get
# merged into them (see normalize.disambiguate_key).
_TOP_FLIGHT_SOURCES = {"Brasileirao_Matches", "novo_campeonato_brasileiro"}

# Common schema shared by every row in the unified `matches` DataFrame.
MATCH_COLUMNS = [
    "match_id",
    "competition",
    "source",
    "season",
    "round",
    "stage",
    "datetime",
    "date",
    "home_team",
    "home_team_key",
    "home_team_raw",
    "home_state",
    "away_team",
    "away_team_key",
    "away_team_raw",
    "away_state",
    "home_goal",
    "away_goal",
    "result",
    "stadium",
    "home_corner",
    "away_corner",
    "home_shots",
    "away_shots",
    "total_corners",
]


def default_data_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")


def _load_brasileirao(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return pd.DataFrame({
        "competition": "Brasileirao Serie A",
        "source": "Brasileirao_Matches",
        "season": pd.to_numeric(df["season"], errors="coerce").astype("Int64"),
        "round": pd.to_numeric(df["round"], errors="coerce").astype("Int64"),
        "stage": pd.NA,
        "datetime": parse_datetime_column(df["datetime"]),
        "home_team_raw": df["home_team"],
        "away_team_raw": df["away_team"],
        "home_state": df["home_team_state"],
        "away_state": df["away_team_state"],
        "home_goal": parse_goal_column(df["home_goal"]),
        "away_goal": parse_goal_column(df["away_goal"]),
        "stadium": pd.NA,
        "home_corner": pd.NA,
        "away_corner": pd.NA,
        "home_shots": pd.NA,
        "away_shots": pd.NA,
        "total_corners": pd.NA,
    })


def _load_brazilian_cup(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return pd.DataFrame({
        "competition": "Copa do Brasil",
        "source": "Brazilian_Cup_Matches",
        "season": pd.to_numeric(df["season"], errors="coerce").astype("Int64"),
        "round": df["round"].astype(str),
        "stage": pd.NA,
        "datetime": parse_datetime_column(df["datetime"]),
        "home_team_raw": df["home_team"],
        "away_team_raw": df["away_team"],
        "home_state": pd.NA,
        "away_state": pd.NA,
        "home_goal": parse_goal_column(df["home_goal"]),
        "away_goal": parse_goal_column(df["away_goal"]),
        "stadium": pd.NA,
        "home_corner": pd.NA,
        "away_corner": pd.NA,
        "home_shots": pd.NA,
        "away_shots": pd.NA,
        "total_corners": pd.NA,
    })


def _load_libertadores(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return pd.DataFrame({
        "competition": "Copa Libertadores",
        "source": "Libertadores_Matches",
        "season": pd.to_numeric(df["season"], errors="coerce").astype("Int64"),
        "round": pd.NA,
        "stage": df["stage"],
        "datetime": parse_datetime_column(df["datetime"]),
        "home_team_raw": df["home_team"],
        "away_team_raw": df["away_team"],
        "home_state": pd.NA,
        "away_state": pd.NA,
        "home_goal": parse_goal_column(df["home_goal"]),
        "away_goal": parse_goal_column(df["away_goal"]),
        "stadium": pd.NA,
        "home_corner": pd.NA,
        "away_corner": pd.NA,
        "home_shots": pd.NA,
        "away_shots": pd.NA,
        "total_corners": pd.NA,
    })


_TOURNAMENT_TO_COMPETITION = {
    "Serie A": "Brasileirao Serie A",
    "Serie B": "Brasileirao Serie B",
    "Serie C": "Brasileirao Serie C",
    "Copa do Brasil": "Copa do Brasil",
}


def _load_br_football_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    datetime_str = df["date"].astype(str) + " " + df["time"].astype(str)
    return pd.DataFrame({
        "competition": df["tournament"].map(lambda t: _TOURNAMENT_TO_COMPETITION.get(t, t)),
        "source": "BR-Football-Dataset",
        "season": parse_datetime_column(df["date"]).dt.year.astype("Int64"),
        "round": pd.NA,
        "stage": pd.NA,
        "datetime": parse_datetime_column(datetime_str),
        "home_team_raw": df["home"],
        "away_team_raw": df["away"],
        "home_state": pd.NA,
        "away_state": pd.NA,
        "home_goal": parse_goal_column(df["home_goal"]),
        "away_goal": parse_goal_column(df["away_goal"]),
        "stadium": pd.NA,
        "home_corner": parse_goal_column(df["home_corner"]),
        "away_corner": parse_goal_column(df["away_corner"]),
        "home_shots": parse_goal_column(df["home_shots"]),
        "away_shots": parse_goal_column(df["away_shots"]),
        "total_corners": parse_goal_column(df["total_corners"]),
    })


def _load_novo_campeonato(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return pd.DataFrame({
        "competition": "Brasileirao Serie A",
        "source": "novo_campeonato_brasileiro",
        "season": pd.to_numeric(df["Ano"], errors="coerce").astype("Int64"),
        "round": pd.to_numeric(df["Rodada"], errors="coerce").astype("Int64"),
        "stage": pd.NA,
        "datetime": parse_datetime_column(df["Data"], dayfirst=True),
        "home_team_raw": df["Equipe_mandante"],
        "away_team_raw": df["Equipe_visitante"],
        "home_state": df["Mandante_UF"],
        "away_state": df["Visitante_UF"],
        "home_goal": parse_goal_column(df["Gols_mandante"]),
        "away_goal": parse_goal_column(df["Gols_visitante"]),
        "stadium": df["Arena"],
        "home_corner": pd.NA,
        "away_corner": pd.NA,
        "home_shots": pd.NA,
        "away_shots": pd.NA,
        "total_corners": pd.NA,
    })


_LOADERS = {
    "Brasileirao_Matches.csv": _load_brasileirao,
    "Brazilian_Cup_Matches.csv": _load_brazilian_cup,
    "Libertadores_Matches.csv": _load_libertadores,
    "BR-Football-Dataset.csv": _load_br_football_dataset,
    "novo_campeonato_brasileiro.csv": _load_novo_campeonato,
}


def _build_display_names(key_raw_pairs: list[tuple[pd.Series, pd.Series]]) -> dict[str, str]:
    """Pick the most common "clean" spelling seen for each (disambiguated)
    team key, to use as a fallback for teams not in the curated
    TEAM_DISPLAY_NAMES map.
    """
    counters: dict[str, Counter] = {}
    for key_series, raw_series in key_raw_pairs:
        for key, raw in zip(key_series, raw_series):
            if not key or pd.isna(raw):
                continue
            clean, _state = strip_state_suffix(str(raw))
            counters.setdefault(key, Counter())[clean] += 1

    display_names = {}
    for key, counter in counters.items():
        most_common_raw = counter.most_common(1)[0][0]
        if "(" in key:
            # Disambiguated from a known bigger club (see disambiguate_key):
            # keep the state suffix visible so it reads as a distinct team.
            state = key[key.index("(") + 1 : -1].upper()
            display_names[key] = f"{most_common_raw}-{state}"
        else:
            display_names[key] = display_name_for_key(key, fallback=most_common_raw)
    return display_names


def load_matches(data_dir: str | None = None) -> pd.DataFrame:
    """Load and normalize all five match CSVs into one DataFrame."""
    data_dir = data_dir or default_data_dir()
    frames = []
    for filename, loader in _LOADERS.items():
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Expected data file not found: {path}")
        frames.append(loader(path))

    matches = pd.concat(frames, ignore_index=True, sort=False)

    top_flight = matches[matches["source"].isin(_TOP_FLIGHT_SOURCES)]
    known_states = build_known_club_states(
        list(zip(top_flight["home_team_raw"], top_flight["home_state"]))
        + list(zip(top_flight["away_team_raw"], top_flight["away_state"]))
    )

    matches["home_team_key"] = matches["home_team_raw"].map(lambda r: disambiguate_key(r, known_states))
    matches["away_team_key"] = matches["away_team_raw"].map(lambda r: disambiguate_key(r, known_states))

    display_names = _build_display_names([
        (matches["home_team_key"], matches["home_team_raw"]),
        (matches["away_team_key"], matches["away_team_raw"]),
    ])
    matches["home_team"] = matches["home_team_key"].map(lambda k: display_names.get(k, k.title()))
    matches["away_team"] = matches["away_team_key"].map(lambda k: display_names.get(k, k.title()))

    matches["date"] = matches["datetime"].dt.date

    def _result(row):
        if pd.isna(row["home_goal"]) or pd.isna(row["away_goal"]):
            return pd.NA
        if row["home_goal"] > row["away_goal"]:
            return "Home"
        if row["home_goal"] < row["away_goal"]:
            return "Away"
        return "Draw"

    matches["result"] = matches.apply(_result, axis=1)
    matches["match_id"] = matches.index

    return matches[MATCH_COLUMNS]


_FIFA_COLUMNS = {
    "ID": "player_id",
    "Name": "name",
    "Age": "age",
    "Nationality": "nationality",
    "Overall": "overall",
    "Potential": "potential",
    "Club": "club_raw",
    "Position": "position",
    "Jersey Number": "jersey_number",
    "Height": "height",
    "Weight": "weight",
    "Preferred Foot": "preferred_foot",
    "Value": "value",
    "Wage": "wage",
}


def load_players(data_dir: str | None = None) -> pd.DataFrame:
    """Load and normalize the FIFA player CSV."""
    data_dir = data_dir or default_data_dir()
    path = os.path.join(data_dir, "fifa_data.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Expected data file not found: {path}")

    raw = pd.read_csv(path, encoding="utf-8-sig")
    players = raw[list(_FIFA_COLUMNS.keys())].rename(columns=_FIFA_COLUMNS)
    players["age"] = pd.to_numeric(players["age"], errors="coerce").astype("Int64")
    players["overall"] = pd.to_numeric(players["overall"], errors="coerce").astype("Int64")
    players["potential"] = pd.to_numeric(players["potential"], errors="coerce").astype("Int64")
    players["jersey_number"] = pd.to_numeric(players["jersey_number"], errors="coerce").astype("Int64")
    players["club_key"] = players["club_raw"].map(normalize_key)
    players["nationality"] = players["nationality"].astype(str)
    players["name_key"] = players["name"].map(lambda n: normalize_key(n) if pd.notna(n) else "")
    return players


@dataclass(frozen=True)
class SoccerData:
    matches: pd.DataFrame
    players: pd.DataFrame


def load_all(data_dir: str | None = None) -> SoccerData:
    return SoccerData(matches=load_matches(data_dir), players=load_players(data_dir))
