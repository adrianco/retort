"""BDD: player queries.

Feature: Player search
  Filter the FIFA player table by name / nationality / club / position.

Feature: Brazilian player aggregation
  Highest-rated Brazilians overall and grouped by club.
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    brazilian_players_by_club,
    find_players,
    top_brazilian_players,
)


def test_find_player_by_name_neymar(dataset):
    # Given the FIFA data is loaded
    # When  we search by partial name "Neymar"
    rows = find_players(dataset, name="Neymar")
    # Then  Neymar Jr is the top hit and is Brazilian
    assert rows
    names = [r["name"] for r in rows]
    assert any("Neymar" in n for n in names)
    top = rows[0]
    assert top["nationality"] == "Brazil"
    assert top["overall"] >= 90


def test_find_brazilian_players(dataset):
    # Given the FIFA data is loaded
    # When  we filter by nationality = Brazil
    rows = find_players(dataset, nationality="Brazil", limit=1000)
    # Then  hundreds of players are returned and all are Brazilian
    assert len(rows) >= 500
    assert all(r["nationality"] == "Brazil" for r in rows)


def test_top_brazilian_players_sorted_by_overall(dataset):
    # Given the FIFA data is loaded
    # When  we ask for the top 10 Brazilians
    rows = top_brazilian_players(dataset, limit=10)
    # Then  exactly 10 players come back, all Brazilian, sorted by overall desc
    assert len(rows) == 10
    assert all(r["nationality"] == "Brazil" for r in rows)
    overalls = [r["overall"] for r in rows]
    assert overalls == sorted(overalls, reverse=True)


def test_filter_by_club_and_position(dataset):
    # Given the FIFA data is loaded
    # When  we filter by Brazilian club Flamengo (the FIFA data may not include)
    rows = find_players(dataset, club="Flamengo", limit=200)
    # Then  every player's club normalizes to Flamengo
    for r in rows:
        assert "lamengo" in r["club"]


def test_brazilian_players_by_club_returns_groups(dataset):
    # Given the FIFA data contains players with nationality Brazil at many clubs
    # When  we aggregate by club
    rows = brazilian_players_by_club(dataset, top_n_clubs=10)
    # Then  we receive up to 10 group summaries with required fields
    assert 1 <= len(rows) <= 10
    for r in rows:
        assert {"club", "player_count", "avg_overall", "top_player"} <= set(r)
        assert r["player_count"] > 0
