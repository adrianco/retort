"""
================================================================================
brazilian_soccer_mcp.formatting
================================================================================

CONTEXT
-------
Turns the plain dict/list results produced by ``KnowledgeGraph`` into the human
readable, markdown-ish text blocks shown in the specification's example answers.

Keeping all rendering here means the query engine stays pure data (and easily
testable) while the MCP tools in ``server`` simply call an engine method and the
matching formatter. Every formatter tolerates empty input gracefully.
================================================================================
"""

from __future__ import annotations

from typing import List, Optional


def _score_line(m: dict) -> str:
    date = m.get("date") or "????-??-??"
    rnd = m.get("round")
    comp = m.get("competition", "")
    tag = f"{comp}"
    if rnd:
        tag = f"{comp} Round {rnd}" if str(rnd).isdigit() else f"{comp} ({rnd})"
    return (f"- {date}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']} ({tag})")


def format_matches(matches: List[dict], title: Optional[str] = None,
                   limit: int = 25) -> str:
    if not matches:
        return f"No matches found{(' for ' + title) if title else ''}."
    lines = []
    if title:
        lines.append(title)
    shown = matches[-limit:] if len(matches) > limit else matches
    if len(matches) > limit:
        lines.append(f"(showing the {limit} most recent of {len(matches)} matches)")
    lines.extend(_score_line(m) for m in shown)
    return "\n".join(lines)


def format_head_to_head(h2h: dict) -> str:
    t1, t2 = h2h["team1"], h2h["team2"]
    if h2h["total"] == 0:
        return f"No matches found between {t1} and {t2} in the dataset."
    header = f"{t1} vs {t2} head-to-head ({h2h['total']} matches in dataset):"
    record = (f"{t1} {h2h['team1_wins']} wins, "
              f"{t2} {h2h['team2_wins']} wins, "
              f"{h2h['draws']} draws")
    goals = f"Goals: {t1} {h2h['team1_goals']} - {h2h['team2_goals']} {t2}"
    body = format_matches(h2h["matches"], limit=15)
    return f"{header}\n{record}\n{goals}\n\n{body}"


def format_team_record(rec: dict) -> str:
    venue = {"home": " home", "away": " away", "all": ""}.get(rec["venue"], "")
    scope = []
    if rec.get("season"):
        scope.append(str(rec["season"]))
    if rec.get("competition"):
        scope.append(rec["competition"])
    scope_s = f" ({', '.join(scope)})" if scope else ""
    if rec["played"] == 0:
        return f"No matches found for {rec['team']}{venue}{scope_s}."
    return (
        f"{rec['team']}{venue} record{scope_s}:\n"
        f"- Matches: {rec['played']}\n"
        f"- Wins: {rec['wins']}, Draws: {rec['draws']}, Losses: {rec['losses']}\n"
        f"- Goals For: {rec['goals_for']}, Goals Against: {rec['goals_against']} "
        f"(GD {rec['goal_difference']:+d})\n"
        f"- Points: {rec['points']}, Win rate: {rec['win_rate']}%"
    )


def format_players(players: List[dict], title: Optional[str] = None) -> str:
    if not players:
        return f"No players found{(' for ' + title) if title else ''}."
    lines = [title] if title else []
    for i, p in enumerate(players, start=1):
        overall = p.get("overall")
        ov = f"Overall: {overall}" if overall is not None else "Overall: n/a"
        pos = p.get("position") or "?"
        club = p.get("club") or "Unknown club"
        lines.append(f"{i}. {p['name']} - {ov}, Position: {pos}, Club: {club}")
    return "\n".join(lines)


def format_standings(table: List[dict], competition: str, season: int,
                     limit: int = 20) -> str:
    if not table:
        return f"No standings available for {competition} {season}."
    lines = [f"{season} {competition} standings (calculated from matches):"]
    for t in table[:limit]:
        tag = ""
        if t["position"] == 1:
            tag = " - Champion"
        lines.append(
            f"{t['position']}. {t['team']} - {t['points']} pts "
            f"({t['wins']}W {t['draws']}D {t['losses']}L, "
            f"GF {t['goals_for']} GA {t['goals_against']}, GD {t['goal_difference']:+d})"
            f"{tag}"
        )
    return "\n".join(lines)


def format_statistics(stats: dict, scope: str = "") -> str:
    header = f"Statistics{(' for ' + scope) if scope else ''}:"
    return (
        f"{header}\n"
        f"- Matches: {stats['matches']}\n"
        f"- Average goals per match: {stats['avg_goals']}\n"
        f"- Home win rate: {stats['home_win_rate']}%\n"
        f"- Away win rate: {stats['away_win_rate']}%\n"
        f"- Draw rate: {stats['draw_rate']}%"
    )


def format_biggest_wins(matches: List[dict], scope: str = "") -> str:
    if not matches:
        return "No matches found."
    lines = [f"Biggest victories{(' in ' + scope) if scope else ''}:"]
    for i, m in enumerate(matches, start=1):
        lines.append(
            f"{i}. {m.get('date','????')}: {m['home_team']} "
            f"{m['home_goal']}-{m['away_goal']} {m['away_team']} "
            f"({m['competition']}, margin {m['margin']})"
        )
    return "\n".join(lines)


def format_best_record(records: List[dict], scope: str = "", venue: str = "home",
                       limit: int = 10) -> str:
    if not records:
        return "No records found."
    lines = [f"Best {venue} records{(' in ' + scope) if scope else ''}:"]
    for i, r in enumerate(records[:limit], start=1):
        lines.append(
            f"{i}. {r['team']} - {r['win_rate']}% "
            f"({r['wins']}W {r['draws']}D {r['losses']}L, "
            f"GF {r['goals_for']} GA {r['goals_against']})"
        )
    return "\n".join(lines)
