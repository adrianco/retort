"""CSV readers -- one function per provided dataset.

Context
-------
Each loader turns one file in ``data/kaggle/`` into ``Match`` or ``Player``
objects with canonical team slugs, canonical competition slugs and parsed
dates/scores.  Loaders do **not** deduplicate: overlapping fixtures are
reconciled later in :mod:`brazilian_soccer.graph`, which needs to see every
source row in order to merge the extra columns each file contributes.

Source priority (most authoritative first) is declared in :data:`SOURCES` and
is what the graph uses when the same fixture appears in several files:

1. ``Brasileirao_Matches.csv``        Série A 2012-2022, has round numbers
2. ``novo_campeonato_brasileiro.csv`` Série A 2003-2019, has stadium names
3. ``Brazilian_Cup_Matches.csv``      Copa do Brasil 2012-2021, has round
4. ``Libertadores_Matches.csv``       Libertadores 2013-2022, has stage
5. ``BR-Football-Dataset.csv``        Série A/B/C + Copa do Brasil 2014-2023,
                                      has corners/shots/attacks and is the only
                                      source for Série B, Série C and 2023
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from .clubs import resolve_club
from .models import Match, Player
from .normalization import (
    normalize_text,
    parse_date,
    parse_int,
    parse_float,
    parse_season,
    parse_time,
)

__all__ = [
    "DataSource",
    "SOURCES",
    "default_data_dir",
    "load_all_matches",
    "load_players",
    "load_brasileirao",
    "load_historical_brasileirao",
    "load_copa_do_brasil",
    "load_libertadores",
    "load_br_football",
]


def default_data_dir() -> Path:
    """Locate the ``data/kaggle`` directory holding the six CSV files.

    Checked in order: ``$BR_SOCCER_DATA``, the repository checkout next to this
    package, the package directory itself, and finally the current working
    directory -- which is what makes a non-editable ``pip install`` usable as
    long as the server is started from a directory containing ``data/kaggle``.
    """
    env = os.environ.get("BR_SOCCER_DATA")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve().parent
    candidates = (
        here.parent / "data" / "kaggle",
        here / "data" / "kaggle",
        Path.cwd() / "data" / "kaggle",
        Path.cwd(),
    )
    for candidate in candidates:
        if (candidate / "Brasileirao_Matches.csv").is_file():
            return candidate
    return here.parent / "data" / "kaggle"


def _rows(path: Path) -> Iterator[dict[str, str]]:
    """Yield dict rows from a UTF-8 CSV, tolerating a BOM in the header."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def _team_fields(raw: str) -> tuple[str, str, str]:
    """Return ``(slug, canonical_name, raw)`` for a raw team string."""
    identity = resolve_club(raw)
    return identity.slug, identity.name, (raw or "").strip()


# ---------------------------------------------------------------------------
# 1. Brasileirao_Matches.csv
# ---------------------------------------------------------------------------

def load_brasileirao(data_dir: Path) -> list[Match]:
    """Série A 2012-2022 with round numbers and team states."""
    path = data_dir / "Brasileirao_Matches.csv"
    matches: list[Match] = []
    for index, row in enumerate(_rows(path)):
        home_slug, home_name, home_raw = _team_fields(row["home_team"])
        away_slug, away_name, away_raw = _team_fields(row["away_team"])
        matches.append(
            Match(
                match_id=f"bra-{index:05d}",
                competition="serie-a",
                season=parse_season(row.get("season")),
                date=parse_date(row.get("datetime")),
                kickoff=parse_time(row.get("datetime")),
                home_slug=home_slug,
                away_slug=away_slug,
                home_name=home_name,
                away_name=away_name,
                home_raw=home_raw,
                away_raw=away_raw,
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                round=(row.get("round") or "").strip() or None,
                sources=("Brasileirao_Matches.csv",),
            )
        )
    return matches


# ---------------------------------------------------------------------------
# 2. novo_campeonato_brasileiro.csv
# ---------------------------------------------------------------------------

def load_historical_brasileirao(data_dir: Path) -> list[Match]:
    """Série A 2003-2019 with stadium names and Portuguese column headers."""
    path = data_dir / "novo_campeonato_brasileiro.csv"
    matches: list[Match] = []
    for index, row in enumerate(_rows(path)):
        home_slug, home_name, home_raw = _team_fields(row["Equipe_mandante"])
        away_slug, away_name, away_raw = _team_fields(row["Equipe_visitante"])
        matches.append(
            Match(
                match_id=f"hist-{index:05d}",
                competition="serie-a",
                season=parse_season(row.get("Ano")),
                date=parse_date(row.get("Data")),
                home_slug=home_slug,
                away_slug=away_slug,
                home_name=home_name,
                away_name=away_name,
                home_raw=home_raw,
                away_raw=away_raw,
                home_goals=parse_int(row.get("Gols_mandante")),
                away_goals=parse_int(row.get("Gols_visitante")),
                round=(row.get("Rodada") or "").strip() or None,
                venue=(row.get("Arena") or "").strip() or None,
                sources=("novo_campeonato_brasileiro.csv",),
            )
        )
    return matches


# ---------------------------------------------------------------------------
# 3. Brazilian_Cup_Matches.csv
# ---------------------------------------------------------------------------

#: Copa do Brasil ties are two-legged from the round of 16 onwards, so the
#: number of fixtures in a round tells us which stage it is: 2 fixtures is the
#: one two-legged final, 4 the semifinals, and so on.
_CUP_STAGE_BY_FIXTURE_COUNT = {
    2: "Final",
    4: "Semifinals",
    8: "Quarterfinals",
    16: "Round of 16",
    32: "Round of 32",
}

#: Only the last five rounds of an edition are labelled from the ladder above.
#: Preliminary rounds can coincidentally contain 16 or 32 fixtures.
_CUP_LADDER_DEPTH = 4


def load_copa_do_brasil(data_dir: Path) -> list[Match]:
    """Copa do Brasil 2012-2021.

    The ``round`` column is a bare number whose meaning shifts between
    editions -- 2012's final is round 6, 2016's is round 7, 2017-2020's is
    round 8, and 2021's data stops at round 4.  Deriving the stage from the
    *number of fixtures in the round* is stable across all of them, which is
    what makes "find all Copa do Brasil finals" answerable.
    """
    path = data_dir / "Brazilian_Cup_Matches.csv"
    matches: list[Match] = []
    raw_rows = list(_rows(path))

    per_season_max: dict[int | None, int] = {}
    fixtures_per_round: dict[tuple[int | None, int], int] = {}
    for row in raw_rows:
        season = parse_season(row.get("season"))
        value = parse_int(row.get("round"))
        if value is None:
            continue
        per_season_max[season] = max(per_season_max.get(season, 0), value)
        key = (season, value)
        fixtures_per_round[key] = fixtures_per_round.get(key, 0) + 1

    for index, row in enumerate(raw_rows):
        season = parse_season(row.get("season"))
        home_slug, home_name, home_raw = _team_fields(row["home_team"])
        away_slug, away_name, away_raw = _team_fields(row["away_team"])
        round_value = parse_int(row.get("round"))
        stage = None
        if round_value is not None:
            last = per_season_max.get(season, round_value)
            count = fixtures_per_round.get((season, round_value), 0)
            if round_value >= last - _CUP_LADDER_DEPTH:
                stage = _CUP_STAGE_BY_FIXTURE_COUNT.get(count)
            if stage is None:
                stage = f"Round {round_value}"
        matches.append(
            Match(
                match_id=f"cup-{index:05d}",
                competition="copa-do-brasil",
                season=season,
                date=parse_date(row.get("datetime")),
                kickoff=parse_time(row.get("datetime")),
                home_slug=home_slug,
                away_slug=away_slug,
                home_name=home_name,
                away_name=away_name,
                home_raw=home_raw,
                away_raw=away_raw,
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                round=(row.get("round") or "").strip() or None,
                stage=stage,
                sources=("Brazilian_Cup_Matches.csv",),
            )
        )
    return matches


# ---------------------------------------------------------------------------
# 4. Libertadores_Matches.csv
# ---------------------------------------------------------------------------

_STAGE_TITLES = {
    "group stage": "Group stage",
    "round of 16": "Round of 16",
    "quarterfinals": "Quarterfinals",
    "semifinals": "Semifinals",
    "final": "Final",
}


def load_libertadores(data_dir: Path) -> list[Match]:
    """Copa Libertadores 2013-2022 including non-Brazilian clubs."""
    path = data_dir / "Libertadores_Matches.csv"
    matches: list[Match] = []
    for index, row in enumerate(_rows(path)):
        home_slug, home_name, home_raw = _team_fields(row["home_team"])
        away_slug, away_name, away_raw = _team_fields(row["away_team"])
        stage_raw = (row.get("stage") or "").strip()
        matches.append(
            Match(
                match_id=f"lib-{index:05d}",
                competition="libertadores",
                season=parse_season(row.get("season")),
                date=parse_date(row.get("datetime")),
                kickoff=parse_time(row.get("datetime")),
                home_slug=home_slug,
                away_slug=away_slug,
                home_name=home_name,
                away_name=away_name,
                home_raw=home_raw,
                away_raw=away_raw,
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                stage=_STAGE_TITLES.get(stage_raw.lower(), stage_raw or None),
                sources=("Libertadores_Matches.csv",),
            )
        )
    return matches


# ---------------------------------------------------------------------------
# 5. BR-Football-Dataset.csv
# ---------------------------------------------------------------------------

_BR_FOOTBALL_COMPETITIONS = {
    "serie a": "serie-a",
    "serie b": "serie-b",
    "serie c": "serie-c",
    "copa do brasil": "copa-do-brasil",
}


def _infer_season(competition: str, date) -> int | None:
    """Infer a season year for a BR-Football row from its kick-off date.

    Brazilian league seasons normally run April-December, but the COVID-hit
    2020 Série A finished in February 2021.  Any league fixture played in
    January-March therefore belongs to the previous season.  Cup competitions
    run inside a single calendar year, so their season is simply the year.
    """
    if date is None:
        return None
    if competition.startswith("serie-") and date.month <= 3:
        return date.year - 1
    return date.year


def load_br_football(data_dir: Path) -> list[Match]:
    """Série A/B/C and Copa do Brasil 2014-2023 with extended statistics."""
    path = data_dir / "BR-Football-Dataset.csv"
    matches: list[Match] = []
    for index, row in enumerate(_rows(path)):
        tournament = (row.get("tournament") or "").strip()
        competition = _BR_FOOTBALL_COMPETITIONS.get(normalize_text(tournament))
        if competition is None:
            continue
        home_slug, home_name, home_raw = _team_fields(row["home"])
        away_slug, away_name, away_raw = _team_fields(row["away"])
        date = parse_date(row.get("date"))
        stats: dict[str, dict[str, float]] = {}
        for side, prefix in (("home", "home"), ("away", "away")):
            side_stats = {
                "corners": parse_float(row.get(f"{prefix}_corner")),
                "attacks": parse_float(row.get(f"{prefix}_attack")),
                "shots": parse_float(row.get(f"{prefix}_shots")),
            }
            side_stats = {k: v for k, v in side_stats.items() if v is not None}
            if side_stats:
                stats[side] = side_stats
        matches.append(
            Match(
                match_id=f"brf-{index:05d}",
                competition=competition,
                season=_infer_season(competition, date),
                date=date,
                kickoff=parse_time(row.get("time")),
                home_slug=home_slug,
                away_slug=away_slug,
                home_name=home_name,
                away_name=away_name,
                home_raw=home_raw,
                away_raw=away_raw,
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                sources=("BR-Football-Dataset.csv",),
                stats=stats,
            )
        )
    return matches


# ---------------------------------------------------------------------------
# 6. fifa_data.csv
# ---------------------------------------------------------------------------

#: Skill columns kept on every player.  The FIFA export has 89 columns; the
#: positional-rating columns (``LS``, ``RCM``, ...) are dropped because they
#: are derived values stored as strings like ``"88+2"``.
_SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)


def load_players(data_dir: Path) -> list[Player]:
    """FIFA 19 player database (18,207 rows)."""
    path = data_dir / "fifa_data.csv"
    players: list[Player] = []
    for row in _rows(path):
        player_id = parse_int(row.get("ID"))
        name = (row.get("Name") or "").strip()
        if player_id is None or not name:
            continue
        club = (row.get("Club") or "").strip() or None
        skills = {}
        for column in _SKILL_COLUMNS:
            value = parse_int(row.get(column))
            if value is not None:
                skills[column] = value
        players.append(
            Player(
                player_id=player_id,
                name=name,
                age=parse_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip() or None,
                overall=parse_int(row.get("Overall")),
                potential=parse_int(row.get("Potential")),
                club=club,
                club_slug=resolve_club(club).slug if club else None,
                position=(row.get("Position") or "").strip() or None,
                jersey_number=parse_int(row.get("Jersey Number")),
                height=(row.get("Height") or "").strip() or None,
                weight=(row.get("Weight") or "").strip() or None,
                value=(row.get("Value") or "").strip() or None,
                wage=(row.get("Wage") or "").strip() or None,
                preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                work_rate=(row.get("Work Rate") or "").strip() or None,
                joined=(row.get("Joined") or "").strip() or None,
                contract_until=(row.get("Contract Valid Until") or "").strip() or None,
                release_clause=(row.get("Release Clause") or "").strip() or None,
                skills=skills,
            )
        )
    return players


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DataSource:
    """A provided CSV file plus the loader that understands it."""

    filename: str
    description: str
    loader: Callable[[Path], list]
    kind: str  # "matches" or "players"


SOURCES: tuple[DataSource, ...] = (
    DataSource("Brasileirao_Matches.csv",
               "Campeonato Brasileiro Série A 2012-2022 (with round numbers)",
               load_brasileirao, "matches"),
    DataSource("novo_campeonato_brasileiro.csv",
               "Campeonato Brasileiro Série A 2003-2019 (with stadiums)",
               load_historical_brasileirao, "matches"),
    DataSource("Brazilian_Cup_Matches.csv",
               "Copa do Brasil 2012-2021",
               load_copa_do_brasil, "matches"),
    DataSource("Libertadores_Matches.csv",
               "Copa Libertadores 2013-2022",
               load_libertadores, "matches"),
    DataSource("BR-Football-Dataset.csv",
               "Série A/B/C and Copa do Brasil 2014-2023 with shot/corner stats",
               load_br_football, "matches"),
    DataSource("fifa_data.csv",
               "FIFA 19 player database (18,207 players)",
               load_players, "players"),
)


def load_all_matches(data_dir: Path) -> list[Match]:
    """Load every match source in priority order (no deduplication)."""
    matches: list[Match] = []
    for source in SOURCES:
        if source.kind == "matches":
            matches.extend(source.loader(data_dir))
    return matches
