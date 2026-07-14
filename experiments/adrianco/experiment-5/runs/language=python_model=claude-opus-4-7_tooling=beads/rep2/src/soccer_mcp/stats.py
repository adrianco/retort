"""Aggregate statistics over the combined match table.

These are the "what's the average / which team is best at X" computations.
Each function returns plain dicts or lists so they can be ferried through the
MCP tool layer without further conversion. Pandas is used for the grouping
math; results are coerced back to Python types before returning.
"""

from __future__ import annotations

import pandas as pd

from soccer_mcp.data import SoccerData


def _scope(df: pd.DataFrame, competition: str | None, season: int | None) -> pd.DataFrame:
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    if season is not None:
        df = df[df["season"] == season]
    return df.dropna(subset=["home_goal", "away_goal"])


def goals_per_match(data: SoccerData, competition: str | None = None, season: int | None = None) -> dict:
    df = _scope(data.matches, competition, season)
    if df.empty:
        return {"competition": competition, "season": season, "matches": 0, "average_goals": 0.0}
    avg = float((df["home_goal"] + df["away_goal"]).mean())
    return {
        "competition": competition,
        "season": season,
        "matches": int(len(df)),
        "average_goals": round(avg, 3),
        "home_goals_avg": round(float(df["home_goal"].mean()), 3),
        "away_goals_avg": round(float(df["away_goal"].mean()), 3),
    }


def home_advantage(data: SoccerData, competition: str | None = None, season: int | None = None) -> dict:
    """Home-win/draw/away-win rates and home win percentage in scope."""
    df = _scope(data.matches, competition, season)
    if df.empty:
        return {"matches": 0}
    home_wins = int((df["home_goal"] > df["away_goal"]).sum())
    away_wins = int((df["home_goal"] < df["away_goal"]).sum())
    draws = int((df["home_goal"] == df["away_goal"]).sum())
    total = home_wins + away_wins + draws
    return {
        "competition": competition,
        "season": season,
        "matches": total,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / total, 4) if total else 0.0,
        "away_win_rate": round(away_wins / total, 4) if total else 0.0,
        "draw_rate": round(draws / total, 4) if total else 0.0,
    }


def best_home_record(
    data: SoccerData,
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 5,
    limit: int = 10,
) -> list[dict]:
    """Teams with the best home win-rate (minimum match threshold)."""
    df = _scope(data.matches, competition, season)
    if df.empty:
        return []
    grouped = df.groupby("home_team_norm").apply(
        lambda g: pd.Series(
            {
                "team": g["home_team"].iloc[0],
                "matches": len(g),
                "wins": int((g["home_goal"] > g["away_goal"]).sum()),
                "draws": int((g["home_goal"] == g["away_goal"]).sum()),
                "losses": int((g["home_goal"] < g["away_goal"]).sum()),
            }
        ),
        include_groups=False,
    )
    grouped = grouped[grouped["matches"] >= min_matches]
    grouped["win_rate"] = grouped["wins"] / grouped["matches"]
    grouped = grouped.sort_values("win_rate", ascending=False).head(limit)
    return [
        {
            "team": row["team"],
            "matches": int(row["matches"]),
            "wins": int(row["wins"]),
            "draws": int(row["draws"]),
            "losses": int(row["losses"]),
            "win_rate": round(float(row["win_rate"]), 4),
        }
        for _, row in grouped.iterrows()
    ]


def best_away_record(
    data: SoccerData,
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 5,
    limit: int = 10,
) -> list[dict]:
    """Teams with the best away win-rate (minimum match threshold)."""
    df = _scope(data.matches, competition, season)
    if df.empty:
        return []
    grouped = df.groupby("away_team_norm").apply(
        lambda g: pd.Series(
            {
                "team": g["away_team"].iloc[0],
                "matches": len(g),
                "wins": int((g["away_goal"] > g["home_goal"]).sum()),
                "draws": int((g["away_goal"] == g["home_goal"]).sum()),
                "losses": int((g["away_goal"] < g["home_goal"]).sum()),
            }
        ),
        include_groups=False,
    )
    grouped = grouped[grouped["matches"] >= min_matches]
    grouped["win_rate"] = grouped["wins"] / grouped["matches"]
    grouped = grouped.sort_values("win_rate", ascending=False).head(limit)
    return [
        {
            "team": row["team"],
            "matches": int(row["matches"]),
            "wins": int(row["wins"]),
            "draws": int(row["draws"]),
            "losses": int(row["losses"]),
            "win_rate": round(float(row["win_rate"]), 4),
        }
        for _, row in grouped.iterrows()
    ]


def season_comparison(data: SoccerData, season_a: int, season_b: int, competition: str | None = None) -> dict:
    """Compare per-season match counts, goals, and home advantage."""
    return {
        "season_a": goals_per_match(data, competition=competition, season=season_a)
        | home_advantage(data, competition=competition, season=season_a),
        "season_b": goals_per_match(data, competition=competition, season=season_b)
        | home_advantage(data, competition=competition, season=season_b),
    }
