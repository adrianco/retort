"""Acceptance: Statistical Analysis (TASK.md section 5).

Goals-per-match averages, home/away win rates, biggest victories.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_average_goals_per_match(soccer_system):
    # "What's the average goals per match in the Brasileirao?"
    soccer_system.add_brasileirao_match("Flamengo-RJ", "Santos-SP", 2, 1, 2022)  # 3
    soccer_system.add_brasileirao_match("Palmeiras-SP", "Corinthians-SP", 0, 0, 2022)  # 0
    soccer_system.add_brasileirao_match("Gremio-RS", "Internacional-RS", 3, 0, 2022)  # 3

    async with soccer_system.running() as client:
        stats = await client.call(
            "competition_statistics", competition="Brasileirão", season=2022
        )

    assert stats["total_matches"] == 3
    assert stats["total_goals"] == 6
    assert stats["average_goals_per_match"] == pytest.approx(2.0)


async def test_home_win_rate(soccer_system):
    soccer_system.add_brasileirao_match("A", "B", 2, 0, 2022)  # home win
    soccer_system.add_brasileirao_match("C", "D", 0, 1, 2022)  # away win
    soccer_system.add_brasileirao_match("E", "F", 1, 1, 2022)  # draw
    soccer_system.add_brasileirao_match("G", "H", 3, 1, 2022)  # home win

    async with soccer_system.running() as client:
        stats = await client.call("competition_statistics", season=2022)

    assert stats["home_wins"] == 2
    assert stats["away_wins"] == 1
    assert stats["draws"] == 1
    assert stats["home_win_rate"] == pytest.approx(50.0)


async def test_biggest_wins_are_ranked_by_margin(soccer_system):
    # "Show me the biggest wins in the dataset"
    soccer_system.add_brasileirao_match("Palmeiras-SP", "Sao Paulo-SP", 6, 0, 2015)
    soccer_system.add_brasileirao_match("Flamengo-RJ", "Gremio-RS", 5, 0, 2019)
    soccer_system.add_brasileirao_match("Santos-SP", "Bahia-BA", 1, 0, 2019)

    async with soccer_system.running() as client:
        result = await client.call("biggest_wins", limit=2)

    margins = [m["margin"] for m in result["matches"]]
    assert margins == [6, 5]
    assert result["matches"][0]["home_team"] == "Palmeiras"


async def test_statistics_across_all_competitions_when_unfiltered(soccer_system):
    soccer_system.add_brasileirao_match("A", "B", 1, 0, 2022)
    soccer_system.add_cup_match("C", "D", 2, 2, 2022)
    soccer_system.add_libertadores_match("E", "F", 0, 3, 2022)

    async with soccer_system.running() as client:
        stats = await client.call("competition_statistics")

    assert stats["total_matches"] == 3
    assert stats["total_goals"] == 8
