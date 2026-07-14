"""Human-readable formatters that turn query results into text answers.

These produce the answer style shown in the specification and are used by the
MCP tools.
"""

from __future__ import annotations

from typing import List

from .knowledge_graph import TeamRecord
from .models import Match, Player


def format_matches(matches: List[Match], header: str = "", max_show: int = 20) -> str:
    if not matches:
        return (header + "\n" if header else "") + "No matches found."
    lines = []
    if header:
        lines.append(header)
    for m in matches[:max_show]:
        lines.append(f"- {m.describe()}")
    if len(matches) > max_show:
        lines.append(f"... ({len(matches) - max_show} more matches in dataset)")
    return "\n".join(lines)


def format_head_to_head(h2h: dict, max_show: int = 10) -> str:
    if h2h["total"] == 0:
        return f"No matches found between {h2h['team1']} and {h2h['team2']}."
    lines = [f"{h2h['team1']} vs {h2h['team2']}:"]
    for m in h2h["matches"][:max_show]:
        lines.append(f"- {m.describe()}")
    if h2h["total"] > max_show:
        lines.append(f"... ({h2h['total'] - max_show} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {h2h['team1']} {h2h['team1_wins']} wins, "
        f"{h2h['team2']} {h2h['team2_wins']} wins, {h2h['draws']} draws"
    )
    return "\n".join(lines)


def format_team_record(rec: TeamRecord, season=None, competition=None,
                       venue="either") -> str:
    scope = []
    if venue != "either":
        scope.append(venue)
    if season:
        scope.append(str(season))
    if competition:
        scope.append(competition)
    scope_str = (" (" + " ".join(scope) + ")") if scope else ""
    return (
        f"{rec.team}{scope_str} record:\n"
        f"- Matches: {rec.matches}\n"
        f"- Wins: {rec.wins}, Draws: {rec.draws}, Losses: {rec.losses}\n"
        f"- Goals For: {rec.goals_for}, Goals Against: {rec.goals_against}\n"
        f"- Points: {rec.points}\n"
        f"- Win rate: {rec.win_rate:.1f}%"
    )


def format_standings(table: List[TeamRecord], competition: str, season: int,
                     max_show: int = 20) -> str:
    if not table:
        return f"No data for {competition} {season}."
    lines = [f"{season} {competition} Final Standings (calculated from matches):"]
    for i, r in enumerate(table[:max_show], start=1):
        tag = " - Champion" if i == 1 else ""
        lines.append(
            f"{i}. {r.team} - {r.points} pts "
            f"({r.wins}W, {r.draws}D, {r.losses}L) "
            f"GD {r.goal_diff:+d}{tag}"
        )
    return "\n".join(lines)


def format_players(players: List[Player], header: str = "") -> str:
    if not players:
        return (header + "\n" if header else "") + "No players found."
    lines = []
    if header:
        lines.append(header)
    for i, p in enumerate(players, start=1):
        lines.append(f"{i}. {p.describe()}")
    return "\n".join(lines)


def format_biggest_wins(matches: List[Match], header: str = "Biggest victories:") -> str:
    if not matches:
        return "No matches found."
    lines = [header]
    for i, m in enumerate(matches, start=1):
        margin = abs((m.home_goal or 0) - (m.away_goal or 0))
        lines.append(f"{i}. {m.describe()}  [margin {margin}]")
    return "\n".join(lines)


def format_stats(stats: dict, header: str = "Match statistics:") -> str:
    return (
        f"{header}\n"
        f"- Matches analysed: {stats['matches']}\n"
        f"- Average goals per match: {stats['avg_goals']}\n"
        f"- Home win rate: {stats['home_win_rate']}%\n"
        f"- Away win rate: {stats['away_win_rate']}%\n"
        f"- Draw rate: {stats['draw_rate']}%"
    )
