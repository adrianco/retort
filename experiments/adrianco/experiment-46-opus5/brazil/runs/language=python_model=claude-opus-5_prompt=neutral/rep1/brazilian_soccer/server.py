"""MCP server exposing the Brazilian soccer knowledge graph.

Run it over stdio (the transport Claude Desktop and most MCP clients use)::

    python -m brazilian_soccer.server

Every tool returns human-readable text so an LLM can quote it directly; the
structured results behind them live in :mod:`brazilian_soccer.queries`. Tool
functions are plain callables (FastMCP's decorator returns the original
function), which is what the test-suite exercises.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import formatting as fmt
from . import queries as q
from .graph import KnowledgeGraph, load_graph

INSTRUCTIONS = """\
Knowledge graph over Brazilian football: 16k+ matches (Brasileirão Série A/B/C
2003-2023, Copa do Brasil 2012-2023, Copa Libertadores 2013-2022) and 18k FIFA
player records.

Team names are fuzzy-matched, so "Flamengo", "flamengo-rj" and "Palmeiras-SP"
all work. Standings, records and statistics are calculated from the match data
itself, so always describe them as "from the dataset" rather than as official
records. Player data comes from a FIFA snapshot and does not cover every
Brazilian club.
"""

mcp = FastMCP("brazilian-soccer", instructions=INSTRUCTIONS)


def get_graph() -> KnowledgeGraph:
    """The process-wide knowledge graph (loaded on first use).

    The CSVs are located by :func:`~.loader.resolve_data_dir`, which honours
    ``$BRAZILIAN_SOCCER_DATA_DIR``.
    """
    return load_graph()


def _guard(func, *args, **kwargs) -> str:
    """Run a query + formatter pair, turning lookup failures into guidance."""
    try:
        return func(*args, **kwargs)
    except q.UnknownTeamError as error:
        return str(error)
    except q.UnknownCompetitionError as error:
        return str(error)
    except ValueError as error:
        return f"Cannot answer that: {error}"


# --------------------------------------------------------------------------- #
# Match tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str = "any",
    stage: str | None = None,
    limit: int = 20,
) -> str:
    """Find matches by team, opponent, competition, season, date range or stage.

    Args:
        team: Club name, e.g. "Flamengo" or "Palmeiras-SP".
        opponent: Restrict to matches against this club.
        competition: "Brasileirão", "Série B", "Copa do Brasil", "Libertadores".
        season: Year of the season, e.g. 2019.
        date_from: ISO or DD/MM/YYYY lower bound on the match date.
        date_to: Upper bound on the match date.
        venue: "home", "away" or "any" (relative to `team`).
        stage: Cup stage or round text, e.g. "final", "semifinals", "group stage".
        limit: Maximum number of matches listed (default 20).
    """
    return _guard(lambda: fmt.format_matches(q.search_matches(
        get_graph(), team=team, opponent=opponent, competition=competition,
        season=season, date_from=date_from, date_to=date_to, venue=venue,
        stage=stage, limit=limit,
    )))


@mcp.tool()
def last_meeting(team_a: str, team_b: str) -> str:
    """When two clubs last played each other, and the score.

    Args:
        team_a: First club.
        team_b: Second club.
    """
    return _guard(lambda: fmt.format_last_meeting(
        q.last_meeting(get_graph(), team_a, team_b)))


@mcp.tool()
def head_to_head(team_a: str, team_b: str, competition: str | None = None,
                 season: int | None = None, limit: int = 10) -> str:
    """Head-to-head record between two clubs: wins, draws, goals and matches.

    Args:
        team_a: First club.
        team_b: Second club.
        competition: Optional competition filter.
        season: Optional season filter.
        limit: Number of individual matches to list.
    """
    return _guard(lambda: fmt.format_head_to_head(q.head_to_head(
        get_graph(), team_a, team_b, competition=competition, season=season,
        limit=limit)))


@mcp.tool()
def derbies(season: int | None = None, competition: str | None = None,
            limit: int = 30) -> str:
    """Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, ...).

    Args:
        season: Optional season filter, e.g. 2023.
        competition: Optional competition filter.
        limit: Maximum number of derby matches listed.
    """
    return _guard(lambda: fmt.format_derbies(q.derbies(
        get_graph(), season=season, competition=competition, limit=limit)))


# --------------------------------------------------------------------------- #
# Team tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def team_statistics(team: str, season: int | None = None,
                    competition: str | None = None, venue: str = "any") -> str:
    """Win/draw/loss record, goals and points for a club.

    Args:
        team: Club name.
        season: Optional season, e.g. 2022.
        competition: Optional competition filter.
        venue: "home", "away" or "any".
    """
    return _guard(lambda: fmt.format_team_stats(q.team_stats(
        get_graph(), team, season=season, competition=competition, venue=venue)))


@mcp.tool()
def team_profile(team: str) -> str:
    """Everything known about a club: span, record per competition, squad.

    Args:
        team: Club name.
    """
    return _guard(lambda: fmt.format_team_profile(
        q.team_profile(get_graph(), team)))


@mcp.tool()
def compare_teams(team_a: str, team_b: str, season: int | None = None,
                  competition: str | None = None) -> str:
    """Compare two clubs side by side, including their head-to-head.

    Args:
        team_a: First club.
        team_b: Second club.
        season: Optional season filter.
        competition: Optional competition filter.
    """
    return _guard(lambda: fmt.format_compare_teams(q.compare_teams(
        get_graph(), team_a, team_b, season=season, competition=competition)))


@mcp.tool()
def home_away_split(team: str, season: int | None = None,
                    competition: str | None = None) -> str:
    """Compare a club's home record with its away record.

    Args:
        team: Club name.
        season: Optional season filter.
        competition: Optional competition filter.
    """
    return _guard(lambda: fmt.format_home_away(q.home_away_split(
        get_graph(), team, season=season, competition=competition)))


@mcp.tool()
def find_teams(query: str = "", limit: int = 25) -> str:
    """List clubs whose name matches `query` (use it to disambiguate names).

    Args:
        query: Part of a club name; empty lists the first clubs alphabetically.
        limit: Maximum number of clubs returned.
    """
    return _guard(lambda: fmt.format_teams(
        q.list_teams(get_graph(), query=query, limit=limit)))


# --------------------------------------------------------------------------- #
# Player tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def search_players(name: str | None = None, nationality: str | None = None,
                   club: str | None = None, position: str | None = None,
                   min_overall: int | None = None, max_age: int | None = None,
                   sort_by: str = "overall", limit: int = 20) -> str:
    """Search FIFA player records by name, nationality, club, position, rating.

    Args:
        name: Full or partial player name.
        nationality: e.g. "Brazil".
        club: Club name; Brazilian clubs are matched through the team registry.
        position: FIFA position code ("ST", "GK") or a group
            ("forward", "midfielder", "defender", "goalkeeper").
        min_overall: Minimum FIFA overall rating.
        max_age: Maximum age.
        sort_by: "overall", "potential", "age" or "name".
        limit: Maximum number of players listed.
    """
    return _guard(lambda: fmt.format_players(q.search_players(
        get_graph(), name=name, nationality=nationality, club=club,
        position=position, min_overall=min_overall, max_age=max_age,
        sort_by=sort_by, limit=limit)))


@mcp.tool()
def player_profile(name: str) -> str:
    """Profile of one player, plus how their club appears in the match data.

    Args:
        name: Player name, e.g. "Gabriel Barbosa" or "Neymar".
    """
    return _guard(lambda: fmt.format_player_profile(
        q.player_profile(get_graph(), name)))


@mcp.tool()
def club_squad(club: str, limit: int = 15, nationality: str | None = None) -> str:
    """Highest-rated FIFA players at a club.

    Args:
        club: Club name.
        limit: Maximum number of players listed.
        nationality: Optional nationality filter, e.g. "Brazil".
    """
    return _guard(lambda: fmt.format_club_squad(q.club_squad(
        get_graph(), club, limit=limit, nationality=nationality)))


@mcp.tool()
def players_by_club(nationality: str = "Brazil",
                    only_clubs_in_match_data: bool = True,
                    limit: int = 15) -> str:
    """Count players of a nationality per club (e.g. Brazilians at Brazilian clubs).

    Args:
        nationality: Player nationality to aggregate.
        only_clubs_in_match_data: Keep only clubs that also appear in match data.
        limit: Maximum number of clubs listed.
    """
    return _guard(lambda: fmt.format_players_by_club(q.players_by_club_summary(
        get_graph(), nationality=nationality,
        only_clubs_in_match_data=only_clubs_in_match_data, limit=limit)))


# --------------------------------------------------------------------------- #
# Competition tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def standings(competition: str, season: int) -> str:
    """League table for a season, calculated from match results.

    Args:
        competition: "Brasileirão", "Série B", "Série C".
        season: Season year, e.g. 2019.
    """
    return _guard(lambda: fmt.format_standings(
        q.standings(get_graph(), competition, season)))


@mcp.tool()
def competition_summary(competition: str, season: int | None = None) -> str:
    """Coverage and aggregate statistics for a competition.

    Args:
        competition: Competition name.
        season: Optional single season.
    """
    return _guard(lambda: fmt.format_competition_summary(
        q.competition_summary(get_graph(), competition, season=season)))


@mcp.tool()
def knockout_bracket(competition: str, season: int) -> str:
    """Cup matches for a season grouped by stage (bracket view).

    Args:
        competition: "Copa do Brasil" or "Libertadores".
        season: Season year, e.g. 2018.
    """
    return _guard(lambda: fmt.format_bracket(
        q.knockout_bracket(get_graph(), competition, season)))


@mcp.tool()
def list_competitions() -> str:
    """Which competitions, seasons and source files the graph covers."""
    return _guard(lambda: fmt.format_competitions(q.list_competitions(get_graph())))


# --------------------------------------------------------------------------- #
# Statistics tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def biggest_wins(competition: str | None = None, season: int | None = None,
                 team: str | None = None, limit: int = 10) -> str:
    """Largest margins of victory in the data.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
        team: Optional club; returns that club's biggest wins.
        limit: Maximum number of matches listed.
    """
    return _guard(lambda: fmt.format_biggest_wins(q.biggest_wins(
        get_graph(), competition=competition, season=season, team=team,
        limit=limit)))


@mcp.tool()
def team_rankings(metric: str = "points", competition: str | None = None,
                  season: int | None = None, venue: str = "any",
                  min_matches: int = 10, limit: int = 10) -> str:
    """Rank clubs by a metric — "best home record", "most goals", and so on.

    Args:
        metric: "points", "wins", "win_rate", "goals_for", "goals_against",
            "goal_difference" or "points_per_match".
        competition: Optional competition filter.
        season: Optional season filter.
        venue: "home", "away" or "any".
        min_matches: Minimum matches for a club to be ranked.
        limit: Maximum number of clubs listed.
    """
    return _guard(lambda: fmt.format_rankings(q.team_rankings(
        get_graph(), metric=metric, competition=competition, season=season,
        venue=venue, min_matches=min_matches, limit=limit)))


@mcp.tool()
def compare_seasons(competition: str, seasons: list[int]) -> str:
    """Aggregate statistics for several seasons of a competition.

    Args:
        competition: Competition name.
        seasons: Season years, e.g. [2018, 2019].
    """
    return _guard(lambda: fmt.format_compare_seasons(
        q.compare_seasons(get_graph(), competition, seasons)))


@mcp.tool()
def dataset_statistics() -> str:
    """Dataset-wide totals: goals per match, home win rate, coverage."""
    return _guard(lambda: fmt.format_overall_statistics(
        q.overall_statistics(get_graph())))


# --------------------------------------------------------------------------- #
# Resources
# --------------------------------------------------------------------------- #

@mcp.resource("soccer://overview")
def overview_resource() -> str:
    """Summary of the loaded knowledge graph."""
    return fmt.format_competitions(q.list_competitions(get_graph()))


@mcp.resource("soccer://teams")
def teams_resource() -> str:
    """All clubs in the graph that have match data, with their ids."""
    graph = get_graph()
    rows = sorted(
        (
            (graph.team_name(team_id), team_id, len(matches))
            for team_id, matches in graph.matches_by_team.items()
        ),
        key=lambda row: -row[2],
    )
    return "\n".join(f"{name} [{team_id}] - {count} matches"
                     for name, team_id, count in rows)


def main() -> None:
    """Entry point: preload the graph, then serve MCP over stdio."""
    get_graph()
    mcp.run()


if __name__ == "__main__":
    main()
