"""CSV ingestion and cross-source de-duplication.

Context
-------
Six Kaggle CSVs live in ``data/kaggle``.  Five of them contain matches and they
*overlap*: a Brasileirão Série A fixture from 2016 exists in
``Brasileirao_Matches.csv``, in ``novo_campeonato_brasileiro.csv`` and in
``BR-Football-Dataset.csv``.  Loading them naively would triple every league
table.  :func:`merge_matches` therefore groups candidate duplicates by
``(competition, season, home, away)`` and fuses the records that describe the
same fixture -- sharing a round number, or falling within three days of each
other -- keeping the richest value for every field (round from the Brasileirão
file, stadium from the historical file, shots/corners from the extended stats
file) and recording provenance in :attr:`Match.sources`.

Quirks handled here:

* dates come as ``2012-05-19 18:30:00``, ``2023-09-24`` and ``29/03/2003``;
* missing scores appear as ``NA`` (Brasileirão) and ``-`` (Libertadores);
* the extended stats file has no season column and the 2020 league season ran
  into February 2021, so league matches played in January-March are attributed
  to the previous season;
* Copa do Brasil rounds are plain numbers, so knockout stage names are derived
  by walking backwards from the last round of each season;
* every file is read as UTF-8 with BOM tolerance so ``São``/``Grêmio`` survive.
"""

from __future__ import annotations

import csv
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from .models import Match, Player
from .names import normalize_query, resolve_competition, resolve_team

__all__ = [
    "DATA_FILES",
    "default_data_dir",
    "load_all_matches",
    "load_matches",
    "load_players",
    "collect_spellings",
    "merge_matches",
    "parse_date",
    "parse_int",
]


#: Source id -> file name.  Used for provenance in :attr:`Match.sources`.
DATA_FILES: dict[str, str] = {
    "brasileirao": "Brasileirao_Matches.csv",
    "copa_do_brasil": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "br_football": "BR-Football-Dataset.csv",
    "historico": "novo_campeonato_brasileiro.csv",
    "fifa_players": "fifa_data.csv",
}

#: When two sources disagree on a scalar, the lower number wins.
SOURCE_PRIORITY: dict[str, int] = {
    "brasileirao": 1,
    "copa_do_brasil": 1,
    "libertadores": 1,
    "historico": 2,
    "br_football": 3,
}

_MERGE_WINDOW_DAYS = 3


def default_data_dir() -> Path:
    """``$BRAZILIAN_SOCCER_DATA`` or ``<repo>/data/kaggle``."""
    env = os.environ.get("BRAZILIAN_SOCCER_DATA")
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parent.parent / "data" / "kaggle"


# --------------------------------------------------------------------------
# Scalar parsing helpers
# --------------------------------------------------------------------------

_MISSING = {"", "na", "n/a", "nan", "-", "--", "none", "null"}


def parse_int(value: str | None) -> int | None:
    """Parse ``"2"``, ``"2.0"`` and reject ``"NA"``/``"-"``/``""``."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _MISSING:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _MISSING:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value: str | None) -> tuple[date | None, str | None]:
    """Return ``(date, kickoff_time)`` for the three formats in the data."""
    if not value:
        return None, None
    text = str(value).strip()
    if text.lower() in _MISSING:
        return None, None
    for fmt, has_time in (
        ("%Y-%m-%d %H:%M:%S", True),
        ("%Y-%m-%d %H:%M", True),
        ("%Y-%m-%d", False),
        ("%d/%m/%Y", False),
        ("%d/%m/%y", False),
        ("%Y/%m/%d", False),
    ):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.date(), (parsed.strftime("%H:%M") if has_time else None)
    return None, None


def parse_money(value: str | None) -> tuple[float | None, str]:
    """``"€110.5M"`` -> ``(110_500_000.0, "€110.5M")``."""
    if not value:
        return None, ""
    label = str(value).strip()
    match = re.match(r"^[^\d]*([\d.]+)\s*([KMB]?)", label, re.IGNORECASE)
    if not match:
        return None, label
    try:
        amount = float(match.group(1))
    except ValueError:
        return None, label
    multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[
        match.group(2).upper()
    ]
    return amount * multiplier, label


def _read_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


# --------------------------------------------------------------------------
# Per-file loaders
# --------------------------------------------------------------------------


def _competition(name: str) -> tuple[str, str]:
    competition = resolve_competition(name)
    if competition is None:  # pragma: no cover - all fixtures map today
        return normalize_query(name).replace(" ", "-"), name
    return competition.id, competition.name


def load_brasileirao(path: Path) -> list[Match]:
    """``Brasileirao_Matches.csv`` -- Série A 2012-2022, with state columns."""
    competition_id, competition_name = _competition("serie a")
    matches: list[Match] = []
    for index, row in enumerate(_read_csv(path)):
        home = resolve_team(row["home_team"], row.get("home_team_state"))
        away = resolve_team(row["away_team"], row.get("away_team_state"))
        match_date, kickoff = parse_date(row.get("datetime"))
        matches.append(
            Match(
                match_id=f"brasileirao:{index}",
                competition_id=competition_id,
                competition=competition_name,
                season=parse_int(row.get("season")),
                date=match_date,
                kickoff=kickoff,
                round=parse_int(row.get("round")),
                home_team=home.id,
                away_team=away.id,
                home_team_name=home.name,
                away_team_name=away.name,
                home_team_raw=row["home_team"].strip(),
                away_team_raw=row["away_team"].strip(),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                sources=("brasileirao",),
            )
        )
    return matches


_CUP_STAGE_BY_MATCHES: dict[int, str] = {
    2: "Final",
    4: "Semifinals",
    8: "Quarterfinals",
    16: "Round of 16",
    32: "Round of 32",
}


def _cup_stage_labels(rows: Sequence[dict[str, str]]) -> dict[tuple[int, int], str]:
    """Derive knockout stage names from the size of each round.

    The Copa do Brasil file only numbers its rounds.  Walking *backwards* from
    the last round of a season, a two match round is the two legged final, four
    matches are the semi-finals and each earlier round must be twice the size of
    the one after it.  The walk stops at the first round that breaks the
    doubling, which keeps the early qualifying rounds numbered -- 2013-2015 open
    with a two match pre-round that a size-only rule would call a final -- and
    still labels the truncated 2021 season correctly (it ends at the round of
    16, with no final in the data).
    """
    counts: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        season = parse_int(row.get("season"))
        rnd = parse_int(row.get("round"))
        if season is not None and rnd is not None:
            counts[season][rnd] += 1

    labels: dict[tuple[int, int], str] = {}
    for season, rounds in counts.items():
        naming, expected = True, None
        for rnd in sorted(rounds, reverse=True):
            size = rounds[rnd]
            stage = _CUP_STAGE_BY_MATCHES.get(size)
            if naming and stage is not None and (expected is None or size == expected):
                labels[(season, rnd)] = stage
                expected = size * 2
            else:
                # Once the doubling breaks, every earlier round stays numbered.
                naming = False
                labels[(season, rnd)] = f"Round {rnd}"
    return labels


def load_copa_do_brasil(path: Path) -> list[Match]:
    """``Brazilian_Cup_Matches.csv`` -- Copa do Brasil 2012-2021."""
    competition_id, competition_name = _competition("copa do brasil")
    rows = list(_read_csv(path))
    stage_labels = _cup_stage_labels(rows)
    matches: list[Match] = []
    for index, row in enumerate(rows):
        home = resolve_team(row["home_team"])
        away = resolve_team(row["away_team"])
        match_date, kickoff = parse_date(row.get("datetime"))
        season = parse_int(row.get("season"))
        rnd = parse_int(row.get("round"))
        matches.append(
            Match(
                match_id=f"copa_do_brasil:{index}",
                competition_id=competition_id,
                competition=competition_name,
                season=season,
                date=match_date,
                kickoff=kickoff,
                round=rnd,
                stage=stage_labels.get((season, rnd)) if season and rnd else None,
                home_team=home.id,
                away_team=away.id,
                home_team_name=home.name,
                away_team_name=away.name,
                home_team_raw=row["home_team"].strip(),
                away_team_raw=row["away_team"].strip(),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                sources=("copa_do_brasil",),
            )
        )
    return matches


_LIBERTADORES_STAGES = {
    "group stage": "Group stage",
    "round of 16": "Round of 16",
    "quarterfinals": "Quarterfinals",
    "semifinals": "Semifinals",
    "final": "Final",
}


def load_libertadores(path: Path) -> list[Match]:
    """``Libertadores_Matches.csv`` -- Copa Libertadores 2013-2022."""
    competition_id, competition_name = _competition("libertadores")
    matches: list[Match] = []
    for index, row in enumerate(_read_csv(path)):
        home = resolve_team(row["home_team"])
        away = resolve_team(row["away_team"])
        match_date, kickoff = parse_date(row.get("datetime"))
        season = parse_int(row.get("season"))
        if season is None and match_date is not None:
            season = match_date.year
        stage_raw = (row.get("stage") or "").strip().lower()
        matches.append(
            Match(
                match_id=f"libertadores:{index}",
                competition_id=competition_id,
                competition=competition_name,
                season=season,
                date=match_date,
                kickoff=kickoff,
                stage=_LIBERTADORES_STAGES.get(stage_raw, stage_raw.title() or None),
                home_team=home.id,
                away_team=away.id,
                home_team_name=home.name,
                away_team_name=away.name,
                home_team_raw=row["home_team"].strip(),
                away_team_raw=row["away_team"].strip(),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                sources=("libertadores",),
            )
        )
    return matches


_STAT_COLUMNS = (
    "home_corner",
    "away_corner",
    "home_attack",
    "away_attack",
    "home_shots",
    "away_shots",
    "total_corners",
)


def _league_season(competition_id: str, match_date: date | None) -> int | None:
    """Season year for a date, honouring seasons that spill into January.

    The Brazilian league calendar runs roughly April-December, but the COVID
    affected 2020 season only finished in February 2021.  ``BR-Football`` has no
    season column, so a league match played in January-March is attributed to
    the previous season -- cups, which do start in the first quarter, are not.
    """
    if match_date is None:
        return None
    if competition_id.startswith("serie-") and match_date.month <= 3:
        return match_date.year - 1
    return match_date.year


def load_br_football(path: Path) -> list[Match]:
    """``BR-Football-Dataset.csv`` -- Série A/B/C + Copa do Brasil with stats."""
    matches: list[Match] = []
    for index, row in enumerate(_read_csv(path)):
        competition_id, competition_name = _competition(row.get("tournament", ""))
        home = resolve_team(row["home"])
        away = resolve_team(row["away"])
        match_date, _ = parse_date(row.get("date"))
        kickoff = (row.get("time") or "").strip()[:5] or None
        stats = {
            column: value
            for column in _STAT_COLUMNS
            if (value := parse_float(row.get(column))) is not None
        }
        matches.append(
            Match(
                match_id=f"br_football:{index}",
                competition_id=competition_id,
                competition=competition_name,
                season=_league_season(competition_id, match_date),
                date=match_date,
                kickoff=kickoff,
                home_team=home.id,
                away_team=away.id,
                home_team_name=home.name,
                away_team_name=away.name,
                home_team_raw=row["home"].strip(),
                away_team_raw=row["away"].strip(),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                sources=("br_football",),
                stats=stats,
            )
        )
    return matches


def load_historico(path: Path) -> list[Match]:
    """``novo_campeonato_brasileiro.csv`` -- Série A 2003-2019 with stadiums."""
    competition_id, competition_name = _competition("serie a")
    matches: list[Match] = []
    for index, row in enumerate(_read_csv(path)):
        home = resolve_team(row["Equipe_mandante"], row.get("Mandante_UF"))
        away = resolve_team(row["Equipe_visitante"], row.get("Visitante_UF"))
        match_date, _ = parse_date(row.get("Data"))
        venue = (row.get("Arena") or "").strip() or None
        matches.append(
            Match(
                match_id=f"historico:{index}",
                competition_id=competition_id,
                competition=competition_name,
                season=parse_int(row.get("Ano")),
                date=match_date,
                round=parse_int(row.get("Rodada")),
                home_team=home.id,
                away_team=away.id,
                home_team_name=home.name,
                away_team_name=away.name,
                home_team_raw=row["Equipe_mandante"].strip(),
                away_team_raw=row["Equipe_visitante"].strip(),
                home_goals=parse_int(row.get("Gols_mandante")),
                away_goals=parse_int(row.get("Gols_visitante")),
                venue=venue,
                sources=("historico",),
            )
        )
    return matches


_MATCH_LOADERS = {
    "brasileirao": load_brasileirao,
    "copa_do_brasil": load_copa_do_brasil,
    "libertadores": load_libertadores,
    "br_football": load_br_football,
    "historico": load_historico,
}


def load_matches(data_dir: Path | str | None = None) -> list[Match]:
    """Load every match CSV without de-duplicating (see :func:`merge_matches`)."""
    directory = Path(data_dir) if data_dir else default_data_dir()
    matches: list[Match] = []
    for source, loader in _MATCH_LOADERS.items():
        path = directory / DATA_FILES[source]
        if not path.exists():
            continue
        matches.extend(loader(path))
    return matches


# --------------------------------------------------------------------------
# De-duplication
# --------------------------------------------------------------------------


def _merge_key(match: Match) -> tuple[str, int | None, str, str]:
    return (match.competition_id, match.season, match.home_team, match.away_team)


def _best(values: Iterable[tuple[Any, object]]) -> object | None:
    """Pick the value coming from the highest priority source."""
    candidates = [(priority, value) for priority, value in values if value is not None]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _priority(match: Match) -> int:
    return min((SOURCE_PRIORITY.get(source, 9) for source in match.sources), default=9)


def _merge_cluster(cluster: list[Match]) -> Match:
    """Fuse duplicate records of one fixture into a single :class:`Match`."""
    if len(cluster) == 1:
        return cluster[0]
    ordered = sorted(cluster, key=_priority)
    primary = ordered[0]
    pairs = [(_priority(match), match) for match in ordered]

    merged = Match(
        match_id=primary.match_id,
        competition_id=primary.competition_id,
        competition=primary.competition,
        season=_best((p, m.season) for p, m in pairs),  # type: ignore[arg-type]
        # A record with no score carries a *scheduled* date; when a fixture was
        # postponed the source that recorded the result knows when it was
        # actually played, so it wins regardless of source priority.
        date=_best(((0 if m.played else 1, p), m.date) for p, m in pairs),  # type: ignore[arg-type]
        kickoff=_best(((0 if m.played else 1, p), m.kickoff) for p, m in pairs),  # type: ignore[arg-type]
        round=_best((p, m.round) for p, m in pairs),  # type: ignore[arg-type]
        stage=_best((p, m.stage) for p, m in pairs),  # type: ignore[arg-type]
        home_team=primary.home_team,
        away_team=primary.away_team,
        home_team_name=primary.home_team_name,
        away_team_name=primary.away_team_name,
        home_team_raw=primary.home_team_raw,
        away_team_raw=primary.away_team_raw,
        home_goals=_best((p, m.home_goals) for p, m in pairs),  # type: ignore[arg-type]
        away_goals=_best((p, m.away_goals) for p, m in pairs),  # type: ignore[arg-type]
        venue=_best((p, m.venue) for p, m in pairs),  # type: ignore[arg-type]
        sources=tuple(dict.fromkeys(source for m in ordered for source in m.sources)),
    )
    for match in reversed(ordered):  # richer sources win on ties
        merged.stats.update(match.stats)
    # A score is only trustworthy as a pair -- never mix home from one source
    # with away from another.
    if merged.home_goals is None or merged.away_goals is None:
        for match in ordered:
            if match.played:
                merged.home_goals, merged.away_goals = match.home_goals, match.away_goals
                break
    return merged


def _same_fixture(match: Match, cluster: list[Match], league: bool) -> bool:
    """Does *match* describe the same fixture as the records in *cluster*?"""
    dates = [other.date for other in cluster if other.date]
    near_in_time = (
        match.date is None
        or not dates
        or min(abs((match.date - other).days) for other in dates) <= _MERGE_WINDOW_DAYS
    )
    if not league:
        return near_in_time
    # Two records from the *same* file are two fixtures unless they are near
    # duplicates: the extended stats file carries no round numbers and is the
    # only source for Série B/C, where a pairing legitimately repeats in a
    # second phase.  Without this the later meeting would be swallowed.
    if any(set(match.sources) & set(other.sources) for other in cluster):
        return near_in_time
    # Across files, leagues pair every two teams once per venue per season, so a
    # shared round number is enough even when the sources disagree about the
    # date.  Rounds disagree for postponed fixtures (a round 9 game played on
    # round 28's weekend), which the date check then catches -- while Botafogo
    # hosting Flamengo in both round 12 and round 31 of 2009 stays two fixtures.
    rounds = {other.round for other in cluster if other.round is not None}
    same_round = match.round is None or not rounds or match.round in rounds
    return same_round or near_in_time


def merge_matches(matches: Sequence[Match]) -> list[Match]:
    """De-duplicate fixtures shared by several source files.

    Records are grouped by ``(competition, season, home, away)`` and then split
    into clusters of dates within :data:`_MERGE_WINDOW_DAYS`, so two legs of the
    same cup tie (weeks apart) stay separate while the same fixture reported by
    three files collapses into one node.
    """
    groups: dict[tuple[str, int | None, str, str], list[Match]] = defaultdict(list)
    for match in matches:
        if match.home_team == match.away_team:
            # Brazilian_Cup_Matches.csv names both sides "Bragantino - PA" for
            # two 2019 fixtures; counting them would give that club phantom
            # wins on both sides of the same match.
            continue
        groups[_merge_key(match)].append(match)

    merged: list[Match] = []
    for key, items in groups.items():
        items.sort(key=lambda m: (m.date is None, m.date or date.min, _priority(m)))
        # In a double round robin league a pairing happens once per venue per
        # season, so sources that disagree about the date (postponements) still
        # describe the same fixture -- provided the round numbers agree.  Cups
        # can repeat a pairing within a season, hence the date window there.
        league = key[0].startswith("serie-")
        clusters: list[list[Match]] = []
        for match in items:
            target = next(
                (cluster for cluster in clusters if _same_fixture(match, cluster, league)),
                None,
            )
            if target is None:
                clusters.append([match])
            else:
                target.append(match)
        for index, cluster in enumerate(clusters):
            match = _merge_cluster(cluster)
            competition_id, season, home, away = key
            suffix = f":{index}" if len(clusters) > 1 else ""
            match.match_id = f"{competition_id}:{season}:{home}:{away}{suffix}"
            merged.append(match)

    merged.sort(key=lambda m: (m.date or date.min, m.competition_id, m.home_team))
    return merged


def load_all_matches(data_dir: Path | str | None = None) -> list[Match]:
    """Load every match file and de-duplicate across sources."""
    return merge_matches(load_matches(data_dir))


def collect_spellings(matches: Iterable[Match]) -> dict[str, Counter[str]]:
    """Map each team id to the raw spellings that resolved to it.

    Call this on the *pre-merge* list: merging keeps only the primary record's
    raw names, so counting afterwards would lose the variants contributed by the
    other source files, which is exactly what makes this interesting.
    """
    spellings: dict[str, Counter[str]] = defaultdict(Counter)
    for match in matches:
        if match.home_team_raw:
            spellings[match.home_team][match.home_team_raw] += 1
        if match.away_team_raw:
            spellings[match.away_team][match.away_team_raw] += 1
    return dict(spellings)


# --------------------------------------------------------------------------
# Players
# --------------------------------------------------------------------------

_SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
    "Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed",
    "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength",
    "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
    "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)


def load_players(data_dir: Path | str | None = None) -> list[Player]:
    """Load ``fifa_data.csv`` into :class:`Player` records.

    ``club_team_id`` is filled in later by the knowledge graph, which only links
    a FIFA club to a match-data team when that team actually plays in the
    Brazilian competitions (so "FC Barcelona" never becomes Barcelona-EQU).
    """
    directory = Path(data_dir) if data_dir else default_data_dir()
    path = directory / DATA_FILES["fifa_players"]
    if not path.exists():
        return []

    players: list[Player] = []
    for row in _read_csv(path):
        player_id = parse_int(row.get("ID"))
        name = (row.get("Name") or "").strip()
        if player_id is None or not name:
            continue
        value_eur, value_label = parse_money(row.get("Value"))
        wage_eur, wage_label = parse_money(row.get("Wage"))
        clause_eur, _ = parse_money(row.get("Release Clause"))
        skills = {
            column: value
            for column in _SKILL_COLUMNS
            if (value := parse_int(row.get(column))) is not None
        }
        players.append(
            Player(
                player_id=player_id,
                name=name,
                age=parse_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=parse_int(row.get("Overall")),
                potential=parse_int(row.get("Potential")),
                club=(row.get("Club") or "").strip(),
                position=(row.get("Position") or "").strip(),
                jersey_number=parse_int(row.get("Jersey Number")),
                preferred_foot=(row.get("Preferred Foot") or "").strip(),
                height=(row.get("Height") or "").strip(),
                weight=(row.get("Weight") or "").strip(),
                value_eur=value_eur,
                wage_eur=wage_eur,
                release_clause_eur=clause_eur,
                value_label=value_label,
                wage_label=wage_label,
                joined=(row.get("Joined") or "").strip(),
                contract_valid_until=(row.get("Contract Valid Until") or "").strip(),
                international_reputation=parse_int(row.get("International Reputation")),
                work_rate=(row.get("Work Rate") or "").strip(),
                body_type=(row.get("Body Type") or "").strip(),
                skills=skills,
                search_name=normalize_query(name),
            )
        )
    return players
