"""Data access and analysis for the bundled Brazilian soccer CSV files.

The module intentionally uses only the Python standard library.  This keeps the
MCP server easy to run in an isolated environment and makes the data layer useful
from tests, a REPL, or another transport besides MCP.
"""

from __future__ import annotations

import csv
import re
import threading
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


DATA_FILENAMES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "brazilian_cup": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "extended": "BR-Football-Dataset.csv",
    "historical": "novo_campeonato_brasileiro.csv",
    "players": "fifa_data.csv",
}

BRASILEIRAO = "Brasileirão Série A"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

_STATE_CODES = {
    "ac",
    "al",
    "am",
    "ap",
    "ba",
    "ce",
    "df",
    "es",
    "go",
    "ma",
    "mg",
    "ms",
    "mt",
    "pa",
    "pb",
    "pe",
    "pi",
    "pr",
    "rj",
    "rn",
    "ro",
    "rr",
    "rs",
    "sc",
    "se",
    "sp",
    "to",
}

# The aliases cover the common long-form names in the source data while keeping
# names such as Flamengo and Flamengo do Piauí distinct.
_TEAM_ALIASES = {
    "club de regatas do flamengo": "flamengo",
    "cr flamengo": "flamengo",
    "flamengo rj": "flamengo",
    "flamengo pi": "flamengo piaui",
    "flamengo do piaui pi": "flamengo piaui",
    "flamengo do piaui": "flamengo piaui",
    "sport club corinthians paulista": "corinthians",
    "sc corinthians paulista": "corinthians",
    "corinthians paulista": "corinthians",
    "sao paulo fc": "sao paulo",
    "santos fc": "santos",
    "se palmeiras": "palmeiras",
    "palmeiras sp": "palmeiras",
    "gremio fbpa": "gremio",
    "gremio porto alegrense": "gremio",
    "club de regatas vasco da gama": "vasco",
    "vasco da gama": "vasco",
    "atletico mg": "atletico mineiro",
    "atletico mineiro mg": "atletico mineiro",
    "clube atletico mineiro": "atletico mineiro",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "athletico paranaense pr": "athletico paranaense",
    "atletico go": "atletico goianiense",
    "atletico goianiense go": "atletico goianiense",
    "coritiba pr": "coritiba",
    "cruzeiro mg": "cruzeiro",
    "fluminense rj": "fluminense",
    "botafogo rj": "botafogo",
    "internacional rs": "internacional",
    "bahia ba": "bahia",
    "vitoria ba": "vitoria",
    "fortaleza ce": "fortaleza",
    "ceara ce": "ceara",
    "goias go": "goias",
    "sport pe": "sport",
    "nautico pe": "nautico",
    "avai sc": "avai",
    "figueirense sc": "figueirense",
    "america mg": "america mineiro",
    "america rn": "america natal",
    "america de natal": "america natal",
    "america de natal rn": "america natal",
    "america fc natal": "america natal",
}

_NATIONALITY_ALIASES = {
    "brazilian": "brazil",
    "brasil": "brazil",
}

_TEAM_DISPLAY_NAMES = {
    "athletico paranaense": "Athletico Paranaense",
    "atletico mineiro": "Atlético Mineiro",
    "america mineiro": "América Mineiro",
    "america natal": "América de Natal",
    "flamengo piaui": "Flamengo do Piauí",
    "sao paulo": "São Paulo",
    "gremio": "Grêmio",
    "avai": "Avaí",
    "ceara": "Ceará",
    "goias": "Goiás",
    "nautico": "Náutico",
    "vitoria": "Vitória",
}

_COMPETITION_ALIASES = {
    "brasileirao": BRASILEIRAO,
    "campeonato brasileiro": BRASILEIRAO,
    "brasileirao serie a": BRASILEIRAO,
    "serie a": BRASILEIRAO,
    "copa do brasil": COPA_DO_BRASIL,
    "copa brasil": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
    "conmebol libertadores": LIBERTADORES,
    "serie b": "Série B",
    "serie c": "Série C",
}

_DERBIES = {
    frozenset(("flamengo", "fluminense")): "Fla-Flu",
    frozenset(("corinthians", "palmeiras")): "Derby Paulista",
    frozenset(("corinthians", "sao paulo")): "Majestoso",
    frozenset(("palmeiras", "sao paulo")): "Choque-Rei",
    frozenset(("santos", "palmeiras")): "Clássico da Saudade",
    frozenset(("santos", "corinthians")): "Clássico Alvinegro",
    frozenset(("gremio", "internacional")): "Grenal",
    frozenset(("atletico mineiro", "cruzeiro")): "Clássico Mineiro",
    frozenset(("athletico paranaense", "coritiba")): "Atletiba",
    frozenset(("bahia", "vitoria")): "Ba-Vi",
    frozenset(("ceara", "fortaleza")): "Clássico-Rei",
    frozenset(("botafogo", "flamengo")): "Clássico da Rivalidade",
    frozenset(("botafogo", "fluminense")): "Clássico Vovô",
    frozenset(("vasco", "flamengo")): "Clássico dos Milhões",
    frozenset(("vasco", "fluminense")): "Clássico dos Gigantes",
}

_POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "goalkeepers": {"GK"},
    "defender": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB", "SW"},
    "defenders": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB", "SW"},
    "midfielder": {"CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"},
    "midfielders": {"CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"},
    "forward": {"ST", "CF", "LF", "RF", "LW", "RW"},
    "forwards": {"ST", "CF", "LF", "RF", "LW", "RW"},
    "striker": {"ST", "CF"},
    "strikers": {"ST", "CF"},
}

_PLAYER_ATTRIBUTE_COLUMNS = (
    "Crossing",
    "Finishing",
    "HeadingAccuracy",
    "ShortPassing",
    "Volleys",
    "Dribbling",
    "Curve",
    "FKAccuracy",
    "LongPassing",
    "BallControl",
    "Acceleration",
    "SprintSpeed",
    "Agility",
    "Reactions",
    "Balance",
    "ShotPower",
    "Jumping",
    "Stamina",
    "Strength",
    "LongShots",
    "Aggression",
    "Interceptions",
    "Positioning",
    "Vision",
    "Penalties",
    "Composure",
    "Marking",
    "StandingTackle",
    "SlidingTackle",
    "GKDiving",
    "GKHandling",
    "GKKicking",
    "GKPositioning",
    "GKReflexes",
)


class DataLoadError(RuntimeError):
    """Raised when a required bundled dataset cannot be read."""


def normalize_text(value: object | None) -> str:
    """Return an accent-insensitive, punctuation-neutral search key."""

    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def normalize_team_name(value: object | None) -> str:
    """Normalize common Brazilian club spelling, suffix, and accent variations."""

    key = normalize_text(value)
    if not key:
        return ""
    if key in _TEAM_ALIASES:
        return _TEAM_ALIASES[key]

    parts = key.split()
    if len(parts) > 1 and parts[-1] in _STATE_CODES:
        key = " ".join(parts[:-1])
    if key in _TEAM_ALIASES:
        return _TEAM_ALIASES[key]

    # FC often appears only in a user's query (e.g. São Paulo FC).
    key = re.sub(r"\b(?:fc|futebol clube|football club)$", "", key).strip()
    return _TEAM_ALIASES.get(key, key)


def display_team_name(value: object | None) -> str:
    """Produce a readable team label while preserving a useful source spelling."""

    key = normalize_team_name(value)
    if key in _TEAM_DISPLAY_NAMES:
        return _TEAM_DISPLAY_NAMES[key]
    raw = str(value or "").strip()
    raw = re.sub(r"\s*-\s*(?:" + "|".join(_STATE_CODES) + r")$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s+", " ", raw).strip(" -")
    return raw or key.title()


def normalize_competition_name(value: object | None) -> str:
    """Map source-specific competition labels to stable display labels."""

    key = normalize_text(value)
    if not key:
        return ""
    if key in _COMPETITION_ALIASES:
        return _COMPETITION_ALIASES[key]
    if "libertadores" in key:
        return LIBERTADORES
    if "copa" in key and "brasil" in key:
        return COPA_DO_BRASIL
    if "brasileirao" in key or key == "serie a":
        return BRASILEIRAO
    return str(value).strip()


def _normalize_nationality(value: object | None) -> str:
    key = normalize_text(value)
    return _NATIONALITY_ALIASES.get(key, key)


def parse_match_date(value: object | None) -> date | None:
    """Parse the ISO and Brazilian date formats used by the supplied CSVs."""

    if value is None:
        return None
    text = str(value).strip()
    if not text or text.casefold() in {"nan", "nat", "none", "null"}:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _integer(value: object | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.casefold() in {"nan", "none", "null"}:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _as_season(value: object | None, match_date: date | None) -> int | None:
    parsed = _integer(value)
    return parsed if parsed is not None else (match_date.year if match_date else None)


def _team_matches(query: object | None, candidate_key: str) -> bool:
    query_key = normalize_team_name(query)
    if not query_key:
        return True
    if query_key == candidate_key:
        return True

    query_tokens = set(query_key.split())
    candidate_tokens = set(candidate_key.split())
    # This permits "Sport Club Corinthians Paulista" and similar long forms,
    # without treating a one-character fragment as a club search.
    return len(query_tokens) > 1 and (
        query_tokens <= candidate_tokens or candidate_tokens <= query_tokens
    )


def _competition_matches(query: object | None, competition: str) -> bool:
    if query is None or not str(query).strip():
        return True
    normalized_query = normalize_competition_name(query)
    if normalize_text(normalized_query) == normalize_text(competition):
        return True
    return normalize_text(query) in normalize_text(competition)


def _round_or_stage_matches(query: object | None, value: str | None) -> bool:
    if query is None or not str(query).strip():
        return True
    if value is None:
        return False
    return normalize_text(query) in normalize_text(value)


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / denominator, 3) if denominator else 0.0


def _percent(numerator: int | float, denominator: int | float) -> float:
    return round(100 * float(numerator) / denominator, 1) if denominator else 0.0


@dataclass(frozen=True, slots=True)
class Match:
    """A normalized row from any one of the five match CSV files."""

    source: str
    row_number: int
    competition: str
    match_date: date | None
    home_team: str
    away_team: str
    home_key: str
    away_key: str
    home_goals: int | None
    away_goals: int | None
    season: int | None
    round: str | None = None
    stage: str | None = None
    venue: str | None = None
    details: Mapping[str, str] | None = None

    @property
    def identifier(self) -> str:
        return f"{self.source}:{self.row_number}"

    @property
    def is_completed(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def goal_difference(self) -> int | None:
        if not self.is_completed:
            return None
        return abs(self.home_goals - self.away_goals)

    def to_dict(self, *, include_details: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.identifier,
            "date": self.match_date.isoformat() if self.match_date else None,
            "competition": self.competition,
            "season": self.season,
            "home_team": display_team_name(self.home_team),
            "away_team": display_team_name(self.away_team),
            "home_goal": self.home_goals,
            "away_goal": self.away_goals,
            "score": (
                f"{self.home_goals}-{self.away_goals}" if self.is_completed else None
            ),
            "round": self.round,
            "stage": self.stage,
            "venue": self.venue,
            "source": self.source,
        }
        if include_details and self.details:
            result["match_statistics"] = dict(self.details)
        return result


@dataclass(frozen=True, slots=True)
class Player:
    """A searchable subset of a FIFA player-data row."""

    player_id: str
    name: str
    name_key: str
    age: int | None
    nationality: str | None
    nationality_key: str
    overall: int | None
    potential: int | None
    club: str | None
    club_key: str
    position: str | None
    jersey_number: int | None
    height: str | None
    weight: str | None
    preferred_foot: str | None
    attributes: Mapping[str, int]

    def to_dict(self, *, include_attributes: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.player_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
            "preferred_foot": self.preferred_foot,
        }
        if include_attributes:
            result["attributes"] = dict(self.attributes)
        return result


class SoccerRepository:
    """Loads the bundled data once and exposes normalized soccer queries.

    Match searches intentionally retain source rows, including duplicate games
    present in overlapping datasets.  Analytical methods instead select one
    authoritative source per competition/season so standings and records are not
    inflated by those duplicates.
    """

    def __init__(self, data_dir: str | Path | None = None, *, strict: bool = True):
        base_dir = Path(__file__).resolve().parent / "data" / "kaggle"
        self.data_dir = Path(data_dir) if data_dir is not None else base_dir
        self.strict = strict
        self._matches: tuple[Match, ...] = ()
        self._players: tuple[Player, ...] = ()
        self._loaded = False
        self._lock = threading.RLock()
        self._source_counts: dict[str, int] = {}

    @classmethod
    def from_default_data(cls) -> "SoccerRepository":
        return cls()

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def matches(self) -> tuple[Match, ...]:
        self.ensure_loaded()
        return self._matches

    @property
    def players(self) -> tuple[Player, ...]:
        self.ensure_loaded()
        return self._players

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            matches, players, counts = self._load_all()
            self._matches = tuple(matches)
            self._players = tuple(players)
            self._source_counts = counts
            self._loaded = True

    def reload(self) -> None:
        """Clear cached rows; the next query re-reads the CSV files."""

        with self._lock:
            self._matches = ()
            self._players = ()
            self._source_counts = {}
            self._loaded = False

    def dataset_summary(self) -> dict[str, Any]:
        self.ensure_loaded()
        return {
            "data_directory": str(self.data_dir),
            "match_count": len(self._matches),
            "player_count": len(self._players),
            "sources": dict(sorted(self._source_counts.items())),
            "competitions": self.list_competitions(),
        }

    def _required_path(self, filename: str) -> Path | None:
        path = self.data_dir / filename
        if path.exists():
            return path
        if self.strict:
            raise DataLoadError(f"Required dataset is missing: {path}")
        return None

    def _read_rows(self, filename: str) -> Iterator[dict[str, str]]:
        path = self._required_path(filename)
        if path is None:
            return
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                yield from csv.DictReader(csv_file)
        except OSError as exc:
            raise DataLoadError(f"Could not read dataset {path}: {exc}") from exc

    def _load_all(self) -> tuple[list[Match], list[Player], dict[str, int]]:
        matches: list[Match] = []
        counts: Counter[str] = Counter()

        for row_number, row in enumerate(self._read_rows(DATA_FILENAMES["brasileirao"]), start=2):
            match = self._make_match(
                source=DATA_FILENAMES["brasileirao"],
                row_number=row_number,
                competition=BRASILEIRAO,
                date_value=row.get("datetime"),
                home_team=row.get("home_team"),
                away_team=row.get("away_team"),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                season=row.get("season"),
                round_value=row.get("round"),
                details={
                    "home_team_state": row.get("home_team_state", ""),
                    "away_team_state": row.get("away_team_state", ""),
                },
            )
            matches.append(match)
            counts[match.source] += 1

        for row_number, row in enumerate(self._read_rows(DATA_FILENAMES["brazilian_cup"]), start=2):
            match = self._make_match(
                source=DATA_FILENAMES["brazilian_cup"],
                row_number=row_number,
                competition=COPA_DO_BRASIL,
                date_value=row.get("datetime"),
                home_team=row.get("home_team"),
                away_team=row.get("away_team"),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                season=row.get("season"),
                round_value=row.get("round"),
            )
            matches.append(match)
            counts[match.source] += 1

        for row_number, row in enumerate(self._read_rows(DATA_FILENAMES["libertadores"]), start=2):
            match = self._make_match(
                source=DATA_FILENAMES["libertadores"],
                row_number=row_number,
                competition=LIBERTADORES,
                date_value=row.get("datetime"),
                home_team=row.get("home_team"),
                away_team=row.get("away_team"),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                season=row.get("season"),
                stage=row.get("stage"),
            )
            matches.append(match)
            counts[match.source] += 1

        for row_number, row in enumerate(self._read_rows(DATA_FILENAMES["extended"]), start=2):
            details = {
                key: value
                for key, value in row.items()
                if key
                not in {
                    "tournament",
                    "home",
                    "away",
                    "home_goal",
                    "away_goal",
                    "date",
                }
                and value not in (None, "")
            }
            match = self._make_match(
                source=DATA_FILENAMES["extended"],
                row_number=row_number,
                competition=normalize_competition_name(row.get("tournament")),
                date_value=row.get("date"),
                home_team=row.get("home"),
                away_team=row.get("away"),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                season=None,
                details=details,
            )
            matches.append(match)
            counts[match.source] += 1

        for row_number, row in enumerate(self._read_rows(DATA_FILENAMES["historical"]), start=2):
            details = {
                key: value
                for key, value in row.items()
                if key
                not in {
                    "ID",
                    "Data",
                    "Ano",
                    "Rodada",
                    "Equipe_mandante",
                    "Equipe_visitante",
                    "Gols_mandante",
                    "Gols_visitante",
                    "Arena",
                }
                and value not in (None, "")
            }
            match = self._make_match(
                source=DATA_FILENAMES["historical"],
                row_number=row_number,
                competition=BRASILEIRAO,
                date_value=row.get("Data"),
                home_team=row.get("Equipe_mandante"),
                away_team=row.get("Equipe_visitante"),
                home_goals=row.get("Gols_mandante"),
                away_goals=row.get("Gols_visitante"),
                season=row.get("Ano"),
                round_value=row.get("Rodada"),
                venue=row.get("Arena"),
                details=details,
            )
            matches.append(match)
            counts[match.source] += 1

        players: list[Player] = []
        for row in self._read_rows(DATA_FILENAMES["players"]):
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            attributes = {
                column: value
                for column in _PLAYER_ATTRIBUTE_COLUMNS
                if (value := _integer(row.get(column))) is not None
            }
            players.append(
                Player(
                    player_id=(row.get("ID") or "").strip(),
                    name=name,
                    name_key=normalize_text(name),
                    age=_integer(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip() or None,
                    nationality_key=normalize_text(row.get("Nationality")),
                    overall=_integer(row.get("Overall")),
                    potential=_integer(row.get("Potential")),
                    club=(row.get("Club") or "").strip() or None,
                    club_key=normalize_team_name(row.get("Club")),
                    position=(row.get("Position") or "").strip() or None,
                    jersey_number=_integer(row.get("Jersey Number")),
                    height=(row.get("Height") or "").strip() or None,
                    weight=(row.get("Weight") or "").strip() or None,
                    preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                    attributes=attributes,
                )
            )
        counts[DATA_FILENAMES["players"]] = len(players)
        return matches, players, dict(counts)

    @staticmethod
    def _make_match(
        *,
        source: str,
        row_number: int,
        competition: str,
        date_value: object | None,
        home_team: object | None,
        away_team: object | None,
        home_goals: object | None,
        away_goals: object | None,
        season: object | None,
        round_value: object | None = None,
        stage: object | None = None,
        venue: object | None = None,
        details: Mapping[str, object] | None = None,
    ) -> Match:
        match_date = parse_match_date(date_value)
        return Match(
            source=source,
            row_number=row_number,
            competition=normalize_competition_name(competition),
            match_date=match_date,
            home_team=str(home_team or "").strip(),
            away_team=str(away_team or "").strip(),
            home_key=normalize_team_name(home_team),
            away_key=normalize_team_name(away_team),
            home_goals=_integer(home_goals),
            away_goals=_integer(away_goals),
            season=_as_season(season, match_date),
            round=str(round_value).strip() if round_value not in (None, "") else None,
            stage=str(stage).strip() if stage not in (None, "") else None,
            venue=str(venue).strip() if venue not in (None, "") else None,
            details={
                key: str(value)
                for key, value in (details or {}).items()
                if value not in (None, "")
            }
            or None,
        )

    def list_competitions(self) -> list[dict[str, Any]]:
        self.ensure_loaded()
        grouped: dict[str, list[Match]] = defaultdict(list)
        for match in self._matches:
            grouped[match.competition].append(match)
        return [
            {
                "competition": competition,
                "matches": len(matches),
                "seasons": sorted({m.season for m in matches if m.season is not None}),
                "sources": sorted({m.source for m in matches}),
            }
            for competition, matches in sorted(grouped.items())
        ]

    def _filter_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        home_team: str | None = None,
        away_team: str | None = None,
        competition: str | None = None,
        season: int | str | None = None,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        round: str | int | None = None,
        stage: str | None = None,
        source: str | None = None,
        analytical: bool = False,
    ) -> list[Match]:
        self.ensure_loaded()
        parsed_season = _integer(season)
        parsed_from = parse_match_date(date_from)
        parsed_to = parse_match_date(date_to)
        if date_from is not None and parsed_from is None:
            raise ValueError(f"Invalid date_from value: {date_from!r}")
        if date_to is not None and parsed_to is None:
            raise ValueError(f"Invalid date_to value: {date_to!r}")
        if parsed_from and parsed_to and parsed_from > parsed_to:
            raise ValueError("date_from must be on or before date_to")

        source_key = normalize_text(source)
        results: list[Match] = []
        for match in self._matches:
            if team and not (_team_matches(team, match.home_key) or _team_matches(team, match.away_key)):
                continue
            if opponent and not (
                _team_matches(opponent, match.home_key) or _team_matches(opponent, match.away_key)
            ):
                continue
            if home_team and not _team_matches(home_team, match.home_key):
                continue
            if away_team and not _team_matches(away_team, match.away_key):
                continue
            if not _competition_matches(competition, match.competition):
                continue
            if parsed_season is not None and match.season != parsed_season:
                continue
            if parsed_from and (match.match_date is None or match.match_date < parsed_from):
                continue
            if parsed_to and (match.match_date is None or match.match_date > parsed_to):
                continue
            if not _round_or_stage_matches(round, match.round):
                continue
            if not _round_or_stage_matches(stage, match.stage):
                continue
            if source_key and source_key not in normalize_text(match.source):
                continue
            results.append(match)

        if analytical and not source_key:
            results = self._select_authoritative_sources(results)
        return results

    @staticmethod
    def _select_authoritative_sources(matches: Sequence[Match]) -> list[Match]:
        """Select one source per competition/season for meaningful aggregates."""

        source_priority = {
            DATA_FILENAMES["brasileirao"]: 0,
            DATA_FILENAMES["brazilian_cup"]: 0,
            DATA_FILENAMES["libertadores"]: 0,
            DATA_FILENAMES["historical"]: 1,
            DATA_FILENAMES["extended"]: 2,
        }
        grouped: dict[tuple[str, int | None], list[Match]] = defaultdict(list)
        for match in matches:
            grouped[(match.competition, match.season)].append(match)

        selected: list[Match] = []
        for group_matches in grouped.values():
            by_source: dict[str, list[Match]] = defaultdict(list)
            for match in group_matches:
                by_source[match.source].append(match)

            # Prefer the specialised CSV whenever it is complete.  Several late
            # rows in Brasileirão_Matches have blank scores, while the extended
            # source supplies completed equivalents; selecting by priority alone
            # would silently undercount those seasons.
            source_quality = {
                name: sum(match.is_completed for match in source_matches)
                / len(source_matches)
                for name, source_matches in by_source.items()
            }
            complete_sources = [
                name for name, quality in source_quality.items() if quality >= 0.99
            ]
            candidates = complete_sources or list(by_source)
            winning_source = min(
                candidates,
                key=lambda name: (
                    source_priority.get(name, 99),
                    -sum(match.is_completed for match in by_source[name]),
                    name,
                ),
            )
            selected.extend(match for match in group_matches if match.source == winning_source)
        return selected

    @staticmethod
    def _sort_matches(matches: Iterable[Match], *, descending: bool = True) -> list[Match]:
        return sorted(
            matches,
            key=lambda match: (match.match_date or date.min, match.source, match.row_number),
            reverse=descending,
        )

    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> tuple[int, int]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 1_000:
            raise ValueError("limit must be an integer between 1 and 1000")
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError("offset must be a non-negative integer")
        return limit, offset

    def search_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        home_team: str | None = None,
        away_team: str | None = None,
        competition: str | None = None,
        season: int | str | None = None,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        round: str | int | None = None,
        stage: str | None = None,
        source: str | None = None,
        limit: int = 50,
        offset: int = 0,
        descending: bool = True,
    ) -> dict[str, Any]:
        """Return raw source matches satisfying the supplied criteria."""

        limit, offset = self._validate_pagination(limit, offset)
        matches = self._sort_matches(
            self._filter_matches(
                team=team,
                opponent=opponent,
                home_team=home_team,
                away_team=away_team,
                competition=competition,
                season=season,
                date_from=date_from,
                date_to=date_to,
                round=round,
                stage=stage,
                source=source,
            ),
            descending=descending,
        )
        page = matches[offset : offset + limit]
        return {
            "count": len(page),
            "total": len(matches),
            "offset": offset,
            "limit": limit,
            "matches": [match.to_dict() for match in page],
        }

    def latest_match(
        self,
        team: str,
        *,
        opponent: str | None = None,
        competition: str | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Return the latest dated match for a team, optionally against an opponent."""

        matches = self._sort_matches(
            (
                match
                for match in self._filter_matches(
                    team=team,
                    opponent=opponent,
                    competition=competition,
                    source=source,
                    analytical=True,
                )
                if match.is_completed
            )
        )
        return {
            "team": display_team_name(team),
            "opponent": display_team_name(opponent) if opponent else None,
            "match": matches[0].to_dict() if matches else None,
        }

    @staticmethod
    def _team_record(matches: Iterable[Match], team_key: str, venue: str = "all") -> dict[str, Any]:
        record: dict[str, Any] = {
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "points": 0,
        }
        for match in matches:
            if not match.is_completed:
                continue
            is_home = match.home_key == team_key
            is_away = match.away_key == team_key
            if not is_home and not is_away:
                continue
            if venue == "home" and not is_home:
                continue
            if venue == "away" and not is_away:
                continue

            goals_for = match.home_goals if is_home else match.away_goals
            goals_against = match.away_goals if is_home else match.home_goals
            record["matches"] += 1
            record["goals_for"] += goals_for
            record["goals_against"] += goals_against
            if goals_for > goals_against:
                record["wins"] += 1
                record["points"] += 3
            elif goals_for == goals_against:
                record["draws"] += 1
                record["points"] += 1
            else:
                record["losses"] += 1

        record["goal_difference"] = record["goals_for"] - record["goals_against"]
        record["win_rate"] = _percent(record["wins"], record["matches"])
        record["points_per_match"] = _safe_ratio(record["points"], record["matches"])
        return record

    def team_statistics(
        self,
        team: str,
        *,
        season: int | str | None = None,
        competition: str | None = None,
        venue: str = "all",
        source: str | None = None,
    ) -> dict[str, Any]:
        """Calculate wins, losses, goals, and points for one team."""

        venue_key = normalize_text(venue)
        if venue_key not in {"all", "home", "away"}:
            raise ValueError("venue must be one of: all, home, away")
        team_key = normalize_team_name(team)
        matches = self._filter_matches(
            team=team,
            competition=competition,
            season=season,
            source=source,
            analytical=True,
        )
        record = self._team_record(matches, team_key, venue_key)
        display = self._display_for_key(matches, team_key, fallback=team)
        record.update(
            {
                "team": display,
                "season": _integer(season),
                "competition": normalize_competition_name(competition) if competition else None,
                "venue": venue_key,
                "source": source,
            }
        )
        return record

    @staticmethod
    def _display_for_key(matches: Iterable[Match], team_key: str, *, fallback: str) -> str:
        if team_key in _TEAM_DISPLAY_NAMES:
            return _TEAM_DISPLAY_NAMES[team_key]
        for match in matches:
            if match.home_key == team_key:
                return display_team_name(match.home_team)
            if match.away_key == team_key:
                return display_team_name(match.away_team)
        return display_team_name(fallback)

    def compare_teams(
        self,
        team_a: str,
        team_b: str,
        *,
        competition: str | None = None,
        season: int | str | None = None,
        source: str | None = None,
        recent_limit: int = 10,
    ) -> dict[str, Any]:
        """Return a head-to-head record and recent fixtures for two teams."""

        recent_limit, _ = self._validate_pagination(recent_limit, 0)
        a_key, b_key = normalize_team_name(team_a), normalize_team_name(team_b)
        matches = [
            match
            for match in self._filter_matches(
                competition=competition,
                season=season,
                source=source,
                analytical=True,
            )
            if {match.home_key, match.away_key} == {a_key, b_key}
        ]
        a_record = {"wins": 0, "goals": 0}
        b_record = {"wins": 0, "goals": 0}
        draws = 0
        completed = 0
        for match in matches:
            if not match.is_completed:
                continue
            completed += 1
            a_is_home = match.home_key == a_key
            a_goals = match.home_goals if a_is_home else match.away_goals
            b_goals = match.away_goals if a_is_home else match.home_goals
            a_record["goals"] += a_goals
            b_record["goals"] += b_goals
            if a_goals > b_goals:
                a_record["wins"] += 1
            elif b_goals > a_goals:
                b_record["wins"] += 1
            else:
                draws += 1
        sorted_matches = self._sort_matches(matches)
        return {
            "team_a": self._display_for_key(matches, a_key, fallback=team_a),
            "team_b": self._display_for_key(matches, b_key, fallback=team_b),
            "matches": completed,
            "draws": draws,
            "team_a_record": a_record,
            "team_b_record": b_record,
            "recent_matches": [match.to_dict() for match in sorted_matches[:recent_limit]],
            "competition": normalize_competition_name(competition) if competition else None,
            "season": _integer(season),
        }

    def standings(
        self,
        season: int | str,
        *,
        competition: str = BRASILEIRAO,
        source: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Calculate a points table from completed match results."""

        parsed_season = _integer(season)
        if parsed_season is None:
            raise ValueError("season must be a four-digit year")
        if limit is not None:
            self._validate_pagination(limit, 0)
        canonical_competition = normalize_competition_name(competition)
        matches = self._filter_matches(
            competition=canonical_competition,
            season=parsed_season,
            source=source,
            analytical=True,
        )
        table: dict[str, dict[str, Any]] = {}
        for match in matches:
            if not match.is_completed:
                continue
            for key, raw_name in ((match.home_key, match.home_team), (match.away_key, match.away_team)):
                if key not in table:
                    table[key] = {
                        "team": display_team_name(raw_name),
                        "matches": 0,
                        "wins": 0,
                        "draws": 0,
                        "losses": 0,
                        "goals_for": 0,
                        "goals_against": 0,
                        "points": 0,
                    }
            home, away = table[match.home_key], table[match.away_key]
            home["matches"] += 1
            away["matches"] += 1
            home["goals_for"] += match.home_goals
            home["goals_against"] += match.away_goals
            away["goals_for"] += match.away_goals
            away["goals_against"] += match.home_goals
            if match.home_goals > match.away_goals:
                home["wins"] += 1
                home["points"] += 3
                away["losses"] += 1
            elif match.away_goals > match.home_goals:
                away["wins"] += 1
                away["points"] += 3
                home["losses"] += 1
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        entries = list(table.values())
        for entry in entries:
            entry["goal_difference"] = entry["goals_for"] - entry["goals_against"]
            entry["win_rate"] = _percent(entry["wins"], entry["matches"])
        entries.sort(
            key=lambda row: (
                -row["points"],
                -row["goal_difference"],
                -row["goals_for"],
                -row["wins"],
                normalize_text(row["team"]),
            )
        )
        for rank, entry in enumerate(entries, start=1):
            entry["position"] = rank
        if limit is not None:
            entries = entries[:limit]
        return {
            "competition": canonical_competition,
            "season": parsed_season,
            "matches_used": sum(1 for match in matches if match.is_completed),
            "champion": entries[0]["team"] if entries else None,
            "standings": entries,
            "source": source,
        }

    def competition_statistics(
        self,
        *,
        competition: str | None = None,
        season: int | str | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Aggregate goals and outcome rates for a competition or season."""

        matches = self._filter_matches(
            competition=competition,
            season=season,
            source=source,
            analytical=True,
        )
        completed = [match for match in matches if match.is_completed]
        home_wins = sum(match.home_goals > match.away_goals for match in completed)
        away_wins = sum(match.away_goals > match.home_goals for match in completed)
        draws = len(completed) - home_wins - away_wins
        total_goals = sum(match.home_goals + match.away_goals for match in completed)
        return {
            "competition": normalize_competition_name(competition) if competition else None,
            "season": _integer(season),
            "matches": len(completed),
            "total_goals": total_goals,
            "goals_per_match": _safe_ratio(total_goals, len(completed)),
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": _percent(home_wins, len(completed)),
            "away_win_rate": _percent(away_wins, len(completed)),
            "draw_rate": _percent(draws, len(completed)),
            "sources_used": sorted({match.source for match in matches}),
        }

    def best_team_records(
        self,
        *,
        venue: str = "away",
        competition: str | None = None,
        season: int | str | None = None,
        source: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Rank teams by points, then goal difference, for a venue context."""

        venue_key = normalize_text(venue)
        if venue_key not in {"all", "home", "away"}:
            raise ValueError("venue must be one of: all, home, away")
        limit, _ = self._validate_pagination(limit, 0)
        matches = self._filter_matches(
            competition=competition,
            season=season,
            source=source,
            analytical=True,
        )
        keys = {match.home_key for match in matches} | {match.away_key for match in matches}
        rankings = []
        for key in keys:
            record = self._team_record(matches, key, venue_key)
            if not record["matches"]:
                continue
            record["team"] = self._display_for_key(matches, key, fallback=key)
            rankings.append(record)
        rankings.sort(
            key=lambda row: (
                -row["points"],
                -row["goal_difference"],
                -row["goals_for"],
                -row["wins"],
                normalize_text(row["team"]),
            )
        )
        for rank, row in enumerate(rankings, start=1):
            row["position"] = rank
        return {
            "venue": venue_key,
            "competition": normalize_competition_name(competition) if competition else None,
            "season": _integer(season),
            "rankings": rankings[:limit],
        }

    def biggest_wins(
        self,
        *,
        competition: str | None = None,
        season: int | str | None = None,
        source: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """List completed matches with the largest winning margin."""

        limit, _ = self._validate_pagination(limit, 0)
        matches = [
            match
            for match in self._filter_matches(
                competition=competition,
                season=season,
                source=source,
                analytical=True,
            )
            if match.is_completed
        ]
        matches.sort(
            key=lambda match: (
                -(match.goal_difference or 0),
                -(match.home_goals + match.away_goals),
                -((match.match_date or date.min).toordinal()),
                match.identifier,
            ),
        )
        victories = []
        for match in matches[:limit]:
            item = match.to_dict()
            item["winning_margin"] = match.goal_difference
            item["winner"] = display_team_name(
                match.home_team if match.home_goals > match.away_goals else match.away_team
            )
            victories.append(item)
        return {
            "competition": normalize_competition_name(competition) if competition else None,
            "season": _integer(season),
            "victories": victories,
        }

    def team_competitions(self, team: str, *, source: str | None = None) -> dict[str, Any]:
        """Show competitions and seasons in which a team appears in the data."""

        team_key = normalize_team_name(team)
        matches = self._filter_matches(team=team, source=source)
        grouped: dict[str, list[Match]] = defaultdict(list)
        for match in matches:
            grouped[match.competition].append(match)
        competitions = [
            {
                "competition": name,
                "matches": len(group),
                "seasons": sorted({match.season for match in group if match.season is not None}),
                "sources": sorted({match.source for match in group}),
            }
            for name, group in sorted(grouped.items())
        ]
        return {
            "team": self._display_for_key(matches, team_key, fallback=team),
            "competitions": competitions,
        }

    def derbies(
        self,
        *,
        season: int | str | None = None,
        competition: str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Find matches between the traditional-rival pairs known to the server."""

        limit, _ = self._validate_pagination(limit, 0)
        matches = self._filter_matches(
            season=season,
            competition=competition,
            source=source,
        )
        found = []
        for match in matches:
            derby_name = _DERBIES.get(frozenset((match.home_key, match.away_key)))
            if derby_name:
                item = match.to_dict()
                item["derby"] = derby_name
                found.append(item)
        found.sort(key=lambda item: (item["date"] or "", item["id"]), reverse=True)
        return {
            "season": _integer(season),
            "competition": normalize_competition_name(competition) if competition else None,
            "count": min(len(found), limit),
            "total": len(found),
            "matches": found[:limit],
        }

    def compare_seasons(
        self,
        first_season: int | str,
        second_season: int | str,
        *,
        competition: str = BRASILEIRAO,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Compare core competition statistics and calculated champions by season."""

        first = _integer(first_season)
        second = _integer(second_season)
        if first is None or second is None:
            raise ValueError("both seasons must be four-digit years")
        return {
            "competition": normalize_competition_name(competition),
            "seasons": {
                str(first): {
                    "statistics": self.competition_statistics(
                        competition=competition, season=first, source=source
                    ),
                    "champion": self.standings(
                        first, competition=competition, source=source, limit=1
                    )["champion"],
                },
                str(second): {
                    "statistics": self.competition_statistics(
                        competition=competition, season=second, source=source
                    ),
                    "champion": self.standings(
                        second, competition=competition, source=source, limit=1
                    )["champion"],
                },
            },
        }

    def competition_bracket(
        self,
        season: int | str,
        *,
        competition: str = LIBERTADORES,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Group a cup competition's fixtures by its supplied stage or round."""

        parsed_season = _integer(season)
        if parsed_season is None:
            raise ValueError("season must be a four-digit year")
        canonical_competition = normalize_competition_name(competition)
        matches = self._sort_matches(
            self._filter_matches(
                competition=canonical_competition,
                season=parsed_season,
                source=source,
                analytical=True,
            ),
            descending=False,
        )
        grouped: dict[str, list[Match]] = defaultdict(list)
        for match in matches:
            label = match.stage or (f"Round {match.round}" if match.round else "Fixtures")
            grouped[label].append(match)
        stages = [
            {"stage": stage, "matches": [match.to_dict() for match in stage_matches]}
            for stage, stage_matches in grouped.items()
        ]
        return {
            "competition": canonical_competition,
            "season": parsed_season,
            "stages": stages,
            "matches": len(matches),
            "sources_used": sorted({match.source for match in matches}),
        }

    def finals(
        self,
        *,
        competition: str,
        season: int | str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Find explicit final-stage matches and reliable Copa do Brasil finals.

        Libertadores rows label the stage directly.  The dedicated Copa do Brasil
        file uses numeric rounds, where round 8 is the final in complete seasons;
        incomplete seasons are intentionally not guessed as finals.
        """

        limit, _ = self._validate_pagination(limit, 0)
        canonical_competition = normalize_competition_name(competition)
        matches = self._filter_matches(
            competition=canonical_competition,
            season=season,
            source=source,
            analytical=True,
        )
        final_matches = [
            match
            for match in matches
            if match.stage and normalize_text(match.stage) in {"final", "grand final"}
        ]
        inferred = False
        if canonical_competition == COPA_DO_BRASIL:
            grouped: dict[tuple[str, int | None], list[Match]] = defaultdict(list)
            for match in matches:
                grouped[(match.source, match.season)].append(match)
            for group in grouped.values():
                numeric_rounds = [
                    _integer(match.round) for match in group if _integer(match.round) is not None
                ]
                if numeric_rounds and max(numeric_rounds) >= 8:
                    final_round = max(numeric_rounds)
                    final_matches.extend(
                        match for match in group if _integer(match.round) == final_round
                    )
                    inferred = True
        final_matches = self._sort_matches(final_matches)
        return {
            "competition": canonical_competition,
            "season": _integer(season),
            "inferred_from_round": inferred,
            "count": min(len(final_matches), limit),
            "total": len(final_matches),
            "matches": [match.to_dict() for match in final_matches[:limit]],
        }

    def relegated_teams(
        self,
        season: int | str,
        *,
        competition: str = BRASILEIRAO,
        count: int = 4,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Return the lowest-ranked teams in calculated standings."""

        count, _ = self._validate_pagination(count, 0)
        table = self.standings(season, competition=competition, source=source)
        relegated = list(reversed(table["standings"][-count:]))
        return {
            "competition": table["competition"],
            "season": table["season"],
            "relegated_teams": relegated,
            "standings_size": len(table["standings"]),
        }

    def top_scoring_teams(
        self,
        season: int | str,
        *,
        competition: str = BRASILEIRAO,
        source: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Rank teams by goals scored from calculated competition standings."""

        limit, _ = self._validate_pagination(limit, 0)
        table = self.standings(season, competition=competition, source=source)
        teams = sorted(
            table["standings"],
            key=lambda row: (
                -row["goals_for"],
                -row["goal_difference"],
                -row["points"],
                normalize_text(row["team"]),
            ),
        )
        for rank, team in enumerate(teams, start=1):
            team["goals_rank"] = rank
        return {
            "competition": table["competition"],
            "season": table["season"],
            "teams": teams[:limit],
            "source": source,
        }

    def team_profile(
        self,
        team: str,
        *,
        season: int | str | None = None,
        competition: str | None = None,
        player_limit: int = 25,
    ) -> dict[str, Any]:
        """Combine a team's match summary with FIFA players at a matching club."""

        player_limit, _ = self._validate_pagination(player_limit, 0)
        statistics = self.team_statistics(
            team, season=season, competition=competition, venue="all"
        )
        players = self.search_players(
            club=team, limit=player_limit, include_attributes=False
        )
        return {
            "team": statistics["team"],
            "match_statistics": statistics,
            "competitions": self.team_competitions(team)["competitions"],
            "players": players,
        }

    def search_players(
        self,
        *,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | str | None = None,
        max_overall: int | str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_attributes: bool = True,
    ) -> dict[str, Any]:
        """Search FIFA players by identity, club, nationality, role, and rating."""

        self.ensure_loaded()
        limit, offset = self._validate_pagination(limit, offset)
        name_key = normalize_text(name)
        nationality_key = _normalize_nationality(nationality)
        club_key = normalize_team_name(club)
        position_key = normalize_text(position)
        allowed_positions = _POSITION_GROUPS.get(position_key)
        minimum = _integer(min_overall)
        maximum = _integer(max_overall)
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("min_overall must be less than or equal to max_overall")

        results: list[Player] = []
        for player in self._players:
            if name_key and name_key not in player.name_key:
                continue
            if nationality_key and nationality_key not in player.nationality_key:
                continue
            if club_key and club_key not in player.club_key:
                continue
            if position_key:
                if allowed_positions is not None:
                    if player.position not in allowed_positions:
                        continue
                elif normalize_text(player.position) != position_key:
                    continue
            if minimum is not None and (player.overall is None or player.overall < minimum):
                continue
            if maximum is not None and (player.overall is None or player.overall > maximum):
                continue
            results.append(player)
        results.sort(
            key=lambda player: (
                -(player.overall if player.overall is not None else -1),
                -(player.potential if player.potential is not None else -1),
                player.name_key,
            )
        )
        page = results[offset : offset + limit]
        return {
            "count": len(page),
            "total": len(results),
            "offset": offset,
            "limit": limit,
            "players": [
                player.to_dict(include_attributes=include_attributes) for player in page
            ],
        }

    def top_players(
        self,
        *,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Convenience wrapper for the highest-rated player search."""

        return self.search_players(
            nationality=nationality,
            club=club,
            position=position,
            limit=limit,
        )


__all__ = [
    "BRASILEIRAO",
    "COPA_DO_BRASIL",
    "LIBERTADORES",
    "DATA_FILENAMES",
    "DataLoadError",
    "Match",
    "Player",
    "SoccerRepository",
    "display_team_name",
    "normalize_competition_name",
    "normalize_team_name",
    "normalize_text",
    "parse_match_date",
]
