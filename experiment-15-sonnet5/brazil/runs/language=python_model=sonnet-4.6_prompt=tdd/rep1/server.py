"""Brazilian Soccer MCP Server."""
from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from query_engine import QueryEngine


def create_server(data_dir: str = "data/kaggle") -> FastMCP:
    """Build and return a configured FastMCP server."""
    engine = QueryEngine(data_dir)
    engine.load()

    mcp = FastMCP("brazilian-soccer")

    @mcp.tool()
    def search_matches(
        team: str | None = None,
        home_team: str | None = None,
        away_team: str | None = None,
        team1: str | None = None,
        team2: str | None = None,
        season: int | None = None,
        competition: str | None = None,
        limit: int = 50,
    ) -> str:
        """Search Brazilian soccer matches by team, season, or competition.

        Args:
            team: Team name appearing as either home or away.
            home_team: Search only home team.
            away_team: Search only away team.
            team1: First team for head-to-head lookup.
            team2: Second team for head-to-head lookup.
            season: Four-digit year (e.g. 2019).
            competition: One of 'brasileirao', 'copa_brasil', 'libertadores',
                         'br_football', 'historical'.
            limit: Maximum results to return (default 50).
        """
        results = engine.search_matches(
            team=team,
            home_team=home_team,
            away_team=away_team,
            team1=team1,
            team2=team2,
            season=season,
            competition=competition,
            limit=limit,
        )
        # Remove internal raw fields from output
        for r in results:
            r.pop("home_team_raw", None)
            r.pop("away_team_raw", None)
        return json.dumps(results, ensure_ascii=False)

    @mcp.tool()
    def get_team_stats(
        team: str,
        season: int | None = None,
        competition: str | None = None,
        home_only: bool = False,
    ) -> str:
        """Get win/loss/draw statistics for a team.

        Args:
            team: Team name (partial match supported).
            season: Filter by year.
            competition: Filter by competition name.
            home_only: If true, only count home matches.
        """
        stats = engine.get_team_stats(
            team=team,
            season=season,
            competition=competition,
            home_only=home_only,
        )
        return json.dumps(stats, ensure_ascii=False)

    @mcp.tool()
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        sort_by: str | None = "Overall",
        limit: int = 20,
    ) -> str:
        """Search FIFA player database.

        Args:
            name: Player name (partial match, case-insensitive).
            nationality: Exact nationality string (e.g. 'Brazil').
            club: Club name (partial match).
            position: FIFA position code (e.g. 'GK', 'ST', 'CAM').
            sort_by: Column to sort by (default 'Overall').
            limit: Maximum results (default 20).
        """
        players = engine.search_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            sort_by=sort_by,
            limit=limit,
        )
        return json.dumps(players, ensure_ascii=False)

    @mcp.tool()
    def get_head_to_head(team1: str, team2: str) -> str:
        """Get head-to-head record between two teams across all competitions.

        Args:
            team1: First team name.
            team2: Second team name.
        """
        h2h = engine.get_head_to_head(team1, team2)
        # Keep only the last 20 matches in the response to limit size
        if len(h2h.get("matches", [])) > 20:
            h2h["matches"] = h2h["matches"][:20]
            h2h["matches_truncated"] = True
        for m in h2h.get("matches", []):
            m.pop("home_team_raw", None)
            m.pop("away_team_raw", None)
        return json.dumps(h2h, ensure_ascii=False)

    @mcp.tool()
    def get_standings(season: int, competition: str = "brasileirao") -> str:
        """Calculate league standings for a season.

        Args:
            season: Four-digit year (e.g. 2019).
            competition: Competition name (default 'brasileirao').
        """
        standings = engine.get_standings(season=season, competition=competition)
        return json.dumps(standings, ensure_ascii=False)

    @mcp.tool()
    def get_biggest_wins(
        competition: str | None = None,
        limit: int = 10,
    ) -> str:
        """Return the matches with the largest goal-difference margins.

        Args:
            competition: Filter by competition name (optional).
            limit: Maximum results (default 10).
        """
        results = engine.get_biggest_wins(competition=competition, limit=limit)
        for r in results:
            r.pop("home_team_raw", None)
            r.pop("away_team_raw", None)
        return json.dumps(results, ensure_ascii=False)

    @mcp.tool()
    def get_statistics(competition: str | None = None) -> str:
        """Return aggregate statistics: average goals, home win rate, top scorers.

        Args:
            competition: Filter by competition name (optional).
        """
        avg_goals = engine.get_average_goals(competition=competition)
        home_win_rate = engine.get_home_win_rate(competition=competition)
        top_scorers = engine.get_top_scoring_teams(competition=competition, limit=10)
        result: dict[str, Any] = {
            "average_goals_per_match": round(avg_goals, 3),
            "home_win_rate": round(home_win_rate, 3),
            "top_scoring_teams": top_scorers,
        }
        return json.dumps(result, ensure_ascii=False)

    return mcp


if __name__ == "__main__":
    server = create_server()
    server.run()
