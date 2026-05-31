"""Match / team / player / competition / statistics query layer.

All functions in this module take a :class:`~soccer_mcp.data_loader.DataStore`
plus query parameters and return plain Python values (dicts and lists) that
serialise cleanly through MCP's JSON transport. They are the building blocks
behind every MCP tool exposed in :mod:`soccer_mcp.server`.

The five capability areas from ``TASK.md`` map onto the public functions:

* Match queries     -> :func:`find_matches`, :func:`head_to_head`
* Team queries      -> :func:`team_record`, :func:`compare_teams`
* Player queries    -> :func:`find_players`, :func:`top_brazilian_players`,
                       :func:`players_by_club`
* Competition       -> :func:`competition_standings`, :func:`competition_summary`
* Statistical       -> :func:`overall_statistics`, :func:`biggest_wins`,
                       :func:`best_home_record`, :func:`best_away_record`,
                       :func:`average_goals_per_match`

The functions are intentionally tolerant to missing inputs (``None`` /
``""``) so MCP clients can omit optional parameters without raising.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Iterable, Sequence

from soccer_mcp.data_loader import (
    BRASILEIRAO,
    DataStore,
    parse_date,
)
from soccer_mcp.normalizer import matches_team, normalize_team, _strip_accents

# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _serialise_match(match: dict) -> dict:
    """Return a JSON-friendly copy of a match record."""
    out = dict(match)
    d = out.get("date")
    if isinstance(d, date):
        out["date"] = d.isoformat()
    return out


def _winner(match: dict) -> str | None:
    h, a = match.get("home_goal"), match.get("away_goal")
    if h is None or a is None:
        return None
    if h > a:
        return "home"
    if a > h:
        return "away"
    return "draw"


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------
def find_matches(
    store: DataStore,
    *,
    team: str | None = None,
    opponent: str | None = None,
    season: int | None = None,
    competition: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    limit: int | None = 50,
) -> list[dict]:
    """Filter ``store.matches`` by the supplied criteria.

    Parameters
    ----------
    team, opponent:
        Team name fragments. ``team`` may appear as home or away unless
        ``home_only`` or ``away_only`` is set. ``opponent`` constrains the
        other side.
    season, competition:
        Exact-match filters.
    start_date, end_date:
        Inclusive ISO date bounds; the helper accepts any format
        :func:`~soccer_mcp.data_loader.parse_date` understands.
    limit:
        Maximum rows returned (most recent first). ``None`` means unlimited.
    """
    start = parse_date(start_date)
    end = parse_date(end_date)
    season_int = int(season) if season not in (None, "") else None
    comp = competition.strip() if competition else None

    results: list[dict] = []
    for match in store.matches:
        if season_int is not None and match.get("season") != season_int:
            continue
        if comp and (match.get("competition") or "").lower() != comp.lower():
            continue
        if start and (match.get("date") is None or match["date"] < start):
            continue
        if end and (match.get("date") is None or match["date"] > end):
            continue

        is_home = matches_team(match.get("home_team"), team) if team else None
        is_away = matches_team(match.get("away_team"), team) if team else None

        if team:
            if home_only and not is_home:
                continue
            if away_only and not is_away:
                continue
            if not home_only and not away_only and not (is_home or is_away):
                continue

        if opponent:
            opp_is_home = matches_team(match.get("home_team"), opponent)
            opp_is_away = matches_team(match.get("away_team"), opponent)
            if team:
                # opponent must be on the other side from team
                if is_home and not opp_is_away:
                    continue
                if is_away and not opp_is_home:
                    continue
                if not (is_home or is_away):
                    continue
            else:
                if not (opp_is_home or opp_is_away):
                    continue

        results.append(match)

    results.sort(key=lambda m: (m.get("date") or date.min), reverse=True)
    if limit is not None:
        results = results[: int(limit)]
    return [_serialise_match(m) for m in results]


def head_to_head(
    store: DataStore,
    team_a: str,
    team_b: str,
    *,
    competition: str | None = None,
    season: int | None = None,
    limit: int | None = 50,
) -> dict[str, Any]:
    """Return aggregated head-to-head record and recent matches for two clubs."""
    matches = find_matches(
        store,
        team=team_a,
        opponent=team_b,
        competition=competition,
        season=season,
        limit=None,
    )
    a_wins = b_wins = draws = goals_a = goals_b = 0
    for m in matches:
        a_is_home = matches_team(m.get("home_team"), team_a)
        hg, ag = m.get("home_goal"), m.get("away_goal")
        if hg is None or ag is None:
            continue
        if a_is_home:
            goals_a += hg
            goals_b += ag
        else:
            goals_a += ag
            goals_b += hg
        w = _winner(m)
        if w == "draw":
            draws += 1
        elif (w == "home" and a_is_home) or (w == "away" and not a_is_home):
            a_wins += 1
        else:
            b_wins += 1

    return {
        "team_a": team_a,
        "team_b": team_b,
        "matches_played": len(matches),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": goals_a,
        "team_b_goals": goals_b,
        "recent_matches": matches[: int(limit)] if limit else matches,
    }


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------
def team_record(
    store: DataStore,
    team: str,
    *,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,  # 'home', 'away', or None for both
) -> dict[str, Any]:
    """Compute aggregate W/D/L + goals record for a team."""
    home_only = venue == "home"
    away_only = venue == "away"
    matches = find_matches(
        store,
        team=team,
        season=season,
        competition=competition,
        home_only=home_only,
        away_only=away_only,
        limit=None,
    )
    wins = draws = losses = gf = ga = 0
    for m in matches:
        team_is_home = matches_team(m.get("home_team"), team)
        hg, ag = m.get("home_goal"), m.get("away_goal")
        if hg is None or ag is None:
            continue
        team_goals = hg if team_is_home else ag
        opp_goals = ag if team_is_home else hg
        gf += team_goals
        ga += opp_goals
        if team_goals > opp_goals:
            wins += 1
        elif team_goals < opp_goals:
            losses += 1
        else:
            draws += 1
    played = wins + draws + losses
    return {
        "team": team,
        "season": season,
        "competition": competition,
        "venue": venue or "all",
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "points": wins * 3 + draws,
        "win_rate": round(wins / played, 4) if played else 0.0,
    }


def compare_teams(
    store: DataStore,
    team_a: str,
    team_b: str,
    *,
    season: int | None = None,
    competition: str | None = None,
) -> dict[str, Any]:
    """Side-by-side team records plus their head-to-head summary."""
    return {
        "team_a": team_record(store, team_a, season=season, competition=competition),
        "team_b": team_record(store, team_b, season=season, competition=competition),
        "head_to_head": head_to_head(
            store, team_a, team_b, season=season, competition=competition, limit=10
        ),
    }


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------
def _player_summary(p: dict) -> dict:
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "age": p.get("age"),
        "nationality": p.get("nationality"),
        "overall": p.get("overall"),
        "potential": p.get("potential"),
        "club": p.get("club"),
        "position": p.get("position"),
        "jersey_number": p.get("jersey_number"),
    }


def find_players(
    store: DataStore,
    *,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int | None = 25,
) -> list[dict]:
    """Filter the FIFA player list by name/nationality/club/position."""
    name_q = _strip_accents(name).lower() if name else None
    nat_q = _strip_accents(nationality).lower() if nationality else None
    club_q = normalize_team(club) if club else None
    pos_q = position.upper() if position else None

    out: list[dict] = []
    for p in store.players:
        if name_q and name_q not in p.get("name", "").lower() \
                and name_q not in _strip_accents(p.get("name", "")).lower():
            continue
        if nat_q and nat_q not in p.get("nationality_norm", ""):
            continue
        if club_q and club_q != p.get("club_norm") and club_q not in p.get("club_norm", ""):
            continue
        if pos_q and pos_q != p.get("position", "").upper():
            continue
        if min_overall is not None and (p.get("overall") or 0) < int(min_overall):
            continue
        out.append(p)

    out.sort(key=lambda p: p.get("overall") or 0, reverse=True)
    if limit is not None:
        out = out[: int(limit)]
    return [_player_summary(p) for p in out]


def top_brazilian_players(store: DataStore, limit: int = 10) -> list[dict]:
    return find_players(store, nationality="brazil", limit=limit)


def players_by_club(store: DataStore, club: str, *, limit: int | None = 50) -> dict[str, Any]:
    club_norm = normalize_team(club)
    members = [p for p in store.players if p.get("club_norm") == club_norm or
               (club_norm and club_norm in p.get("club_norm", ""))]
    members.sort(key=lambda p: p.get("overall") or 0, reverse=True)
    summarised = [_player_summary(p) for p in members[: int(limit)] if members]
    avg = (
        round(sum(p.get("overall") or 0 for p in members) / len(members), 1)
        if members else 0.0
    )
    return {
        "club": club,
        "club_normalized": club_norm,
        "player_count": len(members),
        "average_overall": avg,
        "players": summarised,
    }


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------
def competition_standings(
    store: DataStore,
    season: int,
    *,
    competition: str = BRASILEIRAO,
) -> list[dict]:
    """Compute season standings by replaying every match in the competition."""
    season_int = int(season)
    table: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "team": None,
        "team_normalized": None,
        "played": 0, "wins": 0, "draws": 0, "losses": 0,
        "goals_for": 0, "goals_against": 0, "points": 0,
    })
    for match in store.matches:
        if match.get("season") != season_int:
            continue
        if (match.get("competition") or "").lower() != competition.lower():
            continue
        hg, ag = match.get("home_goal"), match.get("away_goal")
        if hg is None or ag is None:
            continue
        for team_field, goals_for, goals_against in (
            ("home_team", hg, ag),
            ("away_team", ag, hg),
        ):
            name = match.get(team_field) or ""
            if not name:
                continue
            norm = match["home_team_norm" if team_field == "home_team" else "away_team_norm"]
            row = table[norm]
            row["team"] = row["team"] or name
            row["team_normalized"] = norm
            row["played"] += 1
            row["goals_for"] += goals_for
            row["goals_against"] += goals_against
            if goals_for > goals_against:
                row["wins"] += 1
                row["points"] += 3
            elif goals_for < goals_against:
                row["losses"] += 1
            else:
                row["draws"] += 1
                row["points"] += 1

    standings = list(table.values())
    for row in standings:
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
    standings.sort(
        key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"] or "")
    )
    for i, row in enumerate(standings, start=1):
        row["position"] = i
    return standings


def competition_summary(
    store: DataStore,
    season: int,
    *,
    competition: str = BRASILEIRAO,
) -> dict[str, Any]:
    """Summary metrics for a single (competition, season)."""
    season_int = int(season)
    matches = [
        m for m in store.matches
        if m.get("season") == season_int
        and (m.get("competition") or "").lower() == competition.lower()
    ]
    standings = competition_standings(store, season_int, competition=competition)
    champion = standings[0] if standings else None
    return {
        "season": season_int,
        "competition": competition,
        "matches_played": len(matches),
        "teams": len(standings),
        "champion": champion["team"] if champion else None,
        "champion_points": champion["points"] if champion else None,
        "top_3": [
            {"position": r["position"], "team": r["team"], "points": r["points"]}
            for r in standings[:3]
        ],
    }


# ---------------------------------------------------------------------------
# Statistical queries
# ---------------------------------------------------------------------------
def _completed(match: dict) -> bool:
    return match.get("home_goal") is not None and match.get("away_goal") is not None


def average_goals_per_match(
    store: DataStore,
    *,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    selected: list[dict] = []
    for m in store.matches:
        if competition and (m.get("competition") or "").lower() != competition.lower():
            continue
        if season is not None and m.get("season") != int(season):
            continue
        if not _completed(m):
            continue
        selected.append(m)
    if not selected:
        return {"matches": 0, "average_goals": 0.0, "home_win_rate": 0.0,
                "away_win_rate": 0.0, "draw_rate": 0.0}
    home_w = sum(1 for m in selected if m["home_goal"] > m["away_goal"])
    away_w = sum(1 for m in selected if m["away_goal"] > m["home_goal"])
    draws = sum(1 for m in selected if m["home_goal"] == m["away_goal"])
    total_goals = sum(m["home_goal"] + m["away_goal"] for m in selected)
    n = len(selected)
    return {
        "matches": n,
        "competition": competition,
        "season": season,
        "total_goals": total_goals,
        "average_goals": round(total_goals / n, 3),
        "home_win_rate": round(home_w / n, 4),
        "away_win_rate": round(away_w / n, 4),
        "draw_rate": round(draws / n, 4),
    }


def biggest_wins(
    store: DataStore,
    *,
    limit: int = 10,
    competition: str | None = None,
    season: int | None = None,
) -> list[dict]:
    selected: list[dict] = []
    for m in store.matches:
        if not _completed(m):
            continue
        if competition and (m.get("competition") or "").lower() != competition.lower():
            continue
        if season is not None and m.get("season") != int(season):
            continue
        margin = abs(m["home_goal"] - m["away_goal"])
        if margin <= 0:
            continue
        selected.append((margin, m))
    selected.sort(key=lambda item: (-item[0], item[1].get("date") or date.min))
    return [_serialise_match(m) for _, m in selected[: int(limit)]]


def _venue_record_table(
    store: DataStore,
    venue: str,
    *,
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 5,
) -> list[dict]:
    counters: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "team": None, "wins": 0, "draws": 0, "losses": 0,
        "goals_for": 0, "goals_against": 0, "matches": 0,
    })
    for m in store.matches:
        if not _completed(m):
            continue
        if competition and (m.get("competition") or "").lower() != competition.lower():
            continue
        if season is not None and m.get("season") != int(season):
            continue
        if venue == "home":
            team_field, opp_field = "home_team", "away_team"
            team_goals, opp_goals = m["home_goal"], m["away_goal"]
            norm_field = "home_team_norm"
        else:
            team_field, opp_field = "away_team", "home_team"
            team_goals, opp_goals = m["away_goal"], m["home_goal"]
            norm_field = "away_team_norm"
        norm = m.get(norm_field)
        if not norm:
            continue
        row = counters[norm]
        row["team"] = row["team"] or m.get(team_field)
        row["matches"] += 1
        row["goals_for"] += team_goals
        row["goals_against"] += opp_goals
        if team_goals > opp_goals:
            row["wins"] += 1
        elif team_goals < opp_goals:
            row["losses"] += 1
        else:
            row["draws"] += 1
    rows = []
    for norm, row in counters.items():
        if row["matches"] < min_matches:
            continue
        row["team_normalized"] = norm
        row["points"] = row["wins"] * 3 + row["draws"]
        row["win_rate"] = round(row["wins"] / row["matches"], 4)
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
        rows.append(row)
    rows.sort(key=lambda r: (-r["win_rate"], -r["points"], -r["goal_difference"]))
    return rows


def best_home_record(store: DataStore, **kwargs) -> list[dict]:
    return _venue_record_table(store, "home", **kwargs)


def best_away_record(store: DataStore, **kwargs) -> list[dict]:
    return _venue_record_table(store, "away", **kwargs)


def overall_statistics(store: DataStore) -> dict[str, Any]:
    """Top-line description of the loaded dataset."""
    competitions = store.competitions()
    seasons = store.seasons()
    return {
        "matches_total": len(store.matches),
        "players_total": len(store.players),
        "competitions": competitions,
        "seasons_range": [seasons[0], seasons[-1]] if seasons else None,
        "unique_teams": len(store.teams()),
        "source_dir": str(store.source_dir) if store.source_dir else None,
    }


# ---------------------------------------------------------------------------
# Utility: dataset summary used by both server and tests
# ---------------------------------------------------------------------------
def list_competitions(store: DataStore) -> list[str]:
    return store.competitions()


def list_seasons(store: DataStore, *, competition: str | None = None) -> list[int]:
    if competition:
        comp = competition.lower()
        return sorted({
            m["season"] for m in store.matches
            if m.get("season") is not None and (m.get("competition") or "").lower() == comp
        })
    return store.seasons()
