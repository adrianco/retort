"""
================================================================================
 Module: queries
================================================================================
Context
-------
The high-level query API that sits on top of the KnowledgeGraph.  Every method
here corresponds to one of the capability categories in the specification:

  1. Match queries          -> find_matches, last_match_between
  2. Team queries           -> team_record, head_to_head, top_scoring_team
  3. Player queries         -> search_players, players_at_club, top_players
  4. Competition queries    -> standings, champion, relegated_teams
  5. Statistical analysis   -> average_goals, biggest_wins, best_home_record,
                               best_away_record, compare_seasons

Each method returns a structured ``dict`` (easy to assert on in tests and to
serialize over MCP).  Companion ``format_*`` helpers render those dicts into the
human-readable answer format shown in the specification, which the MCP server
returns to the LLM.

Standings use the standard 3-1-0 points system and the usual tie-breakers
(points, wins, goal difference, goals for).
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from .data_loader import Match, Player
from .knowledge_graph import KnowledgeGraph


class SoccerQueryEngine:
    """Stateless query layer over a :class:`KnowledgeGraph`."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    # ====================================================== 1. MATCH QUERIES
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        matches = self.graph.filter_matches(
            team=team, opponent=opponent, competition=competition,
            season=season, date_from=date_from, date_to=date_to,
        )
        total = len(matches)
        shown = matches if limit is None else matches[:limit]
        result = {
            "count": total,
            "matches": [m.to_dict() for m in shown],
        }
        if team and opponent:
            result["head_to_head"] = self._h2h_from_matches(team, opponent, matches)
        return result

    def last_match_between(self, team_a: str, team_b: str) -> Optional[dict]:
        matches = self.graph.filter_matches(team=team_a, opponent=team_b)
        dated = [m for m in matches if m.date]
        if not dated:
            return matches[-1].to_dict() if matches else None
        return max(dated, key=lambda m: m.date).to_dict()

    # ======================================================= 2. TEAM QUERIES
    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,   # "home", "away", or None for all
    ) -> dict:
        node = self.graph.resolve_team(team)
        if node is None:
            return {"found": False, "team": team}

        home_only_for = team if venue == "home" else None
        matches = self.graph.filter_matches(
            team=team, competition=competition, season=season,
            home_only_for=home_only_for,
        )
        if venue == "away":
            matches = [m for m in matches if m.away_key == node.key]

        rec = self._empty_record()
        for m in matches:
            self._accumulate(rec, m, node.key)
        rec["found"] = True
        rec["team"] = node.display_name
        rec["season"] = season
        rec["competition"] = competition
        rec["venue"] = venue or "all"
        rec["win_rate"] = round(100.0 * rec["wins"] / rec["matches"], 1) if rec["matches"] else 0.0
        return rec

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        matches = self.graph.filter_matches(
            team=team_a, opponent=team_b, competition=competition, season=season,
        )
        return self._h2h_from_matches(team_a, team_b, matches, include_matches=True)

    def top_scoring_team(
        self, season: Optional[int] = None, competition: Optional[str] = None,
        limit: int = 1,
    ) -> dict:
        standings = self._compute_standings(season=season, competition=competition)
        ranked = sorted(standings, key=lambda r: (-r["goals_for"], -r["goal_diff"]))
        return {"season": season, "competition": competition,
                "teams": ranked[:limit]}

    # ===================================================== 3. PLAYER QUERIES
    def search_players(self, name: str, limit: int = 10) -> dict:
        players = self.graph.search_players_by_name(name)
        return {"count": len(players),
                "players": [p.to_dict() for p in players[:limit]]}

    def players_at_club(self, club: str, limit: int = 25,
                        position: Optional[str] = None) -> dict:
        players = self.graph.players_by_club(club)
        if position:
            pos = position.strip().lower()
            players = [p for p in players if p.position.lower() == pos]
        players = sorted(players, key=lambda p: -(p.overall or 0))
        avg = round(sum(p.overall or 0 for p in players) / len(players), 1) if players else 0.0
        return {
            "club": self.graph.team_display_name(club) or club,
            "count": len(players),
            "average_overall": avg,
            "players": [p.to_dict() for p in players[:limit]],
        }

    def top_players(
        self,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        if club:
            players = self.graph.players_by_club(club)
        elif nationality:
            players = self.graph.players_by_nationality(nationality)
        else:
            players = list(self.graph.players)
        if nationality and club:
            nat = nationality.strip().lower()
            players = [p for p in players if p.nationality.lower() == nat]
        if position:
            pos = position.strip().lower()
            players = [p for p in players if p.position.lower() == pos]
        players = sorted(players, key=lambda p: -(p.overall or 0))
        return {
            "nationality": nationality,
            "club": club,
            "position": position,
            "count": len(players),
            "players": [p.to_dict() for p in players[:limit]],
        }

    def brazilian_players_by_club(self, limit: int = 10) -> dict:
        """Brazilian players grouped by their (Brazilian or otherwise) club."""
        brazilians = self.graph.players_by_nationality("Brazil")
        by_club: Dict[str, List[Player]] = defaultdict(list)
        for p in brazilians:
            if p.club:
                by_club[p.club].append(p)
        groups = []
        for club, plist in by_club.items():
            groups.append({
                "club": club,
                "count": len(plist),
                "average_overall": round(sum(pl.overall or 0 for pl in plist) / len(plist), 1),
            })
        groups.sort(key=lambda g: (-g["count"], -g["average_overall"]))
        return {"total_brazilians": len(brazilians), "clubs": groups[:limit]}

    # ================================================ 4. COMPETITION QUERIES
    def standings(self, season: int, competition: str = "Brasileirão") -> dict:
        table = self._compute_standings(season=season, competition=competition)
        table.sort(key=self._standings_sort_key)
        for pos, row in enumerate(table, start=1):
            row["position"] = pos
        return {"season": season, "competition": competition, "table": table}

    def champion(self, season: int, competition: str = "Brasileirão") -> dict:
        table = self.standings(season, competition)["table"]
        champ = table[0] if table else None
        return {"season": season, "competition": competition, "champion": champ}

    def relegated_teams(self, season: int, competition: str = "Brasileirão",
                        count: int = 4) -> dict:
        table = self.standings(season, competition)["table"]
        relegated = table[-count:] if len(table) >= count else table
        return {"season": season, "competition": competition,
                "relegated": list(reversed(relegated))}

    # ================================================= 5. STATISTICAL QUERIES
    def average_goals(self, competition: Optional[str] = None,
                      season: Optional[int] = None) -> dict:
        matches = self.graph.filter_matches(competition=competition, season=season)
        n = len(matches)
        if n == 0:
            return {"matches": 0, "average_goals": 0.0, "home_win_rate": 0.0,
                    "competition": competition, "season": season}
        total = sum(m.total_goals for m in matches)
        home_wins = sum(1 for m in matches if m.home_goal > m.away_goal)
        draws = sum(1 for m in matches if m.home_goal == m.away_goal)
        return {
            "matches": n,
            "average_goals": round(total / n, 2),
            "home_win_rate": round(100.0 * home_wins / n, 1),
            "draw_rate": round(100.0 * draws / n, 1),
            "away_win_rate": round(100.0 * (n - home_wins - draws) / n, 1),
            "competition": competition,
            "season": season,
        }

    def biggest_wins(self, competition: Optional[str] = None,
                     season: Optional[int] = None, limit: int = 10) -> dict:
        matches = self.graph.filter_matches(competition=competition, season=season)
        ranked = sorted(
            matches,
            key=lambda m: (-abs(m.home_goal - m.away_goal), -m.total_goals,
                           m.date or ""),
        )
        return {"competition": competition, "season": season,
                "matches": [m.to_dict() for m in ranked[:limit]]}

    def best_home_record(self, season: Optional[int] = None,
                         competition: Optional[str] = None,
                         min_matches: int = 5, limit: int = 5) -> dict:
        return self._best_venue_record("home", season, competition, min_matches, limit)

    def best_away_record(self, season: Optional[int] = None,
                         competition: Optional[str] = None,
                         min_matches: int = 5, limit: int = 5) -> dict:
        return self._best_venue_record("away", season, competition, min_matches, limit)

    def compare_seasons(self, season_a: int, season_b: int,
                        competition: Optional[str] = None) -> dict:
        return {
            "competition": competition,
            "season_a": self.average_goals(competition, season_a),
            "season_b": self.average_goals(competition, season_b),
        }

    # ============================================================ INTERNALS
    @staticmethod
    def _empty_record() -> dict:
        return {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0}

    @staticmethod
    def _accumulate(rec: dict, m: Match, key: str) -> None:
        if m.home_key == key:
            gf, ga = m.home_goal, m.away_goal
        else:
            gf, ga = m.away_goal, m.home_goal
        rec["matches"] += 1
        rec["goals_for"] += gf
        rec["goals_against"] += ga
        if gf > ga:
            rec["wins"] += 1
        elif gf < ga:
            rec["losses"] += 1
        else:
            rec["draws"] += 1

    def _h2h_from_matches(self, team_a: str, team_b: str,
                          matches: List[Match], include_matches: bool = False) -> dict:
        node_a = self.graph.resolve_team(team_a)
        node_b = self.graph.resolve_team(team_b)
        name_a = node_a.display_name if node_a else team_a
        name_b = node_b.display_name if node_b else team_b
        key_a = node_a.key if node_a else None
        wins_a = wins_b = draws = 0
        for m in matches:
            if m.winner_key is None:
                draws += 1
            elif m.winner_key == key_a:
                wins_a += 1
            else:
                wins_b += 1
        out = {
            "team_a": name_a, "team_b": name_b,
            "total_matches": len(matches),
            "team_a_wins": wins_a, "team_b_wins": wins_b, "draws": draws,
        }
        if include_matches:
            out["matches"] = [m.to_dict() for m in matches]
        return out

    def _compute_standings(self, season: Optional[int] = None,
                           competition: Optional[str] = None) -> List[dict]:
        matches = self.graph.filter_matches(season=season, competition=competition)
        rows: Dict[str, dict] = {}
        names: Dict[str, str] = {}
        for m in matches:
            for key, name in ((m.home_key, m.home_team), (m.away_key, m.away_team)):
                if key not in rows:
                    rows[key] = self._empty_record()
                    rows[key]["key"] = key
                    names[key] = name
            self._accumulate(rows[m.home_key], m, m.home_key)
            self._accumulate(rows[m.away_key], m, m.away_key)
        table = []
        for key, rec in rows.items():
            node = self.graph.teams.get(key)
            rec["team"] = node.display_name if node else names.get(key, key)
            rec["points"] = rec["wins"] * 3 + rec["draws"]
            rec["goal_diff"] = rec["goals_for"] - rec["goals_against"]
            rec.pop("key", None)
            table.append(rec)
        return table

    @staticmethod
    def _standings_sort_key(row: dict):
        return (-row["points"], -row["wins"], -row["goal_diff"], -row["goals_for"])

    def _best_venue_record(self, venue: str, season, competition,
                           min_matches: int, limit: int) -> dict:
        matches = self.graph.filter_matches(season=season, competition=competition)
        agg: Dict[str, dict] = {}
        for m in matches:
            key = m.home_key if venue == "home" else m.away_key
            if key not in agg:
                agg[key] = self._empty_record()
            self._accumulate(agg[key], m, key)
        rows = []
        for key, rec in agg.items():
            if rec["matches"] < min_matches:
                continue
            node = self.graph.teams.get(key)
            rec["team"] = node.display_name if node else key
            rec["win_rate"] = round(100.0 * rec["wins"] / rec["matches"], 1)
            rows.append(rec)
        rows.sort(key=lambda r: (-r["win_rate"], -(r["goals_for"] - r["goals_against"])))
        return {"venue": venue, "season": season, "competition": competition,
                "teams": rows[:limit]}


# ============================================================= FORMATTERS
def _score_line(m: dict) -> str:
    comp = m.get("competition", "")
    rnd = m.get("round")
    stage = m.get("stage")
    tag = comp
    if rnd:
        tag = f"{comp} Round {rnd}"
    elif stage:
        tag = f"{comp} - {stage}"
    date = m.get("date") or "date n/a"
    return (f"- {date}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']} ({tag})")


def format_matches(result: dict, title: str = "Matches", show: int = 15) -> str:
    lines = [f"{title} ({result['count']} found):"]
    for m in result["matches"][:show]:
        lines.append(_score_line(m))
    remaining = result["count"] - min(show, len(result["matches"]))
    if remaining > 0:
        lines.append(f"- ... ({remaining} more)")
    h2h = result.get("head_to_head")
    if h2h:
        lines.append("")
        lines.append(
            f"Head-to-head: {h2h['team_a']} {h2h['team_a_wins']} wins, "
            f"{h2h['team_b']} {h2h['team_b_wins']} wins, {h2h['draws']} draws"
        )
    return "\n".join(lines)


def format_team_record(rec: dict) -> str:
    if not rec.get("found"):
        return f"No data found for team '{rec.get('team')}'."
    scope = []
    if rec.get("season"):
        scope.append(str(rec["season"]))
    if rec.get("competition"):
        scope.append(rec["competition"])
    if rec.get("venue") and rec["venue"] != "all":
        scope.append(f"{rec['venue']} only")
    scope_str = f" ({', '.join(scope)})" if scope else ""
    return (
        f"{rec['team']} record{scope_str}:\n"
        f"- Matches: {rec['matches']}\n"
        f"- Wins: {rec['wins']}, Draws: {rec['draws']}, Losses: {rec['losses']}\n"
        f"- Goals For: {rec['goals_for']}, Goals Against: {rec['goals_against']}\n"
        f"- Win rate: {rec['win_rate']}%"
    )


def format_head_to_head(h2h: dict) -> str:
    return (
        f"Head-to-head: {h2h['team_a']} vs {h2h['team_b']}\n"
        f"- Total matches: {h2h['total_matches']}\n"
        f"- {h2h['team_a']} wins: {h2h['team_a_wins']}\n"
        f"- {h2h['team_b']} wins: {h2h['team_b_wins']}\n"
        f"- Draws: {h2h['draws']}"
    )


def format_players(result: dict, title: str = "Players") -> str:
    lines = [f"{title} ({result['count']} found):"]
    for i, p in enumerate(result["players"], start=1):
        lines.append(
            f"{i}. {p['name']} - Overall: {p['overall']}, "
            f"Position: {p['position'] or 'N/A'}, Club: {p['club'] or 'N/A'}"
        )
    return "\n".join(lines)


def format_standings(result: dict, show: int = 20) -> str:
    lines = [f"{result['competition']} {result['season']} standings "
             f"(calculated from matches):"]
    for row in result["table"][:show]:
        lines.append(
            f"{row['position']}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L) "
            f"GD {row['goal_diff']:+d}"
        )
    return "\n".join(lines)
