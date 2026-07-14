"""Team statistics and record query functions."""
import pandas as pd


def _filter_team_matches(df: pd.DataFrame, team: str, season: int = None) -> pd.DataFrame:
    mask = (
        df["home_team"].str.contains(team, case=False, na=False) |
        df["away_team"].str.contains(team, case=False, na=False)
    )
    sub = df[mask]
    if season is not None and "season" in sub.columns:
        sub = sub[sub["season"] == season]
    return sub


def get_team_record(df: pd.DataFrame, team: str, season: int = None) -> dict:
    """Return W/D/L record for a team."""
    matches = _filter_team_matches(df, team, season)
    wins = draws = losses = 0
    for _, row in matches.iterrows():
        hg, ag = row.get("home_goal"), row.get("away_goal")
        if pd.isna(hg) or pd.isna(ag):
            continue
        home_is_team = team.lower() in str(row.get("home_team", "")).lower()
        if hg == ag:
            draws += 1
        elif hg > ag:
            if home_is_team:
                wins += 1
            else:
                losses += 1
        else:
            if home_is_team:
                losses += 1
            else:
                wins += 1
    total = wins + draws + losses
    return {"wins": wins, "draws": draws, "losses": losses, "matches": total}


def get_team_goals(df: pd.DataFrame, team: str, season: int = None) -> dict:
    """Return total goals scored and conceded by a team."""
    matches = _filter_team_matches(df, team, season)
    scored = conceded = 0
    for _, row in matches.iterrows():
        hg, ag = row.get("home_goal"), row.get("away_goal")
        if pd.isna(hg) or pd.isna(ag):
            continue
        home_is_team = team.lower() in str(row.get("home_team", "")).lower()
        if home_is_team:
            scored += int(hg)
            conceded += int(ag)
        else:
            scored += int(ag)
            conceded += int(hg)
    return {"scored": scored, "conceded": conceded}


def _record_from_matches(df: pd.DataFrame, team: str, home: bool) -> dict:
    role = "home_team" if home else "away_team"
    goal_for = "home_goal" if home else "away_goal"
    goal_against = "away_goal" if home else "home_goal"
    sub = df[df[role].str.contains(team, case=False, na=False)]
    wins = draws = losses = 0
    gf = ga = 0
    for _, row in sub.iterrows():
        hg, ag = row.get(goal_for), row.get(goal_against)
        if pd.isna(hg) or pd.isna(ag):
            continue
        if hg == ag:
            draws += 1
        elif hg > ag:
            wins += 1
        else:
            losses += 1
        gf += int(hg)
        ga += int(ag)
    total = wins + draws + losses
    win_rate = wins / total if total > 0 else 0
    return {"wins": wins, "draws": draws, "losses": losses, "matches": total,
            "goals_for": gf, "goals_against": ga, "win_rate": round(win_rate, 4)}


def get_home_record(df: pd.DataFrame, team: str, season: int = None) -> dict:
    """Return home W/D/L record for a team."""
    sub = df
    if season is not None and "season" in df.columns:
        sub = df[df["season"] == season]
    return _record_from_matches(sub, team, home=True)


def get_away_record(df: pd.DataFrame, team: str, season: int = None) -> dict:
    """Return away W/D/L record for a team."""
    sub = df
    if season is not None and "season" in df.columns:
        sub = df[df["season"] == season]
    return _record_from_matches(sub, team, home=False)


def _all_teams(df: pd.DataFrame) -> set:
    return set(df["home_team"].dropna()) | set(df["away_team"].dropna())


def get_top_scoring_teams(df: pd.DataFrame, season: int = None, limit: int = 10) -> list:
    """Return teams sorted by total goals scored."""
    sub = df
    if season is not None and "season" in df.columns:
        sub = df[df["season"] == season]
    home_goals = sub.groupby("home_team")["home_goal"].sum()
    away_goals = sub.groupby("away_team")["away_goal"].sum()
    total = home_goals.add(away_goals, fill_value=0).sort_values(ascending=False)
    return [{"team": team, "goals_scored": int(goals)} for team, goals in total.head(limit).items()]


def _build_records(df: pd.DataFrame, home: bool, limit: int) -> list:
    role = "home_team" if home else "away_team"
    goal_for = "home_goal" if home else "away_goal"
    goal_against = "away_goal" if home else "home_goal"
    records = []
    for team in _all_teams(df):
        sub = df[df[role].str.contains(team, case=False, na=False, regex=False)]
        sub = sub.dropna(subset=[goal_for, goal_against])
        if len(sub) == 0:
            continue
        wins = int((sub[goal_for] > sub[goal_against]).sum())
        draws = int((sub[goal_for] == sub[goal_against]).sum())
        losses = int((sub[goal_for] < sub[goal_against]).sum())
        total = wins + draws + losses
        records.append({
            "team": team,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "matches": total,
            "win_rate": round(wins / total, 4) if total > 0 else 0,
        })
    records.sort(key=lambda r: r["win_rate"], reverse=True)
    return records[:limit]


def get_best_home_records(df: pd.DataFrame, season: int = None, limit: int = 10) -> list:
    sub = df
    if season is not None and "season" in df.columns:
        sub = df[df["season"] == season]
    return _build_records(sub, home=True, limit=limit)


def get_best_away_records(df: pd.DataFrame, season: int = None, limit: int = 10) -> list:
    sub = df
    if season is not None and "season" in df.columns:
        sub = df[df["season"] == season]
    return _build_records(sub, home=False, limit=limit)
