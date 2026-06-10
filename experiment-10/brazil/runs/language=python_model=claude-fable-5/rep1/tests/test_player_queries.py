"""Feature: Player queries

Scenario: Search players by name, nationality, club, and position
  Given the FIFA player data is loaded
  When I search with various filters
  Then I should receive matching players sorted by rating
"""

import queries


class TestPlayerSearch:
    def test_find_all_brazilian_players(self, db):
        # "Find all Brazilian players in the dataset"
        result = queries.search_players(nationality="Brazil", limit=5)
        assert result["total_players"] > 500
        for p in result["players"]:
            assert p["nationality"] == "Brazil"

    def test_search_by_partial_name(self, db):
        result = queries.search_players(name="Neymar")
        assert result["total_players"] >= 1
        assert result["players"][0]["name"] == "Neymar Jr"

    def test_abbreviated_fifa_names_match_full_names(self, db):
        # FIFA stores "G. Jesus"; the query "Gabriel Jesus" must find him
        player = queries.get_player("Gabriel Jesus")
        assert "error" not in player
        assert player["nationality"] == "Brazil"

    def test_accent_insensitive_search(self, db):
        a = queries.search_players(name="Vinicius Junior")
        b = queries.search_players(name="Vinícius Júnior")
        assert a["total_players"] == b["total_players"]

    def test_search_by_club(self, db):
        # "Which players play for Real Madrid?"
        result = queries.search_players(club="Real Madrid", limit=30)
        assert result["total_players"] > 10
        for p in result["players"]:
            assert "Real Madrid" in p["club"]

    def test_search_by_position_group(self, db):
        result = queries.search_players(nationality="Brazil", position="forward",
                                        limit=10)
        assert result["total_players"] > 0
        forwards = {"LS", "ST", "RS", "LW", "RW", "LF", "CF", "RF"}
        for p in result["players"]:
            assert p["position"] in forwards

    def test_min_overall_filter(self, db):
        result = queries.search_players(min_overall=90)
        for p in result["players"]:
            assert p["overall"] >= 90


class TestTopPlayers:
    def test_top_brazilian_players_sorted_by_rating(self, db):
        # "Who are the top Brazilian players?"
        result = queries.top_players(nationality="Brazil", limit=10)
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)
        assert result["players"][0]["name"] == "Neymar Jr"

    def test_missing_player_returns_helpful_error(self, db):
        result = queries.get_player("Zé Inexistente da Silva")
        assert "error" in result

    def test_player_profile_includes_skills(self, db):
        player = queries.get_player("Casemiro")
        assert "error" not in player
        assert player["skills"]
        assert "Finishing" in player["skills"]
