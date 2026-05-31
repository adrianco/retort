"""
================================================================================
BDD Feature: Player Queries
================================================================================

CONTEXT
-------
Covers specification capability #3: searching the FIFA player database by name,
nationality, club, position and rating, plus single-player lookup and club
squad summaries. Exact assertions use ``synthetic_kg``; integration checks use
the real ``kg``.
================================================================================
"""


class TestSearchPlayers:
    """Feature: Find players by attribute."""

    def test_find_brazilian_players_sorted(self, synthetic_kg):
        # Given the player data is loaded
        # When I search for Brazilian players
        players = synthetic_kg.find_players(nationality="Brazil")
        # Then only Brazilians are returned, highest rated first
        assert players
        assert all(p.nationality == "Brazil" for p in players)
        assert players[0].name == "Neymar Jr"
        overalls = [p.overall for p in players]
        assert overalls == sorted(overalls, reverse=True)

    def test_find_players_by_club(self, synthetic_kg):
        # When I filter by club Flamengo
        players = synthetic_kg.find_players(club="Flamengo")
        # Then I get the Flamengo squad members
        names = {p.name for p in players}
        assert names == {"Gabriel Barbosa", "Pedro"}

    def test_find_players_by_position(self, synthetic_kg):
        # When I filter strikers
        players = synthetic_kg.find_players(position="ST")
        assert players
        assert all(p.position == "ST" for p in players)

    def test_find_players_min_overall(self, synthetic_kg):
        # When I require an overall of at least 90
        players = synthetic_kg.find_players(min_overall=90)
        # Then only elite players come back
        assert all(p.overall >= 90 for p in players)
        assert {p.name for p in players} == {"Neymar Jr", "Lionel Messi"}

    def test_name_search_is_accent_insensitive(self, synthetic_kg):
        # When I search by partial name
        players = synthetic_kg.find_players(name="barbosa")
        assert any(p.name == "Gabriel Barbosa" for p in players)


class TestGetPlayer:
    """Feature: Look up a single player."""

    def test_get_player_by_name(self, synthetic_kg):
        # When I ask who Gabriel Barbosa is
        p = synthetic_kg.get_player("Gabriel Barbosa")
        # Then I get the matching profile
        assert p is not None
        assert p.club == "Flamengo"
        assert p.position == "ST"

    def test_get_unknown_player_returns_none(self, synthetic_kg):
        assert synthetic_kg.get_player("Nonexistent Player") is None


class TestClubSummary:
    """Feature: Club squad summary."""

    def test_club_summary_counts_and_average(self, synthetic_kg):
        # When I summarise the Flamengo squad
        s = synthetic_kg.club_summary("Flamengo")
        # Then I get the player count and average rating
        assert s["player_count"] == 2
        assert s["average_overall"] == round((83 + 80) / 2, 1)


class TestRealPlayerQueries:
    """Feature: Player queries against the real dataset."""

    def test_real_brazilian_players_exist(self, kg):
        players = kg.find_players(nationality="Brazil", limit=10)
        assert players
        assert all(p.nationality == "Brazil" for p in players)
        # Sorted by overall descending
        overalls = [p.overall for p in players if p.overall is not None]
        assert overalls == sorted(overalls, reverse=True)

    def test_real_player_lookup_fast(self, kg):
        import time
        start = time.time()
        kg.find_players(name="Neymar")
        assert time.time() - start < 2.0
