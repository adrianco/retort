"""CSV loaders for the six Brazilian soccer datasets in ``data/kaggle``.

Each loader turns one file into ``Match`` or ``Player`` records. Rows with
unplayed fixtures or unreadable dates/scores (``NA``, ``-``) are skipped and
counted in a ``LoadReport`` so the caller can see what was dropped.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .normalize import display_name, parse_date, parse_int, team_key
from .models import Match, Player

BRASILEIRAO = "Brasileirão Série A"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "historical": "novo_campeonato_brasileiro.csv",
    "cup": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "br_football": "BR-Football-Dataset.csv",
    "fifa": "fifa_data.csv",
}

SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle",
)

_TOURNAMENT_NAMES = {
    "Serie A": BRASILEIRAO,
    "Serie B": "Brasileirão Série B",
    "Serie C": "Brasileirão Série C",
    "Copa do Brasil": COPA_DO_BRASIL,
}


@dataclass
class LoadReport:
    """Counts of rows read and skipped per file, for transparency."""

    rows: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)

    def record(self, source: str, loaded: int, skipped: int) -> None:
        self.rows[source] = loaded
        self.skipped[source] = skipped


def _read_rows(path: Path):
    # utf-8-sig strips the byte-order mark that the FIFA export starts with.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def _match_from(
    *,
    source: str,
    raw_date: str,
    home: str,
    away: str,
    home_goals: str | None,
    away_goals: str | None,
    competition: str,
    season: str | None,
    round_label: str | None = None,
    stage: str | None = None,
    home_state: str | None = None,
    away_state: str | None = None,
) -> Match | None:
    """Build a Match or return None when the row is unplayed or malformed."""
    try:
        when = parse_date(raw_date)
    except ValueError:
        return None
    hg, ag = parse_int(home_goals), parse_int(away_goals)
    if hg is None or ag is None or not home.strip() or not away.strip():
        return None
    year = parse_int(season)
    return Match(
        date=when,
        competition=competition,
        home=display_name(home),
        away=display_name(away),
        home_key=team_key(home, home_state),
        away_key=team_key(away, away_state),
        home_goals=hg,
        away_goals=ag,
        season=year if year is not None else when.year,
        round=round_label or None,
        stage=stage or None,
        source=source,
    )


def _load_generic(path: Path, source: str, competition_for, **columns):
    matches, skipped = [], 0
    for row in _read_rows(path):
        match = _match_from(
            source=source,
            raw_date=row[columns["date"]],
            home=row[columns["home"]],
            away=row[columns["away"]],
            home_goals=row[columns["home_goals"]],
            away_goals=row[columns["away_goals"]],
            competition=competition_for(row),
            season=row.get(columns["season"]),
            round_label=row.get(columns.get("round", "")),
            stage=row.get(columns.get("stage", "")),
            home_state=row.get(columns.get("home_state", "")),
            away_state=row.get(columns.get("away_state", "")),
        )
        if match is None:
            skipped += 1
        else:
            matches.append(match)
    return matches, skipped


def load_brasileirao(path: Path):
    """Brasileirão Série A 2012+ (team names carry a ``-UF`` suffix)."""
    return _load_generic(
        path, "brasileirao", lambda row: BRASILEIRAO,
        date="datetime", home="home_team", away="away_team",
        home_goals="home_goal", away_goals="away_goal",
        season="season", round="round",
        home_state="home_team_state", away_state="away_team_state",
    )


def load_historical(path: Path):
    """Brasileirão 2003-2019 with ``DD/MM/YYYY`` dates."""
    matches, skipped = [], 0
    for row in _read_rows(path):
        match = _match_from(
            source="historical",
            raw_date=row["Data"],
            home=row["Equipe_mandante"],
            away=row["Equipe_visitante"],
            home_goals=row["Gols_mandante"],
            away_goals=row["Gols_visitante"],
            competition=BRASILEIRAO,
            season=row["Ano"],
            round_label=row["Rodada"],
            home_state=row["Mandante_UF"],
            away_state=row["Visitante_UF"],
        )
        if match is None:
            skipped += 1
        else:
            matches.append(match)
    return matches, skipped


def load_cup(path: Path):
    """Copa do Brasil; the round column is a bare number."""
    return _load_generic(
        path, "cup", lambda row: COPA_DO_BRASIL,
        date="datetime", home="home_team", away="away_team",
        home_goals="home_goal", away_goals="away_goal",
        season="season", round="round",
    )


def load_libertadores(path: Path):
    """Copa Libertadores with a stage column (group stage, final, ...)."""
    return _load_generic(
        path, "libertadores", lambda row: LIBERTADORES,
        date="datetime", home="home_team", away="away_team",
        home_goals="home_goal", away_goals="away_goal",
        season="season", stage="stage",
    )


def load_br_football(path: Path):
    """Extended statistics file: several Brazilian national tournaments."""
    matches, skipped = [], 0
    for row in _read_rows(path):
        competition = _TOURNAMENT_NAMES.get(row["tournament"], row["tournament"])
        when_raw = row["date"]
        match = _match_from(
            source="br_football",
            raw_date=when_raw,
            home=row["home"],
            away=row["away"],
            home_goals=row["home_goal"],
            away_goals=row["away_goal"],
            competition=competition,
            season=None,
        )
        if match is None:
            skipped += 1
        else:
            matches.append(match)
    return matches, skipped


def _attributes(row: dict[str, str]) -> dict[str, int | None]:
    return {col: parse_int(row.get(col)) for col in SKILL_COLUMNS}


def load_players(path: Path) -> tuple[list[Player], int]:
    """FIFA player database; rows without a numeric overall are skipped."""
    players, skipped = [], 0
    for row in _read_rows(path):
        overall = parse_int(row.get("Overall"))
        player_id = parse_int(row.get("ID"))
        if overall is None or player_id is None:
            skipped += 1
            continue
        players.append(Player(
            id=player_id,
            name=row["Name"].strip(),
            age=parse_int(row.get("Age")),
            nationality=row.get("Nationality", "").strip(),
            overall=overall,
            potential=parse_int(row.get("Potential")),
            club=row.get("Club", "").strip(),
            position=row.get("Position", "").strip(),
            jersey_number=parse_int(row.get("Jersey Number")),
            height=row.get("Height", "").strip(),
            weight=row.get("Weight", "").strip(),
            value=row.get("Value", "").strip(),
            wage=row.get("Wage", "").strip(),
            preferred_foot=row.get("Preferred Foot", "").strip(),
            attributes=_attributes(row),
        ))
    return players, skipped


def load_all(data_dir: Path) -> tuple[list[Match], list[Player], LoadReport]:
    """Load every dataset from ``data_dir`` and report per-file row counts."""
    report = LoadReport()
    loaders = (
        ("brasileirao", load_brasileirao),
        ("historical", load_historical),
        ("cup", load_cup),
        ("libertadores", load_libertadores),
        ("br_football", load_br_football),
    )
    matches: list[Match] = []
    for source, loader in loaders:
        loaded, skipped = loader(data_dir / FILES[source])
        report.record(source, len(loaded), skipped)
        matches.extend(loaded)

    players, skipped = load_players(data_dir / FILES["fifa"])
    report.record("fifa", len(players), skipped)
    return matches, players, report
