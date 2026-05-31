"""
Context
=======
Feature: Player Queries  (TASK.md section 3)

Scenario: Find all Brazilian players
Scenario: Find players by club
Scenario: Search a player by name
Scenario: Highest-rated players sorted by overall
"""

from __future__ import annotations


class TestPlayerSearch:
    def test_find_brazilian_players(self, graph):
        # WHEN I filter by nationality Brazil
        players = graph.search_players(nationality="Brazil", limit=50)
        # THEN every result is Brazilian and sorted by overall descending
        assert players
        assert all(p.nationality.lower() == "brazil" for p in players)
        overalls = [p.overall or 0 for p in players]
        assert overalls == sorted(overalls, reverse=True)

    def test_top_brazilian_is_well_known(self, graph):
        # The single highest-rated Brazilian in this FIFA snapshot is Neymar.
        top = graph.search_players(nationality="Brazil", limit=1)[0]
        assert "Neymar" in top.name

    def test_find_players_by_club(self, graph):
        # WHEN I filter by a club
        players = graph.search_players(club="Real Madrid", limit=40)
        assert players
        assert all("real madrid" in p.club.lower() for p in players)

    def test_filter_by_position(self, graph):
        players = graph.search_players(nationality="Brazil", position="GK", limit=20)
        assert players
        assert all("GK" in p.position for p in players)

    def test_min_overall_filter(self, graph):
        players = graph.search_players(min_overall=88, limit=50)
        assert players
        assert all(p.overall >= 88 for p in players)


class TestPlayerLookup:
    def test_find_player_by_name(self, graph):
        # WHEN I look up "Neymar"
        player = graph.find_player("Neymar")
        # THEN I get the player profile
        assert player is not None
        assert "Neymar" in player.name
        assert player.nationality.lower() == "brazil"

    def test_accent_insensitive_name_search(self, graph):
        # Searching without accents still finds accented names.
        players = graph.search_players(name="Coutinho", limit=5)
        assert any("Coutinho" in p.name for p in players)

    def test_unknown_player_returns_none(self, graph):
        assert graph.find_player("Nonexistent Playerxyz") is None


class TestBrazilianClubs:
    def test_group_brazilians_by_brazilian_clubs(self, graph):
        grouped = graph.players_by_brazilian_clubs(min_overall=70)
        assert grouped
        # Each entry is a club -> list of Brazilian players.
        for club, players in grouped.items():
            assert players
            assert all(p.nationality.lower() == "brazil" for p in players)
