"""MCP server exposing the Brazilian soccer knowledge graph as tools.

Run with::

    python -m brazilian_soccer_mcp.server

or via the bundled ``run_server.py`` entry point. The server speaks MCP over
stdio and can be connected to any MCP-compatible LLM client.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import get_graph
from . import formatters as fmt

mcp = FastMCP("brazilian-soccer")


# --------------------------------------------------------------------------- #
# Match queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: str = "either",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Find matches by team, opponent, competition, season, venue or date range.

    venue is one of 'home', 'away' or 'either'. Dates are ISO (YYYY-MM-DD).
    Example: find all Palmeiras home matches in 2023.
    """
    g = get_graph()
    if team and opponent:
        return fmt.format_head_to_head(g.head_to_head(team, opponent))
    matches = g.find_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        venue=venue, date_from=date_from, date_to=date_to, limit=limit,
    )
    return fmt.format_matches(matches, header="Matches found:")


@mcp.tool()
def head_to_head(team1: str, team2: str) -> str:
    """Return the full head-to-head record between two teams across all
    competitions (wins, draws and the list of matches)."""
    g = get_graph()
    return fmt.format_head_to_head(g.head_to_head(team1, team2))


# --------------------------------------------------------------------------- #
# Team queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "either",
) -> str:
    """Win/draw/loss record, goals for/against and win rate for a team,
    optionally restricted to a season, competition and/or home/away."""
    g = get_graph()
    rec = g.team_record(team, season=season, competition=competition, venue=venue)
    return fmt.format_team_record(rec, season=season, competition=competition,
                                  venue=venue)


@mcp.tool()
def compare_teams(team1: str, team2: str) -> str:
    """Compare two teams head-to-head."""
    g = get_graph()
    return fmt.format_head_to_head(g.head_to_head(team1, team2))


# --------------------------------------------------------------------------- #
# Competition queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def standings(competition: str, season: int) -> str:
    """Compute the final league table for a competition and season from match
    results. Competition examples: 'Brasileirão', 'Copa do Brasil',
    'Libertadores'."""
    g = get_graph()
    table = g.standings(competition, season)
    return fmt.format_standings(table, competition, season)


@mcp.tool()
def champion(competition: str, season: int) -> str:
    """Return the champion (table winner) of a competition for a season."""
    g = get_graph()
    rec = g.champion(competition, season)
    if not rec:
        return f"No data for {competition} {season}."
    return (f"{season} {competition} champion: {rec.team} "
            f"({rec.points} pts, {rec.wins}W {rec.draws}D {rec.losses}L)")


# --------------------------------------------------------------------------- #
# Statistical analysis
# --------------------------------------------------------------------------- #
@mcp.tool()
def match_statistics(competition: Optional[str] = None,
                     season: Optional[int] = None) -> str:
    """Aggregate statistics (avg goals per match, home/away/draw rates),
    optionally filtered by competition and/or season."""
    g = get_graph()
    stats = g.average_goals(competition=competition, season=season)
    scope = " ".join(x for x in [competition, str(season) if season else ""] if x)
    return fmt.format_stats(stats, header=f"Statistics {scope}".strip() + ":")


@mcp.tool()
def biggest_wins(competition: Optional[str] = None,
                 season: Optional[int] = None, limit: int = 10) -> str:
    """List the biggest victories (largest goal margins) in the data."""
    g = get_graph()
    matches = g.biggest_wins(competition=competition, season=season, limit=limit)
    return fmt.format_biggest_wins(matches)


@mcp.tool()
def best_record(competition: Optional[str] = None, season: Optional[int] = None,
                venue: str = "either", limit: int = 10) -> str:
    """Rank teams by win rate. Set venue to 'home' or 'away' for the best
    home/away records."""
    g = get_graph()
    ranked = g.best_record(competition=competition, season=season, venue=venue)
    if not ranked:
        return "No data."
    label = {"home": "home", "away": "away", "either": "overall"}.get(venue, "overall")
    lines = [f"Best {label} records:"]
    for i, r in enumerate(ranked[:limit], start=1):
        lines.append(f"{i}. {r.team} - {r.win_rate:.1f}% "
                     f"({r.wins}W {r.draws}D {r.losses}L, {r.matches} games)")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Player queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    sort_by: str = "overall",
    limit: int = 25,
) -> str:
    """Search FIFA player data by name, nationality, club, position and/or
    minimum overall rating. sort_by is one of overall, potential, age, name."""
    g = get_graph()
    players = g.search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, sort_by=sort_by, limit=limit,
    )
    return fmt.format_players(players, header="Players found:")


@mcp.tool()
def top_brazilian_players(limit: int = 10) -> str:
    """Return the highest-rated Brazilian players in the dataset."""
    g = get_graph()
    players = g.top_brazilian_players(limit=limit)
    return fmt.format_players(players, header="Top-rated Brazilian players:")


@mcp.tool()
def players_at_club(club: str, limit: int = 25) -> str:
    """List players at a given club, highest rated first."""
    g = get_graph()
    players = g.players_at_club(club, limit=limit)
    return fmt.format_players(players, header=f"Players at {club}:")


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
