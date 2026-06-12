"""MCP server exposing Brazilian soccer queries as tools.

The server is the only public interface to the system. Tools accept and return
plain JSON-friendly values described in the domain's own language ("find
matches", "team record", "standings", "search players").

Configuration:
    The data directory is taken from the ``data_dir`` argument to
    ``create_server`` or, when run as a process, from the ``SOCCER_DATA_DIR``
    environment variable (defaulting to ``./data/kaggle``).
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .repository import SoccerRepository

DEFAULT_DATA_DIR = os.path.join("data", "kaggle")


def create_server(data_dir: str | None = None) -> FastMCP:
    """Build a configured :class:`FastMCP` server over the data in ``data_dir``."""
    data_dir = data_dir or os.environ.get("SOCCER_DATA_DIR") or DEFAULT_DATA_DIR
    repo = SoccerRepository.from_dir(data_dir)
    mcp = FastMCP("brazilian-soccer")

    @mcp.tool()
    def find_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        venue: str | None = None,
        limit: int = 50,
    ) -> dict:
        """Find matches by team, opponent, competition, season, date or venue.

        venue may be "home" or "away" (relative to ``team``). Returns the list of
        matching matches ordered by date.
        """
        matches = repo.find_matches(
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            venue=venue,
            limit=limit,
        )
        return {"count": len(matches), "matches": [m.to_dict() for m in matches]}

    @mcp.tool()
    def head_to_head(
        team_a: str, team_b: str, competition: str | None = None
    ) -> dict:
        """Compare two teams head-to-head: wins, draws and goals between them."""
        return repo.head_to_head(team_a, team_b, competition=competition)

    @mcp.tool()
    def team_record(
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str | None = None,
    ) -> dict:
        """Team record: matches, wins/draws/losses, goals and win rate.

        Optionally filtered by season, competition and venue ("home"/"away").
        """
        return repo.team_record(
            team, season=season, competition=competition, venue=venue
        )

    @mcp.tool()
    def competition_standings(
        competition: str, season: int, limit: int | None = None
    ) -> dict:
        """League standings for a competition and season, calculated from matches."""
        table = repo.standings(competition, season, limit=limit)
        return {"competition": competition, "season": season, "standings": table}

    @mcp.tool()
    def competition_winner(competition: str, season: int) -> dict:
        """The champion of a competition in a season (top of the table)."""
        champ = repo.competition_winner(competition, season)
        return {"winner": champ}

    @mcp.tool()
    def list_competitions() -> dict:
        """List the competitions available in the dataset."""
        return {"competitions": repo.list_competitions()}

    @mcp.tool()
    def competition_statistics(
        competition: str | None = None, season: int | None = None
    ) -> dict:
        """Aggregate statistics: average goals per match, home win rate, totals."""
        return repo.statistics(competition=competition, season=season)

    @mcp.tool()
    def biggest_wins(
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> dict:
        """The biggest victories (largest goal margin) in the data."""
        wins = repo.biggest_wins(
            competition=competition, season=season, limit=limit
        )
        return {"count": len(wins), "matches": wins}

    @mcp.tool()
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 50,
    ) -> dict:
        """Search FIFA players by name, nationality, club, position or rating."""
        players = repo.search_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            limit=limit,
        )
        return {"count": len(players), "players": [p.to_dict() for p in players]}

    @mcp.tool()
    def top_players(
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Highest-rated players, optionally by nationality, club or position."""
        players = repo.search_players(
            nationality=nationality,
            club=club,
            position=position,
            limit=limit,
        )
        return {"count": len(players), "players": [p.to_dict() for p in players]}

    return mcp


def main() -> None:
    """Run the MCP server over stdio."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
