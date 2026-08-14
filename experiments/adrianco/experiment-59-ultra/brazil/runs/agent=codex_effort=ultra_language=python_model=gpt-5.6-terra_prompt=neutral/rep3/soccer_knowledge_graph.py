"""Offline knowledge graph and query service for the bundled soccer datasets.

The module deliberately keeps the data layer dependency-free.  It can therefore be
used directly in tests, a Python shell, or an MCP server without requiring a
database, network access, or an LLM.  The MCP adapter lives in :mod:`server`.
"""

from __future__ import annotations

import csv
import os
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data" / "kaggle"


# Brazilian state abbreviations are deliberately used only as part of an
# identity.  Removing them indiscriminately merges distinct clubs such as
# Atlético-MG, Atlético-GO, and Atlético-PR.
STATE_CODES = frozenset(
    {
        "ac",
        "al",
        "am",
        "ap",
        "ba",
        "bh",  # Present in the historical source for Bahia.
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
)


def normalize_text(value: object | None) -> str:
    """Return an accent- and punctuation-insensitive comparison key."""

    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.casefold() in {"na", "n/a", "nan", "none", "-"}:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


# A small, explicit identity map handles the well-known variants found across
# the sources.  Unrecognised state suffixes remain part of the identity.
TEAM_ALIASES: dict[str, str] = {
    "flamengo": "flamengo-rj",
    "flamengo rj": "flamengo-rj",
    "clube de regatas do flamengo": "flamengo-rj",
    "cr flamengo": "flamengo-rj",
    "flamengo pi": "flamengo-pi",
    "flamengo do piaui": "flamengo-pi",
    "fluminense": "fluminense-rj",
    "fluminense rj": "fluminense-rj",
    "fluminense football club": "fluminense-rj",
    "fluminense pi": "fluminense-pi",
    "palmeiras": "palmeiras-sp",
    "palmeiras sp": "palmeiras-sp",
    "sociedade esportiva palmeiras": "palmeiras-sp",
    "se palmeiras": "palmeiras-sp",
    "corinthians": "corinthians-sp",
    "corinthians sp": "corinthians-sp",
    "sport club corinthians paulista": "corinthians-sp",
    "sc corinthians paulista": "corinthians-sp",
    "sao paulo": "sao-paulo-sp",
    "sao paulo sp": "sao-paulo-sp",
    "sao paulo fc": "sao-paulo-sp",
    "sao paulo futebol clube": "sao-paulo-sp",
    "santos": "santos-sp",
    "santos sp": "santos-sp",
    "gremio": "gremio-rs",
    "gremio rs": "gremio-rs",
    "gremio fbpa": "gremio-rs",
    "vasco": "vasco-rj",
    "vasco da gama": "vasco-rj",
    "vasco da gama rj": "vasco-rj",
    "club de regatas vasco da gama": "vasco-rj",
    "vasco rj": "vasco-rj",
    "botafogo": "botafogo-rj",
    "botafogo rj": "botafogo-rj",
    "cruzeiro": "cruzeiro-mg",
    "cruzeiro mg": "cruzeiro-mg",
    "bahia": "bahia-ba",
    "bahia ba": "bahia-ba",
    "atletico mg": "atletico-mg",
    "atletico mineiro": "atletico-mg",
    "clube atletico mineiro": "atletico-mg",
    "atletico go": "atletico-go",
    "atletico goianiense": "atletico-go",
    "atletico pr": "athletico-pr",
    "athletico pr": "athletico-pr",
    "atletico paranaense": "athletico-pr",
    "athletico paranaense": "athletico-pr",
    "america mg": "america-mg",
    "america mineiro": "america-mg",
    "america rn": "america-rn",
    "internacional": "internacional-rs",
    "internacional rs": "internacional-rs",
    "sport": "sport-pe",
    "sport pe": "sport-pe",
    "sport club do recife": "sport-pe",
    "fortaleza": "fortaleza-ce",
    "fortaleza ce": "fortaleza-ce",
    "ceara": "ceara-ce",
    "ceara ce": "ceara-ce",
    "chapecoense": "chapecoense-sc",
    "chapecoense sc": "chapecoense-sc",
    "goias": "goias-go",
    "goias go": "goias-go",
    "coritiba": "coritiba-pr",
    "coritiba pr": "coritiba-pr",
    "ponte preta": "ponte-preta-sp",
    "ponte preta sp": "ponte-preta-sp",
}

TEAM_LABELS: dict[str, str] = {
    "flamengo-rj": "Flamengo",
    "fluminense-rj": "Fluminense",
    "palmeiras-sp": "Palmeiras",
    "corinthians-sp": "Corinthians",
    "sao-paulo-sp": "São Paulo",
    "santos-sp": "Santos",
    "gremio-rs": "Grêmio",
    "vasco-rj": "Vasco da Gama",
    "botafogo-rj": "Botafogo",
    "cruzeiro-mg": "Cruzeiro",
    "bahia-ba": "Bahia",
    "atletico-mg": "Atlético-MG",
    "atletico-go": "Atlético-GO",
    "athletico-pr": "Athletico-PR",
    "america-mg": "América-MG",
    "america-rn": "América-RN",
    "internacional-rs": "Internacional",
    "sport-pe": "Sport",
    "fortaleza-ce": "Fortaleza",
    "ceara-ce": "Ceará",
    "chapecoense-sc": "Chapecoense",
    "goias-go": "Goiás",
    "coritiba-pr": "Coritiba",
    "ponte-preta-sp": "Ponte Preta",
}


def team_identity(name: object | None, state: object | None = None) -> str:
    """Create a stable team identity without collapsing different state clubs."""

    normalized = normalize_text(name)
    if not normalized:
        return ""
    if normalized in TEAM_ALIASES:
        return TEAM_ALIASES[normalized]

    parts = normalized.split()
    suffix = ""
    if parts and parts[-1] in STATE_CODES:
        suffix = parts.pop()
    supplied_state = normalize_text(state)
    if not suffix and supplied_state in STATE_CODES:
        suffix = supplied_state
    base = " ".join(parts) if parts else normalized

    # Resolve a state-aware alias before falling back to a generic identity.
    alias_key = f"{base} {suffix}".strip()
    if alias_key in TEAM_ALIASES:
        return TEAM_ALIASES[alias_key]
    if base in TEAM_ALIASES and not suffix:
        return TEAM_ALIASES[base]
    return f"{base}-{suffix}" if suffix else base.replace(" ", "-")


def loose_team_identity(team_key: str) -> str:
    """A display/search aid; never use this as an aggregate identity."""

    return re.sub(r"-(?:" + "|".join(sorted(STATE_CODES)) + r")$", "", team_key)


def canonical_competition(value: object | None) -> str:
    key = normalize_text(value)
    if not key:
        return "Unknown competition"
    if "libertadores" in key:
        return "Copa Libertadores"
    if "copa do brasil" in key:
        return "Copa do Brasil"
    if key in {"serie a", "serie a brazil", "brasileirao", "brasileirao serie a"} or (
        "campeonato brasileiro" in key
    ):
        return "Brasileirão Série A"
    if key == "serie b":
        return "Série B"
    if key == "serie c":
        return "Série C"
    return str(value).strip()


def parse_date(value: object | None) -> date | None:
    """Parse the ISO and Brazilian date shapes used by the provided sources."""

    raw = str(value or "").strip()
    if not raw or raw.casefold() in {"na", "n/a", "nan", "none", "-"}:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def parse_int(value: object | None) -> int | None:
    raw = str(value or "").strip()
    if not raw or raw.casefold() in {"na", "n/a", "nan", "none", "-"}:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def parse_number(value: object | None) -> int | float | None:
    raw = str(value or "").strip()
    if not raw or raw.casefold() in {"na", "n/a", "nan", "none", "-"}:
        return None
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _display_from_raw(name: str) -> str:
    """Keep source spelling, minus an obvious state suffix, for unknown clubs."""

    value = re.sub(r"\s*-\s*[A-Za-z]{2}$", "", name.strip())
    return value or name.strip()


@dataclass(slots=True)
class Match:
    match_id: str
    match_date: date | None
    home_team: str
    away_team: str
    home_key: str
    away_key: str
    home_goal: int | None
    away_goal: int | None
    competition: str
    season: int | None
    round: str | None
    stage: str | None
    source_dataset: str
    source_key: str
    stadium: str | None = None
    statistics: dict[str, int | float] = field(default_factory=dict)
    source_datasets: set[str] = field(default_factory=set)

    @property
    def is_completed(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    def dedupe_key(self) -> tuple[object, ...]:
        return (
            self.match_date.isoformat() if self.match_date else None,
            self.home_key,
            self.away_key,
            self.home_goal,
            self.away_goal,
            normalize_text(self.competition),
        )

    def as_dict(self, label_for: Callable[[str], str]) -> dict[str, object]:
        score = f"{self.home_goal}-{self.away_goal}" if self.is_completed else None
        payload: dict[str, object] = {
            "id": self.match_id,
            "date": self.match_date.isoformat() if self.match_date else None,
            "competition": self.competition,
            "season": self.season,
            "round": self.round,
            "stage": self.stage,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_team_normalized": label_for(self.home_key),
            "away_team_normalized": label_for(self.away_key),
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "score": score,
            "completed": self.is_completed,
            "source_dataset": self.source_dataset,
            "source_datasets": sorted(self.source_datasets or {self.source_dataset}),
        }
        if self.stadium:
            payload["stadium"] = self.stadium
        if self.statistics:
            payload["statistics"] = dict(self.statistics)
        return payload


@dataclass(slots=True)
class Player:
    player_id: str
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    height: str
    weight: str
    attributes: dict[str, str]

    def as_dict(self, include_attributes: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
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
        }
        if include_attributes:
            payload["attributes"] = dict(self.attributes)
        return payload


@dataclass(frozen=True, slots=True)
class TeamResolution:
    query: str
    team_key: str | None
    candidates: tuple[str, ...] = ()

    @property
    def ambiguous(self) -> bool:
        return self.team_key is None and bool(self.candidates)


SOURCE_FILES: Mapping[str, str] = {
    "brasileirao": "Brasileirao_Matches.csv",
    "brazilian_cup": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "extended": "BR-Football-Dataset.csv",
    "historical": "novo_campeonato_brasileiro.csv",
    "fifa": "fifa_data.csv",
}

SOURCE_LABELS: Mapping[str, str] = {
    "brasileirao": "Brasileirão Serie A matches",
    "brazilian_cup": "Copa do Brasil matches",
    "libertadores": "Copa Libertadores matches",
    "extended": "Extended Brazilian football statistics",
    "historical": "Historical Brasileirão",
    "fifa": "FIFA player database",
}

SOURCE_ALIASES: Mapping[str, str] = {
    "brasileirao": "brasileirao",
    "brasileirao matches": "brasileirao",
    "brasileirao matches csv": "brasileirao",
    "brazilian cup": "brazilian_cup",
    "brazilian cup matches": "brazilian_cup",
    "copa do brasil": "brazilian_cup",
    "libertadores": "libertadores",
    "libertadores matches": "libertadores",
    "br football dataset": "extended",
    "extended": "extended",
    "historical": "historical",
    "novo campeonato brasileiro": "historical",
}


DERBIES: Mapping[frozenset[str], str] = {
    frozenset(("flamengo-rj", "fluminense-rj")): "Fla-Flu",
    frozenset(("palmeiras-sp", "corinthians-sp")): "Derby Paulista",
    frozenset(("palmeiras-sp", "sao-paulo-sp")): "Choque-Rei",
    frozenset(("corinthians-sp", "sao-paulo-sp")): "Majestoso",
    frozenset(("gremio-rs", "internacional-rs")): "Grenal",
    frozenset(("atletico-mg", "cruzeiro-mg")): "Clássico Mineiro",
    frozenset(("vasco-rj", "flamengo-rj")): "Clássico dos Milhões",
    frozenset(("botafogo-rj", "flamengo-rj")): "Clássico da Rivalidade",
}


class SoccerKnowledgeGraph:
    """Loads the local CSV files and exposes graph-like soccer queries.

    ``canonical`` mode is the default for aggregates.  It uses one preferred
    primary source for each competition/year, preventing the sizeable overlap
    among the provided datasets from inflating standings and team records.
    ``all`` retains every source row, while ``unique`` deduplicates matching
    fixtures and retains their provenance.
    """

    def __init__(self, data_dir: str | Path | None = None, *, load: bool = True) -> None:
        configured_dir = data_dir or os.environ.get("BRAZILIAN_SOCCER_DATA_DIR") or DEFAULT_DATA_DIR
        self.data_dir = Path(configured_dir).expanduser().resolve()
        self._raw_matches: list[Match] = []
        self._unique_matches: list[Match] = []
        self.players: list[Player] = []
        self._team_labels: dict[str, str] = dict(TEAM_LABELS)
        self._source_counts: dict[str, dict[str, int]] = {
            source: {"rows": 0, "loaded": 0, "skipped": 0}
            for source in SOURCE_FILES
        }
        self._loaded = False
        if load:
            self.load()

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def matches(self) -> list[Match]:
        """All source rows, retained with source-specific provenance."""

        self._ensure_loaded()
        return self._raw_matches

    @property
    def unique_matches(self) -> list[Match]:
        self._ensure_loaded()
        return self._unique_matches

    def load(self) -> None:
        if self._loaded:
            return
        missing = [filename for filename in SOURCE_FILES.values() if not (self.data_dir / filename).is_file()]
        if missing:
            names = ", ".join(missing)
            raise FileNotFoundError(f"Brazilian soccer data files not found in {self.data_dir}: {names}")

        self._load_brasileirao()
        self._load_brazilian_cup()
        self._load_libertadores()
        self._load_extended()
        self._load_historical()
        self._load_players()
        self._unique_matches = self._deduplicate_matches(self._raw_matches)
        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def _rows(self, source_key: str) -> Iterable[dict[str, str]]:
        path = self.data_dir / SOURCE_FILES[source_key]
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                self._source_counts[source_key]["rows"] += 1
                yield {str(key or "").strip(): str(value or "").strip() for key, value in row.items()}

    def _append_match(
        self,
        source_key: str,
        row_number: int,
        *,
        match_date: date | None,
        home_team: str,
        away_team: str,
        home_goal: int | None,
        away_goal: int | None,
        competition: str,
        season: int | None,
        round_value: object | None = None,
        stage: object | None = None,
        home_state: object | None = None,
        away_state: object | None = None,
        stadium: object | None = None,
        statistics: Mapping[str, int | float | None] | None = None,
    ) -> None:
        # The Libertadores source has a placeholder with no date, season, or
        # score.  It is transparently counted as skipped rather than treated as
        # a real fixture.
        if not home_team or not away_team or (match_date is None and season is None):
            self._source_counts[source_key]["skipped"] += 1
            return
        source_filename = SOURCE_FILES[source_key]
        stats = {key: value for key, value in (statistics or {}).items() if value is not None}
        match = Match(
            match_id=f"{source_key}:{row_number}",
            match_date=match_date,
            home_team=home_team,
            away_team=away_team,
            home_key=team_identity(home_team, home_state),
            away_key=team_identity(away_team, away_state),
            home_goal=home_goal,
            away_goal=away_goal,
            competition=canonical_competition(competition),
            season=season,
            round=str(round_value).strip() if round_value not in (None, "") else None,
            stage=str(stage).strip() if stage not in (None, "") else None,
            source_dataset=source_filename,
            source_key=source_key,
            stadium=str(stadium).strip() if stadium not in (None, "") else None,
            statistics=stats,
            source_datasets={source_filename},
        )
        self._raw_matches.append(match)
        self._source_counts[source_key]["loaded"] += 1
        self._register_team_label(match.home_key, home_team)
        self._register_team_label(match.away_key, away_team)

    def _register_team_label(self, team_key: str, raw_name: str) -> None:
        self._team_labels.setdefault(team_key, _display_from_raw(raw_name))

    def _load_brasileirao(self) -> None:
        for row_number, row in enumerate(self._rows("brasileirao"), start=1):
            self._append_match(
                "brasileirao",
                row_number,
                match_date=parse_date(row.get("datetime")),
                home_team=row.get("home_team", ""),
                away_team=row.get("away_team", ""),
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
                competition="Brasileirão Série A",
                season=parse_int(row.get("season")),
                round_value=row.get("round"),
                home_state=row.get("home_team_state"),
                away_state=row.get("away_team_state"),
            )

    def _load_brazilian_cup(self) -> None:
        for row_number, row in enumerate(self._rows("brazilian_cup"), start=1):
            self._append_match(
                "brazilian_cup",
                row_number,
                match_date=parse_date(row.get("datetime")),
                home_team=row.get("home_team", ""),
                away_team=row.get("away_team", ""),
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
                competition="Copa do Brasil",
                season=parse_int(row.get("season")),
                round_value=row.get("round"),
            )

    def _load_libertadores(self) -> None:
        for row_number, row in enumerate(self._rows("libertadores"), start=1):
            self._append_match(
                "libertadores",
                row_number,
                match_date=parse_date(row.get("datetime")),
                home_team=row.get("home_team", ""),
                away_team=row.get("away_team", ""),
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
                competition="Copa Libertadores",
                season=parse_int(row.get("season")),
                stage=row.get("stage"),
            )

    def _load_extended(self) -> None:
        stat_fields = {
            "home_corners": "home_corner",
            "away_corners": "away_corner",
            "home_attacks": "home_attack",
            "away_attacks": "away_attack",
            "home_shots": "home_shots",
            "away_shots": "away_shots",
            "total_corners": "total_corners",
        }
        for row_number, row in enumerate(self._rows("extended"), start=1):
            match_date = parse_date(row.get("date"))
            statistics = {name: parse_number(row.get(field)) for name, field in stat_fields.items()}
            self._append_match(
                "extended",
                row_number,
                match_date=match_date,
                home_team=row.get("home", ""),
                away_team=row.get("away", ""),
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
                competition=row.get("tournament", "Unknown competition"),
                season=match_date.year if match_date else None,
                stadium=None,
                statistics=statistics,
            )

    def _load_historical(self) -> None:
        for row_number, row in enumerate(self._rows("historical"), start=1):
            self._append_match(
                "historical",
                row_number,
                match_date=parse_date(row.get("Data")),
                home_team=row.get("Equipe_mandante", ""),
                away_team=row.get("Equipe_visitante", ""),
                home_goal=parse_int(row.get("Gols_mandante")),
                away_goal=parse_int(row.get("Gols_visitante")),
                competition="Brasileirão Série A",
                season=parse_int(row.get("Ano")),
                round_value=row.get("Rodada"),
                home_state=row.get("Mandante_UF"),
                away_state=row.get("Visitante_UF"),
                stadium=row.get("Arena"),
            )

    def _load_players(self) -> None:
        for row_number, row in enumerate(self._rows("fifa"), start=1):
            name = row.get("Name", "")
            player_id = row.get("ID", "")
            if not name or not player_id:
                self._source_counts["fifa"]["skipped"] += 1
                continue
            known = {
                "ID",
                "Name",
                "Age",
                "Nationality",
                "Overall",
                "Potential",
                "Club",
                "Position",
                "Jersey Number",
                "Height",
                "Weight",
                "",
            }
            attributes = {key: value for key, value in row.items() if key not in known and value}
            self.players.append(
                Player(
                    player_id=player_id,
                    name=name,
                    age=parse_int(row.get("Age")),
                    nationality=row.get("Nationality", ""),
                    overall=parse_int(row.get("Overall")),
                    potential=parse_int(row.get("Potential")),
                    club=row.get("Club", ""),
                    position=row.get("Position", ""),
                    jersey_number=parse_int(row.get("Jersey Number")),
                    height=row.get("Height", ""),
                    weight=row.get("Weight", ""),
                    attributes=attributes,
                )
            )
            self._source_counts["fifa"]["loaded"] += 1

    def _deduplicate_matches(self, matches: Sequence[Match]) -> list[Match]:
        deduped: dict[tuple[object, ...], Match] = {}
        for match in matches:
            key = match.dedupe_key()
            existing = deduped.get(key)
            if existing is None:
                deduped[key] = replace(
                    match,
                    source_datasets=set(match.source_datasets),
                    statistics=dict(match.statistics),
                )
                continue
            existing.source_datasets.update(match.source_datasets)
            # Retain information that a preferred source did not contain.
            if not existing.stadium and match.stadium:
                existing.stadium = match.stadium
            for stat_name, value in match.statistics.items():
                existing.statistics.setdefault(stat_name, value)
        return sorted(deduped.values(), key=self._sort_key, reverse=True)

    @staticmethod
    def _sort_key(match: Match) -> tuple[date, str]:
        return (match.match_date or date.min, match.match_id)

    def team_label(self, team_key: str) -> str:
        if team_key in self._team_labels:
            return self._team_labels[team_key]
        return team_key.replace("-", " ").title()

    def resolve_team(self, team: str | None) -> TeamResolution:
        self._ensure_loaded()
        query = str(team or "").strip()
        if not query:
            return TeamResolution(query=query, team_key=None)
        direct = team_identity(query)
        if direct in self._team_labels:
            return TeamResolution(query=query, team_key=direct)

        normalized = normalize_text(query)
        candidates = sorted(
            key
            for key, label in self._team_labels.items()
            if normalize_text(label) == normalized or loose_team_identity(key).replace("-", " ") == normalized
        )
        if len(candidates) == 1:
            return TeamResolution(query=query, team_key=candidates[0])
        return TeamResolution(query=query, team_key=None, candidates=tuple(candidates))

    def _resolve_source(self, source: str | None) -> str | None:
        if not source:
            return None
        raw = normalize_text(source)
        if raw in SOURCE_ALIASES:
            return SOURCE_ALIASES[raw]
        for source_key, filename in SOURCE_FILES.items():
            if raw == normalize_text(filename):
                return source_key
        raise ValueError(f"Unknown source '{source}'. Use one of: {', '.join(SOURCE_FILES.values())}.")

    def _validate_mode(self, dataset_mode: str) -> str:
        normalized = normalize_text(dataset_mode).replace(" ", "_")
        if normalized not in {"canonical", "all", "unique"}:
            raise ValueError("dataset_mode must be one of: canonical, all, unique")
        return normalized

    def _is_canonical(self, match: Match) -> bool:
        year = match.season or (match.match_date.year if match.match_date else None)
        if match.competition == "Brasileirão Série A":
            if year is not None and year <= 2011:
                return match.source_key == "historical"
            if year is not None and year <= 2022:
                return match.source_key == "brasileirao"
            return match.source_key == "extended"
        if match.competition == "Copa do Brasil":
            if year is not None and year <= 2021:
                return match.source_key == "brazilian_cup"
            return match.source_key == "extended"
        if match.competition == "Copa Libertadores":
            return match.source_key == "libertadores"
        return match.source_key == "extended"

    def _matches_for_mode(self, dataset_mode: str) -> list[Match]:
        mode = self._validate_mode(dataset_mode)
        if mode == "all":
            return self._raw_matches
        if mode == "unique":
            return self._unique_matches
        return [match for match in self._raw_matches if self._is_canonical(match)]

    @staticmethod
    def _limit(limit: int | str | None) -> int:
        if limit is None:
            return 25
        try:
            value = int(limit)
        except (TypeError, ValueError) as error:
            raise ValueError("limit must be a whole number") from error
        if value < 1:
            raise ValueError("limit must be at least 1")
        return min(value, 100)

    @staticmethod
    def _parse_query_date(value: str | date | None, name: str) -> date | None:
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value
        parsed = parse_date(value)
        if parsed is None:
            raise ValueError(f"{name} must be an ISO date (YYYY-MM-DD) or a supported source date")
        return parsed

    def _filter_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        home_team: str | None = None,
        away_team: str | None = None,
        competition: str | None = None,
        season: int | str | None = None,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        stage: str | None = None,
        round_value: str | int | None = None,
        source: str | None = None,
        dataset_mode: str = "canonical",
    ) -> tuple[list[Match], dict[str, object]]:
        self._ensure_loaded()
        resolutions = {
            "team": self.resolve_team(team) if team else None,
            "opponent": self.resolve_team(opponent) if opponent else None,
            "home_team": self.resolve_team(home_team) if home_team else None,
            "away_team": self.resolve_team(away_team) if away_team else None,
        }
        ambiguous = [resolution for resolution in resolutions.values() if resolution and resolution.ambiguous]
        unresolved = [resolution for resolution in resolutions.values() if resolution and resolution.team_key is None]
        context: dict[str, object] = {
            "resolved_teams": {
                name: self.team_label(resolution.team_key)
                for name, resolution in resolutions.items()
                if resolution and resolution.team_key
            }
        }
        if ambiguous:
            context["ambiguous_teams"] = {
                item.query: [self.team_label(candidate) for candidate in item.candidates] for item in ambiguous
            }
        if unresolved:
            return [], context

        parsed_season = parse_int(season)
        if season not in (None, "") and parsed_season is None:
            raise ValueError("season must be a four-digit year")
        start = self._parse_query_date(start_date, "start_date")
        end = self._parse_query_date(end_date, "end_date")
        if start and end and start > end:
            raise ValueError("start_date must be on or before end_date")
        source_key = self._resolve_source(source)
        competition_key = normalize_text(canonical_competition(competition)) if competition else ""
        stage_key = normalize_text(stage)
        round_key = normalize_text(round_value)

        selected = self._raw_matches if source_key else self._matches_for_mode(dataset_mode)
        result: list[Match] = []
        for match in selected:
            if source_key and match.source_key != source_key:
                continue
            if competition_key and normalize_text(match.competition) != competition_key:
                continue
            if parsed_season is not None and match.season != parsed_season:
                continue
            if start and (match.match_date is None or match.match_date < start):
                continue
            if end and (match.match_date is None or match.match_date > end):
                continue
            if stage_key and normalize_text(match.stage) != stage_key:
                continue
            if round_key and normalize_text(match.round) != round_key:
                continue

            team_resolution = resolutions["team"]
            opponent_resolution = resolutions["opponent"]
            home_resolution = resolutions["home_team"]
            away_resolution = resolutions["away_team"]
            if team_resolution and team_resolution.team_key not in {match.home_key, match.away_key}:
                continue
            if opponent_resolution and opponent_resolution.team_key not in {match.home_key, match.away_key}:
                continue
            if home_resolution and home_resolution.team_key != match.home_key:
                continue
            if away_resolution and away_resolution.team_key != match.away_key:
                continue
            # When two generic teams are supplied, require a true head-to-head
            # rather than allowing the same side to satisfy both filters.
            if team_resolution and opponent_resolution and {match.home_key, match.away_key} != {
                team_resolution.team_key,
                opponent_resolution.team_key,
            }:
                continue
            result.append(match)
        return sorted(result, key=self._sort_key, reverse=True), context

    def search_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        home_team: str | None = None,
        away_team: str | None = None,
        competition: str | None = None,
        season: int | str | None = None,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        stage: str | None = None,
        round: str | int | None = None,
        source: str | None = None,
        dataset_mode: str = "canonical",
        limit: int = 25,
    ) -> dict[str, object]:
        """Find fixtures using team, date, competition, and source filters."""

        maximum = self._limit(limit)
        matches, context = self._filter_matches(
            team=team,
            opponent=opponent,
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            season=season,
            start_date=start_date,
            end_date=end_date,
            stage=stage,
            round_value=round,
            source=source,
            dataset_mode=dataset_mode,
        )
        returned = matches[:maximum]
        payload: dict[str, object] = {
            "count": len(matches),
            "returned": len(returned),
            "truncated": len(matches) > len(returned),
            "dataset_mode": "source-specific" if source else self._validate_mode(dataset_mode),
            "matches": [match.as_dict(self.team_label) for match in returned],
            **context,
        }
        if context.get("ambiguous_teams"):
            payload["message"] = "A team name is ambiguous; use a state-qualified team name from ambiguous_teams."
        elif not matches:
            payload["message"] = "No matches found for these criteria."
        return payload

    def _team_match_set(
        self,
        team: str,
        *,
        season: int | str | None = None,
        competition: str | None = None,
        venue: str = "all",
        dataset_mode: str = "canonical",
    ) -> tuple[list[Match], TeamResolution, str]:
        resolution = self.resolve_team(team)
        normalized_venue = normalize_text(venue)
        if normalized_venue not in {"all", "home", "away"}:
            raise ValueError("venue must be one of: all, home, away")
        if resolution.team_key is None:
            return [], resolution, normalized_venue
        matches, _ = self._filter_matches(
            team=team,
            competition=competition,
            season=season,
            dataset_mode=dataset_mode,
        )
        if normalized_venue == "home":
            matches = [match for match in matches if match.home_key == resolution.team_key]
        elif normalized_venue == "away":
            matches = [match for match in matches if match.away_key == resolution.team_key]
        return matches, resolution, normalized_venue

    @staticmethod
    def _empty_record() -> dict[str, int]:
        return {
            "matches": 0,
            "completed_matches": 0,
            "unscored_matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }

    @staticmethod
    def _apply_result(record: dict[str, int], goals_for: int | None, goals_against: int | None) -> None:
        record["matches"] += 1
        if goals_for is None or goals_against is None:
            record["unscored_matches"] += 1
            return
        record["completed_matches"] += 1
        record["goals_for"] += goals_for
        record["goals_against"] += goals_against
        if goals_for > goals_against:
            record["wins"] += 1
        elif goals_for < goals_against:
            record["losses"] += 1
        else:
            record["draws"] += 1

    @staticmethod
    def _complete_record(record: dict[str, int]) -> dict[str, object]:
        completed = record["completed_matches"]
        record = dict(record)
        record["goal_difference"] = record["goals_for"] - record["goals_against"]
        record["points"] = record["wins"] * 3 + record["draws"]
        record["win_rate"] = round((record["wins"] / completed) * 100, 1) if completed else 0.0
        return record

    def get_team_statistics(
        self,
        team: str,
        *,
        season: int | str | None = None,
        competition: str | None = None,
        venue: str = "all",
        dataset_mode: str = "canonical",
    ) -> dict[str, object]:
        """Calculate a team's W/D/L and goal record, excluding unknown scores."""

        matches, resolution, normalized_venue = self._team_match_set(
            team,
            season=season,
            competition=competition,
            venue=venue,
            dataset_mode=dataset_mode,
        )
        if resolution.team_key is None:
            return {
                "team": team,
                "matches": 0,
                "message": (
                    f"Team name is ambiguous. Candidates: {', '.join(self.team_label(key) for key in resolution.candidates)}"
                    if resolution.candidates
                    else "No matching team was found."
                ),
                "candidates": [self.team_label(key) for key in resolution.candidates],
            }
        record = self._empty_record()
        for match in matches:
            if match.home_key == resolution.team_key:
                self._apply_result(record, match.home_goal, match.away_goal)
            else:
                self._apply_result(record, match.away_goal, match.home_goal)
        return {
            "team": self.team_label(resolution.team_key),
            "team_id": resolution.team_key,
            "venue": normalized_venue,
            "season": parse_int(season) if season not in (None, "") else None,
            "competition": canonical_competition(competition) if competition else None,
            "dataset_mode": self._validate_mode(dataset_mode),
            **self._complete_record(record),
        }

    def compare_teams(
        self,
        team_a: str,
        team_b: str,
        *,
        season: int | str | None = None,
        competition: str | None = None,
        dataset_mode: str = "canonical",
        limit: int = 25,
    ) -> dict[str, object]:
        """Return a head-to-head record and its most recent fixtures."""

        maximum = self._limit(limit)
        matches, context = self._filter_matches(
            team=team_a,
            opponent=team_b,
            season=season,
            competition=competition,
            dataset_mode=dataset_mode,
        )
        first = self.resolve_team(team_a)
        second = self.resolve_team(team_b)
        if first.team_key is None or second.team_key is None:
            return {
                "message": "Both teams must resolve to one unambiguous club identity.",
                "team_a_candidates": [self.team_label(key) for key in first.candidates],
                "team_b_candidates": [self.team_label(key) for key in second.candidates],
                **context,
            }
        record = {"team_a_wins": 0, "team_b_wins": 0, "draws": 0, "unscored_matches": 0}
        for match in matches:
            if not match.is_completed:
                record["unscored_matches"] += 1
                continue
            a_goals, b_goals = (
                (match.home_goal, match.away_goal)
                if match.home_key == first.team_key
                else (match.away_goal, match.home_goal)
            )
            if a_goals > b_goals:
                record["team_a_wins"] += 1
            elif a_goals < b_goals:
                record["team_b_wins"] += 1
            else:
                record["draws"] += 1
        returned = matches[:maximum]
        return {
            "team_a": self.team_label(first.team_key),
            "team_b": self.team_label(second.team_key),
            "matches": len(matches),
            "returned": len(returned),
            "truncated": len(matches) > len(returned),
            "dataset_mode": self._validate_mode(dataset_mode),
            **record,
            "recent_matches": [match.as_dict(self.team_label) for match in returned],
        }

    def _aggregate_teams(
        self,
        matches: Iterable[Match],
        *,
        venue: str = "all",
    ) -> dict[str, dict[str, int]]:
        records: dict[str, dict[str, int]] = defaultdict(self._empty_record)
        for match in matches:
            if venue in {"all", "home"}:
                self._apply_result(records[match.home_key], match.home_goal, match.away_goal)
            if venue in {"all", "away"}:
                self._apply_result(records[match.away_key], match.away_goal, match.home_goal)
        return records

    def get_standings(
        self,
        season: int | str,
        *,
        competition: str = "Brasileirão",
        dataset_mode: str = "canonical",
    ) -> dict[str, object]:
        """Calculate final/current standings from completed match results."""

        parsed_season = parse_int(season)
        if parsed_season is None:
            raise ValueError("season is required and must be a four-digit year")
        matches, _ = self._filter_matches(
            competition=competition,
            season=parsed_season,
            dataset_mode=dataset_mode,
        )
        records = self._aggregate_teams(matches)
        entries: list[dict[str, object]] = []
        for team_key, record in records.items():
            completed = self._complete_record(record)
            entries.append({"team": self.team_label(team_key), "team_id": team_key, **completed})
        entries.sort(
            key=lambda entry: (
                int(entry["points"]),
                int(entry["goal_difference"]),
                int(entry["goals_for"]),
                int(entry["wins"]),
                str(entry["team"]),
            ),
            reverse=True,
        )
        for rank, entry in enumerate(entries, start=1):
            entry["rank"] = rank
        return {
            "season": parsed_season,
            "competition": canonical_competition(competition),
            "dataset_mode": self._validate_mode(dataset_mode),
            "matches_considered": len(matches),
            "unscored_matches": sum(1 for match in matches if not match.is_completed),
            "champion": entries[0]["team"] if entries else None,
            "standings": entries,
        }

    def get_competition_statistics(
        self,
        *,
        competition: str | None = None,
        season: int | str | None = None,
        dataset_mode: str = "canonical",
    ) -> dict[str, object]:
        """Calculate goals, result rates, and home advantage for a competition."""

        matches, _ = self._filter_matches(
            competition=competition,
            season=season,
            dataset_mode=dataset_mode,
        )
        completed = [match for match in matches if match.is_completed]
        home_wins = sum(match.home_goal > match.away_goal for match in completed)
        draws = sum(match.home_goal == match.away_goal for match in completed)
        away_wins = sum(match.home_goal < match.away_goal for match in completed)
        goals = sum((match.home_goal or 0) + (match.away_goal or 0) for match in completed)
        denominator = len(completed)
        return {
            "competition": canonical_competition(competition) if competition else "All competitions",
            "season": parse_int(season) if season not in (None, "") else None,
            "dataset_mode": self._validate_mode(dataset_mode),
            "matches": len(matches),
            "completed_matches": denominator,
            "unscored_matches": len(matches) - denominator,
            "total_goals": goals,
            "average_goals_per_match": round(goals / denominator, 2) if denominator else 0.0,
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "home_win_rate": round(home_wins / denominator * 100, 1) if denominator else 0.0,
            "draw_rate": round(draws / denominator * 100, 1) if denominator else 0.0,
            "away_win_rate": round(away_wins / denominator * 100, 1) if denominator else 0.0,
        }

    def get_competition_bracket(
        self,
        season: int | str,
        *,
        competition: str = "Libertadores",
        dataset_mode: str = "canonical",
    ) -> dict[str, object]:
        """Group cup fixtures by stage (or Cup round) to form a data-backed bracket."""

        parsed_season = parse_int(season)
        if parsed_season is None:
            raise ValueError("season is required and must be a four-digit year")
        matches, _ = self._filter_matches(
            competition=competition,
            season=parsed_season,
            dataset_mode=dataset_mode,
        )
        grouped: dict[str, list[Match]] = defaultdict(list)
        for match in matches:
            stage = match.stage or (f"Round {match.round}" if match.round else "Unspecified stage")
            grouped[stage].append(match)
        stage_order = {
            "group stage": 0,
            "round of 16": 1,
            "quarterfinals": 2,
            "semifinals": 3,
            "final": 4,
        }
        stages = [
            {
                "stage": stage,
                "matches": [match.as_dict(self.team_label) for match in sorted(items, key=self._sort_key)],
            }
            for stage, items in sorted(
                grouped.items(),
                key=lambda item: (stage_order.get(normalize_text(item[0]), 99), normalize_text(item[0])),
            )
        ]
        return {
            "season": parsed_season,
            "competition": canonical_competition(competition),
            "dataset_mode": self._validate_mode(dataset_mode),
            "stages": stages,
            "matches": len(matches),
        }

    def get_relegated_teams(
        self,
        season: int | str,
        *,
        competition: str = "Brasileirão",
        bottom: int = 4,
        dataset_mode: str = "canonical",
    ) -> dict[str, object]:
        """Return the bottom table positions inferred from the supplied results.

        The result is deliberately labelled as a calculated table rather than an
        external official relegation declaration.
        """

        if bottom < 1:
            raise ValueError("bottom must be at least 1")
        standings = self.get_standings(season, competition=competition, dataset_mode=dataset_mode)
        entries = standings["standings"]
        relegated = list(reversed(entries[-bottom:])) if entries else []
        return {
            "season": standings["season"],
            "competition": standings["competition"],
            "calculation": "Bottom positions in standings calculated from bundled completed match results.",
            "teams": relegated,
            "unscored_matches": standings["unscored_matches"],
        }

    def get_best_team_record(
        self,
        *,
        venue: str = "home",
        competition: str | None = None,
        season: int | str | None = None,
        dataset_mode: str = "canonical",
        limit: int = 10,
    ) -> dict[str, object]:
        """Rank teams by win rate, then points and goal difference."""

        normalized_venue = normalize_text(venue)
        if normalized_venue not in {"home", "away", "all"}:
            raise ValueError("venue must be one of: home, away, all")
        maximum = self._limit(limit)
        matches, _ = self._filter_matches(
            competition=competition,
            season=season,
            dataset_mode=dataset_mode,
        )
        records = self._aggregate_teams(matches, venue=normalized_venue)
        entries = [
            {"team": self.team_label(key), "team_id": key, **self._complete_record(record)}
            for key, record in records.items()
            if record["completed_matches"]
        ]
        entries.sort(
            key=lambda entry: (
                float(entry["win_rate"]),
                int(entry["points"]),
                int(entry["goal_difference"]),
                int(entry["goals_for"]),
            ),
            reverse=True,
        )
        return {
            "venue": normalized_venue,
            "competition": canonical_competition(competition) if competition else "All competitions",
            "season": parse_int(season) if season not in (None, "") else None,
            "dataset_mode": self._validate_mode(dataset_mode),
            "best_team": entries[0] if entries else None,
            "rankings": entries[:maximum],
        }

    def get_biggest_wins(
        self,
        *,
        competition: str | None = None,
        season: int | str | None = None,
        dataset_mode: str = "canonical",
        limit: int = 10,
    ) -> dict[str, object]:
        maximum = self._limit(limit)
        matches, _ = self._filter_matches(
            competition=competition,
            season=season,
            dataset_mode=dataset_mode,
        )
        completed = [match for match in matches if match.is_completed]
        completed.sort(
            key=lambda match: (
                abs((match.home_goal or 0) - (match.away_goal or 0)),
                (match.home_goal or 0) + (match.away_goal or 0),
                match.match_date or date.min,
            ),
            reverse=True,
        )
        results = []
        for match in completed[:maximum]:
            item = match.as_dict(self.team_label)
            item["goal_margin"] = abs((match.home_goal or 0) - (match.away_goal or 0))
            results.append(item)
        return {
            "competition": canonical_competition(competition) if competition else "All competitions",
            "season": parse_int(season) if season not in (None, "") else None,
            "dataset_mode": self._validate_mode(dataset_mode),
            "matches": results,
        }

    def search_players(
        self,
        *,
        query: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | str | None = None,
        limit: int = 25,
        include_attributes: bool = False,
    ) -> dict[str, object]:
        """Find FIFA players by name, nationality, club, position, or rating."""

        self._ensure_loaded()
        maximum = self._limit(limit)
        query_key = normalize_text(query)
        nationality_key = normalize_text(nationality)
        if nationality_key in {"brazilian", "brasileiro", "brasileira"}:
            nationality_key = "brazil"
        club_key = normalize_text(club)
        position_key = normalize_text(position)
        minimum = parse_int(min_overall)
        if min_overall not in (None, "") and minimum is None:
            raise ValueError("min_overall must be a whole number")

        players: list[Player] = []
        for player in self.players:
            if query_key and query_key not in normalize_text(player.name):
                continue
            if nationality_key and nationality_key not in normalize_text(player.nationality):
                continue
            if club_key and club_key not in normalize_text(player.club):
                continue
            if position_key and position_key not in normalize_text(player.position):
                continue
            if minimum is not None and (player.overall is None or player.overall < minimum):
                continue
            players.append(player)
        players.sort(key=lambda player: (player.overall is not None, player.overall or -1, player.name), reverse=True)
        returned = players[:maximum]
        payload: dict[str, object] = {
            "count": len(players),
            "returned": len(returned),
            "truncated": len(players) > len(returned),
            "players": [player.as_dict(include_attributes=include_attributes) for player in returned],
        }
        if not players:
            payload["message"] = "No players in the bundled FIFA snapshot match these criteria."
        return payload

    def get_team_competitions(
        self,
        team: str,
        *,
        dataset_mode: str = "canonical",
    ) -> dict[str, object]:
        matches, resolution, _ = self._team_match_set(team, dataset_mode=dataset_mode)
        if resolution.team_key is None:
            return {
                "team": team,
                "competitions": [],
                "message": "No unambiguous team match was found.",
                "candidates": [self.team_label(key) for key in resolution.candidates],
            }
        counts = Counter(match.competition for match in matches)
        competitions = [
            {"competition": competition, "matches": count}
            for competition, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        return {
            "team": self.team_label(resolution.team_key),
            "team_id": resolution.team_key,
            "dataset_mode": self._validate_mode(dataset_mode),
            "competitions": competitions,
        }

    def search_derbies(
        self,
        *,
        season: int | str | None = None,
        competition: str | None = None,
        dataset_mode: str = "canonical",
        limit: int = 25,
    ) -> dict[str, object]:
        maximum = self._limit(limit)
        matches, _ = self._filter_matches(
            season=season,
            competition=competition,
            dataset_mode=dataset_mode,
        )
        derby_matches: list[tuple[Match, str]] = []
        for match in matches:
            derby_name = DERBIES.get(frozenset((match.home_key, match.away_key)))
            if derby_name:
                derby_matches.append((match, derby_name))
        returned = derby_matches[:maximum]
        return {
            "count": len(derby_matches),
            "returned": len(returned),
            "truncated": len(derby_matches) > len(returned),
            "derbies": [
                {"derby": derby_name, "match": match.as_dict(self.team_label)} for match, derby_name in returned
            ],
        }

    def get_entity_relationships(
        self,
        entity: str,
        *,
        entity_type: str = "team",
        dataset_mode: str = "canonical",
        limit: int = 25,
    ) -> dict[str, object]:
        """Expose graph-style relationships for a team or player entity."""

        maximum = self._limit(limit)
        kind = normalize_text(entity_type)
        if kind == "player":
            found = self.search_players(query=entity, limit=1, include_attributes=True)
            players = found["players"]
            if not players:
                return {"entity": entity, "entity_type": "player", "relationships": [], **found}
            player = players[0]
            relationships = [
                {"type": "NATIONALITY", "target": player["nationality"]},
                {"type": "PLAYS_FOR", "target": player["club"]},
                {"type": "POSITION", "target": player["position"]},
            ]
            return {
                "entity": player["name"],
                "entity_type": "player",
                "relationships": relationships,
                "player": player,
            }
        if kind != "team":
            raise ValueError("entity_type must be 'team' or 'player'")
        matches, resolution, _ = self._team_match_set(entity, dataset_mode=dataset_mode)
        if resolution.team_key is None:
            return {
                "entity": entity,
                "entity_type": "team",
                "relationships": [],
                "candidates": [self.team_label(key) for key in resolution.candidates],
            }
        opponents: Counter[str] = Counter()
        competitions: Counter[str] = Counter()
        for match in matches:
            opponents[match.away_key if match.home_key == resolution.team_key else match.home_key] += 1
            competitions[match.competition] += 1
        relationships = [
            {"type": "PLAYED_IN", "target": competition, "matches": count}
            for competition, count in competitions.most_common()
        ]
        relationships.extend(
            {"type": "PLAYED_AGAINST", "target": self.team_label(opponent), "matches": count}
            for opponent, count in opponents.most_common(maximum)
        )
        player_matches = self.search_players(club=self.team_label(resolution.team_key), limit=maximum)
        relationships.extend(
            {"type": "HAS_PLAYER_SNAPSHOT", "target": player["name"], "overall": player["overall"]}
            for player in player_matches["players"]
        )
        return {
            "entity": self.team_label(resolution.team_key),
            "entity_id": resolution.team_key,
            "entity_type": "team",
            "relationships": relationships,
            "match_count": len(matches),
        }

    def list_available_data(self) -> dict[str, object]:
        """Describe every bundled source and the canonical aggregation policy."""

        self._ensure_loaded()
        sources = []
        for source_key, filename in SOURCE_FILES.items():
            counts = self._source_counts[source_key]
            sources.append(
                {
                    "source_key": source_key,
                    "file": filename,
                    "description": SOURCE_LABELS[source_key],
                    "rows": counts["rows"],
                    "loaded": counts["loaded"],
                    "skipped": counts["skipped"],
                    "kind": "players" if source_key == "fifa" else "matches",
                }
            )
        return {
            "data_directory": str(self.data_dir),
            "sources": sources,
            "raw_match_rows": len(self._raw_matches),
            "unique_match_rows": len(self._unique_matches),
            "players": len(self.players),
            "canonical_policy": (
                "Historical Brasileirão through 2011, Brasileirao_Matches through 2022, extended data for "
                "later Serie A and non-primary competitions; primary Cup and Libertadores sources are preferred."
            ),
            "dataset_modes": {
                "canonical": "Preferred non-overlapping source per competition/year (default for aggregates).",
                "all": "Every source row; useful for source exploration but may include duplicates.",
                "unique": "Cross-source de-duplicated fixtures retaining all source provenance.",
            },
        }

    def _detect_teams_in_question(self, question: str) -> list[str]:
        normalized = normalize_text(question)
        preferred: list[tuple[str, str]] = []
        # Only aliases that deliberately refer to one club can be inferred from
        # prose.  State-qualified raw names are still handled below.
        for alias, key in TEAM_ALIASES.items():
            if key not in self._team_labels:
                continue
            if re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", normalized):
                preferred.append((alias, key))
        preferred.sort(key=lambda pair: (normalized.find(pair[0]), -len(pair[0])))
        result: list[str] = []
        for _, key in preferred:
            if key not in result:
                result.append(key)
        return result

    @staticmethod
    def _years_in_text(text: str) -> list[int]:
        return [int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", text)]

    def ask_soccer(self, question: str, *, limit: int = 10, dataset_mode: str = "canonical") -> dict[str, object]:
        """Answer common natural-language soccer questions without an external LLM.

        This intentionally recognises common query shapes and returns structured
        evidence alongside a concise answer.  An MCP client can use the other
        structured tools for requests outside these patterns.
        """

        if not str(question or "").strip():
            raise ValueError("question must not be empty")
        maximum = self._limit(limit)
        normalized = normalize_text(question)
        years = self._years_in_text(normalized)
        season = years[0] if years else None
        teams = self._detect_teams_in_question(question)
        competition: str | None = None
        if "libertadores" in normalized:
            competition = "Libertadores"
        elif "copa do brasil" in normalized:
            competition = "Copa do Brasil"
        elif "brasileirao" in normalized or "serie a" in normalized:
            competition = "Brasileirão"

        if "derb" in normalized:
            data = self.search_derbies(season=season, competition=competition, dataset_mode=dataset_mode, limit=maximum)
            return {
                "intent": "derby_search",
                "answer": f"Found {data['count']} known derby matches" + (f" in {season}" if season else "") + ".",
                "data": data,
            }
        if "bracket" in normalized or "chave" in normalized:
            if season is None:
                return {
                    "intent": "competition_bracket",
                    "answer": "Please include a season to build a competition bracket.",
                    "data": {},
                }
            data = self.get_competition_bracket(
                season, competition=competition or "Libertadores", dataset_mode=dataset_mode
            )
            return {
                "intent": "competition_bracket",
                "answer": f"{data['competition']} {season} has {len(data['stages'])} recorded stages.",
                "data": data,
            }
        if "relegat" in normalized or "rebaix" in normalized:
            if season is None:
                return {
                    "intent": "relegation",
                    "answer": "Please include a season to calculate the bottom table positions.",
                    "data": {},
                }
            data = self.get_relegated_teams(season, competition=competition or "Brasileirão", dataset_mode=dataset_mode)
            names = ", ".join(item["team"] for item in data["teams"])
            return {
                "intent": "relegation",
                "answer": f"Bottom calculated positions for {season}: {names or 'no teams available'}.",
                "data": data,
            }
        if "final" in normalized and competition:
            stage = "final" if competition == "Libertadores" else None
            cup_round = "8" if competition == "Copa do Brasil" else None
            data = self.search_matches(
                competition=competition,
                season=season,
                stage=stage,
                round=cup_round,
                dataset_mode=dataset_mode,
                limit=maximum,
            )
            return {
                "intent": "competition_finals",
                "answer": f"Found {data['count']} final fixture(s) in the bundled data.",
                "data": data,
            }
        if "biggest" in normalized or "maior" in normalized or "largest win" in normalized:
            data = self.get_biggest_wins(
                competition=competition, season=season, dataset_mode=dataset_mode, limit=maximum
            )
            first = data["matches"][0] if data["matches"] else None
            answer = "No completed matches matched the criteria."
            if first:
                answer = (
                    f"The largest recorded margin is {first['goal_margin']}: {first['home_team_normalized']} "
                    f"{first['score']} {first['away_team_normalized']} on {first['date']}."
                )
            return {"intent": "biggest_wins", "answer": answer, "data": data}
        if "average goals" in normalized or "media de gols" in normalized:
            data = self.get_competition_statistics(
                competition=competition, season=season, dataset_mode=dataset_mode
            )
            return {
                "intent": "competition_statistics",
                "answer": f"Average goals per match: {data['average_goals_per_match']} across {data['completed_matches']} completed matches.",
                "data": data,
            }
        if "best away" in normalized or "melhor fora" in normalized:
            data = self.get_best_team_record(
                venue="away", competition=competition, season=season, dataset_mode=dataset_mode, limit=maximum
            )
            best = data["best_team"]
            answer = "No completed away record is available."
            if best:
                answer = f"Best away record: {best['team']} ({best['wins']}W-{best['draws']}D-{best['losses']}L, {best['win_rate']}% wins)."
            return {"intent": "best_away_record", "answer": answer, "data": data}
        if "best home" in normalized or "melhor em casa" in normalized:
            data = self.get_best_team_record(
                venue="home", competition=competition, season=season, dataset_mode=dataset_mode, limit=maximum
            )
            best = data["best_team"]
            answer = "No completed home record is available."
            if best:
                answer = f"Best home record: {best['team']} ({best['wins']}W-{best['draws']}D-{best['losses']}L, {best['win_rate']}% wins)."
            return {"intent": "best_home_record", "answer": answer, "data": data}
        if ("standings" in normalized or "tabela" in normalized or "who won" in normalized or "quem ganhou" in normalized) and season:
            data = self.get_standings(season, competition=competition or "Brasileirão", dataset_mode=dataset_mode)
            return {
                "intent": "standings",
                "answer": f"{data['champion']} leads the calculated {data['season']} {data['competition']} standings.",
                "data": data,
            }
        if ("compare" in normalized or "comparar" in normalized) and len(years) >= 2 and not teams:
            stats = [
                self.get_competition_statistics(competition=competition, season=year, dataset_mode=dataset_mode)
                for year in years[:2]
            ]
            return {
                "intent": "season_comparison",
                "answer": (
                    f"{years[0]} averaged {stats[0]['average_goals_per_match']} goals per match; "
                    f"{years[1]} averaged {stats[1]['average_goals_per_match']}."
                ),
                "data": {"seasons": stats},
            }
        if ("competition" in normalized or "competicao" in normalized) and teams:
            data = self.get_team_competitions(self.team_label(teams[0]), dataset_mode=dataset_mode)
            names = ", ".join(item["competition"] for item in data["competitions"])
            return {
                "intent": "team_competitions",
                "answer": f"{data['team']} appears in: {names or 'no competitions in the selected data'}.",
                "data": data,
            }
        if ("player" in normalized or "players" in normalized or "jogador" in normalized or "jogadores" in normalized) and (
            "brazil" in normalized or "brasileir" in normalized
        ):
            data = self.search_players(nationality="Brazil", limit=maximum)
            leader = data["players"][0] if data["players"] else None
            answer = "No Brazilian players were found."
            if leader:
                answer = f"Top-rated Brazilian player in this FIFA snapshot: {leader['name']} ({leader['overall']})."
            return {"intent": "player_search", "answer": answer, "data": data}
        if ("players" in normalized or "jogadores" in normalized) and teams:
            team_name = self.team_label(teams[0])
            data = self.search_players(club=team_name, limit=maximum)
            return {
                "intent": "club_players",
                "answer": f"Found {data['count']} FIFA snapshot players whose club contains '{team_name}'.",
                "data": data,
            }
        if normalized.startswith("who is ") or normalized.startswith("quem e "):
            name = re.sub(r"^(?:who is|quem e)\s+", "", normalized)
            data = self.search_players(query=name, limit=maximum, include_attributes=True)
            answer = f"Found {data['count']} player record(s) matching '{name}'."
            return {"intent": "player_lookup", "answer": answer, "data": data}
        if len(teams) >= 2 and ("last" in normalized or "ultima" in normalized or "ultimo" in normalized):
            data = self.compare_teams(
                self.team_label(teams[0]), self.team_label(teams[1]), competition=competition, dataset_mode=dataset_mode, limit=maximum
            )
            latest = data["recent_matches"][0] if data.get("recent_matches") else None
            answer = "No head-to-head match was found."
            if latest:
                answer = (
                    f"Most recent: {latest['date']} — {latest['home_team_normalized']} {latest['score']} "
                    f"{latest['away_team_normalized']} ({latest['competition']})."
                )
            return {"intent": "last_head_to_head", "answer": answer, "data": data}
        if len(teams) >= 2 and ("compare" in normalized or "versus" in normalized or " vs " in f" {normalized} "):
            data = self.compare_teams(
                self.team_label(teams[0]), self.team_label(teams[1]), season=season, competition=competition, dataset_mode=dataset_mode, limit=maximum
            )
            return {
                "intent": "head_to_head",
                "answer": (
                    f"{data.get('team_a', teams[0])}: {data.get('team_a_wins', 0)} wins; "
                    f"{data.get('team_b', teams[1])}: {data.get('team_b_wins', 0)} wins; draws: {data.get('draws', 0)}."
                ),
                "data": data,
            }
        if teams and ("home record" in normalized or "em casa" in normalized):
            data = self.get_team_statistics(
                self.team_label(teams[0]), season=season, competition=competition, venue="home", dataset_mode=dataset_mode
            )
            return {
                "intent": "team_home_record",
                "answer": (
                    f"{data['team']} home record: {data['wins']}W-{data['draws']}D-{data['losses']}L "
                    f"from {data['completed_matches']} completed matches."
                ),
                "data": data,
            }
        if teams:
            data = self.search_matches(team=self.team_label(teams[0]), season=season, competition=competition, dataset_mode=dataset_mode, limit=maximum)
            return {
                "intent": "match_search",
                "answer": f"Found {data['count']} matches for {self.team_label(teams[0])}.",
                "data": data,
            }
        return {
            "intent": "help",
            "answer": (
                "I can search matches, compare teams, calculate standings and statistics, find FIFA players, "
                "list derbies, and inspect team/player graph relationships."
            ),
            "data": {"available_tools": ["search_matches", "get_team_statistics", "search_players", "get_standings"]},
        }


__all__ = [
    "DEFAULT_DATA_DIR",
    "Match",
    "Player",
    "SoccerKnowledgeGraph",
    "canonical_competition",
    "normalize_text",
    "parse_date",
    "team_identity",
]
