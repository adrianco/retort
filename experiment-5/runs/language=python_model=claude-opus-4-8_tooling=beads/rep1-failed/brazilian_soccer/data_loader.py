"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Module    : brazilian_soccer.data_loader
Purpose   : Read the six Kaggle CSV files in data/kaggle/ and turn each row into
            a Match or Player dataclass.

Each dataset has its own column layout, so there is one loader function per file.
All loaders are tolerant of missing/blank cells and use UTF-8 (with BOM handling)
so accented Portuguese names survive. The public entry point load_all() returns
(matches, players) and is used by KnowledgeGraph.

Datasets (data/kaggle/):
  Brasileirao_Matches.csv        -> Brasileirao
  Brazilian_Cup_Matches.csv      -> Copa do Brasil
  Libertadores_Matches.csv       -> Libertadores
  BR-Football-Dataset.csv        -> tournament column (mixed competitions)
  novo_campeonato_brasileiro.csv -> Brasileirao (historical 2003-2019)
  fifa_data.csv                  -> Player records
================================================================================
"""

from __future__ import annotations

import csv
import os
from typing import List, Tuple

from .models import Match, Player
from .normalize import parse_date, to_int

# Allow CSV fields larger than the default limit (FIFA rows are wide).
csv.field_size_limit(10_000_000)

# Default data directory: <repo>/data/kaggle
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "data", "kaggle"))


def _open(path: str):
    """Open a CSV with BOM-tolerant UTF-8 decoding."""
    return open(path, "r", encoding="utf-8-sig", newline="")


# --------------------------------------------------------------------------- #
# Match loaders
# --------------------------------------------------------------------------- #
def load_brasileirao(path: str) -> List[Match]:
    matches: List[Match] = []
    src = os.path.basename(path)
    with _open(path) as f:
        for row in csv.DictReader(f):
            matches.append(
                Match(
                    competition="Brasileirao",
                    home_team=row.get("home_team", ""),
                    away_team=row.get("away_team", ""),
                    home_goal=to_int(row.get("home_goal")),
                    away_goal=to_int(row.get("away_goal")),
                    season=to_int(row.get("season")),
                    match_date=parse_date(row.get("datetime")),
                    round=str(row.get("round") or "").strip() or None,
                    source=src,
                )
            )
    return matches


def load_copa_do_brasil(path: str) -> List[Match]:
    matches: List[Match] = []
    src = os.path.basename(path)
    with _open(path) as f:
        for row in csv.DictReader(f):
            matches.append(
                Match(
                    competition="Copa do Brasil",
                    home_team=row.get("home_team", ""),
                    away_team=row.get("away_team", ""),
                    home_goal=to_int(row.get("home_goal")),
                    away_goal=to_int(row.get("away_goal")),
                    season=to_int(row.get("season")),
                    match_date=parse_date(row.get("datetime")),
                    round=str(row.get("round") or "").strip() or None,
                    source=src,
                )
            )
    return matches


def load_libertadores(path: str) -> List[Match]:
    matches: List[Match] = []
    src = os.path.basename(path)
    with _open(path) as f:
        for row in csv.DictReader(f):
            matches.append(
                Match(
                    competition="Libertadores",
                    home_team=row.get("home_team", ""),
                    away_team=row.get("away_team", ""),
                    home_goal=to_int(row.get("home_goal")),
                    away_goal=to_int(row.get("away_goal")),
                    season=to_int(row.get("season")),
                    match_date=parse_date(row.get("datetime")),
                    stage=str(row.get("stage") or "").strip() or None,
                    source=src,
                )
            )
    return matches


# BR-Football-Dataset uses its own tournament labels; map to the canonical names
# used by the dedicated files so the same fixture lines up across sources.
_TOURNAMENT_MAP = {
    "serie a": "Brasileirao",
    "brasileirao": "Brasileirao",
    "campeonato brasileiro serie a": "Brasileirao",
    "copa do brasil": "Copa do Brasil",
    "libertadores": "Libertadores",
    "copa libertadores": "Libertadores",
}


def _canon_tournament(name: str) -> str:
    key = name.strip().lower()
    return _TOURNAMENT_MAP.get(key, name.strip() or "Unknown")


def load_br_football(path: str) -> List[Match]:
    """BR-Football-Dataset.csv: extended stats; competition in `tournament`."""
    matches: List[Match] = []
    src = os.path.basename(path)
    with _open(path) as f:
        for row in csv.DictReader(f):
            d = parse_date(row.get("date"))
            matches.append(
                Match(
                    competition=_canon_tournament(str(row.get("tournament") or "Unknown")),
                    home_team=row.get("home", ""),
                    away_team=row.get("away", ""),
                    home_goal=to_int(row.get("home_goal")),
                    away_goal=to_int(row.get("away_goal")),
                    season=d.year if d else None,
                    match_date=d,
                    source=src,
                )
            )
    return matches


def load_novo_brasileirao(path: str) -> List[Match]:
    """novo_campeonato_brasileiro.csv: historical Brasileirao 2003-2019."""
    matches: List[Match] = []
    src = os.path.basename(path)
    with _open(path) as f:
        for row in csv.DictReader(f):
            matches.append(
                Match(
                    competition="Brasileirao",
                    home_team=row.get("Equipe_mandante", ""),
                    away_team=row.get("Equipe_visitante", ""),
                    home_goal=to_int(row.get("Gols_mandante")),
                    away_goal=to_int(row.get("Gols_visitante")),
                    season=to_int(row.get("Ano")),
                    match_date=parse_date(row.get("Data")),
                    round=str(row.get("Rodada") or "").strip() or None,
                    stadium=str(row.get("Arena") or "").strip() or None,
                    source=src,
                )
            )
    return matches


# --------------------------------------------------------------------------- #
# Player loader
# --------------------------------------------------------------------------- #
def load_players(path: str) -> List[Player]:
    players: List[Player] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            players.append(
                Player(
                    player_id=to_int(row.get("ID")),
                    name=name,
                    age=to_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip(),
                    overall=to_int(row.get("Overall")),
                    potential=to_int(row.get("Potential")),
                    club=(row.get("Club") or "").strip(),
                    position=(row.get("Position") or "").strip(),
                    jersey_number=to_int(row.get("Jersey Number")),
                    height=(row.get("Height") or "").strip(),
                    weight=(row.get("Weight") or "").strip(),
                    preferred_foot=(row.get("Preferred Foot") or "").strip(),
                )
            )
    return players


# --------------------------------------------------------------------------- #
# Aggregate loader
# --------------------------------------------------------------------------- #
_MATCH_FILES = [
    ("Brasileirao_Matches.csv", load_brasileirao),
    ("Brazilian_Cup_Matches.csv", load_copa_do_brasil),
    ("Libertadores_Matches.csv", load_libertadores),
    ("BR-Football-Dataset.csv", load_br_football),
    ("novo_campeonato_brasileiro.csv", load_novo_brasileirao),
]

_PLAYER_FILE = "fifa_data.csv"


def load_all(data_dir: str | None = None) -> Tuple[List[Match], List[Player]]:
    """Load every available dataset. Missing files are skipped (with no error)."""
    data_dir = data_dir or DEFAULT_DATA_DIR
    matches: List[Match] = []
    for filename, loader in _MATCH_FILES:
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            matches.extend(loader(path))

    players: List[Player] = []
    player_path = os.path.join(data_dir, _PLAYER_FILE)
    if os.path.exists(player_path):
        players = load_players(player_path)

    return matches, players
