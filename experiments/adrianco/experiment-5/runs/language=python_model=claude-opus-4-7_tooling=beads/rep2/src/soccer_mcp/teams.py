"""Team-level aggregate queries.

Given a loaded :class:`SoccerData`, compute the things a fan would ask about a
single club: a season-by-season record, a home/away split, the best/worst
results, etc. Everything in here ultimately walks the combined ``matches``
frame, so adding a new competition (or expanding the filter set in
``matches.find_matches``) automatically shows up here too.
"""

from __future__ import annotations

import pandas as pd

from soccer_mcp.data import SoccerData, normalize_team_name


def _team_mask(df: pd.DataFrame, team_norm: str, side: str = "any") -> pd.Series:
    if side == "home":
        return df["home_team_norm"] == team_norm
    if side == "away":
        return df["away_team_norm"] == team_norm
    return (df["home_team_norm"] == team_norm) | (df["away_team_norm"] == team_norm)


def team_record(
    data: SoccerData,
    team: str,
    competition: str | None = None,
    season: int | None = None,
    side: str = "any",
) -> dict:
    """Return wins/draws/losses, goals for/against, and a derived win rate.

    ``side`` is one of ``"any"``, ``"home"``, ``"away"`` — useful for the
    "Corinthians home record in 2022" type of question.
    """
    team_norm = normalize_team_name(team)
    df = data.matches
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    if season is not None:
        df = df[df["season"] == season]
    df = df[_team_mask(df, team_norm, side)]
    df = df.dropna(subset=["home_goal", "away_goal"])

    wins = draws = losses = goals_for = goals_against = 0
    for _, row in df.iterrows():
        home = row["home_team_norm"] == team_norm
        gf = int(row["home_goal"] if home else row["away_goal"])
        ga = int(row["away_goal"] if home else row["home_goal"])
        goals_for += gf
        goals_against += ga
        if gf > ga:
            wins += 1
        elif gf == ga:
            draws += 1
        else:
            losses += 1

    played = wins + draws + losses
    return {
        "team": team,
        "competition": competition,
        "season": season,
        "side": side,
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goals_for - goals_against,
        "points": wins * 3 + draws,
        "win_rate": (wins / played) if played else 0.0,
    }


def home_away_split(data: SoccerData, team: str, competition: str | None = None, season: int | None = None) -> dict:
    """Convenience wrapper returning both the home and away records side by side."""
    home = team_record(data, team, competition=competition, season=season, side="home")
    away = team_record(data, team, competition=competition, season=season, side="away")
    return {"team": team, "competition": competition, "season": season, "home": home, "away": away}


def team_seasons(data: SoccerData, team: str) -> list[int]:
    """Every season for which we have at least one match featuring this team."""
    team_norm = normalize_team_name(team)
    df = data.matches
    df = df[_team_mask(df, team_norm)]
    return sorted(int(s) for s in df["season"].dropna().unique())


def team_competitions(data: SoccerData, team: str) -> list[str]:
    """Every competition we have data for that this team has appeared in."""
    team_norm = normalize_team_name(team)
    df = data.matches
    df = df[_team_mask(df, team_norm)]
    return sorted(df["competition"].dropna().unique().tolist())


def compare_teams(
    data: SoccerData,
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Side-by-side records and head-to-head record between two teams."""
    from soccer_mcp.matches import head_to_head

    return {
        "team_a_record": team_record(data, team_a, competition=competition, season=season),
        "team_b_record": team_record(data, team_b, competition=competition, season=season),
        "head_to_head": head_to_head(data, team_a, team_b, competition=competition),
    }


def top_scoring_teams(
    data: SoccerData,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> list[dict]:
    """Teams with the most goals scored in the chosen scope."""
    df = data.matches
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    if season is not None:
        df = df[df["season"] == season]
    df = df.dropna(subset=["home_goal", "away_goal"])

    home_goals = df.groupby("home_team_norm")["home_goal"].sum()
    away_goals = df.groupby("away_team_norm")["away_goal"].sum()
    totals = home_goals.add(away_goals, fill_value=0).sort_values(ascending=False).head(limit)

    aliases = data.team_aliases()
    out = []
    for norm, goals in totals.items():
        display = next(iter(aliases.get(norm, [norm])))
        out.append({"team": display, "team_norm": norm, "goals_scored": int(goals)})
    return out
