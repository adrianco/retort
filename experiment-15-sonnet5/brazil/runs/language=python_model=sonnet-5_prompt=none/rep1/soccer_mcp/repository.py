"""Query engine over the unified match/player knowledge graph."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .data_loader import SoccerData, load_all
from .models import Match, Player
from .team_names import normalize_team


def _parse_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(value)


@dataclass
class TeamRecord:
    team: str
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def win_rate(self) -> float:
        return round(self.wins / self.matches, 4) if self.matches else 0.0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    def to_dict(self) -> dict[str, Any]:
        return {
            "team": self.team,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "win_rate": self.win_rate,
        }


class SoccerRepository:
    """In-memory knowledge graph over matches and players.

    All lookups key on normalize_team()'s canonical key so that queries can
    be given any spelling/suffix variant found in the source CSVs.
    """

    def __init__(self, data: SoccerData):
        self._matches: list[Match] = data.matches
        self._players: list[Player] = data.players
        self._by_team: dict[str, list[Match]] = defaultdict(list)
        for m in self._matches:
            self._by_team[m.home_team_key].append(m)
            self._by_team[m.away_team_key].append(m)

    @classmethod
    def from_data_dir(cls, data_dir: Path | str | None = None) -> "SoccerRepository":
        return cls(load_all(data_dir))

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    def list_teams(self, query: str | None = None) -> list[str]:
        names = {m.home_team_key: m.home_team for m in self._matches}
        names.update({m.away_team_key: m.away_team for m in self._matches})
        if query:
            q_key, _ = normalize_team(query)
            names = {k: v for k, v in names.items() if q_key in k}
        return sorted(names.values())

    def list_competitions(self) -> list[str]:
        return sorted({m.competition for m in self._matches})

    def list_seasons(self, competition: str | None = None) -> list[int]:
        seasons = {
            m.season
            for m in self._matches
            if m.season is not None and (competition is None or m.competition == competition)
        }
        return sorted(seasons)

    # ------------------------------------------------------------------
    # Match queries
    # ------------------------------------------------------------------

    def find_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        venue: str | None = None,
        limit: int | None = 50,
    ) -> list[Match]:
        """venue: 'home', 'away', or None for either."""
        team_key = normalize_team(team)[0] if team else None
        opponent_key = normalize_team(opponent)[0] if opponent else None
        date_from_p = _parse_date(date_from)
        date_to_p = _parse_date(date_to)

        pool = self._by_team[team_key] if team_key else self._matches
        results = []
        for m in pool:
            if team_key:
                if venue == "home" and m.home_team_key != team_key:
                    continue
                if venue == "away" and m.away_team_key != team_key:
                    continue
                if not m.involves(team_key):
                    continue
            if opponent_key:
                if team_key:
                    if m.opponent_key(team_key) != opponent_key:
                        continue
                elif opponent_key not in (m.home_team_key, m.away_team_key):
                    continue
            if competition and m.competition != competition:
                continue
            if season and m.season != season:
                continue
            if date_from_p and (m.match_date is None or m.match_date < date_from_p):
                continue
            if date_to_p and (m.match_date is None or m.match_date > date_to_p):
                continue
            results.append(m)

        results.sort(key=lambda m: m.match_date or date.min)
        if limit:
            results = results[-limit:]
        return results

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: str | None = None,
        season: int | None = None,
    ) -> dict[str, Any]:
        key_a, name_a = normalize_team(team_a)
        key_b, name_b = normalize_team(team_b)
        matches = [
            m
            for m in self._by_team[key_a]
            if m.opponent_key(key_a) == key_b
            and (competition is None or m.competition == competition)
            and (season is None or m.season == season)
        ]
        matches.sort(key=lambda m: m.match_date or date.min)

        wins_a = wins_b = draws = goals_a = goals_b = 0
        for m in matches:
            if m.home_team_key == key_a:
                ga, gb = m.home_goal, m.away_goal
            else:
                ga, gb = m.away_goal, m.home_goal
            goals_a += ga
            goals_b += gb
            if ga > gb:
                wins_a += 1
            elif gb > ga:
                wins_b += 1
            else:
                draws += 1

        return {
            "team_a": name_a,
            "team_b": name_b,
            "matches_found": len(matches),
            "wins_a": wins_a,
            "wins_b": wins_b,
            "draws": draws,
            "goals_a": goals_a,
            "goals_b": goals_b,
            "matches": [m.to_dict() for m in matches],
        }

    def team_record(
        self,
        team: str,
        competition: str | None = None,
        season: int | None = None,
        venue: str | None = None,
    ) -> TeamRecord:
        """venue: 'home', 'away', or None for both."""
        key, name = normalize_team(team)
        matches = self.find_matches(
            team=team, competition=competition, season=season, venue=venue, limit=None
        )

        wins = draws = losses = goals_for = goals_against = 0
        for m in matches:
            if m.home_team_key == key:
                gf, ga = m.home_goal, m.away_goal
            else:
                gf, ga = m.away_goal, m.home_goal
            goals_for += gf
            goals_against += ga
            if gf > ga:
                wins += 1
            elif ga > gf:
                losses += 1
            else:
                draws += 1

        return TeamRecord(
            team=name,
            matches=len(matches),
            wins=wins,
            draws=draws,
            losses=losses,
            goals_for=goals_for,
            goals_against=goals_against,
        )

    def standings(
        self, competition: str, season: int, min_matches: int = 1
    ) -> list[TeamRecord]:
        matches = [
            m for m in self._matches if m.competition == competition and m.season == season
        ]
        table: dict[str, TeamRecord] = {}

        def _get(key: str, name: str) -> TeamRecord:
            if key not in table:
                table[key] = TeamRecord(name, 0, 0, 0, 0, 0, 0)
            return table[key]

        for m in matches:
            home = _get(m.home_team_key, m.home_team)
            away = _get(m.away_team_key, m.away_team)
            home.matches += 1
            away.matches += 1
            home.goals_for += m.home_goal
            home.goals_against += m.away_goal
            away.goals_for += m.away_goal
            away.goals_against += m.home_goal
            if m.result == "home_win":
                home.wins += 1
                away.losses += 1
            elif m.result == "away_win":
                away.wins += 1
                home.losses += 1
            else:
                home.draws += 1
                away.draws += 1

        rows = [r for r in table.values() if r.matches >= min_matches]
        rows.sort(key=lambda r: (r.points, r.goal_difference, r.goals_for), reverse=True)
        return rows

    def biggest_wins(
        self,
        competition: str | None = None,
        season: int | None = None,
        n: int = 10,
    ) -> list[Match]:
        pool = [
            m
            for m in self._matches
            if (competition is None or m.competition == competition)
            and (season is None or m.season == season)
        ]
        pool.sort(key=lambda m: m.goal_difference, reverse=True)
        return pool[:n]

    def average_goals(
        self, competition: str | None = None, season: int | None = None
    ) -> dict[str, Any]:
        pool = [
            m
            for m in self._matches
            if (competition is None or m.competition == competition)
            and (season is None or m.season == season)
        ]
        if not pool:
            return {"matches": 0, "average_goals_per_match": 0.0, "home_win_rate": 0.0}
        total_goals = sum(m.home_goal + m.away_goal for m in pool)
        home_wins = sum(1 for m in pool if m.result == "home_win")
        draws = sum(1 for m in pool if m.result == "draw")
        away_wins = sum(1 for m in pool if m.result == "away_win")
        return {
            "matches": len(pool),
            "average_goals_per_match": round(total_goals / len(pool), 3),
            "home_win_rate": round(home_wins / len(pool), 4),
            "draw_rate": round(draws / len(pool), 4),
            "away_win_rate": round(away_wins / len(pool), 4),
        }

    def best_record(
        self,
        competition: str | None = None,
        season: int | None = None,
        venue: str | None = None,
        min_matches: int = 5,
        n: int = 10,
        by: str = "win_rate",
    ) -> list[TeamRecord]:
        """Rank teams by win_rate/points/goal_difference for the given filters."""
        pool = [
            m
            for m in self._matches
            if (competition is None or m.competition == competition)
            and (season is None or m.season == season)
        ]
        table: dict[str, TeamRecord] = {}

        def _get(key: str, name: str) -> TeamRecord:
            if key not in table:
                table[key] = TeamRecord(name, 0, 0, 0, 0, 0, 0)
            return table[key]

        for m in pool:
            if venue in (None, "home"):
                home = _get(m.home_team_key, m.home_team)
                home.matches += 1
                home.goals_for += m.home_goal
                home.goals_against += m.away_goal
                if m.result == "home_win":
                    home.wins += 1
                elif m.result == "away_win":
                    home.losses += 1
                else:
                    home.draws += 1
            if venue in (None, "away"):
                away = _get(m.away_team_key, m.away_team)
                away.matches += 1
                away.goals_for += m.away_goal
                away.goals_against += m.home_goal
                if m.result == "away_win":
                    away.wins += 1
                elif m.result == "home_win":
                    away.losses += 1
                else:
                    away.draws += 1

        rows = [r for r in table.values() if r.matches >= min_matches]
        key_fn = {
            "win_rate": lambda r: r.win_rate,
            "points": lambda r: r.points,
            "goal_difference": lambda r: r.goal_difference,
        }[by]
        rows.sort(key=key_fn, reverse=True)
        return rows[:n]

    # ------------------------------------------------------------------
    # Player queries
    # ------------------------------------------------------------------

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 50,
    ) -> list[Player]:
        results = self._players
        if name:
            needle = name.strip().lower()
            results = [p for p in results if needle in p.name.lower()]
        if nationality:
            needle = nationality.strip().lower()
            results = [p for p in results if p.nationality.lower() == needle]
        if club:
            needle = club.strip().lower()
            results = [p for p in results if needle in p.club.lower()]
        if position:
            needle = position.strip().lower()
            results = [p for p in results if p.position and p.position.lower() == needle]
        if min_overall is not None:
            results = [p for p in results if (p.overall or 0) >= min_overall]
        results = sorted(results, key=lambda p: p.overall or 0, reverse=True)
        return results[:limit]

    def top_players(
        self,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        n: int = 10,
    ) -> list[Player]:
        return self.search_players(
            nationality=nationality, club=club, position=position, limit=n
        )
