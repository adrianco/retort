"""
================================================================================
Module: data_loader.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Context
-------
Loads the six provided Kaggle CSVs (in ``data/kaggle/``) into the normalized
``Match`` and ``Player`` records defined in ``models.py``. Pure stdlib (``csv``)
because the sandbox has no network access to install pandas.

Sources and the competition each maps to:

    Brasileirao_Matches.csv          -> Brasileirão Série A   (2012+, has round)
    novo_campeonato_brasileiro.csv   -> Brasileirão Série A   (2003-2019, arena)
    Brazilian_Cup_Matches.csv        -> Copa do Brasil
    Libertadores_Matches.csv         -> Copa Libertadores     (has stage)
    BR-Football-Dataset.csv          -> Série A/B/C + Copa do Brasil (corner/shot stats)
    fifa_data.csv                    -> Player records

De-duplication
--------------
Série A seasons overlap across three files. Matches are keyed by
``(competition, season, home_key, away_key)`` (one league fixture leg). The
first file to provide a fixture wins; later files only *fill in* missing fields
(arena, shot/corner stats) so stats are never double-counted while still being
enriched. Load order is chosen so the richest primary record wins.

Date handling
-------------
Three formats appear and are all normalized to ISO ``YYYY-MM-DD``:
    "2012-05-19 18:30:00"   "2023-09-24"   "29/03/2003"
================================================================================
"""

from __future__ import annotations

import csv
import os
from typing import Optional

from models import Match, Player
from normalize import normalize_key, canonical_name

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

_BR_FOOTBALL_COMP = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_BRASIL,
}


# --------------------------------------------------------------------------- #
# Small parsing helpers                                                       #
# --------------------------------------------------------------------------- #
def _to_int(value) -> Optional[int]:
    """Parse goal/age fields that may be "", "2", "2.0" or floats."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() in ("nan", "null", "none"):
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() in ("nan", "null", "none"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_date(value) -> str:
    """Normalize the assorted date formats to ISO YYYY-MM-DD ("" if unknown)."""
    if not value:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    # "2012-05-19 18:30:00" / "2023-09-24"
    if "-" in s and s[:4].isdigit():
        return s.split(" ")[0]
    # "29/03/2003"
    if "/" in s:
        parts = s.split(" ")[0].split("/")
        if len(parts) == 3:
            d, m, y = parts
            if len(y) == 4:
                return f"{y}-{int(m):02d}-{int(d):02d}"
    return s


def _open(path):
    # utf-8-sig strips any BOM (fifa_data.csv has one).
    return open(path, encoding="utf-8-sig", newline="")


# --------------------------------------------------------------------------- #
# Dataset                                                                     #
# --------------------------------------------------------------------------- #
class Dataset:
    """Container holding the loaded, de-duplicated matches and players."""

    def __init__(self):
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self._match_index: dict[tuple, Match] = {}

    # -- match ingestion -------------------------------------------------- #
    def _add_match(self, m: Match):
        # Dedup on the league-fixture identity. Date is deliberately excluded:
        # the same fixture is dated differently across files (and some files
        # omit it), so including it would defeat de-duplication.
        key = (m.competition, m.season, m.home_key, m.away_key)
        existing = self._match_index.get(key)
        if existing is None:
            self._match_index[key] = m
            self.matches.append(m)
            return
        # Enrich the existing record with any fields it is missing.
        for src in m.sources:
            if src not in existing.sources:
                existing.sources.append(src)
        for fld in ("date", "round", "stage", "arena", "datetime_raw"):
            if not getattr(existing, fld) and getattr(m, fld):
                setattr(existing, fld, getattr(m, fld))
        for fld in ("home_corner", "away_corner", "home_shots", "away_shots",
                    "home_attack", "away_attack"):
            if getattr(existing, fld) is None and getattr(m, fld) is not None:
                setattr(existing, fld, getattr(m, fld))
        if existing.home_goal is None and m.home_goal is not None:
            existing.home_goal = m.home_goal
            existing.away_goal = m.away_goal

    def _mk_match(self, competition, season, home, away, hg, ag, *,
                  date="", round="", stage="", arena="", dt_raw="", source="",
                  stats=None) -> Match:
        stats = stats or {}
        return Match(
            competition=competition,
            season=_to_int(season),
            date=_parse_date(date),
            home_team=canonical_name(home) or str(home),
            away_team=canonical_name(away) or str(away),
            home_key=normalize_key(home),
            away_key=normalize_key(away),
            home_goal=_to_int(hg),
            away_goal=_to_int(ag),
            round=str(round or "").strip(),
            stage=str(stage or "").strip(),
            arena=str(arena or "").strip(),
            datetime_raw=str(dt_raw or "").strip(),
            sources=[source] if source else [],
            **stats,
        )


# --------------------------------------------------------------------------- #
# Per-file loaders                                                            #
# --------------------------------------------------------------------------- #
def _load_brasileirao(ds: Dataset, path: str):
    src = "Brasileirao_Matches.csv"
    with _open(path) as f:
        for r in csv.DictReader(f):
            ds._add_match(ds._mk_match(
                SERIE_A, r.get("season"), r.get("home_team"), r.get("away_team"),
                r.get("home_goal"), r.get("away_goal"),
                date=r.get("datetime"), round=r.get("round"),
                dt_raw=r.get("datetime"), source=src,
            ))


def _load_novo(ds: Dataset, path: str):
    src = "novo_campeonato_brasileiro.csv"
    with _open(path) as f:
        for r in csv.DictReader(f):
            ds._add_match(ds._mk_match(
                SERIE_A, r.get("Ano"), r.get("Equipe_mandante"), r.get("Equipe_visitante"),
                r.get("Gols_mandante"), r.get("Gols_visitante"),
                date=r.get("Data"), round=r.get("Rodada"),
                arena=r.get("Arena"), dt_raw=r.get("Data"), source=src,
            ))


def _load_cup(ds: Dataset, path: str):
    src = "Brazilian_Cup_Matches.csv"
    with _open(path) as f:
        for r in csv.DictReader(f):
            ds._add_match(ds._mk_match(
                COPA_BRASIL, r.get("season"), r.get("home_team"), r.get("away_team"),
                r.get("home_goal"), r.get("away_goal"),
                date=r.get("datetime"), round=r.get("round"),
                dt_raw=r.get("datetime"), source=src,
            ))


def _load_libertadores(ds: Dataset, path: str):
    src = "Libertadores_Matches.csv"
    with _open(path) as f:
        for r in csv.DictReader(f):
            ds._add_match(ds._mk_match(
                LIBERTADORES, r.get("season"), r.get("home_team"), r.get("away_team"),
                r.get("home_goal"), r.get("away_goal"),
                date=r.get("datetime"), stage=r.get("stage"),
                dt_raw=r.get("datetime"), source=src,
            ))


def _load_br_football(ds: Dataset, path: str):
    src = "BR-Football-Dataset.csv"
    with _open(path) as f:
        for r in csv.DictReader(f):
            comp = _BR_FOOTBALL_COMP.get((r.get("tournament") or "").strip(),
                                         (r.get("tournament") or "").strip())
            date = _parse_date(r.get("date"))
            # BR-Football has no season column. Brazilian league seasons run
            # within a calendar year (Apr-Dec), but the COVID-hit 2020 season
            # spilled into Jan/Feb 2021. Attribute Jan/Feb matches to the prior
            # year so they merge with the dedicated season files instead of
            # creating phantom next-season fixtures.
            season = None
            if date:
                yr, mo = int(date[:4]), int(date[5:7])
                season = yr - 1 if mo <= 2 else yr
            stats = {
                "home_corner": _to_float(r.get("home_corner")),
                "away_corner": _to_float(r.get("away_corner")),
                "home_shots": _to_float(r.get("home_shots")),
                "away_shots": _to_float(r.get("away_shots")),
                "home_attack": _to_float(r.get("home_attack")),
                "away_attack": _to_float(r.get("away_attack")),
            }
            ds._add_match(ds._mk_match(
                comp, season, r.get("home"), r.get("away"),
                r.get("home_goal"), r.get("away_goal"),
                date=r.get("date"), dt_raw=(r.get("date", "") + " " + r.get("time", "")).strip(),
                source=src, stats=stats,
            ))


def _load_players(ds: Dataset, path: str):
    with _open(path) as f:
        for r in csv.DictReader(f):
            club = (r.get("Club") or "").strip()
            ds.players.append(Player(
                player_id=(r.get("ID") or "").strip(),
                name=(r.get("Name") or "").strip(),
                nationality=(r.get("Nationality") or "").strip(),
                club=club,
                club_key=normalize_key(club),
                position=(r.get("Position") or "").strip(),
                age=_to_int(r.get("Age")),
                overall=_to_int(r.get("Overall")),
                potential=_to_int(r.get("Potential")),
                jersey_number=(r.get("Jersey Number") or "").strip(),
                height=(r.get("Height") or "").strip(),
                weight=(r.get("Weight") or "").strip(),
                value=(r.get("Value") or "").strip(),
                wage=(r.get("Wage") or "").strip(),
                preferred_foot=(r.get("Preferred Foot") or "").strip(),
            ))


# Load order: dedicated league files first (richest primary records), then the
# stats file (enriches Série A, adds B/C), then cup & continental, then players.
_MATCH_FILES = [
    ("Brasileirao_Matches.csv", _load_brasileirao),
    ("novo_campeonato_brasileiro.csv", _load_novo),
    ("BR-Football-Dataset.csv", _load_br_football),
    ("Brazilian_Cup_Matches.csv", _load_cup),
    ("Libertadores_Matches.csv", _load_libertadores),
]


def load_dataset(data_dir: str = DEFAULT_DATA_DIR) -> Dataset:
    """Load every CSV under ``data_dir`` into a :class:`Dataset`."""
    ds = Dataset()
    for fname, loader in _MATCH_FILES:
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            loader(ds, path)
    players_path = os.path.join(data_dir, "fifa_data.csv")
    if os.path.exists(players_path):
        _load_players(ds, players_path)
    return ds


if __name__ == "__main__":  # quick manual smoke check
    d = load_dataset()
    print(f"matches: {len(d.matches)}  players: {len(d.players)}")
    from collections import Counter
    comps = Counter(m.competition for m in d.matches)
    for k, v in comps.most_common():
        print(f"  {k}: {v}")
