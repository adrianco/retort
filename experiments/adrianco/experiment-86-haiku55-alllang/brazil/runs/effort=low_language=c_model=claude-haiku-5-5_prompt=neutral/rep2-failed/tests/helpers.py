"""Shared builders for tests: small in-memory matches and players."""

from datetime import date

from brazil_soccer_mcp.loaders import SERIES_A
from brazil_soccer_mcp.models import Match, Player
from brazil_soccer_mcp.normalize import parse_team


def match(day, home, away, hg, ag, competition=SERIES_A, season=None, home_state=None, away_state=None):
    """Build a Match from readable arguments. `day` is an ISO date string."""
    played = date.fromisoformat(day)
    return Match(
        played_on=played,
        competition=competition,
        season=season or played.year,
        home=parse_team(home, home_state),
        away=parse_team(away, away_state),
        home_goals=hg,
        away_goals=ag,
    )


def player(player_id, name, club, overall, nationality="Brazil", position="ST", age=25):
    return Player(
        player_id=player_id,
        name=name,
        age=age,
        nationality=nationality,
        overall=overall,
        potential=overall,
        club=club,
        position=position,
        value="€1M",
        wage="€10K",
        height="5'10",
        weight="150lbs",
        preferred_foot="Right",
        jersey_number=9,
    )
