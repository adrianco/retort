"""
Context
=======
Module: brazilian_soccer.formatters

Turns the dicts produced by graph.py into the compact human-readable text shown
in the specification's "Example answer format" blocks.  The MCP tools return
this text *and* the underlying JSON, so an LLM can quote a ready-made answer or
re-aggregate the structured data itself.

Pure presentation: no data access, no I/O -- which keeps it trivially testable.
"""

from __future__ import annotations


def format_match(match: dict, *, with_competition: bool = True) -> str:
    when = match.get("date") or f"season {match.get('season')}"
    line = (
        f"{when}: {match['home_team']} {match['home_goals']}-{match['away_goals']} "
        f"{match['away_team']}"
    )
    if with_competition:
        detail = match.get("competition", "")
        if match.get("stage"):
            detail += f" {match['stage']}"
        elif match.get("round"):
            detail += f" Round {match['round']}"
        line += f" ({detail.strip()})"
    return line


def format_match_list(matches: list[dict], *, header: str = "", total: int | None = None) -> str:
    if not matches:
        return f"{header}\nNo matches found." if header else "No matches found."
    lines = [header] if header else []
    lines += [f"- {format_match(m)}" for m in matches]
    if total is not None and total > len(matches):
        lines.append(f"... ({total - len(matches)} more matches in dataset)")
    return "\n".join(lines)


def format_record(record: dict, *, title: str) -> str:
    return "\n".join([
        f"{title}:",
        f"- Matches: {record['matches']}",
        f"- Wins: {record['wins']}, Draws: {record['draws']}, Losses: {record['losses']}",
        f"- Goals For: {record['goals_for']}, Goals Against: {record['goals_against']}"
        f" (diff {record['goal_difference']:+d})",
        f"- Points: {record['points']}",
        f"- Win rate: {record['win_rate']}%",
    ])


def format_team_stats(stats: dict) -> str:
    scope = []
    if stats["competition"] != "all":
        scope.append(str(stats["competition"]))
    if stats["season"] != "all":
        scope.append(str(stats["season"]))
    title = f"{stats['team']} record" + (f" ({' '.join(scope)})" if scope else "")
    parts = [format_record(stats["overall"], title=title)]
    if stats["home"]["matches"] and stats["venue"] == "any":
        parts.append(format_record(stats["home"], title=f"{stats['team']} home"))
        parts.append(format_record(stats["away"], title=f"{stats['team']} away"))
    if stats["biggest_win"]:
        parts.append("Biggest win: " + format_match(stats["biggest_win"]))
    if stats["biggest_loss"]:
        parts.append("Biggest loss: " + format_match(stats["biggest_loss"]))
    return "\n\n".join(parts)


def format_head_to_head(h2h: dict) -> str:
    label = f"{h2h['team_a']} vs {h2h['team_b']}"
    if h2h.get("derby"):
        label += f" ({h2h['derby']} derby)"
    rec_a, rec_b = h2h["team_a_record"], h2h["team_b_record"]
    lines = [f"{label}:"]
    lines += [f"- {format_match(m)}" for m in h2h["matches"]]
    remaining = h2h["total_matches"] - len(h2h["matches"])
    if remaining > 0:
        lines.append(f"... ({remaining} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {h2h['team_a']} {rec_a['wins']} wins, "
        f"{h2h['team_b']} {rec_b['wins']} wins, {rec_a['draws']} draws "
        f"({rec_a['goals_for']}-{rec_b['goals_for']} on goals)"
    )
    return "\n".join(lines)


def format_standings(standings: dict) -> str:
    if not standings["table"]:
        return f"No data for {standings['competition']} {standings['season']}."
    lines = [
        f"{standings['season']} {standings['competition']} table "
        f"(calculated from {standings['matches_counted']} matches):"
    ]
    for row in standings["table"]:
        suffix = ""
        if row["position"] == 1 and standings.get("champion"):
            suffix = " - Champion"
        elif standings.get("relegated") and row["team"] in standings["relegated"]:
            suffix = " - Relegated"
        lines.append(
            f"{row['position']}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L, "
            f"{row['goals_for']}:{row['goals_against']}){suffix}"
        )
    if standings.get("note"):
        lines.append(f"Note: {standings['note']}")
    return "\n".join(lines)


def format_players(players: list[dict], *, header: str = "Players") -> str:
    if not players:
        return "No players found."
    lines = [f"{header}:"]
    for index, player in enumerate(players, start=1):
        club = player.get("club") or "free agent"
        lines.append(
            f"{index}. {player['name']} - Overall: {player['overall']}, "
            f"Position: {player.get('position') or 'n/a'}, Club: {club}"
            f" ({player.get('nationality')}, age {player.get('age')})"
        )
    return "\n".join(lines)


def format_statistics(stats: dict) -> str:
    if not stats.get("matches"):
        return "No matches match these filters."
    scope = f"{stats.get('competition', 'all')} {stats.get('season', 'all')}".strip()
    return "\n".join([
        f"Statistics for {scope} ({stats['matches']} matches):",
        f"- Average goals per match: {stats['goals_per_match']}",
        f"- Home win rate: {stats['home_win_rate']}%",
        f"- Away win rate: {stats['away_win_rate']}%",
        f"- Draw rate: {stats['draw_rate']}%",
        f"- Goals: {stats['home_goals']} home, {stats['away_goals']} away "
        f"({stats['total_goals']} total)",
        f"- Goalless draws: {stats['goalless_draws']}",
        f"- Teams involved: {stats['teams_involved']}",
    ])


def format_biggest_wins(matches: list[dict], *, header: str = "Biggest victories") -> str:
    if not matches:
        return "No matches found."
    lines = [f"{header}:"]
    for index, match in enumerate(matches, start=1):
        lines.append(f"{index}. {format_match(match)} [margin {match['margin']}]")
    return "\n".join(lines)


def format_leaderboard(rows: list[dict], *, metric: str) -> str:
    if not rows:
        return "No teams match these filters."
    lines = [f"Teams ranked by {metric}:"]
    for index, row in enumerate(rows, start=1):
        lines.append(
            f"{index}. {row['team']} - {metric}: {row[metric]} "
            f"({row['matches']} matches, {row['wins']}W/{row['draws']}D/{row['losses']}L)"
        )
    return "\n".join(lines)
