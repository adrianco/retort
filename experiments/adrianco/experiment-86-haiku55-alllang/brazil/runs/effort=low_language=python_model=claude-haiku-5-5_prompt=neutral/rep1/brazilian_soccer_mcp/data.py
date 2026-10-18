# Context: CSV loaders that turn the six Kaggle datasets in data/kaggle/ into unified Match and
# Player records. Match files are merged and de-duplicated (Brasileirão 2012-2019 appears in more
# than one file). Everything is read as UTF-8 (with BOM tolerance) and standard library only.

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from .names import display_name, parse_team, resolve_competition

FILE_BRASILEIRAO = "Brasileirao_Matches.csv"
FILE_CUP = "Brazilian_Cup_Matches.csv"
FILE_LIBERTADORES = "Libertadores_Matches.csv"
FILE_BR_FOOTBALL = "BR-Football-Dataset.csv"
FILE_HISTORICAL = "novo_campeonato_brasileiro.csv"
FILE_FIFA = "fifa_data.csv"

BRASILEIRAO_LABEL = "Brasileirão Série A"

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y")


@dataclass(frozen=True)
class Team:
    key: str
    state: str | None
    name: str

    @property
    def identity(self) -> tuple[str, str | None]:
        return (self.key, self.state)

    @property
    def label(self) -> str:
        """Name shown to users; keeps the state so 'Atlético-MG' and 'Athletico-PR' stay distinct."""
        return f"{self.name} ({self.state})" if self.state else self.name


@dataclass(frozen=True)
class Match:
    played_on: date
    competition: str
    season: int
    stage: str
    home: Team
    away: Team
    home_goals: int
    away_goals: int
    source: str

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def goal_margin(self) -> int:
        return abs(self.home_goals - self.away_goals)


@dataclass(frozen=True)
class Player:
    player_id: str
    name: str
    age: int
    nationality: str
    overall: int
    potential: int
    club: str
    position: str
    jersey_number: str


def parse_date(text: str) -> date:
    text = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date: {text!r}")


def _int(text: str) -> int:
    return int(float(text))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _team(raw: str, state_hint: str | None = None) -> Team:
    key, state = parse_team(raw)
    return Team(key=key, state=(state_hint or state or None), name=display_name(raw))


def _score(text: str | None) -> int:
    """Goals as int; raises ValueError for blank or 'NA' cells."""
    return _int(text or "")


def _load_rows(path: Path, build: Callable[[dict[str, str]], Match]) -> list[Match]:
    """Build a Match per row, skipping rows with a missing or malformed date, season or score."""
    matches = []
    for row in _read_rows(path):
        try:
            matches.append(build(row))
        except ValueError:
            continue
    return matches


def _build_brasileirao(row: dict[str, str]) -> Match:
    return Match(
        played_on=parse_date(row["datetime"]),
        competition=BRASILEIRAO_LABEL,
        season=_int(row["season"]),
        stage=f"Round {row['round']}",
        home=_team(row["home_team"], row.get("home_team_state")),
        away=_team(row["away_team"], row.get("away_team_state")),
        home_goals=_score(row["home_goal"]),
        away_goals=_score(row["away_goal"]),
        source=FILE_BRASILEIRAO,
    )


def _build_cup(row: dict[str, str]) -> Match:
    return Match(
        played_on=parse_date(row["datetime"]),
        competition="Copa do Brasil",
        season=_int(row["season"]),
        stage=f"Round {row['round']}",
        home=_team(row["home_team"]),
        away=_team(row["away_team"]),
        home_goals=_score(row["home_goal"]),
        away_goals=_score(row["away_goal"]),
        source=FILE_CUP,
    )


def _build_libertadores(row: dict[str, str]) -> Match:
    return Match(
        played_on=parse_date(row["datetime"]),
        competition="Copa Libertadores",
        season=_int(row["season"]),
        stage=row["stage"].strip(),
        home=_team(row["home_team"]),
        away=_team(row["away_team"]),
        home_goals=_score(row["home_goal"]),
        away_goals=_score(row["away_goal"]),
        source=FILE_LIBERTADORES,
    )


def _build_br_football(row: dict[str, str]) -> Match:
    played_on = parse_date(row["date"])
    return Match(
        played_on=played_on,
        competition=resolve_competition(row["tournament"]) or row["tournament"],
        season=played_on.year,
        stage="",
        home=_team(row["home"]),
        away=_team(row["away"]),
        home_goals=_score(row["home_goal"]),
        away_goals=_score(row["away_goal"]),
        source=FILE_BR_FOOTBALL,
    )


def _build_historical(row: dict[str, str]) -> Match:
    return Match(
        played_on=parse_date(row["Data"]),
        competition=BRASILEIRAO_LABEL,
        season=_int(row["Ano"]),
        stage=f"Round {row['Rodada']}",
        home=_team(row["Equipe_mandante"], row.get("Mandante_UF") or None),
        away=_team(row["Equipe_visitante"], row.get("Visitante_UF") or None),
        home_goals=_score(row["Gols_mandante"]),
        away_goals=_score(row["Gols_visitante"]),
        source=FILE_HISTORICAL,
    )


def load_matches(data_dir: Path) -> list[Match]:
    """Load every match file, using one source per competition and season.

    Several files overlap (Brasileirão 2012-2019 is in three of them) and they spell club names
    differently, so mixing rows from different files would double count fixtures. For each
    (competition, season) the first source in priority order that has rows is used.
    """
    builders = (
        (FILE_BRASILEIRAO, _build_brasileirao),
        (FILE_HISTORICAL, _build_historical),
        (FILE_CUP, _build_cup),
        (FILE_LIBERTADORES, _build_libertadores),
        (FILE_BR_FOOTBALL, _build_br_football),
    )
    chosen: dict[tuple[str, int], str] = {}
    by_slot: dict[tuple[str, int, str], list[Match]] = defaultdict(list)
    for filename, build in builders:
        for match in _load_rows(data_dir / filename, build):
            slot = (match.competition, match.season)
            chosen.setdefault(slot, filename)
            by_slot[(match.competition, match.season, filename)].append(match)
    merged = [
        match
        for (competition, season, filename), matches in by_slot.items()
        if chosen[(competition, season)] == filename
        for match in matches
    ]
    merged.sort(key=lambda m: (m.played_on, m.competition, m.home.key))
    return merged


def load_players(data_dir: Path) -> list[Player]:
    players = []
    for row in _read_rows(data_dir / FILE_FIFA):
        players.append(
            Player(
                player_id=row["ID"],
                name=row["Name"],
                age=_int(row["Age"]),
                nationality=row["Nationality"],
                overall=_int(row["Overall"]),
                potential=_int(row["Potential"]),
                club=row["Club"],
                position=row["Position"],
                jersey_number=row["Jersey Number"],
            )
        )
    return players
