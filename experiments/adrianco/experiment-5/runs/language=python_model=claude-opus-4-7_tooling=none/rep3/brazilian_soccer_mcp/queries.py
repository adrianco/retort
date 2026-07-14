"""Query layer for the Brazilian Soccer MCP server.

Every public function takes a `Dataset` and returns plain dict/list
data so the MCP server can JSON-serialize results directly.

Covers all five capability areas from TASK.md:

    1. Match queries        -- find_matches, head_to_head
    2. Team queries         -- team_stats, compare_teams
    3. Player queries       -- find_players, top_brazilian_players
    4. Competition queries  -- competition_standings, list_seasons
    5. Statistical analysis -- biggest_wins, overall_stats, best_home_record

All competition / team filtering is done through
`team_utils.normalize_team_name` so callers can pass "Flamengo",
"Flamengo-RJ", or "Clube de Regatas do Flamengo" interchangeably.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable

from .data_loader import (
    BRASILEIRAO,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COMPETITIONS,
    COPA_DO_BRASIL,
    LIBERTADORES,
    Dataset,
    Match,
    Player,
)
from .team_utils import normalize_team_name


def canonical_competition(name: str | None) -> str | None:
    """Map a fuzzy competition string to one of our canonical names."""
    if not name:
        return None
    raw = name.strip().lower()
    if raw in {"brasileirão", "brasileirao", "serie a", "série a",
               "brasileirão série a", "brasileirao serie a",
               "campeonato brasileiro", "brasileirao a"}:
        return BRASILEIRAO
    if raw in {"brasileirão série b", "brasileirao serie b", "serie b", "série b"}:
        return BRASILEIRAO_B
    if raw in {"brasileirão série c", "brasileirao serie c", "serie c", "série c"}:
        return BRASILEIRAO_C
    if "libertadores" in raw:
        return LIBERTADORES
    if "copa do brasil" in raw or raw in {"cup", "brazilian cup"}:
        return COPA_DO_BRASIL
    return name.strip()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _parse_iso(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _match_in_competition(m: Match, competition: str | None) -> bool:
    if not competition:
        return True
    canonical = canonical_competition(competition)
    return m.competition.lower() == canonical.lower()


def _team_matches_iter(ds: Dataset, team_norm: str) -> Iterable[Match]:
    return ds.matches_by_norm_team.get(team_norm, [])


# --------------------------------------------------------------------------- #
# 1. Match queries
# --------------------------------------------------------------------------- #


def find_matches(
    ds: Dataset,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    limit: int | None = None,
) -> list[dict]:
    """Return matches that satisfy every supplied filter."""
    df = _parse_iso(date_from)
    dt = _parse_iso(date_to)
    tnorm = normalize_team_name(team) if team else None
    onorm = normalize_team_name(opponent) if opponent else None

    if tnorm:
        candidates = list(_team_matches_iter(ds, tnorm))
    else:
        candidates = ds.matches

    out: list[dict] = []
    for m in candidates:
        if season is not None and m.season != season:
            continue
        if not _match_in_competition(m, competition):
            continue
        if df and (m.match_date is None or m.match_date < df):
            continue
        if dt and (m.match_date is None or m.match_date > dt):
            continue
        if tnorm:
            is_home = m.home_norm == tnorm
            is_away = m.away_norm == tnorm
            if home_only and not is_home:
                continue
            if away_only and not is_away:
                continue
            if onorm and not (
                (is_home and m.away_norm == onorm) or (is_away and m.home_norm == onorm)
            ):
                continue
        elif onorm:
            if onorm not in (m.home_norm, m.away_norm):
                continue
        out.append(m.to_dict())
        if limit and len(out) >= limit:
            break
    return out


def head_to_head(ds: Dataset, team_a: str, team_b: str) -> dict:
    """Aggregate W/D/L between two teams across every competition."""
    a, b = normalize_team_name(team_a), normalize_team_name(team_b)
    matches = [
        m
        for m in _team_matches_iter(ds, a)
        if (m.home_norm == a and m.away_norm == b) or (m.home_norm == b and m.away_norm == a)
    ]
    wins_a = wins_b = draws = goals_a = goals_b = 0
    for m in matches:
        if m.home_goal is None or m.away_goal is None:
            continue
        if m.home_norm == a:
            goals_a += m.home_goal
            goals_b += m.away_goal
        else:
            goals_a += m.away_goal
            goals_b += m.home_goal
        w = m.winner
        if w == "draw":
            draws += 1
        elif (w == "home" and m.home_norm == a) or (w == "away" and m.away_norm == a):
            wins_a += 1
        else:
            wins_b += 1
    return {
        "team_a": a,
        "team_b": b,
        "matches": [m.to_dict() for m in matches],
        "total_matches": len(matches),
        "wins_a": wins_a,
        "wins_b": wins_b,
        "draws": draws,
        "goals_a": goals_a,
        "goals_b": goals_b,
    }


# --------------------------------------------------------------------------- #
# 2. Team queries
# --------------------------------------------------------------------------- #


def team_stats(
    ds: Dataset,
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",  # "home", "away", "all"
) -> dict:
    """W/D/L, goals for/against, win rate for a team."""
    tnorm = normalize_team_name(team)
    matches = [
        m
        for m in _team_matches_iter(ds, tnorm)
        if (season is None or m.season == season) and _match_in_competition(m, competition)
    ]
    wins = draws = losses = gf = ga = home_matches = away_matches = 0
    counted = 0
    for m in matches:
        if m.home_goal is None or m.away_goal is None:
            continue
        is_home = m.home_norm == tnorm
        if venue == "home" and not is_home:
            continue
        if venue == "away" and is_home:
            continue
        team_goals = m.home_goal if is_home else m.away_goal
        opp_goals = m.away_goal if is_home else m.home_goal
        gf += team_goals
        ga += opp_goals
        if team_goals > opp_goals:
            wins += 1
        elif team_goals == opp_goals:
            draws += 1
        else:
            losses += 1
        if is_home:
            home_matches += 1
        else:
            away_matches += 1
        counted += 1
    win_rate = (wins / counted) if counted else 0.0
    return {
        "team": tnorm,
        "season": season,
        "competition": competition,
        "venue": venue,
        "matches": counted,
        "home_matches": home_matches,
        "away_matches": away_matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "points": wins * 3 + draws,
        "win_rate": round(win_rate, 4),
    }


def compare_teams(
    ds: Dataset,
    team_a: str,
    team_b: str,
    season: int | None = None,
    competition: str | None = None,
) -> dict:
    """Side-by-side stat comparison plus the head-to-head record."""
    return {
        "team_a": team_stats(ds, team_a, season=season, competition=competition),
        "team_b": team_stats(ds, team_b, season=season, competition=competition),
        "head_to_head": head_to_head(ds, team_a, team_b),
    }


# --------------------------------------------------------------------------- #
# 3. Player queries
# --------------------------------------------------------------------------- #


def find_players(
    ds: Dataset,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 50,
) -> list[dict]:
    """Filter the FIFA player table.  All filters AND together."""
    name_l = name.lower() if name else None
    nat_l = nationality.lower() if nationality else None
    club_norm = normalize_team_name(club) if club else None
    pos_l = position.upper() if position else None
    out: list[dict] = []
    for p in ds.players:
        if name_l and name_l not in p.name.lower():
            continue
        if nat_l and nat_l != p.nationality.lower():
            continue
        if club_norm and p.club_norm != club_norm:
            continue
        if pos_l and pos_l != p.position.upper():
            continue
        if min_overall is not None and (p.overall is None or p.overall < min_overall):
            continue
        out.append(p.to_dict())
    out.sort(key=lambda r: r["overall"] or 0, reverse=True)
    return out[:limit]


def top_brazilian_players(ds: Dataset, limit: int = 10) -> list[dict]:
    return find_players(ds, nationality="Brazil", limit=limit)


def brazilian_players_by_club(ds: Dataset, top_n_clubs: int = 10) -> list[dict]:
    """Aggregate Brazilian players grouped by their club (FIFA data)."""
    groups: dict[str, list[Player]] = defaultdict(list)
    for p in ds.players:
        if p.nationality.lower() == "brazil" and p.club:
            groups[p.club].append(p)
    summaries = []
    for club, players in groups.items():
        ratings = [p.overall for p in players if p.overall is not None]
        avg = sum(ratings) / len(ratings) if ratings else 0
        summaries.append(
            {
                "club": club,
                "player_count": len(players),
                "avg_overall": round(avg, 1),
                "top_player": max(players, key=lambda p: p.overall or 0).name if players else None,
            }
        )
    summaries.sort(key=lambda r: r["player_count"], reverse=True)
    return summaries[:top_n_clubs]


# --------------------------------------------------------------------------- #
# 4. Competition queries
# --------------------------------------------------------------------------- #


def competition_standings(
    ds: Dataset,
    competition: str,
    season: int,
) -> list[dict]:
    """Compute a league table from match results (3 pts win, 1 pt draw)."""
    table: dict[str, dict] = defaultdict(
        lambda: {
            "team": "",
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "points": 0,
        }
    )
    for m in ds.matches:
        if m.season != season or not _match_in_competition(m, competition):
            continue
        if m.home_goal is None or m.away_goal is None:
            continue
        for team_norm, gf, ga in (
            (m.home_norm, m.home_goal, m.away_goal),
            (m.away_norm, m.away_goal, m.home_goal),
        ):
            if not team_norm:
                continue
            r = table[team_norm]
            r["team"] = team_norm
            r["matches"] += 1
            r["goals_for"] += gf
            r["goals_against"] += ga
            if gf > ga:
                r["wins"] += 1
                r["points"] += 3
            elif gf == ga:
                r["draws"] += 1
                r["points"] += 1
            else:
                r["losses"] += 1
    rows = list(table.values())
    for r in rows:
        r["goal_difference"] = r["goals_for"] - r["goals_against"]
    rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]))
    for i, r in enumerate(rows, 1):
        r["position"] = i
    return rows


def list_seasons(ds: Dataset, competition: str | None = None) -> list[int]:
    seasons = {
        m.season
        for m in ds.matches
        if m.season is not None and _match_in_competition(m, competition)
    }
    return sorted(seasons)


def list_competitions(ds: Dataset) -> list[str]:
    seen = {m.competition for m in ds.matches if m.competition}
    return sorted(seen)


# --------------------------------------------------------------------------- #
# 5. Statistical analysis
# --------------------------------------------------------------------------- #


def biggest_wins(
    ds: Dataset,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> list[dict]:
    pool = []
    for m in ds.matches:
        if m.home_goal is None or m.away_goal is None:
            continue
        if season is not None and m.season != season:
            continue
        if not _match_in_competition(m, competition):
            continue
        margin = abs(m.home_goal - m.away_goal)
        pool.append((margin, m))
    pool.sort(key=lambda kv: (-kv[0], kv[1].match_date or date.min))
    return [m.to_dict() | {"margin": margin} for margin, m in pool[:limit]]


def overall_stats(ds: Dataset, competition: str | None = None) -> dict:
    total = home_wins = away_wins = draws = total_goals = 0
    for m in ds.matches:
        if not _match_in_competition(m, competition):
            continue
        if m.home_goal is None or m.away_goal is None:
            continue
        total += 1
        total_goals += m.home_goal + m.away_goal
        if m.home_goal > m.away_goal:
            home_wins += 1
        elif m.away_goal > m.home_goal:
            away_wins += 1
        else:
            draws += 1
    avg = (total_goals / total) if total else 0.0
    return {
        "competition": competition or "all",
        "matches": total,
        "total_goals": total_goals,
        "avg_goals_per_match": round(avg, 3),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / total, 4) if total else 0,
        "away_win_rate": round(away_wins / total, 4) if total else 0,
        "draw_rate": round(draws / total, 4) if total else 0,
    }


def best_home_record(
    ds: Dataset,
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 5,
    limit: int = 10,
) -> list[dict]:
    """Rank teams by home win rate (after a minimum number of home games)."""
    by_team: dict[str, dict] = defaultdict(
        lambda: {"team": "", "matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
    )
    for m in ds.matches:
        if not _match_in_competition(m, competition):
            continue
        if season is not None and m.season != season:
            continue
        if m.home_goal is None or m.away_goal is None:
            continue
        r = by_team[m.home_norm]
        r["team"] = m.home_norm
        r["matches"] += 1
        r["gf"] += m.home_goal
        r["ga"] += m.away_goal
        if m.home_goal > m.away_goal:
            r["wins"] += 1
        elif m.home_goal == m.away_goal:
            r["draws"] += 1
        else:
            r["losses"] += 1
    rows = [r for r in by_team.values() if r["matches"] >= min_matches and r["team"]]
    for r in rows:
        r["win_rate"] = round(r["wins"] / r["matches"], 4)
        r["points"] = r["wins"] * 3 + r["draws"]
    rows.sort(key=lambda r: (-r["win_rate"], -r["points"]))
    return rows[:limit]


def best_away_record(
    ds: Dataset,
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 5,
    limit: int = 10,
) -> list[dict]:
    by_team: dict[str, dict] = defaultdict(
        lambda: {"team": "", "matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
    )
    for m in ds.matches:
        if not _match_in_competition(m, competition):
            continue
        if season is not None and m.season != season:
            continue
        if m.home_goal is None or m.away_goal is None:
            continue
        r = by_team[m.away_norm]
        r["team"] = m.away_norm
        r["matches"] += 1
        r["gf"] += m.away_goal
        r["ga"] += m.home_goal
        if m.away_goal > m.home_goal:
            r["wins"] += 1
        elif m.away_goal == m.home_goal:
            r["draws"] += 1
        else:
            r["losses"] += 1
    rows = [r for r in by_team.values() if r["matches"] >= min_matches and r["team"]]
    for r in rows:
        r["win_rate"] = round(r["wins"] / r["matches"], 4)
        r["points"] = r["wins"] * 3 + r["draws"]
    rows.sort(key=lambda r: (-r["win_rate"], -r["points"]))
    return rows[:limit]


def top_scoring_teams(
    ds: Dataset,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> list[dict]:
    by_team: dict[str, int] = defaultdict(int)
    matches_played: dict[str, int] = defaultdict(int)
    for m in ds.matches:
        if not _match_in_competition(m, competition):
            continue
        if season is not None and m.season != season:
            continue
        if m.home_goal is None or m.away_goal is None:
            continue
        if m.home_norm:
            by_team[m.home_norm] += m.home_goal
            matches_played[m.home_norm] += 1
        if m.away_norm:
            by_team[m.away_norm] += m.away_goal
            matches_played[m.away_norm] += 1
    rows = [
        {"team": t, "goals": g, "matches": matches_played[t]}
        for t, g in by_team.items()
        if t
    ]
    rows.sort(key=lambda r: -r["goals"])
    return rows[:limit]


def champion(ds: Dataset, competition: str, season: int) -> dict | None:
    table = competition_standings(ds, competition, season)
    return table[0] if table else None
