"""
================================================================================
brazilian_soccer_mcp.knowledge_graph
================================================================================

CONTEXT
-------
The KnowledgeGraph is the heart of the system: it holds the normalised match and
player tables (see ``data_loader``) and answers all of the query categories
required by the specification:

    1. Match queries        - find matches by team / date / competition / season
    2. Team queries         - records, goals, home/away splits, comparisons
    3. Player queries       - search by name / nationality / club / position
    4. Competition queries  - standings, champions, relegation (computed)
    5. Statistical analysis - goals-per-match, win rates, biggest wins, H2H

Every method returns plain Python data structures (lists/dicts) so the layer is
transport-agnostic; ``formatting`` and ``server`` turn those into text. This is
what makes the engine directly unit-testable with Given-When-Then pytest cases.

All team-name handling goes through ``normalize`` so the many spellings used by
the datasets resolve to the same club.
================================================================================
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

import pandas as pd

from . import data_loader
from .normalize import canonical_norm, parse_date, strip_accents


class KnowledgeGraph:
    """In-memory knowledge graph over the Brazilian soccer datasets."""

    def __init__(self, matches: pd.DataFrame, players: pd.DataFrame):
        self.matches = matches
        self.players = players

    # ------------------------------------------------------------------ build
    @classmethod
    def load(cls, data_dir=None) -> "KnowledgeGraph":
        matches, players = data_loader.load_all(data_dir)
        return cls(matches, players)

    # --------------------------------------------------------------- helpers
    def _team_mask(self, df: pd.DataFrame, query: str, side: str) -> pd.Series:
        """Boolean mask of rows where *query* matches the team on *side*.

        side: 'home', 'away' or 'either'. Matching is accent-insensitive and
        tolerant of state suffixes via whole-word containment on normalised keys.
        """
        q = canonical_norm(query)
        pad = lambda col: " " + df[col] + " "  # noqa: E731
        token = f" {q} "
        if side == "home":
            return pad("home_norm").str.contains(token, regex=False)
        if side == "away":
            return pad("away_norm").str.contains(token, regex=False)
        return (pad("home_norm").str.contains(token, regex=False)
                | pad("away_norm").str.contains(token, regex=False))

    @staticmethod
    def _match_to_dict(row) -> dict:
        d = row.date
        return {
            "competition": row.competition,
            "season": int(row.season) if pd.notna(row.season) else None,
            "date": d.isoformat() if isinstance(d, date) else None,
            "round": row.round,
            "home_team": row.home_team,
            "away_team": row.away_team,
            "home_goal": int(row.home_goal),
            "away_goal": int(row.away_goal),
            "source": row.source,
        }

    # =================================================================
    # 1. MATCH QUERIES
    # =================================================================
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        """Return matches filtered by any combination of the given criteria."""
        df = self.matches
        if df.empty:
            return []
        mask = pd.Series(True, index=df.index)
        if team:
            mask &= self._team_mask(df, team, "either")
        if opponent:
            mask &= self._team_mask(df, opponent, "either")
        if home_team:
            mask &= self._team_mask(df, home_team, "home")
        if away_team:
            mask &= self._team_mask(df, away_team, "away")
        if competition:
            comp_norm = strip_accents(competition).lower()
            mask &= df["competition"].map(
                lambda c: comp_norm in strip_accents(str(c)).lower()
            )
        if season is not None:
            mask &= df["season"] == int(season)
        sd = parse_date(start_date) if start_date else None
        ed = parse_date(end_date) if end_date else None
        if sd is not None:
            mask &= df["date"].map(lambda d: isinstance(d, date) and d >= sd)
        if ed is not None:
            mask &= df["date"].map(lambda d: isinstance(d, date) and d <= ed)

        result = df[mask].copy()
        result = result.sort_values(
            by="date", key=lambda s: s.map(lambda d: d or date.min)
        )
        rows = [self._match_to_dict(r) for r in result.itertuples(index=False)]
        if limit:
            rows = rows[-limit:] if limit > 0 else rows
        return rows

    def last_meeting(self, team1: str, team2: str) -> Optional[dict]:
        """Most recent match between two teams (any competition)."""
        matches = self.find_matches(team=team1, opponent=team2)
        dated = [m for m in matches if m["date"]]
        if not dated:
            return matches[-1] if matches else None
        return max(dated, key=lambda m: m["date"])

    # =================================================================
    # 2. TEAM QUERIES & 5. HEAD-TO-HEAD
    # =================================================================
    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",  # 'all' | 'home' | 'away'
    ) -> dict:
        """Win/draw/loss record and goals for a team, optionally filtered."""
        df = self.matches
        if df.empty:
            return self._empty_record(team)
        if venue == "home":
            mask = self._team_mask(df, team, "home")
        elif venue == "away":
            mask = self._team_mask(df, team, "away")
        else:
            mask = self._team_mask(df, team, "either")
        if season is not None:
            mask &= df["season"] == int(season)
        if competition:
            comp_norm = strip_accents(competition).lower()
            mask &= df["competition"].map(
                lambda c: comp_norm in strip_accents(str(c)).lower()
            )
        sub = df[mask]
        wins = draws = losses = gf = ga = 0
        q = canonical_norm(team)
        token = f" {q} "
        for r in sub.itertuples(index=False):
            is_home = token in f" {r.home_norm} "
            tg, og = (r.home_goal, r.away_goal) if is_home else (r.away_goal, r.home_goal)
            gf += tg
            ga += og
            if tg > og:
                wins += 1
            elif tg == og:
                draws += 1
            else:
                losses += 1
        played = wins + draws + losses
        return {
            "team": team,
            "season": season,
            "competition": competition,
            "venue": venue,
            "played": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": round(100 * wins / played, 1) if played else 0.0,
        }

    @staticmethod
    def _empty_record(team: str) -> dict:
        return {
            "team": team, "season": None, "competition": None, "venue": "all",
            "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "goal_difference": 0,
            "points": 0, "win_rate": 0.0,
        }

    def head_to_head(
        self, team1: str, team2: str, competition: Optional[str] = None
    ) -> dict:
        """Head-to-head summary between two teams."""
        matches = self.find_matches(
            team=team1, opponent=team2, competition=competition
        )
        q1 = canonical_norm(team1)
        token1 = f" {q1} "
        t1_wins = t2_wins = draws = t1_goals = t2_goals = 0
        for m in matches:
            home_norm = f" {canonical_norm(m['home_team'])} "
            t1_home = token1 in home_norm
            t1g, t2g = (
                (m["home_goal"], m["away_goal"]) if t1_home
                else (m["away_goal"], m["home_goal"])
            )
            t1_goals += t1g
            t2_goals += t2g
            if t1g > t2g:
                t1_wins += 1
            elif t1g == t2g:
                draws += 1
            else:
                t2_wins += 1
        return {
            "team1": team1,
            "team2": team2,
            "competition": competition,
            "matches": matches,
            "total": len(matches),
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "team1_goals": t1_goals,
            "team2_goals": t2_goals,
        }

    # =================================================================
    # 3. PLAYER QUERIES
    # =================================================================
    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort_by: str = "Overall",
        limit: int = 20,
    ) -> List[dict]:
        """Search the FIFA player database by any combination of criteria."""
        df = self.players
        if df.empty:
            return []
        mask = pd.Series(True, index=df.index)
        if name:
            n = strip_accents(name).lower()
            mask &= df["name_norm"].str.contains(n, regex=False, na=False)
        if nationality:
            nat = strip_accents(nationality).lower()
            mask &= df["nat_norm"].str.contains(nat, regex=False, na=False)
        if club:
            c = canonical_norm(club)
            token = f" {c} "
            mask &= (" " + df["club_norm"] + " ").str.contains(token, regex=False, na=False)
        if position:
            pos = position.strip().upper()
            mask &= df["Position"].astype(str).str.upper().str.strip() == pos
        if min_overall is not None:
            mask &= df["Overall"] >= float(min_overall)
        sub = df[mask]
        if sort_by in sub.columns:
            sub = sub.sort_values(by=sort_by, ascending=False, na_position="last")
        return [self._player_to_dict(r) for r in sub.head(limit).itertuples(index=False)]

    @staticmethod
    def _player_to_dict(row) -> dict:
        def g(attr, default=None):
            v = getattr(row, attr, default)
            if isinstance(v, float) and v != v:
                return default
            return v
        overall = g("Overall")
        return {
            "name": g("Name"),
            "age": int(g("Age")) if pd.notna(g("Age")) else None,
            "nationality": g("Nationality"),
            "overall": int(overall) if overall is not None and pd.notna(overall) else None,
            "potential": int(g("Potential")) if pd.notna(g("Potential")) else None,
            "club": g("club_clean") or g("Club"),
            "position": g("Position"),
            "value": g("Value"),
        }

    def players_by_club_summary(self, clubs: List[str]) -> List[dict]:
        """For each club return count + average overall of its players."""
        out = []
        for club in clubs:
            players = self.search_players(club=club, limit=10_000)
            if not players:
                continue
            overalls = [p["overall"] for p in players if p["overall"] is not None]
            avg = round(sum(overalls) / len(overalls), 1) if overalls else None
            out.append({"club": club, "count": len(players), "avg_overall": avg})
        return out

    # =================================================================
    # 4. COMPETITION QUERIES
    # =================================================================
    def standings(self, competition: str, season: int) -> List[dict]:
        """Compute a league table from match results (3pts win / 1pt draw)."""
        df = self.matches
        comp_norm = strip_accents(competition).lower()
        mask = df["competition"].map(
            lambda c: comp_norm in strip_accents(str(c)).lower()
        ) & (df["season"] == int(season))
        sub = df[mask]
        table: dict = {}

        def entry(name):
            return table.setdefault(name, {
                "team": name, "played": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "points": 0,
            })

        for r in sub.itertuples(index=False):
            home, away = entry(r.home_team), entry(r.away_team)
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += r.home_goal
            home["goals_against"] += r.away_goal
            away["goals_for"] += r.away_goal
            away["goals_against"] += r.home_goal
            if r.home_goal > r.away_goal:
                home["wins"] += 1
                home["points"] += 3
                away["losses"] += 1
            elif r.home_goal < r.away_goal:
                away["wins"] += 1
                away["points"] += 3
                home["losses"] += 1
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        rows = list(table.values())
        for row in rows:
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
        rows.sort(
            key=lambda t: (t["points"], t["goal_difference"], t["goals_for"]),
            reverse=True,
        )
        for i, row in enumerate(rows, start=1):
            row["position"] = i
        return rows

    def champion(self, competition: str, season: int) -> Optional[dict]:
        table = self.standings(competition, season)
        return table[0] if table else None

    def relegated(self, competition: str, season: int, count: int = 4) -> List[dict]:
        table = self.standings(competition, season)
        return table[-count:] if table else []

    # =================================================================
    # 5. STATISTICAL ANALYSIS
    # =================================================================
    def average_goals(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        df = self.matches
        mask = pd.Series(True, index=df.index)
        if competition:
            comp_norm = strip_accents(competition).lower()
            mask &= df["competition"].map(
                lambda c: comp_norm in strip_accents(str(c)).lower()
            )
        if season is not None:
            mask &= df["season"] == int(season)
        sub = df[mask]
        n = len(sub)
        if n == 0:
            return {"matches": 0, "avg_goals": 0.0, "home_win_rate": 0.0,
                    "away_win_rate": 0.0, "draw_rate": 0.0}
        total_goals = int((sub["home_goal"] + sub["away_goal"]).sum())
        home_wins = int((sub["home_goal"] > sub["away_goal"]).sum())
        away_wins = int((sub["home_goal"] < sub["away_goal"]).sum())
        draws = n - home_wins - away_wins
        return {
            "matches": n,
            "avg_goals": round(total_goals / n, 2),
            "home_win_rate": round(100 * home_wins / n, 1),
            "away_win_rate": round(100 * away_wins / n, 1),
            "draw_rate": round(100 * draws / n, 1),
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[dict]:
        """Matches with the largest goal margin."""
        df = self.matches
        mask = pd.Series(True, index=df.index)
        if competition:
            comp_norm = strip_accents(competition).lower()
            mask &= df["competition"].map(
                lambda c: comp_norm in strip_accents(str(c)).lower()
            )
        if season is not None:
            mask &= df["season"] == int(season)
        sub = df[mask].copy()
        if sub.empty:
            return []
        sub["margin"] = (sub["home_goal"] - sub["away_goal"]).abs()
        sub = sub.sort_values(
            by=["margin", "home_goal", "away_goal"], ascending=False
        )
        out = []
        for r in sub.head(limit).itertuples(index=False):
            d = self._match_to_dict(r)
            d["margin"] = abs(d["home_goal"] - d["away_goal"])
            out.append(d)
        return out

    def best_record(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: str = "home",
        metric: str = "win_rate",
        min_played: int = 5,
    ) -> List[dict]:
        """Rank teams by a record metric (e.g. best home record)."""
        df = self.matches
        mask = pd.Series(True, index=df.index)
        if competition:
            comp_norm = strip_accents(competition).lower()
            mask &= df["competition"].map(
                lambda c: comp_norm in strip_accents(str(c)).lower()
            )
        if season is not None:
            mask &= df["season"] == int(season)
        sub = df[mask]
        teams = set(sub["home_team"]) | set(sub["away_team"])
        records = []
        for t in teams:
            rec = self.team_record(t, season=season, competition=competition, venue=venue)
            if rec["played"] >= min_played:
                records.append(rec)
        records.sort(key=lambda r: (r.get(metric, 0), r["goal_difference"]), reverse=True)
        return records

    # ---------------------------------------------------------------- misc
    def list_competitions(self) -> List[str]:
        if self.matches.empty:
            return []
        return sorted(self.matches["competition"].unique().tolist())

    def list_seasons(self, competition: Optional[str] = None) -> List[int]:
        df = self.matches
        if competition:
            comp_norm = strip_accents(competition).lower()
            df = df[df["competition"].map(
                lambda c: comp_norm in strip_accents(str(c)).lower())]
        seasons = sorted({int(s) for s in df["season"].dropna().unique()})
        return seasons


# ----------------------------------------------------------------------------
# Module-level singleton so the server / repeated queries share one load.
# ----------------------------------------------------------------------------
_GRAPH: Optional[KnowledgeGraph] = None


def get_knowledge_graph(data_dir=None) -> KnowledgeGraph:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = KnowledgeGraph.load(data_dir)
    return _GRAPH
