"""
================================================================================
data_loader.py - Typed in-memory store loaded from the Kaggle CSV files
================================================================================

CONTEXT
-------
Loads all six datasets described in the specification into a single, normalised
in-memory store using only the Python standard library (no pandas), so the
server starts quickly and has no heavy runtime dependencies.

Two record types are produced:

    Match  - one row per fixture, normalised from five different match files
    Player - one row per FIFA player

Data-quality handling
----------------------
Three files cover Brasileirão Série A and two cover Copa do Brasil with heavy
season overlap. Loading them naively would triple-count games. We therefore:

  * tag every match with a ``competition`` family and ``source`` file, and
  * compute a single *canonical* source per (competition, season) using a fixed
    priority order, marking the chosen rows ``canonical=True``.

Standings and league-wide statistics consume only canonical rows; raw match
search can optionally include every source.

Canonical priority (best first):
    Série A        : Brasileirao_Matches > novo_campeonato > BR-Football
    Copa do Brasil : Brazilian_Cup_Matches > BR-Football
    Série B/C      : BR-Football (only source)
    Libertadores   : Libertadores_Matches (only source)
================================================================================
"""

from __future__ import annotations

import csv
import datetime
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .normalize import normalize_team, parse_date, parse_int, team_display

# --------------------------------------------------------------------------- #
# Competition metadata
# --------------------------------------------------------------------------- #
COMPETITION_NAMES = {
    "serie_a": "Brasileirão Série A",
    "serie_b": "Brasileirão Série B",
    "serie_c": "Brasileirão Série C",
    "copa_do_brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
}

# Lower priority number wins when choosing the canonical source for a season.
_SOURCE_PRIORITY = {
    "Brasileirao_Matches.csv": 0,
    "novo_campeonato_brasileiro.csv": 1,
    "Brazilian_Cup_Matches.csv": 0,
    "Libertadores_Matches.csv": 0,
    "BR-Football-Dataset.csv": 2,
}


@dataclass
class Match:
    """A single normalised fixture from any of the match datasets."""

    competition: str                 # family key, e.g. "serie_a"
    season: Optional[int]
    date: Optional[datetime.date]
    home_team: str                   # canonical key
    away_team: str                   # canonical key
    home_display: str
    away_display: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    source: str
    round: Optional[str] = None
    stage: Optional[str] = None
    home_state: Optional[str] = None
    away_state: Optional[str] = None
    arena: Optional[str] = None
    stats: Dict[str, float] = field(default_factory=dict)
    canonical: bool = False

    @property
    def competition_name(self) -> str:
        return COMPETITION_NAMES.get(self.competition, self.competition)

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def total_goals(self) -> Optional[int]:
        if not self.has_score:
            return None
        return self.home_goal + self.away_goal

    def winner(self) -> Optional[str]:
        """Canonical key of the winner, or ``None`` for a draw / no score."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return self.home_team
        if self.away_goal > self.home_goal:
            return self.away_team
        return None

    def involves(self, team_key: str) -> bool:
        return team_key in (self.home_team, self.away_team)


@dataclass
class Player:
    """A FIFA player record (subset of the most useful columns)."""

    player_id: Optional[int]
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    club_key: str
    position: str
    jersey_number: Optional[int]
    height: str
    weight: str
    preferred_foot: str
    skills: Dict[str, Optional[int]] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Store
# --------------------------------------------------------------------------- #
class DataStore:
    """Holds all loaded matches and players plus a few derived indexes."""

    def __init__(self, matches: List[Match], players: List[Player]):
        self.matches = matches
        self.players = players
        self._mark_canonical_sources()

    # -- canonical-source de-duplication ---------------------------------- #
    def _mark_canonical_sources(self) -> None:
        best: Dict[Tuple[str, Optional[int]], str] = {}
        for m in self.matches:
            key = (m.competition, m.season)
            pr = _SOURCE_PRIORITY.get(m.source, 99)
            cur = best.get(key)
            if cur is None or pr < _SOURCE_PRIORITY.get(cur, 99):
                best[key] = m.source
        for m in self.matches:
            m.canonical = best.get((m.competition, m.season)) == m.source

    # -- convenience accessors -------------------------------------------- #
    def canonical_matches(self) -> List[Match]:
        return [m for m in self.matches if m.canonical]

    def seasons(self, competition: Optional[str] = None) -> List[int]:
        out = {
            m.season
            for m in self.matches
            if m.season is not None and (competition is None or m.competition == competition)
        }
        return sorted(out)

    def competitions(self) -> List[str]:
        return sorted({m.competition for m in self.matches})

    def summary(self) -> Dict[str, int]:
        return {
            "total_matches": len(self.matches),
            "canonical_matches": len(self.canonical_matches()),
            "players": len(self.players),
            "competitions": len(self.competitions()),
        }


# --------------------------------------------------------------------------- #
# Loading helpers
# --------------------------------------------------------------------------- #
def _open(path: str):
    # utf-8-sig transparently strips the BOM present in fifa_data.csv.
    return open(path, "r", encoding="utf-8-sig", newline="")


def _make_match(competition, season, date, home_raw, away_raw, hg, ag, source,
                round_=None, stage=None, home_state=None, away_state=None,
                arena=None, stats=None) -> Match:
    return Match(
        competition=competition,
        season=season,
        date=date,
        home_team=normalize_team(home_raw),
        away_team=normalize_team(away_raw),
        home_display=team_display(home_raw),
        away_display=team_display(away_raw),
        home_goal=parse_int(hg),
        away_goal=parse_int(ag),
        source=source,
        round=str(round_) if round_ not in (None, "") else None,
        stage=stage or None,
        home_state=home_state or None,
        away_state=away_state or None,
        arena=arena or None,
        stats=stats or {},
    )


def _load_brasileirao(path: str) -> List[Match]:
    src = "Brasileirao_Matches.csv"
    out = []
    with _open(path) as fh:
        for r in csv.DictReader(fh):
            out.append(_make_match(
                "serie_a", parse_int(r.get("season")), parse_date(r.get("datetime")),
                r.get("home_team"), r.get("away_team"),
                r.get("home_goal"), r.get("away_goal"), src,
                round_=r.get("round"),
                home_state=r.get("home_team_state"), away_state=r.get("away_team_state"),
            ))
    return out


def _load_cup(path: str) -> List[Match]:
    src = "Brazilian_Cup_Matches.csv"
    out = []
    with _open(path) as fh:
        for r in csv.DictReader(fh):
            out.append(_make_match(
                "copa_do_brasil", parse_int(r.get("season")), parse_date(r.get("datetime")),
                r.get("home_team"), r.get("away_team"),
                r.get("home_goal"), r.get("away_goal"), src,
                round_=r.get("round"),
            ))
    return out


def _load_libertadores(path: str) -> List[Match]:
    src = "Libertadores_Matches.csv"
    out = []
    with _open(path) as fh:
        for r in csv.DictReader(fh):
            out.append(_make_match(
                "libertadores", parse_int(r.get("season")), parse_date(r.get("datetime")),
                r.get("home_team"), r.get("away_team"),
                r.get("home_goal"), r.get("away_goal"), src,
                stage=r.get("stage"),
            ))
    return out


def _load_novo(path: str) -> List[Match]:
    src = "novo_campeonato_brasileiro.csv"
    out = []
    with _open(path) as fh:
        for r in csv.DictReader(fh):
            out.append(_make_match(
                "serie_a", parse_int(r.get("Ano")), parse_date(r.get("Data")),
                r.get("Equipe_mandante"), r.get("Equipe_visitante"),
                r.get("Gols_mandante"), r.get("Gols_visitante"), src,
                round_=r.get("Rodada"),
                home_state=r.get("Mandante_UF"), away_state=r.get("Visitante_UF"),
                arena=r.get("Arena"),
            ))
    return out


_BR_FOOTBALL_COMP = {
    "serie a": "serie_a",
    "serie b": "serie_b",
    "serie c": "serie_c",
    "copa do brasil": "copa_do_brasil",
}


def _load_br_football(path: str) -> List[Match]:
    src = "BR-Football-Dataset.csv"
    out = []
    with _open(path) as fh:
        for r in csv.DictReader(fh):
            comp = _BR_FOOTBALL_COMP.get((r.get("tournament") or "").strip().lower())
            if comp is None:
                continue
            date = parse_date(r.get("date"))
            season = date.year if date else None
            stats = {}
            for k in ("home_corner", "away_corner", "home_shots", "away_shots",
                      "home_attack", "away_attack", "total_corners"):
                v = r.get(k)
                try:
                    if v not in (None, ""):
                        stats[k] = float(v)
                except (ValueError, TypeError):
                    pass
            out.append(_make_match(
                comp, season, date,
                r.get("home"), r.get("away"),
                r.get("home_goal"), r.get("away_goal"), src,
                stats=stats,
            ))
    return out


_BRAZIL_NATIONALITY = "Brazil"


def _load_players(path: str) -> List[Player]:
    out = []
    skill_cols = (
        "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling",
        "BallControl", "Acceleration", "SprintSpeed", "ShotPower", "Stamina",
        "Strength", "Vision", "Penalties", "Composure", "StandingTackle",
        "GKReflexes",
    )
    with _open(path) as fh:
        for r in csv.DictReader(fh):
            club = (r.get("Club") or "").strip()
            out.append(Player(
                player_id=parse_int(r.get("ID")),
                name=(r.get("Name") or "").strip(),
                age=parse_int(r.get("Age")),
                nationality=(r.get("Nationality") or "").strip(),
                overall=parse_int(r.get("Overall")),
                potential=parse_int(r.get("Potential")),
                club=club,
                club_key=normalize_team(club),
                position=(r.get("Position") or "").strip(),
                jersey_number=parse_int(r.get("Jersey Number")),
                height=(r.get("Height") or "").strip(),
                weight=(r.get("Weight") or "").strip(),
                preferred_foot=(r.get("Preferred Foot") or "").strip(),
                skills={c: parse_int(r.get(c)) for c in skill_cols},
            ))
    return out


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #
_LOADERS = {
    "Brasileirao_Matches.csv": _load_brasileirao,
    "Brazilian_Cup_Matches.csv": _load_cup,
    "Libertadores_Matches.csv": _load_libertadores,
    "novo_campeonato_brasileiro.csv": _load_novo,
    "BR-Football-Dataset.csv": _load_br_football,
}


def default_data_dir() -> str:
    """Path to the bundled ``data/kaggle`` directory (override with env var)."""
    env = os.environ.get("BR_SOCCER_DATA_DIR")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "data", "kaggle")


def load_store(data_dir: Optional[str] = None) -> DataStore:
    """Load every available dataset from *data_dir* into a :class:`DataStore`."""
    data_dir = data_dir or default_data_dir()
    matches: List[Match] = []
    for filename, loader in _LOADERS.items():
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            matches.extend(loader(path))

    players: List[Player] = []
    players_path = os.path.join(data_dir, "fifa_data.csv")
    if os.path.exists(players_path):
        players = _load_players(players_path)

    return DataStore(matches, players)


# Cached singleton so the (relatively expensive) load happens once per process.
_DEFAULT_STORE: Optional[DataStore] = None


def load_default_store(refresh: bool = False) -> DataStore:
    """Return a process-wide cached store loaded from the bundled data."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None or refresh:
        _DEFAULT_STORE = load_store()
    return _DEFAULT_STORE
