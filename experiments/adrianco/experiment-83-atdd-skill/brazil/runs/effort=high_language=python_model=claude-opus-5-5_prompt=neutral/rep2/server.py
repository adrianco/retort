"""Brazilian Soccer MCP server.

Exposes the query engine in queries.py as MCP tools so an LLM can answer
natural-language questions about Brazilian soccer matches, teams, players and
competitions.  Run with:

    python server.py                 # stdio transport (for Claude Desktop / Claude Code)
    python server.py --http 8000     # streamable HTTP transport on port 8000
"""

from __future__ import annotations

import argparse
from typing import Annotated, Callable

from pydantic import Field

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from queries import QueryError, SoccerQueries

INSTRUCTIONS = """\
Knowledge graph of Brazilian soccer built from six Kaggle datasets:
Brasileirão Série A 2003-2023 (plus Série B/C 2014-2023), Copa do Brasil 2012-2023,
Copa Libertadores 2013-2022 and the FIFA 19 player database (18,207 players).
Team names are normalized, so 'Palmeiras-SP', 'Palmeiras' and 'SE Palmeiras' are the same
club. Competition arguments accept 'Brasileirão'/'Serie A', 'Copa do Brasil', 'Libertadores'.
Standings are calculated from match results. FIFA 19 has squads for only 15 Brazilian clubs
(no Flamengo, Palmeiras, Corinthians or São Paulo)."""

mcp = MCPServer("brazilian-soccer", instructions=INSTRUCTIONS, version="1.0.0")

_queries: SoccerQueries | None = None


def get_queries() -> SoccerQueries:
    global _queries
    if _queries is None:
        _queries = SoccerQueries()
    return _queries


def _run(fn: Callable[[SoccerQueries], str]) -> str:
    try:
        return fn(get_queries())
    except QueryError as exc:
        raise ToolError(str(exc)) from exc


Team = Annotated[str, Field(description="Team name in any spelling, e.g. 'Flamengo', 'Sao Paulo', 'Atlético-MG'")]
OptTeam = Annotated[str | None, Field(description="Team name in any spelling")]
Competition = Annotated[str | None, Field(
    description="'Brasileirão' (Série A), 'Serie B', 'Serie C', 'Copa do Brasil' or 'Libertadores'; omit for all")]
Season = Annotated[int | None, Field(description="Season year, e.g. 2019")]
Venue = Annotated[str, Field(description="'all', 'home' or 'away'")]


@mcp.tool()
def dataset_info() -> str:
    """Describe the loaded datasets: files, row counts, competitions and seasons covered."""
    return _run(lambda q: q.dataset_info())


@mcp.tool()
def find_team(query: Annotated[str, Field(description="Full or partial team name")], limit: int = 10) -> str:
    """Search team names across all match files and show canonical names, ids and spelling variants."""
    return _run(lambda q: q.find_team(query, limit))


@mcp.tool()
def search_matches(team: OptTeam = None, opponent: OptTeam = None, competition: Competition = None,
                   season: Season = None,
                   date_from: Annotated[str | None, Field(description="Start date, YYYY-MM-DD or DD/MM/YYYY")] = None,
                   date_to: Annotated[str | None, Field(description="End date, YYYY-MM-DD or DD/MM/YYYY")] = None,
                   venue: Venue = "all",
                   stage: Annotated[str | None, Field(
                       description="Cup stage: 'group stage', 'round of 16', 'quarterfinals', 'semifinals', "
                                   "'final'")] = None,
                   limit: int = 20) -> str:
    """Find matches by team, opponent, competition, season, date range, venue or cup stage.

    Results are most recent first, so limit=1 answers 'when did X last play Y?'.
    """
    return _run(lambda q: q.search_matches(team, opponent, competition, season, date_from, date_to, venue, stage,
                                           limit))


@mcp.tool()
def head_to_head(team_a: Team, team_b: Team, competition: Competition = None,
                 season_from: Season = None, season_to: Season = None, limit: int = 15) -> str:
    """Head-to-head record between two teams: wins, draws, goals, home/away split and recent meetings."""
    return _run(lambda q: q.head_to_head(team_a, team_b, competition, season_from, season_to, limit))


@mcp.tool()
def team_record(team: Team, season: Season = None, competition: Competition = None, venue: Venue = "all") -> str:
    """Win/draw/loss record, goals for/against and win rate for a team (optionally home or away only)."""
    return _run(lambda q: q.team_record(team, season, competition, venue))


@mcp.tool()
def team_overview(team: Team) -> str:
    """Cross-dataset team profile: competitions and seasons played, records, league titles, derbies,
    recent matches and FIFA 19 squad."""
    return _run(lambda q: q.team_overview(team))


@mcp.tool()
def team_trend(team: Team, competition: Competition = "Brasileirão") -> str:
    """Season-by-season league position, points and goals for a team (performance trend)."""
    return _run(lambda q: q.team_trend(team, competition))


@mcp.tool()
def standings(season: Annotated[int, Field(description="Season year, e.g. 2019")],
              competition: Competition = "Brasileirão",
              top: Annotated[int | None, Field(description="Only show the top N teams")] = None) -> str:
    """League table for a season calculated from match results, with champion and relegated teams."""
    return _run(lambda q: q.standings(season, competition, top))


@mcp.tool()
def team_rankings(metric: Annotated[str, Field(
                      description="points, wins, win_rate, goals_for, goals_against, goal_difference, "
                                  "goals_per_match, points_per_match, losses or draws")] = "points",
                  competition: Competition = "Brasileirão", season: Season = None, venue: Venue = "all",
                  min_matches: Annotated[int | None, Field(
                      description="Minimum matches to qualify (default 5 for a season, 30 all-time)")] = None,
                  limit: int = 10,
                  ascending: Annotated[bool | None, Field(
                      description="Sort lowest first (default: only for goals_against)")] = None) -> str:
    """Rank teams by a metric, e.g. most goals in a season, best home or away record, best defence."""
    return _run(lambda q: q.team_rankings(metric, competition, season, venue, min_matches, limit, ascending))


@mcp.tool()
def competition_stats(competition: Competition = None, season: Season = None, team: OptTeam = None) -> str:
    """Aggregate statistics: goals per match, home/draw/away rates, common scores, corners and shots."""
    return _run(lambda q: q.competition_stats(competition, season, team))


@mcp.tool()
def compare_seasons(seasons: Annotated[list[int], Field(description="Seasons to compare, e.g. [2018, 2019]")],
                    competition: Competition = "Brasileirão") -> str:
    """Compare seasons side by side: scoring, home advantage, champion, best attack/defence, relegations."""
    return _run(lambda q: q.compare_seasons(seasons, competition))


@mcp.tool()
def biggest_wins(competition: Competition = None, season: Season = None, team: OptTeam = None,
                 limit: int = 10) -> str:
    """Largest victory margins, optionally filtered by competition, season or winning team."""
    return _run(lambda q: q.biggest_wins(competition, season, team, limit))


@mcp.tool()
def knockout_results(competition: Annotated[str, Field(
                         description="'Libertadores' or 'Copa do Brasil'")] = "Libertadores",
                     season: Season = None,
                     stage: Annotated[str | None, Field(
                         description="'round of 16', 'quarterfinals', 'semifinals' or 'final'; "
                                     "defaults to 'final' when no season is given")] = None) -> str:
    """Cup knockout ties with aggregate scores: a season's bracket, or every final when no season is given."""
    return _run(lambda q: q.knockout_results(competition, season, stage))


@mcp.tool()
def derby_matches(season: Season = None, team: OptTeam = None, competition: Competition = None,
                  derby: Annotated[str | None, Field(description="Derby name, e.g. 'Fla-Flu', 'Grenal'")] = None,
                  limit: int = 30) -> str:
    """Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, Clássico Mineiro, ...)."""
    return _run(lambda q: q.derby_matches(season, team, competition, derby, limit))


@mcp.tool()
def search_players(name: Annotated[str | None, Field(description="Full or partial player name")] = None,
                   nationality: Annotated[str | None, Field(description="e.g. 'Brazil' or 'Brazilian'")] = None,
                   club: Annotated[str | None, Field(description="Club name, e.g. 'Santos', 'Real Madrid'")] = None,
                   position: Annotated[str | None, Field(
                       description="Position code (ST, CB, GK, ...) or group: goalkeeper, defender, "
                                   "midfielder, forward")] = None,
                   min_overall: int | None = None, max_age: int | None = None,
                   brazilian_clubs_only: bool = False,
                   sort_by: Annotated[str, Field(
                       description="overall, potential, age, name or a skill such as Finishing")] = "overall",
                   limit: int = 20) -> str:
    """Search the FIFA 19 player database by name, nationality, club, position, rating or age."""
    return _run(lambda q: q.search_players(name, nationality, club, position, min_overall, max_age,
                                           brazilian_clubs_only, sort_by, limit))


@mcp.tool()
def player_profile(name: Annotated[str, Field(description="Player name, e.g. 'Neymar', 'Casemiro'")]) -> str:
    """Detailed FIFA 19 profile of a player, linked to their club's match record when it is Brazilian."""
    return _run(lambda q: q.player_profile(name))


@mcp.tool()
def player_club_summary(nationality: Annotated[str | None, Field(description="Nationality filter")] = "Brazil",
                        brazilian_clubs_only: bool = False, top_players: int = 10, max_clubs: int = 20) -> str:
    """Top-rated players of a nationality and player counts / average ratings per club."""
    return _run(lambda q: q.player_club_summary(nationality, brazilian_clubs_only, top_players, max_clubs))


@mcp.resource("soccer://dataset-info", name="dataset-info", mime_type="text/plain")
def dataset_info_resource() -> str:
    """Summary of the loaded datasets."""
    return get_queries().dataset_info()


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument("--http", type=int, metavar="PORT", help="serve streamable HTTP on PORT instead of stdio")
    args = parser.parse_args()
    get_queries()  # load data before accepting requests
    if args.http:
        mcp.run(transport="streamable-http", port=args.http)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
