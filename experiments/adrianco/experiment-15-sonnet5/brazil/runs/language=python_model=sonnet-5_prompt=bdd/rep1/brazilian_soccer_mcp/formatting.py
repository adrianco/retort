"""Turns QueryEngine results (DataFrames/dicts) into the human-readable
text the MCP tools return, in the style shown by TASK.md's example answer
formats.
"""

from __future__ import annotations

import pandas as pd

MAX_MATCHES_SHOWN = 15
MAX_PLAYERS_SHOWN = 25


def _match_label(row) -> str:
    if pd.notna(row.get("round")) and str(row["round"]).strip():
        return f"{row['competition']} Round {row['round']}"
    if pd.notna(row.get("stage")):
        return f"{row['competition']} ({str(row['stage']).title()})"
    return str(row["competition"])


def _match_line(row) -> str:
    date_str = row["date"] if pd.notna(row["date"]) else "date unknown"
    if pd.notna(row["home_goal"]) and pd.notna(row["away_goal"]):
        score = f"{row['home_goal']}-{row['away_goal']}"
    else:
        score = "vs"
    return f"{date_str}: {row['home_team']} {score} {row['away_team']} ({_match_label(row)})"


def format_matches(matches: pd.DataFrame, header: str | None = None) -> str:
    if matches.empty:
        return "No matches found for that query."
    lines = [f"- {_match_line(row)}" for _, row in matches.head(MAX_MATCHES_SHOWN).iterrows()]
    remaining = len(matches) - MAX_MATCHES_SHOWN
    if remaining > 0:
        lines.append(f"- ... ({remaining} more matches in dataset)")
    body = "\n".join(lines)
    return f"{header}\n{body}" if header else body


def format_head_to_head(result: dict) -> str:
    header = f"{result['team_a']} vs {result['team_b']} ({result['total']} matches in dataset):"
    body = format_matches(result["matches"])
    summary = (
        f"Head-to-head in dataset: {result['team_a']} {result['wins_a']} wins, "
        f"{result['team_b']} {result['wins_b']} wins, {result['draws']} draws"
    )
    return f"{header}\n{body}\n\n{summary}"


def _record_scope(record: dict) -> str:
    parts = []
    if record.get("competition"):
        parts.append(str(record["competition"]))
    if record.get("season") is not None:
        parts.append(str(record["season"]))
    if record.get("venue"):
        parts.append(record["venue"])
    return f" ({', '.join(parts)})" if parts else ""


def format_team_record(record: dict) -> str:
    lines = [
        f"{record['team']} record{_record_scope(record)}:",
        f"- Matches: {record['played']}",
        f"- Wins: {record['wins']}, Draws: {record['draws']}, Losses: {record['losses']}",
        f"- Goals For: {record['goals_for']}, Goals Against: {record['goals_against']} "
        f"(GD: {record['goal_diff']:+d})",
        f"- Win rate: {record['win_rate']}%",
    ]
    return "\n".join(lines)


def format_compare_teams(result: dict) -> str:
    parts = [
        format_team_record(result["team_a"]),
        "",
        format_team_record(result["team_b"]),
        "",
        format_head_to_head(result["head_to_head"]),
    ]
    return "\n".join(parts)


def format_top_scoring(table: pd.DataFrame) -> str:
    if table.empty:
        return "No data found for that query."
    lines = [f"{i}. {row['team']} - {int(row['goals'])} goals" for i, (_, row) in enumerate(table.iterrows(), 1)]
    return "\n".join(lines)


def format_players(players: pd.DataFrame) -> str:
    if players.empty:
        return "No players found."
    lines = []
    for i, (_, row) in enumerate(players.head(MAX_PLAYERS_SHOWN).iterrows(), 1):
        overall = row["overall"] if pd.notna(row["overall"]) else "?"
        position = row["position"] if pd.notna(row["position"]) else "?"
        club = row["club_raw"] if pd.notna(row["club_raw"]) else "Free agent"
        lines.append(f"{i}. {row['name']} - Overall: {overall}, Position: {position}, Club: {club}")
    remaining = len(players) - MAX_PLAYERS_SHOWN
    if remaining > 0:
        lines.append(f"... ({remaining} more players in dataset)")
    return "\n".join(lines)


def format_brazilian_players_by_club(table: pd.DataFrame) -> str:
    if table.empty:
        return "No matching Brazilian players found at clubs in the match dataset."
    lines = [f"- {row['club']}: {int(row['players'])} players (avg rating: {row['avg_overall']})" for _, row in table.iterrows()]
    return "\n".join(lines)


def format_standings(table: pd.DataFrame, competition: str, season: int) -> str:
    header = f"{season} {competition} Standings (calculated from matches):"
    lines = [header]
    for _, row in table.iterrows():
        suffix = " - Champion" if row["position"] == 1 else ""
        lines.append(
            f"{row['position']}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L){suffix}"
        )
    return "\n".join(lines)


def format_champion(result: dict) -> str:
    header = f"{result['season']} {result['competition']} Champion: {result['champion'] or 'Draw on aggregate'}"
    if "standings_row" in result:
        row = result["standings_row"]
        return (
            f"{header}\n"
            f"({row['points']} pts, {row['wins']}W-{row['draws']}D-{row['losses']}L, "
            f"GD {row['goal_diff']:+d})"
        )
    aggregate_lines = [f"{entry['team']} {entry['goals_for']}-{entry['goals_against']}" for entry in result["aggregate"]]
    text = f"{header}\nFinal aggregate: {' vs '.join(aggregate_lines)}"
    if result.get("note"):
        text += f"\nNote: {result['note']}"
    return text


def format_biggest_wins(table: pd.DataFrame) -> str:
    if table.empty:
        return "No data found for that query."
    lines = []
    for i, (_, row) in enumerate(table.iterrows(), 1):
        lines.append(
            f"{i}. {row['date']}: {row['home_team']} {row['home_goal']}-{row['away_goal']} "
            f"{row['away_team']} ({row['competition']} {row['season']})"
        )
    return "\n".join(lines)


def format_best_away_record(table: pd.DataFrame) -> str:
    if table.empty:
        return "No teams met the minimum match threshold."
    lines = [
        f"{i}. {row['team']} - {row['wins']}/{row['played']} away wins ({row['win_rate']}%)"
        for i, (_, row) in enumerate(table.iterrows(), 1)
    ]
    return "\n".join(lines)


def format_statistics(average_goals: float, home_win_rate: float) -> str:
    return f"Average goals per match: {average_goals}\nHome win rate: {home_win_rate}%"
