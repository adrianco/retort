"""
================================================================================
Module: data_loader.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
-------
Loads the six provided Kaggle CSV files (in ``data/kaggle/``) into two clean,
unified pandas DataFrames that the rest of the system queries:

  * ``matches``  - every match across all competitions in ONE schema
  * ``players``  - the FIFA player database, lightly cleaned

Each source file has its own column names, date format and team-naming
convention.  This module is the single place where those differences are
reconciled:

  File                              -> competition
  --------------------------------------------------------------
  Brasileirao_Matches.csv           -> "Brasileirão Série A"   (2012-2022)
  novo_campeonato_brasileiro.csv    -> "Brasileirão Série A"   (2003-2019)
  Brazilian_Cup_Matches.csv         -> "Copa do Brasil"
  Libertadores_Matches.csv          -> "Copa Libertadores"
  BR-Football-Dataset.csv           -> Série A/B/C + Copa do Brasil (+ stats)
  fifa_data.csv                     -> players

Unified match schema (columns of the ``matches`` DataFrame)::

    competition  season  stage   date        source
    home_team    away_team                    (raw names, as in the file)
    home_disp    away_disp                    (clean display names)
    home_norm    away_norm                    (canonical match keys)
    home_goal    away_goal                    (nullable Int)
    home_shots   away_shots                   (nullable, BR dataset only)
    home_corner  away_corner                  (nullable, BR dataset only)

Note on overlap: the Brasileirão Série A is described by THREE sources with
overlapping years.  We keep all rows (each tagged with ``source``) and rely on
``knowledge_graph.dedupe_matches`` to collapse duplicates when computing
standings/records, so no information is lost at load time.
================================================================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

from normalization import clean_display_name, normalize_team_name, strip_accents

# Directory containing the Kaggle CSVs, relative to this file.
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

# Canonical competition labels.
SERIE_A = "Brasileirão Série A"
COPA_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"
SERIE_B = "Série B"
SERIE_C = "Série C"

# Map the BR-Football-Dataset "tournament" field onto canonical labels.
_BR_TOURNAMENT_MAP = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_BRASIL,
}

# Unified column order for the matches DataFrame.
MATCH_COLUMNS = [
    "competition", "season", "stage", "date", "source",
    "home_team", "away_team", "home_disp", "away_disp", "home_norm", "away_norm",
    "home_goal", "away_goal", "home_shots", "away_shots", "home_corner", "away_corner",
]


@dataclass
class Dataset:
    """Container for the two unified DataFrames."""

    matches: pd.DataFrame
    players: pd.DataFrame


def _add_team_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add display + normalized columns derived from home_team/away_team."""
    df["home_disp"] = df["home_team"].map(clean_display_name)
    df["away_disp"] = df["away_team"].map(clean_display_name)
    df["home_norm"] = df["home_team"].map(normalize_team_name)
    df["away_norm"] = df["away_team"].map(normalize_team_name)
    return df


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure every unified column exists and is in canonical order/typing."""
    for col in MATCH_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[MATCH_COLUMNS].copy()
    # Nullable integer types so unplayed matches keep <NA> instead of NaN floats.
    for col in ["season", "home_goal", "away_goal",
                "home_shots", "away_shots", "home_corner", "away_corner"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


def _load_brasileirao(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={"round": "stage"})
    df["competition"] = SERIE_A
    df["source"] = "Brasileirao_Matches.csv"
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["stage"] = df["stage"].map(lambda r: f"Round {int(r)}" if pd.notna(r) else pd.NA)
    df = _add_team_columns(df)
    return _finalize(df)


def _load_novo(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={
        "Equipe_mandante": "home_team",
        "Equipe_visitante": "away_team",
        "Gols_mandante": "home_goal",
        "Gols_visitante": "away_goal",
        "Ano": "season",
    })
    df["competition"] = SERIE_A
    df["source"] = "novo_campeonato_brasileiro.csv"
    df["date"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    df["stage"] = df["Rodada"].map(lambda r: f"Round {int(r)}" if pd.notna(r) else pd.NA)
    df = _add_team_columns(df)
    return _finalize(df)


def _load_cup(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={"round": "stage"})
    df["competition"] = COPA_BRASIL
    df["source"] = "Brazilian_Cup_Matches.csv"
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["stage"] = df["stage"].astype("string")
    df = _add_team_columns(df)
    return _finalize(df)


def _load_libertadores(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["competition"] = LIBERTADORES
    df["source"] = "Libertadores_Matches.csv"
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["stage"] = df["stage"].astype("string")
    df = _add_team_columns(df)
    return _finalize(df)


def _load_br_football(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={
        "home": "home_team",
        "away": "away_team",
    })
    df["competition"] = df["tournament"].map(_BR_TOURNAMENT_MAP).fillna(df["tournament"])
    df["source"] = "BR-Football-Dataset.csv"
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["season"] = df["date"].dt.year
    df["stage"] = pd.NA
    df = _add_team_columns(df)
    return _finalize(df)


def load_matches(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Load and concatenate every match source into the unified schema."""
    frames = [
        _load_brasileirao(os.path.join(data_dir, "Brasileirao_Matches.csv")),
        _load_novo(os.path.join(data_dir, "novo_campeonato_brasileiro.csv")),
        _load_cup(os.path.join(data_dir, "Brazilian_Cup_Matches.csv")),
        _load_libertadores(os.path.join(data_dir, "Libertadores_Matches.csv")),
        _load_br_football(os.path.join(data_dir, "BR-Football-Dataset.csv")),
    ]
    matches = pd.concat(frames, ignore_index=True)
    return matches


def load_players(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Load the FIFA player database, keeping the columns we query on."""
    df = pd.read_csv(os.path.join(data_dir, "fifa_data.csv"))
    # The first column is an unnamed row index (with a BOM); drop it if present.
    first = df.columns[0]
    if first.strip("﻿") == "" or first.startswith("Unnamed"):
        df = df.drop(columns=[first])
    keep = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club",
        "Position", "Jersey Number", "Height", "Weight", "Value", "Wage",
        "Preferred Foot",
    ]
    keep = [c for c in keep if c in df.columns]
    df = df[keep].copy()
    df["Name"] = df["Name"].astype("string")
    df["club_norm"] = df["Club"].fillna("").map(normalize_team_name)
    df["name_lower"] = df["Name"].fillna("").map(lambda s: strip_accents(s).lower())
    df["nationality_lower"] = df["Nationality"].fillna("").str.lower()
    return df


def load_dataset(data_dir: str = DATA_DIR) -> Dataset:
    """Load both matches and players into a :class:`Dataset`."""
    return Dataset(matches=load_matches(data_dir), players=load_players(data_dir))
