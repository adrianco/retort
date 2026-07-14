"""
Brazilian Soccer MCP Server.

Exposes knowledge-graph tools for querying Brazilian soccer data:
players, matches, team statistics, standings, and head-to-head records.
"""

import json
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from data_loader import DataLoader, normalize_team_name

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

mcp = FastMCP("Brazilian Soccer MCP Server")
_loader = DataLoader(DATA_DIR)
_loader.load_all()  # load at import time; fast enough for demo use


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _team_filter(df, team: str):
    t = team.lower()
    mask = df["home_team"].str.lower().str.contains(t, regex=False, na=False) | \
           df["away_team"].str.lower().str.contains(t, regex=False, na=False)
    return df[mask]


def _row_to_match(row) -> dict:
    return {
        "date": str(row["date"]),
        "home_team": str(row["home_team"]),
        "away_team": str(row["away_team"]),
        "home_goals": int(row["home_goals"]),
        "away_goals": int(row["away_goals"]),
        "competition": str(row["competition"]),
        "season": int(row["season"]) if row["season"] else 0,
        "round_or_stage": str(row["round_or_stage"]),
    }


# ---------------------------------------------------------------------------
# Tool: find_matches
# ---------------------------------------------------------------------------

@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    team1: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> str:
    """
    Search for matches across all Brazilian soccer datasets.

    Args:
        team: Filter by a single team name (home or away).
        team1: First team for a head-to-head search (use with team2).
        team2: Second team for a head-to-head search (use with team1).
        competition: Filter by competition. One of: brasileirao, copa_do_brasil,
                     libertadores, serie_b, serie_c.
        season: Filter by season year.
        date_from: Earliest date (YYYY-MM-DD inclusive).
        date_to: Latest date (YYYY-MM-DD inclusive).
        limit: Maximum number of matches to return (default 50).

    Returns:
        JSON with total_found, showing, and a list of match objects.
    """
    df = _loader.get_all_matches()

    if team:
        df = _team_filter(df, team)

    if team1 and team2:
        t1, t2 = team1.lower(), team2.lower()
        mask = (
            (df["home_team"].str.lower().str.contains(t1, regex=False, na=False) &
             df["away_team"].str.lower().str.contains(t2, regex=False, na=False)) |
            (df["home_team"].str.lower().str.contains(t2, regex=False, na=False) &
             df["away_team"].str.lower().str.contains(t1, regex=False, na=False))
        )
        df = df[mask]
    elif team1:
        df = _team_filter(df, team1)

    if competition:
        comp = competition.lower()
        df = df[df["competition"].str.lower().str.contains(comp, regex=False, na=False)]

    if season is not None:
        df = df[df["season"] == season]

    if date_from:
        df = df[df["date"] >= date_from]

    if date_to:
        df = df[df["date"] <= date_to]

    df = df.sort_values("date", ascending=False)
    total = int(len(df))
    df = df.head(limit)

    matches = [_row_to_match(row) for _, row in df.iterrows()]

    return json.dumps(
        {"total_found": total, "showing": len(matches), "matches": matches},
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Tool: get_team_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """
    Calculate win/draw/loss statistics for a team.

    Args:
        team: Team name to analyse.
        competition: Optional competition filter (brasileirao, copa_do_brasil, libertadores).
        season: Optional season year.

    Returns:
        JSON with team name, matches_played, wins, draws, losses, points,
        goals_for, goals_against, goal_difference, and win_rate.
    """
    # Choose dataset: prefer primary Brasileirao for brasileirao competition
    if competition and "brasileirao" in competition.lower():
        df = _loader.get_brasileirao_matches()
        if season and season < 2012:
            df = _loader.get_historical_matches()
    elif competition and "copa_do_brasil" in competition.lower():
        df = _loader.get_copa_matches()
    elif competition and "libertadores" in competition.lower():
        df = _loader.get_libertadores_matches()
    else:
        df = _loader.get_all_matches()

    df = _team_filter(df, team)

    if season is not None:
        df = df[df["season"] == season]

    if competition:
        comp = competition.lower()
        df = df[df["competition"].str.lower().str.contains(comp, regex=False, na=False)]

    wins = draws = losses = goals_for = goals_against = 0
    t = team.lower()

    for _, row in df.iterrows():
        home = str(row["home_team"]).lower()
        is_home = t in home
        hg, ag = int(row["home_goals"]), int(row["away_goals"])

        if is_home:
            gf, ga = hg, ag
        else:
            gf, ga = ag, hg

        goals_for += gf
        goals_against += ga

        if gf > ga:
            wins += 1
        elif gf == ga:
            draws += 1
        else:
            losses += 1

    played = wins + draws + losses
    points = wins * 3 + draws
    win_rate = round(wins / played * 100, 1) if played else 0.0

    return json.dumps({
        "team": team,
        "competition": competition or "all",
        "season": season,
        "matches_played": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "points": points,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goals_for - goals_against,
        "win_rate": win_rate,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: find_players
# ---------------------------------------------------------------------------

@mcp.tool()
def find_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> str:
    """
    Search FIFA player data.

    Args:
        name: Substring search on player name.
        nationality: Exact nationality filter (e.g. "Brazil").
        club: Substring search on club name.
        position: Exact position filter (e.g. "GK", "CB", "LW").
        min_overall: Minimum FIFA overall rating.
        limit: Maximum players to return (default 20, returned sorted by Overall desc).

    Returns:
        JSON with total_found and a list of player objects.
    """
    df = _loader.get_players()

    if name:
        df = df[df["Name"].str.contains(name, case=False, na=False)]

    if nationality:
        df = df[df["Nationality"] == nationality]

    if club:
        df = df[df["Club"].str.contains(club, case=False, na=False)]

    if position:
        df = df[df["Position"] == position]

    if min_overall is not None:
        df = df[df["Overall"] >= min_overall]

    df = df.sort_values("Overall", ascending=False)
    total = int(len(df))
    df = df.head(limit)

    players = []
    for _, row in df.iterrows():
        players.append({
            "name": str(row.get("Name", "")),
            "nationality": str(row.get("Nationality", "")),
            "overall": int(row.get("Overall", 0)),
            "potential": int(row.get("Potential", 0)),
            "club": str(row.get("Club", "")),
            "position": str(row.get("Position", "")),
            "age": int(row.get("Age", 0)),
            "value": str(row.get("Value", "")),
            "wage": str(row.get("Wage", "")),
        })

    return json.dumps(
        {"total_found": total, "showing": len(players), "players": players},
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Tool: get_head_to_head
# ---------------------------------------------------------------------------

@mcp.tool()
def get_head_to_head(
    team1: str,
    team2: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """
    Get head-to-head record between two teams.

    Args:
        team1: First team name.
        team2: Second team name.
        competition: Optional competition filter.
        season: Optional season filter.

    Returns:
        JSON with team names, total_matches, team1_wins, team2_wins, draws,
        goals_for_team1, goals_for_team2, and recent_matches list.
    """
    df = _loader.get_all_matches()

    t1, t2 = team1.lower(), team2.lower()
    mask = (
        (df["home_team"].str.lower().str.contains(t1, regex=False, na=False) &
         df["away_team"].str.lower().str.contains(t2, regex=False, na=False)) |
        (df["home_team"].str.lower().str.contains(t2, regex=False, na=False) &
         df["away_team"].str.lower().str.contains(t1, regex=False, na=False))
    )
    df = df[mask]

    if competition:
        comp = competition.lower()
        df = df[df["competition"].str.lower().str.contains(comp, regex=False, na=False)]

    if season is not None:
        df = df[df["season"] == season]

    t1_wins = t2_wins = draws = t1_goals = t2_goals = 0

    for _, row in df.iterrows():
        home = str(row["home_team"]).lower()
        hg, ag = int(row["home_goals"]), int(row["away_goals"])

        if t1 in home:
            gf1, gf2 = hg, ag
        else:
            gf1, gf2 = ag, hg

        t1_goals += gf1
        t2_goals += gf2

        if gf1 > gf2:
            t1_wins += 1
        elif gf1 < gf2:
            t2_wins += 1
        else:
            draws += 1

    total = t1_wins + t2_wins + draws

    df_sorted = df.sort_values("date", ascending=False).head(10)
    recent = [_row_to_match(row) for _, row in df_sorted.iterrows()]

    return json.dumps({
        "team1": team1,
        "team2": team2,
        "total_matches": total,
        "team1_wins": t1_wins,
        "team2_wins": t2_wins,
        "draws": draws,
        "goals_for_team1": t1_goals,
        "goals_for_team2": t2_goals,
        "recent_matches": recent,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: get_standings
# ---------------------------------------------------------------------------

@mcp.tool()
def get_standings(
    season: int,
    competition: str = "brasileirao",
) -> str:
    """
    Calculate standings table for a competition and season.

    Args:
        season: Season year (e.g. 2019).
        competition: Competition name (default: brasileirao).

    Returns:
        JSON with season, competition, and standings list sorted by points.
    """
    if "brasileirao" in competition.lower():
        if season >= 2012:
            df = _loader.get_brasileirao_matches()
        else:
            df = _loader.get_historical_matches()
        df = df[df["competition"] == "brasileirao"]
    elif "copa_do_brasil" in competition.lower():
        df = _loader.get_copa_matches()
    elif "libertadores" in competition.lower():
        df = _loader.get_libertadores_matches()
    else:
        df = _loader.get_all_matches()
        comp_lower = competition.lower()
        df = df[df["competition"].str.lower().str.contains(comp_lower, regex=False, na=False)]

    df = df[df["season"] == season].copy()

    # Accumulate points per team
    teams: dict[str, dict] = {}

    def _get(team: str) -> dict:
        if team not in teams:
            teams[team] = dict(played=0, wins=0, draws=0, losses=0,
                               gf=0, ga=0, points=0)
        return teams[team]

    for _, row in df.iterrows():
        ht = str(row["home_team"])
        at = str(row["away_team"])
        hg = int(row["home_goals"])
        ag = int(row["away_goals"])

        h = _get(ht)
        a = _get(at)

        h["played"] += 1
        a["played"] += 1
        h["gf"] += hg
        h["ga"] += ag
        a["gf"] += ag
        a["ga"] += hg

        if hg > ag:
            h["wins"] += 1
            h["points"] += 3
            a["losses"] += 1
        elif hg < ag:
            a["wins"] += 1
            a["points"] += 3
            h["losses"] += 1
        else:
            h["draws"] += 1
            a["draws"] += 1
            h["points"] += 1
            a["points"] += 1

    standings = []
    for team, s in teams.items():
        standings.append({
            "team": team,
            "played": s["played"],
            "wins": s["wins"],
            "draws": s["draws"],
            "losses": s["losses"],
            "goals_for": s["gf"],
            "goals_against": s["ga"],
            "goal_difference": s["gf"] - s["ga"],
            "points": s["points"],
        })

    standings.sort(key=lambda x: (-x["points"], -x["goal_difference"], -x["goals_for"]))

    return json.dumps({
        "season": season,
        "competition": competition,
        "total_teams": len(standings),
        "standings": standings,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: get_statistics
# ---------------------------------------------------------------------------

@mcp.tool()
def get_statistics(
    stat_type: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """
    Calculate aggregate statistics across Brazilian soccer datasets.

    Args:
        stat_type: One of: biggest_wins, goals_per_match, home_win_rate,
                   top_scoring_teams.
        competition: Optional competition filter.
        season: Optional season filter.
        limit: Max results to return.

    Returns:
        JSON with the requested statistics.
    """
    df = _loader.get_all_matches()

    if competition:
        comp = competition.lower()
        df = df[df["competition"].str.lower().str.contains(comp, regex=False, na=False)]

    if season is not None:
        df = df[df["season"] == season]

    stat = stat_type.lower()

    if stat == "biggest_wins":
        df = df.copy()
        df["goal_difference"] = (df["home_goals"] - df["away_goals"]).abs()
        df = df.sort_values("goal_difference", ascending=False).head(limit)
        results = []
        for _, row in df.iterrows():
            results.append({
                **_row_to_match(row),
                "goal_difference": int(abs(row["home_goals"] - row["away_goals"])),
            })
        return json.dumps({"stat_type": stat_type, "results": results}, ensure_ascii=False)

    if stat == "goals_per_match":
        total_matches = int(len(df))
        total_goals = int(df["home_goals"].sum() + df["away_goals"].sum())
        avg = round(total_goals / total_matches, 2) if total_matches else 0.0
        return json.dumps({
            "stat_type": stat_type,
            "total_matches": total_matches,
            "total_goals": total_goals,
            "average_goals_per_match": avg,
        }, ensure_ascii=False)

    if stat == "home_win_rate":
        total = int(len(df))
        home_wins = int((df["home_goals"] > df["away_goals"]).sum())
        away_wins = int((df["home_goals"] < df["away_goals"]).sum())
        draws = total - home_wins - away_wins
        return json.dumps({
            "stat_type": stat_type,
            "total_matches": total,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(home_wins / total * 100, 1) if total else 0.0,
        }, ensure_ascii=False)

    if stat == "top_scoring_teams":
        df = df.copy()
        home = df.groupby("home_team")["home_goals"].sum().rename("goals")
        away = df.groupby("away_team")["away_goals"].sum().rename("goals")
        combined = home.add(away, fill_value=0).sort_values(ascending=False)
        results = [
            {"team": team, "total_goals": int(goals)}
            for team, goals in combined.head(limit).items()
        ]
        return json.dumps({"stat_type": stat_type, "results": results}, ensure_ascii=False)

    return json.dumps(
        {"error": f"Unknown stat_type: {stat_type}. Use: biggest_wins, goals_per_match, "
                  "home_win_rate, top_scoring_teams"},
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
