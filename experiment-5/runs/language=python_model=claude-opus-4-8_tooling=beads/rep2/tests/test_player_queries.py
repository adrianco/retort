"""
================================================================================
test_player_queries.py - BDD scenarios for FIFA player search
================================================================================

Feature: Player Queries
  Scenario: Find players by criteria
    Given the player data is loaded
    When I filter players by nationality / club / position / rating
    Then I should receive matching, correctly-sorted players.
================================================================================
"""


class TestPlayerSearch:
    def test_find_brazilian_players(self, engine):
        # When I search for Brazilian players
        res = engine.search_players(nationality="Brazil", limit=10)
        # Then many are found and all are Brazilian, sorted by overall desc
        assert res["total"] > 100
        assert all(p["nationality"] == "Brazil" for p in res["players"])
        overalls = [p["overall"] for p in res["players"]]
        assert overalls == sorted(overalls, reverse=True)

    def test_top_brazilian_includes_neymar(self, engine):
        # When I list the highest-rated Brazilians
        res = engine.search_players(nationality="Brazil", limit=5)
        names = [p["name"] for p in res["players"]]
        # Then Neymar is among the very top
        assert any("Neymar" in n for n in names)

    def test_search_by_name(self, engine):
        # When I look up a player by (partial) name
        res = engine.search_players(name="Casemiro")
        assert res["total"] >= 1
        assert any("Casemiro" in p["name"] for p in res["players"])

    def test_filter_by_position(self, engine):
        # When I filter Brazilian goalkeepers
        res = engine.search_players(nationality="Brazil", position="GK", limit=20)
        assert res["total"] >= 1
        assert all(p["position"] == "GK" for p in res["players"])

    def test_filter_by_min_overall(self, engine):
        res = engine.search_players(min_overall=85, limit=50)
        assert all(p["overall"] >= 85 for p in res["players"])


class TestGetPlayer:
    def test_lookup_single_player(self, engine):
        # When I ask "Who is Gabriel Barbosa?"
        res = engine.get_player("Gabriel Barbosa")
        # Then a profile is returned (or a sensible not-found)
        assert "found" in res
        if res["found"]:
            assert res["player"]["name"]
            assert res["player"]["overall"] is not None


class TestClubSummary:
    def test_brazilian_clubs_summary(self, engine):
        # When I summarise Brazilian players by club
        data = engine.club_player_summary("Brazil", top=10)
        # Then each row has a club, a player count and an average rating
        assert len(data["clubs"]) > 0
        for row in data["clubs"]:
            assert row["players"] > 0
            assert row["avg_overall"] is None or row["avg_overall"] > 0
