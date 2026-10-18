"""Load the six Kaggle CSV files into Match and Player records.

Each source has its own column layout; every loader maps its rows onto the
shared `Match` model. Files overlap (e.g. Brasileirão 2012-2019 appears in the
2003-2019 file and the current file), so `load_matches` selects one source per
competition and season. See its docstring.
"""

import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from .dates import parse_date
from .models import Match, Player
from .normalize import parse_team

SERIES_A = "Brasileirão Série A"
SERIES_B = "Brasileirão Série B"
SERIES_C = "Brasileirão Série C"
CUP = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

BRASILEIRAO_FILE = "Brasileirao_Matches.csv"
CUP_FILE = "Brazilian_Cup_Matches.csv"
LIBERTADORES_FILE = "Libertadores_Matches.csv"
HISTORICAL_FILE = "novo_campeonato_brasileiro.csv"
EXTENDED_FILE = "BR-Football-Dataset.csv"
FIFA_FILE = "fifa_data.csv"

_TOURNAMENT_NAMES = {
    "serie a": SERIES_A,
    "serie b": SERIES_B,
    "serie c": SERIES_C,
    "copa do brasil": CUP,
}


def _read_rows(path: Path) -> Iterable[dict]:
    # utf-8-sig tolerates the BOM found at the start of fifa_data.csv.
    with path.open(newline="", encoding="utf-8-sig") as handle:
        yield from csv.DictReader(handle)


def _int(value) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _to_match(
    *,
    played_on,
    competition: str,
    season,
    home: str,
    away: str,
    home_goals,
    away_goals,
    home_state=None,
    away_state=None,
    stage=None,
    source: str,
) -> Optional[Match]:
    """Build a Match, or None when the row lacks a usable date or score."""
    day = parse_date(played_on)
    hg, ag = _int(home_goals), _int(away_goals)
    if day is None or hg is None or ag is None or not home or not away:
        return None
    season_year = _int(season) or day.year
    return Match(
        played_on=day,
        competition=competition,
        season=season_year,
        home=parse_team(home, home_state),
        away=parse_team(away, away_state),
        home_goals=hg,
        away_goals=ag,
        round_or_stage=stage or None,
        source=source,
    )


def load_brasileirao(path: Path) -> List[Match]:
    matches = []
    for row in _read_rows(path):
        match = _to_match(
            played_on=row["datetime"],
            competition=SERIES_A,
            season=row["season"],
            home=row["home_team"],
            away=row["away_team"],
            home_state=row.get("home_team_state"),
            away_state=row.get("away_team_state"),
            home_goals=row["home_goal"],
            away_goals=row["away_goal"],
            stage=f"Round {row['round']}" if row.get("round") else None,
            source=BRASILEIRAO_FILE,
        )
        if match:
            matches.append(match)
    return matches


def load_cup(path: Path) -> List[Match]:
    matches = []
    for row in _read_rows(path):
        match = _to_match(
            played_on=row["datetime"],
            competition=CUP,
            season=row["season"],
            home=row["home_team"],
            away=row["away_team"],
            home_goals=row["home_goal"],
            away_goals=row["away_goal"],
            stage=f"Round {row['round']}" if row.get("round") else None,
            source=CUP_FILE,
        )
        if match:
            matches.append(match)
    return matches


def load_libertadores(path: Path) -> List[Match]:
    matches = []
    for row in _read_rows(path):
        match = _to_match(
            played_on=row["datetime"],
            competition=LIBERTADORES,
            season=row["season"],
            home=row["home_team"],
            away=row["away_team"],
            home_goals=row["home_goal"],
            away_goals=row["away_goal"],
            stage=row.get("stage"),
            source=LIBERTADORES_FILE,
        )
        if match:
            matches.append(match)
    return matches


def load_historical(path: Path) -> List[Match]:
    matches = []
    for row in _read_rows(path):
        match = _to_match(
            played_on=row["Data"],
            competition=SERIES_A,
            season=row["Ano"],
            home=row["Equipe_mandante"],
            away=row["Equipe_visitante"],
            home_state=row.get("Mandante_UF"),
            away_state=row.get("Visitante_UF"),
            home_goals=row["Gols_mandante"],
            away_goals=row["Gols_visitante"],
            stage=f"Round {row['Rodada']}" if row.get("Rodada") else None,
            source=HISTORICAL_FILE,
        )
        if match:
            matches.append(match)
    return matches


def load_extended(path: Path) -> List[Match]:
    matches = []
    for row in _read_rows(path):
        competition = _TOURNAMENT_NAMES.get(row["tournament"].strip().lower(), row["tournament"])
        match = _to_match(
            played_on=row["date"],
            competition=competition,
            season=None,
            home=row["home"],
            away=row["away"],
            home_goals=row["home_goal"],
            away_goals=row["away_goal"],
            source=EXTENDED_FILE,
        )
        if match:
            matches.append(match)
    return matches


MATCH_SOURCES: List[tuple] = [
    (BRASILEIRAO_FILE, load_brasileirao),
    (CUP_FILE, load_cup),
    (LIBERTADORES_FILE, load_libertadores),
    (HISTORICAL_FILE, load_historical),
    (EXTENDED_FILE, load_extended),
]


def load_matches(data_dir: Path, sources: Optional[List[tuple]] = None) -> List[Match]:
    """Load every match file and keep one source per (competition, season).

    The files overlap heavily but disagree on dates, club spellings and even
    row counts (e.g. the 2021 Brasileirão appears with 380 rows in one file and
    491 in another, and 2022 is only partly covered by one of them). Matching
    individual fixtures across files is unreliable, so for each competition and
    season we keep the source with the most rows; ties go to the earlier file.
    """
    by_group: Dict[tuple, Dict[str, List[Match]]] = defaultdict(lambda: defaultdict(list))
    for filename, loader in (sources or MATCH_SOURCES):
        for match in loader(Path(data_dir) / filename):
            by_group[(match.competition, match.season)][filename].append(match)
    result: List[Match] = []
    for per_source in by_group.values():
        result.extend(max(per_source.values(), key=len))
    return result


def load_players(path: Path) -> List[Player]:
    players = []
    for row in _read_rows(path):
        players.append(
            Player(
                player_id=_int(row.get("ID")) or 0,
                name=(row.get("Name") or "").strip(),
                age=_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=_int(row.get("Overall")),
                potential=_int(row.get("Potential")),
                club=(row.get("Club") or "").strip(),
                position=(row.get("Position") or "").strip(),
                value=(row.get("Value") or "").strip(),
                wage=(row.get("Wage") or "").strip(),
                height=(row.get("Height") or "").strip(),
                weight=(row.get("Weight") or "").strip(),
                preferred_foot=(row.get("Preferred Foot") or "").strip(),
                jersey_number=_int(row.get("Jersey Number")),
            )
        )
    return players
