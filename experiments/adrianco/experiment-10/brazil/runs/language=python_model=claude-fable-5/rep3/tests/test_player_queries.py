"""Feature: Player Queries.

Search the FIFA player data by name, nationality, club and position.
"""

import queries


class TestSearchPlayers:
    def test_find_all_brazilian_players(self, db):
        """Scenario: 'Find all Brazilian players in the dataset'."""
        result = queries.search_players(db, nationality="Brazil", limit=5)
        assert result["total_matches"] == 827
        assert all(p["nationality"] == "Brazil" for p in result["players"])

    def test_top_brazilian_is_neymar(self, db):
        result = queries.search_players(db, nationality="Brazil", limit=1)
        best = result["players"][0]
        assert best["name"] == "Neymar Jr"
        assert best["overall"] == 92

    def test_results_sorted_by_rating(self, db):
        players = queries.search_players(db, nationality="Brazil",
                                         limit=50)["players"]
        ratings = [p["overall"] for p in players]
        assert ratings == sorted(ratings, reverse=True)

    def test_filter_by_club(self, db):
        """Scenario: 'Who are the highest-rated players at Cruzeiro?'"""
        result = queries.search_players(db, club="Cruzeiro")
        assert result["total_matches"] > 10
        assert all("Cruzeiro" in p["club"] for p in result["players"])

    def test_position_group_forwards(self, db):
        result = queries.search_players(db, nationality="Brazil",
                                        position="forward", limit=200)
        assert result["total_matches"] > 0
        assert all(p["position"] in {"ST", "CF", "LW", "RW", "LF", "RF",
                                     "LS", "RS"}
                   for p in result["players"])

    def test_position_code_and_min_overall(self, db):
        result = queries.search_players(db, position="GK", min_overall=85)
        assert all(p["position"] == "GK" and p["overall"] >= 85
                   for p in result["players"])
        names = {p["name"] for p in result["players"]}
        assert "Alisson" in names

    def test_accent_insensitive_name_search(self, db):
        result = queries.search_players(db, name="vinicius")
        assert result["total_matches"] > 0

    def test_limit_respected(self, db):
        result = queries.search_players(db, nationality="Brazil", limit=7)
        assert len(result["players"]) == 7
        assert result["total_matches"] == 827


class TestGetPlayer:
    def test_player_profile_with_skills(self, db):
        profile = queries.get_player(db, "Neymar")
        assert profile["name"] == "Neymar Jr"
        assert profile["club"] == "Paris Saint-Germain"
        assert profile["nationality"] == "Brazil"
        assert profile["skills"]["Dribbling"] >= 90

    def test_missing_player_returns_none(self, db):
        """'Who is Gabriel Barbosa?' — not in this FIFA snapshot, so the
        server must say so rather than invent an answer."""
        assert queries.get_player(db, "Gabriel Barbosa") is None

    def test_partial_name_picks_best_match(self, db):
        profile = queries.get_player(db, "casemiro")
        assert profile["name"] == "Casemiro"
