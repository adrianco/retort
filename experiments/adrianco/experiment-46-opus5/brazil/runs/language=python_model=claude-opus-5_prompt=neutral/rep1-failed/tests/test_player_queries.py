"""Feature: Player queries.

  Scenario: Find players by nationality, club or position
    Given the FIFA player data is loaded
    When I search for Brazilian players
    Then I should receive players sorted by rating with club and position
"""

from __future__ import annotations

from brazilian_soccer import queries as q
from brazilian_soccer.formatting import (
    format_club_squad,
    format_player_profile,
    format_players,
    format_players_by_club,
)


class TestPlayerSearch:

    def test_all_brazilian_players(self, graph):
        """
        Given the FIFA player data is loaded
        When I ask for Brazilian players
        Then hundreds are returned, sorted by overall rating
        """
        result = q.search_players(graph, nationality="Brazil", limit=25)

        assert result["total"] > 500
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)
        assert all(p["nationality"] == "Brazil" for p in result["players"])
        assert result["players"][0]["name"].startswith("Neymar")

    def test_players_at_a_brazilian_club(self, graph):
        """
        Given clubs are spelled differently in the FIFA and match files
        When I ask for players at Grêmio
        Then the squad is found through the shared team registry
        """
        result = q.search_players(graph, club="Grêmio", limit=30)

        assert result["total"] >= 15
        assert all(p["club_team_id"] == "gremio" for p in result["players"])

    def test_filtering_by_position_group(self, graph):
        """
        Given FIFA position codes such as ST, LW and CAM
        When I ask for forwards at a club
        Then only attacking positions come back
        """
        result = q.search_players(graph, club="Santos", position="forward")

        assert result["total"] > 0
        assert all(p["position"] in {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"}
                   for p in result["players"])

    def test_filtering_by_rating_and_age(self, graph):
        result = q.search_players(graph, nationality="Brazil", min_overall=85,
                                  max_age=30, limit=50)

        assert result["total"] > 0
        assert all(p["overall"] >= 85 and p["age"] <= 30
                   for p in result["players"])

    def test_sorting_by_potential(self, graph):
        result = q.search_players(graph, nationality="Brazil", max_age=21,
                                  sort_by="potential", limit=10)
        potentials = [p["potential"] for p in result["players"]]

        assert potentials == sorted(potentials, reverse=True)

    def test_search_by_name(self, graph):
        result = q.search_players(graph, name="Neymar")

        assert result["total"] >= 1
        assert "Neymar" in result["players"][0]["name"]

    def test_a_player_is_never_listed_twice(self, graph):
        """
        Given players indexed both by full name and by name token
        When a one-word name is searched
        Then the player appears once, not once per index entry
        """
        result = q.search_players(graph, name="Casemiro")
        names = [player["name"] for player in result["players"]]

        assert names.count("Casemiro") == 1
        assert result["total"] == len(set(p["player_id"] for p in result["players"]))

    def test_formatted_player_list(self, graph):
        text = format_players(q.search_players(graph, nationality="Brazil",
                                               limit=3))

        assert "Overall:" in text and "Position:" in text and "Club:" in text
        assert text.count("\n") >= 4


class TestPlayerProfile:

    def test_profile_includes_attributes_and_club_context(self, graph):
        """
        Given a player who plays for a club that appears in the match data
        When I ask who they are
        Then their attributes and their club's match record are returned
        """
        result = q.player_profile(graph, "Neymar")

        assert result["found"] is True
        assert result["player"]["nationality"] == "Brazil"
        assert result["player"]["overall"] >= 90
        assert result["player"]["skills"]

    def test_profile_of_a_player_at_a_brazilian_club_links_to_matches(self, graph):
        """
        Given the FIFA data and the match data share club identities
        When I profile a player at a Brazilian club
        Then the club's match record is attached (a cross-file query)
        """
        squad = q.club_squad(graph, "Internacional", limit=1)
        name = squad["players"][0]["name"]

        result = q.player_profile(graph, name)

        assert result["club_context"]["team"] == "Internacional"
        assert result["club_context"]["matches"] > 100
        assert result["club_context"]["last_match"]["score"]

    def test_missing_player_is_reported_honestly(self, graph):
        """
        Given the FIFA file is a single-season snapshot
        When I ask about a player who is not in it
        Then the answer says so and offers similar names instead of guessing
        """
        result = q.player_profile(graph, "Gabriel Barbosa")

        assert result["found"] is False
        assert result["alternatives"]
        text = format_player_profile(result)
        assert "No player named 'Gabriel Barbosa'" in text
        assert "Similar names:" in text


class TestSquads:

    def test_club_squad_is_sorted_by_rating(self, graph):
        """
        Given a club in the FIFA data
        When I ask for its highest-rated players
        Then they are returned best-first with a squad average
        """
        result = q.club_squad(graph, "Internacional", limit=10)

        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)
        assert result["average_overall"] > 50
        assert result["squad_size"] >= 10

    def test_club_without_fifa_players_is_reported_clearly(self, graph):
        """
        Given the FIFA snapshot does not license every Brazilian club
        When I ask for the Flamengo squad
        Then the answer explains that there are no player records
        """
        result = q.club_squad(graph, "Flamengo")
        text = format_club_squad(result)

        if result["squad_size"] == 0:
            assert "does not license every Brazilian club" in text
        else:
            assert result["players"]

    def test_players_grouped_by_brazilian_club(self, graph):
        """
        Given Brazilian players spread across clubs
        When I aggregate them by club, keeping clubs that have match data
        Then each row reports the squad size and average rating
        """
        result = q.players_by_club_summary(graph, nationality="Brazil", limit=10)

        assert result["clubs"] >= 10
        assert result["total_players"] > 100
        for row in result["rows"]:
            assert row["players"] > 0
            assert row["average_overall"] > 40
            assert row["best_player"]
        text = format_players_by_club(result)
        assert "avg rating" in text
