"""
================================================================================
brazilian_soccer_mcp.data_loader
================================================================================

CONTEXT
-------
Reads the six provided Kaggle CSV files from ``data/kaggle/`` and turns them
into two tidy pandas DataFrames with a stable, documented schema:

MATCHES schema (one row per match):
    competition   str   canonical competition name
    season        int   season / year
    date          date  match date (python ``datetime.date`` or None)
    round         str   round / stage label (may be None)
    home_team     str   cleaned home team display name
    away_team     str   cleaned away team display name
    home_norm     str   normalised home team key (for matching)
    away_norm     str   normalised away team key
    home_goal     int   home goals
    away_goal     int   away goals
    source        str   originating CSV file
    extra         dict  any source-specific extra stats (corners, shots, ...)

PLAYERS schema (one row per player) keeps the most useful FIFA columns plus a
``club_norm`` / ``name_norm`` for matching.

Loading is deliberately defensive: rows with unparseable scores are skipped
rather than crashing the whole load. The result is cached so repeated access in
the test-suite or the running server is cheap.

The data directory can be overridden with the ``BR_SOCCER_DATA_DIR`` env var,
otherwise it defaults to ``<repo>/data/kaggle``.
================================================================================
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from .normalize import (
    canonical_norm,
    canonical_team_name,
    parse_date,
    strip_accents,
)

# --- Canonical competition names -------------------------------------------------
BRASILEIRAO = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

_BR_FOOTBALL_TOURNAMENTS = {
    "serie a": BRASILEIRAO,
    "serie b": BRASILEIRAO_B,
    "serie c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
}


def default_data_dir() -> Path:
    env = os.environ.get("BR_SOCCER_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1] / "data" / "kaggle"


def _to_int(value) -> Optional[int]:
    """Coerce a score-like value to int, tolerating floats/strings; None if bad."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if value == "" or value.lower() in {"nan", "na"}:
                return None
        f = float(value)
        if f != f:  # NaN
            return None
        return int(round(f))
    except (ValueError, TypeError):
        return None


def _make_row(competition, season, date_val, round_val, home, away, hg, ag,
              source, extra=None):
    hg_i, ag_i = _to_int(hg), _to_int(ag)
    if hg_i is None or ag_i is None:
        return None
    return {
        "competition": competition,
        "season": _to_int(season),
        "date": parse_date(date_val),
        "round": str(round_val) if round_val is not None and str(round_val) != "nan" else None,
        "home_team": canonical_team_name(home),
        "away_team": canonical_team_name(away),
        "home_norm": canonical_norm(home),
        "away_norm": canonical_norm(away),
        "home_goal": hg_i,
        "away_goal": ag_i,
        "source": source,
        "extra": extra or {},
    }


def _load_brasileirao(path: Path) -> list:
    df = pd.read_csv(path, encoding="utf-8")
    rows = []
    for r in df.itertuples(index=False):
        row = _make_row(BRASILEIRAO, r.season, r.datetime, r.round,
                        r.home_team, r.away_team, r.home_goal, r.away_goal,
                        path.name)
        if row:
            rows.append(row)
    return rows


def _load_cup(path: Path) -> list:
    df = pd.read_csv(path, encoding="utf-8")
    rows = []
    for r in df.itertuples(index=False):
        row = _make_row(COPA_DO_BRASIL, r.season, r.datetime, r.round,
                        r.home_team, r.away_team, r.home_goal, r.away_goal,
                        path.name)
        if row:
            rows.append(row)
    return rows


def _load_libertadores(path: Path) -> list:
    df = pd.read_csv(path, encoding="utf-8")
    rows = []
    for r in df.itertuples(index=False):
        row = _make_row(LIBERTADORES, r.season, r.datetime, r.stage,
                        r.home_team, r.away_team, r.home_goal, r.away_goal,
                        path.name)
        if row:
            rows.append(row)
    return rows


def _load_novo(path: Path) -> list:
    df = pd.read_csv(path, encoding="utf-8")
    rows = []
    for r in df.itertuples(index=False):
        row = _make_row(BRASILEIRAO, r.Ano, r.Data, r.Rodada,
                        r.Equipe_mandante, r.Equipe_visitante,
                        r.Gols_mandante, r.Gols_visitante, path.name,
                        extra={"arena": getattr(r, "Arena", None)})
        if row:
            rows.append(row)
    return rows


def _load_br_football(path: Path) -> list:
    df = pd.read_csv(path, encoding="utf-8")
    rows = []
    for r in df.itertuples(index=False):
        comp = _BR_FOOTBALL_TOURNAMENTS.get(
            strip_accents(str(r.tournament)).strip().lower(), str(r.tournament)
        )
        d = parse_date(r.date)
        season = d.year if d else None
        extra = {
            "home_corner": r.home_corner,
            "away_corner": r.away_corner,
            "home_shots": r.home_shots,
            "away_shots": r.away_shots,
            "home_attack": r.home_attack,
            "away_attack": r.away_attack,
        }
        row = _make_row(comp, season, r.date, None,
                        r.home, r.away, r.home_goal, r.away_goal,
                        path.name, extra=extra)
        if row:
            rows.append(row)
    return rows


_MATCH_LOADERS = {
    "Brasileirao_Matches.csv": _load_brasileirao,
    "Brazilian_Cup_Matches.csv": _load_cup,
    "Libertadores_Matches.csv": _load_libertadores,
    "novo_campeonato_brasileiro.csv": _load_novo,
    "BR-Football-Dataset.csv": _load_br_football,
}

# When several files cover the same (competition, season) we keep only the single
# most authoritative source to avoid double-counting in standings / records.
# Lower number = higher priority. The dedicated per-competition files (which carry
# rounds/stages and clean naming) win over the broad BR-Football aggregate.
_SOURCE_PRIORITY = {
    "Brasileirao_Matches.csv": 0,
    "Brazilian_Cup_Matches.csv": 1,
    "Libertadores_Matches.csv": 2,
    "novo_campeonato_brasileiro.csv": 3,
    "BR-Football-Dataset.csv": 4,
}


def load_matches(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load and unify every match CSV into a single normalised DataFrame.

    Overlapping seasons (Série A appears in three files) are reconciled by
    keeping, for each (competition, season), only the highest-priority source so
    aggregate statistics are not inflated by duplicate fixtures.
    """
    data_dir = Path(data_dir) if data_dir else default_data_dir()
    all_rows = []
    for filename, loader in _MATCH_LOADERS.items():
        path = data_dir / filename
        if path.exists():
            all_rows.extend(loader(path))
    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    # Exact-duplicate pass (identical fixture rows within / across files).
    df["_key"] = (
        df["competition"].astype(str)
        + "|" + df["season"].astype(str)
        + "|" + df["date"].astype(str)
        + "|" + df["home_norm"] + "|" + df["away_norm"]
        + "|" + df["home_goal"].astype(str) + "|" + df["away_goal"].astype(str)
    )
    df = df.drop_duplicates("_key").drop(columns="_key")

    # Source-priority pass: per (competition, season) keep the single best source.
    df["_rank"] = df["source"].map(_SOURCE_PRIORITY).fillna(99)
    df["_grp_season"] = df["season"].fillna(-1).astype(int)
    best = df.groupby(["competition", "_grp_season"])["_rank"].transform("min")
    df = df[df["_rank"] == best]
    df = df.drop(columns=["_rank", "_grp_season"]).reset_index(drop=True)
    return df


# FIFA columns we keep (a curated subset of the 88 available columns).
_PLAYER_COLUMNS = [
    "ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club",
    "Position", "Jersey Number", "Height", "Weight", "Preferred Foot",
    "Value", "Wage", "Crossing", "Finishing", "Dribbling", "ShortPassing",
    "BallControl", "Acceleration", "SprintSpeed", "ShotPower", "Stamina",
]


def load_players(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load the FIFA player database into a tidy DataFrame."""
    data_dir = Path(data_dir) if data_dir else default_data_dir()
    path = data_dir / "fifa_data.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    keep = [c for c in _PLAYER_COLUMNS if c in df.columns]
    df = df[keep].copy()
    df["Club"] = df["Club"].fillna("")
    df["Name"] = df["Name"].fillna("")
    df["Nationality"] = df["Nationality"].fillna("")
    df["Position"] = df["Position"].fillna("")
    df["name_norm"] = df["Name"].map(lambda x: strip_accents(str(x)).lower())
    df["club_norm"] = df["Club"].map(lambda x: canonical_norm(x) if x else "")
    df["club_clean"] = df["Club"].map(lambda x: canonical_team_name(x) if x else "")
    df["nat_norm"] = df["Nationality"].map(lambda x: strip_accents(str(x)).lower())
    df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
    return df.reset_index(drop=True)


_CACHE: dict = {}


def load_all(data_dir: Optional[Path] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return ``(matches, players)``, cached per data directory."""
    key = str(Path(data_dir) if data_dir else default_data_dir())
    if key not in _CACHE:
        _CACHE[key] = (load_matches(data_dir), load_players(data_dir))
    return _CACHE[key]
