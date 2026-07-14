"""MCP Server for Brazilian Soccer Knowledge Graph."""

import json
import logging

import pandas as pd

from mcp.server.fastmcp import FastMCP

from .data_loader import (
    get_match_data,
    get_player_data,
    normalize_team_name,
    get_all_competitions,
)
from .query_engine import QueryEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP(
    name="Brazilian Soccer MCP",
    instructions=(
        "A knowledge graph server for Brazilian soccer data including matches, "
        "teams, players, and competitions from multiple datasets."
    ),
)

# Initialize the query engine once
_match_data = get_match_data()
_player_data = get_player_data()
engine = QueryEngine(match_data=_match_data, player_data=_player_data)


@mcp.tool()
def search_matches(
    team: str,
    competition: str = None,
    season: int = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 50,
) -> str:
    """Search for matches involving a specific team.

    Args:
        team: Team name to search for (e.g., "Flamengo", "Palmeiras").
        competition: Optional competition filter (e.g., "Brasileirao Serie A").
        season: Optional season year (e.g., 2023).
        date_from: Optional start date in YYYY-MM-DD format.
        date_to: Optional end date in YYYY-MM-DD format.
        limit: Maximum number of results to return.

    Returns:
        JSON string of matching matches.
    """
    results = engine.find_matches_by_team(
        team=team,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return json.dumps({"matches": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def find_matches_between_teams(
    team_a: str,
    team_b: str,
    competition: str = None,
    limit: int = 50,
) -> str:
    """Find head-to-head matches between two teams.

    Args:
        team_a: First team name.
        team_b: Second team name.
        competition: Optional competition filter.
        limit: Maximum results to return.

    Returns:
        JSON string with matches and head-to-head summary.
    """
    result = engine.find_matches_between_teams(
        team_a=team_a,
        team_b=team_b,
        competition=competition,
        limit=limit,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def find_latest_match(
    team_a: str,
    team_b: str,
    competition: str = None,
) -> str:
    """Find the most recent match between two teams.

    Args:
        team_a: First team name.
        team_b: Second team name.
        competition: Optional competition filter.

    Returns:
        JSON string of the latest match.
    """
    result = engine.find_latest_match(
        team_a=team_a,
        team_b=team_b,
        competition=competition,
    )
    return json.dumps({"match": result}, indent=2, default=str)


@mcp.tool()
def find_copa_do_brasil_finals(
    season: int = None,
) -> str:
    """Find Copa do Brasil final matches.

    Args:
        season: Optional season year. If None, returns finals from all seasons.

    Returns:
        JSON string of final matches.
    """
    results = engine.find_copa_do_brasil_final(season=season)
    return json.dumps({"finals": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def get_team_statistics(
    team: str,
    competition: str = None,
    season: int = None,
    date_from: str = None,
    date_to: str = None,
) -> str:
    """Get comprehensive team statistics.

    Args:
        team: Team name.
        competition: Optional competition filter.
        season: Optional season filter.
        date_from: Optional start date.
        date_to: Optional end date.

    Returns:
        JSON string with team statistics including wins, draws, losses, goals, and breakdown.
    """
    result = engine.get_team_statistics(
        team=team,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
    )
    return json.dumps({"statistics": result}, indent=2, default=str)


@mcp.tool()
def get_standings(
    competition: str,
    season: int,
) -> str:
    """Get standings for a competition and season, calculated from match results.

    Uses 3 points for a win, 1 for a draw.

    Args:
        competition: Competition name (e.g., "Brasileirao Serie A").
        season: Season year.

    Returns:
        JSON string of standings table.
    """
    results = engine.get_standings(competition=competition, season=season)
    return json.dumps({"standings": results, "total_teams": len(results)}, indent=2, default=str)


@mcp.tool()
def get_champion(
    competition: str,
    season: int,
) -> str:
    """Get the champion of a competition and season.

    Args:
        competition: Competition name.
        season: Season year.

    Returns:
        JSON string of the champion team details.
    """
    result = engine.get_champion(competition=competition, season=season)
    return json.dumps({"champion": result}, indent=2, default=str)


@mcp.tool()
def get_average_goals(
    competition: str = None,
    season: int = None,
) -> str:
    """Calculate average goals per match statistics.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.

    Returns:
        JSON string with goals statistics.
    """
    result = engine.get_average_goals_per_match(
        competition=competition,
        season=season,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def get_biggest_wins(
    competition: str = None,
    limit: int = 10,
) -> str:
    """Get the biggest goal margin victories.

    Args:
        competition: Optional competition filter.
        limit: Maximum results to return.

    Returns:
        JSON string of biggest wins.
    """
    results = engine.get_biggest_wins(competition=competition, limit=limit)
    return json.dumps({"biggest_wins": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def search_player(
    name: str,
    limit: int = 10,
) -> str:
    """Search for players by name (case-insensitive partial match).

    Args:
        name: Player name to search for.
        limit: Maximum results to return.

    Returns:
        JSON string of matching players.
    """
    results = engine.search_player(name=name, limit=limit)
    return json.dumps({"players": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def get_players_by_nationality(
    nationality: str,
    min_overall: int = None,
    limit: int = 50,
) -> str:
    """Get players filtered by nationality.

    Args:
        nationality: Nationality to filter by (e.g., "Brazil").
        min_overall: Minimum overall rating filter.
        limit: Maximum results.

    Returns:
        JSON string of players.
    """
    results = engine.get_players_by_nationality(
        nationality=nationality,
        min_overall=min_overall,
        limit=limit,
    )
    return json.dumps({"players": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def get_players_by_club(
    club: str,
    min_overall: int = None,
    position: str = None,
    limit: int = 50,
) -> str:
    """Get players filtered by club.

    Args:
        club: Club name to filter by.
        min_overall: Minimum overall rating.
        position: Optional position filter.
        limit: Maximum results.

    Returns:
        JSON string of players.
    """
    results = engine.get_players_by_club(
        club=club,
        min_overall=min_overall,
        position=position,
        limit=limit,
    )
    return json.dumps({"players": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def get_brazilian_players_at_brazilian_clubs(
    min_overall: int = None,
    limit: int = 100,
) -> str:
    """Get Brazilian players playing at Brazilian clubs.

    Args:
        min_overall: Minimum overall rating.
        limit: Maximum results.

    Returns:
        JSON string of Brazilian players at Brazilian clubs.
    """
    results = engine.get_brazilian_players_by_brazilian_club(
        min_overall=min_overall,
        limit=limit,
    )
    return json.dumps({"players": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def get_brazilian_club_summary() -> str:
    """Get summary of Brazilian players at Brazilian clubs.

    Returns:
        JSON string of club summaries with player counts and ratings.
    """
    results = engine.get_brazilian_club_summary()
    return json.dumps({"summaries": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def get_biggest_wins_by_margin(
    competition: str = None,
    min_margin: int = 4,
    limit: int = 10,
) -> str:
    """Get matches with the biggest goal margin victories above a threshold.

    Args:
        competition: Optional competition filter.
        min_margin: Minimum goal margin to include.
        limit: Maximum results.

    Returns:
        JSON string of biggest wins above the margin threshold.
    """
    results = engine.get_biggest_wins(competition=competition, limit=limit)
    filtered = [r for r in results if r["margin"] >= min_margin]
    return json.dumps({"biggest_wins": filtered, "total": len(filtered)}, indent=2, default=str)


@mcp.tool()
def get_team_performance_trend(
    team: str,
    competition: str = None,
    season: int = None,
    period: str = "season",
) -> str:
    """Get team performance trend over time.

    Args:
        team: Team name.
        competition: Optional competition filter.
        season: Optional season filter.
        period: How to group results - "season" or "round".

    Returns:
        JSON string of performance trend data.
    """
    results = engine.get_team_performance_trend(
        team=team,
        competition=competition,
        season=season,
        period=period,
    )
    return json.dumps({"trend": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def get_best_away_record(
    competition: str = None,
    season: int = None,
    limit: int = 10,
) -> str:
    """Find teams with the best away records.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
        limit: Maximum results.

    Returns:
        JSON string of best away records.
    """
    results = engine.get_best_away_record(
        competition=competition,
        season=season,
        limit=limit,
    )
    return json.dumps({"best_away_records": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def get_competitions_for_team(
    team: str,
) -> str:
    """Find all competitions a team has played in.

    Args:
        team: Team name.

    Returns:
        JSON string of competitions.
    """
    results = engine.get_competitions_for_team(team=team)
    return json.dumps({"competitions": results, "total": len(results)}, indent=2, default=str)


@mcp.tool()
def get_all_competitions_list() -> str:
    """Get list of all available competitions in the dataset.

    Returns:
        JSON string of all competitions.
    """
    competitions = get_all_competitions(_match_data)
    return json.dumps({"competitions": competitions, "total": len(competitions)}, indent=2, default=str)


@mcp.tool()
def get_dataset_summary() -> str:
    """Get a summary of all datasets and their contents.

    Returns:
        JSON string with dataset summary including match counts and player counts.
    """
    match_df = get_match_data()
    player_df = get_player_data()

    summary = {
        "match_data": {
            "total_matches": len(match_df),
            "competitions": {},
            "date_range": {
                "earliest": str(match_df["date"].min()) if not match_df.empty else None,
                "latest": str(match_df["date"].max()) if not match_df.empty else None,
            },
        },
        "player_data": {
            "total_players": len(player_df),
        },
    }

    for comp in match_df["competition"].unique():
        comp_df = match_df[match_df["competition"] == comp]
        summary["match_data"]["competitions"][comp] = {
            "matches": len(comp_df),
            "seasons": sorted(comp_df["season"].dropna().unique().tolist()),
        }

    return json.dumps(summary, indent=2, default=str)


@mcp.tool()
def get_teams_list() -> str:
    """Get list of all unique teams across all match data.

    Returns:
        JSON string of all teams.
    """
    teams = set()
    for _, row in _match_data.iterrows():
        teams.add(row["home_team"])
        teams.add(row["away_team"])
    return json.dumps({"teams": sorted(teams), "total": len(teams)}, indent=2, default=str)


def main():
    """Entry point for the MCP server."""
    logger.info("Starting Brazilian Soccer MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
