"""
MCP server for the Brazilian Soccer knowledge graph.

Context
-------
Exposes the :class:`knowledge_graph.KnowledgeGraph` query engine as a Model
Context Protocol (MCP) server using the official ``mcp`` Python SDK's
``FastMCP`` helper.  An LLM client (Claude Desktop, etc.) connects over stdio
and can call the registered tools to answer natural-language questions about
Brazilian soccer players, teams, matches, competitions and statistics.

The datasets are loaded once at start-up and held in memory, so every tool call
is an in-memory lookup that comfortably meets the spec's latency targets.

Run directly with:  ``python server.py``  (speaks MCP over stdio)

Tools registered (mirroring the five spec capability families):
    Match       : find_matches, head_to_head
    Team        : team_record, team_competitions
    Player      : search_players, top_brazilian_players, brazilian_players_by_club
    Competition : league_standings, list_seasons
    Statistics  : average_goals, biggest_wins, best_team_records
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

import formatters as fmt
from data_loader import parse_date
from knowledge_graph import KnowledgeGraph

mcp = FastMCP("brazilian-soccer")

# Load the knowledge graph once at import time.
KG = KnowledgeGraph.load()


# ----------------------------------------------------------------------------
# Match tools
# ----------------------------------------------------------------------------
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    venue: str = "either",
    limit: int = 20,
) -> str:
    """Find matches by team, opponent, competition, season and/or date range.

    Args:
        team: Team name (any spelling/suffix variant), e.g. "Flamengo".
        opponent: Restrict to matches against this opponent.
        competition: "Brasileirao", "Copa do Brasil" or "Libertadores".
        season: Four-digit year, e.g. 2019.
        start_date / end_date: ISO dates ("YYYY-MM-DD") bounding the search.
        venue: "home", "away" or "either" (relative to ``team``).
        limit: Maximum matches to display.
    """
    matches = KG.find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        start_date=parse_date(start_date) if start_date else None,
        end_date=parse_date(end_date) if end_date else None,
        venue=venue,
        limit=None,
    )
    header = "Matches found:" if matches else ""
    return fmt.format_matches(matches, limit=limit, header=header)


@mcp.tool()
def head_to_head(team1: str, team2: str) -> str:
    """Head-to-head record and match list between two teams (all competitions)."""
    return fmt.format_head_to_head(KG.head_to_head(team1, team2))


# ----------------------------------------------------------------------------
# Team tools
# ----------------------------------------------------------------------------
@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "either",
) -> str:
    """Win/draw/loss record, goals and win-rate for a team, optionally scoped
    to a season, competition and/or home/away venue."""
    return fmt.format_team_record(
        KG.team_record(team, season=season, competition=competition, venue=venue)
    )


@mcp.tool()
def team_competitions(team: str) -> str:
    """List the competitions a team has appeared in, with match counts."""
    data = KG.team_competitions(team)
    if not data["competitions"]:
        return f"No matches found for {data['team']}."
    lines = [f"{data['team']} has appeared in:"]
    for comp, n in data["competitions"].items():
        lines.append(f"- {comp}: {n} matches")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Player tools
# ----------------------------------------------------------------------------
@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    sort_by: str = "overall",
    limit: int = 25,
) -> str:
    """Search the FIFA player database by name, nationality, club, position
    and/or minimum overall rating. Sort by overall|potential|age|name."""
    players = KG.find_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, sort_by=sort_by, limit=limit,
    )
    return fmt.format_players(players, header="Players found:")


@mcp.tool()
def top_brazilian_players(limit: int = 10) -> str:
    """Return the highest-rated Brazilian players in the dataset."""
    players = KG.top_brazilian_players(limit=limit)
    return fmt.format_players(players, header="Top-rated Brazilian players in dataset:")


@mcp.tool()
def brazilian_players_by_club(limit_clubs: int = 10) -> str:
    """Group Brazilian players by club with counts and average ratings."""
    rows = KG.brazilian_players_by_club(limit_clubs=limit_clubs)
    return fmt.format_players_by_club(rows, header="Brazilian players by club:")


# ----------------------------------------------------------------------------
# Competition tools
# ----------------------------------------------------------------------------
@mcp.tool()
def league_standings(competition: str, season: int) -> str:
    """Compute a league table for a competition + season from match results
    (3 points for a win, 1 for a draw)."""
    rows = KG.standings(competition, season)
    return fmt.format_standings(rows, competition, season)


@mcp.tool()
def list_seasons(competition: Optional[str] = None) -> str:
    """List the seasons available in the dataset (optionally per competition)."""
    seasons = KG.list_seasons(competition)
    label = competition or "all competitions"
    if not seasons:
        return f"No seasons found for {label}."
    return f"Seasons available for {label}: " + ", ".join(str(s) for s in seasons)


# ----------------------------------------------------------------------------
# Statistics tools
# ----------------------------------------------------------------------------
@mcp.tool()
def average_goals(competition: Optional[str] = None, season: Optional[int] = None) -> str:
    """Average goals per match plus home/draw/away outcome rates, optionally
    scoped to a competition and/or season."""
    return fmt.format_average_goals(KG.average_goals(competition=competition, season=season))


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """List the matches with the largest goal margins."""
    matches = KG.biggest_wins(competition=competition, season=season, limit=limit)
    return fmt.format_matches(matches, limit=limit, header="Biggest victories in dataset:")


@mcp.tool()
def best_team_records(
    venue: str = "home",
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 5,
    metric: str = "win_rate",
    limit: int = 10,
) -> str:
    """Rank teams by home/away/overall win-rate (or points)."""
    rows = KG.best_team_record(
        venue=venue, competition=competition, season=season,
        min_matches=min_matches, metric=metric, limit=limit,
    )
    return fmt.format_best_records(rows, header=f"Best {venue} records (min {min_matches} matches):")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
