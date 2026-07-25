"""Query layer: every question the MCP server can answer.

Each function takes a :class:`~.graph.KnowledgeGraph` and returns plain
JSON-serializable dictionaries, so the same results can be rendered as text for
an LLM (see :mod:`brazilian_soccer.formatting`) or consumed programmatically by
tests. Team arguments are free text — ``"Flamengo"``, ``"flamengo-rj"``,
``"Palmeiras-SP"`` and ``"sao paulo"`` all resolve through the registry.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date

from .graph import KnowledgeGraph
from .models import DRAW, HOME, AWAY, Match, Player, TeamRecord
from .normalization import normalize_competition, parse_date, slugify

ANY = "any"
DEFAULT_LIMIT = 20


class UnknownTeamError(ValueError):
    """Raised when a team name cannot be resolved to a club in the data."""

    def __init__(self, query: str, suggestions: list[str] | None = None) -> None:
        self.query = query
        self.suggestions = suggestions or []
        hint = f" Did you mean: {', '.join(self.suggestions)}?" if self.suggestions else ""
        super().__init__(f"No team matching '{query}' in the dataset.{hint}")


class UnknownCompetitionError(ValueError):
    """Raised when a competition name cannot be normalized."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def resolve_team_id(graph: KnowledgeGraph, query: str) -> str:
    """Resolve free text to a canonical team id or raise :class:`UnknownTeamError`."""
    team = graph.resolve_team(query)
    if team is None:
        # Offer clubs starting with the same few letters, but only when there is
        # enough of a name to make the suggestions meaningful.
        stem = str(query).strip()[:4]
        suggestions = ([t.name for t in graph.registry.search(stem, limit=5)]
                       if len(stem) >= 3 else [])
        raise UnknownTeamError(str(query), suggestions)
    return team.team_id


def resolve_competition(value: str | None) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    competition = normalize_competition(value)
    if competition is None:
        raise UnknownCompetitionError(
            f"Unknown competition '{value}'. Known: Brasileirão Série A/B/C, "
            f"Copa do Brasil, Copa Libertadores."
        )
    return competition


def match_to_dict(graph: KnowledgeGraph, match: Match) -> dict:
    """JSON-friendly view of a match, with display names resolved."""
    return {
        "match_id": match.match_id,
        "date": match.date.isoformat() if match.date else None,
        "competition": match.competition,
        "season": match.season,
        "round": match.round,
        "stage": match.stage,
        "home_team": graph.team_name(match.home_team),
        "away_team": graph.team_name(match.away_team),
        "home_team_id": match.home_team,
        "away_team_id": match.away_team,
        "home_goals": match.home_goals,
        "away_goals": match.away_goals,
        "score": (f"{match.home_goals}-{match.away_goals}" if match.played else None),
        "venue": match.venue,
        "result": match.result,
        "winner": graph.team_name(match.winner) if match.winner else None,
        "sources": list(match.sources),
        "stats": dict(match.stats),
    }


def player_to_dict(player: Player, graph: KnowledgeGraph | None = None) -> dict:
    data = {
        "player_id": player.player_id,
        "name": player.name,
        "age": player.age,
        "nationality": player.nationality,
        "overall": player.overall,
        "potential": player.potential,
        "club": player.club,
        "club_team_id": player.club_team_id,
        "position": player.position,
        "jersey_number": player.jersey_number,
        "height": player.height,
        "weight": player.weight,
        "value": player.value,
        "wage": player.wage,
        "preferred_foot": player.preferred_foot,
    }
    if graph is not None and player.club_team_id:
        data["club_in_match_data"] = bool(graph.team_matches(player.club_team_id))
    return data


def _filter_matches(
    graph: KnowledgeGraph,
    team_id: str | None = None,
    opponent_id: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    season_from: int | None = None,   # inclusive season range, used by
    season_to: int | None = None,     # callers that span several years
    date_from: date | None = None,
    date_to: date | None = None,
    venue: str = ANY,
    stage: str | None = None,
    played_only: bool = False,
) -> list[Match]:
    """Shared filtering used by every match-oriented query."""
    if team_id:
        pool = graph.team_matches(team_id)
    elif competition and season is not None:
        pool = graph.matches_by_competition_season.get((competition, season), [])
    elif competition:
        pool = graph.matches_by_competition.get(competition, [])
    else:
        pool = graph.matches

    stage_needle = slugify(stage) if stage else None
    found = []
    for match in pool:
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
        if opponent_id and not match.involves(opponent_id):
            continue
        if opponent_id and team_id and match.opponent_of(team_id) != opponent_id:
            continue
        if team_id and venue == HOME and match.home_team != team_id:
            continue
        if team_id and venue == AWAY and match.away_team != team_id:
            continue
        if stage_needle and not _stage_matches(match, stage_needle):
            continue
        if played_only and not match.played:
            continue
        found.append(match)
    return found


def _stage_matches(match: Match, needle: str) -> bool:
    """Does ``match`` belong to the stage/round the caller asked for?

    Word boundaries matter both ways: "final" must not match "semifinals", and
    a numbered round is only consulted when the query carries a number, so that
    ``stage="round"`` does not match every match in the dataset.
    """
    pattern = rf"\b{re.escape(needle)}\b"
    if match.stage and re.search(pattern, slugify(match.stage)):
        return True
    if match.round is not None and any(ch.isdigit() for ch in needle):
        return bool(re.search(pattern, slugify(f"round {match.round}")))
    return False


def _limit(value: int | None, default: int = DEFAULT_LIMIT) -> int:
    """Clamp a caller-supplied limit; negative values would slice from the end."""
    if value is None:
        return default
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def _sorted_recent(matches: list[Match]) -> list[Match]:
    return sorted(matches, key=lambda m: (m.date is not None, m.date or date.min),
                  reverse=True)


# --------------------------------------------------------------------------- #
# 1. Match queries
# --------------------------------------------------------------------------- #

def search_matches(
    graph: KnowledgeGraph,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str = ANY,
    stage: str | None = None,
    limit: int = DEFAULT_LIMIT,
    newest_first: bool = True,
) -> dict:
    """Find matches by team, opponent, competition, season, date range or stage."""
    if venue in (HOME, AWAY) and not team:
        raise ValueError(
            f"venue='{venue}' only means something with a team; pass a team or "
            f"use venue='any'."
        )
    team_id = resolve_team_id(graph, team) if team else None
    opponent_id = resolve_team_id(graph, opponent) if opponent else None
    competition_name = resolve_competition(competition)

    matches = _filter_matches(
        graph,
        team_id=team_id,
        opponent_id=opponent_id,
        competition=competition_name,
        season=int(season) if season is not None else None,
        date_from=parse_date(date_from),
        date_to=parse_date(date_to),
        venue=venue,
        stage=stage,
    )
    ordered = _sorted_recent(matches) if newest_first else sorted(
        matches, key=lambda m: (m.date is None, m.date or date.min))
    limit = _limit(limit)

    return {
        "query": {
            "team": graph.team_name(team_id) if team_id else None,
            "opponent": graph.team_name(opponent_id) if opponent_id else None,
            "competition": competition_name,
            "season": season,
            "date_from": date_from,
            "date_to": date_to,
            "venue": venue,
            "stage": stage,
        },
        "total": len(matches),
        "returned": min(len(ordered), limit),
        "matches": [match_to_dict(graph, m) for m in ordered[:limit]],
    }


def last_meeting(graph: KnowledgeGraph, team_a: str, team_b: str) -> dict:
    """The most recent match between two teams ("When did X last play Y?")."""
    a_id = resolve_team_id(graph, team_a)
    b_id = resolve_team_id(graph, team_b)
    matches = [m for m in _filter_matches(graph, team_id=a_id, opponent_id=b_id)
               if m.played and m.date]
    if not matches:
        return {"found": False, "team_a": graph.team_name(a_id),
                "team_b": graph.team_name(b_id), "match": None}
    latest = max(matches, key=lambda m: m.date)
    return {
        "found": True,
        "team_a": graph.team_name(a_id),
        "team_b": graph.team_name(b_id),
        "match": match_to_dict(graph, latest),
        "total_meetings": len(matches),
    }


# --------------------------------------------------------------------------- #
# 2. Team queries
# --------------------------------------------------------------------------- #

def team_stats(
    graph: KnowledgeGraph,
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = ANY,
) -> dict:
    """Win/draw/loss record and goals for a team, optionally filtered."""
    team_id = resolve_team_id(graph, team)
    competition_name = resolve_competition(competition)
    matches = _filter_matches(
        graph, team_id=team_id, competition=competition_name,
        season=int(season) if season is not None else None, venue=venue,
        played_only=True,
    )
    record = TeamRecord(team_id)
    for match in matches:
        record.add(match)

    # Only actual wins qualify: a club with no win in the selected scope should
    # get no "biggest win" rather than its least-bad draw or defeat.
    biggest = max(
        (m for m in matches if m.winner == team_id),
        key=lambda m: (m.goals_for(team_id) - m.goals_against(team_id),
                       m.goals_for(team_id)),
        default=None,
    )
    result = record.as_dict(graph.team_name(team_id))
    result.update({
        "season": season,
        "competition": competition_name,
        "venue": venue,
        "goals_per_match": round(record.goals_for / record.matches, 2) if record.matches else 0.0,
        "conceded_per_match": round(record.goals_against / record.matches, 2) if record.matches else 0.0,
        "points_per_match": round(record.points_per_match, 2),
        "biggest_win": match_to_dict(graph, biggest) if biggest else None,
        "competitions": sorted({m.competition for m in matches}),
        "seasons": sorted({m.season for m in matches if m.season is not None}),
    })
    return result


def team_profile(graph: KnowledgeGraph, team: str) -> dict:
    """Everything the graph knows about one club."""
    team_id = resolve_team_id(graph, team)
    club = graph.registry.get(team_id)
    matches = graph.team_matches(team_id)
    played = [m for m in matches if m.played]

    by_competition = {}
    for competition in sorted({m.competition for m in matches}):
        record = TeamRecord(team_id)
        seasons = set()
        for match in played:
            if match.competition == competition:
                record.add(match)
                if match.season is not None:
                    seasons.add(match.season)
        by_competition[competition] = {
            **record.as_dict(club.name),
            "seasons": sorted(seasons),
        }

    overall = TeamRecord(team_id)
    for match in played:
        overall.add(match)

    dates = [m.date for m in matches if m.date]
    opponents = Counter(m.opponent_of(team_id) for m in played)
    squad = graph.players_by_club.get(team_id, [])
    return {
        "team": club.name,
        "team_id": team_id,
        "state": club.state,
        "country": club.country,
        "known_as": sorted(club.aliases)[:10],
        "matches": len(matches),
        "first_match": min(dates).isoformat() if dates else None,
        "last_match": max(dates).isoformat() if dates else None,
        "overall": overall.as_dict(club.name),
        "competitions": by_competition,
        "most_played_opponents": [
            {"team": graph.team_name(other), "matches": count}
            for other, count in opponents.most_common(5)
        ],
        "squad_size_in_fifa_data": len(squad),
        "top_rated_player": (
            {"name": squad[0].name, "overall": squad[0].overall} if squad else None
        ),
    }


def head_to_head(
    graph: KnowledgeGraph,
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict:
    """Head-to-head record and match list for two clubs."""
    a_id = resolve_team_id(graph, team_a)
    b_id = resolve_team_id(graph, team_b)
    if a_id == b_id:
        raise ValueError("head_to_head needs two different teams")
    competition_name = resolve_competition(competition)
    matches = _filter_matches(
        graph, team_id=a_id, opponent_id=b_id, competition=competition_name,
        season=int(season) if season is not None else None,
    )
    played = [m for m in matches if m.played]

    record_a, record_b = TeamRecord(a_id), TeamRecord(b_id)
    for match in played:
        record_a.add(match)
        record_b.add(match)

    by_competition = Counter(m.competition for m in matches)
    ordered = _sorted_recent(matches)
    limit = _limit(limit, 10)
    return {
        "team_a": graph.team_name(a_id),
        "team_b": graph.team_name(b_id),
        "competition": competition_name,
        "season": season,
        "total_matches": len(matches),
        "played_matches": len(played),
        "team_a_wins": record_a.wins,
        "team_b_wins": record_b.wins,
        "draws": record_a.draws,
        "team_a_goals": record_a.goals_for,
        "team_b_goals": record_b.goals_for,
        "by_competition": dict(by_competition),
        "first_meeting": (
            match_to_dict(graph, ordered[-1]) if ordered else None
        ),
        "last_meeting": match_to_dict(graph, ordered[0]) if ordered else None,
        "matches": [match_to_dict(graph, m) for m in ordered[:limit]],
    }


def compare_teams(graph: KnowledgeGraph, team_a: str, team_b: str,
                  season: int | None = None,
                  competition: str | None = None) -> dict:
    """Side-by-side records plus the head-to-head between two clubs."""
    return {
        "team_a": team_stats(graph, team_a, season=season, competition=competition),
        "team_b": team_stats(graph, team_b, season=season, competition=competition),
        "head_to_head": head_to_head(graph, team_a, team_b,
                                     competition=competition, season=season),
    }


def list_teams(graph: KnowledgeGraph, query: str = "", limit: int = 25) -> dict:
    """Search the club list (used to disambiguate names)."""
    found = graph.registry.search(query, limit=None)
    teams = found[:_limit(limit, 25)]
    return {
        "query": query,
        "total": len(found),
        "returned": len(teams),
        "teams": [
            {
                "team_id": team.team_id,
                "name": team.name,
                "state": team.state,
                "country": team.country,
                "matches": len(graph.team_matches(team.team_id)),
            }
            for team in teams
        ],
    }


# --------------------------------------------------------------------------- #
# 3. Player queries
# --------------------------------------------------------------------------- #

_POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
    "midfielder": {"CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM",
                   "LM", "RM"},
    "forward": {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"},
}


def _position_matches(player: Player, wanted: str) -> bool:
    if not player.position:
        return False
    wanted_slug = slugify(wanted)
    group = _POSITION_GROUPS.get(wanted_slug)
    if group:
        return player.position.upper() in group
    return player.position.upper() == wanted.upper().strip()


def search_players(
    graph: KnowledgeGraph,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_age: int | None = None,
    sort_by: str = "overall",
    limit: int = DEFAULT_LIMIT,
) -> dict:
    """Search the FIFA player dataset by any combination of attributes."""
    club_team = graph.resolve_team(club) if club else None
    if name:
        pool = graph.find_players(name)
    elif club:
        team = club_team
        if team is not None and graph.players_by_club.get(team.team_id):
            pool = graph.players_by_club[team.team_id]
        else:                                     # fall back to raw club text
            needle = slugify(club)
            pool = [p for p in graph.players if p.club and needle in slugify(p.club)]
    elif nationality:
        pool = graph.players_by_nationality.get(nationality.strip().title(), [])
        if not pool:
            needle = slugify(nationality)
            pool = [p for p in graph.players if needle in slugify(p.nationality)]
    else:
        pool = graph.players

    found = []
    for player in pool:
        if nationality and slugify(nationality) not in slugify(player.nationality):
            continue
        if club:
            club_ok = (
                (club_team is not None and player.club_team_id == club_team.team_id)
                or (player.club and slugify(club) in slugify(player.club))
            )
            if not club_ok:
                continue
        if position and not _position_matches(player, position):
            continue
        if min_overall is not None and (player.overall or 0) < int(min_overall):
            continue
        if max_age is not None and (player.age or 0) > int(max_age):
            continue
        found.append(player)

    keys = {
        "overall": lambda p: (-(p.overall or 0), p.name),
        "potential": lambda p: (-(p.potential or 0), p.name),
        "age": lambda p: (p.age or 999, p.name),
        "name": lambda p: p.name,
    }
    found.sort(key=keys.get(sort_by, keys["overall"]))
    limit = _limit(limit)

    return {
        "query": {
            "name": name, "nationality": nationality, "club": club,
            "position": position, "min_overall": min_overall, "max_age": max_age,
            "sort_by": sort_by,
        },
        "total": len(found),
        "returned": min(len(found), limit),
        "players": [player_to_dict(p, graph) for p in found[:limit]],
    }


def player_profile(graph: KnowledgeGraph, name: str) -> dict:
    """Full profile for the best name match, with club context from match data."""
    candidates = graph.find_players(name, allow_fuzzy=False)
    if not candidates:
        # Never pass off a fuzzy hit as the requested player: suggest players
        # sharing the most distinctive part of the name instead, so that
        # "Gabriel Barbosa" (absent from the FIFA snapshot) still leads
        # somewhere useful.
        tokens = sorted(slugify(name).split(), key=len, reverse=True)
        suggestions: list[str] = []
        for token in tokens[:2]:
            suggestions += [p.name for p in graph.find_players(token)[:5]]
        return {"found": False, "query": name, "player": None,
                "alternatives": list(dict.fromkeys(suggestions))[:5]}
    player = candidates[0]
    profile = player_to_dict(player, graph)
    profile["skills"] = dict(sorted(player.skills.items(), key=lambda kv: -kv[1]))

    club_context = None
    if player.club_team_id:
        matches = graph.team_matches(player.club_team_id)
        played = [m for m in matches if m.played]
        if played:
            record = TeamRecord(player.club_team_id)
            for match in played:
                record.add(match)
            club_context = {
                "team": graph.team_name(player.club_team_id),
                **record.as_dict(graph.team_name(player.club_team_id)),
                "competitions": sorted({m.competition for m in played}),
                "last_match": match_to_dict(graph, _sorted_recent(played)[0]),
            }
    return {
        "found": True,
        "query": name,
        "player": profile,
        "club_context": club_context,
        "alternatives": [p.name for p in candidates[1:6]],
    }


def club_squad(graph: KnowledgeGraph, club: str, limit: int = 15,
               nationality: str | None = None) -> dict:
    """Squad from the FIFA data for a club, ordered by rating."""
    team = graph.resolve_team(club)
    team_id = team.team_id if team else None
    players = graph.players_by_club.get(team_id, []) if team_id else []
    if not players:
        needle = slugify(club)
        players = sorted(
            (p for p in graph.players if p.club and needle in slugify(p.club)),
            key=lambda p: -(p.overall or 0),
        )
    if nationality:
        players = [p for p in players
                   if slugify(nationality) in slugify(p.nationality)]
    ratings = [p.overall for p in players if p.overall is not None]
    limit = _limit(limit, 15)
    return {
        "club": team.name if team else club,
        "team_id": team_id,
        "squad_size": len(players),
        "average_overall": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "nationalities": dict(Counter(p.nationality for p in players).most_common(5)),
        "players": [player_to_dict(p, graph) for p in players[:limit]],
    }


def players_by_club_summary(graph: KnowledgeGraph, nationality: str = "Brazil",
                            only_clubs_in_match_data: bool = True,
                            limit: int = 15) -> dict:
    """Aggregate players of one nationality by club (cross-file query).

    ``only_clubs_in_match_data`` keeps clubs that also appear in the match data,
    which is how "Brazilian players at Brazilian clubs" is answered.
    """
    needle = slugify(nationality)
    buckets: dict[str, list[Player]] = defaultdict(list)
    for player in graph.players:
        if needle and needle not in slugify(player.nationality):
            continue
        if not player.club:
            continue
        if only_clubs_in_match_data:
            if not player.club_team_id or not graph.team_matches(player.club_team_id):
                continue
            buckets[graph.team_name(player.club_team_id)].append(player)
        else:
            buckets[player.club].append(player)

    rows = []
    for club, players in buckets.items():
        ratings = [p.overall for p in players if p.overall is not None]
        rows.append({
            "club": club,
            "players": len(players),
            "average_overall": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "best_player": max(players, key=lambda p: p.overall or 0).name,
        })
    rows.sort(key=lambda row: (-row["players"], -(row["average_overall"] or 0)))
    limit = _limit(limit, 15)
    return {
        "nationality": nationality,
        "clubs": len(rows),
        "total_players": sum(row["players"] for row in rows),
        "rows": rows[:limit],
    }


# --------------------------------------------------------------------------- #
# 4. Competition queries
# --------------------------------------------------------------------------- #

#: Number of teams relegated from the Brazilian first/second division.
RELEGATION_SPOTS = 4



def standings(graph: KnowledgeGraph, competition: str, season: int) -> dict:
    """League table calculated from match results (3 points for a win)."""
    competition_name = resolve_competition(competition)
    season = int(season)
    matches = [m for m in graph.matches_by_competition_season.get(
        (competition_name, season), []) if m.played]
    if not matches:
        return {"competition": competition_name, "season": season,
                "complete": False, "table": [], "matches": 0}

    # A handful of rows in the source data are labelled with the wrong
    # competition (a state-league match filed under "Serie A", say). Such teams
    # play a couple of matches where the real participants play dozens, so
    # anything below half the busiest team's tally is dropped from the table.
    appearances: Counter[str] = Counter()
    for match in matches:
        appearances[match.home_team] += 1
        appearances[match.away_team] += 1
    threshold = max(appearances.values()) / 2
    members = {team_id for team_id, count in appearances.items() if count >= threshold}
    excluded = sorted(graph.team_name(team_id) for team_id in appearances
                      if team_id not in members)
    matches = [m for m in matches
               if m.home_team in members and m.away_team in members]

    records: dict[str, TeamRecord] = {}
    for match in matches:
        for team_id in (match.home_team, match.away_team):
            records.setdefault(team_id, TeamRecord(team_id)).add(match)

    table = sorted(
        records.values(),
        key=lambda r: (-r.points, -r.wins, -r.goal_difference, -r.goals_for,
                       graph.team_name(r.team_id)),
    )
    teams = len(table)
    expected = teams * (teams - 1)
    missing = max(expected - len(matches), 0)
    # A champion is only named when every fixture is present: the 2023 Série A
    # is three matches short in the source data, and those three matches are
    # enough to change who finishes top.
    complete = missing == 0 and all(r.matches == 2 * (teams - 1) for r in table)
    league = competition_name.startswith("Brasileirão")

    rows = []
    for position, record in enumerate(table, start=1):
        row = record.as_dict(graph.team_name(record.team_id))
        row["position"] = position
        row["note"] = None
        if complete and league:
            if position == 1:
                row["note"] = "Champion"
            elif position <= 4:
                row["note"] = "Libertadores"
            elif position > teams - RELEGATION_SPOTS:
                row["note"] = "Relegated"
        rows.append(row)

    return {
        "competition": competition_name,
        "season": season,
        "teams": teams,
        "matches": len(matches),
        "complete": complete,
        "expected_matches": expected,
        "missing_matches": missing,
        "champion": rows[0]["team"] if complete and league else None,
        "relegated": [r["team"] for r in rows if r["note"] == "Relegated"],
        "excluded_teams": excluded,
        "table": rows,
    }


def competition_summary(graph: KnowledgeGraph, competition: str,
                        season: int | None = None) -> dict:
    """Coverage and aggregate numbers for a competition (optionally one season)."""
    competition_name = resolve_competition(competition)
    matches = _filter_matches(
        graph, competition=competition_name,
        season=int(season) if season is not None else None,
    )
    played = [m for m in matches if m.played]
    seasons = sorted({m.season for m in matches if m.season is not None})
    goals = sum(m.total_goals for m in played)
    home_wins = sum(1 for m in played if m.result == HOME)
    away_wins = sum(1 for m in played if m.result == AWAY)
    draws = sum(1 for m in played if m.result == DRAW)

    scorers = Counter()
    for match in played:
        scorers[match.home_team] += match.home_goals
        scorers[match.away_team] += match.away_goals

    return {
        "competition": competition_name,
        "season": season,
        "seasons": seasons,
        "matches": len(matches),
        "played": len(played),
        "teams": len({t for m in matches for t in (m.home_team, m.away_team)}),
        "goals": goals,
        "goals_per_match": round(goals / len(played), 2) if played else 0.0,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / len(played) * 100, 1) if played else 0.0,
        "draw_rate": round(draws / len(played) * 100, 1) if played else 0.0,
        "away_win_rate": round(away_wins / len(played) * 100, 1) if played else 0.0,
        "top_scoring_teams": [
            {"team": graph.team_name(team_id), "goals": count}
            for team_id, count in scorers.most_common(5)
        ],
    }


def list_competitions(graph: KnowledgeGraph) -> dict:
    """Which competitions and seasons are covered by the data."""
    rows = []
    for competition in graph.competitions:
        matches = graph.matches_by_competition[competition]
        seasons = sorted({m.season for m in matches if m.season is not None})
        rows.append({
            "competition": competition,
            "matches": len(matches),
            "seasons": seasons,
            "first_season": seasons[0] if seasons else None,
            "last_season": seasons[-1] if seasons else None,
        })
    return {"competitions": rows, "summary": graph.summary()}


def knockout_bracket(graph: KnowledgeGraph, competition: str, season: int) -> dict:
    """Matches of a cup season grouped by stage (Libertadores / Copa do Brasil)."""
    competition_name = resolve_competition(competition)
    matches = graph.matches_by_competition_season.get((competition_name, int(season)), [])
    stages: dict[str, list[dict]] = defaultdict(list)
    for match in sorted(matches, key=lambda m: (m.date or date.min)):
        label = match.stage or (f"round {match.round}"
                                if match.round else "round not recorded")
        stages[label].append(match_to_dict(graph, match))
    order = ["group stage", "round of 128", "round of 64", "round of 32",
             "round of 16", "quarterfinals", "semifinals", "final"]

    def stage_key(name: str) -> tuple:
        """Numbered early rounds first, then the named ladder, then the rest."""
        slug = slugify(name)
        numbered = re.fullmatch(r"round (\d+)", slug)
        if numbered:
            return (0, int(numbered.group(1)), name)
        if slug in order:
            return (1, order.index(slug), name)
        return (2, 0, name)

    return {
        "competition": competition_name,
        "season": int(season),
        "matches": len(matches),
        "stages": {name: stages[name] for name in sorted(stages, key=stage_key)},
    }


# --------------------------------------------------------------------------- #
# 5. Statistical analysis
# --------------------------------------------------------------------------- #

def biggest_wins(graph: KnowledgeGraph, competition: str | None = None,
                 season: int | None = None, team: str | None = None,
                 limit: int = 10) -> dict:
    """Largest margins of victory, optionally scoped to a team/competition."""
    team_id = resolve_team_id(graph, team) if team else None
    competition_name = resolve_competition(competition)
    matches = _filter_matches(
        graph, team_id=team_id, competition=competition_name,
        season=int(season) if season is not None else None, played_only=True,
    )
    if team_id:
        matches = [m for m in matches if m.winner == team_id]
    ranked = sorted(
        matches,
        key=lambda m: (-m.goal_difference, -m.total_goals,
                       m.date or date.min),
    )
    limit = _limit(limit, 10)
    return {
        "competition": competition_name,
        "season": season,
        "team": graph.team_name(team_id) if team_id else None,
        "matches": [
            {**match_to_dict(graph, m), "margin": m.goal_difference}
            for m in ranked[:limit]
        ],
    }


def team_rankings(graph: KnowledgeGraph, metric: str = "points",
                  competition: str | None = None, season: int | None = None,
                  venue: str = ANY, min_matches: int = 10,
                  limit: int = 10) -> dict:
    """Rank teams by a metric — the "best home record" style questions.

    Metrics: ``points``, ``wins``, ``win_rate``, ``goals_for``, ``goals_against``
    (fewest first), ``goal_difference``, ``points_per_match``.
    """
    competition_name = resolve_competition(competition)
    season_value = int(season) if season is not None else None
    pool = _filter_matches(graph, competition=competition_name,
                           season=season_value, played_only=True)

    records: dict[str, TeamRecord] = {}
    for match in pool:
        if venue in (ANY, HOME):
            records.setdefault(match.home_team, TeamRecord(match.home_team)).add(match)
        if venue in (ANY, AWAY):
            records.setdefault(match.away_team, TeamRecord(match.away_team)).add(match)

    eligible = [r for r in records.values() if r.matches >= min_matches]
    metrics = {
        "points": lambda r: (-r.points, -r.goal_difference),
        "wins": lambda r: (-r.wins, -r.goal_difference),
        "win_rate": lambda r: (-r.win_rate, -r.matches),
        "goals_for": lambda r: (-r.goals_for, -r.matches),
        "goals_against": lambda r: (r.goals_against, -r.matches),
        "goal_difference": lambda r: (-r.goal_difference, -r.points),
        "points_per_match": lambda r: (-r.points_per_match, -r.matches),
    }
    if metric not in metrics:
        raise ValueError(f"Unknown metric '{metric}'. Options: {sorted(metrics)}")
    eligible.sort(key=metrics[metric])
    limit = _limit(limit, 10)

    return {
        "metric": metric,
        "venue": venue,
        "competition": competition_name,
        "season": season,
        "min_matches": min_matches,
        "rows": [
            {**record.as_dict(graph.team_name(record.team_id)),
             "points_per_match": round(record.points_per_match, 2)}
            for record in eligible[:limit]
        ],
    }


def home_away_split(graph: KnowledgeGraph, team: str,
                    competition: str | None = None,
                    season: int | None = None) -> dict:
    """Compare a club's home and away performance."""
    home = team_stats(graph, team, season=season, competition=competition, venue=HOME)
    away = team_stats(graph, team, season=season, competition=competition, venue=AWAY)
    return {"team": home["team"], "season": season,
            "competition": resolve_competition(competition),
            "home": home, "away": away}


def compare_seasons(graph: KnowledgeGraph, competition: str,
                    seasons: list[int]) -> dict:
    """Aggregate statistics for several seasons side by side."""
    competition_name = resolve_competition(competition)
    rows = [competition_summary(graph, competition_name, season=int(s))
            for s in seasons]
    return {"competition": competition_name, "seasons": rows}


#: Traditional rivalries, used by :func:`derbies`.
RIVALRIES: tuple[tuple[str, str, str], ...] = (
    ("flamengo", "fluminense", "Fla-Flu"),
    ("flamengo", "vasco-da-gama", "Clássico dos Milhões"),
    ("flamengo", "botafogo", "Clássico da Rivalidade"),
    ("fluminense", "vasco-da-gama", "Clássico dos Gigantes"),
    ("botafogo", "vasco-da-gama", "Clássico da Amizade"),
    ("corinthians", "palmeiras", "Derby Paulista"),
    ("corinthians", "sao-paulo", "Majestoso"),
    ("corinthians", "santos", "Clássico Alvinegro"),
    ("palmeiras", "sao-paulo", "Choque-Rei"),
    ("palmeiras", "santos", "Clássico da Saudade"),
    ("santos", "sao-paulo", "San-São"),
    ("gremio", "internacional", "Grenal"),
    ("atletico-mineiro", "cruzeiro", "Clássico Mineiro"),
    ("athletico-paranaense", "coritiba", "Atletiba"),
    ("ceara", "fortaleza", "Clássico-Rei"),
    ("bahia", "vitoria", "Ba-Vi"),
    ("sport-recife", "santa-cruz", "Clássico das Multidões"),
    ("sport-recife", "nautico", "Clássico dos Clássicos"),
)


def derbies(graph: KnowledgeGraph, season: int | None = None,
            competition: str | None = None, limit: int = 50) -> dict:
    """Matches between traditional rivals, with the derby name attached."""
    competition_name = resolve_competition(competition)
    season_value = int(season) if season is not None else None
    rows = []
    for a_id, b_id, name in RIVALRIES:
        if a_id not in graph.teams or b_id not in graph.teams:
            continue
        matches = _filter_matches(graph, team_id=a_id, opponent_id=b_id,
                                  competition=competition_name, season=season_value)
        for match in _sorted_recent(matches):
            rows.append({"derby": name, **match_to_dict(graph, match)})
    rows.sort(key=lambda row: row["date"] or "", reverse=True)
    limit = _limit(limit, 50)
    return {
        "season": season,
        "competition": competition_name,
        "total": len(rows),
        "matches": rows[:limit],
    }


def overall_statistics(graph: KnowledgeGraph) -> dict:
    """Dataset-wide aggregates: coverage, goals, home advantage."""
    played = [m for m in graph.matches if m.played]
    goals = sum(m.total_goals for m in played)
    home_wins = sum(1 for m in played if m.result == HOME)
    draws = sum(1 for m in played if m.result == DRAW)
    first, last = graph.date_range()
    return {
        **graph.summary(),
        "played_matches": len(played),
        "total_goals": goals,
        "goals_per_match": round(goals / len(played), 2) if played else 0.0,
        "home_win_rate": round(home_wins / len(played) * 100, 1) if played else 0.0,
        "draw_rate": round(draws / len(played) * 100, 1) if played else 0.0,
        "coverage": {
            "first_match": first.isoformat() if first else None,
            "last_match": last.isoformat() if last else None,
        },
    }
