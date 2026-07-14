"""Loading and normalization of the bundled Brazilian soccer CSV files.

The six CSV files use different schemas; this module reads each one and
produces a single unified ``matches`` DataFrame plus a ``players`` DataFrame.
Every match row gets these canonical columns:

    competition, season, round, date, home_team, away_team,
    home_goal, away_goal, stage, home_state, away_state,
    venue, home_team_norm, away_team_norm

The unified frame is what every higher-level query operates on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pandas as pd

from .team_names import loose_key, normalize


DATA_DIR_DEFAULT = Path(__file__).resolve().parents[2] / "data" / "kaggle"

_FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "copa_do_brasil": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "br_football": "BR-Football-Dataset.csv",
    "novo_brasileirao": "novo_campeonato_brasileiro.csv",
    "fifa": "fifa_data.csv",
}


def _to_int(value) -> int | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_date(value) -> pd.Timestamp | None:
    """Parse a date in either ISO or Brazilian (DD/MM/YYYY) format."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    # Try a sequence of explicit formats first to avoid pandas' inference warnings.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            continue
    try:
        return pd.to_datetime(s, errors="coerce", dayfirst=True)
    except Exception:  # pragma: no cover - defensive
        return None


def _load_brasileirao(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "competition": "Brasileirão Serie A",
        "season": df["season"].apply(_to_int),
        "round": df["round"].apply(_to_int),
        "date": df["datetime"].apply(_parse_date),
        "home_team": df["home_team"].astype(str),
        "away_team": df["away_team"].astype(str),
        "home_goal": df["home_goal"].apply(_to_int),
        "away_goal": df["away_goal"].apply(_to_int),
        "stage": "",
        "home_state": df["home_team_state"].astype(str),
        "away_state": df["away_team_state"].astype(str),
        "venue": "",
        "source": "Brasileirao_Matches.csv",
    })
    return out


def _load_cup(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return pd.DataFrame({
        "competition": "Copa do Brasil",
        "season": df["season"].apply(_to_int),
        "round": df["round"].astype(str),
        "date": df["datetime"].apply(_parse_date),
        "home_team": df["home_team"].astype(str),
        "away_team": df["away_team"].astype(str),
        "home_goal": df["home_goal"].apply(_to_int),
        "away_goal": df["away_goal"].apply(_to_int),
        "stage": df["round"].astype(str),
        "home_state": "",
        "away_state": "",
        "venue": "",
        "source": "Brazilian_Cup_Matches.csv",
    })


def _load_libertadores(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return pd.DataFrame({
        "competition": "Copa Libertadores",
        "season": df["season"].apply(_to_int),
        "round": None,
        "date": df["datetime"].apply(_parse_date),
        "home_team": df["home_team"].astype(str),
        "away_team": df["away_team"].astype(str),
        "home_goal": df["home_goal"].apply(_to_int),
        "away_goal": df["away_goal"].apply(_to_int),
        "stage": df["stage"].astype(str),
        "home_state": "",
        "away_state": "",
        "venue": "",
        "source": "Libertadores_Matches.csv",
    })


def _load_br_football(path: Path) -> pd.DataFrame:
    # BR-Football reports kick-off dates that occasionally differ by ±1 day
    # from the other files, so we don't try to merge its competitions into
    # the same names as the canonical Brasileirão / Cup files — that would
    # cause false "extra" matches in the standings.
    df = pd.read_csv(path)
    dates = df["date"].apply(_parse_date)
    seasons = dates.apply(lambda d: d.year if d is not None and not pd.isna(d) else None)
    return pd.DataFrame({
        "competition": df["tournament"].astype(str),
        "season": seasons,
        "round": None,
        "date": dates,
        "home_team": df["home"].astype(str),
        "away_team": df["away"].astype(str),
        "home_goal": df["home_goal"].apply(_to_int),
        "away_goal": df["away_goal"].apply(_to_int),
        "stage": "",
        "home_state": "",
        "away_state": "",
        "venue": "",
        "source": "BR-Football-Dataset.csv",
        "home_corner": df["home_corner"],
        "away_corner": df["away_corner"],
        "home_shots": df["home_shots"],
        "away_shots": df["away_shots"],
    })


def _load_novo(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return pd.DataFrame({
        "competition": "Brasileirão Serie A",
        "season": df["Ano"].apply(_to_int),
        "round": df["Rodada"].apply(_to_int),
        "date": df["Data"].apply(_parse_date),
        "home_team": df["Equipe_mandante"].astype(str),
        "away_team": df["Equipe_visitante"].astype(str),
        "home_goal": df["Gols_mandante"].apply(_to_int),
        "away_goal": df["Gols_visitante"].apply(_to_int),
        "stage": "",
        "home_state": df["Mandante_UF"].astype(str),
        "away_state": df["Visitante_UF"].astype(str),
        "venue": df["Arena"].astype(str),
        "source": "novo_campeonato_brasileiro.csv",
    })


def _load_fifa(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    # First column is an unnamed index in the source file.
    if df.columns[0].startswith("Unnamed") or df.columns[0] == "":
        df = df.drop(columns=df.columns[0])
    return df


@dataclass
class DataStore:
    """In-memory store of the loaded soccer datasets."""

    matches: pd.DataFrame
    players: pd.DataFrame
    sources: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.matches = self.matches.copy()
        self.matches["home_team_norm"] = self.matches["home_team"].map(normalize)
        self.matches["away_team_norm"] = self.matches["away_team"].map(normalize)
        # Brasileirao_Matches.csv (2012+) and novo_campeonato_brasileiro.csv (2003-2019)
        # overlap on 2012-2019. Use a loose key (state suffix stripped) so
        # "Palmeiras" and "Palmeiras-SP" dedupe to the same row.
        self.matches["_date_key"] = self.matches["date"].dt.strftime("%Y-%m-%d")
        self.matches["_h_loose"] = self.matches["home_team"].map(loose_key)
        self.matches["_a_loose"] = self.matches["away_team"].map(loose_key)
        self.matches = (
            self.matches.sort_values("source")
            .drop_duplicates(
                subset=["competition", "season", "_date_key", "_h_loose", "_a_loose"],
                keep="first",
            )
            .drop(columns=["_date_key", "_h_loose", "_a_loose"])
            .reset_index(drop=True)
        )


def load_all(data_dir: str | Path | None = None) -> DataStore:
    """Load every CSV file and return a populated :class:`DataStore`."""
    base = Path(data_dir) if data_dir else DATA_DIR_DEFAULT
    if not base.exists():
        raise FileNotFoundError(f"Data directory not found: {base}")

    loaders = [
        _load_brasileirao(base / _FILES["brasileirao"]),
        _load_cup(base / _FILES["copa_do_brasil"]),
        _load_libertadores(base / _FILES["libertadores"]),
        _load_br_football(base / _FILES["br_football"]),
        _load_novo(base / _FILES["novo_brasileirao"]),
    ]
    matches = pd.concat(loaders, ignore_index=True, sort=False)
    players = _load_fifa(base / _FILES["fifa"])
    sources = {df["source"].iloc[0]: len(df) for df in loaders if len(df) > 0}
    sources[_FILES["fifa"]] = len(players)
    return DataStore(matches=matches, players=players, sources=sources)
