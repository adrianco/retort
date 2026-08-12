"""Application services for match, team, player, and competition queries."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Iterable

from .models import Match
from .normalize import fold_text, normalize_team, parse_date, team_matches
from .repository import SoccerRepository

_BRASILEIRAO_NAMES = {"brasileirao", "brasileirao serie a", "campeonato brasileiro", "serie a"}


def _competition_group(value: str) -> str:
    key = fold_text(value)
    if key in _BRASILEIRAO_NAMES:
        return "brasileirao serie a"
    if "libertadores" in key:
        return "copa libertadores"
    return key


class SoccerService:
    def __init__(self, repository: SoccerRepository | None = None) -> None:
        self.repository = repository or SoccerRepository()
        # Several CSVs overlap. Pick the most complete source for each
        # competition-season so aggregate results never double/triple count.
        coverage: dict[tuple[int, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for match in self.repository.matches:
            coverage[(match.season, _competition_group(match.competition))][match.source] += 1
        self._preferred_source = {
            key: max(source_counts, key=source_counts.get)
            for key, source_counts in coverage.items()
        }

    @staticmethod
    def _competition_matches(actual: str, requested: str | None) -> bool:
        if not requested:
            return True
        query, value = fold_text(requested), fold_text(actual)
        if query in _BRASILEIRAO_NAMES:
            return value in _BRASILEIRAO_NAMES
        if query == "libertadores":
            return "libertadores" in value
        return query in value

    def _bounded(self, matches: Iterable[Match], *, season: int | None = None,
                 competition: str | None = None, start_date: str | None = None,
                 end_date: str | None = None) -> list[Match]:
        start = parse_date(start_date) if start_date else date.min
        end = parse_date(end_date) if end_date else date.max
        if start > end:
            raise ValueError("start_date must be on or before end_date")
        return [m for m in matches if (season is None or m.season == season)
                and self._competition_matches(m.competition, competition)
                and start <= m.date <= end
                and m.source == self._preferred_source[(m.season, _competition_group(m.competition))]]

    def search_matches(self, team: str | None = None, opponent: str | None = None,
                       competition: str | None = None, season: int | None = None,
                       start_date: str | None = None, end_date: str | None = None,
                       stage: str | None = None, limit: int = 50) -> dict[str, Any]:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        candidates = self.repository.matches_for_team(team) if team else self.repository.matches
        matches = self._bounded(candidates, season=season, competition=competition,
                                start_date=start_date, end_date=end_date)
        if opponent:
            matches = [m for m in matches if team_matches(m.home_team, opponent) or team_matches(m.away_team, opponent)]
        if stage:
            stage_key = fold_text(stage)
            matches = [m for m in matches if stage_key in fold_text(m.round_or_stage)]
        matches.sort(key=lambda m: m.date, reverse=True)
        return {"count": len(matches), "returned": min(len(matches), limit),
                "matches": [m.to_dict() for m in matches[:limit]]}

    def team_statistics(self, team: str, season: int | None = None,
                        competition: str | None = None, venue: str = "all") -> dict[str, Any]:
        if venue not in {"all", "home", "away"}:
            raise ValueError("venue must be one of: all, home, away")
        matches = self._bounded(self.repository.matches_for_team(team), season=season, competition=competition)
        if venue == "home":
            matches = [m for m in matches if team_matches(m.home_team, team)]
        elif venue == "away":
            matches = [m for m in matches if team_matches(m.away_team, team)]
        wins = draws = losses = goals_for = goals_against = 0
        for match in matches:
            home = team_matches(match.home_team, team)
            scored, conceded = ((match.home_goals, match.away_goals) if home
                                else (match.away_goals, match.home_goals))
            goals_for += scored
            goals_against += conceded
            if scored > conceded:
                wins += 1
            elif scored < conceded:
                losses += 1
            else:
                draws += 1
        total = len(matches)
        return {"team": team, "season": season, "competition": competition, "venue": venue,
                "matches": total, "wins": wins, "draws": draws, "losses": losses,
                "goals_for": goals_for, "goals_against": goals_against,
                "goal_difference": goals_for - goals_against,
                "points": wins * 3 + draws, "win_rate": round(wins * 100 / total, 1) if total else 0.0}

    def head_to_head(self, team1: str, team2: str, season: int | None = None,
                     competition: str | None = None, limit: int = 50) -> dict[str, Any]:
        candidates = self._bounded(self.repository.matches_for_team(team1), season=season, competition=competition)
        matches = [m for m in candidates if team_matches(m.home_team, team2) or team_matches(m.away_team, team2)]
        team1_wins = team2_wins = draws = 0
        for match in matches:
            team1_home = team_matches(match.home_team, team1)
            first, second = ((match.home_goals, match.away_goals) if team1_home
                             else (match.away_goals, match.home_goals))
            if first > second:
                team1_wins += 1
            elif second > first:
                team2_wins += 1
            else:
                draws += 1
        matches.sort(key=lambda m: m.date, reverse=True)
        return {"team1": team1, "team2": team2, "matches": len(matches),
                "team1_wins": team1_wins, "team2_wins": team2_wins, "draws": draws,
                "results": [m.to_dict() for m in matches[:limit]]}

    def standings(self, season: int, competition: str = "Brasileirão", limit: int = 30) -> dict[str, Any]:
        matches = self._bounded(self.repository.matches, season=season, competition=competition)
        table: dict[str, dict[str, Any]] = {}
        display: dict[str, str] = {}
        for match in matches:
            home, away = normalize_team(match.home_team), normalize_team(match.away_team)
            display.setdefault(home, match.home_team)
            display.setdefault(away, match.away_team)
            for key in (home, away):
                table.setdefault(key, {"played": 0, "wins": 0, "draws": 0, "losses": 0,
                                       "goals_for": 0, "goals_against": 0, "points": 0})
            hs, aws = table[home], table[away]
            hs["played"] += 1; aws["played"] += 1
            hs["goals_for"] += match.home_goals; hs["goals_against"] += match.away_goals
            aws["goals_for"] += match.away_goals; aws["goals_against"] += match.home_goals
            if match.home_goals > match.away_goals:
                hs["wins"] += 1; hs["points"] += 3; aws["losses"] += 1
            elif match.away_goals > match.home_goals:
                aws["wins"] += 1; aws["points"] += 3; hs["losses"] += 1
            else:
                hs["draws"] += 1; aws["draws"] += 1; hs["points"] += 1; aws["points"] += 1
        rows = []
        for key, stats in table.items():
            row = {"team": display[key], **stats,
                   "goal_difference": stats["goals_for"] - stats["goals_against"]}
            rows.append(row)
        rows.sort(key=lambda r: (r["points"], r["goal_difference"], r["goals_for"]), reverse=True)
        for position, row in enumerate(rows, 1):
            row["position"] = position
        return {"season": season, "competition": competition, "match_count": len(matches),
                "standings": rows[:limit]}

    def competition_statistics(self, competition: str | None = None,
                               season: int | None = None) -> dict[str, Any]:
        matches = self._bounded(self.repository.matches, season=season, competition=competition)
        goals = sum(m.home_goals + m.away_goals for m in matches)
        home_wins = sum(m.home_goals > m.away_goals for m in matches)
        away_wins = sum(m.away_goals > m.home_goals for m in matches)
        draws = len(matches) - home_wins - away_wins
        total = len(matches)
        return {"competition": competition, "season": season, "matches": total, "goals": goals,
                "goals_per_match": round(goals / total, 2) if total else 0.0,
                "home_wins": home_wins, "away_wins": away_wins, "draws": draws,
                "home_win_rate": round(home_wins * 100 / total, 1) if total else 0.0}

    def biggest_wins(self, competition: str | None = None, season: int | None = None,
                     limit: int = 10) -> dict[str, Any]:
        matches = self._bounded(self.repository.matches, season=season, competition=competition)
        matches.sort(key=lambda m: (abs(m.home_goals - m.away_goals), m.home_goals + m.away_goals), reverse=True)
        return {"count": len(matches), "matches": [
            {**m.to_dict(), "margin": abs(m.home_goals - m.away_goals)} for m in matches[:limit]
        ]}

    def search_players(self, name: str | None = None, nationality: str | None = None,
                       club: str | None = None, position: str | None = None,
                       min_overall: int | None = None, limit: int = 50) -> dict[str, Any]:
        players = self.repository.player_search(name, nationality, club, position)
        if min_overall is not None:
            players = [p for p in players if p.overall is not None and p.overall >= min_overall]
        players.sort(key=lambda p: (p.overall or -1, p.potential or -1), reverse=True)
        return {"count": len(players), "returned": min(len(players), limit),
                "players": [p.to_dict() for p in players[:limit]]}

    def team_competitions(self, team: str, season: int | None = None) -> dict[str, Any]:
        matches = self._bounded(self.repository.matches_for_team(team), season=season)
        counts: dict[str, int] = defaultdict(int)
        for match in matches:
            counts[match.competition] += 1
        return {"team": team, "season": season, "competitions": [
            {"competition": name, "matches": count} for name, count in sorted(counts.items())
        ]}

    def dataset_summary(self) -> dict[str, Any]:
        return {"datasets": self.repository.dataset_counts,
                "total_matches": len(self.repository.matches), "total_players": len(self.repository.players)}
