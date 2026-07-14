"""
==============================================================================
File: tests/test_player_queries.py
==============================================================================
CONTEXT
-------
BDD tests for the PLAYER query category (spec section 3): search by name,
nationality and club, top-rated Brazilians, and the cross-file aggregate of
Brazilian players grouped by club.
==============================================================================
"""

from brazilian_soccer import queries as q


class TestPlayerSearch:
    def test_search_by_name(self, graph):
        # Given player data / When I search the name "Neymar"
        r = q.search_players(graph, name="Neymar")
        # Then at least one Neymar is returned
        assert r["count"] >= 1
        assert any("Neymar" in p["name"] for p in r["players"])

    def test_find_all_brazilian_players(self, graph):
        # Given the data / When I filter by nationality Brazil
        r = q.search_players(graph, nationality="Brazil", limit=None)
        # Then many Brazilian players are returned, all Brazilian
        assert r["count"] > 500
        assert all(p["nationality"] == "Brazil" for p in r["players"])

    def test_top_brazilian_players_sorted_descending(self, graph):
        # Given the data / When I ask for the top Brazilians
        r = q.top_players(graph, nationality="Brazil", limit=5)
        overalls = [p["overall"] for p in r["players"]]
        # Then they are sorted by overall rating descending
        assert overalls == sorted(overalls, reverse=True)
        # And the very top player is a 90+ rated Brazilian (Neymar in this data)
        assert r["players"][0]["overall"] >= 88

    def test_search_by_position(self, graph):
        # Given the data / When I search Brazilian goalkeepers
        r = q.search_players(graph, nationality="Brazil", position="GK", limit=None)
        # Then every returned player is a GK
        assert r["count"] > 0
        assert all(p["position"] == "GK" for p in r["players"])

    def test_min_overall_filter(self, graph):
        # Given the data / When I require overall >= 85
        r = q.search_players(graph, nationality="Brazil", min_overall=85, limit=None)
        # Then all returned players meet the threshold
        assert all(p["overall"] >= 85 for p in r["players"])


class TestBrazilianPlayersByClub:
    def test_grouped_by_club_with_averages(self, graph):
        # Given the data / When grouping Brazilians by club
        r = q.brazilian_players_by_club(graph, limit=10)
        # Then I get clubs with counts and average ratings
        assert r["total_brazilian_players"] > 500
        assert len(r["clubs"]) > 0
        for c in r["clubs"]:
            assert c["players"] >= 1
            assert 0 <= c["avg_rating"] <= 99
        # And clubs are ordered by player count (descending)
        counts = [c["players"] for c in r["clubs"]]
        assert counts == sorted(counts, reverse=True)
