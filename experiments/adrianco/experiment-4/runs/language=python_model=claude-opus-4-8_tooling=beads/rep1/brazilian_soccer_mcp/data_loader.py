"""
================================================================================
Module: brazilian_soccer_mcp.data_loader
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
  Loads the six provided Kaggle CSV datasets (under data/kaggle/) into a single
  normalized in-memory model so every downstream query works off one consistent
  shape regardless of the source file's columns, language, or date format.

  The datasets differ widely:
    * Brasileirao_Matches.csv       English cols, ISO datetime, state suffixes
    * Brazilian_Cup_Matches.csv     Copa do Brasil, ISO datetime
    * Libertadores_Matches.csv      adds a `stage` column, country suffixes
    * BR-Football-Dataset.csv       extra stats (corners/shots/attacks),
                                    `tournament` column, date only (no season)
    * novo_campeonato_brasileiro.csv  Portuguese cols, DD/MM/YYYY dates, arena
    * fifa_data.csv                 FIFA player attributes (18k players)

  All files are read as UTF-8 (with BOM tolerance) to preserve Portuguese
  accents and the cedilla.

NORMALIZED MODEL
  Match dataclass  - one row per match, unified across all five match files.
  Player dataclass - one row per FIFA player.
  SoccerData       - container exposing .matches and .players, loaded once.

DATE HANDLING
  Multiple input formats are parsed to datetime.date (parse_date), and a season
  is derived from the year when the source file lacks an explicit season column.
================================================================================
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from typing import Optional

from .normalize import resolve_team

# ---------------------------------------------------------------------------
# Locate the bundled data directory (data/kaggle relative to the repo root).
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
DEFAULT_DATA_DIR = os.path.join(_REPO_ROOT, "data", "kaggle")


# ---------------------------------------------------------------------------
# Canonical competition labels.
# ---------------------------------------------------------------------------
BRASILEIRAO = "Brasileirão Série A"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

# Map the BR-Football-Dataset `tournament` values to canonical labels.
_BR_TOURNAMENT_MAP = {
    "Serie A": BRASILEIRAO,
    "Serie B": "Brasileirão Série B",
    "Serie C": "Brasileirão Série C",
    "Copa do Brasil": COPA_DO_BRASIL,
}


@dataclass
class Match:
    """A single match, normalized across every source dataset."""

    competition: str
    season: Optional[int]
    match_date: Optional[date]
    home_key: str
    away_key: str
    home_name: str
    away_name: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    round: Optional[str] = None
    stage: Optional[str] = None
    arena: Optional[str] = None
    source: str = ""
    # Optional extended statistics (only present in BR-Football-Dataset).
    stats: dict = field(default_factory=dict)

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def total_goals(self) -> Optional[int]:
        if not self.has_score:
            return None
        return self.home_goal + self.away_goal

    def winner_key(self) -> Optional[str]:
        """Canonical key of the winner, or None for a draw / unknown score."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None  # draw


@dataclass
class Player:
    """A FIFA player record (subset of the most useful attributes)."""

    player_id: str
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    club_key: str
    position: str
    jersey: str
    height: str
    weight: str
    value: str
    wage: str
    preferred_foot: str
    skills: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parsing helpers.
# ---------------------------------------------------------------------------
def parse_date(raw: str) -> Optional[date]:
    """Parse the several date formats found in the datasets."""
    if not raw:
        return None
    raw = raw.strip()
    fmts = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%Y/%m/%d",
    )
    for fmt in fmts:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    # Last resort: take the leading date token of an ISO-ish string.
    head = raw.split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(head, fmt).date()
        except ValueError:
            continue
    return None


def _to_int(raw) -> Optional[int]:
    """Coerce a possibly-float-looking string to int, tolerating blanks."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _team(raw: str) -> tuple[str, str]:
    return resolve_team(raw or "")


# ---------------------------------------------------------------------------
# Per-file loaders. Each yields normalized Match records.
# ---------------------------------------------------------------------------
def _open(path: str):
    return open(path, encoding="utf-8-sig", newline="")


def _load_brasileirao(path: str) -> list[Match]:
    out = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            hk, hn = _team(row["home_team"])
            ak, an = _team(row["away_team"])
            out.append(Match(
                competition=BRASILEIRAO,
                season=_to_int(row.get("season")),
                match_date=parse_date(row.get("datetime", "")),
                home_key=hk, away_key=ak, home_name=hn, away_name=an,
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                round=str(row.get("round") or "").strip() or None,
                source="Brasileirao_Matches.csv",
            ))
    return out


def _load_cup(path: str) -> list[Match]:
    out = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            hk, hn = _team(row["home_team"])
            ak, an = _team(row["away_team"])
            out.append(Match(
                competition=COPA_DO_BRASIL,
                season=_to_int(row.get("season")),
                match_date=parse_date(row.get("datetime", "")),
                home_key=hk, away_key=ak, home_name=hn, away_name=an,
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                round=str(row.get("round") or "").strip() or None,
                source="Brazilian_Cup_Matches.csv",
            ))
    return out


def _load_libertadores(path: str) -> list[Match]:
    out = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            hk, hn = _team(row["home_team"])
            ak, an = _team(row["away_team"])
            out.append(Match(
                competition=LIBERTADORES,
                season=_to_int(row.get("season")),
                match_date=parse_date(row.get("datetime", "")),
                home_key=hk, away_key=ak, home_name=hn, away_name=an,
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                stage=str(row.get("stage") or "").strip() or None,
                source="Libertadores_Matches.csv",
            ))
    return out


def _load_br_football(path: str) -> list[Match]:
    out = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            hk, hn = _team(row["home"])
            ak, an = _team(row["away"])
            d = parse_date(row.get("date", ""))
            competition = _BR_TOURNAMENT_MAP.get(
                (row.get("tournament") or "").strip(),
                (row.get("tournament") or "").strip() or "Unknown",
            )
            stats = {
                "home_corner": _to_int(row.get("home_corner")),
                "away_corner": _to_int(row.get("away_corner")),
                "home_shots": _to_int(row.get("home_shots")),
                "away_shots": _to_int(row.get("away_shots")),
                "home_attack": _to_int(row.get("home_attack")),
                "away_attack": _to_int(row.get("away_attack")),
                "total_corners": _to_int(row.get("total_corners")),
                "ht_result": (row.get("ht_result") or "").strip() or None,
            }
            out.append(Match(
                competition=competition,
                season=d.year if d else None,
                match_date=d,
                home_key=hk, away_key=ak, home_name=hn, away_name=an,
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                source="BR-Football-Dataset.csv",
                stats=stats,
            ))
    return out


def _load_novo(path: str) -> list[Match]:
    out = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            hk, hn = _team(row["Equipe_mandante"])
            ak, an = _team(row["Equipe_visitante"])
            out.append(Match(
                competition=BRASILEIRAO,
                season=_to_int(row.get("Ano")),
                match_date=parse_date(row.get("Data", "")),
                home_key=hk, away_key=ak, home_name=hn, away_name=an,
                home_goal=_to_int(row.get("Gols_mandante")),
                away_goal=_to_int(row.get("Gols_visitante")),
                round=str(row.get("Rodada") or "").strip() or None,
                arena=(row.get("Arena") or "").strip() or None,
                source="novo_campeonato_brasileiro.csv",
            ))
    return out


def _load_players(path: str) -> list[Player]:
    out = []
    skill_cols = (
        "Crossing", "Finishing", "ShortPassing", "Dribbling", "BallControl",
        "Acceleration", "SprintSpeed", "ShotPower", "Stamina", "Strength",
        "Vision", "Penalties", "Composure", "StandingTackle", "GKReflexes",
    )
    with _open(path) as f:
        for row in csv.DictReader(f):
            club = (row.get("Club") or "").strip()
            ck, _ = _team(club) if club else ("", "")
            skills = {c: _to_int(row.get(c)) for c in skill_cols}
            out.append(Player(
                player_id=(row.get("ID") or "").strip(),
                name=(row.get("Name") or "").strip(),
                age=_to_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=_to_int(row.get("Overall")),
                potential=_to_int(row.get("Potential")),
                club=club,
                club_key=ck,
                position=(row.get("Position") or "").strip(),
                jersey=(row.get("Jersey Number") or "").strip(),
                height=(row.get("Height") or "").strip(),
                weight=(row.get("Weight") or "").strip(),
                value=(row.get("Value") or "").strip(),
                wage=(row.get("Wage") or "").strip(),
                preferred_foot=(row.get("Preferred Foot") or "").strip(),
                skills=skills,
            ))
    return out


# ---------------------------------------------------------------------------
# Top-level container.
# ---------------------------------------------------------------------------
@dataclass
class SoccerData:
    matches: list[Match]
    players: list[Player]

    @property
    def competitions(self) -> set[str]:
        return {m.competition for m in self.matches}

    @property
    def seasons(self) -> set[int]:
        return {m.season for m in self.matches if m.season is not None}


_MATCH_LOADERS = {
    "Brasileirao_Matches.csv": _load_brasileirao,
    "Brazilian_Cup_Matches.csv": _load_cup,
    "Libertadores_Matches.csv": _load_libertadores,
    "BR-Football-Dataset.csv": _load_br_football,
    "novo_campeonato_brasileiro.csv": _load_novo,
}


def _deduplicate(matches: list[Match]) -> list[Match]:
    """Collapse the same real-world fixture appearing in multiple datasets.

    The provided files overlap heavily (e.g. season 2019 Série A is present in
    Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv AND the Serie A rows
    of BR-Football-Dataset.csv). Without this, standings and aggregates would be
    inflated 2-3x.

    A fixture is keyed by (competition, season, home_key, away_key). Season +
    home/away ordering uniquely identifies a league fixture and is robust to the
    ±1 day kick-off date offsets present between datasets (BR-Football stores
    several matches one calendar day later than the official source). When the
    season is unknown we fall back to a date-based key. The first occurrence
    wins (loader order prefers the clean league/cup files), and extended
    statistics from any later duplicate are merged into the kept record so no
    information is lost.
    """
    kept: list[Match] = []
    index: dict[tuple, Match] = {}
    for m in matches:
        if m.season is not None:
            key = (m.competition, m.season, m.home_key, m.away_key)
        elif m.match_date is not None:
            key = (m.competition, m.match_date, m.home_key, m.away_key)
        else:
            kept.append(m)
            continue
        existing = index.get(key)
        if existing is None:
            index[key] = m
            kept.append(m)
        else:
            # Enrich the kept record with stats from the duplicate, if missing.
            if m.stats and not existing.stats:
                existing.stats = m.stats
            if existing.arena is None and m.arena:
                existing.arena = m.arena
    return kept


def load_data(data_dir: str | None = None) -> SoccerData:
    """Load all six datasets from `data_dir` into a SoccerData container."""
    data_dir = data_dir or DEFAULT_DATA_DIR
    matches: list[Match] = []
    for fname, loader in _MATCH_LOADERS.items():
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            matches.extend(loader(path))
    matches = _deduplicate(matches)

    players: list[Player] = []
    players_path = os.path.join(data_dir, "fifa_data.csv")
    if os.path.exists(players_path):
        players = _load_players(players_path)

    return SoccerData(matches=matches, players=players)


@lru_cache(maxsize=2)
def get_data(data_dir: str | None = None) -> SoccerData:
    """Cached singleton accessor so the CSVs are parsed only once per process."""
    return load_data(data_dir)
