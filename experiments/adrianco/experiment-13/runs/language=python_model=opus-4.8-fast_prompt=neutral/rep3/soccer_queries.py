"""
=============================================================================
 Brazilian Soccer MCP Server -- Query Engine ("knowledge graph" interface)
=============================================================================
 Purpose
 -------
 Implements every query capability required by the specification on top of
 the normalized records produced by `soccer_data.py`:

   1. Match queries     -> find_matches, last_match, head_to_head
   2. Team queries      -> team_record, compare_teams
   3. Player queries    -> search_players, players_by_club,
                           players_by_nationality, top_players
   4. Competition queries -> standings, list_seasons / competitions
   5. Statistical analysis -> competition_stats, biggest_wins,
                              best_record (home/away/overall)

 Each public method returns plain Python dicts/lists (JSON-serializable) so
 the MCP server can hand them straight to the LLM, and so the test-suite can
 assert on them directly without any MCP runtime.

 Design notes
 ------------
 * Pure standard library; no third-party dependencies.
 * Team and competition filters are fuzzy and accent-insensitive (see
   `soccer_data.team_matches`).
 * League standings and records are *computed from match results* (3 pts for
   a win, 1 for a draw) exactly as the spec requests.
=============================================================================
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

from soccer_data import (
    Match,
    Player,
    SoccerDatabase,
    canonical_key,
    get_db,
    strip_accents,
)


def _comp_matches(query: str, competition: str) -> bool:
    """Fuzzy, accent-insensitive competition matching."""
    if not query:
        return True
    q = strip_accents(query).lower().strip()
    c = strip_accents(competition).lower()
    # common shorthands
    aliases = {
        "brasileirao": "brasileirao serie a",
        "brasileiro": "brasileirao serie a",
        "serie a": "brasileirao serie a",
        "libertadores": "copa libertadores",
        "copa do brasil": "copa do brasil",
        "cup": "copa do brasil",
    }
    q = aliases.get(q, q)
    return q in c or c in q


class SoccerQueryEngine:
    """All query capabilities over a loaded :class:`SoccerDatabase`."""

    def __init__(self, db: Optional[SoccerDatabase] = None):
        self.db = db or get_db()

    # ====================================================================
    # 1. MATCH QUERIES
    # ====================================================================

    def find_matches(
        self,
        team: Optional[str] = None,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        season_from: Optional[int] = None,
        season_to: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Find matches by any combination of team/competition/season/date.

        `team` matches home OR away; `opponent` (used with `team`) requires
        the other side to be that opponent.
        """
        df = _parse_iso(date_from)
        dt = _parse_iso(date_to)
        results = []
        for m in self.db.matches:
            if competition and not _comp_matches(competition, m.competition):
                continue
            if season is not None and m.season != season:
                continue
            if season_from is not None and (m.season is None or m.season < season_from):
                continue
            if season_to is not None and (m.season is None or m.season > season_to):
                continue
            if df and (m.date is None or m.date < df):
                continue
            if dt and (m.date is None or m.date > dt):
                continue
            if home_team and not _tm(home_team, m.home_team):
                continue
            if away_team and not _tm(away_team, m.away_team):
                continue
            if team and not m.involves(team):
                continue
            if opponent:
                # the side that is NOT `team` must be the opponent
                if team and _tm(team, m.home_team):
                    if not _tm(opponent, m.away_team):
                        continue
                elif team and _tm(team, m.away_team):
                    if not _tm(opponent, m.home_team):
                        continue
                elif not m.involves(opponent):
                    continue
            results.append(m)

        results.sort(key=_match_sort_key)
        total = len(results)
        shown = results[-limit:][::-1] if limit else results[::-1]
        return {
            "count": total,
            "returned": len(shown),
            "matches": [_match_dict(m) for m in shown],
        }

    def last_match(self, team_a: str, team_b: str) -> dict:
        """Most recent match between two teams."""
        h2h = [
            m
            for m in self.db.matches
            if m.involves(team_a) and m.involves(team_b)
        ]
        h2h.sort(key=_match_sort_key)
        if not h2h:
            return {"found": False, "message": f"No matches found between {team_a} and {team_b}."}
        m = h2h[-1]
        return {"found": True, "match": _match_dict(m)}

    def head_to_head(
        self, team_a: str, team_b: str, competition: Optional[str] = None
    ) -> dict:
        """Full head-to-head record and match list between two teams."""
        a_wins = b_wins = draws = a_goals = b_goals = 0
        matches = []
        for m in self.db.matches:
            if not (m.involves(team_a) and m.involves(team_b)):
                continue
            if competition and not _comp_matches(competition, m.competition):
                continue
            matches.append(m)
            if not m.has_score:
                continue
            # figure out which side is team_a
            if _tm(team_a, m.home_team):
                ag, bg = m.home_goal, m.away_goal
            else:
                ag, bg = m.away_goal, m.home_goal
            a_goals += ag
            b_goals += bg
            if ag > bg:
                a_wins += 1
            elif bg > ag:
                b_wins += 1
            else:
                draws += 1
        matches.sort(key=_match_sort_key)
        name_a = _display_name(matches, team_a) or team_a
        name_b = _display_name(matches, team_b) or team_b
        return {
            "team_a": name_a,
            "team_b": name_b,
            "total_matches": len(matches),
            f"{name_a}_wins": a_wins,
            f"{name_b}_wins": b_wins,
            "draws": draws,
            f"{name_a}_goals": a_goals,
            f"{name_b}_goals": b_goals,
            "summary": (
                f"In {len(matches)} matches: {name_a} {a_wins} wins, "
                f"{name_b} {b_wins} wins, {draws} draws."
            ),
            "matches": [_match_dict(m) for m in matches[::-1]],
        }

    # ====================================================================
    # 2. TEAM QUERIES
    # ====================================================================

    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",   # "all" | "home" | "away"
    ) -> dict:
        """Win/draw/loss record and goals for/against, computed from matches."""
        venue = (venue or "all").lower()
        played = wins = draws = losses = gf = ga = 0
        display = None
        for m in self.db.matches:
            if not m.involves(team):
                continue
            if season is not None and m.season != season:
                continue
            if competition and not _comp_matches(competition, m.competition):
                continue
            if not m.has_score:
                continue
            is_home = _tm(team, m.home_team)
            if venue == "home" and not is_home:
                continue
            if venue == "away" and is_home:
                continue
            display = m.home_team if is_home else m.away_team
            if is_home:
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
            "team": display or team,
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
            "win_rate_pct": win_rate,
        }

    def compare_teams(
        self, team_a: str, team_b: str, season: Optional[int] = None
    ) -> dict:
        """Side-by-side records plus head-to-head between two teams."""
        return {
            "team_a_record": self.team_record(team_a, season=season),
            "team_b_record": self.team_record(team_b, season=season),
            "head_to_head": self.head_to_head(team_a, team_b),
        }

    # ====================================================================
    # 3. PLAYER QUERIES
    # ====================================================================

    def search_players(self, name: str, limit: int = 25) -> dict:
        q = strip_accents(name or "").lower().strip()
        hits = [
            p
            for p in self.db.players
            if q in strip_accents(p.name).lower()
        ]
        hits.sort(key=lambda p: (-(p.overall or 0), p.name))
        return {
            "query": name,
            "count": len(hits),
            "players": [_player_dict(p) for p in hits[:limit]],
        }

    def players_by_nationality(
        self, nationality: str = "Brazil", limit: int = 25
    ) -> dict:
        q = strip_accents(nationality or "").lower().strip()
        hits = [
            p
            for p in self.db.players
            if q in strip_accents(p.nationality).lower()
        ]
        hits.sort(key=lambda p: (-(p.overall or 0), p.name))
        return {
            "nationality": nationality,
            "count": len(hits),
            "players": [_player_dict(p) for p in hits[:limit]],
        }

    def players_by_club(
        self, club: str, position: Optional[str] = None, limit: int = 25
    ) -> dict:
        q = strip_accents(club or "").lower().strip()
        hits = []
        for p in self.db.players:
            if q not in strip_accents(p.club).lower():
                continue
            if position and strip_accents(position).lower() not in strip_accents(
                p.position
            ).lower():
                continue
            hits.append(p)
        hits.sort(key=lambda p: (-(p.overall or 0), p.name))
        avg = (
            round(sum(p.overall for p in hits if p.overall is not None) /
                  max(1, len([p for p in hits if p.overall is not None])), 1)
            if hits else 0.0
        )
        return {
            "club": club,
            "position": position,
            "count": len(hits),
            "avg_overall": avg,
            "players": [_player_dict(p) for p in hits[:limit]],
        }

    def top_players(
        self,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        natq = strip_accents(nationality or "").lower().strip()
        clubq = strip_accents(club or "").lower().strip()
        posq = strip_accents(position or "").lower().strip()
        hits = []
        for p in self.db.players:
            if natq and natq not in strip_accents(p.nationality).lower():
                continue
            if clubq and clubq not in strip_accents(p.club).lower():
                continue
            if posq and posq not in strip_accents(p.position).lower():
                continue
            hits.append(p)
        hits.sort(key=lambda p: (-(p.overall or 0), p.name))
        return {
            "nationality": nationality,
            "club": club,
            "position": position,
            "count": len(hits),
            "players": [_player_dict(p) for p in hits[:limit]],
        }

    # ====================================================================
    # 4. COMPETITION QUERIES
    # ====================================================================

    def standings(
        self, season: int, competition: str = "Brasileirão Série A"
    ) -> dict:
        """Compute a league table from match results for a season."""
        table = defaultdict(lambda: {
            "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "points": 0,
        })
        display = {}
        for m in self.db.matches:
            if m.season != season:
                continue
            if not _comp_matches(competition, m.competition):
                continue
            if not m.has_score:
                continue
            for team, scored, conceded in (
                (m.home_team, m.home_goal, m.away_goal),
                (m.away_team, m.away_goal, m.home_goal),
            ):
                key = canonical_key(team)
                display.setdefault(key, team)
                row = table[key]
                row["played"] += 1
                row["goals_for"] += scored
                row["goals_against"] += conceded
                if scored > conceded:
                    row["wins"] += 1
                    row["points"] += 3
                elif scored < conceded:
                    row["losses"] += 1
                else:
                    row["draws"] += 1
                    row["points"] += 1

        rows = []
        for key, row in table.items():
            row = dict(row)
            row["team"] = display[key]
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
            rows.append(row)
        rows.sort(
            key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"])
        )
        for i, r in enumerate(rows, 1):
            r["position"] = i
        return {
            "competition": competition,
            "season": season,
            "teams": len(rows),
            "champion": rows[0]["team"] if rows else None,
            "standings": rows,
        }

    def list_competitions(self) -> dict:
        return {"competitions": self.db.competitions()}

    def list_seasons(self, competition: Optional[str] = None) -> dict:
        seasons = sorted({
            m.season
            for m in self.db.matches
            if m.season is not None
            and (not competition or _comp_matches(competition, m.competition))
        })
        return {"competition": competition, "seasons": seasons}

    # ====================================================================
    # 5. STATISTICAL ANALYSIS
    # ====================================================================

    def competition_stats(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        """Aggregate stats: avg goals/match, home win rate, etc."""
        scored = [
            m
            for m in self.db.matches
            if m.has_score
            and (not competition or _comp_matches(competition, m.competition))
            and (season is None or m.season == season)
        ]
        n = len(scored)
        if n == 0:
            return {"matches": 0, "message": "No matches found for the given filters."}
        goals = sum(m.total_goals for m in scored)
        home_wins = sum(1 for m in scored if m.home_goal > m.away_goal)
        away_wins = sum(1 for m in scored if m.away_goal > m.home_goal)
        draws = n - home_wins - away_wins
        return {
            "competition": competition or "all",
            "season": season,
            "matches": n,
            "total_goals": goals,
            "avg_goals_per_match": round(goals / n, 2),
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate_pct": round(100.0 * home_wins / n, 1),
            "away_win_rate_pct": round(100.0 * away_wins / n, 1),
            "draw_rate_pct": round(100.0 * draws / n, 1),
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        team: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """Matches with the largest goal margin."""
        cands = [
            m
            for m in self.db.matches
            if m.has_score
            and (not competition or _comp_matches(competition, m.competition))
            and (season is None or m.season == season)
            and (not team or m.involves(team))
        ]
        cands.sort(
            key=lambda m: (-abs(m.home_goal - m.away_goal), -(m.total_goals or 0))
        )
        out = []
        for m in cands[:limit]:
            d = _match_dict(m)
            d["margin"] = abs(m.home_goal - m.away_goal)
            out.append(d)
        return {
            "competition": competition or "all",
            "season": season,
            "count": len(out),
            "matches": out,
        }

    def best_record(
        self,
        venue: str = "home",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_games: int = 5,
        metric: str = "win_rate",   # "win_rate" | "points"
        limit: int = 10,
    ) -> dict:
        """Rank teams by home/away/overall record computed from matches."""
        venue = (venue or "home").lower()
        agg = defaultdict(lambda: {"played": 0, "wins": 0, "draws": 0,
                                   "losses": 0, "gf": 0, "ga": 0})
        display = {}
        for m in self.db.matches:
            if not m.has_score:
                continue
            if competition and not _comp_matches(competition, m.competition):
                continue
            if season is not None and m.season != season:
                continue
            sides = []
            if venue in ("home", "all"):
                sides.append((m.home_team, m.home_goal, m.away_goal))
            if venue in ("away", "all"):
                sides.append((m.away_team, m.away_goal, m.home_goal))
            for team, scored, conceded in sides:
                key = canonical_key(team)
                display.setdefault(key, team)
                row = agg[key]
                row["played"] += 1
                row["gf"] += scored
                row["ga"] += conceded
                if scored > conceded:
                    row["wins"] += 1
                elif scored < conceded:
                    row["losses"] += 1
                else:
                    row["draws"] += 1

        rows = []
        for key, row in agg.items():
            if row["played"] < min_games:
                continue
            points = row["wins"] * 3 + row["draws"]
            win_rate = round(100.0 * row["wins"] / row["played"], 1)
            rows.append({
                "team": display[key],
                "played": row["played"],
                "wins": row["wins"],
                "draws": row["draws"],
                "losses": row["losses"],
                "goals_for": row["gf"],
                "goals_against": row["ga"],
                "points": points,
                "win_rate_pct": win_rate,
            })
        sort_key = "win_rate_pct" if metric == "win_rate" else "points"
        rows.sort(key=lambda r: (-r[sort_key], -r["points"], r["team"]))
        return {
            "venue": venue,
            "competition": competition or "all",
            "season": season,
            "metric": metric,
            "min_games": min_games,
            "teams": rows[:limit],
        }

    # ====================================================================
    # Meta
    # ====================================================================

    def database_summary(self) -> dict:
        return self.db.summary()


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------

# alias to keep call-sites short
def _tm(query: str, team_name: str) -> bool:
    from soccer_data import team_matches
    return team_matches(query, team_name)


def _parse_iso(s: Optional[str]) -> Optional[date]:
    from soccer_data import parse_date
    return parse_date(s) if s else None


def _match_sort_key(m: Match):
    # Sort chronologically; matches without a date fall back to season.
    return (
        m.date or date(m.season or 1, 1, 1),
        m.season or 0,
    )


def _match_dict(m: Match) -> dict:
    return {
        "date": m.date.isoformat() if m.date else None,
        "season": m.season,
        "competition": m.competition,
        "stage": m.stage,
        "home_team": m.home_team,
        "away_team": m.away_team,
        "home_goal": m.home_goal,
        "away_goal": m.away_goal,
        "winner": m.winner(),
        "source": m.source,
        "summary": m.describe(),
    }


def _player_dict(p: Player) -> dict:
    return {
        "id": p.player_id,
        "name": p.name,
        "age": p.age,
        "nationality": p.nationality,
        "overall": p.overall,
        "potential": p.potential,
        "club": p.club,
        "position": p.position,
        "value": p.value,
        "preferred_foot": p.preferred_foot,
        "jersey_number": p.jersey_number,
    }


def _display_name(matches, query: str) -> Optional[str]:
    """Pick a representative display name for a fuzzy team query."""
    for m in matches:
        if _tm(query, m.home_team):
            return m.home_team
        if _tm(query, m.away_team):
            return m.away_team
    return None
