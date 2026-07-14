"""
================================================================================
formatters.py - Render query-engine result dicts to human-readable text
================================================================================

CONTEXT
-------
The query engine returns structured dicts (easy to test / serialise). The MCP
tools, however, are consumed by an LLM and a human, so they return text laid out
like the "Example answer format" blocks in the specification. Each function here
takes one of those dicts and produces a readable string. Keeping formatting
separate from querying means the BDD tests can assert on data while the server
returns prose.
================================================================================
"""

from __future__ import annotations

from typing import Dict


def _score_line(m: Dict) -> str:
    date = m.get("date") or "????-??-??"
    score = m.get("score") or "vs"
    comp = m.get("competition", "")
    extra = []
    if m.get("round"):
        extra.append(f"Round {m['round']}")
    if m.get("stage"):
        extra.append(m["stage"])
    tag = f"{comp}" + (f" {', '.join(extra)}" if extra else "")
    return f"- {date}: {m['home_team']} {score} {m['away_team']} ({tag})"


def format_matches(data: Dict) -> str:
    q = data.get("query", {})
    header_bits = [b for b in (q.get("team"), q.get("opponent")) if b]
    title = " vs ".join(header_bits) if header_bits else "Matches"
    if q.get("competition"):
        title += f" — {q['competition']}"
    if q.get("season"):
        title += f" ({q['season']})"
    lines = [f"{title}:"]
    if not data["matches"]:
        lines.append("No matches found.")
        return "\n".join(lines)
    for m in data["matches"]:
        lines.append(_score_line(m))
    if data["total"] > data["returned"]:
        lines.append(f"... ({data['total'] - data['returned']} more matches in dataset)")
    return "\n".join(lines)


def format_last_match(data: Dict) -> str:
    if not data["found"]:
        return f"No matches found between {data['team']} and {data['opponent']}."
    m = data["match"]
    return (
        f"{data['team']} last played {data['opponent']} on {m['date']}:\n"
        f"{_score_line(m)}\n"
        f"Total meetings in dataset: {data['total_meetings']}"
    )


def format_team_record(r: Dict) -> str:
    scope = {"home": "home ", "away": "away ", "overall": ""}.get(r["scope"], "")
    season = f" {r['season']}" if r.get("season") else ""
    return (
        f"{r['team']} {scope}record ({r['competition']}{season}):\n"
        f"- Matches: {r['matches']}\n"
        f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}\n"
        f"- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']} "
        f"(GD {r['goal_difference']:+d})\n"
        f"- Points: {r['points']}\n"
        f"- Win rate: {r['win_rate']}%"
    )


def format_head_to_head(h: Dict) -> str:
    lines = [f"{h['team1']} vs {h['team2']} head-to-head:"]
    for m in h["matches"][:15]:
        lines.append(_score_line(m))
    if h["total_matches"] > 15:
        lines.append(f"... ({h['total_matches'] - 15} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {h['team1']} {h['team1_wins']} wins, "
        f"{h['team2']} {h['team2_wins']} wins, {h['draws']} draws"
    )
    lines.append(f"Goals: {h['team1']} {h['team1_goals']} - {h['team2_goals']} {h['team2']}")
    return "\n".join(lines)


def format_players(data: Dict) -> str:
    q = data.get("query", {})
    bits = []
    if q.get("nationality"):
        bits.append(q["nationality"])
    if q.get("position"):
        bits.append(q["position"])
    if q.get("club"):
        bits.append(f"at {q['club']}")
    title = "Players" + (f" ({', '.join(bits)})" if bits else "")
    lines = [f"{title} — {data['total']} found:"]
    if not data["players"]:
        return f"No players found for query {q}."
    for i, p in enumerate(data["players"], 1):
        lines.append(
            f"{i}. {p['name']} - Overall: {p['overall']}, Position: {p['position']}, "
            f"Club: {p['club']} ({p['nationality']}, age {p['age']})"
        )
    return "\n".join(lines)


def format_player(data: Dict) -> str:
    if not data["found"]:
        return f"No player found matching '{data['query']}'."
    p = data["player"]
    lines = [
        f"{p['name']}:",
        f"- Nationality: {p['nationality']}",
        f"- Age: {p['age']}",
        f"- Club: {p['club']}",
        f"- Position: {p['position']} (#{p['jersey_number']})",
        f"- Overall: {p['overall']}, Potential: {p['potential']}",
        f"- Physical: {p['height']}, {p['weight']}, {p['preferred_foot']} footed",
    ]
    if data.get("other_matches"):
        names = ", ".join(o["name"] for o in data["other_matches"])
        lines.append(f"Other matches: {names}")
    return "\n".join(lines)


def format_club_summary(data: Dict) -> str:
    lines = [f"{data['nationality']} players by club:"]
    for r in data["clubs"]:
        avg = r["avg_overall"]
        lines.append(f"- {r['club']}: {r['players']} players (avg rating: {avg})")
    return "\n".join(lines)


def format_standings(data: Dict) -> str:
    lines = [f"{data['season']} {data['competition']} Final Standings (calculated from matches):"]
    for r in data["table"]:
        champ = " - Champion" if r["position"] == 1 else ""
        lines.append(
            f"{r['position']}. {r['team']} - {r['Pts']} pts "
            f"({r['W']}W, {r['D']}D, {r['L']}L, GD {r['GD']:+d}){champ}"
        )
    return "\n".join(lines)


def format_league_statistics(s: Dict) -> str:
    if s.get("matches", 0) == 0:
        return f"No match data for {s.get('competition')} {s.get('season') or ''}."
    season = f" {s['season']}" if s.get("season") else " (all seasons)"
    return (
        f"{s['competition']}{season} statistics:\n"
        f"- Matches: {s['matches']}\n"
        f"- Total goals: {s['total_goals']}\n"
        f"- Average goals per match: {s['avg_goals_per_match']}\n"
        f"- Home win rate: {s['home_win_rate']}%\n"
        f"- Away win rate: {s['away_win_rate']}%\n"
        f"- Draw rate: {s['draw_rate']}%"
    )


def format_biggest_wins(data: Dict) -> str:
    lines = [f"Biggest victories ({data['competition']}):"]
    for i, m in enumerate(data["matches"], 1):
        lines.append(
            f"{i}. {m['date']}: {m['home_team']} {m['score']} {m['away_team']} "
            f"({m['competition']}, margin {m['margin']})"
        )
    return "\n".join(lines)


def format_best_record(data: Dict) -> str:
    lines = [f"Best {data['scope']} record — {data['competition']} "
             f"{data.get('season') or '(all seasons)'} (by {data['metric']}):"]
    for i, r in enumerate(data["ranking"], 1):
        lines.append(
            f"{i}. {r['team']} - {r['win_rate']}% win rate "
            f"({r['wins']}W {r['draws']}D {r['losses']}L, GD {r['goal_difference']:+d})"
        )
    return "\n".join(lines)


def format_competitions_for_team(data: Dict) -> str:
    lines = [f"{data['team']} has appeared in these competitions:"]
    for c in data["competitions"]:
        seasons = c["seasons"]
        rng = f"{seasons[0]}–{seasons[-1]}" if seasons else "?"
        lines.append(f"- {c['competition']} ({len(seasons)} seasons: {rng})")
    return "\n".join(lines)
