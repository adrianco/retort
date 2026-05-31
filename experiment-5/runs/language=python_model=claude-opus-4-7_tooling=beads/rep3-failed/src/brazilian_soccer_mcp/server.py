"""MCP server exposing the Brazilian soccer knowledge graph as tools.

Run as a stdio MCP server::

    python -m brazilian_soccer_mcp.server

Each query category in TASK.md maps to one or more tools. Tools return
JSON-friendly dicts so the calling LLM gets structured data it can
summarize.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from brazilian_soccer_mcp.knowledge import SoccerKnowledge, display_matches


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert a DataFrame to a list of JSON-friendly dicts."""
    if df is None or df.empty:
        return []
    out = df.copy()
    # Convert timestamps to ISO strings
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d").fillna("")
    # Replace remaining NaN with None
    out = out.astype(object).where(pd.notna(out), None)
    return out.to_dict(orient="records")


def build_server(knowledge: SoccerKnowledge):
    """Wire all tools onto a FastMCP server bound to ``knowledge``."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("brazilian-soccer")

    # ------ Match queries -------------------------------------------------
    @mcp.tool(description="Find matches matching filters (team, opponent, competition, season, date range). Returns a list of matches.")
    def find_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        home_only: bool = False,
        away_only: bool = False,
        limit: int = 50,
    ) -> dict:
        df = knowledge.find_matches(
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            home_only=home_only,
            away_only=away_only,
            limit=limit,
        )
        return {
            "count": len(df),
            "matches": _df_to_records(display_matches(df)),
        }

    @mcp.tool(description="Aggregate head-to-head record between two teams across all competitions (or one).")
    def head_to_head(team_a: str, team_b: str, competition: Optional[str] = None) -> dict:
        return knowledge.head_to_head(team_a, team_b, competition=competition)

    # ------ Team queries --------------------------------------------------
    @mcp.tool(description="Aggregate W/D/L and goals for a team, optionally filtered to a season and competition.")
    def team_stats(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        home_only: bool = False,
        away_only: bool = False,
    ) -> dict:
        return knowledge.team_stats(
            team,
            season=season,
            competition=competition,
            home_only=home_only,
            away_only=away_only,
        )

    @mcp.tool(description="List the seasons in which a team has match data.")
    def team_seasons(team: str) -> dict:
        return {"team": team, "seasons": knowledge.team_seasons(team)}

    @mcp.tool(description="List the competitions a team has appeared in.")
    def team_competitions(team: str) -> dict:
        return {"team": team, "competitions": knowledge.team_competitions(team)}

    # ------ Player queries ------------------------------------------------
    @mcp.tool(description="Search FIFA players by name, nationality, club, position, or rating range.")
    def find_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        limit: int = 25,
    ) -> dict:
        df = knowledge.find_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            max_overall=max_overall,
            limit=limit,
        )
        keep = [c for c in [
            "name", "age", "nationality", "overall", "potential",
            "club", "position", "jersey_number", "preferred_foot", "value",
        ] if c in df.columns]
        return {
            "count": len(df),
            "players": _df_to_records(df[keep]) if not df.empty else [],
        }

    @mcp.tool(description="Top Brazilian players by FIFA overall rating.")
    def top_brazilian_players(limit: int = 10) -> dict:
        df = knowledge.top_brazilian_players(limit=limit)
        keep = [c for c in [
            "name", "overall", "potential", "position", "club", "age"
        ] if c in df.columns]
        return {"count": len(df), "players": _df_to_records(df[keep])}

    # ------ Competition queries ------------------------------------------
    @mcp.tool(description="Compute final standings for a competition season from match results.")
    def season_standings(season: int, competition: str = "Brasileirão Série A") -> dict:
        df = knowledge.season_standings(season=season, competition=competition)
        return {
            "season": season,
            "competition": competition,
            "rows": _df_to_records(df),
        }

    @mcp.tool(description="Return the rank-1 team for a given season and competition.")
    def champion(season: int, competition: str = "Brasileirão Série A") -> dict:
        result = knowledge.champion(season=season, competition=competition)
        return {"champion": result}

    @mcp.tool(description="List all competitions present in the dataset.")
    def competitions() -> dict:
        return {"competitions": knowledge.data.competitions}

    @mcp.tool(description="List all seasons present in the dataset.")
    def seasons() -> dict:
        return {"seasons": knowledge.data.seasons}

    # ------ Statistical analysis -----------------------------------------
    @mcp.tool(description="Average goals per match and home/away/draw rates, optionally filtered.")
    def average_goals(
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        return knowledge.average_goals(competition=competition, season=season)

    @mcp.tool(description="Biggest victories (by goal margin) optionally filtered to a season/competition.")
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> dict:
        df = knowledge.biggest_wins(competition=competition, season=season, limit=limit)
        return {
            "count": len(df),
            "matches": _df_to_records(display_matches(df).assign(
                margin=(df["home_goal"].astype(int) - df["away_goal"].astype(int)).abs()
            )) if not df.empty else [],
        }

    @mcp.tool(description="Teams with the best home record in a season/competition.")
    def best_home_record(
        season: Optional[int] = None,
        competition: str = "Brasileirão Série A",
        min_matches: int = 5,
        limit: int = 5,
    ) -> dict:
        df = knowledge.best_home_record(
            season=season, competition=competition,
            min_matches=min_matches, limit=limit,
        )
        return {"count": len(df), "rows": _df_to_records(df)}

    @mcp.tool(description="Teams with the best away record in a season/competition.")
    def best_away_record(
        season: Optional[int] = None,
        competition: str = "Brasileirão Série A",
        min_matches: int = 5,
        limit: int = 5,
    ) -> dict:
        df = knowledge.best_away_record(
            season=season, competition=competition,
            min_matches=min_matches, limit=limit,
        )
        return {"count": len(df), "rows": _df_to_records(df)}

    @mcp.tool(description="Top goal-scoring teams in a season/competition.")
    def top_scoring_teams(
        season: int,
        competition: str = "Brasileirão Série A",
        limit: int = 5,
    ) -> dict:
        df = knowledge.top_scorers_by_team(
            season=season, competition=competition, limit=limit
        )
        return {"count": len(df), "rows": _df_to_records(df)}

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("SOCCER_DATA_DIR", "data/kaggle"),
        help="Path to the Kaggle data directory",
    )
    args = parser.parse_args()
    knowledge = SoccerKnowledge.from_dir(Path(args.data_dir))
    mcp = build_server(knowledge)
    mcp.run()


if __name__ == "__main__":
    main()
