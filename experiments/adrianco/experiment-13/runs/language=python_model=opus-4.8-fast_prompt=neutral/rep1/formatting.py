"""
================================================================================
Module: formatting.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
-------
Pure presentation layer.  Turns the structured dicts/lists returned by
:mod:`knowledge_graph` into the human-readable text blocks shown in the
specification's "Example answer format" sections (match lists, head-to-head
summaries, league tables, player rankings, etc.).

Keeping formatting separate from the query engine means:
  * the engine stays JSON-friendly and easy to unit-test, and
  * the MCP tool layer (``server.py``) is a thin wiring layer.

Every function takes plain Python data and returns a ``str``.  No pandas, no I/O.
================================================================================
"""

from __future__ import annotations


def _score_line(m: dict) -> str:
    """Render one match as a single line, e.g.
    '2019-11-11: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 33)'."""
    date = m.get("date") or "date unknown"
    hg = m.get("home_goal")
    ag = m.get("away_goal")
    score = f"{hg}-{ag}" if hg is not None and ag is not None else "vs"
    comp = m.get("competition", "")
    stage = m.get("stage")
    context = f"{comp}, {stage}" if stage else comp
    return f"- {date}: {m['home_team']} {score} {m['away_team']} ({context})"


def format_matches(matches: list[dict], team: str | None = None, opponent: str | None = None) -> str:
    if not matches:
        who = " ".join(x for x in [team, ("vs " + opponent) if opponent else None] if x)
        return f"No matches found{(' for ' + who) if who else ''}."

    header_bits = [x for x in [team, ("vs " + opponent) if opponent else None] if x]
    header = f"Matches{(' for ' + ' '.join(header_bits)) if header_bits else ''} "
    header += f"({len(matches)} shown, most recent first):"
    lines = [header] + [_score_line(m) for m in matches]
    return "\n".join(lines)


def format_head_to_head(data: dict) -> str:
    t1, t2 = data["team1"], data["team2"]
    if data["total_matches"] == 0:
        return f"No matches found between {t1} and {t2} in the dataset."

    lines = [
        f"{t1} vs {t2} — head-to-head ({data['total_matches']} matches in dataset):",
        f"  {t1}: {data['team1_wins']} wins",
        f"  {t2}: {data['team2_wins']} wins",
        f"  Draws: {data['draws']}",
        f"  Goals: {t1} {data['team1_goals']} — {data['team2_goals']} {t2}",
        "",
        "Most recent meetings:",
    ]
    for m in data["matches"][:5]:
        lines.append(_score_line(m))
    remaining = data["total_matches"] - min(5, len(data["matches"]))
    if remaining > 0:
        lines.append(f"  ... ({remaining} more in dataset)")
    return "\n".join(lines)


def format_team_record(rec: dict) -> str:
    scope = []
    if rec.get("season"):
        scope.append(str(rec["season"]))
    if rec.get("competition"):
        scope.append(rec["competition"])
    venue = rec.get("venue", "all")
    venue_label = {"home": "home ", "away": "away ", "all": ""}[venue]
    scope_label = (" (" + ", ".join(scope) + ")") if scope else ""

    return "\n".join([
        f"{rec['team']} {venue_label}record{scope_label}:",
        f"- Matches: {rec['played']}",
        f"- Wins: {rec['wins']}, Draws: {rec['draws']}, Losses: {rec['losses']}",
        f"- Goals For: {rec['goals_for']}, Goals Against: {rec['goals_against']} "
        f"(GD {rec['goal_difference']:+d})",
        f"- Points: {rec['points']}",
        f"- Win rate: {rec['win_rate']}%",
    ])


def format_standings(table: list[dict], competition: str, season: int, top: int = 20) -> str:
    if not table:
        return f"No standings could be computed for {competition} {season}."

    lines = [f"{season} {competition} — Final Standings (calculated from matches):"]
    for r in table[:top]:
        tag = " — Champion" if r["position"] == 1 else ""
        lines.append(
            f"{r['position']:>2}. {r['team']:<22} {r['points']:>3} pts "
            f"({r['wins']}W {r['draws']}D {r['losses']}L, "
            f"GF {r['goals_for']} GA {r['goals_against']}, GD {r['goal_difference']:+d}){tag}"
        )
    if len(table) > top:
        lines.append(f"... ({len(table) - top} more)")
    return "\n".join(lines)


def format_top_scorers(teams: list[dict], competition: str, season: int) -> str:
    if not teams:
        return f"No data for {competition} {season}."
    lines = [f"Top scoring teams — {season} {competition}:"]
    for i, t in enumerate(teams, 1):
        lines.append(f"{i}. {t['team']} — {t['goals_for']} goals in {t['played']} matches")
    return "\n".join(lines)


def format_average_goals(stats: dict) -> str:
    if stats["matches"] == 0:
        return "No matches found for the requested filters."
    scope = []
    if stats.get("competition"):
        scope.append(stats["competition"])
    if stats.get("season"):
        scope.append(str(stats["season"]))
    scope_label = (" (" + ", ".join(scope) + ")") if scope else ""
    return "\n".join([
        f"Match statistics{scope_label}:",
        f"- Matches analysed: {stats['matches']}",
        f"- Total goals: {stats['total_goals']}",
        f"- Average goals per match: {stats['avg_goals_per_match']}",
        f"- Home win rate: {stats['home_win_rate']}%",
        f"- Draw rate: {stats['draw_rate']}%",
        f"- Away win rate: {stats['away_win_rate']}%",
    ])


def format_biggest_wins(wins: list[dict]) -> str:
    if not wins:
        return "No matches found for the requested filters."
    lines = ["Biggest victories (by goal margin):"]
    for i, m in enumerate(wins, 1):
        date = m.get("date") or "date unknown"
        lines.append(
            f"{i}. {date}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']} ({m['competition']}) — margin {m['margin']}"
        )
    return "\n".join(lines)


def format_players(players: list[dict]) -> str:
    if not players:
        return "No players found for the requested filters."
    lines = [f"{len(players)} player(s) found:"]
    for i, p in enumerate(players, 1):
        club = p.get("club") or "Unknown club"
        pos = p.get("position") or "?"
        lines.append(
            f"{i}. {p['name']} — Overall: {p['overall']}, Position: {pos}, Club: {club}"
        )
    return "\n".join(lines)


def format_player_detail(p: dict) -> str:
    return "\n".join([
        f"{p['name']}",
        f"- Nationality: {p.get('nationality')}",
        f"- Age: {p.get('age')}",
        f"- Overall: {p.get('overall')} (Potential: {p.get('potential')})",
        f"- Position: {p.get('position')}",
        f"- Club: {p.get('club')}",
        f"- Value: {p.get('value')}",
    ])


def format_players_by_club(rows: list[dict]) -> str:
    if not rows:
        return "No Brazilian players with club data found."
    lines = ["Brazilian players by club (most first):"]
    for r in rows:
        lines.append(f"- {r['club']}: {r['players']} players (avg rating: {r['avg_overall']})")
    return "\n".join(lines)
