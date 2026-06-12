"""
Context
=======
The MCP (Model Context Protocol) server. It exposes the Brazilian-soccer
knowledge base as a set of MCP tools an LLM can call to answer natural
language questions about matches, teams, players, competitions and stats.

Design: a thin adapter. Every tool delegates to ``SoccerTools`` (formatting)
which delegates to ``KnowledgeBase`` (querying). ``build_server`` is factored
out so tests can inject a small in-memory KnowledgeBase instead of loading the
full datasets. Running the module starts a stdio MCP server.

Run with:  python -m brazilian_soccer.server
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from .queries import KnowledgeBase
from .tools import SoccerTools


def build_server(kb: Optional[KnowledgeBase] = None) -> FastMCP:
    """Create a FastMCP server wired to *kb* (loads real data if None)."""
    if kb is None:
        kb = KnowledgeBase.load()
    tools = SoccerTools(kb)
    mcp = FastMCP("brazilian-soccer")

    @mcp.tool()
    def search_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        home: Optional[str] = None,
        away: Optional[str] = None,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 25,
    ) -> str:
        """Find football matches by team, opponent, venue, season, competition
        or date range (dates as YYYY-MM-DD). Returns a formatted match list."""
        return tools.search_matches(
            team=team, opponent=opponent, home=home, away=away, season=season,
            competition=competition, start_date=start_date, end_date=end_date,
            limit=limit,
        )

    @mcp.tool()
    def head_to_head(
        team_a: str,
        team_b: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> str:
        """Head-to-head record (wins/draws/goals) between two teams."""
        return tools.head_to_head(team_a, team_b, season=season, competition=competition)

    @mcp.tool()
    def team_record(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> str:
        """A team's win/loss/draw record and goals. ``venue`` may be 'home',
        'away' or omitted for overall."""
        return tools.team_record(team, season=season, competition=competition, venue=venue)

    @mcp.tool()
    def standings(season: int, competition: str = "Brasileirão", limit: int = 20) -> str:
        """League standings for a season, calculated from match results."""
        return tools.standings(season=season, competition=competition, limit=limit)

    @mcp.tool()
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 15,
    ) -> str:
        """Search FIFA players by name, nationality, club, position or minimum
        overall rating. Results are sorted by rating."""
        return tools.search_players(
            name=name, nationality=nationality, club=club,
            position=position, min_overall=min_overall, limit=limit,
        )

    @mcp.tool()
    def players_by_club(nationality: Optional[str] = None, limit: int = 15) -> str:
        """Player counts and average rating grouped by club."""
        return tools.players_by_club(nationality=nationality, limit=limit)

    @mcp.tool()
    def statistics(competition: Optional[str] = None, season: Optional[int] = None) -> str:
        """Aggregate stats: average goals per match and home win rate."""
        return tools.statistics(competition=competition, season=season)

    @mcp.tool()
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """The largest-margin victories in the data."""
        return tools.biggest_wins(competition=competition, season=season, limit=limit)

    @mcp.tool()
    def best_record(
        venue: str = "home",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 10,
        limit: int = 10,
    ) -> str:
        """Rank teams by home or away win-rate."""
        return tools.best_record(
            venue=venue, competition=competition, season=season,
            min_matches=min_matches, limit=limit,
        )

    @mcp.tool()
    def data_summary() -> str:
        """Summary of how many matches/players are loaded, by competition."""
        return tools.data_summary()

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
