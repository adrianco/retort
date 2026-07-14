"""Load the provided CSV datasets into the in-memory domain models.

Each loader is tolerant of missing columns and malformed rows so that small
test fixtures (a handful of hand-written rows) load through exactly the same
code path as the full Kaggle datasets.

Only files that are actually present in ``data_dir`` are loaded, which is what
lets acceptance tests point the server at a temporary directory containing just
the fixtures a given scenario needs.
"""

from __future__ import annotations

import csv
import os
from typing import Iterable

from .models import Match, Player
from .normalize import (
    canonical_competition,
    clean_team_name,
    parse_date,
    team_key,
    text_key,
)

_LEAGUE_COMPETITIONS = {
    "Brasileirão",
    "Brasileirão Série B",
    "Brasileirão Série C",
}


def _to_int(value) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", ""}:
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def _open(path: str):
    # utf-8-sig transparently strips a BOM if present (fifa_data.csv has one).
    return open(path, newline="", encoding="utf-8-sig")


def _make_match(
    competition: str,
    home_raw: str,
    away_raw: str,
    home_goal,
    away_goal,
    *,
    season=None,
    raw_date=None,
    round_=None,
    stage=None,
    source="",
    stats=None,
) -> Match:
    competition = canonical_competition(competition)
    ctype = "league" if competition in _LEAGUE_COMPETITIONS else "cup"
    return Match(
        competition=competition,
        competition_type=ctype,
        home_team=clean_team_name(home_raw),
        away_team=clean_team_name(away_raw),
        home_goal=_to_int(home_goal),
        away_goal=_to_int(away_goal),
        season=_to_int(season),
        date=parse_date(raw_date),
        round=str(round_).strip() if round_ not in (None, "") else None,
        stage=str(stage).strip() if stage not in (None, "") else None,
        home_team_raw=str(home_raw).strip(),
        away_team_raw=str(away_raw).strip(),
        home_key=team_key(home_raw),
        away_key=team_key(away_raw),
        source=source,
        stats=stats or {},
    )


def _load_brasileirao(path: str) -> Iterable[Match]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            yield _make_match(
                "Brasileirão",
                row.get("home_team"),
                row.get("away_team"),
                row.get("home_goal"),
                row.get("away_goal"),
                season=row.get("season"),
                raw_date=row.get("datetime"),
                round_=row.get("round"),
                source=os.path.basename(path),
            )


def _load_cup(path: str) -> Iterable[Match]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            yield _make_match(
                "Copa do Brasil",
                row.get("home_team"),
                row.get("away_team"),
                row.get("home_goal"),
                row.get("away_goal"),
                season=row.get("season"),
                raw_date=row.get("datetime"),
                round_=row.get("round"),
                source=os.path.basename(path),
            )


def _load_libertadores(path: str) -> Iterable[Match]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            yield _make_match(
                "Copa Libertadores",
                row.get("home_team"),
                row.get("away_team"),
                row.get("home_goal"),
                row.get("away_goal"),
                season=row.get("season"),
                raw_date=row.get("datetime"),
                stage=row.get("stage"),
                source=os.path.basename(path),
            )


def _load_historical(path: str) -> Iterable[Match]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            yield _make_match(
                "Brasileirão",
                row.get("Equipe_mandante"),
                row.get("Equipe_visitante"),
                row.get("Gols_mandante"),
                row.get("Gols_visitante"),
                season=row.get("Ano"),
                raw_date=row.get("Data"),
                round_=row.get("Rodada"),
                stage=row.get("Arena"),
                source=os.path.basename(path),
            )


def _load_extended(path: str) -> Iterable[Match]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            d = parse_date(row.get("date"))
            stats = {
                "home_corner": _to_int(row.get("home_corner")),
                "away_corner": _to_int(row.get("away_corner")),
                "home_shots": _to_int(row.get("home_shots")),
                "away_shots": _to_int(row.get("away_shots")),
                "total_corners": _to_int(row.get("total_corners")),
            }
            yield _make_match(
                row.get("tournament"),
                row.get("home"),
                row.get("away"),
                row.get("home_goal"),
                row.get("away_goal"),
                season=d.year if d else None,
                raw_date=row.get("date"),
                source=os.path.basename(path),
                stats=stats,
            )


def _load_players(path: str) -> Iterable[Player]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            club = (row.get("Club") or "").strip()
            nationality = (row.get("Nationality") or "").strip()
            position = (row.get("Position") or "").strip()
            yield Player(
                id=_to_int(row.get("ID")),
                name=name,
                nationality=nationality,
                overall=_to_int(row.get("Overall")),
                potential=_to_int(row.get("Potential")),
                club=club,
                position=position,
                age=_to_int(row.get("Age")),
                jersey_number=_to_int(row.get("Jersey Number")),
                height=(row.get("Height") or "").strip(),
                weight=(row.get("Weight") or "").strip(),
                name_key=text_key(name),
                club_key=text_key(club),
                nationality_key=text_key(nationality),
                position_key=text_key(position),
            )


# Map known filenames to their loader. Unknown files are ignored.
_MATCH_LOADERS = {
    "Brasileirao_Matches.csv": _load_brasileirao,
    "Brazilian_Cup_Matches.csv": _load_cup,
    "Libertadores_Matches.csv": _load_libertadores,
    "novo_campeonato_brasileiro.csv": _load_historical,
    "BR-Football-Dataset.csv": _load_extended,
}
_PLAYER_LOADERS = {
    "fifa_data.csv": _load_players,
}


def _dedup_key(match: Match):
    """Key used to drop duplicate matches that appear across overlapping files.

    League fixtures occur once per ordered (home, away) pair per season, so for
    leagues the date is excluded (the same fixture may carry a slightly
    different kickoff date between sources). Cup/continental ties can repeat, so
    those keep the date in the key.
    """
    base = (match.competition, match.season, match.home_key, match.away_key)
    if match.competition_type == "cup":
        return base + (match.date.isoformat() if match.date else None,)
    return base


def load_dataset(data_dir: str):
    """Load all recognised CSV files found under ``data_dir``.

    Returns a tuple ``(matches, players)``.
    """
    matches: list[Match] = []
    players: list[Player] = []
    seen: set = set()

    if not data_dir or not os.path.isdir(data_dir):
        return matches, players

    filenames = set(os.listdir(data_dir))
    for filename, loader in _MATCH_LOADERS.items():
        if filename not in filenames:
            continue
        for match in loader(os.path.join(data_dir, filename)):
            key = _dedup_key(match)
            if key in seen:
                continue
            seen.add(key)
            matches.append(match)

    for filename, loader in _PLAYER_LOADERS.items():
        if filename not in filenames:
            continue
        players.extend(loader(os.path.join(data_dir, filename)))

    return matches, players
