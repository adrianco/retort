# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : soccer_mcp.data_loader
# Purpose : Parse the six provided Kaggle CSV files into the shared Match /
#           Player records. Each file has its own column layout, naming
#           convention and date format, so there is one loader per file plus a
#           `load_all` convenience that returns (matches, players).
# Encoding: All files are read as UTF-8 (with BOM tolerance for fifa_data.csv).
# Robust  : Loaders skip rows with unparseable scores rather than aborting, so
#           a few dirty rows never take down the whole dataset.
# =============================================================================

from __future__ import annotations

import csv
import os
from typing import List, Tuple

from .models import Match, Player
from .normalize import (
    normalize_team,
    normalize_text,
    parse_date,
    to_int,
    year_from_date,
)

# Default location of the datasets, relative to the repository root.
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "kaggle",
)

# Filenames -> loader competition labels.
BRASILEIRAO_FILE = "Brasileirao_Matches.csv"
CUP_FILE = "Brazilian_Cup_Matches.csv"
LIBERTADORES_FILE = "Libertadores_Matches.csv"
EXTENDED_FILE = "BR-Football-Dataset.csv"
HISTORICAL_FILE = "novo_campeonato_brasileiro.csv"
FIFA_FILE = "fifa_data.csv"


def _open(path: str):
    """Open a CSV for reading as UTF-8, tolerating a BOM."""
    return open(path, "r", encoding="utf-8-sig", newline="")


def _make_match(competition, season, date, home, away, hg, ag, **kw) -> Match:
    return Match(
        competition=competition,
        season=season,
        date=date,
        home_team=home,
        away_team=away,
        home_team_norm=normalize_team(home),
        away_team_norm=normalize_team(away),
        home_goal=hg,
        away_goal=ag,
        **kw,
    )


def load_brasileirao(data_dir: str = DEFAULT_DATA_DIR) -> List[Match]:
    path = os.path.join(data_dir, BRASILEIRAO_FILE)
    out: List[Match] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            hg, ag = to_int(row.get("home_goal")), to_int(row.get("away_goal"))
            date = parse_date(row.get("datetime", ""))
            season = to_int(row.get("season")) or year_from_date(date)
            out.append(
                _make_match(
                    "Brasileirão", season, date,
                    row.get("home_team", "").strip(),
                    row.get("away_team", "").strip(),
                    hg, ag,
                    round=str(row.get("round", "")).strip() or None,
                    source=BRASILEIRAO_FILE,
                )
            )
    return out


def load_cup(data_dir: str = DEFAULT_DATA_DIR) -> List[Match]:
    path = os.path.join(data_dir, CUP_FILE)
    out: List[Match] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            hg, ag = to_int(row.get("home_goal")), to_int(row.get("away_goal"))
            date = parse_date(row.get("datetime", ""))
            season = to_int(row.get("season")) or year_from_date(date)
            out.append(
                _make_match(
                    "Copa do Brasil", season, date,
                    row.get("home_team", "").strip(),
                    row.get("away_team", "").strip(),
                    hg, ag,
                    round=str(row.get("round", "")).strip() or None,
                    source=CUP_FILE,
                )
            )
    return out


def load_libertadores(data_dir: str = DEFAULT_DATA_DIR) -> List[Match]:
    path = os.path.join(data_dir, LIBERTADORES_FILE)
    out: List[Match] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            hg, ag = to_int(row.get("home_goal")), to_int(row.get("away_goal"))
            date = parse_date(row.get("datetime", ""))
            season = to_int(row.get("season")) or year_from_date(date)
            out.append(
                _make_match(
                    "Libertadores", season, date,
                    row.get("home_team", "").strip(),
                    row.get("away_team", "").strip(),
                    hg, ag,
                    stage=str(row.get("stage", "")).strip() or None,
                    source=LIBERTADORES_FILE,
                )
            )
    return out


def load_extended(data_dir: str = DEFAULT_DATA_DIR) -> List[Match]:
    """BR-Football-Dataset.csv: multi-competition matches with extended stats."""
    path = os.path.join(data_dir, EXTENDED_FILE)
    # Map the dataset's tournament labels to canonical competition names.
    comp_map = {
        "serie a": "Brasileirão",
        "serie b": "Brasileirão Série B",
        "serie c": "Brasileirão Série C",
        "copa do brasil": "Copa do Brasil",
    }
    out: List[Match] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            hg, ag = to_int(row.get("home_goal")), to_int(row.get("away_goal"))
            date = parse_date(row.get("date", ""))
            tournament = (row.get("tournament", "") or "").strip()
            competition = comp_map.get(tournament.lower(), tournament or "Unknown")
            stats = {
                "home_shots": to_int(row.get("home_shots")),
                "away_shots": to_int(row.get("away_shots")),
                "home_corner": to_int(row.get("home_corner")),
                "away_corner": to_int(row.get("away_corner")),
                "total_corners": to_int(row.get("total_corners")),
                "ht_result": (row.get("ht_result") or "").strip(),
            }
            out.append(
                _make_match(
                    competition, year_from_date(date), date,
                    row.get("home", "").strip(),
                    row.get("away", "").strip(),
                    hg, ag,
                    source=EXTENDED_FILE,
                    stats=stats,
                )
            )
    return out


def load_historical(data_dir: str = DEFAULT_DATA_DIR) -> List[Match]:
    """novo_campeonato_brasileiro.csv: historical Brasileirão 2003-2019."""
    path = os.path.join(data_dir, HISTORICAL_FILE)
    out: List[Match] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            hg = to_int(row.get("Gols_mandante"))
            ag = to_int(row.get("Gols_visitante"))
            date = parse_date(row.get("Data", ""))
            season = to_int(row.get("Ano")) or year_from_date(date)
            out.append(
                _make_match(
                    "Brasileirão", season, date,
                    row.get("Equipe_mandante", "").strip(),
                    row.get("Equipe_visitante", "").strip(),
                    hg, ag,
                    round=str(row.get("Rodada", "")).strip() or None,
                    venue=(row.get("Arena") or "").strip() or None,
                    source=HISTORICAL_FILE,
                )
            )
    return out


def load_players(data_dir: str = DEFAULT_DATA_DIR) -> List[Player]:
    path = os.path.join(data_dir, FIFA_FILE)
    out: List[Player] = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            club = (row.get("Club") or "").strip()
            out.append(
                Player(
                    player_id=to_int(row.get("ID")),
                    name=name,
                    name_norm=normalize_text(name),
                    age=to_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip(),
                    overall=to_int(row.get("Overall")),
                    potential=to_int(row.get("Potential")),
                    club=club,
                    club_norm=normalize_team(club),
                    position=(row.get("Position") or "").strip(),
                    jersey_number=(row.get("Jersey Number") or "").strip() or None,
                    height=(row.get("Height") or "").strip(),
                    weight=(row.get("Weight") or "").strip(),
                    value=(row.get("Value") or "").strip(),
                    wage=(row.get("Wage") or "").strip(),
                    preferred_foot=(row.get("Preferred Foot") or "").strip(),
                )
            )
    return out


# The three Brasileirão sources and the two Copa do Brasil sources overlap on
# the years they share (e.g. all three Brasileirão files carry the full 2019
# season). Counting those copies would triple a team's points in a computed
# table, so for each (competition, season) we keep matches from a single
# canonical source. Lower number = higher priority. novo_campeonato uses the
# cleanest Portuguese club names (one row per team) so it wins for the years it
# covers; BR-Football is the fallback that fills the most recent seasons.
SOURCE_PRIORITY = {
    HISTORICAL_FILE: 0,      # novo_campeonato_brasileiro.csv (Brasileirão 2003-2019)
    BRASILEIRAO_FILE: 1,     # Brasileirao_Matches.csv        (Brasileirão 2012-2022)
    CUP_FILE: 2,             # Brazilian_Cup_Matches.csv      (Copa do Brasil 2012-2021)
    LIBERTADORES_FILE: 3,    # Libertadores_Matches.csv       (Libertadores only)
    EXTENDED_FILE: 4,        # BR-Football-Dataset.csv        (fills 2023 + Série B/C)
}


def dedupe_matches(matches: List[Match]) -> List[Match]:
    """Keep one canonical source per (competition, season).

    For every (competition, season) bucket we keep only the rows from the
    highest-priority source present, which removes the cross-file duplication
    while preserving full chronological coverage (each season is supplied by
    exactly one file).
    """
    from collections import defaultdict

    buckets: dict = defaultdict(list)
    for m in matches:
        buckets[(m.competition, m.season)].append(m)

    out: List[Match] = []
    for group in buckets.values():
        best = min(SOURCE_PRIORITY.get(m.source, 99) for m in group)
        out.extend(m for m in group if SOURCE_PRIORITY.get(m.source, 99) == best)
    return out


def load_all_matches(
    data_dir: str = DEFAULT_DATA_DIR, dedupe: bool = True
) -> List[Match]:
    """Load every match dataset.

    With ``dedupe=True`` (default) overlapping seasons are collapsed to one
    canonical source so aggregate calculations are correct. Pass
    ``dedupe=False`` to get the raw concatenation of all files.
    """
    matches: List[Match] = []
    matches += load_brasileirao(data_dir)
    matches += load_cup(data_dir)
    matches += load_libertadores(data_dir)
    matches += load_extended(data_dir)
    matches += load_historical(data_dir)
    return dedupe_matches(matches) if dedupe else matches


def load_all(
    data_dir: str = DEFAULT_DATA_DIR, dedupe: bool = True
) -> Tuple[List[Match], List[Player]]:
    """Load everything: returns (matches, players)."""
    return load_all_matches(data_dir, dedupe=dedupe), load_players(data_dir)
