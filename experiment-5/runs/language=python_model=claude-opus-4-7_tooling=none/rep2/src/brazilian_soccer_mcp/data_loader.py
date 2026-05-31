"""Load every provided CSV into a single, queryable in-memory store.

Each upstream file has its own column naming convention; we normalize them
into one tall ``matches`` DataFrame with this schema:

    date          pandas.Timestamp (NaT allowed)
    season        int (0 when unknown)
    competition   one of:
                  "Brasileirão Serie A", "Brasileirão Serie B",
                  "Brasileirão Serie C", "Copa do Brasil",
                  "Copa Libertadores"
    round         str (raw round/stage label, may be empty)
    stage         str (Libertadores only — group stage, final, etc.)
    home_team     raw team name as it appeared in the source file
    away_team     raw team name as it appeared in the source file
    home_team_norm canonical key from normalize.normalize_team
    away_team_norm canonical key from normalize.normalize_team
    home_goal     int
    away_goal     int
    source        which CSV the row came from
    home_corner / away_corner / home_shots / away_shots (optional, float NaN)

Players are kept in a slim ``players`` DataFrame with only the columns the
spec calls out. The full FIFA frame is kept around as ``players_full`` in
case a query needs an attribute that isn't pre-selected.

The default data path is ``data/kaggle/`` relative to the repo root; tests
override it by constructing ``DataStore`` with an explicit path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .normalize import normalize_team

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "kaggle"


_MATCH_COLUMNS = [
    "date",
    "season",
    "competition",
    "round",
    "stage",
    "home_team",
    "away_team",
    "home_team_norm",
    "away_team_norm",
    "home_goal",
    "away_goal",
    "home_corner",
    "away_corner",
    "home_shots",
    "away_shots",
    "source",
]


def _to_int_goal(value) -> int | None:
    """Coerce a goal field to int; return None when unparseable (e.g. '-')."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if value in ("", "-", "—"):
                return None
        result = int(float(value))
    except (TypeError, ValueError):
        return None
    return result


def _parse_date(value) -> pd.Timestamp:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", dayfirst=False)


def _parse_date_brazilian(value) -> pd.Timestamp:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", dayfirst=True)


def _load_brasileirao_matches(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame()
    out["date"] = df["datetime"].map(_parse_date)
    out["season"] = df["season"].astype("Int64").fillna(0).astype(int)
    out["competition"] = "Brasileirão Serie A"
    out["round"] = df["round"].astype(str)
    out["stage"] = ""
    out["home_team"] = df["home_team"].astype(str)
    out["away_team"] = df["away_team"].astype(str)
    out["home_goal"] = df["home_goal"].map(_to_int_goal)
    out["away_goal"] = df["away_goal"].map(_to_int_goal)
    out["source"] = "Brasileirao_Matches.csv"
    return out


def _load_brazilian_cup_matches(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame()
    out["date"] = df["datetime"].map(_parse_date)
    out["season"] = df["season"].astype("Int64").fillna(0).astype(int)
    out["competition"] = "Copa do Brasil"
    out["round"] = df["round"].astype(str)
    out["stage"] = ""
    out["home_team"] = df["home_team"].astype(str)
    out["away_team"] = df["away_team"].astype(str)
    out["home_goal"] = df["home_goal"].map(_to_int_goal)
    out["away_goal"] = df["away_goal"].map(_to_int_goal)
    out["source"] = "Brazilian_Cup_Matches.csv"
    return out


def _load_libertadores_matches(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame()
    out["date"] = df["datetime"].map(_parse_date)
    out["season"] = df["season"].astype("Float64").fillna(0).astype(int)
    out["competition"] = "Copa Libertadores"
    out["round"] = df["stage"].astype(str)
    out["stage"] = df["stage"].astype(str)
    out["home_team"] = df["home_team"].astype(str)
    out["away_team"] = df["away_team"].astype(str)
    out["home_goal"] = df["home_goal"].map(_to_int_goal)
    out["away_goal"] = df["away_goal"].map(_to_int_goal)
    out["source"] = "Libertadores_Matches.csv"
    return out


def _load_br_football_extended(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    tournament_map = {
        "Serie A": "Brasileirão Serie A",
        "Serie B": "Brasileirão Serie B",
        "Serie C": "Brasileirão Serie C",
        "Copa do Brasil": "Copa do Brasil",
    }
    out = pd.DataFrame()
    out["date"] = df["date"].map(_parse_date)
    out["season"] = out["date"].dt.year.fillna(0).astype(int)
    out["competition"] = df["tournament"].map(tournament_map).fillna(df["tournament"])
    out["round"] = ""
    out["stage"] = ""
    out["home_team"] = df["home"].astype(str)
    out["away_team"] = df["away"].astype(str)
    out["home_goal"] = df["home_goal"].map(_to_int_goal)
    out["away_goal"] = df["away_goal"].map(_to_int_goal)
    out["home_corner"] = df.get("home_corner")
    out["away_corner"] = df.get("away_corner")
    out["home_shots"] = df.get("home_shots")
    out["away_shots"] = df.get("away_shots")
    out["source"] = "BR-Football-Dataset.csv"
    return out


def _load_novo_brasileirao(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame()
    out["date"] = df["Data"].map(_parse_date_brazilian)
    out["season"] = df["Ano"].astype("Int64").fillna(0).astype(int)
    out["competition"] = "Brasileirão Serie A"
    out["round"] = df["Rodada"].astype(str)
    out["stage"] = ""
    out["home_team"] = df["Equipe_mandante"].astype(str)
    out["away_team"] = df["Equipe_visitante"].astype(str)
    out["home_goal"] = df["Gols_mandante"].map(_to_int_goal)
    out["away_goal"] = df["Gols_visitante"].map(_to_int_goal)
    out["source"] = "novo_campeonato_brasileiro.csv"
    return out


_MATCH_LOADERS = {
    "Brasileirao_Matches.csv": _load_brasileirao_matches,
    "Brazilian_Cup_Matches.csv": _load_brazilian_cup_matches,
    "Libertadores_Matches.csv": _load_libertadores_matches,
    "BR-Football-Dataset.csv": _load_br_football_extended,
    "novo_campeonato_brasileiro.csv": _load_novo_brasileirao,
}


# When the same fixture appears in multiple source files we keep the row
# from the highest-priority file. The "officially-shaped" files
# (Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches) carry
# state suffixes and explicit competition labels, so we prefer them. The
# historical CSV is next-best; BR-Football-Dataset is only used to fill in
# matches the others miss.
_SOURCE_PRIORITY = {
    "Brasileirao_Matches.csv": 1,
    "Brazilian_Cup_Matches.csv": 1,
    "Libertadores_Matches.csv": 1,
    "novo_campeonato_brasileiro.csv": 2,
    "BR-Football-Dataset.csv": 3,
}


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in _MATCH_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[_MATCH_COLUMNS]


def _dedup_matches(matches: pd.DataFrame) -> pd.DataFrame:
    """Remove rows that describe the same fixture in multiple source files.

    Two passes:
      1. Exact-date dedup — keys on (date.date, home_norm, away_norm,
         home_goal, away_goal). Catches identical rows.
      2. Same-month dedup — keys on (year, month, home_norm, away_norm,
         home_goal, away_goal). Catches rows where the same kickoff was
         recorded in local vs UTC time (off by one day).

    Within each pass we sort by ``_priority`` (lower = better source) so
    ``drop_duplicates(keep="first")`` keeps the higher-priority row.
    """
    matches = matches.copy()
    matches["_priority"] = matches["source"].map(_SOURCE_PRIORITY).fillna(99).astype(int)
    matches["_date_only"] = matches["date"].dt.normalize()
    matches["_year"] = matches["date"].dt.year
    matches["_month"] = matches["date"].dt.month
    matches = matches.sort_values(["_priority", "date"], kind="mergesort")
    matches = matches.drop_duplicates(
        subset=[
            "_date_only",
            "home_team_norm",
            "away_team_norm",
            "home_goal",
            "away_goal",
        ],
        keep="first",
    )
    matches = matches.drop_duplicates(
        subset=[
            "_year",
            "_month",
            "home_team_norm",
            "away_team_norm",
            "home_goal",
            "away_goal",
        ],
        keep="first",
    )
    matches = matches.drop(columns=["_priority", "_date_only", "_year", "_month"])
    return matches.sort_values("date", kind="mergesort").reset_index(drop=True)


def _load_players(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    full = pd.read_csv(path, low_memory=False)
    slim = pd.DataFrame()
    slim["id"] = full["ID"]
    slim["name"] = full["Name"].astype(str)
    slim["age"] = pd.to_numeric(full["Age"], errors="coerce").astype("Int64")
    slim["nationality"] = full["Nationality"].astype(str)
    slim["overall"] = pd.to_numeric(full["Overall"], errors="coerce").astype("Int64")
    slim["potential"] = pd.to_numeric(full["Potential"], errors="coerce").astype("Int64")
    slim["club"] = full["Club"].fillna("").astype(str)
    slim["position"] = full["Position"].fillna("").astype(str)
    slim["jersey_number"] = pd.to_numeric(full["Jersey Number"], errors="coerce").astype("Int64")
    slim["height"] = full["Height"].fillna("").astype(str)
    slim["weight"] = full["Weight"].fillna("").astype(str)
    slim["name_lower"] = slim["name"].str.lower()
    slim["club_norm"] = slim["club"].map(normalize_team)
    slim["nationality_lower"] = slim["nationality"].str.lower()
    return slim, full


@dataclass
class DataStore:
    """In-memory store of every CSV the spec ships with."""

    data_dir: Path = field(default_factory=lambda: DEFAULT_DATA_DIR)
    matches: pd.DataFrame = field(init=False)
    players: pd.DataFrame = field(init=False)
    players_full: pd.DataFrame = field(init=False)

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        frames: list[pd.DataFrame] = []
        for filename, loader in _MATCH_LOADERS.items():
            path = self.data_dir / filename
            if not path.exists():
                continue
            frame = loader(path)
            frame = _ensure_columns(frame)
            frames.append(frame)
        if not frames:
            raise FileNotFoundError(f"No match CSVs found under {self.data_dir}")
        self.matches = pd.concat(frames, ignore_index=True)
        # Drop rows where goals are unrecoverable; they break aggregations and
        # the spec only cares about completed matches.
        self.matches = self.matches.dropna(subset=["home_goal", "away_goal"]).copy()
        self.matches["home_goal"] = self.matches["home_goal"].astype(int)
        self.matches["away_goal"] = self.matches["away_goal"].astype(int)
        self.matches["home_team_norm"] = self.matches["home_team"].map(normalize_team)
        self.matches["away_team_norm"] = self.matches["away_team"].map(normalize_team)
        self.matches["date"] = pd.to_datetime(self.matches["date"], errors="coerce")
        self.matches = _dedup_matches(self.matches)

        players_path = self.data_dir / "fifa_data.csv"
        if players_path.exists():
            self.players, self.players_full = _load_players(players_path)
        else:
            self.players = pd.DataFrame(
                columns=[
                    "id",
                    "name",
                    "age",
                    "nationality",
                    "overall",
                    "potential",
                    "club",
                    "position",
                    "jersey_number",
                    "height",
                    "weight",
                    "name_lower",
                    "club_norm",
                    "nationality_lower",
                ]
            )
            self.players_full = pd.DataFrame()


def load_default() -> DataStore:
    """Convenience constructor pointing at the repo's data/kaggle directory."""
    return DataStore()
