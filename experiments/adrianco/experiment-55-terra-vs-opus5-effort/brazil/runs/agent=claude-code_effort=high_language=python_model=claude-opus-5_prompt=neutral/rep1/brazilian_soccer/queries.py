"""The query API behind every MCP tool.

Context
-------
Each public function here takes plain Python arguments (already validated by
:mod:`brazilian_soccer.tools`), reads from the indexed
:class:`~brazilian_soccer.graph.KnowledgeGraph`, and returns a JSON-ready dict.
Rendering those dicts as prose is :mod:`brazilian_soccer.formatting`'s job, so
the same result can be returned both as ``structuredContent`` and as readable
text in a single MCP response.

Conventions used throughout:

* ``team``/``opponent`` accept any spelling; they are resolved through
  :meth:`KnowledgeGraph.resolve_team` and a :class:`QueryError` is raised with
  suggestions when the club is unknown.
* ``competition`` accepts any alias and ``None`` means "all competitions".
* Every result carries a ``notes`` list explaining data caveats (missing
  seasons, unplayed fixtures, competitions absent from the source files) so an
  LLM can qualify its answer instead of over-claiming.
"""

from __future__ import annotations

import datetime as _dt
import difflib
import statistics
from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence

from .clubs import RIVALRIES, resolve_club, rivalry_for
from .competitions import COMPETITIONS, competition_name, resolve_competition
from .graph import KnowledgeGraph, load_graph
from .models import Match, Player
from .normalization import normalize_text, parse_date

__all__ = [
    "QueryError",
    "find_matches",
    "head_to_head",
    "team_stats",
    "team_profile",
    "standings",
    "team_rankings",
    "competition_stats",
    "biggest_wins",
    "compare_seasons",
    "search_players",
    "player_profile",
    "club_squad",
    "brazilian_players_by_club",
    "find_derbies",
    "resolve_team",
    "dataset_summary",
]

DEFAULT_LIMIT = 25
MAX_LIMIT = 500


class QueryError(ValueError):
    """Raised for user-fixable problems (unknown club, bad date, ...)."""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _graph(graph: KnowledgeGraph | None) -> KnowledgeGraph:
    return graph if graph is not None else load_graph()


def _require_team(graph: KnowledgeGraph, name: str, *, label: str = "team") -> str:
    resolution = graph.resolve_team(name)
    if not resolution.matched or resolution.slug is None:
        raise QueryError(resolution.message or f"Unknown {label}: {name!r}")
    return resolution.slug


def _competition(value: str | None) -> str | None:
    try:
        return resolve_competition(value)
    except ValueError as exc:
        raise QueryError(str(exc)) from exc


def _as_date(value: str | None, label: str) -> _dt.date | None:
    if value in (None, ""):
        return None
    parsed = parse_date(value)
    if parsed is None:
        raise QueryError(
            f"Could not read {label}={value!r}; use YYYY-MM-DD or DD/MM/YYYY.")
    return parsed


def _clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise QueryError(f"limit must be an integer, got {limit!r}")
    if value <= 0:
        raise QueryError("limit must be positive")
    return min(value, MAX_LIMIT)


def _contains_words(needle: str, haystack: str) -> bool:
    """True when *needle*'s tokens appear as a whole-token run in *haystack*.

    A plain substring test is wrong for club names: ``"nacional"`` is inside
    ``"Internacional"``, which would hand back Internacional's squad for a
    query about Nacional.  Both arguments must already be normalised.
    """
    wanted = needle.split()
    if not wanted:
        return False
    tokens = haystack.split()
    return any(tokens[i:i + len(wanted)] == wanted
               for i in range(len(tokens) - len(wanted) + 1))


def _players_by_club_name(graph: KnowledgeGraph,
                          club: str) -> tuple[list[Player], list[str]]:
    """Find players by their FIFA club string when the club graph lookup fails.

    Used for clubs that appear in the FIFA file but not in the Brazilian match
    datasets (Real Madrid, FC Barcelona, ...).  Matching is on whole tokens and
    on the resolved club slug, never on a bare substring -- ``"Nacional"`` must
    not drag in Internacional's squad.

    Returns the players of a *single* club plus the names of the other clubs
    the query also matched, so an ambiguous search reports one coherent squad
    and names the alternatives instead of blending them.
    """
    target = resolve_club(club).slug
    key = normalize_text(club)
    groups: dict[str, list[Player]] = defaultdict(list)
    for player in graph.players:
        if not player.club:
            continue
        if (player.club_slug == target
                or _contains_words(key, normalize_text(player.club))):
            groups[player.club].append(player)
    if not groups:
        return [], []

    def rank(name: str) -> tuple:
        return (normalize_text(name) != key, -len(groups[name]), name)

    ordered = sorted(groups, key=rank)
    best = ordered[0]
    squad = sorted(groups[best], key=lambda p: (-(p.overall or 0), p.name))
    return squad, ordered[1:]


def _stage_matches(stage_key: str, match: Match) -> bool:
    """Whole-word stage matching.

    A substring test would make ``stage="Final"`` also select every
    ``"Semifinals"`` fixture, so the query has to line up with a run of whole
    tokens in the stage or round label.
    """
    wanted = stage_key.split()
    for label in (match.stage, match.round, f"round {match.round}"
                  if match.round else None):
        if not label:
            continue
        tokens = normalize_text(str(label)).split()
        for start in range(len(tokens) - len(wanted) + 1):
            if tokens[start:start + len(wanted)] == wanted:
                return True
    return False


def _filter(
    matches: Iterable[Match],
    *,
    competition: str | None = None,
    season: int | None = None,
    season_from: int | None = None,
    season_to: int | None = None,
    date_from: _dt.date | None = None,
    date_to: _dt.date | None = None,
    stage: str | None = None,
    played_only: bool = False,
) -> list[Match]:
    stage_key = normalize_text(stage) if stage else None
    result = []
    for match in matches:
        if competition and match.competition != competition:
            continue
        if season is not None and match.season != season:
            continue
        if season_from is not None and (match.season is None or match.season < season_from):
            continue
        if season_to is not None and (match.season is None or match.season > season_to):
            continue
        if date_from and (match.date is None or match.date < date_from):
            continue
        if date_to and (match.date is None or match.date > date_to):
            continue
        if stage_key and not _stage_matches(stage_key, match):
            continue
        if played_only and not match.played:
            continue
        result.append(match)
    return result


def _sorted_matches(matches: Sequence[Match], newest_first: bool = True) -> list[Match]:
    return sorted(
        matches,
        key=lambda m: (m.date or _dt.date.min, m.match_id),
        reverse=newest_first,
    )


def _record(matches: Iterable[Match], slug: str) -> dict[str, Any]:
    """Aggregate a win/draw/loss and goals record for one club."""
    played = wins = draws = losses = goals_for = goals_against = 0
    biggest_win: Match | None = None
    biggest_loss: Match | None = None
    for match in matches:
        result = match.result_for(slug)
        if result is None:
            continue
        played += 1
        goals_for += match.goals_for(slug)
        goals_against += match.goals_against(slug)
        if result == "W":
            wins += 1
            if biggest_win is None or match.goal_margin > biggest_win.goal_margin:
                biggest_win = match
        elif result == "D":
            draws += 1
        else:
            losses += 1
            if biggest_loss is None or match.goal_margin > biggest_loss.goal_margin:
                biggest_loss = match
    points = wins * 3 + draws
    return {
        "played": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goals_for - goals_against,
        "points": points,
        "win_rate": round(wins / played * 100, 1) if played else 0.0,
        "points_per_game": round(points / played, 2) if played else 0.0,
        "goals_for_per_game": round(goals_for / played, 2) if played else 0.0,
        "goals_against_per_game": round(goals_against / played, 2) if played else 0.0,
        "biggest_win": biggest_win.to_dict() if biggest_win else None,
        "biggest_defeat": biggest_loss.to_dict() if biggest_loss else None,
    }


def _coverage_note(graph: KnowledgeGraph, competition: str | None,
                   season: int | None) -> list[str]:
    notes: list[str] = []
    if competition and season is not None:
        seasons = graph.competition_seasons(competition)
        if seasons and season not in seasons:
            notes.append(
                f"{competition_name(competition)} data covers "
                f"{seasons[0]}-{seasons[-1]}; season {season} is not in the datasets."
            )
    return notes


# ---------------------------------------------------------------------------
# 1. Match queries
# ---------------------------------------------------------------------------

def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    venue: str = "any",
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    limit: int | None = None,
    newest_first: bool = True,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """Find fixtures matching any combination of criteria.

    ``venue`` is ``"home"``, ``"away"`` or ``"any"`` and is interpreted from
    *team*'s point of view.
    """
    g = _graph(graph)
    limit = _clamp_limit(limit)
    comp = _competition(competition)
    start, end = _as_date(date_from, "date_from"), _as_date(date_to, "date_to")
    if venue not in {"home", "away", "any"}:
        raise QueryError('venue must be one of "home", "away" or "any"')

    team_slug = _require_team(g, team) if team else None
    opponent_slug = _require_team(g, opponent, label="opponent") if opponent else None

    if team_slug and opponent_slug:
        pool = g.matches_between(team_slug, opponent_slug)
    elif team_slug:
        pool = g.matches_for(team_slug)
    elif opponent_slug:
        pool = g.matches_for(opponent_slug)
    elif comp and season is not None:
        pool = g.matches_by_comp_season.get((comp, season), [])
    elif comp:
        pool = g.matches_by_competition.get(comp, [])
    else:
        pool = g.matches

    if team_slug and venue == "home":
        pool = [m for m in pool if m.home_slug == team_slug]
    elif team_slug and venue == "away":
        pool = [m for m in pool if m.away_slug == team_slug]

    selected = _filter(pool, competition=comp, season=season,
                       date_from=start, date_to=end, stage=stage)
    selected = _sorted_matches(selected, newest_first)

    notes = _coverage_note(g, comp, season)
    if team_slug and not selected:
        notes.append(f"No fixtures found for {g.team_name(team_slug)} with these filters.")

    return {
        "query": {
            "team": g.team_name(team_slug) if team_slug else None,
            "opponent": g.team_name(opponent_slug) if opponent_slug else None,
            "venue": venue,
            "competition": competition_name(comp) if comp else "All competitions",
            "season": season,
            "date_from": start.isoformat() if start else None,
            "date_to": end.isoformat() if end else None,
            "stage": stage,
        },
        "total_matches": len(selected),
        "returned": min(len(selected), limit),
        "matches": [m.to_dict() for m in selected[:limit]],
        "notes": notes,
    }


def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
    limit: int | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """Complete head-to-head record between two clubs."""
    g = _graph(graph)
    limit = _clamp_limit(limit)
    comp = _competition(competition)
    slug_a = _require_team(g, team_a)
    slug_b = _require_team(g, team_b, label="opponent")
    if slug_a == slug_b:
        raise QueryError("A club cannot play itself; give two different teams.")

    fixtures = _filter(g.matches_between(slug_a, slug_b), competition=comp, season=season)
    fixtures = _sorted_matches(fixtures)

    a_wins = b_wins = draws = 0
    goals_a = goals_b = 0
    by_competition: Counter = Counter()
    for match in fixtures:
        by_competition[match.competition] += 1
        if not match.played:
            continue
        goals_a += match.goals_for(slug_a)
        goals_b += match.goals_for(slug_b)
        outcome = match.result_for(slug_a)
        if outcome == "W":
            a_wins += 1
        elif outcome == "L":
            b_wins += 1
        else:
            draws += 1

    home_a = [m for m in fixtures if m.home_slug == slug_a]
    home_b = [m for m in fixtures if m.home_slug == slug_b]

    return {
        "team_a": g.team_name(slug_a),
        "team_b": g.team_name(slug_b),
        "derby_name": rivalry_for(slug_a, slug_b),
        "competition": competition_name(comp) if comp else "All competitions",
        "season": season,
        "total_matches": len(fixtures),
        # Keys are fixed rather than derived from the club names, so a caller
        # can rely on the shape regardless of which two clubs were asked for.
        "summary": {
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": goals_a,
            "team_b_goals": goals_b,
        },
        "by_competition": [
            {"competition": competition_name(slug), "matches": count}
            for slug, count in by_competition.most_common()
        ],
        "at_team_a_home": _record(home_a, slug_a),
        "at_team_b_home": _record(home_b, slug_b),
        "first_meeting": fixtures[-1].to_dict() if fixtures else None,
        "last_meeting": fixtures[0].to_dict() if fixtures else None,
        "matches": [m.to_dict() for m in fixtures[:limit]],
        "returned": min(len(fixtures), limit),
        "notes": _coverage_note(g, comp, season),
    }


# ---------------------------------------------------------------------------
# 2. Team queries
# ---------------------------------------------------------------------------

def team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",
    season_from: int | None = None,
    season_to: int | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """Win/draw/loss and goal record for a club, optionally split by venue."""
    g = _graph(graph)
    comp = _competition(competition)
    if venue not in {"home", "away", "all"}:
        raise QueryError('venue must be one of "home", "away" or "all"')
    if (season_from is not None and season_to is not None
            and season_from > season_to):
        raise QueryError(
            f"season_from ({season_from}) is after season_to ({season_to}).")
    slug = _require_team(g, team)

    fixtures = _filter(g.matches_for(slug), competition=comp, season=season,
                       season_from=season_from, season_to=season_to)
    home = [m for m in fixtures if m.home_slug == slug]
    away = [m for m in fixtures if m.away_slug == slug]
    scope = {"home": home, "away": away, "all": fixtures}[venue]

    seasons = sorted({m.season for m in fixtures if m.season is not None})
    return {
        "team": g.team_name(slug),
        "team_slug": slug,
        "state": (g.team(slug).state or "").upper() or None,
        "competition": competition_name(comp) if comp else "All competitions",
        "season": season,
        "venue": venue,
        "seasons_covered": seasons,
        "overall": _record(scope, slug),
        "home": _record(home, slug),
        "away": _record(away, slug),
        # Broken down over `scope`, not `fixtures`, so a home-only request does
        # not hand back a breakdown that silently includes away games.
        "by_competition": [
            {
                "competition": competition_name(comp_slug),
                **{k: v for k, v in _record(
                    [m for m in scope if m.competition == comp_slug], slug).items()
                   if k not in {"biggest_win", "biggest_defeat"}},
            }
            for comp_slug in sorted({m.competition for m in scope})
        ],
        "notes": _coverage_note(g, comp, season),
    }


def team_profile(team: str, graph: KnowledgeGraph | None = None) -> dict[str, Any]:
    """A team's neighbourhood in the knowledge graph.

    Answers "what competitions has Palmeiras played in?" and doubles as the
    entry point for exploring a club: competitions, seasons, biggest rivals by
    number of meetings, stadiums used and any FIFA squad members.
    """
    g = _graph(graph)
    slug = _require_team(g, team)
    node = g.team(slug)
    fixtures = g.matches_for(slug)

    per_competition: dict[str, list[Match]] = defaultdict(list)
    opponents: Counter = Counter()
    venues: Counter = Counter()
    for match in fixtures:
        per_competition[match.competition].append(match)
        other = match.opponent_of(slug)
        if other:
            opponents[other] += 1
        if match.venue:
            venues[match.venue] += 1

    competitions = []
    for comp_slug, group in sorted(per_competition.items(),
                                   key=lambda kv: -len(kv[1])):
        seasons = sorted({m.season for m in group if m.season is not None})
        record = _record(group, slug)
        competitions.append({
            "competition": competition_name(comp_slug),
            "competition_slug": comp_slug,
            "matches": len(group),
            "seasons": f"{seasons[0]}-{seasons[-1]}" if seasons else None,
            "wins": record["wins"],
            "draws": record["draws"],
            "losses": record["losses"],
            "win_rate": record["win_rate"],
        })

    squad = g.squad(slug)
    return {
        "team": node.name,
        "team_slug": slug,
        "state": (node.state or "").upper() or None,
        "curated_club": node.known,
        "spellings_in_data": sorted(node.aliases),
        "total_matches": len(fixtures),
        "record": {k: v for k, v in _record(fixtures, slug).items()
                   if k not in {"biggest_win", "biggest_defeat"}},
        "competitions": competitions,
        "most_played_opponents": [
            {"opponent": g.team_name(other), "matches": count,
             "derby": rivalry_for(slug, other)}
            for other, count in opponents.most_common(10)
        ],
        "stadiums": [{"venue": v, "matches": c} for v, c in venues.most_common(5)],
        "fifa_squad_size": len(squad),
        "fifa_squad_top_rated": [p.to_dict() for p in squad[:5]],
        "notes": ([] if squad else
                  ["No FIFA 19 squad data for this club -- the FIFA dataset only "
                   "includes licensed Brazilian clubs (Grêmio, Cruzeiro, Santos, "
                   "Internacional, Atlético Mineiro, Fluminense, Botafogo, Bahia, "
                   "Vitória, Chapecoense, Ceará, Sport, Paraná, Athletico "
                   "Paranaense and América Mineiro)."]),
    }


# ---------------------------------------------------------------------------
# 3. Competition queries
# ---------------------------------------------------------------------------

#: Number of clubs relegated from Série A, by era.  Before 2006 the format
#: changed year to year, so we only label relegation when we are confident.
_RELEGATION_SLOTS = {"serie-a": 4, "serie-b": 4, "serie-c": 4}


def standings(
    season: int,
    competition: str = "serie-a",
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """League table for a season, computed from the match results.

    Three points for a win, one for a draw; ties are broken by wins, then goal
    difference, then goals scored -- the CBF criteria.  Clubs that appear in
    only a handful of fixtures (mislabelled rows in the source data) are
    reported separately instead of polluting the table.
    """
    g = _graph(graph)
    comp = _competition(competition)
    if comp is None:
        raise QueryError("standings requires a competition")
    fixtures = g.matches_by_comp_season.get((comp, season), [])
    if not fixtures:
        seasons = g.competition_seasons(comp)
        available = f"{seasons[0]}-{seasons[-1]}" if seasons else "none"
        raise QueryError(
            f"No {competition_name(comp)} matches for season {season} "
            f"(available seasons: {available}).")

    per_team: dict[str, list[Match]] = defaultdict(list)
    for match in fixtures:
        per_team[match.home_slug].append(match)
        per_team[match.away_slug].append(match)

    counts = [len(v) for v in per_team.values()]
    median = statistics.median(counts) if counts else 0
    threshold = median / 2

    rows, outliers = [], []
    for slug, group in per_team.items():
        record = _record(group, slug)
        entry = {
            "team": g.team_name(slug),
            "team_slug": slug,
            "played": record["played"],
            "wins": record["wins"],
            "draws": record["draws"],
            "losses": record["losses"],
            "goals_for": record["goals_for"],
            "goals_against": record["goals_against"],
            "goal_difference": record["goal_difference"],
            "points": record["points"],
        }
        (rows if len(group) >= threshold else outliers).append(entry)

    rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_difference"],
                             -r["goals_for"], r["team"]))
    for position, row in enumerate(rows, start=1):
        row["position"] = position

    comp_meta = next((c for c in COMPETITIONS if c.slug == comp), None)
    is_league = comp_meta is not None and comp_meta.kind == "league"
    notes: list[str] = []
    champion = None
    relegated: list[str] = []
    if is_league and rows:
        expected = len(rows) * (len(rows) - 1)
        # Count only fixtures between clubs that made the table: a mislabelled
        # row involving an excluded club must not pad the total and make a
        # genuinely incomplete season look finished.
        ranked = {row["team_slug"] for row in rows}
        counted = sum(1 for m in fixtures
                      if m.home_slug in ranked and m.away_slug in ranked)
        complete = counted >= expected
        if complete:
            champion = rows[0]["team"]
            slots = _RELEGATION_SLOTS.get(comp, 0)
            if slots:
                relegated = [r["team"] for r in rows[-slots:]]
        else:
            notes.append(
                f"Only {counted} of the expected {expected} fixtures are in "
                "the datasets, so this table is partial and no champion is claimed.")
    else:
        notes.append(
            f"{competition_name(comp)} is a knockout competition; this table "
            "ranks clubs by results but is not an official standing.")
    if outliers:
        notes.append(
            "Excluded from the table (too few fixtures, probably mislabelled rows): "
            + ", ".join(sorted(o["team"] for o in outliers)))
    if comp == "serie-a" and rows and len(rows) != 20:
        notes.append(
            f"The {season} Série A was contested by {len(rows)} clubs "
            f"({len(fixtures)} fixtures), not the modern 20.")

    return {
        "competition": competition_name(comp),
        "competition_slug": comp,
        "season": season,
        "matches_played": len(fixtures),
        "teams": len(rows),
        "champion": champion,
        "relegated": relegated,
        "table": rows,
        "excluded": outliers,
        "notes": notes,
    }


def team_rankings(
    metric: str = "points",
    competition: str | None = None,
    season: int | None = None,
    venue: str = "all",
    min_matches: int = 10,
    limit: int | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """Rank clubs by a metric -- the backbone of "which team has the best ..." .

    Supported metrics: ``points``, ``points_per_game``, ``wins``, ``win_rate``,
    ``goals_for``, ``goals_against`` (ascending), ``goal_difference``,
    ``goals_for_per_game``, ``matches``.
    """
    g = _graph(graph)
    limit = _clamp_limit(limit)
    comp = _competition(competition)
    if venue not in {"home", "away", "all"}:
        raise QueryError('venue must be one of "home", "away" or "all"')

    ascending_metrics = {"goals_against", "goals_against_per_game"}
    valid = {"points", "points_per_game", "wins", "win_rate", "goals_for",
             "goals_against", "goal_difference", "goals_for_per_game",
             "goals_against_per_game", "matches", "played"}
    if metric not in valid:
        raise QueryError(f"Unknown metric {metric!r}. Choose from: "
                         + ", ".join(sorted(valid)))

    pool = (g.matches_by_comp_season.get((comp, season), []) if comp and season is not None
            else g.matches_by_competition.get(comp, []) if comp
            else g.matches)
    pool = _filter(pool, competition=comp, season=season, played_only=True)

    per_team: dict[str, list[Match]] = defaultdict(list)
    for match in pool:
        if venue in ("all", "home"):
            per_team[match.home_slug].append(match)
        if venue in ("all", "away"):
            per_team[match.away_slug].append(match)
    if venue == "home":
        per_team = {s: [m for m in v if m.home_slug == s] for s, v in per_team.items()}
    elif venue == "away":
        per_team = {s: [m for m in v if m.away_slug == s] for s, v in per_team.items()}

    rows = []
    for slug, group in per_team.items():
        record = _record(group, slug)
        if record["played"] < min_matches:
            continue
        rows.append({
            "team": g.team_name(slug),
            "team_slug": slug,
            "matches": record["played"],
            "played": record["played"],
            "wins": record["wins"],
            "draws": record["draws"],
            "losses": record["losses"],
            "goals_for": record["goals_for"],
            "goals_against": record["goals_against"],
            "goal_difference": record["goal_difference"],
            "points": record["points"],
            "points_per_game": record["points_per_game"],
            "win_rate": record["win_rate"],
            "goals_for_per_game": record["goals_for_per_game"],
            "goals_against_per_game": record["goals_against_per_game"],
        })

    # `goals_against` sorts ascending (fewer is better) but the points-per-game
    # tie-break must stay descending either way, so the sign is applied per key
    # rather than with a blanket `reverse=`.
    direction = 1 if metric in ascending_metrics else -1
    rows.sort(key=lambda r: (direction * r[metric], -r["points_per_game"], r["team"]))
    for position, row in enumerate(rows, start=1):
        row["rank"] = position

    return {
        "metric": metric,
        "venue": venue,
        "competition": competition_name(comp) if comp else "All competitions",
        "season": season,
        "min_matches": min_matches,
        "teams_considered": len(rows),
        "rankings": rows[:limit],
        "notes": _coverage_note(g, comp, season),
    }


def competition_stats(
    competition: str | None = None,
    season: int | None = None,
    season_from: int | None = None,
    season_to: int | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """Aggregate statistics: goals per match, home advantage, scoring spread."""
    g = _graph(graph)
    comp = _competition(competition)
    pool = (g.matches_by_competition.get(comp, []) if comp else g.matches)
    fixtures = _filter(pool, competition=comp, season=season,
                       season_from=season_from, season_to=season_to,
                       played_only=True)
    if not fixtures:
        raise QueryError(
            f"No played fixtures for {competition_name(comp)}"
            + (f" season {season}" if season is not None else "")
            + " in the datasets.")

    total = len(fixtures)
    home_wins = sum(1 for m in fixtures if m.outcome == "home")
    away_wins = sum(1 for m in fixtures if m.outcome == "away")
    draws = total - home_wins - away_wins
    goals_home = sum(m.home_goals for m in fixtures)
    goals_away = sum(m.away_goals for m in fixtures)
    goals = goals_home + goals_away
    scorelines = Counter(f"{m.home_goals}-{m.away_goals}" for m in fixtures)
    clean_sheets = sum(1 for m in fixtures if m.home_goals == 0 or m.away_goals == 0)

    by_season = []
    per_season: dict[int, list[Match]] = defaultdict(list)
    for match in fixtures:
        if match.season is not None:
            per_season[match.season].append(match)
    for year in sorted(per_season):
        group = per_season[year]
        by_season.append({
            "season": year,
            "matches": len(group),
            "goals": sum(m.total_goals for m in group),
            "goals_per_match": round(sum(m.total_goals for m in group) / len(group), 2),
            "home_win_rate": round(
                sum(1 for m in group if m.outcome == "home") / len(group) * 100, 1),
        })

    scoring = Counter()
    for match in fixtures:
        scoring[match.home_slug] += match.home_goals
        scoring[match.away_slug] += match.away_goals

    return {
        "competition": competition_name(comp) if comp else "All competitions",
        "season": season,
        "seasons": (f"{by_season[0]['season']}-{by_season[-1]['season']}"
                    if by_season else None),
        "matches": total,
        "goals": goals,
        "goals_per_match": round(goals / total, 2),
        "home_goals": goals_home,
        "away_goals": goals_away,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / total * 100, 1),
        "away_win_rate": round(away_wins / total * 100, 1),
        "draw_rate": round(draws / total * 100, 1),
        "matches_with_a_clean_sheet": clean_sheets,
        "most_common_scorelines": [
            {"score": score, "count": count} for score, count in scorelines.most_common(5)
        ],
        "top_scoring_teams": [
            {"team": g.team_name(slug), "goals": count}
            for slug, count in scoring.most_common(10)
        ],
        "by_season": by_season,
        "notes": (["The datasets record match results only -- there is no "
                   "goalscorer column, so individual top-scorer questions cannot "
                   "be answered from this data."]
                  + _coverage_note(g, comp, season)),
    }


def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
    limit: int | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """The largest winning margins, optionally restricted to one club."""
    g = _graph(graph)
    limit = _clamp_limit(limit)
    comp = _competition(competition)
    slug = _require_team(g, team) if team else None

    pool = g.matches_for(slug) if slug else (
        g.matches_by_competition.get(comp, []) if comp else g.matches)
    fixtures = _filter(pool, competition=comp, season=season, played_only=True)
    if slug:
        fixtures = [m for m in fixtures if m.winner_slug == slug]

    fixtures.sort(key=lambda m: (-m.goal_margin, -m.total_goals,
                                 -(m.date.toordinal() if m.date else 0)))
    return {
        "competition": competition_name(comp) if comp else "All competitions",
        "season": season,
        "team": g.team_name(slug) if slug else None,
        "matches_considered": len(fixtures),
        "results": [
            {**m.to_dict(), "margin": m.goal_margin,
             "winner": g.team_name(m.winner_slug) if m.winner_slug else None}
            for m in fixtures[:limit]
        ],
        "notes": _coverage_note(g, comp, season),
    }


def compare_seasons(
    seasons: Sequence[int],
    competition: str = "serie-a",
    team: str | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """Side-by-side aggregates for two or more seasons of one competition."""
    g = _graph(graph)
    comp = _competition(competition)
    if comp is None:
        raise QueryError("compare_seasons requires a competition")
    if not seasons:
        raise QueryError("Give at least one season to compare")
    slug = _require_team(g, team) if team else None

    rows = []
    for year in seasons:
        fixtures = _filter(g.matches_by_comp_season.get((comp, year), []),
                           played_only=True)
        if slug:
            fixtures = [m for m in fixtures if m.involves(slug)]
        if not fixtures:
            rows.append({"season": year, "matches": 0,
                         "note": "no data for this season"})
            continue
        goals = sum(m.total_goals for m in fixtures)
        entry = {
            "season": year,
            "matches": len(fixtures),
            "goals": goals,
            "goals_per_match": round(goals / len(fixtures), 2),
            "home_win_rate": round(
                sum(1 for m in fixtures if m.outcome == "home") / len(fixtures) * 100, 1),
            "draw_rate": round(
                sum(1 for m in fixtures if m.outcome == "draw") / len(fixtures) * 100, 1),
            "teams": len({m.home_slug for m in fixtures} | {m.away_slug for m in fixtures}),
        }
        if slug:
            entry["team_record"] = {
                k: v for k, v in _record(fixtures, slug).items()
                if k not in {"biggest_win", "biggest_defeat"}
            }
        else:
            table = standings(year, comp, graph=g)
            entry["champion"] = table["champion"]
            entry["top_three"] = [r["team"] for r in table["table"][:3]]
        rows.append(entry)

    return {
        "competition": competition_name(comp),
        "team": g.team_name(slug) if slug else None,
        "seasons": list(seasons),
        "comparison": rows,
        "notes": [],
    }


def find_derbies(
    season: int | None = None,
    competition: str | None = None,
    team: str | None = None,
    limit: int | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """Fixtures between traditional rivals (Fla-Flu, Gre-Nal, Derby Paulista...)."""
    g = _graph(graph)
    limit = _clamp_limit(limit)
    comp = _competition(competition)
    slug = _require_team(g, team) if team else None

    pool = g.matches_for(slug) if slug else g.matches
    fixtures = []
    for match in _filter(pool, competition=comp, season=season):
        name = rivalry_for(match.home_slug, match.away_slug)
        if name:
            fixtures.append((name, match))
    fixtures.sort(key=lambda pair: (pair[1].date or _dt.date.min), reverse=True)

    per_derby = Counter(name for name, _ in fixtures)
    return {
        "season": season,
        "competition": competition_name(comp) if comp else "All competitions",
        "team": g.team_name(slug) if slug else None,
        "total_matches": len(fixtures),
        "derbies": [{"derby": name, "matches": count}
                    for name, count in per_derby.most_common()],
        "matches": [{**match.to_dict(), "derby": name}
                    for name, match in fixtures[:limit]],
        "known_rivalries": sorted(set(RIVALRIES.values())),
        "notes": _coverage_note(g, comp, season),
    }


# ---------------------------------------------------------------------------
# 4. Player queries
# ---------------------------------------------------------------------------

_POSITION_GROUPS = {"GK", "DEF", "MID", "FWD"}


def _player_sort_key(sort_by: str):
    if sort_by == "name":
        return lambda p: (p.name.lower(),)
    if sort_by == "age":
        return lambda p: (p.age or 999, -(p.overall or 0))
    if sort_by == "potential":
        return lambda p: (-(p.potential or 0), -(p.overall or 0), p.name)
    return lambda p: (-(p.overall or 0), -(p.potential or 0), p.name)


def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    brazilian_clubs_only: bool = False,
    sort_by: str = "overall",
    limit: int | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """Search the FIFA player database on any combination of attributes.

    ``position`` accepts either a precise FIFA code (``"LW"``, ``"CDM"``) or a
    coarse group (``"GK"``, ``"DEF"``, ``"MID"``, ``"FWD"``).
    """
    g = _graph(graph)
    limit = _clamp_limit(limit)

    pool: Sequence[Player] = g.players
    if club:
        club_slug = g.resolve_team(club).slug
        if club_slug and club_slug in g.players_by_club:
            pool = g.players_by_club[club_slug]
        else:
            pool, _ = _players_by_club_name(g, club)
    if nationality:
        key = normalize_text(nationality)
        if pool is g.players and key in g.players_by_nationality:
            pool = g.players_by_nationality[key]
        else:
            pool = [p for p in pool if normalize_text(p.nationality or "") == key]

    name_key = normalize_text(name) if name else None
    position_key = (position or "").strip().upper()
    is_group = position_key in _POSITION_GROUPS
    brazilian_club_slugs = {s for s in g.players_by_club if s in g.teams}

    results = []
    for player in pool:
        if name_key and name_key not in normalize_text(player.name):
            continue
        if position_key:
            if is_group:
                if player.position_group != position_key:
                    continue
            elif (player.position or "").upper() != position_key:
                continue
        if min_overall is not None and (player.overall or 0) < min_overall:
            continue
        if max_overall is not None and (player.overall or 0) > max_overall:
            continue
        if min_age is not None and (player.age or 0) < min_age:
            continue
        if max_age is not None and (player.age or 999) > max_age:
            continue
        if brazilian_clubs_only and player.club_slug not in brazilian_club_slugs:
            continue
        results.append(player)

    results.sort(key=_player_sort_key(sort_by))

    notes: list[str] = []
    if name and not results:
        close = difflib.get_close_matches(
            name_key or "", [normalize_text(p.name) for p in g.players], n=5, cutoff=0.7)
        if close:
            lookup = {normalize_text(p.name): p.name for p in g.players}
            notes.append("No player matched. Did you mean: "
                         + ", ".join(dict.fromkeys(lookup[c] for c in close)) + "?")
    if position_key and not results:
        known = sorted({(p.position or "").upper() for p in g.players if p.position})
        notes.append(
            f"No player matched position {position!r}. Use a group (GK, DEF, MID, "
            f"FWD) or one of: {', '.join(known)}.")
    if club and not results:
        notes.append(
            f"No FIFA 19 players found for club {club!r}. The FIFA 19 dataset only "
            "licenses 15 Brazilian clubs; Flamengo, Palmeiras, Corinthians, "
            "São Paulo, Vasco da Gama and Cruzeiro's rivals are largely absent.")

    return {
        "query": {
            "name": name, "nationality": nationality, "club": club,
            "position": position or None, "min_overall": min_overall,
            "max_overall": max_overall, "min_age": min_age, "max_age": max_age,
            "brazilian_clubs_only": brazilian_clubs_only, "sort_by": sort_by,
        },
        "total_players": len(results),
        "returned": min(len(results), limit),
        "players": [p.to_dict() for p in results[:limit]],
        "notes": notes,
    }


def player_profile(name: str, graph: KnowledgeGraph | None = None) -> dict[str, Any]:
    """Full attribute profile for one player, matched by name.

    Exact matches win; otherwise the highest-rated substring match is used, and
    other candidates are returned so the caller can disambiguate.
    """
    g = _graph(graph)
    key = normalize_text(name)
    if not key:
        raise QueryError("Give a player name to look up.")

    exact = [p for p in g.players if normalize_text(p.name) == key]
    partial = [p for p in g.players if key in normalize_text(p.name)]
    candidates = exact or partial
    if not candidates:
        close = difflib.get_close_matches(
            key, [normalize_text(p.name) for p in g.players], n=5, cutoff=0.7)
        lookup = {normalize_text(p.name): p.name for p in g.players}
        hint = (" Did you mean: " + ", ".join(dict.fromkeys(lookup[c] for c in close)) + "?"
                if close else "")
        raise QueryError(f"No player called {name!r} in the FIFA dataset.{hint}")

    candidates.sort(key=lambda p: (-(p.overall or 0), p.name))
    player = candidates[0]
    club_team = g.team(player.club_slug) if player.club_slug else None
    profile = player.to_dict(include_skills=True)
    profile["best_skills"] = [
        {"attribute": k, "rating": v}
        for k, v in sorted(player.skills.items(), key=lambda kv: -kv[1])[:8]
    ]
    profile["club_in_match_data"] = bool(
        club_team and g.matches_for(player.club_slug))
    if profile["club_in_match_data"]:
        profile["club_matches_in_dataset"] = len(g.matches_for(player.club_slug))
    return {
        "player": profile,
        "other_matches": [p.to_dict() for p in candidates[1:6]],
        "notes": ["FIFA 19 snapshot: ratings, club and age are as of the 2018/19 "
                  "season and do not reflect later transfers."],
    }


def club_squad(
    club: str,
    limit: int | None = None,
    min_overall: int | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """The FIFA squad registered to a club, best rated first.

    The club is looked up in the match graph first.  When that club has no
    FIFA squad -- either because FIFA 19 did not license it, or because the
    club only exists in the player file (Real Madrid, FC Barcelona) -- we fall
    back to searching the FIFA club column by whole-token name match, and
    report the club under the name the players are actually registered to.
    """
    g = _graph(graph)
    limit = _clamp_limit(limit)
    resolution = g.resolve_team(club)
    slug = resolution.slug
    squad = list(g.players_by_club.get(slug, [])) if slug else []
    label = resolution.name if resolution.matched else club
    name_search = False
    others: list[str] = []
    if not squad:
        squad, others = _players_by_club_name(g, club)
        if squad:
            name_search = True
            label = squad[0].club
            slug = squad[0].club_slug
    if min_overall is not None:
        squad = [p for p in squad if (p.overall or 0) >= min_overall]

    ratings = [p.overall for p in squad if p.overall is not None]
    ages = [p.age for p in squad if p.age is not None]
    notes: list[str] = []
    if not squad:
        notes.append(
            f"No FIFA 19 players are registered to {club!r}. FIFA 19 only "
            "licensed 15 Brazilian clubs, so many major sides (Flamengo, "
            "Palmeiras, Corinthians, São Paulo, Vasco da Gama) have no "
            "player rows in this dataset.")
    elif name_search:
        notes.append(
            f"{club!r} is not a club in the match datasets; this squad comes "
            f"from searching the FIFA club column, which matched {label!r}.")
        if others:
            notes.append("Other clubs matching that name: " + ", ".join(others))
    return {
        "club": label,
        "club_slug": slug,
        "other_clubs_matching_the_name": others,
        "squad_size": len(squad),
        "average_overall": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "average_age": round(sum(ages) / len(ages), 1) if ages else None,
        "brazilian_players": sum(1 for p in squad if p.is_brazilian),
        "by_position_group": [
            {"group": group, "players": count}
            for group, count in Counter(p.position_group for p in squad).most_common()
        ],
        "players": [p.to_dict() for p in squad[:limit]],
        "returned": min(len(squad), limit),
        "notes": notes,
    }


def brazilian_players_by_club(
    min_players: int = 1,
    limit: int | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """Where Brazilian players play: club-by-club counts and average ratings.

    This is a cross-file query -- it joins the FIFA player table to the clubs
    that appear in the match datasets, which is how "Brazilian players at
    Brazilian clubs" is answered.
    """
    g = _graph(graph)
    limit = _clamp_limit(limit)
    brazilians = g.players_by_nationality.get("brazil", [])

    per_club: dict[str, list[Player]] = defaultdict(list)
    for player in brazilians:
        if player.club_slug:
            per_club[player.club_slug].append(player)

    rows = []
    for slug, group in per_club.items():
        if len(group) < min_players:
            continue
        ratings = [p.overall for p in group if p.overall is not None]
        in_match_data = slug in g.teams and bool(g.matches_for(slug))
        rows.append({
            "club": group[0].club,
            "club_slug": slug,
            "players": len(group),
            "average_overall": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "best_player": max(group, key=lambda p: p.overall or 0).name,
            "best_overall": max((p.overall or 0) for p in group),
            "club_appears_in_match_data": in_match_data,
        })
    rows.sort(key=lambda r: (-r["players"], -(r["average_overall"] or 0)))

    at_brazilian_clubs = [r for r in rows if r["club_appears_in_match_data"]]
    return {
        "total_brazilian_players": len(brazilians),
        "clubs": len(rows),
        "top_rated": [p.to_dict() for p in sorted(
            brazilians, key=lambda p: (-(p.overall or 0), p.name))[:10]],
        "by_club": rows[:limit],
        "at_clubs_present_in_match_data": at_brazilian_clubs[:limit],
        "notes": ["`club_appears_in_match_data` is True when the same club also "
                  "appears in the Brazilian match datasets, which is the join "
                  "between the player and match sides of the graph."],
    }


# ---------------------------------------------------------------------------
# 5. Introspection
# ---------------------------------------------------------------------------

def resolve_team(name: str, graph: KnowledgeGraph | None = None) -> dict[str, Any]:
    """Explain how a team name is normalised and what data exists for it."""
    g = _graph(graph)
    resolution = g.resolve_team(name)
    if not resolution.matched or resolution.slug is None:
        return {
            "query": name,
            "matched": False,
            "message": resolution.message,
            "suggestions": [g.team_name(s) for s in resolution.alternatives],
        }
    team = g.team(resolution.slug)
    fixtures = g.matches_for(resolution.slug)
    seasons = sorted({m.season for m in fixtures if m.season is not None})
    return {
        "query": name,
        "matched": True,
        "team": team.to_dict(),
        "matches_in_data": len(fixtures),
        "seasons": f"{seasons[0]}-{seasons[-1]}" if seasons else None,
        "competitions": sorted({competition_name(m.competition) for m in fixtures}),
        "fifa_squad_size": len(g.squad(resolution.slug)),
        "other_clubs_with_similar_names": [
            g.team_name(s) for s in dict.fromkeys(
                (*resolution.alternatives, *g.namesakes(resolution.slug)))
            if s != resolution.slug],
    }


def dataset_summary(graph: KnowledgeGraph | None = None) -> dict[str, Any]:
    """What is loaded: files, row counts, competitions, seasons, coverage."""
    g = _graph(graph)
    summary = g.summary()
    summary["notes"] = [
        "Overlapping fixtures across the source files are merged into one match "
        f"({summary['matches']['merged_duplicates']} duplicate rows folded in), so "
        "aggregate statistics are not double counted.",
        "The datasets contain no goalscorer, lineup or referee information.",
    ]
    return summary
