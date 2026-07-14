"""Query engine for the Brazilian Soccer MCP server.

All functions operate on the in-memory SoccerDatabase and return plain
dicts/lists suitable for JSON serialization back to the LLM client.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional

from soccer_data import (
    COMPETITIONS,
    POSITION_GROUPS,
    Match,
    Player,
    get_database,
    normalize_competition,
    normalize_team,
    parse_date,
    strip_accents,
)


class TeamNotFoundError(ValueError):
    pass


class TeamRef:
    """A resolved team reference: the bases it can match plus an optional state.

    A query like "Flamengo-RJ" matches only RJ records; plain "Flamengo"
    matches any state (including records where the state is unknown).
    """

    def __init__(self, query: str):
        db = get_database()
        base, state = normalize_team(query)
        known_bases = {m.home_base for m in db.matches} | {m.away_base for m in db.matches}
        if base in known_bases:
            self.bases = [base]
        else:
            self.bases = sorted(b for b in known_bases if base and base in b)
        if not self.bases:
            raise TeamNotFoundError(
                f"Team '{query}' not found in the datasets. "
                f"Try a common short name like 'Flamengo' or 'Palmeiras'."
            )
        self.state = state
        self.display = db.display_name(self.bases[0])

    def matches_side(self, base: str, state: Optional[str]) -> bool:
        if base not in self.bases:
            return False
        if self.state and state and self.state != state:
            return False
        return True

    def is_home(self, m: Match) -> bool:
        return self.matches_side(m.home_base, m.home_state)

    def is_away(self, m: Match) -> bool:
        return self.matches_side(m.away_base, m.away_state)

    def involves(self, m: Match) -> bool:
        return self.is_home(m) or self.is_away(m)


def _team_matches(team: str, competition: Optional[str] = None,
                  season: Optional[int] = None) -> tuple[TeamRef, list[Match]]:
    ref = TeamRef(team)
    comp = normalize_competition(competition)
    matches = [
        m for m in get_database().matches
        if ref.involves(m)
        and (comp is None or m.competition == comp)
        and (season is None or m.season == season)
    ]
    return ref, matches


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------

def search_matches(team: Optional[str] = None, opponent: Optional[str] = None,
                   competition: Optional[str] = None, season: Optional[int] = None,
                   date_from: Optional[str] = None, date_to: Optional[str] = None,
                   limit: int = 50) -> dict:
    """Search matches by team(s), competition, season, and/or date range."""
    db = get_database()
    matches = db.matches

    if team:
        ref = TeamRef(team)
        matches = [m for m in matches if ref.involves(m)]
    if opponent:
        opp = TeamRef(opponent)
        matches = [m for m in matches if opp.involves(m)]

    comp = normalize_competition(competition)
    if comp:
        matches = [m for m in matches if m.competition == comp]
    if season is not None:
        matches = [m for m in matches if m.season == season]

    start = parse_date(date_from)
    end = parse_date(date_to)
    if start:
        matches = [m for m in matches if m.date and m.date >= start]
    if end:
        end = end.replace(hour=23, minute=59, second=59)
        matches = [m for m in matches if m.date and m.date <= end]

    matches = sorted(matches, key=lambda m: m.date or datetime.min,
                     reverse=True)
    return {
        "total_matches": len(matches),
        "showing": min(limit, len(matches)),
        "matches": [m.to_dict() for m in matches[:limit]],
    }


def head_to_head(team1: str, team2: str, competition: Optional[str] = None) -> dict:
    """All matches between two teams plus the aggregate head-to-head record."""
    ref1 = TeamRef(team1)
    ref2 = TeamRef(team2)
    comp = normalize_competition(competition)

    matches = [
        m for m in get_database().matches
        if ((ref1.is_home(m) and ref2.is_away(m))
            or (ref2.is_home(m) and ref1.is_away(m)))
        and (comp is None or m.competition == comp)
    ]
    matches.sort(key=lambda m: m.date or datetime.min, reverse=True)

    name1, name2 = ref1.display, ref2.display
    wins1 = wins2 = draws = goals1 = goals2 = 0
    for m in matches:
        if not m.has_score:
            continue
        t1_home = ref1.is_home(m)
        g1, g2 = (m.home_goal, m.away_goal) if t1_home else (m.away_goal, m.home_goal)
        goals1 += g1
        goals2 += g2
        if g1 > g2:
            wins1 += 1
        elif g2 > g1:
            wins2 += 1
        else:
            draws += 1

    return {
        "teams": [name1, name2],
        "total_matches": len(matches),
        "record": {
            f"{name1}_wins": wins1,
            f"{name2}_wins": wins2,
            "draws": draws,
        },
        "goals": {name1: goals1, name2: goals2},
        "summary": (
            f"Head-to-head in dataset: {name1} {wins1} wins, "
            f"{name2} {wins2} wins, {draws} draws"
        ),
        "matches": [m.to_dict() for m in matches],
    }


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------

def team_stats(team: str, season: Optional[int] = None,
               competition: Optional[str] = None, venue: str = "all") -> dict:
    """Win/draw/loss record and goal stats for a team.

    venue: 'all', 'home', or 'away'.
    """
    ref, matches = _team_matches(team, competition, season)
    name = ref.display

    wins = draws = losses = goals_for = goals_against = 0
    counted = 0
    for m in matches:
        if not m.has_score:
            continue
        is_home = ref.is_home(m)
        if venue == "home" and not is_home:
            continue
        if venue == "away" and is_home:
            continue
        counted += 1
        gf, ga = (m.home_goal, m.away_goal) if is_home else (m.away_goal, m.home_goal)
        goals_for += gf
        goals_against += ga
        if gf > ga:
            wins += 1
        elif gf < ga:
            losses += 1
        else:
            draws += 1

    comp = normalize_competition(competition)
    return {
        "team": name,
        "season": season,
        "competition": COMPETITIONS.get(comp, comp) if comp else "all competitions",
        "venue": venue,
        "matches": counted,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goals_for - goals_against,
        "win_rate": round(100 * wins / counted, 1) if counted else 0.0,
        "points": wins * 3 + draws,
    }


def team_competitions(team: str) -> dict:
    """Which competitions and seasons a team appears in across the datasets."""
    ref, matches = _team_matches(team)
    name = ref.display
    comp_seasons: dict[str, set] = defaultdict(set)
    for m in matches:
        if m.season:
            comp_seasons[m.competition_name].add(m.season)
    return {
        "team": name,
        "total_matches": len(matches),
        "competitions": {
            comp: sorted(seasons) for comp, seasons in sorted(comp_seasons.items())
        },
    }


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------

def standings(season: int, competition: str = "serie-a") -> dict:
    """League table for a season, calculated from match results (3 pts/win)."""
    comp = normalize_competition(competition) or "serie-a"
    matches = [
        m for m in get_database().matches
        if m.competition == comp and m.season == season and m.has_score
    ]
    if not matches:
        seasons = sorted({m.season for m in get_database().matches
                          if m.competition == comp and m.season})
        return {
            "error": f"No {COMPETITIONS.get(comp, comp)} matches for season {season}.",
            "available_seasons": seasons,
        }

    rows: dict[str, dict] = {}
    for m in matches:
        for base in (m.home_base, m.away_base):
            rows.setdefault(base, {
                "team": get_database().display_name(base), "played": 0, "wins": 0, "draws": 0,
                "losses": 0, "goals_for": 0, "goals_against": 0,
            })
        h, a = rows[m.home_base], rows[m.away_base]
        h["played"] += 1
        a["played"] += 1
        h["goals_for"] += m.home_goal
        h["goals_against"] += m.away_goal
        a["goals_for"] += m.away_goal
        a["goals_against"] += m.home_goal
        if m.home_goal > m.away_goal:
            h["wins"] += 1
            a["losses"] += 1
        elif m.home_goal < m.away_goal:
            a["wins"] += 1
            h["losses"] += 1
        else:
            h["draws"] += 1
            a["draws"] += 1

    table = []
    for row in rows.values():
        row["points"] = row["wins"] * 3 + row["draws"]
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
        table.append(row)
    table.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_difference"],
                              -r["goals_for"]))
    for i, row in enumerate(table, 1):
        row["position"] = i

    games = [r["played"] for r in table]
    complete = comp != "serie-a" or (len(set(games)) == 1 and games[0] in (38, 42, 44, 46))
    result = {
        "competition": COMPETITIONS.get(comp, comp),
        "season": season,
        "matches_in_dataset": len(matches),
        "standings": table,
    }
    if comp == "serie-a":
        result["champion"] = table[0]["team"]
        result["relegated"] = [r["team"] for r in table[-4:]] if complete else None
        if not complete:
            result["note"] = (
                "Dataset does not cover the full season; standings are partial "
                "and champion/relegation cannot be determined reliably."
            )
    return result


def competition_seasons(competition: Optional[str] = None) -> dict:
    """Summary of competitions, seasons, and match counts in the datasets."""
    comp = normalize_competition(competition)
    summary: dict[str, dict] = {}
    for m in get_database().matches:
        if comp and m.competition != comp:
            continue
        entry = summary.setdefault(m.competition_name, {"matches": 0, "seasons": set()})
        entry["matches"] += 1
        if m.season:
            entry["seasons"].add(m.season)
    return {
        name: {"matches": e["matches"],
               "seasons": f"{min(e['seasons'])}-{max(e['seasons'])}" if e["seasons"] else None}
        for name, e in sorted(summary.items())
    }


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------

def competition_stats(competition: Optional[str] = None,
                      season: Optional[int] = None) -> dict:
    """Aggregate stats: goals per match, home/away win rates."""
    comp = normalize_competition(competition)
    matches = [
        m for m in get_database().matches
        if m.has_score
        and (comp is None or m.competition == comp)
        and (season is None or m.season == season)
    ]
    if not matches:
        return {"error": "No matches found for the given filters."}

    total_goals = sum(m.home_goal + m.away_goal for m in matches)
    home_wins = sum(1 for m in matches if m.home_goal > m.away_goal)
    away_wins = sum(1 for m in matches if m.away_goal > m.home_goal)
    draws = len(matches) - home_wins - away_wins
    return {
        "competition": COMPETITIONS.get(comp, comp) if comp else "all competitions",
        "season": season if season else "all seasons",
        "matches": len(matches),
        "total_goals": total_goals,
        "avg_goals_per_match": round(total_goals / len(matches), 2),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(100 * home_wins / len(matches), 1),
        "away_win_rate": round(100 * away_wins / len(matches), 1),
        "draw_rate": round(100 * draws / len(matches), 1),
    }


def biggest_wins(competition: Optional[str] = None, season: Optional[int] = None,
                 limit: int = 10) -> dict:
    """Matches with the largest goal margin."""
    comp = normalize_competition(competition)
    matches = [
        m for m in get_database().matches
        if m.has_score
        and (comp is None or m.competition == comp)
        and (season is None or m.season == season)
    ]
    matches.sort(key=lambda m: (abs(m.home_goal - m.away_goal),
                                m.home_goal + m.away_goal), reverse=True)
    return {
        "matches": [
            {**m.to_dict(), "margin": abs(m.home_goal - m.away_goal)}
            for m in matches[:limit]
        ],
    }


def best_records(season: Optional[int] = None, competition: str = "serie-a",
                 venue: str = "all", min_matches: int = 10, limit: int = 10) -> dict:
    """Teams ranked by win rate (optionally home-only or away-only)."""
    comp = normalize_competition(competition) or "serie-a"
    stats: dict[str, dict] = {}
    for m in get_database().matches:
        if not m.has_score or m.competition != comp:
            continue
        if season is not None and m.season != season:
            continue
        for base, is_home in ((m.home_base, True), (m.away_base, False)):
            if venue == "home" and not is_home:
                continue
            if venue == "away" and is_home:
                continue
            s = stats.setdefault(base, {"team": get_database().display_name(base), "matches": 0,
                                        "wins": 0, "draws": 0, "losses": 0})
            s["matches"] += 1
            gf, ga = ((m.home_goal, m.away_goal) if is_home
                      else (m.away_goal, m.home_goal))
            if gf > ga:
                s["wins"] += 1
            elif gf == ga:
                s["draws"] += 1
            else:
                s["losses"] += 1

    rows = [s for s in stats.values() if s["matches"] >= min_matches]
    for s in rows:
        s["win_rate"] = round(100 * s["wins"] / s["matches"], 1)
    rows.sort(key=lambda s: (-s["win_rate"], -s["wins"]))
    return {
        "competition": COMPETITIONS.get(comp, comp),
        "season": season if season else "all seasons",
        "venue": venue,
        "min_matches": min_matches,
        "teams": rows[:limit],
    }


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------

def _match_player_name(query: str, player: Player) -> bool:
    """Accent-insensitive name match, tolerant of FIFA's abbreviated first
    names: "Gabriel Barbosa" matches "G. Barbosa" and vice versa."""
    key = strip_accents(query).lower().strip()
    if key in player.name_key:
        return True
    name_tokens = player.name_key.split()
    query_tokens = key.split()
    if len(query_tokens) < 2:
        return False

    def token_matches(q: str) -> bool:
        q_bare = q.rstrip(".")
        for n in name_tokens:
            n_bare = n.rstrip(".")
            if n_bare.startswith(q_bare):
                return True
            # "Gabriel" matches the initial "G." (but not the reverse for
            # plain tokens, which would be far too loose).
            if n.endswith(".") and q_bare.startswith(n_bare):
                return True
        return False

    return all(token_matches(q) for q in query_tokens)


def _match_position(player: Player, position: str) -> bool:
    pos = position.strip().lower()
    if pos in POSITION_GROUPS:
        return player.position in POSITION_GROUPS[pos]
    return player.position.upper() == position.strip().upper()


def search_players(name: Optional[str] = None, nationality: Optional[str] = None,
                   club: Optional[str] = None, position: Optional[str] = None,
                   min_overall: Optional[int] = None, limit: int = 20) -> dict:
    """Search FIFA player data by name, nationality, club, and/or position."""
    players = get_database().players
    if name:
        players = [p for p in players if _match_player_name(name, p)]
    if nationality:
        nat = strip_accents(nationality).lower()
        players = [p for p in players if strip_accents(p.nationality).lower() == nat]
    if club:
        club_key = strip_accents(club).lower()
        players = [p for p in players if club_key in strip_accents(p.club).lower()]
    if position:
        players = [p for p in players if _match_position(p, position)]
    if min_overall is not None:
        players = [p for p in players if p.overall is not None and p.overall >= min_overall]

    players = sorted(players, key=lambda p: -(p.overall or 0))
    return {
        "total_players": len(players),
        "showing": min(limit, len(players)),
        "players": [p.to_dict() for p in players[:limit]],
    }


def get_player(name: str) -> dict:
    """Detailed profile (including skill ratings) for the best name match."""
    key = strip_accents(name).lower()
    candidates = [p for p in get_database().players if _match_player_name(name, p)]
    if not candidates:
        return {"error": f"No player matching '{name}' found in the FIFA dataset."}
    candidates.sort(key=lambda p: (p.name_key != key, -(p.overall or 0)))
    player = candidates[0]
    result = player.to_dict(include_skills=True)
    if len(candidates) > 1:
        result["other_matches"] = [
            {"name": p.name, "club": p.club, "overall": p.overall}
            for p in candidates[1:6]
        ]
    return result


def top_players(nationality: Optional[str] = None, club: Optional[str] = None,
                position: Optional[str] = None, limit: int = 10) -> dict:
    """Highest-rated players, optionally filtered by nationality/club/position."""
    result = search_players(nationality=nationality, club=club,
                            position=position, limit=limit)
    result["criteria"] = {
        "nationality": nationality, "club": club, "position": position,
        "sorted_by": "overall rating",
    }
    return result
