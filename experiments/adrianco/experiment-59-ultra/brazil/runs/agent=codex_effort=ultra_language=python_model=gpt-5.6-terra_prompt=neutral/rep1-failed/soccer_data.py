"""Query and normalization layer for the bundled Brazilian soccer datasets.

The module deliberately has no third-party dependencies.  Keeping the data layer
separate from the MCP transport makes it useful both from MCP clients and ordinary
Python programs, and makes the results straightforward to test.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class SoccerDataError(ValueError):
    """Raised when a query cannot be interpreted safely."""


_MISSING_VALUES = {"", "-", "na", "n/a", "nan", "none", "null"}
_BRAZILIAN_STATE_CODES = {
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
_COUNTRY_CODES = {
    "arg",
    "bol",
    "chi",
    "col",
    "ecu",
    "equ",
    "par",
    "per",
    "uru",
    "ven",
}
_LOCATION_CODES = _BRAZILIAN_STATE_CODES | _COUNTRY_CODES

# These aliases unify actual spelling variants in the six source files.  Explicit
# state suffixes remain part of the key, which prevents Flamengo-RJ from being
# silently merged with Flamengo-PI (and likewise for Botafogo, América, etc.).
_BASE_ALIASES = {
    "clube de regatas do flamengo": "flamengo",
    "corinthians paulista": "corinthians",
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "sao paulo fc": "sao paulo",
    "sao paulo futebol clube": "sao paulo",
    "santos fc": "santos",
    "gremio foot ball porto alegrense": "gremio",
    "gremio porto alegrense": "gremio",
    "fluminense football club": "fluminense",
    "cruzeiro esporte clube": "cruzeiro",
    "atletico paranaense": "athletico",
    "athletico paranaense": "athletico",
}
_DEFAULT_STATE_BY_BASE = {
    "atletico mineiro": "mg",
    "athletico": "pr",
    "botafogo": "rj",
    "corinthians": "sp",
    "cruzeiro": "mg",
    "flamengo": "rj",
    "fluminense": "rj",
    "gremio": "rs",
    "internacional": "rs",
    "palmeiras": "sp",
    "santos": "sp",
    "sao paulo": "sp",
    "sport": "pe",
    "vasco": "rj",
    "vasco da gama": "rj",
}
_KEY_ALIASES = {
    "atletico-mg": "atletico-mineiro-mg",
    "atletico-mineiro": "atletico-mineiro-mg",
    "atletico-paranaense": "athletico-pr",
    "atletico-paranaense-pr": "athletico-pr",
    "atletico-pr": "athletico-pr",
    "vasco-da-gama-rj": "vasco-rj",
}
_COMPETITION_ALIASES = {
    "brasileirao": "Brasileirão",
    "campeonato brasileiro": "Brasileirão",
    "serie a": "Brasileirão",
    "serie a brasileira": "Brasileirão",
    "copa do brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
    "copa libertadores da america": "Copa Libertadores",
    "serie b": "Série B",
    "serie c": "Série C",
}
_FORWARD_POSITIONS = {"st", "cf", "lw", "rw", "lf", "rf"}


def fold_text(value: object | None) -> str:
    """Return an accent-insensitive, tokenized representation of *value*."""

    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    ascii_text = ascii_text.casefold().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", ascii_text)).strip()


def normalize_team_name(value: object | None, state: object | None = None) -> str:
    """Create a stable team key without losing meaningful state disambiguation.

    A supplied state column is used only when the source name did not already state a
    location.  That preserves distinct clubs such as Botafogo-RJ and Botafogo-PB.
    """

    words = fold_text(value).split()
    if not words:
        return ""

    detected_state: str | None = None
    if words[-1] in _LOCATION_CODES:
        detected_state = words.pop()
    supplied_state = fold_text(state)
    if not detected_state and supplied_state in _LOCATION_CODES:
        detected_state = supplied_state

    base = " ".join(words)
    base = _BASE_ALIASES.get(base, base)
    if not detected_state:
        detected_state = _DEFAULT_STATE_BY_BASE.get(base)
    key = "-".join(part for part in (base.replace(" ", "-"), detected_state) if part)
    return _KEY_ALIASES.get(key, key)


def team_base_key(team_key: str) -> str:
    """Return a team key without a terminal geographic code."""

    base, separator, suffix = team_key.rpartition("-")
    if separator and suffix in _LOCATION_CODES:
        return base
    return team_key


def canonical_competition(value: object | None) -> str:
    """Normalize the competition labels used by the different CSV files."""

    raw = str(value or "").strip()
    normalized = fold_text(raw)
    return _COMPETITION_ALIASES.get(normalized, raw or "Unknown")


def _is_missing(value: object | None) -> bool:
    return value is None or fold_text(value) in _MISSING_VALUES


def parse_optional_int(value: object | None) -> int | None:
    if _is_missing(value):
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else None


def parse_match_datetime(value: object | None, kickoff: object | None = None) -> datetime | None:
    """Parse the ISO, ISO-datetime, and Brazilian date formats in the sources."""

    if _is_missing(value):
        return None
    text = str(value).strip()
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        for date_format in ("%d/%m/%Y", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(text, date_format)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if kickoff and parsed.time() == time.min and not _is_missing(kickoff):
        try:
            parsed_time = time.fromisoformat(str(kickoff).strip())
            parsed = datetime.combine(parsed.date(), parsed_time)
        except ValueError:
            pass
    return parsed.replace(tzinfo=None)


def parse_query_date(value: object | date | datetime | None, *, field_name: str) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = parse_match_datetime(value)
    if not parsed:
        raise SoccerDataError(f"{field_name} must be an ISO date or a Brazilian DD/MM/YYYY date")
    return parsed.date()


@dataclass(frozen=True)
class Match:
    identifier: str
    source: str
    competition: str
    date_time: datetime | None
    season: int | None
    home_team: str
    away_team: str
    home_key: str
    away_key: str
    home_goals: int | None
    away_goals: int | None
    round: str | None = None
    stage: str | None = None
    statistics: Mapping[str, int | float | str | None] = field(default_factory=dict)

    @property
    def completed(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def match_date(self) -> date | None:
        return self.date_time.date() if self.date_time else None

    def to_dict(self) -> dict[str, Any]:
        kickoff = None
        if self.date_time and self.date_time.time() != time.min:
            kickoff = self.date_time.strftime("%H:%M")
        return {
            "id": self.identifier,
            "date": self.match_date.isoformat() if self.match_date else None,
            "kickoff": kickoff,
            "season": self.season,
            "competition": self.competition,
            "round": self.round,
            "stage": self.stage,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "status": "completed" if self.completed else "incomplete",
            "source": self.source,
            "statistics": dict(self.statistics),
        }


@dataclass(frozen=True)
class Player:
    identifier: str | None
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    attributes: Mapping[str, int | float | str | None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.identifier,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "attributes": dict(self.attributes),
        }


_SOURCE_NAMES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "brazilian_cup": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "extended_statistics": "BR-Football-Dataset.csv",
    "historical_brasileirao": "novo_campeonato_brasileiro.csv",
    "fifa_players": "fifa_data.csv",
}
_SOURCE_PRIORITY = {
    "brasileirao": 1,
    "brazilian_cup": 1,
    "libertadores": 1,
    "historical_brasileirao": 2,
    "extended_statistics": 3,
}


class SoccerRepository:
    """Loads the six bundled files once and exposes deterministic query operations."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data" / "kaggle"
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self._source_rows: Counter[str] = Counter()
        self._display_names: dict[str, Counter[str]] = defaultdict(Counter)
        self._load_all()
        self._canonical_matches = self._deduplicated_matches(self.matches)
        self._primary_matches = self._select_primary_matches(self.matches)
        self._team_aliases = self._build_team_aliases()

    @classmethod
    def from_default_data(cls) -> "SoccerRepository":
        return cls(Path(__file__).parent / "data" / "kaggle")

    def _csv_rows(self, source: str) -> Iterable[dict[str, str]]:
        path = self.data_dir / _SOURCE_NAMES[source]
        if not path.exists():
            raise FileNotFoundError(f"Required dataset is missing: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)

    def _load_all(self) -> None:
        self._load_brasileirao()
        self._load_brazilian_cup()
        self._load_libertadores()
        self._load_extended_statistics()
        self._load_historical_brasileirao()
        self._load_players()

    def _add_match(
        self,
        *,
        source: str,
        row_number: int,
        competition: str,
        date_time: datetime | None,
        season: int | None,
        home_team: object | None,
        away_team: object | None,
        home_goals: object | None,
        away_goals: object | None,
        home_state: object | None = None,
        away_state: object | None = None,
        round_value: object | None = None,
        stage: object | None = None,
        statistics: Mapping[str, int | float | str | None] | None = None,
    ) -> None:
        home_display = str(home_team or "").strip()
        away_display = str(away_team or "").strip()
        if not home_display or not away_display:
            return
        home_key = normalize_team_name(home_display, home_state)
        away_key = normalize_team_name(away_display, away_state)
        if not home_key or not away_key:
            return
        self._source_rows[source] += 1
        self._display_names[home_key][home_display] += 1
        self._display_names[away_key][away_display] += 1
        self.matches.append(
            Match(
                identifier=f"{source}:{row_number}",
                source=source,
                competition=canonical_competition(competition),
                date_time=date_time,
                season=season,
                home_team=home_display,
                away_team=away_display,
                home_key=home_key,
                away_key=away_key,
                home_goals=parse_optional_int(home_goals),
                away_goals=parse_optional_int(away_goals),
                round=str(round_value).strip() if not _is_missing(round_value) else None,
                stage=str(stage).strip() if not _is_missing(stage) else None,
                statistics=statistics or {},
            )
        )

    def _load_brasileirao(self) -> None:
        source = "brasileirao"
        for row_number, row in enumerate(self._csv_rows(source), start=2):
            self._add_match(
                source=source,
                row_number=row_number,
                competition="Brasileirão",
                date_time=parse_match_datetime(row.get("datetime")),
                season=parse_optional_int(row.get("season")),
                home_team=row.get("home_team"),
                away_team=row.get("away_team"),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                home_state=row.get("home_team_state"),
                away_state=row.get("away_team_state"),
                round_value=row.get("round"),
            )

    def _load_brazilian_cup(self) -> None:
        source = "brazilian_cup"
        for row_number, row in enumerate(self._csv_rows(source), start=2):
            self._add_match(
                source=source,
                row_number=row_number,
                competition="Copa do Brasil",
                date_time=parse_match_datetime(row.get("datetime")),
                season=parse_optional_int(row.get("season")),
                home_team=row.get("home_team"),
                away_team=row.get("away_team"),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                round_value=row.get("round"),
            )

    def _load_libertadores(self) -> None:
        source = "libertadores"
        for row_number, row in enumerate(self._csv_rows(source), start=2):
            self._add_match(
                source=source,
                row_number=row_number,
                competition="Copa Libertadores",
                date_time=parse_match_datetime(row.get("datetime")),
                season=parse_optional_int(row.get("season")),
                home_team=row.get("home_team"),
                away_team=row.get("away_team"),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                stage=row.get("stage"),
            )

    def _load_extended_statistics(self) -> None:
        source = "extended_statistics"
        statistic_columns = (
            "home_corner",
            "away_corner",
            "home_attack",
            "away_attack",
            "home_shots",
            "away_shots",
            "total_corners",
            "ht_result",
            "at_result",
        )
        for row_number, row in enumerate(self._csv_rows(source), start=2):
            statistics: dict[str, int | float | str | None] = {}
            for column in statistic_columns:
                value = row.get(column)
                numeric = parse_optional_int(value)
                statistics[column] = numeric if numeric is not None else (None if _is_missing(value) else value)
            self._add_match(
                source=source,
                row_number=row_number,
                competition=row.get("tournament") or "Unknown",
                date_time=parse_match_datetime(row.get("date"), row.get("time")),
                season=parse_optional_int((row.get("date") or "")[:4]),
                home_team=row.get("home"),
                away_team=row.get("away"),
                home_goals=row.get("home_goal"),
                away_goals=row.get("away_goal"),
                statistics=statistics,
            )

    def _load_historical_brasileirao(self) -> None:
        source = "historical_brasileirao"
        for row_number, row in enumerate(self._csv_rows(source), start=2):
            self._add_match(
                source=source,
                row_number=row_number,
                competition="Brasileirão",
                date_time=parse_match_datetime(row.get("Data")),
                season=parse_optional_int(row.get("Ano")),
                home_team=row.get("Equipe_mandante"),
                away_team=row.get("Equipe_visitante"),
                home_goals=row.get("Gols_mandante"),
                away_goals=row.get("Gols_visitante"),
                home_state=row.get("Mandante_UF"),
                away_state=row.get("Visitante_UF"),
                round_value=row.get("Rodada"),
                statistics={"stadium": row.get("Arena"), "note": row.get("OBS")},
            )

    def _load_players(self) -> None:
        source = "fifa_players"
        attribute_columns = (
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
        )
        for row in self._csv_rows(source):
            self._source_rows[source] += 1
            attributes = {column: parse_optional_int(row.get(column)) for column in attribute_columns}
            self.players.append(
                Player(
                    identifier=(row.get("ID") or "").strip() or None,
                    name=(row.get("Name") or "").strip(),
                    age=parse_optional_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip(),
                    overall=parse_optional_int(row.get("Overall")),
                    potential=parse_optional_int(row.get("Potential")),
                    club=(row.get("Club") or "").strip(),
                    position=(row.get("Position") or "").strip(),
                    jersey_number=parse_optional_int(row.get("Jersey Number")),
                    attributes=attributes,
                )
            )

    @staticmethod
    def _deduplication_key(match: Match) -> tuple[Any, ...]:
        return (
            match.competition,
            match.match_date,
            match.home_key,
            match.away_key,
            match.home_goals,
            match.away_goals,
        )

    def _deduplicated_matches(self, matches: Sequence[Match]) -> list[Match]:
        chosen: dict[tuple[Any, ...], Match] = {}
        for match in matches:
            key = self._deduplication_key(match)
            existing = chosen.get(key)
            if existing is None or _SOURCE_PRIORITY.get(match.source, 99) < _SOURCE_PRIORITY.get(existing.source, 99):
                chosen[key] = match
        return list(chosen.values())

    def _select_primary_matches(self, matches: Sequence[Match]) -> list[Match]:
        """Choose one authoritative source per competition and season.

        Several supplied files intentionally overlap (for example, 2019 Serie A is
        present in the dedicated Brasileirão, historical, and extended-statistics
        files).  Their dates can differ by a day, so value-based de-duplication is
        not enough for tables and aggregate figures.  Default queries therefore use
        the dedicated competition file when present, then the historical file, then
        the general extended-statistics file.  Passing ``source`` still exposes every
        original record for cross-file inspection.
        """

        by_competition_and_season: dict[tuple[str, int | None], list[Match]] = defaultdict(list)
        for match in matches:
            by_competition_and_season[(match.competition, match.season)].append(match)
        selected: list[Match] = []
        for grouped_matches in by_competition_and_season.values():
            best_priority = min(_SOURCE_PRIORITY.get(match.source, 99) for match in grouped_matches)
            primary_source_matches = [
                match for match in grouped_matches if _SOURCE_PRIORITY.get(match.source, 99) == best_priority
            ]
            selected.extend(self._deduplicated_matches(primary_source_matches))
        return selected

    def _build_team_aliases(self) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for team_key, display_counts in self._display_names.items():
            aliases[fold_text(team_key.replace("-", " "))] = team_key
            for display in display_counts:
                aliases.setdefault(fold_text(display), team_key)
        for spelling in set(_DEFAULT_STATE_BY_BASE) | set(_BASE_ALIASES):
            aliases[fold_text(spelling)] = normalize_team_name(spelling)
        aliases.update(
            {
                "atletico paranaense": "athletico-pr",
                "athletico paranaense": "athletico-pr",
                "sao paulo fc": "sao-paulo-sp",
                "sport club corinthians paulista": "corinthians-sp",
            }
        )
        return aliases

    def display_name(self, team_key: str) -> str:
        counts = self._display_names.get(team_key)
        if counts:
            return counts.most_common(1)[0][0]
        return team_key.replace("-", " ").title()

    def source_summary(self) -> dict[str, Any]:
        sources = []
        for source, filename in _SOURCE_NAMES.items():
            rows = self._source_rows[source]
            if source == "fifa_players":
                sources.append({"source": source, "file": filename, "records": rows, "kind": "players"})
                continue
            all_matches = [match for match in self.matches if match.source == source]
            sources.append(
                {
                    "source": source,
                    "file": filename,
                    "records": rows,
                    "kind": "matches",
                    "completed_matches": sum(match.completed for match in all_matches),
                    "incomplete_matches": sum(not match.completed for match in all_matches),
                }
            )
        return {
            "data_directory": str(self.data_dir),
            "sources": sources,
            "raw_match_records": len(self.matches),
            "deduplicated_match_records": len(self._canonical_matches),
            "default_query_match_records": len(self._primary_matches),
            "players": len(self.players),
        }

    @staticmethod
    def _sort_matches(matches: Iterable[Match], *, newest_first: bool = True) -> list[Match]:
        return sorted(
            matches,
            key=lambda match: (match.date_time is not None, match.date_time or datetime.min, match.identifier),
            reverse=newest_first,
        )

    def _team_matches_key(self, actual_key: str, query_key: str) -> bool:
        if actual_key == query_key:
            return True
        # A generic query without a state code is intentionally broad.  It gives a
        # caller useful results while retaining the individual stateful identities
        # in every returned record.
        return "-" not in query_key and team_base_key(actual_key) == query_key

    @staticmethod
    def _source_matches(match: Match, source: str | None) -> bool:
        return not source or fold_text(match.source) == fold_text(source) or fold_text(_SOURCE_NAMES[match.source]) == fold_text(source)

    @staticmethod
    def _round_matches(match: Match, round_or_stage: str | None) -> bool:
        if not round_or_stage:
            return True
        wanted = fold_text(round_or_stage)
        if wanted in {"final", "finals"}:
            return fold_text(match.stage) == "final" or (
                match.competition == "Copa do Brasil" and str(match.round or "") == "8"
            )
        return wanted in {fold_text(match.round), fold_text(match.stage)}

    def _filtered_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        home_team: str | None = None,
        away_team: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | date | datetime | None = None,
        date_to: str | date | datetime | None = None,
        round_or_stage: str | None = None,
        source: str | None = None,
        include_incomplete: bool = False,
        include_duplicates: bool = False,
    ) -> list[Match]:
        team_key = normalize_team_name(team) if team else None
        opponent_key = normalize_team_name(opponent) if opponent else None
        home_key = normalize_team_name(home_team) if home_team else None
        away_key = normalize_team_name(away_team) if away_team else None
        desired_competition = canonical_competition(competition) if competition else None
        start = parse_query_date(date_from, field_name="date_from")
        end = parse_query_date(date_to, field_name="date_to")
        if start and end and start > end:
            raise SoccerDataError("date_from must not be later than date_to")
        candidates = self.matches if include_duplicates or source else self._primary_matches
        result: list[Match] = []
        for match in candidates:
            if not include_incomplete and not match.completed:
                continue
            if season is not None and match.season != int(season):
                continue
            if desired_competition and match.competition != desired_competition:
                continue
            if source and not self._source_matches(match, source):
                continue
            if team_key and not (
                self._team_matches_key(match.home_key, team_key) or self._team_matches_key(match.away_key, team_key)
            ):
                continue
            if opponent_key and not (
                self._team_matches_key(match.home_key, opponent_key)
                or self._team_matches_key(match.away_key, opponent_key)
            ):
                continue
            if home_key and not self._team_matches_key(match.home_key, home_key):
                continue
            if away_key and not self._team_matches_key(match.away_key, away_key):
                continue
            if not self._round_matches(match, round_or_stage):
                continue
            if start or end:
                if not match.match_date:
                    continue
                if start and match.match_date < start:
                    continue
                if end and match.match_date > end:
                    continue
            result.append(match)
        return self._sort_matches(result)

    @staticmethod
    def _clamp_limit(limit: int, maximum: int = 500) -> int:
        try:
            parsed = int(limit)
        except (TypeError, ValueError) as exc:
            raise SoccerDataError("limit must be an integer") from exc
        if not 1 <= parsed <= maximum:
            raise SoccerDataError(f"limit must be between 1 and {maximum}")
        return parsed

    def search_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        home_team: str | None = None,
        away_team: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | date | datetime | None = None,
        date_to: str | date | datetime | None = None,
        round_or_stage: str | None = None,
        source: str | None = None,
        include_incomplete: bool = False,
        include_duplicates: bool = False,
        limit: int = 50,
    ) -> dict[str, Any]:
        limit = self._clamp_limit(limit)
        matches = self._filtered_matches(
            team=team,
            opponent=opponent,
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            round_or_stage=round_or_stage,
            source=source,
            include_incomplete=include_incomplete,
            include_duplicates=include_duplicates,
        )
        return {
            "filters": {
                "team": team,
                "opponent": opponent,
                "home_team": home_team,
                "away_team": away_team,
                "competition": canonical_competition(competition) if competition else None,
                "season": season,
                "date_from": str(date_from) if date_from else None,
                "date_to": str(date_to) if date_to else None,
                "round_or_stage": round_or_stage,
                "source": source,
                "include_incomplete": include_incomplete,
                "include_duplicates": include_duplicates,
            },
            "count": len(matches),
            "returned": min(len(matches), limit),
            "matches": [match.to_dict() for match in matches[:limit]],
        }

    @staticmethod
    def _empty_record() -> dict[str, int]:
        return {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0}

    @staticmethod
    def _record_match(record: dict[str, int], goals_for: int, goals_against: int) -> None:
        record["matches"] += 1
        record["goals_for"] += goals_for
        record["goals_against"] += goals_against
        if goals_for > goals_against:
            record["wins"] += 1
            record["points"] += 3
        elif goals_for < goals_against:
            record["losses"] += 1
        else:
            record["draws"] += 1
            record["points"] += 1

    def _aggregate_records(self, matches: Iterable[Match], *, venue: str = "all") -> dict[str, dict[str, int]]:
        if venue not in {"all", "home", "away"}:
            raise SoccerDataError("venue must be one of: all, home, away")
        records: dict[str, dict[str, int]] = defaultdict(self._empty_record)
        for match in matches:
            if not match.completed:
                continue
            assert match.home_goals is not None and match.away_goals is not None
            if venue in {"all", "home"}:
                self._record_match(records[match.home_key], match.home_goals, match.away_goals)
            if venue in {"all", "away"}:
                self._record_match(records[match.away_key], match.away_goals, match.home_goals)
        return records

    @staticmethod
    def _record_public(record: Mapping[str, int]) -> dict[str, Any]:
        matches = record["matches"]
        goals_for = record["goals_for"]
        goals_against = record["goals_against"]
        return {
            **dict(record),
            "goal_difference": goals_for - goals_against,
            "win_rate": round((record["wins"] / matches) * 100, 1) if matches else 0.0,
        }

    def team_statistics(
        self,
        team: str,
        *,
        competition: str | None = None,
        season: int | None = None,
        venue: str = "all",
        source: str | None = None,
        include_duplicates: bool = False,
    ) -> dict[str, Any]:
        if not team or not team.strip():
            raise SoccerDataError("team is required")
        matching = self._filtered_matches(
            team=team,
            competition=competition,
            season=season,
            source=source,
            include_duplicates=include_duplicates,
        )
        requested_key = normalize_team_name(team)
        record = self._empty_record()
        for match in matching:
            assert match.home_goals is not None and match.away_goals is not None
            if venue in {"all", "home"} and self._team_matches_key(match.home_key, requested_key):
                self._record_match(record, match.home_goals, match.away_goals)
            if venue in {"all", "away"} and self._team_matches_key(match.away_key, requested_key):
                self._record_match(record, match.away_goals, match.home_goals)
        if venue not in {"all", "home", "away"}:
            raise SoccerDataError("venue must be one of: all, home, away")
        return {
            "team": self.display_name(requested_key),
            "team_key": requested_key,
            "competition": canonical_competition(competition) if competition else None,
            "season": season,
            "venue": venue,
            "record": self._record_public(record),
        }

    def head_to_head(
        self,
        team_one: str,
        team_two: str,
        *,
        competition: str | None = None,
        season: int | None = None,
        source: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        if not team_one or not team_two:
            raise SoccerDataError("team_one and team_two are required")
        first_key = normalize_team_name(team_one)
        second_key = normalize_team_name(team_two)
        if first_key == second_key:
            raise SoccerDataError("head-to-head teams must be different")
        candidates = self._filtered_matches(
            competition=competition,
            season=season,
            source=source,
        )
        matches = [
            match
            for match in candidates
            if (
                self._team_matches_key(match.home_key, first_key)
                and self._team_matches_key(match.away_key, second_key)
            )
            or (
                self._team_matches_key(match.home_key, second_key)
                and self._team_matches_key(match.away_key, first_key)
            )
        ]
        first_record = self._empty_record()
        second_record = self._empty_record()
        for match in matches:
            assert match.home_goals is not None and match.away_goals is not None
            if self._team_matches_key(match.home_key, first_key):
                self._record_match(first_record, match.home_goals, match.away_goals)
                self._record_match(second_record, match.away_goals, match.home_goals)
            else:
                self._record_match(first_record, match.away_goals, match.home_goals)
                self._record_match(second_record, match.home_goals, match.away_goals)
        limit = self._clamp_limit(limit)
        return {
            "team_one": self.display_name(first_key),
            "team_two": self.display_name(second_key),
            "matches": len(matches),
            "team_one_record": self._record_public(first_record),
            "team_two_record": self._record_public(second_record),
            "recent_matches": [match.to_dict() for match in matches[:limit]],
        }

    def search_players(
        self,
        *,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        limit = self._clamp_limit(limit)
        wanted_name = fold_text(name)
        wanted_nationality = fold_text(nationality)
        wanted_club = fold_text(club)
        wanted_position = fold_text(position)
        if wanted_nationality in {"brazilian", "brasileiro", "brasileira", "brasil"}:
            wanted_nationality = "brazil"
        position_tokens = set(wanted_position.split())
        if position_tokens & {"forward", "forwards", "attacker", "attackers", "atacante", "atacantes"}:
            wanted_positions = _FORWARD_POSITIONS
        else:
            wanted_positions = {token.upper() for token in position_tokens}
        threshold = parse_optional_int(min_overall) if min_overall is not None else None
        if min_overall is not None and threshold is None:
            raise SoccerDataError("min_overall must be an integer")

        def club_matches(actual: str) -> bool:
            if not wanted_club:
                return True
            actual_tokens = set(fold_text(actual).split())
            wanted_tokens = {token for token in wanted_club.split() if token not in {"fc", "club"}}
            return wanted_tokens <= actual_tokens or wanted_club in fold_text(actual)

        result = []
        for player in self.players:
            if wanted_name and wanted_name not in fold_text(player.name):
                continue
            if wanted_nationality and wanted_nationality not in fold_text(player.nationality):
                continue
            if not club_matches(player.club):
                continue
            if wanted_positions and player.position.upper() not in wanted_positions:
                continue
            if threshold is not None and (player.overall is None or player.overall < threshold):
                continue
            result.append(player)
        result.sort(key=lambda player: (player.overall is not None, player.overall or -1, player.name), reverse=True)
        return {
            "filters": {
                "name": name,
                "nationality": nationality,
                "club": club,
                "position": position,
                "min_overall": threshold,
            },
            "count": len(result),
            "returned": min(len(result), limit),
            "players": [player.to_dict() for player in result[:limit]],
        }

    def competition_standings(
        self,
        competition: str,
        season: int,
        *,
        source: str | None = None,
    ) -> dict[str, Any]:
        if not competition:
            raise SoccerDataError("competition is required")
        if season is None:
            raise SoccerDataError("season is required")
        matches = self._filtered_matches(competition=competition, season=int(season), source=source)
        records = self._aggregate_records(matches)
        rows = []
        for team_key, record in records.items():
            rows.append({"team": self.display_name(team_key), "team_key": team_key, **self._record_public(record)})
        # Brasileirão's published ordering uses number of wins before goal
        # difference, which makes the supplied 2019 Santos/Palmeiras tie resolve
        # the same way as the example in TASK.md.
        rows.sort(
            key=lambda row: (
                -row["points"],
                -row["wins"],
                -row["goal_difference"],
                -row["goals_for"],
                fold_text(row["team"]),
            )
        )
        for position, row in enumerate(rows, start=1):
            row["position"] = position
        return {
            "competition": canonical_competition(competition),
            "season": int(season),
            "matches_used": len(matches),
            "standings": rows,
            "methodology": "Three points for a win, one for a draw; ties sort by wins, goal difference, then goals scored.",
        }

    def team_leaderboard(
        self,
        *,
        metric: str = "goals_for",
        competition: str | None = None,
        season: int | None = None,
        venue: str = "all",
        limit: int = 20,
    ) -> dict[str, Any]:
        metric_key = fold_text(metric).replace(" ", "_")
        accepted = {"goals_for", "wins", "points", "win_rate", "goals_against", "goal_difference"}
        if metric_key not in accepted:
            raise SoccerDataError(f"metric must be one of: {', '.join(sorted(accepted))}")
        matches = self._filtered_matches(competition=competition, season=season)
        records = self._aggregate_records(matches, venue=venue)
        rows = [{"team": self.display_name(key), "team_key": key, **self._record_public(record)} for key, record in records.items()]
        reverse = metric_key != "goals_against"
        rows.sort(
            key=lambda row: (row[metric_key], row["points"], row["goal_difference"], row["goals_for"], fold_text(row["team"])),
            reverse=reverse,
        )
        limit = self._clamp_limit(limit)
        return {
            "metric": metric_key,
            "competition": canonical_competition(competition) if competition else None,
            "season": season,
            "venue": venue,
            "count": len(rows),
            "leaders": rows[:limit],
        }

    def analyze_statistics(
        self,
        metric: str = "summary",
        *,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        metric_key = fold_text(metric).replace(" ", "_")
        aliases = {
            "average_goals": "average_goals",
            "goals_per_match": "average_goals",
            "home_win_rate": "home_win_rate",
            "biggest_wins": "biggest_wins",
            "best_away_record": "best_away_record",
            "top_scoring_teams": "top_scoring_teams",
            "summary": "summary",
        }
        if metric_key not in aliases:
            raise SoccerDataError(f"unsupported statistical metric: {metric}")
        metric_key = aliases[metric_key]
        matches = self._filtered_matches(competition=competition, season=season)
        common = {
            "metric": metric_key,
            "competition": canonical_competition(competition) if competition else None,
            "season": season,
            "matches_used": len(matches),
        }
        home_wins = sum(match.home_goals > match.away_goals for match in matches if match.completed)
        draws = sum(match.home_goals == match.away_goals for match in matches if match.completed)
        away_wins = len(matches) - home_wins - draws
        total_goals = sum((match.home_goals or 0) + (match.away_goals or 0) for match in matches)
        if metric_key == "average_goals":
            return {**common, "average_goals_per_match": round(total_goals / len(matches), 3) if matches else 0.0}
        if metric_key == "home_win_rate":
            return {**common, "home_win_rate": round((home_wins / len(matches)) * 100, 2) if matches else 0.0}
        if metric_key == "biggest_wins":
            biggest = sorted(
                matches,
                key=lambda match: (
                    abs((match.home_goals or 0) - (match.away_goals or 0)),
                    (match.home_goals or 0) + (match.away_goals or 0),
                    match.date_time or datetime.min,
                ),
                reverse=True,
            )
            return {**common, "matches": [match.to_dict() for match in biggest[: self._clamp_limit(limit)] ]}
        if metric_key == "best_away_record":
            leaders = self.team_leaderboard(
                metric="win_rate", competition=competition, season=season, venue="away", limit=limit
            )
            return {**common, "leaders": leaders["leaders"]}
        if metric_key == "top_scoring_teams":
            leaders = self.team_leaderboard(
                metric="goals_for", competition=competition, season=season, venue="all", limit=limit
            )
            return {**common, "leaders": leaders["leaders"]}
        return {
            **common,
            "total_goals": total_goals,
            "average_goals_per_match": round(total_goals / len(matches), 3) if matches else 0.0,
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "home_win_rate": round((home_wins / len(matches)) * 100, 2) if matches else 0.0,
        }

    def competition_matches_by_stage(
        self, competition: str, season: int, *, limit: int = 500
    ) -> dict[str, Any]:
        matches = self._filtered_matches(competition=competition, season=season)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for match in matches[: self._clamp_limit(limit)]:
            grouped[match.stage or (f"Round {match.round}" if match.round else "Unspecified")].append(match.to_dict())
        return {
            "competition": canonical_competition(competition),
            "season": season,
            "stages": dict(grouped),
            "note": "The datasets contain match stages/results, not an official bracket diagram.",
        }

    def competitions_for_team(self, team: str, *, limit: int = 200) -> dict[str, Any]:
        matches = self._filtered_matches(team=team)
        grouped: dict[str, int] = Counter(match.competition for match in matches[: self._clamp_limit(limit)])
        return {"team": team, "competitions": [{"competition": name, "matches": count} for name, count in sorted(grouped.items())]}

    def derbies(self, season: int, *, limit: int = 100) -> dict[str, Any]:
        rival_pairs = {
            frozenset(("flamengo-rj", "fluminense-rj")),
            frozenset(("palmeiras-sp", "corinthians-sp")),
            frozenset(("corinthians-sp", "santos-sp")),
            frozenset(("palmeiras-sp", "sao-paulo-sp")),
            frozenset(("gremio-rs", "internacional-rs")),
            frozenset(("atletico-mineiro-mg", "cruzeiro-mg")),
            frozenset(("flamengo-rj", "vasco-rj")),
            frozenset(("flamengo-rj", "botafogo-rj")),
        }
        matches = self._filtered_matches(season=season)
        derby_matches = [match for match in matches if frozenset((match.home_key, match.away_key)) in rival_pairs]
        return {
            "season": int(season),
            "count": len(derby_matches),
            "matches": [match.to_dict() for match in derby_matches[: self._clamp_limit(limit)]],
            "rivalry_definition": "Traditional rival-pair list documented by the server; it is not inferred from scores.",
        }

    def team_profile(
        self,
        team: str,
        *,
        competition: str | None = None,
        season: int | None = None,
        match_limit: int = 20,
        player_limit: int = 20,
    ) -> dict[str, Any]:
        """Join match/team and FIFA-player views for a club-oriented query."""

        statistics = self.team_statistics(team, competition=competition, season=season)
        matches = self.search_matches(
            team=team, competition=competition, season=season, limit=self._clamp_limit(match_limit)
        )
        players = self.search_players(club=team, limit=self._clamp_limit(player_limit))
        return {
            "team": statistics["team"],
            "match_statistics": statistics,
            "recent_matches": matches,
            "players": players,
            "source_join": "Team identity is normalized for match data; FIFA club matching is accent-insensitive and reported separately because the datasets cover different snapshots.",
        }

    def knowledge_graph(
        self,
        *,
        team: str | None = None,
        player_name: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return explicit nodes and edges for the requested soccer-data neighborhood."""

        if not any((team, player_name, competition, season)):
            raise SoccerDataError("provide at least one of: team, player_name, competition, season")
        limit = self._clamp_limit(limit)
        matches = self._filtered_matches(team=team, competition=competition, season=season)[:limit]
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, str]] = []

        def add_node(node_id: str, entity_type: str, label: str, **properties: Any) -> None:
            nodes.setdefault(node_id, {"id": node_id, "type": entity_type, "label": label, "properties": properties})

        for match in matches:
            match_id = f"match:{match.identifier}"
            competition_id = f"competition:{fold_text(match.competition).replace(' ', '-')}"
            home_id = f"team:{match.home_key}"
            away_id = f"team:{match.away_key}"
            add_node(match_id, "match", f"{match.home_team} vs {match.away_team}", date=match.match_date.isoformat() if match.match_date else None)
            add_node(competition_id, "competition", match.competition)
            add_node(home_id, "team", self.display_name(match.home_key), team_key=match.home_key)
            add_node(away_id, "team", self.display_name(match.away_key), team_key=match.away_key)
            edges.extend(
                [
                    {"source": home_id, "relationship": "home_team_in", "target": match_id},
                    {"source": away_id, "relationship": "away_team_in", "target": match_id},
                    {"source": match_id, "relationship": "part_of", "target": competition_id},
                ]
            )

        player_query = player_name or (team if team else None)
        if player_query:
            players = self.search_players(
                name=player_name if player_name else None,
                club=team if team and not player_name else None,
                limit=limit,
            )["players"]
            for player in players:
                player_id = f"player:{player['id'] or fold_text(player['name']).replace(' ', '-')}"
                club_id = f"club:{fold_text(player['club']).replace(' ', '-')}"
                add_node(player_id, "player", player["name"], position=player["position"], overall=player["overall"])
                add_node(club_id, "club", player["club"])
                edges.append({"source": player_id, "relationship": "plays_for", "target": club_id})

        return {
            "filters": {"team": team, "player_name": player_name, "competition": competition, "season": season},
            "nodes": list(nodes.values()),
            "edges": edges,
            "match_count": len(matches),
            "note": "Edges are derived only from explicit rows in the bundled CSV files; no external facts are inferred.",
        }

    def find_team_mentions(self, question: str, *, maximum: int = 3) -> list[str]:
        normalized_question = f" {fold_text(question)} "
        found: list[tuple[int, int, str]] = []
        for spelling, team_key in self._team_aliases.items():
            if len(spelling) < 4:
                continue
            match = re.search(rf"(?<![a-z0-9]){re.escape(spelling)}(?![a-z0-9])", normalized_question)
            if match:
                found.append((match.start(), -len(spelling), team_key))
        found.sort()
        unique: list[str] = []
        for _, _, team_key in found:
            if team_key not in unique:
                unique.append(team_key)
            if len(unique) >= maximum:
                break
        return unique


def format_match(match: Mapping[str, Any]) -> str:
    """Format a structured match result as concise, user-facing text."""

    score = "–" if match["home_goals"] is None or match["away_goals"] is None else f"{match['home_goals']}–{match['away_goals']}"
    context = match["competition"]
    if match.get("stage"):
        context += f" {match['stage']}"
    elif match.get("round"):
        context += f" Round {match['round']}"
    return f"{match.get('date') or 'Unknown date'}: {match['home_team']} {score} {match['away_team']} ({context})"


class NaturalLanguageQueryService:
    """Small deterministic router for common football questions.

    It intentionally does not attempt to be an LLM.  An MCP client may use an LLM to
    choose the precise tools, while this convenience tool still answers the benchmark's
    natural-language examples predictably and without external credentials.
    """

    def __init__(self, repository: SoccerRepository) -> None:
        self.repository = repository
        self._last_matches: list[dict[str, Any]] = []

    @staticmethod
    def _season_from_question(question: str) -> int | None:
        match = re.search(r"\b((?:19|20)\d{2})\b", question)
        return int(match.group(1)) if match else None

    @staticmethod
    def _competition_from_question(question: str) -> str | None:
        folded = fold_text(question)
        if "libertadores" in folded:
            return "Copa Libertadores"
        if "copa do brasil" in folded:
            return "Copa do Brasil"
        if any(label in folded for label in ("brasileirao", "serie a", "campeonato brasileiro")):
            return "Brasileirão"
        return None

    def _success(self, intent: str, answer: str, data: Mapping[str, Any]) -> dict[str, Any]:
        return {"intent": intent, "answer": answer, "data": dict(data)}

    def _matches_answer(self, result: Mapping[str, Any], *, title: str | None = None) -> str:
        matches = result["matches"]
        if not matches:
            return (title + ": " if title else "") + "No completed matches matched those criteria."
        heading = title or f"Found {result['count']} match(es)"
        lines = [heading + ":"] + [f"- {format_match(match)}" for match in matches]
        if result["count"] > result["returned"]:
            lines.append(f"- … {result['count'] - result['returned']} more match(es) are available with a higher limit.")
        return "\n".join(lines)

    def ask(self, question: str, *, limit: int = 20) -> dict[str, Any]:
        if not question or not question.strip():
            raise SoccerDataError("question is required")
        limit = self.repository._clamp_limit(limit)
        original = question.strip()
        folded = fold_text(original)
        season = self._season_from_question(folded)
        competition = self._competition_from_question(folded)
        teams = self.repository.find_team_mentions(original)

        if "what was the score" in folded or folded in {"score", "the score"}:
            if self._last_matches:
                match = self._last_matches[0]
                return self._success("follow_up_score", format_match(match), {"match": match})
            return self._success(
                "follow_up_score",
                "I need a preceding match query before I can resolve “the score”. Ask for the teams or date first.",
                {"match": None},
            )

        if "who is" in folded or "player" in folded or "players" in folded or "highest rated" in folded or "forwards" in folded:
            if "who is" in folded:
                player_name = re.sub(r"^\s*who is\s+", "", original, flags=re.IGNORECASE).rstrip("?")
                result = self.repository.search_players(name=player_name, limit=limit)
            else:
                nationality = "Brazil" if any(word in folded for word in ("brazilian", "brazil players", "brasileir")) else None
                position = "forward" if any(word in folded for word in ("forward", "forwards", "atacante")) else None
                club = self.repository.display_name(teams[0]) if teams else None
                result = self.repository.search_players(nationality=nationality, club=club, position=position, limit=limit)
            if result["players"]:
                lines = [f"Found {result['count']} player(s):"]
                lines.extend(
                    f"- {player['name']} — Overall {player['overall']}, {player['position']}, {player['club']}"
                    for player in result["players"]
                )
                answer = "\n".join(lines)
            else:
                answer = "No players matched those criteria."
            return self._success("player_search", answer, result)

        if "derb" in folded:
            if season is None:
                return self._success("derbies", "Please include a season for derby queries.", {"matches": []})
            result = self.repository.derbies(season, limit=limit)
            self._last_matches = result["matches"]
            return self._success("derbies", self._matches_answer({**result, "returned": len(result["matches"])}, title=f"Derbies in {season}"), result)

        if "competitions" in folded and teams:
            result = self.repository.competitions_for_team(self.repository.display_name(teams[0]))
            listed = ", ".join(item["competition"] for item in result["competitions"]) or "none in the loaded data"
            return self._success("team_competitions", f"{result['team']} has played in: {listed}.", result)

        if "home record" in folded and teams:
            result = self.repository.team_statistics(
                self.repository.display_name(teams[0]),
                competition=competition or "Brasileirão",
                season=season,
                venue="home",
            )
            record = result["record"]
            answer = (
                f"{result['team']} home record{f' in {season}' if season else ''}: {record['matches']} matches, "
                f"{record['wins']} wins, {record['draws']} draws, {record['losses']} losses; "
                f"{record['goals_for']} scored, {record['goals_against']} conceded; {record['win_rate']}% win rate."
            )
            return self._success("team_statistics", answer, result)

        if "best away" in folded:
            result = self.repository.analyze_statistics("best_away_record", competition=competition, season=season, limit=limit)
            leader = result["leaders"][0] if result["leaders"] else None
            answer = "No completed matches matched those criteria." if not leader else (
                f"Best away record: {leader['team']} — {leader['wins']} wins from {leader['matches']} away matches "
                f"({leader['win_rate']}% win rate)."
            )
            return self._success("best_away_record", answer, result)

        if "average goals" in folded or "goals per match" in folded:
            result = self.repository.analyze_statistics("average_goals", competition=competition, season=season)
            return self._success(
                "average_goals", f"Average goals per match: {result['average_goals_per_match']}.", result
            )

        if "biggest win" in folded or "biggest vict" in folded:
            result = self.repository.analyze_statistics("biggest_wins", competition=competition, season=season, limit=limit)
            answer = self._matches_answer(
                {"matches": result["matches"], "count": len(result["matches"]), "returned": len(result["matches"])},
                title="Biggest victories",
            )
            return self._success("biggest_wins", answer, result)

        if "scored the most" in folded or "top scoring" in folded:
            result = self.repository.team_leaderboard(metric="goals_for", competition=competition, season=season, limit=limit)
            leader = result["leaders"][0] if result["leaders"] else None
            answer = "No completed matches matched those criteria." if not leader else (
                f"Top scoring team: {leader['team']} with {leader['goals_for']} goals in {leader['matches']} matches."
            )
            return self._success("top_scoring_team", answer, result)

        if "relegat" in folded:
            if season is None:
                return self._success("relegation_candidates", "Please include a season for a relegation-table query.", {"standings": []})
            result = self.repository.competition_standings(competition or "Brasileirão", season)
            bottom = result["standings"][-4:]
            names = ", ".join(row["team"] for row in bottom) or "none"
            return self._success(
                "relegation_candidates",
                f"Bottom four by the calculated table: {names}. The source data does not explicitly label relegation.",
                {**result, "bottom_four": bottom},
            )

        if "won" in folded or "champion" in folded or "standings" in folded:
            if season is None:
                return self._success("standings", "Please include a season for a standings query.", {"standings": []})
            result = self.repository.competition_standings(competition or "Brasileirão", season)
            leader = result["standings"][0] if result["standings"] else None
            answer = "No completed matches matched those criteria." if not leader else (
                f"Calculated {result['season']} {result['competition']} leader: {leader['team']} on {leader['points']} points."
            )
            return self._success("standings", answer, result)

        if "bracket" in folded:
            if season is None or not competition:
                return self._success("competition_bracket", "Please include a competition and season for a bracket query.", {"stages": {}})
            result = self.repository.competition_matches_by_stage(competition, season, limit=limit)
            stages = ", ".join(result["stages"].keys()) or "none"
            return self._success("competition_bracket", f"Available stages: {stages}. {result['note']}", result)

        is_last_meeting = "last play" in folded or "last played" in folded or "most recent" in folded
        is_head_to_head = "head to head" in folded or "compare" in folded or " versus " in f" {folded} " or " vs " in f" {folded} "
        if len(teams) >= 2 and (is_last_meeting or is_head_to_head):
            first, second = (self.repository.display_name(team) for team in teams[:2])
            if is_last_meeting:
                result = self.repository.search_matches(team=first, opponent=second, competition=competition, season=season, limit=limit)
                self._last_matches = result["matches"]
                return self._success("last_meeting", self._matches_answer(result, title=f"Most recent {first} vs {second}"), result)
            result = self.repository.head_to_head(first, second, competition=competition, season=season, limit=limit)
            self._last_matches = result["recent_matches"]
            answer = (
                f"{result['team_one']} vs {result['team_two']}: {result['team_one_record']['wins']} wins, "
                f"{result['team_two_record']['wins']} wins, {result['team_one_record']['draws']} draws in {result['matches']} match(es)."
            )
            return self._success("head_to_head", answer, result)

        if "final" in folded and competition:
            result = self.repository.search_matches(
                competition=competition, season=season, round_or_stage="final", limit=limit
            )
            self._last_matches = result["matches"]
            return self._success("match_search", self._matches_answer(result, title=f"{competition} finals"), result)

        if "match" in folded or "played" in folded or (teams and season is not None):
            team = self.repository.display_name(teams[0]) if teams else None
            result = self.repository.search_matches(team=team, competition=competition, season=season, limit=limit)
            self._last_matches = result["matches"]
            return self._success("match_search", self._matches_answer(result), result)

        examples = (
            "Try a match, team, player, standings, or statistics question — for example: "
            "‘When did Flamengo last play Corinthians?’"
        )
        return self._success("unsupported", examples, {"supported_examples": ["When did Flamengo last play Corinthians?", "Who are the top Brazilian players?", "Who won the 2019 Brasileirão?"]})
