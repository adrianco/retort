"""The Brazilian football knowledge graph.

Context
-------
This module turns the six CSV files into a single in-memory graph:

    Team  --(played home / played away)-->  Match  --(part of)-->  Competition
      ^                                                                |
      |                                                             (season)
      +--(has squad member)-->  Player

Two things make it more than a pile of lists:

*Deduplication.*  The same Série A fixture is present in up to three of the
provided files.  Naively concatenating them would double the goals in every
aggregate and produce nonsense standings.  Fixtures are therefore matched on
``(competition, home_slug, away_slug)`` plus a +/-5 day date window -- which is
exact for a double round robin, where an ordered pair meets once per season --
and merged into a single :class:`~brazilian_soccer.models.Match` that carries
the union of all the columns (round numbers from one file, the stadium from
another, shot/corner statistics from a third).

*Indexing.*  Every query the MCP tools need is answered from a precomputed
adjacency index, so a lookup is a dict access rather than a scan of 30k rows.
The whole graph is built once and cached at module level, keeping simple
lookups far inside the 2 second budget from the specification.
"""

from __future__ import annotations

import datetime as _dt
import difflib
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .clubs import alternatives_for, profile_for, resolve_club
from .competitions import COMPETITIONS
from .loaders import SOURCES, default_data_dir, load_players
from .models import Match, Player, Team
from .normalization import BRAZILIAN_STATES, normalize_text, slugify

__all__ = ["KnowledgeGraph", "TeamResolution", "load_graph", "clear_cache"]


#: How far apart two records of the same fixture may be dated and still be
#: considered the same match.  Sources disagree by a day or two because of
#: late kick-offs and time zones.
MERGE_WINDOW_DAYS = 5

#: A repeated fixture *inside one file* is only treated as a duplicate when the
#: two rows are this close together; anything further apart is a replay.
SAME_FILE_WINDOW_DAYS = 2


@dataclass(frozen=True)
class TeamResolution:
    """Outcome of looking a team name up in the graph."""

    slug: str | None
    team: Team | None
    matched: bool
    query: str
    #: Other clubs the query could plausibly have meant.
    alternatives: tuple[str, ...] = ()
    #: Human readable explanation, used when ``matched`` is False.
    message: str = ""

    @property
    def name(self) -> str:
        return self.team.name if self.team else self.query


@dataclass
class BuildReport:
    """Diagnostics produced while assembling the graph."""

    rows_read: dict[str, int] = field(default_factory=dict)
    merged_rows: int = 0
    discarded_rows: int = 0
    unique_matches: int = 0
    players: int = 0
    build_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "rows_read": dict(self.rows_read),
            "merged_duplicate_rows": self.merged_rows,
            "discarded_invalid_rows": self.discarded_rows,
            "unique_matches": self.unique_matches,
            "players": self.players,
            "build_seconds": round(self.build_seconds, 3),
        }


class KnowledgeGraph:
    """Deduplicated, indexed view over the provided datasets."""

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.teams: dict[str, Team] = {}
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self.report = BuildReport()

        # --- adjacency indexes -------------------------------------------
        self.matches_by_team: dict[str, list[Match]] = defaultdict(list)
        self.matches_by_pair: dict[frozenset, list[Match]] = defaultdict(list)
        self.matches_by_competition: dict[str, list[Match]] = defaultdict(list)
        self.matches_by_comp_season: dict[tuple[str, int], list[Match]] = defaultdict(list)
        self.players_by_club: dict[str, list[Player]] = defaultdict(list)
        self.players_by_nationality: dict[str, list[Player]] = defaultdict(list)
        self.seasons_by_competition: dict[str, set[int]] = defaultdict(set)
        self._name_index: dict[str, str] = {}
        self._teams_by_base: dict[str, list[str]] = {}

        self._build()

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    def _build(self) -> None:
        started = time.perf_counter()
        merged_index: dict[tuple[str, str, str], list[Match]] = defaultdict(list)
        # Raw spellings are collected here rather than after merging, because
        # merging discards the duplicate rows that carry the alternatives.
        spellings: dict[str, set[str]] = defaultdict(set)

        for source in SOURCES:
            if source.kind != "matches":
                continue
            rows = source.loader(self.data_dir)
            self.report.rows_read[source.filename] = len(rows)
            for match in rows:
                if not match.home_slug or match.home_slug == match.away_slug:
                    # The Copa do Brasil file contains two rows listing
                    # "Bragantino - PA" as both sides; a club cannot play
                    # itself, so these are dropped rather than reported.
                    self.report.discarded_rows += 1
                    continue
                spellings[match.home_slug].add(match.home_raw or match.home_name)
                spellings[match.away_slug].add(match.away_raw or match.away_name)
                key = (match.competition, match.home_slug, match.away_slug)
                target = self._find_mergeable(merged_index[key], match)
                if target is None:
                    merged_index[key].append(match)
                    self.matches.append(match)
                else:
                    self._merge_into(target, match)
                    self.report.merged_rows += 1

        self.matches.sort(key=lambda m: (m.date or _dt.date.min, m.match_id))
        self.report.unique_matches = len(self.matches)

        for match in self.matches:
            self._register_team(match.home_slug, match.home_name,
                                spellings.get(match.home_slug, ()))
            self._register_team(match.away_slug, match.away_name,
                                spellings.get(match.away_slug, ()))
            self.matches_by_team[match.home_slug].append(match)
            self.matches_by_team[match.away_slug].append(match)
            self.matches_by_pair[frozenset({match.home_slug, match.away_slug})].append(match)
            self.matches_by_competition[match.competition].append(match)
            if match.season is not None:
                self.matches_by_comp_season[(match.competition, match.season)].append(match)
                self.seasons_by_competition[match.competition].add(match.season)

        self.players = load_players(self.data_dir)
        self.report.players = len(self.players)
        self.report.rows_read["fifa_data.csv"] = len(self.players)
        self._separate_foreign_namesakes()
        for player in self.players:
            if player.club_slug:
                self.players_by_club[player.club_slug].append(player)
            if player.nationality:
                self.players_by_nationality[normalize_text(player.nationality)].append(player)

        for bucket in self.players_by_club.values():
            bucket.sort(key=lambda p: (-(p.overall or 0), p.name))

        self._build_name_index()
        self.report.build_seconds = time.perf_counter() - started

    def _find_mergeable(self, candidates: list[Match], incoming: Match) -> Match | None:
        """Return an already-loaded fixture that *incoming* duplicates.

        Candidates already share ``(competition, home, away)``.  Two rules
        decide whether they are the same fixture:

        *Leagues* (Série A/B/C) are double round robins, so an ordered pair
        meets exactly once per season -- agreeing on the season is proof
        enough, which matters because sources disagree by weeks about
        postponed games.

        *Cups* can pair the same two clubs twice in one edition with the same
        home side (Libertadores group stage plus a knockout tie), so there we
        insist the dates are within :data:`MERGE_WINDOW_DAYS` and pick the
        closest one.
        """
        is_league = incoming.competition.startswith("serie-")
        best: Match | None = None
        best_distance = float("inf")
        for candidate in candidates:
            same_file = incoming.sources[0] in candidate.sources
            if same_file and not (candidate.date and incoming.date
                                  and abs((candidate.date - incoming.date).days)
                                  <= SAME_FILE_WINDOW_DAYS):
                # Within one file a repeated fixture is normally a genuine
                # replay (or a second leg) and must be kept.  Only rows a day
                # or two apart are the same game recorded twice -- which
                # BR-Football does for a handful of late kick-offs.
                continue
            same_season = (candidate.season is not None
                           and incoming.season is not None
                           and candidate.season == incoming.season)
            conflicting_season = (candidate.season is not None
                                  and incoming.season is not None
                                  and candidate.season != incoming.season)
            if conflicting_season:
                continue
            if candidate.date and incoming.date:
                distance = abs((candidate.date - incoming.date).days)
                if distance > MERGE_WINDOW_DAYS and not (is_league and same_season):
                    continue
            elif same_season:
                distance = MERGE_WINDOW_DAYS
            else:
                continue
            if distance < best_distance:
                best, best_distance = candidate, distance
        return best

    @staticmethod
    def _merge_into(target: Match, extra: Match) -> None:
        """Fold the columns *extra* contributes into the authoritative match."""
        for attribute in ("round", "stage", "venue", "kickoff", "season", "date"):
            if getattr(target, attribute) is None:
                setattr(target, attribute, getattr(extra, attribute))
        if target.home_goals is None and extra.home_goals is not None:
            target.home_goals = extra.home_goals
            target.away_goals = extra.away_goals
        for side, values in extra.stats.items():
            target.stats.setdefault(side, {}).update(values)
        target.sources = tuple(dict.fromkeys(target.sources + extra.sources))

    def _separate_foreign_namesakes(self) -> None:
        """Stop foreign clubs from being joined onto same-named Brazilian ones.

        ``Boavista FC`` (Portugal) and ``Boavista`` (Rio de Janeiro) normalise
        to the same base name, as do ``FC Barcelona`` and the Ecuadorian
        ``Barcelona``.  Rather than hand-maintaining an exclusion list we use
        the data: a FIFA club that shares a slug with a club in the match
        datasets but whose squad is mostly *not* Brazilian cannot be the
        Brazilian club, so it is given its own slug derived from its raw name.
        """
        by_raw_club: dict[str, list[Player]] = defaultdict(list)
        for player in self.players:
            if player.club and player.club_slug:
                by_raw_club[player.club].append(player)

        for raw, squad in by_raw_club.items():
            slug = squad[0].club_slug
            if slug not in self.teams:
                continue
            brazilians = sum(1 for p in squad if p.is_brazilian)
            if brazilians * 2 >= len(squad):
                continue  # majority Brazilian: the join is genuine
            replacement = slugify(raw) or f"{slug}-intl"
            if replacement == slug:
                replacement = f"{slug}-intl"
            for player in squad:
                player.club_slug = replacement

    def _register_team(self, slug: str, name: str,
                       spellings: Iterable[str] = ()) -> None:
        team = self.teams.get(slug)
        if team is None:
            profile = profile_for(slug)
            identity = resolve_club(name)
            team = Team(
                slug=slug,
                name=profile.name if profile else identity.name,
                state=profile.state if profile else identity.state,
                known=profile is not None,
            )
            self.teams[slug] = team
        team.aliases.update(s for s in spellings if s)

    @staticmethod
    def _slug_base(slug: str) -> str:
        """``botafogo-rj`` -> ``botafogo``; ``sao-paulo`` stays as it is."""
        head, _, tail = slug.rpartition("-")
        return head if head and tail in BRAZILIAN_STATES else slug

    def namesakes(self, slug: str) -> tuple[str, ...]:
        """Other loaded clubs whose name differs only by state.

        This is what lets a caller be warned that ``Botafogo`` could also mean
        Botafogo-PB or Botafogo-SP even when the query already carried a state
        suffix and therefore resolved unambiguously.
        """
        siblings = self._teams_by_base.get(self._slug_base(slug), ())
        return tuple(s for s in siblings if s != slug)

    def _build_name_index(self) -> None:
        """Index normalised display names and aliases for fuzzy lookups."""
        for slug in self.teams:
            self._teams_by_base.setdefault(self._slug_base(slug), []).append(slug)
        for base, slugs in self._teams_by_base.items():
            slugs.sort(key=lambda s: -len(self.matches_by_team.get(s, ())))
        for slug, team in self.teams.items():
            for label in {team.name, slug.replace("-", " "), *team.aliases}:
                key = normalize_text(label)
                if key:
                    self._name_index.setdefault(key, slug)
            profile = profile_for(slug)
            if profile:
                for label in (*profile.aliases, *profile.nicknames):
                    key = normalize_text(label)
                    if key:
                        self._name_index.setdefault(key, slug)

    # ------------------------------------------------------------------
    # lookups
    # ------------------------------------------------------------------
    def resolve_team(self, name: str) -> TeamResolution:
        """Resolve a user-supplied team name against the loaded data.

        Tries the curated resolver first, then the observed-alias index, then
        a fuzzy match, so that typos and partial names ("Atletico Min",
        "Corinthans") still land on the right club.
        """
        query = (name or "").strip()
        if not query:
            return TeamResolution(None, None, False, query, message="No team name given.")

        identity = resolve_club(query)
        if identity.slug in self.teams:
            return TeamResolution(identity.slug, self.teams[identity.slug], True, query,
                                  alternatives=self._present(alternatives_for(query)))

        key = normalize_text(query)
        slug = self._name_index.get(key)
        if slug:
            return TeamResolution(slug, self.teams[slug], True, query)

        # Substring match against every known spelling, preferring the club
        # with the most fixtures in the data.
        contains = [s for label, s in self._name_index.items() if key and key in label]
        if contains:
            # Rank by fixture count, then by slug: iterating a set here would
            # make the winner depend on PYTHONHASHSEED, so the same question
            # could get a different club after a server restart.
            ordered = sorted(dict.fromkeys(contains),
                             key=lambda s: (-len(self.matches_by_team[s]), s))
            best = ordered[0]
            return TeamResolution(best, self.teams[best], True, query,
                                  alternatives=self._present(tuple(ordered)))

        close = difflib.get_close_matches(key, list(self._name_index), n=5, cutoff=0.82)
        if close:
            slug = self._name_index[close[0]]
            return TeamResolution(slug, self.teams[slug], True, query,
                                  alternatives=self._present(
                                      tuple(self._name_index[c] for c in close)))

        suggestions = difflib.get_close_matches(key, list(self._name_index), n=5, cutoff=0.5)
        names = [self.teams[self._name_index[s]].name for s in suggestions]
        message = f"No team matching {query!r} in the loaded data."
        if names:
            message += " Did you mean: " + ", ".join(dict.fromkeys(names)) + "?"
        return TeamResolution(None, None, False, query,
                              alternatives=tuple(dict.fromkeys(
                                  self._name_index[s] for s in suggestions)),
                              message=message)

    def _present(self, slugs: Iterable[str]) -> tuple[str, ...]:
        """Keep only the slugs that actually occur in the loaded matches."""
        return tuple(s for s in slugs if s in self.teams)

    def team(self, slug: str) -> Team | None:
        return self.teams.get(slug)

    def team_name(self, slug: str) -> str:
        team = self.teams.get(slug)
        return team.name if team else slug.replace("-", " ").title()

    def matches_for(self, slug: str) -> list[Match]:
        return self.matches_by_team.get(slug, [])

    def matches_between(self, slug_a: str, slug_b: str) -> list[Match]:
        return self.matches_by_pair.get(frozenset({slug_a, slug_b}), [])

    def competition_seasons(self, competition: str) -> list[int]:
        return sorted(self.seasons_by_competition.get(competition, ()))

    def squad(self, slug: str) -> list[Player]:
        return self.players_by_club.get(slug, [])

    # ------------------------------------------------------------------
    # summaries
    # ------------------------------------------------------------------
    def summary(self) -> dict:
        """A compact description of everything that was loaded."""
        competitions = []
        for comp in COMPETITIONS:
            fixtures = self.matches_by_competition.get(comp.slug, [])
            if not fixtures:
                continue
            seasons = self.competition_seasons(comp.slug)
            competitions.append({
                "slug": comp.slug,
                "name": comp.name,
                "matches": len(fixtures),
                "seasons": f"{seasons[0]}-{seasons[-1]}" if seasons else None,
                "teams": len({m.home_slug for m in fixtures} | {m.away_slug for m in fixtures}),
            })
        nationalities = sorted(
            ((len(v), k) for k, v in self.players_by_nationality.items()), reverse=True)
        return {
            "data_directory": str(self.data_dir),
            "files": [
                {"file": source.filename,
                 "description": source.description,
                 "rows": self.report.rows_read.get(source.filename, 0)}
                for source in SOURCES
            ],
            "matches": {
                "unique": len(self.matches),
                "source_rows": sum(v for k, v in self.report.rows_read.items()
                                   if k != "fifa_data.csv"),
                "merged_duplicates": self.report.merged_rows,
                "discarded_invalid": self.report.discarded_rows,
            },
            "competitions": competitions,
            "teams": len(self.teams),
            "curated_teams": sum(1 for t in self.teams.values() if t.known),
            "players": len(self.players),
            "brazilian_players": len(self.players_by_nationality.get("brazil", [])),
            "top_nationalities": [
                {"nationality": self.players_by_nationality[key][0].nationality,
                 "players": count}
                for count, key in nationalities[:5]
            ],
            "build_seconds": round(self.report.build_seconds, 3),
        }


# ---------------------------------------------------------------------------
# module level cache
# ---------------------------------------------------------------------------

_CACHE: dict[str, KnowledgeGraph] = {}
_LOCK = threading.Lock()


def load_graph(data_dir: Path | str | None = None) -> KnowledgeGraph:
    """Return the shared graph for *data_dir*, building it on first use."""
    key = str(Path(data_dir).resolve()) if data_dir else str(default_data_dir())
    with _LOCK:
        graph = _CACHE.get(key)
        if graph is None:
            graph = KnowledgeGraph(key)
            _CACHE[key] = graph
        return graph


def clear_cache() -> None:
    """Drop the cached graph (used by tests)."""
    with _LOCK:
        _CACHE.clear()
