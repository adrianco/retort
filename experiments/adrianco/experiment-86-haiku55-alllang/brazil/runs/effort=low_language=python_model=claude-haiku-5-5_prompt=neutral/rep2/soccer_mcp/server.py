"""MCP server exposing the Brazilian soccer dataset as tools.

Run with ``python -m soccer_mcp`` (stdio transport). The data directory defaults
to ``data/kaggle`` and can be overridden with the ``SOCCER_DATA_DIR`` variable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import formatting as fmt
from .loader import DEFAULT_DATA_DIR, Dataset, load_dataset
from .queries import QueryError, SoccerQueries
from .normalize import COMPETITION_NAMES, resolve_competition

INSTRUCTIONS = (
    "Answers questions about Brazilian soccer from Kaggle datasets: Brasileirão "
    "(2003-2023), Copa do Brasil, Copa Libertadores matches, and FIFA player ratings. "
    "Team names may include state suffixes (Palmeiras-SP) or be written in full. "
    "Competition values: 'Brasileirão Série A', 'Série B', 'Série C', 'Copa do Brasil', "
    "'Copa Libertadores'. Dates accept YYYY-MM-DD or DD/MM/YYYY."
)


def create_server(data_dir: Path | str | None = None,
                  dataset: Optional[Dataset] = None) -> FastMCP:
    """Build the MCP server. Pass ``dataset`` to reuse an already-loaded dataset."""
    if dataset is None:
        dataset = load_dataset(data_dir or os.environ.get("SOCCER_DATA_DIR", DEFAULT_DATA_DIR))
    queries = SoccerQueries(dataset)
    mcp = FastMCP("brazilian-soccer", instructions=INSTRUCTIONS)

    def guarded(call):
        """Return query errors as text so the LLM can correct its arguments."""
        try:
            return call()
        except (QueryError, ValueError) as exc:
            return f"Error: {exc}"

    @mcp.tool()
    def search_matches(team: Optional[str] = None, opponent: Optional[str] = None,
                       competition: Optional[str] = None, season: Optional[int] = None,
                       start_date: Optional[str] = None, end_date: Optional[str] = None,
                       venue: str = "either", limit: int = 20) -> str:
        """Find matches by team (optionally vs an opponent), competition, season, date range
        and venue ('either', 'home' or 'away'). Newest first."""
        def run():
            matches = queries.find_matches(team=team, opponent=opponent, competition=competition,
                                           season=season, start=start_date, end=end_date,
                                           venue=venue)
            title = "Matches for " + fmt.describe_filters(
                ("team", team), ("vs", opponent), ("competition", competition),
                ("season", season))
            return fmt.format_matches(matches, title, limit=limit)
        return guarded(run)

    @mcp.tool()
    def head_to_head(team_a: str, team_b: str, competition: Optional[str] = None,
                     season: Optional[int] = None) -> str:
        """Head-to-head record between two clubs: wins, draws, goals and recent meetings."""
        return guarded(lambda: fmt.format_head_to_head(
            queries.head_to_head(team_a, team_b, competition=competition, season=season)))

    @mcp.tool()
    def team_record(team: str, season: Optional[int] = None, competition: Optional[str] = None,
                    venue: str = "either") -> str:
        """A team's wins, draws, losses, goals and win rate, filtered by season, competition
        and venue ('either', 'home' or 'away')."""
        return guarded(lambda: fmt.format_team_record(
            queries.team_record(team, season=season, competition=competition, venue=venue)))

    @mcp.tool()
    def standings(season: int, competition: str = "Brasileirão Série A") -> str:
        """League table for a season, calculated from match results (3 pts win, 1 pt draw)."""
        return guarded(lambda: fmt.format_standings(
            queries.standings(season, competition), season, _competition_name(competition)))

    @mcp.tool()
    def league_stats(competition: Optional[str] = None, season: Optional[int] = None) -> str:
        """Goals per match and home/draw/away result rates for a competition and/or season."""
        return guarded(lambda: fmt.format_league_stats(
            queries.league_stats(competition=competition, season=season)))

    @mcp.tool()
    def biggest_wins(competition: Optional[str] = None, season: Optional[int] = None,
                     limit: int = 5) -> str:
        """Matches with the largest winning margin."""
        return guarded(lambda: fmt.format_biggest_wins(
            queries.biggest_wins(competition=competition, season=season, limit=limit)))

    @mcp.tool()
    def venue_leaderboard(venue: str = "home", competition: Optional[str] = None,
                          season: Optional[int] = None, min_matches: int = 10,
                          limit: int = 5) -> str:
        """Teams ranked by win rate at home ('home') or away ('away')."""
        return guarded(lambda: fmt.format_leaderboard(
            queries.venue_leaderboard(venue, competition=competition, season=season,
                                      min_matches=min_matches, limit=limit),
            venue, min_matches))

    @mcp.tool()
    def search_teams(query: str, limit: int = 20) -> str:
        """Find club names in the match data, to check how a club is spelled before querying."""
        return guarded(lambda: fmt.format_teams(queries.search_teams(query, limit), query))

    @mcp.tool()
    def search_players(name: Optional[str] = None, nationality: Optional[str] = None,
                       club: Optional[str] = None, position: Optional[str] = None,
                       min_overall: Optional[int] = None, sort_by: str = "overall",
                       limit: int = 20) -> str:
        """Search FIFA players by name, nationality (e.g. 'Brazil'), club, position
        ('ST', 'CM', or a group: 'forward', 'midfielder', 'defender', 'goalkeeper')
        and minimum overall rating. sort_by: 'overall', 'potential' or 'age'."""
        def run():
            players = queries.search_players(name=name, nationality=nationality, club=club,
                                             position=position, min_overall=min_overall,
                                             sort_by=sort_by, limit=limit)
            return fmt.format_players(players, "Matching players")
        return guarded(run)

    @mcp.tool()
    def brazilian_players_by_club(limit: int = 20) -> str:
        """Brazilian players grouped by Brazilian club, with counts and average rating."""
        return guarded(lambda: fmt.format_brazilian_clubs(
            queries.brazilian_players_by_club(limit=limit)))

    @mcp.tool()
    def list_competitions() -> str:
        """List the competitions in the dataset and the number of matches in each."""
        def run():
            counts: dict[str, int] = {}
            for match in dataset.matches:
                counts[match.competition] = counts.get(match.competition, 0) + 1
            lines = ["Competitions in dataset:"]
            for key, name in COMPETITION_NAMES.items():
                if key in counts:
                    lines.append(f"- {name}: {counts[key]} matches")
            lines.append(f"\nFIFA player records: {len(dataset.players)}")
            return "\n".join(lines)
        return run()

    return mcp


def _competition_name(value: str) -> str:
    key = resolve_competition(value)
    return COMPETITION_NAMES.get(key, value) if key else value


def main() -> None:
    create_server().run()
