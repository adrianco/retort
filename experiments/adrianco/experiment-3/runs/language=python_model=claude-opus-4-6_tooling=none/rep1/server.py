import json
from mcp.server.fastmcp import FastMCP
from data_loader import BrazilianSoccerData

mcp = FastMCP("brazilian-soccer")
data = BrazilianSoccerData()


def _df_to_str(df, max_rows: int = 50) -> str:
    if df.empty:
        return "No results found."
    records = df.head(max_rows).to_dict(orient="records")
    lines = []
    for r in records:
        parts = []
        for k, v in r.items():
            if v is not None and str(v) != "" and str(v) != "nan" and str(v) != "NaT":
                parts.append(f"{k}: {v}")
        lines.append(" | ".join(parts))
    result = "\n".join(lines)
    if len(df) > max_rows:
        result += f"\n\n... and {len(df) - max_rows} more results (showing first {max_rows})"
    return result


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
) -> str:
    """Search for Brazilian soccer matches by team, opponent, competition, season, or date range.

    Args:
        team: Team name to search for (home or away)
        opponent: Opponent team name (use with team for head-to-head)
        competition: Competition name (Brasileirao, Copa do Brasil, Copa Libertadores)
        season: Year of the season
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        limit: Maximum results to return (default 50)
    """
    df = data.search_matches(
        team=team, opponent=opponent, competition=competition,
        season=season, date_from=date_from, date_to=date_to, limit=limit,
    )
    return _df_to_str(df)


@mcp.tool()
def get_team_statistics(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    home_only: bool = False,
    away_only: bool = False,
) -> str:
    """Get win/loss/draw record and goal statistics for a team.

    Args:
        team: Team name
        competition: Filter by competition name
        season: Filter by season year
        home_only: Only include home matches
        away_only: Only include away matches
    """
    stats = data.team_statistics(
        team=team, competition=competition, season=season,
        home_only=home_only, away_only=away_only,
    )
    return json.dumps(stats, indent=2, ensure_ascii=False)


@mcp.tool()
def get_head_to_head(
    team1: str,
    team2: str,
    competition: str | None = None,
) -> str:
    """Compare two teams head-to-head across all matches in the dataset.

    Args:
        team1: First team name
        team2: Second team name
        competition: Optionally filter by competition
    """
    result = data.head_to_head(team1=team1, team2=team2, competition=competition)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 50,
) -> str:
    """Search FIFA player database by name, nationality, club, position, or minimum rating.

    Args:
        name: Player name (partial match)
        nationality: Player nationality (e.g., Brazil)
        club: Club name (partial match)
        position: Playing position (e.g., ST, GK, LW)
        min_overall: Minimum FIFA overall rating
        limit: Maximum results to return (default 50)
    """
    df = data.search_players(
        name=name, nationality=nationality, club=club,
        position=position, min_overall=min_overall, limit=limit,
    )
    cols = ["Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position"]
    existing = [c for c in cols if c in df.columns]
    return _df_to_str(df[existing])


@mcp.tool()
def get_competition_standings(
    competition: str,
    season: int,
) -> str:
    """Get league standings calculated from match results for a given competition and season.

    Args:
        competition: Competition name (e.g., Brasileirao)
        season: Season year
    """
    df = data.competition_standings(competition=competition, season=season)
    if df.empty:
        return "No standings data found for that competition and season."
    cols = ["team", "matches", "wins", "draws", "losses", "goals_for", "goals_against", "points", "win_rate"]
    existing = [c for c in cols if c in df.columns]
    return _df_to_str(df[existing], max_rows=30)


@mcp.tool()
def get_match_statistics(
    team: str | None = None,
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Get aggregate match statistics: average goals, home/away win rates, biggest wins.

    Args:
        team: Optionally filter by team
        competition: Optionally filter by competition
        season: Optionally filter by season year
    """
    stats = data.match_statistics(team=team, competition=competition, season=season)
    return json.dumps(stats, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
