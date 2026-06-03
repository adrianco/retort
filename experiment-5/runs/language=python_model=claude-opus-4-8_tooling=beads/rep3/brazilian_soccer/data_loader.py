"""
==============================================================================
Module: brazilian_soccer.data_loader
==============================================================================
CONTEXT
-------
Reads the six provided Kaggle CSV files from ``data/kaggle/`` and converts each
row into a domain object (``Match`` / ``Player``). All parsing quirks called
out in the specification are handled here:

  * Multiple date formats .... "2012-05-19 18:30:00", "2023-09-24",
                               "29/03/2003" (DD/MM/YYYY).
  * UTF-8 / BOM .............. files are opened as ``utf-8-sig``.
  * Team name variations ..... left intact on the object; normalization is done
                               lazily by the Match/Player models.

DE-DUPLICATION STRATEGY (important for correct standings)
---------------------------------------------------------
The Brasileirão (Serie A) appears in THREE files with overlapping seasons:

    * novo_campeonato_brasileiro.csv ... 2003-2019
    * Brasileirao_Matches.csv .......... 2012-2022
    * BR-Football-Dataset.csv (Serie A)  2014-2023 (extended stats)

To avoid triple-counting matches when computing standings/aggregates, each
match carries a ``primary`` flag. Only ONE source is marked primary per
(competition, season):

    * Brasileirão 2003-2011 -> novo_campeonato_brasileiro.csv
    * Brasileirão 2012-2022 -> Brasileirao_Matches.csv
    * Copa do Brasil        -> Brazilian_Cup_Matches.csv
    * Libertadores          -> Libertadores_Matches.csv
    * Serie B / Serie C     -> BR-Football-Dataset.csv (unique to this file)

Non-primary rows remain fully queryable (and supply extended statistics) but
are excluded from standings/aggregate counts.
==============================================================================
"""

from __future__ import annotations

import csv
import os
from datetime import date, datetime
from typing import Iterable, List, Optional

from .models import Match, Player

# Default location of the data, relative to the repository root.
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "kaggle",
)

# Canonical competition labels.
BRASILEIRAO = "Brasileirão"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Libertadores"


# --------------------------------------------------------------------------- #
# Small parsing helpers
# --------------------------------------------------------------------------- #
def _to_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.upper() in ("NA", "NAN", "NONE"):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.upper() in ("NA", "NAN", "NONE"):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_date(value: Optional[str]) -> Optional[date]:
    """Parse the several date formats present across the datasets."""
    if not value:
        return None
    value = str(value).strip()
    if value == "" or value.upper() in ("NA", "NAN"):
        return None
    # Take just the date portion if a time is attached.
    head = value.split(" ")[0]
    fmts = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y")
    for fmt in fmts:
        try:
            return datetime.strptime(head, fmt).date()
        except ValueError:
            continue
    # Last resort: full datetime string.
    for fmt in ("%Y-%m-%d %H:%M:%S",):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _open(path: str):
    return open(path, newline="", encoding="utf-8-sig")


# --------------------------------------------------------------------------- #
# Per-file loaders
# --------------------------------------------------------------------------- #
def load_brasileirao(path: str) -> List[Match]:
    matches: List[Match] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            season = _to_int(row.get("season"))
            matches.append(
                Match(
                    competition=BRASILEIRAO,
                    season=season,
                    home_raw=row.get("home_team", ""),
                    away_raw=row.get("away_team", ""),
                    home_goal=_to_int(row.get("home_goal")),
                    away_goal=_to_int(row.get("away_goal")),
                    source=os.path.basename(path),
                    date=parse_date(row.get("datetime")),
                    round=(row.get("round") or "").strip() or None,
                    primary=True,  # canonical for 2012-2022
                )
            )
    return matches


def load_historical_brasileirao(path: str) -> List[Match]:
    matches: List[Match] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            year = _to_int(row.get("Ano"))
            # Primary only for seasons not covered by Brasileirao_Matches.csv.
            primary = year is not None and year <= 2011
            matches.append(
                Match(
                    competition=BRASILEIRAO,
                    season=year,
                    home_raw=row.get("Equipe_mandante", ""),
                    away_raw=row.get("Equipe_visitante", ""),
                    home_goal=_to_int(row.get("Gols_mandante")),
                    away_goal=_to_int(row.get("Gols_visitante")),
                    source=os.path.basename(path),
                    date=parse_date(row.get("Data")),
                    round=(row.get("Rodada") or "").strip() or None,
                    arena=(row.get("Arena") or "").strip() or None,
                    primary=primary,
                )
            )
    return matches


def load_cup(path: str) -> List[Match]:
    matches: List[Match] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            matches.append(
                Match(
                    competition=COPA_DO_BRASIL,
                    season=_to_int(row.get("season")),
                    home_raw=row.get("home_team", ""),
                    away_raw=row.get("away_team", ""),
                    home_goal=_to_int(row.get("home_goal")),
                    away_goal=_to_int(row.get("away_goal")),
                    source=os.path.basename(path),
                    date=parse_date(row.get("datetime")),
                    round=(row.get("round") or "").strip() or None,
                    primary=True,
                )
            )
    return matches


def load_libertadores(path: str) -> List[Match]:
    matches: List[Match] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            matches.append(
                Match(
                    competition=LIBERTADORES,
                    season=_to_int(row.get("season")),
                    home_raw=row.get("home_team", ""),
                    away_raw=row.get("away_team", ""),
                    home_goal=_to_int(row.get("home_goal")),
                    away_goal=_to_int(row.get("away_goal")),
                    source=os.path.basename(path),
                    date=parse_date(row.get("datetime")),
                    stage=(row.get("stage") or "").strip() or None,
                    primary=True,
                )
            )
    return matches


def load_br_football(path: str) -> List[Match]:
    """Extended-statistics dataset (corners, shots, attacks, half-time)."""
    matches: List[Match] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            tournament = (row.get("tournament") or "").strip()
            # Serie A / Copa do Brasil already covered by dedicated files.
            primary = tournament in ("Serie B", "Serie C")
            d = parse_date(row.get("date"))
            stats = {
                "home_corner": _to_float(row.get("home_corner")),
                "away_corner": _to_float(row.get("away_corner")),
                "home_attack": _to_float(row.get("home_attack")),
                "away_attack": _to_float(row.get("away_attack")),
                "home_shots": _to_float(row.get("home_shots")),
                "away_shots": _to_float(row.get("away_shots")),
                "ht_result": row.get("ht_result"),
                "at_result": row.get("at_result"),
                "total_corners": _to_float(row.get("total_corners")),
            }
            matches.append(
                Match(
                    competition=tournament or "Unknown",
                    season=d.year if d else None,
                    home_raw=row.get("home", ""),
                    away_raw=row.get("away", ""),
                    home_goal=_to_int(_to_float(row.get("home_goal"))),
                    away_goal=_to_int(_to_float(row.get("away_goal"))),
                    source=os.path.basename(path),
                    date=d,
                    primary=primary,
                    stats=stats,
                )
            )
    return matches


def load_players(path: str) -> List[Player]:
    players: List[Player] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            players.append(
                Player(
                    player_id=_to_int(row.get("ID")),
                    name=(row.get("Name") or "").strip(),
                    age=_to_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip(),
                    overall=_to_int(row.get("Overall")),
                    potential=_to_int(row.get("Potential")),
                    club=(row.get("Club") or "").strip(),
                    position=(row.get("Position") or "").strip(),
                    jersey_number=(row.get("Jersey Number") or "").strip() or None,
                    height=(row.get("Height") or "").strip() or None,
                    weight=(row.get("Weight") or "").strip() or None,
                    preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                    value=(row.get("Value") or "").strip() or None,
                    wage=(row.get("Wage") or "").strip() or None,
                )
            )
    return players


# --------------------------------------------------------------------------- #
# Aggregate loader
# --------------------------------------------------------------------------- #
# Maps file name -> loader function.
MATCH_FILES = {
    "Brasileirao_Matches.csv": load_brasileirao,
    "novo_campeonato_brasileiro.csv": load_historical_brasileirao,
    "Brazilian_Cup_Matches.csv": load_cup,
    "Libertadores_Matches.csv": load_libertadores,
    "BR-Football-Dataset.csv": load_br_football,
}
PLAYER_FILE = "fifa_data.csv"


def load_all_matches(data_dir: str = DEFAULT_DATA_DIR) -> List[Match]:
    matches: List[Match] = []
    for fname, loader in MATCH_FILES.items():
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            matches.extend(loader(path))
    return matches


def load_all_players(data_dir: str = DEFAULT_DATA_DIR) -> List[Player]:
    path = os.path.join(data_dir, PLAYER_FILE)
    return load_players(path) if os.path.exists(path) else []
