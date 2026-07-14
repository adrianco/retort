# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : soccer_mcp.knowledge_graph
# Purpose : The in-memory knowledge graph and query API. Holds every Match and
#           Player record and exposes the query surface required by the spec:
#           match search, team statistics, head-to-head, player search,
#           competition standings, and aggregate statistics.
# Why no  : The spec/sample mentions Neo4j, but a graph database would require a
# Neo4j     running external server and make the test-suite non-hermetic. The
#           data volume (~24k matches, ~18k players) fits trivially in memory,
#           so we model the same entities/relationships as plain Python indexes
#           — teams, matches and players are the nodes; "played", "plays_for"
#           and "competed_in" are the edges, realised as lookups below. The
#           public method names mirror graph traversals (neighbours of a team,
#           edges between two teams, etc.).
# Perf    : Construction builds light indexes by competition and season so the
#           aggregate queries comfortably meet the <2s / <5s targets in the spec.
# =============================================================================

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from . import data_loader
from .models import Match, Player
from .normalize import normalize_team, normalize_text, team_matches


class KnowledgeGraph:
    """In-memory store + query API over matches and players."""

    def __init__(self, matches: List[Match], players: List[Player]):
        self.matches: List[Match] = matches
        self.players: List[Player] = players

        # Indexes (the "graph" adjacency structures).
        self._by_competition: Dict[str, List[Match]] = defaultdict(list)
        self._by_season: Dict[int, List[Match]] = defaultdict(list)
        self._team_keys: set = set()
        for m in matches:
            self._by_competition[m.competition].append(m)
            if m.season is not None:
                self._by_season[m.season].append(m)
            self._team_keys.add(m.home_team_norm)
            self._team_keys.add(m.away_team_norm)

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def load(cls, data_dir: str = data_loader.DEFAULT_DATA_DIR) -> "KnowledgeGraph":
        """Build a graph from the CSV files in `data_dir`."""
        matches, players = data_loader.load_all(data_dir)
        return cls(matches, players)

    # ------------------------------------------------------------------ #
    # Reference / metadata
    # ------------------------------------------------------------------ #
    def competitions(self) -> List[str]:
        return sorted(self._by_competition.keys())

    def seasons(self) -> List[int]:
        return sorted(self._by_season.keys())

    def team_count(self) -> int:
        return len(self._team_keys)

    # User-friendly competition inputs -> canonical competition label.
    _COMP_ALIASES = {
        "brasileirao": "Brasileirão",
        "brasileiro": "Brasileirão",
        "campeonato brasileiro": "Brasileirão",
        "serie a": "Brasileirão",
        "brasileirao serie a": "Brasileirão",
        "brasileirao serie b": "Brasileirão Série B",
        "serie b": "Brasileirão Série B",
        "brasileirao serie c": "Brasileirão Série C",
        "serie c": "Brasileirão Série C",
        "copa do brasil": "Copa do Brasil",
        "brazilian cup": "Copa do Brasil",
        "cup": "Copa do Brasil",
        "libertadores": "Libertadores",
        "copa libertadores": "Libertadores",
    }

    def _resolve_competitions(self, competition: str) -> List[str]:
        """Map a free-text competition name to the matching canonical labels.

        Resolution is exact (after alias + accent folding) so that asking for
        "Brasileirão" does not also pull in "Brasileirão Série B/C".
        """
        qn = normalize_text(competition)
        if qn in self._COMP_ALIASES:
            return [self._COMP_ALIASES[qn]]
        exact = [c for c in self._by_competition if normalize_text(c) == qn]
        if exact:
            return exact
        # Last resort: whole-word containment (handles e.g. unseen spellings)
        return [
            c for c in self._by_competition
            if qn and qn in normalize_text(c).split()
        ]

    def _competition_matches(self, competition: Optional[str]) -> List[Match]:
        """Return matches for a competition filter (or all matches if None)."""
        if not competition:
            return self.matches
        result: List[Match] = []
        for comp in self._resolve_competitions(competition):
            result.extend(self._by_competition.get(comp, []))
        return result

    # ------------------------------------------------------------------ #
    # 1. Match queries
    # ------------------------------------------------------------------ #
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        venue: Optional[str] = None,   # "home" | "away" | None, relative to `team`
        limit: Optional[int] = None,
    ) -> List[Match]:
        """Find matches by any combination of criteria.

        `venue` constrains where `team` played: "home", "away", or None (either).
        Results are sorted most-recent first.
        """
        pool = self._competition_matches(competition)
        out: List[Match] = []
        for m in pool:
            if season is not None and m.season != season:
                continue
            if start_date and (m.date is None or m.date < start_date):
                continue
            if end_date and (m.date is None or m.date > end_date):
                continue
            if team:
                is_home = team_matches(team, m.home_team_norm)
                is_away = team_matches(team, m.away_team_norm)
                if venue == "home" and not is_home:
                    continue
                if venue == "away" and not is_away:
                    continue
                if venue not in ("home", "away") and not (is_home or is_away):
                    continue
                if opponent:
                    opp_home = team_matches(opponent, m.home_team_norm)
                    opp_away = team_matches(opponent, m.away_team_norm)
                    # team and opponent must be the two sides of this match.
                    if not ((is_home and opp_away) or (is_away and opp_home)):
                        continue
            out.append(m)

        out.sort(key=lambda x: (x.date or "", x.source), reverse=True)
        if limit is not None:
            out = out[:limit]
        return out

    def head_to_head(self, team1: str, team2: str) -> dict:
        """Aggregate head-to-head record between two teams across all data."""
        games = self.find_matches(team=team1, opponent=team2)
        t1_wins = t2_wins = draws = t1_goals = t2_goals = 0
        for m in games:
            t1_home = team_matches(team1, m.home_team_norm)
            hg, ag = m.home_goal or 0, m.away_goal or 0
            t1g, t2g = (hg, ag) if t1_home else (ag, hg)
            t1_goals += t1g
            t2_goals += t2g
            if t1g > t2g:
                t1_wins += 1
            elif t2g > t1g:
                t2_wins += 1
            else:
                draws += 1
        return {
            "team1": team1,
            "team2": team2,
            "matches": len(games),
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "team1_goals": t1_goals,
            "team2_goals": t2_goals,
            "games": games,
        }

    # ------------------------------------------------------------------ #
    # 2. Team queries
    # ------------------------------------------------------------------ #
    def team_stats(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> dict:
        """Win/draw/loss + goal record for a team, optionally filtered."""
        games = self.find_matches(
            team=team, season=season, competition=competition, venue=venue
        )
        wins = draws = losses = gf = ga = 0
        for m in games:
            is_home = team_matches(team, m.home_team_norm)
            hg, ag = m.home_goal, m.away_goal
            if hg is None or ag is None:
                continue
            scored, conceded = (hg, ag) if is_home else (ag, hg)
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
            "win_rate": round(100 * wins / played, 1) if played else 0.0,
        }

    # ------------------------------------------------------------------ #
    # 3. Player queries
    # ------------------------------------------------------------------ #
    def find_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort_by: str = "overall",
        limit: Optional[int] = None,
    ) -> List[Player]:
        """Search the FIFA player database by any combination of criteria."""
        name_q = normalize_text(name) if name else None
        nat_q = normalize_text(nationality) if nationality else None
        pos_q = normalize_text(position) if position else None
        out: List[Player] = []
        for p in self.players:
            if name_q and name_q not in p.name_norm:
                continue
            if nat_q and nat_q not in normalize_text(p.nationality):
                continue
            if club and not team_matches(club, p.club_norm):
                continue
            if pos_q and pos_q != normalize_text(p.position):
                continue
            if min_overall is not None and (p.overall or 0) < min_overall:
                continue
            out.append(p)

        if sort_by == "overall":
            out.sort(key=lambda x: (x.overall or 0), reverse=True)
        elif sort_by == "potential":
            out.sort(key=lambda x: (x.potential or 0), reverse=True)
        elif sort_by == "age":
            out.sort(key=lambda x: (x.age or 0))
        elif sort_by == "name":
            out.sort(key=lambda x: x.name_norm)

        if limit is not None:
            out = out[:limit]
        return out

    def players_by_club_summary(self, nationality: Optional[str] = None) -> List[dict]:
        """Summarise players grouped by club (optionally one nationality).

        Powers answers like "Brazilian players at Brazilian clubs".
        """
        nat_q = normalize_text(nationality) if nationality else None
        buckets: Dict[str, List[Player]] = defaultdict(list)
        for p in self.players:
            if not p.club:
                continue
            if nat_q and nat_q not in normalize_text(p.nationality):
                continue
            buckets[p.club].append(p)
        summary = []
        for club, members in buckets.items():
            ratings = [m.overall for m in members if m.overall is not None]
            summary.append({
                "club": club,
                "players": len(members),
                "avg_overall": round(sum(ratings) / len(ratings), 1) if ratings else 0.0,
            })
        summary.sort(key=lambda x: (-x["players"], x["club"]))
        return summary

    # ------------------------------------------------------------------ #
    # 4. Competition queries
    # ------------------------------------------------------------------ #
    def standings(self, competition: str, season: int) -> List[dict]:
        """Compute a league table from match results (points: W=3, D=1).

        Tie-break: points, then goal difference, then goals scored.
        """
        games = self.find_matches(competition=competition, season=season)
        table: Dict[str, dict] = {}

        def row(team_raw: str) -> dict:
            key = normalize_team(team_raw)
            if key not in table:
                table[key] = {
                    "team": team_raw, "played": 0, "wins": 0, "draws": 0,
                    "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0,
                }
            return table[key]

        for m in games:
            if m.home_goal is None or m.away_goal is None:
                continue
            h, a = row(m.home_team), row(m.away_team)
            h["played"] += 1
            a["played"] += 1
            h["goals_for"] += m.home_goal
            h["goals_against"] += m.away_goal
            a["goals_for"] += m.away_goal
            a["goals_against"] += m.home_goal
            if m.home_goal > m.away_goal:
                h["wins"] += 1; h["points"] += 3; a["losses"] += 1
            elif m.away_goal > m.home_goal:
                a["wins"] += 1; a["points"] += 3; h["losses"] += 1
            else:
                h["draws"] += 1; a["draws"] += 1
                h["points"] += 1; a["points"] += 1

        rows = list(table.values())
        for r in rows:
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
        rows.sort(
            key=lambda r: (r["points"], r["goal_difference"], r["goals_for"]),
            reverse=True,
        )
        for i, r in enumerate(rows, start=1):
            r["position"] = i
        return rows

    def champion(self, competition: str, season: int) -> Optional[dict]:
        """Return the top row of the computed standings (league champion)."""
        table = self.standings(competition, season)
        return table[0] if table else None

    # ------------------------------------------------------------------ #
    # 5. Statistical analysis
    # ------------------------------------------------------------------ #
    def statistics(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        """Aggregate stats: goals/match, home win rate, totals."""
        pool = [
            m for m in self._competition_matches(competition)
            if season is None or m.season == season
        ]
        scored = [m for m in pool if m.home_goal is not None and m.away_goal is not None]
        total_goals = sum(m.total_goals for m in scored)
        home_wins = sum(1 for m in scored if (m.home_goal or 0) > (m.away_goal or 0))
        away_wins = sum(1 for m in scored if (m.away_goal or 0) > (m.home_goal or 0))
        draws = sum(1 for m in scored if m.is_draw)
        n = len(scored)
        return {
            "competition": competition,
            "season": season,
            "matches": n,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / n, 2) if n else 0.0,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(100 * home_wins / n, 1) if n else 0.0,
            "away_win_rate": round(100 * away_wins / n, 1) if n else 0.0,
            "draw_rate": round(100 * draws / n, 1) if n else 0.0,
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[Match]:
        """Matches with the largest goal margin, biggest first."""
        pool = [
            m for m in self._competition_matches(competition)
            if (season is None or m.season == season)
            and m.home_goal is not None and m.away_goal is not None
        ]
        pool.sort(
            key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals),
            reverse=True,
        )
        return pool[:limit]

    def top_scoring_teams(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[dict]:
        """Teams ranked by total goals scored within the filter."""
        pool = [
            m for m in self._competition_matches(competition)
            if (season is None or m.season == season)
            and m.home_goal is not None and m.away_goal is not None
        ]
        goals: Dict[str, dict] = {}
        for m in pool:
            for team_raw, scored in ((m.home_team, m.home_goal), (m.away_team, m.away_goal)):
                key = normalize_team(team_raw)
                entry = goals.setdefault(key, {"team": team_raw, "goals": 0, "matches": 0})
                entry["goals"] += scored
                entry["matches"] += 1
        ranked = sorted(goals.values(), key=lambda x: x["goals"], reverse=True)
        return ranked[:limit]
