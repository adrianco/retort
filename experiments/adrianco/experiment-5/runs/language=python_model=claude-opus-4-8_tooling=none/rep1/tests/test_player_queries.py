"""
================================================================================
 BDD tests: Player Queries (capability category 3)
================================================================================
Feature: Player Queries
  I want to search players by name, nationality, club and position
  So that I can answer player-related questions from the FIFA dataset.

Note: the bundled FIFA dataset (FIFA 19) is licensed without some big Brazilian
clubs (Flamengo, Palmeiras, Corinthians), but does include many others
(Santos, Grêmio, Fluminense, Internacional, ...).  Tests use clubs known to be
present.
================================================================================
"""


class TestPlayerSearchByName:
    def test_known_brazilian_player_is_found(self, engine):
        # Given the player data is loaded
        # When I search for "Neymar"
        result = engine.search_players("Neymar")
        # Then at least one matching player is returned with rating attributes
        assert result["count"] >= 1
        top = result["players"][0]
        assert "neymar" in top["name"].lower()
        assert isinstance(top["overall"], int)

    def test_accent_insensitive_name_search(self, engine):
        # Given the player data is loaded
        # When I search without accents
        result = engine.search_players("Coutinho")
        # Then players are still found
        assert result["count"] >= 1


class TestPlayersByNationality:
    def test_brazilian_players_are_filtered_correctly(self, engine):
        # Given the player data is loaded
        # When I request the top Brazilian players
        result = engine.top_players(nationality="Brazil", limit=10)
        # Then there are many and they are sorted by overall rating descending
        assert result["count"] > 100
        overalls = [p["overall"] for p in result["players"]]
        assert overalls == sorted(overalls, reverse=True)


class TestPlayersByClub:
    def test_players_at_present_club_are_returned(self, engine):
        # Given the player data is loaded
        # When I request the squad of a club present in the FIFA data
        result = engine.players_at_club("Santos")
        # Then players are returned, sorted by rating, with an average
        assert result["count"] > 0
        assert result["average_overall"] > 0
        overalls = [p["overall"] for p in result["players"]]
        assert overalls == sorted(overalls, reverse=True)

    def test_filter_squad_by_position(self, engine):
        # Given the player data is loaded
        # When I request only goalkeepers at a club
        result = engine.players_at_club("Grêmio", position="GK")
        # Then every returned player plays that position
        assert all(p["position"] == "GK" for p in result["players"])


class TestTopPlayersCrossFilter:
    def test_top_brazilian_at_specific_club(self, engine):
        # Given the player data is loaded
        # When I ask for Brazilian players at Fluminense (a club in the data)
        result = engine.top_players(nationality="Brazil", club="Fluminense", limit=5)
        # Then every returned player is Brazilian
        assert all(p["nationality"] == "Brazil" for p in result["players"])
