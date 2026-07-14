"""Match query functions for the Brazilian soccer MCP server."""
import pandas as pd


def search_matches_by_team(df: pd.DataFrame, team: str, *, home_only: bool = False, away_only: bool = False) -> pd.DataFrame:
    """Find all matches involving a team (case-insensitive partial match)."""
    if home_only:
        mask = df["home_team"].str.contains(team, case=False, na=False)
    elif away_only:
        mask = df["away_team"].str.contains(team, case=False, na=False)
    else:
        mask = (
            df["home_team"].str.contains(team, case=False, na=False) |
            df["away_team"].str.contains(team, case=False, na=False)
        )
    return df[mask].copy()


def search_matches_head_to_head(df: pd.DataFrame, team1: str, team2: str) -> pd.DataFrame:
    """Find all matches between two specific teams."""
    mask = (
        (df["home_team"].str.contains(team1, case=False, na=False) &
         df["away_team"].str.contains(team2, case=False, na=False)) |
        (df["home_team"].str.contains(team2, case=False, na=False) &
         df["away_team"].str.contains(team1, case=False, na=False))
    )
    return df[mask].copy()


def search_matches_by_season(df: pd.DataFrame, season: int) -> pd.DataFrame:
    """Find all matches in a given season year."""
    if "season" not in df.columns:
        return df.iloc[0:0].copy()
    return df[df["season"] == season].copy()


def search_matches_by_competition(df: pd.DataFrame, competition: str) -> pd.DataFrame:
    """Find matches by competition name (case-insensitive partial match)."""
    if "competition" not in df.columns:
        return df.iloc[0:0].copy()
    mask = df["competition"].str.contains(competition, case=False, na=False)
    return df[mask].copy()


def search_matches_by_date_range(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    """Find matches within a date range (inclusive, ISO format dates)."""
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    mask = (df["date"] >= start) & (df["date"] <= end)
    return df[mask].copy()


def format_match_result(row: pd.Series) -> str:
    """Format a single match result as a human-readable string."""
    date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row.get("date")) else "Unknown date"
    home = row.get("home_team", "?")
    away = row.get("away_team", "?")
    hg = int(row["home_goal"]) if pd.notna(row.get("home_goal")) else "?"
    ag = int(row["away_goal"]) if pd.notna(row.get("away_goal")) else "?"
    comp = row.get("competition", "")
    comp_str = f" ({comp})" if comp else ""
    return f"{date_str}: {home} {hg}-{ag} {away}{comp_str}"


def head_to_head_summary(df: pd.DataFrame, team1: str, team2: str) -> dict:
    """Return win/draw/loss counts for team1 vs team2 from a head-to-head DataFrame."""
    total = len(df)
    t1_wins = 0
    t2_wins = 0
    draws = 0
    for _, row in df.iterrows():
        hg = row.get("home_goal")
        ag = row.get("away_goal")
        if pd.isna(hg) or pd.isna(ag):
            continue
        home_is_t1 = str(team1).lower() in str(row.get("home_team", "")).lower()
        if hg == ag:
            draws += 1
        elif hg > ag:
            if home_is_t1:
                t1_wins += 1
            else:
                t2_wins += 1
        else:
            if home_is_t1:
                t2_wins += 1
            else:
                t1_wins += 1
    return {
        "team1": team1,
        "team2": team2,
        "team1_wins": t1_wins,
        "team2_wins": t2_wins,
        "draws": draws,
        "total_matches": total,
    }
