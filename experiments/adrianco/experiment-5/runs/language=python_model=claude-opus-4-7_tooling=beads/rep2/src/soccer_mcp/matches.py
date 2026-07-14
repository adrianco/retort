"""Match-level queries against the combined match table.

Every function takes a loaded :class:`SoccerData` and returns plain Python
dicts/lists — never pandas objects — so callers (CLI, tests, MCP tool layer)
get something trivially JSON-serialisable. Team names from the user are
funnelled through :func:`normalize_team_name`; the canonical name returned in
results is whatever raw form appears in the underlying CSV, which is what a
human would expect to see.
"""

from __future__ import annotations

from datetime import date as _date_t
from typing import Iterable

import pandas as pd

from soccer_mcp.data import SoccerData, normalize_team_name


def _to_iso(value) -> str | None:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _match_dict(row: pd.Series) -> dict:
    return {
        "competition": row.get("competition"),
        "date": _to_iso(row.get("date")),
        "season": int(row["season"]) if pd.notna(row.get("season")) else None,
        "round": row.get("round") if pd.notna(row.get("round")) else None,
        "stage": row.get("stage") if pd.notna(row.get("stage")) else None,
        "home_team": row.get("home_team"),
        "away_team": row.get("away_team"),
        "home_goal": int(row["home_goal"]) if pd.notna(row.get("home_goal")) else None,
        "away_goal": int(row["away_goal"]) if pd.notna(row.get("away_goal")) else None,
        "arena": row.get("arena") if pd.notna(row.get("arena")) else None,
    }


def _filter_competition(df: pd.DataFrame, competition: str | None) -> pd.DataFrame:
    if not competition:
        return df
    target = competition.strip().lower()
    return df[df["competition"].str.lower().str.contains(target, na=False)]


def _filter_season(df: pd.DataFrame, season: int | None) -> pd.DataFrame:
    if season is None:
        return df
    return df[df["season"] == season]


def _filter_date_range(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    if start is None and end is None:
        return df
    out = df
    if start:
        out = out[out["date"] >= pd.to_datetime(start)]
    if end:
        out = out[out["date"] <= pd.to_datetime(end)]
    return out


def find_matches(
    data: SoccerData,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    limit: int | None = 100,
) -> list[dict]:
    """Return matches matching all given filters, sorted newest-first."""
    df = data.matches
    df = _filter_competition(df, competition)
    df = _filter_season(df, season)
    df = _filter_date_range(df, start_date, end_date)

    if team:
        t_norm = normalize_team_name(team)
        if home_only:
            mask = df["home_team_norm"] == t_norm
        elif away_only:
            mask = df["away_team_norm"] == t_norm
        else:
            mask = (df["home_team_norm"] == t_norm) | (df["away_team_norm"] == t_norm)
        df = df[mask]
    if opponent:
        o_norm = normalize_team_name(opponent)
        df = df[(df["home_team_norm"] == o_norm) | (df["away_team_norm"] == o_norm)]
    if team and opponent:
        # When both are given, require the row to mention both teams.
        t_norm = normalize_team_name(team)
        o_norm = normalize_team_name(opponent)
        df = df[
            ((df["home_team_norm"] == t_norm) & (df["away_team_norm"] == o_norm))
            | ((df["home_team_norm"] == o_norm) & (df["away_team_norm"] == t_norm))
        ]

    df = df.sort_values("date", ascending=False, na_position="last")
    if limit is not None:
        df = df.head(limit)
    return [_match_dict(row) for _, row in df.iterrows()]


def head_to_head(data: SoccerData, team_a: str, team_b: str, competition: str | None = None) -> dict:
    """Return wins/losses/draws and the full match list between two teams."""
    matches = find_matches(data, team=team_a, opponent=team_b, competition=competition, limit=None)
    a_norm = normalize_team_name(team_a)
    a_wins = b_wins = draws = goals_a = goals_b = 0
    counted = 0
    for m in matches:
        if m["home_goal"] is None or m["away_goal"] is None:
            continue
        counted += 1
        home_is_a = normalize_team_name(m["home_team"]) == a_norm
        if home_is_a:
            goals_a += m["home_goal"]
            goals_b += m["away_goal"]
            if m["home_goal"] > m["away_goal"]:
                a_wins += 1
            elif m["home_goal"] < m["away_goal"]:
                b_wins += 1
            else:
                draws += 1
        else:
            goals_a += m["away_goal"]
            goals_b += m["home_goal"]
            if m["away_goal"] > m["home_goal"]:
                a_wins += 1
            elif m["away_goal"] < m["home_goal"]:
                b_wins += 1
            else:
                draws += 1
    return {
        "team_a": team_a,
        "team_b": team_b,
        "matches_played": counted,
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "goals_team_a": goals_a,
        "goals_team_b": goals_b,
        "matches": matches,
    }


def last_match_between(data: SoccerData, team_a: str, team_b: str) -> dict | None:
    """Most recent match between the two teams across every competition."""
    matches = find_matches(data, team=team_a, opponent=team_b, limit=1)
    return matches[0] if matches else None


def biggest_wins(
    data: SoccerData, competition: str | None = None, limit: int = 10, min_margin: int = 1
) -> list[dict]:
    """Largest goal-difference results, optionally restricted to a competition."""
    df = _filter_competition(data.matches, competition).copy()
    df = df.dropna(subset=["home_goal", "away_goal"])
    df["margin"] = (df["home_goal"].astype(int) - df["away_goal"].astype(int)).abs()
    df = df[df["margin"] >= min_margin]
    df = df.sort_values(["margin", "date"], ascending=[False, False]).head(limit)
    return [_match_dict(row) | {"margin": int(row["margin"])} for _, row in df.iterrows()]
