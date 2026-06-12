"""Brazilian Soccer MCP Server — exposes soccer data as MCP tools."""
import os
from mcp.server.fastmcp import FastMCP
from data_loader import DataStore

DATA_DIR = os.environ.get("SOCCER_DATA_DIR", "data/kaggle")
store = DataStore(DATA_DIR)
mcp = FastMCP("Brazilian Soccer MCP")


# ---------------------------------------------------------------------------
# Tool: find_matches
# ---------------------------------------------------------------------------

@mcp.tool()
def find_matches(
    team: str = "",
    opponent: str = "",
    competition: str = "",
    season: int = 0,
    date_from: str = "",
    date_to: str = "",
    limit: int = 20,
) -> str:
    """Find soccer matches by team, opponent, competition, season, or date range.

    Args:
        team: Team name (partial match). E.g. 'Flamengo', 'Palmeiras-SP'
        opponent: Second team for head-to-head search
        competition: 'Brasileirao', 'Copa do Brasil', 'Libertadores', or 'all'
        season: Year (e.g. 2022)
        date_from: Start date YYYY-MM-DD
        date_to: End date YYYY-MM-DD
        limit: Maximum number of matches to return (default 20)
    """
    df = store.search_matches(
        team=team or None,
        opponent=opponent or None,
        competition=competition or None,
        season=season or None,
        date_from=date_from or None,
        date_to=date_to or None,
    )

    if df.empty:
        return "No matches found matching the given criteria."

    total = len(df)
    display = df.head(limit)

    lines = []

    # Header
    parts = []
    if team and opponent:
        parts.append(f"{team} vs {opponent}")
    elif team:
        parts.append(team)
    if competition:
        parts.append(competition)
    if season:
        parts.append(str(season))
    header = " | ".join(parts) if parts else "All matches"
    lines.append(f"Matches: {header}")
    lines.append(f"Found {total} match(es){', showing first ' + str(limit) if total > limit else ''}:")
    lines.append("")

    for _, row in display.iterrows():
        date_str = str(row['date']) if row['date'] else "?"
        comp = row['competition']
        round_info = str(row.get('round_info', '')).strip()
        round_part = f" [{round_info}]" if round_info and round_info not in ('', 'nan', '0') else ""
        lines.append(
            f"  {date_str}: {row['norm_home']} {row['home_goal']} - {row['away_goal']} "
            f"{row['norm_away']}  ({comp}{round_part})"
        )

    # Head-to-head summary when two teams specified
    if team and opponent:
        h2h = store.compute_head_to_head(team, opponent, competition or None)
        lines.append("")
        t1 = team; t2 = opponent
        lines.append(
            f"Head-to-head: {t1} {h2h['team1_wins']} wins | "
            f"{t2} {h2h['team2_wins']} wins | "
            f"{h2h['draws']} draws  (total: {h2h['total']})"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_team_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_team_stats(
    team: str,
    competition: str = "",
    season: int = 0,
) -> str:
    """Get win/draw/loss statistics and goal record for a team.

    Args:
        team: Team name (partial match)
        competition: Optional competition filter
        season: Optional year filter
    """
    if not team:
        return "Please provide a team name."

    stats = store.compute_team_stats(
        team=team,
        competition=competition or None,
        season=season or None,
    )

    if stats['total'] == 0:
        return f"No matches found for '{team}'."

    comp_label = competition if competition else "all competitions"
    season_label = str(season) if season else "all seasons"
    win_rate = (stats['W'] / stats['total'] * 100) if stats['total'] else 0.0

    lines = [
        f"{team} — {season_label} | {comp_label}",
        f"Matches played : {stats['total']}",
        f"Overall record : {stats['W']}W  {stats['D']}D  {stats['L']}L  "
        f"({win_rate:.1f}% win rate)",
        f"Goals          : For {stats['GF']}  Against {stats['GA']}  "
        f"(diff: {stats['GF'] - stats['GA']:+d})",
        f"Points (3 for W): {stats['W'] * 3 + stats['D']}",
        "",
        f"Home ({stats['home']} matches): "
        f"{stats['home_W']}W {stats['home_D']}D {stats['home_L']}L  "
        f"GF {stats['home_GF']} GA {stats['home_GA']}",
        f"Away ({stats['away']} matches): "
        f"{stats['away_W']}W {stats['away_D']}D {stats['away_L']}L  "
        f"GF {stats['away_GF']} GA {stats['away_GA']}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: find_players
# ---------------------------------------------------------------------------

@mcp.tool()
def find_players(
    name: str = "",
    nationality: str = "",
    club: str = "",
    position: str = "",
    min_rating: int = 0,
    limit: int = 20,
) -> str:
    """Search FIFA player database by name, nationality, club, or position.

    Args:
        name: Player name fragment (e.g. 'Neymar', 'Gabriel')
        nationality: Country (e.g. 'Brazil', 'Argentina')
        club: Club name fragment (e.g. 'Flamengo', 'Palmeiras')
        position: Position (e.g. 'ST', 'GK', 'CB')
        min_rating: Minimum overall FIFA rating
        limit: Maximum results to return (default 20)
    """
    df = store.search_players(
        name=name or None,
        nationality=nationality or None,
        club=club or None,
        position=position or None,
        min_rating=min_rating or None,
    )

    if df.empty:
        return "No players found matching the given criteria."

    total = len(df)
    display = df.head(limit)

    parts = []
    if name: parts.append(f"name='{name}'")
    if nationality: parts.append(f"nationality='{nationality}'")
    if club: parts.append(f"club='{club}'")
    if position: parts.append(f"position='{position}'")
    if min_rating: parts.append(f"rating≥{min_rating}")
    header = ", ".join(parts) if parts else "all players"

    lines = [
        f"Players ({header}): {total} found"
        + (f", showing top {limit}" if total > limit else ""),
        "",
    ]

    for i, (_, row) in enumerate(display.iterrows(), 1):
        name_str = row.get('Name', '?')
        nat = row.get('Nationality', '?')
        club_str = row.get('Club', '?')
        pos = row.get('Position', '?')
        overall = row.get('Overall', '?')
        age = row.get('Age', '?')
        lines.append(
            f"{i:2}. {name_str} ({nat}) — {club_str} | {pos} | Overall: {overall} | Age: {age}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_standings
# ---------------------------------------------------------------------------

@mcp.tool()
def get_standings(competition: str, season: int) -> str:
    """Calculate and return league standings for a given competition and season.

    Args:
        competition: 'Brasileirao', 'Copa do Brasil', etc.
        season: Year (e.g. 2019, 2022)
    """
    if not competition or not season:
        return "Please provide both competition and season."

    standings = store.compute_standings(competition=competition, season=season)

    if standings.empty:
        return f"No data found for {competition} {season}."

    lines = [
        f"{season} {competition} Standings",
        f"{'Pos':>3}  {'Team':<30} {'Pts':>4} {'W':>3} {'D':>3} {'L':>3} "
        f"{'GF':>4} {'GA':>4} {'GD':>5}",
        "-" * 65,
    ]
    for pos, row in standings.iterrows():
        gd = f"{row['GD']:+d}"
        lines.append(
            f"{pos:>3}. {row['team']:<30} {row['Pts']:>4} {row['W']:>3} {row['D']:>3} "
            f"{row['L']:>3} {row['GF']:>4} {row['GA']:>4} {gd:>5}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_head_to_head
# ---------------------------------------------------------------------------

@mcp.tool()
def get_head_to_head(
    team1: str,
    team2: str,
    competition: str = "",
    season: int = 0,
    limit: int = 10,
) -> str:
    """Get head-to-head record and recent matches between two teams.

    Args:
        team1: First team name
        team2: Second team name
        competition: Optional competition filter
        season: Optional year filter
        limit: Number of recent matches to display
    """
    if not team1 or not team2:
        return "Please provide both team names."

    h2h = store.compute_head_to_head(team1, team2, competition or None)
    df = h2h['matches']

    if h2h['total'] == 0:
        return f"No matches found between '{team1}' and '{team2}'."

    comp_label = f" ({competition})" if competition else ""
    lines = [
        f"Head-to-Head: {team1} vs {team2}{comp_label}",
        f"Total matches : {h2h['total']}",
        f"{team1} wins  : {h2h['team1_wins']}",
        f"{team2} wins  : {h2h['team2_wins']}",
        f"Draws         : {h2h['draws']}",
        "",
        f"Recent {min(limit, len(df))} match(es):",
    ]

    if season:
        df = df[df['season'] == int(season)]

    for _, row in df.head(limit).iterrows():
        date_str = str(row['date']) if row['date'] else "?"
        comp = row['competition']
        lines.append(
            f"  {date_str}: {row['norm_home']} {row['home_goal']} - "
            f"{row['away_goal']} {row['norm_away']}  ({comp})"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_top_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_top_stats(
    stat_type: str,
    competition: str = "",
    season: int = 0,
    limit: int = 10,
) -> str:
    """Get top statistics and records from the dataset.

    Args:
        stat_type: One of 'biggest_wins', 'averages', 'best_home', 'best_away',
                   'top_scoring', 'most_matches'
        competition: Optional competition filter
        season: Optional year filter
        limit: Number of results to show
    """
    df = store.search_matches(
        competition=competition or None,
        season=season or None,
    )

    if df.empty:
        return "No data found for the given criteria."

    stat_type = stat_type.lower().strip()

    if stat_type == "biggest_wins":
        df = df.copy()
        df['margin'] = abs(df['home_goal'] - df['away_goal'])
        top = df.nlargest(limit, 'margin')
        lines = [f"Biggest wins{' — ' + competition if competition else ''}:"]
        for i, (_, row) in enumerate(top.iterrows(), 1):
            winner = row['norm_home'] if row['home_goal'] > row['away_goal'] else row['norm_away']
            loser = row['norm_away'] if row['home_goal'] > row['away_goal'] else row['norm_home']
            wg = max(row['home_goal'], row['away_goal'])
            lg = min(row['home_goal'], row['away_goal'])
            lines.append(
                f"{i:2}. {str(row['date'])}: {winner} {wg}-{lg} {loser}  "
                f"({row['competition']}) margin: {row['margin']}"
            )
        return "\n".join(lines)

    elif stat_type == "averages":
        total = len(df)
        total_goals = (df['home_goal'] + df['away_goal']).sum()
        avg_goals = total_goals / total if total else 0
        home_wins = (df['home_goal'] > df['away_goal']).sum()
        away_wins = (df['away_goal'] > df['home_goal']).sum()
        draws = (df['home_goal'] == df['away_goal']).sum()
        label = competition if competition else "all competitions"
        season_label = str(season) if season else "all seasons"
        lines = [
            f"Statistics for {label} — {season_label}:",
            f"Total matches     : {total}",
            f"Total goals       : {total_goals}",
            f"Average goals/match: {avg_goals:.2f}",
            f"Home wins         : {home_wins} ({home_wins/total*100:.1f}%)",
            f"Away wins         : {away_wins} ({away_wins/total*100:.1f}%)",
            f"Draws             : {draws} ({draws/total*100:.1f}%)",
        ]
        return "\n".join(lines)

    elif stat_type in ("best_home", "best_away"):
        is_home = (stat_type == "best_home")
        records: dict[str, dict] = {}

        for _, row in df.iterrows():
            team = row['norm_home'] if is_home else row['norm_away']
            hg, ag = int(row['home_goal']), int(row['away_goal'])
            if team not in records:
                records[team] = {'team': team, 'P': 0, 'W': 0, 'D': 0, 'L': 0}
            records[team]['P'] += 1
            if is_home:
                if hg > ag: records[team]['W'] += 1
                elif hg == ag: records[team]['D'] += 1
                else: records[team]['L'] += 1
            else:
                if ag > hg: records[team]['W'] += 1
                elif ag == hg: records[team]['D'] += 1
                else: records[team]['L'] += 1

        import pandas as pd
        tbl = pd.DataFrame(list(records.values()))
        tbl['Pts'] = tbl['W'] * 3 + tbl['D']
        tbl = tbl[tbl['P'] >= 5].nlargest(limit, 'Pts')

        venue = "home" if is_home else "away"
        lines = [f"Best {venue} records:"]
        for i, (_, row) in enumerate(tbl.iterrows(), 1):
            wr = row['W'] / row['P'] * 100 if row['P'] else 0
            lines.append(
                f"{i:2}. {row['team']:<30} {row['W']}W {row['D']}D {row['L']}L  "
                f"({wr:.0f}% wins, {row['P']} matches)"
            )
        return "\n".join(lines)

    elif stat_type == "top_scoring":
        df2 = df.copy()
        df2['total_goals'] = df2['home_goal'] + df2['away_goal']
        top = df2.nlargest(limit, 'total_goals')
        lines = [f"Highest scoring matches:"]
        for i, (_, row) in enumerate(top.iterrows(), 1):
            lines.append(
                f"{i:2}. {str(row['date'])}: {row['norm_home']} {row['home_goal']}-"
                f"{row['away_goal']} {row['norm_away']}  "
                f"({row['competition']}, {row['total_goals']} goals)"
            )
        return "\n".join(lines)

    elif stat_type == "most_matches":
        from collections import Counter
        teams = list(df['norm_home']) + list(df['norm_away'])
        counts = Counter(teams).most_common(limit)
        lines = [f"Teams with most matches:"]
        for i, (team, count) in enumerate(counts, 1):
            lines.append(f"{i:2}. {team:<30} {count} matches")
        return "\n".join(lines)

    else:
        return (
            f"Unknown stat_type '{stat_type}'. "
            "Valid options: biggest_wins, averages, best_home, best_away, top_scoring, most_matches"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
