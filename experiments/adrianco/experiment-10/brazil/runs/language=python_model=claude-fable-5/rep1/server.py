"""Brazilian Soccer MCP Server.

Exposes the Kaggle Brazilian soccer datasets (matches 2003-2023 and FIFA
player data) as MCP tools so an LLM can answer natural language questions
about players, teams, matches, and competitions.

Run over stdio:
    python server.py
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

import queries
from queries import TeamNotFoundError
from soccer_data import get_database

mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Knowledge base of Brazilian soccer: Brasileirão Série A/B/C "
        "(2003-2023), Copa do Brasil, Copa Libertadores match results, and "
        "FIFA player ratings. Team names may be given with or without state "
        "suffixes (e.g. 'Flamengo' or 'Flamengo-RJ'); accents are optional. "
        "Competition filters accept: serie-a, serie-b, serie-c, "
        "copa-do-brasil, libertadores (or common names like 'Brasileirão')."
    ),
)


def _safe(fn, *args, **kwargs) -> dict:
    try:
        return fn(*args, **kwargs)
    except TeamNotFoundError as exc:
        return {"error": str(exc)}


@mcp.tool()
def search_matches(team: Optional[str] = None, opponent: Optional[str] = None,
                   competition: Optional[str] = None, season: Optional[int] = None,
                   date_from: Optional[str] = None, date_to: Optional[str] = None,
                   limit: int = 25) -> dict:
    """Search matches by team, opponent, competition, season, or date range.

    Args:
        team: Team name (any side). E.g. "Flamengo", "São Paulo", "Palmeiras-SP".
        opponent: Second team to require in the match (for fixtures between two teams).
        competition: serie-a | serie-b | serie-c | copa-do-brasil | libertadores
            (common names like "Brasileirão" or "Copa Libertadores" also work).
        season: Season year, e.g. 2019.
        date_from: Earliest date, YYYY-MM-DD.
        date_to: Latest date, YYYY-MM-DD.
        limit: Maximum matches to return (most recent first).
    """
    return _safe(queries.search_matches, team=team, opponent=opponent,
                 competition=competition, season=season,
                 date_from=date_from, date_to=date_to, limit=limit)


@mcp.tool()
def get_head_to_head(team1: str, team2: str, competition: Optional[str] = None) -> dict:
    """All matches between two teams plus aggregate wins/draws and goals.

    Use for derby questions ("Fla-Flu", "Palmeiras vs Santos") and
    head-to-head comparisons.
    """
    return _safe(queries.head_to_head, team1, team2, competition)


@mcp.tool()
def get_team_stats(team: str, season: Optional[int] = None,
                   competition: Optional[str] = None, venue: str = "all") -> dict:
    """Win/draw/loss record, goals for/against, and win rate for a team.

    Args:
        team: Team name.
        season: Optional season year filter.
        competition: Optional competition filter (serie-a, copa-do-brasil, ...).
        venue: "all", "home", or "away" — e.g. venue="home" for home record.
    """
    return _safe(queries.team_stats, team, season, competition, venue)


@mcp.tool()
def get_team_competitions(team: str) -> dict:
    """List the competitions and seasons in which a team appears in the datasets."""
    return _safe(queries.team_competitions, team)


@mcp.tool()
def get_standings(season: int, competition: str = "serie-a") -> dict:
    """League table for a season calculated from match results (3 pts per win).

    Includes champion and relegated teams for complete Série A seasons.
    Best supported for serie-a (2003-2023); other competitions return a
    points table over the matches available.
    """
    return _safe(queries.standings, season, competition)


@mcp.tool()
def get_competition_stats(competition: Optional[str] = None,
                          season: Optional[int] = None) -> dict:
    """Aggregate statistics: average goals per match, home/away win rates, draws."""
    return _safe(queries.competition_stats, competition, season)


@mcp.tool()
def get_biggest_wins(competition: Optional[str] = None,
                     season: Optional[int] = None, limit: int = 10) -> dict:
    """Matches with the largest goal margins (biggest victories)."""
    return _safe(queries.biggest_wins, competition, season, limit)


@mcp.tool()
def get_best_records(season: Optional[int] = None, competition: str = "serie-a",
                     venue: str = "all", min_matches: int = 10,
                     limit: int = 10) -> dict:
    """Teams ranked by win rate. Use venue="home"/"away" for home/away records."""
    return _safe(queries.best_records, season, competition, venue, min_matches, limit)


@mcp.tool()
def search_players(name: Optional[str] = None, nationality: Optional[str] = None,
                   club: Optional[str] = None, position: Optional[str] = None,
                   min_overall: Optional[int] = None, limit: int = 20) -> dict:
    """Search the FIFA player database, sorted by overall rating.

    Args:
        name: Partial or full player name (accent-insensitive).
        nationality: e.g. "Brazil" for Brazilian players.
        club: Club name substring, e.g. "Real Madrid".
        position: Position code (ST, GK, CAM...) or group
            (forward, midfielder, defender, goalkeeper).
        min_overall: Minimum overall rating.
        limit: Maximum players to return.
    """
    return queries.search_players(name=name, nationality=nationality, club=club,
                                  position=position, min_overall=min_overall,
                                  limit=limit)


@mcp.tool()
def get_player(name: str) -> dict:
    """Detailed profile for one player, including skill ratings.

    Returns the best name match plus other candidate matches.
    """
    return queries.get_player(name)


@mcp.tool()
def get_top_players(nationality: Optional[str] = None, club: Optional[str] = None,
                    position: Optional[str] = None, limit: int = 10) -> dict:
    """Highest-rated players, optionally filtered by nationality, club, or position."""
    return queries.top_players(nationality=nationality, club=club,
                               position=position, limit=limit)


@mcp.tool()
def get_data_summary() -> dict:
    """Overview of the loaded datasets: competitions, season coverage, match and player counts."""
    db = get_database()
    return {
        "total_matches": len(db.matches),
        "total_players": len(db.players),
        "competitions": queries.competition_seasons(),
        "sources": {name: len(rows) for name, rows in db.matches_by_source.items()},
        "notes": (
            "Matches duplicated across source files are de-duplicated. "
            "Player data is the FIFA 19 database; most Brazilian-league club "
            "rosters are not included, but 800+ Brazilian players at clubs "
            "worldwide are."
        ),
    }


if __name__ == "__main__":
    get_database()  # load data eagerly at startup
    mcp.run()
