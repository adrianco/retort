"""
================================================================================
Module: brazilian_soccer_mcp.formatting
--------------------------------------------------------------------------------
Context:
    TASK.md shows human-readable "Example answer format" blocks for each query
    category. The MCP tools return these rendered strings (alongside structured
    data) so an LLM client can surface a clean answer directly.

Responsibility:
    Pure rendering functions: take the dicts/lists produced by KnowledgeGraph
    and format them as readable text. No data access or business logic here.
================================================================================
"""

from __future__ import annotations

from typing import List

from .models import Match, Player


def format_matches(matches: List[Match], header: str = "", limit: int = 15) -> str:
    if not matches:
        return f"{header}\nNo matches found.".strip()
    lines = [header] if header else []
    for m in matches[:limit]:
        lines.append(f"- {m.summary()}")
    if len(matches) > limit:
        lines.append(f"- ... ({len(matches) - limit} more in dataset)")
    return "\n".join(lines).strip()


def format_head_to_head(h: dict, limit: int = 10) -> str:
    lines = [f"{h['team1']} vs {h['team2']} — head-to-head ({h['total']} matches):"]
    for m in h["matches"][:limit]:
        lines.append(f"- {m.summary()}")
    if len(h["matches"]) > limit:
        lines.append(f"- ... ({len(h['matches']) - limit} more in dataset)")
    lines.append("")
    lines.append(
        f"Record: {h['team1']} {h['team1_wins']} wins, "
        f"{h['team2']} {h['team2_wins']} wins, {h['draws']} draws"
    )
    lines.append(f"Goals: {h['team1']} {h['team1_goals']} — {h['team2_goals']} {h['team2']}")
    return "\n".join(lines)


def format_team_record(r: dict) -> str:
    scope = []
    if r.get("competition"):
        scope.append(str(r["competition"]))
    if r.get("season"):
        scope.append(str(r["season"]))
    if r.get("venue") and r["venue"] != "all":
        scope.append(f"{r['venue']} only")
    scope_str = f" ({', '.join(scope)})" if scope else ""
    return (
        f"{r['team']} record{scope_str}:\n"
        f"- Matches: {r['matches']}\n"
        f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}\n"
        f"- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']} "
        f"(GD {r['goal_difference']:+d})\n"
        f"- Points: {r['points']}\n"
        f"- Win rate: {r['win_rate']}%"
    )


def format_players(players: List[Player], header: str = "Players:", limit: int = 25) -> str:
    if not players:
        return f"{header}\nNo players found."
    lines = [header]
    for i, p in enumerate(players[:limit], 1):
        lines.append(f"{i}. {p.summary()}")
    if len(players) > limit:
        lines.append(f"... ({len(players) - limit} more)")
    return "\n".join(lines)


def format_standings(table: List[dict], competition: str, season: int, limit: int = 20) -> str:
    if not table:
        return f"No standings could be computed for {competition} {season}."
    lines = [f"{competition} {season} — Final Standings (calculated from matches):"]
    lines.append(f"{'#':>2}  {'Team':<22} {'Pts':>3} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GD':>4}")
    for r in table[:limit]:
        tag = "  — Champion" if r["position"] == 1 else ""
        lines.append(
            f"{r['position']:>2}  {r['team']:<22} {r['points']:>3} {r['played']:>3} "
            f"{r['wins']:>3} {r['draws']:>3} {r['losses']:>3} {r['goal_difference']:>+4}{tag}"
        )
    return "\n".join(lines)


def format_stats(s: dict) -> str:
    scope = []
    if s.get("competition"):
        scope.append(str(s["competition"]))
    if s.get("season"):
        scope.append(str(s["season"]))
    scope_str = f" ({', '.join(scope)})" if scope else " (all competitions)"
    return (
        f"Match statistics{scope_str}:\n"
        f"- Matches analysed: {s['matches']}\n"
        f"- Total goals: {s['total_goals']}\n"
        f"- Average goals per match: {s['avg_goals_per_match']}\n"
        f"- Home win rate: {s['home_win_rate']}%\n"
        f"- Away win rate: {s['away_win_rate']}%\n"
        f"- Draw rate: {s['draw_rate']}%"
    )


def format_best_record(rows: List[dict], title: str) -> str:
    if not rows:
        return f"{title}\nNo teams met the criteria."
    lines = [title]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i}. {r['team']} — {r['win_rate']}% win rate "
            f"({r['wins']}W {r['draws']}D {r['losses']}L, GD {r['goal_difference']:+d})"
        )
    return "\n".join(lines)


def format_club_summary(rows: List[dict], nationality: str, limit: int = 15) -> str:
    if not rows:
        return f"No clubs found for {nationality} players."
    lines = [f"{nationality} players by club:"]
    for r in rows[:limit]:
        lines.append(f"- {r['club']}: {r['count']} players (avg rating: {r['avg_overall']})")
    return "\n".join(lines)
