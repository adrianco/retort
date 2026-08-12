"""CSV ingestion and indexed access to all six bundled datasets."""

from __future__ import annotations

import csv
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from .models import Match, Player
from .normalize import normalize_team_name, parse_date, safe_float, safe_int


MATCH_FILES = (
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
)
PLAYER_FILE = "fifa_data.csv"


class SoccerRepository:
    """Load once, then answer read-only queries from memory."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        package_default = Path(__file__).resolve().parent.parent / "data" / "kaggle"
        working_default = Path.cwd() / "data" / "kaggle"
        configured = data_dir or os.environ.get("BRAZILIAN_SOCCER_DATA_DIR")
        default = working_default if working_default.is_dir() else package_default
        self.data_dir = Path(configured or default).expanduser().resolve()
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self.matches_by_team: dict[str, list[Match]] = defaultdict(list)
        self.source_counts: Counter[str] = Counter()
        self.skipped_rows: Counter[str] = Counter()
        self._load_all()

    def _rows(self, filename: str) -> Iterable[dict[str, str]]:
        path = self.data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Required dataset not found: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)

    def _append_match(self, match: Match) -> None:
        self.matches.append(match)
        self.matches_by_team[match.home_key].append(match)
        if match.away_key != match.home_key:
            self.matches_by_team[match.away_key].append(match)
        self.source_counts[match.source] += 1

    def _make_match(
        self,
        *,
        date: str,
        season: object,
        competition: str,
        home: str,
        away: str,
        home_goals: object,
        away_goals: object,
        source: str,
        round_: object = None,
        stage: object = None,
        venue: object = None,
        statistics: dict[str, float] | None = None,
    ) -> Match:
        parsed_date = parse_date(date)
        parsed_season = safe_int(season) or parsed_date.year
        home_score, away_score = safe_int(home_goals), safe_int(away_goals)
        if home_score is None or away_score is None:
            raise ValueError("Match has no final score")
        return Match(
            date=parsed_date,
            season=parsed_season,
            competition=competition,
            home_team=home.strip(),
            away_team=away.strip(),
            home_key=normalize_team_name(home),
            away_key=normalize_team_name(away),
            home_goals=home_score,
            away_goals=away_score,
            source=source,
            round=str(round_).strip() if round_ not in (None, "") else None,
            stage=str(stage).strip() if stage not in (None, "") else None,
            venue=str(venue).strip() if venue not in (None, "") else None,
            statistics=statistics or {},
        )

    def _load_matches(self) -> None:
        loaders = {
            "Brasileirao_Matches.csv": self._load_brasileirao,
            "Brazilian_Cup_Matches.csv": self._load_cup,
            "Libertadores_Matches.csv": self._load_libertadores,
            "BR-Football-Dataset.csv": self._load_extended,
            "novo_campeonato_brasileiro.csv": self._load_historical,
        }
        for filename, loader in loaders.items():
            for row in self._rows(filename):
                try:
                    self._append_match(loader(row, filename))
                except (ValueError, TypeError, KeyError):
                    self.skipped_rows[filename] += 1
        self.matches.sort(key=lambda match: match.date, reverse=True)
        for matches in self.matches_by_team.values():
            matches.sort(key=lambda match: match.date, reverse=True)

    def _load_brasileirao(self, row: dict[str, str], source: str) -> Match:
        return self._make_match(date=row["datetime"], season=row["season"], competition="Brasileirão Série A", home=row["home_team"], away=row["away_team"], home_goals=row["home_goal"], away_goals=row["away_goal"], round_=row["round"], source=source)

    def _load_cup(self, row: dict[str, str], source: str) -> Match:
        return self._make_match(date=row["datetime"], season=row["season"], competition="Copa do Brasil", home=row["home_team"], away=row["away_team"], home_goals=row["home_goal"], away_goals=row["away_goal"], round_=row["round"], source=source)

    def _load_libertadores(self, row: dict[str, str], source: str) -> Match:
        return self._make_match(date=row["datetime"], season=row["season"], competition="Copa Libertadores", home=row["home_team"], away=row["away_team"], home_goals=row["home_goal"], away_goals=row["away_goal"], stage=row["stage"], source=source)

    def _load_extended(self, row: dict[str, str], source: str) -> Match:
        stats = {}
        for column in ("home_corner", "away_corner", "home_attack", "away_attack", "home_shots", "away_shots", "total_corners"):
            value = safe_float(row.get(column))
            if value is not None:
                stats[column] = value
        return self._make_match(date=row["date"], season=None, competition=row["tournament"], home=row["home"], away=row["away"], home_goals=row["home_goal"], away_goals=row["away_goal"], source=source, statistics=stats)

    def _load_historical(self, row: dict[str, str], source: str) -> Match:
        return self._make_match(date=row["Data"], season=row["Ano"], competition="Brasileirão Série A", home=row["Equipe_mandante"], away=row["Equipe_visitante"], home_goals=row["Gols_mandante"], away_goals=row["Gols_visitante"], round_=row["Rodada"], venue=row.get("Arena"), source=source)

    def _load_players(self) -> None:
        attribute_columns = (
            "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
            "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
            "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
            "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
            "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
            "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving",
            "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
        )
        for row in self._rows(PLAYER_FILE):
            player_id = safe_int(row.get("ID"))
            name = (row.get("Name") or "").strip()
            if player_id is None or not name:
                self.skipped_rows[PLAYER_FILE] += 1
                continue
            attributes = {column: value for column in attribute_columns if (value := safe_int(row.get(column))) is not None}
            self.players.append(Player(
                player_id=player_id,
                name=name,
                age=safe_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=safe_int(row.get("Overall")),
                potential=safe_int(row.get("Potential")),
                club=(row.get("Club") or "").strip(),
                position=(row.get("Position") or "").strip(),
                jersey_number=safe_int(row.get("Jersey Number")),
                height=(row.get("Height") or "").strip(),
                weight=(row.get("Weight") or "").strip(),
                attributes=attributes,
            ))
        self.players.sort(key=lambda player: (player.overall or -1, player.name), reverse=True)
        self.source_counts[PLAYER_FILE] = len(self.players)

    def _load_all(self) -> None:
        self._load_matches()
        self._load_players()

    def status(self) -> dict[str, object]:
        required = (*MATCH_FILES, PLAYER_FILE)
        return {
            "data_directory": str(self.data_dir),
            "all_datasets_loaded": all(name in self.source_counts for name in required),
            "total_matches": len(self.matches),
            "total_players": len(self.players),
            "rows_by_source": {name: self.source_counts.get(name, 0) for name in required},
            "skipped_rows": dict(self.skipped_rows),
        }
