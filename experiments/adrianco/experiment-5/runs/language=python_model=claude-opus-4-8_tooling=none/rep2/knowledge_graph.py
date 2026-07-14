"""
Knowledge-graph query engine for the Brazilian Soccer MCP server.

Context
-------
This module is the heart of the server.  It loads the unified match and player
records produced by :mod:`data_loader` and exposes the query capabilities the
specification requires, grouped into five families:

    1. Match queries        -- find_matches, head_to_head
    2. Team queries         -- team_record, team_competitions
    3. Player queries       -- find_players, top_brazilian_players,
                               brazilian_players_by_club
    4. Competition queries  -- standings, list_seasons
    5. Statistical analysis -- average_goals, biggest_wins, best_team_record

Every method returns plain Python data structures (dicts / lists) so they can
be JSON-serialised by the MCP layer or asserted against in tests.  The engine
itself has no third-party dependencies; it models the data as an in-memory
"knowledge graph" of Team / Player / Match / Competition entities linked by
normalized name keys (see :mod:`team_names`).

The companion :mod:`formatters` module turns these structures into the
human-readable answers shown in the specification examples.
"""

from __future__ import annotations

import datetime as _dt
from collections import defaultdict
from typing import Optional

from data_loader import Match, Player, load_all
from team_names import _base_key, display_name, match_key, names_match, split_team


class KnowledgeGraph:
    """In-memory query engine over the Brazilian soccer datasets."""

    def __init__(self, matches: list[Match], players: list[Player]):
        self.matches = matches
        self.players = players

        # Index matches by accent-folded base key (region-agnostic) so a query
        # like "Atletico" can find every Atletico, then be narrowed by region.
        self._matches_by_team: dict[str, list[Match]] = defaultdict(list)
        for m in matches:
            self._matches_by_team[m.home_base_key].append(m)
            if m.away_base_key != m.home_base_key:
                self._matches_by_team[m.away_base_key].append(m)

        self._players_by_nat: dict[str, list[Player]] = defaultdict(list)
        for p in players:
            self._players_by_nat[match_key(p.nationality)].append(p)

    # -- construction ----------------------------------------------------
    @classmethod
    def load(cls, data_dir: Optional[str] = None) -> "KnowledgeGraph":
        if data_dir is None:
            matches, players = load_all()
        else:
            matches, players = load_all(data_dir)
        return cls(matches, players)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _team_matches(self, team: str) -> list[Match]:
        """Return every match the given team played.

        Candidates are gathered from the base-key index (with a substring
        fallback for partial names) and then filtered region-aware so that, for
        example, "Atletico-MG" never returns Athletico-PR fixtures.
        """
        base, _region = split_team(team)
        bk = _base_key(base)
        candidates = self._matches_by_team.get(bk)
        if candidates is None:
            # Fallback: substring match against the index keys (partial names).
            candidates = []
            seen = set()
            for ik, ms in self._matches_by_team.items():
                if bk and (bk in ik or ik in bk):
                    for m in ms:
                        if id(m) not in seen:
                            seen.add(id(m))
                            candidates.append(m)
        return [m for m in candidates if m.involves(team)]

    @staticmethod
    def _passes(m: Match, competition, season, start_date, end_date) -> bool:
        if competition and match_key(m.competition) != match_key(competition):
            return False
        if season is not None and m.season != int(season):
            return False
        if start_date and (m.date is None or m.date < start_date):
            return False
        if end_date and (m.date is None or m.date > end_date):
            return False
        return True

    # ------------------------------------------------------------------
    # 1. Match queries
    # ------------------------------------------------------------------
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[_dt.date] = None,
        end_date: Optional[_dt.date] = None,
        venue: str = "either",       # "home", "away" or "either" (w.r.t. team)
        limit: Optional[int] = None,
    ) -> list[Match]:
        """Find matches by any combination of team, opponent, competition,
        season and date range.  Results are sorted most-recent first."""
        if team:
            candidates = self._team_matches(team)
        else:
            candidates = self.matches

        results = []
        for m in candidates:
            if not self._passes(m, competition, season, start_date, end_date):
                continue
            if team:
                is_home = m.is_home(team)
                is_away = m.is_away(team)
                if venue == "home" and not is_home:
                    continue
                if venue == "away" and not is_away:
                    continue
                if not (is_home or is_away):
                    continue
            if opponent and not m.involves(opponent):
                continue
            results.append(m)

        results.sort(key=lambda x: (x.date or _dt.date.min), reverse=True)
        if limit is not None:
            results = results[:limit]
        return results

    def head_to_head(self, team1: str, team2: str) -> dict:
        """Compute the all-competition head-to-head record between two teams."""
        matches = self.find_matches(team=team1, opponent=team2)
        t1_wins = t2_wins = draws = 0
        t1_goals = t2_goals = 0
        for m in matches:
            if m.home_goal is None or m.away_goal is None:
                continue
            t1_home = m.is_home(team1)
            t1_gf = m.home_goal if t1_home else m.away_goal
            t1_ga = m.away_goal if t1_home else m.home_goal
            t1_goals += t1_gf
            t2_goals += t1_ga
            if t1_gf > t1_ga:
                t1_wins += 1
            elif t1_gf < t1_ga:
                t2_wins += 1
            else:
                draws += 1
        return {
            "team1": display_name(team1),
            "team2": display_name(team2),
            "total_matches": len(matches),
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "team1_goals": t1_goals,
            "team2_goals": t2_goals,
            "matches": matches,
        }

    # ------------------------------------------------------------------
    # 2. Team queries
    # ------------------------------------------------------------------
    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "either",
    ) -> dict:
        """Win/draw/loss record, goals for/against and win rate for a team."""
        matches = self.find_matches(
            team=team, competition=competition, season=season, venue=venue
        )
        wins = draws = losses = gf = ga = played = 0
        for m in matches:
            if m.home_goal is None or m.away_goal is None:
                continue
            is_home = m.is_home(team)
            scored = m.home_goal if is_home else m.away_goal
            conceded = m.away_goal if is_home else m.home_goal
            played += 1
            gf += scored
            ga += conceded
            if scored > conceded:
                wins += 1
            elif scored < conceded:
                losses += 1
            else:
                draws += 1
        win_rate = (wins / played * 100.0) if played else 0.0
        return {
            "team": display_name(team),
            "season": season,
            "competition": competition,
            "venue": venue,
            "matches": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": round(win_rate, 1),
        }

    def team_competitions(self, team: str) -> dict:
        """Return the competitions a team has appeared in, with match counts."""
        counts: dict[str, int] = defaultdict(int)
        for m in self._team_matches(team):
            counts[m.competition] += 1
        return {
            "team": display_name(team),
            "competitions": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        }

    # ------------------------------------------------------------------
    # 3. Player queries
    # ------------------------------------------------------------------
    def find_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort_by: str = "overall",
        limit: Optional[int] = 25,
    ) -> list[Player]:
        """Search players by name / nationality / club / position / rating."""
        nat_key = match_key(nationality) if nationality else None
        pool = self._players_by_nat.get(nat_key, self.players) if nat_key else self.players

        results = []
        for p in pool:
            if name and match_key(name) not in match_key(p.name):
                continue
            if nationality and match_key(p.nationality) != nat_key:
                continue
            if club and not names_match(club, p.club):
                continue
            if position and match_key(position) != match_key(p.position):
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)

        if sort_by == "overall":
            results.sort(key=lambda x: (x.overall or 0), reverse=True)
        elif sort_by == "potential":
            results.sort(key=lambda x: (x.potential or 0), reverse=True)
        elif sort_by == "age":
            results.sort(key=lambda x: (x.age or 0))
        elif sort_by == "name":
            results.sort(key=lambda x: x.name.lower())

        if limit is not None:
            results = results[:limit]
        return results

    def top_brazilian_players(self, limit: int = 10) -> list[Player]:
        return self.find_players(nationality="Brazil", sort_by="overall", limit=limit)

    def brazilian_players_by_club(self, limit_clubs: int = 10) -> list[dict]:
        """Group Brazilian players by club with count and average rating."""
        by_club: dict[str, list[Player]] = defaultdict(list)
        for p in self._players_by_nat.get(match_key("Brazil"), []):
            if p.club:
                by_club[p.club].append(p)
        rows = []
        for club, players in by_club.items():
            rated = [p.overall for p in players if p.overall is not None]
            rows.append({
                "club": club,
                "count": len(players),
                "avg_overall": round(sum(rated) / len(rated), 1) if rated else 0.0,
            })
        rows.sort(key=lambda r: (-r["count"], -r["avg_overall"]))
        return rows[:limit_clubs]

    # ------------------------------------------------------------------
    # 4. Competition queries
    # ------------------------------------------------------------------
    def list_seasons(self, competition: Optional[str] = None) -> list[int]:
        seasons = set()
        for m in self.matches:
            if competition and match_key(m.competition) != match_key(competition):
                continue
            if m.season is not None:
                seasons.add(m.season)
        return sorted(seasons)

    def standings(self, competition: str, season: int) -> list[dict]:
        """Compute a league table from match results (3 pts win, 1 pt draw).

        Rows are ordered by points, then goal difference, then goals for.
        """
        season = int(season)
        table: dict[str, dict] = {}

        def row_for(key: str, display: str) -> dict:
            return table.setdefault(key, {
                "team": display, "played": 0, "wins": 0, "draws": 0,
                "losses": 0, "goals_for": 0, "goals_against": 0,
                "goal_difference": 0, "points": 0,
            })

        for m in self.matches:
            if match_key(m.competition) != match_key(competition):
                continue
            if m.season != season:
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            home = row_for(m.home_key, m.home_team)
            away = row_for(m.away_key, m.away_team)
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += m.home_goal
            home["goals_against"] += m.away_goal
            away["goals_for"] += m.away_goal
            away["goals_against"] += m.home_goal
            if m.home_goal > m.away_goal:
                home["wins"] += 1
                home["points"] += 3
                away["losses"] += 1
            elif m.home_goal < m.away_goal:
                away["wins"] += 1
                away["points"] += 3
                home["losses"] += 1
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        rows = list(table.values())
        for r in rows:
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
        rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"]))
        for i, r in enumerate(rows, start=1):
            r["position"] = i
        return rows

    def champion(self, competition: str, season: int) -> Optional[dict]:
        table = self.standings(competition, season)
        return table[0] if table else None

    # ------------------------------------------------------------------
    # 5. Statistical analysis
    # ------------------------------------------------------------------
    def average_goals(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        """Average goals per match plus home/draw/away outcome rates."""
        total_goals = 0
        played = home_wins = away_wins = draws = 0
        for m in self.matches:
            if not self._passes(m, competition, season, None, None):
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            played += 1
            total_goals += m.home_goal + m.away_goal
            if m.home_goal > m.away_goal:
                home_wins += 1
            elif m.home_goal < m.away_goal:
                away_wins += 1
            else:
                draws += 1
        return {
            "competition": competition,
            "season": season,
            "matches": played,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / played, 2) if played else 0.0,
            "home_win_rate": round(home_wins / played * 100, 1) if played else 0.0,
            "away_win_rate": round(away_wins / played * 100, 1) if played else 0.0,
            "draw_rate": round(draws / played * 100, 1) if played else 0.0,
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> list[Match]:
        """Matches with the largest goal margin, biggest first."""
        candidates = [
            m for m in self.matches
            if self._passes(m, competition, season, None, None)
            and m.home_goal is not None and m.away_goal is not None
        ]
        candidates.sort(
            key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals),
            reverse=True,
        )
        return candidates[:limit]

    def best_team_record(
        self,
        venue: str = "home",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 5,
        metric: str = "win_rate",
        limit: int = 10,
    ) -> list[dict]:
        """Rank teams by home/away/overall win-rate (or points)."""
        agg: dict[str, dict] = defaultdict(
            lambda: {"team": "", "played": 0, "wins": 0, "draws": 0,
                     "losses": 0, "goals_for": 0, "goals_against": 0}
        )
        for m in self.matches:
            if not self._passes(m, competition, season, None, None):
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            sides = []
            if venue in ("home", "either"):
                sides.append((m.home_key, m.home_team, m.home_goal, m.away_goal))
            if venue in ("away", "either"):
                sides.append((m.away_key, m.away_team, m.away_goal, m.home_goal))
            for key, display, gf, ga in sides:
                a = agg[key]
                a["team"] = display
                a["played"] += 1
                a["goals_for"] += gf
                a["goals_against"] += ga
                if gf > ga:
                    a["wins"] += 1
                elif gf < ga:
                    a["losses"] += 1
                else:
                    a["draws"] += 1

        rows = []
        for key, a in agg.items():
            if a["played"] < min_matches:
                continue
            win_rate = a["wins"] / a["played"] * 100
            points = a["wins"] * 3 + a["draws"]
            rows.append({
                "venue": venue,
                **a,
                "win_rate": round(win_rate, 1),
                "points": points,
            })
        key = "points" if metric == "points" else "win_rate"
        rows.sort(key=lambda r: (-r[key], -r["goals_for"]))
        return rows[:limit]
