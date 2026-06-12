"""Acceptance: Match Queries (TASK.md section 1).

Find matches by team, opponent, competition, season, date range and venue.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_find_all_matches_between_two_teams(soccer_system):
    # "Show me all Flamengo vs Fluminense matches"
    soccer_system.add_brasileirao_match("Flamengo-RJ", "Fluminense-RJ", 2, 1, 2023)
    soccer_system.add_brasileirao_match("Fluminense-RJ", "Flamengo-RJ", 1, 0, 2023)
    soccer_system.add_brasileirao_match("Palmeiras-SP", "Santos-SP", 3, 0, 2023)

    async with soccer_system.running() as client:
        result = await client.call(
            "find_matches", team="Flamengo", opponent="Fluminense"
        )

    assert result["count"] == 2
    teams_in_each = [
        {m["home_team"], m["away_team"]} for m in result["matches"]
    ]
    assert all({"Flamengo", "Fluminense"} == pair for pair in teams_in_each)


async def test_find_matches_a_team_played_in_a_season(soccer_system):
    # "What matches did Palmeiras play in 2023?"
    soccer_system.add_brasileirao_match("Palmeiras-SP", "Santos-SP", 2, 0, 2023)
    soccer_system.add_brasileirao_match("Corinthians-SP", "Palmeiras-SP", 1, 1, 2023)
    soccer_system.add_brasileirao_match("Palmeiras-SP", "Santos-SP", 0, 0, 2022)

    async with soccer_system.running() as client:
        result = await client.call("find_matches", team="Palmeiras", season=2023)

    assert result["count"] == 2
    for m in result["matches"]:
        assert m["season"] == 2023
        assert "Palmeiras" in (m["home_team"], m["away_team"])


async def test_find_matches_filtered_by_competition(soccer_system):
    soccer_system.add_brasileirao_match("Flamengo-RJ", "Santos-SP", 1, 0, 2022)
    soccer_system.add_cup_match("Flamengo", "Corinthians", 2, 0, 2022, round="Final")

    async with soccer_system.running() as client:
        result = await client.call(
            "find_matches", team="Flamengo", competition="Copa do Brasil"
        )

    assert result["count"] == 1
    assert result["matches"][0]["competition"] == "Copa do Brasil"


async def test_find_matches_by_venue_home_only(soccer_system):
    soccer_system.add_brasileirao_match("Corinthians-SP", "Santos-SP", 2, 0, 2022)
    soccer_system.add_brasileirao_match("Santos-SP", "Corinthians-SP", 1, 1, 2022)

    async with soccer_system.running() as client:
        result = await client.call(
            "find_matches", team="Corinthians", venue="home"
        )

    assert result["count"] == 1
    assert result["matches"][0]["home_team"] == "Corinthians"


async def test_find_matches_by_date_range(soccer_system):
    soccer_system.add_brasileirao_match(
        "Gremio-RS", "Internacional-RS", 1, 0, 2021, date="2021-03-10 16:00:00"
    )
    soccer_system.add_brasileirao_match(
        "Gremio-RS", "Bahia-BA", 2, 2, 2021, date="2021-09-20 16:00:00"
    )

    async with soccer_system.running() as client:
        result = await client.call(
            "find_matches",
            team="Gremio",
            date_from="2021-06-01",
            date_to="2021-12-31",
        )

    assert result["count"] == 1
    assert result["matches"][0]["date"] == "2021-09-20"


async def test_matches_are_returned_in_chronological_order(soccer_system):
    soccer_system.add_brasileirao_match(
        "Bahia-BA", "Vitoria-BA", 1, 0, 2020, date="2020-08-15 16:00:00"
    )
    soccer_system.add_brasileirao_match(
        "Vitoria-BA", "Bahia-BA", 0, 0, 2020, date="2020-02-10 16:00:00"
    )

    async with soccer_system.running() as client:
        result = await client.call("find_matches", team="Bahia")

    dates = [m["date"] for m in result["matches"]]
    assert dates == sorted(dates)
