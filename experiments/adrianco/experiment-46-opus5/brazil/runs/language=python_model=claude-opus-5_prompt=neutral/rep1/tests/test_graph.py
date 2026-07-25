"""Feature: The knowledge graph itself.

Nodes and edges are what make cross-file questions ("which club does this
player play for, and how did that club do?") answerable.
"""

from __future__ import annotations

from brazilian_soccer.graph import (
    AWAY_TEAM,
    FROM_COUNTRY,
    HOME_TEAM,
    IN_COMPETITION,
    KnowledgeGraph,
    PLAYS_FOR,
    load_graph,
)


class TestGraphStructure:

    def test_matches_are_connected_to_both_teams(self, synthetic_graph: KnowledgeGraph):
        """
        Given a match in the graph
        When its edges are followed
        Then it points at its home team and its away team
        """
        match = next(m for m in synthetic_graph.matches if m.home_team == "flamengo"
                     and m.away_team == "sao-paulo")
        node_id = f"match:{match.match_id}"

        home = synthetic_graph.neighbors(node_id, HOME_TEAM)
        away = synthetic_graph.neighbors(node_id, AWAY_TEAM)

        assert [node.label for node in home] == ["Flamengo"]
        assert [node.label for node in away] == ["São Paulo"]

    def test_teams_can_be_walked_back_to_their_matches(self, synthetic_graph):
        """
        Given a team node
        When incoming HOME_TEAM edges are followed
        Then the club's home matches come back
        """
        incoming = synthetic_graph.neighbors("team:flamengo", HOME_TEAM, incoming=True)

        assert incoming
        assert all(node.node_type == "match" for node in incoming)

    def test_players_link_to_clubs_and_countries(self, synthetic_graph):
        """
        Given a player from the FIFA file whose club plays in the match data
        When the PLAYS_FOR edge is followed
        Then it lands on the same team node the matches use
        """
        player = next(p for p in synthetic_graph.players if p.name == "Ronaldinho")
        node_id = f"player:{player.player_id}"

        clubs = synthetic_graph.neighbors(node_id, PLAYS_FOR)
        countries = synthetic_graph.neighbors(node_id, FROM_COUNTRY)

        assert [node.node_id for node in clubs] == ["team:flamengo"]
        assert [node.label for node in countries] == ["Brazil"]

    def test_matches_link_to_competitions(self, synthetic_graph):
        match = synthetic_graph.matches[0]
        competitions = synthetic_graph.neighbors(
            f"match:{match.match_id}", IN_COMPETITION)

        assert [node.label for node in competitions] == [match.competition]

    def test_summary_counts_nodes_and_edges(self, graph):
        summary = graph.summary()

        assert summary["teams"] > 900
        assert summary["matches"] > 16_000
        assert summary["players"] == 18_207
        assert summary["nodes"] > summary["matches"] + summary["players"]
        assert summary["edges"] > 2 * summary["matches"]
        assert len(summary["competitions"]) == 5


class TestIndexes:

    def test_team_matches_index_agrees_with_the_match_list(self, synthetic_graph):
        """
        Given the per-team index used to keep lookups fast
        When it is compared with a full scan
        Then the two agree
        """
        scanned = [m for m in synthetic_graph.matches if m.involves("flamengo")]

        assert len(synthetic_graph.team_matches("flamengo")) == len(scanned)

    def test_competition_season_index(self, graph):
        matches = graph.matches_by_competition_season[("Brasileirão Série A", 2019)]

        assert len(matches) == 380

    def test_unknown_team_id_is_empty_not_an_error(self, graph):
        assert graph.team_matches("no-such-club") == []


class TestGraphCaching:

    def test_graph_is_cached_between_calls(self):
        """
        Given loading the CSVs takes about half a second
        When the graph is requested twice with default settings
        Then the same object is returned
        """
        assert load_graph() is load_graph()

    def test_each_data_directory_is_cached_separately(self, synthetic_data_dir):
        """
        Given a server pointed at a custom data directory
        When the graph is requested repeatedly
        Then the cached graph for that directory is reused, not rebuilt
        And it stays distinct from the default one
        """
        one = load_graph(synthetic_data_dir)
        two = load_graph(synthetic_data_dir)

        assert one is two
        assert one is not load_graph()

    def test_refresh_rebuilds(self, synthetic_data_dir):
        first = load_graph(synthetic_data_dir)
        rebuilt = load_graph(synthetic_data_dir, refresh=True)

        assert rebuilt is not first
        assert rebuilt.summary()["matches"] == first.summary()["matches"]


class TestPlayerLookup:

    def test_exact_name_beats_partial(self, graph):
        players = graph.find_players("Neymar Jr")

        assert players[0].name == "Neymar Jr"

    def test_token_search_finds_multi_word_names(self, graph):
        players = graph.find_players("Roberto Firmino")

        assert players and players[0].name == "Roberto Firmino"

    def test_fuzzy_matching_is_opt_out(self, graph):
        assert graph.find_players("Gabriel Barbosa", allow_fuzzy=False) == []
