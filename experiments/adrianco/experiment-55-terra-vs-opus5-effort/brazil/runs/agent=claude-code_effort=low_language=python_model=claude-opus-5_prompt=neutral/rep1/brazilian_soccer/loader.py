"""
Context
=======
Module: brazilian_soccer.loader

Reads the six CSV files in data/kaggle/ and turns them into Match / Player
records.  One reader per file because every file has its own column names,
date format and quirks:

  Brasileirao_Matches.csv          ISO datetime, "Palmeiras-SP" style names
  Brazilian_Cup_Matches.csv        ISO datetime, long official club names
  Libertadores_Matches.csv         ISO datetime, foreign clubs, goals quoted
  BR-Football-Dataset.csv          separate date/time, Serie A/B/C + Cup,
                                   plus shots / corners / attacks
  novo_campeonato_brasileiro.csv   DD/MM/YYYY dates, Portuguese columns, arena
  fifa_data.csv                    UTF-8 BOM, unnamed index column

Cross-source de-duplication
---------------------------
Brasileirao_Matches.csv (2012-2022), novo_campeonato_brasileiro.csv (2003-2019)
and BR-Football-Dataset.csv (Serie A 2014-2023) all describe the *same* Série A
fixtures for the overlapping years.  Counting them three times would triple every
"goals scored" figure and break standings, so `deduplicate()` merges records that
share (competition, season, home, away) and whose dates agree to within a few
days, keeping the highest-priority source's core fields and back-filling
round/arena/stats from the others.  The date tolerance matters because the same
kick-off is dated a day apart in different files.
"""

from __future__ import annotations

import csv
import os
from datetime import date, datetime
from pathlib import Path

from .models import (
    BRASILEIRAO_A,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COPA_DO_BRASIL,
    LIBERTADORES,
    Match,
    Player,
)
from .names import DisplayNames, split_region

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

# Lower number wins when the same fixture appears in several files.
SOURCE_PRIORITY = {
    "Brasileirao_Matches": 0,
    "novo_campeonato_brasileiro": 1,
    "BR-Football-Dataset": 2,
    "Brazilian_Cup_Matches": 3,
    "Libertadores_Matches": 4,
}

TOURNAMENT_TO_COMPETITION = {
    "serie a": BRASILEIRAO_A,
    "serie b": BRASILEIRAO_B,
    "serie c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
}


class DataError(RuntimeError):
    """Raised when a required dataset is missing or unreadable."""


def parse_date(raw: str | None) -> date | None:
    """Parse the three date shapes present in the datasets."""
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_time(raw: str | None) -> str | None:
    """Extract HH:MM from either a datetime column or a standalone time column."""
    if not raw:
        return None
    text = raw.strip()
    if " " in text:
        text = text.split(" ", 1)[1]
    if ":" in text:
        return text[:5]
    return None


def parse_int(raw) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _open(path: Path):
    if not path.exists():
        raise DataError(f"required dataset not found: {path}")
    return open(path, newline="", encoding="utf-8-sig")


def _make_match(
    names: DisplayNames,
    *,
    competition: str,
    season,
    match_date: date | None,
    home_raw: str,
    away_raw: str,
    home_goals,
    away_goals,
    source: str,
    **extra,
) -> Match | None:
    """Build a Match, returning None when the row is unusable (no teams/score)."""
    home_key = names.observe(home_raw or "")
    away_key = names.observe(away_raw or "")
    hg, ag = parse_int(home_goals), parse_int(away_goals)
    season_int = parse_int(season)
    if not home_key or not away_key or hg is None or ag is None:
        return None
    if season_int is None:
        if match_date is None:
            return None
        season_int = match_date.year
    _, home_state = split_region(home_raw)
    _, away_state = split_region(away_raw)
    return Match(
        competition=competition,
        season=season_int,
        match_date=match_date,
        home_team=home_key,
        away_team=away_key,
        home_display=names.display(home_key),
        away_display=names.display(away_key),
        home_goals=hg,
        away_goals=ag,
        source=source,
        home_state=extra.pop("home_state", None) or home_state,
        away_state=extra.pop("away_state", None) or away_state,
        **extra,
    )


def load_brasileirao(path: Path, names: DisplayNames) -> list[Match]:
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            match = _make_match(
                names,
                competition=BRASILEIRAO_A,
                season=row.get("season"),
                match_date=parse_date(row.get("datetime")),
                home_raw=row.get("home_team", ""),
                away_raw=row.get("away_team", ""),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                source="Brasileirao_Matches",
                round=(row.get("round") or "").strip() or None,
                kickoff=parse_time(row.get("datetime")),
                home_state=(row.get("home_team_state") or "").strip() or None,
                away_state=(row.get("away_team_state") or "").strip() or None,
            )
            if match:
                out.append(match)
    return out


# Copa do Brasil rounds are bare numbers; the last round of a season is the
# final, the one before it the semifinals, and so on.  Naming them lets users
# ask for "Copa do Brasil finals" instead of guessing the round number, which
# varies by season (the competition has had 6, 7 and 8 rounds).
CUP_STAGE_FROM_END = ["final", "semifinals", "quarterfinals", "round of 16"]


def _cup_stage(round_number: int | None, last_round: int | None) -> str | None:
    if round_number is None or last_round is None:
        return None
    offset = last_round - round_number
    if 0 <= offset < len(CUP_STAGE_FROM_END):
        return CUP_STAGE_FROM_END[offset]
    return f"round {round_number}"


def load_cup(path: Path, names: DisplayNames) -> list[Match]:
    with _open(path) as fh:
        rows = list(csv.DictReader(fh))
    # First pass: how many rounds did each season have?  Needed to name stages.
    last_round: dict[int | None, int] = {}
    for row in rows:
        season, rnd = parse_int(row.get("season")), parse_int(row.get("round"))
        if rnd is not None:
            last_round[season] = max(last_round.get(season, 0), rnd)

    out = []
    for row in rows:
        season = parse_int(row.get("season"))
        stage = _cup_stage(parse_int(row.get("round")), last_round.get(season))
        match = _make_match(
            names,
            competition=COPA_DO_BRASIL,
            season=row.get("season"),
            match_date=parse_date(row.get("datetime")),
            home_raw=row.get("home_team", ""),
            away_raw=row.get("away_team", ""),
            home_goals=row.get("home_goal"),
            away_goals=row.get("away_goal"),
            source="Brazilian_Cup_Matches",
            round=(row.get("round") or "").strip() or None,
            stage=stage,
            kickoff=parse_time(row.get("datetime")),
        )
        if match:
            out.append(match)
    return out


def load_libertadores(path: Path, names: DisplayNames) -> list[Match]:
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            match = _make_match(
                names,
                competition=LIBERTADORES,
                season=row.get("season"),
                match_date=parse_date(row.get("datetime")),
                home_raw=row.get("home_team", ""),
                away_raw=row.get("away_team", ""),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                source="Libertadores_Matches",
                stage=(row.get("stage") or "").strip() or None,
                kickoff=parse_time(row.get("datetime")),
            )
            if match:
                out.append(match)
    return out


def _br_football_season(competition: str, match_date: date | None) -> int | None:
    """Season year for a BR-Football row, which carries only a calendar date.

    Brazilian league seasons normally run April-December, so the calendar year is
    the season -- except that the COVID-delayed 2020 championship finished in
    February 2021.  A Serie A/B/C match played in January or February therefore
    belongs to the previous year's season.  The Copa do Brasil is a calendar-year
    competition and is left alone.
    """
    if match_date is None:
        return None
    if competition != COPA_DO_BRASIL and match_date.month <= 2:
        return match_date.year - 1
    return match_date.year


_BRF_STAT_COLUMNS = (
    "home_corner", "away_corner", "home_attack", "away_attack",
    "home_shots", "away_shots", "total_corners",
)


def load_br_football(path: Path, names: DisplayNames) -> list[Match]:
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            tournament = (row.get("tournament") or "").strip()
            competition = TOURNAMENT_TO_COMPETITION.get(tournament.lower())
            if competition is None:
                continue
            match_date = parse_date(row.get("date"))
            stats = {}
            season = _br_football_season(competition, match_date)
            for column in _BRF_STAT_COLUMNS:
                value = parse_int(row.get(column))
                if value is not None:
                    stats[column] = value
            for column in ("ht_result", "at_result"):
                value = (row.get(column) or "").strip()
                if value:
                    stats[column] = value
            match = _make_match(
                names,
                competition=competition,
                season=season,
                match_date=match_date,
                home_raw=row.get("home", ""),
                away_raw=row.get("away", ""),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                source="BR-Football-Dataset",
                kickoff=parse_time(row.get("time")),
                stats=stats,
            )
            if match:
                out.append(match)
    return out


def load_novo(path: Path, names: DisplayNames) -> list[Match]:
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            match = _make_match(
                names,
                competition=BRASILEIRAO_A,
                season=row.get("Ano"),
                match_date=parse_date(row.get("Data")),
                home_raw=row.get("Equipe_mandante", ""),
                away_raw=row.get("Equipe_visitante", ""),
                home_goals=row.get("Gols_mandante"),
                away_goals=row.get("Gols_visitante"),
                source="novo_campeonato_brasileiro",
                round=(row.get("Rodada") or "").strip() or None,
                arena=(row.get("Arena") or "").strip() or None,
                home_state=(row.get("Mandante_UF") or "").strip() or None,
                away_state=(row.get("Visitante_UF") or "").strip() or None,
            )
            if match:
                out.append(match)
    return out


# FIFA columns copied verbatim into Player.skills.
_SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)


def load_players(path: Path, names: DisplayNames) -> list[Player]:
    """Load fifa_data.csv.

    Note: club names are normalised with the *same* function used for match
    teams, which is what makes "which Flamengo players ..." cross-file queries
    work.  Foreign clubs simply never match a Brazilian fixture key.
    """
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            player_id = parse_int(row.get("ID"))
            name = (row.get("Name") or "").strip()
            if player_id is None or not name:
                continue
            club = (row.get("Club") or "").strip()
            club_key = names.observe(club) if club else ""
            skills = {}
            for column in _SKILL_COLUMNS:
                value = parse_int(row.get(column))
                if value is not None:
                    skills[column] = value
            out.append(
                Player(
                    player_id=player_id,
                    name=name,
                    age=parse_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip(),
                    overall=parse_int(row.get("Overall")),
                    potential=parse_int(row.get("Potential")),
                    club=club,
                    club_key=club_key,
                    position=(row.get("Position") or "").strip() or None,
                    jersey_number=(row.get("Jersey Number") or "").strip() or None,
                    height=(row.get("Height") or "").strip() or None,
                    weight=(row.get("Weight") or "").strip() or None,
                    value=(row.get("Value") or "").strip() or None,
                    wage=(row.get("Wage") or "").strip() or None,
                    preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                    skills=skills,
                )
            )
    return out


# Two records of the same fixture may be dated up to this many days apart
# (different files record kick-off in different time zones, and one file dates
# a handful of matches by the day the result was published).
DEDUP_DATE_TOLERANCE_DAYS = 3


def _same_fixture(a: Match, b: Match) -> bool:
    if a.match_date is None or b.match_date is None:
        return True
    return abs((a.match_date - b.match_date).days) <= DEDUP_DATE_TOLERANCE_DAYS


def _merge(keep: Match, drop: Match) -> Match:
    merged_stats = dict(drop.stats)
    merged_stats.update(keep.stats)
    return Match(
        competition=keep.competition,
        season=keep.season,
        match_date=keep.match_date,
        home_team=keep.home_team,
        away_team=keep.away_team,
        home_display=keep.home_display,
        away_display=keep.away_display,
        home_goals=keep.home_goals,
        away_goals=keep.away_goals,
        source=keep.source,
        round=keep.round or drop.round,
        stage=keep.stage or drop.stage,
        arena=keep.arena or drop.arena,
        home_state=keep.home_state or drop.home_state,
        away_state=keep.away_state or drop.away_state,
        kickoff=keep.kickoff or drop.kickoff,
        stats=merged_stats,
    )


def deduplicate(matches: list[Match]) -> list[Match]:
    """Merge the same fixture reported by several datasets.

    Records are bucketed by (competition, season, home, away); within a bucket
    two records are the same fixture when their dates agree to within
    DEDUP_DATE_TOLERANCE_DAYS.  The highest-priority source wins for the core
    fields and the others back-fill round / stage / arena / kickoff / stats, so
    nothing a lower-priority file uniquely contributes is lost.
    """
    buckets: dict[tuple, list[Match]] = {}
    order: list[tuple] = []
    for match in matches:
        key = match.dedup_key
        group = buckets.get(key)
        if group is None:
            buckets[key] = [match]
            order.append(key)
            continue
        for index, existing in enumerate(group):
            if _same_fixture(existing, match):
                keep, drop = existing, match
                if SOURCE_PRIORITY.get(match.source, 99) < SOURCE_PRIORITY.get(existing.source, 99):
                    keep, drop = match, existing
                group[index] = _merge(keep, drop)
                break
        else:
            # Same pairing, far-apart dates: a genuinely distinct fixture
            # (e.g. a Libertadores group meeting and a later knockout leg).
            group.append(match)
    return [m for key in order for m in buckets[key]]


DATASETS = {
    "Brasileirao_Matches.csv": load_brasileirao,
    "Brazilian_Cup_Matches.csv": load_cup,
    "Libertadores_Matches.csv": load_libertadores,
    "BR-Football-Dataset.csv": load_br_football,
    "novo_campeonato_brasileiro.csv": load_novo,
}


def resolve_data_dir(data_dir: str | os.PathLike | None = None) -> Path:
    if data_dir is not None:
        return Path(data_dir)
    env = os.environ.get("BRAZILIAN_SOCCER_DATA_DIR")
    return Path(env) if env else DEFAULT_DATA_DIR


def load_all(data_dir: str | os.PathLike | None = None):
    """Load every dataset.

    Returns (deduplicated matches, players, DisplayNames, per-file raw counts).
    """
    root = resolve_data_dir(data_dir)
    names = DisplayNames()
    matches: list[Match] = []
    counts: dict[str, int] = {}
    for filename, reader in DATASETS.items():
        loaded = reader(root / filename, names)
        counts[filename] = len(loaded)
        matches.extend(loaded)
    players = load_players(root / "fifa_data.csv", names)
    counts["fifa_data.csv"] = len(players)
    # Re-stamp display names: a later file may have supplied a nicer spelling
    # than was known when an earlier match was constructed.
    matches = [
        Match(
            **{
                **{f: getattr(m, f) for f in m.__dataclass_fields__},
                "home_display": names.display(m.home_team),
                "away_display": names.display(m.away_team),
            }
        )
        for m in matches
    ]
    return deduplicate(matches), players, names, counts
