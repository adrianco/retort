"""CSV loading and indexed canonical catalog for the supplied datasets."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Iterable, Iterator, Mapping
import csv

from .models import MatchRecord, PlayerRecord
from .normalization import (
    clean_text,
    display_competition,
    normalize_competition,
    normalize_team,
    normalize_text,
    parse_date,
    parse_float,
    parse_int,
)


class CatalogLoadError(RuntimeError):
    """Raised when a required source file cannot be loaded safely."""


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    """The schema and canonical mapping for one bundled CSV file."""

    filename: str
    source: str
    kind: str
    required_columns: frozenset[str]
    fixed_competition: str | None = None


DATASET_SPECS: Final[tuple[DatasetSpec, ...]] = (
    DatasetSpec(
        filename="Brasileirao_Matches.csv",
        source="brasileirao_matches",
        kind="standard_match",
        fixed_competition="Brasileirão",
        required_columns=frozenset(
            {
                "datetime",
                "home_team",
                "away_team",
                "home_goal",
                "away_goal",
                "season",
                "round",
            }
        ),
    ),
    DatasetSpec(
        filename="Brazilian_Cup_Matches.csv",
        source="brazilian_cup_matches",
        kind="standard_match",
        fixed_competition="Copa do Brasil",
        required_columns=frozenset(
            {
                "datetime",
                "home_team",
                "away_team",
                "home_goal",
                "away_goal",
                "season",
                "round",
            }
        ),
    ),
    DatasetSpec(
        filename="Libertadores_Matches.csv",
        source="libertadores_matches",
        kind="standard_match",
        fixed_competition="Copa Libertadores",
        required_columns=frozenset(
            {
                "datetime",
                "home_team",
                "away_team",
                "home_goal",
                "away_goal",
                "season",
                "stage",
            }
        ),
    ),
    DatasetSpec(
        filename="BR-Football-Dataset.csv",
        source="extended_match_statistics",
        kind="extended_match",
        required_columns=frozenset(
            {
                "tournament",
                "home",
                "away",
                "home_goal",
                "away_goal",
                "date",
            }
        ),
    ),
    DatasetSpec(
        filename="novo_campeonato_brasileiro.csv",
        source="historical_brasileirao",
        kind="historical_match",
        fixed_competition="Brasileirão",
        required_columns=frozenset(
            {
                "ID",
                "Data",
                "Ano",
                "Rodada",
                "Equipe_mandante",
                "Equipe_visitante",
                "Gols_mandante",
                "Gols_visitante",
            }
        ),
    ),
    DatasetSpec(
        filename="fifa_data.csv",
        source="fifa_players",
        kind="player",
        required_columns=frozenset(
            {"ID", "Name", "Nationality", "Overall", "Club", "Position"}
        ),
    ),
)

_EXTENDED_NUMERIC_COLUMNS: Final[tuple[str, ...]] = (
    "home_corner",
    "away_corner",
    "home_attack",
    "away_attack",
    "home_shots",
    "away_shots",
    "total_corners",
    "ht_diff",
    "at_diff",
)
_PLAYER_ATTRIBUTE_COLUMNS: Final[tuple[str, ...]] = (
    "Crossing",
    "Finishing",
    "HeadingAccuracy",
    "ShortPassing",
    "Dribbling",
    "LongPassing",
    "BallControl",
    "Acceleration",
    "SprintSpeed",
    "Reactions",
    "Stamina",
    "Strength",
    "LongShots",
    "Vision",
    "Composure",
)


@dataclass(slots=True)
class SoccerCatalog:
    """Loaded source records plus indexes used for fast in-memory queries."""

    data_directory: Path
    matches: tuple[MatchRecord, ...]
    players: tuple[PlayerRecord, ...]
    source_row_counts: dict[str, int]
    source_files: dict[str, str]
    matches_by_team: dict[str, tuple[MatchRecord, ...]]
    matches_by_season: dict[int, tuple[MatchRecord, ...]]
    matches_by_competition: dict[str, tuple[MatchRecord, ...]]
    players_by_name: dict[str, tuple[PlayerRecord, ...]]
    players_by_club: dict[str, tuple[PlayerRecord, ...]]
    players_by_nationality: dict[str, tuple[PlayerRecord, ...]]

    @classmethod
    def from_directory(cls, data_directory: str | Path) -> "SoccerCatalog":
        """Load all six required CSV files and construct canonical indexes."""

        directory = Path(data_directory).expanduser().resolve()
        if not directory.is_dir():
            raise CatalogLoadError(f"Dataset directory does not exist: {directory}")

        matches: list[MatchRecord] = []
        players: list[PlayerRecord] = []
        source_row_counts: dict[str, int] = {}
        source_files: dict[str, str] = {}

        for spec in DATASET_SPECS:
            path = directory / spec.filename
            rows = list(_read_rows(path, spec))
            source_row_counts[spec.source] = len(rows)
            source_files[spec.source] = spec.filename

            if spec.kind == "player":
                players.extend(_player_from_row(row, spec, index) for index, row in rows)
                continue

            matches.extend(_match_from_row(row, spec, index) for index, row in rows)

        return cls(
            data_directory=directory,
            matches=tuple(matches),
            players=tuple(players),
            source_row_counts=source_row_counts,
            source_files=source_files,
            matches_by_team=_index_matches(matches, lambda match: (match.home_team_key, match.away_team_key)),
            matches_by_season=_index_matches(matches, lambda match: (match.season,)),
            matches_by_competition=_index_matches(
                matches, lambda match: (match.competition_key,)
            ),
            players_by_name=_index_players(players, lambda player: (player.name_key,)),
            players_by_club=_index_players(players, lambda player: (player.club_key,)),
            players_by_nationality=_index_players(
                players, lambda player: (player.nationality_key,)
            ),
        )

    @property
    def match_count(self) -> int:
        """Return the raw number of canonicalized match rows."""

        return len(self.matches)

    @property
    def player_count(self) -> int:
        """Return the raw number of FIFA player rows."""

        return len(self.players)


def default_data_directory() -> Path:
    """Find the bundled data when the project is run from its repository root."""

    repository_root = Path(__file__).resolve().parents[1]
    return repository_root / "data" / "kaggle"


@lru_cache(maxsize=4)
def load_catalog(data_directory: str | Path | None = None) -> SoccerCatalog:
    """Load and cache a catalog by absolute dataset directory."""

    directory = Path(data_directory) if data_directory is not None else default_data_directory()
    return SoccerCatalog.from_directory(directory)


def _read_rows(path: Path, spec: DatasetSpec) -> Iterator[tuple[int, dict[str, str]]]:
    if not path.is_file():
        raise CatalogLoadError(f"Required dataset is missing: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = frozenset(name.strip() for name in (reader.fieldnames or []) if name)
        missing = sorted(spec.required_columns - fieldnames)
        if missing:
            joined = ", ".join(missing)
            raise CatalogLoadError(f"{path.name} is missing required columns: {joined}")

        for index, row in enumerate(reader, start=1):
            # DictReader can emit None keys for malformed trailing fields. They
            # are irrelevant to the documented schema and must not crash loading.
            yield index, {str(key).strip(): clean_text(value) for key, value in row.items() if key}


def _match_from_row(row: Mapping[str, str], spec: DatasetSpec, index: int) -> MatchRecord:
    if spec.kind == "standard_match":
        home_team = clean_text(row.get("home_team"))
        away_team = clean_text(row.get("away_team"))
        match_date = parse_date(row.get("datetime"))
        season = parse_int(row.get("season")) or (match_date.year if match_date else None)
        competition = spec.fixed_competition or "Unknown competition"
        round_value = clean_text(row.get("round")) or None
        stage = clean_text(row.get("stage")) or None
        home_goals = parse_int(row.get("home_goal"))
        away_goals = parse_int(row.get("away_goal"))
        home_state = clean_text(row.get("home_team_state")) or None
        away_state = clean_text(row.get("away_team_state")) or None
        statistics: dict[str, Any] = {}
    elif spec.kind == "extended_match":
        home_team = clean_text(row.get("home"))
        away_team = clean_text(row.get("away"))
        match_date = parse_date(row.get("date"))
        season = match_date.year if match_date else None
        competition = display_competition(row.get("tournament"))
        round_value = None
        stage = None
        home_goals = parse_int(row.get("home_goal"))
        away_goals = parse_int(row.get("away_goal"))
        home_state = None
        away_state = None
        statistics = _extended_statistics(row)
    elif spec.kind == "historical_match":
        home_team = clean_text(row.get("Equipe_mandante"))
        away_team = clean_text(row.get("Equipe_visitante"))
        match_date = parse_date(row.get("Data"))
        season = parse_int(row.get("Ano")) or (match_date.year if match_date else None)
        competition = spec.fixed_competition or "Unknown competition"
        round_value = clean_text(row.get("Rodada")) or None
        stage = None
        home_goals = parse_int(row.get("Gols_mandante"))
        away_goals = parse_int(row.get("Gols_visitante"))
        home_state = clean_text(row.get("Mandante_UF")) or None
        away_state = clean_text(row.get("Visitante_UF")) or None
        statistics = {
            key: value
            for key, value in {
                "winner_source_value": clean_text(row.get("Vencedor")) or None,
                "kickoff_time": clean_text(row.get("time")) or None,
            }.items()
            if value is not None
        }
        venue = clean_text(row.get("Arena")) or None
        return MatchRecord(
            id=f"{spec.source}:{clean_text(row.get('ID')) or index}",
            source=spec.source,
            source_file=spec.filename,
            competition=competition,
            competition_key=normalize_competition(competition),
            match_date=match_date,
            season=season,
            round=round_value,
            stage=stage,
            home_team=home_team,
            away_team=away_team,
            home_team_key=normalize_team(home_team),
            away_team_key=normalize_team(away_team),
            home_goals=home_goals,
            away_goals=away_goals,
            home_state=home_state,
            away_state=away_state,
            venue=venue,
            statistics=statistics,
        )
    else:  # pragma: no cover - guards future DatasetSpec additions
        raise CatalogLoadError(f"Unsupported match dataset kind: {spec.kind}")

    return MatchRecord(
        id=f"{spec.source}:{index}",
        source=spec.source,
        source_file=spec.filename,
        competition=competition,
        competition_key=normalize_competition(competition),
        match_date=match_date,
        season=season,
        round=round_value,
        stage=stage,
        home_team=home_team,
        away_team=away_team,
        home_team_key=normalize_team(home_team),
        away_team_key=normalize_team(away_team),
        home_goals=home_goals,
        away_goals=away_goals,
        home_state=home_state,
        away_state=away_state,
        venue=None,
        statistics=statistics,
    )


def _extended_statistics(row: Mapping[str, str]) -> dict[str, Any]:
    statistics: dict[str, Any] = {}
    for column in _EXTENDED_NUMERIC_COLUMNS:
        value = parse_float(row.get(column))
        if value is not None:
            statistics[column] = value
    for column in ("time", "ht_result", "at_result"):
        value = clean_text(row.get(column))
        if value:
            statistics[column] = value
    return statistics


def _player_from_row(row: Mapping[str, str], spec: DatasetSpec, index: int) -> PlayerRecord:
    name = clean_text(row.get("Name"))
    club = clean_text(row.get("Club"))
    nationality = clean_text(row.get("Nationality"))
    attributes = {
        column: value
        for column in _PLAYER_ATTRIBUTE_COLUMNS
        if (value := parse_int(row.get(column))) is not None
    }
    return PlayerRecord(
        id=clean_text(row.get("ID")) or f"{spec.source}:{index}",
        name=name,
        name_key=normalize_text(name),
        age=parse_int(row.get("Age")),
        nationality=nationality,
        nationality_key=normalize_text(nationality),
        overall=parse_int(row.get("Overall")),
        potential=parse_int(row.get("Potential")),
        club=club,
        club_key=normalize_team(club),
        position=clean_text(row.get("Position")),
        jersey_number=parse_int(row.get("Jersey Number")),
        height=clean_text(row.get("Height")) or None,
        weight=clean_text(row.get("Weight")) or None,
        attributes=attributes,
    )


def _index_matches(
    records: Iterable[MatchRecord], key_factory: Any
) -> dict[Any, tuple[MatchRecord, ...]]:
    index: dict[Any, list[MatchRecord]] = defaultdict(list)
    for record in records:
        for key in key_factory(record):
            if key is not None and key != "":
                index[key].append(record)
    return {key: tuple(value) for key, value in index.items()}


def _index_players(
    records: Iterable[PlayerRecord], key_factory: Any
) -> dict[Any, tuple[PlayerRecord, ...]]:
    index: dict[Any, list[PlayerRecord]] = defaultdict(list)
    for record in records:
        for key in key_factory(record):
            if key:
                index[key].append(record)
    return {key: tuple(value) for key, value in index.items()}

