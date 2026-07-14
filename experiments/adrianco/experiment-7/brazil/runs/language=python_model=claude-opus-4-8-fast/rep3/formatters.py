"""
================================================================================
Context
================================================================================
Module:   formatters.py
Project:  Brazilian Soccer MCP Server
Purpose:  Turn the structured results produced by knowledge_graph into the
          human-readable, natural-language answer formats shown in the
          specification (TASK.md).  Keeping presentation here means the MCP
          tools in server.py stay thin and the query engine stays free of any
          formatting concerns, so each layer can be tested independently.

Each function takes already-computed query results (Match lists, stat dicts,
TableRow lists, Player lists) and returns a printable string.

Dependencies: data_loader (types only), knowledge_graph (TableRow). Stdlib only.
================================================================================
"""

from __future__ import annotations

from typing import Optional

from data_loader import Match, Player
from knowledge_graph import TableRow


def _fmt_date(m: Match) -> str:
    return m.date.isoformat() if m.date else "????-??-??"


def _round_label(m: Match) -> str:
    if m.stage:
        return m.stage
    if m.round:
        return f"Round {m.round}"
    return ""


def format_match_line(m: Match) -> str:
    """e.g. '2019-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)'."""
    context = m.competition
    rl = _round_label(m)
    if rl:
        context = f"{m.competition}, {rl}"
    return f"{_fmt_date(m)}: {m.score_line()} ({context})"


def format_matches(matches: list[Match], header: Optional[str] = None,
                   limit: Optional[int] = None) -> str:
    if not matches:
        return (header + "\n" if header else "") + "No matches found."
    shown = matches[:limit] if limit else matches
    lines = [header] if header else []
    lines.extend(f"- {format_match_line(m)}" for m in shown)
    if limit and len(matches) > limit:
        lines.append(f"... ({len(matches) - limit} more matches in dataset)")
    return "\n".join(lines)


def format_head_to_head(h2h: dict, limit: int = 10) -> str:
    a, b = h2h["team_a"], h2h["team_b"]
    lines = [f"{a} vs {b} — head-to-head ({h2h['total_matches']} matches in dataset):"]
    recent = h2h["matches"][:limit]
    for m in recent:
        lines.append(f"- {format_match_line(m)}")
    if h2h["total_matches"] > limit:
        lines.append(f"... ({h2h['total_matches'] - limit} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head: {a} {h2h['team_a_wins']} wins, "
        f"{b} {h2h['team_b_wins']} wins, {h2h['draws']} draws "
        f"(goals {h2h['team_a_goals']}-{h2h['team_b_goals']})"
    )
    return "\n".join(lines)


def format_team_stats(stats: dict) -> str:
    bits = [stats["team"]]
    if stats.get("competition"):
        bits.append(str(stats["competition"]))
    if stats.get("season"):
        bits.append(str(stats["season"]))
    venue = stats.get("venue", "either")
    venue_label = {"home": "home", "away": "away"}.get(venue, "")
    title = " ".join(bits)
    if venue_label:
        title += f" {venue_label} record"
    else:
        title += " record"
    return (
        f"{title}:\n"
        f"- Matches: {stats['matches']}\n"
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}\n"
        f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']} "
        f"(GD {stats['goal_difference']:+d})\n"
        f"- Points: {stats['points']}\n"
        f"- Win rate: {stats['win_rate']}%"
    )


def format_standings(table: list[TableRow], competition: str, season: int,
                     limit: Optional[int] = None) -> str:
    if not table:
        return f"No standings available for {competition} {season}."
    rows = table[:limit] if limit else table
    lines = [f"{season} {competition} — Final Standings (calculated from matches):"]
    for r in rows:
        tag = ""
        if r.position == 1:
            tag = " — Champion"
        lines.append(
            f"{r.position:>2}. {r.team:<18} {r.points:>3} pts "
            f"({r.wins}W {r.draws}D {r.losses}L, "
            f"GF {r.goals_for} GA {r.goals_against}, GD {r.goal_difference:+d}){tag}"
        )
    return "\n".join(lines)


def format_players(players: list[Player], header: Optional[str] = None) -> str:
    if not players:
        return (header + "\n" if header else "") + "No players found."
    lines = [header] if header else []
    for i, p in enumerate(players, 1):
        rating = p.overall if p.overall is not None else "?"
        club = p.club or "Free agent"
        lines.append(
            f"{i}. {p.name} — Overall: {rating}, Position: {p.position or '?'}, "
            f"Club: {club} ({p.nationality})"
        )
    return "\n".join(lines)


def format_average_goals(stats: dict) -> str:
    scope = []
    if stats.get("competition"):
        scope.append(str(stats["competition"]))
    if stats.get("season"):
        scope.append(str(stats["season"]))
    title = "Statistics" + (f" — {', '.join(scope)}" if scope else " (all competitions)")
    if not stats["matches"]:
        return f"{title}:\nNo matches found."
    return (
        f"{title}:\n"
        f"- Matches analysed: {stats['matches']}\n"
        f"- Average goals per match: {stats['avg_goals_per_match']}\n"
        f"- Home win rate: {stats['home_win_rate']}%\n"
        f"- Away win rate: {stats['away_win_rate']}%\n"
        f"- Draw rate: {stats['draw_rate']}%"
    )


def format_best_record(records: list[dict], venue: str) -> str:
    if not records:
        return "No teams matched the criteria."
    venue_label = {"home": "home", "away": "away"}.get(venue, "overall")
    lines = [f"Best {venue_label} records:"]
    for i, s in enumerate(records, 1):
        lines.append(
            f"{i}. {s['team']} — {s['win_rate']}% win rate "
            f"({s['wins']}W {s['draws']}D {s['losses']}L, GD {s['goal_difference']:+d})"
        )
    return "\n".join(lines)
