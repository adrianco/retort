"""
================================================================================
Context
================================================================================
Test module: test_player_queries.py
Project:     Brazilian Soccer MCP Server
Feature:     Player Queries (capability category 3).
Style:       BDD Given-When-Then.
================================================================================
"""


class TestPlayerSearch:
    def test_search_by_name(self, kg):
        # Given the player data is loaded
        # When I search for "Neymar"
        results = kg.search_players(name="Neymar")
        # Then Neymar Jr is returned with his attributes
        assert results
        neymar = results[0]
        assert "Neymar" in neymar.name
        assert neymar.nationality == "Brazil"
        assert neymar.overall and neymar.overall > 85

    def test_search_is_case_insensitive_substring(self, kg):
        # When I search with a lowercase partial name
        results = kg.search_players(name="messi")
        assert any("Messi" in p.name for p in results)

    def test_filter_by_nationality(self, kg):
        # When I ask for all Brazilian players
        brazilians = kg.search_players(nationality="Brazil", limit=None)
        # Then a large set is returned, all Brazilian
        assert len(brazilians) > 500
        assert all(p.nationality == "Brazil" for p in brazilians)

    def test_results_sorted_by_overall_descending(self, kg):
        # When I list top Brazilian players
        top = kg.top_players(nationality="Brazil", limit=10)
        ratings = [p.overall for p in top]
        assert ratings == sorted(ratings, reverse=True)
        assert top[0].overall >= 88

    def test_filter_by_position(self, kg):
        # When I filter Brazilian goalkeepers
        gks = kg.search_players(nationality="Brazil", position="GK", limit=None)
        assert gks
        assert all(p.position == "GK" for p in gks)

    def test_min_overall_threshold(self, kg):
        # When I require a minimum overall rating
        elite = kg.search_players(min_overall=90, limit=None)
        assert elite
        assert all(p.overall >= 90 for p in elite)

    def test_brazilian_players_grouped_by_club(self, kg):
        # When I group Brazilian players by club
        groups = kg.brazilian_players_by_club()
        # Then each group reports a count and an average rating
        assert groups
        assert all("club" in g and "count" in g and "avg_overall" in g for g in groups)
        # And the list is ordered by squad size
        counts = [g["count"] for g in groups]
        assert counts == sorted(counts, reverse=True)
