"""
Context
=======
CSV loaders for the Brazilian Soccer MCP server.

Each of the six provided Kaggle files has a different schema; this module parses
all of them into the unified ``Match`` / ``Player`` domain records. Loading is
done with the standard-library ``csv`` module (no heavy dependencies) and is
tolerant of the data-quality issues called out in the spec: multiple date
formats, goals stored as ints / floats / strings, UTF-8 with a leading BOM, and
team-name variations (handled via ``normalize``).

Files are detected by name, so a data directory may contain any subset of the
six files (tests seed only what they need; production has all six).
"""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Optional

from .models import Match, Player
from .normalize import key, normalize_team

# Canonical competition labels. Several files cover the same competition under
# different names (e.g. "Serie A" == "Brasileirão"); canonicalising lets the
# loader de-duplicate matches that appear in more than one source file.
BRASILEIRAO = "Brasileirão"
# Named without the "Brasileirão" prefix so a substring query for the top flight
# ("Brasileirão") does not accidentally include the lower divisions.
BRASILEIRAO_B = "Série B"
BRASILEIRAO_C = "Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

# BR-Football "tournament" values -> canonical competition.
_TOURNAMENT_ALIASES = {
    "serie a": BRASILEIRAO,
    "serie b": BRASILEIRAO_B,
    "serie c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
    "copa libertadores": LIBERTADORES,
    "libertadores": LIBERTADORES,
}


def canonical_competition(raw: str) -> str:
    """Map a raw competition / tournament label onto a canonical name."""
    if not raw:
        return "Unknown"
    return _TOURNAMENT_ALIASES.get(key(raw), str(raw).strip())


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _parse_date(value) -> tuple[Optional[str], Optional[int]]:
    """Return ``(iso_date, year)`` for a raw date string in any known format."""
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None
    # Drop a trailing time component: "2012-05-19 18:30:00".
    head = text.split(" ")[0].split("T")[0]
    # Brazilian format DD/MM/YYYY.
    if "/" in head:
        parts = head.split("/")
        if len(parts) == 3:
            d, m, y = parts
            if len(y) == 4:
                return f"{y}-{int(m):02d}-{int(d):02d}", int(y)
    # ISO format YYYY-MM-DD.
    if "-" in head:
        parts = head.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            y, m, d = parts
            try:
                return f"{int(y):04d}-{int(m):02d}-{int(d):02d}", int(y)
            except ValueError:
                return None, None
    return None, None


def _rows(path: Path) -> Iterable[dict]:
    # utf-8-sig transparently strips a leading BOM (present in fifa_data.csv).
    with path.open("r", newline="", encoding="utf-8-sig") as fh:
        yield from csv.DictReader(fh)


def _load_brasileirao(path: Path) -> list[Match]:
    matches = []
    for row in _rows(path):
        iso, year = _parse_date(row.get("datetime"))
        matches.append(Match(
            competition=BRASILEIRAO,
            season=_to_int(row.get("season")) or year,
            date=iso,
            home_team=normalize_team(row.get("home_team")),
            away_team=normalize_team(row.get("away_team")),
            home_goal=_to_int(row.get("home_goal")),
            away_goal=_to_int(row.get("away_goal")),
            round=(str(row.get("round")).strip() or None) if row.get("round") else None,
        ))
    return matches


def _load_copa(path: Path) -> list[Match]:
    matches = []
    for row in _rows(path):
        iso, year = _parse_date(row.get("datetime"))
        matches.append(Match(
            competition=COPA_DO_BRASIL,
            season=_to_int(row.get("season")) or year,
            date=iso,
            home_team=normalize_team(row.get("home_team")),
            away_team=normalize_team(row.get("away_team")),
            home_goal=_to_int(row.get("home_goal")),
            away_goal=_to_int(row.get("away_goal")),
            round=(str(row.get("round")).strip() or None) if row.get("round") else None,
        ))
    return matches


def _load_libertadores(path: Path) -> list[Match]:
    matches = []
    for row in _rows(path):
        iso, year = _parse_date(row.get("datetime"))
        matches.append(Match(
            competition=LIBERTADORES,
            season=_to_int(row.get("season")) or year,
            date=iso,
            home_team=normalize_team(row.get("home_team")),
            away_team=normalize_team(row.get("away_team")),
            home_goal=_to_int(row.get("home_goal")),
            away_goal=_to_int(row.get("away_goal")),
            stage=(str(row.get("stage")).strip() or None) if row.get("stage") else None,
        ))
    return matches


def _load_br_football(path: Path) -> list[Match]:
    matches = []
    for row in _rows(path):
        iso, year = _parse_date(row.get("date"))
        matches.append(Match(
            competition=canonical_competition(row.get("tournament")),
            season=year,
            date=iso,
            home_team=normalize_team(row.get("home")),
            away_team=normalize_team(row.get("away")),
            home_goal=_to_int(row.get("home_goal")),
            away_goal=_to_int(row.get("away_goal")),
        ))
    return matches


def _load_historical(path: Path) -> list[Match]:
    matches = []
    for row in _rows(path):
        iso, year = _parse_date(row.get("Data"))
        matches.append(Match(
            competition=BRASILEIRAO,
            season=_to_int(row.get("Ano")) or year,
            date=iso,
            home_team=normalize_team(row.get("Equipe_mandante")),
            away_team=normalize_team(row.get("Equipe_visitante")),
            home_goal=_to_int(row.get("Gols_mandante")),
            away_goal=_to_int(row.get("Gols_visitante")),
            round=(str(row.get("Rodada")).strip() or None) if row.get("Rodada") else None,
        ))
    return matches


def _load_players(path: Path) -> list[Player]:
    players = []
    for row in _rows(path):
        name = (row.get("Name") or "").strip()
        if not name:
            continue
        players.append(Player(
            name=name,
            age=_to_int(row.get("Age")),
            nationality=(row.get("Nationality") or "").strip(),
            overall=_to_int(row.get("Overall")),
            potential=_to_int(row.get("Potential")),
            club=normalize_team(row.get("Club")) if row.get("Club") else "",
            position=(row.get("Position") or "").strip(),
        ))
    return players


_MATCH_FILES = {
    "Brasileirao_Matches.csv": _load_brasileirao,
    "Brazilian_Cup_Matches.csv": _load_copa,
    "Libertadores_Matches.csv": _load_libertadores,
    "BR-Football-Dataset.csv": _load_br_football,
    "novo_campeonato_brasileiro.csv": _load_historical,
}


def _select_primary_source(matches: list[Match]) -> list[Match]:
    """Resolve overlapping source files so each competition-season is consistent.

    Several files cover the same competition and years (e.g. Brasileirão Série A
    appears in three files), spelling teams differently. Unioning them would
    invent phantom fixtures (same game, two spellings) and inflate standings. So
    for each (competition, season) only the single source file contributing the
    most matches is kept — yielding one clean, internally-consistent record set
    per season while still drawing on whichever file covers each season best.
    """
    from collections import Counter, defaultdict

    groups: dict[tuple, list[Match]] = defaultdict(list)
    for m in matches:
        groups[(key(m.competition), m.season)].append(m)

    result: list[Match] = []
    for group in groups.values():
        counts = Counter(m.source for m in group)
        best = counts.most_common(1)[0][0]
        # Within the chosen source, keep one record per ordered pairing.
        seen = set()
        for m in group:
            if m.source != best:
                continue
            pairing = (key(m.home_team), key(m.away_team))
            if pairing in seen:
                continue
            seen.add(pairing)
            result.append(m)
    return result


def load_matches(data_dir: Path) -> list[Match]:
    matches: list[Match] = []
    for filename, parser in _MATCH_FILES.items():
        path = data_dir / filename
        if path.exists():
            matches.extend(
                replace(m, source=filename) for m in parser(path)
            )
    return _select_primary_source(matches)


def load_players(data_dir: Path) -> list[Player]:
    path = data_dir / "fifa_data.csv"
    return _load_players(path) if path.exists() else []
