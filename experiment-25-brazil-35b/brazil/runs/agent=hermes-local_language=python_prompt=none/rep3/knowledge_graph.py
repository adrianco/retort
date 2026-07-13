# Brazilian Soccer MCP Server - Knowledge Graph
# Builds a NetworkX knowledge graph from match and player data.
# Provides graph-based queries for relationships between teams, matches, and players.

import networkx as nx
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime

from data_loader import MatchDataset, normalize_team_name


class KnowledgeGraph:
    """Builds and queries a NetworkX knowledge graph from soccer data.
    
    Nodes:
        - Teams: labeled with 'team' node_type
        - Competitions: labeled with 'competition' node_type  
        - Seasons: labeled with 'season' node_type
        - Players: labeled with 'player' node_type
        - Matches: labeled with 'match' node_type
    
    Edges:
        - (team) --[PLAYED_IN]--> (match)
        - (match) --[HOME]--> (team)
        - (match) --[AWAY]--> (team)
        - (team) --[PLAYED_IN]--> (competition)
        - (competition) --[HAS_SEASON]--> (season)
        - (player) --[PLAYS_FOR]--> (team)
    """

    def __init__(self, dataset: MatchDataset):
        self.dataset = dataset
        self.graph = nx.MultiDiGraph()
        self._node_counter = 0
        self._build_graph()

    def _next_node_id(self) -> str:
        """Generate unique node ID with type prefix."""
        self._node_counter += 1
        return f"n{self._node_counter}"

    def _ensure_node(self, node_id: str, node_type: str, **attrs):
        """Add node if not exists, return its ID."""
        if not self.graph.has_node(node_id):
            self.graph.add_node(node_id, node_type=node_type, **attrs)
        return node_id

    def _build_graph(self):
        """Build the knowledge graph from the dataset."""
        # Add team nodes
        for team in self.dataset.all_teams:
            tid = self._ensure_node(team, 'team', name=team)

        # Add match nodes and edges
        for i, match in enumerate(self.dataset.all_matches):
            mid = f"match_{i}"
            self.graph.add_node(mid, node_type='match', **match)

            home = match['home_team']
            away = match['away_team']
            comp = match['competition']
            season = match['season']

            # Match connected to teams
            self.graph.add_edge(mid, home, relation='home', match_idx=i)
            self.graph.add_edge(mid, away, relation='away', match_idx=i)

            # Team connected to competition
            if comp:
                self._ensure_node(comp, 'competition', name=comp)
                self.graph.add_edge(home, comp, relation='played_in', source='match', match_idx=i)
                self.graph.add_edge(away, comp, relation='played_in', source='match', match_idx=i)

            # Competition connected to season
            if season:
                self._ensure_node(str(season), 'season', year=season)
                self.graph.add_edge(comp, str(season), relation='has_season', source='match', match_idx=i)

        # Add player nodes
        for player in self.dataset.all_players:
            pid = f"player_{player['id']}"
            self._ensure_node(pid, 'player', **player)

            # Player connected to club (team-like node)
            club = player['club']
            if club:
                self._ensure_node(club, 'player_club', name=club)
                self.graph.add_edge(pid, club, relation='plays_for', position=player['position'])

    def get_node_info(self, node_id: str) -> Optional[Dict]:
        """Get detailed information about a node."""
        if not self.graph.has_node(node_id):
            return None
        info = dict(self.graph.nodes[node_id])
        info['id'] = node_id
        return info

    def get_connected_teams(self, team_name: str, depth: int = 2) -> List[Dict]:
        """Find teams connected to the given team via shared matches or competitions."""
        target = normalize_team_name(team_name)
        # Find the normalized team node
        team_node = None
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get('node_type') == 'team' and attrs.get('name') == target:
                team_node = node
                break

        if not team_node:
            return []

        # Find teams at same competition level
        competitors = []
        seen = set()
        for neighbor, _, edge_data in self.graph.out_edges(team_node, data=True):
            relation = edge_data.get('relation', '')
            if relation in ('played_in',) and self.graph.nodes[neighbor].get('node_type') == 'competition':
                comp_name = self.graph.nodes[neighbor].get('name', '')
                for prev_node, _, prev_edge_data in self.graph.in_edges(neighbor, data=True):
                    if prev_edge_data.get('relation') == 'played_in' and self.graph.nodes[next_hop].get('node_type') == 'team':
                        other_name = self.graph.nodes[prev_node].get('name', '')
                        if other_name != target and other_name not in seen:
                            seen.add(other_name)
                            competitors.append({
                                'team': other_name,
                                'competition': comp_name,
                            })

        return competitors

    def find_path_between_teams(self, team1: str, team2: str, max_depth: int = 3) -> List[Dict]:
        """Find connection paths between two teams."""
        t1_norm = normalize_team_name(team1)
        t2_norm = normalize_team_name(team2)

        t1_node = t2_node = None
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get('node_type') == 'team':
                if attrs.get('name') == t1_norm and t1_node is None:
                    t1_node = node
                if attrs.get('name') == t2_norm and t2_node is None:
                    t2_node = node

        if not t1_node or not t2_node:
            return []

        paths = []
        try:
            path_list = nx.single_source_shortest_path(self.graph, t1_node, cutoff=max_depth)
            if t2_node in path_list:
                path = path_list[t2_node]
                for i in range(len(path) - 1):
                    edge_data = self.graph.edges[path[i], path[i + 1]]
                    paths.append({
                        'from': path[i],
                        'to': path[i + 1],
                        'relation': edge_data.get('relation', ''),
                        'from_type': self.graph.nodes[path[i]].get('node_type', ''),
                        'to_type': self.graph.nodes[path[i + 1]].get('node_type', ''),
                    })
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        return paths

    def get_common_opponents(self, team1: str, team2: str) -> List[str]:
        """Find teams that both team1 and team2 have played against."""
        t1_norm = normalize_team_name(team1)
        t2_norm = normalize_team_name(team2)

        t1_teams = set()
        t2_teams = set()

        for node, attrs in self.graph.nodes(data=True):
            if attrs.get('node_type') == 'team':
                name = attrs.get('name', '')
                if name == t1_norm:
                    for neighbor in self.graph.successors(node):
                        if self.graph.nodes[neighbor].get('node_type') == 'competition':
                            for next_node in self.graph.predecessors(neighbor):
                                if self.graph.nodes[next_node].get('node_type') == 'team':
                                    t1_teams.add(self.graph.nodes[next_node].get('name', ''))
                if name == t2_norm:
                    for neighbor in self.graph.successors(node):
                        if self.graph.nodes[neighbor].get('node_type') == 'competition':
                            for next_node in self.graph.predecessors(neighbor):
                                if self.graph.nodes[next_node].get('node_type') == 'team':
                                    t2_teams.add(self.graph.nodes[next_node].get('name', ''))

        common = t1_teams & t2_teams
        common.discard(t1_norm)
        common.discard(t2_norm)
        return list(common)

    def get_graph_statistics(self) -> Dict:
        """Return statistics about the knowledge graph."""
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'teams': sum(1 for _, attrs in self.graph.nodes(data=True) if attrs.get('node_type') == 'team'),
            'matches': sum(1 for _, attrs in self.graph.nodes(data=True) if attrs.get('node_type') == 'match'),
            'competitions': sum(1 for _, attrs in self.graph.nodes(data=True) if attrs.get('node_type') == 'competition'),
            'seasons': sum(1 for _, attrs in self.graph.nodes(data=True) if attrs.get('node_type') == 'season'),
            'players': sum(1 for _, attrs in self.graph.nodes(data=True) if attrs.get('node_type') == 'player'),
        }

    def get_team_neighbors(self, team_name: str) -> List[Dict]:
        """Get all direct neighbors of a team node in the graph."""
        target = normalize_team_name(team_name)
        target_node = None
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get('node_type') == 'team' and attrs.get('name') == target:
                target_node = node
                break

        if not target_node:
            return []

        neighbors = []
        for neighbor in self.graph.successors(target_node):
            attr = self.graph.nodes[neighbor]
            edge_data = self.graph.edges[target_node, neighbor]
            neighbors.append({
                'node_id': neighbor,
                'type': attr.get('node_type', ''),
                'name': attr.get('name', ''),
                'relation': edge_data.get('relation', ''),
            })
        for neighbor in self.graph.predecessors(target_node):
            attr = self.graph.nodes[neighbor]
            edge_data = self.graph.edges[target_node, neighbor]
            neighbors.append({
                'node_id': neighbor,
                'type': attr.get('node_type', ''),
                'name': attr.get('name', ''),
                'relation': edge_data.get('relation', ''),
            })

        return neighbors
