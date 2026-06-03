"""
Human-readable formatters for the Brazilian Soccer MCP server.

Context
-------
The query engine in :mod:`knowledge_graph` returns plain data structures.  The
MCP specification, however, shows answers as nicely formatted text (match
lists, league tables, head-to-head summaries, etc.).  This module converts the
engine's structured results into those text blocks so the MCP tools can return
ready-to-read strings to the calling LLM.

Pure standard library; safe to import anywhere.
"""

from __future__ import annotations

from data_loader import Match, Player


def fmt_date(match: Match) -> str:
    return match.date.isoformat() if match.date else "????-??-??"


def format_match(m: Match) -> str:
    """One-line match summary, e.g.
    "2023-09-03: Flamengo 2-1 Fluminense (Brasileirao Round 22)"."""
    score = (
        f"{m.home_goal}-{m.away_goal}"
        if m.home_goal is not None and m.away_goal is not None
        else "vs"
    )
    context = m.competition
    if m.round:
        context += f" Round {m.round}"
    elif m.stage:
        context += f" {m.stage}"
    return f"{fmt_date(m)}: {m.home_team} {score} {m.away_team} ({context})"


def format_matches(matches: list[Match], limit: int = 20, header: str = "") -> str:
    if not matches:
        return (header + "\n" if header else "") + "No matches found."
    lines = [header] if header else []
    for m in matches[:limit]:
        lines.append(f"- {format_match(m)}")
    if len(matches) > limit:
        lines.append(f"... ({len(matches) - limit} more matches in dataset)")
    return "\n".join(lines)


def format_head_to_head(h2h: dict) -> str:
    lines = [
        f"{h2h['team1']} vs {h2h['team2']} head-to-head "
        f"(across all competitions in dataset):",
        format_matches(h2h["matches"], limit=15),
        "",
        f"Head-to-head: {h2h['team1']} {h2h['team1_wins']} wins, "
        f"{h2h['team2']} {h2h['team2_wins']} wins, {h2h['draws']} draws "
        f"(goals {h2h['team1_goals']}-{h2h['team2_goals']})",
    ]
    return "\n".join(lines)


def format_team_record(rec: dict) -> str:
    scope = []
    if rec.get("season"):
        scope.append(str(rec["season"]))
    if rec.get("competition"):
        scope.append(rec["competition"])
    if rec.get("venue") and rec["venue"] != "either":
        scope.append(f"{rec['venue']} only")
    scope_str = f" ({', '.join(scope)})" if scope else ""
    return (
        f"{rec['team']} record{scope_str}:\n"
        f"- Matches: {rec['matches']}\n"
        f"- Wins: {rec['wins']}, Draws: {rec['draws']}, Losses: {rec['losses']}\n"
        f"- Goals For: {rec['goals_for']}, Goals Against: {rec['goals_against']} "
        f"(GD {rec['goal_difference']:+d})\n"
        f"- Points: {rec['points']}\n"
        f"- Win rate: {rec['win_rate']}%"
    )


def format_player(p: Player) -> str:
    bits = [f"Overall: {p.overall}" if p.overall is not None else "Overall: ?"]
    if p.position:
        bits.append(f"Position: {p.position}")
    if p.club:
        bits.append(f"Club: {p.club}")
    return f"{p.name} - " + ", ".join(bits)


def format_players(players: list[Player], header: str = "") -> str:
    if not players:
        return (header + "\n" if header else "") + "No players found."
    lines = [header] if header else []
    for i, p in enumerate(players, start=1):
        lines.append(f"{i}. {format_player(p)}")
    return "\n".join(lines)


def format_players_by_club(rows: list[dict], header: str = "") -> str:
    lines = [header] if header else []
    for r in rows:
        lines.append(f"- {r['club']}: {r['count']} players (avg rating: {r['avg_overall']})")
    return "\n".join(lines)


def format_standings(rows: list[dict], competition: str, season: int) -> str:
    if not rows:
        return f"No standings could be computed for {competition} {season}."
    lines = [f"{season} {competition} standings (calculated from matches):"]
    for r in rows:
        tag = " - Champion" if r["position"] == 1 else ""
        lines.append(
            f"{r['position']}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L, "
            f"GD {r['goal_difference']:+d}){tag}"
        )
    return "\n".join(lines)


def format_average_goals(stats: dict) -> str:
    scope = []
    if stats.get("competition"):
        scope.append(stats["competition"])
    if stats.get("season"):
        scope.append(str(stats["season"]))
    scope_str = f" ({', '.join(scope)})" if scope else ""
    return (
        f"Match statistics{scope_str}:\n"
        f"- Matches analysed: {stats['matches']}\n"
        f"- Average goals per match: {stats['avg_goals_per_match']}\n"
        f"- Home win rate: {stats['home_win_rate']}%\n"
        f"- Draw rate: {stats['draw_rate']}%\n"
        f"- Away win rate: {stats['away_win_rate']}%"
    )


def format_best_records(rows: list[dict], header: str = "") -> str:
    lines = [header] if header else []
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"{i}. {r['team']} - {r['win_rate']}% win rate "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L in {r['played']}, "
            f"{r['points']} pts)"
        )
    return "\n".join(lines)
