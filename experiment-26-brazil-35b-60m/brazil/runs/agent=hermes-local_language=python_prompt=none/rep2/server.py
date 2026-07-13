"""Brazilian Soccer MCP Server.

Exposes tools for querying Brazilian soccer match and player data via the
Model Context Protocol (MCP) using FastMCP.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd
from mcp.server.fastmcp import FastMCP

from data_loader import (
    DATA_DIR,
    load_all_data,
    normalize_team_name,
    is_brazilian_club,
)

# ---------------------------------------------------------------------------
# Initialise MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="Brazilian Soccer MCP",
    instructions=(
        "Knowledge graph interface for Brazilian soccer data. "
        "Query matches, teams, players, competitions, and statistics."
    ),
)

# ---------------------------------------------------------------------------
# In-memory data store (loaded once on first tool call)
# ---------------------------------------------------------------------------

_data_cache: dict | None = None


def _get_data() -> dict:
    """Load data on first call, then return cached copy."""
    global _data_cache
    if _data_cache is None:
        _data_cache = load_all_data()
    return _data_cache


def _normalise_goals(value) -> int:
    """Convert goals to int, handling float, string, and dash representations."""
    if value is None:
        return 0
    if isinstance(value, float) and pd.isna(value):
        return 0
    s = str(value).strip()
    if s == "" or s == "-" or s.lower() == "nan":
        return 0
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Tool: search_matches
# ---------------------------------------------------------------------------

@mcp.tool()
def search_matches(
    team: str | None = None,
    competition: str | None = None,
    season: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    home_or_away: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Search matches by team, competition, season, or date range.

    Args:
        team: Team name to search (normalized).
        competition: Competition name (e.g. 'Brasileirao', 'Copa do Brasil').
        season: Season year.
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).
        home_or_away: 'home', 'away', or None for either side.
        limit: Maximum results to return.
    """
    data = _get_data()

    results: list[dict] = []
    norm_team = normalize_team_name(team) if team else None

    for source_name, df in data.items():
        if source_name == "players":
            continue

        # Filter by competition
        if competition:
            comp_match = [
                c for c in df["competition"].unique()
                if competition.lower() in c.lower()
            ]
            if not comp_match:
                continue
            df = df[df["competition"].isin(comp_match)]

        # Filter by date range
        if date_from or date_to:
            date_col = None
            for col in ["datetime", "date"]:
                if col in df.columns:
                    date_col = col
                    break
            if date_col:
                dates = pd.to_datetime(df[date_col], errors="coerce")
                date_mask = dates.notna()
                if date_from:
                    date_mask = date_mask & (dates >= pd.to_datetime(date_from))
                if date_to:
                    date_mask = date_mask & (dates <= pd.to_datetime(date_to))
                df = df[date_mask]

        # Filter by season
        if season:
            for col in ["season", "Ano"]:
                if col in df.columns:
                    df = df[df[col].astype(str).str.startswith(str(season))]
                    break

        # Filter by team
        if norm_team:
            team_filter = pd.Series([False] * len(df), index=df.index)
            for home_col, away_col in [
                ("home_team", "away_team"),
                ("Equipe_mandante", "Equipe_visitante"),
            ]:
                if home_col in df.columns and away_col in df.columns:
                    h_match = df[home_col].apply(normalize_team_name) == norm_team
                    a_match = df[away_col].apply(normalize_team_name) == norm_team
                    team_filter = team_filter | h_match | a_match
                    break
            if home_or_away == "home":
                for col in ["home_team", "Equipe_mandante"]:
                    if col in df.columns:
                        team_filter = team_filter & (
                            df[col].apply(normalize_team_name) == norm_team
                        )
                        break
            elif home_or_away == "away":
                for col in ["away_team", "Equipe_visitante"]:
                    if col in df.columns:
                        team_filter = team_filter & (
                            df[col].apply(normalize_team_name) == norm_team
                        )
                        break
            df = df[team_filter]

        if df.empty:
            continue

        # Build result rows
        for _, row in df.head(limit).iterrows():
            match: dict = {"source": source_name}

            date_val = ""
            for date_col in ["datetime", "date"]:
                if date_col in row and pd.notna(row.get(date_col)):
                    date_val = str(row[date_col])
                    break

            if source_name == "historic":
                match["date"] = date_val
                match["home_team"] = str(row.get("Equipe_mandante", ""))
                match["away_team"] = str(row.get("Equipe_visitante", ""))
                match["home_goals"] = _normalise_goals(row.get("Gols_mandante"))
                match["away_goals"] = _normalise_goals(row.get("Gols_visitante"))
                match["competition"] = str(row.get("competition", ""))
                match["season"] = int(row.get("Ano", 0)) if pd.notna(row.get("Ano")) else None
                match["round"] = int(row.get("Rodada", 0)) if pd.notna(row.get("Rodada")) else None
            elif source_name == "extended_stats":
                match["date"] = date_val
                match["home_team"] = str(row.get("home", ""))
                match["away_team"] = str(row.get("away", ""))
                match["home_goals"] = _normalise_goals(row.get("home_goal"))
                match["away_goals"] = _normalise_goals(row.get("away_goal"))
                match["competition"] = str(row.get("competition", ""))
            else:
                match["datetime"] = date_val
                match["home_team"] = str(row.get("home_team", ""))
                match["away_team"] = str(row.get("away_team", ""))
                match["home_goals"] = _normalise_goals(row.get("home_goal"))
                match["away_goals"] = _normalise_goals(row.get("away_goal"))
                match["competition"] = str(row.get("competition", ""))
                if "season" in row and pd.notna(row.get("season")):
                    match["season"] = int(row["season"])
                if "round" in row and pd.notna(row.get("round")):
                    match["round"] = int(row["round"])
                if "stage" in row and pd.notna(row.get("stage")):
                    match["stage"] = str(row["stage"])

            results.append(match)

    return results[:limit]


# ---------------------------------------------------------------------------
# Tool: get_team_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_team_stats(
    team: str,
    season: str | None = None,
    competition: str | None = None,
) -> dict:
    """Get team statistics: wins, draws, losses, goals.

    Args:
        team: Team name.
        season: Optional season year filter.
        competition: Optional competition filter.
    """
    data = _get_data()
    norm_team = normalize_team_name(team)

    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0
    match_count = 0

    for source_name, df in data.items():
        if source_name == "players":
            continue

        # Competition filter
        if competition:
            comp_match = [
                c for c in df["competition"].unique()
                if competition.lower() in c.lower()
            ]
            if not comp_match:
                continue
            df = df[df["competition"].isin(comp_match)]

        # Season filter
        if season:
            for col in ["season", "Ano"]:
                if col in df.columns:
                    df = df[df[col].astype(str).str.startswith(str(season))]
                    break

        # Find team as home or away
        home_cols = {"home_team": "away_team", "Equipe_mandante": "Equipe_visitante"}
        for h_col, a_col in home_cols.items():
            if h_col not in df.columns:
                continue
            h_norm = df[h_col].apply(normalize_team_name)
            a_norm = df[a_col].apply(normalize_team_name)

            home_mask = h_norm == norm_team
            away_mask = a_norm == norm_team
            combined = home_mask | away_mask
            team_df = df[combined]

            for _, r in team_df.iterrows():
                hf_goals = _normalise_goals(r.get("home_goal"))
                af_goals = _normalise_goals(r.get("away_goal"))

                if home_mask.get(r.name, False):
                    goals_for += hf_goals
                    goals_against += af_goals
                    if hf_goals > af_goals:
                        wins += 1
                    elif hf_goals == af_goals:
                        draws += 1
                    else:
                        losses += 1
                    match_count += 1
                elif away_mask.get(r.name, False):
                    goals_for += af_goals
                    goals_against += hf_goals
                    if af_goals > hf_goals:
                        wins += 1
                    elif af_goals == hf_goals:
                        draws += 1
                    else:
                        losses += 1
                    match_count += 1

    win_rate = (wins / match_count * 100) if match_count > 0 else 0.0

    return {
        "team": norm_team,
        "season": season,
        "competition": competition,
        "matches": match_count,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goals_for - goals_against,
        "win_rate": round(win_rate, 1),
    }


# ---------------------------------------------------------------------------
# Tool: get_head_to_head
# ---------------------------------------------------------------------------

@mcp.tool()
def get_head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
) -> dict:
    """Get head-to-head record between two teams.

    Args:
        team_a: First team name.
        team_b: Second team name.
        competition: Optional competition filter.
    """
    data = _get_data()
    norm_a = normalize_team_name(team_a)
    norm_b = normalize_team_name(team_b)

    team_a_wins = 0
    team_b_wins = 0
    draws_count = 0
    matches: list[dict] = []

    for source_name, df in data.items():
        if source_name == "players":
            continue

        if competition:
            comp_match = [
                c for c in df["competition"].unique()
                if competition.lower() in c.lower()
            ]
            if not comp_match:
                continue
            df = df[df["competition"].isin(comp_match)]

        home_cols = {"home_team": "away_team", "Equipe_mandante": "Equipe_visitante"}
        for h_col, a_col in home_cols.items():
            if h_col not in df.columns:
                continue
            h_norm = df[h_col].apply(normalize_team_name)
            a_norm = df[a_col].apply(normalize_team_name)

            # Match where team_a is home and team_b is away
            mask1 = (h_norm == norm_a) & (a_norm == norm_b)
            # Match where team_b is home and team_a is away
            mask2 = (h_norm == norm_b) & (a_norm == norm_a)
            h2h = df[mask1 | mask2]

            for _, r in h2h.iterrows():
                hf = _normalise_goals(r.get("home_goal"))
                af = _normalise_goals(r.get("away_goal"))
                result: dict = {
                    "source": source_name,
                    "date": str(r.get("datetime", r.get("date", ""))),
                    "home": str(r.get(h_col, "")),
                    "away": str(r.get(a_col, "")),
                    "home_goals": hf,
                    "away_goals": af,
                }
                if "season" in r and pd.notna(r.get("season")):
                    result["season"] = int(r["season"])
                if "competition" in r:
                    result["competition"] = str(r["competition"])
                matches.append(result)

                if (h_norm.get(r.name) == norm_a and af > hf) or \
                   (a_norm.get(r.name) == norm_a and hf > af):
                    team_a_wins += 1
                elif (h_norm.get(r.name) == norm_b and af > hf) or \
                     (a_norm.get(r.name) == norm_b and hf > af):
                    team_b_wins += 1
                else:
                    draws_count += 1

    return {
        "team_a": norm_a,
        "team_b": norm_b,
        "team_a_wins": team_a_wins,
        "team_b_wins": team_b_wins,
        "draws": draws_count,
        "total_matches": len(matches),
        "matches": matches,
    }


# ---------------------------------------------------------------------------
# Tool: get_player_info
# ---------------------------------------------------------------------------

@mcp.tool()
def get_player_info(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search players by name, nationality, club, or position.

    Args:
        name: Player name (partial match).
        nationality: Nationality to filter by.
        club: Club to filter by.
        position: Position to filter by.
        min_overall: Minimum overall rating.
        limit: Max results.
    """
    data = _get_data()
    players_df = data["players"]

    mask = pd.Series([True] * len(players_df), index=players_df.index)

    if name:
        mask &= players_df["Name"].str.contains(name, case=False, na=False)
    if nationality:
        mask &= players_df["Nationality"].str.contains(
            nationality, case=False, na=False
        )
    if club:
        mask &= players_df["Club"].str.contains(club, case=False, na=False)
    if position:
        mask &= players_df["Position"].str.contains(position, case=False, na=False)
    if min_overall is not None:
        mask &= pd.to_numeric(players_df["Overall"], errors="coerce") >= min_overall

    filtered = players_df[mask]

    results = []
    for _, row in filtered.head(limit).iterrows():
        overall = row.get("Overall", 0)
        if isinstance(overall, str):
            try:
                overall = float(overall)
            except ValueError:
                overall = 0
        results.append({
            "id": int(row.get("ID", 0)),
            "name": str(row.get("Name", "")),
            "age": int(row.get("Age", 0)),
            "nationality": str(row.get("Nationality", "")),
            "overall": int(overall) if overall else 0,
            "potential": int(row.get("Potential", 0)) if pd.notna(row.get("Potential")) else 0,
            "club": str(row.get("Club", "")),
            "position": str(row.get("Position", "")),
            "height": str(row.get("Height", "")),
            "weight": str(row.get("Weight", "")),
        })

    return results


# ---------------------------------------------------------------------------
# Tool: get_competition_standings
# ---------------------------------------------------------------------------

@mcp.tool()
def get_competition_standings(
    competition: str = "Brasileirao",
    season: int | None = None,
) -> list[dict]:
    """Calculate standings for a competition from match results.

    Args:
        competition: Competition name.
        season: Season year (optional).
    """
    data = _get_data()
    teams: dict[str, dict] = {}

    for source_name, df in data.items():
        if source_name == "players":
            continue

        # Competition filter (partial match on competition name)
        comp_match = [
            c for c in df["competition"].unique()
            if competition.lower() in c.lower()
        ]
        if not comp_match:
            continue
        df = df[df["competition"].isin(comp_match)]

        if season is not None:
            for col in ["season", "Ano"]:
                if col in df.columns:
                    df = df[df[col].astype(str).str.startswith(str(season))]
                    break

        home_cols = {"home_team": "away_team", "Equipe_mandante": "Equipe_visitante"}
        for h_col, a_col in home_cols.items():
            if h_col not in df.columns:
                continue

            for _, r in df.iterrows():
                home = normalize_team_name(str(r.get(h_col, "")))
                away = normalize_team_name(str(r.get(a_col, "")))
                hf = _normalise_goals(r.get("home_goal"))
                af = _normalise_goals(r.get("away_goal"))

                if home:
                    if home not in teams:
                        teams[home] = {
                            "team": home,
                            "played": 0,
                            "wins": 0,
                            "draws": 0,
                            "losses": 0,
                            "goals_for": 0,
                            "goals_against": 0,
                            "points": 0,
                        }
                    teams[home]["played"] += 1
                    teams[home]["goals_for"] += hf
                    teams[home]["goals_against"] += af
                    if hf > af:
                        teams[home]["wins"] += 1
                        teams[home]["points"] += 3
                    elif hf == af:
                        teams[home]["draws"] += 1
                        teams[home]["points"] += 1
                    else:
                        teams[home]["losses"] += 1

                if away:
                    if away not in teams:
                        teams[away] = {
                            "team": away,
                            "played": 0,
                            "wins": 0,
                            "draws": 0,
                            "losses": 0,
                            "goals_for": 0,
                            "goals_against": 0,
                            "points": 0,
                        }
                    teams[away]["played"] += 1
                    teams[away]["goals_for"] += af
                    teams[away]["goals_against"] += hf
                    if af > hf:
                        teams[away]["wins"] += 1
                        teams[away]["points"] += 3
                    elif af == hf:
                        teams[away]["draws"] += 1
                        teams[away]["points"] += 1
                    else:
                        teams[away]["losses"] += 1

    standings = sorted(
        teams.values(),
        key=lambda x: (-x["points"], -(x["goals_for"] - x["goals_against"]), -x["goals_for"]),
    )

    return standings


# ---------------------------------------------------------------------------
# Tool: get_biggest_wins
# ---------------------------------------------------------------------------

@mcp.tool()
def get_biggest_wins(
    competition: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Find the biggest wins in the dataset.

    Args:
        competition: Filter by competition.
        limit: Max results.
    """
    data = _get_data()
    all_matches: list[dict] = []

    for source_name, df in data.items():
        if source_name == "players":
            continue

        if competition:
            comp_match = [
                c for c in df["competition"].unique()
                if competition.lower() in c.lower()
            ]
            if not comp_match:
                continue
            df = df[df["competition"].isin(comp_match)]

        home_cols = {"home_team": "away_team", "Equipe_mandante": "Equipe_visitante"}
        for h_col, a_col in home_cols.items():
            if h_col not in df.columns:
                continue
            for _, r in df.iterrows():
                hf = _normalise_goals(r.get("home_goal"))
                af = _normalise_goals(r.get("away_goal"))
                diff = abs(hf - af)
                if diff >= 3:
                    all_matches.append({
                        "date": str(r.get("datetime", r.get("date", ""))),
                        "home": str(r.get(h_col, "")),
                        "away": str(r.get(a_col, "")),
                        "home_goals": hf,
                        "away_goals": af,
                        "margin": diff,
                        "source": source_name,
                        "competition": str(r.get("competition", "")),
                    })

    all_matches.sort(key=lambda x: (-x["margin"], x["date"]))
    return all_matches[:limit]


# ---------------------------------------------------------------------------
# Tool: get_average_goals
# ---------------------------------------------------------------------------

@mcp.tool()
def get_average_goals(
    competition: str | None = None,
) -> dict:
    """Calculate average goals per match statistics.

    Args:
        competition: Filter by competition.
    """
    data = _get_data()
    total_goals = 0
    total_matches = 0
    home_wins = 0
    away_wins = 0
    draws_count = 0

    for source_name, df in data.items():
        if source_name == "players":
            continue

        if competition:
            comp_match = [
                c for c in df["competition"].unique()
                if competition.lower() in c.lower()
            ]
            if not comp_match:
                continue
            df = df[df["competition"].isin(comp_match)]

        home_cols = {"home_team": "away_team", "Equipe_mandante": "Equipe_visitante"}
        for h_col, a_col in home_cols.items():
            if h_col not in df.columns:
                continue
            for _, r in df.iterrows():
                hf = _normalise_goals(r.get("home_goal"))
                af = _normalise_goals(r.get("away_goal"))
                total_goals += hf + af
                total_matches += 1
                if hf > af:
                    home_wins += 1
                elif af > hf:
                    away_wins += 1
                else:
                    draws_count += 1

    avg_goals = (total_goals / total_matches) if total_matches > 0 else 0
    home_win_rate = (home_wins / total_matches * 100) if total_matches > 0 else 0
    away_win_rate = (away_wins / total_matches * 100) if total_matches > 0 else 0
    draw_rate = (draws_count / total_matches * 100) if total_matches > 0 else 0

    return {
        "total_matches": total_matches,
        "total_goals": total_goals,
        "average_goals_per_match": round(avg_goals, 2),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws_count,
        "home_win_rate": round(home_win_rate, 1),
        "away_win_rate": round(away_win_rate, 1),
        "draw_rate": round(draw_rate, 1),
    }


# ---------------------------------------------------------------------------
# Tool: list_datasets
# ---------------------------------------------------------------------------

@mcp.tool()
def list_datasets() -> list[dict]:
    """List all available datasets with row counts and column info."""
    data = _get_data()
    result = []
    for name, df in data.items():
        result.append({
            "name": name,
            "rows": len(df),
            "columns": list(df.columns),
        })
    return result


# ---------------------------------------------------------------------------
# Tool: get_team_players
# ---------------------------------------------------------------------------

@mcp.tool()
def get_team_players(
    team: str,
    min_overall: int | None = None,
    limit: int = 20,
) -> list[dict]:
    """Find players currently at a specific club.

    Args:
        team: Club name.
        min_overall: Minimum overall rating filter.
        limit: Max results.
    """
    data = _get_data()
    players_df = data["players"]

    norm_team = normalize_team_name(team)
    mask = players_df["Club"].str.contains(norm_team, case=False, na=False)
    mask = mask | players_df["Club"].str.contains(team, case=False, na=False)

    filtered = players_df[mask]
    if min_overall is not None:
        mask_ol = pd.to_numeric(filtered["Overall"], errors="coerce") >= min_overall
        filtered = filtered[mask_ol]

    results = []
    for _, row in filtered.head(limit).iterrows():
        overall = row.get("Overall", 0)
        if isinstance(overall, str):
            try:
                overall = float(overall)
            except ValueError:
                overall = 0
        results.append({
            "id": int(row.get("ID", 0)),
            "name": str(row.get("Name", "")),
            "age": int(row.get("Age", 0)),
            "nationality": str(row.get("Nationality", "")),
            "overall": int(overall) if overall else 0,
            "potential": int(row.get("Potential", 0)) if pd.notna(row.get("Potential")) else 0,
            "position": str(row.get("Position", "")),
        })

    return results


if __name__ == "__main__":
    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    mcp.run(transport=transport)
