"""Normalized, indexed knowledge graph for the bundled Brazilian soccer data."""

from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator


DATA_FILES = (
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
    "fifa_data.csv",
)

BRAZILIAN_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT",
    "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO",
    "RR", "SC", "SP", "SE", "TO",
}

TEAM_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "corinthians paulista": "corinthians",
    "clube de regatas do flamengo": "flamengo",
    "sociedade esportiva palmeiras": "palmeiras",
    "sao paulo futebol clube": "sao paulo",
    "sao paulo fc": "sao paulo",
    "santos futebol clube": "santos",
    "fluminense football club": "fluminense",
    "botafogo de futebol e regatas": "botafogo",
    "club de regatas vasco da gama": "vasco",
    "vasco da gama": "vasco",
    "gremio foot ball porto alegrense": "gremio",
    "gremio porto alegre": "gremio",
    "ec bahia": "bahia",
    "esporte clube bahia": "bahia",
    "ec juventude": "juventude",
    "fortaleza fc": "fortaleza",
    "clube atletico mineiro": "atletico mineiro",
    "atletico": "atletico mineiro",
    "atletico mg": "atletico mineiro",
    "atletico go": "atletico goianiense",
    "america mg": "america mineiro",
    "america": "america mineiro",
    "america rn": "america natal",
    "botafogo rj": "botafogo",
    "botafogo": "botafogo",
    "botafogo pb": "botafogo paraiba",
    "botafogo sp": "botafogo sp",
    "america mineiro": "america mineiro",
    "atletico paranaense": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "atletico pr": "athletico paranaense",
    "sport club internacional": "internacional",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
}

COMPETITION_ALIASES = {
    "brasileirao": "Brasileirão",
    "brasileirao serie a": "Brasileirão",
    "campeonato brasileiro": "Brasileirão",
    "serie a": "Brasileirão",
    "copa do brasil": "Copa do Brasil",
    "brazilian cup": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
    "copa libertadores da america": "Copa Libertadores",
    "serie b": "Série B",
    "serie c": "Série C",
}

RIVALRIES = {
    frozenset(("flamengo", "fluminense")): "Fla-Flu",
    frozenset(("flamengo", "vasco")): "Clássico dos Milhões",
    frozenset(("corinthians", "palmeiras")): "Derby Paulista",
    frozenset(("gremio", "internacional")): "Gre-Nal",
    frozenset(("atletico mineiro", "cruzeiro")): "Clássico Mineiro",
    frozenset(("santos", "sao paulo")): "San-São",
}


def normalize_text(value: str | None) -> str:
    """Return a case/diacritic/punctuation-insensitive search key."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value))
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", asciiish.casefold()).strip()


def normalize_team(value: str | None) -> str:
    """Normalize common Brazilian club variants to a stable graph key."""
    if not value:
        return ""
    cleaned = str(value).strip()
    # Parenthetical country/state qualifiers and historical-name notes are metadata.
    cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", cleaned)
    raw_key = normalize_text(cleaned)
    if raw_key in TEAM_ALIASES:
        return TEAM_ALIASES[raw_key]
    state_pattern = "|".join(sorted(BRAZILIAN_STATES))
    cleaned = re.sub(rf"\s*-\s*(?:{state_pattern})$", "", cleaned, flags=re.I)
    cleaned = re.sub(rf"-(?:{state_pattern})$", "", cleaned, flags=re.I)
    cleaned = re.sub(rf"\s+(?:{state_pattern})$", "", cleaned, flags=re.I)
    key = normalize_text(cleaned)
    return TEAM_ALIASES.get(key, key)


def normalize_competition(value: str | None) -> str:
    key = normalize_text(value)
    return COMPETITION_ALIASES.get(key, str(value or "Unknown").strip() or "Unknown")


def parse_date(value: str | None) -> date | None:
    text = (value or "").strip()
    if not text or normalize_text(text) in {"na", "nan", "none"}:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or normalize_text(text) in {"na", "nan", "none"}:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return int(number) if math.isfinite(number) else None


@dataclass(slots=True)
class Match:
    date: date | None
    competition: str
    home_team: str
    away_team: str
    home_goals: int | None
    away_goals: int | None
    season: int | None = None
    round: str | None = None
    stage: str | None = None
    venue: str | None = None
    home_state: str | None = None
    away_state: str | None = None
    sources: list[str] = field(default_factory=list)
    statistics: dict[str, int | float] = field(default_factory=dict)
    home_key: str = field(init=False, repr=False)
    away_key: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        home_value = self.home_team
        away_value = self.away_team
        if normalize_text(home_value) in {"america", "atletico", "botafogo"} and self.home_state:
            home_value = f"{home_value}-{self.home_state}"
        if normalize_text(away_value) in {"america", "atletico", "botafogo"} and self.away_state:
            away_value = f"{away_value}-{self.away_state}"
        self.home_key = normalize_team(home_value)
        self.away_key = normalize_team(away_value)

    @property
    def played(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.pop("home_key", None)
        result.pop("away_key", None)
        result["date"] = self.date.isoformat() if self.date else None
        result["score"] = (
            f"{self.home_goals}-{self.away_goals}" if self.played else None
        )
        return result


@dataclass(frozen=True, slots=True)
class Player:
    id: int | None
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    attributes: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SoccerGraph:
    """Loads all supplied CSVs into normalized entities and indexed relationships."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir or Path(__file__).parent / "data" / "kaggle")
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self.raw_row_counts: dict[str, int] = {}
        self._matches_by_team: dict[str, list[Match]] = defaultdict(list)
        self._team_names: dict[str, Counter[str]] = defaultdict(Counter)
        self._players_by_club: dict[str, list[Player]] = defaultdict(list)
        self._load()

    @staticmethod
    def _rows(path: Path) -> Iterator[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)

    def _load(self) -> None:
        missing = [name for name in DATA_FILES if not (self.data_dir / name).is_file()]
        if missing:
            raise FileNotFoundError(f"Missing required data files: {', '.join(missing)}")

        candidates: list[Match] = []
        loaders = {
            "Brasileirao_Matches.csv": self._load_brasileirao,
            "Brazilian_Cup_Matches.csv": self._load_brazilian_cup,
            "Libertadores_Matches.csv": self._load_libertadores,
            "BR-Football-Dataset.csv": self._load_extended,
            "novo_campeonato_brasileiro.csv": self._load_historical,
        }
        for filename, loader in loaders.items():
            rows = list(self._rows(self.data_dir / filename))
            self.raw_row_counts[filename] = len(rows)
            candidates.extend(loader(rows, filename))

        player_rows = list(self._rows(self.data_dir / "fifa_data.csv"))
        self.raw_row_counts["fifa_data.csv"] = len(player_rows)
        self.players = self._load_players(player_rows)
        self.matches = self._deduplicate(candidates)
        self._build_indexes()

    def _load_brasileirao(self, rows: Iterable[dict[str, str]], source: str) -> list[Match]:
        return [
            Match(
                date=parse_date(r["datetime"]), competition="Brasileirão",
                home_team=r["home_team"], away_team=r["away_team"],
                home_goals=parse_int(r["home_goal"]), away_goals=parse_int(r["away_goal"]),
                season=parse_int(r["season"]), round=r.get("round"),
                home_state=r.get("home_team_state"), away_state=r.get("away_team_state"),
                sources=[source],
            ) for r in rows
        ]

    def _load_brazilian_cup(self, rows: Iterable[dict[str, str]], source: str) -> list[Match]:
        return [
            Match(
                date=parse_date(r["datetime"]), competition="Copa do Brasil",
                home_team=r["home_team"], away_team=r["away_team"],
                home_goals=parse_int(r["home_goal"]), away_goals=parse_int(r["away_goal"]),
                season=parse_int(r["season"]), round=r.get("round"), sources=[source],
            ) for r in rows
        ]

    def _load_libertadores(self, rows: Iterable[dict[str, str]], source: str) -> list[Match]:
        return [
            Match(
                date=parse_date(r["datetime"]), competition="Copa Libertadores",
                home_team=r["home_team"], away_team=r["away_team"],
                home_goals=parse_int(r["home_goal"]), away_goals=parse_int(r["away_goal"]),
                season=parse_int(r["season"]), stage=r.get("stage"), sources=[source],
            ) for r in rows
        ]

    def _load_extended(self, rows: Iterable[dict[str, str]], source: str) -> list[Match]:
        result = []
        for r in rows:
            statistics = {}
            for key in (
                "home_corner", "away_corner", "home_attack", "away_attack",
                "home_shots", "away_shots", "total_corners",
            ):
                parsed = parse_int(r.get(key))
                if parsed is not None:
                    statistics[key] = parsed
            match_date = parse_date(r.get("date"))
            result.append(Match(
                date=match_date, competition=normalize_competition(r.get("tournament")),
                home_team=r["home"], away_team=r["away"],
                home_goals=parse_int(r.get("home_goal")), away_goals=parse_int(r.get("away_goal")),
                season=match_date.year if match_date else None, sources=[source],
                statistics=statistics,
            ))
        return result

    def _load_historical(self, rows: Iterable[dict[str, str]], source: str) -> list[Match]:
        return [
            Match(
                date=parse_date(r["Data"]), competition="Brasileirão",
                home_team=r["Equipe_mandante"], away_team=r["Equipe_visitante"],
                home_goals=parse_int(r["Gols_mandante"]), away_goals=parse_int(r["Gols_visitante"]),
                season=parse_int(r["Ano"]), round=r.get("Rodada"), venue=r.get("Arena"),
                home_state=r.get("Mandante_UF"), away_state=r.get("Visitante_UF"),
                sources=[source],
            ) for r in rows
        ]

    def _load_players(self, rows: Iterable[dict[str, str]]) -> list[Player]:
        skill_names = (
            "Crossing", "Finishing", "Dribbling", "ShortPassing", "LongPassing",
            "BallControl", "Acceleration", "SprintSpeed", "Stamina", "Strength",
            "LongShots", "Vision", "Composure", "Marking", "StandingTackle",
            "GKDiving", "GKHandling", "GKPositioning", "GKReflexes",
        )
        result = []
        for row in rows:
            attrs = {
                key: value for key in skill_names
                if (value := parse_int(row.get(key))) is not None
            }
            result.append(Player(
                id=parse_int(row.get("ID")), name=(row.get("Name") or "").strip(),
                age=parse_int(row.get("Age")), nationality=(row.get("Nationality") or "").strip(),
                overall=parse_int(row.get("Overall")), potential=parse_int(row.get("Potential")),
                club=(row.get("Club") or "").strip(), position=(row.get("Position") or "").strip(),
                jersey_number=parse_int(row.get("Jersey Number")), attributes=attrs,
            ))
        return result

    @staticmethod
    def _deduplicate(candidates: Iterable[Match]) -> list[Match]:
        unique: dict[tuple[Any, ...], Match] = {}
        fixture_index: dict[tuple[Any, ...], Match] = {}
        result_index: dict[tuple[Any, ...], list[Match]] = defaultdict(list)
        for match in candidates:
            fixture_key = (
                match.date, normalize_text(match.competition), match.home_key, match.away_key,
            )
            key = (
                *fixture_key,
                match.home_goals, match.away_goals,
            )
            existing = unique.get(key)
            # One file sometimes contains an unscored fixture while another has its result.
            fixture = fixture_index.get(fixture_key)
            if existing is None and fixture is not None and (not fixture.played or not match.played):
                existing = fixture
            # Some source dates are shifted by one day (usually a timezone conversion).
            if existing is None and match.played and match.date:
                result_key = (
                    normalize_text(match.competition), match.home_key, match.away_key,
                    match.home_goals, match.away_goals,
                )
                existing = next(
                    (
                        other for other in result_index[result_key]
                        if other.date and abs((other.date - match.date).days) <= 1
                    ),
                    None,
                )
            if existing is None:
                unique[key] = match
                fixture_index[fixture_key] = match
                if match.played:
                    result_index[(
                        normalize_text(match.competition), match.home_key, match.away_key,
                        match.home_goals, match.away_goals,
                    )].append(match)
                continue
            promoted = not existing.played and match.played
            if promoted:
                existing.home_goals = match.home_goals
                existing.away_goals = match.away_goals
                result_index[(
                    normalize_text(existing.competition), existing.home_key, existing.away_key,
                    existing.home_goals, existing.away_goals,
                )].append(existing)
            for source in match.sources:
                if source not in existing.sources:
                    existing.sources.append(source)
            if not existing.statistics and match.statistics:
                existing.statistics = match.statistics
            if not existing.venue and match.venue:
                existing.venue = match.venue
        return list(unique.values())

    def _build_indexes(self) -> None:
        for match in self.matches:
            self._matches_by_team[match.home_key].append(match)
            self._matches_by_team[match.away_key].append(match)
            self._team_names[match.home_key][match.home_team] += 1
            self._team_names[match.away_key][match.away_team] += 1
        for player in self.players:
            self._players_by_club[normalize_team(player.club)].append(player)

    def resolve_team(self, team: str) -> set[str]:
        """Resolve a user spelling to graph keys, preferring an exact alias."""
        key = normalize_team(team)
        if key in self._matches_by_team:
            return {key}
        if not key:
            return set()
        return {
            candidate for candidate in self._matches_by_team
            if key in candidate or candidate in key
        }

    def display_team(self, key: str) -> str:
        names = self._team_names.get(key)
        if not names:
            return key.title()
        name = names.most_common(1)[0][0]
        return re.sub(r"\s*-\s*[A-Z]{2}$", "", name).strip()

    def find_matches(
        self, *, team: str | None = None, opponent: str | None = None,
        start_date: str | date | None = None, end_date: str | date | None = None,
        competition: str | None = None, season: int | None = None,
        stage: str | None = None, source: str | None = None, limit: int = 100,
    ) -> list[Match]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        team_keys = self.resolve_team(team) if team else set()
        opponent_keys = self.resolve_team(opponent) if opponent else set()
        if team and not team_keys or opponent and not opponent_keys:
            return []
        candidates: Iterable[Match]
        if team_keys:
            candidates = {
                id(match): match
                for key in team_keys for match in self._matches_by_team[key]
            }.values()
        else:
            candidates = self.matches
        start = parse_date(start_date) if isinstance(start_date, str) else start_date
        end = parse_date(end_date) if isinstance(end_date, str) else end_date
        competition_key = normalize_text(normalize_competition(competition)) if competition else ""
        stage_key = normalize_text(stage)
        source_key = normalize_text(source)

        def accepted(match: Match) -> bool:
            involved = {match.home_key, match.away_key}
            return (
                (not team_keys or bool(involved & team_keys))
                and (not opponent_keys or bool(involved & opponent_keys))
                and (not opponent_keys or not team_keys or bool(involved & team_keys) and bool(involved & opponent_keys))
                and (start is None or match.date is not None and match.date >= start)
                and (end is None or match.date is not None and match.date <= end)
                and (season is None or match.season == int(season))
                and (not competition_key or normalize_text(match.competition) == competition_key)
                and (not stage_key or stage_key == normalize_text(match.stage))
                and (not source_key or any(source_key in normalize_text(item) for item in match.sources))
            )

        result = [match for match in candidates if accepted(match)]
        result.sort(key=lambda m: (m.date or date.min, m.season or 0), reverse=True)
        return result[:limit]

    def team_statistics(
        self, team: str, *, season: int | None = None,
        competition: str | None = None, venue: str = "all",
    ) -> dict[str, Any]:
        venue = normalize_text(venue)
        if venue not in {"all", "home", "away"}:
            raise ValueError("venue must be 'all', 'home', or 'away'")
        keys = self.resolve_team(team)
        matches = self.find_matches(team=team, season=season, competition=competition, limit=1000)
        wins = draws = losses = goals_for = goals_against = 0
        used: list[Match] = []
        for match in matches:
            is_home = match.home_key in keys
            if venue == "home" and not is_home or venue == "away" and is_home or not match.played:
                continue
            own = match.home_goals if is_home else match.away_goals
            other = match.away_goals if is_home else match.home_goals
            assert own is not None and other is not None
            goals_for += own
            goals_against += other
            wins += own > other
            draws += own == other
            losses += own < other
            used.append(match)
        played = len(used)
        return {
            "team": self.display_team(next(iter(keys))) if keys else team,
            "season": season, "competition": normalize_competition(competition) if competition else None,
            "venue": venue, "matches": played, "wins": wins, "draws": draws,
            "losses": losses, "goals_for": goals_for, "goals_against": goals_against,
            "goal_difference": goals_for - goals_against,
            "points": wins * 3 + draws,
            "win_rate": round(wins * 100 / played, 1) if played else 0.0,
        }

    def head_to_head(
        self, team1: str, team2: str, *, competition: str | None = None,
        season: int | None = None, limit: int = 100,
    ) -> dict[str, Any]:
        keys1, keys2 = self.resolve_team(team1), self.resolve_team(team2)
        matches = self.find_matches(
            team=team1, opponent=team2, competition=competition, season=season, limit=limit,
        )
        first_wins = second_wins = draws = 0
        for match in matches:
            if not match.played:
                continue
            first_home = match.home_key in keys1
            first_goals = match.home_goals if first_home else match.away_goals
            second_goals = match.away_goals if first_home else match.home_goals
            assert first_goals is not None and second_goals is not None
            first_wins += first_goals > second_goals
            second_wins += first_goals < second_goals
            draws += first_goals == second_goals
        return {
            "team1": self.display_team(next(iter(keys1))) if keys1 else team1,
            "team2": self.display_team(next(iter(keys2))) if keys2 else team2,
            "matches": len(matches), "team1_wins": first_wins,
            "team2_wins": second_wins, "draws": draws,
            "results": [match.to_dict() for match in matches],
        }

    def search_players(
        self, *, name: str | None = None, nationality: str | None = None,
        club: str | None = None, position: str | None = None,
        min_overall: int | None = None, limit: int = 50,
    ) -> list[Player]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        name_key, nationality_key = normalize_text(name), normalize_text(nationality)
        club_key, position_key = normalize_team(club), normalize_text(position)
        result = [
            player for player in self.players
            if (not name_key or name_key in normalize_text(player.name))
            and (not nationality_key or nationality_key in normalize_text(player.nationality))
            and (
                not club_key
                or bool(normalize_team(player.club))
                and (club_key in normalize_team(player.club) or normalize_team(player.club) in club_key)
            )
            and (not position_key or position_key in normalize_text(player.position))
            and (min_overall is None or (player.overall or 0) >= min_overall)
        ]
        result.sort(key=lambda p: (p.overall or -1, p.potential or -1, p.name), reverse=True)
        return result[:limit]

    def standings(self, season: int, competition: str = "Brasileirão", limit: int = 100) -> list[dict[str, Any]]:
        matches = self.find_matches(season=season, competition=competition, limit=1000)
        table: dict[str, dict[str, int]] = defaultdict(lambda: {
            "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "points": 0,
        })
        for match in matches:
            if not match.played:
                continue
            home, away = table[match.home_key], table[match.away_key]
            hg, ag = match.home_goals, match.away_goals
            assert hg is not None and ag is not None
            for row in (home, away):
                row["played"] += 1
            home["goals_for"] += hg; home["goals_against"] += ag
            away["goals_for"] += ag; away["goals_against"] += hg
            if hg > ag:
                home["wins"] += 1; home["points"] += 3; away["losses"] += 1
            elif hg < ag:
                away["wins"] += 1; away["points"] += 3; home["losses"] += 1
            else:
                home["draws"] += 1; away["draws"] += 1
                home["points"] += 1; away["points"] += 1
        rows = []
        for key, stats in table.items():
            row: dict[str, Any] = {"team": self.display_team(key), **stats}
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
            rows.append(row)
        rows.sort(key=lambda r: (r["points"], r["goal_difference"], r["goals_for"], r["wins"]), reverse=True)
        for position, row in enumerate(rows[:limit], 1):
            row["position"] = position
        return rows[:limit]

    def aggregate_statistics(
        self, *, competition: str | None = None, season: int | None = None,
    ) -> dict[str, Any]:
        matches = self.find_matches(competition=competition, season=season, limit=1000)
        played = [match for match in matches if match.played]
        goals = sum((m.home_goals or 0) + (m.away_goals or 0) for m in played)
        home_wins = sum((m.home_goals or 0) > (m.away_goals or 0) for m in played)
        away_wins = sum((m.home_goals or 0) < (m.away_goals or 0) for m in played)
        draws = len(played) - home_wins - away_wins
        return {
            "competition": normalize_competition(competition) if competition else None,
            "season": season, "matches": len(played), "goals": goals,
            "goals_per_match": round(goals / len(played), 3) if played else 0.0,
            "home_wins": home_wins, "away_wins": away_wins, "draws": draws,
            "home_win_rate": round(home_wins * 100 / len(played), 1) if played else 0.0,
        }

    def biggest_wins(
        self, *, competition: str | None = None, season: int | None = None, limit: int = 10,
    ) -> list[dict[str, Any]]:
        matches = self.find_matches(competition=competition, season=season, limit=1000)
        played = [m for m in matches if m.played]
        played.sort(
            key=lambda m: (abs((m.home_goals or 0) - (m.away_goals or 0)), (m.home_goals or 0) + (m.away_goals or 0)),
            reverse=True,
        )
        return [match.to_dict() for match in played[:limit]]

    def find_derbies(
        self, *, season: int | None = None, competition: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        matches = self.find_matches(season=season, competition=competition, limit=1000)
        result = []
        for match in matches:
            rivalry = RIVALRIES.get(frozenset((match.home_key, match.away_key)))
            if rivalry:
                row = match.to_dict()
                row["derby"] = rivalry
                result.append(row)
        return result[:limit]

    def team_competitions(self, team: str) -> list[dict[str, Any]]:
        counts = Counter(match.competition for match in self.find_matches(team=team, limit=1000))
        return [{"competition": name, "matches": count} for name, count in counts.most_common()]

    def rank_teams(
        self, *, season: int | None = None, competition: str = "Brasileirão",
        venue: str = "all", metric: str = "points", limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Rank every participating team by a calculated record metric."""
        allowed = {"points", "wins", "win_rate", "goals_for", "goal_difference"}
        if metric not in allowed:
            raise ValueError(f"metric must be one of: {', '.join(sorted(allowed))}")
        matches = self.find_matches(season=season, competition=competition, limit=1000)
        keys = {key for match in matches for key in (match.home_key, match.away_key)}
        rows = [
            self.team_statistics(self.display_team(key), season=season, competition=competition, venue=venue)
            for key in keys
        ]
        rows.sort(key=lambda row: (row[metric], row["goal_difference"], row["goals_for"]), reverse=True)
        for rank, row in enumerate(rows[:limit], 1):
            row["rank"] = rank
        return rows[:limit]

    def club_overview(
        self, team: str, *, season: int | None = None,
        competition: str | None = None, player_limit: int = 20,
    ) -> dict[str, Any]:
        """Join match-derived team performance with FIFA club/player data."""
        return {
            "team": team,
            "statistics": self.team_statistics(team, season=season, competition=competition),
            "competitions": self.team_competitions(team),
            "players": [
                player.to_dict() for player in self.search_players(club=team, limit=player_limit)
            ],
        }

    def dataset_summary(self) -> dict[str, Any]:
        return {
            "data_directory": str(self.data_dir), "files": dict(self.raw_row_counts),
            "raw_match_rows": sum(v for k, v in self.raw_row_counts.items() if k != "fifa_data.csv"),
            "unique_matches": len(self.matches), "players": len(self.players),
            "teams": len(self._matches_by_team),
            "competitions": sorted({match.competition for match in self.matches}),
            "date_range": {
                "start": min(m.date for m in self.matches if m.date).isoformat(),
                "end": max(m.date for m in self.matches if m.date).isoformat(),
            },
        }
