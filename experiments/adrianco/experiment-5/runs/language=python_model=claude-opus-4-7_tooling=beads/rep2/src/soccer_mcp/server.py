"""MCP server entry point.

Exposes the query modules in this package as MCP tools so an LLM client (or
any MCP-aware harness) can answer natural-language questions about Brazilian
soccer. Each tool is a thin wrapper that funnels arguments into the
corresponding query function and returns its result; the heavy lifting lives
in :mod:`soccer_mcp.matches`, :mod:`soccer_mcp.teams`,
:mod:`soccer_mcp.players`, :mod:`soccer_mcp.competitions`, and
:mod:`soccer_mcp.stats`.

Data is loaded once at startup via :class:`SoccerData.load` and held in
module-level state so each tool call is just a pandas filter (well under the
two-second simple-lookup budget). The server speaks stdio MCP by default,
which is the transport every current MCP client supports.
"""

from __future__ import annotations

import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from soccer_mcp import competitions as comp_mod
from soccer_mcp import matches as match_mod
from soccer_mcp import players as player_mod
from soccer_mcp import stats as stats_mod
from soccer_mcp import teams as team_mod
from soccer_mcp.data import DEFAULT_DATA_DIR, SoccerData

logger = logging.getLogger("soccer_mcp")

_state: dict[str, SoccerData | None] = {"data": None}


def get_data() -> SoccerData:
    if _state["data"] is None:
        _state["data"] = SoccerData.load()
    return _state["data"]


def build_server(data_dir: Path | str | None = None) -> FastMCP:
    """Construct (but don't run) the MCP server.

    Exposing this as a separate function makes the server importable from
    tests and from notebooks without immediately blocking on stdio.
    """
    if data_dir is not None:
        _state["data"] = SoccerData.load(data_dir)
    else:
        get_data()  # eager-load with default path

    mcp = FastMCP("brazilian-soccer-mcp")

    @mcp.tool()
    def find_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        home_only: bool = False,
        away_only: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        """Find matches that match the given filters. All filters are optional.

        Use this for questions like "Show me all Flamengo vs Fluminense matches"
        or "What matches did Palmeiras play in 2023?".
        """
        return match_mod.find_matches(
            get_data(),
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            start_date=start_date,
            end_date=end_date,
            home_only=home_only,
            away_only=away_only,
            limit=limit,
        )

    @mcp.tool()
    def head_to_head(team_a: str, team_b: str, competition: str | None = None) -> dict:
        """Wins/losses/draws and the full match list between two teams."""
        return match_mod.head_to_head(get_data(), team_a, team_b, competition=competition)

    @mcp.tool()
    def last_match_between(team_a: str, team_b: str) -> dict | None:
        """Most recent match between two teams across every competition."""
        return match_mod.last_match_between(get_data(), team_a, team_b)

    @mcp.tool()
    def biggest_wins(competition: str | None = None, limit: int = 10) -> list[dict]:
        """Largest goal-difference results, optionally for one competition."""
        return match_mod.biggest_wins(get_data(), competition=competition, limit=limit)

    @mcp.tool()
    def team_record(
        team: str,
        competition: str | None = None,
        season: int | None = None,
        side: str = "any",
    ) -> dict:
        """Wins/draws/losses, goals for/against, points and win rate for a team.

        ``side`` is ``"home"``, ``"away"``, or ``"any"`` (default).
        """
        return team_mod.team_record(get_data(), team, competition=competition, season=season, side=side)

    @mcp.tool()
    def home_away_split(team: str, competition: str | None = None, season: int | None = None) -> dict:
        """Home record and away record side by side."""
        return team_mod.home_away_split(get_data(), team, competition=competition, season=season)

    @mcp.tool()
    def team_seasons(team: str) -> list[int]:
        """Every season we have at least one match for this team."""
        return team_mod.team_seasons(get_data(), team)

    @mcp.tool()
    def team_competitions(team: str) -> list[str]:
        """Every competition we have data for that this team appears in."""
        return team_mod.team_competitions(get_data(), team)

    @mcp.tool()
    def compare_teams(team_a: str, team_b: str, competition: str | None = None, season: int | None = None) -> dict:
        """Side-by-side records and head-to-head between two teams."""
        return team_mod.compare_teams(get_data(), team_a, team_b, competition=competition, season=season)

    @mcp.tool()
    def top_scoring_teams(competition: str | None = None, season: int | None = None, limit: int = 10) -> list[dict]:
        """Teams with the most goals scored in the chosen scope."""
        return team_mod.top_scoring_teams(get_data(), competition=competition, season=season, limit=limit)

    @mcp.tool()
    def search_players(name: str, limit: int = 25) -> list[dict]:
        """FIFA-database player search by (accent-insensitive) name substring."""
        return player_mod.search_players_by_name(get_data(), name, limit=limit)

    @mcp.tool()
    def players_by_nationality(nationality: str, limit: int = 25) -> list[dict]:
        """Players from a given country, sorted by overall rating."""
        return player_mod.players_by_nationality(get_data(), nationality, limit=limit)

    @mcp.tool()
    def players_by_club(club: str, position: str | None = None, limit: int = 50) -> list[dict]:
        """Players at a club; optionally restricted to a position code (e.g. ``CF``)."""
        return player_mod.players_by_club(get_data(), club, position=position, limit=limit)

    @mcp.tool()
    def top_players(nationality: str | None = None, position: str | None = None, limit: int = 10) -> list[dict]:
        """Highest-rated players in scope."""
        return player_mod.top_players(get_data(), nationality=nationality, position=position, limit=limit)

    @mcp.tool()
    def brazilian_players_by_club(limit: int = 20) -> list[dict]:
        """Per-club counts and average rating among Brazilian players."""
        return player_mod.brazilian_players_by_club_summary(get_data(), limit=limit)

    @mcp.tool()
    def standings(competition: str, season: int) -> list[dict]:
        """Final table for a competition+season, computed from match results."""
        return comp_mod.standings(get_data(), competition, season)

    @mcp.tool()
    def champion(competition: str, season: int) -> dict | None:
        """Top team in the computed standings for ``competition`` and ``season``."""
        return comp_mod.champion(get_data(), competition, season)

    @mcp.tool()
    def relegated_teams(season: int, n: int = 4) -> list[dict]:
        """Bottom ``n`` of the Brasileirão (Serie A) table for ``season``."""
        return comp_mod.relegated_teams(get_data(), season, n=n)

    @mcp.tool()
    def libertadores_stages(season: int) -> dict[str, list[dict]]:
        """Group the Copa Libertadores matches in a given season by stage."""
        return comp_mod.libertadores_stages(get_data(), season)

    @mcp.tool()
    def goals_per_match(competition: str | None = None, season: int | None = None) -> dict:
        """Per-match average goals and home/away breakdowns."""
        return stats_mod.goals_per_match(get_data(), competition=competition, season=season)

    @mcp.tool()
    def home_advantage(competition: str | None = None, season: int | None = None) -> dict:
        """Home-win/draw/away-win rates in the chosen scope."""
        return stats_mod.home_advantage(get_data(), competition=competition, season=season)

    @mcp.tool()
    def best_home_record(
        competition: str | None = None,
        season: int | None = None,
        min_matches: int = 5,
        limit: int = 10,
    ) -> list[dict]:
        """Teams with the best home win-rate (minimum match threshold)."""
        return stats_mod.best_home_record(
            get_data(), competition=competition, season=season, min_matches=min_matches, limit=limit
        )

    @mcp.tool()
    def best_away_record(
        competition: str | None = None,
        season: int | None = None,
        min_matches: int = 5,
        limit: int = 10,
    ) -> list[dict]:
        """Teams with the best away win-rate (minimum match threshold)."""
        return stats_mod.best_away_record(
            get_data(), competition=competition, season=season, min_matches=min_matches, limit=limit
        )

    @mcp.tool()
    def season_comparison(season_a: int, season_b: int, competition: str | None = None) -> dict:
        """Compare per-season match counts, goals, and home advantage."""
        return stats_mod.season_comparison(get_data(), season_a, season_b, competition=competition)

    @mcp.tool()
    def list_competitions() -> list[str]:
        """List every competition name present in the loaded data."""
        return get_data().competitions()

    @mcp.tool()
    def list_seasons(competition: str | None = None) -> list[int]:
        """List every season present in the loaded data (optionally filtered)."""
        return get_data().seasons(competition)

    return mcp


def main() -> None:
    """Entry point used by the ``brazilian-soccer-mcp`` console script."""
    logging.basicConfig(level=logging.INFO)
    mcp = build_server()
    mcp.run()


if __name__ == "__main__":
    main()
