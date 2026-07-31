"""The in-memory knowledge graph: teams, matches, players and their edges.

Context
-------
Nodes are clubs (:class:`Team`) and players (:class:`Player`); edges are
matches (:class:`Match`, a team-team edge carrying competition/season/score)
and club membership (player -> team).

Two responsibilities beyond plain storage:

1. **De-duplication.**  ``Brasileirao_Matches.csv``,
   ``novo_campeonato_brasileiro.csv`` and ``BR-Football-Dataset.csv`` all cover
   Série A and overlap for 2014-2019.  Counting those rows twice would double
   every standings table.  League fixtures de-duplicate on
   ``(competition, season, home_key, away_key)`` -- in a double round-robin an
   ordered pair meets exactly once per season.  Cups (where two legs are normal)
   de-duplicate on the match date instead.  Duplicates are *merged*, so a row
   from the stats file can enrich a row from the schedule file.

2. **Indexing.**  Per-team, per-season and per-competition posting lists plus
   player name/nationality/club indexes, all built once at load time so that
   every query is a dictionary lookup followed by a linear scan of a small
   candidate list.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .loader import DEFAULT_DATA_DIR, load_all_matches, load_all_players
from .models import LEAGUE_COMPETITIONS, Match, Player, Team
from .normalization import normalize_team, normalize_text


@dataclass
class KnowledgeGraph:
    """Loaded dataset with all lookup indexes."""

    matches: list[Match] = field(default_factory=list)
    players: list[Player] = field(default_factory=list)
    teams: dict[str, Team] = field(default_factory=dict)

    # indexes -------------------------------------------------------------
    matches_by_team: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    matches_by_season: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    matches_by_competition: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    players_by_nationality: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    players_by_club: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    _team_search_index: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _player_name_index: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))

    load_seconds: float = 0.0
    rows_read: int = 0
    duplicates_merged: int = 0

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    @classmethod
    def build(
        cls,
        matches: Iterable[Match],
        players: Iterable[Player] = (),
    ) -> "KnowledgeGraph":
        started = time.perf_counter()
        graph = cls()
        graph._ingest_matches(matches)
        graph._ingest_players(players)
        graph.load_seconds = time.perf_counter() - started
        return graph

    @classmethod
    def from_data_dir(cls, data_dir: Path | str = DEFAULT_DATA_DIR) -> "KnowledgeGraph":
        return cls.build(load_all_matches(data_dir), load_all_players(data_dir))

    # -- matches ---------------------------------------------------------
    def _ingest_matches(self, matches: Iterable[Match]) -> None:
        seen: dict[tuple, int] = {}
        for match in matches:
            self.rows_read += 1
            fingerprint = _fingerprint(match)
            existing = seen.get(fingerprint)
            if existing is not None:
                _merge_match(self.matches[existing], match)
                self.duplicates_merged += 1
                continue
            seen[fingerprint] = len(self.matches)
            self.matches.append(match)

        self.matches.sort(key=_sort_key)
        for index, match in enumerate(self.matches):
            self._register_team(match.home_key, match.home_name, match.home_state, index)
            self._register_team(match.away_key, match.away_name, match.away_state, index)
            self.matches_by_team[match.home_key].append(index)
            self.matches_by_team[match.away_key].append(index)
            self.matches_by_competition[match.competition].append(index)
            if match.season is not None:
                self.matches_by_season[match.season].append(index)

    def _register_team(
        self, key: str, display: str, region: str | None, match_index: int
    ) -> None:
        team = self.teams.get(key)
        if team is None:
            team = Team(key=key, display=display, region=region)
            self.teams[key] = team
            for token in normalize_text(display).split():
                self._team_search_index[token].add(key)
            self._team_search_index[key].add(key)
        team.aliases.add(display)
        if region and not team.region:
            team.region = region
        team.match_indexes.append(match_index)

    # -- players ---------------------------------------------------------
    def _ingest_players(self, players: Iterable[Player]) -> None:
        for player in players:
            self.rows_read += 1
            index = len(self.players)
            self.players.append(player)
            self.players_by_nationality[normalize_text(player.nationality)].append(index)
            if player.club_key:
                self.players_by_club[player.club_key].append(index)
                team = self.teams.get(player.club_key)
                if team is not None:
                    team.player_indexes.append(index)
            for token in normalize_text(player.name).replace(".", " ").split():
                self._player_name_index[token].append(index)

    # ------------------------------------------------------------------
    # lookups
    # ------------------------------------------------------------------
    def resolve_team(self, query: str) -> Team | None:
        """Best single team for a user-typed name (``None`` if nothing fits)."""
        candidates = self.resolve_teams(query)
        return candidates[0] if candidates else None

    def resolve_teams(self, query: str, limit: int = 10) -> list[Team]:
        """All plausible teams for *query*, most-played first.

        Resolution order: exact canonical key, then key prefix (so ``atletico``
        finds ``atletico-mg``/``-pr``/``-go``), then token overlap on the
        display names and raw aliases.
        """
        query = (query or "").strip()
        if not query:
            return []

        normalized = normalize_team(query)
        base = normalized.base.replace(" ", "-")

        # A bare ambiguous name ("Atletico", "Botafogo") should surface every
        # regional club, busiest first -- but an explicit region pins it down.
        if normalized.key in self.teams and normalized.explicit_region:
            return [self.teams[normalized.key]]

        prefix_hits = [
            team
            for key, team in self.teams.items()
            if key == base or key == normalized.key or key.startswith(f"{base}-")
        ]
        if prefix_hits:
            return sorted(prefix_hits, key=lambda t: -len(t.match_indexes))[:limit]

        tokens = [t for t in normalize_text(query).split() if len(t) > 1]
        if not tokens:
            tokens = normalize_text(query).split()
        scored: dict[str, int] = defaultdict(int)
        matched: dict[str, set[str]] = defaultdict(set)
        for token in tokens:
            for indexed_token, keys in self._team_search_index.items():
                if indexed_token == token:
                    bonus = 3
                elif indexed_token.startswith(token) and len(token) >= 3:
                    bonus = 2
                elif len(token) >= 4 and token in indexed_token:
                    bonus = 1
                else:
                    continue
                for key in keys:
                    scored[key] += bonus
                    matched[key].add(token)
        # Require at least half the query's words to hit: one weak token match
        # out of four is noise ("Real Madrid Castilla B" is not Real-RR).
        needed = max(1, (len(tokens) + 1) // 2)
        ranked = sorted(
            (
                (key, score)
                for key, score in scored.items()
                if score >= 2 and len(matched[key]) >= needed
            ),
            key=lambda item: (
                -len(matched[item[0]]),
                -item[1],
                -len(self.teams[item[0]].match_indexes),
            ),
        )
        return [self.teams[key] for key, _ in ranked[:limit]]

    def team_matches(self, key: str) -> list[Match]:
        return [self.matches[i] for i in self.matches_by_team.get(key, ())]

    def find_players_by_name(self, query: str, limit: int = 50) -> list[Player]:
        """Substring/token search over player names (accent-insensitive).

        Players matching *more distinct query tokens* always outrank players
        matching one token well, so "Thiago Silva" beats every other Thiago.
        """
        needle = normalize_text(query)
        if not needle:
            return []
        tokens = needle.split()
        matched_tokens: dict[int, set[str]] = defaultdict(set)
        quality: dict[int, int] = defaultdict(int)
        for token in tokens:
            for indexed_token, indexes in self._player_name_index.items():
                if indexed_token == token:
                    bonus = 3
                elif indexed_token.startswith(token):
                    bonus = 2
                elif token in indexed_token:
                    bonus = 1
                else:
                    continue
                for index in indexes:
                    matched_tokens[index].add(token)
                    quality[index] = max(quality[index], 0) + bonus

        results = []
        for index, matched in matched_tokens.items():
            player = self.players[index]
            score = len(matched) * 100 + quality[index]
            if needle in normalize_text(player.name):  # verbatim substring
                score += 50
            results.append((score, player.overall or 0, player))
        results.sort(key=lambda item: (-item[0], -item[1]))
        return [player for _, _, player in results[:limit]]

    def name_is_exact(self, query: str, player: Player) -> bool:
        """True when every token of *query* appears in the player's name."""
        name = normalize_text(player.name)
        return all(token in name for token in normalize_text(query).split())

    # ------------------------------------------------------------------
    # metadata
    # ------------------------------------------------------------------
    @property
    def competitions(self) -> list[str]:
        return sorted(self.matches_by_competition)

    @property
    def seasons(self) -> list[int]:
        return sorted(self.matches_by_season)

    def seasons_for(self, competition: str) -> list[int]:
        return sorted(
            {
                self.matches[i].season
                for i in self.matches_by_competition.get(competition, ())
                if self.matches[i].season is not None
            }
        )

    def summary(self) -> dict:
        return {
            "matches": len(self.matches),
            "teams": len(self.teams),
            "players": len(self.players),
            "rows_read": self.rows_read,
            "duplicate_rows_merged": self.duplicates_merged,
            "load_seconds": round(self.load_seconds, 2),
            "competitions": {
                competition: len(indexes)
                for competition, indexes in sorted(self.matches_by_competition.items())
            },
            "season_range": (
                [self.seasons[0], self.seasons[-1]] if self.seasons else []
            ),
        }


# --------------------------------------------------------------------------
# de-duplication helpers
# --------------------------------------------------------------------------


def _fingerprint(match: Match) -> tuple:
    """Identity used to detect the same fixture appearing in two files."""
    if match.competition in LEAGUE_COMPETITIONS and match.season is not None:
        return (match.competition, match.season, match.home_key, match.away_key)
    return (
        match.competition,
        match.match_date,
        match.home_key,
        match.away_key,
    )


def _merge_match(target: Match, other: Match) -> None:
    """Fold a duplicate row into the record we are keeping."""
    target.sources |= other.sources
    if target.match_date is None:
        target.match_date = other.match_date
    if target.home_goals is None and other.home_goals is not None:
        target.home_goals = other.home_goals
        target.away_goals = other.away_goals
    for attribute in ("round", "stage", "venue", "home_state", "away_state"):
        if getattr(target, attribute) is None:
            setattr(target, attribute, getattr(other, attribute))
    for name, value in other.stats.items():
        target.stats.setdefault(name, value)


def _sort_key(match: Match) -> tuple:
    return (
        match.match_date.toordinal() if match.match_date else 0,
        match.competition,
        match.home_key,
    )


# --------------------------------------------------------------------------
# module-level cached graph (the MCP server loads once per process)
# --------------------------------------------------------------------------

_CACHED: dict[str, KnowledgeGraph] = {}


def load_default_graph(data_dir: Path | str = DEFAULT_DATA_DIR) -> KnowledgeGraph:
    """Load (and memoise) the graph for *data_dir*."""
    key = str(Path(data_dir).resolve())
    graph = _CACHED.get(key)
    if graph is None:
        graph = KnowledgeGraph.from_data_dir(data_dir)
        _CACHED[key] = graph
    return graph
