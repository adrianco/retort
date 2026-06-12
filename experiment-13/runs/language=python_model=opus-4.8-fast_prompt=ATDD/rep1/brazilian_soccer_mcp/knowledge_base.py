"""
Context
=======
The query engine for the Brazilian Soccer MCP server.

``KnowledgeBase`` holds the loaded matches and players in memory and answers the
domain questions the MCP tools expose:
  * find_matches          — by team, opponent, competition, season, date range,
                            home/away; with a head-to-head summary for two teams.
  * team_record           — wins/draws/losses, goals for/against, win rate.
  * head_to_head          — meetings and win tallies between two teams.
  * search_players        — by name, nationality, club, position, min rating.
  * standings             — a league table computed from match results.
  * competition_stats     — goals/match, home & away win rates, biggest wins.

All team matching goes through ``normalize`` keys, so callers can use any spelling
(with or without state/country suffixes or accents). Competition matching is
accent/case-insensitive substring matching ("libertadores" -> "Copa
Libertadores"). Everything is computed from the provided data only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import loader
from .models import Match, Player
from .normalize import key, strip_accents, team_key


class KnowledgeBase:
    def __init__(self, matches: list[Match], players: list[Player]):
        self.matches = matches
        self.players = players

    @classmethod
    def from_directory(cls, data_dir) -> "KnowledgeBase":
        path = Path(data_dir)
        return cls(loader.load_matches(path), loader.load_players(path))

    # -- internal helpers ---------------------------------------------------
    @staticmethod
    def _competition_matches(match: Match, query: Optional[str]) -> bool:
        if not query:
            return True
        return strip_accents(query).lower() in strip_accents(match.competition).lower()

    @staticmethod
    def _involves(match: Match, k: str) -> Optional[str]:
        """Return 'home', 'away' or None for whether team key ``k`` plays."""
        if team_key(match.home_team) == k:
            return "home"
        if team_key(match.away_team) == k:
            return "away"
        return None

    # -- match queries ------------------------------------------------------
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        home_away: Optional[str] = None,
    ) -> list[Match]:
        team_k = key(team) if team else None
        opp_k = key(opponent) if opponent else None
        results = []
        for m in self.matches:
            if not self._competition_matches(m, competition):
                continue
            if season is not None and m.season != season:
                continue
            side = self._involves(m, team_k) if team_k else "any"
            if team_k and side is None:
                continue
            if home_away and side != home_away:
                continue
            if opp_k:
                other = m.away_team if side == "home" else m.home_team
                if team_key(other) != opp_k:
                    continue
            if start_date and (m.date is None or m.date < start_date):
                continue
            if end_date and (m.date is None or m.date > end_date):
                continue
            results.append(m)
        results.sort(key=lambda x: (x.date or "", x.competition))
        return results

    # -- team queries -------------------------------------------------------
    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        home_away: Optional[str] = None,
    ) -> dict:
        team_k = key(team)
        wins = draws = losses = gf = ga = played = 0
        for m in self.find_matches(team=team, competition=competition,
                                   season=season, home_away=home_away):
            if not m.has_score:
                continue
            side = self._involves(m, team_k)
            if side == "home":
                scored, conceded = m.home_goal, m.away_goal
            else:
                scored, conceded = m.away_goal, m.home_goal
            played += 1
            gf += scored
            ga += conceded
            if scored > conceded:
                wins += 1
            elif scored < conceded:
                losses += 1
            else:
                draws += 1
        win_rate = round(100.0 * wins / played, 1) if played else 0.0
        return {
            "team": team,
            "season": season,
            "competition": competition,
            "home_away": home_away,
            "matches": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "win_rate": win_rate,
        }

    def head_to_head(
        self,
        team1: str,
        team2: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        k1 = key(team1)
        meetings = self.find_matches(team=team1, opponent=team2,
                                     competition=competition, season=season)
        t1_wins = t2_wins = draws = 0
        for m in meetings:
            if not m.has_score:
                continue
            side = self._involves(m, k1)
            if side == "home":
                s1, s2 = m.home_goal, m.away_goal
            else:
                s1, s2 = m.away_goal, m.home_goal
            if s1 > s2:
                t1_wins += 1
            elif s1 < s2:
                t2_wins += 1
            else:
                draws += 1
        return {
            "team1": team1,
            "team2": team2,
            "total_matches": len(meetings),
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "matches": [m.as_dict() for m in meetings],
        }

    # -- player queries -----------------------------------------------------
    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 25,
    ) -> list[Player]:
        name_k = key(name) if name else None
        nat_k = key(nationality) if nationality else None
        club_k = key(club) if club else None
        pos_k = key(position) if position else None
        results = []
        for p in self.players:
            if name_k and name_k not in key(p.name):
                continue
            if nat_k and key(p.nationality) != nat_k:
                continue
            if club_k and club_k not in key(p.club):
                continue
            if pos_k and key(p.position) != pos_k:
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)
        results.sort(key=lambda x: (-(x.overall or 0), x.name))
        return results[:limit] if limit else results

    # -- competition queries ------------------------------------------------
    def standings(self, season: int, competition: str = "Brasileirão") -> dict:
        table: dict[str, dict] = {}

        def row(team: str) -> dict:
            return table.setdefault(team, {
                "team": team, "points": 0, "played": 0, "wins": 0,
                "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0,
            })

        for m in self.find_matches(competition=competition, season=season):
            if not m.has_score:
                continue
            home, away = row(m.home_team), row(m.away_team)
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += m.home_goal
            home["goals_against"] += m.away_goal
            away["goals_for"] += m.away_goal
            away["goals_against"] += m.home_goal
            if m.home_goal > m.away_goal:
                home["points"] += 3
                home["wins"] += 1
                away["losses"] += 1
            elif m.home_goal < m.away_goal:
                away["points"] += 3
                away["wins"] += 1
                home["losses"] += 1
            else:
                home["points"] += 1
                away["points"] += 1
                home["draws"] += 1
                away["draws"] += 1

        rows = list(table.values())
        for r in rows:
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
        rows.sort(key=lambda r: (-r["points"], -r["goal_difference"],
                                 -r["goals_for"], r["team"]))
        for i, r in enumerate(rows, start=1):
            r["position"] = i
        return {
            "season": season,
            "competition": competition,
            "standings": rows,
            "champion": rows[0]["team"] if rows else None,
        }

    # -- statistical analysis ----------------------------------------------
    def competition_stats(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        biggest_n: int = 5,
    ) -> dict:
        scored = [m for m in self.find_matches(competition=competition, season=season)
                  if m.has_score]
        total = len(scored)
        if total == 0:
            return {
                "competition": competition,
                "season": season,
                "matches": 0,
                "average_goals_per_match": 0.0,
                "home_win_rate": 0.0,
                "away_win_rate": 0.0,
                "draw_rate": 0.0,
                "biggest_wins": [],
            }
        goals = sum(m.total_goals for m in scored)
        home_wins = sum(1 for m in scored if m.home_goal > m.away_goal)
        away_wins = sum(1 for m in scored if m.away_goal > m.home_goal)
        draws = total - home_wins - away_wins
        biggest = sorted(scored, key=lambda m: (-m.goal_margin, m.date or ""))
        return {
            "competition": competition,
            "season": season,
            "matches": total,
            "average_goals_per_match": round(goals / total, 2),
            "home_win_rate": round(100.0 * home_wins / total, 1),
            "away_win_rate": round(100.0 * away_wins / total, 1),
            "draw_rate": round(100.0 * draws / total, 1),
            "biggest_wins": [m.as_dict() for m in biggest[:biggest_n]],
        }
