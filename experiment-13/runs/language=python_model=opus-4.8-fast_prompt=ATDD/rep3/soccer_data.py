"""
Data access layer for the Brazilian Soccer MCP server.

Loads the six provided Kaggle CSV files into two normalized in-memory pandas
tables -- ``matches`` and ``players`` -- with consistent column names, parsed
dates, integer scores and a canonical team key on every row.

Because the Brasileirão appears in three overlapping source files
(``Brasileirao_Matches``, ``novo_campeonato_brasileiro`` and the Serie A rows
of ``BR-Football-Dataset``), matches are de-duplicated on
(competition, home key, away key, season, score) so aggregate queries such as
league standings are not double-counted.

The repository is a read-only singleton built once from disk; the MCP service
layer queries it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

from team_names import normalize_team

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

# Unified match columns produced by every loader.
_MATCH_COLUMNS = [
    "competition",
    "season",
    "date",
    "round",
    "home_team",
    "away_team",
    "home_key",
    "away_key",
    "home_goal",
    "away_goal",
    "source",
]


def _to_int_goal(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _iso_date(series, dayfirst=False):
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=dayfirst, format="mixed")
    return parsed.dt.strftime("%Y-%m-%d")


def _finalize(df: pd.DataFrame, competition_default=None, source="") -> pd.DataFrame:
    """Attach keys, coerce scores and return only the unified columns."""
    if competition_default is not None and "competition" not in df:
        df["competition"] = competition_default
    df["source"] = source
    df["home_key"] = df["home_team"].map(normalize_team)
    df["away_key"] = df["away_team"].map(normalize_team)
    df["home_goal"] = df["home_goal"].map(_to_int_goal)
    df["away_goal"] = df["away_goal"].map(_to_int_goal)
    if "round" not in df:
        df["round"] = None
    df = df.dropna(subset=["home_goal", "away_goal"])
    df["home_goal"] = df["home_goal"].astype(int)
    df["away_goal"] = df["away_goal"].astype(int)
    df["season"] = df["season"].astype(int)
    return df[_MATCH_COLUMNS]


def _load_brasileirao(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame(
        {
            "competition": "Brasileirão",
            "season": df["season"],
            "date": _iso_date(df["datetime"]),
            "round": df["round"],
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_goal": df["home_goal"],
            "away_goal": df["away_goal"],
        }
    )
    return _finalize(out, source="Brasileirao_Matches")


def _load_cup(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame(
        {
            "competition": "Copa do Brasil",
            "season": df["season"],
            "date": _iso_date(df["datetime"]),
            "round": df["round"],
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_goal": df["home_goal"],
            "away_goal": df["away_goal"],
        }
    )
    return _finalize(out, source="Brazilian_Cup_Matches")


def _load_libertadores(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame(
        {
            "competition": "Copa Libertadores",
            "season": df["season"],
            "date": _iso_date(df["datetime"]),
            "round": df["stage"],
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_goal": df["home_goal"],
            "away_goal": df["away_goal"],
        }
    )
    return _finalize(out, source="Libertadores_Matches")


def _load_historical(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame(
        {
            "competition": "Brasileirão",
            "season": df["Ano"],
            "date": _iso_date(df["Data"], dayfirst=True),
            "round": df["Rodada"],
            "home_team": df["Equipe_mandante"],
            "away_team": df["Equipe_visitante"],
            "home_goal": df["Gols_mandante"],
            "away_goal": df["Gols_visitante"],
        }
    )
    return _finalize(out, source="novo_campeonato_brasileiro")


# Map the BR-Football "tournament" column onto canonical competition labels.
_BR_TOURNAMENT = {
    "Serie A": "Brasileirão",
    "Serie B": "Brasileirão Série B",
    "Serie C": "Brasileirão Série C",
    "Copa do Brasil": "Copa do Brasil",
}


def _load_br_football(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["tournament"].isin(_BR_TOURNAMENT)]
    dates = pd.to_datetime(df["date"], errors="coerce")
    out = pd.DataFrame(
        {
            "competition": df["tournament"].map(_BR_TOURNAMENT),
            "season": dates.dt.year,
            "date": dates.dt.strftime("%Y-%m-%d"),
            "round": None,
            "home_team": df["home"],
            "away_team": df["away"],
            "home_goal": df["home_goal"],
            "away_goal": df["away_goal"],
        }
    )
    out = out.dropna(subset=["season"])
    return _finalize(out, source="BR-Football-Dataset")


def _load_players(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={df.columns[0]: "row_index"})
    keep = {
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
    }
    players = df[[c for c in keep if c in df.columns]].rename(columns=keep)
    players["name"] = players["name"].fillna("").astype(str)
    players["nationality"] = players["nationality"].fillna("").astype(str)
    players["club"] = players["club"].fillna("").astype(str)
    players["position"] = players["position"].fillna("").astype(str)
    players["overall"] = pd.to_numeric(players["overall"], errors="coerce").fillna(0).astype(int)
    players["potential"] = pd.to_numeric(players["potential"], errors="coerce").fillna(0).astype(int)
    players["age"] = pd.to_numeric(players["age"], errors="coerce").fillna(0).astype(int)
    players["club_key"] = players["club"].map(normalize_team)
    return players


# The Brasileirão and Copa do Brasil are each covered by several source files
# with overlapping seasons. To avoid double-counting in aggregate queries we
# keep, for every (competition, season), the rows from a single authoritative
# source -- the first available one in this preference order.
_SOURCE_PREFERENCE = {
    "Brasileirão": [
        "novo_campeonato_brasileiro",
        "Brasileirao_Matches",
        "BR-Football-Dataset",
    ],
    "Copa do Brasil": ["Brazilian_Cup_Matches", "BR-Football-Dataset"],
}


def _select_authoritative(matches: pd.DataFrame) -> pd.DataFrame:
    """For each (competition, season) keep rows from one preferred source."""
    kept = []
    for (competition, season), group in matches.groupby(["competition", "season"], sort=False):
        preference = _SOURCE_PREFERENCE.get(competition)
        if preference:
            available = set(group["source"].unique())
            chosen = next((s for s in preference if s in available), None)
            if chosen is not None:
                group = group[group["source"] == chosen]
        # Drop any exact in-source duplicate fixtures defensively.
        group = group.drop_duplicates(
            subset=["home_key", "away_key", "home_goal", "away_goal"]
        )
        kept.append(group)
    return pd.concat(kept, ignore_index=True)


@dataclass
class SoccerRepository:
    matches: pd.DataFrame
    players: pd.DataFrame

    _singleton: "SoccerRepository | None" = None

    @classmethod
    def default(cls) -> "SoccerRepository":
        """Build (once) the repository from the bundled data directory."""
        if cls._singleton is None:
            cls._singleton = cls.from_dir(DATA_DIR)
        return cls._singleton

    @classmethod
    def from_dir(cls, data_dir: str) -> "SoccerRepository":
        loaders = [
            (_load_brasileirao, "Brasileirao_Matches.csv"),
            (_load_cup, "Brazilian_Cup_Matches.csv"),
            (_load_libertadores, "Libertadores_Matches.csv"),
            (_load_historical, "novo_campeonato_brasileiro.csv"),
            (_load_br_football, "BR-Football-Dataset.csv"),
        ]
        frames = []
        for loader, filename in loaders:
            frames.append(loader(os.path.join(data_dir, filename)))
        matches = pd.concat(frames, ignore_index=True)
        matches = _select_authoritative(matches)

        players = _load_players(os.path.join(data_dir, "fifa_data.csv"))
        return cls(matches=matches, players=players)
