"""
================================================================================
 Module: knowledge_graph
================================================================================
Context
-------
An in-memory knowledge graph over the loaded Brazilian soccer data.  The graph
models four node types -- Team, Player, Match and Competition -- and the
relationships between them (a team *plays in* a match, a player *plays for* a
club, a match *belongs to* a competition / season).

Why in-memory rather than an external graph database?  The benchmark must build
and run its tests deterministically with no external services.  The full
dataset (~24k matches, ~18k players) fits comfortably in memory, and the
indexes built here keep simple lookups well under the < 2s requirement and
aggregate queries under < 5s.

The graph builds adjacency indexes keyed by the canonical team key produced by
``normalization.team_key`` so the many naming variations in the source data all
resolve to a single Team node.
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from . import data_loader
from .data_loader import Match, Player
from .normalization import display_name_for_key, team_key, team_query_matches


class Team:
    """A team node, aggregating its canonical key and observed display names."""

    def __init__(self, key: str):
        self.key = key
        self.names: Dict[str, int] = defaultdict(int)  # display name -> frequency
        self.match_indices: List[int] = []

    @property
    def display_name(self) -> str:
        """Preferred canonical name if defined, else the most frequently
        observed (and otherwise shortest) display name."""
        preferred = display_name_for_key(self.key)
        if preferred:
            return preferred
        if not self.names:
            return self.key.title()
        return max(self.names.items(), key=lambda kv: (kv[1], -len(kv[0])))[0]


class KnowledgeGraph:
    """Holds all matches/players and the indexes used to query them."""

    def __init__(self, matches: Optional[List[Match]] = None,
                 players: Optional[List[Player]] = None):
        self.matches: List[Match] = matches or []
        self.players: List[Player] = players or []
        self.teams: Dict[str, Team] = {}
        self._players_by_club: Dict[str, List[Player]] = defaultdict(list)
        self._build_indexes()

    # ------------------------------------------------------------------ build
    @classmethod
    def from_data_dir(cls, data_dir: Optional[str] = None) -> "KnowledgeGraph":
        """Load every available dataset from ``data_dir`` into a new graph."""
        matches = data_loader.load_all_matches(data_dir)
        players = data_loader.load_all_players(data_dir)
        return cls(matches=matches, players=players)

    def _build_indexes(self) -> None:
        self.teams = {}
        for idx, match in enumerate(self.matches):
            self._register_team(match.home_key, match.home_team, idx)
            self._register_team(match.away_key, match.away_team, idx)
        self._players_by_club = defaultdict(list)
        for player in self.players:
            if player.club_key:
                self._players_by_club[player.club_key].append(player)

    def _register_team(self, key: str, name: str, match_index: int) -> None:
        if not key:
            return
        team = self.teams.get(key)
        if team is None:
            team = Team(key)
            self.teams[key] = team
        if name:
            team.names[name] += 1
        team.match_indices.append(match_index)

    # ----------------------------------------------------------- team lookups
    def resolve_team(self, query: str) -> Optional[Team]:
        """Resolve a free-text team query to a single Team node.

        Prefers an exact canonical-key match; otherwise picks the team with the
        most matches among fuzzy candidates (so "Atletico" prefers the club with
        the largest footprint in the data)."""
        if not query:
            return None
        key = team_key(query)
        if key in self.teams:
            return self.teams[key]
        candidates = [t for t in self.teams.values()
                      if team_query_matches(query, t.key)]
        if not candidates:
            return None
        return max(candidates, key=lambda t: len(t.match_indices))

    def team_matches(self, team: Team) -> List[Match]:
        return [self.matches[i] for i in team.match_indices]

    def team_display_name(self, query: str) -> Optional[str]:
        team = self.resolve_team(query)
        return team.display_name if team else None

    # --------------------------------------------------------- match filtering
    def filter_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        season_from: Optional[int] = None,
        season_to: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        home_only_for: Optional[str] = None,
    ) -> List[Match]:
        """Return matches satisfying all supplied criteria.

        ``team``/``opponent`` are free-text and resolved to canonical keys.
        ``home_only_for`` restricts to matches where that team played at home.
        """
        team_node = self.resolve_team(team) if team else None
        opp_node = self.resolve_team(opponent) if opponent else None
        home_node = self.resolve_team(home_only_for) if home_only_for else None

        # Use the smaller candidate set as the iteration base for speed.
        if team_node is not None:
            base = self.team_matches(team_node)
        elif opp_node is not None:
            base = self.team_matches(opp_node)
        else:
            base = self.matches

        comp_lc = competition.lower() if competition else None
        results: List[Match] = []
        for m in base:
            if team_node and not m.involves(team_node.key):
                continue
            if opp_node and not m.involves(opp_node.key):
                continue
            if home_node and m.home_key != home_node.key:
                continue
            if comp_lc and comp_lc not in m.competition.lower():
                continue
            if season is not None and m.season != season:
                continue
            if season_from is not None and (m.season is None or m.season < season_from):
                continue
            if season_to is not None and (m.season is None or m.season > season_to):
                continue
            if date_from and (m.date is None or m.date < date_from):
                continue
            if date_to and (m.date is None or m.date > date_to):
                continue
            results.append(m)

        results.sort(key=lambda x: (x.date or "", x.competition))
        return results

    # ------------------------------------------------------- player filtering
    def players_by_club(self, query: str) -> List[Player]:
        team = self.resolve_team(query)
        results: List[Player] = []
        if team and team.key in self._players_by_club:
            results.extend(self._players_by_club[team.key])
        # Fall back to fuzzy club-name matching for clubs not present as teams
        # in the match data (e.g. European clubs in the FIFA set).
        if not results:
            key = team_key(query)
            for club_key, plist in self._players_by_club.items():
                if team_query_matches(query, club_key) or key == club_key:
                    results.extend(plist)
        return results

    def players_by_nationality(self, nationality: str) -> List[Player]:
        nat = nationality.strip().lower()
        return [p for p in self.players if p.nationality.lower() == nat]

    def search_players_by_name(self, name: str) -> List[Player]:
        q = name.strip().lower()
        if not q:
            return []
        from .normalization import strip_accents
        qn = strip_accents(q)
        scored = []
        for p in self.players:
            pn = strip_accents(p.name.lower())
            if qn == pn:
                scored.append((0, p))
            elif pn.startswith(qn):
                scored.append((1, p))
            elif qn in pn:
                scored.append((2, p))
        scored.sort(key=lambda sp: (sp[0], -(sp[1].overall or 0)))
        return [p for _, p in scored]

    # --------------------------------------------------------------- summary
    def competitions(self) -> List[str]:
        return sorted({m.competition for m in self.matches})

    def seasons(self) -> List[int]:
        return sorted({m.season for m in self.matches if m.season is not None})

    def stats_summary(self) -> dict:
        return {
            "matches": len(self.matches),
            "players": len(self.players),
            "teams": len(self.teams),
            "competitions": len(self.competitions()),
        }
