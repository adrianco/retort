"""
Context
=======
Module: bsoccer.server
Purpose: The MCP (Model Context Protocol) server. Exposes the Brazilian soccer
         query engine (bsoccer.queries) as MCP tools so an LLM client can answer
         natural-language questions about players, teams, matches and
         competitions over the provided Kaggle datasets.

Transport: stdio (the standard MCP transport for local servers). Run with:
    python -m bsoccer.server
or via the console entry point:
    brazilian-soccer-mcp

Each tool returns a JSON object with two keys:
    "text"  - a concise human-readable answer (bsoccer.format)
    "data"  - the structured result for programmatic use
This dual shape lets the connected LLM either quote the prose directly or reason
over the structured fields.

The query engine and data are loaded lazily on first tool call so server
start-up is instant and a missing-data error surfaces as a tool error rather
than a crash at import time.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import format as fmt
from .data import get_data
from .queries import QueryEngine

mcp = FastMCP("brazilian-soccer")

_ENGINE: QueryEngine | None = None


def engine() -> QueryEngine:
    """Lazily construct (and cache) the query engine."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = QueryEngine(get_data())
    return _ENGINE


def _wrap(text: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"text": text, "data": data}


# --------------------------------------------------------------------------- #
# Match tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    side: str = "either",
    limit: int = 50,
) -> dict[str, Any]:
    """Find soccer matches by team, opponent, competition, season or date range.

    Args:
        team: Team name (any spelling, e.g. "Flamengo", "Palmeiras-SP").
        opponent: Restrict to matches against this second team.
        competition: "Brasileirão", "Copa do Brasil", "Copa Libertadores", etc.
        season: Year of the season (e.g. 2019).
        date_from: ISO date lower bound (YYYY-MM-DD).
        date_to: ISO date upper bound (YYYY-MM-DD).
        side: "home", "away" or "either" (default) for the `team` filter.
        limit: Max matches to return.
    """
    res = engine().find_matches(team, opponent, competition, season,
                                date_from, date_to, side, limit)
    return _wrap(fmt.format_matches(res), res)


# --------------------------------------------------------------------------- #
# Team tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def team_record(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "all",
) -> dict[str, Any]:
    """Get a team's win/draw/loss and goals record.

    Args:
        team: Team name.
        competition: Optional competition filter.
        season: Optional season year filter.
        venue: "all", "home" or "away".
    """
    res = engine().team_record(team, competition, season, venue)
    return _wrap(fmt.format_record(res), res)


@mcp.tool()
def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Compare two teams head-to-head: wins, draws, goals and recent meetings."""
    res = engine().head_to_head(team_a, team_b, competition, limit)
    return _wrap(fmt.format_head_to_head(res), res)


# --------------------------------------------------------------------------- #
# Player tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    sort_by: str = "Overall",
    limit: int = 25,
) -> dict[str, Any]:
    """Search the FIFA player database.

    Args:
        name: Substring of the player's name.
        nationality: e.g. "Brazil".
        club: Club name (any spelling).
        position: One or more positions, comma-separated (e.g. "ST,CF").
        min_overall: Minimum FIFA overall rating.
        sort_by: Column to sort by descending (default "Overall").
        limit: Max players to return.
    """
    res = engine().search_players(name, nationality, club, position,
                                  min_overall, sort_by, limit)
    return _wrap(fmt.format_players(res), res)


@mcp.tool()
def players_by_club(nationality: str = "Brazil", top: int = 10) -> dict[str, Any]:
    """Summarize players of a nationality grouped by club (count + avg rating)."""
    res = engine().players_by_club_summary(nationality, top)
    return _wrap(fmt.format_club_summary(res), res)


# --------------------------------------------------------------------------- #
# Competition tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def standings(
    competition: str = "Brasileirão",
    season: int | None = None,
    top: int | None = None,
) -> dict[str, Any]:
    """Compute a league table from match results (3 pts win, 1 pt draw)."""
    res = engine().standings(competition, season, top)
    return _wrap(fmt.format_standings(res), res)


@mcp.tool()
def champion(competition: str = "Brasileirão", season: int | None = None) -> dict[str, Any]:
    """Return the season champion (top of the calculated standings)."""
    res = engine().champion(competition, season)
    return _wrap(fmt.format_champion(res), res)


@mcp.tool()
def list_seasons(competition: str | None = None) -> dict[str, Any]:
    """List available competitions and seasons in the data."""
    res = engine().seasons_available(competition)
    comps = ", ".join(res["competitions"])
    seasons = ", ".join(str(s) for s in res["seasons"])
    text = f"Competitions: {comps}\nSeasons: {seasons or 'n/a'}"
    return _wrap(text, res)


# --------------------------------------------------------------------------- #
# Statistics tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def competition_stats(
    competition: str | None = None, season: int | None = None
) -> dict[str, Any]:
    """Aggregate goal and home-advantage statistics for a competition/season."""
    res = engine().competition_stats(competition, season)
    return _wrap(fmt.format_competition_stats(res), res)


@mcp.tool()
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """List matches with the largest goal margins."""
    res = engine().biggest_wins(competition, season, limit)
    return _wrap(fmt.format_biggest_wins(res), res)


@mcp.tool()
def top_scoring_teams(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Rank teams by total goals scored in a competition/season."""
    res = engine().top_scoring_teams(competition, season, limit)
    rows = res.get("teams", [])
    text = "Top scoring teams:\n" + "\n".join(
        f"{i}. {t['team']}: {t['goals_for']} goals in {t['matches']} matches"
        for i, t in enumerate(rows, 1)
    )
    return _wrap(text, res)


def main() -> None:
    """Console entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
