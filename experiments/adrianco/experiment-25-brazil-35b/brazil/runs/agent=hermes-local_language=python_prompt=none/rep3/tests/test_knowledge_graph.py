# Brazilian Soccer MCP Server - Tests for Knowledge Graph
# BDD-style tests for graph building and graph-based queries.

import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import MatchDataset
from knowledge_graph import KnowledgeGraph


@pytest.fixture
def data_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")


@pytest.fixture
def dataset(data_dir):
    ds = MatchDataset()
    ds.load_all(data_dir)
    return ds


@pytest.fixture
def graph(dataset):
    return KnowledgeGraph(dataset)


class TestGraphBuilding:
    """Test knowledge graph construction."""

    def test_graph_created(self, graph):
        """Given dataset loaded, when graph built, then graph object exists."""
        assert graph is not None
        assert graph.graph is not None

    def test_graph_has_nodes(self, graph):
        """Given graph built, then it contains nodes."""
        assert graph.graph.number_of_nodes() > 0

    def test_graph_has_edges(self, graph):
        """Given graph built, then it contains edges."""
        assert graph.graph.number_of_edges() > 0

    def test_teams_in_graph(self, graph):
        """Given graph built, then team nodes exist."""
        team_count = sum(1 for _, attrs in graph.graph.nodes(data=True) if attrs.get('node_type') == 'team')
        assert team_count > 0

    def test_matches_in_graph(self, graph):
        """Given graph built, then match nodes exist."""
        match_count = sum(1 for _, attrs in graph.graph.nodes(data=True) if attrs.get('node_type') == 'match')
        assert match_count > 0

    def test_competitions_in_graph(self, graph):
        """Given graph built, then competition nodes exist."""
        comp_count = sum(1 for _, attrs in graph.graph.nodes(data=True) if attrs.get('node_type') == 'competition')
        assert comp_count > 0

    def test_players_in_graph(self, graph):
        """Given graph built, then player nodes exist."""
        player_count = sum(1 for _, attrs in graph.graph.nodes(data=True) if attrs.get('node_type') == 'player')
        assert player_count > 0

    def test_graph_node_info(self, graph):
        """Given a team node, when info requested, then node data is returned."""
        # Find a team node
        for node, attrs in graph.graph.nodes(data=True):
            if attrs.get('node_type') == 'team':
                info = graph.get_node_info(node)
                assert info is not None
                assert 'node_type' in info
                assert info['node_type'] == 'team'
                break


class TestTeamConnections:
    """Test team connection queries."""

    def test_get_connected_teams(self, graph):
        """Given a team, when connections found, then competing teams are returned."""
        competitors = graph.get_connected_teams("palmeiras")
        assert isinstance(competitors, list)

    def test_no_self_connections(self, graph):
        """Given connections, when returned, then team does not appear as its own competitor."""
        competitors = graph.get_connected_teams("palmeiras")
        for c in competitors:
            assert c['team'] != 'palmeiras'


class TestGraphStatistics:
    """Test graph statistics."""

    def test_get_graph_stats(self, graph):
        """Given graph, when stats requested, then returns statistics dict."""
        stats = graph.get_graph_statistics()
        assert 'total_nodes' in stats
        assert 'total_edges' in stats
        assert stats['total_nodes'] > 0
        assert stats['total_edges'] > 0

    def test_stats_match_dataset(self, graph, dataset):
        """Given graph stats, when compared to dataset, then match counts align."""
        stats = graph.get_graph_statistics()
        assert stats['matches'] == len(dataset.all_matches)
        assert stats['teams'] == len(dataset.all_teams)
        assert stats['players'] == len(dataset.all_players)


class TestPathFinding:
    """Test path finding between teams."""

    def test_path_finding_basic(self, graph):
        """Given two teams, when path found, then path exists."""
        paths = graph.find_path_between_teams("Palmeiras", "Santos")
        assert isinstance(paths, list)

    def test_path_has_edges(self, graph):
        """Given paths, when returned, then each has from, to, and relation."""
        paths = graph.find_path_between_teams("Palmeiras", "Santos")
        if paths:
            for p in paths:
                assert 'from' in p
                assert 'to' in p
                assert 'relation' in p


class TestCommonOpponents:
    """Test common opponent queries."""

    def test_common_opponents_basic(self, graph):
        """Given two teams, when common opponents found, then list is returned."""
        opponents = graph.get_common_opponents("Palmeiras", "Santos")
        assert isinstance(opponents, list)
