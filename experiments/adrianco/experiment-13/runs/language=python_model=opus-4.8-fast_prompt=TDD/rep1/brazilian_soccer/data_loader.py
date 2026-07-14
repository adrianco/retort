"""Load the bundled Kaggle CSV datasets into normalized records.

Each match file has its own column layout; the loaders below map them onto a
single :class:`Match` structure with consistent team names, dates and goal
counts.  Player rows from the FIFA dataset map onto :class:`Player`.
"""
from __future__ import annotations

import csv
import datetime
import os
from dataclasses import dataclass
from typing import List, Optional

from . import normalize

# Filenames for each dataset (relative to the data directory).
BRASILEIRAO_FILE = "Brasileirao_Matches.csv"
CUP_FILE = "Brazilian_Cup_Matches.csv"
LIBERTADORES_FILE = "Libertadores_Matches.csv"
EXTENDED_FILE = "BR-Football-Dataset.csv"
HISTORICAL_FILE = "novo_campeonato_brasileiro.csv"
FIFA_FILE = "fifa_data.csv"

BRASILEIRAO = "Brasileirão"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"


@dataclass
class Match:
    """A single match, normalized across all source files."""

    competition: str
    home_team: str
    away_team: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    season: Optional[int]
    date: Optional[datetime.date] = None
    round: Optional[str] = None
    stage: Optional[str] = None
    source: str = ""

    def __post_init__(self):
        self.home_key = normalize.team_key(self.home_team)
        self.away_key = normalize.team_key(self.away_team)

    @property
    def played(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def winner_key(self) -> Optional[str]:
        """team_key of the winner, or ``None`` for a draw/unplayed match."""
        if not self.played:
            return None
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None


@dataclass
class Player:
    """A FIFA-database player."""

    id: Optional[int]
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    jersey_number: Optional[int]
    height: str
    weight: str

    def __post_init__(self):
        self.club_key = normalize.team_key(self.club) if self.club else ""
        self.name_key = normalize.strip_accents(self.name).lower()


def _read_rows(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _load_brasileirao(path: str) -> List[Match]:
    matches = []
    for row in _read_rows(path):
        matches.append(
            Match(
                competition=BRASILEIRAO,
                home_team=normalize.normalize_team_name(row["home_team"]),
                away_team=normalize.normalize_team_name(row["away_team"]),
                home_goal=normalize.parse_goal(row["home_goal"]),
                away_goal=normalize.parse_goal(row["away_goal"]),
                season=_to_int(row.get("season")),
                date=normalize.parse_date(row.get("datetime")),
                round=str(row["round"]).strip() if row.get("round") else None,
                source=BRASILEIRAO_FILE,
            )
        )
    return matches


def _load_cup(path: str) -> List[Match]:
    matches = []
    for row in _read_rows(path):
        matches.append(
            Match(
                competition=COPA_DO_BRASIL,
                home_team=normalize.normalize_team_name(row["home_team"]),
                away_team=normalize.normalize_team_name(row["away_team"]),
                home_goal=normalize.parse_goal(row["home_goal"]),
                away_goal=normalize.parse_goal(row["away_goal"]),
                season=_to_int(row.get("season")),
                date=normalize.parse_date(row.get("datetime")),
                round=str(row["round"]).strip() if row.get("round") else None,
                source=CUP_FILE,
            )
        )
    return matches


def _load_libertadores(path: str) -> List[Match]:
    matches = []
    for row in _read_rows(path):
        matches.append(
            Match(
                competition=LIBERTADORES,
                home_team=normalize.normalize_team_name(row["home_team"]),
                away_team=normalize.normalize_team_name(row["away_team"]),
                home_goal=normalize.parse_goal(row["home_goal"]),
                away_goal=normalize.parse_goal(row["away_goal"]),
                season=_to_int(row.get("season")),
                date=normalize.parse_date(row.get("datetime")),
                stage=str(row["stage"]).strip() if row.get("stage") else None,
                source=LIBERTADORES_FILE,
            )
        )
    return matches


def _load_extended(path: str) -> List[Match]:
    matches = []
    for row in _read_rows(path):
        matches.append(
            Match(
                competition=str(row.get("tournament") or "").strip() or "Unknown",
                home_team=normalize.normalize_team_name(row["home"]),
                away_team=normalize.normalize_team_name(row["away"]),
                home_goal=normalize.parse_goal(row["home_goal"]),
                away_goal=normalize.parse_goal(row["away_goal"]),
                season=normalize.parse_date(row.get("date")).year
                if normalize.parse_date(row.get("date"))
                else None,
                date=normalize.parse_date(row.get("date")),
                source=EXTENDED_FILE,
            )
        )
    return matches


def _load_historical(path: str) -> List[Match]:
    matches = []
    for row in _read_rows(path):
        matches.append(
            Match(
                competition=BRASILEIRAO,
                home_team=normalize.normalize_team_name(row["Equipe_mandante"]),
                away_team=normalize.normalize_team_name(row["Equipe_visitante"]),
                home_goal=normalize.parse_goal(row["Gols_mandante"]),
                away_goal=normalize.parse_goal(row["Gols_visitante"]),
                season=_to_int(row.get("Ano")),
                date=normalize.parse_date(row.get("Data")),
                round=str(row["Rodada"]).strip() if row.get("Rodada") else None,
                source=HISTORICAL_FILE,
            )
        )
    return matches


_MATCH_LOADERS = [
    (BRASILEIRAO_FILE, _load_brasileirao),
    (CUP_FILE, _load_cup),
    (LIBERTADORES_FILE, _load_libertadores),
    (EXTENDED_FILE, _load_extended),
    (HISTORICAL_FILE, _load_historical),
]


def load_matches(data_dir) -> List[Match]:
    """Load and normalize every match file present in ``data_dir``."""
    data_dir = str(data_dir)
    matches: List[Match] = []
    for filename, loader in _MATCH_LOADERS:
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            matches.extend(loader(path))
    return matches


def load_players(data_dir) -> List[Player]:
    """Load FIFA player records from ``data_dir``."""
    path = os.path.join(str(data_dir), FIFA_FILE)
    if not os.path.exists(path):
        return []
    players = []
    for row in _read_rows(path):
        players.append(
            Player(
                id=_to_int(row.get("ID")),
                name=str(row.get("Name") or "").strip(),
                age=_to_int(row.get("Age")),
                nationality=str(row.get("Nationality") or "").strip(),
                overall=_to_int(row.get("Overall")),
                potential=_to_int(row.get("Potential")),
                club=str(row.get("Club") or "").strip(),
                position=str(row.get("Position") or "").strip(),
                jersey_number=_to_int(row.get("Jersey Number")),
                height=str(row.get("Height") or "").strip(),
                weight=str(row.get("Weight") or "").strip(),
            )
        )
    return players
