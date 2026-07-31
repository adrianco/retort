"""
MCP server binding.

Context
-------
This is the only module that talks to the MCP SDK.  Every tool is a thin,
explicitly typed wrapper around :func:`brazilian_soccer.tools.call_tool`, which
keeps the tool schemas that an LLM sees rich and self-describing while the
actual behaviour stays in the transport-independent layer (and therefore stays
identical between the server, the CLI and the tests).

Exposed surface
---------------
* **Tools** -- match search, head-to-head, team records, standings, champions,
  relegation, statistics, player search, squads, derbies and raw graph
  traversal.  Each returns the answer already formatted in the layouts from
  TASK.md.
* **Resources** -- ``soccer://datasets``, ``soccer://competitions``,
  ``soccer://teams`` and ``soccer://graph/schema`` expose the same information
  as JSON for clients that prefer to read rather than call.
* **Prompts** -- ready-made question templates for team and season analysis.

Run it with ``python -m brazilian_soccer.server`` (stdio transport) or through
the console script ``brazilian-soccer-mcp serve``.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server import MCPServer

from .graph import load_knowledge_graph
from .tools import TOOLS, call_tool

INSTRUCTIONS = """
Knowledge graph of Brazilian soccer built from six Kaggle datasets:
Brasileirao Serie A (2003-2023), Serie B and C (2014-2023), Copa do Brasil
(2012-2023), Copa Libertadores (2013-2022) and the FIFA 19 player database.

Tips for good answers:
* Club names are matched fuzzily -- "Flamengo", "Flamengo-RJ" and "Mengao" all
  work. Use `resolve_team` when a name is ambiguous (Botafogo, America, Atletico).
* Standings, champions and every statistic are calculated from match results;
  the datasets contain no goalscorer or lineup data, so individual top scorers
  cannot be derived.
* The FIFA 19 player file omits clubs that were unlicensed at the time
  (Flamengo, Palmeiras, Corinthians, Sao Paulo, Vasco), so player queries for
  those clubs return nothing even though their matches are present.
* Call `dataset_summary` first if you need to know the coverage limits.
""".strip()

server: MCPServer = MCPServer(
    name="brazilian-soccer",
    title="Brazilian Soccer Knowledge Graph",
    version="1.0.0",
    instructions=INSTRUCTIONS,
)


def _run(tool_name: str, /, **arguments: Any) -> str:
    """Delegate to the shared tool layer.

    ``tool_name`` is positional-only so tools that themselves take a ``name``
    argument (``player_profile``, ``search_players``) do not collide with it.
    """

    return call_tool(tool_name, arguments).text


# ---------------------------------------------------------------------------
# Match tools
# ---------------------------------------------------------------------------


@server.tool(description="Find matches by club, opponent, competition, season, date "
                         "range, cup stage or league round.")
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    home_away: str = "any",
    stage: str | None = None,
    round: str | None = None,
    limit: int = 20,
) -> str:
    """Search matches.

    Args:
        team: Club name, e.g. "Flamengo".
        opponent: Restrict to meetings with this club.
        competition: brasileirao | serie-b | serie-c | copa do brasil | libertadores.
        season: Season year, e.g. 2019.
        date_from: Lower bound date (ISO or DD/MM/YYYY).
        date_to: Upper bound date (ISO or DD/MM/YYYY).
        home_away: "home", "away" or "any" -- applies to `team`.
        stage: Cup stage such as "final", "semifinals", "group stage".
        round: League round number.
        limit: Maximum matches to return.
    """

    return _run("search_matches", team=team, opponent=opponent, competition=competition,
                season=season, date_from=date_from, date_to=date_to,
                home_away=home_away, stage=stage, round=round, limit=limit)


@server.tool(description="Head-to-head record between two clubs: every meeting plus "
                         "wins, draws and goals for each side.")
def head_to_head(team_a: str, team_b: str, competition: str | None = None,
                 season: int | None = None, limit: int = 15) -> str:
    """Compare two clubs' meetings.

    Args:
        team_a: First club.
        team_b: Second club.
        competition: Optional competition filter.
        season: Optional season filter.
        limit: How many matches to list.
    """

    return _run("head_to_head", team_a=team_a, team_b=team_b, competition=competition,
                season=season, limit=limit)


@server.tool(description="Matches between traditional rivals: Fla-Flu, Grenal, Derby "
                         "Paulista, Classico Mineiro and more.")
def find_derbies(season: int | None = None, competition: str | None = None,
                 derby: str | None = None, limit: int = 5) -> str:
    """Find derby matches.

    Args:
        season: Optional season year.
        competition: Optional competition filter.
        derby: Name of one rivalry, e.g. "Grenal".
        limit: Matches listed per rivalry.
    """

    return _run("find_derbies", season=season, competition=competition, derby=derby,
                limit=limit)


# ---------------------------------------------------------------------------
# Team tools
# ---------------------------------------------------------------------------


@server.tool(description="Win/draw/loss record and goals for a club, optionally by "
                         "competition, season and home/away.")
def team_stats(team: str, competition: str | None = None, season: int | None = None,
               scope: str = "all") -> str:
    """Team record.

    Args:
        team: Club name.
        competition: Optional competition filter.
        season: Optional season year.
        scope: "all", "home" or "away".
    """

    return _run("team_stats", team=team, competition=competition, season=season, scope=scope)


@server.tool(description="Full club profile: overall/home/away records, competitions, "
                         "seasons, recent matches and squad size.")
def team_profile(team: str, season: int | None = None) -> str:
    """Team profile.

    Args:
        team: Club name.
        season: Optional season filter.
    """

    return _run("team_profile", team=team, season=season)


@server.tool(description="Side-by-side records for two clubs plus their head-to-head.")
def compare_teams(team_a: str, team_b: str, competition: str | None = None,
                  season: int | None = None) -> str:
    """Compare two clubs.

    Args:
        team_a: First club.
        team_b: Second club.
        competition: Optional competition filter.
        season: Optional season filter.
    """

    return _run("compare_teams", team_a=team_a, team_b=team_b, competition=competition,
                season=season)


@server.tool(description="Rank clubs by points per game, win rate, wins, goals or goal "
                         "difference -- overall, home-only or away-only.")
def best_records(competition: str | None = None, season: int | None = None,
                 scope: str = "all", metric: str = "points_per_game",
                 min_matches: int = 10, limit: int = 10) -> str:
    """Best records.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
        scope: "all", "home" or "away".
        metric: points_per_game | points | win_rate | wins | goals_for |
            goals_against | goal_difference.
        min_matches: Minimum matches for a club to qualify.
        limit: How many clubs to return.
    """

    return _run("best_records", competition=competition, season=season, scope=scope,
                metric=metric, min_matches=min_matches, limit=limit)


@server.tool(description="Clubs ranked by goals scored in a competition or season.")
def top_scoring_teams(competition: str | None = None, season: int | None = None,
                      limit: int = 10) -> str:
    """Top scoring teams.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
        limit: How many clubs to return.
    """

    return _run("top_scoring_teams", competition=competition, season=season, limit=limit)


# ---------------------------------------------------------------------------
# Competition tools
# ---------------------------------------------------------------------------


@server.tool(description="League table calculated from match results, with champion "
                         "and relegation places marked.")
def competition_standings(season: int, competition: str = "brasileirao",
                          scope: str = "all", limit: int | None = None) -> str:
    """League standings.

    Args:
        season: Season year, required.
        competition: brasileirao | serie-b | serie-c.
        scope: "all", "home" or "away".
        limit: How many rows to show.
    """

    return _run("competition_standings", season=season, competition=competition,
                scope=scope, limit=limit)


@server.tool(description="Who won a season -- table winner for leagues, winner of the "
                         "final for the Copa do Brasil and Libertadores.")
def competition_champion(competition: str, season: int) -> str:
    """Season champion.

    Args:
        competition: Competition name.
        season: Season year.
    """

    return _run("competition_champion", competition=competition, season=season)


@server.tool(description="The relegation places of a calculated league table.")
def relegated_teams(season: int, competition: str = "brasileirao", slots: int = 4) -> str:
    """Relegated clubs.

    Args:
        season: Season year.
        competition: Competition name.
        slots: How many relegation places.
    """

    return _run("relegated_teams", season=season, competition=competition, slots=slots)


@server.tool(description="Aggregate statistics: goals per match, home advantage, draw "
                         "rate and the biggest wins.")
def competition_stats(competition: str | None = None, season: int | None = None) -> str:
    """Competition statistics.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
    """

    return _run("competition_stats", competition=competition, season=season)


@server.tool(description="Matches ordered by margin of victory.")
def biggest_wins(competition: str | None = None, season: int | None = None,
                 team: str | None = None, limit: int = 10) -> str:
    """Biggest wins.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
        team: Optional club filter.
        limit: How many matches to return.
    """

    return _run("biggest_wins", competition=competition, season=season, team=team,
                limit=limit)


@server.tool(description="Aggregate several seasons of a competition side by side.")
def compare_seasons(seasons: list[int], competition: str = "brasileirao") -> str:
    """Compare seasons.

    Args:
        seasons: Season years, e.g. [2018, 2019].
        competition: Competition name.
    """

    return _run("compare_seasons", seasons=seasons, competition=competition)


# ---------------------------------------------------------------------------
# Player tools
# ---------------------------------------------------------------------------


@server.tool(description="Search the FIFA player database by name, nationality, club, "
                         "position and rating.")
def search_players(name: str | None = None, nationality: str | None = None,
                   club: str | None = None, position: str | None = None,
                   min_overall: int | None = None, max_age: int | None = None,
                   brazilian_clubs_only: bool = False, sort_by: str = "overall",
                   limit: int = 20) -> str:
    """Search players.

    Args:
        name: Full or partial player name.
        nationality: e.g. "Brazil".
        club: Club name.
        position: FIFA code ("LW") or group ("forward", "goalkeeper").
        min_overall: Minimum FIFA overall rating.
        max_age: Maximum age.
        brazilian_clubs_only: Only players whose club exists in the match graph.
        sort_by: overall | potential | age | name.
        limit: How many players to return.
    """

    return _run("search_players", name=name, nationality=nationality, club=club,
                position=position, min_overall=min_overall, max_age=max_age,
                brazilian_clubs_only=brazilian_clubs_only, sort_by=sort_by, limit=limit)


@server.tool(description="Profile one player: age, club, position, ratings and best "
                         "attributes.")
def player_profile(name: str) -> str:
    """Player profile.

    Args:
        name: Player name, full or partial.
    """

    return _run("player_profile", name=name)


@server.tool(description="Cross-file query: a club's FIFA squad joined to its match "
                         "record in the graph.")
def club_squad(club: str, limit: int = 30) -> str:
    """Club squad.

    Args:
        club: Club name.
        limit: How many players to list.
    """

    return _run("club_squad", club=club, limit=limit)


@server.tool(description="Squad size and average FIFA rating for every club that has "
                         "both player rows and matches.")
def brazilian_club_squads(limit: int = 20) -> str:
    """Squads by club.

    Args:
        limit: How many clubs to return.
    """

    return _run("brazilian_club_squads", limit=limit)


# ---------------------------------------------------------------------------
# Meta tools
# ---------------------------------------------------------------------------


@server.tool(description="Resolve a club name to its canonical identity and list close "
                         "alternatives -- use for ambiguous names.")
def resolve_team(query: str, limit: int = 8) -> str:
    """Resolve a club name.

    Args:
        query: Name to resolve.
        limit: How many candidates to return.
    """

    return _run("resolve_team", query=query, limit=limit)


@server.tool(description="List clubs, optionally filtered by state, country, "
                         "competition or a name substring.")
def list_teams(state: str | None = None, country: str | None = None,
               competition: str | None = None, search: str | None = None,
               limit: int = 30) -> str:
    """List clubs.

    Args:
        state: Brazilian state code, e.g. "SP".
        country: Country code, e.g. "BRA" or "ARG".
        competition: Only clubs that played this competition.
        search: Name substring filter.
        limit: How many clubs to return.
    """

    return _run("list_teams", state=state, country=country, competition=competition,
                search=search, limit=limit)


@server.tool(description="Competitions in the graph with season coverage and match counts.")
def list_competitions() -> str:
    """List competitions."""

    return _run("list_competitions")


@server.tool(description="Provenance and coverage of every dataset, plus graph shape "
                         "and de-duplication results.")
def dataset_summary() -> str:
    """Dataset summary."""

    return _run("dataset_summary")


@server.tool(description="Raw knowledge-graph traversal from a node id such as "
                         "'team:flamengo-rj' or 'competition:serie-a'.")
def graph_neighbors(node_id: str, relation: str | None = None, direction: str = "both",
                    limit: int = 25) -> str:
    """Traverse the graph.

    Args:
        node_id: Node to start from.
        relation: Edge type filter.
        direction: "out", "in" or "both".
        limit: How many neighbours to return.
    """

    return _run("graph_neighbors", node_id=node_id, relation=relation,
                direction=direction, limit=limit)


@server.tool(description="FIFA position codes behind each position group word.")
def position_groups() -> str:
    """Position groups."""

    return _run("position_groups")


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@server.resource("soccer://datasets", mime_type="application/json",
                 description="Source CSVs, licences, row counts and coverage.")
def datasets_resource() -> str:
    return json.dumps(call_tool("dataset_summary").data, indent=2, ensure_ascii=False,
                      default=str)


@server.resource("soccer://competitions", mime_type="application/json",
                 description="Competitions with season coverage and match counts.")
def competitions_resource() -> str:
    return json.dumps(call_tool("list_competitions").data, indent=2, ensure_ascii=False)


@server.resource("soccer://teams", mime_type="application/json",
                 description="Every club in the graph with its match count.")
def teams_resource() -> str:
    return json.dumps(call_tool("list_teams", {"limit": 1000}).data, indent=2,
                      ensure_ascii=False)


@server.resource("soccer://graph/schema", mime_type="application/json",
                 description="Node and edge types in the knowledge graph.")
def graph_schema_resource() -> str:
    return json.dumps(load_knowledge_graph().graph_schema(), indent=2)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@server.prompt(description="Analyse a club using the knowledge graph tools.")
def analyze_team(team: str) -> str:
    return (
        f"Use the Brazilian soccer knowledge graph to analyse {team}.\n"
        f"1. Call team_profile for the overall picture.\n"
        f"2. Call best_records and team_stats to place the club in context.\n"
        f"3. Call club_squad for player data (note it may be empty for unlicensed clubs).\n"
        f"Summarise the club's strengths, home/away split and notable rivalries."
    )


@server.prompt(description="Review a season of a competition.")
def season_review(competition: str = "brasileirao", season: int = 2019) -> str:
    return (
        f"Review the {season} {competition} season.\n"
        f"1. Call competition_standings for the table.\n"
        f"2. Call competition_stats for goals per match and home advantage.\n"
        f"3. Call biggest_wins for the standout results.\n"
        f"Write a short season report citing the numbers you retrieved."
    )


def annotate_tool_schemas(target: MCPServer = server) -> int:
    """Copy per-argument help from the tool layer into the JSON schemas.

    ``MCPServer`` derives each schema from the function signature, which gives
    types but no per-property ``description``.  The tool layer already
    documents every argument, so reuse it -- an LLM picking arguments benefits
    a lot from "'home', 'away' or 'any'" next to ``home_away``.

    Returns the number of properties annotated; degrades to a no-op if the SDK
    stops exposing its tool registry.
    """

    registry = getattr(target, "_tool_manager", None)
    tools = getattr(registry, "_tools", None)
    if not isinstance(tools, dict):  # pragma: no cover - SDK internals changed
        return 0
    annotated = 0
    for tool_name, tool_obj in tools.items():
        spec = TOOLS.get(tool_name)
        schema = getattr(tool_obj, "parameters", None)
        if spec is None or not isinstance(schema, dict):
            continue
        for argument, properties in schema.get("properties", {}).items():
            help_text = spec.parameters.get(argument)
            if help_text and "description" not in properties:
                properties["description"] = help_text
                annotated += 1
    return annotated


annotate_tool_schemas()


def main(transport: str = "stdio") -> None:
    """Entry point -- warm the graph, then serve."""

    load_knowledge_graph()
    server.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":  # pragma: no cover
    main()
