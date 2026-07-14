# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : soccer_mcp.formatting
# Purpose : Turn the structured query results from KnowledgeGraph into the
#           human-readable text blocks shown in the spec's "Example answer
#           format" sections. Kept separate from both the query layer (pure
#           data) and the server (transport) so the formatting is unit-testable.
# =============================================================================

from __future__ import annotations

from typing import List

from .models import Match, Player


def format_matches(matches: List[Match], title: str = "Matches", max_rows: int = 25) -> str:
    if not matches:
        return f"{title}: no matches found."
    lines = [f"{title} ({len(matches)} found):"]
    for m in matches[:max_rows]:
        date = m.date or "????-??-??"
        ctx = m.competition
        if m.round:
            ctx += f" Round {m.round}"
        elif m.stage:
            ctx += f" {m.stage}"
        lines.append(f"- {date}: {m.score_line()} ({ctx})")
    if len(matches) > max_rows:
        lines.append(f"- ... ({len(matches) - max_rows} more)")
    return "\n".join(lines)


def format_head_to_head(h2h: dict, max_rows: int = 10) -> str:
    if h2h["matches"] == 0:
        return f"No matches found between {h2h['team1']} and {h2h['team2']}."
    lines = [
        f"{h2h['team1']} vs {h2h['team2']} head-to-head ({h2h['matches']} matches):",
        f"- {h2h['team1']} wins: {h2h['team1_wins']}",
        f"- {h2h['team2']} wins: {h2h['team2_wins']}",
        f"- Draws: {h2h['draws']}",
        f"- Goals: {h2h['team1']} {h2h['team1_goals']} - {h2h['team2_goals']} {h2h['team2']}",
        "",
        "Recent meetings:",
    ]
    lines += [
        f"- {m.date or '????-??-??'}: {m.score_line()} ({m.competition})"
        for m in h2h["games"][:max_rows]
    ]
    return "\n".join(lines)


def format_team_stats(s: dict) -> str:
    scope = []
    if s.get("competition"):
        scope.append(s["competition"])
    if s.get("season"):
        scope.append(str(s["season"]))
    if s.get("venue"):
        scope.append(f"{s['venue']} only")
    scope_str = f" ({', '.join(scope)})" if scope else ""
    return "\n".join([
        f"{s['team']} record{scope_str}:",
        f"- Matches: {s['matches']}",
        f"- Wins: {s['wins']}, Draws: {s['draws']}, Losses: {s['losses']}",
        f"- Goals For: {s['goals_for']}, Goals Against: {s['goals_against']} "
        f"(GD: {s['goal_difference']:+d})",
        f"- Points: {s['points']}",
        f"- Win rate: {s['win_rate']}%",
    ])


def format_players(players: List[Player], title: str = "Players", max_rows: int = 25) -> str:
    if not players:
        return f"{title}: no players found."
    lines = [f"{title} ({len(players)} found):"]
    for i, p in enumerate(players[:max_rows], start=1):
        ovr = p.overall if p.overall is not None else "?"
        club = p.club or "Free agent"
        lines.append(
            f"{i}. {p.name} - Overall: {ovr}, Position: {p.position or '?'}, "
            f"Club: {club}, Nationality: {p.nationality}"
        )
    if len(players) > max_rows:
        lines.append(f"... ({len(players) - max_rows} more)")
    return "\n".join(lines)


def format_standings(rows: List[dict], title: str, max_rows: int = 30) -> str:
    if not rows:
        return f"{title}: no data."
    lines = [f"{title}:"]
    for r in rows[:max_rows]:
        tag = " - Champion" if r["position"] == 1 else ""
        lines.append(
            f"{r['position']}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L, "
            f"GD {r['goal_difference']:+d}){tag}"
        )
    return "\n".join(lines)


def format_statistics(s: dict) -> str:
    scope = []
    if s.get("competition"):
        scope.append(s["competition"])
    if s.get("season"):
        scope.append(str(s["season"]))
    scope_str = f" ({', '.join(scope)})" if scope else " (all data)"
    return "\n".join([
        f"Statistics{scope_str}:",
        f"- Matches: {s['matches']}",
        f"- Total goals: {s['total_goals']}",
        f"- Average goals per match: {s['avg_goals_per_match']}",
        f"- Home win rate: {s['home_win_rate']}%",
        f"- Away win rate: {s['away_win_rate']}%",
        f"- Draw rate: {s['draw_rate']}%",
    ])
