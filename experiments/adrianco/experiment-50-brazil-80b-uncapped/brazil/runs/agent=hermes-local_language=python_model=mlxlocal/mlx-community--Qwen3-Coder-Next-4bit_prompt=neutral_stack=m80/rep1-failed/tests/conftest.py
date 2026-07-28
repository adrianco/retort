# Test fixtures for Brazilian Soccer MCP Server
"""Test fixtures for the Brazilian Soccer MCP Server."""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import Match, Player, TeamStats, TeamComparison, CompetitionStandings, BigWin


@pytest.fixture
def sample_match():
    """Create a sample Match object."""
    return Match(
        id=1,
        datetime="2023-09-24 18:30:00",
        home_team="Flamengo",
        away_team="Fluminense",
        home_team_state="RJ",
        away_team_state="RJ",
        home_goal=2,
        away_goal=1,
        season=2023,
        round=10,
        competition="Brasileirão",
    )


@pytest.fixture
def sample_player():
    """Create a sample Player object."""
    return Player(
        id=190871,
        name="Neymar Jr",
        age=31,
        nationality="Brazil",
        overall=92,
        potential=93,
        club="Paris Saint-Germain",
        position="LW",
        jersey_number=10,
    )


@pytest.fixture
def sample_team_stats():
    """Create a sample TeamStats object."""
    return TeamStats(
        team_name="Palmeiras",
        competition="Brasileirão",
        season=2023,
        matches=38,
        wins=25,
        draws=8,
        losses=5,
        goals_for=75,
        goals_against=35,
    )


@pytest.fixture
def sample_competition_standings():
    """Create a sample CompetitionStandings object."""
    return CompetitionStandings(
        competition="Brasileirão",
        season=2023,
        position=1,
        team="Flamengo",
        matches_played=38,
        wins=28,
        draws=6,
        losses=4,
        goals_for=76,
        goals_against=32,
        goal_difference=44,
        points=90,
    )
