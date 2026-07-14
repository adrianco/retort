"""MCP server exposing the Brazilian soccer knowledge graph as tools.

Run with: python -m soccer_mcp.server
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .repository import SoccerRepository

mcp = FastMCP(
    name="brazilian-soccer",
    instructions=(
        "Knowledge graph over Brazilian soccer matches (Brasileirao, Copa do "
        "Brasil, Copa Libertadores, Serie B/C) and FIFA player ratings. Team "
        "names may be given in any spelling/suffix form (e.g. 'Flamengo', "
        "'Flamengo-RJ'); they are normalized automatically."
    ),
)

_repo: SoccerRepository | None = None


def get_repository() -> SoccerRepository:
    global _repo
    if _repo is None:
        _repo = SoccerRepository.from_data_dir()
    return _repo


@mcp.tool()
def list_teams(query: str | None = None) -> list[str]:
    """List distinct team names found in the match datasets.

    Args:
        query: optional substring to filter team names by (case-insensitive).
    """
    return get_repository().list_teams(query)


@mcp.tool()
def list_competitions() -> list[str]:
    """List the competitions covered by the loaded datasets."""
    return get_repository().list_competitions()


@mcp.tool()
def list_seasons(competition: str | None = None) -> list[int]:
    """List seasons (years) available, optionally scoped to one competition."""
    return get_repository().list_seasons(competition)


@mcp.tool()
def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Find matches by team, opponent, competition, season, date range, or venue.

    Args:
        team: a team name (any spelling), e.g. "Flamengo" or "Flamengo-RJ".
        opponent: restrict to matches against this team.
        competition: e.g. "Brasileirao Serie A", "Copa do Brasil", "Copa Libertadores".
        season: year, e.g. 2023.
        date_from: ISO date (YYYY-MM-DD) lower bound, inclusive.
        date_to: ISO date (YYYY-MM-DD) upper bound, inclusive.
        venue: "home" or "away" relative to `team`; omit for either.
        limit: max number of matches to return (most recent first).
    """
    matches = get_repository().find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        venue=venue,
        limit=limit,
    )
    return [m.to_dict() for m in matches]


@mcp.tool()
def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Head-to-head record and match list between two teams.

    Args:
        team_a: first team name (any spelling).
        team_b: second team name (any spelling).
        competition: optionally restrict to one competition.
        season: optionally restrict to one season/year.
    """
    return get_repository().head_to_head(team_a, team_b, competition=competition, season=season)


@mcp.tool()
def team_record(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
) -> dict[str, Any]:
    """Win/draw/loss record and goal stats for one team.

    Args:
        team: team name (any spelling).
        competition: optionally restrict to one competition.
        season: optionally restrict to one season/year.
        venue: "home", "away", or omit for both.
    """
    return get_repository().team_record(
        team, competition=competition, season=season, venue=venue
    ).to_dict()


@mcp.tool()
def standings(competition: str, season: int, min_matches: int = 1) -> list[dict[str, Any]]:
    """Calculated league table for a competition/season, ranked by points.

    Args:
        competition: e.g. "Brasileirao Serie A".
        season: year, e.g. 2019.
        min_matches: exclude teams with fewer matches than this (data-quality filter).
    """
    rows = get_repository().standings(competition, season, min_matches=min_matches)
    return [r.to_dict() for r in rows]


@mcp.tool()
def biggest_wins(
    competition: str | None = None, season: int | None = None, n: int = 10
) -> list[dict[str, Any]]:
    """Largest victories by goal difference, optionally scoped to a competition/season."""
    matches = get_repository().biggest_wins(competition=competition, season=season, n=n)
    return [m.to_dict() for m in matches]


@mcp.tool()
def average_goals(competition: str | None = None, season: int | None = None) -> dict[str, Any]:
    """Average goals per match and home/draw/away win rates for a filtered set of matches."""
    return get_repository().average_goals(competition=competition, season=season)


@mcp.tool()
def best_record(
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
    min_matches: int = 5,
    n: int = 10,
    by: str = "win_rate",
) -> list[dict[str, Any]]:
    """Rank teams by win_rate, points, or goal_difference for the given filters.

    Args:
        competition: optionally restrict to one competition.
        season: optionally restrict to one season/year.
        venue: "home", "away", or omit to combine both.
        min_matches: minimum matches played to be eligible (avoids small-sample noise).
        n: number of teams to return.
        by: ranking metric — one of "win_rate", "points", "goal_difference".
    """
    rows = get_repository().best_record(
        competition=competition,
        season=season,
        venue=venue,
        min_matches=min_matches,
        n=n,
        by=by,
    )
    return [r.to_dict() for r in rows]


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search FIFA player data by name/nationality/club/position/rating.

    Args:
        name: substring match against player name.
        nationality: exact country match, e.g. "Brazil".
        club: substring match against club name.
        position: exact position match, e.g. "ST", "GK", "CDM".
        min_overall: minimum FIFA overall rating.
        limit: max results, sorted by overall rating descending.
    """
    players = get_repository().search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        limit=limit,
    )
    return [p.to_dict() for p in players]


@mcp.tool()
def top_players(
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    n: int = 10,
) -> list[dict[str, Any]]:
    """Top-rated FIFA players for an optional nationality/club/position filter."""
    players = get_repository().top_players(
        nationality=nationality, club=club, position=position, n=n
    )
    return [p.to_dict() for p in players]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
