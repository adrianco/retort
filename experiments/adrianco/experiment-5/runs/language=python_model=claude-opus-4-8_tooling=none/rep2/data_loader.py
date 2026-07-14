"""
Data-loading layer for the Brazilian Soccer MCP server.

Context
-------
Loads the six pre-downloaded Kaggle CSV files from ``data/kaggle/`` and turns
them into two flat, in-memory collections of typed records:

    * Match  -- a unified match record produced from the five match datasets
                (Brasileirao, Copa do Brasil, Libertadores, the extended
                BR-Football statistics file and the historical 2003-2019 file).
    * Player -- a player record produced from the FIFA player database.

The loader is responsible for the messy parts called out in the specification:
multiple date formats (ISO, ISO+time, DD/MM/YYYY), goals stored as quoted
strings or floats, UTF-8 / BOM encoding and team-name variations.  Team names
are normalized through :mod:`team_names` so downstream queries can match
"Palmeiras-SP", "Palmeiras" and "Sao Paulo FC" consistently.

Only the Python standard library is used here (``csv``) so the data layer and
the test-suite have no third-party dependencies.
"""

from __future__ import annotations

import csv
import datetime as _dt
import os
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from team_names import (
    display_team,
    keys_match,
    split_team,
    team_key,
    _base_key,
    _REGION_CODES as _VALID_REGIONS,
)

# Allow large fields (some legal club names are very long).
csv.field_size_limit(10_000_000)

# Default location of the bundled datasets, relative to this file.
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

# Canonical competition labels.
BRASILEIRAO = "Brasileirao"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Libertadores"


@dataclass
class Match:
    """A single match, unified across every source dataset.

    Team identity is captured by a region-aware ``*_key`` (e.g. "atletico-mg")
    plus the accent-folded ``*_base_key`` and ``*_region`` parts used for
    flexible, region-aware query matching (see :func:`team_names.keys_match`).
    """

    competition: str
    season: Optional[int]
    date: Optional[_dt.date]
    home_team: str            # canonical display name ("Base-REGION")
    away_team: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    home_team_raw: str = ""
    away_team_raw: str = ""
    home_key: str = ""        # region-aware identity key
    away_key: str = ""
    home_base_key: str = ""   # accent-folded base (no region)
    away_base_key: str = ""
    home_region: Optional[str] = None
    away_region: Optional[str] = None
    round: str = ""           # round number or cup/knockout stage
    stage: str = ""
    source: str = ""
    arena: str = ""
    # Optional extended statistics (only present for BR-Football rows).
    stats: dict = field(default_factory=dict)

    # -- derived helpers -------------------------------------------------
    @property
    def total_goals(self) -> Optional[int]:
        if self.home_goal is None or self.away_goal is None:
            return None
        return self.home_goal + self.away_goal

    def is_home(self, team: str) -> bool:
        qb, qr = split_team(team)
        return keys_match(_base_key(qb), qr, self.home_base_key, self.home_region)

    def is_away(self, team: str) -> bool:
        qb, qr = split_team(team)
        return keys_match(_base_key(qb), qr, self.away_base_key, self.away_region)

    def involves(self, team: str) -> bool:
        return self.is_home(team) or self.is_away(team)

    def winner(self) -> Optional[str]:
        """Return the display name of the winning team, or ``None`` for a draw
        (or when the score is unknown)."""
        if self.home_goal is None or self.away_goal is None:
            return None
        if self.home_goal > self.away_goal:
            return self.home_team
        if self.away_goal > self.home_goal:
            return self.away_team
        return None


@dataclass
class Player:
    """A FIFA player record."""

    player_id: str
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    jersey_number: str = ""
    height: str = ""
    weight: str = ""
    value: str = ""
    wage: str = ""
    preferred_foot: str = ""

    @property
    def club_key(self) -> str:
        base, region = split_team(self.club)
        return team_key(base, region)


# ----------------------------------------------------------------------------
# Parsing helpers
# ----------------------------------------------------------------------------
def parse_date(value: str) -> Optional[_dt.date]:
    """Parse the several date formats found across the datasets."""
    if not value:
        return None
    value = value.strip().strip('"')
    if not value:
        return None
    # Drop any time component ("2012-05-19 18:30:00" -> "2012-05-19").
    head = value.split(" ")[0].split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return _dt.datetime.strptime(head, fmt).date()
        except ValueError:
            continue
    return None


def parse_int(value) -> Optional[int]:
    """Parse goals/years that may be quoted strings or floats ("2", "1.0")."""
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if text == "" or text.lower() in {"nan", "na", "none"}:
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def _year_from(season, date: Optional[_dt.date]) -> Optional[int]:
    year = parse_int(season)
    if year is not None:
        return year
    if date is not None:
        return date.year
    return None


# ----------------------------------------------------------------------------
# Per-file loaders
# ----------------------------------------------------------------------------
def _open(path: str):
    # utf-8-sig transparently strips a BOM if present (fifa_data.csv has one).
    return open(path, "r", encoding="utf-8-sig", newline="")


def _resolve_team(raw, state) -> tuple[str, str, str, Optional[str]]:
    """Return (display, key, base_key, region) for a raw name + optional state.

    An explicit state column (when present and valid) takes precedence over any
    region code embedded in the name string.
    """
    base, suffix_region = split_team(raw)
    region = None
    if state:
        st = str(state).strip().upper()
        if st in _VALID_REGIONS:
            region = st
    if region is None:
        region = suffix_region
    return (
        display_team(base, region),
        team_key(base, region),
        _base_key(base),
        region,
    )


def _make_match(competition, season, date, home_raw, away_raw, hg, ag,
                source, round_="", stage="", arena="", stats=None,
                home_state=None, away_state=None) -> Match:
    h_disp, h_key, h_base, h_region = _resolve_team(home_raw, home_state)
    a_disp, a_key, a_base, a_region = _resolve_team(away_raw, away_state)
    return Match(
        competition=competition,
        season=_year_from(season, date),
        date=date,
        home_team=h_disp,
        away_team=a_disp,
        home_goal=parse_int(hg),
        away_goal=parse_int(ag),
        home_team_raw=str(home_raw or ""),
        away_team_raw=str(away_raw or ""),
        home_key=h_key,
        away_key=a_key,
        home_base_key=h_base,
        away_base_key=a_base,
        home_region=h_region,
        away_region=a_region,
        round=str(round_ or ""),
        stage=str(stage or ""),
        source=source,
        arena=str(arena or ""),
        stats=stats or {},
    )


def load_brasileirao(path: str) -> list[Match]:
    matches = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            d = parse_date(row.get("datetime", ""))
            matches.append(_make_match(
                BRASILEIRAO, row.get("season"), d,
                row.get("home_team"), row.get("away_team"),
                row.get("home_goal"), row.get("away_goal"),
                source="Brasileirao_Matches.csv",
                round_=row.get("round", ""),
                home_state=row.get("home_team_state"),
                away_state=row.get("away_team_state"),
            ))
    return matches


def load_cup(path: str) -> list[Match]:
    matches = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            d = parse_date(row.get("datetime", ""))
            matches.append(_make_match(
                COPA_DO_BRASIL, row.get("season"), d,
                row.get("home_team"), row.get("away_team"),
                row.get("home_goal"), row.get("away_goal"),
                source="Brazilian_Cup_Matches.csv",
                round_=row.get("round", ""),
            ))
    return matches


def load_libertadores(path: str) -> list[Match]:
    matches = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            d = parse_date(row.get("datetime", ""))
            matches.append(_make_match(
                LIBERTADORES, row.get("season"), d,
                row.get("home_team"), row.get("away_team"),
                row.get("home_goal"), row.get("away_goal"),
                source="Libertadores_Matches.csv",
                stage=row.get("stage", ""),
            ))
    return matches


# BR-Football tournaments that are already covered (more reliably, with state
# codes and explicit seasons) by the dedicated competition files.  These rows
# are skipped to avoid duplicating the authoritative Brasileirao / Copa graphs;
# the file's UNIQUE contribution is its Serie B and Serie C data.
_BR_FOOTBALL_REDUNDANT = {"Serie A", "Copa do Brasil"}


def load_br_football(path: str) -> list[Match]:
    """Extended statistics file (corners, shots, attacks) for the lower
    divisions.

    The file uses a state-code-free, internally-inconsistent club-naming
    convention ("Botafogo RJ", "EC Bahia", "Sao Paulo"), so its "Serie A" and
    "Copa do Brasil" rows — which merely duplicate the dedicated, region-aware
    competition files — are dropped to keep standings and head-to-head records
    clean.  Its Serie B and Serie C rows exist in no other dataset and are kept,
    along with their extended statistics, demonstrating cross-division and
    statistics queries.
    """
    matches = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            tournament = (row.get("tournament") or "").strip()
            if tournament in _BR_FOOTBALL_REDUNDANT:
                continue
            d = parse_date(row.get("date", ""))
            stats = {
                "home_corner": parse_int(row.get("home_corner")),
                "away_corner": parse_int(row.get("away_corner")),
                "home_shots": parse_int(row.get("home_shots")),
                "away_shots": parse_int(row.get("away_shots")),
                "home_attack": parse_int(row.get("home_attack")),
                "away_attack": parse_int(row.get("away_attack")),
                "total_corners": parse_int(row.get("total_corners")),
            }
            matches.append(_make_match(
                tournament, None, d,
                row.get("home"), row.get("away"),
                row.get("home_goal"), row.get("away_goal"),
                source="BR-Football-Dataset.csv",
                stats=stats,
            ))
    return matches


def load_novo(path: str) -> list[Match]:
    """Historical Brasileirao 2003-2019 (Portuguese column names)."""
    matches = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            d = parse_date(row.get("Data", ""))
            matches.append(_make_match(
                BRASILEIRAO, row.get("Ano"), d,
                row.get("Equipe_mandante"), row.get("Equipe_visitante"),
                row.get("Gols_mandante"), row.get("Gols_visitante"),
                source="novo_campeonato_brasileiro.csv",
                round_=row.get("Rodada", ""),
                arena=row.get("Arena", ""),
                home_state=row.get("Mandante_UF"),
                away_state=row.get("Visitante_UF"),
            ))
    return matches


def load_players(path: str) -> list[Player]:
    players = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            players.append(Player(
                player_id=str(row.get("ID", "")).strip(),
                name=(row.get("Name") or "").strip(),
                age=parse_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=parse_int(row.get("Overall")),
                potential=parse_int(row.get("Potential")),
                club=(row.get("Club") or "").strip(),
                position=(row.get("Position") or "").strip(),
                jersey_number=(row.get("Jersey Number") or "").strip(),
                height=(row.get("Height") or "").strip(),
                weight=(row.get("Weight") or "").strip(),
                value=(row.get("Value") or "").strip(),
                wage=(row.get("Wage") or "").strip(),
                preferred_foot=(row.get("Preferred Foot") or "").strip(),
            ))
    return players


# ----------------------------------------------------------------------------
# Top-level loader
# ----------------------------------------------------------------------------
# Authoritative, region-bearing match files, loaded first.  Their loader order
# also sets de-dupe precedence (richer round-annotated sources win).
_AUTHORITATIVE_LOADERS = {
    "Brasileirao_Matches.csv": load_brasileirao,
    "Brazilian_Cup_Matches.csv": load_cup,
    "Libertadores_Matches.csv": load_libertadores,
    "novo_campeonato_brasileiro.csv": load_novo,
}


def dedupe_matches(matches: list[Match]) -> list[Match]:
    """Collapse the same logical match appearing in more than one source file.

    The five match datasets overlap: the Brasileirao label is carried by
    ``Brasileirao_Matches.csv`` (2012-2022), the historical
    ``novo_campeonato_brasileiro.csv`` (2003-2019) *and* the "Serie A" rows of
    ``BR-Football-Dataset.csv``.  Without de-duplication a single 2019 fixture
    would be counted up to three times, corrupting standings and statistics.

    A real fixture is identified by ``(competition, home_key, away_key)`` plus a
    time anchor, but the sources disagree on which anchor is reliable:

      * the historical file and Brasileirao_Matches agree on *season* but record
        slightly different *dates* for the same game;
      * the BR-Football file has no season column (its season is derived from the
        date, which is wrong for COVID-delayed seasons) but its *dates* match
        Brasileirao_Matches exactly.

    So two matches are considered the same when they share competition + teams
    and EITHER the same season OR the same date.  Both anchors are indexed and
    either hit collapses the duplicate.  The first occurrence wins (loaders run
    authoritative-first), and extended statistics from a dropped duplicate are
    carried onto the survivor.
    """
    by_season: dict[tuple, Match] = {}
    by_date: dict[tuple, Match] = {}
    unique: list[Match] = []
    for m in matches:
        if m.home_goal is None or m.away_goal is None:
            unique.append(m)
            continue
        comp = _base_key(m.competition)
        skey = (comp, m.season, m.home_key, m.away_key) if m.season is not None else None
        dkey = (comp, m.date, m.home_key, m.away_key) if m.date is not None else None

        existing = None
        if skey is not None:
            existing = by_season.get(skey)
        if existing is None and dkey is not None:
            existing = by_date.get(dkey)
        if existing is not None:
            if not existing.stats and m.stats:
                existing.stats = m.stats
            continue

        if skey is not None:
            by_season[skey] = m
        if dkey is not None:
            by_date[dkey] = m
        unique.append(m)
    return unique


# A base name is only assigned an inferred region when one region accounts for
# at least this share of its authoritative appearances.  This resolves big
# clubs that have obscure namesakes (Flamengo-RJ vs Flamengo-PI) while leaving
# genuinely split names (Atletico MG/GO/PR, America MG/RN) ambiguous.
_REGION_DOMINANCE = 0.75


def _build_region_map(matches: list[Match]) -> dict:
    """Map each accent-folded base name to a Counter of the regions it appears
    with in the authoritative (region-bearing) datasets."""
    region_map: dict[str, Counter] = {}
    for m in matches:
        if m.home_region:
            region_map.setdefault(m.home_base_key, Counter())[m.home_region] += 1
        if m.away_region:
            region_map.setdefault(m.away_base_key, Counter())[m.away_region] += 1
    return region_map


def _dominant_region(region_map: Optional[dict], base_key: str,
                     threshold: float = _REGION_DOMINANCE) -> Optional[str]:
    if not region_map:
        return None
    counts = region_map.get(base_key)
    if not counts:
        return None
    region, top = counts.most_common(1)[0]
    if top / sum(counts.values()) >= threshold:
        return region
    return None


# Within the top division (Brasileirao) only the single major club bearing a
# given name ever plays, so the dominant region IS its true region and a source
# mislabel (e.g. the historical file recording "Vitoria-ES" instead of the
# Bahia club, or internally mixing the two) can be corrected.  Copa do Brasil
# and the lower divisions legitimately contain minor namesakes (Botafogo-PB,
# Atletico-GO, America-RN), so their regions are never overridden.  Genuinely
# split top-flight names (Atletico MG/GO/PR) have no dominant region and are
# therefore never touched either.
_OVERRIDE_COMPETITIONS = {"brasileirao"}
_OVERRIDE_DOMINANCE = 0.6


def _apply_inferred_regions(matches: list[Match], region_map: dict) -> None:
    """Normalize regions in place so the same fixture de-duplicates across
    datasets.

    A missing region (blank ``Mandante_UF`` in the historical file) is filled
    from the club's strongly-dominant region.  Inside the top division a present
    but inconsistent region is also corrected to the dominant one.
    """
    def resolve(region, base_key, comp_key):
        if not region:
            return _dominant_region(region_map, base_key)
        if comp_key in _OVERRIDE_COMPETITIONS:
            dom = _dominant_region(region_map, base_key, _OVERRIDE_DOMINANCE)
            if dom and dom != region:
                return dom
        return None

    for m in matches:
        comp_key = _base_key(m.competition)
        new_home = resolve(m.home_region, m.home_base_key, comp_key)
        if new_home:
            base, _ = split_team(m.home_team_raw)
            m.home_region = new_home
            m.home_key = team_key(base, new_home)
            m.home_team = display_team(base, new_home)
        new_away = resolve(m.away_region, m.away_base_key, comp_key)
        if new_away:
            base, _ = split_team(m.away_team_raw)
            m.away_region = new_away
            m.away_key = team_key(base, new_away)
            m.away_team = display_team(base, new_away)


def load_all(data_dir: str = DATA_DIR) -> tuple[list[Match], list[Player]]:
    """Load every dataset found in ``data_dir`` and return (matches, players).

    Missing files are skipped silently so the loader still works if a dataset
    is unavailable, but the bundled repository ships all six files.  The
    authoritative competition files are loaded first; the BR-Football extended
    statistics file is then loaded with region inference so its rows merge onto
    the canonical fixtures.  Matches appearing in more than one source are
    de-duplicated (extended stats are carried onto the surviving row).
    """
    matches: list[Match] = []
    for filename, loader in _AUTHORITATIVE_LOADERS.items():
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            matches.extend(loader(path))

    br_path = os.path.join(data_dir, "BR-Football-Dataset.csv")
    if os.path.exists(br_path):
        matches.extend(load_br_football(br_path))

    # Repair missing regions from the dominant region of each club, then merge
    # the same fixture appearing across multiple source files.
    _apply_inferred_regions(matches, _build_region_map(matches))
    matches = dedupe_matches(matches)

    players: list[Player] = []
    fifa_path = os.path.join(data_dir, "fifa_data.csv")
    if os.path.exists(fifa_path):
        players = load_players(fifa_path)

    return matches, players
