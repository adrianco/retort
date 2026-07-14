"""
=============================================================================
 Brazilian Soccer MCP Server -- MCP entry point
=============================================================================
 Purpose
 -------
 Exposes the Brazilian soccer knowledge graph (`soccer_queries.py`) over the
 Model Context Protocol so that an LLM can answer natural-language questions
 about players, teams, matches and competitions.

 Transport: stdio (the standard MCP transport). Run with:

     python server.py            # starts the stdio MCP server
     python server.py --selftest # loads data, prints a summary, exits

 Tools exposed (thin wrappers around SoccerQueryEngine):
   find_matches, last_match, head_to_head,
   team_record, compare_teams,
   search_players, players_by_club, players_by_nationality, top_players,
   standings, list_competitions, list_seasons,
   competition_stats, biggest_wins, best_record,
   database_summary

 Implementation notes
 --------------------
 * Built on the official `mcp` Python SDK's FastMCP helper.
 * The query engine is loaded once at import time (module-level singleton in
   soccer_data) so every tool call is fast (simple lookups < 2s, aggregates
   < 5s per the spec).
 * Every tool returns JSON-serializable dicts/lists.
=============================================================================
"""

from __future__ import annotations

import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from soccer_queries import SoccerQueryEngine

mcp = FastMCP("brazilian-soccer")

# Single shared engine (loads all CSVs once).
engine = SoccerQueryEngine()


# --------------------------------------------------------------------------
# 1. Match queries
# --------------------------------------------------------------------------


@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    season_from: Optional[int] = None,
    season_to: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """Find matches by team, opponent, competition, season or date range.

    `team` matches home OR away. Combine `team` + `opponent` to get every
    meeting between two clubs. Competitions: "Brasileirão", "Copa do Brasil",
    "Libertadores". Dates use ISO format (YYYY-MM-DD).
    """
    return engine.find_matches(
        team=team, opponent=opponent, home_team=home_team, away_team=away_team,
        competition=competition, season=season, season_from=season_from,
        season_to=season_to, date_from=date_from, date_to=date_to, limit=limit,
    )


@mcp.tool()
def last_match(team_a: str, team_b: str) -> dict:
    """Return the most recent match played between two teams."""
    return engine.last_match(team_a, team_b)


@mcp.tool()
def head_to_head(team_a: str, team_b: str, competition: Optional[str] = None) -> dict:
    """Full head-to-head record (wins/draws/goals) and match list."""
    return engine.head_to_head(team_a, team_b, competition=competition)


# --------------------------------------------------------------------------
# 2. Team queries
# --------------------------------------------------------------------------


@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> dict:
    """Win/draw/loss record and goals for/against for a team.

    `venue` is "all", "home" or "away". Computed from match results.
    """
    return engine.team_record(team, season=season, competition=competition, venue=venue)


@mcp.tool()
def compare_teams(team_a: str, team_b: str, season: Optional[int] = None) -> dict:
    """Compare two teams' records side by side plus their head-to-head."""
    return engine.compare_teams(team_a, team_b, season=season)


# --------------------------------------------------------------------------
# 3. Player queries
# --------------------------------------------------------------------------


@mcp.tool()
def search_players(name: str, limit: int = 25) -> dict:
    """Search FIFA players by (partial) name."""
    return engine.search_players(name, limit=limit)


@mcp.tool()
def players_by_club(club: str, position: Optional[str] = None, limit: int = 25) -> dict:
    """List FIFA players at a club, optionally filtered by position."""
    return engine.players_by_club(club, position=position, limit=limit)


@mcp.tool()
def players_by_nationality(nationality: str = "Brazil", limit: int = 25) -> dict:
    """List FIFA players by nationality (defaults to Brazil)."""
    return engine.players_by_nationality(nationality, limit=limit)


@mcp.tool()
def top_players(
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Highest-rated players, optionally filtered by nationality/club/position."""
    return engine.top_players(
        nationality=nationality, club=club, position=position, limit=limit
    )


# --------------------------------------------------------------------------
# 4. Competition queries
# --------------------------------------------------------------------------


@mcp.tool()
def standings(season: int, competition: str = "Brasileirão Série A") -> dict:
    """League table for a season, computed from match results."""
    return engine.standings(season, competition=competition)


@mcp.tool()
def list_competitions() -> dict:
    """List all competitions available in the data."""
    return engine.list_competitions()


@mcp.tool()
def list_seasons(competition: Optional[str] = None) -> dict:
    """List all seasons available, optionally filtered by competition."""
    return engine.list_seasons(competition=competition)


# --------------------------------------------------------------------------
# 5. Statistical analysis
# --------------------------------------------------------------------------


@mcp.tool()
def competition_stats(
    competition: Optional[str] = None, season: Optional[int] = None
) -> dict:
    """Aggregate stats: average goals/match, home & away win rates, draws."""
    return engine.competition_stats(competition=competition, season=season)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    team: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Matches with the largest goal margins."""
    return engine.biggest_wins(
        competition=competition, season=season, team=team, limit=limit
    )


@mcp.tool()
def best_record(
    venue: str = "home",
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_games: int = 5,
    metric: str = "win_rate",
    limit: int = 10,
) -> dict:
    """Rank teams by home/away/overall record (win_rate or points)."""
    return engine.best_record(
        venue=venue, competition=competition, season=season,
        min_games=min_games, metric=metric, limit=limit,
    )


@mcp.tool()
def database_summary() -> dict:
    """Overview of the loaded data (counts, competitions, season range)."""
    return engine.database_summary()


def _selftest() -> None:
    s = engine.database_summary()
    print("Brazilian Soccer MCP server -- data loaded:")
    print(f"  matches      : {s['total_matches']}")
    print(f"  players      : {s['total_players']}")
    print(f"  competitions : {', '.join(s['competitions'])}")
    print(f"  seasons      : {s['season_range']}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        mcp.run()
