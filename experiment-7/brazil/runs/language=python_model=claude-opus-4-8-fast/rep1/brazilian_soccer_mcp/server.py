"""
================================================================================
brazilian_soccer_mcp.server
================================================================================

CONTEXT
-------
The MCP (Model Context Protocol) server. It exposes the KnowledgeGraph query
engine as a set of MCP *tools* an LLM can call to answer natural-language
questions about Brazilian soccer (players, teams, matches, competitions, stats).

This module is a thin adapter: every tool validates/forwards its arguments to a
``KnowledgeGraph`` method and renders the result with ``formatting``. All real
logic lives in ``knowledge_graph`` so it can be tested without a running server.

Run it with stdio transport (the default MCP transport for local servers):

    python -m brazilian_soccer_mcp.server
        or
    python run_server.py

The heavy CSV load happens once, lazily, on the first tool call (and is cached),
keeping start-up instant and satisfying the latency requirements in the spec.
================================================================================
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import formatting
from .knowledge_graph import KnowledgeGraph, get_knowledge_graph

mcp = FastMCP("brazilian-soccer")


def _kg() -> KnowledgeGraph:
    return get_knowledge_graph()


# ---------------------------------------------------------------------------
# 1. MATCH QUERIES
# ---------------------------------------------------------------------------
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 25,
) -> str:
    """Find matches by team, opponent, competition, season and/or date range.

    Args:
        team: A team name (matches whether it played home or away).
        opponent: Restrict to matches against this opponent.
        competition: e.g. "Brasileirão", "Copa do Brasil", "Libertadores".
        season: Season/year, e.g. 2019.
        start_date / end_date: ISO dates ("YYYY-MM-DD") bounding the search.
        limit: Maximum number of matches to display.
    """
    matches = _kg().find_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        start_date=start_date, end_date=end_date,
    )
    title_parts = [p for p in [team, ("vs " + opponent) if opponent else None,
                               competition, str(season) if season else None] if p]
    title = " ".join(title_parts) if title_parts else None
    return formatting.format_matches(matches, title=title, limit=limit)


@mcp.tool()
def last_meeting(team1: str, team2: str) -> str:
    """Return the most recent match played between two teams."""
    m = _kg().last_meeting(team1, team2)
    if not m:
        return f"No matches found between {team1} and {team2}."
    return formatting.format_matches([m], title=f"Most recent {team1} vs {team2}:")


# ---------------------------------------------------------------------------
# 2. TEAM QUERIES
# ---------------------------------------------------------------------------
@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> str:
    """Win/draw/loss record, goals and win-rate for a team.

    Args:
        team: Team name.
        season: Optional season filter.
        competition: Optional competition filter.
        venue: "all", "home" or "away".
    """
    rec = _kg().team_record(team, season=season, competition=competition, venue=venue)
    return formatting.format_team_record(rec)


@mcp.tool()
def head_to_head(team1: str, team2: str, competition: Optional[str] = None) -> str:
    """Head-to-head record and match list between two teams."""
    h = _kg().head_to_head(team1, team2, competition=competition)
    return formatting.format_head_to_head(h)


# ---------------------------------------------------------------------------
# 3. PLAYER QUERIES
# ---------------------------------------------------------------------------
@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Search the FIFA player database.

    Args:
        name: Substring of the player's name.
        nationality: e.g. "Brazil".
        club: Club name (e.g. "Flamengo").
        position: Position code, e.g. "ST", "GK", "CB".
        min_overall: Minimum FIFA overall rating.
        limit: Max players to return (sorted by Overall, descending).
    """
    players = _kg().search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, limit=limit,
    )
    crit = [c for c in [name, nationality, club, position] if c]
    title = ("Players: " + ", ".join(crit)) if crit else "Players"
    return formatting.format_players(players, title=title)


# ---------------------------------------------------------------------------
# 4. COMPETITION QUERIES
# ---------------------------------------------------------------------------
@mcp.tool()
def standings(competition: str, season: int) -> str:
    """Compute the league table for a competition & season from match results."""
    table = _kg().standings(competition, season)
    return formatting.format_standings(table, competition, season)


@mcp.tool()
def champion(competition: str, season: int) -> str:
    """Return the champion (table winner) of a competition & season."""
    c = _kg().champion(competition, season)
    if not c:
        return f"No data for {competition} {season}."
    return (f"{season} {competition} champion: {c['team']} "
            f"({c['points']} pts, {c['wins']}W {c['draws']}D {c['losses']}L)")


@mcp.tool()
def relegated(competition: str, season: int, count: int = 4) -> str:
    """Return the bottom *count* teams (relegation zone) of a season's table."""
    teams = _kg().relegated(competition, season, count=count)
    if not teams:
        return f"No data for {competition} {season}."
    lines = [f"{season} {competition} bottom {count} (relegation zone):"]
    for t in teams:
        lines.append(f"{t['position']}. {t['team']} - {t['points']} pts")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5. STATISTICAL ANALYSIS
# ---------------------------------------------------------------------------
@mcp.tool()
def competition_statistics(
    competition: Optional[str] = None, season: Optional[int] = None
) -> str:
    """Average goals per match and home/away/draw rates for a scope."""
    stats = _kg().average_goals(competition=competition, season=season)
    scope = " ".join(p for p in [competition, str(season) if season else None] if p)
    return formatting.format_statistics(stats, scope=scope)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
) -> str:
    """List the matches with the largest goal margin in a scope."""
    matches = _kg().biggest_wins(competition=competition, season=season, limit=limit)
    scope = " ".join(p for p in [competition, str(season) if season else None] if p)
    return formatting.format_biggest_wins(matches, scope=scope)


@mcp.tool()
def best_record(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: str = "home",
    limit: int = 10,
) -> str:
    """Rank teams by win-rate for a venue (e.g. best home/away record)."""
    records = _kg().best_record(
        competition=competition, season=season, venue=venue
    )
    scope = " ".join(p for p in [competition, str(season) if season else None] if p)
    return formatting.format_best_record(records, scope=scope, venue=venue, limit=limit)


# ---------------------------------------------------------------------------
# Reference / discovery tools
# ---------------------------------------------------------------------------
@mcp.tool()
def list_competitions() -> str:
    """List the competitions available in the dataset."""
    comps = _kg().list_competitions()
    return "Available competitions:\n" + "\n".join(f"- {c}" for c in comps)


@mcp.tool()
def list_seasons(competition: Optional[str] = None) -> str:
    """List the seasons available, optionally for a given competition."""
    seasons = _kg().list_seasons(competition=competition)
    scope = competition or "all competitions"
    return f"Seasons for {scope}: " + ", ".join(str(s) for s in seasons)


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
