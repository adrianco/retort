"""Load the Kaggle CSV files into normalised match and player records.

Six files are read from ``data/kaggle``. The match files overlap (the 2012+
Brasileirão file and the 2003-2019 historical file share seasons, and the
BR-Football file repeats some Copa do Brasil games), so matches are
de-duplicated on date, competition, both clubs and the score.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Iterator, Optional

from .normalize import TeamRef, name_tokens, parse_date, parse_team

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

BRASILEIRAO_FILE = "Brasileirao_Matches.csv"
CUP_FILE = "Brazilian_Cup_Matches.csv"
LIBERTADORES_FILE = "Libertadores_Matches.csv"
BR_FOOTBALL_FILE = "BR-Football-Dataset.csv"
HISTORICAL_FILE = "novo_campeonato_brasileiro.csv"
FIFA_FILE = "fifa_data.csv"

# BR-Football 'tournament' values -> canonical competition keys.
_BR_FOOTBALL_COMPETITIONS = {
    "Serie A": "brasileirao_a",
    "Serie B": "brasileirao_b",
    "Serie C": "brasileirao_c",
    "Copa do Brasil": "copa_do_brasil",
}


@dataclass(frozen=True)
class Match:
    date: date
    competition: str  # key into normalize.COMPETITION_NAMES
    season: int
    home: TeamRef
    away: TeamRef
    home_goals: int
    away_goals: int
    stage: Optional[str] = None
    source: str = ""

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def goal_margin(self) -> int:
        return abs(self.home_goals - self.away_goals)

    @property
    def is_draw(self) -> bool:
        return self.home_goals == self.away_goals



@dataclass(frozen=True)
class Player:
    id: int
    name: str
    age: int
    nationality: str
    overall: int
    potential: int
    club: str
    position: str
    jersey_number: Optional[int]


@dataclass
class Dataset:
    matches: list[Match]
    players: list[Player]
    skipped_rows: int = 0


class _RowSkipped(Exception):
    """A CSV row that cannot be parsed; it is counted and dropped."""


def _read_rows(path: Path) -> Iterator[dict]:
    # utf-8-sig strips the BOM that the FIFA file starts with.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def _goals(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        raise _RowSkipped from None


def _make_match(*, competition: str, date_value: str, home: str, away: str,
                home_goals: str, away_goals: str, season: str, source: str,
                home_state: Optional[str] = None, away_state: Optional[str] = None,
                stage: Optional[str] = None) -> Match:
    try:
        parsed_date = parse_date(date_value)
        parsed_season = int(float(season)) if season else parsed_date.year
    except ValueError:
        raise _RowSkipped from None
    return Match(
        date=parsed_date,
        competition=competition,
        season=parsed_season,
        home=parse_team(home, home_state),
        away=parse_team(away, away_state),
        home_goals=_goals(home_goals),
        away_goals=_goals(away_goals),
        stage=stage,
        source=source,
    )


def _iter_matches(data_dir: Path, counter: list[int]) -> Iterator[Match]:
    """Yield matches from every source file, in priority order."""
    sources = [
        (BRASILEIRAO_FILE, _brasileirao_row),
        (CUP_FILE, _cup_row),
        (LIBERTADORES_FILE, _libertadores_row),
        (BR_FOOTBALL_FILE, _br_football_row),
        (HISTORICAL_FILE, _historical_row),
    ]
    for filename, convert in sources:
        for row in _read_rows(data_dir / filename):
            try:
                yield convert(row, filename)
            except _RowSkipped:
                counter[0] += 1


def _brasileirao_row(row: dict, source: str) -> Match:
    return _make_match(
        competition="brasileirao_a", source=source,
        date_value=row["datetime"], home=row["home_team"], away=row["away_team"],
        home_goals=row["home_goal"], away_goals=row["away_goal"], season=row["season"],
        home_state=row["home_team_state"], away_state=row["away_team_state"],
        stage=f"Round {row['round']}",
    )


def _cup_row(row: dict, source: str) -> Match:
    return _make_match(
        competition="copa_do_brasil", source=source,
        date_value=row["datetime"], home=row["home_team"], away=row["away_team"],
        home_goals=row["home_goal"], away_goals=row["away_goal"], season=row["season"],
        stage=f"Round {row['round']}",
    )


def _libertadores_row(row: dict, source: str) -> Match:
    return _make_match(
        competition="libertadores", source=source,
        date_value=row["datetime"], home=row["home_team"], away=row["away_team"],
        home_goals=row["home_goal"], away_goals=row["away_goal"], season=row["season"],
        stage=row["stage"] or None,
    )


def _br_football_row(row: dict, source: str) -> Match:
    competition = _BR_FOOTBALL_COMPETITIONS.get(row["tournament"])
    if competition is None:
        raise _RowSkipped
    return _make_match(
        competition=competition, source=source,
        date_value=row["date"], home=row["home"], away=row["away"],
        home_goals=row["home_goal"], away_goals=row["away_goal"], season="",
    )


def _historical_row(row: dict, source: str) -> Match:
    return _make_match(
        competition="brasileirao_a", source=source,
        date_value=row["Data"], home=row["Equipe_mandante"], away=row["Equipe_visitante"],
        home_goals=row["Gols_mandante"], away_goals=row["Gols_visitante"], season=row["Ano"],
        home_state=row["Mandante_UF"], away_state=row["Visitante_UF"],
        stage=f"Round {row['Rodada']}",
    )


def _same_club(a: TeamRef, b: TeamRef) -> bool:
    return bool(name_tokens(a.base) & name_tokens(b.base))


def _same_match(a: Match, b: Match) -> bool:
    """Two rows are one game when competition and score agree, the dates are within
    a day of each other, and the clubs overlap.

    Sources spell clubs differently ("Vasco" / "Vasco da Gama-RJ") and some date a
    game one day apart, so club names are compared on their significant words and
    the date allows one day of drift. Two different games with the same score in the
    same competition, on adjacent days, involving the same clubs do not occur here.
    """
    if (a.competition, a.home_goals, a.away_goals) != (b.competition, b.home_goals, b.away_goals):
        return False
    if abs((a.date - b.date).days) > 1:
        return False
    return ((_same_club(a.home, b.home) and _same_club(a.away, b.away)) or
            (_same_club(a.home, b.away) and _same_club(a.away, b.home)))


def _dedupe(matches: Iterable[Match]) -> list[Match]:
    """Keep the first occurrence of each game; later sources only add new games.

    Candidates are bucketed by (competition, score) first so the date and club
    comparison only runs on a handful of rows per bucket.
    """
    buckets: dict[tuple, list[Match]] = defaultdict(list)
    unique: list[Match] = []
    for match in matches:
        key = (match.competition, match.home_goals, match.away_goals)
        if any(_same_match(match, kept) for kept in buckets[key]):
            continue
        buckets[key].append(match)
        unique.append(match)
    return unique


def _optional_int(value: str) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _load_players(path: Path) -> Iterator[Player]:
    for row in _read_rows(path):
        try:
            yield Player(
                id=int(row["ID"]),
                name=row["Name"].strip(),
                age=int(row["Age"]),
                nationality=row["Nationality"].strip(),
                overall=int(row["Overall"]),
                potential=int(row["Potential"]),
                club=row["Club"].strip(),
                position=row["Position"].strip(),
                jersey_number=_optional_int(row["Jersey Number"]),
            )
        except (KeyError, TypeError, ValueError):
            continue


def load_dataset(data_dir: Path | str = DEFAULT_DATA_DIR) -> Dataset:
    """Load every match file and the FIFA player file from ``data_dir``."""
    data_dir = Path(data_dir)
    skipped = [0]
    matches = _dedupe(_iter_matches(data_dir, skipped))
    matches.sort(key=lambda m: (m.date, m.home.base, m.away.base))
    players = list(_load_players(data_dir / FIFA_FILE))
    return Dataset(
        matches=matches,
        players=players,
        skipped_rows=skipped[0],
    )
