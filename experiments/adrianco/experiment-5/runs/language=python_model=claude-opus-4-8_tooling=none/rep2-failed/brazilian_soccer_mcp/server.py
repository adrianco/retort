"""
Context
=======
Module: brazilian_soccer_mcp.server
Purpose: The MCP (Model Context Protocol) server.  It exposes the
:class:`~brazilian_soccer_mcp.knowledge_graph.KnowledgeGraph` query API as a set
of MCP *tools* that an LLM can call to answer natural-language questions about
Brazilian soccer (matches, teams, players, competitions, statistics).

Each tool is a thin wrapper that calls the graph and renders the result with
:mod:`brazilian_soccer_mcp.formatting`, so the LLM receives clean, ready-to-read
text.  The data is loaded once into a cached singleton graph
(:func:`brazilian_soccer_mcp.get_graph`).

Run it over stdio with::

    python -m brazilian_soccer_mcp.server

The tools map onto the five capability groups in TASK.md:
    1. Match queries          -> find_matches, head_to_head
    2. Team queries           -> team_record, best_team_records
    3. Player queries         -> search_players, player_profile
    4. Competition queries    -> league_standings, competition_champion
    5. Statistical analysis   -> league_statistics, biggest_wins
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import formatting as F
from . import get_graph

mcp = FastMCP("brazilian-soccer")


# --------------------------------------------------------------------------- #
# 1. Match queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "either",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 25,
) -> str:
    """Find matches by team, opponent, season, competition, venue or date range.

    Args:
        team: Team name (any spelling, e.g. "Flamengo", "Palmeiras-SP").
        opponent: Optional second team to find head-to-head fixtures.
        season: Season year, e.g. 2019.
        competition: "Brasileirão", "Copa do Brasil" or "Libertadores".
        venue: "home", "away" or "either" (relative to ``team``).
        date_from / date_to: ISO dates (YYYY-MM-DD) to bound the range.
        limit: Maximum matches to return.
    """
    g = get_graph()
    matches = g.find_matches(
        team=team, opponent=opponent, season=season, competition=competition,
        venue=venue, date_from=date_from, date_to=date_to, limit=limit,
    )
    bits = [b for b in [team, ("vs " + opponent) if opponent else None,
                        competition, str(season) if season else None] if b]
    title = "Matches" + (": " + " ".join(bits) if bits else "")
    return F.format_matches(matches, title=title, max_rows=limit)


@mcp.tool()
def head_to_head(team1: str, team2: str) -> str:
    """Aggregate head-to-head record and recent meetings between two teams."""
    g = get_graph()
    h2h = g.head_to_head(team1, team2)
    if h2h is None:
        return f"Could not find one of the teams: {team1!r} / {team2!r}."
    return F.format_head_to_head(h2h)


# --------------------------------------------------------------------------- #
# 2. Team queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> str:
    """Win/draw/loss and goals record for a team, optionally filtered.

    Args:
        team: Team name.
        season: Season year filter.
        competition: Competition filter.
        venue: "all", "home" or "away".
    """
    g = get_graph()
    stats = g.team_stats(team, season=season, competition=competition, venue=venue)
    if stats is None:
        return f"Could not find team {team!r}."
    return F.format_team_stats(stats)


@mcp.tool()
def best_team_records(
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
    metric: str = "win_rate",
    limit: int = 10,
) -> str:
    """Rank teams by win rate or points (e.g. the best home record).

    Args:
        venue: "all", "home" or "away".
        metric: "win_rate" or "points".
    """
    g = get_graph()
    rows = g.best_records(
        season=season, competition=competition, venue=venue,
        metric=metric, limit=limit,
    )
    if not rows:
        return "No team records found for those filters."
    scope = " ".join(str(x) for x in [competition, season] if x) or "all competitions"
    lines = [f"Best {venue} records by {metric} ({scope}):"]
    for i, s in enumerate(rows, start=1):
        lines.append(
            f"{i}. {s['team']} - {s['win_rate']}% win rate, {s['points']} pts "
            f"({s['wins']}W {s['draws']}D {s['losses']}L in {s['played']} games)"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 3. Player queries
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
    """Search the FIFA player database by name, nationality, club or position.

    Args:
        nationality: e.g. "Brazil".
        club: e.g. "Flamengo", "Paris Saint-Germain".
        position: e.g. "ST", "GK", "LW".
        min_overall: Minimum FIFA overall rating.
        sort_by: "overall", "potential", "age" or "name".
    """
    g = get_graph()
    players = g.search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, sort_by=sort_by, limit=limit,
    )
    bits = [b for b in [name, nationality, club, position] if b]
    title = "Players" + (": " + ", ".join(bits) if bits else "")
    return F.format_players(players, title=title)


@mcp.tool()
def player_profile(name: str) -> str:
    """Return the full profile (ratings, attributes) for a player by name."""
    g = get_graph()
    player = g.find_player(name)
    if player is None:
        return f"No player found matching {name!r} in the FIFA dataset."
    return F.format_player(player)


# --------------------------------------------------------------------------- #
# 4. Competition queries
# --------------------------------------------------------------------------- #
@mcp.tool()
def league_standings(season: int, competition: str = "Brasileirão") -> str:
    """Compute the final league table for a season from match results."""
    g = get_graph()
    rows = g.standings(season, competition)
    return F.format_standings(rows, season, competition)


@mcp.tool()
def competition_champion(season: int, competition: str = "Brasileirão") -> str:
    """Return the champion (top of the calculated table) for a season."""
    g = get_graph()
    champ = g.champion(season, competition)
    if champ is None:
        return f"No data to determine the {competition} {season} champion."
    return (
        f"{competition} {season} champion: {champ['team']} - {champ['points']} pts "
        f"({champ['wins']}W, {champ['draws']}D, {champ['losses']}L, "
        f"GD {champ['goal_difference']:+d})."
    )


# --------------------------------------------------------------------------- #
# 5. Statistical analysis
# --------------------------------------------------------------------------- #
@mcp.tool()
def league_statistics(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """Aggregate stats: avg goals/match, home/away win rates, draw rate."""
    g = get_graph()
    return F.format_competition_stats(g.competition_stats(competition, season))


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """List the matches with the largest winning margin."""
    g = get_graph()
    matches = g.biggest_wins(competition=competition, season=season, limit=limit)
    scope = " ".join(str(x) for x in [competition, season] if x) or "all data"
    return F.format_matches(matches, title=f"Biggest victories ({scope}):", max_rows=limit)


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #
@mcp.tool()
def dataset_overview() -> str:
    """Summarise the loaded datasets: matches, players, competitions, seasons."""
    g = get_graph()
    s = g.dataset_summary()
    lines = [
        "Brazilian Soccer knowledge graph:",
        f"- Matches (canonical): {s['total_matches']} (from {s['raw_match_rows']} raw rows)",
        f"- Players: {s['total_players']} ({s['brazilian_players']} Brazilian)",
        f"- Distinct teams: {s['distinct_teams']}",
        f"- Seasons: {s['season_range'][0]}-{s['season_range'][1]}"
        if s["season_range"] else "- Seasons: n/a",
        "- Matches by competition: "
        + ", ".join(f"{k} ({v})" for k, v in s["matches_by_competition"].items()),
    ]
    return "\n".join(lines)


def main() -> None:
    """Entry point: load the data then serve over stdio."""
    get_graph()  # warm the cache before accepting requests
    mcp.run()


if __name__ == "__main__":
    main()
