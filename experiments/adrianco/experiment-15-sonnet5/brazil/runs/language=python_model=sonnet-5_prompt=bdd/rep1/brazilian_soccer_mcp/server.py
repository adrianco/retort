"""MCP server exposing the Brazilian soccer knowledge graph as tools an
LLM can call to answer natural-language questions about players, teams,
matches and competitions.

Run directly (`python -m brazilian_soccer_mcp.server`) to serve over
stdio, the transport most MCP clients (Claude Desktop, etc.) expect.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import formatting as fmt
from .data_loader import load_all
from .graph import KnowledgeGraph, TeamNotFoundError
from .queries import QueryEngine

mcp = FastMCP("brazilian-soccer")

_data = load_all()
_graph = KnowledgeGraph(_data.matches, _data.players)
_engine = QueryEngine(_graph)


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> str:
    """Find matches by team, opponent, competition, season, and/or date range.

    competition: one of "Brasileirao", "Serie B", "Serie C", "Copa do Brasil", "Libertadores".
    date_from/date_to: "YYYY-MM-DD".
    """
    try:
        matches = _engine.search_matches(team, opponent, competition, season, date_from, date_to, limit)
    except ValueError as exc:
        return str(exc)
    return fmt.format_matches(matches)


@mcp.tool()
def get_head_to_head(team_a: str, team_b: str, competition: str | None = None) -> str:
    """Head-to-head win/loss/draw record and match history between two teams."""
    try:
        result = _engine.head_to_head(team_a, team_b, competition)
    except (TeamNotFoundError, ValueError) as exc:
        return str(exc)
    return fmt.format_head_to_head(result)


@mcp.tool()
def get_team_record(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
) -> str:
    """Win/draw/loss and goal record for a team. venue: "home", "away", or omit for both."""
    try:
        record = _engine.team_record(team, season, competition, venue)
    except (TeamNotFoundError, ValueError) as exc:
        return str(exc)
    return fmt.format_team_record(record)


@mcp.tool()
def compare_teams(
    team_a: str,
    team_b: str,
    season: int | None = None,
    competition: str | None = None,
) -> str:
    """Compare two teams' overall records plus their head-to-head history."""
    try:
        result = _engine.compare_teams(team_a, team_b, season, competition)
    except (TeamNotFoundError, ValueError) as exc:
        return str(exc)
    return fmt.format_compare_teams(result)


@mcp.tool()
def get_top_scoring_teams(competition: str | None = None, season: int | None = None, limit: int = 10) -> str:
    """Teams ranked by total goals scored (home + away)."""
    try:
        table = _engine.top_scoring_teams(competition, season, limit)
    except ValueError as exc:
        return str(exc)
    return fmt.format_top_scoring(table)


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_age: int | None = None,
    limit: int = 20,
) -> str:
    """Search FIFA player data by name, nationality, club, position and/or rating.

    position accepts a FIFA code (e.g. "ST", "GK") or a group
    ("goalkeeper", "defender", "midfielder", "forward").
    """
    players = _engine.search_players(name, nationality, club, position, min_overall, max_age, limit)
    return fmt.format_players(players)


@mcp.tool()
def get_top_rated_players_at_club(club: str, limit: int = 10) -> str:
    """Highest-overall-rated FIFA players at a given club."""
    players = _engine.top_rated_at_club(club, limit)
    return fmt.format_players(players)


@mcp.tool()
def get_brazilian_players_by_club(limit: int = 20) -> str:
    """Count and average FIFA rating of Brazilian players at each Brazilian
    club that appears in both the match data and the FIFA player data.
    """
    table = _engine.brazilian_players_by_club(limit)
    return fmt.format_brazilian_players_by_club(table)


@mcp.tool()
def get_standings(competition: str, season: int) -> str:
    """League table (points, W/D/L, goals) for a competition/season, calculated from match results."""
    try:
        table = _engine.standings(competition, season)
    except ValueError as exc:
        return str(exc)
    return fmt.format_standings(table, competition, season)


@mcp.tool()
def get_champion(competition: str, season: int) -> str:
    """Winner of a competition/season (table-topper for leagues, aggregate final winner for cups)."""
    try:
        result = _engine.champion(competition, season)
    except ValueError as exc:
        return str(exc)
    return fmt.format_champion(result)


@mcp.tool()
def get_relegated_teams(competition: str, season: int, count: int = 4) -> str:
    """Bottom `count` teams in a competition/season's standings."""
    try:
        table = _engine.relegated_teams(competition, season, count)
    except ValueError as exc:
        return str(exc)
    return fmt.format_standings(table, competition, season)


@mcp.tool()
def get_biggest_wins(competition: str | None = None, season: int | None = None, limit: int = 10) -> str:
    """Biggest victories (by goal margin) in the dataset."""
    try:
        table = _engine.biggest_wins(competition, season, limit)
    except ValueError as exc:
        return str(exc)
    return fmt.format_biggest_wins(table)


@mcp.tool()
def get_statistics(competition: str | None = None, season: int | None = None) -> str:
    """Average goals per match and home win rate for a competition/season (or the whole dataset)."""
    try:
        average_goals = _engine.average_goals_per_match(competition, season)
        home_rate = _engine.home_win_rate(competition, season)
    except ValueError as exc:
        return str(exc)
    return fmt.format_statistics(average_goals, home_rate)


@mcp.tool()
def get_best_away_record(
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 5,
    limit: int = 5,
) -> str:
    """Teams with the best away win rate (minimum matches played away)."""
    try:
        table = _engine.best_away_record(competition, season, min_matches, limit)
    except ValueError as exc:
        return str(exc)
    return fmt.format_best_away_record(table)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
