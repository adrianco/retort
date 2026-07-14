"""CSV data loaders for the Brazilian Soccer MCP server.

Loads all six provided datasets, normalizes team/competition names, parses
dates, and exposes them as a single :class:`DataStore`. Loading is performed
eagerly the first time :func:`load_all` is called and the result is cached so
that the MCP server only pays the I/O cost once per process.

Output schemas (all match DataFrames are concatenated into one ``matches``
table with the columns below):

- ``date``                pandas Timestamp (or NaT)
- ``home_team``           original home team name
- ``away_team``           original away team name
- ``home_team_norm``      normalized home team key
- ``away_team_norm``      normalized away team key
- ``home_goals``          int
- ``away_goals``          int
- ``season``              int (year)
- ``round``               string (may be empty)
- ``stage``               string (may be empty)
- ``competition``         "Brasileirão" / "Copa do Brasil" / "Libertadores" /
                          "Brasileirão (historical)" / various from BR-Football
- ``source``              short tag identifying the source file
- ``arena``               stadium name (from novo_campeonato_brasileiro only)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .normalize import normalize_team_name, strip_state_suffix

KAGGLE_FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "copa": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "br_football": "BR-Football-Dataset.csv",
    "historical": "novo_campeonato_brasileiro.csv",
    "fifa": "fifa_data.csv",
}


def default_data_dir() -> Path:
    """Locate the data/kaggle directory shipped with this repo."""
    env = os.environ.get("BRAZILIAN_SOCCER_DATA_DIR")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "data" / "kaggle"
        if candidate.is_dir():
            return candidate
    return Path("data/kaggle")


def _to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


def _parse_datetime(series: pd.Series, dayfirst: bool = False) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=dayfirst)


def _load_brasileirao(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "date": _parse_datetime(df["datetime"]),
        "home_team": df["home_team"].astype(str),
        "away_team": df["away_team"].astype(str),
        "home_goals": _to_int(df["home_goal"]),
        "away_goals": _to_int(df["away_goal"]),
        "season": _to_int(df["season"]),
        "round": df["round"].astype(str),
        "stage": "",
        "competition": "Brasileirão",
        "source": "brasileirao",
        "arena": "",
    })
    return out


def _load_copa(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return pd.DataFrame({
        "date": _parse_datetime(df["datetime"]),
        "home_team": df["home_team"].astype(str),
        "away_team": df["away_team"].astype(str),
        "home_goals": _to_int(df["home_goal"]),
        "away_goals": _to_int(df["away_goal"]),
        "season": _to_int(df["season"]),
        "round": df["round"].astype(str),
        "stage": "",
        "competition": "Copa do Brasil",
        "source": "copa_do_brasil",
        "arena": "",
    })


def _load_libertadores(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return pd.DataFrame({
        "date": _parse_datetime(df["datetime"]),
        "home_team": df["home_team"].astype(str),
        "away_team": df["away_team"].astype(str),
        "home_goals": _to_int(df["home_goal"]),
        "away_goals": _to_int(df["away_goal"]),
        "season": _to_int(df["season"]),
        "round": "",
        "stage": df["stage"].astype(str),
        "competition": "Copa Libertadores",
        "source": "libertadores",
        "arena": "",
    })


def _load_br_football(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    dates = _parse_datetime(df["date"])
    return pd.DataFrame({
        "date": dates,
        "home_team": df["home"].astype(str),
        "away_team": df["away"].astype(str),
        "home_goals": _to_int(df["home_goal"]),
        "away_goals": _to_int(df["away_goal"]),
        "season": dates.dt.year.fillna(0).astype(int),
        "round": "",
        "stage": "",
        "competition": df["tournament"].astype(str),
        "source": "br_football",
        "arena": "",
        "home_corner": _to_int(df["home_corner"]),
        "away_corner": _to_int(df["away_corner"]),
        "home_shots": _to_int(df["home_shots"]),
        "away_shots": _to_int(df["away_shots"]),
        "total_corners": _to_int(df["total_corners"]),
    })


def _load_historical(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return pd.DataFrame({
        "date": _parse_datetime(df["Data"], dayfirst=True),
        "home_team": df["Equipe_mandante"].astype(str),
        "away_team": df["Equipe_visitante"].astype(str),
        "home_goals": _to_int(df["Gols_mandante"]),
        "away_goals": _to_int(df["Gols_visitante"]),
        "season": _to_int(df["Ano"]),
        "round": df["Rodada"].astype(str),
        "stage": "",
        "competition": "Brasileirão (historical)",
        "source": "historical",
        "arena": df["Arena"].fillna("").astype(str),
    })


def _attach_norm(df: pd.DataFrame) -> pd.DataFrame:
    df["home_team_norm"] = df["home_team"].map(normalize_team_name)
    df["away_team_norm"] = df["away_team"].map(normalize_team_name)
    df["home_team_short"] = df["home_team_norm"].map(strip_state_suffix)
    df["away_team_short"] = df["away_team_norm"].map(strip_state_suffix)
    return df


def _load_matches(data_dir: Path) -> pd.DataFrame:
    parts = [
        _load_brasileirao(data_dir / KAGGLE_FILES["brasileirao"]),
        _load_copa(data_dir / KAGGLE_FILES["copa"]),
        _load_libertadores(data_dir / KAGGLE_FILES["libertadores"]),
        _load_br_football(data_dir / KAGGLE_FILES["br_football"]),
        _load_historical(data_dir / KAGGLE_FILES["historical"]),
    ]
    matches = pd.concat(parts, ignore_index=True, sort=False)
    matches = _attach_norm(matches)
    matches["home_goals"] = matches["home_goals"].astype(int)
    matches["away_goals"] = matches["away_goals"].astype(int)
    matches["season"] = matches["season"].astype(int)

    # Normalize competition labels across sources.
    matches.loc[matches["competition"] == "Brasileirão (historical)", "competition"] = "Brasileirão"
    matches.loc[
        (matches["source"] == "br_football") & (matches["competition"] == "Serie A"),
        "competition",
    ] = "Brasileirão"

    # The historical (2003-2019), brasileirao (2012+) and BR-Football Serie A
    # (~2018+) sources all cover Brasileirão Serie A and overlap. To avoid
    # double-counting standings, for each Brasileirão season keep exactly one
    # source — the most precise one available. Priority: brasileirao first,
    # then BR-Football, then historical.
    is_bras = matches["competition"] == "Brasileirão"
    keep_rows = ~is_bras  # non-Brasileirão rows are kept as-is
    bras = matches[is_bras]
    for season, group in bras.groupby("season"):
        sources_present = set(group["source"].unique())
        if "brasileirao" in sources_present:
            chosen = "brasileirao"
        elif "br_football" in sources_present:
            chosen = "br_football"
        else:
            chosen = "historical"
        season_keep = (matches["season"] == season) & is_bras & (matches["source"] == chosen)
        keep_rows |= season_keep
    matches = matches[keep_rows].reset_index(drop=True)
    return matches


def _load_players(data_dir: Path) -> pd.DataFrame:
    path = data_dir / KAGGLE_FILES["fifa"]
    # The first column is an unnamed index; keep usecols light to save memory.
    cols = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential",
        "Club", "Position", "Jersey Number", "Height", "Weight",
        "Preferred Foot", "Wage", "Value",
    ]
    df = pd.read_csv(path, usecols=cols)
    df = df.rename(columns={
        "ID": "id",
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
        "Preferred Foot": "preferred_foot",
        "Wage": "wage",
        "Value": "value",
    })
    df["club"] = df["club"].fillna("")
    df["nationality"] = df["nationality"].fillna("")
    df["position"] = df["position"].fillna("")
    df["club_norm"] = df["club"].map(normalize_team_name)
    df["club_short"] = df["club_norm"].map(strip_state_suffix)
    df["name_lower"] = df["name"].astype(str).str.lower()
    df["nationality_lower"] = df["nationality"].astype(str).str.lower()
    df["overall"] = pd.to_numeric(df["overall"], errors="coerce").fillna(0).astype(int)
    df["potential"] = pd.to_numeric(df["potential"], errors="coerce").fillna(0).astype(int)
    df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(0).astype(int)
    return df


@dataclass
class DataStore:
    """Container for the loaded datasets."""

    matches: pd.DataFrame
    players: pd.DataFrame
    data_dir: Path = field(default_factory=default_data_dir)

    def teams(self) -> list[str]:
        names = pd.concat([self.matches["home_team"], self.matches["away_team"]])
        return sorted(set(names.dropna().astype(str)))

    def normalized_teams(self, *, short: bool = False) -> list[str]:
        if short:
            names = pd.concat([self.matches["home_team_short"], self.matches["away_team_short"]])
        else:
            names = pd.concat([self.matches["home_team_norm"], self.matches["away_team_norm"]])
        return sorted({n for n in names if n})

    def competitions(self) -> list[str]:
        return sorted(set(self.matches["competition"].dropna().astype(str)))


@lru_cache(maxsize=4)
def load_all(data_dir: str | None = None) -> DataStore:
    """Load every dataset from disk. Cached by directory path."""
    directory = Path(data_dir) if data_dir else default_data_dir()
    matches = _load_matches(directory)
    players = _load_players(directory)
    return DataStore(matches=matches, players=players, data_dir=directory)
