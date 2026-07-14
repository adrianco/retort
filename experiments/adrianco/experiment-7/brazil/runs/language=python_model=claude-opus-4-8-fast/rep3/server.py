"""
================================================================================
Context
================================================================================
Module:   server.py
Project:  Brazilian Soccer MCP Server
Purpose:  Expose the Brazilian-soccer knowledge graph to an LLM through the
          Model Context Protocol (MCP).  Built on FastMCP, it registers one tool
          per natural-language capability described in TASK.md (match, team,
          player, competition and statistical queries) and returns the
          human-readable answer formats produced by formatters.py.

Runtime:
    The knowledge graph (all six CSV datasets) is loaded once at process start
    and held in memory, so every tool call is an in-RAM lookup that meets the
    spec's latency targets (<2s simple, <5s aggregate).

Run:
    python server.py            # serve over stdio for an MCP client
    The module also exposes `mcp` (the FastMCP app) and `get_graph()` for tests.

Dependencies: mcp (FastMCP), knowledge_graph, formatters, data_loader.
================================================================================
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import formatters
from knowledge_graph import KnowledgeGraph

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - allows import without mcp installed
    FastMCP = None


# ---------------------------------------------------------------------------
# Lazily-loaded singleton knowledge graph
# ---------------------------------------------------------------------------
_graph: Optional[KnowledgeGraph] = None


def get_graph() -> KnowledgeGraph:
    """Return the shared knowledge graph, loading it on first use."""
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph.load()
    return _graph


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Tool implementations (pure functions, independently testable)
# ---------------------------------------------------------------------------
def tool_find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: str = "either",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20,
) -> str:
    kg = get_graph()
    matches = kg.find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        venue=venue,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
        dedup=True,
        limit=None,
    )
    parts = [p for p in (team, opponent, competition, str(season) if season else None) if p]
    header = "Matches" + (f" — {', '.join(parts)}" if parts else "") + f" ({len(matches)} found):"
    return formatters.format_matches(matches, header=header, limit=limit)


def tool_head_to_head(team_a: str, team_b: str,
                      competition: Optional[str] = None,
                      season: Optional[int] = None) -> str:
    kg = get_graph()
    h2h = kg.head_to_head(team_a, team_b, competition=competition, season=season)
    if h2h["total_matches"] == 0:
        return f"No matches found between {h2h['team_a']} and {h2h['team_b']}."
    return formatters.format_head_to_head(h2h)


def tool_team_record(team: str, season: Optional[int] = None,
                     competition: Optional[str] = None, venue: str = "either") -> str:
    kg = get_graph()
    stats = kg.team_stats(team, season=season, competition=competition, venue=venue)
    if stats["matches"] == 0:
        return f"No match records found for {stats['team']} with the given filters."
    return formatters.format_team_stats(stats)


def tool_compare_teams(team_a: str, team_b: str, season: Optional[int] = None) -> str:
    kg = get_graph()
    cmp = kg.compare_teams(team_a, team_b, season=season)
    return "\n\n".join(
        [
            formatters.format_head_to_head(cmp["head_to_head"]),
            formatters.format_team_stats(cmp["team_a_stats"]),
            formatters.format_team_stats(cmp["team_b_stats"]),
        ]
    )


def tool_standings(competition: str = "Brasileirão Série A",
                   season: int = 2019, limit: Optional[int] = None) -> str:
    kg = get_graph()
    table = kg.standings(competition, season)
    from knowledge_graph import resolve_competition
    return formatters.format_standings(table, resolve_competition(competition), season, limit=limit)


def tool_season_champion(competition: str = "Brasileirão Série A", season: int = 2019) -> str:
    kg = get_graph()
    champ = kg.champion(competition, season)
    from knowledge_graph import resolve_competition
    comp = resolve_competition(competition)
    if not champ:
        return f"No champion could be determined for {comp} {season}."
    return (
        f"{season} {comp} champion: {champ.team} — {champ.points} pts "
        f"({champ.wins}W {champ.draws}D {champ.losses}L, "
        f"GF {champ.goals_for} GA {champ.goals_against})."
    )


def tool_search_players(name: Optional[str] = None, nationality: Optional[str] = None,
                        club: Optional[str] = None, position: Optional[str] = None,
                        min_overall: Optional[int] = None, limit: int = 20) -> str:
    kg = get_graph()
    players = kg.search_players(
        name=name, nationality=nationality, club=club,
        position=position, min_overall=min_overall, limit=limit,
    )
    crit = [c for c in (name, nationality, club, position) if c]
    header = "Players" + (f" — {', '.join(crit)}" if crit else "") + f" ({len(players)} shown):"
    return formatters.format_players(players, header=header)


def tool_top_players(nationality: Optional[str] = None,
                     club: Optional[str] = None, limit: int = 10) -> str:
    kg = get_graph()
    players = kg.top_players(nationality=nationality, club=club, limit=limit)
    label_bits = [b for b in (nationality, club) if b]
    header = "Top-rated players" + (f" — {', '.join(label_bits)}" if label_bits else "") + ":"
    return formatters.format_players(players, header=header)


def tool_biggest_wins(competition: Optional[str] = None,
                      season: Optional[int] = None, limit: int = 10) -> str:
    kg = get_graph()
    matches = kg.biggest_wins(competition=competition, season=season, limit=limit)
    return formatters.format_matches(matches, header="Biggest victories in dataset:")


def tool_average_goals(competition: Optional[str] = None, season: Optional[int] = None) -> str:
    kg = get_graph()
    return formatters.format_average_goals(kg.average_goals(competition=competition, season=season))


def tool_best_record(venue: str = "home", competition: Optional[str] = None,
                     season: Optional[int] = None, min_matches: int = 5, limit: int = 10) -> str:
    kg = get_graph()
    records = kg.best_record(venue=venue, competition=competition,
                             season=season, min_matches=min_matches, limit=limit)
    return formatters.format_best_record(records, venue)


def tool_list_seasons(competition: Optional[str] = None) -> str:
    kg = get_graph()
    seasons = kg.list_seasons(competition)
    label = competition or "all competitions"
    if not seasons:
        return f"No seasons found for {label}."
    return f"Seasons available for {label}: {', '.join(str(s) for s in seasons)}"


def tool_list_competitions() -> str:
    kg = get_graph()
    return "Competitions in dataset:\n" + "\n".join(f"- {c}" for c in kg.list_competitions())


# ---------------------------------------------------------------------------
# MCP registration
# ---------------------------------------------------------------------------
def build_server(name: str = "brazilian-soccer"):
    """Create and configure the FastMCP server with all tools registered."""
    if FastMCP is None:
        raise RuntimeError(
            "The 'mcp' package is not installed. Install it with: pip install mcp"
        )
    mcp = FastMCP(name)

    @mcp.tool()
    def find_matches(team: Optional[str] = None, opponent: Optional[str] = None,
                     competition: Optional[str] = None, season: Optional[int] = None,
                     venue: str = "either", start_date: Optional[str] = None,
                     end_date: Optional[str] = None, limit: int = 20) -> str:
        """Find matches by team, opponent, competition, season, venue or date range.

        venue is one of 'home', 'away' or 'either' (relative to `team`).
        Dates are ISO format 'YYYY-MM-DD'. Returns a formatted list of matches.
        """
        return tool_find_matches(team, opponent, competition, season,
                                 venue, start_date, end_date, limit)

    @mcp.tool()
    def head_to_head(team_a: str, team_b: str, competition: Optional[str] = None,
                     season: Optional[int] = None) -> str:
        """Head-to-head record and match list between two teams (e.g. a derby)."""
        return tool_head_to_head(team_a, team_b, competition, season)

    @mcp.tool()
    def team_record(team: str, season: Optional[int] = None,
                    competition: Optional[str] = None, venue: str = "either") -> str:
        """Win/draw/loss record, goals and win rate for a team, optionally filtered
        by season, competition and venue ('home'/'away'/'either')."""
        return tool_team_record(team, season, competition, venue)

    @mcp.tool()
    def compare_teams(team_a: str, team_b: str, season: Optional[int] = None) -> str:
        """Compare two teams: head-to-head plus each team's overall record."""
        return tool_compare_teams(team_a, team_b, season)

    @mcp.tool()
    def standings(competition: str = "Brasileirão Série A", season: int = 2019,
                  limit: Optional[int] = None) -> str:
        """League table for a competition+season, calculated from match results."""
        return tool_standings(competition, season, limit)

    @mcp.tool()
    def season_champion(competition: str = "Brasileirão Série A", season: int = 2019) -> str:
        """Who won (topped the table of) a competition in a given season."""
        return tool_season_champion(competition, season)

    @mcp.tool()
    def search_players(name: Optional[str] = None, nationality: Optional[str] = None,
                       club: Optional[str] = None, position: Optional[str] = None,
                       min_overall: Optional[int] = None, limit: int = 20) -> str:
        """Search FIFA players by name, nationality, club, position or min rating."""
        return tool_search_players(name, nationality, club, position, min_overall, limit)

    @mcp.tool()
    def top_players(nationality: Optional[str] = None, club: Optional[str] = None,
                    limit: int = 10) -> str:
        """Highest-rated players, optionally filtered by nationality and/or club."""
        return tool_top_players(nationality, club, limit)

    @mcp.tool()
    def biggest_wins(competition: Optional[str] = None, season: Optional[int] = None,
                     limit: int = 10) -> str:
        """The largest victory margins in the dataset, optionally scoped."""
        return tool_biggest_wins(competition, season, limit)

    @mcp.tool()
    def average_goals(competition: Optional[str] = None, season: Optional[int] = None) -> str:
        """Average goals per match plus home/away/draw rates, optionally scoped."""
        return tool_average_goals(competition, season)

    @mcp.tool()
    def best_record(venue: str = "home", competition: Optional[str] = None,
                    season: Optional[int] = None, min_matches: int = 5, limit: int = 10) -> str:
        """Rank teams by win rate for a venue ('home'/'away'/'either')."""
        return tool_best_record(venue, competition, season, min_matches, limit)

    @mcp.tool()
    def list_seasons(competition: Optional[str] = None) -> str:
        """List the seasons available, optionally for one competition."""
        return tool_list_seasons(competition)

    @mcp.tool()
    def list_competitions() -> str:
        """List all competitions present in the dataset."""
        return tool_list_competitions()

    return mcp


# Module-level app for `mcp run server.py` style launchers (only if mcp present).
mcp = build_server() if FastMCP is not None else None


def main() -> None:
    if mcp is None:
        raise SystemExit("The 'mcp' package is required to run the server.")
    # Warm the cache so the first client call is fast.
    get_graph()
    mcp.run()


if __name__ == "__main__":
    main()
