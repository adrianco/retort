"""
================================================================================
Module: server.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
-------
The MCP (Model Context Protocol) server that exposes the Brazilian soccer
knowledge graph to an LLM.  It is built on the official MCP Python SDK's
``FastMCP`` helper and communicates over stdio, so it can be wired into any MCP
client (Claude Desktop, etc.) via a config entry like::

    {
      "mcpServers": {
        "brazilian-soccer": {
          "command": "python",
          "args": ["/abs/path/to/server.py"]
        }
      }
    }

Each ``@mcp.tool()`` function is a natural-language-friendly capability that maps
onto one method of :class:`knowledge_graph.KnowledgeGraph`.  Tools return
human-readable, pre-formatted text (matching the answer formats in the spec) so
the LLM can relay results directly, while the underlying engine returns
structured data that is also available programmatically.

The heavy data load happens once, lazily, on first tool call (see
``get_graph``), keeping start-up cheap and tests fast.

Run directly for a stdio MCP server:   python server.py
Import ``mcp`` / ``get_graph`` for tests and embedding.
================================================================================
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

import formatting
from knowledge_graph import KnowledgeGraph

mcp = FastMCP("brazilian-soccer")

# Lazily-initialised singleton so importing this module is cheap and the CSVs
# are only parsed when a tool is actually invoked.
_GRAPH: Optional[KnowledgeGraph] = None


def get_graph() -> KnowledgeGraph:
    """Return the shared KnowledgeGraph, loading the datasets on first use."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = KnowledgeGraph()
    return _GRAPH


# ---------------------------------------------------------------------------- #
# Match tools
# ---------------------------------------------------------------------------- #
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Find matches by team, opponent, competition, season and/or date range.

    Examples: "Show me all Flamengo vs Fluminense matches",
    "What matches did Palmeiras play in 2021?".

    Args:
        team: A team that played (home or away). Name variations are handled.
        opponent: Restrict to matches against this opponent.
        competition: One of Brasileirão Série A, Série B, Série C, Copa do
            Brasil, Copa Libertadores (substring, accent-insensitive).
        season: Year of the season, e.g. 2019.
        start_date: Inclusive lower date bound, ISO ``YYYY-MM-DD``.
        end_date: Inclusive upper date bound, ISO ``YYYY-MM-DD``.
        limit: Maximum number of matches to return.
    """
    matches = get_graph().find_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        start_date=start_date, end_date=end_date, limit=limit,
    )
    return formatting.format_matches(matches, team=team, opponent=opponent)


@mcp.tool()
def head_to_head(
    team1: str,
    team2: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """Head-to-head record between two teams (wins, draws, goals, recent games).

    Example: "Compare Palmeiras and Santos head-to-head".
    """
    data = get_graph().head_to_head(team1, team2, competition=competition, season=season)
    return formatting.format_head_to_head(data)


# ---------------------------------------------------------------------------- #
# Team tools
# ---------------------------------------------------------------------------- #
@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> str:
    """Win/draw/loss and goal record for a team.

    Example: "What is Corinthians' home record in 2022?".

    Args:
        team: Team name (variations handled).
        season: Year to restrict to, optional.
        competition: Competition to restrict to, optional.
        venue: 'all', 'home', or 'away'.
    """
    rec = get_graph().team_record(team, season=season, competition=competition, venue=venue)
    return formatting.format_team_record(rec)


# ---------------------------------------------------------------------------- #
# Competition tools
# ---------------------------------------------------------------------------- #
@mcp.tool()
def standings(competition: str, season: int, top: int = 20) -> str:
    """League table for a competition/season, computed from match results.

    Example: "Who won the 2019 Brasileirão?", "Show the 2020 Série A standings".

    Args:
        competition: Competition label (e.g. "Série A", "Série B").
        season: Year, e.g. 2019.
        top: Number of rows to show (default full table of 20).
    """
    table = get_graph().standings(competition, season)
    return formatting.format_standings(table, competition, season, top=top)


@mcp.tool()
def top_scoring_teams(competition: str, season: int, limit: int = 5) -> str:
    """Teams that scored the most goals in a competition/season.

    Example: "Which team scored the most goals in Série A 2019?".
    """
    teams = get_graph().top_scoring_teams(competition, season, limit=limit)
    return formatting.format_top_scorers(teams, competition, season)


@mcp.tool()
def list_competitions() -> str:
    """List the competitions available in the dataset."""
    return "Available competitions:\n" + "\n".join(
        f"- {c}" for c in get_graph().list_competitions()
    )


@mcp.tool()
def list_seasons(competition: Optional[str] = None) -> str:
    """List the seasons (years) available, optionally for one competition."""
    seasons = get_graph().list_seasons(competition)
    label = competition or "all competitions"
    return f"Seasons available for {label}: " + ", ".join(str(s) for s in seasons)


@mcp.tool()
def list_teams(competition: Optional[str] = None, season: Optional[int] = None) -> str:
    """List the teams present, optionally filtered by competition and season."""
    teams = get_graph().list_teams(competition, season)
    return f"{len(teams)} teams found:\n" + "\n".join(f"- {t}" for t in teams)


# ---------------------------------------------------------------------------- #
# Statistics tools
# ---------------------------------------------------------------------------- #
@mcp.tool()
def average_goals(competition: Optional[str] = None, season: Optional[int] = None) -> str:
    """Average goals per match and home/draw/away win rates for a data slice.

    Example: "What's the average goals per match in the Brasileirão?".
    """
    stats = get_graph().average_goals(competition=competition, season=season)
    return formatting.format_average_goals(stats)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    team: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Matches with the largest goal margin (biggest victories).

    Example: "Show me the biggest wins in the dataset".
    """
    wins = get_graph().biggest_wins(competition=competition, season=season, team=team, limit=limit)
    return formatting.format_biggest_wins(wins)


# ---------------------------------------------------------------------------- #
# Player tools
# ---------------------------------------------------------------------------- #
@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 15,
) -> str:
    """Search the FIFA player database.

    Examples: "Find all Brazilian players", "Who are the highest-rated players
    at Grêmio?", "Show me forwards from Brazil rated 85+".

    Args:
        name: Substring of the player's name (accent-insensitive).
        nationality: Country, e.g. "Brazil".
        club: Club name (variations handled).
        position: FIFA position code, e.g. "GK", "ST", "CB".
        min_overall: Minimum FIFA Overall rating.
        limit: Maximum players to return (sorted by Overall).
    """
    players = get_graph().search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, limit=limit,
    )
    return formatting.format_players(players)


@mcp.tool()
def get_player(name: str) -> str:
    """Look up a single player by name (best-rated match).

    Example: "Who is Gabriel Barbosa?", "Tell me about Neymar".
    """
    player = get_graph().get_player(name)
    if player is None:
        return f"No player found matching '{name}'."
    return formatting.format_player_detail(player)


@mcp.tool()
def brazilian_players_by_club(limit: int = 20) -> str:
    """Summarise Brazilian players grouped by club (count + average rating).

    Example: "Which clubs have the most Brazilian players?".
    """
    rows = get_graph().brazilian_players_by_club(limit=limit)
    return formatting.format_players_by_club(rows)


if __name__ == "__main__":
    mcp.run()
