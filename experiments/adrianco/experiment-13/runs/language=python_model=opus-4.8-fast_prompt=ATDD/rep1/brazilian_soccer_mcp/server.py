"""
Context
=======
The MCP tool surface for the Brazilian Soccer knowledge base.

This module is the *public interface* of the system: it exposes the query engine
(``KnowledgeBase``) as MCP tools that an LLM client invokes by name. Tools map
one-to-one onto the required capability categories in the spec:

  * find_matches          -> Match Queries
  * get_team_record       -> Team Queries
  * head_to_head          -> Team / Statistical (head-to-head)
  * search_players        -> Player Queries
  * get_standings         -> Competition Queries
  * get_competition_stats -> Statistical Analysis

``create_server(data_dir)`` builds a server bound to a specific data directory,
which is how the acceptance tests serve a small controlled dataset. The
``main()`` entry point runs over stdio using ``BRZ_SOCCER_DATA_DIR`` (default
``data/kaggle``) so the server can be wired into a real MCP client.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .knowledge_base import KnowledgeBase

DEFAULT_DATA_DIR = "data/kaggle"


def create_server(data_dir: str) -> FastMCP:
    kb = KnowledgeBase.from_directory(data_dir)
    mcp = FastMCP("brazilian-soccer")

    @mcp.tool()
    def find_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        home_away: Optional[str] = None,
    ) -> dict:
        """Find matches by team, opponent, competition, season or date range.

        Args:
            team: A team name (any spelling; suffixes/accents optional).
            opponent: Restrict to matches against this other team.
            competition: e.g. "Brasileirão", "Copa do Brasil", "Libertadores".
            season: Year of the season.
            start_date: Inclusive ISO date "YYYY-MM-DD".
            end_date: Inclusive ISO date "YYYY-MM-DD".
            home_away: "home" or "away" relative to ``team``.

        Returns matches plus a head-to-head summary when both teams are given.
        """
        matches = kb.find_matches(team, opponent, competition, season,
                                  start_date, end_date, home_away)
        h2h = None
        if team and opponent:
            h2h = kb.head_to_head(team, opponent, competition, season)
            h2h = {k: h2h[k] for k in
                   ("team1", "team2", "team1_wins", "team2_wins", "draws",
                    "total_matches")}
        return {
            "count": len(matches),
            "matches": [m.as_dict() for m in matches],
            "head_to_head": h2h,
        }

    @mcp.tool()
    def get_team_record(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        home_away: Optional[str] = None,
    ) -> dict:
        """Get a team's win/draw/loss record, goals and win rate.

        Args:
            team: The team name (required).
            season: Optional year filter.
            competition: Optional competition filter.
            home_away: "home" or "away" to restrict to that venue.
        """
        if not team or not team.strip():
            raise ValueError("A 'team' name is required.")
        return kb.team_record(team, season, competition, home_away)

    @mcp.tool()
    def head_to_head(
        team1: str,
        team2: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        """Compare two teams head-to-head: meetings and win tallies.

        Args:
            team1: First team.
            team2: Second team.
            competition: Optional competition filter.
            season: Optional season filter.
        """
        if not team1 or not team1.strip() or not team2 or not team2.strip():
            raise ValueError("Both 'team1' and 'team2' are required.")
        return kb.head_to_head(team1, team2, competition, season)

    @mcp.tool()
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 25,
    ) -> dict:
        """Search FIFA players by name, nationality, club, position or rating.

        Results are sorted by FIFA overall rating (highest first).

        Args:
            name: Substring of the player's name.
            nationality: e.g. "Brazil".
            club: Club name (any spelling).
            position: e.g. "ST", "GK".
            min_overall: Minimum FIFA overall rating.
            limit: Maximum number of players to return.
        """
        players = kb.search_players(name, nationality, club, position,
                                    min_overall, limit)
        return {"count": len(players), "players": [p.as_dict() for p in players]}

    @mcp.tool()
    def get_standings(season: int, competition: str = "Brasileirão") -> dict:
        """Calculate a league table for a season from the match results.

        Args:
            season: The year of the season.
            competition: League competition (default "Brasileirão").

        Points are 3 for a win, 1 for a draw; ranked by points then goal
        difference then goals scored.
        """
        return kb.standings(season, competition)

    @mcp.tool()
    def get_competition_stats(
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        """Aggregate statistics: goals per match, home/away win rates, biggest wins.

        Args:
            competition: Optional competition filter.
            season: Optional season filter.
        """
        return kb.competition_stats(competition, season)

    return mcp


def main() -> None:
    data_dir = os.environ.get("BRZ_SOCCER_DATA_DIR", DEFAULT_DATA_DIR)
    server = create_server(str(Path(data_dir)))
    server.run()


if __name__ == "__main__":
    main()
