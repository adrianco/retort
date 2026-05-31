"""
================================================================================
query_engine.py - Match / Team / Player / Competition / Statistics queries
================================================================================

CONTEXT
-------
Implements every capability required by the specification on top of the
in-memory :class:`DataStore`. Each public method returns a plain ``dict`` (so it
is trivially JSON-serialisable and unit-testable) and there is a matching
``format_*`` helper that renders the dict to the human-readable text shown in the
spec's "Example answer format" blocks. The MCP server (server.py) calls the
query method then the formatter.

Capability map (spec section -> methods):
    1. Match queries        -> find_matches, last_match
    2. Team queries         -> team_record, compare_teams
    3. Player queries       -> search_players, get_player, club_player_summary
    4. Competition queries  -> standings, competition_winner
    5. Statistical analysis -> head_to_head, league_statistics, biggest_wins,
                               best_record

All team inputs are matched via the canonical normalisation in normalize.py so
name variations ("Palmeiras-SP" vs "Palmeiras") resolve consistently.
================================================================================
"""

from __future__ import annotations

import datetime
from typing import Dict, List, Optional

from .data_loader import COMPETITION_NAMES, DataStore, Match, Player
from .normalize import (
    normalize_team,
    parse_date,
    strip_accents,
    team_display,
    team_matches_query,
)

# Friendly aliases users may type for a competition.
_COMPETITION_ALIASES = {
    "serie a": "serie_a",
    "seriea": "serie_a",
    "brasileirao": "serie_a",
    "brasileirao serie a": "serie_a",
    "brazilian serie a": "serie_a",
    "campeonato brasileiro": "serie_a",
    "serie b": "serie_b",
    "serie c": "serie_c",
    "copa do brasil": "copa_do_brasil",
    "brazilian cup": "copa_do_brasil",
    "cup": "copa_do_brasil",
    "libertadores": "libertadores",
    "copa libertadores": "libertadores",
}


def resolve_competition(value: Optional[str]) -> Optional[str]:
    """Map a free-text competition name to its internal family key."""
    if not value:
        return None
    if value in COMPETITION_NAMES:
        return value
    key = strip_accents(value).lower().strip()
    return _COMPETITION_ALIASES.get(key)


class QueryEngine:
    """Read-only query API over a :class:`DataStore`."""

    def __init__(self, store: DataStore):
        self.store = store

    # ------------------------------------------------------------------ #
    # internal selection helper
    # ------------------------------------------------------------------ #
    def _select(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        home_only: bool = False,
        away_only: bool = False,
        include_all_sources: bool = False,
    ) -> List[Match]:
        comp_key = resolve_competition(competition) if competition else None
        team_key = normalize_team(team) if team else None
        opp_key = normalize_team(opponent) if opponent else None

        out = []
        for m in self.store.matches:
            if not include_all_sources and not m.canonical:
                continue
            if comp_key and m.competition != comp_key:
                continue
            if season is not None and m.season != season:
                continue
            if date_from and (m.date is None or m.date < date_from):
                continue
            if date_to and (m.date is None or m.date > date_to):
                continue
            if team_key:
                if home_only and m.home_team != team_key:
                    continue
                if away_only and m.away_team != team_key:
                    continue
                if not home_only and not away_only and not m.involves(team_key):
                    continue
            if opp_key and not m.involves(opp_key):
                continue
            out.append(m)

        out.sort(key=lambda x: (x.date or datetime.date.min, x.competition))
        return out

    @staticmethod
    def _match_dict(m: Match) -> Dict:
        return {
            "date": m.date.isoformat() if m.date else None,
            "competition": m.competition_name,
            "season": m.season,
            "round": m.round,
            "stage": m.stage,
            "home_team": m.home_display,
            "away_team": m.away_display,
            "home_goal": m.home_goal,
            "away_goal": m.away_goal,
            "score": (f"{m.home_goal}-{m.away_goal}" if m.has_score else None),
            "arena": m.arena,
        }

    # ================================================================== #
    # 1. MATCH QUERIES
    # ================================================================== #
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        date_from=None,
        date_to=None,
        home_only: bool = False,
        away_only: bool = False,
        include_all_sources: bool = False,
        limit: Optional[int] = 50,
    ) -> Dict:
        """Find fixtures matching any combination of criteria."""
        matches = self._select(
            team=team, opponent=opponent, season=season, competition=competition,
            date_from=parse_date(date_from) if isinstance(date_from, str) else date_from,
            date_to=parse_date(date_to) if isinstance(date_to, str) else date_to,
            home_only=home_only, away_only=away_only,
            include_all_sources=include_all_sources,
        )
        total = len(matches)
        shown = matches if limit is None else matches[:limit]
        return {
            "query": {
                "team": team, "opponent": opponent, "season": season,
                "competition": competition,
            },
            "total": total,
            "returned": len(shown),
            "matches": [self._match_dict(m) for m in shown],
        }

    def last_match(self, team: str, opponent: str) -> Dict:
        """Most recent fixture between two teams (e.g. 'When did X last play Y?')."""
        matches = self._select(team=team, opponent=opponent)
        dated = [m for m in matches if m.date is not None]
        latest = max(dated, key=lambda m: m.date) if dated else (matches[-1] if matches else None)
        return {
            "team": team_display(team),
            "opponent": team_display(opponent),
            "found": latest is not None,
            "match": self._match_dict(latest) if latest else None,
            "total_meetings": len(matches),
        }

    # ================================================================== #
    # 2. TEAM QUERIES + 5. HEAD TO HEAD
    # ================================================================== #
    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        home_only: bool = False,
        away_only: bool = False,
    ) -> Dict:
        """Win/draw/loss + goals record for a team, optionally scoped."""
        team_key = normalize_team(team)
        matches = self._select(
            team=team, season=season, competition=competition,
            home_only=home_only, away_only=away_only,
        )
        wins = draws = losses = gf = ga = 0
        for m in matches:
            if not m.has_score:
                continue
            if m.home_team == team_key:
                mine, theirs = m.home_goal, m.away_goal
            else:
                mine, theirs = m.away_goal, m.home_goal
            gf += mine
            ga += theirs
            if mine > theirs:
                wins += 1
            elif mine < theirs:
                losses += 1
            else:
                draws += 1
        played = wins + draws + losses
        scope = "home" if home_only else "away" if away_only else "overall"
        return {
            "team": team_display(team),
            "season": season,
            "competition": COMPETITION_NAMES.get(resolve_competition(competition), competition)
            if competition else "all competitions",
            "scope": scope,
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

    def head_to_head(
        self, team1: str, team2: str, season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> Dict:
        """Aggregate head-to-head record and full meeting list between two teams."""
        k1, k2 = normalize_team(team1), normalize_team(team2)
        matches = self._select(team=team1, opponent=team2, season=season,
                               competition=competition)
        t1_wins = t2_wins = draws = t1_goals = t2_goals = 0
        for m in matches:
            if not m.has_score:
                continue
            if m.home_team == k1:
                g1, g2 = m.home_goal, m.away_goal
            else:
                g1, g2 = m.away_goal, m.home_goal
            t1_goals += g1
            t2_goals += g2
            if g1 > g2:
                t1_wins += 1
            elif g2 > g1:
                t2_wins += 1
            else:
                draws += 1
        return {
            "team1": team_display(team1),
            "team2": team_display(team2),
            "total_matches": len(matches),
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "team1_goals": t1_goals,
            "team2_goals": t2_goals,
            "matches": [self._match_dict(m) for m in matches],
        }

    def compare_teams(self, team1: str, team2: str, season: Optional[int] = None) -> Dict:
        """Side-by-side records plus their head-to-head."""
        return {
            "team1_record": self.team_record(team1, season=season),
            "team2_record": self.team_record(team2, season=season),
            "head_to_head": self.head_to_head(team1, team2, season=season),
        }

    def competitions_for_team(self, team: str) -> Dict:
        """Which competitions a team appears in across all datasets."""
        team_key = normalize_team(team)
        found = {}
        for m in self.store.matches:
            if m.involves(team_key):
                found.setdefault(m.competition_name, set())
                if m.season is not None:
                    found[m.competition_name].add(m.season)
        return {
            "team": team_display(team),
            "competitions": [
                {"competition": c, "seasons": sorted(s)} for c, s in sorted(found.items())
            ],
        }

    # ================================================================== #
    # 3. PLAYER QUERIES
    # ================================================================== #
    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort_by: str = "overall",
        limit: Optional[int] = 25,
    ) -> Dict:
        """Search the FIFA database by name/nationality/club/position/rating."""
        name_q = strip_accents(name).lower() if name else None
        nat_q = strip_accents(nationality).lower() if nationality else None
        club_key = normalize_team(club) if club else None
        pos_q = position.upper().strip() if position else None

        results: List[Player] = []
        for p in self.store.players:
            if name_q and name_q not in strip_accents(p.name).lower():
                continue
            if nat_q and nat_q not in strip_accents(p.nationality).lower():
                continue
            if club_key and p.club_key != club_key:
                continue
            if pos_q and p.position.upper() != pos_q:
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)

        reverse = sort_by in ("overall", "potential", "age")
        results.sort(key=lambda p: (getattr(p, sort_by, None) or 0), reverse=reverse)
        total = len(results)
        shown = results if limit is None else results[:limit]
        return {
            "query": {
                "name": name, "nationality": nationality, "club": club,
                "position": position, "min_overall": min_overall,
            },
            "total": total,
            "returned": len(shown),
            "players": [self._player_dict(p) for p in shown],
        }

    def get_player(self, name: str) -> Dict:
        """Look up a single player by (partial) name; returns the best match."""
        res = self.search_players(name=name, limit=10)
        players = res["players"]
        return {
            "query": name,
            "found": bool(players),
            "player": players[0] if players else None,
            "other_matches": players[1:5],
        }

    def club_player_summary(self, nationality: str = "Brazil", top: int = 10) -> Dict:
        """Player counts and average rating per Brazilian club (cross-club view)."""
        nat_q = strip_accents(nationality).lower()
        clubs: Dict[str, List[Player]] = {}
        for p in self.store.players:
            if nat_q and nat_q not in strip_accents(p.nationality).lower():
                continue
            if not p.club:
                continue
            clubs.setdefault(p.club, []).append(p)
        rows = []
        for club, players in clubs.items():
            rated = [p.overall for p in players if p.overall is not None]
            rows.append({
                "club": club,
                "players": len(players),
                "avg_overall": round(sum(rated) / len(rated), 1) if rated else None,
            })
        rows.sort(key=lambda r: (r["players"], r["avg_overall"] or 0), reverse=True)
        return {"nationality": nationality, "clubs": rows[:top]}

    @staticmethod
    def _player_dict(p: Player) -> Dict:
        return {
            "id": p.player_id,
            "name": p.name,
            "age": p.age,
            "nationality": p.nationality,
            "overall": p.overall,
            "potential": p.potential,
            "club": p.club,
            "position": p.position,
            "jersey_number": p.jersey_number,
            "height": p.height,
            "weight": p.weight,
            "preferred_foot": p.preferred_foot,
        }

    # ================================================================== #
    # 4. COMPETITION QUERIES
    # ================================================================== #
    def standings(self, season: int, competition: str = "serie_a") -> Dict:
        """League table for a season, computed from canonical match results."""
        comp_key = resolve_competition(competition) or competition
        matches = self._select(season=season, competition=comp_key)
        table: Dict[str, Dict] = {}

        def row(key: str, display: str):
            return table.setdefault(key, {
                "team": display, "P": 0, "W": 0, "D": 0, "L": 0,
                "GF": 0, "GA": 0, "Pts": 0,
            })

        for m in matches:
            if not m.has_score:
                continue
            h = row(m.home_team, m.home_display)
            a = row(m.away_team, m.away_display)
            h["P"] += 1
            a["P"] += 1
            h["GF"] += m.home_goal
            h["GA"] += m.away_goal
            a["GF"] += m.away_goal
            a["GA"] += m.home_goal
            if m.home_goal > m.away_goal:
                h["W"] += 1
                h["Pts"] += 3
                a["L"] += 1
            elif m.away_goal > m.home_goal:
                a["W"] += 1
                a["Pts"] += 3
                h["L"] += 1
            else:
                h["D"] += 1
                a["D"] += 1
                h["Pts"] += 1
                a["Pts"] += 1

        rows = list(table.values())
        for r in rows:
            r["GD"] = r["GF"] - r["GA"]
        # Official Brasileirão tie-break order: points, wins, goal difference,
        # goals for. (Head-to-head, the next official criterion, is omitted.)
        rows.sort(key=lambda r: (r["Pts"], r["W"], r["GD"], r["GF"]), reverse=True)
        for i, r in enumerate(rows, 1):
            r["position"] = i
        return {
            "season": season,
            "competition": COMPETITION_NAMES.get(comp_key, competition),
            "teams": len(rows),
            "table": rows,
            "champion": rows[0]["team"] if rows else None,
        }

    def competition_winner(self, season: int, competition: str = "serie_a") -> Dict:
        """Champion of a league season (top of the calculated standings)."""
        table = self.standings(season, competition)
        top = table["table"][0] if table["table"] else None
        return {
            "season": season,
            "competition": table["competition"],
            "champion": top["team"] if top else None,
            "champion_row": top,
        }

    def relegated(self, season: int, competition: str = "serie_a", count: int = 4) -> Dict:
        """Bottom-*count* teams of a season's standings (relegation zone)."""
        table = self.standings(season, competition)
        rows = table["table"]
        return {
            "season": season,
            "competition": table["competition"],
            "relegated": rows[-count:] if len(rows) >= count else rows,
        }

    # ================================================================== #
    # 5. STATISTICAL ANALYSIS
    # ================================================================== #
    def league_statistics(
        self, competition: str = "serie_a", season: Optional[int] = None,
    ) -> Dict:
        """Average goals per match, home win rate, totals for a competition."""
        comp_key = resolve_competition(competition) or competition
        matches = [m for m in self._select(season=season, competition=comp_key) if m.has_score]
        n = len(matches)
        if n == 0:
            return {
                "competition": COMPETITION_NAMES.get(comp_key, competition),
                "season": season, "matches": 0,
            }
        total_goals = sum(m.total_goals for m in matches)
        home_wins = sum(1 for m in matches if m.home_goal > m.away_goal)
        away_wins = sum(1 for m in matches if m.away_goal > m.home_goal)
        draws = n - home_wins - away_wins
        return {
            "competition": COMPETITION_NAMES.get(comp_key, competition),
            "season": season,
            "matches": n,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / n, 2),
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(100 * home_wins / n, 1),
            "away_win_rate": round(100 * away_wins / n, 1),
            "draw_rate": round(100 * draws / n, 1),
        }

    def biggest_wins(
        self, competition: Optional[str] = None, season: Optional[int] = None,
        limit: int = 10,
    ) -> Dict:
        """Largest goal-margin victories, optionally scoped to a competition."""
        matches = [m for m in self._select(season=season, competition=competition) if m.has_score]
        matches.sort(key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals), reverse=True)
        top = matches[:limit]
        return {
            "competition": (COMPETITION_NAMES.get(resolve_competition(competition), competition)
                            if competition else "all competitions"),
            "season": season,
            "matches": [
                {**self._match_dict(m), "margin": abs(m.home_goal - m.away_goal)} for m in top
            ],
        }

    def best_record(
        self, competition: str = "serie_a", season: Optional[int] = None,
        scope: str = "home", metric: str = "win_rate", min_matches: int = 5,
    ) -> Dict:
        """Rank teams by home/away/overall record (e.g. 'best home record')."""
        comp_key = resolve_competition(competition) or competition
        home_only = scope == "home"
        away_only = scope == "away"
        matches = self._select(season=season, competition=comp_key)
        teams = set()
        for m in matches:
            teams.add((m.home_team, m.home_display))
            teams.add((m.away_team, m.away_display))

        rows = []
        for key, display in teams:
            rec = self.team_record(display, season=season, competition=comp_key,
                                  home_only=home_only, away_only=away_only)
            if rec["matches"] >= min_matches:
                rows.append(rec)
        reverse = True
        rows.sort(key=lambda r: (r.get(metric, 0), r["goal_difference"]), reverse=reverse)
        return {
            "competition": COMPETITION_NAMES.get(comp_key, competition),
            "season": season,
            "scope": scope,
            "metric": metric,
            "ranking": rows[:15],
        }

    def top_scoring_team(self, competition: str = "serie_a", season: Optional[int] = None) -> Dict:
        """Team that scored the most goals in a competition/season."""
        table = self.standings(season, competition) if season else None
        if table and table["table"]:
            rows = sorted(table["table"], key=lambda r: r["GF"], reverse=True)
            return {
                "competition": table["competition"],
                "season": season,
                "ranking": [{"team": r["team"], "goals": r["GF"]} for r in rows[:10]],
            }
        # No season -> aggregate across all canonical seasons.
        comp_key = resolve_competition(competition) or competition
        scored: Dict[str, Dict] = {}
        for m in self._select(competition=comp_key):
            if not m.has_score:
                continue
            scored.setdefault(m.home_team, {"team": m.home_display, "goals": 0})["goals"] += m.home_goal
            scored.setdefault(m.away_team, {"team": m.away_display, "goals": 0})["goals"] += m.away_goal
        rows = sorted(scored.values(), key=lambda r: r["goals"], reverse=True)
        return {
            "competition": COMPETITION_NAMES.get(comp_key, competition),
            "season": None,
            "ranking": rows[:10],
        }

    # ------------------------------------------------------------------ #
    # meta
    # ------------------------------------------------------------------ #
    def data_summary(self) -> Dict:
        s = self.store.summary()
        s["seasons"] = self.store.seasons()
        s["competition_names"] = [COMPETITION_NAMES[c] for c in self.store.competitions()]
        return s
