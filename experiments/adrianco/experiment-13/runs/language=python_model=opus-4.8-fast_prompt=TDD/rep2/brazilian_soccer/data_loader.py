"""
Context
=======
Loads the six provided Kaggle CSVs into uniform in-memory records so the
rest of the knowledge base can query them without caring about each file's
idiosyncratic columns, date formats or naming conventions.

Two record types are produced:

* ``Match``  -- one football match (any competition / source file).
* ``Player`` -- one FIFA player row.

All team names are normalized eagerly (``home_key`` / ``away_key``) using
``brazilian_soccer.normalize`` so cross-file matching is cheap. Parsing of
goals, integers and the several date formats is tolerant: anything
unparseable becomes ``None`` rather than raising, because the raw data
contains blanks and malformed cells.
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from .normalize import normalize_team

# Repository ``data/kaggle`` directory, resolved relative to this file.
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M:%S",
)


def parse_int(value) -> Optional[int]:
    """Best-effort int parse tolerant of floats ("2.0"), blanks and junk."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def parse_date(value) -> Optional[dt.date]:
    """Parse the several date formats found in the datasets; None if blank."""
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    # Some rows carry only a date, others date+time; try each known format.
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Fall back to ISO parsing for anything else.
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


@dataclass
class Match:
    """A single match, normalized across all source files."""

    competition: str
    season: Optional[int]
    date: Optional[dt.date]
    round: Optional[str]
    stage: Optional[str]
    home_team: str
    away_team: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    source: str = ""
    home_key: str = field(default="", init=False)
    away_key: str = field(default="", init=False)

    def __post_init__(self):
        self.home_key = normalize_team(self.home_team)
        self.away_key = normalize_team(self.away_team)

    @property
    def winner(self) -> Optional[str]:
        """Return 'home', 'away', 'draw' or None when the score is unknown."""
        if self.home_goal is None or self.away_goal is None:
            return None
        if self.home_goal > self.away_goal:
            return "home"
        if self.home_goal < self.away_goal:
            return "away"
        return "draw"

    @property
    def total_goals(self) -> Optional[int]:
        if self.home_goal is None or self.away_goal is None:
            return None
        return self.home_goal + self.away_goal


@dataclass
class Player:
    """A FIFA player record (subset of the many available columns)."""

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
    club_key: str = field(default="", init=False)

    def __post_init__(self):
        self.club_key = normalize_team(self.club)


def _open(path: Path):
    # utf-8-sig transparently drops the BOM present in some files.
    return open(path, newline="", encoding="utf-8-sig")


def load_brasileirao(path: Path) -> List[Match]:
    out = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            out.append(Match(
                competition="Brasileirão",
                season=parse_int(row.get("season")),
                date=parse_date(row.get("datetime")),
                round=str(row.get("round") or "").strip() or None,
                stage=None,
                home_team=row["home_team"],
                away_team=row["away_team"],
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
                source=path.name,
            ))
    return out


def load_cup(path: Path) -> List[Match]:
    out = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            out.append(Match(
                competition="Copa do Brasil",
                season=parse_int(row.get("season")),
                date=parse_date(row.get("datetime")),
                round=str(row.get("round") or "").strip() or None,
                stage=str(row.get("round") or "").strip() or None,
                home_team=row["home_team"],
                away_team=row["away_team"],
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
                source=path.name,
            ))
    return out


def load_libertadores(path: Path) -> List[Match]:
    out = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            out.append(Match(
                competition="Copa Libertadores",
                season=parse_int(row.get("season")),
                date=parse_date(row.get("datetime")),
                round=None,
                stage=str(row.get("stage") or "").strip() or None,
                home_team=row["home_team"],
                away_team=row["away_team"],
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
                source=path.name,
            ))
    return out


def load_br_football(path: Path) -> List[Match]:
    out = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            date = parse_date(row.get("date"))
            out.append(Match(
                competition=str(row.get("tournament") or "").strip() or "Unknown",
                season=date.year if date else None,
                date=date,
                round=None,
                stage=None,
                home_team=row["home"],
                away_team=row["away"],
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
                source=path.name,
            ))
    return out


def load_historical_brasileirao(path: Path) -> List[Match]:
    out = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            out.append(Match(
                competition="Brasileirão",
                season=parse_int(row.get("Ano")),
                date=parse_date(row.get("Data")),
                round=str(row.get("Rodada") or "").strip() or None,
                stage=None,
                home_team=row["Equipe_mandante"],
                away_team=row["Equipe_visitante"],
                home_goal=parse_int(row.get("Gols_mandante")),
                away_goal=parse_int(row.get("Gols_visitante")),
                source=path.name,
            ))
    return out


# Loaders in priority order. ``novo_campeonato_brasileiro.csv`` is the
# canonical Brasileirão source for 2003-2019 and is listed first so it owns the
# seasons that also appear in ``Brasileirao_Matches.csv`` (2012-2019);
# ``Brasileirao_Matches.csv`` then contributes only the later seasons it adds.
_MATCH_LOADERS = (
    ("novo_campeonato_brasileiro.csv", load_historical_brasileirao),
    ("Brasileirao_Matches.csv", load_brasileirao),
    ("Brazilian_Cup_Matches.csv", load_cup),
    ("Libertadores_Matches.csv", load_libertadores),
    ("BR-Football-Dataset.csv", load_br_football),
)


def load_all_matches(data_dir: Path = DATA_DIR) -> List[Match]:
    """Load every match file in *data_dir*, de-duplicating overlapping
    Brasileirão seasons so each season is served by a single source file."""
    data_dir = Path(data_dir)
    matches: List[Match] = []
    brasileirao_season_owner: dict = {}
    for filename, loader in _MATCH_LOADERS:
        path = data_dir / filename
        if not path.exists():
            continue
        for mt in loader(path):
            if mt.competition == "Brasileirão" and mt.season is not None:
                owner = brasileirao_season_owner.setdefault(mt.season, mt.source)
                if owner != mt.source:
                    continue  # season already supplied by an earlier source
            matches.append(mt)
    return matches


def load_players(path: Path = DATA_DIR / "fifa_data.csv") -> List[Player]:
    """Load the FIFA player database."""
    out: List[Player] = []
    with _open(Path(path)) as f:
        for row in csv.DictReader(f):
            out.append(Player(
                player_id=parse_int(row.get("ID")),
                name=str(row.get("Name") or "").strip(),
                age=parse_int(row.get("Age")),
                nationality=str(row.get("Nationality") or "").strip(),
                overall=parse_int(row.get("Overall")),
                potential=parse_int(row.get("Potential")),
                club=str(row.get("Club") or "").strip(),
                position=str(row.get("Position") or "").strip(),
                jersey_number=parse_int(row.get("Jersey Number")),
                height=str(row.get("Height") or "").strip(),
                weight=str(row.get("Weight") or "").strip(),
            ))
    return out
