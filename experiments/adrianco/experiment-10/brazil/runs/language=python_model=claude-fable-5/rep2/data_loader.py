"""Load the six Kaggle CSVs into unified Match and Player records.

Datasets (under ``data/kaggle/``):
  - Brasileirao_Matches.csv        Serie A 2012-2022, state-suffixed names
  - novo_campeonato_brasileiro.csv Serie A 2003-2019, DD/MM/YYYY dates, stadiums
  - Brazilian_Cup_Matches.csv      Copa do Brasil 2012+
  - Libertadores_Matches.csv       Copa Libertadores 2013+, stage column
  - BR-Football-Dataset.csv        Serie A/B/C + cup, corners/shots/attacks
  - fifa_data.csv                  FIFA player attributes

Serie A seasons 2012-2019 appear in three sources; matches are de-duplicated
on (date, home team, away team) with the more detailed extras merged in.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional

from team_normalizer import parse_team, team_key

DATA_DIR = Path(__file__).resolve().parent / "data" / "kaggle"

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

_TOURNAMENT_MAP = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}


@dataclass
class Match:
    competition: str
    season: Optional[int]
    date: Optional[date]
    home_team: str          # display name as it appears in the source
    away_team: str
    home_goal: int
    away_goal: int
    round: Optional[str] = None
    stage: Optional[str] = None
    stadium: Optional[str] = None
    source: str = ""
    extras: Dict[str, float] = field(default_factory=dict)
    home_key: str = ""      # canonical team keys, filled in __post_init__
    away_key: str = ""

    def __post_init__(self) -> None:
        self.home_key = team_key(self.home_team)
        self.away_key = team_key(self.away_team)

    @property
    def winner_key(self) -> Optional[str]:
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None

    def to_dict(self) -> dict:
        out = {
            "date": self.date.isoformat() if self.date else None,
            "competition": self.competition,
            "season": self.season,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "score": f"{self.home_goal}-{self.away_goal}",
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
        }
        if self.round:
            out["round"] = self.round
        if self.stage:
            out["stage"] = self.stage
        if self.stadium:
            out["stadium"] = self.stadium
        if self.extras:
            out["stats"] = self.extras
        return out


@dataclass
class Player:
    player_id: str
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
    value: str
    wage: str
    skills: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.player_id,
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
            "value": self.value,
            "wage": self.wage,
        }


_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",
)


def parse_date(text: str) -> Optional[date]:
    """Parse the date formats used across the datasets (ISO and DD/MM/YYYY)."""
    text = (text or "").strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _to_int(value: str) -> Optional[int]:
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def _read_csv(filename: str) -> List[dict]:
    path = DATA_DIR / filename
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _load_brasileirao() -> List[Match]:
    matches = []
    for row in _read_csv("Brasileirao_Matches.csv"):
        hg, ag = _to_int(row["home_goal"]), _to_int(row["away_goal"])
        if hg is None or ag is None:
            continue
        matches.append(Match(
            competition=SERIE_A,
            season=_to_int(row["season"]),
            date=parse_date(row["datetime"]),
            home_team=row["home_team"],
            away_team=row["away_team"],
            home_goal=hg,
            away_goal=ag,
            round=row.get("round") or None,
            source="Brasileirao_Matches.csv",
        ))
    return matches


def _load_novo() -> List[Match]:
    matches = []
    for row in _read_csv("novo_campeonato_brasileiro.csv"):
        hg, ag = _to_int(row["Gols_mandante"]), _to_int(row["Gols_visitante"])
        if hg is None or ag is None:
            continue
        matches.append(Match(
            competition=SERIE_A,
            season=_to_int(row["Ano"]),
            date=parse_date(row["Data"]),
            home_team=row["Equipe_mandante"],
            away_team=row["Equipe_visitante"],
            home_goal=hg,
            away_goal=ag,
            round=row.get("Rodada") or None,
            stadium=(row.get("Arena") or "").strip() or None,
            source="novo_campeonato_brasileiro.csv",
        ))
    return matches


def _load_cup() -> List[Match]:
    matches = []
    for row in _read_csv("Brazilian_Cup_Matches.csv"):
        hg, ag = _to_int(row["home_goal"]), _to_int(row["away_goal"])
        if hg is None or ag is None:
            continue
        matches.append(Match(
            competition=COPA_DO_BRASIL,
            season=_to_int(row["season"]),
            date=parse_date(row["datetime"]),
            home_team=row["home_team"],
            away_team=row["away_team"],
            home_goal=hg,
            away_goal=ag,
            round=row.get("round") or None,
            source="Brazilian_Cup_Matches.csv",
        ))
    return matches


def _load_libertadores() -> List[Match]:
    matches = []
    for row in _read_csv("Libertadores_Matches.csv"):
        hg, ag = _to_int(row["home_goal"]), _to_int(row["away_goal"])
        if hg is None or ag is None:
            continue
        matches.append(Match(
            competition=LIBERTADORES,
            season=_to_int(row["season"]),
            date=parse_date(row["datetime"]),
            home_team=row["home_team"],
            away_team=row["away_team"],
            home_goal=hg,
            away_goal=ag,
            stage=(row.get("stage") or "").strip() or None,
            source="Libertadores_Matches.csv",
        ))
    return matches


def _load_br_football() -> List[Match]:
    matches = []
    stat_cols = (
        "home_corner", "away_corner", "home_attack", "away_attack",
        "home_shots", "away_shots", "total_corners",
    )
    for row in _read_csv("BR-Football-Dataset.csv"):
        hg, ag = _to_int(row["home_goal"]), _to_int(row["away_goal"])
        if hg is None or ag is None:
            continue
        when = parse_date(row.get("date", ""))
        extras = {}
        for col in stat_cols:
            val = _to_int(row.get(col, ""))
            if val is not None:
                extras[col] = val
        matches.append(Match(
            competition=_TOURNAMENT_MAP.get(row["tournament"], row["tournament"]),
            season=when.year if when else None,
            date=when,
            home_team=row["home"],
            away_team=row["away"],
            home_goal=hg,
            away_goal=ag,
            source="BR-Football-Dataset.csv",
            extras=extras,
        ))
    return matches


def load_matches() -> List[Match]:
    """All matches from the five match CSVs, de-duplicated across sources.

    Sources are loaded in priority order; a match already seen (same date and
    teams) is not added twice, but extra statistics from the lower-priority
    source are merged into the kept record.
    """
    loaders = (
        _load_brasileirao, _load_novo, _load_cup,
        _load_libertadores, _load_br_football,
    )
    seen: Dict[tuple, Match] = {}
    matches: List[Match] = []
    for loader in loaders:
        for match in loader():
            # Duplicate signatures use accent/suffix-free base team names
            # (sources disagree on "Sao Paulo" vs "São Paulo-SP").  A fixture
            # is a duplicate when it matches on season+round, or on teams
            # with a date within one day (sources disagree on kick-off date).
            hb, _ = parse_team(match.home_team)
            ab, _ = parse_team(match.away_team)
            lookup = []
            if match.date is not None:
                ordinal = match.date.toordinal()
                lookup += [("d", ordinal + delta, hb, ab) for delta in (-1, 0, 1)]
            round_no = _to_int(match.round) if match.round else None
            if match.season is not None and round_no is not None:
                lookup.append((
                    "r", match.competition, match.season, round_no, hb, ab,
                ))
            kept = next((seen[k] for k in lookup if k in seen), None)
            if kept is not None:
                for k, v in match.extras.items():
                    kept.extras.setdefault(k, v)
                if match.stadium and not kept.stadium:
                    kept.stadium = match.stadium
                continue
            if match.date is not None:
                seen[("d", match.date.toordinal(), hb, ab)] = match
            if match.season is not None and round_no is not None:
                seen[("r", match.competition, match.season, round_no, hb, ab)] = match
            matches.append(match)
    matches.sort(key=lambda m: (m.date or date.min))
    return matches


_SKILL_COLS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)


def load_players() -> List[Player]:
    """All players from fifa_data.csv."""
    players = []
    for row in _read_csv("fifa_data.csv"):
        name = (row.get("Name") or "").strip()
        if not name:
            continue
        skills = {}
        for col in _SKILL_COLS:
            val = _to_int(row.get(col, ""))
            if val is not None:
                skills[col] = val
        players.append(Player(
            player_id=(row.get("ID") or "").strip(),
            name=name,
            age=_to_int(row.get("Age", "")),
            nationality=(row.get("Nationality") or "").strip(),
            overall=_to_int(row.get("Overall", "")),
            potential=_to_int(row.get("Potential", "")),
            club=(row.get("Club") or "").strip(),
            position=(row.get("Position") or "").strip(),
            jersey_number=_to_int(row.get("Jersey Number", "")),
            height=(row.get("Height") or "").strip(),
            weight=(row.get("Weight") or "").strip(),
            value=(row.get("Value") or "").strip(),
            wage=(row.get("Wage") or "").strip(),
            skills=skills,
        ))
    return players
