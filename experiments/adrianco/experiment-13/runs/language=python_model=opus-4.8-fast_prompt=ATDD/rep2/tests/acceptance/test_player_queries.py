"""Acceptance: Player Queries (TASK.md section 3).

Search players by name, nationality, club, position and rating.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_find_player_by_name(soccer_system):
    # "Who is Gabriel Barbosa?"
    soccer_system.add_player("Gabriel Barbosa", "Brazil", 83, "Flamengo", "ST")
    soccer_system.add_player("L. Messi", "Argentina", 94, "FC Barcelona", "RF")

    async with soccer_system.running() as client:
        result = await client.call("search_players", name="Gabriel Barbosa")

    assert result["count"] == 1
    player = result["players"][0]
    assert player["name"] == "Gabriel Barbosa"
    assert player["nationality"] == "Brazil"
    assert player["club"] == "Flamengo"


async def test_find_all_brazilian_players(soccer_system):
    # "Find all Brazilian players in the dataset"
    soccer_system.add_player("Neymar Jr", "Brazil", 92, "Paris Saint-Germain", "LW")
    soccer_system.add_player("Casemiro", "Brazil", 89, "Real Madrid", "CDM")
    soccer_system.add_player("K. Mbappe", "France", 89, "Paris Saint-Germain", "ST")

    async with soccer_system.running() as client:
        result = await client.call("search_players", nationality="Brazil")

    assert result["count"] == 2
    assert {p["name"] for p in result["players"]} == {"Neymar Jr", "Casemiro"}


async def test_players_for_a_club(soccer_system):
    # "Which players play for Flamengo?"
    soccer_system.add_player("Gabriel Barbosa", "Brazil", 83, "Flamengo", "ST")
    soccer_system.add_player("Bruno Henrique", "Brazil", 80, "Flamengo", "LM")
    soccer_system.add_player("Hulk", "Brazil", 79, "Atletico Mineiro", "ST")

    async with soccer_system.running() as client:
        result = await client.call("search_players", club="Flamengo")

    assert result["count"] == 2
    assert all(p["club"] == "Flamengo" for p in result["players"])


async def test_highest_rated_players_at_a_club_are_sorted(soccer_system):
    # "Who are the highest-rated players at Flamengo?"
    soccer_system.add_player("Player B", "Brazil", 80, "Flamengo", "CM")
    soccer_system.add_player("Player A", "Brazil", 85, "Flamengo", "ST")
    soccer_system.add_player("Player C", "Brazil", 78, "Flamengo", "CB")

    async with soccer_system.running() as client:
        result = await client.call("top_players", club="Flamengo", limit=2)

    ratings = [p["overall"] for p in result["players"]]
    assert ratings == [85, 80]


async def test_filter_forwards_by_club(soccer_system):
    # "Show me all forwards from Sao Paulo FC"
    soccer_system.add_player("Forward One", "Brazil", 79, "Sao Paulo", "ST")
    soccer_system.add_player("Midfielder", "Brazil", 80, "Sao Paulo", "CM")

    async with soccer_system.running() as client:
        result = await client.call(
            "search_players", club="Sao Paulo", position="ST"
        )

    assert result["count"] == 1
    assert result["players"][0]["position"] == "ST"


async def test_top_brazilian_players_sorted_by_rating(soccer_system):
    # "Who are the top Brazilian players?"
    soccer_system.add_player("Neymar Jr", "Brazil", 92, "Paris Saint-Germain", "LW")
    soccer_system.add_player("Alisson", "Brazil", 89, "Liverpool", "GK")
    soccer_system.add_player("Casemiro", "Brazil", 89, "Real Madrid", "CDM")
    soccer_system.add_player("Low Rated", "Brazil", 65, "Some Club", "CB")

    async with soccer_system.running() as client:
        result = await client.call("top_players", nationality="Brazil", limit=3)

    names = [p["name"] for p in result["players"]]
    assert names[0] == "Neymar Jr"
    assert len(names) == 3
    assert "Low Rated" not in names


async def test_filter_players_by_minimum_rating(soccer_system):
    soccer_system.add_player("Star", "Brazil", 90, "Club", "ST")
    soccer_system.add_player("Average", "Brazil", 70, "Club", "ST")

    async with soccer_system.running() as client:
        result = await client.call("search_players", min_overall=85)

    assert result["count"] == 1
    assert result["players"][0]["name"] == "Star"
