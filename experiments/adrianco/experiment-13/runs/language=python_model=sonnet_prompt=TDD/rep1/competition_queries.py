"""Competition standings and aggregate statistical analysis."""
import pandas as pd


def _filter_season(df: pd.DataFrame, season: int = None) -> pd.DataFrame:
    if season is None or "season" not in df.columns:
        return df
    return df[df["season"] == season]


def calculate_standings(df: pd.DataFrame, season: int = None) -> list:
    """Calculate a league table from match results."""
    sub = _filter_season(df, season).dropna(subset=["home_goal", "away_goal"])
    records: dict[str, dict] = {}

    def _ensure(team):
        if team not in records:
            records[team] = {"team": team, "wins": 0, "draws": 0, "losses": 0, "matches": 0,
                             "goals_for": 0, "goals_against": 0}

    for _, row in sub.iterrows():
        home, away = row["home_team"], row["away_team"]
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        _ensure(home)
        _ensure(away)
        records[home]["matches"] += 1
        records[away]["matches"] += 1
        records[home]["goals_for"] += hg
        records[home]["goals_against"] += ag
        records[away]["goals_for"] += ag
        records[away]["goals_against"] += hg
        if hg > ag:
            records[home]["wins"] += 1
            records[away]["losses"] += 1
        elif hg < ag:
            records[away]["wins"] += 1
            records[home]["losses"] += 1
        else:
            records[home]["draws"] += 1
            records[away]["draws"] += 1

    result = list(records.values())
    for r in result:
        r["points"] = r["wins"] * 3 + r["draws"]
        r["goal_diff"] = r["goals_for"] - r["goals_against"]

    result.sort(key=lambda r: (r["points"], r["goal_diff"], r["goals_for"]), reverse=True)
    return result


def get_biggest_wins(df: pd.DataFrame, season: int = None, limit: int = 10) -> list:
    """Return the matches with the largest goal difference."""
    sub = _filter_season(df, season).dropna(subset=["home_goal", "away_goal"]).copy()
    sub["home_goal"] = pd.to_numeric(sub["home_goal"], errors="coerce")
    sub["away_goal"] = pd.to_numeric(sub["away_goal"], errors="coerce")
    sub = sub.dropna(subset=["home_goal", "away_goal"])
    sub["goal_diff"] = (sub["home_goal"] - sub["away_goal"]).abs().astype(int)
    sub = sub.sort_values("goal_diff", ascending=False).head(limit)
    result = []
    for _, row in sub.iterrows():
        result.append({
            "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row.get("date")) else None,
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_goal": int(row["home_goal"]),
            "away_goal": int(row["away_goal"]),
            "goal_diff": int(row["goal_diff"]),
            "competition": row.get("competition", ""),
        })
    return result


def get_average_goals_per_match(df: pd.DataFrame, season: int = None) -> float:
    """Calculate average total goals per match."""
    sub = _filter_season(df, season).dropna(subset=["home_goal", "away_goal"])
    if len(sub) == 0:
        return 0.0
    total_goals = pd.to_numeric(sub["home_goal"], errors="coerce") + pd.to_numeric(sub["away_goal"], errors="coerce")
    return round(float(total_goals.mean()), 4)


def get_home_win_rate(df: pd.DataFrame, season: int = None) -> float:
    """Return the fraction of matches won by the home team."""
    sub = _filter_season(df, season).dropna(subset=["home_goal", "away_goal"])
    if len(sub) == 0:
        return 0.0
    hg = pd.to_numeric(sub["home_goal"], errors="coerce")
    ag = pd.to_numeric(sub["away_goal"], errors="coerce")
    home_wins = (hg > ag).sum()
    return round(float(home_wins / len(sub)), 4)


def get_season_summary(df: pd.DataFrame, season: int) -> dict:
    """Return summary statistics for a given season."""
    sub = _filter_season(df, season).dropna(subset=["home_goal", "away_goal"])
    total_matches = len(sub)
    hg = pd.to_numeric(sub["home_goal"], errors="coerce")
    ag = pd.to_numeric(sub["away_goal"], errors="coerce")
    total_goals = int((hg + ag).sum())
    avg_goals = round(float((hg + ag).mean()), 4) if total_matches > 0 else 0.0
    home_wins = int((hg > ag).sum())
    home_win_rate = round(home_wins / total_matches, 4) if total_matches > 0 else 0.0
    return {
        "season": season,
        "total_matches": total_matches,
        "total_goals": total_goals,
        "avg_goals_per_match": avg_goals,
        "home_win_rate": home_win_rate,
        "home_wins": home_wins,
    }
