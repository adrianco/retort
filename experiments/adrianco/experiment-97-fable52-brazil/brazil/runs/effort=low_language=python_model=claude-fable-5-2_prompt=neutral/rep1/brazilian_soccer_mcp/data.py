"""CSV loading for the six Kaggle datasets (UTF-8, mixed date formats)."""
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_BR = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"
COMPETITIONS = [SERIE_A, SERIE_B, SERIE_C, COPA_BR, LIBERTADORES]

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M")


def parse_date(value) -> Optional[dt.date]:
    """Parse ISO ("2023-09-24"), ISO with time, or Brazilian ("29/03/2003") dates."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = str(value or "").strip()
    if not text or text.upper() == "NA":
        return None
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unrecognised date: {value!r} (use YYYY-MM-DD or DD/MM/YYYY)")


def _int(value) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


@dataclass
class Match:
    competition: str
    season: int
    date: Optional[dt.date]
    home_raw: str
    away_raw: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    round: str = ""          # round number or stage name
    time: str = ""
    arena: str = ""
    sources: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)   # corners / attacks / shots
    home: str = ""           # canonical names, filled in by KnowledgeBase
    away: str = ""
    home_key: str = ""
    away_key: str = ""

    @property
    def played(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def winner(self) -> Optional[str]:
        if not self.played or self.home_goals == self.away_goals:
            return None
        return self.home if self.home_goals > self.away_goals else self.away

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat() if self.date else None,
            "competition": self.competition, "season": self.season, "round": self.round,
            "home_team": self.home, "away_team": self.away,
            "home_goals": self.home_goals, "away_goals": self.away_goals,
            "arena": self.arena, "stats": self.stats, "sources": self.sources,
        }


@dataclass
class Player:
    id: int
    name: str
    age: Optional[int]
    nationality: str
    overall: int
    potential: Optional[int]
    club: str
    position: str
    jersey: Optional[int]
    height: str
    weight: str
    value: str
    wage: str
    foot: str
    skills: dict

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _rows(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh)


def _split_dt(text: str):
    text = (text or "").strip()
    return parse_date(text), (text[11:16] if len(text) > 10 else "")


def load_brasileirao(d: Path = DATA_DIR):
    src = "Brasileirao_Matches.csv"
    for r in _rows(d / src):
        date, time = _split_dt(r["datetime"])
        yield Match(SERIE_A, int(r["season"]), date, r["home_team"], r["away_team"],
                    _int(r["home_goal"]), _int(r["away_goal"]), round=r["round"], time=time,
                    sources=[src])


def load_cup(d: Path = DATA_DIR):
    src = "Brazilian_Cup_Matches.csv"
    for r in _rows(d / src):
        date, time = _split_dt(r["datetime"])
        yield Match(COPA_BR, int(r["season"]), date, r["home_team"], r["away_team"],
                    _int(r["home_goal"]), _int(r["away_goal"]), round=r["round"], time=time,
                    sources=[src])


def load_libertadores(d: Path = DATA_DIR):
    src = "Libertadores_Matches.csv"
    for r in _rows(d / src):
        season = _int(r["season"])
        if season is None:
            continue  # placeholder row without date/season
        date, time = _split_dt(r["datetime"])
        yield Match(LIBERTADORES, season, date, r["home_team"].strip(), r["away_team"].strip(),
                    _int(r["home_goal"]), _int(r["away_goal"]), round=r["stage"], time=time,
                    sources=[src])


def load_historical(d: Path = DATA_DIR):
    src = "novo_campeonato_brasileiro.csv"
    for r in _rows(d / src):
        yield Match(SERIE_A, int(r["Ano"]), parse_date(r["Data"]), r["Equipe_mandante"],
                    r["Equipe_visitante"], _int(r["Gols_mandante"]), _int(r["Gols_visitante"]),
                    round=r["Rodada"], arena=r["Arena"].strip(), sources=[src])


_TOURNAMENTS = {"Serie A": SERIE_A, "Serie B": SERIE_B, "Serie C": SERIE_C, "Copa do Brasil": COPA_BR}
_STAT_COLS = ["home_corner", "away_corner", "home_attack", "away_attack", "home_shots",
              "away_shots", "total_corners"]


def load_extended(d: Path = DATA_DIR):
    src = "BR-Football-Dataset.csv"
    for r in _rows(d / src):
        date = parse_date(r["date"])
        comp = _TOURNAMENTS.get(r["tournament"], r["tournament"])
        # League seasons follow the calendar year; the 2020 season ran into early 2021.
        season = date.year - 1 if comp != COPA_BR and date.month <= 2 else date.year
        stats = {c: _int(r[c]) for c in _STAT_COLS if _int(r.get(c)) is not None}
        for c in ("ht_result", "at_result"):
            if r.get(c):
                stats[c] = r[c]
        yield Match(comp, season, date, r["home"], r["away"], _int(r["home_goal"]),
                    _int(r["away_goal"]), time=r["time"][:5], stats=stats, sources=[src])


_SKILL_START, _SKILL_END = "Crossing", "GKReflexes"


def load_players(d: Path = DATA_DIR):
    for r in _rows(d / "fifa_data.csv"):
        cols = list(r.keys())
        i, j = cols.index(_SKILL_START), cols.index(_SKILL_END)
        skills = {c: _int(r[c]) for c in cols[i:j + 1] if _int(r[c]) is not None}
        yield Player(int(r["ID"]), r["Name"], _int(r["Age"]), r["Nationality"],
                     _int(r["Overall"]) or 0, _int(r["Potential"]), r["Club"], r["Position"],
                     _int(r["Jersey Number"]), r["Height"], r["Weight"], r["Value"], r["Wage"],
                     r["Preferred Foot"], skills)
