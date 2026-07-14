"""Query engine for the Brazilian soccer knowledge graph.

All functions take a :class:`data_loader.SoccerDatabase` and return plain
dicts/lists so they are easy to test and to format for MCP responses.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date as Date
from datetime import timedelta
from typing import Optional

from data_loader import SOURCE_PRIORITY, SoccerDatabase, parse_date
from models import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    SERIE_C,
    Match,
)
from team_names import TeamKey, parse_team, strip_accents

COMPETITIONS = [SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES]


def resolve_competition(text: Optional[str]) -> Optional[str]:
    """Map fuzzy user input ('brasileirao', 'Serie A', 'cup') to a canonical
    competition name, or None when no filter was requested."""
    if not text:
        return None
    cleaned = strip_accents(text).lower()
    if "liber" in cleaned:
        return LIBERTADORES
    if "copa do brasil" in cleaned or "cup" in cleaned:
        return COPA_DO_BRASIL
    if "serie b" in cleaned or cleaned == "b":
        return SERIE_B
    if "serie c" in cleaned or cleaned == "c":
        return SERIE_C
    if "brasileir" in cleaned or "serie a" in cleaned or "campeonato" in cleaned:
        return SERIE_A
    raise ValueError(
        f"Unknown competition {text!r}. Known competitions: "
        + ", ".join(COMPETITIONS)
    )


# ---------------------------------------------------------------------------
# Match filtering
# ---------------------------------------------------------------------------

def _dedupe(matches: list[Match]) -> list[Match]:
    """Drop duplicate rows for the same real-world match across source files.

    Two rows are considered the same match when both team base names and the
    final score agree and the dates are within one day of each other (the
    extended-stats file records some kick-offs in UTC, shifting the date).
    The source earlier in SOURCE_PRIORITY wins.
    """
    rank = {source: index for index, source in enumerate(SOURCE_PRIORITY)}
    ordered = sorted(matches, key=lambda m: rank.get(m.source, 99))
    seen: set[tuple] = set()
    kept = []
    one_day = timedelta(days=1)
    for match in ordered:
        teams_and_score = (match.home_key.base, match.away_key.base,
                           match.home_goals, match.away_goals)
        if match.date is not None:
            nearby = (match.date - one_day, match.date, match.date + one_day)
            if any((day, *teams_and_score) in seen for day in nearby):
                continue
            seen.add((match.date, *teams_and_score))
        kept.append(match)
    return kept


def filter_matches(
    db: SoccerDatabase,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    dedupe: bool = True,
) -> list[Match]:
    """Filter matches by team(s), competition, season and date range.

    Results are de-duplicated across overlapping source files and sorted
    newest first.
    """
    comp = resolve_competition(competition)
    team_key = parse_team(team) if team else None
    opp_key = parse_team(opponent) if opponent else None
    start = parse_date(date_from) if date_from else None
    end = parse_date(date_to) if date_to else None

    selected = []
    for match in db.matches:
        if comp and match.competition != comp:
            continue
        if season is not None and match.season != season:
            continue
        if start and (match.date is None or match.date < start):
            continue
        if end and (match.date is None or match.date > end):
            continue
        if team_key:
            home_is_team = match.home_key.matches(team_key)
            away_is_team = match.away_key.matches(team_key)
            if not (home_is_team or away_is_team):
                continue
            if opp_key:
                other = match.away_key if home_is_team else match.home_key
                if not other.matches(opp_key):
                    continue
        elif opp_key:
            if not (match.home_key.matches(opp_key)
                    or match.away_key.matches(opp_key)):
                continue
        selected.append(match)

    if dedupe:
        selected = _dedupe(selected)
    selected.sort(key=lambda m: (m.date or Date.min), reverse=True)
    return selected


def match_to_dict(match: Match) -> dict:
    return {
        "date": match.date.isoformat() if match.date else None,
        "competition": match.competition,
        "round": match.round,
        "stage": match.stage,
        "season": match.season,
        "home_team": match.home_name,
        "away_team": match.away_name,
        "home_goals": match.home_goals,
        "away_goals": match.away_goals,
        "score": match.score_line(),
        "source": match.source,
    }


# ---------------------------------------------------------------------------
# Head-to-head and team statistics
# ---------------------------------------------------------------------------

def head_to_head(
    db: SoccerDatabase,
    team1: str,
    team2: str,
    competition: Optional[str] = None,
) -> dict:
    """Full head-to-head record between two teams across all competitions."""
    key1, key2 = parse_team(team1), parse_team(team2)
    matches = filter_matches(db, team=team1, opponent=team2,
                             competition=competition)
    wins1 = wins2 = draws = goals1 = goals2 = 0
    for match in matches:
        if not match.has_score:
            continue
        team1_home = match.home_key.matches(key1)
        for1 = match.home_goals if team1_home else match.away_goals
        for2 = match.away_goals if team1_home else match.home_goals
        goals1 += for1
        goals2 += for2
        if for1 > for2:
            wins1 += 1
        elif for2 > for1:
            wins2 += 1
        else:
            draws += 1
    return {
        "team1": db.display_name(key1),
        "team2": db.display_name(key2),
        "matches": len(matches),
        "team1_wins": wins1,
        "team2_wins": wins2,
        "draws": draws,
        "team1_goals": goals1,
        "team2_goals": goals2,
        "recent_matches": [match_to_dict(m) for m in matches],
    }


def team_statistics(
    db: SoccerDatabase,
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> dict:
    """Win/draw/loss record and goals for a team, optionally filtered by
    season, competition and venue ('home', 'away' or 'all')."""
    if venue not in ("all", "home", "away"):
        raise ValueError("venue must be 'all', 'home' or 'away'")
    key = parse_team(team)
    matches = filter_matches(db, team=team, season=season,
                             competition=competition)
    played = wins = draws = losses = goals_for = goals_against = 0
    by_competition: dict[str, Counter] = defaultdict(Counter)
    for match in matches:
        if not match.has_score:
            continue
        is_home = match.home_key.matches(key)
        if venue == "home" and not is_home:
            continue
        if venue == "away" and is_home:
            continue
        scored = match.home_goals if is_home else match.away_goals
        conceded = match.away_goals if is_home else match.home_goals
        played += 1
        goals_for += scored
        goals_against += conceded
        bucket = by_competition[match.competition]
        bucket["played"] += 1
        if scored > conceded:
            wins += 1
            bucket["wins"] += 1
        elif scored < conceded:
            losses += 1
            bucket["losses"] += 1
        else:
            draws += 1
            bucket["draws"] += 1
    return {
        "team": db.display_name(key),
        "season": season,
        "competition": resolve_competition(competition),
        "venue": venue,
        "played": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "win_rate": round(100 * wins / played, 1) if played else 0.0,
        "by_competition": {comp: dict(c) for comp, c in by_competition.items()},
    }


# ---------------------------------------------------------------------------
# Standings and league-wide statistics
# ---------------------------------------------------------------------------

def _pick_standings_source(db: SoccerDatabase, competition: str,
                           season: int) -> list[Match]:
    """Standings must come from a single source file to avoid double counting
    matches that appear in several datasets.  Pick the source with the most
    scored matches for that competition+season."""
    by_source: dict[str, list[Match]] = defaultdict(list)
    for match in db.matches:
        if (match.competition == competition and match.season == season
                and match.has_score):
            by_source[match.source].append(match)
    if not by_source:
        return []
    rank = {source: index for index, source in enumerate(SOURCE_PRIORITY)}
    best = max(by_source, key=lambda s: (len(by_source[s]), -rank.get(s, 99)))
    return by_source[best]


def competition_standings(
    db: SoccerDatabase,
    season: int,
    competition: str = "serie a",
) -> dict:
    """League table calculated from match results (3 pts win, 1 pt draw)."""
    comp = resolve_competition(competition) or SERIE_A
    matches = _pick_standings_source(db, comp, season)
    table: dict[str, dict] = {}

    def row(key: TeamKey) -> dict:
        return table.setdefault(str(key), {
            "team": db.display_name(key), "played": 0, "wins": 0,
            "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0,
        })

    for match in matches:
        home, away = row(match.home_key), row(match.away_key)
        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += match.home_goals
        home["goals_against"] += match.away_goals
        away["goals_for"] += match.away_goals
        away["goals_against"] += match.home_goals
        if match.home_goals > match.away_goals:
            home["wins"] += 1
            away["losses"] += 1
        elif match.home_goals < match.away_goals:
            away["wins"] += 1
            home["losses"] += 1
        else:
            home["draws"] += 1
            away["draws"] += 1

    standings = list(table.values())
    for entry in standings:
        entry["points"] = 3 * entry["wins"] + entry["draws"]
        entry["goal_difference"] = entry["goals_for"] - entry["goals_against"]
    standings.sort(key=lambda e: (e["points"], e["wins"],
                                  e["goal_difference"], e["goals_for"]),
                   reverse=True)
    for position, entry in enumerate(standings, start=1):
        entry["position"] = position
    return {
        "competition": comp,
        "season": season,
        "matches_counted": len(matches),
        "standings": standings,
    }


def goal_statistics(
    db: SoccerDatabase,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict:
    """Average goals per match and home/draw/away outcome rates."""
    matches = [m for m in filter_matches(db, competition=competition,
                                         season=season) if m.has_score]
    total = len(matches)
    if not total:
        return {"matches": 0}
    goals = sum(m.home_goals + m.away_goals for m in matches)
    home_wins = sum(1 for m in matches if m.home_goals > m.away_goals)
    away_wins = sum(1 for m in matches if m.away_goals > m.home_goals)
    draws = total - home_wins - away_wins
    return {
        "competition": resolve_competition(competition),
        "season": season,
        "matches": total,
        "total_goals": goals,
        "avg_goals_per_match": round(goals / total, 2),
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_win_rate": round(100 * home_wins / total, 1),
        "draw_rate": round(100 * draws / total, 1),
        "away_win_rate": round(100 * away_wins / total, 1),
    }


def biggest_wins(
    db: SoccerDatabase,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> list[dict]:
    """Matches with the largest margin of victory."""
    matches = [m for m in filter_matches(db, competition=competition,
                                         season=season) if m.has_score]
    matches.sort(key=lambda m: (abs(m.home_goals - m.away_goals),
                                m.home_goals + m.away_goals,
                                m.date or Date.min),
                 reverse=True)
    results = []
    for match in matches[:max(0, limit)]:
        entry = match_to_dict(match)
        entry["margin"] = abs(match.home_goals - match.away_goals)
        results.append(entry)
    return results


def best_records(
    db: SoccerDatabase,
    venue: str = "all",
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 10,
    limit: int = 10,
) -> list[dict]:
    """Teams ranked by win rate, optionally restricted to home or away games."""
    if venue not in ("all", "home", "away"):
        raise ValueError("venue must be 'all', 'home' or 'away'")
    matches = [m for m in filter_matches(db, competition=competition,
                                         season=season) if m.has_score]
    records: dict[str, dict] = {}

    def tally(key: TeamKey, scored: int, conceded: int) -> None:
        entry = records.setdefault(str(key), {
            "team": db.display_name(key), "played": 0, "wins": 0,
            "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0,
        })
        entry["played"] += 1
        entry["goals_for"] += scored
        entry["goals_against"] += conceded
        if scored > conceded:
            entry["wins"] += 1
        elif scored < conceded:
            entry["losses"] += 1
        else:
            entry["draws"] += 1

    for match in matches:
        if venue in ("all", "home"):
            tally(match.home_key, match.home_goals, match.away_goals)
        if venue in ("all", "away"):
            tally(match.away_key, match.away_goals, match.home_goals)

    ranked = [e for e in records.values() if e["played"] >= min_matches]
    for entry in ranked:
        entry["win_rate"] = round(100 * entry["wins"] / entry["played"], 1)
    ranked.sort(key=lambda e: (e["win_rate"], e["played"]), reverse=True)
    return ranked[:max(0, limit)]


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------

_POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
    "midfielder": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM",
                   "RDM", "LAM", "RAM"},
    "forward": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
}


def _norm(text: str) -> str:
    return strip_accents(text or "").lower().strip()


def _position_set(position: Optional[str]) -> Optional[set[str]]:
    if not position:
        return None
    cleaned = _norm(position).rstrip("s")
    if cleaned in _POSITION_GROUPS:
        return _POSITION_GROUPS[cleaned]
    return {part.strip().upper() for part in position.split(",") if part.strip()}


def player_to_dict(player, include_skills: bool = False) -> dict:
    data = {
        "name": player.name,
        "age": player.age,
        "nationality": player.nationality,
        "overall": player.overall,
        "potential": player.potential,
        "club": player.club,
        "position": player.position,
        "jersey_number": player.jersey_number,
        "value": player.value,
        "wage": player.wage,
        "height": player.height,
        "weight": player.weight,
        "preferred_foot": player.preferred_foot,
    }
    if include_skills:
        data["skills"] = dict(player.skills)
    return data


def search_players(
    db: SoccerDatabase,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> dict:
    """Search the FIFA player data; results sorted by overall rating."""
    name_q = _norm(name) if name else None
    nat_q = _norm(nationality) if nationality else None
    club_q = _norm(club) if club else None
    positions = _position_set(position)

    found = []
    for player in db.players:
        if name_q and name_q not in _norm(player.name):
            continue
        if nat_q and nat_q not in _norm(player.nationality):
            continue
        if club_q and club_q not in _norm(player.club):
            continue
        if positions and player.position not in positions:
            continue
        if min_overall is not None and (player.overall or 0) < min_overall:
            continue
        found.append(player)
    found.sort(key=lambda p: (p.overall or 0, p.potential or 0), reverse=True)
    return {
        "total_matches": len(found),
        "players": [player_to_dict(p) for p in found[:max(0, limit)]],
    }


def get_player(db: SoccerDatabase, name: str) -> Optional[dict]:
    """Detailed profile for the best-matching player name."""
    query = _norm(name)
    exact = [p for p in db.players if _norm(p.name) == query]
    candidates = exact or [p for p in db.players if query in _norm(p.name)]
    if not candidates:
        return None
    best = max(candidates, key=lambda p: p.overall or 0)
    profile = player_to_dict(best, include_skills=True)
    profile["other_matches"] = [
        p.name for p in candidates if p is not best
    ][:10]
    return profile


# ---------------------------------------------------------------------------
# Dataset overview
# ---------------------------------------------------------------------------

def data_summary(db: SoccerDatabase) -> dict:
    """Coverage summary: match counts, season ranges, players, teams."""
    by_competition: dict[str, dict] = {}
    for match in db.matches:
        entry = by_competition.setdefault(match.competition, {
            "matches": 0, "first_season": match.season,
            "last_season": match.season,
        })
        entry["matches"] += 1
        if match.season is not None:
            if entry["first_season"] is None or match.season < entry["first_season"]:
                entry["first_season"] = match.season
            if entry["last_season"] is None or match.season > entry["last_season"]:
                entry["last_season"] = match.season
    teams = {str(m.home_key) for m in db.matches} | {
        str(m.away_key) for m in db.matches}
    return {
        "total_matches": len(db.matches),
        "total_players": len(db.players),
        "total_teams": len(teams),
        "brazilian_players": sum(
            1 for p in db.players if p.nationality == "Brazil"),
        "competitions": by_competition,
        "source_files": db.sources(),
    }
