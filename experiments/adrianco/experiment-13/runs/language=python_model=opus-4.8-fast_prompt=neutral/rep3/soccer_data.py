"""
=============================================================================
 Brazilian Soccer MCP Server -- Data Layer
=============================================================================
 Purpose
 -------
 Loads the six provided Kaggle CSV datasets into a single, normalized
 in-memory knowledge base of `Match` and `Player` records. This module is
 the foundation that the query engine (`soccer_queries.py`) and the MCP
 server (`server.py`) build on.

 Design notes
 ------------
 * Pure standard library (csv, dataclasses, datetime, unicodedata, re) so
   the data layer has zero third-party dependencies and is trivially
   testable. The only external dependency in the project is the `mcp`
   package, used solely by `server.py`.
 * Team names are normalized to strip state/country suffixes ("Palmeiras-SP"
   -> "Palmeiras", "Nacional (URU)" -> "Nacional") and matched
   accent-insensitively so that "sao paulo", "São Paulo" and
   "Sport Club Corinthians Paulista" all resolve correctly.
 * Multiple date formats are handled (ISO, ISO+time, Brazilian DD/MM/YYYY).
 * Each source file maps onto a named competition; the BR-Football dataset
   carries its competition in a `tournament` column.

 Source files (in data/kaggle/):
   Brasileirao_Matches.csv          -> Brasileirão Série A
   Brazilian_Cup_Matches.csv        -> Copa do Brasil
   Libertadores_Matches.csv         -> Copa Libertadores
   BR-Football-Dataset.csv          -> Série A/B/C, Copa do Brasil (extended stats)
   novo_campeonato_brasileiro.csv   -> Brasileirão Série A (2003-2019)
   fifa_data.csv                    -> FIFA player database
=============================================================================
"""

from __future__ import annotations

import csv
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable, Optional

# --------------------------------------------------------------------------
# Locations
# --------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

# The broad, calendar-year-seasoned dataset used only to fill coverage gaps.
BROAD_SOURCE = "BR-Football-Dataset.csv"


# --------------------------------------------------------------------------
# Text / name normalization helpers
# --------------------------------------------------------------------------

# Parenthetical content, e.g. "Nacional (URU)" or "Boavista (antigo ...)".
_PAREN_RE = re.compile(r"\s*\([^)]*\)")
# A trailing 2-3 letter state/country code following a dash: "-SP", " - RJ",
# "-EQU", "Atlético - MG".
_DASH_STATE_RE = re.compile(r"\s*-\s*([A-Za-z]{2,3})\.?\s*$")
# A trailing parenthesised country code: "Nacional (URU)".
_PAREN_STATE_RE = re.compile(r"\(\s*([A-Za-z]{2,4})\s*\)\s*$")
_WS_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]")

# Base names that are NOT unique on their own -- the state/country code is part
# of the club's identity (Atlético-MG vs Atlético-PR vs Atlético-GO). For these
# the canonical key keeps the state so the three clubs stay distinct.
_AMBIGUOUS_BASES = {"atletico", "america", "nacional"}

# Full names (as they appear in BR-Football-Dataset.csv, which carries no state
# suffix) mapped onto the suffixed canonical key used everywhere else.
_FULL_NAME_ALIASES = {
    "atletico mineiro": "atletico mg",
    "atletico paranaense": "atletico pr",
    "athletico paranaense": "atletico pr",
    "atletico goianiense": "atletico go",
    "atletico cearense": "atletico ce",
    "america mineiro": "america mg",
    "america de natal": "america rn",
    # Long/short and rebrand variants of the same club (exact-key, so they do
    # NOT merge distinct clubs that merely share a word, e.g. Grêmio Prudente).
    "vasco da gama": "vasco",
    "vasco da gama rj": "vasco",
    "botafogo rj": "botafogo",
    "fortaleza fc": "fortaleza",
    "ec bahia": "bahia",
    "red bull bragantino": "bragantino",
}

# Preferred display strings for the disambiguated clubs.
_CANON_DISPLAY = {
    "atletico mg": "Atlético-MG",
    "atletico pr": "Atlético-PR",
    "atletico go": "Atlético-GO",
    "atletico ce": "Atlético-CE",
    "america mg": "América-MG",
    "america rn": "América-RN",
}

# Short club names used for *fuzzy user-query* matching only (see
# `team_matches`). These are deliberately NOT applied inside `canonical_key`:
# substring collapsing there would merge genuinely distinct clubs that share a
# word (e.g. "Grêmio" and "Grêmio Prudente"), corrupting standings. The strict
# identity key relies on suffix handling plus the explicit `_FULL_NAME_ALIASES`.
_FUZZY_ALIASES = [
    "corinthians", "palmeiras", "sao paulo", "flamengo", "fluminense",
    "botafogo", "vasco", "gremio", "internacional", "cruzeiro", "santos",
    "fortaleza", "coritiba", "goias", "bahia", "ceara", "chapecoense",
]


def strip_accents(text: str) -> str:
    """Return *text* with diacritics removed (São -> Sao)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def split_team(raw: str) -> tuple:
    """Split a raw team string into (clean_base_name, state_or_country_code).

    Handles "Palmeiras-SP", "América - MG", "Nacional (URU)" and removes any
    other parenthetical notes. Accents and casing of the base are preserved.
    """
    if raw is None:
        return "", ""
    s = str(raw).strip()
    state = ""
    pm = _PAREN_STATE_RE.search(s)
    if pm:
        state = pm.group(1)
        s = s[: pm.start()]
    s = _PAREN_RE.sub("", s)          # drop any remaining parentheticals
    dm = _DASH_STATE_RE.search(s)
    if dm:
        state = dm.group(1)
        s = s[: dm.start()]
    s = _WS_RE.sub(" ", s).strip(" -")
    return s, state.upper()


def _base_key(base: str) -> str:
    key = strip_accents(base).lower()
    key = _NON_ALNUM_RE.sub(" ", key)
    key = _WS_RE.sub(" ", key).strip()
    # "Athletico Paranaense" is the club's own spelling; fold it onto the
    # "Atlético" form used by the other datasets.
    key = re.sub(r"\bathletico\b", "atletico", key)
    return key


def canonical_key(name: str) -> str:
    """Identity key for a team: accent-insensitive, state-aware, de-aliased.

    Two raw strings referring to the same club yield the same key even across
    datasets with different naming conventions; genuinely different clubs that
    merely share a base name (the Atléticos) keep distinct keys.
    """
    base, state = split_team(name)
    key = _base_key(base)
    if key in _FULL_NAME_ALIASES:
        return _FULL_NAME_ALIASES[key]
    if key in _AMBIGUOUS_BASES and state:
        return f"{key} {state.lower()}"
    return key


def normalize_team_name(raw: str) -> str:
    """Human-readable display name for a raw team string."""
    base, state = split_team(raw)
    ck = canonical_key(raw)
    if ck in _CANON_DISPLAY:
        return _CANON_DISPLAY[ck]
    if not base:
        return ""
    # Keep the state on ambiguous bases that lack a curated display string.
    if _base_key(base) in _AMBIGUOUS_BASES and state:
        return f"{base}-{state}"
    return base


def team_key(name: str) -> str:
    """Backwards-compatible alias for :func:`canonical_key`."""
    return canonical_key(name)


def _fuzzy_key(name: str) -> str:
    """Looser key for user-query matching: collapse a known short club name."""
    key = canonical_key(name)
    for alias in _FUZZY_ALIASES:
        if alias in key:
            return alias
    return key


def team_matches(query: str, team_name: str) -> bool:
    """True if *query* refers to *team_name* (fuzzy, accent-insensitive).

    Used for query recall only -- never for identity/standings grouping, so a
    little over-matching here is acceptable and keeps lookups forgiving.
    """
    qk = canonical_key(query)
    tk = canonical_key(team_name)
    if not qk or not tk:
        return False
    if qk == tk or qk in tk or tk in qk:
        return True
    return _fuzzy_key(query) == _fuzzy_key(team_name)


# --------------------------------------------------------------------------
# Date parsing
# --------------------------------------------------------------------------

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
)


def parse_date(raw: str) -> Optional[date]:
    """Parse the several date formats present in the datasets; None if unknown."""
    if not raw:
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    # Last resort: leading ISO date inside a longer string.
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _to_int(raw) -> Optional[int]:
    """Best-effort integer conversion (handles '2', '2.0', '', None)."""
    if raw is None or raw == "":
        return None
    try:
        return int(float(raw))
    except (ValueError, TypeError):
        return None


# --------------------------------------------------------------------------
# Data models
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Match:
    """A single normalized match record from any of the match datasets."""

    competition: str
    season: Optional[int]
    date: Optional[date]
    home_team: str
    away_team: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    stage: str = ""          # cup round / tournament stage / league round
    source: str = ""         # originating CSV file
    home_state: str = ""
    away_state: str = ""
    arena: str = ""

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def total_goals(self) -> Optional[int]:
        if not self.has_score:
            return None
        return self.home_goal + self.away_goal

    def winner(self) -> Optional[str]:
        """Return the winning team's display name, or None for a draw/unknown."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return self.home_team
        if self.away_goal > self.home_goal:
            return self.away_team
        return None  # draw

    def involves(self, team_query: str) -> bool:
        return team_matches(team_query, self.home_team) or team_matches(
            team_query, self.away_team
        )

    def score_str(self) -> str:
        if not self.has_score:
            return "vs"
        return f"{self.home_goal}-{self.away_goal}"

    def describe(self) -> str:
        when = self.date.isoformat() if self.date else (str(self.season) or "?")
        comp = self.competition
        if self.stage:
            comp = f"{comp} {self.stage}"
        return (
            f"{when}: {self.home_team} {self.score_str()} {self.away_team} "
            f"({comp})"
        )


@dataclass(frozen=True)
class Player:
    """A FIFA player record (subset of the most useful columns)."""

    player_id: Optional[int]
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    value: str = ""
    wage: str = ""
    preferred_foot: str = ""
    height: str = ""
    weight: str = ""
    jersey_number: str = ""

    def describe(self) -> str:
        bits = [self.name]
        if self.overall is not None:
            bits.append(f"Overall: {self.overall}")
        if self.position:
            bits.append(f"Position: {self.position}")
        if self.club:
            bits.append(f"Club: {self.club}")
        return " - ".join([bits[0]] + bits[1:]) if len(bits) > 1 else bits[0]


# --------------------------------------------------------------------------
# Loaders -- one function per file, all returning List[Match]
# --------------------------------------------------------------------------


def _open(path: str):
    # utf-8-sig transparently strips the BOM present in some files.
    return open(path, "r", encoding="utf-8-sig", newline="")


def _load_brasileirao(path: str) -> Iterable[Match]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            yield Match(
                competition="Brasileirão Série A",
                season=_to_int(row.get("season")),
                date=parse_date(row.get("datetime")),
                home_team=normalize_team_name(row.get("home_team")),
                away_team=normalize_team_name(row.get("away_team")),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                stage=f"Round {row.get('round')}" if row.get("round") else "",
                source="Brasileirao_Matches.csv",
                home_state=(row.get("home_team_state") or "").strip(),
                away_state=(row.get("away_team_state") or "").strip(),
            )


def _load_cup(path: str) -> Iterable[Match]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            yield Match(
                competition="Copa do Brasil",
                season=_to_int(row.get("season")),
                date=parse_date(row.get("datetime")),
                home_team=normalize_team_name(row.get("home_team")),
                away_team=normalize_team_name(row.get("away_team")),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                stage=(row.get("round") or "").strip(),
                source="Brazilian_Cup_Matches.csv",
            )


def _load_libertadores(path: str) -> Iterable[Match]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            yield Match(
                competition="Copa Libertadores",
                season=_to_int(row.get("season")),
                date=parse_date(row.get("datetime")),
                home_team=normalize_team_name(row.get("home_team")),
                away_team=normalize_team_name(row.get("away_team")),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                stage=(row.get("stage") or "").strip(),
                source="Libertadores_Matches.csv",
            )


_BR_FOOTBALL_COMP = {
    "Serie A": "Brasileirão Série A",
    "Serie B": "Brasileirão Série B",
    "Serie C": "Brasileirão Série C",
    "Copa do Brasil": "Copa do Brasil",
}


def _load_br_football(path: str) -> Iterable[Match]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            d = parse_date(row.get("date"))
            tournament = (row.get("tournament") or "").strip()
            yield Match(
                competition=_BR_FOOTBALL_COMP.get(tournament, tournament or "Unknown"),
                season=d.year if d else None,
                date=d,
                home_team=normalize_team_name(row.get("home")),
                away_team=normalize_team_name(row.get("away")),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                stage="",
                source="BR-Football-Dataset.csv",
            )


def _load_novo(path: str) -> Iterable[Match]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            yield Match(
                competition="Brasileirão Série A",
                season=_to_int(row.get("Ano")),
                date=parse_date(row.get("Data")),
                home_team=normalize_team_name(row.get("Equipe_mandante")),
                away_team=normalize_team_name(row.get("Equipe_visitante")),
                home_goal=_to_int(row.get("Gols_mandante")),
                away_goal=_to_int(row.get("Gols_visitante")),
                stage=f"Round {row.get('Rodada')}" if row.get("Rodada") else "",
                source="novo_campeonato_brasileiro.csv",
                home_state=(row.get("Mandante_UF") or "").strip(),
                away_state=(row.get("Visitante_UF") or "").strip(),
                arena=(row.get("Arena") or "").strip(),
            )


def _load_players(path: str) -> Iterable[Player]:
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            yield Player(
                player_id=_to_int(row.get("ID")),
                name=(row.get("Name") or "").strip(),
                age=_to_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=_to_int(row.get("Overall")),
                potential=_to_int(row.get("Potential")),
                club=(row.get("Club") or "").strip(),
                position=(row.get("Position") or "").strip(),
                value=(row.get("Value") or "").strip(),
                wage=(row.get("Wage") or "").strip(),
                preferred_foot=(row.get("Preferred Foot") or "").strip(),
                height=(row.get("Height") or "").strip(),
                weight=(row.get("Weight") or "").strip(),
                jersey_number=(row.get("Jersey Number") or "").strip(),
            )


_MATCH_LOADERS = {
    "Brasileirao_Matches.csv": _load_brasileirao,
    "Brazilian_Cup_Matches.csv": _load_cup,
    "Libertadores_Matches.csv": _load_libertadores,
    "BR-Football-Dataset.csv": _load_br_football,
    "novo_campeonato_brasileiro.csv": _load_novo,
}


# --------------------------------------------------------------------------
# Database container
# --------------------------------------------------------------------------


def _dedupe_matches(matches: list) -> list:
    """Collapse the same fixture appearing in multiple source files.

    The Brasileirão and Copa do Brasil overlap across several datasets
    (e.g. a 2019 Série A fixture lives in Brasileirao_Matches.csv,
    novo_campeonato_brasileiro.csv *and* BR-Football-Dataset.csv). Without
    de-duplication, computed standings and aggregate stats are inflated 2-3x.

    A fixture is keyed by (competition, season, home, away, score). Home/away
    ordering distinguishes the two legs of a double round-robin, so distinct
    matches are preserved. When duplicates are found we keep the record
    carrying the most information (a real date, then a round/stage label).
    """
    best: dict = {}
    order: list = []

    def richness(m: "Match") -> tuple:
        return (1 if m.date else 0, 1 if m.stage else 0, 1 if m.arena else 0)

    for m in matches:
        key = (
            m.competition,
            m.season,
            canonical_key(m.home_team),
            canonical_key(m.away_team),
            m.home_goal,
            m.away_goal,
        )
        if key not in best:
            best[key] = m
            order.append(key)
        elif richness(m) > richness(best[key]):
            best[key] = m
    return [best[k] for k in order]


@dataclass
class SoccerDatabase:
    """In-memory store of all matches and players with simple indexes."""

    matches: list = field(default_factory=list)
    players: list = field(default_factory=list)

    @classmethod
    def load(cls, data_dir: str = DATA_DIR, dedupe: bool = True) -> "SoccerDatabase":
        primary: list = []
        broad: list = []
        for fname, loader in _MATCH_LOADERS.items():
            path = os.path.join(data_dir, fname)
            if not os.path.exists(path):
                continue
            # BR-Football is a broad multi-tournament dataset that dates seasons
            # by calendar year and uses its own team spellings. The other files
            # are curated, single-competition and season-labelled, so we treat
            # them as authoritative and use BR-Football only to fill the
            # competition/season gaps it uniquely covers (notably Série B & C).
            (broad if fname == BROAD_SOURCE else primary).extend(loader(path))
        if dedupe:
            covered = {(m.competition, m.season) for m in primary}
            broad = [m for m in broad if (m.competition, m.season) not in covered]
            matches = _dedupe_matches(primary + broad)
        else:
            matches = primary + broad
        players: list = []
        player_path = os.path.join(data_dir, "fifa_data.csv")
        if os.path.exists(player_path):
            players.extend(_load_players(player_path))
        return cls(matches=matches, players=players)

    # -- convenience accessors -------------------------------------------
    def competitions(self) -> list:
        return sorted({m.competition for m in self.matches})

    def seasons(self) -> list:
        return sorted({m.season for m in self.matches if m.season is not None})

    def summary(self) -> dict:
        return {
            "total_matches": len(self.matches),
            "total_players": len(self.players),
            "competitions": self.competitions(),
            "season_range": (
                [min(self.seasons()), max(self.seasons())] if self.seasons() else []
            ),
            "sources": sorted({m.source for m in self.matches}),
        }


# Module-level lazy singleton so the (slightly expensive) load happens once.
_DB: Optional[SoccerDatabase] = None


def get_db(data_dir: str = DATA_DIR) -> SoccerDatabase:
    global _DB
    if _DB is None:
        _DB = SoccerDatabase.load(data_dir)
    return _DB
