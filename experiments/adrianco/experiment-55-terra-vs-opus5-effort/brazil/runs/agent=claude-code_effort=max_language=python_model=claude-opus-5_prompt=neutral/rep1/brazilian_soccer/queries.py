"""Query and analytics layer.

Context
-------
Every MCP tool is a thin wrapper around one function in this module.  Functions
take the :class:`~brazilian_soccer.graph.KnowledgeGraph` plus plain arguments
and return JSON-friendly dictionaries; rendering lives in
:mod:`brazilian_soccer.formatting` so the same result can be printed for a human
or handed to a model as structured output.

Conventions
-----------
* An unresolvable team or competition returns ``{"error": ..., "suggestions":
  [...]}`` instead of raising -- an LLM can then retry with a better name.
* Standings are *calculated* from match results (3 points for a win); the CSVs
  contain no tables, no goalscorers and no cards, so anything that cannot be
  derived is reported as unavailable rather than guessed.
* League tables drop teams with an implausibly low number of matches: the
  extended stats file mislabels one 2016 Campeonato Brasiliense fixture as
  Série A, which would otherwise put Brasília and Taguatinga in the 2015 table.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date
from statistics import median
from typing import Any, Iterable, Sequence

from .graph import KnowledgeGraph, TeamNode
from .loaders import parse_date
from .models import Match, Player, TeamRecord
from .names import DERBIES, normalize_query, search_clubs

__all__ = [
    "find_matches",
    "head_to_head",
    "team_stats",
    "team_profile",
    "team_rankings",
    "search_players",
    "player_profile",
    "team_squad",
    "standings",
    "knockout_bracket",
    "competition_stats",
    "biggest_wins",
    "derbies",
    "compare_seasons",
    "search_teams",
    "dataset_overview",
]

_DEFAULT_LIMIT = 20
_RELEGATION_SPOTS = 4
#: Hard ceiling on list-shaped answers.  A tool result is read by a model, so an
#: unbounded "show me every match" would waste an entire context window; the
#: total is always reported so nothing is silently hidden.
_MAX_LIMIT = 200
#: Level ties are reported, never decided.  The away goals rule is tempting --
#: it does explain some results -- but the data itself disproves applying it
#: blindly: the 2015 Copa do Brasil final finished 2-2 with Santos ahead on away
#: goals, and Palmeiras won it on penalties.  Shootouts are absent from every
#: file, so the honest answer is the aggregate plus the away goals split.
_LEVEL_TIE_NOTE = "Level on aggregate - no shootout data, so the winner is not derivable."


def _display(graph: KnowledgeGraph, team_id: str) -> str:
    node = graph.teams.get(team_id)
    return node.display if node else team_id


def _clamp(limit: int | None) -> int:
    """Normalise a caller supplied limit (``0``/negative/None mean "as many as allowed")."""
    if not limit or limit < 0:
        return _MAX_LIMIT
    return min(limit, _MAX_LIMIT)


# --------------------------------------------------------------------------
# Resolution helpers
# --------------------------------------------------------------------------


def _resolve_team(graph: KnowledgeGraph, text: str, label: str = "team") -> TeamNode | dict[str, Any]:
    node = graph.find_team(text)
    if node is not None:
        return node
    suggestions = [item.display for item in graph.suggest_teams(text, limit=8)]
    if not suggestions:
        suggestions = [club.name for club in search_clubs(text, limit=8)]
    return {
        "error": f"No {label} matching {text!r} in the dataset.",
        "suggestions": suggestions,
    }


def _resolve_competition(graph: KnowledgeGraph, text: str | None) -> Any:
    if not text:
        return None
    competition = graph.competition(text)
    if competition is None:
        return {
            "error": f"Unknown competition {text!r}.",
            "suggestions": [graph.competition_name(cid) for cid in graph.competition_ids()],
        }
    return competition


def _is_error(value: Any) -> bool:
    return isinstance(value, dict) and "error" in value


_VENUES = {"home", "away", "any"}


def _check_venue(home_away: str) -> dict[str, Any] | None:
    """Reject an unknown venue filter rather than silently answering "any"."""
    if home_away in _VENUES:
        return None
    return {
        "error": f"Unknown home_away value {home_away!r}.",
        "suggestions": sorted(_VENUES),
    }


def _check_dates(*values: str | None) -> dict[str, Any] | None:
    """Reject an unparseable date rather than silently dropping the filter."""
    for value in values:
        if value and _as_date(value) is None:
            return {
                "error": f"Could not read the date {value!r}.",
                "suggestions": ["2023-09-24", "24/09/2023", "2023"],
            }
    return None


def _as_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    parsed, _ = parse_date(str(value))
    if parsed is None and str(value).strip().isdigit() and len(str(value).strip()) == 4:
        return date(int(str(value).strip()), 1, 1)
    return parsed


def _stage_matches(needle: str, label: str) -> bool:
    """Word-boundary stage match so "Final" does not select "Semifinals"."""
    return re.search(rf"\b{re.escape(needle)}\b", label) is not None


def _filter_matches(
    matches: Iterable[Match],
    *,
    competition_id: str | None = None,
    season: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    stage: str | None = None,
    played_only: bool = False,
) -> list[Match]:
    stage_needle = normalize_query(stage) if stage else None
    selected: list[Match] = []
    for match in matches:
        if competition_id and match.competition_id != competition_id:
            continue
        if season is not None and match.season != season:
            continue
        if date_from and (match.date is None or match.date < date_from):
            continue
        if date_to and (match.date is None or match.date > date_to):
            continue
        if stage_needle:
            label = normalize_query(match.stage_label or "")
            if not _stage_matches(stage_needle, label):
                continue
        if played_only and not match.played:
            continue
        selected.append(match)
    return selected


def _sorted_matches(matches: Sequence[Match], newest_first: bool = True) -> list[Match]:
    return sorted(
        matches,
        key=lambda match: (match.date or date.min, match.competition_id, match.home_team),
        reverse=newest_first,
    )


def _record(team_id: str, team_name: str, matches: Iterable[Match]) -> TeamRecord:
    record = TeamRecord(team_id=team_id, team_name=team_name)
    for match in matches:
        if not match.played or not match.involves(team_id):
            continue
        record.add(match.goals_for(team_id) or 0, match.goals_against(team_id) or 0)
    return record


# --------------------------------------------------------------------------
# 1. Match queries
# --------------------------------------------------------------------------


def find_matches(
    graph: KnowledgeGraph,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    home_away: str = "any",
    stage: str | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Matches filtered by team, opponent, competition, season and date range."""
    team_node = opponent_node = None
    if team:
        resolved = _resolve_team(graph, team)
        if _is_error(resolved):
            return resolved
        team_node = resolved
    if opponent:
        resolved = _resolve_team(graph, opponent, label="opponent")
        if _is_error(resolved):
            return resolved
        opponent_node = resolved

    competition_ref = _resolve_competition(graph, competition)
    if _is_error(competition_ref):
        return competition_ref
    invalid = _check_venue(home_away) or _check_dates(date_from, date_to)
    if invalid:
        return invalid
    if home_away != "any" and team_node is None:
        return {
            "error": '"home_away" filters relative to a team, so a team is required.',
            "suggestions": ["pass team=..., or use team_rankings for a league-wide split"],
        }

    if team_node is not None:
        candidates: Iterable[Match] = graph.team_matches(team_node.id)
    elif competition_ref is not None:
        candidates = graph.competition_matches(competition_ref.id, season)
    else:
        candidates = graph.matches

    selected = _filter_matches(
        candidates,
        competition_id=competition_ref.id if competition_ref else None,
        season=season,
        date_from=_as_date(date_from),
        date_to=_as_date(date_to),
        stage=stage,
    )

    if opponent_node is not None:
        selected = [match for match in selected if match.involves(opponent_node.id)]
    if team_node is not None and home_away in {"home", "away"}:
        want_home = home_away == "home"
        selected = [match for match in selected if match.is_home(team_node.id) == want_home]

    ordered = _sorted_matches(selected)
    capped = _clamp(limit)
    result: dict[str, Any] = {
        "team": team_node.display if team_node else None,
        "opponent": opponent_node.display if opponent_node else None,
        "competition": competition_ref.name if competition_ref else None,
        "season": season,
        "home_away": home_away,
        "total": len(ordered),
        "returned": min(capped, len(ordered)),
        "matches": [match.to_dict() for match in ordered[:capped]],
    }
    if team_node is not None and opponent_node is not None:
        result["head_to_head"] = _head_to_head_summary(team_node, opponent_node, ordered)
        result["derby"] = _derby_name(team_node.id, opponent_node.id)
    elif team_node is not None:
        result["record"] = _record(team_node.id, team_node.display, ordered).to_dict()
    return result


def _head_to_head_summary(
    team_a: TeamNode, team_b: TeamNode, matches: Sequence[Match]
) -> dict[str, Any]:
    record = _record(team_a.id, team_a.display, matches)
    return {
        "team_a": team_a.display,
        "team_b": team_b.display,
        "matches": record.played,
        "team_a_wins": record.wins,
        "team_b_wins": record.losses,
        "draws": record.draws,
        "team_a_goals": record.goals_for,
        "team_b_goals": record.goals_against,
    }


def _derby_name(team_a: str, team_b: str) -> str | None:
    pair = {team_a, team_b}
    for first, second, name in DERBIES:
        if {first, second} == pair:
            return name
    return None


def head_to_head(
    graph: KnowledgeGraph,
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Full head-to-head record between two clubs."""
    first = _resolve_team(graph, team_a)
    if _is_error(first):
        return first
    second = _resolve_team(graph, team_b, label="opponent")
    if _is_error(second):
        return second
    if first.id == second.id:
        return {"error": f"{first.display} cannot play itself.", "suggestions": []}

    competition_ref = _resolve_competition(graph, competition)
    if _is_error(competition_ref):
        return competition_ref

    matches = _filter_matches(
        (match for match in graph.team_matches(first.id) if match.involves(second.id)),
        competition_id=competition_ref.id if competition_ref else None,
        season=season,
    )
    ordered = _sorted_matches(matches)
    played = [match for match in ordered if match.played]

    by_competition: dict[str, TeamRecord] = {}
    for match in played:
        record = by_competition.setdefault(
            match.competition, TeamRecord(first.id, first.display)
        )
        record.add(match.goals_for(first.id) or 0, match.goals_against(first.id) or 0)

    biggest_a = max(
        (m for m in played if m.winner_id == first.id),
        key=lambda m: (m.goal_difference or 0, m.total_goals or 0),
        default=None,
    )
    biggest_b = max(
        (m for m in played if m.winner_id == second.id),
        key=lambda m: (m.goal_difference or 0, m.total_goals or 0),
        default=None,
    )

    limit = _clamp(limit)
    return {
        "summary": _head_to_head_summary(first, second, played),
        "derby": _derby_name(first.id, second.id),
        "competition": competition_ref.name if competition_ref else None,
        "season": season,
        "first_meeting": played[-1].to_dict() if played else None,
        "last_meeting": played[0].to_dict() if played else None,
        "biggest_win_team_a": biggest_a.to_dict() if biggest_a else None,
        "biggest_win_team_b": biggest_b.to_dict() if biggest_b else None,
        "by_competition": {
            name: record.to_dict() for name, record in sorted(by_competition.items())
        },
        "recent_matches": [match.to_dict() for match in ordered[:limit]],
        "total": len(ordered),
    }


# --------------------------------------------------------------------------
# 2. Team queries
# --------------------------------------------------------------------------


def _splits(team_id: str, matches: Sequence[Match]) -> dict[str, TeamRecord]:
    home = TeamRecord(team_id, "home")
    away = TeamRecord(team_id, "away")
    for match in matches:
        if not match.played:
            continue
        target = home if match.is_home(team_id) else away
        target.add(match.goals_for(team_id) or 0, match.goals_against(team_id) or 0)
    return {"home": home, "away": away}


def team_stats(
    graph: KnowledgeGraph,
    team: str,
    season: int | None = None,
    competition: str | None = None,
    home_away: str = "any",
) -> dict[str, Any]:
    """Win/draw/loss record, goals and form for a club."""
    node = _resolve_team(graph, team)
    if _is_error(node):
        return node
    competition_ref = _resolve_competition(graph, competition)
    if _is_error(competition_ref):
        return competition_ref
    invalid = _check_venue(home_away)
    if invalid:
        return invalid

    matches = _filter_matches(
        graph.team_matches(node.id),
        competition_id=competition_ref.id if competition_ref else None,
        season=season,
        played_only=True,
    )
    if home_away in {"home", "away"}:
        want_home = home_away == "home"
        matches = [match for match in matches if match.is_home(node.id) == want_home]

    ordered = _sorted_matches(matches)
    record = _record(node.id, node.display, matches)
    splits = _splits(node.id, matches)
    clean_sheets = sum(1 for match in matches if (match.goals_against(node.id) or 0) == 0)
    failed_to_score = sum(1 for match in matches if (match.goals_for(node.id) or 0) == 0)

    per_competition: dict[str, TeamRecord] = {}
    per_season: dict[int, TeamRecord] = {}
    for match in matches:
        competition_record = per_competition.setdefault(
            match.competition, TeamRecord(node.id, node.display)
        )
        competition_record.add(match.goals_for(node.id) or 0, match.goals_against(node.id) or 0)
        if match.season is not None:
            season_record = per_season.setdefault(match.season, TeamRecord(node.id, node.display))
            season_record.add(match.goals_for(node.id) or 0, match.goals_against(node.id) or 0)

    biggest_win = max(
        (m for m in matches if m.winner_id == node.id),
        key=lambda m: (m.goal_difference or 0, m.total_goals or 0),
        default=None,
    )
    heaviest_defeat = max(
        (m for m in matches if m.loser_id == node.id),
        key=lambda m: (m.goal_difference or 0, m.total_goals or 0),
        default=None,
    )

    return {
        "team": node.display,
        "team_id": node.id,
        "season": season,
        "competition": competition_ref.name if competition_ref else None,
        "home_away": home_away,
        "record": record.to_dict(),
        "home": splits["home"].to_dict(),
        "away": splits["away"].to_dict(),
        "clean_sheets": clean_sheets,
        "failed_to_score": failed_to_score,
        "goals_per_match": round(record.goals_for / record.played, 2) if record.played else 0.0,
        "conceded_per_match": (
            round(record.goals_against / record.played, 2) if record.played else 0.0
        ),
        "by_competition": {
            name: value.to_dict() for name, value in sorted(per_competition.items())
        },
        "by_season": {year: value.to_dict() for year, value in sorted(per_season.items())},
        "biggest_win": biggest_win.to_dict() if biggest_win else None,
        "heaviest_defeat": heaviest_defeat.to_dict() if heaviest_defeat else None,
        "form": [
            {"outcome": match.outcome_for(node.id), **match.to_dict()} for match in ordered[:5]
        ],
    }


def team_profile(graph: KnowledgeGraph, team: str) -> dict[str, Any]:
    """Everything the graph knows about one club, across all files."""
    node = _resolve_team(graph, team)
    if _is_error(node):
        return node

    matches = graph.team_matches(node.id)
    played = [match for match in matches if match.played]
    record = _record(node.id, node.display, played)
    seasons = sorted(node.seasons)
    dates = [match.date for match in matches if match.date]

    per_competition: dict[str, TeamRecord] = {}
    for match in played:
        competition_record = per_competition.setdefault(
            match.competition, TeamRecord(node.id, node.display)
        )
        competition_record.add(match.goals_for(node.id) or 0, match.goals_against(node.id) or 0)

    opponents = Counter(match.opponent_of(node.id) for match in played)
    titles = _league_titles(graph, node.id)
    squad = graph.team_players(node.id)

    return {
        "team": node.display,
        "team_id": node.id,
        "state": node.state_name,
        "country": node.country,
        "name_variants": [name for name, _ in node.spellings.most_common()],
        "matches": len(matches),
        "first_match": min(dates).isoformat() if dates else None,
        "last_match": max(dates).isoformat() if dates else None,
        "seasons": seasons,
        "competitions": sorted(node.competitions),
        "record": record.to_dict(),
        "by_competition": {
            name: value.to_dict() for name, value in sorted(per_competition.items())
        },
        "most_played_opponents": [
            {"team": graph.teams[team_id].display if team_id in graph.teams else team_id,
             "matches": count}
            for team_id, count in opponents.most_common(5)
            if team_id
        ],
        "serie_a_titles": titles,
        "fifa_squad_size": len(squad),
        "fifa_squad_top": [player.to_dict() for player in
                           sorted(squad, key=lambda p: -(p.overall or 0))[:5]],
    }


def _league_titles(graph: KnowledgeGraph, team_id: str) -> list[int]:
    """Seasons in which *team_id* topped a complete Série A table."""
    cache: dict[str, list[int]] = graph.cache.setdefault("serie_a_champions", {})  # type: ignore[attr-defined]
    if not cache:
        for season in graph.seasons("serie-a"):
            table = standings(graph, "serie-a", season)
            if table.get("complete") and table.get("table"):
                cache.setdefault(table["table"][0]["team_id"], []).append(season)
    return sorted(cache.get(team_id, []))


def team_rankings(
    graph: KnowledgeGraph,
    metric: str = "points",
    competition: str | None = None,
    season: int | None = None,
    home_away: str = "any",
    limit: int = 10,
    min_matches: int | None = None,
    ascending: bool = False,
) -> dict[str, Any]:
    """Rank teams by points, wins, win rate, goals or clean sheets.

    Answers "which team has the best home record?" (``metric="win_rate"``,
    ``home_away="home"``) and "which team scored the most goals in Série A
    2023?" (``metric="goals_for"``).
    """
    metrics = {
        "points": lambda r: r.points,
        "wins": lambda r: r.wins,
        "draws": lambda r: r.draws,
        "losses": lambda r: r.losses,
        "win_rate": lambda r: r.win_rate,
        "points_per_game": lambda r: r.points_per_game,
        "goals_for": lambda r: r.goals_for,
        "goals_against": lambda r: r.goals_against,
        "goal_difference": lambda r: r.goal_difference,
        "matches": lambda r: r.played,
    }
    if metric not in metrics:
        return {"error": f"Unknown metric {metric!r}.", "suggestions": sorted(metrics)}

    competition_ref = _resolve_competition(graph, competition)
    if _is_error(competition_ref):
        return competition_ref
    invalid = _check_venue(home_away)
    if invalid:
        return invalid

    if competition_ref is not None:
        pool = graph.competition_matches(competition_ref.id, season)
    else:
        pool = graph.matches
    matches = _filter_matches(pool, season=season, played_only=True)

    records: dict[str, TeamRecord] = {}
    for match in matches:
        for team_id, is_home in ((match.home_team, True), (match.away_team, False)):
            if home_away == "home" and not is_home:
                continue
            if home_away == "away" and is_home:
                continue
            node = graph.teams.get(team_id)
            record = records.setdefault(
                team_id, TeamRecord(team_id, node.display if node else team_id)
            )
            record.add(match.goals_for(team_id) or 0, match.goals_against(team_id) or 0)

    if min_matches is None:
        # Scale the qualification bar to the busiest club in the selection: a
        # quarter of a full league season keeps every team, while ranking across
        # all competitions stops a club with three away games from "having the
        # best away record".
        played_counts = [record.played for record in records.values()]
        min_matches = max(3, int(max(played_counts) * 0.25)) if played_counts else 0
    limit = _clamp(limit)
    eligible = [record for record in records.values() if record.played >= min_matches]
    # Negate rather than reverse: with reverse=True the tie-breakers would
    # invert too, ranking the worse goal difference first.
    direction = 1 if ascending else -1
    eligible.sort(
        key=lambda r: (direction * metrics[metric](r), -r.goal_difference, -r.goals_for,
                       r.team_name)
    )

    return {
        "metric": metric,
        "competition": competition_ref.name if competition_ref else "all competitions",
        "season": season,
        "home_away": home_away,
        "min_matches": min_matches,
        "teams_considered": len(eligible),
        "ranking": [
            {"rank": index, "value": round(metrics[metric](record), 2), **record.to_dict()}
            for index, record in enumerate(eligible[:limit], start=1)
        ],
    }


# --------------------------------------------------------------------------
# 3. Player queries
# --------------------------------------------------------------------------


def _match_players_by_name(
    players: Iterable[Player], name: str
) -> tuple[list[Player], list[Player]]:
    """Return ``(substring matches, fuzzy token matches)`` for a player name.

    ``fifa_data.csv`` stores short display names ("Gabriel Jesus", "L. Messi"),
    so a full name such as "Gabriel Barbosa" often has no substring match.  The
    fuzzy list shares at least one name token and is ranked by how many tokens
    it shares, which lets the caller offer alternatives instead of a bare miss.
    """
    needle = normalize_query(name)
    if not needle:
        return [], []
    pool = list(players)
    direct = [player for player in pool if needle in player.search_name]
    if direct:
        return direct, []
    tokens = set(needle.split())
    scored = [
        (len(tokens & set(player.search_name.split())), player.overall or 0, player)
        for player in pool
    ]
    fuzzy = [item for item in scored if item[0]]
    fuzzy.sort(key=lambda item: (-item[0], -item[1]))
    return [], [player for _, _, player in fuzzy]


def _player_sort_key(sort_by: str):
    keys = {
        "overall": lambda p: (-(p.overall or 0), p.name),
        "potential": lambda p: (-(p.potential or 0), p.name),
        "age": lambda p: (p.age or 999, p.name),
        "value": lambda p: (-(p.value_eur or 0), p.name),
        "name": lambda p: (p.search_name,),
    }
    return keys.get(sort_by, keys["overall"])


def search_players(
    graph: KnowledgeGraph,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_age: int | None = None,
    sort_by: str = "overall",
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Search the FIFA player database by name, nationality, club or position."""
    candidates: Iterable[Player] = graph.players
    club_node = None
    notes: list[str] = []

    if nationality:
        candidates = graph.nationality_players(nationality)
        if not candidates:
            available = sorted({player.nationality for player in graph.players})
            close = [item for item in available if normalize_query(nationality) in normalize_query(item)]
            return {
                "error": f"No players with nationality {nationality!r}.",
                "suggestions": close[:10] or available[:10],
            }

    if club:
        club_node = graph.find_team(club)
        club_needle = normalize_query(club)
        if club_node is not None and club_node.id in graph.players_by_team:
            club_players = {player.player_id for player in graph.team_players(club_node.id)}
            candidates = [player for player in candidates if player.player_id in club_players]
        else:
            candidates = [
                player for player in candidates if club_needle in normalize_query(player.club)
            ]
            if not candidates:
                return {
                    "error": (
                        f"No players found for club {club!r}. The FIFA file only covers "
                        f"{len(graph.club_links)} Brazilian clubs."
                    ),
                    "suggestions": sorted(graph.club_links),
                }

    if name:
        direct, fuzzy = _match_players_by_name(candidates, name)
        candidates = direct or fuzzy
        if fuzzy:
            notes.append(
                f"No player name contains {name!r}; showing the closest names in the file."
            )
    if position:
        wanted = {item.strip().upper() for item in position.split(",") if item.strip()}
        candidates = [player for player in candidates if player.position.upper() in wanted]
    if min_overall is not None:
        candidates = [player for player in candidates if (player.overall or 0) >= min_overall]
    if max_age is not None:
        candidates = [player for player in candidates if (player.age or 999) <= max_age]

    limit = _clamp(limit)
    ordered = sorted(candidates, key=_player_sort_key(sort_by))
    if club_node is not None and club_node.id in graph.players_by_team:
        notes.append(
            f"Club matched to graph team {club_node.display} "
            f"({graph.teams[club_node.id].match_count} matches in the match data)."
        )

    return {
        "filters": {
            "name": name,
            "nationality": nationality,
            "club": club,
            "position": position,
            "min_overall": min_overall,
            "max_age": max_age,
            "sort_by": sort_by,
        },
        "total": len(ordered),
        "players": [player.to_dict() for player in ordered[:limit]],
        "notes": notes,
    }


def player_profile(graph: KnowledgeGraph, name: str) -> dict[str, Any]:
    """Full attributes for the best matching player."""
    needle = normalize_query(name)
    matches, fuzzy = _match_players_by_name(graph.players, name)
    if not matches:
        return {
            "error": (
                f"No player named {name!r} in fifa_data.csv (a FIFA 19 snapshot, so recent "
                "signings and unlicensed clubs are missing)."
            ),
            "suggestions": [
                f"{player.name} ({player.club or 'no club'}, {player.overall})"
                for player in fuzzy[:8]
            ],
        }
    exact = [player for player in matches if player.search_name == needle]
    pool = exact or matches
    player = max(pool, key=lambda item: (item.overall or 0))

    club_team = graph.teams.get(player.club_team_id) if player.club_team_id else None
    profile = player.to_dict()
    profile.update(
        {
            "potential": player.potential,
            "preferred_foot": player.preferred_foot,
            "work_rate": player.work_rate,
            "international_reputation": player.international_reputation,
            "joined": player.joined,
            "contract_valid_until": player.contract_valid_until,
            "release_clause": player.release_clause_eur,
            "top_skills": [{"skill": skill, "rating": rating} for skill, rating in player.top_skills(8)],
            "skills": dict(player.skills),
            "club_in_match_data": club_team.display if club_team else None,
        }
    )
    return {
        "player": profile,
        "other_matches": [item.to_dict() for item in pool[:5] if item.player_id != player.player_id],
        "total_name_matches": len(matches),
    }


def team_squad(graph: KnowledgeGraph, team: str, limit: int = 30) -> dict[str, Any]:
    """FIFA squad for a club, joined to its match-data record (cross-file query)."""
    node = _resolve_team(graph, team)
    if _is_error(node):
        return node
    limit = _clamp(limit)
    squad = sorted(graph.team_players(node.id), key=lambda player: -(player.overall or 0))
    if not squad:
        return {
            "team": node.display,
            "team_id": node.id,
            "squad_size": 0,
            "players": [],
            "note": (
                f"{node.display} has no entry in fifa_data.csv (the file only licenses "
                f"{len(graph.club_links)} Brazilian clubs)."
            ),
            "clubs_with_players": sorted(graph.club_links),
        }
    ratings = [player.overall for player in squad if player.overall is not None]
    record = _record(node.id, node.display, graph.team_matches(node.id))
    return {
        "team": node.display,
        "team_id": node.id,
        "squad_size": len(squad),
        "average_overall": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "average_age": (
            round(sum(p.age for p in squad if p.age) / sum(1 for p in squad if p.age), 1)
            if any(p.age for p in squad)
            else None
        ),
        "players": [player.to_dict() for player in squad[:limit]],
        "match_record": record.to_dict(),
        "seasons": sorted(graph.teams[node.id].seasons),
    }


# --------------------------------------------------------------------------
# 4. Competition queries
# --------------------------------------------------------------------------


def standings(graph: KnowledgeGraph, competition: str, season: int) -> dict[str, Any]:
    """League table calculated from match results (3pts win, 1pt draw)."""
    competition_ref = _resolve_competition(graph, competition)
    if _is_error(competition_ref):
        return competition_ref
    if competition_ref is None:
        return {"error": "A competition is required.", "suggestions": []}
    if competition_ref.kind != "league":
        return {
            "error": (
                f"{competition_ref.name} is a knockout competition -- it has no league table. "
                "Use the bracket tool instead."
            ),
            "suggestions": ["knockout_bracket"],
        }

    matches = _filter_matches(
        graph.competition_matches(competition_ref.id, season), played_only=True
    )
    if not matches:
        return {
            "error": f"No {competition_ref.name} matches for season {season}.",
            "suggestions": [str(year) for year in graph.seasons(competition_ref.id)],
        }

    records: dict[str, TeamRecord] = {}
    for match in matches:
        for team_id in match.teams:
            node = graph.teams.get(team_id)
            record = records.setdefault(
                team_id, TeamRecord(team_id, node.display if node else team_id)
            )
            record.add(match.goals_for(team_id) or 0, match.goals_against(team_id) or 0)

    counts = [record.played for record in records.values()]
    threshold = max(1, int(median(counts) * 0.5)) if counts else 0
    excluded = [record.team_name for record in records.values() if record.played < threshold]
    table = [record for record in records.values() if record.played >= threshold]
    # CBF order of merit: points, wins, goal difference, goals scored.  Wins
    # matter -- in 2019 Santos (22 wins) finish above Palmeiras (21) on equal
    # points, and in Série B 2017 the criterion decides who is relegated.
    table.sort(key=lambda r: (-r.points, -r.wins, -r.goal_difference, -r.goals_for, r.team_name))

    teams = len(table)
    expected = teams * (teams - 1)
    # Count only matches between the teams that made the table: the outlier
    # filter above can drop matches, which would otherwise make a season with
    # holes in it look complete.
    ranked = {record.team_id for record in table}
    counted = sum(1 for match in matches if set(match.teams) <= ranked)
    complete = (
        counted >= expected
        and teams >= 8
        and all(record.played == 2 * (teams - 1) for record in table)
    )

    rows = []
    for position, record in enumerate(table, start=1):
        row = record.to_dict()
        row["position"] = position
        rows.append(row)

    notes = [
        "Table calculated from match results in the dataset (3 points for a win).",
    ]
    if excluded:
        notes.append(
            "Excluded as data outliers (too few matches): " + ", ".join(sorted(excluded)) + "."
        )
    if not complete:
        short = sorted(
            f"{record.team_name} ({record.played})"
            for record in table
            if record.played != 2 * (teams - 1)
        )
        detail = f"; clubs short of {2 * (teams - 1)} matches: " + ", ".join(short) if short else ""
        notes.append(
            f"Season looks incomplete: {counted} of {expected} expected matches between "
            f"these {teams} clubs are present{detail}. Champion and relegation are not asserted."
        )

    result: dict[str, Any] = {
        "competition": competition_ref.name,
        "season": season,
        "matches": len(matches),
        "teams": teams,
        "complete": complete,
        "table": rows,
        "notes": notes,
    }
    if complete:
        result["champion"] = rows[0]["team"]
        result["runner_up"] = rows[1]["team"] if len(rows) > 1 else None
        if teams >= 16:
            result["relegated"] = [row["team"] for row in rows[-_RELEGATION_SPOTS:]]
    return result


def _tie_key(match: Match) -> tuple[str, ...]:
    return tuple(sorted(match.teams))


def knockout_bracket(graph: KnowledgeGraph, competition: str, season: int) -> dict[str, Any]:
    """Stage-by-stage bracket with two-legged ties aggregated."""
    competition_ref = _resolve_competition(graph, competition)
    if _is_error(competition_ref):
        return competition_ref
    if competition_ref is None:
        return {"error": "A competition is required.", "suggestions": []}
    if competition_ref.kind != "cup":
        return {
            "error": (
                f"{competition_ref.name} is a league -- it is played as a round robin, "
                "not a bracket. Use the standings tool instead."
            ),
            "suggestions": ["standings"],
        }

    matches = graph.competition_matches(competition_ref.id, season)
    if not matches:
        return {
            "error": f"No {competition_ref.name} matches for season {season}.",
            "suggestions": [str(year) for year in graph.seasons(competition_ref.id)],
        }

    stage_order = [
        "Group stage", "Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Final",
    ]

    def stage_rank(name: str) -> tuple[int, int, str]:
        if name in stage_order:
            return (1, stage_order.index(name), "")
        numbered = re.fullmatch(r"Round (\d+)", name)
        if numbered:  # qualifying rounds run *before* the named stages
            return (0, int(numbered.group(1)), "")
        return (2, 0, name)

    by_stage: dict[str, list[Match]] = defaultdict(list)
    for match in matches:
        by_stage[match.stage_label or "Unknown stage"].append(match)

    stages = []
    for stage_name in sorted(by_stage, key=stage_rank):
        stage_matches = by_stage[stage_name]
        if stage_name == "Group stage":
            stages.append(
                {
                    "stage": stage_name,
                    "matches": len(stage_matches),
                    "ties": [],
                    "sample": [m.to_dict() for m in _sorted_matches(stage_matches)[:6]],
                }
            )
            continue
        ties: dict[tuple[str, ...], list[Match]] = defaultdict(list)
        for match in stage_matches:
            ties[_tie_key(match)].append(match)
        stage_ties = []
        for teams, legs in ties.items():
            legs = _sorted_matches(legs, newest_first=False)
            aggregate = {team: 0 for team in teams}
            away_goals = {team: 0 for team in teams}
            for leg in legs:
                if not leg.played:
                    continue
                aggregate[leg.home_team] += leg.home_goals or 0
                aggregate[leg.away_team] += leg.away_goals or 0
                away_goals[leg.away_team] += leg.away_goals or 0
            ranked = sorted(aggregate.items(), key=lambda item: -item[1])
            winner_id, decided_by, note = None, None, None
            if len(ranked) == 2 and ranked[0][1] != ranked[1][1]:
                winner_id, decided_by = ranked[0][0], "aggregate"
            elif len(ranked) == 2:
                by_away = sorted(away_goals.items(), key=lambda item: -item[1])
                note = _LEVEL_TIE_NOTE
                if len(legs) == 2 and by_away[0][1] != by_away[1][1]:
                    note += f" {_display(graph, by_away[0][0])} scored more away goals."
            stage_ties.append(
                {
                    "teams": [_display(graph, team) for team in teams],
                    "legs": [leg.to_dict() for leg in legs],
                    "aggregate": {
                        _display(graph, team): goals for team, goals in aggregate.items()
                    },
                    "away_goals": {
                        _display(graph, team): goals for team, goals in away_goals.items()
                    },
                    "winner": _display(graph, winner_id) if winner_id else None,
                    "decided_by": decided_by,
                    "note": note,
                }
            )
        stage_ties.sort(key=lambda tie: tie["teams"])
        stages.append({"stage": stage_name, "matches": len(stage_matches), "ties": stage_ties})

    final_stage = next((stage for stage in stages if stage["stage"] == "Final"), None)
    champion = None
    if final_stage and final_stage["ties"]:
        champion = final_stage["ties"][0]["winner"]

    notes = []
    if all(stage["stage"] == "Unknown stage" for stage in stages):
        notes.append(
            f"No round or stage labels exist for {competition_ref.name} {season} -- that "
            "season only appears in the extended statistics file, which has no round "
            "column. The ties below are grouped by opponent, not arranged by stage."
        )
    return {
        "competition": competition_ref.name,
        "season": season,
        "matches": len(matches),
        "stages": stages,
        "champion": champion,
        "notes": notes + [
            "Ties are aggregated over both legs. The datasets contain no penalty "
            "shootouts, and away goals did not always settle these ties -- the 2015 "
            "Copa do Brasil final finished 2-2 with Santos ahead on away goals, yet "
            "Palmeiras won on penalties -- so a level tie is reported as undecided.",
        ],
    }


def competition_stats(
    graph: KnowledgeGraph,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Aggregate statistics: goals per match, home advantage, biggest wins."""
    competition_ref = _resolve_competition(graph, competition)
    if _is_error(competition_ref):
        return competition_ref

    if competition_ref is not None:
        pool = graph.competition_matches(competition_ref.id, season)
    else:
        pool = graph.matches
    matches = _filter_matches(pool, season=season, played_only=True)
    if not matches:
        return {
            "error": "No matches for that competition/season combination.",
            "suggestions": [graph.competition_name(cid) for cid in graph.competition_ids()],
        }

    total_goals = sum(match.total_goals or 0 for match in matches)
    home_wins = sum(1 for match in matches if match.result == "home")
    away_wins = sum(1 for match in matches if match.result == "away")
    draws = len(matches) - home_wins - away_wins
    home_goals = sum(match.home_goals or 0 for match in matches)
    away_goals = sum(match.away_goals or 0 for match in matches)

    scorelines = Counter(f"{match.home_goals}-{match.away_goals}" for match in matches)
    ranking = team_rankings(
        graph,
        metric="goals_for",
        competition=competition_ref.id if competition_ref else None,
        season=season,
        limit=5,
    )

    return {
        "competition": competition_ref.name if competition_ref else "all competitions",
        "season": season,
        "matches": len(matches),
        "goals": total_goals,
        "goals_per_match": round(total_goals / len(matches), 2),
        "home_win_rate": round(home_wins / len(matches) * 100, 1),
        "draw_rate": round(draws / len(matches) * 100, 1),
        "away_win_rate": round(away_wins / len(matches) * 100, 1),
        "home_goals": home_goals,
        "away_goals": away_goals,
        "goalless_matches": sum(1 for match in matches if (match.total_goals or 0) == 0),
        "common_scorelines": [
            {"score": score, "count": count} for score, count in scorelines.most_common(5)
        ],
        "biggest_wins": [
            match.to_dict()
            for match in sorted(
                matches, key=lambda m: (-(m.goal_difference or 0), -(m.total_goals or 0))
            )[:5]
        ],
        "highest_scoring": [
            match.to_dict()
            for match in sorted(matches, key=lambda m: -(m.total_goals or 0))[:5]
        ],
        "top_scoring_teams": ranking.get("ranking", []),
        "seasons_available": (
            graph.seasons(competition_ref.id) if competition_ref else graph.seasons()
        ),
        "notes": [
            "The datasets contain no goalscorer, card or lineup data, so individual top "
            "scorers cannot be derived.",
        ],
    }


def biggest_wins(
    graph: KnowledgeGraph,
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Largest winning margins, optionally filtered by team/competition/season."""
    competition_ref = _resolve_competition(graph, competition)
    if _is_error(competition_ref):
        return competition_ref
    node = None
    if team:
        node = _resolve_team(graph, team)
        if _is_error(node):
            return node

    if node is not None:
        pool: Iterable[Match] = graph.team_matches(node.id)
    elif competition_ref is not None:
        pool = graph.competition_matches(competition_ref.id, season)
    else:
        pool = graph.matches
    matches = _filter_matches(
        pool,
        competition_id=competition_ref.id if competition_ref else None,
        season=season,
        played_only=True,
    )
    if node is not None:
        matches = [match for match in matches if match.winner_id == node.id]

    limit = _clamp(limit)
    ordered = sorted(
        matches, key=lambda m: (-(m.goal_difference or 0), -(m.total_goals or 0), m.date or date.min)
    )
    return {
        "competition": competition_ref.name if competition_ref else "all competitions",
        "season": season,
        "team": node.display if node else None,
        "total_considered": len(matches),
        "matches": [match.to_dict() for match in ordered[:limit]],
    }


def derbies(
    graph: KnowledgeGraph,
    season: int | None = None,
    competition: str | None = None,
    team: str | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    """Matches between traditional rivals (Fla-Flu, Gre-Nal, Derby Paulista...)."""
    competition_ref = _resolve_competition(graph, competition)
    if _is_error(competition_ref):
        return competition_ref
    node = None
    if team:
        node = _resolve_team(graph, team)
        if _is_error(node):
            return node

    rivalries = [
        (first, second, name)
        for first, second, name in DERBIES
        if node is None or node.id in (first, second)
    ]
    wanted = {frozenset((first, second)): name for first, second, name in rivalries}

    pool = graph.team_matches(node.id) if node is not None else graph.matches
    matches = _filter_matches(
        pool,
        competition_id=competition_ref.id if competition_ref else None,
        season=season,
    )
    found = [
        (match, wanted[key])
        for match in matches
        if (key := frozenset(match.teams)) in wanted
    ]
    limit = _clamp(limit)
    found = sorted(found, key=lambda item: item[0].date or date.min, reverse=True)

    by_name = Counter(name for _, name in found)
    return {
        "season": season,
        "competition": competition_ref.name if competition_ref else None,
        "team": node.display if node else None,
        "total": len(found),
        "by_derby": [{"derby": name, "matches": count} for name, count in by_name.most_common()],
        "matches": [{"derby": name, **match.to_dict()} for match, name in found[:limit]],
    }


def compare_seasons(
    graph: KnowledgeGraph, competition: str, seasons: Sequence[int]
) -> dict[str, Any]:
    """Side-by-side aggregate comparison of two or more seasons."""
    competition_ref = _resolve_competition(graph, competition)
    if _is_error(competition_ref):
        return competition_ref
    if competition_ref is None:
        return {"error": "A competition is required.", "suggestions": []}
    if len(seasons) < 2:
        return {"error": "Give at least two seasons to compare.", "suggestions": []}

    comparison = []
    for season in seasons:
        stats = competition_stats(graph, competition_ref.id, season)
        if _is_error(stats):
            return stats
        entry = {
            "season": season,
            "matches": stats["matches"],
            "goals": stats["goals"],
            "goals_per_match": stats["goals_per_match"],
            "home_win_rate": stats["home_win_rate"],
            "draw_rate": stats["draw_rate"],
            "away_win_rate": stats["away_win_rate"],
        }
        if competition_ref.kind == "league":
            table = standings(graph, competition_ref.id, season)
            if not _is_error(table) and table.get("table"):
                leader = table["table"][0]
                # Only a finished season has a champion; 2023 is truncated in
                # the source data, so it gets a leader instead.
                key = "champion" if table.get("complete") else "leader"
                entry[key] = leader["team"]
                entry["champion_points" if key == "champion" else "leader_points"] = (
                    leader["points"]
                )
                entry["complete"] = bool(table.get("complete"))
                entry["top_scorer_team"] = max(
                    table["table"], key=lambda row: row["goals_for"]
                )["team"]
        comparison.append(entry)

    return {
        "competition": competition_ref.name,
        "seasons": list(seasons),
        "comparison": comparison,
    }


# --------------------------------------------------------------------------
# 5. Discovery helpers
# --------------------------------------------------------------------------


def search_teams(graph: KnowledgeGraph, query: str, limit: int = 10) -> dict[str, Any]:
    """Resolve a name and show which spellings map onto the same club."""
    node = graph.find_team(query)
    suggestions = graph.suggest_teams(query, limit=limit)
    return {
        "query": query,
        "resolved": node.to_dict() if node else None,
        "candidates": [item.to_dict() for item in suggestions],
    }


def dataset_overview(graph: KnowledgeGraph) -> dict[str, Any]:
    """Coverage of the loaded files: competitions, seasons, teams, players."""
    stats = graph.stats()
    competitions = []
    for competition_id in graph.competition_ids():
        seasons = graph.seasons(competition_id)
        matches = graph.matches_by_competition[competition_id]
        competitions.append(
            {
                "competition": graph.competition_name(competition_id),
                "id": competition_id,
                "matches": len(matches),
                "seasons": f"{seasons[0]}-{seasons[-1]}" if seasons else "n/a",
                "season_list": seasons,
            }
        )
    nationalities = Counter(player.nationality for player in graph.players if player.nationality)
    return {
        "summary": stats,
        "competitions": competitions,
        "top_nationalities": [
            {"nationality": name, "players": count} for name, count in nationalities.most_common(5)
        ],
        "linked_fifa_clubs": sorted(graph.club_links),
        "notes": [
            "Matches present in several source files are merged into a single record; "
            "provenance is kept in each match's 'sources' field.",
            "No goalscorer, card, lineup or transfer data exists in these files.",
            *(
                [
                    "Source rows dropped as impossible: "
                    + ", ".join(f"{count} with a {reason}" for reason, count in stats["dropped_rows"].items())
                    + "."
                ]
                if stats.get("dropped_rows")
                else []
            ),
        ],
    }
