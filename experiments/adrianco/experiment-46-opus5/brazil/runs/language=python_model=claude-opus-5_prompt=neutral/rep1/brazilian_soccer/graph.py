"""The knowledge graph.

Nodes are teams, players, matches, competitions, seasons and countries; edges
connect them:

.. code-block:: text

    (match)  -[:HOME_TEAM]->  (team)
    (match)  -[:AWAY_TEAM]->  (team)
    (match)  -[:IN_COMPETITION]-> (competition)
    (match)  -[:IN_SEASON]->  (season)
    (player) -[:PLAYS_FOR]->  (team)
    (player) -[:FROM_COUNTRY]-> (country)

The store is plain Python (no external database) so the server starts with a
single ``load_graph()`` call and answers queries from memory. Alongside the
generic node/edge API, the graph keeps sorted adjacency lists and lookup indexes
so that "every Flamengo match" is a dict hit rather than a scan of 20k matches.
"""

from __future__ import annotations

import difflib
import os
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from .loader import Dataset, load_dataset
from .models import Match, Player, Team
from .normalization import slugify
from .teams import TeamRegistry

# Edge types
HOME_TEAM = "HOME_TEAM"
AWAY_TEAM = "AWAY_TEAM"
IN_COMPETITION = "IN_COMPETITION"
IN_SEASON = "IN_SEASON"
PLAYS_FOR = "PLAYS_FOR"
FROM_COUNTRY = "FROM_COUNTRY"

# Node types
TEAM = "team"
PLAYER = "player"
MATCH = "match"
COMPETITION = "competition"
SEASON = "season"
COUNTRY = "country"


@dataclass(frozen=True)
class Node:
    """A graph node: a typed id plus the domain object it wraps."""

    node_id: str
    node_type: str
    label: str
    payload: object = None


class KnowledgeGraph:
    """In-memory property graph over the Brazilian soccer datasets."""

    def __init__(self, dataset: Dataset) -> None:
        self.dataset = dataset
        self.registry: TeamRegistry = dataset.registry
        self.matches: list[Match] = dataset.matches
        self.players: list[Player] = dataset.players

        self._nodes: dict[str, Node] = {}
        self._out: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        self._in: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

        # Derived indexes (all values sorted by date, oldest first).
        self.matches_by_id: dict[str, Match] = {}
        self.matches_by_team: dict[str, list[Match]] = defaultdict(list)
        self.matches_by_competition: dict[str, list[Match]] = defaultdict(list)
        self.matches_by_competition_season: dict[tuple[str, int], list[Match]] = defaultdict(list)
        self.players_by_club: dict[str, list[Player]] = defaultdict(list)
        self.players_by_nationality: dict[str, list[Player]] = defaultdict(list)
        self.players_by_id: dict[str, Player] = {}
        self._player_name_index: dict[str, list[Player]] = defaultdict(list)

        self._build()

    # -- construction ------------------------------------------------------- #

    def _build(self) -> None:
        for team in self.registry.teams.values():
            self.add_node(f"team:{team.team_id}", TEAM, team.name, team)

        for match in self.matches:
            node_id = f"match:{match.match_id}"
            self.matches_by_id[match.match_id] = match
            self.add_node(node_id, MATCH, self.describe_match(match), match)

            for team_id, relation in ((match.home_team, HOME_TEAM),
                                      (match.away_team, AWAY_TEAM)):
                self.add_edge(node_id, relation, f"team:{team_id}")
                self.matches_by_team[team_id].append(match)

            competition_node = f"competition:{match.competition}"
            if competition_node not in self._nodes:
                self.add_node(competition_node, COMPETITION, match.competition)
            self.add_edge(node_id, IN_COMPETITION, competition_node)
            self.matches_by_competition[match.competition].append(match)

            if match.season is not None:
                season_node = f"season:{match.season}"
                if season_node not in self._nodes:
                    self.add_node(season_node, SEASON, str(match.season))
                self.add_edge(node_id, IN_SEASON, season_node)
                self.matches_by_competition_season[
                    (match.competition, match.season)
                ].append(match)

        for player in self.players:
            node_id = f"player:{player.player_id}"
            self.add_node(node_id, PLAYER, player.name, player)
            self.players_by_id[player.player_id] = player
            self.players_by_nationality[player.nationality].append(player)
            slug = slugify(player.name)
            self._player_name_index[slug].append(player)
            for token in slug.split():
                # A single-token name is already indexed under its full slug;
                # adding it again would list the player twice in every result.
                if len(token) > 2 and token != slug:
                    self._player_name_index[token].append(player)
            country_node = f"country:{player.nationality}"
            if country_node not in self._nodes:
                self.add_node(country_node, COUNTRY, player.nationality)
            self.add_edge(node_id, FROM_COUNTRY, country_node)
            if player.club_team_id:
                self.add_edge(node_id, PLAYS_FOR, f"team:{player.club_team_id}")
                self.players_by_club[player.club_team_id].append(player)

        for players in self.players_by_club.values():
            players.sort(key=lambda p: (-(p.overall or 0), p.name))
        for players in self.players_by_nationality.values():
            players.sort(key=lambda p: (-(p.overall or 0), p.name))

    # -- generic graph API -------------------------------------------------- #

    def add_node(self, node_id: str, node_type: str, label: str,
                 payload: object = None) -> Node:
        node = Node(node_id, node_type, label, payload)
        self._nodes[node_id] = node
        return node

    def add_edge(self, source: str, relation: str, target: str) -> None:
        self._out[source][relation].append(target)
        self._in[target][relation].append(source)

    def node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def neighbors(self, node_id: str, relation: str | None = None,
                  incoming: bool = False) -> list[Node]:
        """Nodes reachable from ``node_id`` (or pointing at it)."""
        table = self._in if incoming else self._out
        edges = table.get(node_id, {})
        relations = [relation] if relation else list(edges)
        found: list[Node] = []
        for name in relations:
            for other in edges.get(name, ()):
                node = self._nodes.get(other)
                if node is not None:
                    found.append(node)
        return found

    def nodes_of_type(self, node_type: str) -> list[Node]:
        return [node for node in self._nodes.values() if node.node_type == node_type]

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(targets) for edges in self._out.values()
                   for targets in edges.values())

    # -- convenience -------------------------------------------------------- #

    @property
    def teams(self) -> dict[str, Team]:
        return self.registry.teams

    @property
    def competitions(self) -> list[str]:
        return sorted(self.matches_by_competition)

    def team_name(self, team_id: str) -> str:
        return self.registry.name_of(team_id)

    def resolve_team(self, query: str) -> Team | None:
        return self.registry.resolve_one(query)

    def resolve_teams(self, query: str, limit: int = 5) -> list[Team]:
        return self.registry.resolve(query, limit=limit)

    def team_matches(self, team_id: str) -> list[Match]:
        return self.matches_by_team.get(team_id, [])

    def find_players(self, name: str, allow_fuzzy: bool = True) -> list[Player]:
        """Players matching ``name``: exact, then all-tokens, then fuzzy.

        FIFA spells many players with initials ("L. Messi"), so a search for
        "Lionel Messi" has to fall back from exact to token matching. Fuzzy
        matching is a last resort and callers that must not confuse two players
        should pass ``allow_fuzzy=False``.
        """
        needle = slugify(name)
        if not needle:
            return []

        exact = self._player_name_index.get(needle, ())
        if exact:
            return sorted(exact, key=lambda p: -(p.overall or 0))

        tokens = [t for t in needle.split() if len(t) > 1]
        if tokens:
            candidates = [p for p in self.players
                          if all(t in slugify(p.name) for t in tokens)]
            if candidates:
                return sorted(candidates, key=lambda p: -(p.overall or 0))

        if not allow_fuzzy:
            return []
        close = difflib.get_close_matches(
            needle, list(self._player_name_index), n=10, cutoff=0.75)
        found: dict[str, Player] = {}
        for key in close:
            for player in self._player_name_index[key]:
                found[player.player_id] = player
        return sorted(found.values(), key=lambda p: -(p.overall or 0))

    def seasons(self, competition: str | None = None) -> list[int]:
        matches = (self.matches_by_competition.get(competition, [])
                   if competition else self.matches)
        return sorted({m.season for m in matches if m.season is not None})

    def date_range(self) -> tuple[date | None, date | None]:
        dates = [m.date for m in self.matches if m.date]
        return (min(dates), max(dates)) if dates else (None, None)

    def describe_match(self, match: Match) -> str:
        home = self.team_name(match.home_team)
        away = self.team_name(match.away_team)
        if match.played:
            return f"{home} {match.home_goals}-{match.away_goals} {away}"
        return f"{home} vs {away}"

    def summary(self) -> dict:
        """High-level counts, handy as an MCP resource or a health check."""
        first, last = self.date_range()
        return {
            "teams": len(self.teams),
            "matches": len(self.matches),
            "players": len(self.players),
            "competitions": self.competitions,
            "nodes": self.node_count,
            "edges": self.edge_count,
            "first_match": first.isoformat() if first else None,
            "last_match": last.isoformat() if last else None,
            "sources": self.dataset.source_counts,
        }


_GRAPHS: dict[str | None, KnowledgeGraph] = {}
_LOCK = threading.Lock()


def load_graph(data_dir: str | os.PathLike | None = None,
               refresh: bool = False) -> KnowledgeGraph:
    """Load (and cache) the knowledge graph for a data directory.

    The graph is immutable once built, so it is cached per directory: the server
    calls this on every tool invocation and must not re-parse the CSVs each
    time. ``refresh=True`` forces a rebuild (useful after the files change).
    """
    key = os.fspath(data_dir) if data_dir is not None else None
    with _LOCK:
        if refresh or key not in _GRAPHS:
            _GRAPHS[key] = KnowledgeGraph(load_dataset(data_dir))
        return _GRAPHS[key]
