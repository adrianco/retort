"""CSV loaders for the six Kaggle datasets.

All loaders normalize into two dataclasses, `Match` and `Player`, so the
query layer can treat them uniformly.  The loader is stdlib-only (no
pandas) so the package is installable without extra dependencies; the
total row count (~24k matches + 18k players) comfortably fits in memory.

Date parsing handles three formats seen in the data:
    "2023-09-24"         (ISO date)
    "29/03/2003"         (Brazilian d/m/Y)
    "2012-05-19 18:30:00"(ISO datetime)
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable

from .team_utils import normalize_team_name

# Canonical competition labels.
BRASILEIRAO = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

COMPETITIONS = (BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES)


def _canonical_competition(raw: str) -> str:
    """Map dataset-specific competition labels onto canonical names."""
    if not raw:
        return "Other"
    r = raw.strip().lower()
    if r in {"serie a", "série a", "brasileirao", "brasileirão", "brasileirao serie a", "brasileirão série a"}:
        return BRASILEIRAO
    if r in {"serie b", "série b"}:
        return BRASILEIRAO_B
    if r in {"serie c", "série c"}:
        return BRASILEIRAO_C
    if "copa do brasil" in r:
        return COPA_DO_BRASIL
    if "libertadores" in r:
        return LIBERTADORES
    return raw.strip()


@dataclass
class Match:
    """One match, normalized across all five match CSVs."""

    competition: str
    home_team: str
    away_team: str
    home_goal: int | None
    away_goal: int | None
    season: int | None
    match_date: date | None
    round: str | None = None
    stage: str | None = None
    arena: str | None = None
    home_state: str | None = None
    away_state: str | None = None
    # Extended stats from BR-Football-Dataset only.
    extras: dict = field(default_factory=dict)
    source: str = ""

    # Derived.
    home_norm: str = ""
    away_norm: str = ""

    def __post_init__(self) -> None:
        self.home_norm = normalize_team_name(self.home_team)
        self.away_norm = normalize_team_name(self.away_team)

    @property
    def winner(self) -> str | None:
        """'home', 'away', 'draw', or None if scores unknown."""
        if self.home_goal is None or self.away_goal is None:
            return None
        if self.home_goal > self.away_goal:
            return "home"
        if self.away_goal > self.home_goal:
            return "away"
        return "draw"

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "date": self.match_date.isoformat() if self.match_date else None,
            "season": self.season,
            "round": self.round,
            "stage": self.stage,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "arena": self.arena,
            "source": self.source,
        }


@dataclass
class Player:
    """One FIFA player record (subset of the 89 columns we surface)."""

    player_id: int | None
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    height: str
    weight: str
    preferred_foot: str
    value: str
    wage: str

    club_norm: str = ""

    def __post_init__(self) -> None:
        self.club_norm = normalize_team_name(self.club)

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
            "preferred_foot": self.preferred_foot,
            "value": self.value,
            "wage": self.wage,
        }


@dataclass
class Dataset:
    matches: list[Match]
    players: list[Player]

    # Indexes for fast lookup.
    matches_by_norm_team: dict[str, list[Match]] = field(default_factory=dict)
    players_by_norm_club: dict[str, list[Player]] = field(default_factory=dict)

    def build_indexes(self) -> "Dataset":
        for m in self.matches:
            if m.home_norm:
                self.matches_by_norm_team.setdefault(m.home_norm, []).append(m)
            if m.away_norm and m.away_norm != m.home_norm:
                self.matches_by_norm_team.setdefault(m.away_norm, []).append(m)
        for p in self.players:
            if p.club_norm:
                self.players_by_norm_club.setdefault(p.club_norm, []).append(p)
        return self


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none"}:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    fmts = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y")
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _read_csv(path: str, encoding: str = "utf-8") -> Iterable[dict]:
    with open(path, newline="", encoding=encoding) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield row


def load_brasileirao(path: str) -> list[Match]:
    out = []
    for row in _read_csv(path):
        out.append(
            Match(
                competition=BRASILEIRAO,
                home_team=row["home_team"].strip(),
                away_team=row["away_team"].strip(),
                home_goal=_parse_int(row.get("home_goal")),
                away_goal=_parse_int(row.get("away_goal")),
                season=_parse_int(row.get("season")),
                match_date=_parse_date(row.get("datetime")),
                round=row.get("round") or None,
                home_state=row.get("home_team_state") or None,
                away_state=row.get("away_team_state") or None,
                source=os.path.basename(path),
            )
        )
    return out


def load_copa_do_brasil(path: str) -> list[Match]:
    out = []
    for row in _read_csv(path):
        out.append(
            Match(
                competition=COPA_DO_BRASIL,
                home_team=row["home_team"].strip(),
                away_team=row["away_team"].strip(),
                home_goal=_parse_int(row.get("home_goal")),
                away_goal=_parse_int(row.get("away_goal")),
                season=_parse_int(row.get("season")),
                match_date=_parse_date(row.get("datetime")),
                round=row.get("round") or None,
                source=os.path.basename(path),
            )
        )
    return out


def load_libertadores(path: str) -> list[Match]:
    out = []
    for row in _read_csv(path):
        out.append(
            Match(
                competition=LIBERTADORES,
                home_team=row["home_team"].strip(),
                away_team=row["away_team"].strip(),
                home_goal=_parse_int(row.get("home_goal")),
                away_goal=_parse_int(row.get("away_goal")),
                season=_parse_int(row.get("season")),
                match_date=_parse_date(row.get("datetime")),
                stage=row.get("stage") or None,
                source=os.path.basename(path),
            )
        )
    return out


def load_br_football(path: str) -> list[Match]:
    """Extended match-stats dataset (`BR-Football-Dataset.csv`)."""
    out = []
    for row in _read_csv(path):
        tournament = (row.get("tournament") or "").strip()
        out.append(
            Match(
                competition=_canonical_competition(tournament),
                home_team=(row.get("home") or "").strip(),
                away_team=(row.get("away") or "").strip(),
                home_goal=_parse_int(row.get("home_goal")),
                away_goal=_parse_int(row.get("away_goal")),
                season=_parse_date(row.get("date")).year if _parse_date(row.get("date")) else None,
                match_date=_parse_date(row.get("date")),
                extras={
                    "home_corner": _parse_int(row.get("home_corner")),
                    "away_corner": _parse_int(row.get("away_corner")),
                    "home_shots": _parse_int(row.get("home_shots")),
                    "away_shots": _parse_int(row.get("away_shots")),
                    "home_attack": _parse_int(row.get("home_attack")),
                    "away_attack": _parse_int(row.get("away_attack")),
                    "ht_result": row.get("ht_result"),
                    "at_result": row.get("at_result"),
                    "total_corners": _parse_int(row.get("total_corners")),
                    "time": row.get("time"),
                },
                source=os.path.basename(path),
            )
        )
    return out


def load_historical_brasileirao(path: str) -> list[Match]:
    """`novo_campeonato_brasileiro.csv`, the 2003-2019 Brasileirão archive."""
    out = []
    for row in _read_csv(path):
        out.append(
            Match(
                competition=BRASILEIRAO,
                home_team=(row.get("Equipe_mandante") or "").strip(),
                away_team=(row.get("Equipe_visitante") or "").strip(),
                home_goal=_parse_int(row.get("Gols_mandante")),
                away_goal=_parse_int(row.get("Gols_visitante")),
                season=_parse_int(row.get("Ano")),
                match_date=_parse_date(row.get("Data")),
                round=row.get("Rodada") or None,
                arena=row.get("Arena") or None,
                home_state=row.get("Mandante_UF") or None,
                away_state=row.get("Visitante_UF") or None,
                source=os.path.basename(path),
            )
        )
    return out


def load_players(path: str) -> list[Player]:
    out = []
    # `utf-8-sig` strips the BOM so the first column key is "" instead of ﻿.
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            out.append(
                Player(
                    player_id=_parse_int(row.get("ID")),
                    name=(row.get("Name") or "").strip(),
                    age=_parse_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip(),
                    overall=_parse_int(row.get("Overall")),
                    potential=_parse_int(row.get("Potential")),
                    club=(row.get("Club") or "").strip(),
                    position=(row.get("Position") or "").strip(),
                    jersey_number=_parse_int(row.get("Jersey Number")),
                    height=(row.get("Height") or "").strip(),
                    weight=(row.get("Weight") or "").strip(),
                    preferred_foot=(row.get("Preferred Foot") or "").strip(),
                    value=(row.get("Value") or "").strip(),
                    wage=(row.get("Wage") or "").strip(),
                )
            )
    return out


def _dedup_matches(matches: list[Match]) -> list[Match]:
    """Drop duplicates that arise from overlapping data sources.

    `Brasileirao_Matches.csv` (2012+), `novo_campeonato_brasileiro.csv`
    (2003-2019), and `BR-Football-Dataset.csv` (2014-2023) all overlap.
    Without dedup, queries like "Flamengo 2019 Brasileirão" return
    double or triple counts.

    The BR-Football dataset stamps matches with a UTC kickoff that is
    often one calendar day off from the other sources, so we cannot
    dedup on the date alone.  Instead we treat two matches as the same
    if they share (competition, season, home_team, away_team, scores)
    and the kickoff dates are within four days.

    The kept record is enriched with non-empty fields (extras, arena,
    stage, round, state) from the duplicates so no information is lost.
    """
    buckets: dict[tuple, list[Match]] = {}
    out: list[Match] = []
    for m in matches:
        if (
            not m.match_date
            or not m.home_norm
            or not m.away_norm
            or m.home_goal is None
            or m.away_goal is None
        ):
            out.append(m)
            continue
        key = (
            m.competition.lower(),
            m.season,
            m.home_norm,
            m.away_norm,
            m.home_goal,
            m.away_goal,
        )
        existing = buckets.setdefault(key, [])
        kept = None
        for prev in existing:
            if abs((m.match_date - prev.match_date).days) <= 4:
                kept = prev
                break
        if kept is None:
            existing.append(m)
            out.append(m)
            continue
        # Merge complementary fields into the kept match.
        if not kept.arena and m.arena:
            kept.arena = m.arena
        if not kept.round and m.round:
            kept.round = m.round
        if not kept.stage and m.stage:
            kept.stage = m.stage
        if not kept.home_state and m.home_state:
            kept.home_state = m.home_state
        if not kept.away_state and m.away_state:
            kept.away_state = m.away_state
        if m.extras:
            kept.extras = {**m.extras, **kept.extras}
    return out


def load_dataset(data_dir: str | None = None) -> Dataset:
    """Load every CSV in `data/kaggle/` into a single deduplicated `Dataset`."""
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "kaggle")
    data_dir = os.path.abspath(data_dir)

    matches: list[Match] = []
    matches += load_brasileirao(os.path.join(data_dir, "Brasileirao_Matches.csv"))
    matches += load_copa_do_brasil(os.path.join(data_dir, "Brazilian_Cup_Matches.csv"))
    matches += load_libertadores(os.path.join(data_dir, "Libertadores_Matches.csv"))
    matches += load_br_football(os.path.join(data_dir, "BR-Football-Dataset.csv"))
    matches += load_historical_brasileirao(
        os.path.join(data_dir, "novo_campeonato_brasileiro.csv")
    )

    matches = _dedup_matches(matches)
    players = load_players(os.path.join(data_dir, "fifa_data.csv"))

    return Dataset(matches=matches, players=players).build_indexes()
