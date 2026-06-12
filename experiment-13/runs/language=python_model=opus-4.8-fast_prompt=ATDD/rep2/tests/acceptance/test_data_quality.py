"""Acceptance: Data Quality requirements (TASK.md "Data Quality Notes").

Team-name normalization, multiple date formats, UTF-8 accents, and cross-file
queries that combine data from several CSV sources.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_team_name_with_and_without_state_suffix_match(soccer_system):
    # Same team appears as "Palmeiras-SP" and "Palmeiras" across files.
    soccer_system.add_brasileirao_match("Palmeiras-SP", "Santos-SP", 2, 0, 2022)
    soccer_system.add_cup_match("Palmeiras", "Flamengo", 1, 0, 2022)

    async with soccer_system.running() as client:
        result = await client.call("find_matches", team="Palmeiras")

    assert result["count"] == 2


async def test_accented_and_unaccented_names_match(soccer_system):
    # "Sao Paulo" should match "São Paulo" and "Gremio" should match "Grêmio".
    soccer_system.add_brasileirao_match("São Paulo-SP", "Grêmio-RS", 1, 1, 2022)

    async with soccer_system.running() as client:
        by_plain = await client.call("find_matches", team="Sao Paulo")
        by_accent = await client.call("find_matches", team="São Paulo")

    assert by_plain["count"] == 1
    assert by_accent["count"] == 1


async def test_brazilian_date_format_is_parsed(soccer_system):
    # The historical file uses DD/MM/YYYY dates.
    soccer_system.add_historical_match(
        "Guarani", "Vasco", 4, 2, 2003, date="29/03/2003"
    )

    async with soccer_system.running() as client:
        result = await client.call("find_matches", team="Guarani")

    assert result["count"] == 1
    assert result["matches"][0]["date"] == "2003-03-29"


async def test_country_suffix_in_parentheses_is_normalized(soccer_system):
    # Libertadores names like "Nacional (URU)" carry a country qualifier.
    soccer_system.add_libertadores_match("Nacional (URU)", "Flamengo", 2, 2, 2013)

    async with soccer_system.running() as client:
        result = await client.call("find_matches", team="Nacional")

    assert result["count"] == 1
    assert result["matches"][0]["home_team"] == "Nacional"


async def test_overlapping_seasons_across_files_are_deduplicated(soccer_system):
    # The same league fixture exists in two source files; it must count once.
    soccer_system.add_brasileirao_match(
        "Flamengo-RJ", "Santos-SP", 2, 1, 2015, date="2015-08-15 16:00:00"
    )
    soccer_system.add_historical_match(
        "Flamengo", "Santos", 2, 1, 2015, date="15/08/2015"
    )

    async with soccer_system.running() as client:
        result = await client.call(
            "find_matches", team="Flamengo", opponent="Santos", season=2015
        )

    assert result["count"] == 1


async def test_cross_file_query_combines_match_and_player_data(soccer_system):
    # A single running system answers both "who plays for Flamengo" and
    # "what matches did Flamengo play" — data drawn from different CSV files.
    soccer_system.add_player("Gabriel Barbosa", "Brazil", 83, "Flamengo", "ST")
    soccer_system.add_brasileirao_match("Flamengo-RJ", "Fluminense-RJ", 2, 1, 2023)

    async with soccer_system.running() as client:
        players = await client.call("search_players", club="Flamengo")
        matches = await client.call("find_matches", team="Flamengo")

    assert players["count"] == 1
    assert matches["count"] == 1
