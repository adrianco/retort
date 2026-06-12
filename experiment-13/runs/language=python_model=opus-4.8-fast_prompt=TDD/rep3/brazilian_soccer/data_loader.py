"""
CSV loaders for the Brazilian soccer datasets.

Context
-------
Each provided file uses a different column layout (see TASK.md). This module
reads every file into a single uniform :class:`Match` schema (and FIFA rows
into :class:`Player`), applying the team/date normalization from
:mod:`brazilian_soccer.normalize`.

Two Serie A sources overlap (``Brasileirao_Matches.csv`` 2012-2022 and
``novo_campeonato_brasileiro.csv`` 2003-2019), and ``BR-Football-Dataset.csv``
re-lists many league/cup games. :func:`load_all_matches` therefore de-duplicates
on a stable match signature so aggregate statistics are not double counted.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from . import normalize as nz

# Canonical competition labels used across all sources.
BRASILEIRAO_A = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

_BR_FOOTBALL_TOURNAMENTS = {
    "Serie A": BRASILEIRAO_A,
    "Serie B": BRASILEIRAO_B,
    "Serie C": BRASILEIRAO_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}


@dataclass
class Match:
    competition: str
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    season: Optional[int] = None
    date: Optional[str] = None
    round: Optional[str] = None
    stage: Optional[str] = None
    source: str = ""
    # Extended stats (only populated from BR-Football-Dataset.csv).
    home_corners: Optional[float] = None
    away_corners: Optional[float] = None
    home_shots: Optional[float] = None
    away_shots: Optional[float] = None
    home_key: str = field(default="", repr=False)
    away_key: str = field(default="", repr=False)

    def __post_init__(self):
        # Derive the matching key from the raw name (which may carry a
        # distinguishing state suffix) BEFORE stripping it for display.
        if not self.home_key:
            self.home_key = nz.team_key(self.home_team)
        if not self.away_key:
            self.away_key = nz.team_key(self.away_team)
        self.home_team = nz.normalize_team_name(self.home_team)
        self.away_team = nz.normalize_team_name(self.away_team)

    @property
    def total_goals(self) -> Optional[int]:
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_score + self.away_score

    @property
    def winner_key(self) -> Optional[str]:
        """Key of the winning team, or ``None`` for a draw/unknown score."""
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return self.home_key
        if self.away_score > self.home_score:
            return self.away_key
        return None  # draw

    def signature(self):
        return (self.competition, self.season, self.date,
                self.home_key, self.away_key)

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "season": self.season,
            "date": self.date,
            "round": self.round,
            "stage": self.stage,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
        }


@dataclass
class Player:
    id: Optional[int]
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    jersey_number: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    name_key: str = field(default="", repr=False)

    def __post_init__(self):
        if not self.name_key:
            self.name_key = nz.strip_accents(self.name or "").lower().strip()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
        }


# --- helpers ---------------------------------------------------------------

def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        if isinstance(value, float) and pd.isna(value):
            return None
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _to_str(value) -> Optional[str]:
    if value is None:
        return None
    try:
        if isinstance(value, float) and pd.isna(value):
            return None
    except TypeError:
        pass
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


# --- per-file loaders ------------------------------------------------------

def load_brasileirao(path: str) -> List[Match]:
    df = _read_csv(path)
    out = []
    for r in df.itertuples(index=False):
        d = r._asdict()
        out.append(Match(
            competition=BRASILEIRAO_A,
            home_team=d["home_team"],
            away_team=d["away_team"],
            home_score=_to_int(d["home_goal"]),
            away_score=_to_int(d["away_goal"]),
            season=_to_int(d["season"]),
            date=nz.parse_date(d["datetime"]),
            round=_to_str(d["round"]),
            source=os.path.basename(path),
        ))
    return out


def load_cup(path: str) -> List[Match]:
    df = _read_csv(path)
    out = []
    for r in df.itertuples(index=False):
        d = r._asdict()
        out.append(Match(
            competition=COPA_DO_BRASIL,
            home_team=d["home_team"],
            away_team=d["away_team"],
            home_score=_to_int(d["home_goal"]),
            away_score=_to_int(d["away_goal"]),
            season=_to_int(d["season"]),
            date=nz.parse_date(d["datetime"]),
            round=_to_str(d["round"]),
            source=os.path.basename(path),
        ))
    return out


def load_libertadores(path: str) -> List[Match]:
    df = _read_csv(path)
    out = []
    for r in df.itertuples(index=False):
        d = r._asdict()
        out.append(Match(
            competition=LIBERTADORES,
            home_team=d["home_team"],
            away_team=d["away_team"],
            home_score=_to_int(d["home_goal"]),
            away_score=_to_int(d["away_goal"]),
            season=_to_int(d["season"]),
            date=nz.parse_date(d["datetime"]),
            stage=_to_str(d["stage"]),
            source=os.path.basename(path),
        ))
    return out


def load_br_football(path: str) -> List[Match]:
    df = _read_csv(path)
    out = []
    for r in df.itertuples(index=False):
        d = r._asdict()
        tournament = _to_str(d["tournament"]) or ""
        competition = _BR_FOOTBALL_TOURNAMENTS.get(tournament, tournament)
        date = nz.parse_date(d["date"])
        out.append(Match(
            competition=competition,
            home_team=d["home"],
            away_team=d["away"],
            home_score=_to_int(d["home_goal"]),
            away_score=_to_int(d["away_goal"]),
            season=nz.year_of(d["date"]),
            date=date,
            home_corners=_to_int(d["home_corner"]),
            away_corners=_to_int(d["away_corner"]),
            home_shots=_to_int(d["home_shots"]),
            away_shots=_to_int(d["away_shots"]),
            source=os.path.basename(path),
        ))
    return out


def load_novo(path: str) -> List[Match]:
    df = _read_csv(path)
    out = []
    for r in df.itertuples(index=False):
        d = r._asdict()
        out.append(Match(
            competition=BRASILEIRAO_A,
            home_team=d["Equipe_mandante"],
            away_team=d["Equipe_visitante"],
            home_score=_to_int(d["Gols_mandante"]),
            away_score=_to_int(d["Gols_visitante"]),
            season=_to_int(d["Ano"]),
            date=nz.parse_date(d["Data"]),
            round=_to_str(d["Rodada"]),
            source=os.path.basename(path),
        ))
    return out


def load_players(path: str) -> List[Player]:
    df = _read_csv(path)
    out = []
    for r in df.itertuples(index=False):
        d = r._asdict()
        name = _to_str(d.get("Name"))
        if not name:
            continue
        out.append(Player(
            id=_to_int(d.get("ID")),
            name=name,
            age=_to_int(d.get("Age")),
            nationality=_to_str(d.get("Nationality")) or "",
            overall=_to_int(d.get("Overall")),
            potential=_to_int(d.get("Potential")),
            club=_to_str(d.get("Club")) or "",
            position=_to_str(d.get("Position")) or "",
            jersey_number=_to_str(d.get("Jersey Number")),
            height=_to_str(d.get("Height")),
            weight=_to_str(d.get("Weight")),
        ))
    return out


# --- aggregate -------------------------------------------------------------

_MATCH_FILES = [
    ("Brasileirao_Matches.csv", load_brasileirao),
    ("novo_campeonato_brasileiro.csv", load_novo),
    ("Libertadores_Matches.csv", load_libertadores),
    ("Brazilian_Cup_Matches.csv", load_cup),
    ("BR-Football-Dataset.csv", load_br_football),
]

PLAYER_FILE = "fifa_data.csv"


def load_all_matches(data_dir: str) -> List[Match]:
    """Load every match, choosing one authoritative source per season.

    The same competition/season often appears in several files with off-by-one
    dates and divergent team-name spellings (e.g. "Athletico-PR" vs
    "Atletico Paranaense"), which makes per-row de-duplication unreliable.
    Instead, for each ``(competition, season)`` we keep only the matches from
    the highest-priority source that covers it (file order in ``_MATCH_FILES``).
    A lower-priority source is still used for seasons the better sources lack
    (e.g. BR-Football is the sole source of Série B/C and recent Série A).
    """
    loaded = []  # list of (priority, filename, [Match])
    for priority, (filename, loader) in enumerate(_MATCH_FILES):
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            continue
        loaded.append((priority, filename, loader(path)))

    # Best (lowest) priority available for each (competition, season).
    best: dict = {}
    for priority, _filename, matches in loaded:
        for m in matches:
            key = (m.competition, m.season)
            if key not in best or priority < best[key]:
                best[key] = priority

    out: List[Match] = []
    seen = set()  # within-source safety net against exact repeats
    for priority, _filename, matches in loaded:
        for m in matches:
            if best[(m.competition, m.season)] != priority:
                continue
            sig = m.signature()
            if sig in seen:
                continue
            seen.add(sig)
            out.append(m)
    return out


def load_all_players(data_dir: str) -> List[Player]:
    path = os.path.join(data_dir, PLAYER_FILE)
    if not os.path.exists(path):
        return []
    return load_players(path)
