"""Pure query functions operating on a :class:`DataStore`.

Every function takes a ``DataStore`` and keyword args and returns a JSON-able
dict (lists of dicts, ints, floats, strings). Keeping these pure makes them
trivial to unit-test and lets the MCP server layer remain a thin wrapper.

The query surface mirrors the five categories called out in the spec:

    1. Match queries        — search_matches, head_to_head, last_match
    2. Team queries         — team_record, top_scoring_teams, compare_teams
    3. Player queries       — search_players, top_players_by_nationality,
                              top_players_by_club
    4. Competition queries  — season_standings, biggest_wins,
                              list_competitions, list_seasons
    5. Statistical analysis — average_goals_per_match, home_away_split

Team-name parameters are normalized via :func:`normalize_team` so callers can
pass any spelling ("Atletico-MG", "Galo", "Atlético Mineiro").
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .data_loader import DataStore
from .normalize import label_for, normalize_team

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _match_to_dict(row: pd.Series) -> dict[str, Any]:
    date = row.get("date")
    date_str = ""
    if isinstance(date, pd.Timestamp) and not pd.isna(date):
        date_str = date.strftime("%Y-%m-%d")
    return {
        "date": date_str,
        "season": int(row.get("season", 0) or 0),
        "competition": row.get("competition", ""),
        "round": str(row.get("round", "") or ""),
        "stage": str(row.get("stage", "") or ""),
        "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""),
        "home_goal": int(row.get("home_goal", 0)),
        "away_goal": int(row.get("away_goal", 0)),
        "source": row.get("source", ""),
    }


def _matches_for_team(df: pd.DataFrame, team_key: str) -> pd.DataFrame:
    if not team_key:
        return df.iloc[0:0]
    mask = (df["home_team_norm"] == team_key) | (df["away_team_norm"] == team_key)
    return df[mask]


def _apply_filters(
    df: pd.DataFrame,
    *,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    out = df
    if competition:
        comp_lower = competition.lower()
        out = out[out["competition"].str.lower().str.contains(comp_lower, na=False)]
    if season is not None:
        out = out[out["season"] == int(season)]
    if start_date:
        out = out[out["date"] >= pd.to_datetime(start_date)]
    if end_date:
        out = out[out["date"] <= pd.to_datetime(end_date)]
    return out


# ---------------------------------------------------------------------------
# 1. Match queries
# ---------------------------------------------------------------------------


def search_matches(
    store: DataStore,
    *,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Return matches matching the given filters, most-recent first."""
    df = store.matches
    if team:
        df = _matches_for_team(df, normalize_team(team))
    if opponent:
        df = _matches_for_team(df, normalize_team(opponent))
    df = _apply_filters(
        df,
        competition=competition,
        season=season,
        start_date=start_date,
        end_date=end_date,
    )
    df = df.sort_values("date", ascending=False, na_position="last")
    total = int(len(df))
    rows = [_match_to_dict(r) for _, r in df.head(limit).iterrows()]
    return {"count": total, "returned": len(rows), "matches": rows}


def head_to_head(
    store: DataStore,
    team_a: str,
    team_b: str,
    *,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Compute a head-to-head record between two teams."""
    key_a = normalize_team(team_a)
    key_b = normalize_team(team_b)
    if not key_a or not key_b:
        return {"error": "Both team names must be provided."}
    df = store.matches
    mask = (
        ((df["home_team_norm"] == key_a) & (df["away_team_norm"] == key_b))
        | ((df["home_team_norm"] == key_b) & (df["away_team_norm"] == key_a))
    )
    df = df[mask]
    df = _apply_filters(df, competition=competition, season=season)
    a_wins = b_wins = draws = a_goals = b_goals = 0
    for _, row in df.iterrows():
        if row["home_team_norm"] == key_a:
            a, b = row["home_goal"], row["away_goal"]
        else:
            a, b = row["away_goal"], row["home_goal"]
        a_goals += a
        b_goals += b
        if a > b:
            a_wins += 1
        elif b > a:
            b_wins += 1
        else:
            draws += 1
    df_sorted = df.sort_values("date", ascending=False, na_position="last")
    return {
        "team_a": label_for(key_a),
        "team_b": label_for(key_b),
        "matches": int(len(df)),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_goals,
        "team_b_goals": b_goals,
        "recent_matches": [_match_to_dict(r) for _, r in df_sorted.head(10).iterrows()],
    }


def last_match(store: DataStore, team_a: str, team_b: str) -> dict[str, Any]:
    """Return the single most recent match between two teams."""
    h2h = head_to_head(store, team_a, team_b)
    if h2h.get("recent_matches"):
        return {"team_a": h2h["team_a"], "team_b": h2h["team_b"], "match": h2h["recent_matches"][0]}
    return {"team_a": h2h.get("team_a", team_a), "team_b": h2h.get("team_b", team_b), "match": None}


# ---------------------------------------------------------------------------
# 2. Team queries
# ---------------------------------------------------------------------------


def team_record(
    store: DataStore,
    team: str,
    *,
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
) -> dict[str, Any]:
    """Return wins/draws/losses and goals for a single team.

    ``venue`` may be "home", "away", or omitted to count both.
    """
    key = normalize_team(team)
    if not key:
        return {"error": "Team name must be provided."}
    df = store.matches
    df = _apply_filters(df, competition=competition, season=season)
    if venue == "home":
        df = df[df["home_team_norm"] == key]
    elif venue == "away":
        df = df[df["away_team_norm"] == key]
    else:
        df = df[(df["home_team_norm"] == key) | (df["away_team_norm"] == key)]
    wins = draws = losses = gf = ga = 0
    for _, row in df.iterrows():
        if row["home_team_norm"] == key:
            for_, against = row["home_goal"], row["away_goal"]
        else:
            for_, against = row["away_goal"], row["home_goal"]
        gf += for_
        ga += against
        if for_ > against:
            wins += 1
        elif for_ < against:
            losses += 1
        else:
            draws += 1
    matches = wins + draws + losses
    return {
        "team": label_for(key),
        "competition": competition,
        "season": season,
        "venue": venue,
        "matches": matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "points": wins * 3 + draws,
        "win_rate": round(wins / matches, 3) if matches else 0.0,
    }


def top_scoring_teams(
    store: DataStore,
    *,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Rank teams by total goals scored, optionally filtered by season/comp."""
    df = _apply_filters(store.matches, competition=competition, season=season)
    home = df.groupby("home_team_norm")["home_goal"].sum()
    away = df.groupby("away_team_norm")["away_goal"].sum()
    totals = home.add(away, fill_value=0).sort_values(ascending=False)
    rows = [
        {"team": label_for(key), "goals": int(value)}
        for key, value in totals.head(limit).items()
        if key
    ]
    return {"competition": competition, "season": season, "teams": rows}


def compare_teams(
    store: DataStore,
    team_a: str,
    team_b: str,
    *,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Stat-by-stat comparison of two teams plus their head-to-head."""
    record_a = team_record(store, team_a, competition=competition, season=season)
    record_b = team_record(store, team_b, competition=competition, season=season)
    return {
        "team_a": record_a,
        "team_b": record_b,
        "head_to_head": head_to_head(
            store, team_a, team_b, competition=competition, season=season
        ),
    }


# ---------------------------------------------------------------------------
# 3. Player queries
# ---------------------------------------------------------------------------


def search_players(
    store: DataStore,
    *,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Filter the FIFA player table by any combination of attributes."""
    df = store.players
    if name:
        df = df[df["name_lower"].str.contains(name.lower(), na=False)]
    if nationality:
        df = df[df["nationality_lower"] == nationality.lower()]
    if club:
        key = normalize_team(club)
        df = df[df["club_norm"] == key]
    if position:
        df = df[df["position"].str.upper() == position.upper()]
    if min_overall is not None:
        df = df[df["overall"].fillna(0) >= int(min_overall)]
    df = df.sort_values("overall", ascending=False, na_position="last")
    total = int(len(df))
    rows = [_player_to_dict(r) for _, r in df.head(limit).iterrows()]
    return {"count": total, "returned": len(rows), "players": rows}


def _player_to_dict(row: pd.Series) -> dict[str, Any]:
    return {
        "id": int(row["id"]) if pd.notna(row["id"]) else None,
        "name": row["name"],
        "age": int(row["age"]) if pd.notna(row["age"]) else None,
        "nationality": row["nationality"],
        "overall": int(row["overall"]) if pd.notna(row["overall"]) else None,
        "potential": int(row["potential"]) if pd.notna(row["potential"]) else None,
        "club": row["club"],
        "position": row["position"],
        "jersey_number": int(row["jersey_number"]) if pd.notna(row["jersey_number"]) else None,
        "height": row["height"],
        "weight": row["weight"],
    }


def top_players_by_nationality(
    store: DataStore, nationality: str, *, limit: int = 10
) -> dict[str, Any]:
    return search_players(store, nationality=nationality, limit=limit)


def top_players_by_club(store: DataStore, club: str, *, limit: int = 10) -> dict[str, Any]:
    return search_players(store, club=club, limit=limit)


def brazilian_player_summary(store: DataStore) -> dict[str, Any]:
    """Aggregate stats on Brazilian players by club (Brazilian clubs only)."""
    df = store.players
    brazilians = df[df["nationality_lower"] == "brazil"]
    by_club = (
        brazilians[brazilians["club_norm"].isin(_brazilian_club_keys(store))]
        .groupby("club_norm")
        .agg(player_count=("name", "count"), avg_overall=("overall", "mean"))
        .sort_values("player_count", ascending=False)
    )
    clubs = [
        {
            "club": label_for(key),
            "player_count": int(row.player_count),
            "avg_overall": round(float(row.avg_overall), 2) if pd.notna(row.avg_overall) else None,
        }
        for key, row in by_club.iterrows()
    ]
    return {
        "total_brazilian_players": int(len(brazilians)),
        "brazilian_clubs": clubs,
    }


def _brazilian_club_keys(store: DataStore) -> set[str]:
    return set(store.matches["home_team_norm"]).union(store.matches["away_team_norm"])


# ---------------------------------------------------------------------------
# 4. Competition queries
# ---------------------------------------------------------------------------


def season_standings(
    store: DataStore,
    season: int,
    *,
    competition: str = "Brasileirão Serie A",
    limit: int = 20,
) -> dict[str, Any]:
    """Reconstruct league standings from match results.

    Points are 3-for-win / 1-for-draw, the same as the real Brasileirão.
    """
    df = _apply_filters(store.matches, competition=competition, season=int(season))
    # de-duplicate when both the historical and modern Brasileirão CSVs cover
    # the same season — they often do, with the same matches.
    df = df.drop_duplicates(subset=["date", "home_team_norm", "away_team_norm"])
    table: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        for key, gf, ga in (
            (row["home_team_norm"], row["home_goal"], row["away_goal"]),
            (row["away_team_norm"], row["away_goal"], row["home_goal"]),
        ):
            if not key:
                continue
            t = table.setdefault(
                key,
                {
                    "team": label_for(key),
                    "matches": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "points": 0,
                },
            )
            t["matches"] += 1
            t["goals_for"] += int(gf)
            t["goals_against"] += int(ga)
            if gf > ga:
                t["wins"] += 1
                t["points"] += 3
            elif gf < ga:
                t["losses"] += 1
            else:
                t["draws"] += 1
                t["points"] += 1
    standings = sorted(
        table.values(),
        key=lambda t: (t["points"], t["goals_for"] - t["goals_against"], t["goals_for"]),
        reverse=True,
    )
    for idx, t in enumerate(standings, start=1):
        t["position"] = idx
        t["goal_difference"] = t["goals_for"] - t["goals_against"]
    return {
        "competition": competition,
        "season": int(season),
        "standings": standings[:limit],
        "champion": standings[0]["team"] if standings else None,
    }


def list_competitions(store: DataStore) -> dict[str, Any]:
    counts = store.matches["competition"].value_counts().to_dict()
    return {"competitions": [{"name": k, "match_count": int(v)} for k, v in counts.items()]}


def list_seasons(store: DataStore, *, competition: str | None = None) -> dict[str, Any]:
    df = _apply_filters(store.matches, competition=competition)
    seasons = sorted({int(s) for s in df["season"].dropna().unique() if int(s) > 0})
    return {"competition": competition, "seasons": seasons}


# ---------------------------------------------------------------------------
# 5. Statistical analysis
# ---------------------------------------------------------------------------


def average_goals_per_match(
    store: DataStore,
    *,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    df = _apply_filters(store.matches, competition=competition, season=season)
    if df.empty:
        return {
            "competition": competition,
            "season": season,
            "matches": 0,
            "average_goals": 0.0,
        }
    total_goals = float(df["home_goal"].sum() + df["away_goal"].sum())
    matches = int(len(df))
    return {
        "competition": competition,
        "season": season,
        "matches": matches,
        "average_goals": round(total_goals / matches, 3),
        "average_home_goals": round(float(df["home_goal"].sum()) / matches, 3),
        "average_away_goals": round(float(df["away_goal"].sum()) / matches, 3),
    }


def biggest_wins(
    store: DataStore,
    *,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    df = _apply_filters(store.matches, competition=competition, season=season).copy()
    df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
    df = df.sort_values(["margin", "date"], ascending=[False, False])
    rows = []
    for _, row in df.head(limit).iterrows():
        m = _match_to_dict(row)
        m["margin"] = int(row["margin"])
        rows.append(m)
    return {"competition": competition, "season": season, "matches": rows}


def home_away_split(
    store: DataStore,
    *,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    df = _apply_filters(store.matches, competition=competition, season=season)
    matches = int(len(df))
    if matches == 0:
        return {
            "competition": competition,
            "season": season,
            "matches": 0,
            "home_win_rate": 0.0,
            "away_win_rate": 0.0,
            "draw_rate": 0.0,
        }
    home_wins = int((df["home_goal"] > df["away_goal"]).sum())
    away_wins = int((df["away_goal"] > df["home_goal"]).sum())
    draws = int((df["home_goal"] == df["away_goal"]).sum())
    return {
        "competition": competition,
        "season": season,
        "matches": matches,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / matches, 3),
        "away_win_rate": round(away_wins / matches, 3),
        "draw_rate": round(draws / matches, 3),
    }


def best_home_records(
    store: DataStore,
    *,
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 5,
    limit: int = 10,
) -> dict[str, Any]:
    """Rank teams by home win rate (with a minimum match count filter)."""
    df = _apply_filters(store.matches, competition=competition, season=season)
    rows: list[dict[str, Any]] = []
    for team_key, group in df.groupby("home_team_norm"):
        if not team_key or len(group) < min_matches:
            continue
        wins = int((group["home_goal"] > group["away_goal"]).sum())
        rows.append(
            {
                "team": label_for(team_key),
                "matches": int(len(group)),
                "wins": wins,
                "win_rate": round(wins / len(group), 3),
            }
        )
    rows.sort(key=lambda r: (r["win_rate"], r["wins"]), reverse=True)
    return {"competition": competition, "season": season, "teams": rows[:limit]}


def best_away_records(
    store: DataStore,
    *,
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 5,
    limit: int = 10,
) -> dict[str, Any]:
    df = _apply_filters(store.matches, competition=competition, season=season)
    rows: list[dict[str, Any]] = []
    for team_key, group in df.groupby("away_team_norm"):
        if not team_key or len(group) < min_matches:
            continue
        wins = int((group["away_goal"] > group["home_goal"]).sum())
        rows.append(
            {
                "team": label_for(team_key),
                "matches": int(len(group)),
                "wins": wins,
                "win_rate": round(wins / len(group), 3),
            }
        )
    rows.sort(key=lambda r: (r["win_rate"], r["wins"]), reverse=True)
    return {"competition": competition, "season": season, "teams": rows[:limit]}
