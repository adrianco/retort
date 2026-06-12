"""MCP server exposing the Brazilian soccer knowledge graph as tools.

``SoccerService`` holds a :class:`KnowledgeGraph` and turns query results into
human-readable text.  ``build_server`` registers those methods as FastMCP tools
so an LLM can call them.  Run ``python -m brazilian_soccer.server`` to start the
server over stdio.
"""
from __future__ import annotations

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import data_loader
from .data_loader import Match
from .queries import KnowledgeGraph, display_competition

DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle"
)


def _format_match(m: Match) -> str:
    date = m.date.isoformat() if m.date else "????-??-??"
    if m.played:
        score = f"{m.home_goal}-{m.away_goal}"
    else:
        score = "vs"
    detail = display_competition(m.competition)
    if m.round:
        detail += f" Round {m.round}"
    elif m.stage:
        detail += f" {m.stage}"
    return f"{date}: {m.home_team} {score} {m.away_team} ({detail})"


class SoccerService:
    """Query the knowledge graph and format answers as text."""

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    @classmethod
    def from_data_dir(cls, data_dir=DEFAULT_DATA_DIR) -> "SoccerService":
        matches = data_loader.load_matches(data_dir)
        players = data_loader.load_players(data_dir)
        return cls(KnowledgeGraph(matches, players))

    # --- match tools -----------------------------------------------------

    def search_matches(
        self,
        team: Optional[str] = None,
        team2: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 25,
    ) -> str:
        matches = self.kg.find_matches(
            team=team, team2=team2, competition=competition, season=season
        )
        if not matches:
            return "No matches found for the given criteria."
        header = f"Found {len(matches)} match(es):"
        lines = [f"- {_format_match(m)}" for m in matches[:limit]]
        if len(matches) > limit:
            lines.append(f"- ... ({len(matches) - limit} more)")
        return "\n".join([header, *lines])

    def head_to_head(
        self, team_a: str, team_b: str, competition: Optional[str] = None
    ) -> str:
        h2h = self.kg.head_to_head(team_a, team_b, competition=competition)
        if h2h["total"] == 0:
            return f"No matches found between {h2h['team_a']} and {h2h['team_b']}."
        lines = [
            f"{h2h['team_a']} vs {h2h['team_b']} head-to-head "
            f"({h2h['total']} matches):",
            f"- {h2h['team_a']} wins: {h2h['wins_a']}",
            f"- {h2h['team_b']} wins: {h2h['wins_b']}",
            f"- Draws: {h2h['draws']}",
            "",
            "Recent matches:",
        ]
        for m in sorted(
            h2h["matches"], key=lambda x: (x.date is None, x.date), reverse=True
        )[:5]:
            lines.append(f"- {_format_match(m)}")
        return "\n".join(lines)

    # --- team tools ------------------------------------------------------

    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "either",
    ) -> str:
        r = self.kg.team_record(
            team, season=season, competition=competition, venue=venue
        )
        scope = []
        if competition:
            scope.append(competition)
        if season:
            scope.append(str(season))
        if venue != "either":
            scope.append(f"{venue} only")
        suffix = f" ({', '.join(scope)})" if scope else ""
        return (
            f"{r['team']} record{suffix}:\n"
            f"- Matches: {r['matches']}\n"
            f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}\n"
            f"- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']}\n"
            f"- Win rate: {r['win_rate']}%"
        )

    # --- player tools ----------------------------------------------------

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        players = self.kg.find_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            limit=limit,
        )
        if not players:
            return "No players found for the given criteria."
        lines = [f"Found {len(players)} player(s):"]
        for i, p in enumerate(players, 1):
            lines.append(
                f"{i}. {p.name} - Overall: {p.overall}, Position: {p.position}, "
                f"Club: {p.club}, Nationality: {p.nationality}"
            )
        return "\n".join(lines)

    # --- competition tools -----------------------------------------------

    def standings(self, competition: str, season: int, limit: int = 20) -> str:
        table = self.kg.standings(competition, season)
        if not table:
            return f"No standings available for {competition} {season}."
        lines = [f"{competition} {season} standings (calculated from matches):"]
        for i, row in enumerate(table[:limit], 1):
            tag = " - Champion" if i == 1 else ""
            lines.append(
                f"{i}. {row['team']} - {row['points']} pts "
                f"({row['wins']}W, {row['draws']}D, {row['losses']}L) "
                f"GF:{row['goals_for']} GA:{row['goals_against']}{tag}"
            )
        return "\n".join(lines)

    def competition_champion(self, competition: str, season: int) -> str:
        champ = self.kg.champion(competition, season)
        if not champ:
            return f"No champion could be determined for {competition} {season}."
        return f"{competition} {season} champion (calculated from matches): {champ}"

    # --- statistics tools ------------------------------------------------

    def statistics(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> str:
        avg = self.kg.average_goals_per_match(competition=competition, season=season)
        home = self.kg.home_win_rate(competition=competition, season=season)
        biggest = self.kg.biggest_wins(competition=competition, season=season, limit=5)
        scope = []
        if competition:
            scope.append(competition)
        if season:
            scope.append(str(season))
        suffix = f" ({', '.join(scope)})" if scope else ""
        lines = [
            f"Statistics{suffix}:",
            f"- Average goals per match: {avg}",
            f"- Home win rate: {home}%",
        ]
        if biggest:
            lines.append("- Biggest wins:")
            for m in biggest:
                lines.append(f"    {_format_match(m)}")
        return "\n".join(lines)


def build_server(service: SoccerService, name: str = "brazilian-soccer") -> FastMCP:
    """Register the service methods as FastMCP tools and return the server."""
    mcp = FastMCP(name)

    @mcp.tool()
    def search_matches(
        team: Optional[str] = None,
        team2: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 25,
    ) -> str:
        """Search matches by team, opponent, competition and/or season."""
        return service.search_matches(team, team2, competition, season, limit)

    @mcp.tool()
    def head_to_head(
        team_a: str, team_b: str, competition: Optional[str] = None
    ) -> str:
        """Head-to-head record between two teams."""
        return service.head_to_head(team_a, team_b, competition)

    @mcp.tool()
    def team_record(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "either",
    ) -> str:
        """Win/loss/draw and goal record for a team (venue: home/away/either)."""
        return service.team_record(team, season, competition, venue)

    @mcp.tool()
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """Search FIFA players by name, nationality, club, position or rating."""
        return service.search_players(
            name, nationality, club, position, min_overall, limit
        )

    @mcp.tool()
    def standings(competition: str, season: int, limit: int = 20) -> str:
        """League table for a competition/season, computed from match results."""
        return service.standings(competition, season, limit)

    @mcp.tool()
    def competition_champion(competition: str, season: int) -> str:
        """The champion of a competition/season (top of computed standings)."""
        return service.competition_champion(competition, season)

    @mcp.tool()
    def statistics(
        competition: Optional[str] = None, season: Optional[int] = None
    ) -> str:
        """Aggregate stats: avg goals/match, home win rate, biggest wins."""
        return service.statistics(competition, season)

    return mcp


def main() -> None:
    service = SoccerService.from_data_dir()
    mcp = build_server(service)
    mcp.run()


if __name__ == "__main__":
    main()
