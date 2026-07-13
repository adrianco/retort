"""
Brazilian Soccer MCP Server - Model Context Protocol implementation.

Provides tools for querying Brazilian soccer data including:
  - Match search and results
  - Team statistics and records
  - Player search and profiles
  - Competition standings
  - Statistical analysis

Author: Brazilian Soccer MCP Project
"""

import logging
from typing import Optional, List, Dict, Any

from mcp.server.fastmcp import FastMCP
from brazilian_soccer_mcp.data_loader import DataLoader
from brazilian_soccer_mcp.queries import (
    search_matches,
    find_matches_between,
    get_h2h,
    get_biggest_wins,
    get_team_stats,
    get_team_matches,
    get_competition_leaderboard,
    search_players,
    get_brazilian_players,
    get_players_by_club,
    get_average_goals,
    get_team_best_away_record,
    format_match_display,
    format_h2h_display,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP(
    name="Brazilian Soccer MCP",
    version="0.1.0",
    description="Knowledge graph interface for Brazilian soccer data including "
                "Brasileirao, Copa do Brasil, Libertadores, and FIFA player data.",
)

# Global data loader
_data_loader: Optional[DataLoader] = None


def _get_loader() -> DataLoader:
    """Get or create the shared DataLoader instance."""
    global _data_loader
    if _data_loader is None:
        logger.info("Loading all datasets...")
        _data_loader = DataLoader()
        _data_loader.load_all()
        logger.info(
            "Loaded: Brasileirao=%d, Brazilian_Cup=%d, Libertadores=%d, "
            "BR_Football=%d, Novo_Campeonato=%d, FIFA=%d",
            len(_data_loader.brasileirao_df) if _data_loader.brasileirao_df is not None else 0,
            len(_data_loader.brazilian_cup_df) if _data_loader.brazilian_cup_df is not None else 0,
            len(_data_loader.libertadores_df) if _data_loader.libertadores_df is not None else 0,
            len(_data_loader.br_football_df) if _data_loader.br_football_df is not None else 0,
            len(_data_loader.novo_campeonato_df) if _data_loader.novo_campeonato_df is not None else 0,
            len(_data_loader.fifa_df) if _data_loader.fifa_df is not None else 0,
        )
    return _data_loader


# ─── Match tools ─────────────────────────────────────────────────────────────

@mcp.tool()
def search_matches_tool(
    team: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 50,
) -> str:
    """
    Search matches by criteria.

    Args:
        team: Team name to filter (home or away)
        date_from: Start date in YYYY-MM-DD format
        date_to: End date in YYYY-MM-DD format
        competition: Competition name (e.g. 'Brasileirao', 'Brazilian_Cup', 'Libertadores')
        season: Season/year to filter
        limit: Maximum number of results

    Returns:
        Formatted string of matching matches.
    """
    loader = _get_loader()
    all_matches = loader.all_matches
    result = search_matches(all_matches, team, date_from, date_to, competition, season, limit)

    lines = [f"Found {result['total_found']} matches:"]
    for m in result['matches']:
        lines.append(f"  {format_match_display(m)}")
    return "\n".join(lines)


@mcp.tool()
def find_matches_between_tool(team_a: str, team_b: str, limit: int = 50) -> str:
    """
    Find all matches between two teams (head-to-head).

    Args:
        team_a: First team name
        team_b: Second team name
        limit: Maximum number of results

    Returns:
        Formatted head-to-head results.
    """
    loader = _get_loader()
    result = find_matches_between(loader.all_matches, team_a, team_b, limit)
    return f"Found {result['total_found']} matches:\n" + \
           "\n".join(f"  {format_match_display(m)}" for m in result['matches'])


@mcp.tool()
def get_h2h_tool(team_a: str, team_b: str) -> str:
    """
    Get head-to-head record between two teams.

    Args:
        team_a: First team name
        team_b: Second team name

    Returns:
        Formatted head-to-head summary with wins/draws/losses and match list.
    """
    loader = _get_loader()
    result = get_h2h(loader.all_matches, team_a, team_b)
    return format_h2h_display(result)


@mcp.tool()
def get_biggest_wins_tool(competition: Optional[str] = None, limit: int = 10) -> str:
    """
    Find the biggest wins (largest goal difference) in the dataset.

    Args:
        competition: Optional competition filter
        limit: Maximum number of results

    Returns:
        Formatted list of biggest wins.
    """
    loader = _get_loader()
    result = get_biggest_wins(loader.all_matches, competition, limit)
    lines = [f"Biggest wins ({len(result['matches'])}):"]
    for i, m in enumerate(result['matches'], 1):
        lines.append(
            f"  {i}. {m['home_team']} {m['home_goals']}-{m['away_goals']} {m['away_team']} "
            f"({m['date']}, {m['competition']}, diff: {m['goal_difference']})"
        )
    return "\n".join(lines)


# ─── Team tools ──────────────────────────────────────────────────────────────

@mcp.tool()
def get_team_stats_tool(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    home_only: bool = False,
    away_only: bool = False,
) -> str:
    """
    Get team statistics including wins, losses, draws, goals, win rate.

    Args:
        team: Team name
        season: Optional season filter
        competition: Optional competition filter
        home_only: If True, only home matches
        away_only: If True, only away matches

    Returns:
        Formatted team statistics.
    """
    loader = _get_loader()
    result = get_team_stats(loader.all_matches, team, season, competition, home_only, away_only)
    stats = result['overall']
    lines = [
        f"Team: {result['team']}",
        f"  Matches: {stats['matches']}",
        f"  Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}",
        f"  Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}",
        f"  Win Rate: {stats['win_rate']}%",
    ]
    if result['by_competition']:
        lines.append("  By competition:")
        for comp, cs in result['by_competition'].items():
            lines.append(
                f"    {comp}: {cs['wins']}W {cs['draws']}D {cs['losses']}L, "
                f"{cs['goals_for']}-{cs['goals_against']}, {cs['win_rate']}% win rate"
            )
    return "\n".join(lines)


@mcp.tool()
def get_team_matches_tool(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    limit: int = 20,
    order: str = "desc",
) -> str:
    """
    Get recent or chronological match history for a team.

    Args:
        team: Team name
        season: Optional season filter
        competition: Optional competition filter
        limit: Maximum results
        order: 'desc' (newest first) or 'asc' (oldest first)

    Returns:
        Formatted list of matches.
    """
    loader = _get_loader()
    result = get_team_matches(loader.all_matches, team, season, competition, limit, order)
    lines = [f"Matches for {result['team']} ({result['total_matches']} total):"]
    for m in result['matches']:
        lines.append(f"  {format_match_display(m)}")
    return "\n".join(lines)


@mcp.tool()
def get_competition_standings_tool(
    competition: str,
    season: Optional[int] = None,
) -> str:
    """
    Get competition standings (calculated from match results).

    Args:
        competition: Competition name (e.g. 'Brasileirao', 'Brazilian_Cup')
        season: Optional season filter

    Returns:
        Formatted standings table.
    """
    loader = _get_loader()
    result = get_competition_leaderboard(loader.all_matches, competition, season)
    if not result['standings']:
        return f"No standings found for {competition}"
    lines = [
        f"Standings: {result['competition']}"
        + (f" ({result['season']})" if result['season'] else ""),
        f"{'#':<4}{'Team':<25}{'P':>4}{'W':>4}{'D':>4}{'L':>4}{'GF':>4}{'GA':>4}{'GD':>5}{'Pts':>5}",
        "-" * 70,
    ]
    for i, s in enumerate(result['standings'], 1):
        lines.append(
            f"{i:<4}{s['team']:<25}"
            f"{s['played']:>4}{s['won']:>4}{s['drawn']:>4}{s['lost']:>4}"
            f"{s['goals_for']:>4}{s['goals_against']:>4}{s['goal_difference']:>5}"
            f"{s['points']:>5}"
        )
    return "\n".join(lines)


# ─── Player tools ────────────────────────────────────────────────────────────

@mcp.tool()
def search_players_tool(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> str:
    """
    Search FIFA player database.

    Args:
        name: Partial name search
        nationality: Nationality filter (e.g. 'Brazil')
        club: Club filter
        position: Position filter
        min_overall: Minimum overall rating
        limit: Maximum results

    Returns:
        Formatted list of matching players.
    """
    loader = _get_loader()
    result = search_players(loader.fifa_df, name, nationality, club, position, min_overall, limit)
    if not result['players']:
        return "No players found matching the criteria."
    lines = [f"Found {result['total_found']} players:"]
    for i, p in enumerate(result['players'], 1):
        lines.append(
            f"  {i}. {p['name']} - Overall: {p['overall']}, "
            f"Potential: {p['potential']}, Age: {p['age']}, "
            f"Club: {p['club']}, Position: {p['position']}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_brazilian_players_tool(limit: int = 50) -> str:
    """
    Get top Brazilian players in the FIFA dataset.

    Args:
        limit: Maximum number of results

    Returns:
        Formatted list of Brazilian players.
    """
    loader = _get_loader()
    result = get_brazilian_players(loader.fifa_df, limit)
    if not result['players']:
        return "No Brazilian players found."
    lines = [f"Top Brazilian players (total: {result['total_found']}):"]
    for i, p in enumerate(result['players'], 1):
        lines.append(
            f"  {i}. {p['name']} - Overall: {p['overall']}, "
            f"Club: {p['club']}, Position: {p['position']}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_players_by_club_tool(
    club: str,
    nationality: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    Get players at a specific club.

    Args:
        club: Club name
        nationality: Optional nationality filter
        limit: Maximum results

    Returns:
        Formatted list of players at the club.
    """
    loader = _get_loader()
    result = get_players_by_club(loader.fifa_df, club, nationality, limit)
    if not result['players']:
        return f"No players found at {club}."
    lines = [f"Players at {result['club']} (total: {result['total_found']}):"]
    for i, p in enumerate(result['players'], 1):
        lines.append(
            f"  {i}. {p['name']} - Overall: {p['overall']}, "
            f"Nationality: {p['nationality']}, Position: {p['position']}"
        )
    return "\n".join(lines)


# ─── Statistics tools ────────────────────────────────────────────────────────

@mcp.tool()
def get_average_goals_tool(competition: Optional[str] = None) -> str:
    """
    Get average goals per match statistics.

    Args:
        competition: Optional competition filter

    Returns:
        Formatted average goals statistics.
    """
    loader = _get_loader()
    result = get_average_goals(loader.all_matches, competition)
    lines = [
        f"Average goals: {competition if competition else 'All competitions'}",
        f"  Total matches: {result['total_matches']}",
        f"  Average total goals per match: {result['avg_total_goals']}",
        f"  Average home goals: {result['avg_home_goals']}",
        f"  Average away goals: {result['avg_away_goals']}",
        f"  Home win rate: {result['home_win_rate']}%",
        f"  Away win rate: {result['away_win_rate']}%",
        f"  Draw rate: {result['draw_rate']}%",
    ]
    return "\n".join(lines)


@mcp.tool()
def get_team_best_away_record_tool(competition: Optional[str] = None, limit: int = 10) -> str:
    """
    Get the best away records across all teams.

    Args:
        competition: Optional competition filter
        limit: Maximum number of results

    Returns:
        Formatted list of best away records.
    """
    loader = _get_loader()
    result = get_team_best_away_record(loader.all_matches, competition, limit)
    if not result['away_records']:
        return "No away records found."
    lines = [f"Best away records ({len(result['away_records'])}):"]
    for i, r in enumerate(result['away_records'], 1):
        lines.append(
            f"  {i}. {r['team']} - {r['wins']}W {r['draws']}D {r['losses']}L, "
            f"{r['goals_for']}-{r['goals_against']}, {r['win_rate']}% win rate"
        )
    return "\n".join(lines)


# ─── Health ──────────────────────────────────────────────────────────────────

@mcp.tool()
def health_check() -> str:
    """Check if the server is running and data is loaded."""
    loader = _get_loader()
    total_matches = len(loader.all_matches)
    total_players = len(loader.fifa_df)
    return (
        f"Server running. Data loaded:\n"
        f"  Total matches: {total_matches}\n"
        f"  Total players: {total_players}\n"
        f"  Brasileirao: {len(loader.brasileirao_df)} matches\n"
        f"  Brazilian Cup: {len(loader.brazilian_cup_df)} matches\n"
        f"  Libertadores: {len(loader.libertadores_df)} matches\n"
        f"  BR Football: {len(loader.br_football_df)} matches\n"
        f"  Novo Campeonato: {len(loader.novo_campeonato_df)} matches\n"
        f"  FIFA players: {total_players}"
    )


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    """Main entry point for the MCP server."""
    import sys

    # Determine transport
    transport = "stdio"
    if len(sys.argv) > 1:
        transport = sys.argv[1]

    if transport == "http":
        # Start HTTP server
        import uvicorn
        app = mcp._create_starlette_app()
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # Default: stdio transport
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
