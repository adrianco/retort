"""
================================================================================
Context
================================================================================
Module:   data_loader.py
Project:  Brazilian Soccer MCP Server
Purpose:  Read the six raw Kaggle CSV files into uniform in-memory record
          objects (Match, Player).  Each source file has a different schema,
          column order, date format and team-naming convention; this module is
          the single place that knows about those quirks and produces clean,
          typed records for the rest of the system.

Outputs:
    load_matches(data_dir) -> list[Match]
    load_players(data_dir) -> list[Player]
    Match  : a normalized fixture (competition, season, date, teams, score, ...)
    Player : a normalized FIFA player row (name, nationality, club, rating, ...)

Design notes:
    * Standard library only (csv, datetime, dataclasses) so the data layer and
      its tests never depend on pandas/numpy being installed.
    * Team names are normalized lazily via team_names.normalize_team; both the
      raw and canonical forms are retained for display and matching.
    * Goals/ratings that are blank or malformed become None rather than raising.
    * BR-Football-Dataset overlaps the dedicated competition files, so its rows
      are tagged with source='br-football' allowing callers to deduplicate.
================================================================================
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from team_names import display_team, normalize_team

# ---------------------------------------------------------------------------
# Canonical competition labels
# ---------------------------------------------------------------------------
SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"


@dataclass
class Match:
    """A single normalized fixture."""

    competition: str
    season: int
    home_team: str            # canonical display name
    away_team: str            # canonical display name
    home_goal: Optional[int]
    away_goal: Optional[int]
    date: Optional[date] = None
    round: Optional[str] = None
    stage: Optional[str] = None
    arena: Optional[str] = None
    source: str = ""
    home_key: str = ""
    away_key: str = ""
    # Optional extended statistics (BR-Football dataset only)
    stats: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.home_key:
            self.home_key = normalize_team(self.home_team)
        if not self.away_key:
            self.away_key = normalize_team(self.away_team)

    @property
    def winner(self) -> Optional[str]:
        """Canonical display name of the winner, or None for a draw / unknown."""
        if self.home_goal is None or self.away_goal is None:
            return None
        if self.home_goal > self.away_goal:
            return self.home_team
        if self.away_goal > self.home_goal:
            return self.away_team
        return None

    @property
    def is_draw(self) -> bool:
        return (
            self.home_goal is not None
            and self.away_goal is not None
            and self.home_goal == self.away_goal
        )

    @property
    def total_goals(self) -> Optional[int]:
        if self.home_goal is None or self.away_goal is None:
            return None
        return self.home_goal + self.away_goal

    def involves(self, team_key: str) -> bool:
        return team_key in (self.home_key, self.away_key)

    def score_line(self) -> str:
        """e.g. 'Flamengo 2-1 Fluminense'."""
        hg = "?" if self.home_goal is None else self.home_goal
        ag = "?" if self.away_goal is None else self.away_goal
        return f"{self.home_team} {hg}-{ag} {self.away_team}"


@dataclass
class Player:
    """A normalized FIFA player record."""

    player_id: Optional[int]
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    jersey_number: Optional[int]
    height: str = ""
    weight: str = ""
    club_key: str = ""

    def __post_init__(self) -> None:
        if not self.club_key and self.club:
            self.club_key = normalize_team(self.club)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",
)


def _parse_date(value) -> Optional[date]:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Last resort: take the leading date-looking token.
    token = s.split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(token, fmt).date()
        except ValueError:
            continue
    return None


def _open(path: str):
    # utf-8-sig transparently strips the BOM present in fifa_data.csv.
    return open(path, "r", encoding="utf-8-sig", newline="")


# ---------------------------------------------------------------------------
# Per-file loaders
# ---------------------------------------------------------------------------
def _load_brasileirao(path: str) -> list[Match]:
    matches: list[Match] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            matches.append(
                Match(
                    competition=SERIE_A,
                    season=_to_int(row.get("season")) or 0,
                    home_team=display_team(row.get("home_team", "")),
                    away_team=display_team(row.get("away_team", "")),
                    home_goal=_to_int(row.get("home_goal")),
                    away_goal=_to_int(row.get("away_goal")),
                    date=_parse_date(row.get("datetime")),
                    round=str(row.get("round") or "").strip() or None,
                    source="brasileirao",
                )
            )
    return matches


def _load_cup(path: str) -> list[Match]:
    matches: list[Match] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            matches.append(
                Match(
                    competition=COPA_DO_BRASIL,
                    season=_to_int(row.get("season")) or 0,
                    home_team=display_team(row.get("home_team", "")),
                    away_team=display_team(row.get("away_team", "")),
                    home_goal=_to_int(row.get("home_goal")),
                    away_goal=_to_int(row.get("away_goal")),
                    date=_parse_date(row.get("datetime")),
                    round=str(row.get("round") or "").strip() or None,
                    source="copa_do_brasil",
                )
            )
    return matches


def _load_libertadores(path: str) -> list[Match]:
    matches: list[Match] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            matches.append(
                Match(
                    competition=LIBERTADORES,
                    season=_to_int(row.get("season")) or 0,
                    home_team=display_team(row.get("home_team", "")),
                    away_team=display_team(row.get("away_team", "")),
                    home_goal=_to_int(row.get("home_goal")),
                    away_goal=_to_int(row.get("away_goal")),
                    date=_parse_date(row.get("datetime")),
                    stage=str(row.get("stage") or "").strip() or None,
                    source="libertadores",
                )
            )
    return matches


_BR_TOURNAMENT_MAP = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}


def _load_br_football(path: str) -> list[Match]:
    matches: list[Match] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            d = _parse_date(row.get("date"))
            season = d.year if d else 0
            stats = {
                "home_corner": _to_float(row.get("home_corner")),
                "away_corner": _to_float(row.get("away_corner")),
                "home_shots": _to_float(row.get("home_shots")),
                "away_shots": _to_float(row.get("away_shots")),
                "home_attack": _to_float(row.get("home_attack")),
                "away_attack": _to_float(row.get("away_attack")),
                "total_corners": _to_float(row.get("total_corners")),
            }
            matches.append(
                Match(
                    competition=_BR_TOURNAMENT_MAP.get(
                        row.get("tournament", ""), row.get("tournament", "")
                    ),
                    season=season,
                    home_team=display_team(row.get("home", "")),
                    away_team=display_team(row.get("away", "")),
                    home_goal=_to_int(row.get("home_goal")),
                    away_goal=_to_int(row.get("away_goal")),
                    date=d,
                    source="br-football",
                    stats={k: v for k, v in stats.items() if v is not None},
                )
            )
    return matches


def _load_novo(path: str) -> list[Match]:
    matches: list[Match] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            matches.append(
                Match(
                    competition=SERIE_A,
                    season=_to_int(row.get("Ano")) or 0,
                    home_team=display_team(row.get("Equipe_mandante", "")),
                    away_team=display_team(row.get("Equipe_visitante", "")),
                    home_goal=_to_int(row.get("Gols_mandante")),
                    away_goal=_to_int(row.get("Gols_visitante")),
                    date=_parse_date(row.get("Data")),
                    round=str(row.get("Rodada") or "").strip() or None,
                    arena=str(row.get("Arena") or "").strip() or None,
                    source="novo",
                )
            )
    return matches


def _load_players(path: str) -> list[Player]:
    players: list[Player] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
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
                    jersey_number=_to_int(row.get("Jersey Number")),
                    height=(row.get("Height") or "").strip(),
                    weight=(row.get("Weight") or "").strip(),
                )
            )
    return players


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
_MATCH_FILES = (
    ("Brasileirao_Matches.csv", _load_brasileirao),
    ("Brazilian_Cup_Matches.csv", _load_cup),
    ("Libertadores_Matches.csv", _load_libertadores),
    ("BR-Football-Dataset.csv", _load_br_football),
    ("novo_campeonato_brasileiro.csv", _load_novo),
)


def default_data_dir() -> str:
    """Directory holding the Kaggle CSV files, relative to this module."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")


def load_matches(data_dir: Optional[str] = None) -> list[Match]:
    """Load and normalize every match from all five match CSV files."""
    data_dir = data_dir or default_data_dir()
    matches: list[Match] = []
    for filename, loader in _MATCH_FILES:
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            matches.extend(loader(path))
    return matches


def load_players(data_dir: Optional[str] = None) -> list[Player]:
    """Load and normalize every FIFA player row."""
    data_dir = data_dir or default_data_dir()
    path = os.path.join(data_dir, "fifa_data.csv")
    if not os.path.exists(path):
        return []
    return _load_players(path)
