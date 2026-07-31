"""
Analytical query API over the knowledge graph.

Context
-------
This module implements the five capability groups TASK.md requires, and is the
only place that knows how to *compute* anything:

1. Match queries      -- :func:`search_matches`, :func:`find_derbies`
2. Team queries       -- :func:`team_record`, :func:`team_profile`,
                         :func:`compare_teams`, :func:`best_records`
3. Player queries     -- :func:`search_players`, :func:`player_profile`,
                         :func:`club_squad`
4. Competition queries-- :func:`standings`, :func:`competition_champion`,
                         :func:`relegated_teams`
5. Statistics         -- :func:`competition_stats`, :func:`biggest_wins`,
                         :func:`head_to_head`, :func:`compare_seasons`

Every public function takes the :class:`~brazilian_soccer.graph.KnowledgeGraph`
as its first argument and returns plain dataclasses/dicts -- rendering lives in
:mod:`brazilian_soccer.formatting` and transport in
:mod:`brazilian_soccer.tools`.

Fuzzy argument handling is deliberate: an LLM will pass "flamengo", "Flamengo
RJ", "Mengão" or "brasileirao" and all of those must work.  When a name cannot
be resolved a :class:`TeamNotFound` / :class:`CompetitionNotFound` is raised
carrying suggestions so the tool layer can answer helpfully instead of failing.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence

from .graph import KnowledgeGraph
from .loaders import POSITION_GROUP_ALIASES, POSITION_GROUPS, position_group
from .models import (
    COMPETITIONS,
    Competition,
    HeadToHead,
    Match,
    Player,
    StandingRow,
    Team,
    TeamRecord,
)
from .text import normalize_name, parse_date, parse_int

__all__ = [
    "TeamNotFound",
    "CompetitionNotFound",
    "resolve_team",
    "resolve_competition",
    "search_matches",
    "head_to_head",
    "team_record",
    "team_profile",
    "compare_teams",
    "standings",
    "competition_champion",
    "relegated_teams",
    "competition_stats",
    "biggest_wins",
    "best_records",
    "top_scoring_teams",
    "search_players",
    "player_profile",
    "club_squad",
    "find_derbies",
    "compare_seasons",
    "dataset_summary",
]


class TeamNotFound(LookupError):
    """Raised when a club name cannot be resolved; carries suggestions."""

    def __init__(self, query: str, suggestions: Sequence[str] = ()) -> None:
        self.query = query
        self.suggestions = list(suggestions)
        message = f"No club matching {query!r}"
        if self.suggestions:
            message += f". Did you mean: {', '.join(self.suggestions)}?"
        super().__init__(message)


class CompetitionNotFound(LookupError):
    """Raised when a competition name cannot be resolved."""

    def __init__(self, query: str, suggestions: Sequence[str] = ()) -> None:
        self.query = query
        self.suggestions = list(suggestions)
        message = f"No competition matching {query!r}"
        if self.suggestions:
            message += f". Known competitions: {', '.join(self.suggestions)}"
        super().__init__(message)


# ---------------------------------------------------------------------------
# Argument resolution
# ---------------------------------------------------------------------------


def resolve_team(graph: KnowledgeGraph, value: str) -> Team:
    """Resolve a user/LLM supplied club name to a canonical :class:`Team`.

    Clubs that actually appear in the match data win over registry-only
    entries, so "Botafogo" resolves to the club with 700+ matches rather than a
    homonym that never played.
    """

    if not value or not str(value).strip():
        raise TeamNotFound(str(value), _sample_team_names(graph))
    value = str(value).strip()
    if value in graph.teams:
        return graph.teams[value]

    candidates = graph.registry.search(value, limit=25)
    if not candidates:
        raise TeamNotFound(value, _sample_team_names(graph))
    # Registry order is by match quality; break ties towards clubs that played.
    return min(candidates, key=lambda team: 0 if graph.matches_by_team.get(team.id) else 1)


def team_suggestions(graph: KnowledgeGraph, value: str, limit: int = 5) -> list[str]:
    return [team.display_name for team in graph.registry.search(str(value or ""), limit=limit)]


def _sample_team_names(graph: KnowledgeGraph, limit: int = 8) -> list[str]:
    ordered = sorted(
        graph.matches_by_team.items(), key=lambda item: -len(item[1])
    )[:limit]
    return [graph.team_name(team_id) for team_id, _ in ordered]


_COMPETITION_LOOKUP: dict[str, str] = {}
for _competition in COMPETITIONS:
    _COMPETITION_LOOKUP[_competition.id] = _competition.id
    _COMPETITION_LOOKUP[normalize_name(_competition.id)] = _competition.id
    _COMPETITION_LOOKUP[normalize_name(_competition.name)] = _competition.id
    _COMPETITION_LOOKUP[normalize_name(_competition.short_name)] = _competition.id
    for _alias in _competition.aliases:
        _COMPETITION_LOOKUP[normalize_name(_alias)] = _competition.id


def resolve_competition(value: str | None) -> Competition | None:
    """Resolve "brasileirao", "Série A", "serie-a", ... to a competition."""

    if value is None or not str(value).strip():
        return None
    key = normalize_name(str(value))
    competition_id = _COMPETITION_LOOKUP.get(key)
    if competition_id is None:
        for known, mapped in _COMPETITION_LOOKUP.items():
            if known and (key in known or known in key):
                competition_id = mapped
                break
    if competition_id is None:
        raise CompetitionNotFound(str(value), [c.name for c in COMPETITIONS])
    return next(c for c in COMPETITIONS if c.id == competition_id)


def _competition_id(value: str | None) -> str | None:
    competition = resolve_competition(value)
    return competition.id if competition else None


def _as_season(value: object) -> int | None:
    return parse_int(value)


#: Public aliases used by the tool layer.
as_season = _as_season
competition_id_of = _competition_id


def _as_date(value: object) -> dt.date | None:
    return parse_date(value)


def _as_scope(value: str | None) -> str:
    """Normalise ``scope``/``home_away`` so "Home" and "HOME" also work."""

    scope = (value or "all").strip().lower()
    return scope if scope in {"all", "home", "away", "any"} else "all"


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------


def search_matches(
    graph: KnowledgeGraph,
    *,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: object = None,
    season_from: object = None,
    season_to: object = None,
    date_from: object = None,
    date_to: object = None,
    venue: str | None = None,
    stage: str | None = None,
    round: str | None = None,
    home_away: str = "any",
    played_only: bool = False,
    limit: int | None = 50,
    order: str = "desc",
) -> list[Match]:
    """Filtered match search -- the workhorse behind most tools.

    ``home_away`` restricts ``team`` to ``"home"``/``"away"``/``"any"``.
    Results are ordered by date (most recent first by default).
    """

    team_obj = resolve_team(graph, team) if team else None
    opponent_obj = resolve_team(graph, opponent) if opponent else None
    competition_id = _competition_id(competition)
    season_value = _as_season(season)
    season_lo = _as_season(season_from)
    season_hi = _as_season(season_to)
    date_lo = _as_date(date_from)
    date_hi = _as_date(date_to)
    home_away = _as_scope(home_away)
    if home_away == "all":
        home_away = "any"
    venue_key = normalize_name(venue) if venue else None
    stage_key = normalize_name(stage) if stage else None
    round_key = str(round).strip() if round is not None and str(round).strip() else None

    # Pick the cheapest index available.
    if team_obj is not None:
        pool: Iterable[Match] = graph.matches_by_team.get(team_obj.id, [])
    elif competition_id and season_value is not None:
        pool = graph.matches_by_competition_season.get((competition_id, season_value), [])
    elif competition_id:
        pool = graph.matches_by_competition.get(competition_id, [])
    else:
        pool = graph.matches

    results: list[Match] = []
    for match in pool:
        if competition_id and match.competition_id != competition_id:
            continue
        if season_value is not None and match.season != season_value:
            continue
        if season_lo is not None and (match.season is None or match.season < season_lo):
            continue
        if season_hi is not None and (match.season is None or match.season > season_hi):
            continue
        if date_lo is not None and (match.date is None or match.date < date_lo):
            continue
        if date_hi is not None and (match.date is None or match.date > date_hi):
            continue
        if team_obj is not None:
            if home_away == "home" and match.home_team_id != team_obj.id:
                continue
            if home_away == "away" and match.away_team_id != team_obj.id:
                continue
        if opponent_obj is not None and not match.involves(opponent_obj.id):
            continue
        if opponent_obj is not None and team_obj is not None and (
            {match.home_team_id, match.away_team_id} != {team_obj.id, opponent_obj.id}
        ):
            continue
        if stage_key and normalize_name(match.stage or "") != stage_key:
            continue
        if round_key and str(match.round or "") != round_key:
            continue
        if venue_key and normalize_name(match.venue or "") != venue_key:
            continue
        if played_only and not match.has_score:
            continue
        results.append(match)

    reverse = order != "asc"
    results.sort(key=lambda m: (m.date or dt.date(1, 1, 1), m.id), reverse=reverse)
    if limit is not None and limit > 0:
        return results[:limit]
    return results


def head_to_head(
    graph: KnowledgeGraph,
    team_a: str,
    team_b: str,
    *,
    competition: str | None = None,
    season: object = None,
    limit: int | None = 20,
) -> HeadToHead:
    """Aggregate every meeting between two clubs."""

    a = resolve_team(graph, team_a)
    b = resolve_team(graph, team_b)
    matches = search_matches(
        graph, team=a.id, opponent=b.id, competition=competition,
        season=season, limit=None,
    )
    record = HeadToHead(
        team_a_id=a.id, team_a=a.display_name,
        team_b_id=b.id, team_b=b.display_name,
        matches=matches if limit is None else matches[:limit],
    )
    for match in matches:
        if not match.has_score:
            continue
        goals_a = match.goals_for(a.id) or 0
        goals_b = match.goals_for(b.id) or 0
        record.team_a_goals += goals_a
        record.team_b_goals += goals_b
        if goals_a > goals_b:
            record.team_a_wins += 1
        elif goals_b > goals_a:
            record.team_b_wins += 1
        else:
            record.draws += 1
    return record


def find_derbies(
    graph: KnowledgeGraph,
    *,
    season: object = None,
    competition: str | None = None,
    derby: str | None = None,
    limit: int | None = 50,
) -> list[dict[str, Any]]:
    """Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista...)."""

    wanted = normalize_name(derby) if derby else None
    out: list[dict[str, Any]] = []
    for rivalry in graph.derbies:
        if wanted and wanted not in normalize_name(rivalry.name):
            continue
        if rivalry.team_a not in graph.teams or rivalry.team_b not in graph.teams:
            continue
        matches = search_matches(
            graph, team=rivalry.team_a, opponent=rivalry.team_b,
            competition=competition, season=season, limit=limit,
        )
        if not matches:
            continue
        out.append({
            "derby": rivalry.name,
            "description": rivalry.description,
            "team_a": graph.team_name(rivalry.team_a),
            "team_b": graph.team_name(rivalry.team_b),
            "matches": matches,
        })
    return out


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------


def team_record(
    graph: KnowledgeGraph,
    team: str,
    *,
    competition: str | None = None,
    season: object = None,
    scope: str = "all",
    matches: Sequence[Match] | None = None,
) -> TeamRecord:
    """Wins/draws/losses and goals for a club, optionally home- or away-only."""

    team_obj = resolve_team(graph, team)
    scope = _as_scope(scope)
    if matches is None:
        matches = search_matches(
            graph, team=team_obj.id, competition=competition, season=season,
            home_away={"home": "home", "away": "away"}.get(scope, "any"),
            limit=None,
        )
    record = TeamRecord(team_id=team_obj.id, team_name=team_obj.display_name, scope=scope)
    for match in matches:
        if not match.has_score or not match.involves(team_obj.id):
            continue
        if scope == "home" and match.home_team_id != team_obj.id:
            continue
        if scope == "away" and match.away_team_id != team_obj.id:
            continue
        record.add(match.goals_for(team_obj.id) or 0, match.goals_against(team_obj.id) or 0)
    return record


def team_profile(graph: KnowledgeGraph, team: str, *, season: object = None) -> dict[str, Any]:
    """Everything the graph knows about one club."""

    team_obj = resolve_team(graph, team)
    season_value = _as_season(season)
    matches = search_matches(graph, team=team_obj.id, season=season_value, limit=None)
    by_competition: dict[str, TeamRecord] = {}
    for competition_id in sorted({m.competition_id for m in matches}):
        subset = [m for m in matches if m.competition_id == competition_id]
        record = team_record(graph, team_obj.id, matches=subset)
        record.scope = graph.competition_name(competition_id)
        by_competition[competition_id] = record

    overall = team_record(graph, team_obj.id, matches=matches)
    home = team_record(graph, team_obj.id, matches=matches, scope="home")
    away = team_record(graph, team_obj.id, matches=matches, scope="away")
    dated = [m.date for m in matches if m.date]
    squad = graph.players_by_club_team.get(team_obj.id, [])
    return {
        "team": team_obj,
        "season": season_value,
        "overall": overall,
        "home": home,
        "away": away,
        "by_competition": by_competition,
        "competitions": sorted(graph.team_competitions.get(team_obj.id, set())),
        "seasons": sorted(graph.team_seasons.get(team_obj.id, set())),
        "first_match": min(dated) if dated else None,
        "last_match": max(dated) if dated else None,
        "recent_matches": sorted(
            matches, key=lambda m: (m.date or dt.date(1, 1, 1)), reverse=True
        )[:5],
        "squad_size": len(squad),
    }


def compare_teams(
    graph: KnowledgeGraph,
    team_a: str,
    team_b: str,
    *,
    competition: str | None = None,
    season: object = None,
) -> dict[str, Any]:
    """Side-by-side records plus the head-to-head between two clubs."""

    a = resolve_team(graph, team_a)
    b = resolve_team(graph, team_b)
    return {
        "team_a": a,
        "team_b": b,
        "record_a": team_record(graph, a.id, competition=competition, season=season),
        "record_b": team_record(graph, b.id, competition=competition, season=season),
        "head_to_head": head_to_head(graph, a.id, b.id, competition=competition,
                                     season=season, limit=10),
        "competition": _competition_id(competition),
        "season": _as_season(season),
    }


def best_records(
    graph: KnowledgeGraph,
    *,
    competition: str | None = None,
    season: object = None,
    scope: str = "all",
    metric: str = "points_per_game",
    min_matches: int = 10,
    limit: int = 10,
) -> list[TeamRecord]:
    """Rank clubs by win rate / points per game / goals, over any slice."""

    competition_id = _competition_id(competition)
    season_value = _as_season(season)
    scope = _as_scope(scope)
    if competition_id and season_value is not None:
        pool = graph.matches_by_competition_season.get((competition_id, season_value), [])
    elif competition_id:
        pool = graph.matches_by_competition.get(competition_id, [])
    else:
        pool = graph.matches
    if season_value is not None:
        pool = [m for m in pool if m.season == season_value]

    records: dict[str, TeamRecord] = {}
    for match in pool:
        if not match.has_score:
            continue
        sides = []
        if scope in ("all", "home"):
            sides.append((match.home_team_id, match.home_goals, match.away_goals))
        if scope in ("all", "away"):
            sides.append((match.away_team_id, match.away_goals, match.home_goals))
        for team_id, scored, conceded in sides:
            record = records.get(team_id)
            if record is None:
                record = TeamRecord(team_id=team_id, team_name=graph.team_name(team_id),
                                    scope=scope)
                records[team_id] = record
            record.add(scored or 0, conceded or 0)

    metrics = {
        "points_per_game": lambda r: r.points_per_game,
        "points": lambda r: r.points,
        "win_rate": lambda r: r.win_rate,
        "wins": lambda r: r.wins,
        "goals_for": lambda r: r.goals_for,
        "goals_against": lambda r: -r.goals_against,
        "goal_difference": lambda r: r.goal_difference,
    }
    key = metrics.get(metric, metrics["points_per_game"])
    eligible = [r for r in records.values() if r.played >= min_matches]
    eligible.sort(key=lambda r: (-key(r), -r.goal_difference, r.team_name))
    return eligible[:limit]


def top_scoring_teams(
    graph: KnowledgeGraph,
    *,
    competition: str | None = None,
    season: object = None,
    limit: int = 10,
) -> list[TeamRecord]:
    """Clubs ranked by goals scored (TASK.md: "which team scored the most")."""

    return best_records(graph, competition=competition, season=season,
                        metric="goals_for", min_matches=1, limit=limit)


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------

#: How many clubs are relegated from Serie A / B, by table size.
_RELEGATION_SLOTS = 4


def standings(
    graph: KnowledgeGraph,
    competition: str,
    season: object,
    *,
    scope: str = "all",
) -> list[StandingRow]:
    """Calculate a league table from match results (3 points for a win).

    Tie-breaks follow the CBF order that is derivable from this data: points,
    wins, goal difference, goals for, then name.
    """

    competition_obj = resolve_competition(competition)
    if competition_obj is None:
        raise CompetitionNotFound(str(competition), [c.name for c in COMPETITIONS])
    season_value = _as_season(season)
    scope = _as_scope(scope)
    if season_value is None:
        raise ValueError("standings require a season, e.g. 2019")

    matches = graph.matches_by_competition_season.get(
        (competition_obj.id, season_value), []
    )
    records: dict[str, TeamRecord] = {}
    for match in matches:
        if not match.has_score:
            continue
        sides = []
        if scope in ("all", "home"):
            sides.append((match.home_team_id, match.home_goals, match.away_goals))
        if scope in ("all", "away"):
            sides.append((match.away_team_id, match.away_goals, match.home_goals))
        for team_id, scored, conceded in sides:
            record = records.get(team_id)
            if record is None:
                record = TeamRecord(team_id=team_id, team_name=graph.team_name(team_id),
                                    scope=scope)
                records[team_id] = record
            record.add(scored or 0, conceded or 0)

    ordered = sorted(
        records.values(),
        key=lambda r: (-r.points, -r.wins, -r.goal_difference, -r.goals_for, r.team_name),
    )
    rows: list[StandingRow] = []
    league_like = competition_obj.kind == "league" and scope == "all"
    total = len(ordered)
    for index, record in enumerate(ordered, start=1):
        note = None
        if league_like and total >= 16:
            if index == 1:
                note = "Champion"
            elif index > total - _RELEGATION_SLOTS:
                note = "Relegated"
        rows.append(StandingRow(position=index, record=record, note=note))
    return rows


def competition_champion(
    graph: KnowledgeGraph, competition: str, season: object
) -> dict[str, Any]:
    """Champion of a season -- table winner for leagues, final for cups."""

    competition_obj = resolve_competition(competition)
    if competition_obj is None:
        raise CompetitionNotFound(str(competition), [c.name for c in COMPETITIONS])
    season_value = _as_season(season)
    if season_value is None:
        raise ValueError("a season is required, e.g. 2019")

    if competition_obj.kind == "league":
        table = standings(graph, competition_obj.id, season_value)
        if not table:
            return {"competition": competition_obj, "season": season_value,
                    "champion": None, "method": "league table", "final": []}
        return {
            "competition": competition_obj,
            "season": season_value,
            "champion": graph.teams.get(table[0].record.team_id),
            "points": table[0].record.points,
            "record": table[0].record,
            "runner_up": graph.teams.get(table[1].record.team_id) if len(table) > 1 else None,
            "method": "league table calculated from match results",
            "final": [],
        }

    finals = [
        match for match in graph.matches_by_competition_season.get(
            (competition_obj.id, season_value), []
        )
        if normalize_name(match.stage or "") == "final"
    ]
    finals.sort(key=lambda m: (m.date or dt.date(1, 1, 1), m.id))
    aggregate: Counter[str] = Counter()
    played = [m for m in finals if m.has_score]
    for match in played:
        aggregate[match.home_team_id] += match.home_goals or 0
        aggregate[match.away_team_id] += match.away_goals or 0

    champion_id: str | None = None
    method = "aggregate score of the final"
    if played:
        ranked = aggregate.most_common()
        if len(ranked) >= 2 and ranked[0][1] == ranked[1][1]:
            champion_id = None
            method = ("final level on aggregate -- decided on penalties, which the "
                      "datasets do not record")
        elif ranked:
            champion_id = ranked[0][0]
            if len(played) == 1:
                method = "single-match final"
    return {
        "competition": competition_obj,
        "season": season_value,
        "champion": graph.teams.get(champion_id) if champion_id else None,
        "aggregate": {graph.team_name(t): g for t, g in aggregate.items()},
        "method": method,
        "final": finals,
    }


def relegated_teams(
    graph: KnowledgeGraph, competition: str, season: object, *, slots: int = _RELEGATION_SLOTS
) -> list[StandingRow]:
    """The bottom ``slots`` of a calculated league table."""

    table = standings(graph, competition, season)
    if not table:
        return []
    return table[-slots:]


def competition_stats(
    graph: KnowledgeGraph,
    *,
    competition: str | None = None,
    season: object = None,
) -> dict[str, Any]:
    """Goals per match, home advantage, biggest wins -- for any slice."""

    competition_id = _competition_id(competition)
    season_value = _as_season(season)
    if competition_id and season_value is not None:
        pool = graph.matches_by_competition_season.get((competition_id, season_value), [])
    elif competition_id:
        pool = graph.matches_by_competition.get(competition_id, [])
    elif season_value is not None:
        pool = [m for m in graph.matches if m.season == season_value]
    else:
        pool = graph.matches

    played = [m for m in pool if m.has_score]
    total_matches = len(played)
    home_wins = sum(1 for m in played if m.result == "H")
    away_wins = sum(1 for m in played if m.result == "A")
    draws = total_matches - home_wins - away_wins
    goals = sum(m.total_goals or 0 for m in played)
    home_goals = sum(m.home_goals or 0 for m in played)
    away_goals = sum(m.away_goals or 0 for m in played)
    clean_sheets = sum(1 for m in played if m.home_goals == 0 or m.away_goals == 0)
    seasons = sorted({m.season for m in pool if m.season is not None})
    teams = {m.home_team_id for m in pool} | {m.away_team_id for m in pool}

    def percent(count: int) -> float:
        return round(count / total_matches * 100, 1) if total_matches else 0.0

    return {
        "competition": graph.competition_name(competition_id) if competition_id else "All competitions",
        "competition_id": competition_id,
        "season": season_value,
        "seasons": seasons,
        "matches": len(pool),
        "matches_with_scores": total_matches,
        "teams": len(teams),
        "goals": goals,
        "goals_per_match": round(goals / total_matches, 2) if total_matches else 0.0,
        "home_goals_per_match": round(home_goals / total_matches, 2) if total_matches else 0.0,
        "away_goals_per_match": round(away_goals / total_matches, 2) if total_matches else 0.0,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": percent(home_wins),
        "away_win_rate": percent(away_wins),
        "draw_rate": percent(draws),
        "matches_with_a_clean_sheet": clean_sheets,
        "biggest_win": max(
            (m for m in played), key=lambda m: abs(m.goal_difference or 0), default=None
        ),
        "highest_scoring": max(
            (m for m in played), key=lambda m: m.total_goals or 0, default=None
        ),
    }


def biggest_wins(
    graph: KnowledgeGraph,
    *,
    competition: str | None = None,
    season: object = None,
    team: str | None = None,
    limit: int = 10,
) -> list[Match]:
    """Matches ordered by margin of victory."""

    matches = search_matches(
        graph, team=team, competition=competition, season=season,
        played_only=True, limit=None,
    )
    matches.sort(
        key=lambda m: (-abs(m.goal_difference or 0), -(m.total_goals or 0),
                       m.date or dt.date(1, 1, 1)),
    )
    return matches[:limit]


def compare_seasons(
    graph: KnowledgeGraph,
    seasons: Sequence[object],
    *,
    competition: str | None = "serie-a",
) -> list[dict[str, Any]]:
    """Aggregate statistics for several seasons side by side."""

    out = []
    for season in seasons:
        stats = competition_stats(graph, competition=competition, season=season)
        table = []
        try:
            table = standings(graph, competition or "serie-a", season)
        except (CompetitionNotFound, ValueError):
            table = []
        stats["champion"] = table[0].record.team_name if table else None
        stats["champion_points"] = table[0].record.points if table else None
        out.append(stats)
    return out


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------

_SORTABLE_PLAYER_FIELDS = {
    "overall": lambda p: (-(p.overall or 0), p.name),
    "potential": lambda p: (-(p.potential or 0), p.name),
    "age": lambda p: (p.age if p.age is not None else 999, p.name),
    "name": lambda p: (normalize_name(p.name),),
}


def search_players(
    graph: KnowledgeGraph,
    *,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: object = None,
    max_overall: object = None,
    min_age: object = None,
    max_age: object = None,
    brazilian_clubs_only: bool = False,
    sort_by: str = "overall",
    limit: int = 20,
) -> list[Player]:
    """Search the FIFA player database.

    ``position`` accepts either a FIFA code (``"LW"``) or a group word
    (``"forward"``, ``"goalkeeper"``, ``"midfielders"``).  ``club`` matches both
    the raw FIFA club string and the canonical club it was linked to, so
    "Flamengo", "São Paulo FC" and "sao-paulo-sp" all work.
    """

    # Index selection below is only an optimisation -- every predicate is also
    # re-checked in the loop, so combining `nationality` and `club` cannot lose
    # a filter by picking the wrong index.
    nationality_key = normalize_name(nationality) if nationality else None
    club_key = normalize_name(club) if club else None

    club_team: Team | None = None
    if club:
        try:
            club_team = resolve_team(graph, club)
        except TeamNotFound:
            club_team = None

    pool: Iterable[Player]
    if club_team is not None and graph.players_by_club_team.get(club_team.id):
        pool = graph.players_by_club_team[club_team.id]
    elif nationality_key and nationality_key in graph.players_by_nationality:
        pool = graph.players_by_nationality[nationality_key]
    else:
        pool = graph.players

    name_key = normalize_name(name) if name else None
    group = POSITION_GROUP_ALIASES.get(normalize_name(position)) if position else None
    position_code = position.strip().upper() if position and group is None else None
    min_ovr, max_ovr = parse_int(min_overall), parse_int(max_overall)
    min_years, max_years = parse_int(min_age), parse_int(max_age)

    results: list[Player] = []
    for player in pool:
        if name_key and name_key not in normalize_name(player.name):
            continue
        if nationality_key and nationality_key not in normalize_name(player.nationality or ""):
            continue
        if club_key and not (
            (club_team is not None and player.club_team_id == club_team.id)
            or club_key in normalize_name(player.club_raw or "")
        ):
            continue
        if group and position_group(player.position) != group:
            continue
        if position_code and (player.position or "").upper() != position_code:
            continue
        if min_ovr is not None and (player.overall or 0) < min_ovr:
            continue
        if max_ovr is not None and (player.overall or 0) > max_ovr:
            continue
        if min_years is not None and (player.age or 0) < min_years:
            continue
        if max_years is not None and (player.age or 0) > max_years:
            continue
        if brazilian_clubs_only and not player.club_team_id:
            continue
        results.append(player)

    results.sort(key=_SORTABLE_PLAYER_FIELDS.get(sort_by, _SORTABLE_PLAYER_FIELDS["overall"]))
    if limit and limit > 0:
        return results[:limit]
    return results


def player_profile(graph: KnowledgeGraph, name: str) -> dict[str, Any]:
    """Look up one player by (partial) name, with near-miss suggestions."""

    key = normalize_name(name or "")
    exact = graph.players_by_name.get(key, [])
    if exact:
        matches = exact
    else:
        matches = [p for p in graph.players if key and key in normalize_name(p.name)]
    matches = sorted(matches, key=lambda p: (-(p.overall or 0), p.name))
    suggestions: list[str] = []
    if not matches and key:
        first_token = key.split()[0] if key.split() else key
        suggestions = [
            p.name for p in graph.players
            if first_token and first_token in normalize_name(p.name)
        ][:5]
    player = matches[0] if matches else None
    club_team = graph.teams.get(player.club_team_id) if player and player.club_team_id else None
    return {
        "query": name,
        "player": player,
        "alternatives": matches[1:6],
        "suggestions": suggestions,
        "club_team": club_team,
        "club_matches": len(graph.matches_by_team.get(club_team.id, [])) if club_team else 0,
    }


def club_squad(graph: KnowledgeGraph, club: str, *, limit: int = 40) -> dict[str, Any]:
    """The FIFA squad for a club, plus its record in the match graph.

    This is the cross-file query TASK.md asks for: FIFA player rows joined to
    the club's match history through the canonical team id.
    """

    team = resolve_team(graph, club)
    squad = sorted(
        graph.players_by_club_team.get(team.id, []),
        key=lambda p: (-(p.overall or 0), p.name),
    )
    ratings = [p.overall for p in squad if p.overall is not None]
    by_group: dict[str, list[Player]] = defaultdict(list)
    for player in squad:
        by_group[position_group(player.position) or "unknown"].append(player)
    return {
        "team": team,
        "players": squad[:limit] if limit else squad,
        "squad_size": len(squad),
        "average_overall": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "by_position_group": {
            group: by_group.get(group, []) for group in POSITION_GROUPS if by_group.get(group)
        },
        "record": team_record(graph, team.id),
        "competitions": sorted(graph.team_competitions.get(team.id, set())),
    }


def brazilian_players_by_club(
    graph: KnowledgeGraph, *, limit: int = 20
) -> list[dict[str, Any]]:
    """Brazilian-club squads with size and average rating (TASK.md example)."""

    rows = []
    for team_id, players in graph.players_by_club_team.items():
        ratings = [p.overall for p in players if p.overall is not None]
        rows.append({
            "team": graph.team_name(team_id),
            "team_id": team_id,
            "players": len(players),
            "average_overall": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "best_player": max(players, key=lambda p: p.overall or 0).name if players else None,
        })
    rows.sort(key=lambda row: (-(row["average_overall"] or 0), row["team"]))
    return rows[:limit]


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


def dataset_summary(graph: KnowledgeGraph) -> dict[str, Any]:
    """Provenance, coverage and graph shape -- the ``dataset_summary`` tool."""

    from .config import DATASETS

    competitions = []
    for competition in graph.competitions:
        matches = graph.matches_by_competition.get(competition.id, [])
        seasons = graph.seasons_for(competition.id)
        competitions.append({
            "id": competition.id,
            "name": competition.name,
            "kind": competition.kind,
            "matches": len(matches),
            "seasons": f"{seasons[0]}-{seasons[-1]}" if seasons else "-",
            "season_list": seasons,
        })
    return {
        "datasets": [
            {
                "key": spec.key,
                "file": spec.filename,
                "kind": spec.kind,
                "description": spec.description,
                "license": spec.license,
                "source_url": spec.source_url,
                "rows": graph.report.rows_by_dataset.get(spec.key, 0),
            }
            for spec in DATASETS
        ],
        "competitions": competitions,
        "report": graph.report.to_dict(),
        "graph": graph.graph_schema(),
        "teams_with_matches": len(graph.matches_by_team),
        "players_linked_to_clubs": graph.report.linked_player_clubs,
    }
