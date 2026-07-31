"""
In-memory knowledge graph.

Context
-------
TASK.md asks for "a knowledge graph interface for Brazilian soccer data".  This
module builds exactly that, entirely in memory and with no external database:

* **Nodes** -- ``competition``, ``season``, ``team``, ``match``, ``player``,
  ``venue``.  Ids are namespaced strings such as ``team:flamengo-rj``.
* **Edges** -- typed and directed::

      match  --home_team-->      team
      match  --away_team-->      team
      match  --in_competition--> competition
      match  --in_season-->      season
      match  --played_at-->      venue
      season --of_competition--> competition
      team   --competed_in-->    competition
      player --plays_for-->      team

  Traversal is available in both directions (:meth:`KnowledgeGraph.neighbors`),
  so "which matches did Flamengo play" is an in-edge walk from ``team:flamengo-rj``.

* **Indexes** -- the query layer is latency-bound (TASK.md: simple lookups
  < 2 s, aggregates < 5 s), so the graph also keeps plain dict indexes for the
  hot paths.  A full load of ~43k rows takes well under a second and the graph
  is cached per process by :func:`load_knowledge_graph`.

De-duplication
--------------
The datasets overlap heavily: Serie A 2014-2019 appears in three different
files.  Counting those three times would corrupt every standings table, so
fixtures are merged on ``(competition, home team, away team)`` plus date
proximity, keeping the highest-priority source's scores and the union of every
source's extra statistics.  ``Match.sources`` records which files contributed.
"""

from __future__ import annotations

import datetime as dt
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator

from .config import DATASETS, missing_datasets
from .loaders import SOURCE_PRIORITY, load_matches, load_players, read_all_match_rows
from .models import COMPETITIONS, Competition, Match, Player, Team
from .teams import DERBIES, TeamRegistry
from .text import normalize_name, slugify

__all__ = ["KnowledgeGraph", "LoadReport", "load_knowledge_graph", "build_knowledge_graph"]

#: Two rows describe the same fixture when their dates are this close.
_DUPLICATE_WINDOW = dt.timedelta(days=10)


@dataclass(slots=True)
class LoadReport:
    """What was read, what was merged, and how long it took."""

    rows_by_dataset: dict[str, int] = field(default_factory=dict)
    matches_after_merge: int = 0
    merged_duplicates: int = 0
    rejected_rows: int = 0
    players: int = 0
    teams: int = 0
    linked_player_clubs: int = 0
    missing_files: list[str] = field(default_factory=list)
    load_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows_by_dataset": dict(self.rows_by_dataset),
            "matches_after_merge": self.matches_after_merge,
            "merged_duplicates": self.merged_duplicates,
            "rejected_rows": self.rejected_rows,
            "players": self.players,
            "teams": self.teams,
            "linked_player_clubs": self.linked_player_clubs,
            "missing_files": list(self.missing_files),
            "load_seconds": round(self.load_seconds, 3),
        }


def _merge_group(group: list[Match]) -> Match:
    """Fold duplicate rows for one fixture into a single match record."""

    def rank(match: Match) -> tuple:
        return (
            0 if match.has_score else 1,
            SOURCE_PRIORITY.get(match.sources[0], 99) if match.sources else 99,
            match.id,
        )

    ordered = sorted(group, key=rank)
    primary = ordered[0]
    merged = Match(
        id=primary.id,
        competition_id=primary.competition_id,
        season=primary.season,
        date=primary.date,
        kickoff=primary.kickoff,
        round=primary.round,
        stage=primary.stage,
        venue=primary.venue,
        home_team_id=primary.home_team_id,
        away_team_id=primary.away_team_id,
        home_team_raw=primary.home_team_raw,
        away_team_raw=primary.away_team_raw,
        home_goals=primary.home_goals,
        away_goals=primary.away_goals,
        sources=[],
        stats=dict(primary.stats),
    )
    for match in ordered:
        for source in match.sources:
            if source not in merged.sources:
                merged.sources.append(source)
        if merged.season is None:
            merged.season = match.season
        if merged.date is None:
            merged.date = match.date
        for attribute in ("kickoff", "round", "stage", "venue"):
            if getattr(merged, attribute) is None:
                setattr(merged, attribute, getattr(match, attribute))
        if not merged.has_score and match.has_score:
            merged.home_goals = match.home_goals
            merged.away_goals = match.away_goals
        for name, value in match.stats.items():
            merged.stats.setdefault(name, value)
    return merged


#: Serie A has been a pure double round robin since 2003, so an ordered pair of
#: clubs meets exactly once per season -- any two such rows are the same
#: fixture no matter how far apart the recorded dates are (postponements).
_ROUND_ROBIN_COMPETITIONS = frozenset({"serie-a"})


def deduplicate(matches: Iterable[Match]) -> tuple[list[Match], int]:
    """Merge cross-source duplicates; returns ``(matches, duplicates_removed)``.

    Fixtures are bucketed by competition plus the ordered pair of clubs, which
    already separates the two legs of a cup tie (they have opposite home/away
    order).  Within a bucket:

    * Serie A rows merge per season -- the competition is a guaranteed double
      round robin, so Goias-Corinthians 2022 is one fixture even though the
      Brasileirao file has the original 15 Oct date (no score) and the
      extended-stats file has the 29 Oct replay.
    * every other competition merges by date proximity
      (:data:`_DUPLICATE_WINDOW`), keeping genuinely separate meetings apart.
    """

    buckets: dict[tuple[str, str, str], list[Match]] = defaultdict(list)
    for match in matches:
        buckets[(match.competition_id, match.home_team_id, match.away_team_id)].append(match)

    merged: list[Match] = []
    duplicates = 0
    far_future = dt.date(9999, 12, 31)
    for (competition_id, _, _), bucket in buckets.items():
        bucket.sort(key=lambda m: (m.date or far_future, m.id))
        if competition_id in _ROUND_ROBIN_COMPETITIONS:
            groups = _group_by_season(bucket)
        else:
            groups = _group_by_date_proximity(bucket)
        for group in groups:
            merged.append(_merge_group(group))
            duplicates += len(group) - 1

    merged.sort(key=lambda m: (m.date or far_future, m.competition_id, m.id))
    return merged, duplicates


def _group_by_season(bucket: list[Match]) -> list[list[Match]]:
    """One group per season; rows without a season fall back to proximity."""

    by_season: dict[int, list[Match]] = defaultdict(list)
    undated: list[Match] = []
    for match in bucket:
        if match.season is None:
            undated.append(match)
        else:
            by_season[match.season].append(match)
    groups = [by_season[season] for season in sorted(by_season)]
    groups.extend(_group_by_date_proximity(undated))
    return groups


def _group_by_date_proximity(bucket: list[Match]) -> list[list[Match]]:
    """Split a bucket wherever consecutive dates are more than the window apart."""

    groups: list[list[Match]] = []
    group: list[Match] = []
    anchor: dt.date | None = None
    for match in bucket:
        if group and (
            match.date is None or anchor is None or match.date - anchor > _DUPLICATE_WINDOW
        ):
            groups.append(group)
            group = []
            anchor = None
        group.append(match)
        if anchor is None:
            anchor = match.date
    if group:
        groups.append(group)
    return groups


class KnowledgeGraph:
    """Nodes, typed edges and the indexes the query layer relies on."""

    def __init__(self, registry: TeamRegistry, matches: list[Match],
                 players: list[Player], report: LoadReport) -> None:
        self.registry = registry
        self.matches = matches
        self.players = players
        self.report = report
        self.competitions: tuple[Competition, ...] = COMPETITIONS
        self.competitions_by_id = {comp.id: comp for comp in COMPETITIONS}
        self.derbies = DERBIES

        self.teams: dict[str, Team] = dict(registry.teams)

        # -- graph storage --------------------------------------------------
        self._nodes: dict[str, dict[str, Any]] = {}
        self._out: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self._in: dict[str, list[tuple[str, str]]] = defaultdict(list)

        # -- indexes --------------------------------------------------------
        self.matches_by_id: dict[str, Match] = {}
        self.matches_by_team: dict[str, list[Match]] = defaultdict(list)
        self.matches_by_competition: dict[str, list[Match]] = defaultdict(list)
        self.matches_by_competition_season: dict[tuple[str, int], list[Match]] = defaultdict(list)
        self.team_competitions: dict[str, set[str]] = defaultdict(set)
        self.team_seasons: dict[str, set[int]] = defaultdict(set)
        self.players_by_id: dict[int, Player] = {}
        self.players_by_club_team: dict[str, list[Player]] = defaultdict(list)
        self.players_by_nationality: dict[str, list[Player]] = defaultdict(list)
        self.players_by_name: dict[str, list[Player]] = defaultdict(list)
        self.venues: dict[str, str] = {}

        self._build()

    # -- construction ------------------------------------------------------
    def _add_node(self, node_id: str, node_type: str, label: str, **props: Any) -> None:
        if node_id not in self._nodes:
            self._nodes[node_id] = {"id": node_id, "type": node_type, "label": label, **props}

    def _add_edge(self, source: str, relation: str, target: str) -> None:
        self._out[source].append((relation, target))
        self._in[target].append((relation, source))

    def _build(self) -> None:
        for competition in self.competitions:
            self._add_node(f"competition:{competition.id}", "competition", competition.name,
                           kind=competition.kind, short_name=competition.short_name)

        for team in self.teams.values():
            self._add_node(f"team:{team.id}", "team", team.display_name,
                           state=team.state, country=team.country)

        for match in self.matches:
            match_node = f"match:{match.id}"
            self.matches_by_id[match.id] = match
            label = (
                f"{match.home_team_raw} {match.home_goals}-{match.away_goals} "
                f"{match.away_team_raw}"
            )
            self._add_node(match_node, "match", label,
                           date=match.date.isoformat() if match.date else None,
                           season=match.season, competition=match.competition_id)
            self._add_edge(match_node, "home_team", f"team:{match.home_team_id}")
            self._add_edge(match_node, "away_team", f"team:{match.away_team_id}")
            self._add_edge(match_node, "in_competition", f"competition:{match.competition_id}")

            self.matches_by_team[match.home_team_id].append(match)
            self.matches_by_team[match.away_team_id].append(match)
            self.matches_by_competition[match.competition_id].append(match)
            if match.season is not None:
                key = (match.competition_id, match.season)
                self.matches_by_competition_season[key].append(match)
                season_node = f"season:{match.competition_id}:{match.season}"
                self._add_node(season_node, "season",
                               f"{self.competition_name(match.competition_id)} {match.season}",
                               season=match.season, competition=match.competition_id)
                self._add_edge(season_node, "of_competition",
                               f"competition:{match.competition_id}")
                self._add_edge(match_node, "in_season", season_node)
            for team_id in (match.home_team_id, match.away_team_id):
                self.team_competitions[team_id].add(match.competition_id)
                if match.season is not None:
                    self.team_seasons[team_id].add(match.season)
            if match.venue:
                venue_id = slugify(match.venue)
                if venue_id:
                    self.venues[venue_id] = match.venue
                    self._add_node(f"venue:{venue_id}", "venue", match.venue)
                    self._add_edge(match_node, "played_at", f"venue:{venue_id}")

        for team_id, competition_ids in self.team_competitions.items():
            for competition_id in competition_ids:
                self._add_edge(f"team:{team_id}", "competed_in",
                               f"competition:{competition_id}")

        linked = 0
        for player in self.players:
            node_id = f"player:{player.id}"
            self.players_by_id[player.id] = player
            self._add_node(node_id, "player", player.name,
                           nationality=player.nationality, overall=player.overall,
                           club=player.club_raw)
            self.players_by_name[normalize_name(player.name)].append(player)
            if player.nationality:
                self.players_by_nationality[normalize_name(player.nationality)].append(player)
            if player.club_team_id:
                linked += 1
                self.players_by_club_team[player.club_team_id].append(player)
                self._add_edge(node_id, "plays_for", f"team:{player.club_team_id}")
        self.report.linked_player_clubs = linked
        self.report.teams = len(self.teams)
        self.report.players = len(self.players)
        self.report.matches_after_merge = len(self.matches)

        for matches in self.matches_by_team.values():
            matches.sort(key=lambda m: (m.date or dt.date(1, 1, 1), m.id))

    # -- graph API ---------------------------------------------------------
    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._out.values())

    def node(self, node_id: str) -> dict[str, Any] | None:
        return self._nodes.get(node_id)

    def nodes_of_type(self, node_type: str) -> Iterator[dict[str, Any]]:
        return (node for node in self._nodes.values() if node["type"] == node_type)

    def neighbors(self, node_id: str, relation: str | None = None,
                  direction: str = "out") -> list[tuple[str, str]]:
        """Return ``(relation, node_id)`` pairs adjacent to ``node_id``."""

        if direction == "out":
            edges = self._out.get(node_id, [])
        elif direction == "in":
            edges = self._in.get(node_id, [])
        elif direction == "both":
            edges = [*self._out.get(node_id, []), *self._in.get(node_id, [])]
        else:  # pragma: no cover - programming error
            raise ValueError(f"direction must be out/in/both, got {direction!r}")
        if relation is None:
            return list(edges)
        return [edge for edge in edges if edge[0] == relation]

    def graph_schema(self) -> dict[str, Any]:
        """Node/edge type counts -- surfaced by the ``graph_schema`` MCP tool."""

        node_types: dict[str, int] = defaultdict(int)
        for node in self._nodes.values():
            node_types[node["type"]] += 1
        edge_types: dict[str, int] = defaultdict(int)
        for edges in self._out.values():
            for relation, _ in edges:
                edge_types[relation] += 1
        return {
            "nodes": dict(sorted(node_types.items())),
            "edges": dict(sorted(edge_types.items())),
            "node_count": self.node_count,
            "edge_count": self.edge_count,
        }

    # -- convenience -------------------------------------------------------
    def competition_name(self, competition_id: str) -> str:
        competition = self.competitions_by_id.get(competition_id)
        return competition.name if competition else competition_id

    def team_name(self, team_id: str) -> str:
        team = self.teams.get(team_id)
        return team.display_name if team else team_id

    def team_names(self) -> dict[str, str]:
        return {team_id: team.display_name for team_id, team in self.teams.items()}

    def seasons_for(self, competition_id: str) -> list[int]:
        return sorted(
            season for (comp, season) in self.matches_by_competition_season
            if comp == competition_id
        )

    def active_teams(self) -> list[Team]:
        """Teams that actually appear in at least one match."""

        return [self.teams[team_id] for team_id in self.matches_by_team if team_id in self.teams]


def build_knowledge_graph() -> KnowledgeGraph:
    """Read every CSV and construct a fresh knowledge graph."""

    started = time.perf_counter()
    report = LoadReport(missing_files=missing_datasets())

    parsed = read_all_match_rows()
    for key, rows in parsed.items():
        report.rows_by_dataset[key] = len(rows)

    registry = TeamRegistry()
    rejected: list = []
    raw_matches = load_matches(registry, parsed, rejected=rejected)
    matches, duplicates = deduplicate(raw_matches)
    report.merged_duplicates = duplicates
    report.rejected_rows = len(rejected)

    # FIFA 19 only ships top-division squads, so a club may only claim players
    # if it has played in Serie A somewhere in the match data.
    top_flight = {
        team_id
        for match in matches if match.competition_id == "serie-a"
        for team_id in (match.home_team_id, match.away_team_id)
    }
    players = load_players(registry, top_flight)
    report.rows_by_dataset["fifa_players"] = len(players)

    graph = KnowledgeGraph(registry, matches, players, report)
    report.load_seconds = time.perf_counter() - started
    return graph


_CACHED_GRAPH: KnowledgeGraph | None = None
_CACHED_SIGNATURE: tuple | None = None


def _data_signature() -> tuple:
    from .config import dataset_path

    signature = []
    for spec in DATASETS:
        path = dataset_path(spec.key)
        try:
            stat = path.stat()
            signature.append((spec.key, stat.st_size, int(stat.st_mtime)))
        except OSError:
            signature.append((spec.key, None, None))
    return tuple(signature)


def load_knowledge_graph(*, refresh: bool = False) -> KnowledgeGraph:
    """Return the process-wide knowledge graph, building it on first use.

    The cache key includes each CSV's size and mtime so pointing
    ``BRAZILIAN_SOCCER_DATA_DIR`` at different data (as the tests do) rebuilds
    automatically instead of returning a stale graph.
    """

    global _CACHED_GRAPH, _CACHED_SIGNATURE
    signature = _data_signature()
    if refresh or _CACHED_GRAPH is None or _CACHED_SIGNATURE != signature:
        _CACHED_GRAPH = build_knowledge_graph()
        _CACHED_SIGNATURE = signature
    return _CACHED_GRAPH
