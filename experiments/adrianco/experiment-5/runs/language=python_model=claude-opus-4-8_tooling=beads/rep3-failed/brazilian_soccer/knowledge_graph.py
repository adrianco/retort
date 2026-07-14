"""
================================================================================
Context: Brazilian Soccer MCP Server
Module:   brazilian_soccer.knowledge_graph
--------------------------------------------------------------------------------
Purpose:
    The in-memory knowledge graph. It loads every Match and Player once and
    builds the indexes the query engine relies on:

        - matches_by_team[team_key]      -> list[Match]      (home OR away)
        - players_by_club_key[club_key]  -> list[Player]
        - players_by_nationality[lower]  -> list[Player]
        - team registry (key -> best display name)

    Think of teams and players as nodes; a Match is an edge connecting two team
    nodes (and carrying a result), while "plays for" connects a Player node to
    a club. The engine traverses these adjacency lists to answer questions.

    resolve_team() does fuzzy name resolution so a user typing "flamengo" or
    "Palmeiras-SP" lands on the right canonical team key.

Dependencies: standard library only.
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

from .data_loader import (
    DEFAULT_DATA_DIR,
    load_all_matches,
    load_all_players,
)
from .models import Match, Player
from .normalize import strip_accents, team_key


class KnowledgeGraph:
    """Entity store + adjacency indexes over matches and players."""

    def __init__(self, matches: list[Match], players: list[Player]):
        self.matches = matches
        self.players = players

        self.matches_by_team: dict[str, list[Match]] = defaultdict(list)
        self.team_names: dict[str, str] = {}          # key -> display name
        self._team_name_counts: dict[str, dict] = defaultdict(lambda: defaultdict(int))

        self.players_by_club_key: dict[str, list[Player]] = defaultdict(list)
        self.players_by_nationality: dict[str, list[Player]] = defaultdict(list)

        self._index_matches()
        self._index_players()

    # ----- index construction --------------------------------------------
    def _register_team(self, key: str, display: str) -> None:
        if not key:
            return
        # Track the most common display spelling so the canonical name is the
        # one that appears most often across the datasets.
        self._team_name_counts[key][display] += 1

    def _index_matches(self) -> None:
        for m in self.matches:
            if m.home_key:
                self.matches_by_team[m.home_key].append(m)
                self._register_team(m.home_key, m.home_team)
            if m.away_key:
                self.matches_by_team[m.away_key].append(m)
                self._register_team(m.away_key, m.away_team)
        for key, counts in self._team_name_counts.items():
            self.team_names[key] = max(counts.items(), key=lambda kv: kv[1])[0]

    def _index_players(self) -> None:
        for p in self.players:
            if p.club:
                self.players_by_club_key[team_key(p.club)].append(p)
            if p.nationality:
                self.players_by_nationality[p.nationality.lower()].append(p)

    # ----- team resolution -----------------------------------------------
    def resolve_team(self, name: str) -> str | None:
        """Resolve a free-text team name to a canonical team key.

        Tries exact key match first, then a substring match on the canonical
        keys (so "flamengo" matches "flamengo" even if the user omits a tag).
        Returns the best matching key or None.
        """
        if not name:
            return None
        key = team_key(name)
        if key in self.matches_by_team:
            return key
        # Substring / prefix matching against known team keys.
        candidates = [k for k in self.matches_by_team if key and (key in k or k in key)]
        if not candidates:
            # Fall back to accent-insensitive token overlap.
            token = strip_accents(name).lower().strip()
            candidates = [k for k in self.matches_by_team if token and token in k]
        if not candidates:
            return None
        # Prefer the candidate with the most matches (the canonical big club).
        return max(candidates, key=lambda k: len(self.matches_by_team[k]))

    def team_display(self, key: str) -> str:
        return self.team_names.get(key, key)

    def all_team_keys(self) -> list[str]:
        return sorted(self.matches_by_team.keys())

    # ----- summary --------------------------------------------------------
    def stats_summary(self) -> dict:
        return {
            "matches": len(self.matches),
            "players": len(self.players),
            "teams": len(self.matches_by_team),
            "competitions": sorted({m.competition for m in self.matches}),
            "sources": sorted({m.source for m in self.matches}),
        }


@lru_cache(maxsize=4)
def load_default_graph(data_dir: str = DEFAULT_DATA_DIR) -> KnowledgeGraph:
    """Load (and cache) the knowledge graph from the bundled datasets."""
    matches = load_all_matches(data_dir)
    players = load_all_players(data_dir)
    return KnowledgeGraph(matches, players)
