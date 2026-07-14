"""
================================================================================
Context
================================================================================
Module:   knowledge_graph.py
Project:  Brazilian Soccer MCP Server
Purpose:  The in-memory knowledge graph and query engine that powers every MCP
          tool.  It ingests the normalized Match/Player records from
          data_loader and exposes higher-level queries spanning the five
          capability categories required by the specification:
              1. Match queries          (find_matches, match_between)
              2. Team queries           (team_stats, head_to_head, compare_teams)
              3. Player queries         (search_players, top_players)
              4. Competition queries    (standings, list_seasons)
              5. Statistical analysis   (biggest_wins, average_goals, best_record)

Design:
    * Entities are indexed by canonical team key (see team_names.normalize_team)
      so the same club is found regardless of which dataset / spelling a query
      uses.  This is the "graph": team nodes connected to match edges and player
      nodes connected to club nodes.
    * Pure standard library; deterministic; no external database required, which
      keeps the system fast (<2s lookups) and its tests hermetic.
    * Match deduplication: Série A and Copa do Brasil appear in more than one
      source file.  Standings / aggregate queries deduplicate fixtures by
      (competition, season, home_key, away_key) using a source priority order so
      the same game is never counted twice.

Dependencies: data_loader, team_names (standard library only).
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional

import data_loader
from data_loader import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    SERIE_C,
    Match,
    Player,
)
from team_names import display_team, normalize_team

# Source preference when deduplicating overlapping fixtures (best first).
_SOURCE_PRIORITY = {
    "brasileirao": 0,
    "novo": 1,
    "copa_do_brasil": 0,
    "libertadores": 0,
    "br-football": 5,
}

# User-facing competition aliases -> canonical label.
_COMPETITION_ALIASES = {
    "brasileirao": SERIE_A,
    "brasileirão": SERIE_A,
    "serie a": SERIE_A,
    "série a": SERIE_A,
    "campeonato brasileiro": SERIE_A,
    "serie b": SERIE_B,
    "série b": SERIE_B,
    "serie c": SERIE_C,
    "série c": SERIE_C,
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "cup": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
}


def resolve_competition(name: Optional[str]) -> Optional[str]:
    """Map a free-text competition name to a canonical label (or None)."""
    if not name:
        return None
    key = name.strip().lower()
    if key in _COMPETITION_ALIASES:
        return _COMPETITION_ALIASES[key]
    # Allow already-canonical values through unchanged.
    for canonical in (SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES):
        if key == canonical.lower():
            return canonical
    return name  # unknown -> pass through so it simply matches nothing


@dataclass
class TableRow:
    position: int
    team: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    points: int

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return (self.wins / self.played * 100.0) if self.played else 0.0


class KnowledgeGraph:
    """Indexed, queryable view over all matches and players."""

    def __init__(self, matches: list[Match], players: list[Player]):
        self.matches = matches
        self.players = players

        # Graph indexes -------------------------------------------------
        self._matches_by_team: dict[str, list[Match]] = defaultdict(list)
        self._players_by_club: dict[str, list[Player]] = defaultdict(list)
        self._players_by_nationality: dict[str, list[Player]] = defaultdict(list)
        self._team_display: dict[str, str] = {}

        for m in matches:
            self._matches_by_team[m.home_key].append(m)
            self._matches_by_team[m.away_key].append(m)
            self._team_display.setdefault(m.home_key, m.home_team)
            self._team_display.setdefault(m.away_key, m.away_team)

        for p in players:
            if p.club_key:
                self._players_by_club[p.club_key].append(p)
            if p.nationality:
                self._players_by_nationality[p.nationality.lower()].append(p)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def load(cls, data_dir: Optional[str] = None) -> "KnowledgeGraph":
        return cls(
            data_loader.load_matches(data_dir),
            data_loader.load_players(data_dir),
        )

    # ------------------------------------------------------------------
    # Team / name helpers
    # ------------------------------------------------------------------
    def team_display(self, team: str) -> str:
        key = normalize_team(team)
        return self._team_display.get(key, display_team(team))

    def known_teams(self) -> list[str]:
        return sorted(self._team_display.values())

    # ------------------------------------------------------------------
    # 1. Match queries
    # ------------------------------------------------------------------
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        venue: str = "either",
        dedup: bool = False,
        limit: Optional[int] = None,
    ) -> list[Match]:
        """
        Return matches filtered by any combination of criteria, most recent
        first (matches without a date sort last).

        venue: 'home', 'away' or 'either' (relative to `team`).
        """
        comp = resolve_competition(competition)
        team_key = normalize_team(team) if team else None
        opp_key = normalize_team(opponent) if opponent else None

        if team_key is not None:
            candidates: Iterable[Match] = self._matches_by_team.get(team_key, [])
        else:
            candidates = self.matches

        results: list[Match] = []
        for m in candidates:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != season:
                continue
            if team_key is not None:
                if venue == "home" and m.home_key != team_key:
                    continue
                if venue == "away" and m.away_key != team_key:
                    continue
            if opp_key is not None and not m.involves(opp_key):
                continue
            if opp_key is not None and team_key is not None and opp_key == team_key:
                pass
            if start_date and (m.date is None or m.date < start_date):
                continue
            if end_date and (m.date is None or m.date > end_date):
                continue
            results.append(m)

        if dedup:
            results = self._dedup(results)

        results.sort(key=lambda x: (x.date is not None, x.date or date.min), reverse=True)
        if limit is not None:
            results = results[:limit]
        return results

    def match_between(
        self,
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        dedup: bool = True,
    ) -> list[Match]:
        """All matches between two specific teams (either venue)."""
        return self.find_matches(
            team=team_a,
            opponent=team_b,
            competition=competition,
            season=season,
            dedup=dedup,
        )

    @staticmethod
    def _dedup(matches: list[Match]) -> list[Match]:
        """
        Remove cross-source duplication of fixtures.

        Série A and Copa do Brasil appear in more than one source file with
        overlapping seasons.  For each (competition, season) we keep only the
        single highest-priority source present (e.g. the dedicated brasileirao
        file rather than the broader BR-Football dataset), which both collapses
        duplicated fixtures and excludes stray rows that exist in one source but
        not the authoritative one.  Seasons covered by only one source (e.g.
        2003-2011 in novo) are kept as-is.
        """
        if not matches:
            return []
        # Best (lowest) priority available per (competition, season).
        best_prio: dict[tuple, int] = {}
        for m in matches:
            group = (m.competition, m.season)
            prio = _SOURCE_PRIORITY.get(m.source, 9)
            if group not in best_prio or prio < best_prio[group]:
                best_prio[group] = prio
        return [
            m
            for m in matches
            if _SOURCE_PRIORITY.get(m.source, 9)
            == best_prio[(m.competition, m.season)]
        ]

    # Backwards-friendly alias used by standings (single comp+season group).
    _select_primary_source = _dedup

    # ------------------------------------------------------------------
    # 2. Team queries
    # ------------------------------------------------------------------
    def team_stats(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "either",
    ) -> dict:
        """Aggregate W/D/L, goals and win-rate for a team."""
        team_key = normalize_team(team)
        matches = self.find_matches(
            team=team,
            competition=competition,
            season=season,
            venue=venue,
            dedup=True,
        )
        wins = draws = losses = gf = ga = 0
        counted = 0
        for m in matches:
            if m.home_goal is None or m.away_goal is None:
                continue
            counted += 1
            if m.home_key == team_key:
                team_goals, opp_goals = m.home_goal, m.away_goal
            else:
                team_goals, opp_goals = m.away_goal, m.home_goal
            gf += team_goals
            ga += opp_goals
            if team_goals > opp_goals:
                wins += 1
            elif team_goals < opp_goals:
                losses += 1
            else:
                draws += 1
        return {
            "team": self.team_display(team),
            "season": season,
            "competition": resolve_competition(competition),
            "venue": venue,
            "matches": counted,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": round(wins / counted * 100.0, 1) if counted else 0.0,
        }

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        """Head-to-head record between two teams from team_a's perspective."""
        key_a = normalize_team(team_a)
        key_b = normalize_team(team_b)
        matches = self.match_between(team_a, team_b, competition, season, dedup=True)
        a_wins = b_wins = draws = 0
        a_goals = b_goals = 0
        for m in matches:
            if m.home_goal is None or m.away_goal is None:
                continue
            if m.home_key == key_a:
                ga, gb = m.home_goal, m.away_goal
            else:
                ga, gb = m.away_goal, m.home_goal
            a_goals += ga
            b_goals += gb
            if ga > gb:
                a_wins += 1
            elif gb > ga:
                b_wins += 1
            else:
                draws += 1
        return {
            "team_a": self.team_display(team_a),
            "team_b": self.team_display(team_b),
            "total_matches": len(matches),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
            "matches": matches,
        }

    def compare_teams(self, team_a: str, team_b: str, season: Optional[int] = None) -> dict:
        return {
            "head_to_head": self.head_to_head(team_a, team_b, season=season),
            "team_a_stats": self.team_stats(team_a, season=season),
            "team_b_stats": self.team_stats(team_b, season=season),
        }

    # ------------------------------------------------------------------
    # 3. Player queries
    # ------------------------------------------------------------------
    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: Optional[int] = 50,
    ) -> list[Player]:
        """Search players by any combination of criteria, best rated first."""
        name_q = name.strip().lower() if name else None
        nat_q = nationality.strip().lower() if nationality else None
        pos_q = position.strip().upper() if position else None
        club_key = normalize_team(club) if club else None

        results: list[Player] = []
        for p in self.players:
            if name_q and name_q not in p.name.lower():
                continue
            if nat_q and p.nationality.lower() != nat_q:
                continue
            if club_key and p.club_key != club_key:
                continue
            if pos_q and p.position.upper() != pos_q:
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)

        results.sort(key=lambda x: (x.overall is not None, x.overall or 0), reverse=True)
        if limit is not None:
            results = results[:limit]
        return results

    def top_players(
        self,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        limit: int = 10,
    ) -> list[Player]:
        return self.search_players(
            nationality=nationality, club=club, limit=limit
        )

    def brazilian_players_by_club(self, limit_clubs: int = 20) -> list[dict]:
        """Group Brazilian-national players by club with average rating."""
        groups: dict[str, list[Player]] = defaultdict(list)
        for p in self._players_by_nationality.get("brazil", []):
            if p.club:
                groups[p.club].append(p)
        summary = []
        for club, plist in groups.items():
            rated = [p.overall for p in plist if p.overall is not None]
            summary.append(
                {
                    "club": club,
                    "count": len(plist),
                    "avg_overall": round(sum(rated) / len(rated), 1) if rated else 0.0,
                }
            )
        summary.sort(key=lambda x: (x["count"], x["avg_overall"]), reverse=True)
        return summary[:limit_clubs]

    # ------------------------------------------------------------------
    # 4. Competition queries
    # ------------------------------------------------------------------
    def list_seasons(self, competition: Optional[str] = None) -> list[int]:
        comp = resolve_competition(competition)
        seasons = {
            m.season
            for m in self.matches
            if m.season and (comp is None or m.competition == comp)
        }
        return sorted(seasons)

    def list_competitions(self) -> list[str]:
        return sorted({m.competition for m in self.matches})

    def standings(self, competition: str, season: int) -> list[TableRow]:
        """
        Compute a league table for a competition+season from match results.
        Fixtures are deduplicated so overlapping source files do not double
        count.  Sorted by points, goal difference, goals for, then wins.
        """
        comp = resolve_competition(competition)
        matches = self._select_primary_source(
            [
                m
                for m in self.matches
                if m.competition == comp
                and m.season == season
                and m.home_goal is not None
                and m.away_goal is not None
            ]
        )

        acc: dict[str, dict] = {}

        def slot(key: str, display: str) -> dict:
            if key not in acc:
                acc[key] = {
                    "team": display,
                    "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0,
                }
            return acc[key]

        for m in matches:
            h = slot(m.home_key, m.home_team)
            a = slot(m.away_key, m.away_team)
            h["P"] += 1
            a["P"] += 1
            h["GF"] += m.home_goal
            h["GA"] += m.away_goal
            a["GF"] += m.away_goal
            a["GA"] += m.home_goal
            if m.home_goal > m.away_goal:
                h["W"] += 1; h["Pts"] += 3; a["L"] += 1
            elif m.away_goal > m.home_goal:
                a["W"] += 1; a["Pts"] += 3; h["L"] += 1
            else:
                h["D"] += 1; a["D"] += 1; h["Pts"] += 1; a["Pts"] += 1

        rows = sorted(
            acc.values(),
            key=lambda r: (r["Pts"], r["GF"] - r["GA"], r["GF"], r["W"]),
            reverse=True,
        )
        return [
            TableRow(
                position=i + 1,
                team=r["team"],
                played=r["P"],
                wins=r["W"],
                draws=r["D"],
                losses=r["L"],
                goals_for=r["GF"],
                goals_against=r["GA"],
                points=r["Pts"],
            )
            for i, r in enumerate(rows)
        ]

    def champion(self, competition: str, season: int) -> Optional[TableRow]:
        table = self.standings(competition, season)
        return table[0] if table else None

    # ------------------------------------------------------------------
    # 5. Statistical analysis
    # ------------------------------------------------------------------
    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> list[Match]:
        comp = resolve_competition(competition)
        played = [
            m
            for m in self._dedup(self.matches)
            if m.home_goal is not None
            and m.away_goal is not None
            and (comp is None or m.competition == comp)
            and (season is None or m.season == season)
        ]
        played.sort(
            key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals or 0),
            reverse=True,
        )
        return played[:limit]

    def average_goals(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        comp = resolve_competition(competition)
        played = [
            m
            for m in self._dedup(self.matches)
            if m.home_goal is not None
            and m.away_goal is not None
            and (comp is None or m.competition == comp)
            and (season is None or m.season == season)
        ]
        n = len(played)
        if n == 0:
            return {
                "competition": comp,
                "season": season,
                "matches": 0,
                "avg_goals_per_match": 0.0,
                "home_win_rate": 0.0,
                "away_win_rate": 0.0,
                "draw_rate": 0.0,
            }
        total = sum(m.total_goals for m in played)
        home_wins = sum(1 for m in played if m.home_goal > m.away_goal)
        away_wins = sum(1 for m in played if m.away_goal > m.home_goal)
        draws = n - home_wins - away_wins
        return {
            "competition": comp,
            "season": season,
            "matches": n,
            "avg_goals_per_match": round(total / n, 2),
            "total_goals": total,
            "home_win_rate": round(home_wins / n * 100.0, 1),
            "away_win_rate": round(away_wins / n * 100.0, 1),
            "draw_rate": round(draws / n * 100.0, 1),
        }

    def best_record(
        self,
        venue: str = "either",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 5,
        limit: int = 10,
    ) -> list[dict]:
        """Rank teams by win-rate for a venue (home/away/either)."""
        comp = resolve_competition(competition)
        team_keys = set()
        for m in self.matches:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != season:
                continue
            team_keys.add(m.home_key)
            team_keys.add(m.away_key)

        records = []
        for key in team_keys:
            stats = self.team_stats(
                self._team_display.get(key, key),
                season=season,
                competition=competition,
                venue=venue,
            )
            if stats["matches"] >= min_matches:
                records.append(stats)
        records.sort(key=lambda s: (s["win_rate"], s["goal_difference"]), reverse=True)
        return records[:limit]
