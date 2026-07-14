"""
Context
=======
Module: brazilian_soccer_mcp.formatting
Purpose: Render the structured results returned by
:class:`~brazilian_soccer_mcp.knowledge_graph.KnowledgeGraph` into the
human-readable text blocks shown in the specification (TASK.md).

These helpers are used by the MCP server so the LLM receives clean, already
formatted answers, and are independently unit-tested.
"""

from __future__ import annotations

from typing import List, Optional

from .models import Match, Player


def format_matches(matches: List[Match], title: Optional[str] = None, max_rows: int = 15) -> str:
    if not matches:
        return f"{title + ': ' if title else ''}No matches found."
    lines = []
    if title:
        lines.append(title)
    for m in matches[:max_rows]:
        lines.append(f"- {m.score_line()}")
    if len(matches) > max_rows:
        lines.append(f"- ... ({len(matches) - max_rows} more matches in dataset)")
    return "\n".join(lines)


def format_head_to_head(h2h: dict, max_rows: int = 15) -> str:
    lines = [f"{h2h['team1']} vs {h2h['team2']} head-to-head:"]
    for m in h2h["matches"][:max_rows]:
        lines.append(f"- {m.score_line()}")
    if len(h2h["matches"]) > max_rows:
        lines.append(f"- ... ({len(h2h['matches']) - max_rows} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {h2h['team1']} {h2h['team1_wins']} wins, "
        f"{h2h['team2']} {h2h['team2_wins']} wins, {h2h['draws']} draws "
        f"(goals {h2h['team1_goals']}-{h2h['team2_goals']})."
    )
    return "\n".join(lines)


def format_team_stats(stats: dict) -> str:
    scope = stats["team"]
    extra = []
    if stats.get("season"):
        extra.append(str(stats["season"]))
    if stats.get("competition"):
        extra.append(str(stats["competition"]))
    if stats.get("venue") and stats["venue"] != "all":
        extra.append(f"{stats['venue']} only")
    header = f"{scope} record" + (f" ({', '.join(extra)})" if extra else "")
    return "\n".join([
        f"{header}:",
        f"- Matches: {stats['played']}",
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}",
        f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']} "
        f"(GD {stats['goal_difference']:+d})",
        f"- Points: {stats['points']}",
        f"- Win rate: {stats['win_rate']}%",
    ])


def format_players(players: List[Player], title: Optional[str] = None) -> str:
    if not players:
        return f"{title + ': ' if title else ''}No players found."
    lines = []
    if title:
        lines.append(title)
    for i, p in enumerate(players, start=1):
        lines.append(f"{i}. {p.summary_line()}")
    return "\n".join(lines)


def format_player(p: Player) -> str:
    lines = [
        f"{p.name}",
        f"- Nationality: {p.nationality}",
        f"- Club: {p.club}",
        f"- Position: {p.position}"
        + (f" (#{p.jersey_number})" if p.jersey_number is not None else ""),
        f"- Overall: {p.overall}, Potential: {p.potential}",
        f"- Age: {p.age}, Height: {p.height}, Weight: {p.weight}",
        f"- Preferred foot: {p.preferred_foot}, Value: {p.value}, Wage: {p.wage}",
    ]
    if p.skills:
        top = sorted(p.skills.items(), key=lambda kv: kv[1], reverse=True)[:6]
        lines.append("- Top skills: " + ", ".join(f"{k} {v}" for k, v in top))
    return "\n".join(lines)


def format_standings(rows: List[dict], season: int, competition: str, top: int = 20) -> str:
    if not rows:
        return f"No standings could be computed for {competition} {season}."
    lines = [f"{competition} {season} final standings (calculated from matches):"]
    for r in rows[:top]:
        tag = " - Champion" if r["position"] == 1 else ""
        lines.append(
            f"{r['position']}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L, "
            f"GD {r['goal_difference']:+d}){tag}"
        )
    return "\n".join(lines)


def format_competition_stats(stats: dict) -> str:
    scope_bits = []
    if stats.get("competition"):
        scope_bits.append(str(stats["competition"]))
    if stats.get("season"):
        scope_bits.append(str(stats["season"]))
    scope = " ".join(scope_bits) if scope_bits else "All competitions"
    return "\n".join([
        f"{scope} statistics:",
        f"- Matches (with score): {stats['matches_with_score']}",
        f"- Total goals: {stats['total_goals']}",
        f"- Average goals per match: {stats['avg_goals_per_match']}",
        f"- Home win rate: {stats['home_win_rate']}%",
        f"- Away win rate: {stats['away_win_rate']}%",
        f"- Draw rate: {stats['draw_rate']}%",
    ])
