"""Player queries and player/match cross-file joins (specification section 3).

Context
-------
Feature: Player Queries

  Scenario: Find players by nationality
    Given the FIFA player data is loaded
    When I search for players from Brazil
    Then I should receive players sorted by rating
    And each player should have a club, position and overall rating

  Scenario: Cross-file query
    Given both player and match data are loaded
    When I ask for a club's squad
    Then FIFA players and that club's match record come back together
"""

from __future__ import annotations

import pytest

from brazilian_soccer import queries


class TestPlayerSearch:
    """Scenario: Search the FIFA database."""

    def test_given_a_nationality_when_searched_then_players_are_rated_and_sorted(self, graph):
        """
        Given the FIFA player data is loaded
        When I search for all Brazilian players
        Then every one is Brazilian and they are sorted by rating
        """
        result = queries.search_players(graph, nationality="Brazil", limit=10)
        ratings = [player["overall"] for player in result["players"]]

        assert result["total"] == 827
        assert ratings == sorted(ratings, reverse=True)
        assert all(player["nationality"] == "Brazil" for player in result["players"])
        assert result["players"][0]["name"] == "Neymar Jr"

    def test_given_a_club_when_searched_then_only_its_players_return(self, graph):
        """
        Given the question "who are the highest-rated players at Grêmio?"
        When players are filtered by club
        Then only that club's players are returned, best first
        """
        result = queries.search_players(graph, club="Grêmio", limit=5)

        assert result["total"] >= 15
        assert all(player["club"] == "Grêmio" for player in result["players"])
        assert result["notes"]

    def test_given_positions_when_filtered_then_only_those_positions_return(self, graph):
        """
        Given the question "show me all forwards from Cruzeiro"
        When players are filtered by club and positions
        Then only forwards of that club come back
        """
        result = queries.search_players(
            graph, club="Cruzeiro", position="ST,CF,LW,RW", limit=20
        )

        assert result["players"]
        assert all(player["position"] in {"ST", "CF", "LW", "RW"} for player in result["players"])

    def test_given_a_rating_floor_when_filtered_then_weaker_players_are_excluded(self, graph):
        """
        Given a minimum overall rating
        When Brazilian players are searched
        Then nobody below the floor is returned
        """
        result = queries.search_players(
            graph, nationality="Brazil", min_overall=85, limit=50
        )

        assert result["total"] >= 5
        assert all(player["overall"] >= 85 for player in result["players"])

    def test_given_a_name_when_searched_then_accents_do_not_matter(self, graph):
        """
        Given a player whose name contains accents
        When it is searched without them
        Then the player is still found
        """
        result = queries.search_players(graph, name="Ederson", limit=5)

        assert result["total"] >= 1
        assert any(player["name"].startswith("Ederson") for player in result["players"])

    def test_given_an_unknown_club_when_searched_then_available_clubs_are_listed(self, graph):
        """
        Given a club with no FIFA entry
        When its players are searched
        Then the error explains the file's coverage and lists the clubs it has
        """
        result = queries.search_players(graph, club="Flamengo")

        assert "error" in result
        assert "Grêmio" in result["suggestions"]

    def test_given_an_unknown_nationality_when_searched_then_it_is_reported(self, graph):
        """
        Given a nationality that does not exist in the file
        When players are searched
        Then an error with alternatives is returned
        """
        result = queries.search_players(graph, nationality="Atlantis")

        assert "error" in result


class TestPlayerProfile:
    """Scenario: Look up one player."""

    def test_given_a_player_name_when_profiled_then_attributes_are_returned(self, graph):
        """
        Given the question "who is Neymar?"
        When the player is profiled
        Then rating, club, value and best attributes are returned
        """
        result = queries.player_profile(graph, "Neymar")
        player = result["player"]

        assert player["name"] == "Neymar Jr"
        assert player["overall"] == 92
        assert player["nationality"] == "Brazil"
        assert player["value"].startswith("€")
        assert player["top_skills"][0]["rating"] >= player["top_skills"][-1]["rating"]

    def test_given_a_player_at_a_linked_club_when_profiled_then_the_match_team_is_shown(
        self, graph
    ):
        """
        Given a player at a Brazilian club that also appears in match results
        When the player is profiled
        Then the profile points at the club node used by the match data
        """
        squad = graph.team_players("gremio")
        result = queries.player_profile(graph, squad[0].name)

        assert result["player"]["club_in_match_data"].startswith("Grêmio")

    def test_given_a_missing_player_when_profiled_then_close_names_are_offered(self, graph):
        """
        Given "Gabriel Barbosa", who is absent from this FIFA 19 snapshot
        When the player is profiled
        Then the answer says so and offers the closest names in the file
        """
        result = queries.player_profile(graph, "Gabriel Barbosa")

        assert "error" in result
        assert any("Gabriel" in suggestion for suggestion in result["suggestions"])

    def test_given_a_partial_name_when_profiled_then_the_best_match_wins(self, graph):
        """
        Given several players share part of a name
        When one is profiled
        Then the highest rated match is chosen and the others are listed
        """
        result = queries.player_profile(graph, "Silva")

        assert result["total_name_matches"] > 1
        assert result["other_matches"]


class TestSquadCrossFile:
    """Scenario: Join the player file to the match files."""

    def test_given_a_linked_club_when_asked_for_its_squad_then_both_datasets_appear(
        self, graph
    ):
        """
        Given both player and match data are loaded
        When I ask for the Santos squad
        Then FIFA players and the club's match record come back together
        """
        result = queries.team_squad(graph, "Santos")

        assert result["squad_size"] >= 15
        assert result["average_overall"] > 50
        assert result["match_record"]["played"] > 500
        assert result["seasons"]

    def test_given_an_unlicensed_club_when_asked_for_its_squad_then_it_says_so(self, graph):
        """
        Given Flamengo has no FIFA entry in this snapshot
        When its squad is requested
        Then the answer explains the gap and lists the clubs that do have one
        """
        result = queries.team_squad(graph, "Flamengo")

        assert result["squad_size"] == 0
        assert "fifa_data.csv" in result["note"]
        assert result["clubs_with_players"]

    def test_given_a_squad_when_listed_then_it_is_sorted_by_rating(self, graph):
        """
        Given a club with a FIFA squad
        When the squad is listed
        Then players are ordered by overall rating
        """
        result = queries.team_squad(graph, "Cruzeiro", limit=10)
        ratings = [player["overall"] for player in result["players"]]

        assert ratings == sorted(ratings, reverse=True)
