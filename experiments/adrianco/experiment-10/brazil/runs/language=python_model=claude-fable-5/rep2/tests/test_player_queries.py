"""BDD scenarios: player queries (TASK.md capability 3).

Feature: Player Queries
  Search FIFA player data by name, nationality, club, position and rating.
"""


class TestSearchByName:
    """Scenario: Who is Neymar?"""

    def test_find_player_by_name(self, kb):
        # Given the player data is loaded
        # When I search for "Neymar"
        players = kb.search_players(name="Neymar")
        # Then his record is returned with rating, position and club
        assert players
        top = players[0]
        assert top.name == "Neymar Jr"
        assert top.overall == 92
        assert top.nationality == "Brazil"
        assert top.club == "Paris Saint-Germain"

    def test_partial_name_search(self, kb):
        # When I search a partial surname
        players = kb.search_players(name="Barbosa", limit=0)
        # Then all players whose name contains it are returned
        assert {"M. Barbosa", "Hélder Barbosa"} <= {p.name for p in players}

    def test_accent_insensitive_name_search(self, kb):
        with_accent = kb.search_players(name="Hélder Barbosa")
        without = kb.search_players(name="Helder Barbosa")
        assert [p.name for p in with_accent] == [p.name for p in without] != []

    def test_unknown_player_returns_empty(self, kb):
        # When I search for a player who is not in the dataset
        players = kb.search_players(name="Gabriel Barbosa")
        # Then an empty list is returned (not an error)
        assert players == []


class TestFilterByNationality:
    """Scenario: Find all Brazilian players in the dataset."""

    def test_brazilian_players(self, kb):
        players = kb.search_players(nationality="Brazil", limit=0)
        assert len(players) == 827
        assert all(p.nationality == "Brazil" for p in players)

    def test_top_brazilians_sorted_by_rating(self, kb):
        # When I ask for the top Brazilian players
        players = kb.search_players(nationality="Brazil", limit=10)
        ratings = [p.overall for p in players]
        # Then they are sorted highest-rated first, led by Neymar Jr
        assert ratings == sorted(ratings, reverse=True)
        assert players[0].name == "Neymar Jr"


class TestFilterByClub:
    """Scenario: Which players play for a Brazilian club?"""

    def test_gremio_squad(self, kb):
        players = kb.search_players(club="Grêmio", limit=0)
        assert len(players) == 20
        assert all(p.club == "Grêmio" for p in players)

    def test_club_accent_variants(self, kb):
        a = kb.search_players(club="Gremio", limit=0)
        b = kb.search_players(club="Grêmio", limit=0)
        assert len(a) == len(b) == 20

    def test_full_club_name_variant(self, kb):
        # Given the FIFA dataset says "Sport Club do Recife"
        players = kb.search_players(club="Sport Recife", limit=0)
        assert players
        assert all(p.club == "Sport Club do Recife" for p in players)


class TestFilterByPositionAndRating:
    def test_goalkeepers_only(self, kb):
        players = kb.search_players(nationality="Brazil", position="GK", limit=0)
        assert players
        assert all(p.position == "GK" for p in players)

    def test_minimum_rating(self, kb):
        players = kb.search_players(min_overall=90, limit=0)
        assert players
        assert all(p.overall >= 90 for p in players)


class TestClubSummaries:
    """Scenario: Brazilian players at Brazilian clubs, by club."""

    def test_brazilians_by_club(self, kb):
        summary = kb.players_by_club_summary(
            nationality="Brazil",
            clubs=["Grêmio", "Santos", "Cruzeiro", "Fluminense", "Internacional"],
        )
        clubs = {row["club"]: row for row in summary["clubs"]}
        assert clubs
        for row in clubs.values():
            assert row["players"] > 0
            assert 0 < row["avg_rating"] <= 99
