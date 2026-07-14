"""
================================================================================
Brazilian Soccer MCP Server :: queries
================================================================================

Context
-------
The query engine sits on top of the KnowledgeGraph and implements the five
capability groups required by the specification:

  1. Match queries          (by team / date range / competition / season)
  2. Team queries           (records, goals, performance by competition)
  3. Player queries         (by name / nationality / club, ratings)
  4. Competition queries     (standings calculated from results, results lists)
  5. Statistical analysis   (averages, head-to-head, home/away, biggest wins)

Each method returns a plain dict/list (JSON-serialisable) so it can be handed
straight to the MCP layer. Companion `format_*` helpers render the human-facing
text shown in the specification's example answers.

All team inputs are resolved through KnowledgeGraph.resolve_team so that callers
may pass any naming variant ("Flamengo", "Flamengo-RJ", "flamengo").
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

from .data_loader import Match, Player
from .knowledge_graph import KnowledgeGraph


class QueryEngine:
    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    # ================================================================== #
    # Internal helpers
    # ================================================================== #
    def _resolve(self, team: str) -> Optional[str]:
        return self.graph.resolve_team(team)

    @staticmethod
    def _match_dict(m: Match) -> dict:
        return {
            "competition": m.competition,
            "season": m.season,
            "date": m.date.isoformat() if m.date else None,
            "round": m.round,
            "stage": m.stage,
            "home_team": m.home_team,
            "away_team": m.away_team,
            "home_goal": m.home_goal,
            "away_goal": m.away_goal,
            "arena": m.arena,
        }

    @staticmethod
    def _within_dates(m: Match, start: Optional[date], end: Optional[date]) -> bool:
        if start is None and end is None:
            return True
        if m.date is None:
            return False
        if start and m.date < start:
            return False
        if end and m.date > end:
            return False
        return True

    # ================================================================== #
    # 1. MATCH QUERIES
    # ================================================================== #
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        venue: str = "either",  # "home" | "away" | "either"
        limit: Optional[int] = None,
    ) -> dict:
        """Find matches by any combination of criteria."""
        # Choose the smallest candidate set to start from.
        if team is not None:
            key = self._resolve(team)
            if key is None:
                return {"query": {"team": team}, "count": 0, "matches": [],
                        "error": f"Unknown team: {team}"}
            candidates = self.graph.team_matches(key)
        else:
            candidates = self.graph.matches

        opp_key = self._resolve(opponent) if opponent else None
        if opponent and opp_key is None:
            return {"query": {"opponent": opponent}, "count": 0, "matches": [],
                    "error": f"Unknown team: {opponent}"}

        comp_l = competition.lower() if competition else None
        result: list[Match] = []
        team_key = self._resolve(team) if team else None
        for m in candidates:
            if comp_l and comp_l not in m.competition.lower():
                continue
            if season is not None and m.season != season:
                continue
            if not self._within_dates(m, start_date, end_date):
                continue
            if opp_key and opp_key not in (m.home_key, m.away_key):
                continue
            if team_key and venue == "home" and m.home_key != team_key:
                continue
            if team_key and venue == "away" and m.away_key != team_key:
                continue
            result.append(m)

        result.sort(key=lambda x: (x.date or date.min, x.competition), reverse=True)
        sliced = result[:limit] if limit else result
        out = {
            "query": {
                "team": team, "opponent": opponent, "competition": competition,
                "season": season,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "venue": venue,
            },
            "count": len(result),
            "returned": len(sliced),
            "matches": [self._match_dict(m) for m in sliced],
        }
        if team and opponent:
            out["head_to_head"] = self.head_to_head(team, opponent)["summary"]
        return out

    # ================================================================== #
    # 2. TEAM QUERIES
    # ================================================================== #
    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "either",
    ) -> dict:
        """Win/loss/draw record, goals for/against and win rate for a team."""
        key = self._resolve(team)
        if key is None:
            return {"team": team, "error": f"Unknown team: {team}"}

        comp_l = competition.lower() if competition else None
        rec = _Record()
        for m in self.graph.team_matches(key):
            if season is not None and m.season != season:
                continue
            if comp_l and comp_l not in m.competition.lower():
                continue
            is_home = m.home_key == key
            if venue == "home" and not is_home:
                continue
            if venue == "away" and is_home:
                continue
            rec.add(m, is_home)

        return {
            "team": self.graph.display_name(key),
            "season": season,
            "competition": competition,
            "venue": venue,
            **rec.as_dict(),
        }

    def compare_teams(
        self, team_a: str, team_b: str, competition: Optional[str] = None
    ) -> dict:
        """Head-to-head comparison plus each team's overall record."""
        h2h = self.head_to_head(team_a, team_b, competition=competition)
        return {
            "team_a": self.team_record(team_a, competition=competition),
            "team_b": self.team_record(team_b, competition=competition),
            "head_to_head": h2h,
        }

    # ================================================================== #
    # 3. PLAYER QUERIES
    # ================================================================== #
    @staticmethod
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
            "jersey_number": p.jersey_number,
            "height": p.height,
            "weight": p.weight,
            "preferred_foot": p.preferred_foot,
            "value": p.value,
        }

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort_by: str = "overall",
        limit: int = 25,
    ) -> dict:
        """Search the FIFA player database by any combination of filters."""
        players = self.graph.players
        if name:
            players = self.graph.find_players(name)
        if nationality:
            nat_l = nationality.lower()
            players = [p for p in players if p.nationality and p.nationality.lower() == nat_l]
        if club:
            club_key = self._resolve(club)
            # players use FIFA club names which may differ from match team names;
            # fall back to normalized club substring match.
            from .data_loader import normalize_team_name
            ck = club_key or normalize_team_name(club)
            players = [p for p in players if ck and ck in p.club_key]
        if position:
            pos_l = position.lower()
            players = [p for p in players if p.position and p.position.lower() == pos_l]
        if min_overall is not None:
            players = [p for p in players if (p.overall or 0) >= min_overall]

        reverse = sort_by in ("overall", "potential", "age")
        players = sorted(
            players,
            key=lambda p: (getattr(p, sort_by, 0) or 0) if sort_by != "name" else p.name.lower(),
            reverse=reverse,
        )
        sliced = players[:limit] if limit else players
        return {
            "query": {
                "name": name, "nationality": nationality, "club": club,
                "position": position, "min_overall": min_overall,
            },
            "count": len(players),
            "returned": len(sliced),
            "players": [self._player_dict(p) for p in sliced],
        }

    def players_at_brazilian_clubs(self, nationality: str = "Brazil") -> dict:
        """Group players of a nationality by club with average ratings."""
        players = self.graph.players_by_nationality(nationality)
        by_club: dict[str, list[Player]] = defaultdict(list)
        for p in players:
            if p.club:
                by_club[p.club].append(p)
        rows = []
        for club, ps in by_club.items():
            ratings = [p.overall for p in ps if p.overall is not None]
            rows.append({
                "club": club,
                "players": len(ps),
                "avg_overall": round(sum(ratings) / len(ratings), 1) if ratings else None,
            })
        rows.sort(key=lambda r: (-r["players"], -(r["avg_overall"] or 0)))
        return {"nationality": nationality, "total_players": len(players), "clubs": rows}

    # ================================================================== #
    # 4. COMPETITION QUERIES
    # ================================================================== #
    def standings(self, competition: str, season: int) -> dict:
        """Compute a league table from match results (3 pts win / 1 draw)."""
        matches = self.graph.matches_in(competition=competition, season=season)
        # Cross-file duplicates are already removed at load time; the residual
        # dedup below guards against any same-source repeats.
        seen = set()
        table: dict[str, _Record] = defaultdict(_Record)
        display: dict[str, str] = {}
        for m in matches:
            if m.home_goal is None or m.away_goal is None:
                continue
            dedup = (m.date, m.home_key, m.away_key, m.home_goal, m.away_goal)
            if dedup in seen:
                continue
            seen.add(dedup)
            table[m.home_key].add(m, is_home=True)
            table[m.away_key].add(m, is_home=False)
            display.setdefault(m.home_key, m.home_team)
            display.setdefault(m.away_key, m.away_team)

        rows = []
        for key, rec in table.items():
            d = rec.as_dict()
            d["team"] = self.graph.display_name(key) or display.get(key, key)
            rows.append(d)
        rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"]))
        for i, r in enumerate(rows, 1):
            r["position"] = i
        return {
            "competition": competition,
            "season": season,
            "teams": len(rows),
            "standings": rows,
        }

    def champion(self, competition: str, season: int) -> dict:
        table = self.standings(competition, season)
        champ = table["standings"][0] if table["standings"] else None
        return {"competition": competition, "season": season, "champion": champ}

    def relegated(self, competition: str, season: int, count: int = 4) -> dict:
        table = self.standings(competition, season)
        bottom = table["standings"][-count:] if table["standings"] else []
        return {
            "competition": competition,
            "season": season,
            "relegated": bottom,
        }

    # ================================================================== #
    # 5. STATISTICAL ANALYSIS
    # ================================================================== #
    def head_to_head(
        self, team_a: str, team_b: str, competition: Optional[str] = None
    ) -> dict:
        key_a = self._resolve(team_a)
        key_b = self._resolve(team_b)
        if key_a is None or key_b is None:
            missing = team_a if key_a is None else team_b
            return {"error": f"Unknown team: {missing}", "summary": {}}
        matches = self.graph.matches_between(key_a, key_b)
        comp_l = competition.lower() if competition else None
        a_wins = b_wins = draws = a_goals = b_goals = 0
        used = []
        for m in matches:
            if comp_l and comp_l not in m.competition.lower():
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            used.append(m)
            if m.home_key == key_a:
                a_goals += m.home_goal
                b_goals += m.away_goal
            else:
                a_goals += m.away_goal
                b_goals += m.home_goal
            w = m.winner_key
            if w == key_a:
                a_wins += 1
            elif w == key_b:
                b_wins += 1
            else:
                draws += 1
        name_a = self.graph.display_name(key_a)
        name_b = self.graph.display_name(key_b)
        return {
            "team_a": name_a,
            "team_b": name_b,
            "summary": {
                "matches": len(used),
                f"{name_a}_wins": a_wins,
                f"{name_b}_wins": b_wins,
                "draws": draws,
                f"{name_a}_goals": a_goals,
                f"{name_b}_goals": b_goals,
            },
            "matches_list": [self._match_dict(m) for m in used],
        }

    def competition_stats(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        """Average goals per match, home win rate, draw rate over a slice."""
        matches = self.graph.matches_in(competition=competition, season=season)
        played = [m for m in matches if m.home_goal is not None and m.away_goal is not None]
        n = len(played)
        if n == 0:
            return {"competition": competition, "season": season, "matches": 0}
        total_goals = sum(m.total_goals for m in played)
        home_wins = sum(1 for m in played if m.winner_key == m.home_key)
        away_wins = sum(1 for m in played if m.winner_key == m.away_key and not m.is_draw)
        draws = sum(1 for m in played if m.is_draw)
        return {
            "competition": competition,
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
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> dict:
        matches = self.graph.matches_in(competition=competition, season=season)
        played = [m for m in matches if m.total_goals is not None]
        played.sort(
            key=lambda m: (abs((m.home_goal or 0) - (m.away_goal or 0)), m.total_goals),
            reverse=True,
        )
        rows = []
        for m in played[:limit]:
            d = self._match_dict(m)
            d["margin"] = abs(m.home_goal - m.away_goal)
            rows.append(d)
        return {"competition": competition, "season": season, "biggest_wins": rows}

    def best_record(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: str = "either",
        metric: str = "win_rate",
        limit: int = 10,
    ) -> dict:
        """Rank teams by win rate (or points) over a competition/season slice."""
        matches = self.graph.matches_in(competition=competition, season=season)
        table: dict[str, _Record] = defaultdict(_Record)
        for m in matches:
            if m.home_goal is None or m.away_goal is None:
                continue
            if venue in ("either", "home"):
                table[m.home_key].add(m, is_home=True)
            if venue in ("either", "away"):
                table[m.away_key].add(m, is_home=False)
        rows = []
        for key, rec in table.items():
            d = rec.as_dict()
            d["team"] = self.graph.display_name(key)
            rows.append(d)
        # Only rank teams with a meaningful number of games.
        rows = [r for r in rows if r["played"] >= 5]
        sort_key = "win_rate" if metric == "win_rate" else "points"
        rows.sort(key=lambda r: (r[sort_key], r["goal_difference"]), reverse=True)
        return {
            "competition": competition,
            "season": season,
            "venue": venue,
            "metric": metric,
            "ranking": rows[:limit],
        }

    def top_scoring_teams(
        self, competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
    ) -> dict:
        matches = self.graph.matches_in(competition=competition, season=season)
        goals: dict[str, int] = defaultdict(int)
        for m in matches:
            if m.home_goal is not None:
                goals[m.home_key] += m.home_goal
            if m.away_goal is not None:
                goals[m.away_key] += m.away_goal
        rows = sorted(
            ({"team": self.graph.display_name(k), "goals": g} for k, g in goals.items()),
            key=lambda r: r["goals"],
            reverse=True,
        )
        return {"competition": competition, "season": season, "top_scorers": rows[:limit]}


# --------------------------------------------------------------------------- #
# Record accumulator
# --------------------------------------------------------------------------- #


class _Record:
    """Accumulates W/D/L and goals for a single team over a set of matches."""

    def __init__(self):
        self.played = self.wins = self.draws = self.losses = 0
        self.goals_for = self.goals_against = 0

    def add(self, m: Match, is_home: bool) -> None:
        if m.home_goal is None or m.away_goal is None:
            return
        gf, ga = (m.home_goal, m.away_goal) if is_home else (m.away_goal, m.home_goal)
        self.played += 1
        self.goals_for += gf
        self.goals_against += ga
        if gf > ga:
            self.wins += 1
        elif gf < ga:
            self.losses += 1
        else:
            self.draws += 1

    def as_dict(self) -> dict:
        return {
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goals_for - self.goals_against,
            "points": self.wins * 3 + self.draws,
            "win_rate": round(100 * self.wins / self.played, 1) if self.played else 0.0,
        }


# --------------------------------------------------------------------------- #
# Human-readable formatters (used by MCP layer / CLI)
# --------------------------------------------------------------------------- #


def format_matches(result: dict, max_rows: int = 15) -> str:
    if result.get("error"):
        return f"Error: {result['error']}"
    lines = []
    rows = result.get("matches", [])
    shown = rows[:max_rows]
    for m in shown:
        comp = m["competition"]
        rnd = f" Round {m['round']}" if m.get("round") else ""
        stage = f" {m['stage']}" if m.get("stage") else ""
        date_s = m["date"] or "????-??-??"
        lines.append(
            f"- {date_s}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']} ({comp}{rnd}{stage})"
        )
    remaining = result["count"] - len(shown)
    if remaining > 0:
        lines.append(f"... ({remaining} more matches in dataset)")
    header = f"Found {result['count']} match(es):"
    h2h = result.get("head_to_head")
    footer = ""
    if h2h:
        footer = "\n\nHead-to-head in dataset: " + _format_h2h_summary(h2h)
    return header + "\n" + "\n".join(lines) + footer


def _format_h2h_summary(summary: dict) -> str:
    parts = []
    for k, v in summary.items():
        if k.endswith("_wins"):
            parts.append(f"{k[:-5]} {v} wins")
    parts.append(f"{summary.get('draws', 0)} draws")
    return ", ".join(parts)


def format_team_record(rec: dict) -> str:
    if rec.get("error"):
        return f"Error: {rec['error']}"
    scope = []
    if rec.get("season"):
        scope.append(str(rec["season"]))
    if rec.get("competition"):
        scope.append(rec["competition"])
    if rec.get("venue") and rec["venue"] != "either":
        scope.append(f"{rec['venue']} only")
    scope_s = f" ({', '.join(scope)})" if scope else ""
    return (
        f"{rec['team']} record{scope_s}:\n"
        f"- Matches: {rec['played']}\n"
        f"- Wins: {rec['wins']}, Draws: {rec['draws']}, Losses: {rec['losses']}\n"
        f"- Goals For: {rec['goals_for']}, Goals Against: {rec['goals_against']}\n"
        f"- Win rate: {rec['win_rate']}%"
    )


def format_standings(table: dict, max_rows: int = 20) -> str:
    if not table.get("standings"):
        return f"No standings available for {table['competition']} {table['season']}."
    lines = [f"{table['competition']} {table['season']} standings (calculated from matches):"]
    for r in table["standings"][:max_rows]:
        tag = " - Champion" if r["position"] == 1 else ""
        lines.append(
            f"{r['position']}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L){tag}"
        )
    return "\n".join(lines)


def format_players(result: dict, max_rows: int = 25) -> str:
    rows = result.get("players", [])
    if not rows:
        return "No players found."
    lines = [f"Found {result['count']} player(s):"]
    for i, p in enumerate(rows[:max_rows], 1):
        lines.append(
            f"{i}. {p['name']} - Overall: {p['overall']}, "
            f"Position: {p['position']}, Club: {p['club']}"
        )
    return "\n".join(lines)
