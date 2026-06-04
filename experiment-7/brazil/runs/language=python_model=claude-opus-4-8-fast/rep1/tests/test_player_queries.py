"""
================================================================================
tests.test_player_queries
================================================================================

CONTEXT
-------
BDD scenarios for Required Capability #3 (Player Queries): search by name,
nationality, club and position, and the sample questions "Who is Gabriel
Barbosa?", "Find all Brazilian players", "Who are the highest-rated players?".
================================================================================
"""


class TestPlayerQueries:
    """Feature: Player Queries."""

    def test_search_player_by_name(self, kg):
        # Scenario: "Who is Gabriel Barbosa?"
        players = kg.search_players(name="Neymar")
        assert len(players) > 0
        assert any("Neymar" in p["name"] for p in players)

    def test_find_all_brazilian_players(self, kg):
        # Scenario: "Find all Brazilian players in the dataset"
        players = kg.search_players(nationality="Brazil", limit=10_000)
        # Then there are many, and all are Brazilian
        assert len(players) > 100
        assert all(p["nationality"] == "Brazil" for p in players)

    def test_top_brazilian_players_are_sorted_by_overall(self, kg):
        # Scenario: "Who are the top Brazilian players?"
        players = kg.search_players(nationality="Brazil", limit=10)
        overalls = [p["overall"] for p in players]
        # Then results are sorted descending by overall rating
        assert overalls == sorted(overalls, reverse=True)
        # And the very top Brazilian is a world-class rating
        assert overalls[0] >= 88

    def test_filter_players_by_club(self, kg):
        # Scenario: "Which players play for <Brazilian club>?"
        # (Note: FIFA-19 only licensed a subset of Brazilian clubs, so we use
        #  Internacional, which is present in the dataset.)
        players = kg.search_players(club="Internacional", limit=10_000)
        assert len(players) > 0
        assert all("Internacional" in (p["club"] or "") for p in players)

    def test_filter_players_by_position(self, kg):
        # Scenario: "Show me all goalkeepers"
        players = kg.search_players(position="GK", nationality="Brazil", limit=50)
        assert len(players) > 0
        assert all(p["position"] == "GK" for p in players)

    def test_min_overall_filter(self, kg):
        players = kg.search_players(nationality="Brazil", min_overall=85, limit=50)
        assert all(p["overall"] >= 85 for p in players)

    def test_players_by_club_summary(self, kg):
        # Scenario: "Brazilian players grouped by Brazilian club"
        summary = kg.players_by_club_summary(["Santos", "Internacional", "Grêmio"])
        assert len(summary) > 0
        for entry in summary:
            assert entry["count"] > 0
            assert entry["avg_overall"] is not None
