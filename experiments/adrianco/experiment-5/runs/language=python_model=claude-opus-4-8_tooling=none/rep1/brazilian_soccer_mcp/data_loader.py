"""
================================================================================
 Module: data_loader
================================================================================
Context
-------
Loads the six provided Kaggle CSV datasets from ``data/kaggle/`` into normalized
``Match`` and ``Player`` records.  Each loader maps a file's idiosyncratic
column names onto a common schema and tags every match with its competition.

The module uses only the standard-library ``csv`` reader (UTF-8) so it has no
third-party dependencies and handles the special characters present in
Brazilian Portuguese text.  Rows with unparseable scores are skipped so that
downstream statistics stay correct.

Datasets
--------
  Brasileirao_Matches.csv        -> "Brasileirão Série A"
  Brazilian_Cup_Matches.csv      -> "Copa do Brasil"
  Libertadores_Matches.csv       -> "Copa Libertadores"
  BR-Football-Dataset.csv        -> tournament column (Serie A/B/C, Copa do Brasil)
  novo_campeonato_brasileiro.csv -> "Brasileirão Série A" (historical 2003-2019)
  fifa_data.csv                  -> FIFA player database
================================================================================
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .normalization import (
    canonical_competition,
    clean_team_name,
    iso_date,
    parse_date,
    parse_float,
    parse_int,
    parse_season,
    team_key,
)

# Competition canonical names.
BRASILEIRAO = "Brasileirão Série A"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"


def default_data_dir() -> str:
    """Return the absolute path to the bundled ``data/kaggle`` directory."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    return os.path.join(repo_root, "data", "kaggle")


@dataclass
class Match:
    """A normalized soccer match (one row from any of the match datasets)."""

    competition: str
    season: Optional[int]
    date: Optional[str]                 # ISO YYYY-MM-DD (or None)
    home_team: str                      # cleaned display name
    away_team: str                      # cleaned display name
    home_key: str                       # canonical lookup key
    away_key: str
    home_goal: int
    away_goal: int
    round: Optional[str] = None
    stage: Optional[str] = None
    arena: Optional[str] = None
    source: str = ""                    # source file name
    stats: Dict[str, float] = field(default_factory=dict)  # extended stats

    @property
    def winner_key(self) -> Optional[str]:
        """Canonical key of the winning team, or None for a draw."""
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None

    @property
    def total_goals(self) -> int:
        return self.home_goal + self.away_goal

    def involves(self, key: str) -> bool:
        return key in (self.home_key, self.away_key)

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "season": self.season,
            "date": self.date,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "round": self.round,
            "stage": self.stage,
            "arena": self.arena,
            "source": self.source,
        }


@dataclass
class Player:
    """A normalized FIFA player record."""

    player_id: Optional[int]
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    club_key: str
    position: str
    jersey_number: Optional[int]
    height: str
    weight: str
    raw: Dict[str, str] = field(default_factory=dict)

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
        }


def _make_match(home_raw, away_raw, home_goal, away_goal, **kwargs) -> Optional[Match]:
    """Build a Match, returning None if mandatory fields are unusable."""
    hg = parse_int(home_goal)
    ag = parse_int(away_goal)
    if hg is None or ag is None:
        return None
    home = clean_team_name(home_raw)
    away = clean_team_name(away_raw)
    if not home or not away:
        return None
    return Match(
        home_team=home,
        away_team=away,
        home_key=team_key(home_raw),
        away_key=team_key(away_raw),
        home_goal=hg,
        away_goal=ag,
        **kwargs,
    )


def _open(path: str):
    """Open a CSV file with UTF-8(-sig) encoding to handle BOM + accents."""
    return open(path, "r", encoding="utf-8-sig", newline="")


def load_brasileirao(path: str) -> List[Match]:
    matches: List[Match] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            m = _make_match(
                row.get("home_team"), row.get("away_team"),
                row.get("home_goal"), row.get("away_goal"),
                competition=BRASILEIRAO,
                season=parse_season(row.get("season")),
                date=iso_date(row.get("datetime")),
                round=(row.get("round") or "").strip() or None,
                source="Brasileirao_Matches.csv",
            )
            if m:
                matches.append(m)
    return matches


def load_copa_do_brasil(path: str) -> List[Match]:
    matches: List[Match] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            m = _make_match(
                row.get("home_team"), row.get("away_team"),
                row.get("home_goal"), row.get("away_goal"),
                competition=COPA_DO_BRASIL,
                season=parse_season(row.get("season")),
                date=iso_date(row.get("datetime")),
                round=(row.get("round") or "").strip() or None,
                source="Brazilian_Cup_Matches.csv",
            )
            if m:
                matches.append(m)
    return matches


def load_libertadores(path: str) -> List[Match]:
    matches: List[Match] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            m = _make_match(
                row.get("home_team"), row.get("away_team"),
                row.get("home_goal"), row.get("away_goal"),
                competition=LIBERTADORES,
                season=parse_season(row.get("season")),
                date=iso_date(row.get("datetime")),
                stage=(row.get("stage") or "").strip() or None,
                source="Libertadores_Matches.csv",
            )
            if m:
                matches.append(m)
    return matches


def load_br_football(path: str) -> List[Match]:
    """Extended-statistics dataset; competition comes from the ``tournament``
    column and is prefixed so it is clearly the Brazilian league pyramid."""
    matches: List[Match] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            tournament = (row.get("tournament") or "").strip()
            if not tournament:
                continue
            if tournament.lower().startswith("serie"):
                competition = canonical_competition(f"Brasileirão {tournament}")
            else:
                competition = canonical_competition(tournament)
            d = parse_date(row.get("date"))
            stats = {}
            for col in ("home_corner", "away_corner", "home_attack", "away_attack",
                        "home_shots", "away_shots", "total_corners"):
                val = parse_float(row.get(col))
                if val is not None:
                    stats[col] = val
            m = _make_match(
                row.get("home"), row.get("away"),
                row.get("home_goal"), row.get("away_goal"),
                competition=competition,
                season=d.year if d else None,
                date=d.isoformat() if d else None,
                source="BR-Football-Dataset.csv",
                stats=stats,
            )
            if m:
                matches.append(m)
    return matches


def load_historical_brasileirao(path: str) -> List[Match]:
    matches: List[Match] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            m = _make_match(
                row.get("Equipe_mandante"), row.get("Equipe_visitante"),
                row.get("Gols_mandante"), row.get("Gols_visitante"),
                competition=BRASILEIRAO,
                season=parse_season(row.get("Ano")),
                date=iso_date(row.get("Data")),
                round=(row.get("Rodada") or "").strip() or None,
                arena=(row.get("Arena") or "").strip() or None,
                source="novo_campeonato_brasileiro.csv",
            )
            if m:
                matches.append(m)
    return matches


def load_players(path: str) -> List[Player]:
    players: List[Player] = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            club = (row.get("Club") or "").strip()
            players.append(
                Player(
                    player_id=parse_int(row.get("ID")),
                    name=name,
                    age=parse_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip(),
                    overall=parse_int(row.get("Overall")),
                    potential=parse_int(row.get("Potential")),
                    club=club,
                    club_key=team_key(club) if club else "",
                    position=(row.get("Position") or "").strip(),
                    jersey_number=parse_int(row.get("Jersey Number")),
                    height=(row.get("Height") or "").strip(),
                    weight=(row.get("Weight") or "").strip(),
                    raw=row,
                )
            )
    return players


# Loaders are listed in DEDUPLICATION PRIORITY ORDER.  Several datasets cover
# overlapping years of the Brasileirão (the historical set covers 2003-2019,
# Brasileirao_Matches 2012-2022, and BR-Football's Serie A 2014-2023), so the
# same fixture can appear up to three times.  We load the cleanest league
# sources first and keep only the first occurrence of each fixture, which
# prevents standings and statistics from being multiplied across files.
MATCH_LOADERS = {
    "novo_campeonato_brasileiro.csv": load_historical_brasileirao,
    "Brasileirao_Matches.csv": load_brasileirao,
    "Brazilian_Cup_Matches.csv": load_copa_do_brasil,
    "Libertadores_Matches.csv": load_libertadores,
    "BR-Football-Dataset.csv": load_br_football,
}

PLAYER_FILE = "fifa_data.csv"


def select_authoritative_matches(matches: List[Match],
                                 source_rank: Dict[str, int]) -> List[Match]:
    """Pick a single authoritative source per (competition, season).

    Several files cover overlapping competition-seasons, but they disagree on
    team-name spelling (e.g. "Athletico" vs "Atletico Paranaense",
    "Bahia" vs "EC Bahia"), so naive cross-file fixture dedup leaks duplicates
    and inflates standings.  Instead, for each (competition, season) we keep
    matches from only the highest-priority file that covers it.  Because every
    file is internally consistent, the resulting per-season tables are correct,
    while seasons unique to one file (e.g. Série B/C, the most recent year) are
    still fully included.
    """
    best_rank: Dict[tuple, int] = {}
    for m in matches:
        key = (m.competition, m.season)
        rank = source_rank.get(m.source, 999)
        if key not in best_rank or rank < best_rank[key]:
            best_rank[key] = rank
    return [m for m in matches
            if source_rank.get(m.source, 999) == best_rank[(m.competition, m.season)]]


def load_all_matches(data_dir: Optional[str] = None) -> List[Match]:
    """Load matches from every available dataset, keeping one authoritative
    source per competition-season to avoid double-counting overlaps."""
    data_dir = data_dir or default_data_dir()
    source_rank = {fn: i for i, fn in enumerate(MATCH_LOADERS)}
    matches: List[Match] = []
    for filename, loader in MATCH_LOADERS.items():
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            matches.extend(loader(path))
    return select_authoritative_matches(matches, source_rank)


def load_all_players(data_dir: Optional[str] = None) -> List[Player]:
    """Load every player from the FIFA dataset (if present)."""
    data_dir = data_dir or default_data_dir()
    path = os.path.join(data_dir, PLAYER_FILE)
    if os.path.exists(path):
        return load_players(path)
    return []
