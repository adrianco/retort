"""Acceptance: Team Queries (TASK.md section 2).

Team match history, win/loss/draw records, goals, head-to-head comparison.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_team_home_record_for_a_season(soccer_system):
    # "What is Corinthians' home record in 2022?"
    soccer_system.add_brasileirao_match("Corinthians-SP", "Santos-SP", 2, 0, 2022)
    soccer_system.add_brasileirao_match("Corinthians-SP", "Palmeiras-SP", 1, 1, 2022)
    soccer_system.add_brasileirao_match("Corinthians-SP", "Flamengo-RJ", 0, 2, 2022)
    # Away matches must be excluded from the home record.
    soccer_system.add_brasileirao_match("Santos-SP", "Corinthians-SP", 3, 0, 2022)

    async with soccer_system.running() as client:
        record = await client.call(
            "team_record", team="Corinthians", season=2022, venue="home"
        )

    assert record["matches"] == 3
    assert record["wins"] == 1
    assert record["draws"] == 1
    assert record["losses"] == 1
    assert record["goals_for"] == 3
    assert record["goals_against"] == 3
    assert record["win_rate"] == pytest.approx(33.3, abs=0.1)


async def test_overall_team_record_counts_home_and_away(soccer_system):
    soccer_system.add_brasileirao_match("Santos-SP", "Bahia-BA", 2, 1, 2021)
    soccer_system.add_brasileirao_match("Gremio-RS", "Santos-SP", 0, 1, 2021)

    async with soccer_system.running() as client:
        record = await client.call("team_record", team="Santos", season=2021)

    assert record["matches"] == 2
    assert record["wins"] == 2
    assert record["goals_for"] == 3
    assert record["goals_against"] == 1
    assert record["points"] == 6


async def test_compare_two_teams_head_to_head(soccer_system):
    # "Compare Palmeiras and Santos head-to-head"
    soccer_system.add_brasileirao_match("Palmeiras-SP", "Santos-SP", 3, 0, 2023)
    soccer_system.add_brasileirao_match("Santos-SP", "Palmeiras-SP", 1, 1, 2022)
    soccer_system.add_brasileirao_match("Palmeiras-SP", "Santos-SP", 0, 2, 2021)
    # An unrelated match must not affect the head-to-head.
    soccer_system.add_brasileirao_match("Palmeiras-SP", "Flamengo-RJ", 4, 0, 2023)

    async with soccer_system.running() as client:
        h2h = await client.call("head_to_head", team_a="Palmeiras", team_b="Santos")

    assert h2h["total_matches"] == 3
    assert h2h["team_a_wins"] == 1  # Palmeiras
    assert h2h["team_b_wins"] == 1  # Santos
    assert h2h["draws"] == 1
    assert h2h["team_a_goals"] == 4
    assert h2h["team_b_goals"] == 3


async def test_team_record_goals_conceded_tracked(soccer_system):
    soccer_system.add_brasileirao_match("Fluminense-RJ", "Vasco-RJ", 1, 3, 2023)

    async with soccer_system.running() as client:
        record = await client.call("team_record", team="Fluminense")

    assert record["goals_for"] == 1
    assert record["goals_against"] == 3
    assert record["losses"] == 1
    assert record["goal_difference"] == -2
