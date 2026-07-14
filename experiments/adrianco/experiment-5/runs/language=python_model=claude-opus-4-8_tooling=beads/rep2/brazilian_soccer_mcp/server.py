"""
================================================================================
server.py - FastMCP server exposing the Brazilian soccer knowledge base
================================================================================

CONTEXT
-------
Wires the :class:`QueryEngine` to the Model Context Protocol using the official
``mcp`` SDK's FastMCP helper. Each MCP tool is a thin wrapper: it calls a query
method then a formatter, returning prose suited to an LLM. The engine/store is
loaded once at import time from the bundled ``data/kaggle`` CSVs.

Run as a stdio MCP server (the transport Claude Desktop / clients use):

    python -m brazilian_soccer_mcp.server
        or
    python run_server.py

Tools exposed:
    find_matches, last_match, team_record, head_to_head, compare_teams,
    competitions_for_team, search_players, get_player, brazilian_clubs_summary,
    standings, competition_winner, relegated_teams, league_statistics,
    biggest_wins, best_record, top_scoring_team, data_summary

The module degrades gracefully: if the ``mcp`` package is not installed the
query engine and tool functions still import and work (useful for testing),
only the network ``main()`` entry point requires the SDK.
================================================================================
"""

from __future__ import annotations

from typing import Optional

from . import formatters as fmt
from .data_loader import load_default_store
from .query_engine import QueryEngine

# Build the engine once. Loading ~24k matches + 18k players takes well under a
# second and is cached for the life of the process.
_ENGINE: Optional[QueryEngine] = None


def get_engine() -> QueryEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = QueryEngine(load_default_store())
    return _ENGINE


# --------------------------------------------------------------------------- #
# Tool implementations (plain functions so they are testable without MCP).
# --------------------------------------------------------------------------- #
def find_matches(team=None, opponent=None, season=None, competition=None,
                 date_from=None, date_to=None, limit=25) -> str:
    """Find matches by team(s), season, competition and/or date range."""
    return fmt.format_matches(get_engine().find_matches(
        team=team, opponent=opponent, season=season, competition=competition,
        date_from=date_from, date_to=date_to, limit=limit))


def last_match(team: str, opponent: str) -> str:
    """When two teams last met, with the score and competition."""
    return fmt.format_last_match(get_engine().last_match(team, opponent))


def team_record(team: str, season=None, competition=None, scope="overall") -> str:
    """Win/draw/loss and goals record for a team (scope: overall|home|away)."""
    return fmt.format_team_record(get_engine().team_record(
        team, season=season, competition=competition,
        home_only=(scope == "home"), away_only=(scope == "away")))


def head_to_head(team1: str, team2: str, season=None, competition=None) -> str:
    """Head-to-head record and meeting list between two teams."""
    return fmt.format_head_to_head(get_engine().head_to_head(
        team1, team2, season=season, competition=competition))


def compare_teams(team1: str, team2: str, season=None) -> str:
    """Compare two teams' records side by side plus their head-to-head."""
    data = get_engine().compare_teams(team1, team2, season=season)
    return (
        fmt.format_team_record(data["team1_record"]) + "\n\n"
        + fmt.format_team_record(data["team2_record"]) + "\n\n"
        + fmt.format_head_to_head(data["head_to_head"])
    )


def competitions_for_team(team: str) -> str:
    """List the competitions and seasons a team appears in."""
    return fmt.format_competitions_for_team(get_engine().competitions_for_team(team))


def search_players(name=None, nationality=None, club=None, position=None,
                   min_overall=None, limit=15) -> str:
    """Search FIFA players by name, nationality, club, position or rating."""
    return fmt.format_players(get_engine().search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, limit=limit))


def get_player(name: str) -> str:
    """Look up a single player's profile by name."""
    return fmt.format_player(get_engine().get_player(name))


def brazilian_clubs_summary(top: int = 10) -> str:
    """Player counts and average ratings for Brazilian clubs."""
    return fmt.format_club_summary(get_engine().club_player_summary("Brazil", top=top))


def standings(season: int, competition="serie_a") -> str:
    """League table for a season, calculated from match results."""
    return fmt.format_standings(get_engine().standings(season, competition))


def competition_winner(season: int, competition="serie_a") -> str:
    """Champion of a league season (top of the calculated standings)."""
    data = get_engine().competition_winner(season, competition)
    return f"{data['season']} {data['competition']} champion: {data['champion']}"


def relegated_teams(season: int, competition="serie_a", count: int = 4) -> str:
    """Teams in the relegation zone for a season."""
    data = get_engine().relegated(season, competition, count)
    teams = ", ".join(r["team"] for r in data["relegated"])
    return f"{data['season']} {data['competition']} relegated ({count}): {teams}"


def league_statistics(competition="serie_a", season=None) -> str:
    """Average goals, home/away win rates and totals for a competition."""
    return fmt.format_league_statistics(get_engine().league_statistics(competition, season))


def biggest_wins(competition=None, season=None, limit=10) -> str:
    """Largest goal-margin victories in the dataset."""
    return fmt.format_biggest_wins(get_engine().biggest_wins(competition, season, limit))


def best_record(competition="serie_a", season=None, scope="home") -> str:
    """Rank teams by home/away/overall record."""
    return fmt.format_best_record(get_engine().best_record(
        competition=competition, season=season, scope=scope))


def top_scoring_team(competition="serie_a", season=None) -> str:
    """Teams that scored the most goals in a competition/season."""
    data = get_engine().top_scoring_team(competition, season)
    lines = [f"Top scoring teams — {data['competition']} {data.get('season') or '(all seasons)'}:"]
    for i, r in enumerate(data["ranking"], 1):
        lines.append(f"{i}. {r['team']} - {r['goals']} goals")
    return "\n".join(lines)


def data_summary() -> str:
    """Overview of how much data is loaded."""
    s = get_engine().data_summary()
    return (
        f"Loaded {s['total_matches']} matches "
        f"({s['canonical_matches']} canonical, de-duplicated) and "
        f"{s['players']} players across {s['competitions']} competitions.\n"
        f"Competitions: {', '.join(s['competition_names'])}\n"
        f"Seasons: {s['seasons'][0]}–{s['seasons'][-1]}"
    )


# All tools registered with the MCP server.
_TOOLS = [
    find_matches, last_match, team_record, head_to_head, compare_teams,
    competitions_for_team, search_players, get_player, brazilian_clubs_summary,
    standings, competition_winner, relegated_teams, league_statistics,
    biggest_wins, best_record, top_scoring_team, data_summary,
]


def build_mcp():
    """Construct and return a FastMCP server with all tools registered."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("brazilian-soccer")
    for tool in _TOOLS:
        mcp.add_tool(tool)
    return mcp


def main() -> None:
    """Entry point: run the server over stdio (eagerly load data first)."""
    get_engine()  # warm the cache so the first query is fast
    build_mcp().run()


if __name__ == "__main__":
    main()
