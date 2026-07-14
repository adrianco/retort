"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
Module    : brazilian_soccer.knowledge_graph
Purpose   : In-memory knowledge graph + indexes over matches and players.

KnowledgeGraph is the central data store. On construction it loads all datasets
(via data_loader) and builds indexes for fast lookup:

  * matches_by_team[team_key]      -> list[Match]
  * matches_by_competition[name]   -> list[Match]
  * matches_by_season[year]        -> list[Match]
  * players_by_club[club_key]      -> list[Player]
  * players_by_nationality[key]    -> list[Player]
  * team_display[team_key]         -> best human-readable team name

All query modules (queries/*) operate on a KnowledgeGraph instance. A module-level
get_default_graph() provides a lazily-loaded singleton shared by the MCP server so
the CSVs are parsed only once per process.
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from .data_loader import load_all
from .models import Match, Player
from .normalize import normalize_team_name

# Max gap (days) between two records of the same (competition, home, away) fixture
# for them to be considered the same match. See KnowledgeGraph._dedupe_matches.
DEDUP_WINDOW_DAYS = 80


class KnowledgeGraph:
    """Holds all matches/players and the indexes used by the query layer."""

    def __init__(self, data_dir: Optional[str] = None, *, load: bool = True):
        self.matches: List[Match] = []
        self.players: List[Player] = []

        self.matches_by_team: Dict[str, List[Match]] = defaultdict(list)
        self.matches_by_competition: Dict[str, List[Match]] = defaultdict(list)
        self.matches_by_season: Dict[int, List[Match]] = defaultdict(list)
        self.players_by_club: Dict[str, List[Player]] = defaultdict(list)
        self.players_by_nationality: Dict[str, List[Player]] = defaultdict(list)
        self.team_display: Dict[str, str] = {}

        if load:
            matches, players = load_all(data_dir)
            self.load_records(matches, players)

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    def load_records(self, matches: List[Match], players: List[Player]) -> None:
        """Populate the store and (re)build all indexes."""
        self.matches = self._dedupe_matches(matches)
        self.players = list(players)
        self._build_indexes()

    @staticmethod
    def _dedupe_matches(matches: List[Match]) -> List[Match]:
        """Drop duplicate fixtures that appear in more than one source file.

        Several datasets overlap (e.g. Brasileirao_Matches.csv and
        novo_campeonato_brasileiro.csv both cover 2019, and BR-Football repeats
        Serie A games), which would otherwise double-count results.

        A fixture is keyed by (competition, home_team, away_team) — the *ordered*
        orientation, which is a physical fact a fixture cannot disagree on. Two
        records with that same key are treated as the same match when their dates
        fall within DEDUP_WINDOW_DAYS of each other. The window (rather than an
        exact date) absorbs timezone offsets and postponements (the COVID-era 2020
        season pushed some games months later, and BR-Football logs the rescheduled
        date). It stays well under the ~half-season gap between a pair's two legs
        (which have opposite orientations anyway), so legitimate fixtures survive.
        Records without a parseable date are always kept (cannot be safely keyed).
        The first occurrence wins, preserving the canonical competition label.
        """
        seen: dict = {}  # (competition, home_key, away_key) -> list[date] kept
        unique: List[Match] = []
        for m in matches:
            if m.match_date is None:
                unique.append(m)
                continue
            key = (m.competition, m.home_key, m.away_key)
            kept_dates = seen.setdefault(key, [])
            if any(abs((m.match_date - d).days) <= DEDUP_WINDOW_DAYS for d in kept_dates):
                continue
            kept_dates.append(m.match_date)
            unique.append(m)
        return unique

    def _build_indexes(self) -> None:
        self.matches_by_team.clear()
        self.matches_by_competition.clear()
        self.matches_by_season.clear()
        self.players_by_club.clear()
        self.players_by_nationality.clear()
        self.team_display.clear()

        for m in self.matches:
            self.matches_by_team[m.home_key].append(m)
            self.matches_by_team[m.away_key].append(m)
            self.matches_by_competition[m.competition].append(m)
            if m.season is not None:
                self.matches_by_season[m.season].append(m)
            # Remember the most descriptive display name seen for each team key
            # (the longest one), so distinct clubs that share a short base name
            # — e.g. the three "Atlético"s — render with their full names.
            self._record_display(m.home_key, m.home_team)
            self._record_display(m.away_key, m.away_team)

        for p in self.players:
            if p.club_key:
                self.players_by_club[p.club_key].append(p)
            if p.nationality_key:
                self.players_by_nationality[p.nationality_key].append(p)

    def _record_display(self, key: str, name: str) -> None:
        """Keep the longest non-empty display name seen for a team key."""
        if not name:
            return
        current = self.team_display.get(key)
        if current is None or len(name) > len(current):
            self.team_display[key] = name

    # ------------------------------------------------------------------ #
    # Convenience accessors
    # ------------------------------------------------------------------ #
    def team_key(self, name: str) -> str:
        return normalize_team_name(name)

    def display_name(self, team_key: str) -> str:
        return self.team_display.get(team_key, team_key.title())

    def matches_for_team(self, name: str) -> List[Match]:
        return list(self.matches_by_team.get(self.team_key(name), []))

    def competitions(self) -> List[str]:
        return sorted(self.matches_by_competition.keys())

    def seasons(self) -> List[int]:
        return sorted(self.matches_by_season.keys())

    def stats(self) -> dict:
        """Summary counts, handy for diagnostics and the MCP `summary` tool."""
        return {
            "total_matches": len(self.matches),
            "total_players": len(self.players),
            "competitions": self.competitions(),
            "seasons": [s for s in self.seasons()],
            "distinct_teams": len(self.matches_by_team),
        }


# --------------------------------------------------------------------------- #
# Lazy singleton for the server
# --------------------------------------------------------------------------- #
_DEFAULT: Optional[KnowledgeGraph] = None


def get_default_graph(data_dir: Optional[str] = None) -> KnowledgeGraph:
    """Return a process-wide KnowledgeGraph, loading the CSVs on first use."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = KnowledgeGraph(data_dir)
    return _DEFAULT
