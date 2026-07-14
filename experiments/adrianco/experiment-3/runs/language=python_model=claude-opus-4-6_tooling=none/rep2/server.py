import json
from mcp.server.fastmcp import FastMCP
from data_loader import BrazilianSoccerData

mcp = FastMCP(
    "Brazilian Soccer MCP",
    instructions="MCP server providing a knowledge graph interface for Brazilian soccer data. "
    "Query players, teams, matches, and competitions across Brasileirão, Copa do Brasil, and Libertadores.",
)

data = BrazilianSoccerData()


@mcp.tool()
def search_matches(
    team: str | None = None,
    team2: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 20,
) -> str:
    """Search for matches by team, competition, and/or season.

    Args:
        team: Team name to search for (e.g. "Flamengo", "Palmeiras")
        team2: Second team for head-to-head matches
        competition: Competition name (Brasileirão, Copa do Brasil, Libertadores)
        season: Season year (e.g. 2023)
        limit: Max results to return (default 20)
    """
    matches = data.search_matches(team=team, team2=team2, competition=competition, season=season, limit=limit)
    if not matches:
        return "No matches found for the given criteria."
    lines = [f"Found {len(matches)} match(es):\n"]
    for m in matches:
        score = f"{m['home_goals']}-{m['away_goals']}" if m["home_goals"] is not None else "N/A"
        date = m["date"][:10] if m["date"] else "Unknown date"
        comp = m.get("competition", "")
        rnd = f" Round {m['round']}" if m.get("round") else ""
        stage = f" ({m['stage']})" if m.get("stage") else ""
        lines.append(f"  {date}: {m['home_team']} {score} {m['away_team']} [{comp}{rnd}{stage}]")
    return "\n".join(lines)


@mcp.tool()
def get_team_stats(
    team: str,
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Get win/loss/draw statistics for a team.

    Args:
        team: Team name (e.g. "Corinthians")
        competition: Filter by competition
        season: Filter by season year
    """
    stats = data.get_team_stats(team=team, competition=competition, season=season)
    if stats["matches"] == 0:
        return f"No matches found for {team}."
    lines = [
        f"{stats['team']} Statistics" + (f" ({stats['competition']}" if stats["competition"] else "") + (f" {stats['season']})" if stats["season"] else (")" if stats["competition"] else "")) + ":",
        f"  Matches: {stats['matches']}",
        f"  Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}",
        f"  Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']} (GD: {stats['goal_difference']:+d})",
        f"  Points: {stats['points']}",
        f"  Win Rate: {stats['win_rate']}%",
        f"  Home: {stats['home_matches']} matches, {stats['home_wins']} wins",
        f"  Away: {stats['away_matches']} matches, {stats['away_wins']} wins",
    ]
    return "\n".join(lines)


@mcp.tool()
def head_to_head(team1: str, team2: str) -> str:
    """Compare two teams head-to-head across all competitions.

    Args:
        team1: First team name
        team2: Second team name
    """
    result = data.head_to_head(team1, team2)
    if result["total_matches"] == 0:
        return f"No matches found between {team1} and {team2}."
    n1, n2 = result["team1"], result["team2"]
    lines = [
        f"{n1} vs {n2} - Head to Head:",
        f"  Total matches: {result['total_matches']}",
        f"  {n1} wins: {result[f'{n1}_wins']}",
        f"  {n2} wins: {result[f'{n2}_wins']}",
        f"  Draws: {result['draws']}",
        f"  {n1} goals: {result[f'{n1}_goals']}, {n2} goals: {result[f'{n2}_goals']}",
        "",
        "  Recent matches:",
    ]
    for m in result["recent_matches"][:5]:
        score = f"{m['home_goals']}-{m['away_goals']}" if m["home_goals"] is not None else "N/A"
        date = m["date"][:10] if m["date"] else "Unknown"
        lines.append(f"    {date}: {m['home_team']} {score} {m['away_team']} [{m.get('competition', '')}]")
    return "\n".join(lines)


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 20,
) -> str:
    """Search FIFA player database by name, nationality, club, or position.

    Args:
        name: Player name (partial match)
        nationality: Country (e.g. "Brazil")
        club: Club name (e.g. "Flamengo")
        position: Position (e.g. "ST", "GK", "CB")
        min_overall: Minimum FIFA overall rating
        limit: Max results (default 20)
    """
    players = data.search_players(name=name, nationality=nationality, club=club, position=position, min_overall=min_overall, limit=limit)
    if not players:
        return "No players found for the given criteria."
    lines = [f"Found {len(players)} player(s):\n"]
    for p in players:
        lines.append(f"  {p.get('Name', 'N/A')} - Overall: {p.get('Overall', 'N/A')}, "
                     f"Position: {p.get('Position', 'N/A')}, Club: {p.get('Club', 'N/A')}, "
                     f"Nationality: {p.get('Nationality', 'N/A')}")
    return "\n".join(lines)


@mcp.tool()
def get_standings(season: int) -> str:
    """Get Brasileirão standings for a specific season, calculated from match results.

    Args:
        season: Season year (e.g. 2019)
    """
    standings = data.get_standings(season)
    if not standings:
        return f"No standings data available for season {season}."
    lines = [f"Brasileirão {season} Standings:\n"]
    lines.append(f"  {'#':<4}{'Team':<25}{'P':>4}{'W':>4}{'D':>4}{'L':>4}{'GF':>5}{'GA':>5}{'GD':>5}{'Pts':>5}")
    lines.append("  " + "-" * 65)
    for t in standings[:20]:
        lines.append(
            f"  {t['position']:<4}{t['team']:<25}{t['matches']:>4}{t['wins']:>4}"
            f"{t['draws']:>4}{t['losses']:>4}{t['gf']:>5}{t['ga']:>5}"
            f"{t['goal_difference']:>+5}{t['points']:>5}"
        )
    if len(standings) > 20:
        lines.append(f"  ... and {len(standings) - 20} more teams")
    return "\n".join(lines)


@mcp.tool()
def get_competition_stats(competition: str | None = None) -> str:
    """Get aggregate statistics for a competition (or all competitions).

    Args:
        competition: Competition name, or None for all competitions
    """
    stats = data.get_competition_stats(competition=competition)
    if "error" in stats:
        return stats["error"]
    lines = [
        f"{stats['competition']} Statistics:",
        f"  Total matches: {stats['total_matches']}",
        f"  Total goals: {stats['total_goals']}",
        f"  Average goals per match: {stats['avg_goals_per_match']}",
        f"  Home wins: {stats['home_wins']} ({stats['home_win_pct']}%)",
        f"  Away wins: {stats['away_wins']}",
        f"  Draws: {stats['draws']}",
        "",
        "  Biggest victories:",
    ]
    for m in stats["biggest_wins"][:5]:
        diff = abs(m["home_goals"] - m["away_goals"])
        date = m["date"][:10] if m["date"] else "Unknown"
        lines.append(f"    {date}: {m['home_team']} {m['home_goals']}-{m['away_goals']} {m['away_team']} (diff: {diff}) [{m.get('competition', '')}]")
    lines.append("")
    lines.append("  Highest scoring matches:")
    for m in stats["highest_scoring"][:5]:
        total = m["home_goals"] + m["away_goals"]
        date = m["date"][:10] if m["date"] else "Unknown"
        lines.append(f"    {date}: {m['home_team']} {m['home_goals']}-{m['away_goals']} {m['away_team']} (total: {total}) [{m.get('competition', '')}]")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
