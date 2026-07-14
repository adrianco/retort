"""BDD-style tests for player queries.

Feature: Player Queries
  Scenario: Search the FIFA player database
    Given the player data is loaded
    When I search by name / nationality / club
    Then I receive structured player records with rating attributes.
"""

from __future__ import annotations

from brazilian_soccer_mcp import queries as Q


class TestPlayerLookup:
    def test_search_by_name_returns_neymar(self, store):
        # Given a search by name fragment
        results = Q.find_players(store, name="Neymar", limit=5)
        # Then Neymar Jr is present with sensible attributes
        assert any("Neymar" in p["name"] for p in results)
        neymar = next(p for p in results if "Neymar" in p["name"])
        assert neymar["nationality"] == "Brazil"
        assert neymar["overall"] >= 85

    def test_top_brazilian_players_returns_brazilians(self, store):
        results = Q.top_brazilian_players(store, limit=10)
        assert len(results) == 10
        assert all(p["nationality"] == "Brazil" for p in results)
        # Sorted by overall descending
        overalls = [p["overall"] for p in results]
        assert overalls == sorted(overalls, reverse=True)

    def test_filter_by_min_overall(self, store):
        results = Q.find_players(store, nationality="Brazil", min_overall=85, limit=50)
        assert results, "expected some elite Brazilian players"
        assert all(p["overall"] >= 85 for p in results)

    def test_players_at_brazilian_clubs_returns_grouped_summary(self, store):
        groups = Q.players_at_brazilian_clubs(store)
        assert groups, "expected at least one matched Brazilian club"
        # The FIFA 19 dataset omits some unlicensed clubs (Flamengo, Palmeiras)
        # but reliably includes Santos, Grêmio, and Atlético Mineiro.
        club_names = {g["club"] for g in groups}
        assert any(
            expected in club_names
            for expected in ("Santos", "Grêmio", "Atlético Mineiro", "Botafogo")
        )
        for g in groups:
            assert g["players"] > 0
            assert 0 <= g["avg_overall"] <= 100
