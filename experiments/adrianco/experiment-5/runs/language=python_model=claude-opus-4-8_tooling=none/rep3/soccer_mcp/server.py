# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : soccer_mcp.server
# Purpose : The MCP (Model Context Protocol) server. A thin adapter that loads
#           the KnowledgeGraph once at start-up and exposes its query API as MCP
#           tools over stdio, so an LLM client (Claude Desktop, etc.) can answer
#           natural-language questions about Brazilian soccer.
# Transport: stdio (the standard MCP local-server transport). Run with
#            `python -m soccer_mcp.server`.
# Tools   : find_matches, head_to_head, team_stats, find_players,
#           player_club_summary, standings, league_champion, statistics,
#           biggest_wins, top_scoring_teams, list_competitions.
# Design  : Each tool returns formatted text (see formatting.py) so the model
#           gets a ready-to-present answer; the underlying structured data lives
#           in KnowledgeGraph for any caller that wants the raw numbers.
# =============================================================================

from __future__ import annotations

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import formatting
from .data_loader import DEFAULT_DATA_DIR
from .knowledge_graph import KnowledgeGraph

# Allow overriding the dataset location via env var for deployment flexibility.
DATA_DIR = os.environ.get("SOCCER_DATA_DIR", DEFAULT_DATA_DIR)

mcp = FastMCP("brazilian-soccer")

# The graph is loaded lazily so importing this module (e.g. for help text)
# never forces a multi-thousand-row parse until a tool is actually called.
_graph: Optional[KnowledgeGraph] = None


def get_graph() -> KnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph.load(DATA_DIR)
    return _graph


# --------------------------------------------------------------------------- #
# Match queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    venue: Optional[str] = None,
    limit: int = 25,
) -> str:
    """Find matches by team, opponent, competition, season or date range.

    Args:
        team: Team name (any naming variation, e.g. "Flamengo").
        opponent: Restrict to matches against this specific opponent.
        competition: "Brasileirão", "Copa do Brasil" or "Libertadores".
        season: Season year, e.g. 2019.
        start_date / end_date: ISO dates "YYYY-MM-DD" to bound the range.
        venue: "home" or "away" relative to `team` (default: either).
        limit: Maximum number of matches to return.
    """
    matches = get_graph().find_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        start_date=start_date, end_date=end_date, venue=venue, limit=limit,
    )
    title = "Matches"
    if team and opponent:
        title = f"{team} vs {opponent}"
    elif team:
        title = f"{team} matches"
    return formatting.format_matches(matches, title=title)


@mcp.tool()
def head_to_head(team1: str, team2: str) -> str:
    """Head-to-head record between two teams across all competitions."""
    return formatting.format_head_to_head(get_graph().head_to_head(team1, team2))


# --------------------------------------------------------------------------- #
# Team queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def team_stats(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: Optional[str] = None,
) -> str:
    """Win/draw/loss and goal record for a team, optionally filtered by
    season, competition and venue ("home"/"away")."""
    return formatting.format_team_stats(
        get_graph().team_stats(team, season=season, competition=competition, venue=venue)
    )


# --------------------------------------------------------------------------- #
# Player queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def find_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    sort_by: str = "overall",
    limit: int = 25,
) -> str:
    """Search the FIFA player database.

    Args:
        name: Substring of the player's name.
        nationality: e.g. "Brazil".
        club: Club name (any variation).
        position: Exact position code, e.g. "LW", "GK", "ST".
        min_overall: Minimum FIFA overall rating.
        sort_by: "overall" (default), "potential", "age" or "name".
        limit: Maximum players to return.
    """
    players = get_graph().find_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, sort_by=sort_by, limit=limit,
    )
    return formatting.format_players(players, title="Players")


@mcp.tool()
def player_club_summary(nationality: Optional[str] = None, limit: int = 25) -> str:
    """Players grouped by club (count + average rating), optionally filtered to
    one nationality (e.g. Brazilian players by club)."""
    summary = get_graph().players_by_club_summary(nationality=nationality)[:limit]
    if not summary:
        return "No players found."
    label = f"{nationality} players by club" if nationality else "Players by club"
    lines = [f"{label}:"]
    lines += [
        f"- {row['club']}: {row['players']} players (avg rating: {row['avg_overall']})"
        for row in summary
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Competition queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def standings(competition: str, season: int) -> str:
    """Compute the final league table for a competition/season from results."""
    rows = get_graph().standings(competition, season)
    return formatting.format_standings(rows, title=f"{competition} {season} standings")


@mcp.tool()
def league_champion(competition: str, season: int) -> str:
    """Who won a league season (top of the computed standings)."""
    champ = get_graph().champion(competition, season)
    if not champ:
        return f"No data for {competition} {season}."
    return (
        f"{competition} {season} champion: {champ['team']} "
        f"({champ['points']} pts, {champ['wins']}W {champ['draws']}D {champ['losses']}L)"
    )


# --------------------------------------------------------------------------- #
# Statistical analysis
# --------------------------------------------------------------------------- #
@mcp.tool()
def statistics(competition: Optional[str] = None, season: Optional[int] = None) -> str:
    """Aggregate statistics (avg goals/match, home/away win rates) for a
    competition and/or season, or across all data when unfiltered."""
    return formatting.format_statistics(get_graph().statistics(competition, season))


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
) -> str:
    """The largest goal-margin victories within the given filter."""
    matches = get_graph().biggest_wins(competition, season, limit=limit)
    return formatting.format_matches(matches, title="Biggest wins", max_rows=limit)


@mcp.tool()
def top_scoring_teams(
    competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
) -> str:
    """Teams ranked by total goals scored within the given filter."""
    ranked = get_graph().top_scoring_teams(competition, season, limit=limit)
    if not ranked:
        return "No data."
    lines = ["Top scoring teams:"]
    lines += [
        f"{i}. {r['team']} - {r['goals']} goals in {r['matches']} matches"
        for i, r in enumerate(ranked, start=1)
    ]
    return "\n".join(lines)


@mcp.tool()
def list_competitions() -> str:
    """List the competitions and season range available in the dataset."""
    g = get_graph()
    comps = g.competitions()
    seasons = g.seasons()
    span = f"{seasons[0]}-{seasons[-1]}" if seasons else "n/a"
    return (
        f"Competitions: {', '.join(comps)}\n"
        f"Seasons: {span}\n"
        f"Matches: {len(g.matches)}, Players: {len(g.players)}, Teams: {g.team_count()}"
    )


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
