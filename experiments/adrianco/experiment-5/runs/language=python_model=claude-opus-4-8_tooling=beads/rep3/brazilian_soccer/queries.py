"""
==============================================================================
Module: brazilian_soccer.queries
==============================================================================
CONTEXT
-------
The query layer: pure, side-effect-free functions that take a
``KnowledgeGraph`` plus query parameters and return structured Python dicts.
These functions implement every capability required by the specification and
are the single shared implementation behind BOTH the MCP server tools and the
pytest BDD suite (so tests exercise exactly what the server exposes).

CAPABILITY MAP (spec section -> functions)
------------------------------------------
  1. Match Queries ......... find_matches, head_to_head
  2. Team Queries .......... team_record, compare_teams
  3. Player Queries ........ search_players, players_by_club, top_players
  4. Competition Queries ... standings, list_competitions
  5. Statistical Analysis .. competition_stats, biggest_wins, best_home_record,
                             best_away_record

Each function returns JSON-serializable data and (where useful) a pre-rendered
``summary`` string matching the answer formats shown in the specification.
==============================================================================
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .knowledge_graph import KnowledgeGraph
from .models import Match
from .normalization import fold_accents, normalize_team

# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _filter(
    matches: List[Match],
    competition: Optional[str] = None,
    season: Optional[int] = None,
    primary_only: bool = False,
) -> List[Match]:
    out = matches
    if competition:
        comp_key = _competition_key(competition)
        out = [m for m in out if _competition_key(m.competition) == comp_key]
    if season is not None:
        out = [m for m in out if m.season == season]
    if primary_only:
        out = [m for m in out if m.primary]
    return out


_COMPETITION_ALIASES = {
    "brasileirao": "brasileirao",
    "brasileirão": "brasileirao",
    "serie a": "brasileirao",
    "série a": "brasileirao",
    "campeonato brasileiro": "brasileirao",
    "copa do brasil": "copa do brasil",
    "brazilian cup": "copa do brasil",
    "libertadores": "libertadores",
    "copa libertadores": "libertadores",
    "serie b": "serie b",
    "serie c": "serie c",
}


def _competition_key(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    k = fold_accents(name).lower().strip()
    return _COMPETITION_ALIASES.get(k, k)


def _sorted_by_date(matches: List[Match], reverse: bool = False) -> List[Match]:
    from datetime import date

    return sorted(
        matches,
        key=lambda m: (m.date or date.min, m.season or 0),
        reverse=reverse,
    )


# --------------------------------------------------------------------------- #
# 1. MATCH QUERIES
# --------------------------------------------------------------------------- #
def find_matches(
    graph: KnowledgeGraph,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    home_only: bool = False,
    away_only: bool = False,
    limit: Optional[int] = 50,
) -> Dict:
    """Find matches by team / opponent / competition / season.

    Returns a dict with ``count``, ``matches`` (list of dicts) and a human
    ``summary`` line list.
    """
    if team:
        candidate = graph.matches_for_team(team)
    else:
        candidate = list(graph.matches)

    team_key = normalize_team(team) if team else None
    opp_key = normalize_team(opponent) if opponent else None

    result: List[Match] = []
    for m in candidate:
        if team_key:
            if home_only and m.home_key != team_key:
                continue
            if away_only and m.away_key != team_key:
                continue
        if opp_key and not m.involves(opp_key):
            continue
        result.append(m)

    result = _filter(result, competition=competition, season=season)
    result = _sorted_by_date(result, reverse=True)

    total = len(result)
    shown = result[:limit] if limit else result
    return {
        "count": total,
        "returned": len(shown),
        "matches": [_match_dict(m) for m in shown],
        "summary": [m.describe() for m in shown],
    }


def head_to_head(
    graph: KnowledgeGraph,
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: Optional[int] = 50,
) -> Dict:
    """Head-to-head record and match list between two teams."""
    a = normalize_team(team_a)
    b = normalize_team(team_b)
    matches = [
        m
        for m in graph.matches_for_team(team_a)
        if m.involves(a) and m.involves(b)
    ]
    matches = _filter(matches, competition=competition, season=season)
    matches = _sorted_by_date(matches, reverse=True)

    a_wins = b_wins = draws = 0
    a_goals = b_goals = 0
    for m in matches:
        if not m.has_score:
            continue
        # Resolve goals from team A's perspective.
        if m.home_key == a:
            ga, gb = m.home_goal, m.away_goal
        else:
            ga, gb = m.away_goal, m.home_goal
        a_goals += ga
        b_goals += gb
        if ga > gb:
            a_wins += 1
        elif gb > ga:
            b_wins += 1
        else:
            draws += 1

    a_disp = graph.display_for(a)
    b_disp = graph.display_for(b)
    shown = matches[:limit] if limit else matches
    summary = (
        f"Head-to-head in dataset: {a_disp} {a_wins} wins, "
        f"{b_disp} {b_wins} wins, {draws} draws"
    )
    return {
        "team_a": a_disp,
        "team_b": b_disp,
        "total_matches": len(matches),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_goals,
        "team_b_goals": b_goals,
        "summary": summary,
        "matches": [_match_dict(m) for m in shown],
        "match_lines": [m.describe() for m in shown],
    }


def last_meeting(graph: KnowledgeGraph, team_a: str, team_b: str) -> Dict:
    """Most recent match between two teams (answers 'when did X last play Y')."""
    h2h = head_to_head(graph, team_a, team_b, limit=1)
    if not h2h["matches"]:
        return {"found": False, "summary": "No matches found between these teams."}
    m = h2h["matches"][0]
    return {"found": True, "match": m, "summary": h2h["match_lines"][0]}


# --------------------------------------------------------------------------- #
# 2. TEAM QUERIES
# --------------------------------------------------------------------------- #
def team_record(
    graph: KnowledgeGraph,
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",  # 'all' | 'home' | 'away'
) -> Dict:
    """Win/loss/draw record and goals for a team, optionally filtered."""
    key = normalize_team(team)
    matches = _filter(
        graph.matches_for_team(team),
        competition=competition,
        season=season,
        primary_only=True,
    )

    wins = draws = losses = gf = ga = played = 0
    for m in matches:
        if not m.has_score:
            continue
        is_home = m.home_key == key
        if venue == "home" and not is_home:
            continue
        if venue == "away" and is_home:
            continue
        played += 1
        if is_home:
            tf, ta = m.home_goal, m.away_goal
        else:
            tf, ta = m.away_goal, m.home_goal
        gf += tf
        ga += ta
        if tf > ta:
            wins += 1
        elif tf < ta:
            losses += 1
        else:
            draws += 1

    win_rate = round(100.0 * wins / played, 1) if played else 0.0
    points = wins * 3 + draws
    disp = graph.display_for(key)
    scope = []
    if competition:
        scope.append(competition)
    if season:
        scope.append(str(season))
    if venue != "all":
        scope.append(f"{venue} only")
    scope_str = f" ({', '.join(scope)})" if scope else ""

    summary = (
        f"{disp}{scope_str}:\n"
        f"- Matches: {played}\n"
        f"- Wins: {wins}, Draws: {draws}, Losses: {losses}\n"
        f"- Goals For: {gf}, Goals Against: {ga}\n"
        f"- Points: {points}\n"
        f"- Win rate: {win_rate}%"
    )
    return {
        "team": disp,
        "season": season,
        "competition": competition,
        "venue": venue,
        "played": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "points": points,
        "win_rate": win_rate,
        "summary": summary,
    }


def compare_teams(
    graph: KnowledgeGraph,
    team_a: str,
    team_b: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
) -> Dict:
    """Compare two teams' overall records plus their head-to-head."""
    ra = team_record(graph, team_a, season=season, competition=competition)
    rb = team_record(graph, team_b, season=season, competition=competition)
    h2h = head_to_head(graph, team_a, team_b, season=season, competition=competition)
    return {"team_a": ra, "team_b": rb, "head_to_head": h2h}


# --------------------------------------------------------------------------- #
# 3. PLAYER QUERIES
# --------------------------------------------------------------------------- #
def _player_dict(p) -> Dict:
    return {
        "id": p.player_id,
        "name": p.name,
        "age": p.age,
        "nationality": p.nationality,
        "overall": p.overall,
        "potential": p.potential,
        "club": p.club,
        "position": p.position,
        "jersey_number": p.jersey_number,
        "height": p.height,
        "weight": p.weight,
        "preferred_foot": p.preferred_foot,
        "value": p.value,
    }


def search_players(
    graph: KnowledgeGraph,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: Optional[int] = 25,
) -> Dict:
    """Search FIFA players by name / nationality / club / position / rating."""
    players = graph.players

    # Narrow using indexes when possible.
    if club:
        players = graph.players_at_club(club)
    elif nationality:
        players = graph.players_of_nationality(nationality)

    name_q = fold_accents(name).lower().strip() if name else None
    nat_q = fold_accents(nationality).lower().strip() if nationality else None
    pos_q = position.upper().strip() if position else None

    out = []
    for p in players:
        if name_q and name_q not in p.name_key:
            continue
        if nat_q and fold_accents(p.nationality).lower() != nat_q:
            continue
        if pos_q and (p.position or "").upper() != pos_q:
            continue
        if min_overall is not None and (p.overall or 0) < min_overall:
            continue
        out.append(p)

    out.sort(key=lambda p: (p.overall or 0), reverse=True)
    total = len(out)
    shown = out[:limit] if limit else out
    return {
        "count": total,
        "returned": len(shown),
        "players": [_player_dict(p) for p in shown],
        "summary": [
            f"{i+1}. {p.describe()}" for i, p in enumerate(shown)
        ],
    }


def top_players(
    graph: KnowledgeGraph,
    nationality: Optional[str] = "Brazil",
    club: Optional[str] = None,
    limit: int = 10,
) -> Dict:
    """Highest-rated players for a nationality and/or club."""
    return search_players(
        graph, nationality=nationality, club=club, limit=limit
    )


def brazilian_players_by_club(graph: KnowledgeGraph, limit: int = 15) -> Dict:
    """Aggregate Brazilian players grouped by their (Brazilian) club."""
    from collections import defaultdict

    brazilians = graph.players_of_nationality("Brazil")
    by_club: Dict[str, list] = defaultdict(list)
    for p in brazilians:
        if p.club:
            by_club[p.club].append(p)

    rows = []
    for club, plist in by_club.items():
        ratings = [p.overall for p in plist if p.overall is not None]
        avg = round(sum(ratings) / len(ratings), 1) if ratings else 0
        rows.append(
            {"club": club, "players": len(plist), "avg_rating": avg}
        )
    rows.sort(key=lambda r: (r["players"], r["avg_rating"]), reverse=True)
    shown = rows[:limit]
    return {
        "total_brazilian_players": len(brazilians),
        "clubs": shown,
        "summary": [
            f"- {r['club']}: {r['players']} players (avg rating: {r['avg_rating']})"
            for r in shown
        ],
    }


# --------------------------------------------------------------------------- #
# 4. COMPETITION QUERIES
# --------------------------------------------------------------------------- #
def standings(
    graph: KnowledgeGraph,
    competition: str,
    season: int,
    limit: Optional[int] = None,
) -> Dict:
    """Compute a league table from match results (3pts win / 1 draw)."""
    matches = _filter(
        list(graph.matches),
        competition=competition,
        season=season,
        primary_only=True,
    )

    table: Dict[str, Dict] = {}

    def row(key: str) -> Dict:
        if key not in table:
            table[key] = {
                "team_key": key,
                "team": graph.display_for(key),
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "points": 0,
            }
        return table[key]

    for m in matches:
        if not m.has_score:
            continue
        h, a = row(m.home_key), row(m.away_key)
        h["played"] += 1
        a["played"] += 1
        h["goals_for"] += m.home_goal
        h["goals_against"] += m.away_goal
        a["goals_for"] += m.away_goal
        a["goals_against"] += m.home_goal
        if m.home_goal > m.away_goal:
            h["wins"] += 1
            h["points"] += 3
            a["losses"] += 1
        elif m.away_goal > m.home_goal:
            a["wins"] += 1
            a["points"] += 3
            h["losses"] += 1
        else:
            h["draws"] += 1
            a["draws"] += 1
            h["points"] += 1
            a["points"] += 1

    rows = list(table.values())
    for r in rows:
        r["goal_difference"] = r["goals_for"] - r["goals_against"]
    rows.sort(
        key=lambda r: (r["points"], r["goal_difference"], r["goals_for"]),
        reverse=True,
    )
    for i, r in enumerate(rows, 1):
        r["position"] = i

    shown = rows[:limit] if limit else rows
    champion = rows[0]["team"] if rows else None
    summary = [
        f"{r['position']}. {r['team']} - {r['points']} pts "
        f"({r['wins']}W, {r['draws']}D, {r['losses']}L)"
        + (" - Champion" if r["position"] == 1 else "")
        for r in shown
    ]
    return {
        "competition": competition,
        "season": season,
        "champion": champion,
        "teams": len(rows),
        "table": shown,
        "summary": summary,
    }


def list_competitions(graph: KnowledgeGraph) -> Dict:
    """List available competitions and the seasons present for each."""
    out = {}
    for comp, matches in graph.matches_by_competition.items():
        seasons = sorted({m.season for m in matches if m.season is not None})
        out[comp] = {"matches": len(matches), "seasons": seasons}
    return {"competitions": out}


# --------------------------------------------------------------------------- #
# 5. STATISTICAL ANALYSIS
# --------------------------------------------------------------------------- #
def competition_stats(
    graph: KnowledgeGraph,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> Dict:
    """Average goals/match, home win rate, draw rate over a match set."""
    matches = _filter(
        list(graph.matches),
        competition=competition,
        season=season,
        primary_only=True,
    )
    scored = [m for m in matches if m.has_score]
    n = len(scored)
    if n == 0:
        return {
            "competition": competition,
            "season": season,
            "matches": 0,
            "summary": "No scored matches found for the given filters.",
        }
    total_goals = sum(m.total_goals for m in scored)
    home_wins = sum(1 for m in scored if m.home_goal > m.away_goal)
    away_wins = sum(1 for m in scored if m.away_goal > m.home_goal)
    draws = n - home_wins - away_wins
    avg = round(total_goals / n, 2)
    home_rate = round(100.0 * home_wins / n, 1)
    away_rate = round(100.0 * away_wins / n, 1)
    draw_rate = round(100.0 * draws / n, 1)
    summary = (
        f"Average goals per match: {avg}\n"
        f"Home win rate: {home_rate}%\n"
        f"Away win rate: {away_rate}%\n"
        f"Draw rate: {draw_rate}%"
    )
    return {
        "competition": competition,
        "season": season,
        "matches": n,
        "total_goals": total_goals,
        "avg_goals_per_match": avg,
        "home_win_rate": home_rate,
        "away_win_rate": away_rate,
        "draw_rate": draw_rate,
        "summary": summary,
    }


def biggest_wins(
    graph: KnowledgeGraph,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> Dict:
    """Matches with the largest goal margin."""
    matches = _filter(
        list(graph.matches),
        competition=competition,
        season=season,
        primary_only=True,
    )
    scored = [m for m in matches if m.has_score]
    scored.sort(
        key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals),
        reverse=True,
    )
    shown = scored[:limit]
    return {
        "count": len(scored),
        "matches": [_match_dict(m) for m in shown],
        "summary": [
            f"{i+1}. {m.describe()} [margin {abs(m.home_goal - m.away_goal)}]"
            for i, m in enumerate(shown)
        ],
    }


def best_home_record(
    graph: KnowledgeGraph,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 5,
    limit: int = 10,
) -> Dict:
    return _best_venue_record(
        graph, "home", competition, season, min_matches, limit
    )


def best_away_record(
    graph: KnowledgeGraph,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 5,
    limit: int = 10,
) -> Dict:
    return _best_venue_record(
        graph, "away", competition, season, min_matches, limit
    )


def _best_venue_record(graph, venue, competition, season, min_matches, limit):
    from collections import defaultdict

    matches = _filter(
        list(graph.matches),
        competition=competition,
        season=season,
        primary_only=True,
    )
    agg: Dict[str, Dict] = defaultdict(
        lambda: {"played": 0, "wins": 0, "draws": 0, "losses": 0}
    )
    for m in matches:
        if not m.has_score:
            continue
        key = m.home_key if venue == "home" else m.away_key
        if venue == "home":
            tf, ta = m.home_goal, m.away_goal
        else:
            tf, ta = m.away_goal, m.home_goal
        rec = agg[key]
        rec["played"] += 1
        if tf > ta:
            rec["wins"] += 1
        elif tf < ta:
            rec["losses"] += 1
        else:
            rec["draws"] += 1

    rows = []
    for key, rec in agg.items():
        if rec["played"] < min_matches:
            continue
        win_rate = round(100.0 * rec["wins"] / rec["played"], 1)
        rows.append(
            {
                "team": graph.display_for(key),
                "win_rate": win_rate,
                **rec,
            }
        )
    rows.sort(key=lambda r: (r["win_rate"], r["wins"]), reverse=True)
    shown = rows[:limit]
    return {
        "venue": venue,
        "competition": competition,
        "season": season,
        "teams": shown,
        "summary": [
            f"{i+1}. {r['team']} - {r['win_rate']}% "
            f"({r['wins']}W {r['draws']}D {r['losses']}L of {r['played']})"
            for i, r in enumerate(shown)
        ],
    }


# --------------------------------------------------------------------------- #
# Serialization helper
# --------------------------------------------------------------------------- #
def _match_dict(m: Match) -> Dict:
    d = {
        "competition": m.competition,
        "season": m.season,
        "date": m.date_str(),
        "home": m.home,
        "away": m.away,
        "home_goal": m.home_goal,
        "away_goal": m.away_goal,
        "round": m.round,
        "stage": m.stage,
        "arena": m.arena,
        "source": m.source,
        "description": m.describe(),
    }
    if m.stats:
        d["stats"] = {k: v for k, v in m.stats.items() if v is not None}
    return d
