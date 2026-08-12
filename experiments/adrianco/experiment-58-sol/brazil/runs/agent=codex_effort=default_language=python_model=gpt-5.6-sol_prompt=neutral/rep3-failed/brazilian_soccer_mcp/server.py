"""Official FastMCP transport adapter for the soccer query service."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP

from .query import NaturalLanguageQuery
from .service import SoccerService


mcp = FastMCP(
    "Brazilian Soccer Knowledge Graph",
    instructions=(
        "Use structured tools for exact filtering and analytics. Use ask_soccer for common "
        "natural-language demo questions. Results cover bundled historical datasets only; "
        "never describe them as live scores or current rosters."
    ),
)


@lru_cache(maxsize=1)
def get_service() -> SoccerService:
    return SoccerService()


@mcp.tool()
def ask_soccer(question: str, limit: int = 20) -> dict[str, Any]:
    """Answer a common natural-language question by routing it to deterministic soccer analytics."""
    return NaturalLanguageQuery(get_service()).ask(question, limit=limit)


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    season: int | None = None,
    competition: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    side: str = "either",
    stage: str | None = None,
    source: str | None = None,
    deduplicate: bool = True,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Find scored matches by team, opponent, season, competition, date range, venue, stage, or source."""
    return get_service().search_matches(team=team, opponent=opponent, season=season, competition=competition, start_date=start_date, end_date=end_date, side=side, stage=stage, source=source, deduplicate=deduplicate, limit=limit, offset=offset)


@mcp.tool()
def team_statistics(team: str, season: int | None = None, competition: str | None = None, side: str = "either") -> dict[str, Any]:
    """Calculate wins, draws, losses, goals, points, and win rate for a team."""
    return get_service().team_statistics(team, season=season, competition=competition, side=side)


@mcp.tool()
def head_to_head(team1: str, team2: str, season: int | None = None, competition: str | None = None, limit: int = 25) -> dict[str, Any]:
    """Compare two teams and return their record plus recent meetings."""
    return get_service().head_to_head(team1, team2, season=season, competition=competition, limit=limit)


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    sort_by: str = "overall",
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Search FIFA players by name, nationality, club, position family, or minimum rating."""
    return get_service().search_players(name=name, nationality=nationality, club=club, position=position, min_overall=min_overall, sort_by=sort_by, limit=limit, offset=offset)


@mcp.tool()
def standings(season: int, competition: str = "Brasileirão Série A", limit: int = 30) -> dict[str, Any]:
    """Calculate a league-style table from one canonical match source to avoid duplicates."""
    return get_service().standings(season, competition, limit=limit)


@mcp.tool()
def competition_statistics(competition: str | None = None, season: int | None = None) -> dict[str, Any]:
    """Calculate goal averages and home, away, and draw outcome rates."""
    return get_service().competition_statistics(competition=competition, season=season)


@mcp.tool()
def biggest_victories(competition: str | None = None, season: int | None = None, limit: int = 10) -> dict[str, Any]:
    """Return matches with the largest winning margins."""
    return get_service().biggest_victories(competition=competition, season=season, limit=limit)


@mcp.tool()
def best_record(side: str, season: int | None = None, competition: str | None = None, min_matches: int = 5, limit: int = 10) -> dict[str, Any]:
    """Rank teams by home or away win rate with a minimum sample size."""
    return get_service().best_record(side, season=season, competition=competition, min_matches=min_matches, limit=limit)


@mcp.tool()
def team_competitions(team: str, season: int | None = None) -> dict[str, Any]:
    """List competitions in which a team appears across the bundled match files."""
    return get_service().team_competitions(team, season=season)


@mcp.tool()
def derby_matches(season: int | None = None, limit: int = 100) -> dict[str, Any]:
    """Find matches for a curated set of traditional Brazilian rivalries."""
    return get_service().derby_matches(season=season, limit=limit)


@mcp.tool()
def competition_finals(competition: str, season: int | None = None, limit: int = 100) -> dict[str, Any]:
    """Return labeled finals or infer Copa do Brasil finals from each season's highest numbered round."""
    return get_service().competition_finals(competition, season=season, limit=limit)


@mcp.tool()
def club_profile(team: str, season: int | None = None, competition: str | None = None, player_limit: int = 25) -> dict[str, Any]:
    """Join match statistics, competitions, and FIFA player records for one club."""
    return get_service().club_profile(team, season=season, competition=competition, player_limit=player_limit)


@mcp.tool()
def compare_seasons(season1: int, season2: int, competition: str = "Brasileirão Série A") -> dict[str, Any]:
    """Compare aggregate outcomes and scoring across two seasons."""
    return get_service().compare_seasons(season1, season2, competition)


@mcp.tool()
def dataset_status() -> dict[str, Any]:
    """Report load status and usable row counts for every required CSV file."""
    return get_service().dataset_status()


@mcp.resource("soccer://datasets")
def dataset_resource() -> str:
    """Human-readable dataset inventory for MCP clients."""
    status = get_service().dataset_status()
    lines = ["Bundled Brazilian soccer dataset inventory:"]
    lines.extend(f"- {name}: {count} usable rows" for name, count in status["rows_by_source"].items())
    lines.append("Data is historical and must not be represented as live.")
    return "\n".join(lines)


def main() -> None:
    """Start the default stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
