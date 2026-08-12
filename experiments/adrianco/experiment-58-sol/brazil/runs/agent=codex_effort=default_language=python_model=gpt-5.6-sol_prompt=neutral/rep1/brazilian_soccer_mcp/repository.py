"""CSV adapters and in-memory repository for the bundled datasets."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .models import Match, Player
from .normalize import fold_text, normalize_team, parse_date, parse_int, team_matches

MATCH_FILES = (
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
)
PLAYER_FILE = "fifa_data.csv"


class SoccerRepository:
    """Load all six CSVs once and provide fast, normalized filtering."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent.parent / "data" / "kaggle"
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self._team_index: dict[str, list[Match]] = defaultdict(list)
        self._load()

    def _rows(self, filename: str) -> Iterable[dict[str, str]]:
        path = self.data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Required dataset not found: {path}")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)

    def _load(self) -> None:
        loaders = {
            "Brasileirao_Matches.csv": self._load_brasileirao,
            "Brazilian_Cup_Matches.csv": self._load_copa,
            "Libertadores_Matches.csv": self._load_libertadores,
            "BR-Football-Dataset.csv": self._load_extended,
            "novo_campeonato_brasileiro.csv": self._load_historical,
        }
        for filename, loader in loaders.items():
            self.matches.extend(loader(filename))
        self.players = list(self._load_players(PLAYER_FILE))
        for match in self.matches:
            self._team_index[normalize_team(match.home_team)].append(match)
            self._team_index[normalize_team(match.away_team)].append(match)

    def _make_match(
        self, *, filename: str, date_value: str, home: str, away: str,
        home_goals: str, away_goals: str, season: str | int | None,
        competition: str, round_or_stage: str | None = None,
        metadata: dict | None = None,
    ) -> Match | None:
        hg, ag = parse_int(home_goals), parse_int(away_goals)
        if hg is None or ag is None or not home or not away or not date_value:
            return None
        match_date = parse_date(date_value)
        parsed_season = parse_int(season) or match_date.year
        return Match(match_date, home.strip(), away.strip(), hg, ag, parsed_season,
                     competition.strip(), filename, round_or_stage or None, metadata or {})

    def _valid(self, matches: Iterable[Match | None]) -> Iterable[Match]:
        return (match for match in matches if match is not None)

    def _load_brasileirao(self, filename: str) -> Iterable[Match]:
        return self._valid(self._make_match(
            filename=filename, date_value=r["datetime"], home=r["home_team"], away=r["away_team"],
            home_goals=r["home_goal"], away_goals=r["away_goal"], season=r["season"],
            competition="Brasileirão Série A", round_or_stage=f"Round {r['round']}",
            metadata={"home_state": r["home_team_state"], "away_state": r["away_team_state"]},
        ) for r in self._rows(filename))

    def _load_copa(self, filename: str) -> Iterable[Match]:
        return self._valid(self._make_match(
            filename=filename, date_value=r["datetime"], home=r["home_team"], away=r["away_team"],
            home_goals=r["home_goal"], away_goals=r["away_goal"], season=r["season"],
            competition="Copa do Brasil", round_or_stage=f"Round {r['round']}",
        ) for r in self._rows(filename))

    def _load_libertadores(self, filename: str) -> Iterable[Match]:
        return self._valid(self._make_match(
            filename=filename, date_value=r["datetime"], home=r["home_team"], away=r["away_team"],
            home_goals=r["home_goal"], away_goals=r["away_goal"], season=r["season"],
            competition="Copa Libertadores", round_or_stage=r["stage"],
        ) for r in self._rows(filename))

    def _load_extended(self, filename: str) -> Iterable[Match]:
        numeric = ("home_corner", "away_corner", "home_attack", "away_attack", "home_shots", "away_shots", "total_corners")
        return self._valid(self._make_match(
            filename=filename, date_value=r["date"], home=r["home"], away=r["away"],
            home_goals=r["home_goal"], away_goals=r["away_goal"], season=None,
            competition=r["tournament"],
            metadata={key: parse_int(r.get(key)) for key in numeric},
        ) for r in self._rows(filename))

    def _load_historical(self, filename: str) -> Iterable[Match]:
        return self._valid(self._make_match(
            filename=filename, date_value=r["Data"], home=r["Equipe_mandante"], away=r["Equipe_visitante"],
            home_goals=r["Gols_mandante"], away_goals=r["Gols_visitante"], season=r["Ano"],
            competition="Brasileirão Série A", round_or_stage=f"Round {r['Rodada']}",
            metadata={"home_state": r["Mandante_UF"], "away_state": r["Visitante_UF"], "stadium": r["Arena"]},
        ) for r in self._rows(filename))

    def _load_players(self, filename: str) -> Iterable[Player]:
        skills = ("Crossing", "Finishing", "Dribbling", "ShortPassing", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "ShotPower", "Stamina")
        for row in self._rows(filename):
            player_id = parse_int(row.get("ID"))
            if player_id is None or not row.get("Name"):
                continue
            yield Player(
                player_id, row["Name"].strip(), parse_int(row.get("Age")), row.get("Nationality", "").strip(),
                parse_int(row.get("Overall")), parse_int(row.get("Potential")), row.get("Club", "").strip(),
                row.get("Position", "").strip(), parse_int(row.get("Jersey Number")),
                {skill: value for skill in skills if (value := parse_int(row.get(skill))) is not None},
            )

    @property
    def dataset_counts(self) -> dict[str, int]:
        counts = {filename: 0 for filename in MATCH_FILES}
        for match in self.matches:
            counts[match.source] += 1
        counts[PLAYER_FILE] = len(self.players)
        return counts

    def matches_for_team(self, team: str) -> list[Match]:
        exact = self._team_index.get(normalize_team(team))
        if exact is not None:
            return list(exact)
        return [m for m in self.matches if team_matches(m.home_team, team) or team_matches(m.away_team, team)]

    def player_search(self, name: str | None = None, nationality: str | None = None,
                      club: str | None = None, position: str | None = None) -> list[Player]:
        filters = {"name": fold_text(name), "nationality": fold_text(nationality),
                   "club": fold_text(club), "position": fold_text(position)}
        results = []
        for player in self.players:
            if filters["name"] and filters["name"] not in fold_text(player.name):
                continue
            if filters["nationality"] and filters["nationality"] not in fold_text(player.nationality):
                continue
            if filters["club"] and filters["club"] not in fold_text(player.club):
                continue
            if filters["position"] and filters["position"] not in fold_text(player.position):
                continue
            results.append(player)
        return results
