"""The knowledge graph: nodes, relations and cross-file links.

Context
-------
Feature: A traversable knowledge graph

  Teams, matches, players, competitions, seasons, venues and states are nodes;
  relations such as played_home, competed_in and plays_for connect them.  The
  interesting part is the join between the two halves of the data: FIFA clubs
  have to be linked to the clubs that appear in match results without wiring
  FIFA's "Inter" (Internazionale) to Internacional of Porto Alegre.
"""

from __future__ import annotations

import pytest


class TestNodes:
    """Scenario: The graph exposes every entity in the datasets."""

    def test_given_the_loaded_graph_when_summarised_then_it_covers_all_sources(self, graph):
        """
        Given the graph built from all six CSVs
        When its summary is requested
        Then matches, teams, players and competitions are all populated
        """
        stats = graph.stats()

        assert stats["matches"] > 16_000
        assert stats["teams"] > 300
        assert stats["players"] == 18_207
        assert stats["competitions"] == 5
        assert stats["venues"] > 50
        assert 2.0 < stats["goals_per_match"] < 3.0
        assert 40 < stats["home_win_rate"] < 60

    def test_given_a_team_node_when_inspected_then_it_records_its_spellings(self, graph):
        """
        Given a club that is spelled several ways across the files
        When its node is inspected
        Then the node knows its competitions, seasons and match count
        """
        flamengo = graph.team("flamengo")

        assert flamengo is not None
        assert flamengo.name == "Flamengo"
        assert flamengo.state == "RJ"
        assert flamengo.match_count > 800
        assert "Brasileirão Série A" in flamengo.competitions
        assert 2003 in flamengo.seasons

    @pytest.mark.parametrize(
        "query, team_id",
        [
            ("Flamengo", "flamengo"),
            ("flamengo-rj", "flamengo"),
            ("Timão", "corinthians"),
            ("são paulo", "sao-paulo"),
            ("Atletico Mineiro", "atletico-mg"),
            ("Sport", "sport-recife"),
            ("Gremio", "gremio"),
        ],
    )
    def test_given_free_text_when_looking_up_a_team_then_the_node_is_found(
        self, graph, query, team_id
    ):
        """
        Given a club name typed in any of its forms
        When the graph is searched
        Then the canonical node is returned
        """
        node = graph.find_team(query)

        assert node is not None and node.id == team_id

    def test_given_variant_spellings_when_indexed_then_the_node_records_them_all(self, graph):
        """
        Given a club written differently in each source file
        When its node is inspected
        Then every raw spelling that resolved to it is recorded
        And each of those spellings also resolves back to the node
        """
        node = graph.team("athletico-pr")
        spellings = set(node.spellings)

        assert {"Athletico-PR", "Atletico Paranaense", "Atlético - PR", "Athletico"} <= spellings
        for spelling in spellings:
            assert graph.find_team(spelling).id == "athletico-pr"

    def test_given_all_teams_when_counted_then_spellings_outnumber_nodes(self, graph):
        """
        Given the specification's requirement to handle name variations
        When spellings are counted across the graph
        Then many more raw spellings than club nodes were unified
        """
        spellings = sum(len(node.spellings) for node in graph.teams.values())

        assert spellings > len(graph.teams) * 1.5

    def test_given_an_unknown_name_when_looking_up_then_suggestions_are_offered(self, graph):
        """
        Given a name that matches no club exactly
        When suggestions are requested
        Then candidate clubs are proposed
        """
        suggestions = graph.suggest_teams("santa")

        assert suggestions
        assert any("Santa" in node.name for node in suggestions)


class TestRelations:
    """Scenario: Walk the graph from a node."""

    def test_given_a_team_node_when_traversed_then_matches_and_context_are_linked(self, graph):
        """
        Given the node for a club
        When its neighbours are listed
        Then home matches, away matches, competitions, seasons and state are linked
        """
        edges = graph.neighbours("team:palmeiras")

        assert len(edges["played_home"]) > 300
        assert len(edges["played_away"]) > 300
        assert "competition:serie-a" in edges["competed_in"]
        assert "season:2019" in edges["active_in"]
        assert edges["based_in"] == ["state:SP"]

    def test_given_a_match_node_when_traversed_then_both_teams_are_linked(self, graph):
        """
        Given any match node
        When its neighbours are listed
        Then it links to both teams, its competition and its winner
        """
        match = next(item for item in graph.matches if item.played and item.winner_id)
        edges = graph.neighbours(f"match:{match.match_id}")

        assert edges["home_team"] == [f"team:{match.home_team}"]
        assert edges["away_team"] == [f"team:{match.away_team}"]
        assert edges["part_of"] == [f"competition:{match.competition_id}"]
        assert edges["won_by"] == [f"team:{match.winner_id}"]

    def test_given_a_relation_filter_when_traversing_then_only_that_relation_returns(
        self, graph
    ):
        """
        Given a node with many relations
        When a specific relation is requested
        Then only that relation is returned
        """
        edges = graph.neighbours("team:santos", relation="squad")

        assert set(edges) == {"squad"}
        assert edges["squad"]

    def test_given_an_unknown_node_when_traversed_then_nothing_is_returned(self, graph):
        """
        Given a node id that does not exist
        When it is looked up
        Then no node and no edges come back
        """
        assert graph.node("team:does-not-exist") is None
        assert graph.neighbours("team:does-not-exist") == {}


class TestNodeKinds:
    """Scenario: Every namespaced node kind can be described and walked."""

    @pytest.mark.parametrize(
        "node_id, kind",
        [
            ("team:flamengo", "team"),
            ("competition:serie-a", "competition"),
            ("season:2019", "season"),
            ("state:RJ", "state"),
            ("country:Brazil", "country"),
        ],
    )
    def test_given_a_node_id_when_described_then_its_kind_is_reported(
        self, graph, node_id, kind
    ):
        """
        Given a namespaced node id
        When the node is described
        Then its kind and attributes are returned
        """
        node = graph.node(node_id)

        assert node is not None and node["kind"] == kind

    def test_given_a_season_node_when_traversed_then_its_competitions_are_linked(self, graph):
        """
        Given a season that several competitions ran in
        When the season node is traversed
        Then all of those competitions are linked
        """
        edges = graph.neighbours("season:2019")

        assert "competition:serie-a" in edges["competitions"]
        assert "competition:libertadores" in edges["competitions"]

    def test_given_a_venue_node_when_traversed_then_it_lists_its_matches(self, graph):
        """
        Given a stadium recorded in the historical file
        When the venue node is traversed
        Then the matches it hosted are linked
        """
        venue = max(graph.matches_by_venue, key=lambda name: len(graph.matches_by_venue[name]))
        node = graph.node(f"venue:{venue}")
        edges = graph.neighbours(f"venue:{venue}")

        assert node["matches"] > 100
        assert len(edges["hosted"]) == node["matches"]

    @pytest.mark.parametrize("node_id, expected", [("state:SP", "Palmeiras"), ("state:RS", "Grêmio")])
    def test_given_a_state_node_when_traversed_then_its_clubs_are_linked(
        self, graph, node_id, expected
    ):
        """
        Given a Brazilian state
        When the state node is traversed
        Then the clubs based there are linked
        """
        edges = graph.neighbours(node_id)
        names = {graph.teams[item.split(":", 1)[1]].name for item in edges["teams"]}

        assert expected in names

    def test_given_a_country_node_when_traversed_then_foreign_clubs_are_grouped(self, graph):
        """
        Given the Libertadores brings in clubs from other countries
        When the Argentina node is traversed
        Then Argentine clubs are linked and Brazilian ones are not
        """
        edges = graph.neighbours("country:Argentina")
        ids = {item.split(":", 1)[1] for item in edges["teams"]}

        assert "boca-juniors" in ids
        assert "flamengo" not in ids

    def test_given_a_competition_node_when_traversed_then_seasons_and_matches_link(self, graph):
        """
        Given a competition node
        When it is traversed
        Then every season and every match of that competition is linked
        """
        edges = graph.neighbours("competition:libertadores")

        assert "season:2018" in edges["seasons"]
        assert len(edges["matches"]) == len(graph.matches_by_competition["libertadores"])


class TestCrossFileLinks:
    """Scenario: Join FIFA players to the clubs in the match data."""

    def test_given_brazilian_fifa_clubs_when_linked_then_they_map_to_match_teams(self, graph):
        """
        Given FIFA clubs whose squads are mostly Brazilian
        When the graph links them to the match data
        Then well known clubs are connected in both directions
        """
        assert graph.club_links["Grêmio"] == "gremio"
        assert graph.club_links["Atlético Paranaense"] == "athletico-pr"
        assert graph.club_links["América FC (Minas Gerais)"] == "america-mg"

        squad = graph.team_players("gremio")
        assert len(squad) >= 15
        assert all(player.club_team_id == "gremio" for player in squad)

    def test_given_a_foreign_club_with_a_brazilian_sounding_name_when_linked_then_it_is_skipped(
        self, graph
    ):
        """
        Given FIFA's "Inter" (Internazionale) and "Boavista FC" (Portugal)
        When clubs are linked to the match data
        Then the majority-Brazilian rule keeps them unlinked
        """
        assert "Inter" not in graph.club_links
        assert "Boavista FC" not in graph.club_links

        internacional_squad = graph.team_players("internacional")
        assert internacional_squad
        assert all(player.club == "Internacional" for player in internacional_squad)

    def test_given_a_player_node_when_traversed_then_it_links_to_its_club(self, graph):
        """
        Given a player at a linked Brazilian club
        When the player node is traversed
        Then it points at the club node used by the match data
        """
        player = graph.team_players("santos")[0]
        edges = graph.neighbours(f"player:{player.player_id}")

        assert edges["plays_for"] == ["team:santos"]
        assert edges["nationality"] == [f"country:{player.nationality}"]

    def test_given_a_nationality_when_filtered_then_brazilian_players_are_indexed(self, graph):
        """
        Given the FIFA player file
        When Brazilian players are requested
        Then the nationality index returns them all
        """
        brazilians = graph.nationality_players("Brazil")

        assert len(brazilians) == 827
        assert all(player.nationality == "Brazil" for player in brazilians)
