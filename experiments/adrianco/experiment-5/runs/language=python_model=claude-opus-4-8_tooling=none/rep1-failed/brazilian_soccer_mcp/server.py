"""
================================================================================
Brazilian Soccer MCP Server - MCP Transport Layer
================================================================================

CONTEXT
-------
Exposes the ``KnowledgeGraph`` query engine as MCP (Model Context Protocol)
tools so an LLM client can answer natural-language questions about Brazilian
soccer. Each tool is a thin wrapper that parses arguments, calls the engine and
returns a formatted text block (see ``formatting``).

This is the ONLY module that depends on the third-party ``mcp`` SDK. The import
is guarded (done lazily inside ``build_server``) so that importing the package
for data/engine use - and running the test-suite - never requires ``mcp`` to be
installed. Install it with::

    pip install "mcp[cli]"

and run the server over stdio with::

    python -m brazilian_soccer_mcp.server

TOOLS
-----
  search_matches, last_match, head_to_head, team_stats, compare_teams,
  search_players, get_player, club_squad, league_standings, season_champion,
  relegated_teams, average_goals, biggest_wins, best_home_records,
  best_away_records, list_competitions, list_seasons
================================================================================
"""

from __future__ import annotations

from typing import Optional

from .data_loader import load_knowledge_graph
from . import formatting as fmt

# The populated knowledge graph is loaded once and cached.
_KG = None


def get_kg():
    """Lazily build and cache the knowledge graph."""
    global _KG
    if _KG is None:
        _KG = load_knowledge_graph()
    return _KG


def build_server():
    """Construct and return a configured FastMCP server instance.

    The ``mcp`` import is performed here (not at module import) so the rest of
    the package works without the SDK installed.
    """
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("brazilian-soccer")
    kg = get_kg()

    # --- 1. Match queries ---------------------------------------------
    @mcp.tool()
    def search_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 25,
    ) -> str:
        """Find matches by team, opponent, competition, season or date range.

        Dates are ISO ``YYYY-MM-DD``. Returns a formatted list of matches."""
        matches = kg.find_matches(
            team=team, opponent=opponent, competition=competition,
            season=season, start_date=start_date, end_date=end_date,
            limit=limit,
        )
        return fmt.format_matches(matches, max_rows=limit)

    @mcp.tool()
    def last_match(team: str, opponent: Optional[str] = None,
                  competition: Optional[str] = None) -> str:
        """When did a team last play (optionally against a specific opponent)?"""
        m = kg.last_match(team, opponent=opponent, competition=competition)
        return m.describe() if m else "No match found."

    @mcp.tool()
    def head_to_head(team_a: str, team_b: str,
                    competition: Optional[str] = None,
                    season: Optional[int] = None) -> str:
        """Head-to-head record and match list between two teams."""
        return fmt.format_head_to_head(
            kg.head_to_head(team_a, team_b, competition, season)
        )

    # --- 2. Team queries ----------------------------------------------
    @mcp.tool()
    def team_stats(team: str, season: Optional[int] = None,
                  competition: Optional[str] = None, venue: str = "all") -> str:
        """W/D/L, goals and win-rate for a team. ``venue`` = all|home|away."""
        return fmt.format_team_stats(
            kg.team_stats(team, season=season, competition=competition,
                          venue=venue)
        )

    @mcp.tool()
    def compare_teams(team_a: str, team_b: str, season: Optional[int] = None,
                     competition: Optional[str] = None) -> str:
        """Compare two teams' records plus their head-to-head."""
        data = kg.compare_teams(team_a, team_b, season, competition)
        return (
            fmt.format_team_stats(data["team_a"]) + "\n\n" +
            fmt.format_team_stats(data["team_b"]) + "\n\n" +
            fmt.format_head_to_head(data["head_to_head"])
        )

    # --- 3. Player queries --------------------------------------------
    @mcp.tool()
    def search_players(name: Optional[str] = None,
                      nationality: Optional[str] = None,
                      club: Optional[str] = None, position: Optional[str] = None,
                      min_overall: Optional[int] = None, limit: int = 20) -> str:
        """Search FIFA players by name, nationality, club, position or rating."""
        players = kg.find_players(
            name=name, nationality=nationality, club=club, position=position,
            min_overall=min_overall, limit=limit,
        )
        return fmt.format_players(players, max_rows=limit)

    @mcp.tool()
    def get_player(name: str) -> str:
        """Look up a single player's profile by name."""
        p = kg.get_player(name)
        if not p:
            return f"No player found matching '{name}'."
        d = p.to_dict()
        return (
            f"{d['name']}\n"
            f"- Overall: {d['overall']} (Potential: {d['potential']})\n"
            f"- Position: {d['position']}, Age: {d['age']}\n"
            f"- Nationality: {d['nationality']}\n"
            f"- Club: {d['club']}"
        )

    @mcp.tool()
    def club_squad(club: str) -> str:
        """List players at a club with the average overall rating."""
        s = kg.club_summary(club)
        header = (f"{s['club']}: {s['player_count']} players "
                  f"(avg rating: {s['average_overall']})")
        return fmt.format_players(s["players"], header=header)

    # --- 4. Competition queries ---------------------------------------
    @mcp.tool()
    def league_standings(season: int,
                        competition: str = "Brasileirão Série A") -> str:
        """Compute a season league table from match results."""
        rows = kg.standings(season, competition)
        return fmt.format_standings(rows, season, competition)

    @mcp.tool()
    def season_champion(season: int,
                       competition: str = "Brasileirão Série A") -> str:
        """Who won a given season (top of the computed standings)?"""
        champ = kg.champion(season, competition)
        if not champ:
            return f"No champion could be determined for {competition} {season}."
        return (f"{competition} {season} champion: {champ['team']} "
                f"({champ['points']} pts, {champ['wins']}W "
                f"{champ['draws']}D {champ['losses']}L)")

    @mcp.tool()
    def relegated_teams(season: int,
                       competition: str = "Brasileirão Série A",
                       count: int = 4) -> str:
        """Bottom teams of the season standings (relegation zone)."""
        rows = kg.relegated(season, competition, count)
        if not rows:
            return f"No standings for {competition} {season}."
        out = [f"{competition} {season} relegation zone (bottom {count}):"]
        for r in rows:
            out.append(f"{r['position']}. {r['team']} - {r['points']} pts")
        return "\n".join(out)

    # --- 5. Statistical analysis --------------------------------------
    @mcp.tool()
    def average_goals(competition: Optional[str] = None,
                     season: Optional[int] = None) -> str:
        """Average goals per match for the filtered set."""
        avg = kg.average_goals_per_match(competition, season)
        scope = competition or "all competitions"
        if season:
            scope += f" {season}"
        return f"Average goals per match ({scope}): {avg}"

    @mcp.tool()
    def biggest_wins(competition: Optional[str] = None,
                    season: Optional[int] = None, limit: int = 10) -> str:
        """Largest goal-margin victories in the filtered set."""
        matches = kg.biggest_wins(competition, season, limit)
        return fmt.format_biggest_wins(matches)

    @mcp.tool()
    def best_home_records(competition: Optional[str] = None,
                         season: Optional[int] = None,
                         min_matches: int = 5) -> str:
        """Teams ranked by home win-rate."""
        rows = kg.best_home_record(competition, season, min_matches)
        return fmt.format_venue_ranking(rows, "home")

    @mcp.tool()
    def best_away_records(competition: Optional[str] = None,
                         season: Optional[int] = None,
                         min_matches: int = 5) -> str:
        """Teams ranked by away win-rate."""
        rows = kg.best_away_record(competition, season, min_matches)
        return fmt.format_venue_ranking(rows, "away")

    # --- Discovery helpers --------------------------------------------
    @mcp.tool()
    def list_competitions() -> str:
        """List all competitions available in the dataset."""
        return "Competitions:\n" + "\n".join(
            f"- {c}" for c in kg.competitions()
        )

    @mcp.tool()
    def list_seasons(competition: Optional[str] = None) -> str:
        """List all seasons available (optionally for one competition)."""
        seasons = kg.seasons(competition)
        return "Seasons: " + ", ".join(str(s) for s in seasons)

    return mcp


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
