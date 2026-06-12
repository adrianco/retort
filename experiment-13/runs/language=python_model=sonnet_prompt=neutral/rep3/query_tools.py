"""Query functions for Brazilian soccer data, used by the MCP server tools."""

from __future__ import annotations

import json
from typing import Optional
import pandas as pd

from data_loader import SoccerData, normalize_team, get_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match_row_to_dict(row: pd.Series) -> dict:
    return {
        "date": str(row.get("date", "")),
        "home_team": str(row.get("home_team", "")),
        "away_team": str(row.get("away_team", "")),
        "home_goal": int(row["home_goal"]) if pd.notna(row.get("home_goal")) else None,
        "away_goal": int(row["away_goal"]) if pd.notna(row.get("away_goal")) else None,
        "competition": str(row.get("competition", "")),
        "season": int(row["season"]) if pd.notna(row.get("season")) else None,
        "round": str(row["round"]) if pd.notna(row.get("round", None)) else None,
    }


def _filter_by_team(df: pd.DataFrame, team: str, role: str = "either") -> pd.DataFrame:
    """Filter matches by team name (fuzzy normalized match)."""
    norm = normalize_team(team)
    if role == "home":
        return df[df["home_norm"] == norm]
    elif role == "away":
        return df[df["away_norm"] == norm]
    else:
        return df[(df["home_norm"] == norm) | (df["away_norm"] == norm)]


def _filter_by_date(df: pd.DataFrame, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
    if start:
        df = df[df["datetime"] >= pd.Timestamp(start)]
    if end:
        df = df[df["datetime"] <= pd.Timestamp(end)]
    return df


def _comp_df(data: SoccerData, competition: Optional[str]) -> pd.DataFrame:
    if not competition:
        return data.all_matches
    comp_lower = competition.lower()
    if "brasileir" in comp_lower or "serie a" in comp_lower or "brasileirao" in comp_lower:
        return data.brasileirao
    elif "copa do brasil" in comp_lower or "cup" in comp_lower:
        return data.cup
    elif "libertadores" in comp_lower:
        return data.libertadores
    return data.all_matches


def _win_loss_draw(df: pd.DataFrame, team_norm: str) -> dict:
    wins = losses = draws = gf = ga = 0
    for _, row in df.iterrows():
        hg = row.get("home_goal")
        ag = row.get("away_goal")
        if pd.isna(hg) or pd.isna(ag):
            continue
        hg, ag = int(hg), int(ag)
        if row["home_norm"] == team_norm:
            gf += hg; ga += ag
            if hg > ag: wins += 1
            elif hg == ag: draws += 1
            else: losses += 1
        elif row["away_norm"] == team_norm:
            gf += ag; ga += hg
            if ag > hg: wins += 1
            elif ag == hg: draws += 1
            else: losses += 1
    total = wins + draws + losses
    return {
        "matches": total,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def search_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    role: str = "either",
    limit: int = 50,
    data: Optional[SoccerData] = None,
) -> str:
    """
    Search for matches by team, competition, season, or date range.

    Args:
        team: Team name to search for (home, away, or either)
        opponent: Optional second team for head-to-head filtering
        competition: 'Brasileirão', 'Copa do Brasil', or 'Libertadores'
        season: Year (e.g. 2023)
        start_date: ISO date string YYYY-MM-DD
        end_date: ISO date string YYYY-MM-DD
        role: 'home', 'away', or 'either' (default)
        limit: Maximum number of matches to return (default 50)
    """
    if data is None:
        data = get_data()
    df = _comp_df(data, competition)

    if team:
        df = _filter_by_team(df, team, role)
    if opponent:
        opp_norm = normalize_team(opponent)
        df = df[(df["home_norm"] == opp_norm) | (df["away_norm"] == opp_norm)]
    if season:
        df = df[df["season"] == season]
    df = _filter_by_date(df, start_date, end_date)
    df = df.sort_values("datetime", ascending=False)

    total = len(df)
    rows = [_match_row_to_dict(r) for _, r in df.head(limit).iterrows()]

    # Head-to-head summary if two teams specified
    h2h = None
    if team and opponent:
        team_norm = normalize_team(team)
        opp_norm = normalize_team(opponent)
        t_wins = opp_wins = draws = 0
        for r in rows:
            hg = r["home_goal"]; ag = r["away_goal"]
            if hg is None or ag is None:
                continue
            if normalize_team(r["home_team"]) == team_norm:
                if hg > ag: t_wins += 1
                elif hg == ag: draws += 1
                else: opp_wins += 1
            else:
                if ag > hg: t_wins += 1
                elif ag == hg: draws += 1
                else: opp_wins += 1
        h2h = {
            f"{team} wins": t_wins,
            f"{opponent} wins": opp_wins,
            "draws": draws,
        }

    result: dict = {"total_found": total, "showing": len(rows), "matches": rows}
    if h2h:
        result["head_to_head"] = h2h
    return json.dumps(result, ensure_ascii=False, default=str)


def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    role: str = "either",
    data: Optional[SoccerData] = None,
) -> str:
    """
    Get win/loss/draw statistics for a team.

    Args:
        team: Team name
        competition: Filter by competition (optional)
        season: Filter by year (optional)
        role: 'home', 'away', or 'either' (default)
    """
    if data is None:
        data = get_data()
    df = _comp_df(data, competition)
    df = _filter_by_team(df, team, role)
    if season:
        df = df[df["season"] == season]

    team_norm = normalize_team(team)
    stats = _win_loss_draw(df, team_norm)
    stats["team"] = team
    if competition:
        stats["competition"] = competition
    if season:
        stats["season"] = season
    stats["role"] = role
    return json.dumps(stats, ensure_ascii=False)


def head_to_head(
    team1: str,
    team2: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 20,
    data: Optional[SoccerData] = None,
) -> str:
    """
    Get head-to-head record and recent matches between two teams.

    Args:
        team1: First team name
        team2: Second team name
        competition: Filter by competition (optional)
        season: Filter by season year (optional)
        limit: Max number of recent matches to include
    """
    if data is None:
        data = get_data()
    df = _comp_df(data, competition)

    n1 = normalize_team(team1)
    n2 = normalize_team(team2)
    df = df[
        ((df["home_norm"] == n1) & (df["away_norm"] == n2)) |
        ((df["home_norm"] == n2) & (df["away_norm"] == n1))
    ]
    if season:
        df = df[df["season"] == season]
    df = df.sort_values("datetime", ascending=False)

    t1_wins = t2_wins = draws = 0
    for _, row in df.iterrows():
        hg = row.get("home_goal"); ag = row.get("away_goal")
        if pd.isna(hg) or pd.isna(ag):
            continue
        hg, ag = int(hg), int(ag)
        if row["home_norm"] == n1:
            if hg > ag: t1_wins += 1
            elif hg == ag: draws += 1
            else: t2_wins += 1
        else:
            if ag > hg: t1_wins += 1
            elif ag == hg: draws += 1
            else: t2_wins += 1

    matches = [_match_row_to_dict(r) for _, r in df.head(limit).iterrows()]
    result = {
        "team1": team1,
        "team2": team2,
        "total_matches": len(df),
        f"{team1}_wins": t1_wins,
        f"{team2}_wins": t2_wins,
        "draws": draws,
        "recent_matches": matches,
    }
    return json.dumps(result, ensure_ascii=False, default=str)


def get_competition_standings(
    season: int,
    competition: str = "Brasileirão",
    data: Optional[SoccerData] = None,
) -> str:
    """
    Calculate league standings for a given season.

    Args:
        season: Year (e.g. 2019)
        competition: Competition name (default 'Brasileirão')
    """
    if data is None:
        data = get_data()
    df = _comp_df(data, competition)
    df = df[df["season"] == season].copy()
    df = df.dropna(subset=["home_goal", "away_goal"])

    if df.empty:
        return json.dumps({"error": f"No data found for {competition} {season}"})

    teams: dict[str, dict] = {}

    def ensure(t):
        if t not in teams:
            teams[t] = {"team": t, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0}

    for _, row in df.iterrows():
        h, a = row["home_norm"], row["away_norm"]
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        ensure(h); ensure(a)
        teams[h]["P"] += 1; teams[a]["P"] += 1
        teams[h]["GF"] += hg; teams[h]["GA"] += ag
        teams[a]["GF"] += ag; teams[a]["GA"] += hg
        teams[h]["GD"] = teams[h]["GF"] - teams[h]["GA"]
        teams[a]["GD"] = teams[a]["GF"] - teams[a]["GA"]
        if hg > ag:
            teams[h]["W"] += 1; teams[h]["Pts"] += 3
            teams[a]["L"] += 1
        elif hg == ag:
            teams[h]["D"] += 1; teams[h]["Pts"] += 1
            teams[a]["D"] += 1; teams[a]["Pts"] += 1
        else:
            teams[a]["W"] += 1; teams[a]["Pts"] += 3
            teams[h]["L"] += 1

    table = sorted(teams.values(), key=lambda x: (-x["Pts"], -x["GD"], -x["GF"]))
    for i, row in enumerate(table, 1):
        row["pos"] = i

    return json.dumps({
        "competition": competition,
        "season": season,
        "standings": table,
    }, ensure_ascii=False)


def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 30,
    data: Optional[SoccerData] = None,
) -> str:
    """
    Search FIFA player database.

    Args:
        name: Player name (partial match)
        nationality: Nationality (e.g. 'Brazil', 'Argentine')
        club: Club name (partial match)
        position: Position (e.g. 'ST', 'GK', 'CAM')
        min_overall: Minimum FIFA overall rating
        limit: Max results to return (default 30)
    """
    if data is None:
        data = get_data()
    df = data.fifa.copy()

    if name:
        df = df[df["Name"].str.contains(name, case=False, na=False)]
    if nationality:
        df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
    if club:
        df = df[df["Club"].str.contains(club, case=False, na=False)]
    if position:
        df = df[df["Position"].str.contains(position, case=False, na=False)]
    if min_overall is not None:
        df = df[pd.to_numeric(df["Overall"], errors="coerce") >= min_overall]

    df = df.sort_values("Overall", ascending=False)
    cols = ["Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position", "Jersey Number"]
    cols = [c for c in cols if c in df.columns]
    rows = df[cols].head(limit).to_dict(orient="records")
    return json.dumps({"total_found": len(df), "showing": len(rows), "players": rows},
                      ensure_ascii=False, default=str)


def top_scorers_by_team(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    top_n: int = 10,
    data: Optional[SoccerData] = None,
) -> str:
    """
    Rank teams by total goals scored.

    Args:
        competition: Competition filter (optional)
        season: Season year filter (optional)
        top_n: Number of top teams to return (default 10)
    """
    if data is None:
        data = get_data()
    df = _comp_df(data, competition)
    if season:
        df = df[df["season"] == season]
    df = df.dropna(subset=["home_goal", "away_goal"])

    goals: dict[str, int] = {}
    for _, row in df.iterrows():
        h, a = row["home_norm"], row["away_norm"]
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        goals[h] = goals.get(h, 0) + hg
        goals[a] = goals.get(a, 0) + ag

    ranked = sorted(goals.items(), key=lambda x: -x[1])[:top_n]
    return json.dumps({
        "competition": competition or "All",
        "season": season or "All",
        "top_scorers": [{"team": t, "goals": g} for t, g in ranked],
    }, ensure_ascii=False)


def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    top_n: int = 10,
    data: Optional[SoccerData] = None,
) -> str:
    """
    Find the biggest goal-margin victories.

    Args:
        competition: Filter by competition (optional)
        season: Filter by season year (optional)
        top_n: Number of results to return (default 10)
    """
    if data is None:
        data = get_data()
    df = _comp_df(data, competition)
    if season:
        df = df[df["season"] == season]
    df = df.dropna(subset=["home_goal", "away_goal"]).copy()
    df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
    df = df.sort_values(["margin", "home_goal", "away_goal"], ascending=False).head(top_n)
    matches = [_match_row_to_dict(r) for _, r in df.iterrows()]
    return json.dumps({"biggest_wins": matches}, ensure_ascii=False, default=str)


def aggregate_stats(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    data: Optional[SoccerData] = None,
) -> str:
    """
    Get aggregate statistics (goals per match, home win rate, etc.).

    Args:
        competition: Filter by competition (optional)
        season: Filter by season year (optional)
    """
    if data is None:
        data = get_data()
    df = _comp_df(data, competition)
    if season:
        df = df[df["season"] == season]
    df = df.dropna(subset=["home_goal", "away_goal"])

    total = len(df)
    if total == 0:
        return json.dumps({"error": "No data for given filters"})

    total_goals = int(df["home_goal"].sum() + df["away_goal"].sum())
    home_wins = int(((df["home_goal"] > df["away_goal"])).sum())
    draws = int((df["home_goal"] == df["away_goal"]).sum())
    away_wins = total - home_wins - draws

    return json.dumps({
        "competition": competition or "All",
        "season": season or "All",
        "total_matches": total,
        "total_goals": total_goals,
        "avg_goals_per_match": round(total_goals / total, 2),
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_win_rate_pct": round(home_wins / total * 100, 1),
        "draw_rate_pct": round(draws / total * 100, 1),
        "away_win_rate_pct": round(away_wins / total * 100, 1),
    }, ensure_ascii=False)


def best_home_records(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    top_n: int = 10,
    data: Optional[SoccerData] = None,
) -> str:
    """
    Find teams with the best home win records.

    Args:
        competition: Competition filter (optional)
        season: Season year filter (optional)
        top_n: Number of top teams (default 10)
    """
    if data is None:
        data = get_data()
    df = _comp_df(data, competition)
    if season:
        df = df[df["season"] == season]
    df = df.dropna(subset=["home_goal", "away_goal"])

    records: dict[str, dict] = {}
    for _, row in df.iterrows():
        h = row["home_norm"]
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        if h not in records:
            records[h] = {"team": h, "home_played": 0, "home_wins": 0, "home_draws": 0, "home_losses": 0}
        r = records[h]
        r["home_played"] += 1
        if hg > ag: r["home_wins"] += 1
        elif hg == ag: r["home_draws"] += 1
        else: r["home_losses"] += 1

    for r in records.values():
        p = r["home_played"]
        r["home_win_rate_pct"] = round(r["home_wins"] / p * 100, 1) if p >= 5 else 0.0

    ranked = sorted(records.values(), key=lambda x: (-x["home_win_rate_pct"], -x["home_wins"]))
    ranked = [r for r in ranked if r["home_played"] >= 5][:top_n]
    return json.dumps({"best_home_records": ranked}, ensure_ascii=False)
