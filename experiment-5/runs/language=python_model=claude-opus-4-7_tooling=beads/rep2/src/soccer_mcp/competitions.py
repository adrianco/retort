"""Competition-level computations: standings, champions, relegation.

Standings are computed directly from match results because the source CSVs
don't ship pre-aggregated tables. The points calculation uses the standard
Brazilian football scoring: 3 for a win, 1 for a draw, 0 for a loss, with
goal difference and goals-for as tiebreakers. For 20-team Serie A seasons
(2006-onwards), the bottom four are flagged as relegated.
"""

from __future__ import annotations

import pandas as pd

from soccer_mcp.data import SoccerData, normalize_team_name


def standings(data: SoccerData, competition: str, season: int) -> list[dict]:
    """Compute the final table for a given competition + season."""
    df = data.matches
    df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    df = df[df["season"] == season]
    df = df.dropna(subset=["home_goal", "away_goal"])
    if df.empty:
        return []

    table: dict[str, dict] = {}
    aliases = data.team_aliases()

    def bump(team_norm: str, raw: str, gf: int, ga: int, result: str) -> None:
        entry = table.setdefault(
            team_norm,
            {"team": raw, "matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0},
        )
        entry["matches"] += 1
        entry["goals_for"] += gf
        entry["goals_against"] += ga
        if result == "W":
            entry["wins"] += 1
        elif result == "D":
            entry["draws"] += 1
        else:
            entry["losses"] += 1

    for _, row in df.iterrows():
        hg = int(row["home_goal"])
        ag = int(row["away_goal"])
        home_norm = row["home_team_norm"] or normalize_team_name(row["home_team"])
        away_norm = row["away_team_norm"] or normalize_team_name(row["away_team"])
        if hg > ag:
            home_res, away_res = "W", "L"
        elif hg < ag:
            home_res, away_res = "L", "W"
        else:
            home_res = away_res = "D"
        bump(home_norm, row["home_team"], hg, ag, home_res)
        bump(away_norm, row["away_team"], ag, hg, away_res)

    rows = []
    for norm, entry in table.items():
        display = entry["team"]
        if norm in aliases:
            # Prefer the shortest alias for display (no state suffix typically).
            display = sorted(aliases[norm], key=len)[0]
        points = entry["wins"] * 3 + entry["draws"]
        rows.append(
            {
                "team": display,
                "team_norm": norm,
                "matches": entry["matches"],
                "wins": entry["wins"],
                "draws": entry["draws"],
                "losses": entry["losses"],
                "goals_for": entry["goals_for"],
                "goals_against": entry["goals_against"],
                "goal_difference": entry["goals_for"] - entry["goals_against"],
                "points": points,
            }
        )

    rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]))
    for position, row in enumerate(rows, start=1):
        row["position"] = position
    return rows


def champion(data: SoccerData, competition: str, season: int) -> dict | None:
    """Top of the table for ``competition`` and ``season`` (or None)."""
    table = standings(data, competition, season)
    return table[0] if table else None


def relegated_teams(data: SoccerData, season: int, n: int = 4) -> list[dict]:
    """The bottom ``n`` of the Brasileirão (Serie A) table for ``season``."""
    table = standings(data, "Brasileirão", season)
    if not table:
        return []
    return table[-n:]


def libertadores_stages(data: SoccerData, season: int) -> dict[str, list[dict]]:
    """Group the Copa Libertadores matches in ``season`` by stage."""
    df = data.libertadores
    df = df[df["season"] == season]
    out: dict[str, list[dict]] = {}
    for _, row in df.iterrows():
        stage = (row["stage"] or "unknown").strip()
        out.setdefault(stage, []).append(
            {
                "date": row["date"].isoformat() if pd.notna(row["date"]) else None,
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "home_goal": int(row["home_goal"]) if pd.notna(row["home_goal"]) else None,
                "away_goal": int(row["away_goal"]) if pd.notna(row["away_goal"]) else None,
            }
        )
    return out
