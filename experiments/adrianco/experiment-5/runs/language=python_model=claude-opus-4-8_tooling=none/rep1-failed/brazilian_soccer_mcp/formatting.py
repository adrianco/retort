"""
================================================================================
Brazilian Soccer MCP Server - Response Formatting
================================================================================

CONTEXT
-------
Turns the structured results from ``KnowledgeGraph`` into the human-readable,
LLM-friendly text blocks illustrated in the specification's "Example answer
format" sections. Keeping formatting separate from the engine means the engine
stays pure-data (and easily unit-tested) while the MCP tools return nicely
rendered strings.

Pure standard library; imported by ``server`` and usable directly in tests.
================================================================================
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional

from .models import Match, Player


def format_matches(matches: List[Match], header: Optional[str] = None,
                   max_rows: int = 25) -> str:
    if not matches:
        return (header + "\n" if header else "") + "No matches found."
    lines = []
    if header:
        lines.append(header)
    shown = matches[:max_rows]
    for m in shown:
        lines.append("- " + m.describe())
    remaining = len(matches) - len(shown)
    if remaining > 0:
        lines.append(f"- ... ({remaining} more matches in dataset)")
    return "\n".join(lines)


def format_head_to_head(h2h: Dict[str, Any], max_rows: int = 15) -> str:
    a, b = h2h["team_a"], h2h["team_b"]
    lines = [f"{a} vs {b}:"]
    shown = h2h["matches"][:max_rows]
    for m in shown:
        lines.append("- " + m.describe())
    remaining = h2h["total"] - len(shown)
    if remaining > 0:
        lines.append(f"- ... ({remaining} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {a} {h2h['team_a_wins']} wins, "
        f"{b} {h2h['team_b_wins']} wins, {h2h['draws']} draws "
        f"(goals {h2h['team_a_goals']}-{h2h['team_b_goals']})"
    )
    return "\n".join(lines)


def format_team_stats(stats: Dict[str, Any]) -> str:
    venue = stats.get("venue", "all")
    venue_label = {"all": "", "home": " home", "away": " away"}.get(venue, "")
    season = stats.get("season")
    comp = stats.get("competition")
    scope = []
    if season:
        scope.append(str(season))
    if comp:
        scope.append(comp)
    scope_str = f" ({', '.join(scope)})" if scope else ""
    return (
        f"{stats['team']}{venue_label} record{scope_str}:\n"
        f"- Matches: {stats['matches']}\n"
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, "
        f"Losses: {stats['losses']}\n"
        f"- Goals For: {stats['goals_for']}, "
        f"Goals Against: {stats['goals_against']} "
        f"(GD: {stats['goal_difference']:+d})\n"
        f"- Points: {stats['points']}\n"
        f"- Win rate: {stats['win_rate']}%"
    )


def format_players(players: List[Player], header: Optional[str] = None,
                  max_rows: int = 25) -> str:
    if not players:
        return (header + "\n" if header else "") + "No players found."
    lines = []
    if header:
        lines.append(header)
    shown = players[:max_rows]
    for i, p in enumerate(shown, start=1):
        lines.append(f"{i}. {p.describe()}")
    remaining = len(players) - len(shown)
    if remaining > 0:
        lines.append(f"... ({remaining} more players in dataset)")
    return "\n".join(lines)


def format_standings(rows: List[Dict[str, Any]], season: int,
                    competition: str, max_rows: int = 30) -> str:
    if not rows:
        return f"No standings could be computed for {competition} {season}."
    lines = [f"{season} {competition} Final Standings (calculated from matches):"]
    for r in rows[:max_rows]:
        tag = " - Champion" if r["position"] == 1 else ""
        lines.append(
            f"{r['position']}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L), "
            f"GD {r['goal_difference']:+d}{tag}"
        )
    return "\n".join(lines)


def format_venue_ranking(rows: List[Dict[str, Any]], venue: str,
                        max_rows: int = 15) -> str:
    if not rows:
        return f"No {venue} records available."
    lines = [f"Best {venue} records:"]
    for i, r in enumerate(rows[:max_rows], start=1):
        lines.append(
            f"{i}. {r['team']} - {r['win_rate']}% "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L in {r['matches']} "
            f"{venue} matches, GF {r['goals_for']}/GA {r['goals_against']})"
        )
    return "\n".join(lines)


def format_biggest_wins(matches: List[Match],
                       header: str = "Biggest victories") -> str:
    if not matches:
        return "No matches found."
    lines = [header + ":"]
    for i, m in enumerate(matches, start=1):
        margin = abs(m.home_goal - m.away_goal)
        lines.append(f"{i}. {m.describe()} (margin {margin})")
    return "\n".join(lines)
