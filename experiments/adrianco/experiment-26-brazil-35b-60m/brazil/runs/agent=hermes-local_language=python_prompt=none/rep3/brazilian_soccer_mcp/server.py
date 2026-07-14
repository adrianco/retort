"""MCP server for Brazilian soccer knowledge graph."""

from mcp.server.fastmcp import FastMCP
from brazilian_soccer_mcp.data_loader import DataLoader
from brazilian_soccer_mcp import query_handlers

mcp = FastMCP(
    "brazilian-soccer-mcp",
    instructions="MCP server for querying Brazilian soccer data including matches, teams, players, and competitions.",
)

# Global data loader instance
_loader = DataLoader()


@mcp.tool()
def search_matches(
    team: str = None,
    opponent: str = None,
    competition: str = None,
    season: int = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 50,
) -> str:
    """Search for soccer matches by team, opponent, competition, season, or date range.
    
    Args:
        team: Team name to search for (home or away)
        opponent: Opponent team name
        competition: Competition name (e.g., 'Brasileirao', 'Copa do Brasil', 'Libertadores')
        season: Season year (e.g., 2023)
        date_from: Start date in ISO format (e.g., '2023-01-01')
        date_to: End date in ISO format (e.g., '2023-12-31')
        limit: Maximum number of results (default 50)
    
    Returns:
        JSON string with matching matches
    """
    matches = query_handlers.find_matches(
        loader=_loader,
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    import json
    return json.dumps(matches, ensure_ascii=False, indent=2)


@mcp.tool()
def get_team_stats(
    team: str,
    competition: str = None,
    season: int = None,
) -> str:
    """Get team statistics including wins, losses, draws, goals, and win rate.
    
    Args:
        team: Team name
        competition: Filter by competition (optional)
        season: Filter by season year (optional)
    
    Returns:
        JSON string with team statistics
    """
    stats = query_handlers.get_team_statistics(
        loader=_loader,
        team=team,
        competition=competition,
        season=season,
    )
    import json
    return json.dumps(stats, ensure_ascii=False, indent=2)


@mcp.tool()
def get_head_to_head(
    team1: str,
    team2: str,
    competition: str = None,
) -> str:
    """Get head-to-head statistics and match history between two teams.
    
    Args:
        team1: First team name
        team2: Second team name
        competition: Filter by competition (optional)
    
    Returns:
        JSON string with head-to-head record and match details
    """
    h2h = query_handlers.get_head_to_head(
        loader=_loader,
        team1=team1,
        team2=team2,
        competition=competition,
    )
    import json
    return json.dumps(h2h, ensure_ascii=False, indent=2)


@mcp.tool()
def search_players(
    name: str = None,
    nationality: str = None,
    club: str = None,
    position: str = None,
    min_rating: int = None,
    max_results: int = 50,
) -> str:
    """Search for FIFA players by name, nationality, club, position, or rating.
    
    Args:
        name: Partial or full player name
        nationality: Player nationality (e.g., 'Brazil')
        club: Team/club name (e.g., 'Flamengo', 'Paris Saint-Germain')
        position: Playing position (e.g., 'ST', 'GK', 'Forward')
        min_rating: Minimum overall rating (0-99)
        max_results: Maximum number of results (default 50)
    
    Returns:
        JSON string with matching players
    """
    players = query_handlers.search_players(
        loader=_loader,
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_rating=min_rating,
        max_results=max_results,
    )
    import json
    return json.dumps(players, ensure_ascii=False, indent=2)


@mcp.tool()
def get_standings(
    competition: str,
    season: int,
) -> str:
    """Calculate and return league standings for a competition and season.
    
    Args:
        competition: Competition name (e.g., 'Brasileirao', 'Copa do Brasil')
        season: Season year
    
    Returns:
        JSON string with standings list sorted by points
    """
    standings = query_handlers.get_standings(
        loader=_loader,
        competition=competition,
        season=season,
    )
    import json
    return json.dumps(standings, ensure_ascii=False, indent=2)


@mcp.tool()
def get_biggest_wins(
    limit: int = 10,
) -> str:
    """Find the biggest victories (highest goal difference) in the dataset.
    
    Args:
        limit: Maximum number of results (default 10)
    
    Returns:
        JSON string with biggest wins ordered by goal difference
    """
    wins = query_handlers.get_biggest_wins(
        loader=_loader,
        limit=limit,
    )
    import json
    return json.dumps(wins, ensure_ascii=False, indent=2)


@mcp.tool()
def get_average_goals(
    competition: str = None,
) -> str:
    """Calculate average goals per match, home/away win rates, and draw rate.
    
    Args:
        competition: Filter by competition (optional, all if None)
    
    Returns:
        JSON string with average goals statistics
    """
    stats = query_handlers.get_average_goals(
        loader=_loader,
        competition=competition,
    )
    import json
    return json.dumps(stats, ensure_ascii=False, indent=2)


@mcp.tool()
def get_best_away_record(
    limit: int = 10,
) -> str:
    """Find teams with the best away records (minimum 5 away matches required).
    
    Args:
        limit: Maximum number of results (default 10)
    
    Returns:
        JSON string with away records sorted by win rate
    """
    records = query_handlers.get_best_away_record(
        loader=_loader,
        limit=limit,
    )
    import json
    return json.dumps(records, ensure_ascii=False, indent=2)


@mcp.tool()
def get_brazilian_players_by_club() -> str:
    """Get count and average rating of Brazilian players grouped by club.
    
    Returns:
        JSON string with Brazilian player stats per club
    """
    result = query_handlers.get_brazilian_players_by_club(
        loader=_loader,
    )
    import json
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def list_teams() -> str:
    """List all unique team names found in the match data.
    
    Returns:
        JSON string with sorted list of all team names
    """
    teams = query_handlers.get_team_names(
        loader=_loader,
    )
    import json
    return json.dumps(teams, ensure_ascii=False, indent=2)


@mcp.tool()
def list_competitions() -> str:
    """List all unique competitions found in the match data.
    
    Returns:
        JSON string with sorted list of all competition names
    """
    all_matches = _loader.all_matches()
    competitions = sorted(all_matches['competition'].unique().tolist())
    import json
    return json.dumps(competitions, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
