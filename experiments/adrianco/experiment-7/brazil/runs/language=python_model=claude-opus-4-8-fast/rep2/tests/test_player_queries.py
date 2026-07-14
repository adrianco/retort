"""
================================================================================
Module: tests.test_player_queries
--------------------------------------------------------------------------------
Context:
    BDD scenarios for the "Player Queries" feature (TASK.md §3) — searching the
    FIFA player database by name, nationality, club and position, and grouping
    Brazilian players by club.

Responsibility:
    Validate KnowledgeGraph.search_players / get_player / players_by_club_summary
    filtering and sorting behaviour.
================================================================================
"""

from brazilian_soccer_mcp.normalize import names_match, strip_accents


class TestPlayerSearch:
    def test_find_brazilian_players_sorted_by_overall(self, graph):
        # WHEN I search nationality "Brazil"
        players = graph.search_players(nationality="Brazil", limit=10)
        # THEN all are Brazilian
        assert players
        assert all(strip_accents(p.nationality).lower() == "brazil" for p in players)
        # AND sorted by overall rating descending
        overalls = [p.overall for p in players]
        assert overalls == sorted(overalls, reverse=True)

    def test_search_by_name_substring(self, graph):
        players = graph.search_players(name="Neymar", limit=5)
        assert players
        assert any("neymar" in strip_accents(p.name).lower() for p in players)

    def test_search_by_club(self, graph):
        # NB: the FIFA dataset (FIFA-19 vintage) omits a handful of big Brazilian
        # clubs (Flamengo/Palmeiras/Corinthians/São Paulo) due to licensing, but
        # includes most others — Fluminense, Santos, Grêmio, Cruzeiro, etc.
        players = graph.search_players(club="Fluminense", limit=50)
        assert players
        assert all(names_match("Fluminense", p.club) for p in players)

    def test_search_by_position(self, graph):
        players = graph.search_players(position="GK", nationality="Brazil", limit=20)
        assert players
        assert all("gk" in p.position.lower() for p in players)

    def test_min_overall_filter(self, graph):
        players = graph.search_players(min_overall=85, limit=50)
        assert players
        assert all(p.overall >= 85 for p in players)

    def test_get_single_player(self, graph):
        p = graph.get_player("Neymar")
        assert p is not None
        assert "neymar" in strip_accents(p.name).lower()
        assert p.overall and p.overall > 80


class TestPlayersByClub:
    def test_brazilian_players_grouped_by_club(self, graph):
        rows = graph.players_by_club_summary("Brazil")
        assert rows
        # Counts positive and average rating within FIFA's 1-99 scale.
        for r in rows[:10]:
            assert r["count"] > 0
            assert 1 <= r["avg_overall"] <= 99
        # Sorted by player count descending.
        counts = [r["count"] for r in rows]
        assert counts == sorted(counts, reverse=True)
