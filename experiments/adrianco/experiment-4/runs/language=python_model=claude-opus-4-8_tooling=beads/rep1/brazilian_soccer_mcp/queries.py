"""
================================================================================
Module: brazilian_soccer_mcp.queries
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
  The query engine. Pure-Python functions over the normalized SoccerData model
  (see data_loader) implementing every capability required by the spec:

    1. Match queries      - by team / date range / competition / season, plus
                            head-to-head between two teams.
    2. Team queries       - win/loss/draw records, goals for/against, home vs
                            away splits, per-competition breakdowns, and team
                            comparisons.
    3. Player queries     - search by name, filter by nationality / club,
                            ranked by rating.
    4. Competition queries- league standings computed from match results, and
                            season match listings.
    5. Statistical analysis - average goals per match, biggest wins, home-win
                            rate, best home/away records.

  Every function returns plain Python dicts/lists (JSON-serializable) so the MCP
  server layer can hand them straight to a client, and tests can assert on them.

DESIGN
  * All team lookups go through normalize.team_matches so the inconsistent
    naming across datasets is transparent to callers.
  * Standings follow Brazilian league rules: 3 points win, 1 draw, 0 loss,
    ranked by points, then wins, then goal difference, then goals for.
  * Functions accept an optional `data` argument (defaults to the cached
    singleton) to make them easy to unit test with fixtures.
================================================================================
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from .data_loader import Match, Player, SoccerData, get_data, parse_date
from .normalize import canonical_key, resolve_team, team_matches


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------
def _data(data: Optional[SoccerData]) -> SoccerData:
    return data if data is not None else get_data()


def _match_to_dict(m: Match) -> dict:
    """Serialize a Match into a stable, client-friendly dict."""
    return {
        "date": m.match_date.isoformat() if m.match_date else None,
        "season": m.season,
        "competition": m.competition,
        "round": m.round,
        "stage": m.stage,
        "home_team": m.home_name,
        "away_team": m.away_name,
        "home_goal": m.home_goal,
        "away_goal": m.away_goal,
        "score": (
            f"{m.home_goal}-{m.away_goal}" if m.has_score else None
        ),
        "arena": m.arena,
        "source": m.source,
    }


def _team_involved(m: Match, key_query: str) -> Optional[str]:
    """Return 'home' / 'away' if a query matches a side of the match, else None."""
    if team_matches(key_query, m.home_key):
        return "home"
    if team_matches(key_query, m.away_key):
        return "away"
    return None


def _sort_matches(matches: list[Match]) -> list[Match]:
    """Sort matches chronologically (undated rows sink to the end)."""
    return sorted(
        matches,
        key=lambda m: (m.match_date is None, m.match_date or date.min),
    )


def _filter_matches(
    data: SoccerData,
    team: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    venue: Optional[str] = None,
) -> list[Match]:
    """Core filtering primitive used by most match/team queries.

    `venue` may be 'home' or 'away' to restrict to `team`'s home or away games.
    `team2` restricts to matches that also involve a second team (head-to-head).
    `competition` matches case-insensitively as a substring of the label.
    """
    comp_lc = competition.lower() if competition else None
    results = []
    for m in data.matches:
        if comp_lc and comp_lc not in m.competition.lower():
            continue
        if season is not None and m.season != season:
            continue
        if date_from and (m.match_date is None or m.match_date < date_from):
            continue
        if date_to and (m.match_date is None or m.match_date > date_to):
            continue

        if team:
            side = _team_involved(m, team)
            if side is None:
                continue
            if venue and side != venue:
                continue
        if team2 and not (
            team_matches(team2, m.home_key) or team_matches(team2, m.away_key)
        ):
            continue
        results.append(m)
    return results


# ===========================================================================
# 1. MATCH QUERIES
# ===========================================================================
def find_matches(
    team: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    venue: Optional[str] = None,
    limit: int = 50,
    data: Optional[SoccerData] = None,
) -> dict:
    """Find matches by any combination of team, competition, season, dates."""
    d = _data(data)
    matches = _filter_matches(
        d,
        team=team,
        competition=competition,
        season=season,
        date_from=parse_date(date_from) if date_from else None,
        date_to=parse_date(date_to) if date_to else None,
        venue=venue,
    )
    matches = _sort_matches(matches)
    total = len(matches)
    shown = matches[-limit:] if limit and limit > 0 else matches
    return {
        "query": {
            "team": team, "competition": competition, "season": season,
            "date_from": date_from, "date_to": date_to, "venue": venue,
        },
        "total_matches": total,
        "returned": len(shown),
        "matches": [_match_to_dict(m) for m in shown],
    }


def head_to_head(
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 50,
    data: Optional[SoccerData] = None,
) -> dict:
    """Head-to-head record and match list between two teams."""
    d = _data(data)
    matches = _filter_matches(
        d, team=team_a, team2=team_b, competition=competition, season=season
    )
    matches = _sort_matches(matches)

    a_key = canonical_key(team_a)
    a_name = resolve_team(team_a)[1]
    b_name = resolve_team(team_b)[1]
    a_wins = b_wins = draws = 0
    a_goals = b_goals = 0
    for m in matches:
        if not m.has_score:
            continue
        a_is_home = team_matches(team_a, m.home_key)
        a_gf = m.home_goal if a_is_home else m.away_goal
        b_gf = m.away_goal if a_is_home else m.home_goal
        a_goals += a_gf
        b_goals += b_gf
        if a_gf > b_gf:
            a_wins += 1
        elif b_gf > a_gf:
            b_wins += 1
        else:
            draws += 1

    shown = matches[-limit:] if limit and limit > 0 else matches
    return {
        "team_a": a_name,
        "team_b": b_name,
        "total_matches": len(matches),
        "summary": {
            f"{a_name}_wins": a_wins,
            f"{b_name}_wins": b_wins,
            "draws": draws,
            f"{a_name}_goals": a_goals,
            f"{b_name}_goals": b_goals,
        },
        "matches": [_match_to_dict(m) for m in shown],
    }


# ===========================================================================
# 2. TEAM QUERIES
# ===========================================================================
def _record_from_matches(matches: Iterable[Match], team: str) -> dict:
    wins = draws = losses = gf = ga = played = 0
    for m in matches:
        if not m.has_score:
            continue
        side = _team_involved(m, team)
        if side is None:
            continue
        played += 1
        if side == "home":
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
    return {
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "points": wins * 3 + draws,
        "win_rate": win_rate,
    }


def team_record(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: Optional[str] = None,
    data: Optional[SoccerData] = None,
) -> dict:
    """Win/loss/draw record and goals for a team, optionally scoped."""
    d = _data(data)
    matches = _filter_matches(
        d, team=team, competition=competition, season=season, venue=venue
    )
    name = resolve_team(team)[1]
    if not matches:
        return {
            "team": name, "competition": competition, "season": season,
            "venue": venue, "found": False,
            "message": f"No matches found for '{team}' with the given filters.",
        }
    record = _record_from_matches(matches, team)
    return {
        "team": name,
        "competition": competition,
        "season": season,
        "venue": venue,
        "found": True,
        "record": record,
    }


def team_summary(team: str, data: Optional[SoccerData] = None) -> dict:
    """Overall team profile: total record plus a per-competition breakdown."""
    d = _data(data)
    name = resolve_team(team)[1]
    all_matches = _filter_matches(d, team=team)
    if not all_matches:
        return {"team": name, "found": False,
                "message": f"No matches found for '{team}'."}
    by_comp = {}
    for comp in sorted({m.competition for m in all_matches}):
        comp_matches = [m for m in all_matches if m.competition == comp]
        by_comp[comp] = _record_from_matches(comp_matches, team)
    return {
        "team": name,
        "found": True,
        "overall": _record_from_matches(all_matches, team),
        "by_competition": by_comp,
        "seasons": sorted({m.season for m in all_matches if m.season}),
    }


def compare_teams(
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    data: Optional[SoccerData] = None,
) -> dict:
    """Side-by-side comparison of two teams plus their head-to-head record."""
    d = _data(data)
    a_matches = _filter_matches(d, team=team_a, competition=competition, season=season)
    b_matches = _filter_matches(d, team=team_b, competition=competition, season=season)
    return {
        "team_a": resolve_team(team_a)[1],
        "team_b": resolve_team(team_b)[1],
        "competition": competition,
        "season": season,
        "team_a_record": _record_from_matches(a_matches, team_a),
        "team_b_record": _record_from_matches(b_matches, team_b),
        "head_to_head": head_to_head(
            team_a, team_b, competition=competition, season=season, data=d
        )["summary"],
    }


# ===========================================================================
# 3. PLAYER QUERIES
# ===========================================================================
def _player_to_dict(p: Player) -> dict:
    return {
        "id": p.player_id,
        "name": p.name,
        "age": p.age,
        "nationality": p.nationality,
        "overall": p.overall,
        "potential": p.potential,
        "club": p.club,
        "position": p.position,
        "jersey": p.jersey,
        "height": p.height,
        "weight": p.weight,
        "value": p.value,
        "wage": p.wage,
        "preferred_foot": p.preferred_foot,
    }


def find_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    sort_by: str = "overall",
    limit: int = 25,
    data: Optional[SoccerData] = None,
) -> dict:
    """Search FIFA players by name / nationality / club / position / rating."""
    d = _data(data)
    name_lc = name.lower() if name else None
    nat_lc = nationality.lower() if nationality else None
    pos_lc = position.lower() if position else None

    results = []
    for p in d.players:
        if name_lc and name_lc not in p.name.lower():
            continue
        if nat_lc and nat_lc not in p.nationality.lower():
            continue
        if club and not (p.club_key and team_matches(club, p.club_key)):
            continue
        if pos_lc and pos_lc != p.position.lower():
            continue
        if min_overall is not None and (p.overall or 0) < min_overall:
            continue
        results.append(p)

    reverse = sort_by in {"overall", "potential", "age"}
    results.sort(key=lambda p: (getattr(p, sort_by) or 0), reverse=reverse)

    total = len(results)
    shown = results[:limit] if limit and limit > 0 else results
    return {
        "query": {
            "name": name, "nationality": nationality, "club": club,
            "position": position, "min_overall": min_overall,
        },
        "total_players": total,
        "returned": len(shown),
        "players": [_player_to_dict(p) for p in shown],
    }


def get_player(name: str, data: Optional[SoccerData] = None) -> dict:
    """Return the best single match for a player name (highest rated)."""
    res = find_players(name=name, limit=1, data=data)
    if not res["players"]:
        return {"found": False, "name": name,
                "message": f"No player matching '{name}' found."}
    # Re-fetch the full record to include skills.
    d = _data(data)
    pid = res["players"][0]["id"]
    player = next((p for p in d.players if p.player_id == pid), None)
    out = dict(res["players"][0])
    out["found"] = True
    if player:
        out["skills"] = {k: v for k, v in player.skills.items() if v is not None}
    return out


def club_squad(club: str, limit: int = 30, data: Optional[SoccerData] = None) -> dict:
    """List players at a club, ranked by overall rating, with summary stats."""
    res = find_players(club=club, limit=limit, data=data)
    players = res["players"]
    overalls = [p["overall"] for p in players if p["overall"] is not None]
    res["club"] = resolve_team(club)[1]
    res["average_overall"] = round(sum(overalls) / len(overalls), 1) if overalls else None
    return res


# ===========================================================================
# 4. COMPETITION QUERIES
# ===========================================================================
def standings(
    season: int,
    competition: str = "Brasileirão Série A",
    data: Optional[SoccerData] = None,
) -> dict:
    """Compute a league table from match results for a season.

    Uses Brazilian league scoring (3/1/0) ranked by points, wins, goal
    difference, then goals for. Most meaningful for round-robin leagues such as
    the Brasileirão; cup/knockout competitions will produce a partial table.
    """
    d = _data(data)
    matches = _filter_matches(d, competition=competition, season=season)
    table: dict[str, dict] = {}

    def row(key: str, name: str) -> dict:
        return table.setdefault(key, {
            "team": name, "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "points": 0,
        })

    for m in matches:
        if not m.has_score:
            continue
        h = row(m.home_key, m.home_name)
        a = row(m.away_key, m.away_name)
        h["played"] += 1
        a["played"] += 1
        h["goals_for"] += m.home_goal
        h["goals_against"] += m.away_goal
        a["goals_for"] += m.away_goal
        a["goals_against"] += m.home_goal
        if m.home_goal > m.away_goal:
            h["wins"] += 1; h["points"] += 3; a["losses"] += 1
        elif m.away_goal > m.home_goal:
            a["wins"] += 1; a["points"] += 3; h["losses"] += 1
        else:
            h["draws"] += 1; a["draws"] += 1
            h["points"] += 1; a["points"] += 1

    rows = list(table.values())
    for r in rows:
        r["goal_difference"] = r["goals_for"] - r["goals_against"]
    rows.sort(
        key=lambda r: (r["points"], r["wins"], r["goal_difference"], r["goals_for"]),
        reverse=True,
    )
    for i, r in enumerate(rows, start=1):
        r["position"] = i

    return {
        "competition": competition,
        "season": season,
        "teams": len(rows),
        "champion": rows[0]["team"] if rows else None,
        "standings": rows,
    }


def season_results(
    season: int,
    competition: Optional[str] = None,
    limit: int = 100,
    data: Optional[SoccerData] = None,
) -> dict:
    """All match results in a season (optionally a single competition)."""
    return find_matches(
        competition=competition, season=season, limit=limit, data=data
    )


def list_competitions(data: Optional[SoccerData] = None) -> dict:
    """List available competitions and their season coverage."""
    d = _data(data)
    out = {}
    for m in d.matches:
        entry = out.setdefault(m.competition, {"matches": 0, "seasons": set()})
        entry["matches"] += 1
        if m.season is not None:
            entry["seasons"].add(m.season)
    serializable = {
        comp: {
            "matches": v["matches"],
            "seasons": sorted(v["seasons"]),
        }
        for comp, v in sorted(out.items())
    }
    return {"competitions": serializable}


# ===========================================================================
# 5. STATISTICAL ANALYSIS
# ===========================================================================
def competition_stats(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    data: Optional[SoccerData] = None,
) -> dict:
    """Aggregate statistics: goals per match, home-win rate, etc."""
    d = _data(data)
    matches = [m for m in _filter_matches(d, competition=competition, season=season)
               if m.has_score]
    n = len(matches)
    if n == 0:
        return {"competition": competition, "season": season, "matches": 0,
                "message": "No scored matches for the given filters."}
    total_goals = sum(m.total_goals for m in matches)
    home_wins = sum(1 for m in matches if m.home_goal > m.away_goal)
    away_wins = sum(1 for m in matches if m.away_goal > m.home_goal)
    draws = n - home_wins - away_wins
    return {
        "competition": competition,
        "season": season,
        "matches": n,
        "total_goals": total_goals,
        "avg_goals_per_match": round(total_goals / n, 2),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(100.0 * home_wins / n, 1),
        "away_win_rate": round(100.0 * away_wins / n, 1),
        "draw_rate": round(100.0 * draws / n, 1),
    }


def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
    data: Optional[SoccerData] = None,
) -> dict:
    """Largest goal-margin victories matching the filters."""
    d = _data(data)
    matches = [m for m in _filter_matches(d, competition=competition, season=season)
               if m.has_score]
    matches.sort(
        key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals),
        reverse=True,
    )
    top = matches[:limit]
    out = []
    for m in top:
        dd = _match_to_dict(m)
        dd["margin"] = abs(m.home_goal - m.away_goal)
        out.append(dd)
    return {"competition": competition, "season": season, "results": out}


def best_records(
    venue: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 5,
    metric: str = "win_rate",
    limit: int = 10,
    data: Optional[SoccerData] = None,
) -> dict:
    """Rank teams by a record metric (win_rate / points / goals_for ...).

    `venue` may be 'home' or 'away' to evaluate home-only or away-only records.
    """
    d = _data(data)
    matches = _filter_matches(d, competition=competition, season=season, venue=None)
    # Collect per-team match buckets honoring the venue constraint.
    buckets: dict[str, list[Match]] = {}
    names: dict[str, str] = {}
    for m in matches:
        if not m.has_score:
            continue
        if venue in (None, "home"):
            buckets.setdefault(m.home_key, []).append(m)
            names[m.home_key] = m.home_name
        if venue in (None, "away"):
            buckets.setdefault(m.away_key, []).append(m)
            names[m.away_key] = m.away_name

    rows = []
    for key, ms in buckets.items():
        rec = _record_from_matches(ms, key)
        if rec["matches"] < min_matches:
            continue
        rec["team"] = names[key]
        rows.append(rec)

    rows.sort(key=lambda r: (r.get(metric, 0), r["points"]), reverse=True)
    return {
        "venue": venue, "competition": competition, "season": season,
        "metric": metric, "min_matches": min_matches,
        "results": rows[:limit],
    }


def top_scoring_teams(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
    data: Optional[SoccerData] = None,
) -> dict:
    """Teams ranked by total goals scored under the filters."""
    return best_records(
        competition=competition, season=season, metric="goals_for",
        min_matches=1, limit=limit, data=data,
    )
