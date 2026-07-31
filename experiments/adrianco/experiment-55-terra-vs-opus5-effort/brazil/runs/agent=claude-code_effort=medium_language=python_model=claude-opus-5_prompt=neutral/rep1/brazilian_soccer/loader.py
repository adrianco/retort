"""CSV readers for the six Kaggle datasets in ``data/kaggle/``.

Context
-------
One reader per file, each yielding :class:`~brazilian_soccer.models.Match` (or
:class:`~brazilian_soccer.models.Player`) records with normalised team keys,
parsed dates and integer scores.  All files are opened as UTF-8 (the FIFA file
carries a BOM, so it uses ``utf-8-sig``) to preserve ``São``/``Grêmio``/``Avaí``.

Source -> competition mapping::

    Brasileirao_Matches.csv         Brasileirão Série A   (2012-2023)
    novo_campeonato_brasileiro.csv  Brasileirão Série A   (2003-2019)
    BR-Football-Dataset.csv         Série A/B/C + Copa do Brasil (2014-2023)
    Brazilian_Cup_Matches.csv       Copa do Brasil
    Libertadores_Matches.csv        Copa Libertadores
    fifa_data.csv                   players

The first three overlap heavily; de-duplication is the graph layer's job
(:mod:`brazilian_soccer.graph`), not the loader's.
"""

from __future__ import annotations

import csv
import sys
from collections.abc import Iterator
from pathlib import Path

from .models import (
    BRASILEIRAO,
    LEAGUE_COMPETITIONS,
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_B,
    SERIE_C,
    Match,
    Player,
)
from .normalization import normalize_team, parse_date, parse_float, parse_int

#: Repository-relative location of the provided datasets.
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

DATA_FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "copa_do_brasil": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "br_football": "BR-Football-Dataset.csv",
    "historico": "novo_campeonato_brasileiro.csv",
    "fifa": "fifa_data.csv",
}

#: ``tournament`` column values in BR-Football-Dataset.csv -> canonical name.
_BR_FOOTBALL_TOURNAMENTS = {
    "serie a": BRASILEIRAO,
    "serie b": SERIE_B,
    "serie c": SERIE_C,
    "copa do brasil": COPA_DO_BRASIL,
}

# The FIFA skill columns worth exposing (the file has ~90 columns in total).
_FIFA_SKILLS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)


def _read_rows(path: Path, encoding: str = "utf-8") -> Iterator[dict[str, str]]:
    """Stream a CSV as dicts, tolerating the odd oversized field."""
    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
    with path.open("r", encoding=encoding, newline="") as handle:
        yield from csv.DictReader(handle)


def _make_match(
    *,
    competition: str,
    season: int | None,
    match_date,
    home_raw: str,
    away_raw: str,
    home_goals,
    away_goals,
    source: str,
    round_: str | None = None,
    stage: str | None = None,
    venue: str | None = None,
    home_state: str | None = None,
    away_state: str | None = None,
    stats: dict[str, float] | None = None,
) -> Match | None:
    """Build a Match, dropping rows the sources got wrong.

    Three rows are rejected: unnamed teams, a club playing itself (two rows in
    ``Brazilian_Cup_Matches.csv`` list ``Bragantino - PA`` on both sides), and
    rows with neither a date nor a season (the 2022 Libertadores final is
    recorded as ``NA,"Flamengo","Athletico","-","-",NA``).
    """
    home = normalize_team(home_raw)
    away = normalize_team(away_raw)
    if not home.key or not away.key or home.key == away.key:
        return None
    if season is None and match_date is not None:
        season = match_date.year
    if season is None and match_date is None:
        return None
    return Match(
        competition=competition,
        season=season,
        match_date=match_date,
        home_key=home.key,
        away_key=away.key,
        home_name=home.display,
        away_name=away.display,
        home_goals=home_goals,
        away_goals=away_goals,
        round=round_,
        stage=stage,
        venue=venue or None,
        home_state=(home_state or home.region or None),
        away_state=(away_state or away.region or None),
        sources={source},
        stats=stats or {},
    )


# --------------------------------------------------------------------------
# match readers
# --------------------------------------------------------------------------


def load_brasileirao(path: Path) -> Iterator[Match]:
    """``Brasileirao_Matches.csv`` -- Série A with state suffixes and rounds."""
    for row in _read_rows(path):
        match = _make_match(
            competition=BRASILEIRAO,
            season=parse_int(row.get("season")),
            match_date=parse_date(row.get("datetime")),
            home_raw=row.get("home_team", ""),
            away_raw=row.get("away_team", ""),
            home_goals=parse_int(row.get("home_goal")),
            away_goals=parse_int(row.get("away_goal")),
            round_=(row.get("round") or "").strip() or None,
            home_state=(row.get("home_team_state") or "").strip() or None,
            away_state=(row.get("away_team_state") or "").strip() or None,
            source="Brasileirao_Matches.csv",
        )
        if match:
            yield match


def load_copa_do_brasil(path: Path) -> Iterator[Match]:
    """``Brazilian_Cup_Matches.csv`` -- Copa do Brasil, ``round`` is the stage."""
    for row in _read_rows(path):
        round_ = (row.get("round") or "").strip() or None
        match = _make_match(
            competition=COPA_DO_BRASIL,
            season=parse_int(row.get("season")),
            match_date=parse_date(row.get("datetime")),
            home_raw=row.get("home_team", ""),
            away_raw=row.get("away_team", ""),
            home_goals=parse_int(row.get("home_goal")),
            away_goals=parse_int(row.get("away_goal")),
            round_=round_,
            stage=_cup_stage(round_),
            source="Brazilian_Cup_Matches.csv",
        )
        if match:
            yield match


def _cup_stage(round_: str | None) -> str | None:
    """Copa do Brasil rounds are numbered 1..8; 8 is the final, 7 the semis."""
    number = parse_int(round_)
    if number is None:
        return round_
    return {
        8: "final",
        7: "semi-final",
        6: "quarter-final",
        5: "round of 16",
    }.get(number, f"round {number}")


def load_libertadores(path: Path) -> Iterator[Match]:
    """``Libertadores_Matches.csv`` -- continental cup with a ``stage`` column."""
    for row in _read_rows(path):
        match = _make_match(
            competition=LIBERTADORES,
            season=parse_int(row.get("season")),
            match_date=parse_date(row.get("datetime")),
            home_raw=row.get("home_team", ""),
            away_raw=row.get("away_team", ""),
            home_goals=parse_int(row.get("home_goal")),
            away_goals=parse_int(row.get("away_goal")),
            stage=(row.get("stage") or "").strip() or None,
            source="Libertadores_Matches.csv",
        )
        if match:
            yield match


def _br_football_season(competition: str, match_date) -> int | None:
    """Infer the season for a row that only carries a date.

    The Brazilian league season runs roughly April-December, but the pandemic
    pushed the 2020 campaign into February 2021.  Any league fixture played in
    January-March therefore belongs to the *previous* season -- without this,
    39 tail-end 2020 matches would land in 2021 and fail to de-duplicate against
    the same fixtures in ``Brasileirao_Matches.csv``.
    """
    if match_date is None:
        return None
    if competition in LEAGUE_COMPETITIONS and match_date.month <= 3:
        return match_date.year - 1
    return match_date.year


def load_br_football(path: Path) -> Iterator[Match]:
    """``BR-Football-Dataset.csv`` -- adds corners/shots/attacks per match."""
    for row in _read_rows(path):
        tournament = (row.get("tournament") or "").strip()
        competition = _BR_FOOTBALL_TOURNAMENTS.get(tournament.lower())
        if competition is None:
            continue
        match_date = parse_date(row.get("date"))
        stats = {
            name: value
            for name, value in (
                ("home_corners", parse_float(row.get("home_corner"))),
                ("away_corners", parse_float(row.get("away_corner"))),
                ("total_corners", parse_float(row.get("total_corners"))),
                ("home_attacks", parse_float(row.get("home_attack"))),
                ("away_attacks", parse_float(row.get("away_attack"))),
                ("home_shots", parse_float(row.get("home_shots"))),
                ("away_shots", parse_float(row.get("away_shots"))),
            )
            if value is not None
        }
        match = _make_match(
            competition=competition,
            season=_br_football_season(competition, match_date),
            match_date=match_date,
            home_raw=row.get("home", ""),
            away_raw=row.get("away", ""),
            home_goals=parse_int(row.get("home_goal")),
            away_goals=parse_int(row.get("away_goal")),
            source="BR-Football-Dataset.csv",
            stats=stats,
        )
        if match:
            yield match


def load_historico(path: Path) -> Iterator[Match]:
    """``novo_campeonato_brasileiro.csv`` -- 2003-2019 Série A, with stadiums."""
    for row in _read_rows(path):
        match = _make_match(
            competition=BRASILEIRAO,
            season=parse_int(row.get("Ano")),
            match_date=parse_date(row.get("Data")),
            home_raw=row.get("Equipe_mandante", ""),
            away_raw=row.get("Equipe_visitante", ""),
            home_goals=parse_int(row.get("Gols_mandante")),
            away_goals=parse_int(row.get("Gols_visitante")),
            round_=(row.get("Rodada") or "").strip() or None,
            venue=(row.get("Arena") or "").strip() or None,
            home_state=(row.get("Mandante_UF") or "").strip() or None,
            away_state=(row.get("Visitante_UF") or "").strip() or None,
            source="novo_campeonato_brasileiro.csv",
        )
        if match:
            yield match


MATCH_READERS = {
    "brasileirao": load_brasileirao,
    "copa_do_brasil": load_copa_do_brasil,
    "libertadores": load_libertadores,
    "br_football": load_br_football,
    "historico": load_historico,
}


def load_all_matches(data_dir: Path | str = DEFAULT_DATA_DIR) -> Iterator[Match]:
    """Yield every match from every available match file."""
    data_dir = Path(data_dir)
    for name, reader in MATCH_READERS.items():
        path = data_dir / DATA_FILES[name]
        if path.exists():
            yield from reader(path)


# --------------------------------------------------------------------------
# player reader
# --------------------------------------------------------------------------


def load_players(path: Path) -> Iterator[Player]:
    """``fifa_data.csv`` -- 18k players; club strings are matched to team keys."""
    for row in _read_rows(path, encoding="utf-8-sig"):
        name = (row.get("Name") or "").strip()
        if not name:
            continue
        club_raw = (row.get("Club") or "").strip()
        skills = {
            column: value
            for column in _FIFA_SKILLS
            if (value := parse_int(row.get(column))) is not None
        }
        yield Player(
            player_id=parse_int(row.get("ID")),
            name=name,
            age=parse_int(row.get("Age")),
            nationality=(row.get("Nationality") or "").strip(),
            overall=parse_int(row.get("Overall")),
            potential=parse_int(row.get("Potential")),
            club_raw=club_raw,
            club_key=normalize_team(club_raw).key if club_raw else "",
            position=(row.get("Position") or "").strip() or None,
            jersey_number=parse_int(row.get("Jersey Number")),
            height=(row.get("Height") or "").strip() or None,
            weight=(row.get("Weight") or "").strip() or None,
            value=(row.get("Value") or "").strip() or None,
            wage=(row.get("Wage") or "").strip() or None,
            preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
            skills=skills,
        )


def load_all_players(data_dir: Path | str = DEFAULT_DATA_DIR) -> Iterator[Player]:
    path = Path(data_dir) / DATA_FILES["fifa"]
    if path.exists():
        yield from load_players(path)
