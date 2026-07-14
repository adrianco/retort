"""
================================================================================
Brazilian Soccer MCP Server :: server
================================================================================

Context
-------
Exposes the QueryEngine over the Model Context Protocol using FastMCP, so an LLM
client can call typed tools to answer natural-language questions about Brazilian
soccer. The knowledge graph is loaded once at process start (a few hundred ms)
and shared by all tool calls, keeping simple lookups well under the 2s budget.

Tools (grouped by the spec's five capability areas)
--------------------------------------------------
  Match:        find_matches, matches_between
  Team:         team_record, compare_teams
  Player:       search_players, players_by_nationality_clubs
  Competition:  standings, champion, relegated, list_competitions
  Statistics:   head_to_head, competition_stats, biggest_wins,
                best_record, top_scoring_teams

Each tool returns a JSON-serialisable dict (structured data) and, where the spec
shows an example answer, a "text" field with the human-readable rendering.

Run:  python -m brazilian_soccer.server        (stdio transport, for MCP clients)
================================================================================
"""

from __future__ import annotations

import os
from datetime import date
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .data_loader import parse_date
from .knowledge_graph import KnowledgeGraph
from .queries import (
    QueryEngine,
    format_matches,
    format_players,
    format_standings,
    format_team_record,
)

# --------------------------------------------------------------------------- #
# Engine bootstrap (lazy singleton so importing the module is cheap/testable)
# --------------------------------------------------------------------------- #

_engine: Optional[QueryEngine] = None


def get_engine() -> QueryEngine:
    global _engine
    if _engine is None:
        data_dir = os.environ.get("BR_SOCCER_DATA_DIR")
        graph = KnowledgeGraph.from_data_dir(data_dir)
        _engine = QueryEngine(graph)
    return _engine


def _pd(value: Optional[str]) -> Optional[date]:
    return parse_date(value) if value else None


mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Knowledge graph over Brazilian soccer datasets (Brasileirão, Copa do "
        "Brasil, Copa Libertadores matches and a FIFA player database). Use the "
        "tools to look up matches, team records, players, league standings and "
        "aggregated statistics. Team names may be given with or without a state "
        "suffix (e.g. 'Flamengo' or 'Flamengo-RJ')."
    ),
)


# ============================ MATCH TOOLS ================================== #
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    venue: str = "either",
    limit: int = 50,
) -> dict:
    """Find matches by team, opponent, competition, season and/or date range.

    venue: 'home', 'away' or 'either' (relative to `team`). Dates are ISO
    (YYYY-MM-DD). Returns structured matches plus a formatted 'text' summary."""
    result = get_engine().find_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        start_date=_pd(start_date), end_date=_pd(end_date), venue=venue,
        limit=limit,
    )
    result["text"] = format_matches(result)
    return result


@mcp.tool()
def matches_between(team_a: str, team_b: str, competition: Optional[str] = None) -> dict:
    """List every recorded match between two teams (the derby/clássico view)."""
    result = get_engine().head_to_head(team_a, team_b, competition=competition)
    return result


# ============================ TEAM TOOLS =================================== #
@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "either",
) -> dict:
    """Win/draw/loss record, goals for/against and win rate for a team,
    optionally scoped to a season, competition and/or home/away venue."""
    result = get_engine().team_record(team, season=season, competition=competition, venue=venue)
    result["text"] = format_team_record(result)
    return result


@mcp.tool()
def compare_teams(team_a: str, team_b: str, competition: Optional[str] = None) -> dict:
    """Compare two teams: each side's record plus their head-to-head."""
    return get_engine().compare_teams(team_a, team_b, competition=competition)


# ============================ PLAYER TOOLS ================================= #
@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    sort_by: str = "overall",
    limit: int = 25,
) -> dict:
    """Search the FIFA player database by name, nationality, club, position
    and/or minimum overall rating. sort_by: overall|potential|age|name."""
    result = get_engine().search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, sort_by=sort_by, limit=limit,
    )
    result["text"] = format_players(result)
    return result


@mcp.tool()
def players_by_nationality_clubs(nationality: str = "Brazil") -> dict:
    """Group players of a given nationality by club, with per-club averages."""
    return get_engine().players_at_brazilian_clubs(nationality=nationality)


# ========================= COMPETITION TOOLS ============================== #
@mcp.tool()
def standings(competition: str, season: int) -> dict:
    """Compute a league table from match results (3 pts win, 1 draw)."""
    result = get_engine().standings(competition, season)
    result["text"] = format_standings(result)
    return result


@mcp.tool()
def champion(competition: str, season: int) -> dict:
    """Return the calculated champion (table leader) for a competition/season."""
    return get_engine().champion(competition, season)


@mcp.tool()
def relegated(competition: str, season: int, count: int = 4) -> dict:
    """Return the bottom `count` teams (relegation zone) for a season."""
    return get_engine().relegated(competition, season, count=count)


@mcp.tool()
def list_competitions() -> dict:
    """List the competitions and seasons available in the knowledge graph."""
    eng = get_engine()
    return {
        "competitions": [
            {"name": c, "seasons": eng.graph.seasons(c)} for c in eng.graph.competitions
        ],
        "teams": len(eng.graph.teams),
        "matches": len(eng.graph.matches),
        "players": len(eng.graph.players),
    }


# ========================= STATISTICS TOOLS =============================== #
@mcp.tool()
def head_to_head(team_a: str, team_b: str, competition: Optional[str] = None) -> dict:
    """Head-to-head record (wins/draws/goals) between two teams."""
    return get_engine().head_to_head(team_a, team_b, competition=competition)


@mcp.tool()
def competition_stats(competition: Optional[str] = None, season: Optional[int] = None) -> dict:
    """Average goals per match, home/away win rates and draw rate over a slice."""
    return get_engine().competition_stats(competition=competition, season=season)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
) -> dict:
    """Largest-margin victories in the dataset (optionally filtered)."""
    return get_engine().biggest_wins(competition=competition, season=season, limit=limit)


@mcp.tool()
def best_record(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: str = "either",
    metric: str = "win_rate",
    limit: int = 10,
) -> dict:
    """Rank teams by win_rate or points over a competition/season (min 5 games).
    venue: 'home', 'away' or 'either' — e.g. the best home/away record."""
    return get_engine().best_record(
        competition=competition, season=season, venue=venue, metric=metric, limit=limit
    )


@mcp.tool()
def top_scoring_teams(
    competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
) -> dict:
    """Teams that scored the most goals over a competition/season slice."""
    return get_engine().top_scoring_teams(competition=competition, season=season, limit=limit)


def main() -> None:
    # Warm the graph before accepting requests so the first call is fast.
    get_engine()
    mcp.run()


if __name__ == "__main__":
    main()
