"""
Context
=======
Module: bsoccer.format
Purpose: Turn the structured dicts produced by bsoccer.queries.QueryEngine into
         concise human-readable text matching the answer formats illustrated in
         the specification (TASK.md). Used by the MCP tools so an LLM client
         receives ready-to-show prose alongside the structured data.

Every function is pure (dict in, str out) and defensive about missing keys so a
formatting error never masks a successful query.
"""

from __future__ import annotations

from typing import Any


def _score_line(m: dict[str, Any]) -> str:
    date = m.get("date") or "????-??-??"
    comp = m.get("competition", "")
    rnd = m.get("round")
    tag = f" ({comp}" + (f" Round {rnd}" if rnd and str(rnd).isdigit() else (f" {rnd}" if rnd else "")) + ")" if comp else ""
    return (f"- {date}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']}{tag}")


def format_matches(result: dict[str, Any]) -> str:
    if result.get("error"):
        return result["error"]
    if not result.get("matches"):
        return "No matches found."
    lines = [_score_line(m) for m in result["matches"]]
    header = f"Found {result['count']} match(es)"
    if result.get("returned", result["count"]) < result["count"]:
        header += f" (showing first {result['returned']})"
    return header + ":\n" + "\n".join(lines)


def format_record(rec: dict[str, Any]) -> str:
    if rec.get("error"):
        return rec["error"]
    scope = []
    if rec.get("season"):
        scope.append(str(rec["season"]))
    if rec.get("competition"):
        scope.append(rec["competition"])
    if rec.get("venue") and rec["venue"] != "all":
        scope.append(f"{rec['venue']} only")
    scope_txt = f" ({', '.join(scope)})" if scope else ""
    return (
        f"{rec['team']} record{scope_txt}:\n"
        f"- Matches: {rec['matches']}\n"
        f"- Wins: {rec['wins']}, Draws: {rec['draws']}, Losses: {rec['losses']}\n"
        f"- Goals For: {rec['goals_for']}, Goals Against: {rec['goals_against']} "
        f"(diff {rec['goal_difference']:+d})\n"
        f"- Points: {rec['points']}, Win rate: {rec['win_rate']}%"
    )


def format_head_to_head(h2h: dict[str, Any]) -> str:
    if h2h.get("error"):
        return h2h["error"]
    a, b = h2h["team_a"], h2h["team_b"]
    lines = [
        f"{a} vs {b} head-to-head ({h2h['total_matches']} matches):",
        f"- {a}: {h2h['team_a_wins']} wins, {h2h['team_a_goals']} goals",
        f"- {b}: {h2h['team_b_wins']} wins, {h2h['team_b_goals']} goals",
        f"- Draws: {h2h['draws']}",
    ]
    if h2h.get("matches"):
        lines.append("Recent meetings:")
        lines.extend(_score_line(m) for m in h2h["matches"][:10])
    return "\n".join(lines)


def format_players(result: dict[str, Any]) -> str:
    if result.get("error"):
        return result["error"]
    if not result.get("players"):
        return "No players found."
    lines = []
    for i, p in enumerate(result["players"], 1):
        lines.append(
            f"{i}. {p['name']} - Overall: {p['overall']}, "
            f"Position: {p['position']}, Club: {p['club']}, "
            f"Nationality: {p['nationality']}"
        )
    header = f"Found {result['count']} player(s)"
    if result.get("returned", result["count"]) < result["count"]:
        header += f" (showing top {result['returned']})"
    return header + ":\n" + "\n".join(lines)


def format_club_summary(result: dict[str, Any]) -> str:
    if result.get("error"):
        return result["error"]
    lines = [f"{result['nationality']} players by club "
             f"({result['total_players']} total):"]
    for c in result["clubs"]:
        lines.append(f"- {c['club']}: {c['players']} players "
                     f"(avg rating: {c['avg_overall']})")
    return "\n".join(lines)


def format_standings(result: dict[str, Any]) -> str:
    if result.get("error"):
        return result["error"]
    title = result.get("competition", "Standings")
    if result.get("season"):
        title = f"{result['season']} {title}"
    lines = [f"{title} Standings (calculated from matches):"]
    for r in result["table"]:
        lines.append(
            f"{r['position']}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L) "
            f"GF:{r['goals_for']} GA:{r['goals_against']}"
        )
    return "\n".join(lines)


def format_champion(result: dict[str, Any]) -> str:
    if result.get("error"):
        return result["error"]
    title = result.get("competition", "")
    if result.get("season"):
        title = f"{result['season']} {title}"
    return (f"{title} champion (by calculated standings): {result['champion']} "
            f"- {result['points']} pts ({result['record']}), "
            f"goals {result['goals_for']}-{result['goals_against']}")


def format_competition_stats(result: dict[str, Any]) -> str:
    if result.get("error"):
        return result["error"]
    title = result.get("competition") or "All competitions"
    if result.get("season"):
        title = f"{title} {result['season']}"
    return (
        f"{title} statistics ({result['matches']} matches):\n"
        f"- Total goals: {result['total_goals']}\n"
        f"- Average goals per match: {result['avg_goals_per_match']}\n"
        f"- Home wins: {result['home_wins']} ({result['home_win_rate']}%)\n"
        f"- Away wins: {result['away_wins']} ({result['away_win_rate']}%)\n"
        f"- Draws: {result['draws']} ({result['draw_rate']}%)"
    )


def format_biggest_wins(result: dict[str, Any]) -> str:
    if result.get("error") or not result.get("matches"):
        return result.get("error", "No matches found.")
    lines = ["Biggest victories:"]
    for i, m in enumerate(result["matches"], 1):
        date = m.get("date") or "????"
        lines.append(
            f"{i}. {date}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']} ({m['competition']}, margin {m['margin']})"
        )
    return "\n".join(lines)
