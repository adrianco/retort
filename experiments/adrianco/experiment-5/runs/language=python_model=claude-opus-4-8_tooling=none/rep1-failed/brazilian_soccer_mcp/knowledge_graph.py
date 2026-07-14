"""
================================================================================
Brazilian Soccer MCP Server - Knowledge Graph / Query Engine
================================================================================

CONTEXT
-------
The in-memory query engine that backs every MCP tool. It holds the normalised
``Match`` and ``Player`` records produced by ``data_loader`` and exposes the
five capability families required by the specification
(``brazilian-soccer-mcp-guide.md``):

  1. Match queries        - find_matches, last_match, head_to_head
  2. Team queries         - team_stats, compare_teams
  3. Player queries       - find_players, get_player, club_summary
  4. Competition queries  - standings, champion, relegated, top_scoring_team
  5. Statistical analysis - average_goals_per_match, biggest_wins,
                            best_home_record, best_away_record

Design notes
  * Pure standard library; all aggregation is plain Python so the engine and
    its test-suite run with no third-party packages.
  * Team matching is tolerant of name variations via ``normalize.team_key``
    and ``normalize.names_match``.
  * For league standings the two overlapping Brasileirão sources (modern +
    historic) are de-duplicated on (season, home, away) so a season is never
    double counted.
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Any

from .models import Match, Player
from .normalize import (
    team_key,
    strip_accents,
    competition_matches,
    COMP_BRASILEIRAO,
)

# Points awarded in a league table.
WIN_POINTS = 3
DRAW_POINTS = 1


class KnowledgeGraph:
    """In-memory query engine over matches and players."""

    def __init__(self, matches: List[Match], players: List[Player]):
        self.matches: List[Match] = list(matches)
        self.players: List[Player] = list(players)
        # Index of match-key -> canonical display name (first seen).
        self._team_display: Dict[str, str] = {}
        for m in self.matches:
            self._team_display.setdefault(m.home_key, m.home_team)
            self._team_display.setdefault(m.away_key, m.away_team)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def display_name(self, name_or_key: str) -> str:
        """Return the best display name for a team query/key."""
        key = team_key(name_or_key)
        if key in self._team_display:
            return self._team_display[key]
        for k, disp in self._team_display.items():
            if key and (key in k or k in key):
                return disp
        return name_or_key

    def teams(self) -> List[str]:
        """Sorted list of all distinct team display names."""
        return sorted(set(self._team_display.values()))

    # ------------------------------------------------------------------ #
    # 1. Match queries
    # ------------------------------------------------------------------ #
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
        with_score_only: bool = False,
        limit: Optional[int] = None,
    ) -> List[Match]:
        """Return matches filtered by any combination of criteria.

        * ``team``      - involved as home OR away.
        * ``opponent``  - combined with ``team``, restricts to head-to-head.
        * ``home_team`` / ``away_team`` - exact side filters.
        * ``competition`` - alias-aware (see ``normalize.competition_matches``).
        * ``season``    - integer year.
        * ``start_date`` / ``end_date`` - inclusive ISO ``YYYY-MM-DD`` bounds.
        Results are sorted by date ascending (undated last).
        """
        results = []
        for m in self.matches:
            if team and not m.involves(team_key(team)):
                continue
            if opponent and not m.involves(team_key(opponent)):
                continue
            if home_team and m.home_key != team_key(home_team):
                continue
            if away_team and m.away_key != team_key(away_team):
                continue
            if competition and not competition_matches(competition, m.competition):
                continue
            if season is not None and m.season != int(season):
                continue
            if with_score_only and not m.has_score:
                continue
            if start_date and (m.date is None or m.date < start_date):
                continue
            if end_date and (m.date is None or m.date > end_date):
                continue
            results.append(m)

        results.sort(key=lambda x: (x.date is None, x.date or ""))
        if limit is not None:
            results = results[:limit]
        return results

    def last_match(
        self,
        team: str,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
    ) -> Optional[Match]:
        """Most recent match involving *team* (optionally vs *opponent*)."""
        found = self.find_matches(
            team=team, opponent=opponent, competition=competition
        )
        dated = [m for m in found if m.date]
        if not dated:
            return found[-1] if found else None
        return max(dated, key=lambda x: x.date)

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Head-to-head record between two teams across the dataset."""
        key_a = team_key(team_a)
        key_b = team_key(team_b)
        matches = self.find_matches(
            team=team_a, opponent=team_b, competition=competition, season=season
        )
        a_wins = b_wins = draws = 0
        a_goals = b_goals = 0
        for m in matches:
            if not m.has_score:
                continue
            if m.home_key == key_a:
                a_goals += m.home_goal
                b_goals += m.away_goal
            else:
                a_goals += m.away_goal
                b_goals += m.home_goal
            w = m.winner_key
            if w is None:
                draws += 1
            elif w == key_a:
                a_wins += 1
            elif w == key_b:
                b_wins += 1
        return {
            "team_a": self.display_name(team_a),
            "team_b": self.display_name(team_b),
            "matches": matches,
            "total": len(matches),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
        }

    # ------------------------------------------------------------------ #
    # 2. Team queries
    # ------------------------------------------------------------------ #
    def team_stats(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",      # "all" | "home" | "away"
    ) -> Dict[str, Any]:
        """Aggregate W/D/L, goals and win-rate for a team.

        ``venue`` restricts to home-only or away-only fixtures.
        """
        key = team_key(team)
        wins = draws = losses = 0
        gf = ga = 0
        played = 0
        matches = self.find_matches(
            team=team, competition=competition, season=season,
            with_score_only=True,
        )
        for m in matches:
            is_home = m.home_key == key
            if venue == "home" and not is_home:
                continue
            if venue == "away" and is_home:
                continue
            played += 1
            if is_home:
                gf += m.home_goal
                ga += m.away_goal
            else:
                gf += m.away_goal
                ga += m.home_goal
            w = m.winner_key
            if w is None:
                draws += 1
            elif w == key:
                wins += 1
            else:
                losses += 1
        win_rate = round(100.0 * wins / played, 1) if played else 0.0
        points = wins * WIN_POINTS + draws * DRAW_POINTS
        return {
            "team": self.display_name(team),
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
            "points": points,
            "win_rate": win_rate,
        }

    def compare_teams(
        self,
        team_a: str,
        team_b: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Side-by-side comparison of two teams plus their head-to-head."""
        return {
            "team_a": self.team_stats(team_a, season, competition),
            "team_b": self.team_stats(team_b, season, competition),
            "head_to_head": self.head_to_head(team_a, team_b, competition, season),
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
        sort_by_overall: bool = True,
        limit: Optional[int] = None,
    ) -> List[Player]:
        """Search the FIFA player database by any combination of filters."""
        name_q = strip_accents(name).lower() if name else None
        nat_q = strip_accents(nationality).lower() if nationality else None
        club_q = team_key(club) if club else None
        pos_q = position.lower() if position else None

        results = []
        for p in self.players:
            if name_q and name_q not in p.name_key:
                continue
            if nat_q and nat_q != p.nationality_key and nat_q not in p.nationality_key:
                continue
            if club_q:
                if not p.club_key:
                    continue
                if club_q not in p.club_key and p.club_key not in club_q:
                    continue
            if pos_q and (not p.position or pos_q != p.position.lower()):
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)

        if sort_by_overall:
            results.sort(key=lambda x: (x.overall is None, -(x.overall or 0)))
        if limit is not None:
            results = results[:limit]
        return results

    def get_player(self, name: str) -> Optional[Player]:
        """Return the best single match for a player name query."""
        found = self.find_players(name=name)
        if not found:
            return None
        target = strip_accents(name).lower()
        exact = [p for p in found if p.name_key == target]
        if exact:
            return max(exact, key=lambda x: x.overall or 0)
        return found[0]

    def club_summary(self, club: str) -> Dict[str, Any]:
        """Player count and average rating for a club."""
        players = self.find_players(club=club)
        ratings = [p.overall for p in players if p.overall is not None]
        avg = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
        return {
            "club": club,
            "player_count": len(players),
            "average_overall": avg,
            "players": players,
        }

    # ------------------------------------------------------------------ #
    # 4. Competition queries
    # ------------------------------------------------------------------ #
    def _dedup_season_matches(self, matches: List[Match]) -> List[Match]:
        """Drop duplicate fixtures that appear in more than one source for the
        same season (modern vs historic Brasileirão)."""
        seen = set()
        out = []
        for m in matches:
            sig = (m.season, m.home_key, m.away_key)
            if sig in seen:
                continue
            seen.add(sig)
            out.append(m)
        return out

    def standings(
        self,
        season: int,
        competition: str = COMP_BRASILEIRAO,
    ) -> List[Dict[str, Any]]:
        """Compute a league table for *season* from match results.

        Returns rows sorted by points, then goal difference, then goals for.
        Only meaningful for round-robin leagues (Brasileirão).
        """
        matches = self.find_matches(
            competition=competition, season=int(season), with_score_only=True
        )
        matches = self._dedup_season_matches(matches)

        table: Dict[str, Dict[str, Any]] = {}

        def row(key: str, display: str) -> Dict[str, Any]:
            if key not in table:
                table[key] = {
                    "team": display, "played": 0, "wins": 0, "draws": 0,
                    "losses": 0, "goals_for": 0, "goals_against": 0,
                    "goal_difference": 0, "points": 0,
                }
            return table[key]

        for m in matches:
            h = row(m.home_key, m.home_team)
            a = row(m.away_key, m.away_team)
            h["played"] += 1
            a["played"] += 1
            h["goals_for"] += m.home_goal
            h["goals_against"] += m.away_goal
            a["goals_for"] += m.away_goal
            a["goals_against"] += m.home_goal
            if m.home_goal > m.away_goal:
                h["wins"] += 1
                a["losses"] += 1
            elif m.away_goal > m.home_goal:
                a["wins"] += 1
                h["losses"] += 1
            else:
                h["draws"] += 1
                a["draws"] += 1

        for r in table.values():
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
            r["points"] = r["wins"] * WIN_POINTS + r["draws"] * DRAW_POINTS

        ranked = sorted(
            table.values(),
            key=lambda r: (r["points"], r["goal_difference"], r["goals_for"]),
            reverse=True,
        )
        for i, r in enumerate(ranked, start=1):
            r["position"] = i
        return ranked

    def champion(
        self, season: int, competition: str = COMP_BRASILEIRAO
    ) -> Optional[Dict[str, Any]]:
        """Return the top row of the computed standings, or ``None``."""
        table = self.standings(season, competition)
        return table[0] if table else None

    def relegated(
        self,
        season: int,
        competition: str = COMP_BRASILEIRAO,
        count: int = 4,
    ) -> List[Dict[str, Any]]:
        """Return the bottom *count* teams of the standings (relegation zone)."""
        table = self.standings(season, competition)
        return table[-count:] if table else []

    def top_scoring_team(
        self,
        season: int,
        competition: str = COMP_BRASILEIRAO,
    ) -> Optional[Dict[str, Any]]:
        """Team that scored the most goals in a season."""
        table = self.standings(season, competition)
        if not table:
            return None
        return max(table, key=lambda r: r["goals_for"])

    def seasons(self, competition: Optional[str] = None) -> List[int]:
        """Sorted list of distinct seasons available (optionally per comp)."""
        ss = set()
        for m in self.matches:
            if competition and not competition_matches(competition, m.competition):
                continue
            if m.season is not None:
                ss.add(m.season)
        return sorted(ss)

    def competitions(self) -> List[str]:
        """Sorted list of distinct competition labels."""
        return sorted({m.competition for m in self.matches if m.competition})

    # ------------------------------------------------------------------ #
    # 5. Statistical analysis
    # ------------------------------------------------------------------ #
    def average_goals_per_match(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> float:
        """Average total goals per match for the filtered set."""
        matches = self.find_matches(
            competition=competition, season=season, with_score_only=True
        )
        if not matches:
            return 0.0
        total = sum(m.total_goals for m in matches)
        return round(total / len(matches), 2)

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[Match]:
        """Matches with the largest goal margin, biggest first."""
        matches = self.find_matches(
            competition=competition, season=season, with_score_only=True
        )
        matches.sort(
            key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals),
            reverse=True,
        )
        return matches[:limit]

    def best_home_record(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 5,
    ) -> List[Dict[str, Any]]:
        """Teams ranked by home win-rate (min match threshold)."""
        return self._venue_ranking("home", competition, season, min_matches)

    def best_away_record(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 5,
    ) -> List[Dict[str, Any]]:
        """Teams ranked by away win-rate (min match threshold)."""
        return self._venue_ranking("away", competition, season, min_matches)

    def _venue_ranking(
        self,
        venue: str,
        competition: Optional[str],
        season: Optional[int],
        min_matches: int,
    ) -> List[Dict[str, Any]]:
        agg: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"team": "", "matches": 0, "wins": 0, "draws": 0,
                     "losses": 0, "goals_for": 0, "goals_against": 0}
        )
        matches = self.find_matches(
            competition=competition, season=season, with_score_only=True
        )
        for m in matches:
            if venue == "home":
                key, disp, gf, ga = m.home_key, m.home_team, m.home_goal, m.away_goal
                won = m.home_goal > m.away_goal
                lost = m.home_goal < m.away_goal
            else:
                key, disp, gf, ga = m.away_key, m.away_team, m.away_goal, m.home_goal
                won = m.away_goal > m.home_goal
                lost = m.away_goal < m.home_goal
            r = agg[key]
            r["team"] = disp
            r["matches"] += 1
            r["goals_for"] += gf
            r["goals_against"] += ga
            if won:
                r["wins"] += 1
            elif lost:
                r["losses"] += 1
            else:
                r["draws"] += 1
        rows = []
        for r in agg.values():
            if r["matches"] < min_matches:
                continue
            r["win_rate"] = round(100.0 * r["wins"] / r["matches"], 1)
            rows.append(r)
        rows.sort(key=lambda r: (r["win_rate"], r["wins"]), reverse=True)
        return rows
