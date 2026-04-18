"""Brazilian Soccer MCP Server."""

import json
from typing import Optional
import pandas as pd
from mcp.server.fastmcp import FastMCP

from data_loader import (
    load_brasileirao,
    load_copa_brasil,
    load_libertadores,
    load_br_football,
    load_historico,
    load_fifa,
    load_all_matches,
    filter_by_team,
    normalize_team_name,
)

mcp = FastMCP("Brazilian Soccer MCP Server")


def _format_match(row: pd.Series) -> str:
    """Format a single match row as a string."""
    date_str = ""
    if pd.notna(row.get("datetime")):
        date_str = str(row["datetime"])[:10]

    home = row.get("home_team", "?")
    away = row.get("away_team", "?")
    hg = int(row["home_goal"]) if pd.notna(row.get("home_goal")) else "?"
    ag = int(row["away_goal"]) if pd.notna(row.get("away_goal")) else "?"
    comp = row.get("competition", "")
    season = row.get("season", "")
    rnd = row.get("round", "")

    parts = [f"{date_str}: {home} {hg}-{ag} {away}"]
    meta = []
    if comp:
        meta.append(str(comp))
    if season and pd.notna(season):
        meta.append(f"Season {int(season)}")
    if rnd and pd.notna(rnd):
        meta.append(f"Round {rnd}")
    if meta:
        parts.append(f"({', '.join(meta)})")
    return " ".join(parts)


@mcp.tool()
def search_matches(
    team: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    season_from: Optional[int] = None,
    season_to: Optional[int] = None,
    role: str = "either",
    limit: int = 20,
) -> str:
    """Search for soccer matches across all competitions.

    Args:
        team: Team name to search for (partial match supported)
        team2: Second team name for head-to-head search
        competition: Filter by competition name ('brasileirao', 'copa brasil', 'libertadores', 'all')
        season: Filter by specific season year
        season_from: Start year for date range filter
        season_to: End year for date range filter
        role: Team role - 'home', 'away', or 'either' (default)
        limit: Maximum number of matches to return (default 20)

    Returns:
        Formatted list of matches with scores and metadata
    """
    # Select dataset(s)
    comp_lower = (competition or "").lower()
    if "copa do brasil" in comp_lower or "copa brasil" in comp_lower or "cup" in comp_lower:
        df = load_copa_brasil()
    elif "libertadores" in comp_lower:
        df = load_libertadores()
    elif "brasileirao" in comp_lower or "serie a" in comp_lower or "brazilian championship" in comp_lower:
        df = load_brasileirao()
    else:
        df = load_all_matches()

    # Filter by team
    if team:
        df = filter_by_team(df, team, role)

    # Filter by second team (head-to-head)
    if team2 and len(df) > 0:
        team2_lower = normalize_team_name(team2).lower()
        home_mask = df["home_team_norm"].str.lower().str.contains(team2_lower, na=False, regex=False)
        away_mask = df["away_team_norm"].str.lower().str.contains(team2_lower, na=False, regex=False)
        df = df[home_mask | away_mask]

    # Filter by season
    if season is not None:
        df = df[df["season"] == season]
    elif season_from or season_to:
        if season_from:
            df = df[df["season"] >= season_from]
        if season_to:
            df = df[df["season"] <= season_to]

    # Sort by date descending
    df = df.sort_values("datetime", ascending=False)

    total = len(df)
    df_show = df.head(limit)

    lines = [f"Found {total} match(es)"]
    if total > limit:
        lines.append(f"(showing first {limit})")
    lines.append("")

    for _, row in df_show.iterrows():
        lines.append(_format_match(row))

    return "\n".join(lines)


@mcp.tool()
def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    role: str = "either",
) -> str:
    """Get win/loss/draw statistics for a team.

    Args:
        team: Team name
        competition: Optional competition filter ('brasileirao', 'copa brasil', 'libertadores')
        season: Optional season year filter
        role: 'home', 'away', or 'either' (default)

    Returns:
        Team statistics including wins, draws, losses, goals scored/conceded
    """
    comp_lower = (competition or "").lower()
    if "copa do brasil" in comp_lower or "copa brasil" in comp_lower or "cup" in comp_lower:
        df = load_copa_brasil()
    elif "libertadores" in comp_lower:
        df = load_libertadores()
    elif "brasileirao" in comp_lower or "serie a" in comp_lower:
        df = load_brasileirao()
    else:
        df = load_all_matches()

    df = filter_by_team(df, team, role)

    if season is not None:
        df = df[df["season"] == season]

    if len(df) == 0:
        return f"No matches found for team '{team}'"

    team_lower = normalize_team_name(team).lower()

    wins = draws = losses = gf = ga = 0
    home_wins = home_draws = home_losses = 0
    away_wins = away_draws = away_losses = 0

    for _, row in df.iterrows():
        is_home = team_lower in str(row["home_team_norm"]).lower()
        hg = row.get("home_goal", 0) or 0
        ag = row.get("away_goal", 0) or 0
        if pd.isna(hg) or pd.isna(ag):
            continue
        hg, ag = int(hg), int(ag)

        if is_home:
            gf += hg
            ga += ag
            if hg > ag:
                wins += 1
                home_wins += 1
            elif hg == ag:
                draws += 1
                home_draws += 1
            else:
                losses += 1
                home_losses += 1
        else:
            gf += ag
            ga += hg
            if ag > hg:
                wins += 1
                away_wins += 1
            elif ag == hg:
                draws += 1
                away_draws += 1
            else:
                losses += 1
                away_losses += 1

    total = wins + draws + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    pts = wins * 3 + draws

    label = team
    comp_label = competition or "All Competitions"
    season_label = f" {season}" if season else ""

    lines = [
        f"{label} — {comp_label}{season_label}",
        f"Matches: {total}",
        f"Record: {wins}W / {draws}D / {losses}L",
        f"Points: {pts}",
        f"Goals For: {gf}, Goals Against: {ga}, GD: {gf - ga}",
        f"Win Rate: {win_rate:.1f}%",
        "",
        f"Home: {home_wins}W / {home_draws}D / {home_losses}L",
        f"Away: {away_wins}W / {away_draws}D / {away_losses}L",
    ]
    return "\n".join(lines)


@mcp.tool()
def head_to_head(team1: str, team2: str, competition: Optional[str] = None, season: Optional[int] = None) -> str:
    """Get head-to-head record between two teams.

    Args:
        team1: First team name
        team2: Second team name
        competition: Optional competition filter
        season: Optional season filter

    Returns:
        Head-to-head record, recent matches, and statistics
    """
    comp_lower = (competition or "").lower()
    if "copa do brasil" in comp_lower or "copa brasil" in comp_lower or "cup" in comp_lower:
        df = load_copa_brasil()
    elif "libertadores" in comp_lower:
        df = load_libertadores()
    elif "brasileirao" in comp_lower or "serie a" in comp_lower:
        df = load_brasileirao()
    else:
        df = load_all_matches()

    t1_lower = normalize_team_name(team1).lower()
    t2_lower = normalize_team_name(team2).lower()

    home1_mask = df["home_team_norm"].str.lower().str.contains(t1_lower, na=False, regex=False)
    away1_mask = df["away_team_norm"].str.lower().str.contains(t1_lower, na=False, regex=False)
    home2_mask = df["home_team_norm"].str.lower().str.contains(t2_lower, na=False, regex=False)
    away2_mask = df["away_team_norm"].str.lower().str.contains(t2_lower, na=False, regex=False)

    mask = (home1_mask & away2_mask) | (home2_mask & away1_mask)
    df = df[mask]

    if season is not None:
        df = df[df["season"] == season]

    df = df.sort_values("datetime", ascending=False)

    if len(df) == 0:
        return f"No matches found between '{team1}' and '{team2}'"

    t1_wins = t2_wins = draws = 0
    t1_gf = t2_gf = 0

    for _, row in df.iterrows():
        hg = row.get("home_goal")
        ag = row.get("away_goal")
        if pd.isna(hg) or pd.isna(ag):
            continue
        hg, ag = int(hg), int(ag)
        is_t1_home = t1_lower in str(row["home_team_norm"]).lower()
        if is_t1_home:
            t1_gf += hg
            t2_gf += ag
            if hg > ag:
                t1_wins += 1
            elif ag > hg:
                t2_wins += 1
            else:
                draws += 1
        else:
            t1_gf += ag
            t2_gf += hg
            if ag > hg:
                t1_wins += 1
            elif hg > ag:
                t2_wins += 1
            else:
                draws += 1

    total = t1_wins + t2_wins + draws
    lines = [
        f"Head-to-Head: {team1} vs {team2}",
        f"Total Matches: {total}",
        f"{team1}: {t1_wins} wins ({t1_gf} goals)",
        f"{team2}: {t2_wins} wins ({t2_gf} goals)",
        f"Draws: {draws}",
        "",
        "Recent Matches (up to 10):",
    ]
    for _, row in df.head(10).iterrows():
        lines.append(_format_match(row))

    return "\n".join(lines)


@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Search for players in the FIFA dataset.

    Args:
        name: Player name to search for (partial match)
        nationality: Player nationality (e.g., 'Brazil', 'Brazilian')
        club: Club name to filter by (e.g., 'Flamengo', 'Palmeiras')
        position: Playing position (e.g., 'ST', 'GK', 'CB', 'forward')
        min_overall: Minimum overall FIFA rating
        limit: Maximum number of players to return (default 20)

    Returns:
        Formatted list of players with key attributes
    """
    df = load_fifa()

    if name:
        df = df[df["Name"].str.contains(name, case=False, na=False, regex=False)]

    if nationality:
        nat = nationality.replace("Brazilian", "Brazil")
        df = df[df["Nationality"].str.contains(nat, case=False, na=False, regex=False)]

    if club:
        df = df[df["Club"].str.contains(club, case=False, na=False, regex=False)]

    if position:
        pos_upper = position.upper()
        position_map = {
            "FORWARD": ["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"],
            "MIDFIELDER": ["CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM"],
            "DEFENDER": ["CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"],
            "GOALKEEPER": ["GK"],
        }
        if pos_upper in position_map:
            positions = position_map[pos_upper]
            df = df[df["Position"].isin(positions)]
        else:
            df = df[df["Position"].str.contains(position, case=False, na=False, regex=False)]

    if min_overall:
        df = df[df["Overall"] >= min_overall]

    df = df.sort_values("Overall", ascending=False)
    total = len(df)
    df_show = df.head(limit)

    lines = [f"Found {total} player(s)"]
    if total > limit:
        lines.append(f"(showing top {limit} by Overall rating)")
    lines.append("")

    for _, row in df_show.iterrows():
        name_val = row.get("Name", "?")
        nat_val = row.get("Nationality", "?")
        overall = int(row["Overall"]) if pd.notna(row.get("Overall")) else "?"
        potential = int(row["Potential"]) if pd.notna(row.get("Potential")) else "?"
        club_val = row.get("Club", "?")
        pos_val = row.get("Position", "?")
        age_val = int(row["Age"]) if pd.notna(row.get("Age")) else "?"
        lines.append(
            f"{name_val} | {nat_val} | Age: {age_val} | Pos: {pos_val} | "
            f"Overall: {overall} | Potential: {potential} | Club: {club_val}"
        )

    return "\n".join(lines)


@mcp.tool()
def get_standings(season: int, competition: str = "brasileirao") -> str:
    """Calculate standings for a given season.

    Args:
        season: Season year (e.g., 2019, 2022)
        competition: Competition name ('brasileirao', 'copa brasil', 'libertadores')

    Returns:
        League table with points, wins, draws, losses, and goals
    """
    comp_lower = competition.lower()
    if "copa do brasil" in comp_lower or "copa brasil" in comp_lower or "cup" in comp_lower:
        df = load_copa_brasil()
        comp_label = "Copa do Brasil"
    elif "libertadores" in comp_lower:
        df = load_libertadores()
        comp_label = "Copa Libertadores"
    else:
        # Use combined brasileirao data
        df1 = load_brasileirao()
        df2 = load_historico()
        df = pd.concat([df1, df2], ignore_index=True)
        comp_label = "Brasileirão Serie A"

    df = df[df["season"] == season].copy()

    if len(df) == 0:
        return f"No data found for {comp_label} {season}"

    # Build standings
    teams: dict = {}

    def ensure_team(t: str) -> None:
        if t not in teams:
            teams[t] = {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}

    for _, row in df.iterrows():
        hg = row.get("home_goal")
        ag = row.get("away_goal")
        if pd.isna(hg) or pd.isna(ag):
            continue
        hg, ag = int(hg), int(ag)
        home = row["home_team_norm"]
        away = row["away_team_norm"]
        ensure_team(home)
        ensure_team(away)

        teams[home]["P"] += 1
        teams[away]["P"] += 1
        teams[home]["GF"] += hg
        teams[home]["GA"] += ag
        teams[away]["GF"] += ag
        teams[away]["GA"] += hg

        if hg > ag:
            teams[home]["W"] += 1
            teams[home]["Pts"] += 3
            teams[away]["L"] += 1
        elif ag > hg:
            teams[away]["W"] += 1
            teams[away]["Pts"] += 3
            teams[home]["L"] += 1
        else:
            teams[home]["D"] += 1
            teams[away]["D"] += 1
            teams[home]["Pts"] += 1
            teams[away]["Pts"] += 1

    # Sort by points, then GD, then GF
    sorted_teams = sorted(
        teams.items(),
        key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]),
        reverse=True,
    )

    lines = [f"{comp_label} {season} Standings", "=" * 60]
    lines.append(f"{'Pos':<4} {'Team':<25} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4}")
    lines.append("-" * 60)

    for pos, (team, s) in enumerate(sorted_teams, 1):
        gd = s["GF"] - s["GA"]
        lines.append(
            f"{pos:<4} {team:<25} {s['P']:>3} {s['W']:>3} {s['D']:>3} {s['L']:>3} "
            f"{s['GF']:>4} {s['GA']:>4} {gd:>4} {s['Pts']:>4}"
        )

    return "\n".join(lines)


@mcp.tool()
def get_biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    team: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Find the biggest wins (largest goal differences) in the dataset.

    Args:
        competition: Optional competition filter
        season: Optional season filter
        team: Optional team filter (winning team)
        limit: Number of results to return (default 10)

    Returns:
        List of matches ordered by goal difference
    """
    comp_lower = (competition or "").lower()
    if "copa do brasil" in comp_lower or "copa brasil" in comp_lower or "cup" in comp_lower:
        df = load_copa_brasil()
    elif "libertadores" in comp_lower:
        df = load_libertadores()
    elif "brasileirao" in comp_lower or "serie a" in comp_lower:
        df = load_brasileirao()
    else:
        df = load_all_matches()

    if season is not None:
        df = df[df["season"] == season]

    if team:
        df = filter_by_team(df, team)

    df = df.dropna(subset=["home_goal", "away_goal"]).copy()
    df["goal_diff"] = abs(df["home_goal"] - df["away_goal"])
    df = df.sort_values("goal_diff", ascending=False)

    lines = [f"Biggest wins (by goal difference):"]
    if competition:
        lines[0] += f" [{competition}]"
    if season:
        lines[0] += f" [{season}]"
    lines.append("")

    for _, row in df.head(limit).iterrows():
        gd = int(row["goal_diff"])
        lines.append(f"(GD: {gd}) {_format_match(row)}")

    return "\n".join(lines)


@mcp.tool()
def get_competition_stats(competition: Optional[str] = None, season: Optional[int] = None) -> str:
    """Get aggregate statistics for a competition or all competitions.

    Args:
        competition: Competition name filter (optional)
        season: Season year filter (optional)

    Returns:
        Summary statistics including goals per match, home win rates, etc.
    """
    comp_lower = (competition or "").lower()
    if "copa do brasil" in comp_lower or "copa brasil" in comp_lower or "cup" in comp_lower:
        df = load_copa_brasil()
        label = "Copa do Brasil"
    elif "libertadores" in comp_lower:
        df = load_libertadores()
        label = "Copa Libertadores"
    elif "brasileirao" in comp_lower or "serie a" in comp_lower:
        df = load_brasileirao()
        label = "Brasileirão Serie A"
    else:
        df = load_all_matches()
        label = "All Competitions"

    if season is not None:
        df = df[df["season"] == season]
        label += f" {season}"

    df = df.dropna(subset=["home_goal", "away_goal"])
    total = len(df)
    if total == 0:
        return "No data found"

    total_goals = int(df["home_goal"].sum() + df["away_goal"].sum())
    avg_goals = total_goals / total if total > 0 else 0

    home_wins = int((df["home_goal"] > df["away_goal"]).sum())
    away_wins = int((df["away_goal"] > df["home_goal"]).sum())
    draws = int((df["home_goal"] == df["away_goal"]).sum())

    home_win_rate = home_wins / total * 100
    away_win_rate = away_wins / total * 100
    draw_rate = draws / total * 100

    seasons = sorted(df["season"].dropna().unique().astype(int).tolist()) if "season" in df.columns else []

    lines = [
        f"Statistics: {label}",
        f"Total Matches: {total:,}",
        f"Total Goals: {total_goals:,}",
        f"Average Goals/Match: {avg_goals:.2f}",
        "",
        f"Home Wins: {home_wins:,} ({home_win_rate:.1f}%)",
        f"Away Wins: {away_wins:,} ({away_win_rate:.1f}%)",
        f"Draws: {draws:,} ({draw_rate:.1f}%)",
    ]
    if seasons:
        lines.append(f"\nSeasons covered: {min(seasons)}-{max(seasons)}")

    return "\n".join(lines)


@mcp.tool()
def list_teams(competition: Optional[str] = None, season: Optional[int] = None) -> str:
    """List all teams in the dataset.

    Args:
        competition: Optional competition filter
        season: Optional season filter

    Returns:
        Alphabetically sorted list of unique teams
    """
    comp_lower = (competition or "").lower()
    if "copa do brasil" in comp_lower or "copa brasil" in comp_lower or "cup" in comp_lower:
        df = load_copa_brasil()
    elif "libertadores" in comp_lower:
        df = load_libertadores()
    elif "brasileirao" in comp_lower or "serie a" in comp_lower:
        df = load_brasileirao()
    else:
        df = load_all_matches()

    if season is not None:
        df = df[df["season"] == season]

    home_teams = df["home_team_norm"].dropna().unique().tolist()
    away_teams = df["away_team_norm"].dropna().unique().tolist()
    all_teams = sorted(set(home_teams + away_teams))

    lines = [f"Teams found: {len(all_teams)}", ""]
    lines.extend(all_teams)
    return "\n".join(lines)


@mcp.tool()
def get_player_details(name: str) -> str:
    """Get detailed information about a specific player.

    Args:
        name: Player name (partial match supported)

    Returns:
        Detailed player profile including all available attributes
    """
    df = load_fifa()
    matches = df[df["Name"].str.contains(name, case=False, na=False, regex=False)]

    if len(matches) == 0:
        return f"No player found matching '{name}'"

    lines = []
    for _, row in matches.head(5).iterrows():
        lines.append(f"Name: {row.get('Name', '?')}")
        lines.append(f"Nationality: {row.get('Nationality', '?')}")
        lines.append(f"Age: {row.get('Age', '?')}")
        lines.append(f"Club: {row.get('Club', '?')}")
        lines.append(f"Position: {row.get('Position', '?')}")
        lines.append(f"Overall: {row.get('Overall', '?')}")
        lines.append(f"Potential: {row.get('Potential', '?')}")
        lines.append(f"Value: {row.get('Value', '?')}")
        lines.append(f"Wage: {row.get('Wage', '?')}")
        lines.append(f"Jersey Number: {row.get('Jersey Number', '?')}")
        lines.append(f"Height: {row.get('Height', '?')}, Weight: {row.get('Weight', '?')}")

        skill_cols = [
            "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
            "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
            "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
            "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
        ]
        skills = []
        for col in skill_cols:
            val = row.get(col)
            if pd.notna(val):
                try:
                    skills.append(f"{col}: {int(val)}")
                except (ValueError, TypeError):
                    pass
        if skills:
            lines.append("Skills: " + ", ".join(skills))
        lines.append("-" * 40)

    return "\n".join(lines)


@mcp.tool()
def get_team_seasons(team: str) -> str:
    """Get a summary of all seasons a team has played in.

    Args:
        team: Team name

    Returns:
        List of seasons the team played in each competition
    """
    df = load_all_matches()
    df = filter_by_team(df, team)

    if len(df) == 0:
        return f"No data found for team '{team}'"

    summary: dict = {}
    for _, row in df.iterrows():
        season = row.get("season")
        comp = row.get("competition", "Unknown")
        if pd.isna(season):
            continue
        key = (int(season), str(comp))
        if key not in summary:
            summary[key] = 0
        summary[key] += 1

    lines = [f"Seasons for '{team}':"]
    for (season, comp), count in sorted(summary.items()):
        lines.append(f"  {season} — {comp}: {count} matches")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
