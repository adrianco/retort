"""In-memory knowledge graph over Brazilian soccer matches and players.

The graph indexes matches by team and players by name/nationality/club so the
required query categories (match, team, player, competition, statistical) can
be answered quickly and entirely from the provided datasets.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from .loader import load_all
from .models import Match, Player
from .normalize import competition_matches, strip_accents, team_key


@dataclass
class TeamRecord:
    team: str
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return (self.wins / self.matches * 100) if self.matches else 0.0

    def as_dict(self) -> dict:
        return {
            "team": self.team,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_diff": self.goal_diff,
            "points": self.points,
            "win_rate": round(self.win_rate, 1),
        }


def _norm_text(s: str) -> str:
    return strip_accents(s or "").lower().strip()


class SoccerKnowledgeGraph:
    """Holds all data and answers queries."""

    def __init__(self, matches: List[Match], players: List[Player]):
        # Deduplicate identical matches that appear in more than one dataset.
        seen = set()
        self.matches: List[Match] = []
        for m in matches:
            sig = m.signature()
            if sig in seen:
                continue
            seen.add(sig)
            self.matches.append(m)

        self.players: List[Player] = players

        # Indexes.
        self._by_team: Dict[str, List[Match]] = defaultdict(list)
        self._team_display: Dict[str, str] = {}
        for m in self.matches:
            self._by_team[m.home_key].append(m)
            self._by_team[m.away_key].append(m)
            self._team_display.setdefault(m.home_key, m.home)
            self._team_display.setdefault(m.away_key, m.away)

        self._players_by_club: Dict[str, List[Player]] = defaultdict(list)
        for p in self.players:
            self._players_by_club[team_key(p.club)].append(p)

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def from_data_dir(cls, data_dir: Optional[str] = None) -> "SoccerKnowledgeGraph":
        matches, players = load_all(data_dir)
        return cls(matches, players)

    # ------------------------------------------------------------------ #
    # Team / competition helpers
    # ------------------------------------------------------------------ #
    def team_display_name(self, name: str) -> str:
        return self._team_display.get(team_key(name), name)

    def teams(self) -> List[str]:
        return sorted(self._team_display.values())

    def competitions(self) -> List[str]:
        return sorted({m.competition for m in self.matches})

    # ------------------------------------------------------------------ #
    # Match queries
    # ------------------------------------------------------------------ #
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: str = "either",   # 'home' | 'away' | 'either'
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Match]:
        """Return matches filtered by the given criteria, newest first."""
        if team:
            tk = team_key(team)
            pool = self._by_team.get(tk, [])
        else:
            pool = self.matches
            tk = None

        ok_key = team_key(opponent) if opponent else None

        results = []
        for m in pool:
            if tk is not None:
                if venue == "home" and m.home_key != tk:
                    continue
                if venue == "away" and m.away_key != tk:
                    continue
            if ok_key is not None and ok_key not in (m.home_key, m.away_key):
                continue
            if season is not None and m.season != season:
                continue
            if competition and not competition_matches(competition, m.competition):
                continue
            if date_from and (not m.match_date or m.date_str < date_from):
                continue
            if date_to and (not m.match_date or m.date_str > date_to):
                continue
            results.append(m)

        results.sort(key=lambda m: m.date_str, reverse=True)
        if limit is not None:
            results = results[:limit]
        return results

    def head_to_head(self, team1: str, team2: str) -> dict:
        k1, k2 = team_key(team1), team_key(team2)
        matches = [m for m in self._by_team.get(k1, [])
                   if k2 in (m.home_key, m.away_key)]
        matches.sort(key=lambda m: m.date_str, reverse=True)
        w1 = w2 = draws = 0
        for m in matches:
            win = m.winner_key()
            if win == k1:
                w1 += 1
            elif win == k2:
                w2 += 1
            elif m.has_score:
                draws += 1
        return {
            "team1": self._team_display.get(k1, team1),
            "team2": self._team_display.get(k2, team2),
            "team1_wins": w1,
            "team2_wins": w2,
            "draws": draws,
            "total": len(matches),
            "matches": matches,
        }

    # ------------------------------------------------------------------ #
    # Team statistics
    # ------------------------------------------------------------------ #
    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "either",
    ) -> TeamRecord:
        tk = team_key(team)
        rec = TeamRecord(team=self._team_display.get(tk, team))
        for m in self._by_team.get(tk, []):
            if not m.has_score:
                continue
            if season is not None and m.season != season:
                continue
            if competition and not competition_matches(competition, m.competition):
                continue
            is_home = m.home_key == tk
            if venue == "home" and not is_home:
                continue
            if venue == "away" and is_home:
                continue
            gf = m.home_goal if is_home else m.away_goal
            ga = m.away_goal if is_home else m.home_goal
            rec.matches += 1
            rec.goals_for += gf
            rec.goals_against += ga
            if gf > ga:
                rec.wins += 1
            elif gf < ga:
                rec.losses += 1
            else:
                rec.draws += 1
        return rec

    # ------------------------------------------------------------------ #
    # Competition queries
    # ------------------------------------------------------------------ #
    def standings(
        self,
        competition: str,
        season: int,
    ) -> List[TeamRecord]:
        table: Dict[str, TeamRecord] = {}

        def rec_for(key, display):
            if key not in table:
                table[key] = TeamRecord(team=display)
            return table[key]

        for m in self.matches:
            if m.season != season:
                continue
            if not competition_matches(competition, m.competition):
                continue
            if not m.has_score:
                continue
            h = rec_for(m.home_key, m.home)
            a = rec_for(m.away_key, m.away)
            h.matches += 1
            a.matches += 1
            h.goals_for += m.home_goal
            h.goals_against += m.away_goal
            a.goals_for += m.away_goal
            a.goals_against += m.home_goal
            if m.home_goal > m.away_goal:
                h.wins += 1
                a.losses += 1
            elif m.away_goal > m.home_goal:
                a.wins += 1
                h.losses += 1
            else:
                h.draws += 1
                a.draws += 1

        return sorted(
            table.values(),
            key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, r.team),
        )

    def champion(self, competition: str, season: int) -> Optional[TeamRecord]:
        table = self.standings(competition, season)
        return table[0] if table else None

    # ------------------------------------------------------------------ #
    # Statistical analysis
    # ------------------------------------------------------------------ #
    def _filtered(self, competition=None, season=None) -> List[Match]:
        out = []
        for m in self.matches:
            if season is not None and m.season != season:
                continue
            if competition and not competition_matches(competition, m.competition):
                continue
            out.append(m)
        return out

    def average_goals(self, competition=None, season=None) -> dict:
        scored = [m for m in self._filtered(competition, season) if m.has_score]
        n = len(scored)
        if not n:
            return {"matches": 0, "avg_goals": 0.0, "home_win_rate": 0.0,
                    "away_win_rate": 0.0, "draw_rate": 0.0}
        total = sum(m.total_goals for m in scored)
        home_wins = sum(1 for m in scored if m.home_goal > m.away_goal)
        away_wins = sum(1 for m in scored if m.away_goal > m.home_goal)
        draws = n - home_wins - away_wins
        return {
            "matches": n,
            "avg_goals": round(total / n, 2),
            "home_win_rate": round(home_wins / n * 100, 1),
            "away_win_rate": round(away_wins / n * 100, 1),
            "draw_rate": round(draws / n * 100, 1),
        }

    def biggest_wins(self, competition=None, season=None, limit=10) -> List[Match]:
        scored = [m for m in self._filtered(competition, season) if m.has_score]
        scored.sort(
            key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals),
            reverse=True,
        )
        return scored[:limit]

    def best_record(
        self,
        competition=None,
        season=None,
        venue="either",
        min_matches=5,
        metric="win_rate",
    ) -> List[TeamRecord]:
        """Rank teams by record (optionally home-only / away-only)."""
        table: Dict[str, TeamRecord] = {}
        for m in self._filtered(competition, season):
            if not m.has_score:
                continue
            for key, display, is_home in (
                (m.home_key, m.home, True),
                (m.away_key, m.away, False),
            ):
                if venue == "home" and not is_home:
                    continue
                if venue == "away" and is_home:
                    continue
                rec = table.setdefault(key, TeamRecord(team=display))
                gf = m.home_goal if is_home else m.away_goal
                ga = m.away_goal if is_home else m.home_goal
                rec.matches += 1
                rec.goals_for += gf
                rec.goals_against += ga
                if gf > ga:
                    rec.wins += 1
                elif gf < ga:
                    rec.losses += 1
                else:
                    rec.draws += 1
        ranked = [r for r in table.values() if r.matches >= min_matches]
        if metric == "points":
            ranked.sort(key=lambda r: (-r.points, -r.goal_diff))
        elif metric == "goals_for":
            ranked.sort(key=lambda r: -r.goals_for)
        else:
            ranked.sort(key=lambda r: (-r.win_rate, -r.matches))
        return ranked

    def top_scoring_team(self, competition=None, season=None) -> Optional[TeamRecord]:
        ranked = self.best_record(competition, season, metric="goals_for",
                                  min_matches=1)
        return ranked[0] if ranked else None

    # ------------------------------------------------------------------ #
    # Player queries
    # ------------------------------------------------------------------ #
    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort_by: str = "overall",
        limit: Optional[int] = 25,
    ) -> List[Player]:
        name_q = _norm_text(name) if name else None
        nat_q = _norm_text(nationality) if nationality else None
        pos_q = _norm_text(position) if position else None
        club_key = team_key(club) if club else None

        results = []
        for p in self.players:
            if name_q and name_q not in _norm_text(p.name):
                continue
            if nat_q and nat_q != _norm_text(p.nationality):
                continue
            if club_key and team_key(p.club) != club_key:
                continue
            if pos_q and pos_q != _norm_text(p.position):
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)

        if sort_by == "name":
            results.sort(key=lambda p: _norm_text(p.name))
        elif sort_by == "potential":
            results.sort(key=lambda p: (p.potential or 0), reverse=True)
        elif sort_by == "age":
            results.sort(key=lambda p: (p.age or 999))
        else:
            results.sort(key=lambda p: (p.overall or 0), reverse=True)

        if limit is not None:
            results = results[:limit]
        return results

    def players_at_club(self, club: str, limit: Optional[int] = None) -> List[Player]:
        players = list(self._players_by_club.get(team_key(club), []))
        players.sort(key=lambda p: (p.overall or 0), reverse=True)
        return players[:limit] if limit else players

    def top_brazilian_players(self, limit: int = 10) -> List[Player]:
        return self.search_players(nationality="Brazil", sort_by="overall",
                                   limit=limit)
