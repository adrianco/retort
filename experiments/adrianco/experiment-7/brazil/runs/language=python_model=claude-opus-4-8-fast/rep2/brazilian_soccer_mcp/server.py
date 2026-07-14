"""
================================================================================
Module: brazilian_soccer_mcp.server
--------------------------------------------------------------------------------
Context:
    The MCP entry point. Exposes the KnowledgeGraph query API as Model Context
    Protocol tools over stdio so any MCP-capable LLM client (Claude Desktop,
    etc.) can answer natural-language questions about Brazilian soccer. See
    TASK.md "Required Capabilities" for the five query categories implemented.

Responsibility:
    Thin adapter layer only: build the graph once at startup, then map each MCP
    tool call onto a KnowledgeGraph method and render the result with
    formatting.py. All real logic lives in knowledge_graph.py, which keeps the
    tools trivially testable and the server free of business rules.

Run:
    python -m brazilian_soccer_mcp.server         # stdio MCP server
    (or)  bsoccer-mcp                              # console script
================================================================================
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import formatting as fmt
from .knowledge_graph import KnowledgeGraph

mcp = FastMCP("brazilian-soccer")

# Single shared, lazily-loaded knowledge graph.
_graph: Optional[KnowledgeGraph] = None


def get_graph() -> KnowledgeGraph:
    """Return the shared graph, loading the datasets on first use."""
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph().load()
    return _graph


# --------------------------------------------------------------------------- #
# 1. Match queries                                                            #
# --------------------------------------------------------------------------- #
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    venue: str = "either",
    limit: int = 15,
) -> str:
    """Find matches by team, opponent, competition, season and/or date range.

    Args:
        team: Team name (state suffix optional, e.g. "Flamengo" or "Atletico-MG").
        opponent: Restrict to matches against this team (for derbies / H2H).
        competition: "Brasileirão", "Copa do Brasil" or "Libertadores" (aliases ok).
        season: Year of the season.
        start_date / end_date: ISO dates ("2023-01-01") to bound the search.
        venue: "either" (default), "home" or "away", relative to `team`.
        limit: Max matches to list.
    """
    g = get_graph()
    matches = g.find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        start_date=start_date,
        end_date=end_date,
        venue=venue,
        limit=limit,
    )
    header = "Matches found:"
    if team and opponent:
        header = f"{team} vs {opponent}:"
    elif team:
        header = f"{team} matches:"
    return fmt.format_matches(matches, header=header, limit=limit)


@mcp.tool()
def head_to_head(team1: str, team2: str, competition: Optional[str] = None) -> str:
    """Head-to-head record and match list between two teams.

    Args:
        team1: First team.
        team2: Second team.
        competition: Optional competition filter.
    """
    g = get_graph()
    return fmt.format_head_to_head(g.head_to_head(team1, team2, competition))


# --------------------------------------------------------------------------- #
# 2. Team queries                                                             #
# --------------------------------------------------------------------------- #
@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> str:
    """Win/draw/loss record, goals and win-rate for a team.

    Args:
        team: Team name.
        season: Optional season year.
        competition: Optional competition filter.
        venue: "all" (default), "home" or "away".
    """
    g = get_graph()
    return fmt.format_team_record(g.team_record(team, season, competition, venue))


@mcp.tool()
def team_competitions(team: str) -> str:
    """List the competitions a team appears in within the dataset."""
    g = get_graph()
    comps = g.team_competitions(team)
    if not comps:
        return f"No competitions found for '{team}'."
    return f"{team} appears in:\n" + "\n".join(f"- {c}" for c in comps)


# --------------------------------------------------------------------------- #
# 3. Player queries                                                           #
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
    """Search the FIFA player database.

    Args:
        name: Substring of the player's name.
        nationality: e.g. "Brazil".
        club: Club name (e.g. "Flamengo").
        position: e.g. "ST", "GK", "LW".
        min_overall: Minimum FIFA overall rating.
        sort_by: "overall" (default), "potential", "age" or "name".
        limit: Max players to return.
    """
    g = get_graph()
    players = g.search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        sort_by=sort_by,
        limit=limit,
    )
    parts = [p for p in (nationality, position, club) if p]
    header = "Players" + (f" ({', '.join(parts)})" if parts else "") + ":"
    return fmt.format_players(players, header=header, limit=limit)


@mcp.tool()
def get_player(name: str) -> str:
    """Look up a single player by name and return their key attributes."""
    g = get_graph()
    p = g.get_player(name)
    if not p:
        return f"No player found matching '{name}'."
    d = p.to_dict()
    return (
        f"{d['name']}\n"
        f"- Nationality: {d['nationality']}\n"
        f"- Age: {d['age']}\n"
        f"- Club: {d['club']}\n"
        f"- Position: {d['position']}\n"
        f"- Overall: {d['overall']} (Potential: {d['potential']})\n"
        f"- Height/Weight: {d['height']} / {d['weight']}"
    )


@mcp.tool()
def players_by_club(nationality: str = "Brazil", limit: int = 15) -> str:
    """Summarise players of a nationality grouped by club (counts + avg rating)."""
    g = get_graph()
    rows = g.players_by_club_summary(nationality)
    return fmt.format_club_summary(rows, nationality, limit=limit)


# --------------------------------------------------------------------------- #
# 4. Competition queries                                                      #
# --------------------------------------------------------------------------- #
@mcp.tool()
def standings(competition: str, season: int) -> str:
    """League table for a competition/season, computed from match results.

    Args:
        competition: "Brasileirão", "Copa do Brasil", "Libertadores" (aliases ok).
        season: Year.
    """
    g = get_graph()
    comp = g._resolve_competition(competition)
    table = g.standings(competition, season)
    return fmt.format_standings(table, comp, season)


@mcp.tool()
def champion(competition: str, season: int) -> str:
    """Winner of a competition/season (top of the computed standings)."""
    g = get_graph()
    c = g.champion(competition, season)
    comp = g._resolve_competition(competition)
    if not c:
        return f"No data to determine a {comp} {season} champion."
    return (
        f"{comp} {season} champion (calculated from matches): {c['team']}\n"
        f"- {c['points']} pts ({c['wins']}W {c['draws']}D {c['losses']}L), "
        f"GD {c['goal_difference']:+d}"
    )


@mcp.tool()
def list_competitions() -> str:
    """List all competitions available in the dataset."""
    g = get_graph()
    return "Competitions:\n" + "\n".join(f"- {c}" for c in g.list_competitions())


@mcp.tool()
def list_seasons(competition: Optional[str] = None) -> str:
    """List seasons available, optionally for a single competition."""
    g = get_graph()
    seasons = g.list_seasons(competition)
    label = g._resolve_competition(competition) if competition else "all competitions"
    return f"Seasons ({label}): " + ", ".join(str(s) for s in seasons)


# --------------------------------------------------------------------------- #
# 5. Statistical analysis                                                     #
# --------------------------------------------------------------------------- #
@mcp.tool()
def match_statistics(
    competition: Optional[str] = None, season: Optional[int] = None
) -> str:
    """Average goals per match and home/away/draw rates for a slice of data."""
    g = get_graph()
    return fmt.format_stats(g.average_goals(competition, season))


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
) -> str:
    """The most lopsided victories (largest goal margin) in a slice of data."""
    g = get_graph()
    matches = g.biggest_wins(competition, season, limit)
    return fmt.format_matches(matches, header="Biggest victories:", limit=limit)


@mcp.tool()
def best_record(
    venue: str = "all",
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 5,
    limit: int = 10,
) -> str:
    """Rank teams by win-rate over a slice (e.g. best home or away record).

    Args:
        venue: "all", "home" or "away".
        competition / season: Optional filters.
        min_matches: Ignore teams with fewer than this many matches.
        limit: Number of teams to return.
    """
    g = get_graph()
    rows = g.best_record(
        venue=venue,
        competition=competition,
        season=season,
        min_matches=min_matches,
        limit=limit,
    )
    title = f"Best {venue} record" + (f" — {competition}" if competition else "")
    title += f" {season}" if season else ""
    title += ":"
    return fmt.format_best_record(rows, title)


def main() -> None:
    """Console-script / module entry point: run the stdio MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
