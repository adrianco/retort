"""The in-memory knowledge graph.

Context
-------
The server answers natural language questions by traversing a graph whose nodes
are *teams*, *players*, *matches*, *competitions*, *seasons*, *venues*, *states*
and *countries*, connected by relations such as ``played_home``, ``competed_in``,
``plays_for`` and ``based_in``.  Node ids are namespaced (``team:flamengo``,
``match:serie-a:2019:flamengo:santos``) and :meth:`KnowledgeGraph.neighbours`
walks the edges, so a client can explore the graph generically as well as call
the purpose built query functions in :mod:`brazilian_soccer.queries`.

Adjacency is derived from compact indexes rather than a materialised edge table:
16 700 matches x 6 relations would cost far more memory than the handful of
dicts kept here, and every query the specification asks for is either "matches
of a team", "matches of a competition season" or a full scan.

Cross-file linking lives here too.  FIFA clubs are matched to match-data teams
through the same name resolver, but a link is only kept when the squad is
majority Brazilian -- that is what stops FIFA's "Inter" (Internazionale) from
being wired to Internacional of Porto Alegre.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from .loaders import (
    DATA_FILES,
    collect_spellings,
    default_data_dir,
    load_matches,
    load_players,
    merge_matches,
)
from .models import Match, Player
from .names import (
    CLUBS,
    UF_STATES,
    Competition,
    competition_by_id,
    known_club,
    normalize_query,
    resolve_competition,
    resolve_team,
    search_clubs,
)

__all__ = ["KnowledgeGraph", "TeamNode", "load_graph"]


@dataclass(slots=True)
class TeamNode:
    """A club as seen by the graph, plus the spellings that mapped onto it."""

    id: str
    name: str
    state: str | None = None
    country: str = "Brazil"
    known: bool = False
    spellings: Counter = field(default_factory=Counter)
    competitions: set[str] = field(default_factory=set)
    seasons: set[int] = field(default_factory=set)
    match_count: int = 0

    @property
    def state_name(self) -> str | None:
        return UF_STATES.get(self.state or "")

    @property
    def display(self) -> str:
        if self.state and not self.name.endswith(f"-{self.state}"):
            return f"{self.name} ({self.state})"
        return self.name

    def to_dict(self) -> dict[str, object]:
        return {
            "team_id": self.id,
            "name": self.name,
            "state": self.state,
            "state_name": self.state_name,
            "country": self.country,
            "matches": self.match_count,
            "competitions": sorted(self.competitions),
            "seasons": sorted(self.seasons),
            "known_spellings": [name for name, _ in self.spellings.most_common()],
        }


class KnowledgeGraph:
    """Nodes, edges and indexes over the six Kaggle files."""

    def __init__(
        self,
        matches: Sequence[Match],
        players: Sequence[Player],
        spellings: dict[str, Counter] | None = None,
        dropped_rows: dict[str, int] | None = None,
    ) -> None:
        self.matches: list[Match] = list(matches)
        self.players: list[Player] = list(players)
        self._source_spellings = spellings or {}
        #: Source rows the loader refused, so the overview can own up to them.
        self.dropped_rows = {k: v for k, v in (dropped_rows or {}).items() if v}

        self.matches_by_id: dict[str, Match] = {}
        self.teams: dict[str, TeamNode] = {}
        self.matches_by_team: dict[str, list[str]] = defaultdict(list)
        self.matches_by_competition: dict[str, list[str]] = defaultdict(list)
        self.matches_by_competition_season: dict[tuple[str, int | None], list[str]] = defaultdict(list)
        self.matches_by_venue: dict[str, list[str]] = defaultdict(list)
        self.seasons_by_competition: dict[str, set[int]] = defaultdict(set)

        self.players_by_id: dict[int, Player] = {}
        self.players_by_team: dict[str, list[int]] = defaultdict(list)
        self.players_by_nationality: dict[str, list[int]] = defaultdict(list)
        self.club_links: dict[str, str] = {}  # FIFA club name -> team id

        self._team_lookup: dict[str, str] = {}  # normalised text -> team id
        #: Scratch space for derived results that are expensive to recompute
        #: (e.g. the champion of every Série A season).
        self.cache: dict[str, Any] = {}
        self._build_matches()
        self._build_players()

    # -- construction ----------------------------------------------------
    @classmethod
    def load(cls, data_dir: Path | str | None = None) -> "KnowledgeGraph":
        """Build the graph from the CSVs in *data_dir*."""
        directory = Path(data_dir) if data_dir else default_data_dir()
        raw_matches = load_matches(directory)
        impossible = sum(1 for match in raw_matches if match.home_team == match.away_team)
        return cls(
            merge_matches(raw_matches),
            load_players(directory),
            spellings=collect_spellings(raw_matches),
            dropped_rows={"club listed as its own opponent": impossible},
        )

    def _team_node(self, team_id: str, name: str, state: str | None, country: str,
                   known: bool) -> TeamNode:
        node = self.teams.get(team_id)
        if node is None:
            node = TeamNode(id=team_id, name=name, state=state, country=country, known=known)
            self.teams[team_id] = node
        return node

    def _build_matches(self) -> None:
        for match in self.matches:
            self.matches_by_id[match.match_id] = match
            competition_key = (match.competition_id, match.season)
            self.matches_by_competition[match.competition_id].append(match.match_id)
            self.matches_by_competition_season[competition_key].append(match.match_id)
            if match.season is not None:
                self.seasons_by_competition[match.competition_id].add(match.season)
            if match.venue:
                self.matches_by_venue[match.venue].append(match.match_id)

            for team_id, name in (
                (match.home_team, match.home_team_name),
                (match.away_team, match.away_team_name),
            ):
                club = known_club(team_id)
                node = self._team_node(
                    team_id,
                    club.name if club else name,
                    club.state if club else None,
                    club.country if club else "Brazil",
                    club is not None,
                )
                if not self._source_spellings:
                    node.spellings[name] += 1
                node.competitions.add(match.competition)
                if match.season is not None:
                    node.seasons.add(match.season)
                node.match_count += 1
                self.matches_by_team[team_id].append(match.match_id)

        for node in self.teams.values():
            spellings = self._source_spellings.get(node.id)
            if spellings:
                node.spellings.update(spellings)
            # Unregistered clubs display their most common spelling.
            if not node.known and node.spellings:
                node.name = node.spellings.most_common(1)[0][0]

        for node in self.teams.values():
            self._team_lookup.setdefault(normalize_query(node.name), node.id)
            self._team_lookup.setdefault(node.id, node.id)
            for spelling in node.spellings:  # every raw variant resolves too
                self._team_lookup.setdefault(normalize_query(spelling), node.id)
        for club in CLUBS:  # registry aliases resolve even for absent clubs
            if club.id in self.teams:
                for alias in (club.name, *club.aliases, *club.nicknames):
                    self._team_lookup.setdefault(normalize_query(alias), club.id)

    def _build_players(self) -> None:
        by_club: dict[str, list[Player]] = defaultdict(list)
        for player in self.players:
            self.players_by_id[player.player_id] = player
            if player.nationality:
                self.players_by_nationality[normalize_query(player.nationality)].append(
                    player.player_id
                )
            if player.club:
                by_club[player.club].append(player)

        for club_name, squad in by_club.items():
            reference = resolve_team(club_name)
            node = self.teams.get(reference.id)
            if node is None or reference.country != "Brazil":
                continue
            brazilians = sum(1 for player in squad if player.nationality == "Brazil")
            if brazilians / len(squad) < 0.5:
                # "Inter" in FIFA is Internazionale, not Internacional-RS.
                continue
            self.club_links[club_name] = reference.id
            for player in squad:
                player.club_team_id = reference.id
                self.players_by_team[reference.id].append(player.player_id)

    # -- team lookup -----------------------------------------------------
    def team(self, team_id: str) -> TeamNode | None:
        return self.teams.get(team_id)

    def find_team(self, text: str) -> TeamNode | None:
        """Resolve free text ("fla", "Palmeiras-SP", "Timão") to a team node."""
        if not text:
            return None
        needle = normalize_query(text)
        if needle in self._team_lookup:
            return self.teams[self._team_lookup[needle]]
        reference = resolve_team(text)
        node = self.teams.get(reference.id)
        if node is not None:
            return node
        for club in search_clubs(text, limit=1):
            if club.id in self.teams:
                return self.teams[club.id]
        candidates = [
            node
            for key, team_id in self._team_lookup.items()
            if needle and needle in key and (node := self.teams.get(team_id))
        ]
        if candidates:
            candidates.sort(key=lambda item: (-item.match_count, item.name))
            return candidates[0]
        return None

    def suggest_teams(self, text: str, limit: int = 8) -> list[TeamNode]:
        """Teams whose name or alias contains *text*, most active first."""
        needle = normalize_query(text)
        if not needle:
            return []
        seen: dict[str, TeamNode] = {}
        for key, team_id in self._team_lookup.items():
            if needle in key and team_id in self.teams:
                seen.setdefault(team_id, self.teams[team_id])
        for club in search_clubs(text, limit=limit):
            if club.id in self.teams:
                seen.setdefault(club.id, self.teams[club.id])
        ranked = sorted(seen.values(), key=lambda node: (-node.match_count, node.name))
        return ranked[:limit]

    # -- competitions ----------------------------------------------------
    def competition(self, text: str | None) -> Competition | None:
        return resolve_competition(text)

    def competition_ids(self) -> list[str]:
        return sorted(self.matches_by_competition)

    def seasons(self, competition_id: str | None = None) -> list[int]:
        if competition_id:
            return sorted(self.seasons_by_competition.get(competition_id, ()))
        seasons: set[int] = set()
        for values in self.seasons_by_competition.values():
            seasons |= values
        return sorted(seasons)

    def competition_name(self, competition_id: str) -> str:
        competition = competition_by_id(competition_id)
        return competition.name if competition else competition_id

    # -- match access ----------------------------------------------------
    def team_matches(self, team_id: str) -> list[Match]:
        return [self.matches_by_id[mid] for mid in self.matches_by_team.get(team_id, ())]

    def competition_matches(
        self, competition_id: str, season: int | None = None
    ) -> list[Match]:
        if season is None:
            ids = self.matches_by_competition.get(competition_id, ())
        else:
            ids = self.matches_by_competition_season.get((competition_id, season), ())
        return [self.matches_by_id[mid] for mid in ids]

    # -- player access ---------------------------------------------------
    def team_players(self, team_id: str) -> list[Player]:
        return [self.players_by_id[pid] for pid in self.players_by_team.get(team_id, ())]

    def nationality_players(self, nationality: str) -> list[Player]:
        ids = self.players_by_nationality.get(normalize_query(nationality), ())
        return [self.players_by_id[pid] for pid in ids]

    # -- generic graph traversal -----------------------------------------
    def node(self, node_id: str) -> dict[str, object] | None:
        """Return a description of a namespaced node id."""
        kind, _, key = node_id.partition(":")
        if kind == "team":
            node = self.teams.get(key)
            return {"kind": "team", **node.to_dict()} if node else None
        if kind == "match":
            match = self.matches_by_id.get(key)
            return {"kind": "match", **match.to_dict()} if match else None
        if kind == "player":
            player = self.players_by_id.get(int(key)) if key.isdigit() else None
            return {"kind": "player", **player.to_dict()} if player else None
        if kind == "competition":
            competition = competition_by_id(key)
            if competition is None:
                return None
            return {
                "kind": "competition",
                "id": competition.id,
                "name": competition.name,
                "type": competition.kind,
                "seasons": self.seasons(competition.id),
            }
        if kind == "season" and key.isdigit():
            return {"kind": "season", "year": int(key)}
        if kind == "venue":
            return {"kind": "venue", "name": key, "matches": len(self.matches_by_venue.get(key, ()))}
        if kind == "state":
            return {"kind": "state", "code": key, "name": UF_STATES.get(key)}
        if kind == "country":
            return {"kind": "country", "name": key}
        return None

    def neighbours(self, node_id: str, relation: str | None = None) -> dict[str, list[str]]:
        """Adjacent node ids grouped by relation name."""
        kind, _, key = node_id.partition(":")
        edges: dict[str, list[str]] = {}

        if kind == "team":
            node = self.teams.get(key)
            if node is None:
                return {}
            home, away, competitions, seasons = [], [], set(), set()
            for match in self.team_matches(key):
                (home if match.home_team == key else away).append(f"match:{match.match_id}")
                competitions.add(f"competition:{match.competition_id}")
                if match.season is not None:
                    seasons.add(f"season:{match.season}")
            edges = {
                "played_home": home,
                "played_away": away,
                "competed_in": sorted(competitions),
                "active_in": sorted(seasons),
                "squad": [f"player:{pid}" for pid in self.players_by_team.get(key, ())],
            }
            if node.state:
                edges["based_in"] = [f"state:{node.state}"]
            edges["from_country"] = [f"country:{node.country}"]

        elif kind == "match":
            match = self.matches_by_id.get(key)
            if match is None:
                return {}
            edges = {
                "home_team": [f"team:{match.home_team}"],
                "away_team": [f"team:{match.away_team}"],
                "part_of": [f"competition:{match.competition_id}"],
            }
            if match.season is not None:
                edges["in_season"] = [f"season:{match.season}"]
            if match.venue:
                edges["played_at"] = [f"venue:{match.venue}"]
            if match.winner_id:
                edges["won_by"] = [f"team:{match.winner_id}"]

        elif kind == "player":
            player = self.players_by_id.get(int(key)) if key.isdigit() else None
            if player is None:
                return {}
            edges = {"nationality": [f"country:{player.nationality}"]}
            if player.club_team_id:
                edges["plays_for"] = [f"team:{player.club_team_id}"]

        elif kind == "competition":
            ids = self.matches_by_competition.get(key, ())
            edges = {
                "seasons": [f"season:{year}" for year in self.seasons(key)],
                "matches": [f"match:{mid}" for mid in ids],
            }

        elif kind == "season" and key.isdigit():
            year = int(key)
            edges = {
                "competitions": [
                    f"competition:{competition_id}"
                    for competition_id, years in self.seasons_by_competition.items()
                    if year in years
                ]
            }

        elif kind == "venue":
            edges = {"hosted": [f"match:{mid}" for mid in self.matches_by_venue.get(key, ())]}

        elif kind == "state":
            edges = {
                "teams": [f"team:{node.id}" for node in self.teams.values() if node.state == key]
            }

        elif kind == "country":
            edges = {
                "teams": [f"team:{node.id}" for node in self.teams.values() if node.country == key]
            }

        if relation is not None:
            return {relation: edges.get(relation, [])}
        return {name: values for name, values in edges.items() if values}

    # -- summary ---------------------------------------------------------
    def stats(self) -> dict[str, object]:
        played = [match for match in self.matches if match.played]
        goals = sum(match.total_goals or 0 for match in played)
        home_wins = sum(1 for match in played if match.result == "home")
        draws = sum(1 for match in played if match.result == "draw")
        dates = [match.date for match in self.matches if match.date]
        return {
            "matches": len(self.matches),
            "matches_with_scores": len(played),
            "teams": len(self.teams),
            "players": len(self.players),
            "competitions": len(self.matches_by_competition),
            "venues": len(self.matches_by_venue),
            "linked_fifa_clubs": len(self.club_links),
            "goals": goals,
            "goals_per_match": round(goals / len(played), 2) if played else 0.0,
            "home_win_rate": round(home_wins / len(played) * 100, 1) if played else 0.0,
            "draw_rate": round(draws / len(played) * 100, 1) if played else 0.0,
            "date_range": [min(dates).isoformat(), max(dates).isoformat()] if dates else [],
            "source_files": dict(DATA_FILES),
            "dropped_rows": dict(self.dropped_rows),
        }


def load_graph(data_dir: Path | str | None = None) -> KnowledgeGraph:
    """Convenience wrapper around :meth:`KnowledgeGraph.load`."""
    return KnowledgeGraph.load(data_dir)
