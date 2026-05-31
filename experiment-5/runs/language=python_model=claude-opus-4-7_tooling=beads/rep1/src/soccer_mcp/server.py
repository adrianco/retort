"""MCP server exposing Brazilian soccer queries.

This module wires the pure-Python query layer in :mod:`soccer_mcp.queries`
into an MCP server using the official FastMCP helper. Each capability area
from ``TASK.md`` is mapped to one or more MCP tools, with one helper resource
(``soccer://overview``) describing the loaded corpus.

Running this module starts a stdio MCP server suitable for integration with
any MCP-aware LLM client:

    $ python -m soccer_mcp.server

Tools exposed
-------------
* ``find_matches`` – flexible match search.
* ``head_to_head`` – pairwise team history.
* ``team_record`` – W/D/L + goals for one team (optionally by venue).
* ``compare_teams`` – side-by-side team comparison with head-to-head.
* ``find_players`` – FIFA player search.
* ``top_brazilian_players`` – highest-rated Brazilian players.
* ``players_by_club`` – squad listing for a club.
* ``competition_standings`` – season standings table.
* ``competition_summary`` – champion + top-3 summary.
* ``overall_statistics`` – dataset description.
* ``average_goals_per_match`` – aggregate goal/result rates.
* ``biggest_wins`` – largest winning margins.
* ``best_home_record`` / ``best_away_record`` – venue leaderboards.
* ``list_competitions`` / ``list_seasons`` – metadata helpers.

All tools accept and return JSON serialisable values.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from soccer_mcp import queries as q
from soccer_mcp.data_loader import (
    BRASILEIRAO,
    DataStore,
    load_default_store,
)

# ---------------------------------------------------------------------------
# Singleton data store – avoids re-reading CSVs on every tool call.
# ---------------------------------------------------------------------------

_STORE: DataStore | None = None


def get_store() -> DataStore:
    global _STORE
    if _STORE is None:
        base = os.environ.get("SOCCER_DATA_DIR")
        _STORE = load_default_store(base)
    return _STORE


def reset_store() -> None:
    """Drop the cached store (test helper)."""
    global _STORE
    _STORE = None


# ---------------------------------------------------------------------------
# FastMCP wiring
# ---------------------------------------------------------------------------
try:  # FastMCP is the high-level helper in the ``mcp`` SDK
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - mcp is a declared dep
    raise RuntimeError(
        "The 'mcp' package is required. Install with: pip install mcp"
    ) from exc


mcp = FastMCP("brazilian-soccer")


@mcp.tool()
def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    season: int | None = None,
    competition: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search matches across all loaded competitions."""
    return q.find_matches(
        get_store(),
        team=team,
        opponent=opponent,
        season=season,
        competition=competition,
        start_date=start_date,
        end_date=end_date,
        home_only=home_only,
        away_only=away_only,
        limit=limit,
    )


@mcp.tool()
def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Aggregated record and recent matches between two clubs."""
    return q.head_to_head(
        get_store(), team_a, team_b,
        competition=competition, season=season, limit=limit,
    )


@mcp.tool()
def team_record(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
) -> dict[str, Any]:
    """Wins/draws/losses and goals for a single team."""
    return q.team_record(
        get_store(), team,
        season=season, competition=competition, venue=venue,
    )


@mcp.tool()
def compare_teams(
    team_a: str,
    team_b: str,
    season: int | None = None,
    competition: str | None = None,
) -> dict[str, Any]:
    """Side-by-side comparison + head-to-head for two teams."""
    return q.compare_teams(
        get_store(), team_a, team_b,
        season=season, competition=competition,
    )


@mcp.tool()
def find_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Search FIFA player data."""
    return q.find_players(
        get_store(),
        name=name, nationality=nationality, club=club,
        position=position, min_overall=min_overall, limit=limit,
    )


@mcp.tool()
def top_brazilian_players(limit: int = 10) -> list[dict[str, Any]]:
    """Highest-rated Brazilian players in the FIFA dataset."""
    return q.top_brazilian_players(get_store(), limit=limit)


@mcp.tool()
def players_by_club(club: str, limit: int = 50) -> dict[str, Any]:
    """All FIFA players currently listed for a given club."""
    return q.players_by_club(get_store(), club, limit=limit)


@mcp.tool()
def competition_standings(
    season: int,
    competition: str = BRASILEIRAO,
) -> list[dict[str, Any]]:
    """Final standings for a (competition, season) pair."""
    return q.competition_standings(get_store(), season, competition=competition)


@mcp.tool()
def competition_summary(
    season: int,
    competition: str = BRASILEIRAO,
) -> dict[str, Any]:
    """Champion / top-3 summary for a (competition, season) pair."""
    return q.competition_summary(get_store(), season, competition=competition)


@mcp.tool()
def overall_statistics() -> dict[str, Any]:
    """Top-line description of the loaded corpus."""
    return q.overall_statistics(get_store())


@mcp.tool()
def average_goals_per_match(
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Mean goals/match plus home/away/draw rate."""
    return q.average_goals_per_match(
        get_store(), competition=competition, season=season,
    )


@mcp.tool()
def biggest_wins(
    limit: int = 10,
    competition: str | None = None,
    season: int | None = None,
) -> list[dict[str, Any]]:
    """Matches with the largest goal-difference margin."""
    return q.biggest_wins(
        get_store(), limit=limit, competition=competition, season=season,
    )


@mcp.tool()
def best_home_record(
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 5,
) -> list[dict[str, Any]]:
    """Teams sorted by home win-rate (with a minimum match threshold)."""
    return q.best_home_record(
        get_store(),
        competition=competition, season=season, min_matches=min_matches,
    )


@mcp.tool()
def best_away_record(
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 5,
) -> list[dict[str, Any]]:
    """Teams sorted by away win-rate (with a minimum match threshold)."""
    return q.best_away_record(
        get_store(),
        competition=competition, season=season, min_matches=min_matches,
    )


@mcp.tool()
def list_competitions() -> list[str]:
    """Return every competition label present in the corpus."""
    return q.list_competitions(get_store())


@mcp.tool()
def list_seasons(competition: str | None = None) -> list[int]:
    """Return every season present in the corpus (optionally filtered)."""
    return q.list_seasons(get_store(), competition=competition)


@mcp.resource("soccer://overview")
def overview_resource() -> str:
    """A short JSON description of the loaded corpus."""
    return json.dumps(q.overall_statistics(get_store()), indent=2, default=str)


def main() -> None:
    """Run the MCP server over stdio."""
    # Pre-load the store so the very first tool call doesn't pay the parse cost.
    get_store()
    mcp.run()


if __name__ == "__main__":  # pragma: no cover - exec entrypoint
    main()
