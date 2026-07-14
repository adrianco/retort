"""Query functions for the Brazilian Soccer MCP server.

These are pure functions over a :class:`DataStore` so the MCP server layer is
just a thin adapter. Every function returns plain Python (lists, dicts) that
serialize cleanly to JSON for tool responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

import pandas as pd

from .data_loader import DataStore
from .normalize import normalize_team_name, strip_state_suffix

COMPETITION_ALIASES: dict[str, set[str]] = {
    "brasileirao": {"Brasileirão", "Brasileirão (historical)", "Serie A"},
    "serie a": {"Brasileirão", "Brasileirão (historical)", "Serie A"},
    "campeonato brasileiro": {"Brasileirão", "Brasileirão (historical)", "Serie A"},
    "copa do brasil": {"Copa do Brasil"},
    "brazilian cup": {"Copa do Brasil"},
    "libertadores": {"Copa Libertadores"},
    "copa libertadores": {"Copa Libertadores"},
    "serie b": {"Serie B"},
    "serie c": {"Serie C"},
}


def _resolve_competitions(competition: str | None) -> set[str] | None:
    if not competition:
        return None
    key = competition.strip().lower()
    # Strip accents so "Brasileirão" matches "brasileirao".
    import unicodedata
    key = "".join(
        ch for ch in unicodedata.normalize("NFKD", key) if not unicodedata.combining(ch)
    )
    if key in COMPETITION_ALIASES:
        return COMPETITION_ALIASES[key]
    # Allow direct case-insensitive equality on the original spelling.
    return {competition}


def _team_mask(df: pd.DataFrame, query: str, side: str | None = None) -> pd.Series:
    """Build a boolean mask matching the given team query.

    ``side`` is ``"home"``, ``"away"``, or ``None`` (either side).
    Query without a state suffix matches the state-stripped column; with a
    suffix it must match the full normalized column exactly.
    """
    qn = normalize_team_name(query)
    qn_short = strip_state_suffix(qn)
    state_qualified = qn != qn_short

    if state_qualified:
        if side == "home":
            return df["home_team_norm"] == qn
        if side == "away":
            return df["away_team_norm"] == qn
        return (df["home_team_norm"] == qn) | (df["away_team_norm"] == qn)
    if side == "home":
        return df["home_team_short"] == qn
    if side == "away":
        return df["away_team_short"] == qn
    return (df["home_team_short"] == qn) | (df["away_team_short"] == qn)


def _parse_date(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts


def _row_to_match(row: pd.Series) -> dict[str, Any]:
    date = row.get("date")
    date_str: str | None
    if pd.isna(date):
        date_str = None
    else:
        date_str = pd.Timestamp(date).strftime("%Y-%m-%d")

    out = {
        "date": date_str,
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "home_goals": int(row["home_goals"]),
        "away_goals": int(row["away_goals"]),
        "season": int(row["season"]) if row["season"] else None,
        "competition": row["competition"],
        "round": row.get("round") or None,
        "stage": row.get("stage") or None,
        "arena": row.get("arena") or None,
        "source": row.get("source"),
    }
    return out


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------

def find_matches(
    store: DataStore,
    *,
    team: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int | None = 100,
) -> list[dict[str, Any]]:
    """Find matches matching the given criteria."""
    df = store.matches
    mask = pd.Series(True, index=df.index)

    if team:
        mask &= _team_mask(df, team)
    if home_team:
        mask &= _team_mask(df, home_team, side="home")
    if away_team:
        mask &= _team_mask(df, away_team, side="away")
    if opponent:
        mask &= _team_mask(df, opponent)

    comps = _resolve_competitions(competition)
    if comps is not None:
        mask &= df["competition"].isin(comps)

    if season is not None:
        mask &= df["season"] == int(season)

    df_from = _parse_date(date_from)
    if df_from is not None:
        mask &= df["date"] >= df_from
    df_to = _parse_date(date_to)
    if df_to is not None:
        mask &= df["date"] <= df_to

    result = df[mask].sort_values("date", ascending=False, na_position="last")
    if limit is not None:
        result = result.head(limit)
    return [_row_to_match(row) for _, row in result.iterrows()]


def head_to_head(
    store: DataStore,
    team_a: str,
    team_b: str,
    *,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Return head-to-head summary plus per-match list."""
    df = store.matches
    mask_a_home = _team_mask(df, team_a, side="home")
    mask_a_away = _team_mask(df, team_a, side="away")
    mask_b_home = _team_mask(df, team_b, side="home")
    mask_b_away = _team_mask(df, team_b, side="away")
    mask = (mask_a_home & mask_b_away) | (mask_b_home & mask_a_away)
    comps = _resolve_competitions(competition)
    if comps is not None:
        mask &= df["competition"].isin(comps)
    if season is not None:
        mask &= df["season"] == int(season)

    subset = df[mask].sort_values("date", ascending=False, na_position="last")
    a_home_in_subset = mask_a_home.loc[subset.index]
    wins_a = wins_b = draws = goals_a = goals_b = 0
    for idx, row in subset.iterrows():
        if a_home_in_subset.loc[idx]:
            ga, gb = row["home_goals"], row["away_goals"]
        else:
            ga, gb = row["away_goals"], row["home_goals"]
        goals_a += int(ga)
        goals_b += int(gb)
        if ga > gb:
            wins_a += 1
        elif gb > ga:
            wins_b += 1
        else:
            draws += 1

    return {
        "team_a": team_a,
        "team_b": team_b,
        "matches": len(subset),
        "team_a_wins": wins_a,
        "team_b_wins": wins_b,
        "draws": draws,
        "team_a_goals": goals_a,
        "team_b_goals": goals_b,
        "match_list": [_row_to_match(row) for _, row in subset.iterrows()],
    }


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------

def team_stats(
    store: DataStore,
    team: str,
    *,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",  # all | home | away
) -> dict[str, Any]:
    """Aggregate team performance: matches, W/D/L, goals for/against."""
    if venue not in {"all", "home", "away"}:
        raise ValueError("venue must be 'all', 'home', or 'away'")

    df = store.matches
    if venue == "home":
        mask = _team_mask(df, team, side="home")
    elif venue == "away":
        mask = _team_mask(df, team, side="away")
    else:
        mask = _team_mask(df, team)

    if season is not None:
        mask &= df["season"] == int(season)
    comps = _resolve_competitions(competition)
    if comps is not None:
        mask &= df["competition"].isin(comps)

    subset = df[mask]
    is_home_for_team = _team_mask(df, team, side="home").loc[subset.index]
    wins = draws = losses = goals_for = goals_against = 0
    for idx, row in subset.iterrows():
        if is_home_for_team.loc[idx]:
            gf, ga = int(row["home_goals"]), int(row["away_goals"])
        else:
            gf, ga = int(row["away_goals"]), int(row["home_goals"])
        goals_for += gf
        goals_against += ga
        if gf > ga:
            wins += 1
        elif gf < ga:
            losses += 1
        else:
            draws += 1

    matches = len(subset)
    points = wins * 3 + draws
    win_rate = round(wins / matches, 4) if matches else 0.0
    return {
        "team": team,
        "season": season,
        "competition": competition,
        "venue": venue,
        "matches": matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goals_for - goals_against,
        "points": points,
        "win_rate": win_rate,
    }


def team_competitions(store: DataStore, team: str) -> list[dict[str, Any]]:
    """List the competitions a team has appeared in, with counts and seasons."""
    df = store.matches
    subset = df[_team_mask(df, team)]
    out = []
    for comp, group in subset.groupby("competition"):
        seasons = sorted({int(s) for s in group["season"] if s})
        out.append({
            "competition": comp,
            "matches": int(len(group)),
            "seasons": seasons,
        })
    out.sort(key=lambda d: d["competition"])
    return out


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------

def find_players(
    store: DataStore,
    *,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search players in the FIFA dataset."""
    df = store.players
    mask = pd.Series(True, index=df.index)
    if name:
        mask &= df["name_lower"].str.contains(name.lower(), na=False, regex=False)
    if nationality:
        mask &= df["nationality_lower"] == nationality.lower()
    if club:
        qn = normalize_team_name(club)
        qn_short = strip_state_suffix(qn)
        if qn != qn_short:
            mask &= df["club_norm"] == qn
        else:
            mask &= df["club_short"] == qn
    if position:
        mask &= df["position"].str.upper() == position.upper()
    if min_overall is not None:
        mask &= df["overall"] >= int(min_overall)

    subset = df[mask].sort_values("overall", ascending=False).head(limit)
    return [
        {
            "id": int(row["id"]),
            "name": row["name"],
            "age": int(row["age"]) if row["age"] else None,
            "nationality": row["nationality"],
            "club": row["club"] or None,
            "position": row["position"] or None,
            "overall": int(row["overall"]),
            "potential": int(row["potential"]),
            "jersey_number": row["jersey_number"] if pd.notna(row["jersey_number"]) else None,
            "preferred_foot": row["preferred_foot"] if pd.notna(row["preferred_foot"]) else None,
        }
        for _, row in subset.iterrows()
    ]


def top_brazilian_players(store: DataStore, limit: int = 20) -> list[dict[str, Any]]:
    return find_players(store, nationality="Brazil", limit=limit)


def players_at_brazilian_clubs(store: DataStore) -> list[dict[str, Any]]:
    """Group players whose club matches a Brazilian club from the match data.

    Only teams that appeared in Brasileirão or Copa do Brasil count — that
    excludes foreign Libertadores entrants whose short names would otherwise
    collide (e.g. FC Barcelona vs Barcelona-EQU).
    """
    df = store.players
    matches = store.matches
    bras_mask = matches["competition"].isin({"Brasileirão", "Copa do Brasil"})
    bras_matches = matches[bras_mask]
    short_clubs = set(bras_matches["home_team_short"]).union(bras_matches["away_team_short"])
    short_clubs.discard("")
    subset = df[df["club_short"].isin(short_clubs) & (df["club_short"] != "")]
    out = []
    for club, group in subset.groupby("club"):
        out.append({
            "club": club,
            "players": int(len(group)),
            "avg_overall": round(float(group["overall"].mean()), 2),
            "top_player": group.sort_values("overall", ascending=False).iloc[0]["name"],
        })
    out.sort(key=lambda d: d["players"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------

def standings(
    store: DataStore,
    season: int,
    competition: str = "Brasileirão",
) -> list[dict[str, Any]]:
    """Compute a points table for a given season/competition."""
    df = store.matches
    comps = _resolve_competitions(competition) or {competition}
    subset = df[(df["season"] == int(season)) & (df["competition"].isin(comps))]
    if subset.empty:
        return []

    teams: dict[str, dict[str, Any]] = {}

    def slot(norm: str, display: str) -> dict[str, Any]:
        if norm not in teams:
            teams[norm] = {
                "team": display,
                "matches": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0,
            }
        return teams[norm]

    for _, row in subset.iterrows():
        h = slot(row["home_team_norm"], row["home_team"])
        a = slot(row["away_team_norm"], row["away_team"])
        hg, ag = int(row["home_goals"]), int(row["away_goals"])
        h["matches"] += 1; a["matches"] += 1
        h["goals_for"] += hg; h["goals_against"] += ag
        a["goals_for"] += ag; a["goals_against"] += hg
        if hg > ag:
            h["wins"] += 1; a["losses"] += 1
        elif ag > hg:
            a["wins"] += 1; h["losses"] += 1
        else:
            h["draws"] += 1; a["draws"] += 1

    table = []
    for t in teams.values():
        t["points"] = t["wins"] * 3 + t["draws"]
        t["goal_difference"] = t["goals_for"] - t["goals_against"]
        table.append(t)
    table.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]))
    for idx, row in enumerate(table, start=1):
        row["position"] = idx
    return table


def season_summary(
    store: DataStore,
    season: int,
    competition: str = "Brasileirão",
) -> dict[str, Any]:
    table = standings(store, season=season, competition=competition)
    if not table:
        return {"season": season, "competition": competition, "matches": 0}
    df = store.matches
    comps = _resolve_competitions(competition) or {competition}
    subset = df[(df["season"] == int(season)) & (df["competition"].isin(comps))]
    return {
        "season": season,
        "competition": competition,
        "matches": int(len(subset)),
        "champion": table[0]["team"] if table else None,
        "runner_up": table[1]["team"] if len(table) > 1 else None,
        "wooden_spoon": table[-1]["team"] if table else None,
        "standings": table,
    }


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------

def biggest_wins(
    store: DataStore,
    *,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    df = store.matches
    mask = pd.Series(True, index=df.index)
    comps = _resolve_competitions(competition)
    if comps is not None:
        mask &= df["competition"].isin(comps)
    if season is not None:
        mask &= df["season"] == int(season)
    subset = df[mask].copy()
    subset["margin"] = (subset["home_goals"] - subset["away_goals"]).abs()
    subset = subset.sort_values(
        ["margin", "home_goals", "away_goals"], ascending=[False, False, False]
    ).head(limit)
    return [_row_to_match(row) for _, row in subset.iterrows()]


def aggregate_stats(
    store: DataStore,
    *,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    df = store.matches
    mask = pd.Series(True, index=df.index)
    comps = _resolve_competitions(competition)
    if comps is not None:
        mask &= df["competition"].isin(comps)
    if season is not None:
        mask &= df["season"] == int(season)
    subset = df[mask]
    n = len(subset)
    if n == 0:
        return {"matches": 0}
    total_goals = int(subset["home_goals"].sum() + subset["away_goals"].sum())
    home_wins = int((subset["home_goals"] > subset["away_goals"]).sum())
    away_wins = int((subset["home_goals"] < subset["away_goals"]).sum())
    draws = int((subset["home_goals"] == subset["away_goals"]).sum())
    return {
        "matches": n,
        "total_goals": total_goals,
        "avg_goals_per_match": round(total_goals / n, 3),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / n, 4),
        "away_win_rate": round(away_wins / n, 4),
        "draw_rate": round(draws / n, 4),
    }


def top_scoring_teams(
    store: DataStore,
    season: int,
    competition: str = "Brasileirão",
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    table = standings(store, season=season, competition=competition)
    table.sort(key=lambda r: r["goals_for"], reverse=True)
    return table[:limit]


def best_records(
    store: DataStore,
    season: int,
    competition: str = "Brasileirão",
    *,
    venue: str = "home",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Rank teams by win rate at the given venue for the given season."""
    df = store.matches
    comps = _resolve_competitions(competition) or {competition}
    subset = df[(df["season"] == int(season)) & (df["competition"].isin(comps))]
    if subset.empty:
        return []
    norm_teams = set(subset["home_team_norm"]).union(set(subset["away_team_norm"]))
    results = []
    for norm in norm_teams:
        if not norm:
            continue
        if venue == "home":
            games = subset[subset["home_team_norm"] == norm]
            wins = int((games["home_goals"] > games["away_goals"]).sum())
            draws = int((games["home_goals"] == games["away_goals"]).sum())
            display = games["home_team"].iloc[0] if not games.empty else norm
        elif venue == "away":
            games = subset[subset["away_team_norm"] == norm]
            wins = int((games["away_goals"] > games["home_goals"]).sum())
            draws = int((games["home_goals"] == games["away_goals"]).sum())
            display = games["away_team"].iloc[0] if not games.empty else norm
        else:
            raise ValueError("venue must be 'home' or 'away'")
        n = len(games)
        if n == 0:
            continue
        losses = n - wins - draws
        results.append({
            "team": display,
            "matches": n,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "win_rate": round(wins / n, 4),
            "points": wins * 3 + draws,
        })
    results.sort(key=lambda r: (-r["win_rate"], -r["points"], -r["wins"]))
    return results[:limit]
