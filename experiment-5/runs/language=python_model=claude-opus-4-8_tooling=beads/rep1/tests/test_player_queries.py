"""
================================================================================
Feature: Player Queries
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Gherkin scenarios: search players by name, nationality (esp. Brazilian), club,
and position; sort by rating.
================================================================================
"""


class TestSearchByName:
    """Scenario: Who is Gabriel Barbosa / Neymar?"""

    def test_find_by_partial_name(self, graph):
        # Given the FIFA player data is loaded
        # When I search for "Neymar"
        players = graph.find_players(name="Neymar")
        # Then at least one player matches and the name contains the query
        assert players
        assert any("neymar" in p.name.lower() for p in players)


class TestBrazilianPlayers:
    """Scenario: Find all Brazilian players / top Brazilian players."""

    def test_brazilian_filter(self, graph):
        # When I filter by nationality Brazil
        players = graph.find_players(nationality="Brazil", limit=None)
        # Then every result is Brazilian and there are hundreds of them
        assert len(players) > 500
        assert all(p.nationality == "Brazil" for p in players)

    def test_top_brazilians_sorted_descending(self, graph):
        # When I ask for the top Brazilian players
        top = graph.top_brazilian_players(10)
        # Then they are sorted by overall rating, highest first
        overalls = [p.overall for p in top]
        assert overalls == sorted(overalls, reverse=True)
        # And the highest-rated Brazilian is Neymar (Overall 92 in this data)
        assert "neymar" in top[0].name.lower()


class TestSearchByClub:
    """Scenario: Which players play for a club?"""

    def test_club_filter_returns_only_that_club(self, graph):
        # When I list players for Grêmio (a licensed club in this FIFA data)
        players = graph.players_by_club("Grêmio")
        # Then every player's club normalizes to gremio
        assert players
        assert all(p.club_key == "gremio" for p in players)


class TestFiltersAndSorting:
    def test_position_filter(self, graph):
        # When I filter Brazilian goalkeepers
        gks = graph.find_players(nationality="Brazil", position="GK", limit=None)
        assert gks
        assert all(p.position == "GK" for p in gks)

    def test_min_overall(self, graph):
        # When I require a minimum overall rating
        elite = graph.find_players(min_overall=88, limit=None)
        assert elite
        assert all(p.overall >= 88 for p in elite)

    def test_sort_by_potential(self, graph):
        players = graph.find_players(nationality="Brazil", sort_by="potential", limit=10)
        pots = [p.potential for p in players]
        assert pots == sorted(pots, reverse=True)
