"""
================================================================================
 Module: server
================================================================================
Context
-------
The MCP (Model Context Protocol) server entry point.  It wraps the
:class:`SoccerQueryEngine` with a set of MCP *tools* that an LLM client can call
to answer natural-language questions about Brazilian soccer.  Each tool maps to
one capability category from the specification and returns a human-readable,
pre-formatted string (the answer formats shown in TASK.md).

This is the only module that imports the third-party ``mcp`` package, and the
import is intentionally performed inside ``build_server`` / ``main`` so that the
rest of the package (and the entire test suite) can be imported and exercised in
environments where ``mcp`` is not installed.

Run with:
    python -m brazilian_soccer_mcp.server          # stdio transport
or, after installing as a script:
    brazilian-soccer-mcp
================================================================================
"""

from __future__ import annotations

from typing import Optional

from .knowledge_graph import KnowledgeGraph
from . import queries
from .queries import SoccerQueryEngine

# The knowledge graph is loaded once at process start and shared by all tools.
_ENGINE: Optional[SoccerQueryEngine] = None


def get_engine() -> SoccerQueryEngine:
    """Return the lazily-initialized, process-wide query engine."""
    global _ENGINE
    if _ENGINE is None:
        graph = KnowledgeGraph.from_data_dir()
        _ENGINE = SoccerQueryEngine(graph)
    return _ENGINE


def build_server(engine: Optional[SoccerQueryEngine] = None):
    """Construct and return a FastMCP server with all soccer tools registered.

    ``engine`` may be injected for testing; otherwise the shared engine is used.
    The ``mcp`` import lives here so importing this module never requires it.
    """
    from mcp.server.fastmcp import FastMCP

    eng = engine or get_engine()
    mcp = FastMCP("brazilian-soccer")

    # ------------------------------------------------------------ match tools
    @mcp.tool()
    def find_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 25,
    ) -> str:
        """Find matches by team, opponent, competition, season or date range.

        Returns a formatted list of matches (date, score, competition) and, when
        both team and opponent are given, the head-to-head summary.
        """
        result = eng.find_matches(team=team, opponent=opponent,
                                  competition=competition, season=season,
                                  date_from=date_from, date_to=date_to,
                                  limit=limit)
        title = "Matches"
        if team and opponent:
            title = f"{team} vs {opponent}"
        elif team:
            title = f"{team} matches"
        return queries.format_matches(result, title)

    @mcp.tool()
    def last_match_between(team_a: str, team_b: str) -> str:
        """Return the most recent match played between two teams."""
        m = eng.last_match_between(team_a, team_b)
        if not m:
            return f"No matches found between {team_a} and {team_b}."
        return queries.format_matches({"count": 1, "matches": [m]},
                                      f"Most recent {team_a} vs {team_b}")

    # ------------------------------------------------------------- team tools
    @mcp.tool()
    def team_record(team: str, season: Optional[int] = None,
                    competition: Optional[str] = None,
                    venue: Optional[str] = None) -> str:
        """Win/draw/loss record and goals for a team.

        ``venue`` may be "home", "away", or omitted for all matches.
        """
        return queries.format_team_record(
            eng.team_record(team, season=season, competition=competition,
                            venue=venue))

    @mcp.tool()
    def head_to_head(team_a: str, team_b: str,
                     competition: Optional[str] = None,
                     season: Optional[int] = None) -> str:
        """Head-to-head record between two teams."""
        return queries.format_head_to_head(
            eng.head_to_head(team_a, team_b, competition=competition, season=season))

    # ----------------------------------------------------------- player tools
    @mcp.tool()
    def find_player(name: str, limit: int = 10) -> str:
        """Search the FIFA player database by (partial) name."""
        return queries.format_players(eng.search_players(name, limit=limit),
                                      f"Players matching '{name}'")

    @mcp.tool()
    def players_at_club(club: str, position: Optional[str] = None,
                        limit: int = 25) -> str:
        """List FIFA players at a club, highest-rated first (optionally by
        position)."""
        result = eng.players_at_club(club, position=position, limit=limit)
        title = f"{result['club']} squad (avg overall {result['average_overall']})"
        return queries.format_players(result, title)

    @mcp.tool()
    def top_players(nationality: Optional[str] = None,
                    club: Optional[str] = None,
                    position: Optional[str] = None,
                    limit: int = 10) -> str:
        """Top-rated players, optionally filtered by nationality, club and/or
        position.  E.g. nationality="Brazil" for the best Brazilian players."""
        return queries.format_players(
            eng.top_players(nationality=nationality, club=club,
                            position=position, limit=limit),
            "Top players")

    # ------------------------------------------------------ competition tools
    @mcp.tool()
    def standings(season: int, competition: str = "Brasileirão Série A") -> str:
        """League standings for a season, calculated from match results."""
        return queries.format_standings(eng.standings(season, competition))

    @mcp.tool()
    def champion(season: int, competition: str = "Brasileirão Série A") -> str:
        """Name the champion of a competition/season (top of the table)."""
        c = eng.champion(season, competition)["champion"]
        if not c:
            return f"No data for {competition} {season}."
        return (f"{competition} {season} champion: {c['team']} "
                f"({c['points']} pts, {c['wins']}W {c['draws']}D {c['losses']}L)")

    @mcp.tool()
    def relegated_teams(season: int, competition: str = "Brasileirão Série A",
                        count: int = 4) -> str:
        """Bottom ``count`` teams (relegation zone) for a season."""
        rel = eng.relegated_teams(season, competition, count=count)["relegated"]
        if not rel:
            return f"No data for {competition} {season}."
        lines = [f"Relegated from {competition} {season}:"]
        for r in rel:
            lines.append(f"- {r['team']} ({r['points']} pts)")
        return "\n".join(lines)

    # ----------------------------------------------------- statistical tools
    @mcp.tool()
    def average_goals(competition: Optional[str] = None,
                      season: Optional[int] = None) -> str:
        """Average goals per match plus home/draw/away win rates."""
        s = eng.average_goals(competition=competition, season=season)
        scope = " ".join(str(x) for x in (s.get("competition"), s.get("season")) if x)
        return (f"Statistics{(' for ' + scope) if scope else ''} "
                f"({s['matches']} matches):\n"
                f"- Average goals per match: {s['average_goals']}\n"
                f"- Home win rate: {s['home_win_rate']}%\n"
                f"- Draw rate: {s['draw_rate']}%\n"
                f"- Away win rate: {s['away_win_rate']}%")

    @mcp.tool()
    def biggest_wins(competition: Optional[str] = None,
                     season: Optional[int] = None, limit: int = 10) -> str:
        """Largest victory margins in the data (optionally scoped)."""
        return queries.format_matches(
            {"count": limit, "matches": eng.biggest_wins(
                competition=competition, season=season, limit=limit)["matches"]},
            "Biggest wins", show=limit)

    @mcp.tool()
    def best_home_record(season: Optional[int] = None,
                         competition: Optional[str] = None, limit: int = 5) -> str:
        """Teams with the best home win-rate (min 5 home matches)."""
        rows = eng.best_home_record(season=season, competition=competition,
                                    limit=limit)["teams"]
        lines = ["Best home records:"]
        for r in rows:
            lines.append(f"- {r['team']}: {r['win_rate']}% "
                         f"({r['wins']}W {r['draws']}D {r['losses']}L)")
        return "\n".join(lines)

    @mcp.tool()
    def best_away_record(season: Optional[int] = None,
                         competition: Optional[str] = None, limit: int = 5) -> str:
        """Teams with the best away win-rate (min 5 away matches)."""
        rows = eng.best_away_record(season=season, competition=competition,
                                    limit=limit)["teams"]
        lines = ["Best away records:"]
        for r in rows:
            lines.append(f"- {r['team']}: {r['win_rate']}% "
                         f"({r['wins']}W {r['draws']}D {r['losses']}L)")
        return "\n".join(lines)

    @mcp.tool()
    def list_competitions() -> str:
        """List the competitions and seasons available in the knowledge graph."""
        g = eng.graph
        comps = g.competitions()
        seasons = g.seasons()
        summary = g.stats_summary()
        return ("Knowledge graph contents:\n"
                f"- Matches: {summary['matches']}, Players: {summary['players']}, "
                f"Teams: {summary['teams']}\n"
                f"- Competitions: {', '.join(comps)}\n"
                f"- Seasons: {min(seasons)}-{max(seasons)}")

    return mcp


def main() -> None:
    """Console-script / module entry point: run the server over stdio."""
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
