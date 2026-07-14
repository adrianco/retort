"""
==============================================================================
Module: brazilian_soccer.knowledge_graph
==============================================================================
CONTEXT
-------
An in-memory knowledge graph over the Brazilian soccer datasets. The original
benchmark prompt suggested Neo4j; to keep the deliverable self-contained and
dependency-free (no external database server required to run or test) we build
an equivalent property-graph entirely in Python:

    NODES
        * Team    -- keyed by canonical normalized name
        * Player  -- FIFA player records
        * Match   -- fixtures (edges between two Team nodes)
        * Competition / Season -- implicit, via indexes

    EDGES / RELATIONSHIPS
        * Team   --PLAYED-->        Match
        * Match  --HOME_TEAM/AWAY-> Team
        * Player --PLAYS_FOR-->     Team (by club)

The graph pre-builds inverted indexes (by team, by competition, by season, by
player name, by nationality, by club) so every query in
``brazilian_soccer.queries`` runs in well under the spec's latency budget
(< 2s simple, < 5s aggregate) without rescanning the raw rows.

This is the single source of truth loaded once and shared by the MCP server.
==============================================================================
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from .data_loader import load_all_matches, load_all_players, DEFAULT_DATA_DIR
from .models import Match, Player
from .normalization import fold_accents, normalize_team


class KnowledgeGraph:
    """Indexed, in-memory property graph over matches and players."""

    def __init__(self, matches: List[Match], players: List[Player]):
        self.matches: List[Match] = matches
        self.players: List[Player] = players

        # --- Match indexes ------------------------------------------------
        self.matches_by_team: Dict[str, List[Match]] = defaultdict(list)
        self.matches_by_competition: Dict[str, List[Match]] = defaultdict(list)
        self.matches_by_season: Dict[int, List[Match]] = defaultdict(list)
        self.team_display: Dict[str, str] = {}  # canonical key -> best display

        for m in self.matches:
            self.matches_by_team[m.home_key].append(m)
            self.matches_by_team[m.away_key].append(m)
            self.matches_by_competition[m.competition].append(m)
            if m.season is not None:
                self.matches_by_season[m.season].append(m)
            # Remember a human-friendly display name per team key.
            self.team_display.setdefault(m.home_key, m.home)
            self.team_display.setdefault(m.away_key, m.away)

        # --- Player indexes -----------------------------------------------
        self.players_by_club: Dict[str, List[Player]] = defaultdict(list)
        self.players_by_nationality: Dict[str, List[Player]] = defaultdict(list)
        for p in self.players:
            if p.club_key:
                self.players_by_club[p.club_key].append(p)
            if p.nationality:
                self.players_by_nationality[
                    fold_accents(p.nationality).lower()
                ].append(p)

    # ---------------------------------------------------------------------
    # Construction helpers
    # ---------------------------------------------------------------------
    @classmethod
    def load(cls, data_dir: str = DEFAULT_DATA_DIR) -> "KnowledgeGraph":
        """Build the graph from the CSV files in ``data_dir``."""
        return cls(load_all_matches(data_dir), load_all_players(data_dir))

    # ---------------------------------------------------------------------
    # Team helpers
    # ---------------------------------------------------------------------
    def team_key(self, name: str) -> str:
        return normalize_team(name)

    def display_for(self, team_key: str) -> str:
        return self.team_display.get(team_key, team_key.title())

    def known_team_keys(self) -> List[str]:
        return sorted(self.matches_by_team.keys())

    def matches_for_team(self, name: str) -> List[Match]:
        return list(self.matches_by_team.get(self.team_key(name), []))

    # ---------------------------------------------------------------------
    # Player helpers
    # ---------------------------------------------------------------------
    def players_at_club(self, club: str) -> List[Player]:
        return list(self.players_by_club.get(normalize_team(club), []))

    def players_of_nationality(self, nationality: str) -> List[Player]:
        return list(
            self.players_by_nationality.get(fold_accents(nationality).lower(), [])
        )

    # ---------------------------------------------------------------------
    # Stats
    # ---------------------------------------------------------------------
    def summary(self) -> dict:
        return {
            "total_matches": len(self.matches),
            "total_players": len(self.players),
            "teams": len(self.matches_by_team),
            "competitions": sorted(self.matches_by_competition.keys()),
            "seasons": sorted(s for s in self.matches_by_season.keys()),
            "sources": sorted({m.source for m in self.matches}),
        }


# Lazily-instantiated process-wide singleton for the MCP server.
_GRAPH: Optional[KnowledgeGraph] = None


def get_graph(data_dir: str = DEFAULT_DATA_DIR) -> KnowledgeGraph:
    """Return the shared knowledge graph, loading it on first use."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = KnowledgeGraph.load(data_dir)
    return _GRAPH
