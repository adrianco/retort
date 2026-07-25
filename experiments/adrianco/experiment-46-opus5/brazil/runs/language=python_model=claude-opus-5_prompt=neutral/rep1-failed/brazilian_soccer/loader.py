"""CSV loading, cross-source de-duplication and merging.

Six files describe overlapping slices of Brazilian football:

===============================  ===========================  ===============
File                             Competition / span           Adds
===============================  ===========================  ===============
Brasileirao_Matches.csv          Série A 2012-2021            rounds, states
novo_campeonato_brasileiro.csv   Série A 2003-2019            stadium, rounds
Brazilian_Cup_Matches.csv        Copa do Brasil 2012-2021     cup rounds
Libertadores_Matches.csv         Libertadores 2013-2022       stage
BR-Football-Dataset.csv          Série A/B/C + Cup 2014-2023  shots, corners
fifa_data.csv                    18,207 FIFA players          player attributes
===============================  ===========================  ===============

Files are loaded in that order and a match already seen from an earlier file is
*merged* rather than duplicated: same competition and teams, with dates close
enough to be the same fixture. Without this, Série A 2014-2019 would be counted
three times and every standings table would be wrong.
"""

from __future__ import annotations

import math
import os
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import pandas as pd

from .models import Match, Player
from .normalization import (
    BRASILEIRAO,
    COPA_DO_BRASIL,
    LIBERTADORES,
    normalize_competition,
    parse_date,
    parse_int,
    parse_time,
    slugify,
)
from .teams import TeamRegistry

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

BRASILEIRAO_FILE = "Brasileirao_Matches.csv"
NOVO_FILE = "novo_campeonato_brasileiro.csv"
CUP_FILE = "Brazilian_Cup_Matches.csv"
LIBERTADORES_FILE = "Libertadores_Matches.csv"
BR_FOOTBALL_FILE = "BR-Football-Dataset.csv"
FIFA_FILE = "fifa_data.csv"

MATCH_FILES = (
    BRASILEIRAO_FILE, NOVO_FILE, CUP_FILE, LIBERTADORES_FILE, BR_FOOTBALL_FILE,
)

#: Two records of the same fixture can disagree on the date by weeks when a
#: match is postponed and only one source records the replayed date. A fixture
#: with a given home/away ordering happens at most once per season in every
#: competition here, so a wide window cannot merge genuinely distinct matches.
MERGE_WINDOW = timedelta(days=45)

_FIFA_SKILLS = (
    "Crossing", "Finishing", "ShortPassing", "Dribbling", "BallControl",
    "Acceleration", "SprintSpeed", "ShotPower", "Stamina", "Strength",
    "LongShots", "Vision", "Penalties", "Composure", "StandingTackle",
    "GKDiving", "GKReflexes",
)


class DataLoadError(RuntimeError):
    """Raised when a required dataset file is missing or unreadable."""


def _read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise DataLoadError(f"required dataset not found: {path}")
    try:
        return pd.read_csv(path, encoding="utf-8", **kwargs)
    except UnicodeDecodeError:                      # pragma: no cover - safety net
        return pd.read_csv(path, encoding="latin-1", **kwargs)


def _clean(value) -> str | None:
    """Normalize a cell to a stripped string or ``None``."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None
    return text


class MatchCollector:
    """Accumulates matches, merging records that describe the same fixture."""

    def __init__(self) -> None:
        self._by_key: dict[tuple, list[Match]] = defaultdict(list)
        self.matches: list[Match] = []
        self.merged_count = 0
        self.self_matches = 0

    def add(self, match: Match) -> Match | None:
        # One row in the cup file names the same club as home and away; such a
        # match would count twice for that club in every aggregate.
        if match.home_team == match.away_team:
            self.self_matches += 1
            return None

        # The season is deliberately *not* part of the key: the 2020 Série A ran
        # into February 2021, so a source that derives the season from the match
        # date disagrees with the sources that record it explicitly. Dates decide
        # instead (see MERGE_WINDOW).
        key = (match.competition, match.home_team, match.away_team)
        for existing in self._by_key[key]:
            if _same_fixture(existing, match):
                _merge_into(existing, match)
                self.merged_count += 1
                return existing
        self._by_key[key].append(match)
        self.matches.append(match)
        return match


def _derive_season(competition: str, when) -> int | None:
    """Infer the season of a match that only carries a date.

    Brazilian league seasons run April-December; the pandemic-hit 2020 season
    spilled into February 2021, so early-year league matches belong to the
    previous season. The Copa do Brasil, by contrast, kicks off in February.
    """
    if when is None:
        return None
    cutoff = 1 if competition == COPA_DO_BRASIL else 3
    return when.year - 1 if when.month <= cutoff else when.year


def _same_fixture(a: Match, b: Match) -> bool:
    """Same competition and teams already checked — decide on dates."""
    if a.date is not None and b.date is not None:
        return abs(a.date - b.date) <= MERGE_WINDOW
    # An undated record can only be matched by season.
    return a.season is not None and a.season == b.season


def _merge_into(target: Match, other: Match) -> None:
    """Fill gaps in ``target`` from ``other``; earlier sources keep priority."""
    for field_name in ("date", "season", "round", "stage", "venue", "kickoff"):
        if getattr(target, field_name) is None:
            setattr(target, field_name, getattr(other, field_name))
    if target.home_goals is None and other.home_goals is not None:
        target.home_goals = other.home_goals
        target.away_goals = other.away_goals
    for key, value in other.stats.items():
        target.stats.setdefault(key, value)
    target.sources = tuple(dict.fromkeys(target.sources + other.sources))


def _match_id(competition: str, season, home: str, away: str, when) -> str:
    stamp = when.isoformat() if when is not None else "undated"
    return f"{slugify(competition).replace(' ', '-')}:{season}:{home}:{away}:{stamp}"


class Dataset:
    """Everything loaded from disk: teams, matches and players."""

    def __init__(
        self,
        registry: TeamRegistry,
        matches: list[Match],
        players: list[Player],
        source_counts: dict[str, int],
    ) -> None:
        self.registry = registry
        self.matches = matches
        self.players = players
        self.source_counts = source_counts

    @property
    def teams(self):
        return self.registry.teams


def load_dataset(data_dir: str | os.PathLike | None = None) -> Dataset:
    """Load all six CSVs into a :class:`Dataset`.

    The registry is built in two passes: first every raw team spelling in every
    file is observed, then canonical ids are assigned, then rows are converted
    into :class:`~.models.Match` objects.
    """
    directory = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    frames = {name: _read_csv(directory / name) for name in MATCH_FILES}
    fifa = _read_csv(directory / FIFA_FILE, low_memory=False)

    registry = TeamRegistry()
    _observe_names(registry, frames, fifa)
    registry.build()

    collector = MatchCollector()
    source_counts: dict[str, int] = {}
    for loader, name in (
        (_load_brasileirao, BRASILEIRAO_FILE),
        (_load_novo, NOVO_FILE),
        (_load_cup, CUP_FILE),
        (_load_libertadores, LIBERTADORES_FILE),
        (_load_br_football, BR_FOOTBALL_FILE),
    ):
        rows = loader(frames[name], registry, collector)
        source_counts[name] = rows

    players = _load_players(fifa, registry)
    source_counts[FIFA_FILE] = len(players)

    matches = sorted(
        collector.matches,
        key=lambda m: (m.date or _EPOCH, m.competition, m.home_team),
    )
    return Dataset(registry, matches, players, source_counts)


_EPOCH = parse_date("1900-01-01")


def _observe_names(registry: TeamRegistry, frames: dict, fifa: pd.DataFrame) -> None:
    columns = {
        BRASILEIRAO_FILE: ("home_team", "away_team"),
        NOVO_FILE: ("Equipe_mandante", "Equipe_visitante"),
        CUP_FILE: ("home_team", "away_team"),
        LIBERTADORES_FILE: ("home_team", "away_team"),
        BR_FOOTBALL_FILE: ("home", "away"),
    }
    for name, cols in columns.items():
        frame = frames[name]
        for col in cols:
            for value in frame[col].dropna().unique():
                registry.observe(value)
    for value in fifa["Club"].dropna().unique():
        registry.observe(value, brazilian=False)


# --------------------------------------------------------------------------- #
# Per-file loaders
# --------------------------------------------------------------------------- #

def _load_brasileirao(frame: pd.DataFrame, registry: TeamRegistry,
                      collector: MatchCollector) -> int:
    count = 0
    for row in frame.itertuples(index=False):
        home = registry.team_id_for_raw(row.home_team)
        away = registry.team_id_for_raw(row.away_team)
        if not home or not away:
            continue
        when = parse_date(row.datetime)
        season = parse_int(row.season) or (when.year if when else None)
        collector.add(Match(
            match_id=_match_id(BRASILEIRAO, season, home, away, when),
            competition=BRASILEIRAO,
            season=season,
            date=when,
            home_team=home,
            away_team=away,
            home_goals=parse_int(row.home_goal),
            away_goals=parse_int(row.away_goal),
            round=_clean(row.round),
            kickoff=parse_time(row.datetime),
            sources=(BRASILEIRAO_FILE,),
        ))
        count += 1
    return count


def _load_novo(frame: pd.DataFrame, registry: TeamRegistry,
               collector: MatchCollector) -> int:
    count = 0
    for row in frame.itertuples(index=False):
        home = registry.team_id_for_raw(row.Equipe_mandante)
        away = registry.team_id_for_raw(row.Equipe_visitante)
        if not home or not away:
            continue
        when = parse_date(row.Data)
        season = parse_int(row.Ano) or (when.year if when else None)
        collector.add(Match(
            match_id=_match_id(BRASILEIRAO, season, home, away, when),
            competition=BRASILEIRAO,
            season=season,
            date=when,
            home_team=home,
            away_team=away,
            home_goals=parse_int(row.Gols_mandante),
            away_goals=parse_int(row.Gols_visitante),
            round=_clean(row.Rodada),
            venue=_clean(row.Arena),
            sources=(NOVO_FILE,),
        ))
        count += 1
    return count


def _load_cup(frame: pd.DataFrame, registry: TeamRegistry,
              collector: MatchCollector) -> int:
    stage_labels = _cup_stage_labels(frame)
    count = 0
    for row in frame.itertuples(index=False):
        home = registry.team_id_for_raw(row.home_team)
        away = registry.team_id_for_raw(row.away_team)
        if not home or not away:
            continue
        when = parse_date(row.datetime)
        season = parse_int(row.season) or (when.year if when else None)
        cup_round = _clean(row.round)
        collector.add(Match(
            match_id=_match_id(COPA_DO_BRASIL, season, home, away, when),
            competition=COPA_DO_BRASIL,
            season=season,
            date=when,
            home_team=home,
            away_team=away,
            home_goals=parse_int(row.home_goal),
            away_goals=parse_int(row.away_goal),
            round=cup_round,
            stage=stage_labels.get((season, cup_round)),
            kickoff=parse_time(row.datetime),
            sources=(CUP_FILE,),
        ))
        count += 1
    return count


#: Knockout stages, largest first, with the number of matches each contains
#: when every tie is played over two legs.
_KNOCKOUT_LADDER = (
    ("round of 64", 64), ("round of 32", 32), ("round of 16", 16),
    ("quarterfinals", 8), ("semifinals", 4), ("final", 2),
)


def _cup_stage_labels(frame: pd.DataFrame) -> dict[tuple[int | None, str], str]:
    """Name the Copa do Brasil rounds, which the file only numbers.

    The number of matches in a round identifies it: the last round of a season
    has two legs (the final), the one before it four (semifinals) and so on.
    Rounds are walked from the last one backwards and labelling stops as soon as
    the count stops halving, because the early rounds of the modern format are
    single-legged and do not fit the ladder.
    """
    labels: dict[tuple[int | None, str], str] = {}
    counts: dict[int | None, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in frame.itertuples(index=False):
        season = parse_int(row.season)
        cup_round = _clean(row.round)
        if cup_round is not None:
            counts[season][cup_round] += 1

    for season, rounds in counts.items():
        ordered = sorted(rounds, key=lambda value: -(parse_int(value) or 0))
        ladder_index = next(
            (i for i, (_, size) in enumerate(_KNOCKOUT_LADDER)
             if size == rounds[ordered[0]]),
            None,
        )
        if ladder_index is None:
            continue
        for cup_round in ordered:
            if ladder_index < 0 or rounds[cup_round] != _KNOCKOUT_LADDER[ladder_index][1]:
                break
            labels[(season, cup_round)] = _KNOCKOUT_LADDER[ladder_index][0]
            ladder_index -= 1
    return labels


def _load_libertadores(frame: pd.DataFrame, registry: TeamRegistry,
                       collector: MatchCollector) -> int:
    count = 0
    for row in frame.itertuples(index=False):
        home = registry.team_id_for_raw(row.home_team)
        away = registry.team_id_for_raw(row.away_team)
        if not home or not away:
            continue
        when = parse_date(row.datetime)
        season = parse_int(row.season) or (when.year if when else None)
        collector.add(Match(
            match_id=_match_id(LIBERTADORES, season, home, away, when),
            competition=LIBERTADORES,
            season=season,
            date=when,
            home_team=home,
            away_team=away,
            home_goals=parse_int(row.home_goal),
            away_goals=parse_int(row.away_goal),
            stage=_clean(row.stage),
            kickoff=parse_time(row.datetime),
            sources=(LIBERTADORES_FILE,),
        ))
        count += 1
    return count


_BR_FOOTBALL_STATS = {
    "home_corner": "home_corners", "away_corner": "away_corners",
    "home_attack": "home_attacks", "away_attack": "away_attacks",
    "home_shots": "home_shots", "away_shots": "away_shots",
    "total_corners": "total_corners",
}


def _load_br_football(frame: pd.DataFrame, registry: TeamRegistry,
                      collector: MatchCollector) -> int:
    count = 0
    for row in frame.itertuples(index=False):
        home = registry.team_id_for_raw(row.home)
        away = registry.team_id_for_raw(row.away)
        if not home or not away:
            continue
        competition = normalize_competition(row.tournament)
        if competition is None:
            continue
        when = parse_date(row.date)
        season = _derive_season(competition, when)
        stats = {}
        for column, key in _BR_FOOTBALL_STATS.items():
            value = parse_int(getattr(row, column, None))
            if value is not None:
                stats[key] = value
        collector.add(Match(
            match_id=_match_id(competition, season, home, away, when),
            competition=competition,
            season=season,
            date=when,
            home_team=home,
            away_team=away,
            home_goals=parse_int(row.home_goal),
            away_goals=parse_int(row.away_goal),
            kickoff=parse_time(row.time),
            sources=(BR_FOOTBALL_FILE,),
            stats=stats,
        ))
        count += 1
    return count


# --------------------------------------------------------------------------- #
# Players
# --------------------------------------------------------------------------- #

#: FIFA column -> attribute name. Renaming up front keeps ``itertuples`` usable
#: with columns such as "Jersey Number" that are not valid identifiers.
_FIFA_COLUMNS = {
    "ID": "pid", "Name": "name", "Age": "age", "Nationality": "nationality",
    "Overall": "overall", "Potential": "potential", "Club": "club",
    "Position": "position", "Jersey Number": "jersey", "Height": "height",
    "Weight": "weight", "Value": "value", "Wage": "wage",
    "Preferred Foot": "foot",
}


def _load_players(frame: pd.DataFrame, registry: TeamRegistry) -> list[Player]:
    columns = {src: dst for src, dst in _FIFA_COLUMNS.items() if src in frame.columns}
    skills = [skill for skill in _FIFA_SKILLS if skill in frame.columns]
    subset = frame[list(columns) + skills].rename(columns=columns)

    players: list[Player] = []
    for index, row in enumerate(subset.itertuples(index=False)):
        name = _clean(getattr(row, "name", None))
        if not name:
            continue
        club = _clean(getattr(row, "club", None))
        attributes = {}
        for skill in skills:
            value = parse_int(getattr(row, skill, None))
            if value is not None:
                attributes[skill] = value
        players.append(Player(
            player_id=str(parse_int(getattr(row, "pid", None)) or f"row-{index}"),
            name=name,
            age=parse_int(getattr(row, "age", None)),
            nationality=_clean(getattr(row, "nationality", None)) or "Unknown",
            overall=parse_int(getattr(row, "overall", None)),
            potential=parse_int(getattr(row, "potential", None)),
            club=club,
            club_team_id=registry.team_id_for_raw(club) if club else None,
            position=_clean(getattr(row, "position", None)),
            jersey_number=parse_int(getattr(row, "jersey", None)),
            height=_clean(getattr(row, "height", None)),
            weight=_clean(getattr(row, "weight", None)),
            value=_clean(getattr(row, "value", None)),
            wage=_clean(getattr(row, "wage", None)),
            preferred_foot=_clean(getattr(row, "foot", None)),
            skills=attributes,
        ))
    return players
