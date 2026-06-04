"""
================================================================================
Module: brazilian_soccer_mcp.data_loader
--------------------------------------------------------------------------------
Context:
    The six Kaggle CSVs in ``data/kaggle/`` each have a different schema, header
    casing, score encoding and competition implied by the file (see TASK.md
    "Provided Data"). This module is the single place that knows those raw
    schemas; everything downstream consumes the unified ``Match`` / ``Player``
    objects from models.py.

Responsibility:
    * Locate the data directory robustly (works from repo root or installed pkg).
    * Parse each CSV with the stdlib ``csv`` module under UTF-8 (with BOM
      tolerance) so no third-party dependency is required and Portuguese
      characters survive intact.
    * Map raw rows -> normalized domain objects, tagging the source file.

    Loading is intentionally pure-stdlib so unit tests run anywhere.
================================================================================
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Iterable, List, Optional

from .models import (
    BRASILEIRAO_A,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COPA_DO_BRASIL,
    LIBERTADORES,
    Match,
    Player,
)
from .normalize import clean_team_name, parse_date, parse_int

# Tournament strings found in BR-Football-Dataset.csv -> canonical labels.
_BR_TOURNAMENT_MAP = {
    "serie a": BRASILEIRAO_A,
    "serie b": BRASILEIRAO_B,
    "serie c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
}


def find_data_dir(explicit: Optional[str] = None) -> Path:
    """Return the ``data/kaggle`` directory.

    Resolution order: explicit arg -> ``BR_SOCCER_DATA_DIR`` env var ->
    walk up from this file looking for ``data/kaggle``.
    """
    candidates: List[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("BR_SOCCER_DATA_DIR")
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidates.append(parent / "data" / "kaggle")
    candidates.append(Path.cwd() / "data" / "kaggle")

    for cand in candidates:
        if cand.is_dir():
            return cand
    raise FileNotFoundError(
        "Could not locate data/kaggle directory. Set BR_SOCCER_DATA_DIR or pass "
        "data_dir explicitly."
    )


def _open_rows(path: Path) -> Iterable[dict]:
    """Yield CSV rows as dicts, tolerating a UTF-8 BOM in the header."""
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield row


# --------------------------------------------------------------------------- #
# Match loaders (one per source schema)                                        #
# --------------------------------------------------------------------------- #
def load_brasileirao(path: Path) -> List[Match]:
    out = []
    for r in _open_rows(path):
        out.append(
            Match(
                competition=BRASILEIRAO_A,
                season=parse_int(r.get("season")),
                match_date=parse_date(r.get("datetime")),
                home_team=clean_team_name(r.get("home_team", "")),
                away_team=clean_team_name(r.get("away_team", "")),
                home_goal=parse_int(r.get("home_goal")),
                away_goal=parse_int(r.get("away_goal")),
                round=(r.get("round") or "").strip() or None,
                home_state=(r.get("home_team_state") or "").strip() or None,
                away_state=(r.get("away_team_state") or "").strip() or None,
                source=path.name,
            )
        )
    return out


def load_cup(path: Path) -> List[Match]:
    out = []
    for r in _open_rows(path):
        out.append(
            Match(
                competition=COPA_DO_BRASIL,
                season=parse_int(r.get("season")),
                match_date=parse_date(r.get("datetime")),
                home_team=clean_team_name(r.get("home_team", "")),
                away_team=clean_team_name(r.get("away_team", "")),
                home_goal=parse_int(r.get("home_goal")),
                away_goal=parse_int(r.get("away_goal")),
                round=(r.get("round") or "").strip().strip('"') or None,
                source=path.name,
            )
        )
    return out


def load_libertadores(path: Path) -> List[Match]:
    out = []
    for r in _open_rows(path):
        out.append(
            Match(
                competition=LIBERTADORES,
                season=parse_int(r.get("season")),
                match_date=parse_date(r.get("datetime")),
                home_team=clean_team_name(r.get("home_team", "")),
                away_team=clean_team_name(r.get("away_team", "")),
                home_goal=parse_int(r.get("home_goal")),
                away_goal=parse_int(r.get("away_goal")),
                stage=(r.get("stage") or "").strip() or None,
                source=path.name,
            )
        )
    return out


def load_br_football(path: Path) -> List[Match]:
    out = []
    for r in _open_rows(path):
        tourn_raw = (r.get("tournament") or "").strip()
        competition = _BR_TOURNAMENT_MAP.get(tourn_raw.lower(), tourn_raw or "Unknown")
        d = parse_date(r.get("date"))
        out.append(
            Match(
                competition=competition,
                season=d.year if d else None,
                match_date=d,
                home_team=clean_team_name(r.get("home", "")),
                away_team=clean_team_name(r.get("away", "")),
                home_goal=parse_int(r.get("home_goal")),
                away_goal=parse_int(r.get("away_goal")),
                source=path.name,
            )
        )
    return out


def load_historical_brasileirao(path: Path) -> List[Match]:
    out = []
    for r in _open_rows(path):
        out.append(
            Match(
                competition=BRASILEIRAO_A,
                season=parse_int(r.get("Ano")),
                match_date=parse_date(r.get("Data")),
                home_team=clean_team_name(r.get("Equipe_mandante", "")),
                away_team=clean_team_name(r.get("Equipe_visitante", "")),
                home_goal=parse_int(r.get("Gols_mandante")),
                away_goal=parse_int(r.get("Gols_visitante")),
                round=(r.get("Rodada") or "").strip() or None,
                home_state=(r.get("Mandante_UF") or "").strip() or None,
                away_state=(r.get("Visitante_UF") or "").strip() or None,
                source=path.name,
            )
        )
    return out


# --------------------------------------------------------------------------- #
# Player loader                                                                #
# --------------------------------------------------------------------------- #
def load_players(path: Path) -> List[Player]:
    out = []
    for r in _open_rows(path):
        name = (r.get("Name") or "").strip()
        if not name:
            continue
        out.append(
            Player(
                player_id=parse_int(r.get("ID")),
                name=name,
                age=parse_int(r.get("Age")),
                nationality=(r.get("Nationality") or "").strip(),
                overall=parse_int(r.get("Overall")),
                potential=parse_int(r.get("Potential")),
                club=(r.get("Club") or "").strip(),
                position=(r.get("Position") or "").strip(),
                jersey_number=parse_int(r.get("Jersey Number")),
                height=(r.get("Height") or "").strip(),
                weight=(r.get("Weight") or "").strip(),
            )
        )
    return out


# Map of filename -> loader function.
_MATCH_FILES = {
    "Brasileirao_Matches.csv": load_brasileirao,
    "Brazilian_Cup_Matches.csv": load_cup,
    "Libertadores_Matches.csv": load_libertadores,
    "BR-Football-Dataset.csv": load_br_football,
    "novo_campeonato_brasileiro.csv": load_historical_brasileirao,
}
_PLAYER_FILE = "fifa_data.csv"


def load_all_matches(data_dir: Path) -> List[Match]:
    matches: List[Match] = []
    for fname, loader in _MATCH_FILES.items():
        path = data_dir / fname
        if path.exists():
            matches.extend(loader(path))
    return matches


def load_all_players(data_dir: Path) -> List[Player]:
    path = data_dir / _PLAYER_FILE
    return load_players(path) if path.exists() else []
