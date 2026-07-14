"""Brazilian Soccer MCP Server.

Exposes the knowledge base built from the Kaggle datasets (see TASK.md) as
MCP tools over stdio, so an LLM client can answer natural language questions
about Brazilian soccer matches, teams, players and competitions.

Run with:  python server.py
Or add to an MCP client config:
    {"command": "python", "args": ["/path/to/server.py"]}
"""

from __future__ import annotations

from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from soccer_kb import get_kb

mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Knowledge base of Brazilian soccer: Brasileirão Série A/B/C "
        "(2003-2023), Copa do Brasil, Copa Libertadores match results, and "
        "FIFA player attributes. Team names are normalized — 'Flamengo', "
        "'Flamengo-RJ' and 'CR Flamengo' all work. Use get_data_summary to "
        "see coverage."
    ),
)


@mcp.tool()
def search_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 25,
) -> dict:
    """Search matches by team, opponent, competition, season or date range.

    Args:
        team: Team name (any spelling, e.g. "Flamengo" or "Flamengo-RJ").
        opponent: Restrict to matches against this opponent.
        competition: "Brasileirão"/"Serie A", "Serie B", "Serie C",
            "Copa do Brasil" or "Libertadores".
        season: Season year, e.g. 2023.
        date_from: Earliest match date (YYYY-MM-DD or DD/MM/YYYY).
        date_to: Latest match date.
        limit: Maximum matches returned, newest first (0 = no limit).
    """
    kb = get_kb()
    matches = kb.find_matches(
        team=team, opponent=opponent, competition=competition,
        season=season, date_from=date_from, date_to=date_to, limit=limit,
    )
    total = len(kb.find_matches(
        team=team, opponent=opponent, competition=competition,
        season=season, date_from=date_from, date_to=date_to, limit=0,
    ))
    return {
        "total_found": total,
        "returned": len(matches),
        "matches": [m.to_dict() for m in matches],
    }


@mcp.tool()
def get_head_to_head(team1: str, team2: str) -> dict:
    """Head-to-head record between two teams: wins, draws, goals, all matches.

    Args:
        team1: First team name.
        team2: Second team name.
    """
    return get_kb().head_to_head(team1, team2)


@mcp.tool()
def get_team_statistics(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> dict:
    """Win/draw/loss record, goals and win rate for a team.

    Args:
        team: Team name.
        season: Restrict to one season year (e.g. 2022).
        competition: Restrict to one competition.
        venue: "home", "away" or "all".
    """
    return get_kb().team_statistics(
        team, season=season, competition=competition, venue=venue,
    )


@mcp.tool()
def get_team_competitions(team: str) -> dict:
    """List every competition (and seasons) a team appears in.

    Args:
        team: Team name.
    """
    return get_kb().list_team_competitions(team)


@mcp.tool()
def get_standings(season: int, competition: str = "Serie A") -> dict:
    """League table calculated from results: positions, points, champion,
    and (for Série A) the four relegated teams.

    Args:
        season: Season year, e.g. 2019.
        competition: League name (default Brasileirão Série A).
    """
    return get_kb().standings(season, competition)


@mcp.tool()
def get_cup_finals(competition: str = "Copa do Brasil") -> dict:
    """Final-round matches for every season of a knockout cup
    (Copa do Brasil or Copa Libertadores).

    Args:
        competition: Cup name (default Copa do Brasil).
    """
    return get_kb().cup_finals(competition)


@mcp.tool()
def get_libertadores_bracket(season: int, stage: Optional[str] = None) -> dict:
    """Copa Libertadores results grouped by stage (group stage, round of 16,
    quarterfinals, semifinals, final).

    Args:
        season: Season year, e.g. 2018.
        stage: Optional single stage to return.
    """
    return get_kb().libertadores_stage_results(season, stage)


@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> dict:
    """Search FIFA player data by name, nationality, club, position or rating.

    Args:
        name: Full or partial player name (accent-insensitive).
        nationality: e.g. "Brazil".
        club: Club name, e.g. "Flamengo".
        position: FIFA position code (ST, GK, CDM, LW, ...).
        min_overall: Minimum overall rating.
        limit: Maximum players returned, highest-rated first (0 = no limit).
    """
    kb = get_kb()
    players = kb.search_players(
        name=name, nationality=nationality, club=club,
        position=position, min_overall=min_overall, limit=limit,
    )
    total = len(kb.search_players(
        name=name, nationality=nationality, club=club,
        position=position, min_overall=min_overall, limit=0,
    ))
    return {
        "total_found": total,
        "returned": len(players),
        "players": [p.to_dict() for p in players],
    }


@mcp.tool()
def get_players_by_club_summary(
    nationality: str = "Brazil",
    clubs: Optional[List[str]] = None,
    limit: int = 10,
) -> dict:
    """Player count and average FIFA rating per club for one nationality
    (e.g. Brazilian players at Brazilian clubs).

    Args:
        nationality: Player nationality (default "Brazil").
        clubs: Optional list of club names to restrict to.
        limit: Maximum clubs returned (0 = no limit).
    """
    return get_kb().players_by_club_summary(
        nationality=nationality, clubs=clubs, limit=limit,
    )


@mcp.tool()
def get_average_goals(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict:
    """Average goals per match plus home-win / away-win / draw rates.

    Args:
        competition: Optional competition filter.
        season: Optional season year filter.
    """
    return get_kb().average_goals(competition=competition, season=season)


@mcp.tool()
def get_biggest_wins(
    competition: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Matches with the largest winning margins.

    Args:
        competition: Optional competition filter.
        limit: Number of matches to return.
    """
    return {"matches": get_kb().biggest_wins(competition=competition, limit=limit)}


@mcp.tool()
def get_best_record(
    venue: str = "home",
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 10,
    limit: int = 10,
) -> dict:
    """Teams ranked by win rate at home, away, or overall.

    Args:
        venue: "home", "away" or "all".
        competition: Optional competition filter.
        season: Optional season year filter.
        min_matches: Minimum matches played to qualify.
        limit: Number of teams to return.
    """
    return get_kb().best_record(
        venue=venue, competition=competition, season=season,
        min_matches=min_matches, limit=limit,
    )


@mcp.tool()
def get_data_summary() -> dict:
    """Dataset coverage: match counts per competition, season range,
    player counts and source files."""
    return get_kb().data_summary()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
