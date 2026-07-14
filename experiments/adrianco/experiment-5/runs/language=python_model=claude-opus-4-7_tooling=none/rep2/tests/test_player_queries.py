"""BDD: player queries.

Feature: Player Queries
  As an LLM
  I want to search the FIFA player database
  So that I can answer "Who are the top Brazilian players?"
"""

from __future__ import annotations

from brazilian_soccer_mcp import queries as q
from brazilian_soccer_mcp.data_loader import DataStore


class TestSearchByName:
    """Scenario: substring search returns the player."""

    def test_neymar_search(self, store: DataStore) -> None:
        result = q.search_players(store, name="Neymar", limit=5)
        assert result["count"] >= 1
        assert any("neymar" in p["name"].lower() for p in result["players"])


class TestFilterByNationality:
    """Scenario: filter by nationality returns only that country."""

    def test_brazilian_players_only(self, store: DataStore) -> None:
        result = q.search_players(store, nationality="Brazil", limit=20)
        assert result["count"] > 500  # plenty of Brazilians in FIFA data
        for player in result["players"]:
            assert player["nationality"] == "Brazil"


class TestSortedByOverall:
    """Scenario: results come back sorted by overall rating."""

    def test_top_brazilians_descending(self, store: DataStore) -> None:
        result = q.top_players_by_nationality(store, "Brazil", limit=10)
        overalls = [p["overall"] for p in result["players"] if p["overall"] is not None]
        # When I read the overalls
        # Then they are sorted descending
        assert overalls == sorted(overalls, reverse=True)


class TestFilterByClub:
    """Scenario: club filter uses normalized team names."""

    def test_real_madrid_squad(self, store: DataStore) -> None:
        # Real Madrid is in the FIFA dataset and has a non-trivial roster.
        result = q.search_players(store, club="Real Madrid", limit=40)
        assert result["count"] > 10
        for player in result["players"]:
            assert "real madrid" in player["club"].lower()


class TestPositionFilter:
    """Scenario: position filter is case-insensitive."""

    def test_forwards(self, store: DataStore) -> None:
        result = q.search_players(store, position="st", limit=5)
        assert result["count"] > 0
        for player in result["players"]:
            assert player["position"].upper() == "ST"


class TestBrazilianPlayerSummary:
    """Scenario: per-club aggregation for Brazilian players at Brazilian clubs."""

    def test_summary_shape(self, store: DataStore) -> None:
        summary = q.brazilian_player_summary(store)
        assert summary["total_brazilian_players"] > 0
        assert isinstance(summary["brazilian_clubs"], list)
        # Every entry has the documented shape.
        for entry in summary["brazilian_clubs"]:
            assert {"club", "player_count", "avg_overall"} <= set(entry)
            assert entry["player_count"] >= 1
