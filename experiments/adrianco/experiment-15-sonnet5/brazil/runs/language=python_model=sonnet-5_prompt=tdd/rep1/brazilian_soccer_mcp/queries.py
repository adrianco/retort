import pandas as pd

from brazilian_soccer_mcp.normalize import canonical_team_key

MATCH_OUTPUT_COLUMNS = [
    "date", "season", "round", "stage", "competition", "source",
    "home_team_display", "away_team_display", "home_goal", "away_goal",
]


def _filter_by_team(df: pd.DataFrame, team: str, opponent: str | None = None) -> pd.DataFrame:
    key = canonical_team_key(team)
    mask = (df["home_team"] == key) | (df["away_team"] == key)
    if opponent is not None:
        opp_key = canonical_team_key(opponent)
        mask &= (df["home_team"] == opp_key) | (df["away_team"] == opp_key)
    return df[mask]


def find_matches(
    df: pd.DataFrame,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from=None,
    date_to=None,
) -> list[dict]:
    result = df
    if team is not None:
        result = _filter_by_team(result, team, opponent)
    if competition is not None:
        result = result[result["competition"] == competition]
    if season is not None:
        result = result[result["season"] == season]
    if date_from is not None:
        result = result[result["date"] >= date_from]
    if date_to is not None:
        result = result[result["date"] <= date_to]
    result = result.sort_values("date", ascending=False)
    return result[MATCH_OUTPUT_COLUMNS].to_dict(orient="records")


def head_to_head(df: pd.DataFrame, team_a: str, team_b: str, competition: str | None = None, season: int | None = None) -> dict:
    matches = find_matches(df, team=team_a, opponent=team_b, competition=competition, season=season)
    key_a = canonical_team_key(team_a)
    team_a_wins = team_b_wins = draws = 0
    for m in matches:
        home_is_a = canonical_team_key(m["home_team_display"]) == key_a or m["home_team_display"].lower() == team_a.lower()
        home_goal, away_goal = m["home_goal"], m["away_goal"]
        if home_goal == away_goal:
            draws += 1
        else:
            home_won = home_goal > away_goal
            a_won = home_won if home_is_a else not home_won
            if a_won:
                team_a_wins += 1
            else:
                team_b_wins += 1
    return {
        "team_a": team_a,
        "team_b": team_b,
        "team_a_wins": team_a_wins,
        "team_b_wins": team_b_wins,
        "draws": draws,
        "total_matches": len(matches),
        "matches": matches,
    }


def team_record(df: pd.DataFrame, team: str, competition: str | None = None, season: int | None = None, venue: str | None = None) -> dict:
    key = canonical_team_key(team)
    subset = df
    if competition is not None:
        subset = subset[subset["competition"] == competition]
    if season is not None:
        subset = subset[subset["season"] == season]

    if venue == "home":
        subset = subset[subset["home_team"] == key]
    elif venue == "away":
        subset = subset[subset["away_team"] == key]
    else:
        subset = subset[(subset["home_team"] == key) | (subset["away_team"] == key)]

    wins = draws = losses = goals_for = goals_against = 0
    team_display = None
    for _, row in subset.iterrows():
        is_home = row["home_team"] == key
        gf = row["home_goal"] if is_home else row["away_goal"]
        ga = row["away_goal"] if is_home else row["home_goal"]
        if team_display is None:
            team_display = row["home_team_display"] if is_home else row["away_team_display"]
        if pd.isna(gf) or pd.isna(ga):
            continue
        goals_for += gf
        goals_against += ga
        if gf == ga:
            draws += 1
        elif gf > ga:
            wins += 1
        else:
            losses += 1

    matches = wins + draws + losses
    return {
        "team": key,
        "team_display": team_display or key.title(),
        "matches": matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "win_rate": wins / matches if matches else 0.0,
    }


def standings(df: pd.DataFrame, competition: str | None = None, season: int | None = None) -> list[dict]:
    subset = df
    if competition is not None:
        subset = subset[subset["competition"] == competition]
    if season is not None:
        subset = subset[subset["season"] == season]

    teams = set(subset["home_team"].dropna()) | set(subset["away_team"].dropna())
    table = []
    for team in teams:
        record = team_record(subset, team)
        points = record["wins"] * 3 + record["draws"]
        table.append({**record, "points": points, "goal_difference": record["goals_for"] - record["goals_against"]})

    table.sort(key=lambda r: (r["points"], r["goal_difference"], r["goals_for"]), reverse=True)
    return table


def biggest_wins(df: pd.DataFrame, competition: str | None = None, season: int | None = None, n: int = 10) -> list[dict]:
    subset = df
    if competition is not None:
        subset = subset[subset["competition"] == competition]
    if season is not None:
        subset = subset[subset["season"] == season]
    subset = subset.dropna(subset=["home_goal", "away_goal"]).copy()
    subset["margin"] = (subset["home_goal"] - subset["away_goal"]).abs()
    subset = subset.sort_values("margin", ascending=False).head(n)
    return subset[MATCH_OUTPUT_COLUMNS + ["margin"]].to_dict(orient="records")


def average_goals_per_match(df: pd.DataFrame, competition: str | None = None, season: int | None = None) -> float:
    subset = df
    if competition is not None:
        subset = subset[subset["competition"] == competition]
    if season is not None:
        subset = subset[subset["season"] == season]
    subset = subset.dropna(subset=["home_goal", "away_goal"])
    if len(subset) == 0:
        return 0.0
    return float((subset["home_goal"] + subset["away_goal"]).mean())


def home_win_rate(df: pd.DataFrame, competition: str | None = None, season: int | None = None) -> float:
    subset = df
    if competition is not None:
        subset = subset[subset["competition"] == competition]
    if season is not None:
        subset = subset[subset["season"] == season]
    subset = subset.dropna(subset=["home_goal", "away_goal"])
    if len(subset) == 0:
        return 0.0
    return float((subset["home_goal"] > subset["away_goal"]).mean())


def search_players(df: pd.DataFrame, name: str | None = None, nationality: str | None = None, club: str | None = None, position: str | None = None) -> list[dict]:
    subset = df
    if name is not None:
        subset = subset[subset["name"].str.contains(name, case=False, na=False)]
    if nationality is not None:
        subset = subset[subset["nationality"].str.lower() == nationality.lower()]
    if club is not None:
        club_key = canonical_team_key(club)
        subset = subset[subset["club_key"] == club_key]
    if position is not None:
        subset = subset[subset["position"].str.lower() == position.lower()]
    return subset.to_dict(orient="records")


def top_players(df: pd.DataFrame, n: int = 10, nationality: str | None = None, club: str | None = None) -> list[dict]:
    subset = search_players(df, nationality=nationality, club=club)
    subset = sorted(subset, key=lambda p: p["overall"], reverse=True)
    return subset[:n]
