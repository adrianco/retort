"""Brazilian Soccer MCP Server."""

import json
from typing import Any

import pandas as pd
from mcp.server import FastMCP

from data_loader import store, normalize_team_name, team_matches

app = FastMCP("Brazilian Soccer Knowledge Graph")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_match(row: pd.Series, competition: str | None = None) -> str:
    comp = competition or row.get("competition", "")
    date = row["datetime"].strftime("%Y-%m-%d") if pd.notna(row.get("datetime")) else "unknown date"
    home = row.get("home_team_norm") or row.get("home_team", "?")
    away = row.get("away_team_norm") or row.get("away_team", "?")
    hg = int(row["home_goal"]) if pd.notna(row.get("home_goal")) else "?"
    ag = int(row["away_goal"]) if pd.notna(row.get("away_goal")) else "?"
    season = row.get("season", "")
    rnd = f" Round {int(row['round'])}" if pd.notna(row.get("round")) else ""
    stage = f" ({row['stage']})" if pd.notna(row.get("stage", None)) else ""
    return f"{date}: {home} {hg}-{ag} {away} [{comp} {season}{rnd}{stage}]"


def _filter_team(df: pd.DataFrame, team: str) -> pd.DataFrame:
    mask = df["home_team_norm"].str.lower().str.contains(team.lower(), na=False) | \
           df["away_team_norm"].str.lower().str.contains(team.lower(), na=False)
    return df[mask]


def _filter_competition(df: pd.DataFrame, competition: str) -> pd.DataFrame:
    comp_l = competition.lower()
    mask = df["competition"].str.lower().str.contains(comp_l, na=False)
    return df[mask]


# ---------------------------------------------------------------------------
# Match Tools
# ---------------------------------------------------------------------------

@app.tool()
def find_matches(
    team1: str = "",
    team2: str = "",
    competition: str = "",
    season: int = 0,
    date_from: str = "",
    date_to: str = "",
    limit: int = 20,
) -> str:
    """Search for matches by team(s), competition, season, or date range.

    Args:
        team1: First team name (partial match supported)
        team2: Second team name for head-to-head (partial match supported)
        competition: Competition name (Brasileirao, Copa do Brasil, Libertadores)
        season: Year of the season (e.g. 2023)
        date_from: Start date in YYYY-MM-DD format
        date_to: End date in YYYY-MM-DD format
        limit: Maximum number of matches to return (default 20)
    """
    df = store.all_matches().copy()

    if team1:
        if team2:
            mask = (
                (df["home_team_norm"].str.lower().str.contains(team1.lower(), na=False) &
                 df["away_team_norm"].str.lower().str.contains(team2.lower(), na=False)) |
                (df["home_team_norm"].str.lower().str.contains(team2.lower(), na=False) &
                 df["away_team_norm"].str.lower().str.contains(team1.lower(), na=False))
            )
            df = df[mask]
        else:
            df = _filter_team(df, team1)

    if competition:
        df = _filter_competition(df, competition)

    if season:
        df = df[df["season"] == season]

    if date_from:
        df = df[df["datetime"] >= pd.to_datetime(date_from)]

    if date_to:
        df = df[pd.to_datetime(df["datetime"]) <= pd.to_datetime(date_to)]

    df = df.sort_values("datetime", ascending=False)
    total = len(df)
    df = df.head(limit)

    if df.empty:
        return "No matches found matching the criteria."

    lines = []
    if team1 and team2:
        lines.append(f"Head-to-head: {team1} vs {team2}")
    lines.append(f"Found {total} matches (showing {min(limit, total)}):\n")

    for _, row in df.iterrows():
        lines.append("  " + _fmt_match(row))

    if team1 and team2 and total > 0:
        all_h2h = store.all_matches().copy()
        mask = (
            (all_h2h["home_team_norm"].str.lower().str.contains(team1.lower(), na=False) &
             all_h2h["away_team_norm"].str.lower().str.contains(team2.lower(), na=False)) |
            (all_h2h["home_team_norm"].str.lower().str.contains(team2.lower(), na=False) &
             all_h2h["away_team_norm"].str.lower().str.contains(team1.lower(), na=False))
        )
        h2h = all_h2h[mask]
        t1_wins = ((h2h["home_team_norm"].str.lower().str.contains(team1.lower(), na=False) &
                    (h2h["home_goal"] > h2h["away_goal"])) |
                   (h2h["away_team_norm"].str.lower().str.contains(team1.lower(), na=False) &
                    (h2h["away_goal"] > h2h["home_goal"]))).sum()
        t2_wins = ((h2h["home_team_norm"].str.lower().str.contains(team2.lower(), na=False) &
                    (h2h["home_goal"] > h2h["away_goal"])) |
                   (h2h["away_team_norm"].str.lower().str.contains(team2.lower(), na=False) &
                    (h2h["away_goal"] > h2h["home_goal"]))).sum()
        draws = (h2h["home_goal"] == h2h["away_goal"]).sum()
        lines.append(f"\nHead-to-head record ({len(h2h)} matches total):")
        lines.append(f"  {team1}: {t1_wins} wins | {team2}: {t2_wins} wins | Draws: {draws}")

    return "\n".join(lines)


@app.tool()
def get_recent_matches(team: str, limit: int = 10) -> str:
    """Get the most recent matches for a team.

    Args:
        team: Team name (partial match supported)
        limit: Number of matches to return (default 10)
    """
    df = _filter_team(store.all_matches(), team)
    df = df.sort_values("datetime", ascending=False).head(limit)

    if df.empty:
        return f"No matches found for team '{team}'."

    lines = [f"Recent matches for {team} ({len(df)} shown):\n"]
    for _, row in df.iterrows():
        lines.append("  " + _fmt_match(row))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Team Stats Tools
# ---------------------------------------------------------------------------

@app.tool()
def get_team_stats(team: str, season: int = 0, competition: str = "") -> str:
    """Get win/loss/draw record and goals for a team.

    Args:
        team: Team name (partial match supported)
        season: Filter by season year (0 = all seasons)
        competition: Filter by competition name
    """
    df = store.all_matches().copy()
    if competition:
        df = _filter_competition(df, competition)
    if season:
        df = df[df["season"] == season]

    home = df[df["home_team_norm"].str.lower().str.contains(team.lower(), na=False)]
    away = df[df["away_team_norm"].str.lower().str.contains(team.lower(), na=False)]

    if home.empty and away.empty:
        return f"No matches found for team '{team}'."

    home_w = (home["home_goal"] > home["away_goal"]).sum()
    home_d = (home["home_goal"] == home["away_goal"]).sum()
    home_l = (home["home_goal"] < home["away_goal"]).sum()
    home_gf = home["home_goal"].sum()
    home_ga = home["away_goal"].sum()

    away_w = (away["away_goal"] > away["home_goal"]).sum()
    away_d = (away["away_goal"] == away["home_goal"]).sum()
    away_l = (away["away_goal"] < away["home_goal"]).sum()
    away_gf = away["away_goal"].sum()
    away_ga = away["home_goal"].sum()

    total_m = len(home) + len(away)
    total_w = home_w + away_w
    total_d = home_d + away_d
    total_l = home_l + away_l
    total_gf = home_gf + away_gf
    total_ga = home_ga + away_ga
    win_pct = (total_w / total_m * 100) if total_m > 0 else 0
    pts = total_w * 3 + total_d

    season_str = f" ({season})" if season else ""
    comp_str = f" - {competition}" if competition else ""
    lines = [
        f"Statistics for {team}{season_str}{comp_str}:",
        f"  Total matches: {total_m}",
        f"  Record: {total_w}W / {total_d}D / {total_l}L",
        f"  Goals: {int(total_gf)} scored / {int(total_ga)} conceded (diff: {int(total_gf - total_ga):+d})",
        f"  Points: {pts} | Win rate: {win_pct:.1f}%",
        f"",
        f"  Home: {len(home)} matches | {home_w}W {home_d}D {home_l}L | GF {int(home_gf)} GA {int(home_ga)}",
        f"  Away: {len(away)} matches | {away_w}W {away_d}D {away_l}L | GF {int(away_gf)} GA {int(away_ga)}",
    ]
    return "\n".join(lines)


@app.tool()
def compare_teams(team1: str, team2: str, season: int = 0) -> str:
    """Compare two teams head-to-head statistics.

    Args:
        team1: First team name
        team2: Second team name
        season: Filter by season year (0 = all seasons)
    """
    # Get h2h
    h2h_result = find_matches(team1=team1, team2=team2, season=season, limit=100)
    stats1 = get_team_stats(team1, season=season)
    stats2 = get_team_stats(team2, season=season)

    return f"=== {team1} vs {team2} Comparison ===\n\n{h2h_result}\n\n--- {team1} Overall ---\n{stats1}\n\n--- {team2} Overall ---\n{stats2}"


# ---------------------------------------------------------------------------
# Player Tools
# ---------------------------------------------------------------------------

@app.tool()
def find_players(
    name: str = "",
    nationality: str = "",
    club: str = "",
    position: str = "",
    min_overall: int = 0,
    limit: int = 20,
) -> str:
    """Search for players in the FIFA dataset.

    Args:
        name: Player name (partial match)
        nationality: Player nationality (e.g. 'Brazil', 'Brazilian')
        club: Club name (partial match)
        position: Playing position (GK, CB, LB, RB, CDM, CM, CAM, LW, RW, ST, etc.)
        min_overall: Minimum overall rating
        limit: Maximum results to return (default 20)
    """
    df = store.fifa.copy()

    if name:
        df = df[df["Name"].str.lower().str.contains(name.lower(), na=False)]
    if nationality:
        nat = nationality.lower().replace("brazilian", "brazil")
        df = df[df["Nationality"].str.lower().str.contains(nat, na=False)]
    if club:
        df = df[df["Club"].str.lower().str.contains(club.lower(), na=False)]
    if position:
        df = df[df["Position"].str.lower().str.contains(position.lower(), na=False)]
    if min_overall:
        df = df[df["Overall"] >= min_overall]

    df = df.sort_values("Overall", ascending=False)
    total = len(df)
    df = df.head(limit)

    if df.empty:
        return "No players found matching the criteria."

    lines = [f"Found {total} players (showing {min(limit, total)}):\n"]
    for _, row in df.iterrows():
        name_val = row.get("Name", "?")
        overall = int(row["Overall"]) if pd.notna(row.get("Overall")) else "?"
        potential = int(row["Potential"]) if pd.notna(row.get("Potential")) else "?"
        pos = row.get("Position", "?")
        club_val = row.get("Club", "?")
        nat_val = row.get("Nationality", "?")
        age = int(row["Age"]) if pd.notna(row.get("Age")) else "?"
        lines.append(f"  {name_val} | {nat_val} | {pos} | {club_val} | Overall: {overall} | Potential: {potential} | Age: {age}")

    return "\n".join(lines)


@app.tool()
def get_player_details(name: str) -> str:
    """Get detailed information about a specific player.

    Args:
        name: Player name (partial match, returns best match)
    """
    df = store.fifa.copy()
    df = df[df["Name"].str.lower().str.contains(name.lower(), na=False)]
    df = df.sort_values("Overall", ascending=False)

    if df.empty:
        return f"No player found with name '{name}'."

    row = df.iloc[0]
    skill_cols = ["Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
                  "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
                  "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
                  "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
                  "Aggression", "Interceptions", "Positioning", "Vision", "Penalties", "Composure"]

    lines = [
        f"Player: {row.get('Name', '?')}",
        f"  Age: {row.get('Age', '?')} | Nationality: {row.get('Nationality', '?')}",
        f"  Club: {row.get('Club', '?')} | Position: {row.get('Position', '?')}",
        f"  Overall: {row.get('Overall', '?')} | Potential: {row.get('Potential', '?')}",
        f"  Height: {row.get('Height', '?')} | Weight: {row.get('Weight', '?')}",
        f"  Preferred Foot: {row.get('Preferred Foot', '?')} | Jersey: {row.get('Jersey Number', '?')}",
        f"  Value: {row.get('Value', '?')} | Wage: {row.get('Wage', '?')}",
        f"\n  Key Skills:",
    ]
    for col in skill_cols:
        if col in row.index and pd.notna(row[col]):
            lines.append(f"    {col}: {row[col]}")

    return "\n".join(lines)


@app.tool()
def get_club_players(club: str, min_overall: int = 0) -> str:
    """Get all players at a specific club, sorted by overall rating.

    Args:
        club: Club name (partial match)
        min_overall: Minimum overall rating filter
    """
    df = store.fifa.copy()
    df = df[df["Club"].str.lower().str.contains(club.lower(), na=False)]
    if min_overall:
        df = df[df["Overall"] >= min_overall]
    df = df.sort_values("Overall", ascending=False)

    if df.empty:
        return f"No players found at club '{club}'."

    lines = [f"Players at {club} ({len(df)} total):\n"]
    for _, row in df.iterrows():
        lines.append(f"  {row.get('Name','?')} | {row.get('Position','?')} | {row.get('Nationality','?')} | Overall: {int(row['Overall']) if pd.notna(row.get('Overall')) else '?'}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Competition / Standings Tools
# ---------------------------------------------------------------------------

@app.tool()
def get_league_standings(season: int, competition: str = "Brasileirao") -> str:
    """Calculate league standings for a given season from match results.

    Args:
        season: The season year (e.g. 2023)
        competition: Competition name (default: Brasileirao Serie A)
    """
    df = store.all_matches().copy()
    df = df[df["season"] == season]
    df = _filter_competition(df, competition)
    df = df.dropna(subset=["home_goal", "away_goal"])

    if df.empty:
        return f"No match data found for {competition} season {season}."

    standings: dict[str, dict[str, int]] = {}

    def add_team(name: str) -> None:
        if name not in standings:
            standings[name] = {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}

    for _, row in df.iterrows():
        home = row["home_team_norm"]
        away = row["away_team_norm"]
        hg = int(row["home_goal"])
        ag = int(row["away_goal"])
        add_team(home)
        add_team(away)
        standings[home]["P"] += 1
        standings[away]["P"] += 1
        standings[home]["GF"] += hg
        standings[home]["GA"] += ag
        standings[away]["GF"] += ag
        standings[away]["GA"] += hg
        if hg > ag:
            standings[home]["W"] += 1
            standings[home]["Pts"] += 3
            standings[away]["L"] += 1
        elif ag > hg:
            standings[away]["W"] += 1
            standings[away]["Pts"] += 3
            standings[home]["L"] += 1
        else:
            standings[home]["D"] += 1
            standings[away]["D"] += 1
            standings[home]["Pts"] += 1
            standings[away]["Pts"] += 1

    sorted_teams = sorted(
        standings.items(),
        key=lambda x: (x[1]["Pts"], x[1]["W"], x[1]["GF"] - x[1]["GA"]),
        reverse=True,
    )

    lines = [f"{competition} {season} Standings (calculated from {len(df)} matches):\n"]
    lines.append(f"  {'#':>3}  {'Team':<30} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4}")
    lines.append("  " + "-" * 65)
    for i, (team, s) in enumerate(sorted_teams, 1):
        gd = s["GF"] - s["GA"]
        lines.append(
            f"  {i:>3}. {team:<30} {s['P']:>3} {s['W']:>3} {s['D']:>3} {s['L']:>3} {s['GF']:>4} {s['GA']:>4} {gd:>+4} {s['Pts']:>4}"
        )

    return "\n".join(lines)


@app.tool()
def get_competition_history(team: str, competition: str = "") -> str:
    """Get a team's history across competitions.

    Args:
        team: Team name (partial match)
        competition: Filter by competition (optional)
    """
    df = store.all_matches().copy()
    if competition:
        df = _filter_competition(df, competition)
    df = _filter_team(df, team)

    if df.empty:
        return f"No matches found for '{team}'."

    by_comp = df.groupby("competition")
    lines = [f"Competition history for {team}:\n"]
    for comp, group in sorted(by_comp):
        seasons = sorted(group["season"].dropna().unique())
        lines.append(f"  {comp}: {len(group)} matches across {len(seasons)} seasons ({int(min(seasons)) if len(seasons) > 0 else '?'}-{int(max(seasons)) if len(seasons) > 0 else '?'})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Statistical Analysis Tools
# ---------------------------------------------------------------------------

@app.tool()
def get_top_scorers_teams(season: int = 0, competition: str = "", top_n: int = 10) -> str:
    """Get teams ranked by goals scored.

    Args:
        season: Filter by season year (0 = all seasons)
        competition: Filter by competition
        top_n: Number of teams to show (default 10)
    """
    df = store.all_matches().copy()
    if season:
        df = df[df["season"] == season]
    if competition:
        df = _filter_competition(df, competition)
    df = df.dropna(subset=["home_goal", "away_goal"])

    goals: dict[str, int] = {}
    for _, row in df.iterrows():
        home = row["home_team_norm"]
        away = row["away_team_norm"]
        goals[home] = goals.get(home, 0) + int(row["home_goal"])
        goals[away] = goals.get(away, 0) + int(row["away_goal"])

    sorted_goals = sorted(goals.items(), key=lambda x: x[1], reverse=True)[:top_n]
    season_str = f" {season}" if season else ""
    comp_str = f" ({competition})" if competition else ""
    lines = [f"Top {top_n} goal-scoring teams{season_str}{comp_str}:\n"]
    for i, (team, g) in enumerate(sorted_goals, 1):
        lines.append(f"  {i:>3}. {team:<30} {g:>5} goals")
    return "\n".join(lines)


@app.tool()
def get_biggest_wins(competition: str = "", season: int = 0, limit: int = 10) -> str:
    """Get the biggest victories by goal difference.

    Args:
        competition: Filter by competition
        season: Filter by season year
        limit: Number of results (default 10)
    """
    df = store.all_matches().copy()
    if competition:
        df = _filter_competition(df, competition)
    if season:
        df = df[df["season"] == season]
    df = df.dropna(subset=["home_goal", "away_goal"])
    df["goal_diff"] = (df["home_goal"] - df["away_goal"]).abs()
    df = df.sort_values("goal_diff", ascending=False).head(limit)

    if df.empty:
        return "No matches found."

    lines = [f"Biggest victories (by goal difference):\n"]
    for _, row in df.iterrows():
        diff = int(row["goal_diff"])
        lines.append(f"  {_fmt_match(row)} [diff: {diff}]")
    return "\n".join(lines)


@app.tool()
def get_competition_summary(competition: str = "", season: int = 0) -> str:
    """Get aggregate statistics for a competition.

    Args:
        competition: Competition name (partial match)
        season: Filter by season year (0 = all seasons)
    """
    df = store.all_matches().copy()
    if competition:
        df = _filter_competition(df, competition)
    if season:
        df = df[df["season"] == season]
    df = df.dropna(subset=["home_goal", "away_goal"])

    if df.empty:
        return "No match data found."

    total = len(df)
    total_goals = df["home_goal"].sum() + df["away_goal"].sum()
    avg_goals = total_goals / total if total > 0 else 0
    home_wins = (df["home_goal"] > df["away_goal"]).sum()
    away_wins = (df["away_goal"] > df["home_goal"]).sum()
    draws = (df["home_goal"] == df["away_goal"]).sum()

    season_str = f" {season}" if season else " (all seasons)"
    comp_str = competition if competition else "All competitions"

    lines = [
        f"Summary: {comp_str}{season_str}",
        f"  Total matches: {total}",
        f"  Total goals: {int(total_goals)}",
        f"  Average goals per match: {avg_goals:.2f}",
        f"  Home wins: {home_wins} ({home_wins/total*100:.1f}%)",
        f"  Away wins: {away_wins} ({away_wins/total*100:.1f}%)",
        f"  Draws: {draws} ({draws/total*100:.1f}%)",
    ]
    if season == 0:
        seasons = sorted(df["season"].dropna().unique())
        if len(seasons) > 0:
            lines.append(f"  Seasons covered: {int(min(seasons))}-{int(max(seasons))}")
    return "\n".join(lines)


@app.tool()
def get_home_away_performance(team: str = "", top_n: int = 10) -> str:
    """Get home vs away performance breakdown. If no team given, ranks all teams by home win rate.

    Args:
        team: Team name (optional; if empty, returns top teams by home record)
        top_n: Number of teams to show when no team specified
    """
    df = store.all_matches().copy()
    df = df.dropna(subset=["home_goal", "away_goal"])

    if team:
        home = df[df["home_team_norm"].str.lower().str.contains(team.lower(), na=False)]
        away = df[df["away_team_norm"].str.lower().str.contains(team.lower(), na=False)]
        hw = (home["home_goal"] > home["away_goal"]).sum()
        hd = (home["home_goal"] == home["away_goal"]).sum()
        hl = (home["home_goal"] < home["away_goal"]).sum()
        aw = (away["away_goal"] > away["home_goal"]).sum()
        ad = (away["away_goal"] == away["home_goal"]).sum()
        al = (away["away_goal"] < away["home_goal"]).sum()
        hwr = hw / len(home) * 100 if len(home) > 0 else 0
        awr = aw / len(away) * 100 if len(away) > 0 else 0
        return (
            f"{team} home/away breakdown:\n"
            f"  Home: {len(home)} matches | {hw}W {hd}D {hl}L | Win rate: {hwr:.1f}%\n"
            f"  Away: {len(away)} matches | {aw}W {ad}D {al}L | Win rate: {awr:.1f}%"
        )

    # Rank all teams by home win rate
    stats: dict[str, dict] = {}
    for _, row in df.iterrows():
        home_t = row["home_team_norm"]
        away_t = row["away_team_norm"]
        if home_t not in stats:
            stats[home_t] = {"hm": 0, "hw": 0}
        if away_t not in stats:
            stats[away_t] = {"hm": 0, "hw": 0}
        stats[home_t]["hm"] += 1
        if row["home_goal"] > row["away_goal"]:
            stats[home_t]["hw"] += 1

    ranked = [(t, s["hw"] / s["hm"] * 100) for t, s in stats.items() if s["hm"] >= 10]
    ranked.sort(key=lambda x: x[1], reverse=True)
    lines = [f"Top {top_n} teams by home win rate (min 10 home matches):\n"]
    for i, (t, rate) in enumerate(ranked[:top_n], 1):
        hm = stats[t]["hm"]
        hw = stats[t]["hw"]
        lines.append(f"  {i:>3}. {t:<30} {hw}/{hm} home wins ({rate:.1f}%)")
    return "\n".join(lines)


@app.tool()
def list_seasons(competition: str = "") -> str:
    """List all available seasons in the dataset.

    Args:
        competition: Filter by competition (optional)
    """
    df = store.all_matches().copy()
    if competition:
        df = _filter_competition(df, competition)
    seasons = sorted(df["season"].dropna().unique())
    comp_str = f" ({competition})" if competition else ""
    return f"Available seasons{comp_str}: {', '.join(str(int(s)) for s in seasons)}"


@app.tool()
def list_teams(competition: str = "", season: int = 0) -> str:
    """List all teams in the dataset.

    Args:
        competition: Filter by competition
        season: Filter by season year
    """
    df = store.all_matches().copy()
    if competition:
        df = _filter_competition(df, competition)
    if season:
        df = df[df["season"] == season]

    teams = set(df["home_team_norm"].dropna().tolist()) | set(df["away_team_norm"].dropna().tolist())
    teams = sorted(teams)
    season_str = f" {season}" if season else ""
    comp_str = f" ({competition})" if competition else ""
    lines = [f"Teams{comp_str}{season_str} ({len(teams)} total):\n"]
    for t in teams:
        lines.append(f"  {t}")
    return "\n".join(lines)


if __name__ == "__main__":
    app.run(transport="stdio")
