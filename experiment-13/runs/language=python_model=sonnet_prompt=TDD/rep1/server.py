"""Brazilian Soccer MCP Server."""
import os
from functools import lru_cache
from mcp.server.fastmcp import FastMCP

from data_loader import DataLoader
from match_queries import (
    search_matches_by_team,
    search_matches_head_to_head,
    search_matches_by_season,
    search_matches_by_competition,
    search_matches_by_date_range,
    format_match_result,
    head_to_head_summary,
)
from team_queries import (
    get_team_record,
    get_team_goals,
    get_home_record,
    get_away_record,
    get_top_scoring_teams,
    get_best_home_records,
    get_best_away_records,
)
from player_queries import (
    search_players_by_name,
    search_players_by_nationality,
    search_players_by_club,
    search_players_by_position,
    get_top_rated_players,
    format_player_info,
    get_players_at_brazilian_clubs,
)
from competition_queries import (
    calculate_standings,
    get_biggest_wins,
    get_average_goals_per_match,
    get_home_win_rate,
    get_season_summary,
)

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "kaggle")

mcp = FastMCP("Brazilian Soccer Knowledge Graph")


@lru_cache(maxsize=1)
def _get_loader(data_dir: str = DEFAULT_DATA_DIR) -> DataLoader:
    return DataLoader(data_dir)


# ---------------------------------------------------------------------------
# Handler functions (called by both MCP tools and tests)
# ---------------------------------------------------------------------------

def handle_search_matches(
    team: str = None,
    competition: str = None,
    season: int = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 20,
    data_dir: str = DEFAULT_DATA_DIR,
) -> str:
    loader = _get_loader(data_dir)
    df = loader.all_matches.copy()

    if team:
        df = search_matches_by_team(df, team)
    if competition:
        df = search_matches_by_competition(df, competition)
    if season:
        df = search_matches_by_season(df, season)
    if start_date and end_date:
        df = search_matches_by_date_range(df, start_date, end_date)

    if len(df) == 0:
        return f"No matches found for the given criteria."

    df = df.sort_values("date", ascending=False, na_position="last").head(limit)
    lines = [format_match_result(row) for _, row in df.iterrows()]
    header = f"Found {len(df)} matches"
    if team:
        header += f" involving {team}"
    if competition:
        header += f" in {competition}"
    if season:
        header += f" ({season})"
    return header + ":\n" + "\n".join(lines)


def handle_head_to_head(
    team1: str,
    team2: str,
    competition: str = None,
    data_dir: str = DEFAULT_DATA_DIR,
) -> str:
    loader = _get_loader(data_dir)
    df = loader.all_matches
    if competition:
        df = search_matches_by_competition(df, competition)
    matches = search_matches_head_to_head(df, team1, team2)

    if len(matches) == 0:
        return f"No head-to-head matches found between {team1} and {team2}."

    summary = head_to_head_summary(matches, team1, team2)
    lines = [
        f"{team1} vs {team2} — {summary['total_matches']} matches",
        f"  {team1} wins: {summary['team1_wins']}",
        f"  {team2} wins: {summary['team2_wins']}",
        f"  Draws: {summary['draws']}",
        "",
        "Recent matches:",
    ]
    recent = matches.sort_values("date", ascending=False, na_position="last").head(10)
    for _, row in recent.iterrows():
        lines.append("  " + format_match_result(row))
    return "\n".join(lines)


def handle_team_stats(
    team: str,
    season: int = None,
    competition: str = None,
    data_dir: str = DEFAULT_DATA_DIR,
) -> str:
    loader = _get_loader(data_dir)
    df = loader.brasileirao
    if competition and "libertadores" in competition.lower():
        df = loader.libertadores
    elif competition and "copa" in competition.lower():
        df = loader.copa_brasil

    record = get_team_record(df, team, season)
    goals = get_team_goals(df, team, season)
    home = get_home_record(df, team, season)
    away = get_away_record(df, team, season)

    win_rate = record["wins"] / record["matches"] if record["matches"] > 0 else 0

    lines = [
        f"{team} Statistics" + (f" — {season}" if season else "") + ":",
        f"  Overall: {record['matches']} matches | {record['wins']}W {record['draws']}D {record['losses']}L",
        f"  Win rate: {win_rate:.1%}",
        f"  Goals: {goals['scored']} scored, {goals['conceded']} conceded",
        f"  Home: {home['matches']} matches | {home['wins']}W {home['draws']}D {home['losses']}L ({home['win_rate']:.1%} win rate)",
        f"  Away: {away['matches']} matches | {away['wins']}W {away['draws']}D {away['losses']}L ({away['win_rate']:.1%} win rate)",
    ]
    return "\n".join(lines)


def handle_team_record(
    team: str,
    season: int = None,
    competition: str = None,
    data_dir: str = DEFAULT_DATA_DIR,
) -> str:
    loader = _get_loader(data_dir)
    df = loader.all_matches
    if competition:
        df = search_matches_by_competition(df, competition)

    record = get_team_record(df, team, season)
    goals = get_team_goals(df, team, season)
    win_rate = record["wins"] / record["matches"] if record["matches"] > 0 else 0
    pts = record["wins"] * 3 + record["draws"]

    lines = [
        f"{team} Record" + (f" ({season})" if season else "") + ":",
        f"  Matches: {record['matches']}",
        f"  W/D/L: {record['wins']}/{record['draws']}/{record['losses']}",
        f"  Points: {pts}",
        f"  Win rate: {win_rate:.1%}",
        f"  Goals for: {goals['scored']}, Goals against: {goals['conceded']}",
    ]
    return "\n".join(lines)


def handle_search_players(
    name: str = None,
    nationality: str = None,
    club: str = None,
    position: str = None,
    limit: int = 20,
    data_dir: str = DEFAULT_DATA_DIR,
) -> str:
    loader = _get_loader(data_dir)
    df = loader.fifa_players

    if name:
        df = search_players_by_name(df, name)
    if nationality:
        df = search_players_by_nationality(df, nationality)
    if club:
        df = search_players_by_club(df, club)
    if position:
        df = search_players_by_position(df, position)

    if len(df) == 0:
        return "No players found for the given criteria."

    df = df.sort_values("Overall", ascending=False).head(limit)
    lines = [f"Found {len(df)} player(s):"]
    for _, player in df.iterrows():
        lines.append("  " + format_player_info(player))
    return "\n".join(lines)


def handle_top_players(
    nationality: str = None,
    club: str = None,
    position: str = None,
    limit: int = 10,
    data_dir: str = DEFAULT_DATA_DIR,
) -> str:
    loader = _get_loader(data_dir)
    df = get_top_rated_players(loader.fifa_players, nationality=nationality, club=club, limit=limit)

    if position:
        df = search_players_by_position(df, position)

    if len(df) == 0:
        return "No players found."

    lines = ["Top-rated players:"]
    for i, (_, player) in enumerate(df.iterrows(), 1):
        lines.append(f"  {i}. {format_player_info(player)}")
    return "\n".join(lines)


def handle_standings(
    season: int,
    competition: str = "brasileirao",
    limit: int = 20,
    data_dir: str = DEFAULT_DATA_DIR,
) -> str:
    loader = _get_loader(data_dir)
    if competition and "historico" in competition.lower():
        df = loader.historico
    elif competition and "copa" in competition.lower() and "brasil" in competition.lower():
        df = loader.copa_brasil
    elif competition and "libertadores" in competition.lower():
        df = loader.libertadores
    else:
        df = loader.brasileirao

    table = calculate_standings(df, season=season)[:limit]
    if not table:
        return f"No standings data found for season {season}."

    lines = [f"Standings — {season}:"]
    lines.append(f"  {'#':<3} {'Team':<30} {'Pts':>4} {'W':>3} {'D':>3} {'L':>3} {'GF':>3} {'GA':>3} {'GD':>4}")
    lines.append("  " + "-" * 60)
    for i, row in enumerate(table, 1):
        gd = row["goals_for"] - row["goals_against"]
        lines.append(
            f"  {i:<3} {row['team']:<30} {row['points']:>4} {row['wins']:>3} {row['draws']:>3} "
            f"{row['losses']:>3} {row['goals_for']:>3} {row['goals_against']:>3} {gd:>+4}"
        )
    return "\n".join(lines)


def handle_biggest_wins(
    season: int = None,
    competition: str = None,
    limit: int = 10,
    data_dir: str = DEFAULT_DATA_DIR,
) -> str:
    loader = _get_loader(data_dir)
    df = loader.all_matches
    if competition:
        df = search_matches_by_competition(df, competition)

    wins = get_biggest_wins(df, season=season, limit=limit)
    if not wins:
        return "No matches found."

    lines = ["Biggest victories:"]
    for i, w in enumerate(wins, 1):
        date_str = w.get("date") or "Unknown"
        lines.append(
            f"  {i}. {date_str}: {w['home_team']} {w['home_goal']}-{w['away_goal']} {w['away_team']} "
            f"(diff: {w['goal_diff']}) [{w.get('competition', '')}]"
        )
    return "\n".join(lines)


def handle_season_summary(
    season: int,
    competition: str = "brasileirao",
    data_dir: str = DEFAULT_DATA_DIR,
) -> str:
    loader = _get_loader(data_dir)
    if competition and "historico" in competition.lower():
        df = loader.historico
    elif competition and "copa" in competition.lower():
        df = loader.copa_brasil
    elif competition and "libertadores" in competition.lower():
        df = loader.libertadores
    else:
        df = loader.brasileirao

    stats = get_season_summary(df, season=season)
    lines = [
        f"Season {season} Summary ({competition}):",
        f"  Total matches: {stats['total_matches']}",
        f"  Total goals: {stats['total_goals']}",
        f"  Average goals per match: {stats['avg_goals_per_match']:.2f}",
        f"  Home win rate: {stats['home_win_rate']:.1%}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP Tool definitions
# ---------------------------------------------------------------------------

@mcp.tool()
def search_matches(
    team: str = None,
    competition: str = None,
    season: int = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 20,
) -> str:
    """Search for soccer matches by team, competition, season, or date range.

    Args:
        team: Team name to search (partial match, e.g. 'Flamengo', 'Palmeiras')
        competition: Competition name (e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores')
        season: Year of the season (e.g. 2019, 2023)
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)
        limit: Maximum number of results to return (default 20)
    """
    return handle_search_matches(
        team=team, competition=competition, season=season,
        start_date=start_date, end_date=end_date, limit=limit,
    )


@mcp.tool()
def head_to_head(team1: str, team2: str, competition: str = None) -> str:
    """Find all head-to-head matches between two teams, with win/draw/loss summary.

    Args:
        team1: First team name (partial match)
        team2: Second team name (partial match)
        competition: Optional competition filter
    """
    return handle_head_to_head(team1=team1, team2=team2, competition=competition)


@mcp.tool()
def team_statistics(team: str, season: int = None, competition: str = None) -> str:
    """Get overall, home, and away statistics for a team.

    Args:
        team: Team name (partial match, e.g. 'Flamengo')
        season: Optional season year filter
        competition: Optional competition filter (brasileirao/copa/libertadores)
    """
    return handle_team_stats(team=team, season=season, competition=competition)


@mcp.tool()
def team_record(team: str, season: int = None, competition: str = None) -> str:
    """Get a team's win/draw/loss record and points total.

    Args:
        team: Team name (partial match)
        season: Optional season year filter
        competition: Optional competition filter
    """
    return handle_team_record(team=team, season=season, competition=competition)


@mcp.tool()
def search_players(
    name: str = None,
    nationality: str = None,
    club: str = None,
    position: str = None,
    limit: int = 20,
) -> str:
    """Search for players in the FIFA dataset by name, nationality, club, or position.

    Args:
        name: Player name (partial match, e.g. 'Neymar', 'Gabriel')
        nationality: Nationality (e.g. 'Brazil', 'Argentina')
        club: Club name (partial match, e.g. 'Fluminense', 'Grêmio')
        position: Playing position (e.g. 'GK', 'ST', 'CAM')
        limit: Maximum number of results (default 20)
    """
    return handle_search_players(name=name, nationality=nationality, club=club,
                                  position=position, limit=limit)


@mcp.tool()
def top_rated_players(
    nationality: str = None,
    club: str = None,
    position: str = None,
    limit: int = 10,
) -> str:
    """Get the highest-rated players, optionally filtered by nationality, club, or position.

    Args:
        nationality: Filter by nationality (e.g. 'Brazil')
        club: Filter by club name
        position: Filter by position (e.g. 'GK', 'ST')
        limit: Number of players to return (default 10)
    """
    return handle_top_players(nationality=nationality, club=club,
                               position=position, limit=limit)


@mcp.tool()
def league_standings(
    season: int,
    competition: str = "brasileirao",
    limit: int = 20,
) -> str:
    """Calculate league standings for a given season, sorted by points.

    Args:
        season: Season year (e.g. 2019)
        competition: Competition to use: 'brasileirao' (default), 'historico', 'copa', 'libertadores'
        limit: Number of teams to return (default 20)
    """
    return handle_standings(season=season, competition=competition, limit=limit)


@mcp.tool()
def biggest_wins(
    season: int = None,
    competition: str = None,
    limit: int = 10,
) -> str:
    """Find the matches with the largest goal differences (biggest victories).

    Args:
        season: Optional season year filter
        competition: Optional competition filter
        limit: Number of results to return (default 10)
    """
    return handle_biggest_wins(season=season, competition=competition, limit=limit)


@mcp.tool()
def season_summary(season: int, competition: str = "brasileirao") -> str:
    """Get statistical summary for a season: total matches, goals, averages, home win rate.

    Args:
        season: Season year (e.g. 2019)
        competition: Competition: 'brasileirao' (default), 'historico', 'copa', 'libertadores'
    """
    return handle_season_summary(season=season, competition=competition)


@mcp.tool()
def players_at_brazilian_clubs() -> str:
    """List Brazilian clubs in the FIFA dataset with player counts and average ratings."""
    loader = _get_loader(DEFAULT_DATA_DIR)
    clubs = get_players_at_brazilian_clubs(loader.fifa_players)
    if not clubs:
        return "No Brazilian clubs found in the FIFA dataset."
    sorted_clubs = sorted(clubs.items(), key=lambda x: x[1]["count"], reverse=True)
    lines = ["Brazilian clubs in FIFA dataset:"]
    for club, stats in sorted_clubs:
        lines.append(f"  {club}: {stats['count']} players (avg rating: {stats['avg_rating']})")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
