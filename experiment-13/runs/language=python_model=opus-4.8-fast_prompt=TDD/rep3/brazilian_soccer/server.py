"""
Brazilian Soccer MCP server.

Context
-------
Exposes the :class:`SoccerKB` query/analytics capabilities (TASK.md) as MCP
tools over stdio using FastMCP. The knowledge base is loaded once from the
CSV datasets at start-up and shared by all tools. Each tool is a thin wrapper
that delegates to a formatter in :mod:`brazilian_soccer.service`, so the heavy
lifting stays unit-tested and MCP-agnostic.

Run with::

    python -m brazilian_soccer.server          # stdio MCP server

The data directory defaults to ``data/kaggle`` and can be overridden with the
``BRAZILIAN_SOCCER_DATA_DIR`` environment variable.
"""
from __future__ import annotations

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import service as svc
from .knowledge_base import SoccerKB

DEFAULT_DATA_DIR = os.environ.get("BRAZILIAN_SOCCER_DATA_DIR", "data/kaggle")

INSTRUCTIONS = (
    "Knowledge graph over Brazilian soccer data (Brasileirão Série A/B/C, "
    "Copa do Brasil, Copa Libertadores matches and FIFA player attributes). "
    "Use the tools to look up matches, head-to-head records, team records, "
    "league standings computed from results, players, and aggregate statistics."
)


def build_server(kb: Optional[SoccerKB] = None,
                 data_dir: Optional[str] = None) -> FastMCP:
    """Create a configured FastMCP server.

    Provide *kb* directly (e.g. in tests) or a *data_dir* to load from. When
    neither is given, the default data directory is used.
    """
    if kb is None:
        kb = SoccerKB.from_data_dir(data_dir or DEFAULT_DATA_DIR)

    mcp = FastMCP("brazilian-soccer", instructions=INSTRUCTIONS)

    @mcp.tool()
    def find_matches(team: Optional[str] = None, opponent: Optional[str] = None,
                     competition: Optional[str] = None,
                     season: Optional[int] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     venue: str = "any", limit: int = svc.DEFAULT_LIMIT) -> str:
        """Find matches by team, opponent, competition, season, date range or
        venue ("home"/"away"/"any"). Returns a formatted list of results."""
        return svc.answer_find_matches(
            kb, team=team, opponent=opponent, competition=competition,
            season=season, start_date=start_date, end_date=end_date,
            venue=venue, limit=limit)

    @mcp.tool()
    def head_to_head(team1: str, team2: str,
                     competition: Optional[str] = None,
                     season: Optional[int] = None) -> str:
        """Head-to-head record (wins/draws/goals) between two teams,
        optionally scoped to a competition and/or season."""
        return svc.answer_head_to_head(kb, team1, team2,
                                       competition=competition, season=season)

    @mcp.tool()
    def team_record(team: str, competition: Optional[str] = None,
                    season: Optional[int] = None, venue: str = "any") -> str:
        """A team's W/D/L record, goals and win rate, optionally scoped by
        competition, season and venue ("home"/"away"/"any")."""
        return svc.answer_team_record(kb, team, competition=competition,
                                      season=season, venue=venue)

    @mcp.tool()
    def standings(competition: str, season: int) -> str:
        """League table for a competition and season, computed from match
        results (points, W/D/L, goals for/against, goal difference)."""
        return svc.answer_standings(kb, competition=competition, season=season)

    @mcp.tool()
    def search_players(name: Optional[str] = None,
                       nationality: Optional[str] = None,
                       club: Optional[str] = None,
                       position: Optional[str] = None,
                       min_overall: Optional[int] = None,
                       limit: int = svc.DEFAULT_LIMIT) -> str:
        """Search FIFA players by name, nationality, club, position and/or a
        minimum overall rating. Results are sorted by overall rating."""
        return svc.answer_search_players(
            kb, name=name, nationality=nationality, club=club,
            position=position, min_overall=min_overall, limit=limit)

    @mcp.tool()
    def competition_stats(competition: Optional[str] = None,
                          season: Optional[int] = None) -> str:
        """Aggregate statistics (matches, total/average goals, home/away/draw
        rates) for a competition and/or season."""
        return svc.answer_competition_stats(kb, competition=competition,
                                            season=season)

    @mcp.tool()
    def biggest_wins(competition: Optional[str] = None,
                     season: Optional[int] = None, limit: int = 10) -> str:
        """The matches with the largest goal margins, optionally scoped by
        competition and/or season."""
        return svc.answer_biggest_wins(kb, competition=competition,
                                       season=season, limit=limit)

    @mcp.tool()
    def list_competitions() -> str:
        """List the competitions available in the dataset."""
        return svc.answer_list_competitions(kb)

    @mcp.tool()
    def list_seasons(competition: Optional[str] = None) -> str:
        """List the seasons available, optionally for a single competition."""
        return svc.answer_list_seasons(kb, competition=competition)

    return mcp


def main() -> None:
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
