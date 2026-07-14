"""CSV ingestion for the six Kaggle datasets shipped under ``data/kaggle``.

The loader produces a single in-memory ``DataStore`` containing two relations:

* ``matches`` – the union of all match files, normalised into a common shape
  with columns ``date``, ``season``, ``competition``, ``round``, ``stage``,
  ``home_team``, ``away_team``, ``home_team_norm``, ``away_team_norm``,
  ``home_goal``, ``away_goal``, ``home_team_state``, ``away_team_state``,
  ``arena``, plus extended columns (corners, shots, attacks) when available.
* ``players`` – the FIFA player rows with a small set of derived/normalised
  fields (``club_norm``, ``nationality_norm``).

Everything is plain Python (lists of dicts) so the package has no third-party
runtime dependency beyond the MCP SDK. Volumes are small enough (≈24k matches,
18k players) that scans complete well under the 5-second budget set in the
spec.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from soccer_mcp.normalizer import normalize_team, _strip_accents

# ---------------------------------------------------------------------------
# Public competition labels.  These are used both in stored records and in
# query parameters.
# ---------------------------------------------------------------------------
BRASILEIRAO = "Brasileirão"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"
BR_FOOTBALL = "BR-Football"  # extended stats file
HISTORICAL = "Brasileirão (historical)"  # 2003-2019 file

ALL_COMPETITIONS = (
    BRASILEIRAO,
    COPA_DO_BRASIL,
    LIBERTADORES,
    BR_FOOTBALL,
    HISTORICAL,
)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------
_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%Y/%m/%d",
)


def parse_date(text: str | None) -> date | None:
    """Best-effort parse of the mixed date formats used across CSVs."""
    if not text:
        return None
    text = text.strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Some rows have just a year string
    if text.isdigit() and len(text) == 4:
        try:
            return date(int(text), 1, 1)
        except ValueError:
            return None
    return None


def _to_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# DataStore
# ---------------------------------------------------------------------------
@dataclass
class DataStore:
    """In-memory collection of all loaded matches and players."""

    matches: list[dict] = field(default_factory=list)
    players: list[dict] = field(default_factory=list)
    source_dir: Path | None = None

    # -- match helpers --------------------------------------------------
    def iter_matches(self) -> Iterable[dict]:
        return iter(self.matches)

    def competitions(self) -> list[str]:
        return sorted({m["competition"] for m in self.matches if m.get("competition")})

    def seasons(self) -> list[int]:
        return sorted({m["season"] for m in self.matches if m.get("season") is not None})

    def teams(self) -> list[str]:
        seen: set[str] = set()
        for m in self.matches:
            if m.get("home_team_norm"):
                seen.add(m["home_team_norm"])
            if m.get("away_team_norm"):
                seen.add(m["away_team_norm"])
        return sorted(seen)


def load_default_store(base_dir: str | os.PathLike[str] | None = None) -> DataStore:
    """Load every Kaggle CSV under ``base_dir`` (or ``data/kaggle/`` by default)."""
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[2] / "data" / "kaggle"
    base_dir = Path(base_dir)
    store = DataStore(source_dir=base_dir)

    loaders = (
        (_load_brasileirao, "Brasileirao_Matches.csv"),
        (_load_cup, "Brazilian_Cup_Matches.csv"),
        (_load_libertadores, "Libertadores_Matches.csv"),
        (_load_br_football, "BR-Football-Dataset.csv"),
        (_load_historical, "novo_campeonato_brasileiro.csv"),
    )
    for loader, filename in loaders:
        path = base_dir / filename
        if path.exists():
            loader(path, store)

    fifa = base_dir / "fifa_data.csv"
    if fifa.exists():
        _load_fifa_players(fifa, store)

    return store


# ---------------------------------------------------------------------------
# Match loaders
# ---------------------------------------------------------------------------
def _open_csv(path: Path):
    """Open a CSV file with UTF-8 + BOM tolerance."""
    return open(path, newline="", encoding="utf-8-sig")


def _make_match(
    *,
    competition: str,
    season: int | None,
    date_value: date | None,
    home_team: str,
    away_team: str,
    home_goal: int | None,
    away_goal: int | None,
    round_value: str | None = None,
    stage: str | None = None,
    home_state: str | None = None,
    away_state: str | None = None,
    arena: str | None = None,
    extras: dict | None = None,
) -> dict:
    record = {
        "competition": competition,
        "season": season,
        "date": date_value,
        "round": round_value,
        "stage": stage,
        "home_team": home_team,
        "away_team": away_team,
        "home_team_norm": normalize_team(home_team),
        "away_team_norm": normalize_team(away_team),
        "home_goal": home_goal,
        "away_goal": away_goal,
        "home_team_state": home_state,
        "away_team_state": away_state,
        "arena": arena,
    }
    if extras:
        record.update(extras)
    return record


def _load_brasileirao(path: Path, store: DataStore) -> None:
    with _open_csv(path) as fh:
        for row in csv.DictReader(fh):
            store.matches.append(_make_match(
                competition=BRASILEIRAO,
                season=_to_int(row.get("season")),
                date_value=parse_date(row.get("datetime")),
                home_team=row.get("home_team", "").strip(),
                away_team=row.get("away_team", "").strip(),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                round_value=row.get("round"),
                home_state=row.get("home_team_state") or None,
                away_state=row.get("away_team_state") or None,
            ))


def _load_cup(path: Path, store: DataStore) -> None:
    with _open_csv(path) as fh:
        for row in csv.DictReader(fh):
            store.matches.append(_make_match(
                competition=COPA_DO_BRASIL,
                season=_to_int(row.get("season")),
                date_value=parse_date(row.get("datetime")),
                home_team=row.get("home_team", "").strip(),
                away_team=row.get("away_team", "").strip(),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                round_value=row.get("round"),
            ))


def _load_libertadores(path: Path, store: DataStore) -> None:
    with _open_csv(path) as fh:
        for row in csv.DictReader(fh):
            store.matches.append(_make_match(
                competition=LIBERTADORES,
                season=_to_int(row.get("season")),
                date_value=parse_date(row.get("datetime")),
                home_team=row.get("home_team", "").strip(),
                away_team=row.get("away_team", "").strip(),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                stage=row.get("stage"),
            ))


def _load_br_football(path: Path, store: DataStore) -> None:
    with _open_csv(path) as fh:
        for row in csv.DictReader(fh):
            date_value = parse_date(row.get("date"))
            season = date_value.year if date_value else None
            tournament = (row.get("tournament") or "").strip() or BR_FOOTBALL
            extras = {
                "home_corner": _to_int(row.get("home_corner")),
                "away_corner": _to_int(row.get("away_corner")),
                "home_attack": _to_int(row.get("home_attack")),
                "away_attack": _to_int(row.get("away_attack")),
                "home_shots": _to_int(row.get("home_shots")),
                "away_shots": _to_int(row.get("away_shots")),
                "total_corners": _to_int(row.get("total_corners")),
                "ht_result": row.get("ht_result"),
                "at_result": row.get("at_result"),
                "kickoff_time": row.get("time"),
                "source_file": "BR-Football-Dataset",
            }
            store.matches.append(_make_match(
                competition=tournament,
                season=season,
                date_value=date_value,
                home_team=(row.get("home") or "").strip(),
                away_team=(row.get("away") or "").strip(),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                extras=extras,
            ))


def _load_historical(path: Path, store: DataStore) -> None:
    with _open_csv(path) as fh:
        for row in csv.DictReader(fh):
            store.matches.append(_make_match(
                competition=HISTORICAL,
                season=_to_int(row.get("Ano")),
                date_value=parse_date(row.get("Data")),
                home_team=(row.get("Equipe_mandante") or "").strip(),
                away_team=(row.get("Equipe_visitante") or "").strip(),
                home_goal=_to_int(row.get("Gols_mandante")),
                away_goal=_to_int(row.get("Gols_visitante")),
                round_value=row.get("Rodada"),
                home_state=row.get("Mandante_UF") or None,
                away_state=row.get("Visitante_UF") or None,
                arena=row.get("Arena") or None,
                extras={
                    "winner": row.get("Vencedor"),
                    "match_id": row.get("ID"),
                    "source_file": "novo_campeonato_brasileiro",
                },
            ))


# ---------------------------------------------------------------------------
# Player loader
# ---------------------------------------------------------------------------
def _load_fifa_players(path: Path, store: DataStore) -> None:
    with _open_csv(path) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            club = (row.get("Club") or "").strip()
            nationality = (row.get("Nationality") or "").strip()
            player = {
                "id": _to_int(row.get("ID")),
                "name": (row.get("Name") or "").strip(),
                "age": _to_int(row.get("Age")),
                "nationality": nationality,
                "nationality_norm": _strip_accents(nationality).lower(),
                "overall": _to_int(row.get("Overall")),
                "potential": _to_int(row.get("Potential")),
                "club": club,
                "club_norm": normalize_team(club),
                "position": (row.get("Position") or "").strip(),
                "jersey_number": _to_int(row.get("Jersey Number")),
                "height": row.get("Height"),
                "weight": row.get("Weight"),
                "preferred_foot": row.get("Preferred Foot"),
                "value": row.get("Value"),
                "wage": row.get("Wage"),
                "finishing": _to_int(row.get("Finishing")),
                "dribbling": _to_int(row.get("Dribbling")),
                "passing": _to_int(row.get("ShortPassing")),
                "pace": _to_int(row.get("SprintSpeed")),
                "shot_power": _to_int(row.get("ShotPower")),
            }
            store.players.append(player)
