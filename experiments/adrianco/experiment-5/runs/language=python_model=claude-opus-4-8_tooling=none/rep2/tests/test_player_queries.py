"""
BDD scenarios -- Player Queries (Given / When / Then).

Feature: Player Queries
    As an analyst
    I want to search the FIFA player database
    So that I can find players by name, nationality, club and rating.
"""


class TestSearchByName:
    """Scenario: Look up a player by name."""

    def test_find_neymar(self, kg):
        # Given the player data is loaded
        # When I search for "Neymar"
        players = kg.find_players(name="Neymar")
        # Then at least one matching Brazilian player is returned
        assert len(players) > 0
        assert any("neymar" in p.name.lower() for p in players)


class TestFilterByNationality:
    """Scenario: Find all Brazilian players."""

    def test_only_brazilians_returned(self, kg):
        players = kg.find_players(nationality="Brazil", limit=None)
        assert len(players) > 0
        assert all(p.nationality == "Brazil" for p in players)


class TestTopBrazilians:
    """Scenario: Highest-rated Brazilian players, sorted descending."""

    def test_sorted_by_overall_desc(self, kg):
        players = kg.top_brazilian_players(limit=5)
        assert len(players) == 5
        ratings = [p.overall for p in players]
        assert ratings == sorted(ratings, reverse=True)
        assert all(p.nationality == "Brazil" for p in players)


class TestFilterByClub:
    """Scenario: Find players at a specific club."""

    def test_club_filter(self, kg):
        # When I search players whose club is FC Barcelona
        players = kg.find_players(club="Barcelona", limit=None)
        # Then every returned player is at a Barcelona club
        assert len(players) > 0
        assert all("barcelona" in p.club.lower() for p in players)


class TestFilterByPositionAndRating:
    """Scenario: Filter Brazilian forwards above a rating threshold."""

    def test_position_and_min_overall(self, kg):
        players = kg.find_players(
            nationality="Brazil", position="ST", min_overall=80, limit=None
        )
        for p in players:
            assert p.position == "ST"
            assert p.overall >= 80
            assert p.nationality == "Brazil"


class TestBrazilianPlayersByClub:
    """Scenario: Group Brazilian players by club."""

    def test_grouping_has_counts_and_avg(self, kg):
        rows = kg.brazilian_players_by_club(limit_clubs=5)
        assert len(rows) == 5
        for r in rows:
            assert r["count"] >= 1
            assert "avg_overall" in r
        # And clubs are ordered by descending player count
        counts = [r["count"] for r in rows]
        assert counts == sorted(counts, reverse=True)


class TestExactPlayerCountsOnMiniData:
    """Scenario: Deterministic player filtering."""

    def test_two_brazilians_one_at_team_a(self, mini_kg):
        assert len(mini_kg.find_players(nationality="Brazil", limit=None)) == 2
        top = mini_kg.top_brazilian_players(limit=1)
        assert top[0].name == "Star Brazilian"
