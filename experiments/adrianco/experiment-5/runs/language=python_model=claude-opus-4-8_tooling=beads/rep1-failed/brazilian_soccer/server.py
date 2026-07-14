"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Module    : brazilian_soccer.server
Purpose   : The MCP (Model Context Protocol) server. Exposes the query layer as
            MCP tools so an LLM can answer natural-language questions about
            Brazilian soccer (matches, teams, players, competitions, stats).

Built on FastMCP (mcp >= 1.x). Each tool is a thin wrapper around a function in
brazilian_soccer.queries.*, operating on the shared, lazily-loaded
KnowledgeGraph (get_default_graph). Tools return JSON-serialisable dicts/lists.

Run:
    python -m brazilian_soccer.server          # stdio transport (default)
    python run_server.py                       # convenience entry point

Tools exposed:
    find_matches, head_to_head, last_match,
    team_record, team_competitions,
    search_players, player_info, top_players, brazilian_players_by_club,
    standings, champion, relegated,
    competition_summary, biggest_wins, best_records,
    dataset_summary
================================================================================
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from .knowledge_graph import get_default_graph
from .queries import competitions as q_comp
from .queries import matches as q_matches
from .queries import players as q_players
from .queries import stats as q_stats
from .queries import teams as q_teams

mcp = FastMCP("brazilian-soccer")


# --------------------------------------------------------------------------- #
# Match tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    home_only: bool = False,
    away_only: bool = False,
    limit: int = 50,
) -> list:
    """Find matches by team, opponent, competition, season or date range.

    Team names are fuzzy-matched (state suffixes and accents are ignored).
    Returns the most recent matches first. Use home_only/away_only to restrict
    the role of `team`. Competitions: Brasileirao, Copa do Brasil, Libertadores,
    Serie B, Serie C.
    """
    return q_matches.find_matches(
        get_default_graph(),
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        home_only=home_only,
        away_only=away_only,
        limit=limit,
    )


@mcp.tool()
def head_to_head(team_a: str, team_b: str, competition: Optional[str] = None) -> dict:
    """Head-to-head record between two teams: wins, draws, goals and match list."""
    return q_matches.head_to_head(get_default_graph(), team_a, team_b, competition)


@mcp.tool()
def last_match(team_a: str, team_b: str) -> Optional[dict]:
    """Most recent match played between two teams (or null if they never met)."""
    return q_matches.last_match(get_default_graph(), team_a, team_b)


# --------------------------------------------------------------------------- #
# Team tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> dict:
    """Win/draw/loss and goal record for a team.

    Optionally filter by season, competition, and venue ("all", "home", "away").
    Returns points (3/win, 1/draw), goal difference and win rate.
    """
    return q_teams.team_record(
        get_default_graph(), team, season=season, competition=competition, venue=venue
    )


@mcp.tool()
def team_competitions(team: str) -> dict:
    """List the competitions a team appears in, with match counts and seasons."""
    return q_teams.team_competitions(get_default_graph(), team)


# --------------------------------------------------------------------------- #
# Player tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    sort_by: str = "overall",
    limit: int = 25,
) -> list:
    """Search the FIFA player database.

    Filter by name substring, nationality (e.g. "Brazil"), club, position (e.g.
    "ST", "GK") and minimum overall rating. sort_by: overall|potential|age|name.
    """
    return q_players.search_players(
        get_default_graph(),
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        sort_by=sort_by,
        limit=limit,
    )


@mcp.tool()
def player_info(name: str) -> Optional[dict]:
    """Look up a single player by (partial) name; returns the best-rated match."""
    return q_players.player_by_name(get_default_graph(), name)


@mcp.tool()
def top_players(
    nationality: Optional[str] = None, club: Optional[str] = None, limit: int = 10
) -> list:
    """Highest-rated players overall, or within a nationality/club."""
    return q_players.top_players(
        get_default_graph(), nationality=nationality, club=club, limit=limit
    )


@mcp.tool()
def brazilian_players_by_club(limit: int = 20) -> list:
    """Brazilian players grouped by club, with counts and average ratings."""
    return q_players.brazilians_by_club(get_default_graph(), limit=limit)


# --------------------------------------------------------------------------- #
# Competition tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def standings(competition: str = "Brasileirao", season: Optional[int] = None) -> list:
    """League standings calculated from match results (3 pts win / 1 draw).

    Sorted by points, then goal difference, then goals for. Most meaningful for
    round-robin leagues (Brasileirao).
    """
    return q_comp.standings(get_default_graph(), competition, season)


@mcp.tool()
def champion(competition: str = "Brasileirao", season: Optional[int] = None) -> Optional[dict]:
    """The top team of the computed standings for a competition/season."""
    return q_comp.champion(get_default_graph(), competition, season)


@mcp.tool()
def relegated(season: int, competition: str = "Brasileirao", count: int = 4) -> list:
    """The bottom `count` teams of a season's computed standings."""
    return q_comp.relegated(get_default_graph(), season, competition, count)


# --------------------------------------------------------------------------- #
# Statistics tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def competition_summary(
    competition: Optional[str] = None, season: Optional[int] = None
) -> dict:
    """Aggregate stats: average goals per match, home/away/draw rates, totals."""
    return q_stats.competition_summary(get_default_graph(), competition, season)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
) -> list:
    """Matches with the largest goal margin (optionally filtered)."""
    return q_stats.biggest_wins(get_default_graph(), competition, season, limit)


@mcp.tool()
def best_records(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: str = "all",
    min_matches: int = 5,
    limit: int = 10,
) -> list:
    """Teams ranked by win rate (with a minimum games threshold).

    venue: "all", "home" or "away" — e.g. for "best home/away record" questions.
    """
    return q_stats.best_records(
        get_default_graph(), competition, season, venue, min_matches, limit
    )


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #
@mcp.tool()
def dataset_summary() -> dict:
    """Summary of the loaded data: match/player counts, competitions, seasons."""
    return get_default_graph().stats()


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
