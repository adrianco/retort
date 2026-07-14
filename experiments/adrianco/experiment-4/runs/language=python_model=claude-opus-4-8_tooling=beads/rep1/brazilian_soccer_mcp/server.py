"""
================================================================================
Module: brazilian_soccer_mcp.server
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
  The MCP (Model Context Protocol) entry point. Wraps the pure-Python query
  engine (see queries.py) as MCP tools so an LLM client can answer natural
  language questions about Brazilian soccer by calling structured tools.

  Built on the FastMCP server from the official `mcp` SDK and served over
  stdio, which is the transport MCP desktop/CLI clients launch.

TOOLS EXPOSED (grouped by the spec's required capabilities)
  Match:        find_matches, head_to_head
  Team:         team_record, team_summary, compare_teams
  Player:       find_players, get_player, club_squad
  Competition:  standings, season_results, list_competitions
  Statistics:   competition_stats, biggest_wins, best_records, top_scoring_teams

  Each tool is a thin, well-documented adapter over the corresponding function
  in queries.py; the docstrings double as the tool descriptions the LLM sees.

RUN
  python -m brazilian_soccer_mcp.server      # stdio server
  (or)  bsoccer-mcp                            # console script, see setup.py
================================================================================
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import queries
from .data_loader import get_data

mcp = FastMCP("brazilian-soccer")


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    venue: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """Find matches by any combination of filters.

    Args:
        team: Team name (any spelling, e.g. "Flamengo", "Palmeiras-SP").
        competition: e.g. "Brasileirão", "Copa do Brasil", "Libertadores"
            (substring, case-insensitive).
        season: Year, e.g. 2019.
        date_from / date_to: ISO dates ("2019-01-01") bounding the range.
        venue: "home" or "away" to restrict to that side for `team`.
        limit: Max matches returned (most recent kept).
    """
    return queries.find_matches(
        team=team, competition=competition, season=season,
        date_from=date_from, date_to=date_to, venue=venue, limit=limit,
    )


@mcp.tool()
def head_to_head(
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 50,
) -> dict:
    """Head-to-head record and match list between two teams.

    Returns win/draw counts and goals for each side plus the matches.
    """
    return queries.head_to_head(
        team_a, team_b, competition=competition, season=season, limit=limit,
    )


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------
@mcp.tool()
def team_record(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: Optional[str] = None,
) -> dict:
    """Win/loss/draw record, goals and win rate for a team.

    Optionally scope by competition, season, and venue ("home"/"away").
    Example: team_record("Corinthians", competition="Brasileirão",
    season=2022, venue="home").
    """
    return queries.team_record(
        team, competition=competition, season=season, venue=venue,
    )


@mcp.tool()
def team_summary(team: str) -> dict:
    """Overall profile for a team: total record plus per-competition breakdown
    and the seasons it appears in."""
    return queries.team_summary(team)


@mcp.tool()
def compare_teams(
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict:
    """Compare two teams side-by-side (records) and their head-to-head."""
    return queries.compare_teams(
        team_a, team_b, competition=competition, season=season,
    )


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------
@mcp.tool()
def find_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    sort_by: str = "overall",
    limit: int = 25,
) -> dict:
    """Search FIFA players.

    Args:
        name: Substring of the player's name.
        nationality: e.g. "Brazil" (substring, case-insensitive).
        club: Club name (any spelling).
        position: Exact position code, e.g. "LW", "GK", "CB".
        min_overall: Minimum FIFA overall rating.
        sort_by: "overall" (default), "potential", "age", or "name".
        limit: Max players returned.
    """
    return queries.find_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, sort_by=sort_by, limit=limit,
    )


@mcp.tool()
def get_player(name: str) -> dict:
    """Look up a single player by name (best/highest-rated match) including a
    selection of skill attributes."""
    return queries.get_player(name)


@mcp.tool()
def club_squad(club: str, limit: int = 30) -> dict:
    """List the players registered at a club (FIFA data), ranked by rating,
    with the squad's average overall."""
    return queries.club_squad(club, limit=limit)


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------
@mcp.tool()
def standings(season: int, competition: str = "Brasileirão Série A") -> dict:
    """Compute the league table for a season from match results (3/1/0 points).
    Most meaningful for the Brasileirão. Returns ranked rows and the champion.
    """
    return queries.standings(season, competition=competition)


@mcp.tool()
def season_results(
    season: int, competition: Optional[str] = None, limit: int = 100
) -> dict:
    """All match results in a season, optionally for a single competition."""
    return queries.season_results(season, competition=competition, limit=limit)


@mcp.tool()
def list_competitions() -> dict:
    """List the available competitions and the seasons covered by the data."""
    return queries.list_competitions()


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------
@mcp.tool()
def competition_stats(
    competition: Optional[str] = None, season: Optional[int] = None
) -> dict:
    """Aggregate stats: matches, total/average goals per match, home/away win
    and draw rates. Filter by competition and/or season."""
    return queries.competition_stats(competition=competition, season=season)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
) -> dict:
    """The largest goal-margin victories matching the filters."""
    return queries.biggest_wins(
        competition=competition, season=season, limit=limit,
    )


@mcp.tool()
def best_records(
    venue: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 5,
    metric: str = "win_rate",
    limit: int = 10,
) -> dict:
    """Rank teams by a record metric.

    Args:
        venue: "home" or "away" to evaluate home-only/away-only records.
        metric: "win_rate" (default), "points", "wins", "goals_for",
            "goal_difference".
        min_matches: Minimum matches a team needs to be ranked.
    """
    return queries.best_records(
        venue=venue, competition=competition, season=season,
        min_matches=min_matches, metric=metric, limit=limit,
    )


@mcp.tool()
def top_scoring_teams(
    competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
) -> dict:
    """Teams ranked by total goals scored under the given filters."""
    return queries.top_scoring_teams(
        competition=competition, season=season, limit=limit,
    )


def main() -> None:
    """Console entry point: warm the data cache, then serve over stdio."""
    get_data()  # parse CSVs once up-front so first tool call is fast
    mcp.run()


if __name__ == "__main__":
    main()
