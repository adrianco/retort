"""Brazilian Soccer MCP Server.

Exposes match, team, player, competition, and statistics tools via MCP FastMCP.
Run with: python server.py  (stdio transport, default for MCP clients)
"""

from mcp.server.fastmcp import FastMCP
import query_tools as qt

mcp = FastMCP("Brazilian Soccer Knowledge Graph")


@mcp.tool()
def search_matches(
    team: str = "",
    opponent: str = "",
    competition: str = "",
    season: int = 0,
    start_date: str = "",
    end_date: str = "",
    role: str = "either",
    limit: int = 50,
) -> str:
    """Search for soccer matches by team, competition, season, or date range.

    Use this to find matches for a specific team, get results between two teams,
    or browse a competition's schedule. Returns match results with scores.

    Args:
        team: Team name (e.g. 'Flamengo', 'Palmeiras')
        opponent: Second team for head-to-head search (e.g. 'Fluminense')
        competition: 'Brasileirão', 'Copa do Brasil', or 'Libertadores'
        season: Year (e.g. 2023). 0 means all seasons.
        start_date: Start date filter ISO format YYYY-MM-DD
        end_date: End date filter ISO format YYYY-MM-DD
        role: 'home', 'away', or 'either' (default)
        limit: Max results to return (default 50, max 200)
    """
    return qt.search_matches(
        team=team or None,
        opponent=opponent or None,
        competition=competition or None,
        season=season or None,
        start_date=start_date or None,
        end_date=end_date or None,
        role=role,
        limit=min(limit, 200),
    )


@mcp.tool()
def get_team_stats(
    team: str,
    competition: str = "",
    season: int = 0,
    role: str = "either",
) -> str:
    """Get win/loss/draw record and goal statistics for a team.

    Args:
        team: Team name (e.g. 'Corinthians')
        competition: Filter by competition (optional)
        season: Filter by year e.g. 2022. 0 means all seasons.
        role: 'home', 'away', or 'either' (default)
    """
    return qt.get_team_stats(
        team=team,
        competition=competition or None,
        season=season or None,
        role=role,
    )


@mcp.tool()
def head_to_head(
    team1: str,
    team2: str,
    competition: str = "",
    season: int = 0,
    limit: int = 20,
) -> str:
    """Get head-to-head record and recent matches between two teams.

    Args:
        team1: First team (e.g. 'Flamengo')
        team2: Second team (e.g. 'Corinthians')
        competition: Filter by competition (optional)
        season: Filter by season year. 0 means all seasons.
        limit: Max recent matches to include (default 20)
    """
    return qt.head_to_head(
        team1=team1,
        team2=team2,
        competition=competition or None,
        season=season or None,
        limit=limit,
    )


@mcp.tool()
def get_competition_standings(
    season: int,
    competition: str = "Brasileirão",
) -> str:
    """Calculate league standings for a given season from match results.

    Args:
        season: Year (e.g. 2019)
        competition: Competition name — 'Brasileirão' (default), 'Copa do Brasil', 'Libertadores'
    """
    return qt.get_competition_standings(season=season, competition=competition)


@mcp.tool()
def search_players(
    name: str = "",
    nationality: str = "",
    club: str = "",
    position: str = "",
    min_overall: int = 0,
    limit: int = 30,
) -> str:
    """Search the FIFA player database by name, nationality, club, or position.

    Args:
        name: Player name (partial match, e.g. 'Neymar')
        nationality: Country (e.g. 'Brazil', 'Argentina')
        club: Club name (partial match, e.g. 'Flamengo')
        position: Position code (e.g. 'ST', 'GK', 'CAM', 'CB')
        min_overall: Minimum FIFA overall rating (e.g. 80)
        limit: Max results (default 30, max 100)
    """
    return qt.search_players(
        name=name or None,
        nationality=nationality or None,
        club=club or None,
        position=position or None,
        min_overall=min_overall or None,
        limit=min(limit, 100),
    )


@mcp.tool()
def top_scoring_teams(
    competition: str = "",
    season: int = 0,
    top_n: int = 10,
) -> str:
    """Rank teams by total goals scored.

    Args:
        competition: Competition filter (optional)
        season: Season year. 0 means all seasons.
        top_n: Number of top teams (default 10)
    """
    return qt.top_scorers_by_team(
        competition=competition or None,
        season=season or None,
        top_n=top_n,
    )


@mcp.tool()
def biggest_wins(
    competition: str = "",
    season: int = 0,
    top_n: int = 10,
) -> str:
    """Find matches with the biggest goal-margin victories.

    Args:
        competition: Filter by competition (optional)
        season: Filter by season year. 0 means all seasons.
        top_n: Number of results (default 10)
    """
    return qt.biggest_wins(
        competition=competition or None,
        season=season or None,
        top_n=top_n,
    )


@mcp.tool()
def aggregate_stats(
    competition: str = "",
    season: int = 0,
) -> str:
    """Get aggregate statistics: goals per match, home win rate, etc.

    Args:
        competition: Competition filter (optional)
        season: Season year filter. 0 means all seasons.
    """
    return qt.aggregate_stats(
        competition=competition or None,
        season=season or None,
    )


@mcp.tool()
def best_home_records(
    competition: str = "",
    season: int = 0,
    top_n: int = 10,
) -> str:
    """Find teams with the best home win records.

    Args:
        competition: Competition filter (optional)
        season: Season year filter. 0 means all seasons.
        top_n: Number of top teams (default 10)
    """
    return qt.best_home_records(
        competition=competition or None,
        season=season or None,
        top_n=top_n,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
