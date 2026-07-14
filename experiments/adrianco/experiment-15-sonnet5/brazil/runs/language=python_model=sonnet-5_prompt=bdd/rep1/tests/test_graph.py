"""BDD specs for brazilian_soccer_mcp.graph: the in-memory knowledge graph
of teams, matches and player rosters.
"""

import pytest

from brazilian_soccer_mcp.graph import TeamNotFoundError


class TestResolveTeam:
    def test_given_a_well_known_team_when_resolved_by_its_common_name_then_the_team_node_is_found(self, graph):
        # Given the graph built from all match data
        # When resolving "Flamengo" by its common name
        node = graph.resolve_team("Flamengo")
        # Then a team node with the expected display name is returned
        assert node.display == "Flamengo"

    def test_given_a_team_with_a_state_suffix_spelling_when_resolved_then_the_same_node_is_found(self, graph):
        # Given the same club can appear as "Flamengo-RJ" or "Flamengo"
        # When resolving both spellings
        by_suffix = graph.resolve_team("Flamengo-RJ")
        by_bare = graph.resolve_team("Flamengo")
        # Then they resolve to the identical team node
        assert by_suffix.key == by_bare.key

    def test_given_an_unknown_team_name_when_resolved_then_team_not_found_error_is_raised(self, graph):
        # Given a team name that doesn't appear anywhere in the match data
        # When attempting to resolve it
        # Then a TeamNotFoundError is raised rather than returning None or crashing
        with pytest.raises(TeamNotFoundError):
            graph.resolve_team("Definitely Not A Real Football Club")


class TestTeamMatchesAndCompetitions:
    def test_given_a_team_that_has_played_multiple_competitions_when_queried_then_all_are_listed(self, graph):
        # Given Palmeiras has played in the Brasileirao, Copa do Brasil and
        # Copa Libertadores across the provided datasets
        # When its competitions are queried
        competitions = graph.team_competitions("Palmeiras")
        # Then all of them are present
        assert {"Brasileirao Serie A", "Copa do Brasil", "Copa Libertadores"}.issubset(competitions)

    def test_given_a_team_when_its_matches_are_queried_then_every_row_has_that_team_as_home_or_away(self, graph):
        # Given the matches played by Corinthians
        matches = graph.team_matches("Corinthians")
        # When each row is inspected
        node = graph.resolve_team("Corinthians")
        # Then Corinthians appears on the home or away side of every one
        assert ((matches["home_team_key"] == node.key) | (matches["away_team_key"] == node.key)).all()


class TestClubPlayers:
    def test_given_a_club_with_a_fifa_roster_when_queried_then_its_players_are_returned(self, graph):
        # Given Santos has a full FIFA roster in the player dataset
        # When its players are queried through the graph
        players = graph.club_players("Santos")
        # Then a non-empty roster is returned
        assert len(players) > 0

    def test_given_a_club_with_no_fifa_roster_when_queried_then_an_empty_result_is_returned(self, graph):
        # Given Flamengo was not licensed in this edition of FIFA, so it has
        # no players in fifa_data.csv (a genuine data-source limitation)
        # When its players are queried through the graph
        players = graph.club_players("Flamengo")
        # Then an empty result is returned rather than raising
        assert len(players) == 0
