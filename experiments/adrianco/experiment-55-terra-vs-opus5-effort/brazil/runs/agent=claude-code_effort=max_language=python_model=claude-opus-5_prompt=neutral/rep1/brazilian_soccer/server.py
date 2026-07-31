"""The MCP server: 17 tools over the Brazilian soccer knowledge graph.

Context
-------
Each tool is a thin wrapper: resolve arguments -> call
:mod:`brazilian_soccer.queries` -> render with
:mod:`brazilian_soccer.formatting`.  Tools return text because that is what a
model consumes; ``graph_neighbours`` additionally returns raw JSON for clients
that want to walk the graph themselves.

The graph is built lazily on the first tool call (roughly one second for all six
CSVs) and then shared, so start-up is instant and every subsequent query is an
in-memory lookup -- comfortably inside the specification's 2s/5s budgets.

Run it with ``python -m brazilian_soccer.server`` (stdio transport) or point an
MCP client at that command.  ``--data-dir`` overrides the CSV location, as does
the ``BRAZILIAN_SOCCER_DATA`` environment variable.

The SDK class moved in mcp 2.0 (``mcp.server.MCPServer``) from where it lived in
1.x (``mcp.server.fastmcp.FastMCP``); both expose the same ``.tool()``/``.run()``
surface, so the import below accepts either.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from . import formatting, queries
from .graph import KnowledgeGraph

try:  # mcp >= 2.0
    from mcp.server import MCPServer as _ServerClass
except ImportError:  # pragma: no cover - mcp 1.x fallback
    from mcp.server.fastmcp import FastMCP as _ServerClass

__all__ = ["build_server", "GraphProvider", "main", "server"]

SERVER_NAME = "brazilian-soccer"

INSTRUCTIONS = """
Knowledge graph over six Kaggle datasets of Brazilian football: 16 700+ merged
matches (Brasileirão Série A 2003-2023, Série B/C 2014-2023, Copa do Brasil
2012-2023, Copa Libertadores 2013-2022), 360+ clubs and 18 200 FIFA players.

Use `search_teams` when a club name is ambiguous; every tool accepts loose
spellings ("Palmeiras-SP", "Atletico Mineiro", "Timão", "Fla").  League tables
are calculated from match results - the files contain no goalscorers, cards or
lineups, so questions about individual scorers cannot be answered.
""".strip()


class GraphProvider:
    """Lazily builds and caches the knowledge graph for the tools."""

    def __init__(self, graph: KnowledgeGraph | None = None, data_dir: Path | str | None = None):
        self._graph = graph
        self._data_dir = data_dir

    def __call__(self) -> KnowledgeGraph:
        if self._graph is None:
            self._graph = KnowledgeGraph.load(self._data_dir)
        return self._graph


def build_server(
    graph: KnowledgeGraph | None = None,
    data_dir: Path | str | None = None,
    name: str = SERVER_NAME,
) -> Any:
    """Create the MCP server, optionally with a pre-built *graph* (used in tests)."""
    provider = GraphProvider(graph=graph, data_dir=data_dir)
    server = _ServerClass(name=name, instructions=INSTRUCTIONS)

    def _render(kind: str, result: dict[str, Any]) -> str:
        return formatting.format_result(kind, result)

    # -- 1. Discovery ----------------------------------------------------
    @server.tool()
    def dataset_overview() -> str:
        """Summarise what the knowledge graph contains.

        Competitions, seasons, match/team/player counts, date range and which
        clubs are linked between the player and match datasets.  Call this first
        when you are unsure what can be answered.
        """
        return _render("overview", queries.dataset_overview(provider()))

    @server.tool()
    def search_teams(query: str, limit: int = 10) -> str:
        """Resolve a club name and show every spelling that maps onto it.

        Args:
            query: Any spelling, nickname or partial name ("Fla", "Atletico
                Mineiro", "Palmeiras-SP", "Sport").
            limit: Maximum number of candidate clubs to list.
        """
        return _render("search_teams", queries.search_teams(provider(), query, limit=limit))

    # -- 2. Match queries ------------------------------------------------
    @server.tool()
    def find_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        home_away: str = "any",
        stage: str | None = None,
        limit: int = 20,
    ) -> str:
        """Find matches by team, opponent, competition, season or date range.

        Args:
            team: Club to search for (home or away unless `home_away` is set).
            opponent: Restrict to matches against this club.
            competition: "Serie A", "Serie B", "Serie C", "Copa do Brasil" or
                "Libertadores".
            season: Season year, e.g. 2023.
            date_from: Earliest date ("2023-01-01" or "01/01/2023").
            date_to: Latest date.
            home_away: "home", "away" or "any" (relative to `team`).
            stage: Round or stage filter, e.g. "Final", "Semifinals", "Round 22".
            limit: Maximum matches to return, newest first.
        """
        return _render(
            "matches",
            queries.find_matches(
                provider(),
                team=team,
                opponent=opponent,
                competition=competition,
                season=season,
                date_from=date_from,
                date_to=date_to,
                home_away=home_away,
                stage=stage,
                limit=limit,
            ),
        )

    @server.tool()
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> str:
        """Compare two clubs: wins, draws, goals, biggest wins and recent meetings.

        Args:
            team_a: First club.
            team_b: Second club.
            competition: Optional competition filter.
            season: Optional season filter.
            limit: How many recent meetings to list.
        """
        return _render(
            "head_to_head",
            queries.head_to_head(
                provider(), team_a, team_b, competition=competition, season=season, limit=limit
            ),
        )

    @server.tool()
    def biggest_wins(
        competition: str | None = None,
        season: int | None = None,
        team: str | None = None,
        limit: int = 10,
    ) -> str:
        """List the largest winning margins in the dataset.

        Args:
            competition: Optional competition filter.
            season: Optional season filter.
            team: Only wins by this club.
            limit: How many matches to return.
        """
        return _render(
            "biggest_wins",
            queries.biggest_wins(
                provider(), competition=competition, season=season, team=team, limit=limit
            ),
        )

    @server.tool()
    def derbies(
        season: int | None = None,
        competition: str | None = None,
        team: str | None = None,
        limit: int = 30,
    ) -> str:
        """Find matches between traditional rivals (Fla-Flu, Gre-Nal, Derby Paulista...).

        Args:
            season: Optional season filter, e.g. 2023.
            competition: Optional competition filter.
            team: Only derbies involving this club.
            limit: Maximum matches to list.
        """
        return _render(
            "derbies",
            queries.derbies(
                provider(), season=season, competition=competition, team=team, limit=limit
            ),
        )

    # -- 3. Team queries -------------------------------------------------
    @server.tool()
    def team_stats(
        team: str,
        season: int | None = None,
        competition: str | None = None,
        home_away: str = "any",
    ) -> str:
        """Win/draw/loss record, goals, clean sheets and form for one club.

        Args:
            team: Club name.
            season: Optional season year.
            competition: Optional competition filter.
            home_away: "home", "away" or "any".
        """
        return _render(
            "team_stats",
            queries.team_stats(
                provider(), team, season=season, competition=competition, home_away=home_away
            ),
        )

    @server.tool()
    def team_profile(team: str) -> str:
        """Everything known about a club: competitions, seasons, titles, rivals, squad.

        Args:
            team: Club name.
        """
        return _render("team_profile", queries.team_profile(provider(), team))

    @server.tool()
    def team_rankings(
        metric: str = "points",
        competition: str | None = None,
        season: int | None = None,
        home_away: str = "any",
        limit: int = 10,
        min_matches: int | None = None,
        ascending: bool = False,
    ) -> str:
        """Rank clubs by a metric - best home record, most goals, best defence...

        Args:
            metric: points, wins, draws, losses, win_rate, points_per_game,
                goals_for, goals_against, goal_difference or matches.
            competition: Optional competition filter.
            season: Optional season filter.
            home_away: "home", "away" or "any" - use "home" for home records.
            limit: How many clubs to return.
            min_matches: Minimum matches to qualify (defaults to a quarter of the
                busiest club's match count in the selection).
            ascending: True to rank smallest first (e.g. fewest goals conceded).
        """
        return _render(
            "rankings",
            queries.team_rankings(
                provider(),
                metric=metric,
                competition=competition,
                season=season,
                home_away=home_away,
                limit=limit,
                min_matches=min_matches,
                ascending=ascending,
            ),
        )

    # -- 4. Player queries -----------------------------------------------
    @server.tool()
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_age: int | None = None,
        sort_by: str = "overall",
        limit: int = 20,
    ) -> str:
        """Search the FIFA player database.

        Args:
            name: Part of a player name (accent insensitive).
            nationality: Country, e.g. "Brazil".
            club: Club name; Brazilian clubs are matched to the match data.
            position: One or more positions, e.g. "ST" or "ST,CF,LW".
            min_overall: Minimum FIFA overall rating.
            max_age: Maximum age.
            sort_by: overall, potential, age, value or name.
            limit: How many players to return.
        """
        return _render(
            "players",
            queries.search_players(
                provider(),
                name=name,
                nationality=nationality,
                club=club,
                position=position,
                min_overall=min_overall,
                max_age=max_age,
                sort_by=sort_by,
                limit=limit,
            ),
        )

    @server.tool()
    def player_profile(name: str) -> str:
        """Full attributes for one player: rating, club, value, best skills.

        Args:
            name: Player name or part of it, e.g. "Gabriel Barbosa".
        """
        return _render("player_profile", queries.player_profile(provider(), name))

    @server.tool()
    def team_squad(team: str, limit: int = 30) -> str:
        """FIFA squad of a club joined to its match record (cross-dataset query).

        Args:
            team: Club name.
            limit: How many players to list.
        """
        return _render("team_squad", queries.team_squad(provider(), team, limit=limit))

    # -- 5. Competition queries ------------------------------------------
    @server.tool()
    def standings(competition: str, season: int) -> str:
        """League table calculated from results, with champion and relegation.

        Args:
            competition: "Serie A", "Serie B" or "Serie C".
            season: Season year, e.g. 2019.
        """
        return _render("standings", queries.standings(provider(), competition, season))

    @server.tool()
    def knockout_bracket(competition: str, season: int) -> str:
        """Stage-by-stage bracket for a cup season, with two-legged ties aggregated.

        Args:
            competition: "Copa do Brasil" or "Libertadores".
            season: Season year, e.g. 2018.
        """
        return _render("bracket", queries.knockout_bracket(provider(), competition, season))

    @server.tool()
    def competition_stats(competition: str | None = None, season: int | None = None) -> str:
        """Aggregate stats: goals per match, home advantage, biggest wins, top scoring teams.

        Args:
            competition: Optional competition; omit for all competitions.
            season: Optional season year.
        """
        return _render(
            "competition_stats",
            queries.competition_stats(provider(), competition=competition, season=season),
        )

    @server.tool()
    def compare_seasons(competition: str, seasons: list[int]) -> str:
        """Compare two or more seasons of the same competition.

        Args:
            competition: Competition name.
            seasons: Season years, e.g. [2018, 2019].
        """
        return _render(
            "compare_seasons", queries.compare_seasons(provider(), competition, seasons)
        )

    # -- 6. Raw graph access ---------------------------------------------
    @server.tool()
    def graph_neighbours(node_id: str, relation: str | None = None) -> str:
        """Walk the knowledge graph from a node id, returning JSON.

        Node ids are namespaced: `team:flamengo`, `match:serie-a:2019:flamengo:santos`,
        `player:158023`, `competition:serie-a`, `season:2019`, `venue:Maracanã`,
        `state:RJ`, `country:Brazil`.

        Args:
            node_id: Namespaced node id.
            relation: Optional relation filter such as played_home, played_away,
                competed_in, squad, plays_for, part_of, won_by, based_in.
        """
        graph = provider()
        node = graph.node(node_id)
        if node is None:
            return json.dumps({"error": f"Unknown node {node_id!r}"}, ensure_ascii=False)
        edges = graph.neighbours(node_id, relation)
        payload = {
            "node": node,
            "relations": {name: values[:50] for name, values in edges.items()},
            "counts": {name: len(values) for name, values in edges.items()},
        }
        return json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    return server


#: Module level instance so ``python -m brazilian_soccer.server`` and MCP client
#: configs can point at one object.  The graph itself is still loaded lazily.
server = build_server()


def main(argv: list[str] | None = None) -> None:
    """Entry point for ``python -m brazilian_soccer.server``."""
    parser = argparse.ArgumentParser(description="Brazilian soccer MCP server")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Directory holding the Kaggle CSVs (default: <repo>/data/kaggle)",
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="MCP transport to serve on (default: stdio)",
    )
    parser.add_argument(
        "--preload",
        action="store_true",
        help="Build the knowledge graph before serving instead of on first call",
    )
    args = parser.parse_args(argv)

    graph = KnowledgeGraph.load(args.data_dir) if args.preload else None
    if graph is not None or args.data_dir:
        instance = build_server(graph=graph, data_dir=args.data_dir)
    else:
        instance = server
    instance.run(args.transport)


if __name__ == "__main__":  # pragma: no cover
    main()
