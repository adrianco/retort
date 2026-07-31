"""
CSV readers -- one per required dataset.

Context
-------
Each of the five match files has its own column names, its own date format and
its own way of writing club names.  Every reader here converts a raw CSV row
into a single intermediate :class:`ParsedRow`, and the generic machinery in
:func:`load_matches` turns those into :class:`~brazilian_soccer.models.Match`
objects.  That keeps all per-file quirks in one small function each:

===========================  ==========================================
File                          Quirks handled
===========================  ==========================================
Brasileirao_Matches.csv       state suffix on every club, ``datetime``
Brazilian_Cup_Matches.csv     ``" - UF"`` suffix, ``NA`` scores, numbered
                              rounds that must be named (final, SF, ...)
Libertadores_Matches.csv      country suffix ``(URU)``/``-EQU``, quoted
                              integers, one row with ``NA`` everywhere
BR-Football-Dataset.csv       tournament column drives the competition,
                              floats for goals, extra shot/corner stats
novo_campeonato_brasileiro    Portuguese headers, ``DD/MM/YYYY`` dates,
                              explicit ``Mandante_UF``/``Visitante_UF``
fifa_data.csv                 BOM in the header, 89 columns, ``€`` money
===========================  ==========================================

Club names are resolved in two passes (see
:class:`~brazilian_soccer.teams.TeamRegistry`): every raw spelling is observed
first so the registry can cluster ambiguous names, then rows are converted.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from .config import DATASETS_BY_KEY, dataset_path
from .models import Match, Player
from .teams import TeamRegistry
from .text import is_missing, parse_date, parse_float, parse_int, parse_time

__all__ = [
    "ParsedRow",
    "read_csv",
    "read_all_match_rows",
    "load_matches",
    "load_players",
    "POSITION_GROUPS",
    "position_group",
    "SKILL_COLUMNS",
]


@dataclass(slots=True)
class ParsedRow:
    """Source-agnostic representation of one fixture."""

    competition_id: str
    season: int | None
    date: dt.date | None
    home_raw: str
    away_raw: str
    home_state: str | None = None
    away_state: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    kickoff: str | None = None
    round: str | None = None
    stage: str | None = None
    venue: str | None = None
    stats: dict[str, Any] = field(default_factory=dict)


def read_csv(path: Path, *, encoding: str = "utf-8-sig") -> list[dict[str, str]]:
    """Read a UTF-8 CSV (tolerating a byte-order mark) into a list of dicts."""

    with path.open(newline="", encoding=encoding) as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------------------
# Per-file row parsers
# ---------------------------------------------------------------------------


def _parse_brasileirao(row: dict[str, str]) -> ParsedRow | None:
    """``Brasileirao_Matches.csv`` -- Serie A 2012-2022, state-suffixed names."""

    return ParsedRow(
        competition_id="serie-a",
        season=parse_int(row.get("season")),
        date=parse_date(row.get("datetime")),
        kickoff=parse_time(row.get("datetime")),
        home_raw=(row.get("home_team") or "").strip(),
        away_raw=(row.get("away_team") or "").strip(),
        home_state=(row.get("home_team_state") or "").strip() or None,
        away_state=(row.get("away_team_state") or "").strip() or None,
        home_goals=parse_int(row.get("home_goal")),
        away_goals=parse_int(row.get("away_goal")),
        round=_round_label(row.get("round")),
    )


def _parse_copa_do_brasil(row: dict[str, str]) -> ParsedRow | None:
    """``Brazilian_Cup_Matches.csv`` -- ``NA`` scores and numbered rounds."""

    return ParsedRow(
        competition_id="copa-do-brasil",
        season=parse_int(row.get("season")),
        date=parse_date(row.get("datetime")),
        kickoff=parse_time(row.get("datetime")),
        home_raw=(row.get("home_team") or "").strip(),
        away_raw=(row.get("away_team") or "").strip(),
        home_goals=parse_int(row.get("home_goal")),
        away_goals=parse_int(row.get("away_goal")),
        round=_round_label(row.get("round")),
    )


def _parse_libertadores(row: dict[str, str]) -> ParsedRow | None:
    """``Libertadores_Matches.csv`` -- country-suffixed names, explicit stage."""

    home = (row.get("home_team") or "").strip()
    away = (row.get("away_team") or "").strip()
    if not home or not away:
        return None
    stage = (row.get("stage") or "").strip().lower() or None
    return ParsedRow(
        competition_id="libertadores",
        season=parse_int(row.get("season")),
        date=parse_date(row.get("datetime")),
        kickoff=parse_time(row.get("datetime")),
        home_raw=home,
        away_raw=away,
        home_goals=parse_int(row.get("home_goal")),
        away_goals=parse_int(row.get("away_goal")),
        stage=stage,
    )


_BR_FOOTBALL_COMPETITIONS = {
    "serie a": "serie-a",
    "serie b": "serie-b",
    "serie c": "serie-c",
    "copa do brasil": "copa-do-brasil",
}

_BR_FOOTBALL_STATS = (
    ("home_corner", "home_corners"),
    ("away_corner", "away_corners"),
    ("home_attack", "home_attacks"),
    ("away_attack", "away_attacks"),
    ("home_shots", "home_shots"),
    ("away_shots", "away_shots"),
    ("total_corners", "total_corners"),
)


#: Competitions played as a calendar-year double round robin.
LEAGUE_COMPETITIONS = frozenset({"serie-a", "serie-b", "serie-c"})


def _br_football_season(competition_id: str, date: dt.date | None) -> int | None:
    """Derive the season for a row that only carries a date.

    Brazilian league seasons never start before March, so a January or February
    league fixture belongs to the *previous* season -- that is how the 2020
    Brasileirao, which COVID pushed into February 2021, is filed correctly.
    The Copa do Brasil, by contrast, genuinely starts in February.
    """

    if date is None:
        return None
    if competition_id in LEAGUE_COMPETITIONS and date.month <= 2:
        return date.year - 1
    return date.year


def _parse_br_football(row: dict[str, str]) -> ParsedRow | None:
    """``BR-Football-Dataset.csv`` -- extended stats, competition per row."""

    competition_id = _BR_FOOTBALL_COMPETITIONS.get((row.get("tournament") or "").strip().lower())
    if competition_id is None:
        return None
    date = parse_date(row.get("date"))
    stats: dict[str, Any] = {}
    for column, name in _BR_FOOTBALL_STATS:
        value = parse_float(row.get(column))
        if value is not None:
            stats[name] = value
    for column, name in (("ht_result", "home_half_time_result"),
                         ("at_result", "away_half_time_result")):
        value = (row.get(column) or "").strip()
        if value and not is_missing(value):
            stats[name] = value
    return ParsedRow(
        competition_id=competition_id,
        season=_br_football_season(competition_id, date),
        date=date,
        kickoff=parse_time(row.get("time")),
        home_raw=(row.get("home") or "").strip(),
        away_raw=(row.get("away") or "").strip(),
        home_goals=parse_int(row.get("home_goal")),
        away_goals=parse_int(row.get("away_goal")),
        stats=stats,
    )


def _parse_historical_brasileirao(row: dict[str, str]) -> ParsedRow | None:
    """``novo_campeonato_brasileiro.csv`` -- Portuguese headers, DD/MM/YYYY."""

    venue = (row.get("Arena") or "").strip() or None
    return ParsedRow(
        competition_id="serie-a",
        season=parse_int(row.get("Ano")),
        date=parse_date(row.get("Data")),
        home_raw=(row.get("Equipe_mandante") or "").strip(),
        away_raw=(row.get("Equipe_visitante") or "").strip(),
        home_state=(row.get("Mandante_UF") or "").strip() or None,
        away_state=(row.get("Visitante_UF") or "").strip() or None,
        home_goals=parse_int(row.get("Gols_mandante")),
        away_goals=parse_int(row.get("Gols_visitante")),
        round=_round_label(row.get("Rodada")),
        venue=venue,
    )


def _round_label(value: object) -> str | None:
    number = parse_int(value)
    if number is not None:
        return str(number)
    if is_missing(value):
        return None
    return str(value).strip() or None


ROW_PARSERS: dict[str, Callable[[dict[str, str]], ParsedRow | None]] = {
    "brasileirao": _parse_brasileirao,
    "copa_do_brasil": _parse_copa_do_brasil,
    "libertadores": _parse_libertadores,
    "br_football": _parse_br_football,
    "historical_brasileirao": _parse_historical_brasileirao,
}

#: Preferred provenance when the same fixture appears in several files.  The
#: two dedicated Brasileirao files agree on 100% of overlapping scores; the
#: extended-stats file disagrees on a handful, so it ranks last but still
#: contributes its shot/corner columns.
SOURCE_PRIORITY: dict[str, int] = {
    "brasileirao": 0,
    "historical_brasileirao": 1,
    "copa_do_brasil": 0,
    "libertadores": 0,
    "br_football": 5,
}


# ---------------------------------------------------------------------------
# Cup round naming
# ---------------------------------------------------------------------------

#: Knockout stages, latest first, with the match counts each can have when the
#: tie is played over one or two legs.
_KNOCKOUT_STAGES: tuple[tuple[str, frozenset[int]], ...] = (
    ("final", frozenset({1, 2})),
    ("semifinals", frozenset({2, 4})),
    ("quarterfinals", frozenset({4, 8})),
    ("round of 16", frozenset({8, 16})),
    ("round of 32", frozenset({16, 32})),
)


def _name_cup_rounds(rows: Iterable[ParsedRow]) -> None:
    """Give Copa do Brasil's numbered rounds their knockout names.

    The dataset stores ``round`` only as 1..8 and the number of preliminary
    rounds changed between 2012 and 2021, so names are anchored on how many
    matches each round contains rather than on its number.  That matters for
    incomplete seasons: the 2021 file stops after the round of 16, and naively
    calling the last recorded round "the final" would invent a champion.
    Rounds that do not fit the knockout shape keep a plain ``"round N"`` label.
    """

    cup_rows = [row for row in rows if row.competition_id == "copa-do-brasil"]
    counts: dict[int | None, Counter[int]] = defaultdict(Counter)
    for row in cup_rows:
        number = parse_int(row.round)
        if number is not None:
            counts[row.season][number] += 1

    names: dict[tuple[int | None, int], str] = {}
    for season, round_counts in counts.items():
        stage_index: int | None = None
        chain_broken = False
        # Walk from the last recorded round backwards, anchoring the chain on
        # whichever knockout stage the final round's size fits.
        for number in sorted(round_counts, reverse=True):
            size = round_counts[number]
            if not chain_broken and stage_index is None:
                stage_index = next(
                    (index for index, (_, sizes) in enumerate(_KNOCKOUT_STAGES)
                     if size in sizes),
                    None,
                )
            fits = (
                stage_index is not None
                and stage_index < len(_KNOCKOUT_STAGES)
                and size in _KNOCKOUT_STAGES[stage_index][1]
            )
            if not fits:
                names[(season, number)] = f"round {number}"
                stage_index = None
                chain_broken = True
                continue
            names[(season, number)] = _KNOCKOUT_STAGES[stage_index][0]
            stage_index += 1

    for row in cup_rows:
        number = parse_int(row.round)
        if number is not None:
            row.stage = names.get((row.season, number))


# ---------------------------------------------------------------------------
# Public loading API
# ---------------------------------------------------------------------------


def read_all_match_rows(keys: Iterable[str] | None = None) -> dict[str, list[ParsedRow]]:
    """Read and parse every match dataset, keyed by dataset key."""

    selected = [
        key for key in (keys if keys is not None else ROW_PARSERS)
        if DATASETS_BY_KEY[key].kind == "matches"
    ]
    parsed: dict[str, list[ParsedRow]] = {}
    for key in selected:
        path = dataset_path(key)
        if not path.exists():
            parsed[key] = []
            continue
        parser = ROW_PARSERS[key]
        rows: list[ParsedRow] = []
        for raw in read_csv(path):
            row = parser(raw)
            if row is None or not row.home_raw or not row.away_raw:
                continue
            rows.append(row)
        _name_cup_rounds(rows)
        parsed[key] = rows
    return parsed


def load_matches(registry: TeamRegistry,
                 parsed: dict[str, list[ParsedRow]] | None = None,
                 *, rejected: list[ParsedRow] | None = None) -> list[Match]:
    """Resolve club names and materialise :class:`Match` objects.

    ``registry`` is populated in two passes: all raw names are observed first so
    ambiguous bases can be clustered, then the rows are converted.

    Rows where both sides resolve to the same club are dropped and collected in
    ``rejected``.  The Copa do Brasil file really does contain two such rows
    (2019 round 3 lists "Bragantino - PA" as both home and away); counting them
    would hand one club a free win and a free loss.
    """

    parsed = read_all_match_rows() if parsed is None else parsed

    for key, rows in parsed.items():
        for row in rows:
            registry.observe(row.home_raw, state=row.home_state,
                             competition_id=row.competition_id)
            registry.observe(row.away_raw, state=row.away_state,
                             competition_id=row.competition_id)
    registry.build()

    matches: list[Match] = []
    for key in sorted(parsed):
        for index, row in enumerate(parsed[key]):
            home_id = registry.resolve_id(row.home_raw, state=row.home_state)
            away_id = registry.resolve_id(row.away_raw, state=row.away_state)
            if home_id == away_id:
                if rejected is not None:
                    rejected.append(row)
                continue
            season = row.season if row.season is not None else (
                row.date.year if row.date else None
            )
            matches.append(
                Match(
                    id=f"{key}:{index}",
                    competition_id=row.competition_id,
                    season=season,
                    date=row.date,
                    kickoff=row.kickoff,
                    round=row.round,
                    stage=row.stage,
                    venue=row.venue,
                    home_team_id=home_id,
                    away_team_id=away_id,
                    home_team_raw=row.home_raw,
                    away_team_raw=row.away_raw,
                    home_goals=row.home_goals,
                    away_goals=row.away_goals,
                    sources=[key],
                    stats=dict(row.stats),
                )
            )
    return matches


# ---------------------------------------------------------------------------
# FIFA players
# ---------------------------------------------------------------------------

SKILL_COLUMNS: tuple[str, ...] = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)

POSITION_GROUPS: dict[str, tuple[str, ...]] = {
    "goalkeeper": ("GK",),
    "defender": ("CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"),
    "midfielder": ("CDM", "LDM", "RDM", "CM", "LCM", "RCM", "LM", "RM",
                   "CAM", "LAM", "RAM"),
    "forward": ("CF", "LF", "RF", "ST", "LS", "RS", "LW", "RW"),
}

_POSITION_TO_GROUP: dict[str, str] = {
    position: group for group, positions in POSITION_GROUPS.items() for position in positions
}

#: Words an LLM is likely to use for a position group.
POSITION_GROUP_ALIASES: dict[str, str] = {
    "gk": "goalkeeper", "goalkeeper": "goalkeeper", "goalkeepers": "goalkeeper",
    "keeper": "goalkeeper", "goleiro": "goalkeeper",
    "def": "defender", "defender": "defender", "defenders": "defender",
    "defence": "defender", "defense": "defender", "zagueiro": "defender",
    "back": "defender", "fullback": "defender", "centre-back": "defender",
    "mid": "midfielder", "midfield": "midfielder", "midfielder": "midfielder",
    "midfielders": "midfielder", "meia": "midfielder",
    "fw": "forward", "forward": "forward", "forwards": "forward",
    "attacker": "forward", "attackers": "forward", "striker": "forward",
    "strikers": "forward", "winger": "forward", "wingers": "forward",
    "atacante": "forward",
}


def position_group(position: str | None) -> str | None:
    """Map a FIFA position code (``"LW"``) to a group (``"forward"``)."""

    if not position:
        return None
    return _POSITION_TO_GROUP.get(position.strip().upper())


def load_players(registry: TeamRegistry,
                 linkable_team_ids: set[str] | None = None) -> list[Player]:
    """Read ``fifa_data.csv`` and link clubs to canonical teams where possible.

    ``linkable_team_ids`` restricts which clubs a FIFA club string may bind to.
    The FIFA 19 database only contains top-division squads, so passing the set
    of clubs that have played Serie A stops "Boavista FC" of Porto -- which
    normalises to the same key as Boavista of Rio, a Copa do Brasil minnow --
    from acquiring 27 Portuguese players.
    """

    path = dataset_path("fifa_players")
    if not path.exists():
        return []

    players: list[Player] = []
    for row in read_csv(path):
        player_id = parse_int(row.get("ID"))
        name = (row.get("Name") or "").strip()
        if player_id is None or not name:
            continue
        club_raw = (row.get("Club") or "").strip() or None
        club_team = registry.lookup(club_raw, brazilian_only=True) if club_raw else None
        if club_team is not None and linkable_team_ids is not None:
            if club_team.id not in linkable_team_ids:
                club_team = None
        skills = {}
        for column in SKILL_COLUMNS:
            value = parse_int(row.get(column))
            if value is not None:
                skills[column] = value
        players.append(
            Player(
                id=player_id,
                name=name,
                age=parse_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip() or None,
                overall=parse_int(row.get("Overall")),
                potential=parse_int(row.get("Potential")),
                club_raw=club_raw,
                club_team_id=club_team.id if club_team else None,
                position=(row.get("Position") or "").strip() or None,
                jersey_number=parse_int(row.get("Jersey Number")),
                height=(row.get("Height") or "").strip() or None,
                weight=(row.get("Weight") or "").strip() or None,
                value=(row.get("Value") or "").strip() or None,
                wage=(row.get("Wage") or "").strip() or None,
                preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                work_rate=(row.get("Work Rate") or "").strip() or None,
                joined=(row.get("Joined") or "").strip() or None,
                contract_valid_until=(row.get("Contract Valid Until") or "").strip() or None,
                skills=skills,
            )
        )
    return players


def iter_source_keys() -> Iterator[str]:
    """Dataset keys that contribute matches, in priority order."""

    yield from sorted(ROW_PARSERS, key=lambda key: SOURCE_PRIORITY.get(key, 99))
