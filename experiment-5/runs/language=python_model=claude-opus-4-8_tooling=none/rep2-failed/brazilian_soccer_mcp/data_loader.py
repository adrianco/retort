"""
Context
=======
Module: brazilian_soccer_mcp.data_loader
Purpose: Load every provided Kaggle CSV into :class:`Match` / :class:`Player`
objects.

Each of the six CSV files has a different schema, so there is one loader
function per file.  All files are read with ``utf-8-sig`` encoding so that the
BOM that prefixes ``fifa_data.csv`` and the accented Portuguese text are handled
correctly.  Goal/score columns are parsed leniently because some files store
them as floats (``"1.0"``).

Public entry point: :func:`load_dataset` returns ``(matches, players)``.
"""

from __future__ import annotations

import csv
import os
from typing import Iterable, List, Tuple

from .models import Match, Player
from .normalize import parse_date, parse_int

# Default location of the bundled Kaggle data relative to the repo root.
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "kaggle",
)


def _rows(path: str) -> Iterable[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh)


def _load_brasileirao(path: str) -> List[Match]:
    out: List[Match] = []
    for r in _rows(path):
        out.append(
            Match(
                competition="Brasileirão Série A",
                season=parse_int(r.get("season")),
                home_team=r.get("home_team", ""),
                away_team=r.get("away_team", ""),
                home_goal=parse_int(r.get("home_goal")),
                away_goal=parse_int(r.get("away_goal")),
                source="Brasileirao_Matches.csv",
                match_date=parse_date(r.get("datetime")),
                round=(r.get("round") or "").strip() or None,
            )
        )
    return out


def _load_cup(path: str) -> List[Match]:
    out: List[Match] = []
    for r in _rows(path):
        out.append(
            Match(
                competition="Copa do Brasil",
                season=parse_int(r.get("season")),
                home_team=r.get("home_team", ""),
                away_team=r.get("away_team", ""),
                home_goal=parse_int(r.get("home_goal")),
                away_goal=parse_int(r.get("away_goal")),
                source="Brazilian_Cup_Matches.csv",
                match_date=parse_date(r.get("datetime")),
                round=(r.get("round") or "").strip() or None,
            )
        )
    return out


def _load_libertadores(path: str) -> List[Match]:
    out: List[Match] = []
    for r in _rows(path):
        out.append(
            Match(
                competition="Copa Libertadores",
                season=parse_int(r.get("season")),
                home_team=r.get("home_team", ""),
                away_team=r.get("away_team", ""),
                home_goal=parse_int(r.get("home_goal")),
                away_goal=parse_int(r.get("away_goal")),
                source="Libertadores_Matches.csv",
                match_date=parse_date(r.get("datetime")),
                stage=(r.get("stage") or "").strip() or None,
            )
        )
    return out


def _load_br_football(path: str) -> List[Match]:
    """Extended-statistics dataset; ``tournament`` names the competition."""
    out: List[Match] = []
    for r in _rows(path):
        stats = {}
        for key in (
            "home_corner", "away_corner", "home_attack", "away_attack",
            "home_shots", "away_shots", "total_corners",
        ):
            val = parse_int(r.get(key))
            if val is not None:
                stats[key] = val
        for key in ("ht_result", "at_result"):
            if r.get(key):
                stats[key] = r[key]
        out.append(
            Match(
                competition=(r.get("tournament") or "Unknown").strip(),
                season=_season_from_date(r.get("date")),
                home_team=r.get("home", ""),
                away_team=r.get("away", ""),
                home_goal=parse_int(r.get("home_goal")),
                away_goal=parse_int(r.get("away_goal")),
                source="BR-Football-Dataset.csv",
                match_date=parse_date(r.get("date")),
                stats=stats,
            )
        )
    return out


def _load_novo(path: str) -> List[Match]:
    out: List[Match] = []
    for r in _rows(path):
        out.append(
            Match(
                competition="Brasileirão Série A",
                season=parse_int(r.get("Ano")),
                home_team=r.get("Equipe_mandante", ""),
                away_team=r.get("Equipe_visitante", ""),
                home_goal=parse_int(r.get("Gols_mandante")),
                away_goal=parse_int(r.get("Gols_visitante")),
                source="novo_campeonato_brasileiro.csv",
                match_date=parse_date(r.get("Data")),
                round=(r.get("Rodada") or "").strip() or None,
                arena=(r.get("Arena") or "").strip() or None,
            )
        )
    return out


def _load_players(path: str) -> List[Player]:
    out: List[Player] = []
    skill_cols = (
        "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
        "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
        "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
        "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
        "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
        "Composure", "Marking", "StandingTackle", "SlidingTackle",
        "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
    )
    for r in _rows(path):
        skills = {}
        for col in skill_cols:
            val = parse_int(r.get(col))
            if val is not None:
                skills[col] = val
        out.append(
            Player(
                player_id=parse_int(r.get("ID")),
                name=(r.get("Name") or "").strip(),
                age=parse_int(r.get("Age")),
                nationality=(r.get("Nationality") or "").strip(),
                overall=parse_int(r.get("Overall")),
                potential=parse_int(r.get("Potential")),
                club=(r.get("Club") or "").strip(),
                position=(r.get("Position") or "").strip(),
                jersey_number=parse_int(r.get("Jersey Number")),
                height=(r.get("Height") or "").strip(),
                weight=(r.get("Weight") or "").strip(),
                preferred_foot=(r.get("Preferred Foot") or "").strip(),
                value=(r.get("Value") or "").strip(),
                wage=(r.get("Wage") or "").strip(),
                skills=skills,
            )
        )
    return out


def _season_from_date(value) -> int | None:
    d = parse_date(value)
    return d.year if d else None


# Maps each filename to (loader, kind).
_MATCH_LOADERS = {
    "Brasileirao_Matches.csv": _load_brasileirao,
    "Brazilian_Cup_Matches.csv": _load_cup,
    "Libertadores_Matches.csv": _load_libertadores,
    "BR-Football-Dataset.csv": _load_br_football,
    "novo_campeonato_brasileiro.csv": _load_novo,
}
PLAYER_FILE = "fifa_data.csv"


def load_dataset(data_dir: str = DEFAULT_DATA_DIR) -> Tuple[List[Match], List[Player]]:
    """Load all six CSV files and return ``(matches, players)``.

    Missing files are skipped rather than raising, so a partial dataset still
    loads.  Raises :class:`FileNotFoundError` only if the directory itself is
    absent.
    """
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    matches: List[Match] = []
    for filename, loader in _MATCH_LOADERS.items():
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            matches.extend(loader(path))

    players: List[Player] = []
    player_path = os.path.join(data_dir, PLAYER_FILE)
    if os.path.exists(player_path):
        players = _load_players(player_path)

    return matches, players
