"""MCP server exposing Brazilian soccer knowledge-graph tools."""
from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .data import get_data


mcp = FastMCP("brazilian-soccer")


def _df_to_records(df, limit: int | None = None) -> list[dict[str, Any]]:
    if limit is not None:
        df = df.head(limit)
    records = []
    for row in df.to_dict(orient="records"):
        clean = {}
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                clean[k] = v.isoformat()
            elif v is None or (isinstance(v, float) and v != v):
                clean[k] = None
            else:
                clean[k] = v
        records.append(clean)
    return records


@mcp.tool()
def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    season: int | None = None,
    competition: str | None = None,
    limit: int = 50,
) -> str:
    """Find matches by team, opponent, season, and/or competition."""
    df = get_data().find_matches(team, opponent, season, competition, limit=limit)
    cols = ["datetime", "tournament", "home_team", "home_goal",
            "away_goal", "away_team", "season", "round"]
    cols = [c for c in cols if c in df.columns]
    return json.dumps(_df_to_records(df[cols]), default=str)


@mcp.tool()
def head_to_head(team_a: str, team_b: str) -> str:
    """Return head-to-head record between two teams."""
    return json.dumps(get_data().head_to_head(team_a, team_b))


@mcp.tool()
def team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
) -> str:
    """Return aggregate stats (W/D/L, goals, points) for a team."""
    return json.dumps(
        get_data().team_stats(team, season, competition, home_only, away_only)
    )


@mcp.tool()
def standings(season: int, competition: str = "Brasileirão") -> str:
    """Compute a standings table for a season from match results."""
    df = get_data().standings(season, competition)
    return json.dumps(_df_to_records(df))


@mcp.tool()
def biggest_wins(limit: int = 10, competition: str | None = None) -> str:
    """Biggest victories by goal margin."""
    df = get_data().biggest_wins(limit=limit, competition=competition)
    cols = ["datetime", "tournament", "home_team", "home_goal",
            "away_goal", "away_team", "margin"]
    cols = [c for c in cols if c in df.columns]
    return json.dumps(_df_to_records(df[cols]), default=str)


@mcp.tool()
def average_goals(competition: str | None = None, season: int | None = None) -> str:
    """Average goals per match and home-win rate."""
    return json.dumps(get_data().average_goals(competition, season))


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
) -> str:
    """Search the FIFA player database."""
    df = get_data().search_players(name, nationality, club, position, min_overall, limit)
    return json.dumps(_df_to_records(df))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
