"""Acceptance: Competition Queries (TASK.md section 4).

Standings and champions calculated from match results.
"""

import pytest

pytestmark = pytest.mark.asyncio


def _round_robin(system):
    """A tiny 3-team single round-robin where Flamengo finishes top."""
    # Flamengo beats both opponents.
    system.add_brasileirao_match("Flamengo-RJ", "Santos-SP", 2, 0, 2019)
    system.add_brasileirao_match("Flamengo-RJ", "Palmeiras-SP", 1, 0, 2019)
    # Palmeiras beats Santos; Santos loses both.
    system.add_brasileirao_match("Palmeiras-SP", "Santos-SP", 3, 1, 2019)


async def test_who_won_the_season(soccer_system):
    # "Who won the 2019 Brasileirao?"
    _round_robin(soccer_system)

    async with soccer_system.running() as client:
        result = await client.call(
            "competition_winner", competition="Brasileirão", season=2019
        )

    winner = result["winner"]
    assert winner["team"] == "Flamengo"
    assert winner["points"] == 6  # two wins
    assert winner["position"] == 1


async def test_standings_are_ordered_by_points(soccer_system):
    _round_robin(soccer_system)

    async with soccer_system.running() as client:
        result = await client.call(
            "competition_standings", competition="Brasileirão", season=2019
        )

    table = result["standings"]
    assert [r["team"] for r in table] == ["Flamengo", "Palmeiras", "Santos"]
    assert [r["points"] for r in table] == [6, 3, 0]
    assert table[0]["position"] == 1


async def test_standings_use_goal_difference_as_tiebreaker(soccer_system):
    # Two teams on equal points; better goal difference ranks higher.
    soccer_system.add_brasileirao_match("Team A", "Weak", 5, 0, 2020)
    soccer_system.add_brasileirao_match("Team B", "Weak", 2, 0, 2020)
    soccer_system.add_brasileirao_match("Weak", "Other", 0, 0, 2020)

    async with soccer_system.running() as client:
        result = await client.call(
            "competition_standings", competition="Brasileirão", season=2020
        )

    table = result["standings"]
    top_two = [r["team"] for r in table[:2]]
    assert top_two == ["Team A", "Team B"]


async def test_standings_are_per_season(soccer_system):
    soccer_system.add_brasileirao_match("Flamengo-RJ", "Santos-SP", 1, 0, 2018)
    soccer_system.add_brasileirao_match("Santos-SP", "Flamengo-RJ", 1, 0, 2019)

    async with soccer_system.running() as client:
        result = await client.call(
            "competition_standings", competition="Brasileirão", season=2019
        )

    table = result["standings"]
    champion = table[0]["team"]
    assert champion == "Santos"


async def test_list_available_competitions(soccer_system):
    soccer_system.add_brasileirao_match("Flamengo-RJ", "Santos-SP", 1, 0, 2019)
    soccer_system.add_cup_match("Flamengo", "Corinthians", 2, 0, 2019)
    soccer_system.add_libertadores_match("Flamengo", "River Plate", 2, 1, 2019)

    async with soccer_system.running() as client:
        result = await client.call("list_competitions")

    competitions = set(result["competitions"])
    assert {"Brasileirão", "Copa do Brasil", "Copa Libertadores"} <= competitions
