"""
Context
=======
The KnowledgeBase is the query brain of the project. It holds the loaded
``Match`` and ``Player`` records in memory and answers the question
categories from the specification:

* match queries     -- by team / opponent / venue / season / competition / dates
* team queries      -- aggregate win-loss-draw records, optionally per venue
* head-to-head      -- two-team comparison
* competition       -- league standings computed from match results
* player queries    -- search by name / nationality / club / position / rating
* statistics        -- average goals, biggest wins, best home/away records

Everything is plain Python lists and dict aggregation; no external services.
Team matching always goes through the normalized keys so "Palmeiras-SP",
"Palmeiras" and "Sociedade Esportiva Palmeiras" are treated as one club.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Dict, List, Optional

from .data_loader import (
    DATA_DIR,
    Match,
    Player,
    load_all_matches,
    load_players,
)
from .normalize import normalize_team


class KnowledgeBase:
    def __init__(self, matches: List[Match], players: List[Player]):
        self.matches = matches
        self.players = players

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "KnowledgeBase":
        data_dir = Path(data_dir)
        return cls(load_all_matches(data_dir), load_players(data_dir / "fifa_data.csv"))

    # ---- match queries ----------------------------------------------------

    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        home: Optional[str] = None,
        away: Optional[str] = None,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        start_date: Optional[dt.date] = None,
        end_date: Optional[dt.date] = None,
    ) -> List[Match]:
        """Return matches filtered by any combination of criteria, date-sorted.

        * ``team``     -- played at either venue
        * ``opponent`` -- combined with ``team`` for direct meetings
        * ``home`` / ``away`` -- specific venue
        """
        team_key = normalize_team(team) if team else None
        opp_key = normalize_team(opponent) if opponent else None
        home_key = normalize_team(home) if home else None
        away_key = normalize_team(away) if away else None
        comp_key = competition.lower() if competition else None

        results = []
        for mt in self.matches:
            if team_key and team_key not in (mt.home_key, mt.away_key):
                continue
            if opp_key and opp_key not in (mt.home_key, mt.away_key):
                continue
            if home_key and mt.home_key != home_key:
                continue
            if away_key and mt.away_key != away_key:
                continue
            if season is not None and mt.season != season:
                continue
            if comp_key and comp_key not in mt.competition.lower():
                continue
            if start_date and (mt.date is None or mt.date < start_date):
                continue
            if end_date and (mt.date is None or mt.date > end_date):
                continue
            results.append(mt)

        results.sort(key=lambda x: (x.date is None, x.date or dt.date.min))
        return results

    # ---- head-to-head -----------------------------------------------------

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> Dict:
        a_key = normalize_team(team_a)
        b_key = normalize_team(team_b)
        games = self.find_matches(team=team_a, opponent=team_b,
                                  season=season, competition=competition)
        a_wins = b_wins = draws = a_goals = b_goals = 0
        for mt in games:
            if mt.home_goal is None or mt.away_goal is None:
                continue
            if mt.home_key == a_key:
                ag, bg = mt.home_goal, mt.away_goal
            else:
                ag, bg = mt.away_goal, mt.home_goal
            a_goals += ag
            b_goals += bg
            if ag > bg:
                a_wins += 1
            elif ag < bg:
                b_wins += 1
            else:
                draws += 1
        return {
            "team_a": team_a,
            "team_b": team_b,
            "team_a_key": a_key,
            "team_b_key": b_key,
            "matches": len(games),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
            "match_list": games,
        }

    # ---- team record ------------------------------------------------------

    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,  # None | "home" | "away"
    ) -> Dict:
        key = normalize_team(team)
        if venue == "home":
            games = self.find_matches(home=team, season=season, competition=competition)
        elif venue == "away":
            games = self.find_matches(away=team, season=season, competition=competition)
        else:
            games = self.find_matches(team=team, season=season, competition=competition)

        wins = draws = losses = gf = ga = 0
        for mt in games:
            if mt.home_goal is None or mt.away_goal is None:
                continue
            if mt.home_key == key:
                scored, conceded = mt.home_goal, mt.away_goal
            else:
                scored, conceded = mt.away_goal, mt.home_goal
            gf += scored
            ga += conceded
            if scored > conceded:
                wins += 1
            elif scored < conceded:
                losses += 1
            else:
                draws += 1
        played = wins + draws + losses
        return {
            "team": team,
            "team_key": key,
            "matches": len(games),
            "played": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": round(100.0 * wins / played, 1) if played else 0.0,
        }

    # ---- standings --------------------------------------------------------

    def standings(self, season: int, competition: str = "Brasileirão") -> List[Dict]:
        """Compute a league table from match results for *season*."""
        games = self.find_matches(season=season, competition=competition)
        table: Dict[str, Dict] = {}

        def row(key: str, name: str) -> Dict:
            return table.setdefault(key, {
                "team_key": key, "team": name, "played": 0,
                "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "points": 0,
            })

        for mt in games:
            if mt.home_goal is None or mt.away_goal is None:
                continue
            h = row(mt.home_key, mt.home_team)
            a = row(mt.away_key, mt.away_team)
            h["played"] += 1
            a["played"] += 1
            h["goals_for"] += mt.home_goal
            h["goals_against"] += mt.away_goal
            a["goals_for"] += mt.away_goal
            a["goals_against"] += mt.home_goal
            if mt.home_goal > mt.away_goal:
                h["wins"] += 1; h["points"] += 3; a["losses"] += 1
            elif mt.home_goal < mt.away_goal:
                a["wins"] += 1; a["points"] += 3; h["losses"] += 1
            else:
                h["draws"] += 1; a["draws"] += 1
                h["points"] += 1; a["points"] += 1

        for r in table.values():
            r["goal_difference"] = r["goals_for"] - r["goals_against"]

        # Official Brasileirão tiebreakers: points, then wins, then goal
        # difference, then goals scored.
        ranked = sorted(
            table.values(),
            key=lambda r: (r["points"], r["wins"], r["goal_difference"], r["goals_for"]),
            reverse=True,
        )
        for i, r in enumerate(ranked, start=1):
            r["position"] = i
        return ranked

    # ---- player queries ---------------------------------------------------

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: Optional[int] = None,
        sort_by_overall: bool = True,
    ) -> List[Player]:
        name_l = name.lower() if name else None
        nat_l = nationality.lower() if nationality else None
        club_key = normalize_team(club) if club else None
        pos_l = position.lower() if position else None

        results = []
        for p in self.players:
            if name_l and name_l not in p.name.lower():
                continue
            if nat_l and p.nationality.lower() != nat_l:
                continue
            if club_key and p.club_key != club_key:
                continue
            if pos_l and p.position.lower() != pos_l:
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)

        if sort_by_overall:
            results.sort(key=lambda p: (p.overall is None, -(p.overall or 0), p.name))
        if limit is not None:
            results = results[:limit]
        return results

    def players_by_club_summary(self, nationality: Optional[str] = None) -> List[Dict]:
        """Aggregate player counts and average rating per club."""
        agg: Dict[str, Dict] = {}
        for p in self.players:
            if nationality and p.nationality.lower() != nationality.lower():
                continue
            if not p.club:
                continue
            r = agg.setdefault(p.club_key, {"club": p.club, "count": 0, "_sum": 0, "_n": 0})
            r["count"] += 1
            if p.overall is not None:
                r["_sum"] += p.overall
                r["_n"] += 1
        out = []
        for r in agg.values():
            out.append({
                "club": r["club"],
                "count": r["count"],
                "avg_overall": round(r["_sum"] / r["_n"], 1) if r["_n"] else None,
            })
        out.sort(key=lambda r: r["count"], reverse=True)
        return out

    # ---- statistics -------------------------------------------------------

    def average_goals_per_match(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> float:
        games = [g for g in self.find_matches(competition=competition, season=season)
                 if g.total_goals is not None]
        if not games:
            return 0.0
        return round(sum(g.total_goals for g in games) / len(games), 2)

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[Match]:
        games = [g for g in self.find_matches(competition=competition, season=season)
                 if g.winner in ("home", "away")]
        games.sort(key=lambda g: abs(g.home_goal - g.away_goal), reverse=True)
        return games[:limit]

    def best_record(
        self,
        venue: str = "home",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 10,
        limit: int = 10,
        metric: str = "win_rate",
    ) -> List[Dict]:
        """Rank teams by win-rate (or points) for a given venue."""
        if venue not in ("home", "away"):
            raise ValueError("venue must be 'home' or 'away'")
        games = self.find_matches(competition=competition, season=season)
        keys = set()
        for g in games:
            keys.add(g.home_key if venue == "home" else g.away_key)

        rows = []
        for key in keys:
            rec = self.team_record(key, season=season, competition=competition, venue=venue)
            if rec["played"] >= min_matches:
                rows.append(rec)
        rows.sort(key=lambda r: (r.get(metric, 0), r["points"], r["goal_difference"]),
                  reverse=True)
        return rows[:limit]

    # ---- meta -------------------------------------------------------------

    def summary(self) -> Dict:
        comps: Dict[str, int] = {}
        for mt in self.matches:
            comps[mt.competition] = comps.get(mt.competition, 0) + 1
        return {
            "total_matches": len(self.matches),
            "total_players": len(self.players),
            "competitions": comps,
        }
