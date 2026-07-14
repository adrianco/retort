"""
Context
=======
Module: bsoccer.data
Purpose: Load the six provided Kaggle CSV files into clean, normalized pandas
         DataFrames that the query engine (bsoccer.queries) operates on.

Output shape
------------
SoccerData exposes two DataFrames:

  matches  - one row per match, unified across all 5 match files. Columns:
               competition      canonical competition label
               source           originating CSV (for provenance / dedup)
               season           int year
               date             pandas.Timestamp (NaT if unknown)
               round            round / stage label as string (may be "")
               home_team        display name (suffix-stripped)
               away_team        display name
               home_key         normalized lookup key (bsoccer.normalize)
               away_key         normalized lookup key
               home_goal        int
               away_goal        int
               stadium          stadium name where available ("")

  players  - one row per FIFA player with the documented key columns plus a
             normalized club key for cross-file joins with match data.

Design notes
------------
* The Brasileirão appears in three files with overlapping seasons
  (Brasileirao_Matches 2012-2022, novo_campeonato 2003-2019, BR-Football
  Serie A). We keep all rows but tag a `source`, and provide a deduplicated
  view (`matches_dedup`) keyed on (season, home_key, away_key, goals) so
  standings/aggregates do not double-count.
* All reads are UTF-8 with encoding fallbacks to tolerate the Portuguese
  special characters in the data.
"""

from __future__ import annotations

import os
from functools import cached_property

import pandas as pd

from .normalize import display_name, normalize_team

# Default data location relative to the repository root.
_DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "kaggle",
)

# Unified competition labels.
BRASILEIRAO = "Brasileirão"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

_MATCH_COLUMNS = [
    "competition", "source", "season", "date", "round",
    "home_team", "away_team", "home_key", "away_key",
    "home_goal", "away_goal", "stadium",
]


def _read_csv(path: str) -> pd.DataFrame:
    """Read a CSV with UTF-8, falling back to latin-1 for robustness."""
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    # Last resort: replace undecodable bytes rather than crash.
    return pd.read_csv(path, encoding="utf-8", encoding_errors="replace")


def _to_int(series: pd.Series) -> pd.Series:
    """Coerce a goal column (which may be quoted strings/floats) to nullable int."""
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _build_keys(df: pd.DataFrame, home_col: str, away_col: str) -> pd.DataFrame:
    """Attach display + normalized-key columns derived from raw team columns.

    Keys are computed from the raw columns FIRST, before the display columns are
    written, because some files name their raw column "home_team" — assigning the
    display value there first would otherwise feed the already-stripped name into
    normalize_team and drop the disambiguating state suffix.
    """
    df = df.copy()
    home_key = df[home_col].map(normalize_team)
    away_key = df[away_col].map(normalize_team)
    home_disp = df[home_col].map(display_name)
    away_disp = df[away_col].map(display_name)
    df["home_key"] = home_key
    df["away_key"] = away_key
    df["home_team"] = home_disp
    df["away_team"] = away_disp
    return df


class SoccerData:
    """Loads and holds the normalized Brazilian soccer datasets.

    Loading is lazy and cached: DataFrames are built on first access so that
    importing the module (e.g. for tests that only touch normalization) is cheap.
    """

    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or _DEFAULT_DATA_DIR
        if not os.path.isdir(self.data_dir):
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

    def _path(self, name: str) -> str:
        return os.path.join(self.data_dir, name)

    # ----- individual file loaders ---------------------------------------

    def _load_brasileirao(self) -> pd.DataFrame:
        df = _read_csv(self._path("Brasileirao_Matches.csv"))
        df = _build_keys(df, "home_team", "away_team")
        out = pd.DataFrame({
            "competition": BRASILEIRAO,
            "source": "Brasileirao_Matches",
            "season": pd.to_numeric(df["season"], errors="coerce").astype("Int64"),
            "date": pd.to_datetime(df["datetime"], errors="coerce"),
            "round": df["round"].astype(str),
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_key": df["home_key"],
            "away_key": df["away_key"],
            "home_goal": _to_int(df["home_goal"]),
            "away_goal": _to_int(df["away_goal"]),
            "stadium": "",
        })
        return out

    def _load_cup(self) -> pd.DataFrame:
        df = _read_csv(self._path("Brazilian_Cup_Matches.csv"))
        df = _build_keys(df, "home_team", "away_team")
        out = pd.DataFrame({
            "competition": COPA_DO_BRASIL,
            "source": "Brazilian_Cup_Matches",
            "season": pd.to_numeric(df["season"], errors="coerce").astype("Int64"),
            "date": pd.to_datetime(df["datetime"], errors="coerce"),
            "round": df["round"].astype(str),
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_key": df["home_key"],
            "away_key": df["away_key"],
            "home_goal": _to_int(df["home_goal"]),
            "away_goal": _to_int(df["away_goal"]),
            "stadium": "",
        })
        return out

    def _load_libertadores(self) -> pd.DataFrame:
        df = _read_csv(self._path("Libertadores_Matches.csv"))
        df = _build_keys(df, "home_team", "away_team")
        out = pd.DataFrame({
            "competition": LIBERTADORES,
            "source": "Libertadores_Matches",
            "season": pd.to_numeric(df["season"], errors="coerce").astype("Int64"),
            "date": pd.to_datetime(df["datetime"], errors="coerce"),
            "round": df["stage"].astype(str),
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_key": df["home_key"],
            "away_key": df["away_key"],
            "home_goal": _to_int(df["home_goal"]),
            "away_goal": _to_int(df["away_goal"]),
            "stadium": "",
        })
        return out

    def _load_br_football(self) -> pd.DataFrame:
        df = _read_csv(self._path("BR-Football-Dataset.csv"))
        df = _build_keys(df, "home", "away")
        date = pd.to_datetime(df["date"], errors="coerce")
        out = pd.DataFrame({
            "competition": df["tournament"].astype(str),
            "source": "BR-Football-Dataset",
            "season": date.dt.year.astype("Int64"),
            "date": date,
            "round": "",
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_key": df["home_key"],
            "away_key": df["away_key"],
            "home_goal": _to_int(df["home_goal"]),
            "away_goal": _to_int(df["away_goal"]),
            "stadium": "",
        })
        return out

    def _load_novo(self) -> pd.DataFrame:
        df = _read_csv(self._path("novo_campeonato_brasileiro.csv"))
        df = _build_keys(df, "Equipe_mandante", "Equipe_visitante")
        out = pd.DataFrame({
            "competition": BRASILEIRAO,
            "source": "novo_campeonato_brasileiro",
            "season": pd.to_numeric(df["Ano"], errors="coerce").astype("Int64"),
            "date": pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce"),
            "round": df["Rodada"].astype(str),
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_key": df["home_key"],
            "away_key": df["away_key"],
            "home_goal": _to_int(df["Gols_mandante"]),
            "away_goal": _to_int(df["Gols_visitante"]),
            "stadium": df["Arena"].fillna("").astype(str),
        })
        return out

    # ----- combined views -------------------------------------------------

    @cached_property
    def matches(self) -> pd.DataFrame:
        """Unified match table across all five match files."""
        frames = [
            self._load_brasileirao(),
            self._load_cup(),
            self._load_libertadores(),
            self._load_br_football(),
            self._load_novo(),
        ]
        df = pd.concat(frames, ignore_index=True)
        # Drop rows with no usable score.
        df = df.dropna(subset=["home_goal", "away_goal"]).reset_index(drop=True)
        df = df[_MATCH_COLUMNS]
        return df

    @cached_property
    def matches_dedup(self) -> pd.DataFrame:
        """Match table with cross-file duplicates removed.

        Brasileirão seasons overlap across three files. We collapse rows that
        share the same (competition, season, home_key, away_key, goals) and,
        when available, date, keeping the first occurrence. This view is used
        for standings and aggregate stats to avoid double counting.
        """
        df = self.matches.copy()
        df["_date_key"] = df["date"].dt.date.astype(str)
        df = df.drop_duplicates(
            subset=["competition", "season", "_date_key",
                    "home_key", "away_key", "home_goal", "away_goal"],
            keep="first",
        )
        # Secondary pass for rows where one source lacks a date: collapse on
        # season+teams+score regardless of date.
        df = df.drop_duplicates(
            subset=["competition", "season", "home_key", "away_key",
                    "home_goal", "away_goal", "round"],
            keep="first",
        )
        return df.drop(columns="_date_key").reset_index(drop=True)

    @cached_property
    def players(self) -> pd.DataFrame:
        """FIFA player table with a normalized club key added."""
        df = _read_csv(self._path("fifa_data.csv"))
        # The first unnamed column is a row index; drop it if present.
        if df.columns[0].strip() == "" or df.columns[0].startswith("Unnamed"):
            df = df.drop(columns=df.columns[0])
        df["club_key"] = df["Club"].fillna("").map(normalize_team)
        df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
        df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce")
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
        return df

    # ----- metadata helpers ----------------------------------------------

    @cached_property
    def competitions(self) -> list[str]:
        return sorted(self.matches["competition"].dropna().unique().tolist())

    def team_directory(self) -> dict[str, str]:
        """Map normalized key -> a representative display name across matches."""
        directory: dict[str, str] = {}
        m = self.matches
        for key, name in zip(m["home_key"], m["home_team"]):
            directory.setdefault(key, name)
        for key, name in zip(m["away_key"], m["away_team"]):
            directory.setdefault(key, name)
        directory.pop("", None)
        return directory


# Module-level singleton accessor so the MCP server shares one loaded copy.
_SINGLETON: SoccerData | None = None


def get_data(data_dir: str | None = None) -> SoccerData:
    """Return a process-wide SoccerData instance (loaded lazily)."""
    global _SINGLETON
    if _SINGLETON is None or data_dir is not None:
        _SINGLETON = SoccerData(data_dir)
    return _SINGLETON
