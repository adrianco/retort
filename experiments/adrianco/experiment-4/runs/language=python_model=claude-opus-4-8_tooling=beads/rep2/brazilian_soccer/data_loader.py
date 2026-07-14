"""
================================================================================
Brazilian Soccer MCP Server :: data_loader
================================================================================

Context
-------
Loads the six provided Kaggle CSV datasets (under data/kaggle/) into a single
normalised set of `Match` and `Player` records. The raw datasets use different
column names, languages (Portuguese/English), date formats and team-naming
conventions; this module reconciles them so downstream code sees one schema.

Responsibilities
----------------
- Normalise team names: strip "-SP" / " - RJ" state suffixes, "(URU)" country
  tags and accents so "Palmeiras-SP", "Palmeiras" and "palmeiras" all match.
- Parse the multiple date formats (ISO, "DD/MM/YYYY", with/without time) into
  `datetime.date`.
- Map each source file to a canonical competition name.
- Coerce goals/numeric columns robustly (the data has floats, blanks, strings).

This module has no dependency on the MCP layer and is independently testable.
================================================================================
"""

from __future__ import annotations

import csv
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

# --------------------------------------------------------------------------- #
# Paths / competition mapping
# --------------------------------------------------------------------------- #

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "data", "kaggle"))

COMP_BRASILEIRAO = "Brasileirão Série A"
COMP_COPA_BRASIL = "Copa do Brasil"
COMP_LIBERTADORES = "Copa Libertadores"

# --------------------------------------------------------------------------- #
# Team name normalisation
# --------------------------------------------------------------------------- #

# Trailing code after a dash/slash, e.g. "-SP", " - RJ", "-URU", "-EQU".
_DASH_SUFFIX_RE = re.compile(r"\s*[-/]\s*([A-Za-z]{2,4})\s*$")
# Trailing space-separated code, e.g. "America MG", "Botafogo PB".
_SPACE_SUFFIX_RE = re.compile(r"\s+([A-Za-z]{2})\s*$")
_PAREN_RE = re.compile(r"\s*\([^)]*\)")
_WS_RE = re.compile(r"\s+")

# Brazilian state (UF) abbreviations.
_BR_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Base names shared by multiple distinct Brazilian clubs. For these we keep the
# state in the normalised key so "Atletico-MG" and "Atletico-PR" stay distinct,
# while non-ambiguous names ("Palmeiras-SP" -> "palmeiras") drop the suffix as
# the specification requires.
_AMBIGUOUS_BASES = {"atletico", "america", "botafogo", "nacional"}


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _split_suffix(raw: str) -> tuple[str, Optional[str]]:
    """Return (clean_name, uf) splitting any trailing state/country code.

    A dash/slash-separated 2-4 letter code is always treated as a suffix; a
    space-separated 2-letter code is only treated as a suffix when it is a
    valid Brazilian state abbreviation (avoids clobbering real name words)."""
    name = str(raw).strip().strip('"').strip()
    name = _PAREN_RE.sub("", name).strip()
    uf: Optional[str] = None

    m = _DASH_SUFFIX_RE.search(name)
    if m:
        code = m.group(1).upper()
        name = name[: m.start()].strip()
        if code in _BR_STATES:
            uf = code
    else:
        m = _SPACE_SUFFIX_RE.search(name)
        if m and m.group(1).upper() in _BR_STATES:
            uf = m.group(1).upper()
            name = name[: m.start()].strip()

    name = _WS_RE.sub(" ", name).strip(" -")
    return name, uf


def clean_team_name(raw: str) -> str:
    """Return a human-friendly team name with suffixes/parentheticals removed
    but accents and original casing preserved (e.g. "São Paulo")."""
    if raw is None:
        return ""
    name, _ = _split_suffix(raw)
    return name


def normalize_team_name(raw: str, state: Optional[str] = None) -> str:
    """Return a canonical match key: accents folded, lowercase, suffix-stripped.

    "Palmeiras-SP", "Palmeiras", "PALMEIRAS" -> "palmeiras". For the handful of
    base names shared by multiple clubs, the state (from a suffix or the passed
    `state` column) is appended: "Atletico-MG" -> "atletico mg".
    """
    if raw is None:
        return ""
    name, uf = _split_suffix(raw)
    base = _strip_accents(name).lower()
    base = re.sub(r"[^a-z0-9 ]", "", base)
    base = _WS_RE.sub(" ", base).strip()
    uf = uf or (state.strip().upper() if state else None)
    if base in _AMBIGUOUS_BASES and uf in _BR_STATES:
        return f"{base} {uf.lower()}"
    return base


# --------------------------------------------------------------------------- #
# Value coercion
# --------------------------------------------------------------------------- #


def _to_int(value, default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    s = str(value).strip().strip('"')
    if s == "" or s.lower() in ("nan", "none"):
        return default
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return default


def _to_float(value, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    s = str(value).strip().strip('"')
    if s == "" or s.lower() in ("nan", "none"):
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M:%S",
    "%Y/%m/%d",
)


def parse_date(value) -> Optional[date]:
    """Parse the several date formats found across datasets into a date."""
    if value is None:
        return None
    s = str(value).strip().strip('"')
    if s == "" or s.lower() in ("nan", "none"):
        return None
    # Keep only the date portion if a time component is present and space-split.
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Last resort: take leading YYYY-MM-DD or DD/MM/YYYY token.
    token = s.split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(token, fmt).date()
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
# Records
# --------------------------------------------------------------------------- #


@dataclass
class Match:
    """A normalised match record from any of the five match datasets."""

    competition: str
    season: Optional[int]
    date: Optional[date]
    home_team: str  # clean display name
    away_team: str  # clean display name
    home_key: str  # normalized key
    away_key: str  # normalized key
    home_goal: Optional[int]
    away_goal: Optional[int]
    round: Optional[str] = None
    stage: Optional[str] = None
    arena: Optional[str] = None
    home_state: Optional[str] = None
    away_state: Optional[str] = None
    source: str = ""
    # Extended statistics (only present in BR-Football-Dataset).
    stats: dict = field(default_factory=dict)

    @property
    def winner_key(self) -> Optional[str]:
        """Normalized key of the winning team, or None for a draw / unknown."""
        if self.home_goal is None or self.away_goal is None:
            return None
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None  # draw

    @property
    def is_draw(self) -> Optional[bool]:
        if self.home_goal is None or self.away_goal is None:
            return None
        return self.home_goal == self.away_goal

    @property
    def total_goals(self) -> Optional[int]:
        if self.home_goal is None or self.away_goal is None:
            return None
        return self.home_goal + self.away_goal


@dataclass
class Player:
    """A normalised FIFA player record."""

    player_id: Optional[int]
    name: str
    age: Optional[int]
    nationality: Optional[str]
    overall: Optional[int]
    potential: Optional[int]
    club: Optional[str]
    club_key: str
    position: Optional[str]
    jersey_number: Optional[int]
    height: Optional[str]
    weight: Optional[str]
    preferred_foot: Optional[str]
    value: Optional[str]
    wage: Optional[str]


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #


# Source preference when several files cover the same competition+season: lower
# index wins ties. The dedicated league files carry round/state and use a single
# consistent naming scheme, so they are preferred over the aggregate stats file.
_DEDUP_SOURCE_PRIORITY = {
    "Brasileirao_Matches.csv": 0,
    "novo_campeonato_brasileiro.csv": 1,
    "Brazilian_Cup_Matches.csv": 2,
    "Libertadores_Matches.csv": 3,
    "BR-Football-Dataset.csv": 4,
}


def deduplicate_matches(matches: list[Match]) -> list[Match]:
    """Remove cross-file duplication by keeping one authoritative source per
    (competition, season).

    Several datasets overlap heavily — e.g. the 2003-2019 Brasileirão appears in
    the historical file, the main matches file *and* the aggregate stats file —
    and each spells team names differently ("Atletico-MG" vs "Atletico Mineiro").
    A naive fixture-level dedup therefore fails (different keys) and inflates
    every record and standings table. Instead, for each (competition, season) we
    keep only the single source with the most fixtures (ties broken by the
    priority above). This yields a clean, internally consistent fixture set per
    competition-season — the right basis for records, head-to-head and tables."""
    groups: dict[tuple, dict[str, list[Match]]] = {}
    for m in matches:
        groups.setdefault((m.competition, m.season), {}).setdefault(m.source, []).append(m)

    out: list[Match] = []
    for by_source in groups.values():
        best = max(
            by_source,
            key=lambda s: (len(by_source[s]), -_DEDUP_SOURCE_PRIORITY.get(s, 99)),
        )
        out.extend(by_source[best])
    return out


class DataLoader:
    """Loads and normalises all datasets. Use `load_all()` to get matches+players."""

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = data_dir

    # -- helpers ---------------------------------------------------------- #
    def _path(self, name: str) -> str:
        return os.path.join(self.data_dir, name)

    def _read_rows(self, filename: str):
        path = self._path(filename)
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                yield row

    def _make_match(self, *, competition, season, dt, home, away, hg, ag,
                    round_=None, stage=None, arena=None, home_state=None,
                    away_state=None, source="", stats=None) -> Match:
        return Match(
            competition=competition,
            season=_to_int(season),
            date=dt if isinstance(dt, date) else parse_date(dt),
            home_team=clean_team_name(home),
            away_team=clean_team_name(away),
            home_key=normalize_team_name(home, home_state),
            away_key=normalize_team_name(away, away_state),
            home_goal=_to_int(hg),
            away_goal=_to_int(ag),
            round=str(round_).strip() if round_ not in (None, "") else None,
            stage=str(stage).strip() if stage else None,
            arena=str(arena).strip() if arena else None,
            home_state=str(home_state).strip() if home_state else None,
            away_state=str(away_state).strip() if away_state else None,
            source=source,
            stats=stats or {},
        )

    # -- per-file loaders ------------------------------------------------- #
    def load_brasileirao(self):
        for r in self._read_rows("Brasileirao_Matches.csv"):
            yield self._make_match(
                competition=COMP_BRASILEIRAO,
                season=r.get("season"),
                dt=r.get("datetime"),
                home=r.get("home_team"),
                away=r.get("away_team"),
                hg=r.get("home_goal"),
                ag=r.get("away_goal"),
                round_=r.get("round"),
                home_state=r.get("home_team_state"),
                away_state=r.get("away_team_state"),
                source="Brasileirao_Matches.csv",
            )

    def load_copa_brasil(self):
        for r in self._read_rows("Brazilian_Cup_Matches.csv"):
            yield self._make_match(
                competition=COMP_COPA_BRASIL,
                season=r.get("season"),
                dt=r.get("datetime"),
                home=r.get("home_team"),
                away=r.get("away_team"),
                hg=r.get("home_goal"),
                ag=r.get("away_goal"),
                round_=r.get("round"),
                source="Brazilian_Cup_Matches.csv",
            )

    def load_libertadores(self):
        for r in self._read_rows("Libertadores_Matches.csv"):
            yield self._make_match(
                competition=COMP_LIBERTADORES,
                season=r.get("season"),
                dt=r.get("datetime"),
                home=r.get("home_team"),
                away=r.get("away_team"),
                hg=r.get("home_goal"),
                ag=r.get("away_goal"),
                stage=r.get("stage"),
                source="Libertadores_Matches.csv",
            )

    def load_br_football(self):
        # tournament -> canonical competition name
        comp_map = {
            "Serie A": COMP_BRASILEIRAO,
            "Serie B": "Brasileirão Série B",
            "Serie C": "Brasileirão Série C",
            "Copa do Brasil": COMP_COPA_BRASIL,
        }
        for r in self._read_rows("BR-Football-Dataset.csv"):
            dt = parse_date(r.get("date"))
            season = dt.year if dt else None
            tournament = (r.get("tournament") or "").strip()
            stats = {
                "home_corner": _to_float(r.get("home_corner")),
                "away_corner": _to_float(r.get("away_corner")),
                "home_attack": _to_float(r.get("home_attack")),
                "away_attack": _to_float(r.get("away_attack")),
                "home_shots": _to_float(r.get("home_shots")),
                "away_shots": _to_float(r.get("away_shots")),
                "ht_result": r.get("ht_result"),
                "at_result": r.get("at_result"),
                "total_corners": _to_float(r.get("total_corners")),
            }
            yield self._make_match(
                competition=comp_map.get(tournament, tournament or "Unknown"),
                season=season,
                dt=dt,
                home=r.get("home"),
                away=r.get("away"),
                hg=r.get("home_goal"),
                ag=r.get("away_goal"),
                source="BR-Football-Dataset.csv",
                stats=stats,
            )

    def load_novo_brasileirao(self):
        for r in self._read_rows("novo_campeonato_brasileiro.csv"):
            yield self._make_match(
                competition=COMP_BRASILEIRAO,
                season=r.get("Ano"),
                dt=r.get("Data"),
                home=r.get("Equipe_mandante"),
                away=r.get("Equipe_visitante"),
                hg=r.get("Gols_mandante"),
                ag=r.get("Gols_visitante"),
                round_=r.get("Rodada"),
                arena=r.get("Arena"),
                home_state=r.get("Mandante_UF"),
                away_state=r.get("Visitante_UF"),
                source="novo_campeonato_brasileiro.csv",
            )

    def load_players(self):
        for r in self._read_rows("fifa_data.csv"):
            club = (r.get("Club") or "").strip()
            yield Player(
                player_id=_to_int(r.get("ID")),
                name=(r.get("Name") or "").strip(),
                age=_to_int(r.get("Age")),
                nationality=(r.get("Nationality") or "").strip() or None,
                overall=_to_int(r.get("Overall")),
                potential=_to_int(r.get("Potential")),
                club=club or None,
                club_key=normalize_team_name(club),
                position=(r.get("Position") or "").strip() or None,
                jersey_number=_to_int(r.get("Jersey Number")),
                height=(r.get("Height") or "").strip() or None,
                weight=(r.get("Weight") or "").strip() or None,
                preferred_foot=(r.get("Preferred Foot") or "").strip() or None,
                value=(r.get("Value") or "").strip() or None,
                wage=(r.get("Wage") or "").strip() or None,
            )

    # -- aggregate -------------------------------------------------------- #
    def load_matches(self, dedup: bool = True) -> list[Match]:
        matches: list[Match] = []
        matches.extend(self.load_brasileirao())
        matches.extend(self.load_copa_brasil())
        matches.extend(self.load_libertadores())
        matches.extend(self.load_br_football())
        matches.extend(self.load_novo_brasileirao())
        return deduplicate_matches(matches) if dedup else matches

    def load_all(self) -> tuple[list[Match], list[Player]]:
        return self.load_matches(), list(self.load_players())
