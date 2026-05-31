"""
================================================================================
Brazilian Soccer MCP Server :: knowledge_graph
================================================================================

Context
-------
Builds an in-memory knowledge graph over the normalised Match/Player records
produced by data_loader. The "graph" links four entity types:

    Team  --plays-->  Match  <--plays--  Team
    Team  --has-->    Player
    Match --part_of-> Competition (by name + season)

Rather than a heavyweight graph database, the relationships are realised as
dict-based adjacency indexes keyed on normalised team names. This keeps lookups
O(1)/O(k) so simple queries are well under the 2-second budget and aggregate
queries under 5 seconds, with zero external service dependencies.

Public surface
--------------
- KnowledgeGraph.from_data_dir(path) / KnowledgeGraph(matches, players)
- .team_matches(key)         : all matches a team played
- .matches_between(a, b)     : head-to-head matches
- .resolve_team(name)        : fuzzy-ish resolution of a user-supplied team name
- .players_by_club(key)      : roster from FIFA data
- index attributes for competitions, seasons, teams.
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Optional

from .data_loader import (
    DataLoader,
    Match,
    Player,
    clean_team_name,
    normalize_team_name,
)


class KnowledgeGraph:
    """In-memory knowledge graph + lookup indexes over matches and players."""

    def __init__(self, matches: list[Match], players: list[Player]):
        self.matches: list[Match] = matches
        self.players: list[Player] = players

        # team key -> matches involving the team (home or away)
        self._team_matches: dict[str, list[Match]] = defaultdict(list)
        # team key -> canonical display name (prefer shortest clean name seen)
        self._team_display: dict[str, str] = {}
        # competition name -> set of seasons
        self._competition_seasons: dict[str, set[int]] = defaultdict(set)
        # club key -> players
        self._club_players: dict[str, list[Player]] = defaultdict(list)
        # nationality (lower) -> players
        self._players_by_nationality: dict[str, list[Player]] = defaultdict(list)

        self._build()

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def from_data_dir(cls, data_dir: Optional[str] = None) -> "KnowledgeGraph":
        loader = DataLoader(data_dir) if data_dir else DataLoader()
        matches, players = loader.load_all()
        return cls(matches, players)

    def _register_team(self, key: str, display: str) -> None:
        if not key:
            return
        # For state-qualified keys ("atletico mg") keep the state in the display
        # name so distinct clubs ("Atlético-MG" vs "Atlético-PR") read clearly.
        parts = key.rsplit(" ", 1)
        if len(parts) == 2 and len(parts[1]) == 2 and display:
            display = f"{display}-{parts[1].upper()}"
        existing = self._team_display.get(key)
        if existing is None or (display and len(display) < len(existing)):
            self._team_display[key] = display or existing or key

    def _build(self) -> None:
        for m in self.matches:
            if m.home_key:
                self._team_matches[m.home_key].append(m)
                self._register_team(m.home_key, m.home_team)
            if m.away_key:
                self._team_matches[m.away_key].append(m)
                self._register_team(m.away_key, m.away_team)
            if m.season is not None:
                self._competition_seasons[m.competition].add(m.season)

        for p in self.players:
            if p.club_key:
                self._club_players[p.club_key].append(p)
            if p.nationality:
                self._players_by_nationality[p.nationality.lower()].append(p)

    # ------------------------------------------------------------------ #
    # Team resolution & lookups
    # ------------------------------------------------------------------ #
    @property
    def teams(self) -> list[str]:
        """Sorted list of canonical team display names known to the graph."""
        return sorted(set(self._team_display.values()))

    def display_name(self, key: str) -> str:
        return self._team_display.get(key, key)

    def resolve_team(self, name: str) -> Optional[str]:
        """Resolve a user-supplied team name to a normalised key.

        Tries exact normalised match first, then a substring containment match
        (handles "Sao Paulo" vs "Sao Paulo FC" and partial names)."""
        if not name:
            return None
        key = normalize_team_name(name)
        if key in self._team_matches:
            return key
        # containment: candidate key contains the query or vice-versa
        candidates = [
            k
            for k in self._team_matches
            if key and (key in k or k in key)
        ]
        if not candidates:
            return None
        # prefer the closest length match
        candidates.sort(key=lambda k: abs(len(k) - len(key)))
        return candidates[0]

    def team_matches(self, key: str) -> list[Match]:
        return self._team_matches.get(key, [])

    def matches_between(self, key_a: str, key_b: str) -> list[Match]:
        out = [
            m
            for m in self._team_matches.get(key_a, [])
            if key_b in (m.home_key, m.away_key)
        ]
        out.sort(key=lambda m: (m.date or _MIN_DATE, m.competition))
        return out

    # ------------------------------------------------------------------ #
    # Competitions
    # ------------------------------------------------------------------ #
    @property
    def competitions(self) -> list[str]:
        return sorted(self._competition_seasons.keys())

    def seasons(self, competition: Optional[str] = None) -> list[int]:
        if competition is None:
            seasons: set[int] = set()
            for s in self._competition_seasons.values():
                seasons |= s
            return sorted(seasons)
        return sorted(self._competition_seasons.get(competition, set()))

    def matches_in(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> list[Match]:
        out = self.matches
        if competition is not None:
            comp_l = competition.lower()
            out = [m for m in out if comp_l in m.competition.lower()]
        if season is not None:
            out = [m for m in out if m.season == season]
        return out

    # ------------------------------------------------------------------ #
    # Players
    # ------------------------------------------------------------------ #
    def players_by_club(self, club_key: str) -> list[Player]:
        return self._club_players.get(club_key, [])

    def players_by_nationality(self, nationality: str) -> list[Player]:
        return self._players_by_nationality.get(nationality.lower(), [])

    def find_players(self, name: str) -> list[Player]:
        q = name.strip().lower()
        if not q:
            return []
        return [p for p in self.players if q in p.name.lower()]


from datetime import date as _date

_MIN_DATE = _date.min
