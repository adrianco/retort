"""High-level query API over the loaded :class:`DataStore`.

Each method returns plain Python dicts/lists so callers (CLI, MCP tools,
tests) can format them however they like. The methods are intentionally
forgiving about team name variants by funnelling all comparisons through
``team_names.normalize``.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

import pandas as pd

from .data_loader import DataStore
from .team_names import normalize


def _match_to_dict(row: pd.Series) -> dict:
    date = row.get("date")
    return {
        "date": date.strftime("%Y-%m-%d") if isinstance(date, pd.Timestamp) and not pd.isna(date) else None,
        "competition": row.get("competition") or "",
        "season": int(row["season"]) if pd.notna(row.get("season")) else None,
        "round": row.get("round"),
        "stage": row.get("stage") or "",
        "home_team": row.get("home_team"),
        "away_team": row.get("away_team"),
        "home_goal": int(row["home_goal"]) if pd.notna(row.get("home_goal")) else None,
        "away_goal": int(row["away_goal"]) if pd.notna(row.get("away_goal")) else None,
        "venue": row.get("venue") or "",
    }


class SoccerQueries:
    """Query facade over a :class:`DataStore`."""

    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.matches = store.matches
        self.players = store.players

    # ------------------------------------------------------------------
    # Match queries
    # ------------------------------------------------------------------
    def find_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        home_only: bool = False,
        away_only: bool = False,
        limit: int | None = 50,
    ) -> list[dict]:
        df = self.matches
        if team:
            tn = normalize(team)
            if home_only:
                mask = df["home_team_norm"].str.contains(tn, na=False)
            elif away_only:
                mask = df["away_team_norm"].str.contains(tn, na=False)
            else:
                mask = df["home_team_norm"].str.contains(tn, na=False) | df["away_team_norm"].str.contains(tn, na=False)
            df = df[mask]
        if opponent:
            on = normalize(opponent)
            mask = df["home_team_norm"].str.contains(on, na=False) | df["away_team_norm"].str.contains(on, na=False)
            df = df[mask]
        if competition:
            cn = normalize(competition)
            df = df[df["competition"].map(normalize).str.contains(cn, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]
        if date_from:
            df = df[df["date"] >= pd.to_datetime(date_from)]
        if date_to:
            df = df[df["date"] <= pd.to_datetime(date_to)]
        df = df.sort_values("date", ascending=False, na_position="last")
        if limit is not None:
            df = df.head(limit)
        return [_match_to_dict(r) for _, r in df.iterrows()]

    def head_to_head(self, team_a: str, team_b: str, season: int | None = None) -> dict:
        a = normalize(team_a)
        b = normalize(team_b)
        df = self.matches
        if season is not None:
            df = df[df["season"] == int(season)]
        ah_bh = df["home_team_norm"].str.contains(a, na=False) & df["away_team_norm"].str.contains(b, na=False)
        bh_ah = df["home_team_norm"].str.contains(b, na=False) & df["away_team_norm"].str.contains(a, na=False)
        df = df[ah_bh | bh_ah]
        a_wins = b_wins = draws = 0
        a_goals = b_goals = 0
        for _, row in df.iterrows():
            hg, ag = row["home_goal"], row["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            hg, ag = int(hg), int(ag)
            home_is_a = a in (row["home_team_norm"] or "")
            if hg == ag:
                draws += 1
            elif hg > ag:
                if home_is_a:
                    a_wins += 1
                else:
                    b_wins += 1
            else:
                if home_is_a:
                    b_wins += 1
                else:
                    a_wins += 1
            if home_is_a:
                a_goals += hg
                b_goals += ag
            else:
                b_goals += hg
                a_goals += ag
        return {
            "team_a": team_a,
            "team_b": team_b,
            "total_matches": int(len(df)),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
            "matches": [_match_to_dict(r) for _, r in df.sort_values("date", ascending=False).head(50).iterrows()],
        }

    # ------------------------------------------------------------------
    # Team queries
    # ------------------------------------------------------------------
    def team_stats(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str | None = None,  # "home", "away", or None
    ) -> dict:
        tn = normalize(team)
        df = self.matches
        if competition:
            cn = normalize(competition)
            df = df[df["competition"].map(normalize).str.contains(cn, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]

        wins = draws = losses = 0
        goals_for = goals_against = 0
        matches_played = 0
        home_mask = df["home_team_norm"].str.contains(tn, na=False)
        away_mask = df["away_team_norm"].str.contains(tn, na=False)
        if venue == "home":
            chosen = df[home_mask]
        elif venue == "away":
            chosen = df[away_mask]
        else:
            chosen = df[home_mask | away_mask]
        for _, row in chosen.iterrows():
            hg, ag = row["home_goal"], row["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            hg, ag = int(hg), int(ag)
            is_home = tn in (row["home_team_norm"] or "")
            matches_played += 1
            if is_home:
                goals_for += hg
                goals_against += ag
                if hg > ag:
                    wins += 1
                elif hg < ag:
                    losses += 1
                else:
                    draws += 1
            else:
                goals_for += ag
                goals_against += hg
                if ag > hg:
                    wins += 1
                elif ag < hg:
                    losses += 1
                else:
                    draws += 1
        win_rate = wins / matches_played if matches_played else 0.0
        return {
            "team": team,
            "season": season,
            "competition": competition,
            "venue": venue or "all",
            "matches_played": matches_played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_difference": goals_for - goals_against,
            "points": wins * 3 + draws,
            "win_rate": round(win_rate, 4),
        }

    def list_teams(self, competition: str | None = None, season: int | None = None) -> list[str]:
        df = self.matches
        if competition:
            cn = normalize(competition)
            df = df[df["competition"].map(normalize).str.contains(cn, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]
        names = set(df["home_team"].dropna()) | set(df["away_team"].dropna())
        return sorted(names)

    # ------------------------------------------------------------------
    # Competition queries
    # ------------------------------------------------------------------
    def standings(self, competition: str, season: int) -> list[dict]:
        cn = normalize(competition)
        df = self.matches
        df = df[df["competition"].map(normalize).str.contains(cn, na=False)]
        df = df[df["season"] == int(season)]
        df = df.dropna(subset=["home_goal", "away_goal"])

        table: dict[str, dict] = {}

        def slot(team_norm: str, display: str) -> dict:
            row = table.get(team_norm)
            if row is None:
                row = {
                    "team": display,
                    "played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0, "points": 0,
                }
                table[team_norm] = row
            return row

        for _, row in df.iterrows():
            home_norm = row["home_team_norm"] or ""
            away_norm = row["away_team_norm"] or ""
            if not home_norm or not away_norm:
                continue
            home = slot(home_norm, row["home_team"])
            away = slot(away_norm, row["away_team"])
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += hg
            home["goals_against"] += ag
            away["goals_for"] += ag
            away["goals_against"] += hg
            if hg > ag:
                home["wins"] += 1
                home["points"] += 3
                away["losses"] += 1
            elif hg < ag:
                away["wins"] += 1
                away["points"] += 3
                home["losses"] += 1
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        ranked = sorted(
            table.values(),
            key=lambda t: (t["points"], t["goals_for"] - t["goals_against"], t["goals_for"]),
            reverse=True,
        )
        for i, team in enumerate(ranked, start=1):
            team["position"] = i
            team["goal_difference"] = team["goals_for"] - team["goals_against"]
        return ranked

    def list_seasons(self, competition: str | None = None) -> list[int]:
        df = self.matches
        if competition:
            cn = normalize(competition)
            df = df[df["competition"].map(normalize).str.contains(cn, na=False)]
        seasons = sorted({int(s) for s in df["season"].dropna().unique()})
        return seasons

    def list_competitions(self) -> list[str]:
        return sorted({str(c) for c in self.matches["competition"].dropna().unique()})

    # ------------------------------------------------------------------
    # Player queries
    # ------------------------------------------------------------------
    def find_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 25,
    ) -> list[dict]:
        df = self.players
        if name:
            n = normalize(name)
            df = df[df["Name"].astype(str).map(normalize).str.contains(n, na=False)]
        if nationality:
            n = normalize(nationality)
            df = df[df["Nationality"].astype(str).map(normalize) == n]
        if club:
            cn = normalize(club)
            df = df[df["Club"].astype(str).map(normalize).str.contains(cn, na=False)]
        if position:
            p = position.strip().upper()
            df = df[df["Position"].astype(str).str.upper() == p]
        if min_overall is not None:
            df = df[df["Overall"].fillna(0).astype(float) >= float(min_overall)]
        df = df.sort_values("Overall", ascending=False, na_position="last").head(limit)
        cols = [
            "ID", "Name", "Age", "Nationality", "Overall", "Potential",
            "Club", "Position", "Jersey Number", "Height", "Weight",
        ]
        existing = [c for c in cols if c in df.columns]
        records = df[existing].to_dict(orient="records")
        # Clean NaN
        for r in records:
            for k, v in list(r.items()):
                if isinstance(v, float) and pd.isna(v):
                    r[k] = None
        return records

    def top_brazilian_players(self, limit: int = 10) -> list[dict]:
        return self.find_players(nationality="Brazil", limit=limit)

    # ------------------------------------------------------------------
    # Statistical analysis
    # ------------------------------------------------------------------
    def biggest_wins(self, competition: str | None = None, season: int | None = None, limit: int = 10) -> list[dict]:
        df = self.matches.dropna(subset=["home_goal", "away_goal"]).copy()
        if competition:
            cn = normalize(competition)
            df = df[df["competition"].map(normalize).str.contains(cn, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]
        df["margin"] = (df["home_goal"].astype(int) - df["away_goal"].astype(int)).abs()
        df["total_goals"] = df["home_goal"].astype(int) + df["away_goal"].astype(int)
        df = df.sort_values(["margin", "total_goals"], ascending=False).head(limit)
        return [_match_to_dict(r) | {"margin": int(r["margin"])} for _, r in df.iterrows()]

    def average_goals_per_match(self, competition: str | None = None, season: int | None = None) -> dict:
        df = self.matches.dropna(subset=["home_goal", "away_goal"])
        if competition:
            cn = normalize(competition)
            df = df[df["competition"].map(normalize).str.contains(cn, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]
        total = len(df)
        if total == 0:
            return {"matches": 0, "avg_goals": 0.0, "home_win_rate": 0.0, "away_win_rate": 0.0, "draw_rate": 0.0}
        home_wins = int(((df["home_goal"] > df["away_goal"])).sum())
        away_wins = int(((df["home_goal"] < df["away_goal"])).sum())
        draws = int(((df["home_goal"] == df["away_goal"])).sum())
        avg_goals = float((df["home_goal"] + df["away_goal"]).mean())
        return {
            "matches": total,
            "avg_goals": round(avg_goals, 3),
            "home_win_rate": round(home_wins / total, 4),
            "away_win_rate": round(away_wins / total, 4),
            "draw_rate": round(draws / total, 4),
        }

    def summary(self) -> dict:
        return {
            "total_matches": int(len(self.matches)),
            "total_players": int(len(self.players)),
            "competitions": self.list_competitions(),
            "sources": dict(self.store.sources),
        }
