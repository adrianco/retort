"""Shared fixtures for behavior-focused query tests."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest

from brazilian_soccer_mcp.models import MatchRecord, PlayerRecord
from brazilian_soccer_mcp.repository import SoccerCatalog
from brazilian_soccer_mcp.service import SoccerQueryService


@pytest.fixture(scope="session")
def full_service() -> SoccerQueryService:
    """Load the real bundled files once for integration and performance tests."""

    return SoccerQueryService.from_data_directory()


def make_catalog(
    matches: list[MatchRecord], players: list[PlayerRecord] | None = None
) -> SoccerCatalog:
    """Build a small indexed catalog for deterministic unit scenarios."""

    players = players or []
    by_team: dict[str, list[MatchRecord]] = defaultdict(list)
    by_season: dict[int, list[MatchRecord]] = defaultdict(list)
    by_competition: dict[str, list[MatchRecord]] = defaultdict(list)
    for match in matches:
        by_team[match.home_team_key].append(match)
        by_team[match.away_team_key].append(match)
        if match.season is not None:
            by_season[match.season].append(match)
        by_competition[match.competition_key].append(match)
    by_name: dict[str, list[PlayerRecord]] = defaultdict(list)
    by_club: dict[str, list[PlayerRecord]] = defaultdict(list)
    by_nationality: dict[str, list[PlayerRecord]] = defaultdict(list)
    for player in players:
        by_name[player.name_key].append(player)
        by_club[player.club_key].append(player)
        by_nationality[player.nationality_key].append(player)
    return SoccerCatalog(
        data_directory=Path("/fixture-data"),
        matches=tuple(matches),
        players=tuple(players),
        source_row_counts={"fixture": len(matches), "fifa_players": len(players)},
        source_files={"fixture": "fixture.csv", "fifa_players": "players.csv"},
        matches_by_team={key: tuple(value) for key, value in by_team.items()},
        matches_by_season={key: tuple(value) for key, value in by_season.items()},
        matches_by_competition={key: tuple(value) for key, value in by_competition.items()},
        players_by_name={key: tuple(value) for key, value in by_name.items()},
        players_by_club={key: tuple(value) for key, value in by_club.items()},
        players_by_nationality={key: tuple(value) for key, value in by_nationality.items()},
    )


def match(
    identifier: str,
    home: str,
    away: str,
    home_goals: int | None,
    away_goals: int | None,
    *,
    day: date = date(2023, 1, 1),
    season: int = 2023,
    competition: str = "Brasileirão",
    source: str = "brasileirao_matches",
    round_value: str | None = None,
) -> MatchRecord:
    """Create a canonical fixture match with the supplied raw display values."""

    from brazilian_soccer_mcp.normalization import normalize_competition, normalize_team

    return MatchRecord(
        id=f"{source}:{identifier}",
        source=source,
        source_file=f"{source}.csv",
        competition=competition,
        competition_key=normalize_competition(competition),
        match_date=day,
        season=season,
        round=round_value,
        stage=None,
        home_team=home,
        away_team=away,
        home_team_key=normalize_team(home),
        away_team_key=normalize_team(away),
        home_goals=home_goals,
        away_goals=away_goals,
    )


def player(
    identifier: str,
    name: str,
    *,
    nationality: str = "Brazil",
    club: str = "São Paulo FC",
    position: str = "ST",
    overall: int = 80,
) -> PlayerRecord:
    """Create a canonical FIFA-player snapshot for a unit scenario."""

    from brazilian_soccer_mcp.normalization import normalize_team, normalize_text

    return PlayerRecord(
        id=identifier,
        name=name,
        name_key=normalize_text(name),
        age=25,
        nationality=nationality,
        nationality_key=normalize_text(nationality),
        overall=overall,
        potential=overall + 2,
        club=club,
        club_key=normalize_team(club),
        position=position,
        jersey_number=9,
        height="6'0",
        weight="170lbs",
        attributes={"Finishing": 84},
    )

