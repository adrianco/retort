"""High-level query API over the loaded Brazilian soccer data.

:class:`SoccerKnowledge` is the single entry point used by the MCP server
and the test suite. Every method either:

* returns a :class:`pandas.DataFrame` (for list-of-rows results), OR
* returns a plain ``dict`` (for aggregates / single-record results).

DataFrames are always returned with stable column orderings so the MCP
layer can format them deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from brazilian_soccer_mcp.loaders import SoccerData, load_data
from brazilian_soccer_mcp.normalize import (
    display_team,
    normalize_team,
    normalize_text,
)

_MATCH_DISPLAY_COLUMNS = [
    "date", "competition", "season", "round",
    "home_team_display", "away_team_display",
    "home_goal", "away_goal", "stage",
]


def _to_timestamp(value) -> Optional[pd.Timestamp]:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value
    if isinstance(value, (datetime, date)):
        return pd.Timestamp(value)
    return pd.to_datetime(value, errors="coerce")


@dataclass
class SoccerKnowledge:
    """Query interface over :class:`SoccerData`."""

    data: SoccerData

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_dir(cls, data_dir: str | Path = "data/kaggle") -> "SoccerKnowledge":
        return cls(data=load_data(data_dir))

    # ------------------------------------------------------------------
    # Match queries
    # ------------------------------------------------------------------
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        home_only: bool = False,
        away_only: bool = False,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """Return matches matching the given filters."""
        df = self.data.matches
        if team is not None:
            key = normalize_team(team)
            if home_only:
                df = df[df["home_team"] == key]
            elif away_only:
                df = df[df["away_team"] == key]
            else:
                df = df[(df["home_team"] == key) | (df["away_team"] == key)]
        if opponent is not None:
            okey = normalize_team(opponent)
            if team is not None:
                key = normalize_team(team)
                df = df[
                    ((df["home_team"] == key) & (df["away_team"] == okey))
                    | ((df["home_team"] == okey) & (df["away_team"] == key))
                ]
            else:
                df = df[(df["home_team"] == okey) | (df["away_team"] == okey)]
        if competition is not None:
            cnorm = normalize_text(competition)
            df = df[df["competition"].apply(lambda c: cnorm in normalize_text(c))]
        if season is not None:
            df = df[df["season"] == season]
        if date_from is not None:
            ts = _to_timestamp(date_from)
            df = df[df["date"] >= ts]
        if date_to is not None:
            ts = _to_timestamp(date_to)
            df = df[df["date"] <= ts]
        df = df.sort_values("date", na_position="last")
        if limit is not None:
            df = df.head(limit)
        return df.reset_index(drop=True)

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
    ) -> dict:
        """Aggregate head-to-head record between two teams."""
        a, b = normalize_team(team_a), normalize_team(team_b)
        matches = self.find_matches(team=team_a, opponent=team_b, competition=competition)
        if matches.empty:
            return {
                "team_a": team_a,
                "team_b": team_b,
                "matches": 0,
                "a_wins": 0,
                "b_wins": 0,
                "draws": 0,
                "a_goals": 0,
                "b_goals": 0,
                "records": [],
            }
        a_wins = b_wins = draws = a_goals = b_goals = 0
        records = []
        for _, row in matches.iterrows():
            hg = row["home_goal"]
            ag = row["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            hg, ag = int(hg), int(ag)
            if row["home_team"] == a:
                a_goals += hg
                b_goals += ag
                if hg > ag:
                    a_wins += 1
                elif hg < ag:
                    b_wins += 1
                else:
                    draws += 1
            else:
                a_goals += ag
                b_goals += hg
                if ag > hg:
                    a_wins += 1
                elif ag < hg:
                    b_wins += 1
                else:
                    draws += 1
            records.append(
                {
                    "date": (
                        row["date"].strftime("%Y-%m-%d")
                        if pd.notna(row["date"])
                        else None
                    ),
                    "competition": row["competition"],
                    "season": int(row["season"]) if pd.notna(row["season"]) else None,
                    "home": row["home_team_display"],
                    "away": row["away_team_display"],
                    "home_goal": hg,
                    "away_goal": ag,
                }
            )
        return {
            "team_a": team_a,
            "team_b": team_b,
            "matches": len(records),
            "a_wins": a_wins,
            "b_wins": b_wins,
            "draws": draws,
            "a_goals": a_goals,
            "b_goals": b_goals,
            "records": records,
        }

    # ------------------------------------------------------------------
    # Team queries
    # ------------------------------------------------------------------
    def team_stats(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        home_only: bool = False,
        away_only: bool = False,
    ) -> dict:
        """Return aggregate W/D/L and goals for a team."""
        key = normalize_team(team)
        df = self.find_matches(
            team=team,
            season=season,
            competition=competition,
            home_only=home_only,
            away_only=away_only,
        )
        if df.empty:
            return {
                "team": team,
                "team_key": key,
                "matches": 0,
                "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0,
                "goal_diff": 0,
                "win_rate": 0.0,
            }
        wins = draws = losses = gf = ga = 0
        for _, row in df.iterrows():
            hg = row["home_goal"]
            ag = row["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            hg, ag = int(hg), int(ag)
            is_home = row["home_team"] == key
            tg = hg if is_home else ag
            og = ag if is_home else hg
            gf += tg
            ga += og
            if tg > og:
                wins += 1
            elif tg < og:
                losses += 1
            else:
                draws += 1
        played = wins + draws + losses
        return {
            "team": team,
            "team_key": key,
            "matches": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_diff": gf - ga,
            "win_rate": round(wins / played, 3) if played else 0.0,
            "points": wins * 3 + draws,
        }

    def team_seasons(self, team: str) -> list:
        """All seasons in which a team has at least one match."""
        key = normalize_team(team)
        df = self.data.matches
        seasons = df.loc[
            (df["home_team"] == key) | (df["away_team"] == key), "season"
        ].dropna().unique()
        return sorted(int(s) for s in seasons)

    def team_competitions(self, team: str) -> list:
        """All competitions a team has appeared in."""
        key = normalize_team(team)
        df = self.data.matches
        comps = df.loc[
            (df["home_team"] == key) | (df["away_team"] == key), "competition"
        ].dropna().unique()
        return sorted(str(c) for c in comps)

    # ------------------------------------------------------------------
    # Player queries
    # ------------------------------------------------------------------
    def find_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        limit: Optional[int] = 50,
    ) -> pd.DataFrame:
        df = self.data.players
        if name is not None:
            n = normalize_text(name)
            df = df[df["name_norm"].apply(lambda s: n in s)]
        if nationality is not None:
            nn = normalize_text(nationality)
            df = df[df["nationality"].fillna("").apply(
                lambda s: nn in normalize_text(s)
            )]
        if club is not None:
            ck = normalize_team(club)
            df = df[df["club_norm"].apply(lambda s: ck == s or (ck and ck in s))]
        if position is not None:
            pos = position.upper()
            df = df[df["position"].fillna("").str.upper() == pos]
        if min_overall is not None:
            df = df[df["overall"] >= min_overall]
        if max_overall is not None:
            df = df[df["overall"] <= max_overall]
        df = df.sort_values("overall", ascending=False, na_position="last")
        if limit is not None:
            df = df.head(limit)
        return df.reset_index(drop=True)

    def top_brazilian_players(self, limit: int = 10) -> pd.DataFrame:
        return self.find_players(nationality="Brazil", limit=limit)

    # ------------------------------------------------------------------
    # Competition queries
    # ------------------------------------------------------------------
    def season_standings(
        self,
        season: int,
        competition: str = "Brasileirão Série A",
    ) -> pd.DataFrame:
        """Compute a league table from match results for the given season.

        Returns a DataFrame sorted by points (desc), goal difference (desc),
        goals for (desc).
        """
        df = self.find_matches(season=season, competition=competition)
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "rank", "team", "played", "wins", "draws", "losses",
                    "goals_for", "goals_against", "goal_diff", "points",
                ]
            )
        rows: dict[str, dict] = {}

        def _bucket(key, display):
            if key not in rows:
                rows[key] = {
                    "team": display,
                    "played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0,
                }
            return rows[key]

        for _, row in df.iterrows():
            hg = row["home_goal"]
            ag = row["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            hg, ag = int(hg), int(ag)
            home = _bucket(row["home_team"], row["home_team_display"])
            away = _bucket(row["away_team"], row["away_team_display"])
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += hg
            home["goals_against"] += ag
            away["goals_for"] += ag
            away["goals_against"] += hg
            if hg > ag:
                home["wins"] += 1
                away["losses"] += 1
            elif hg < ag:
                away["wins"] += 1
                home["losses"] += 1
            else:
                home["draws"] += 1
                away["draws"] += 1
        table = pd.DataFrame(rows.values())
        table["goal_diff"] = table["goals_for"] - table["goals_against"]
        table["points"] = table["wins"] * 3 + table["draws"]
        table = table.sort_values(
            ["points", "goal_diff", "goals_for"], ascending=[False, False, False]
        ).reset_index(drop=True)
        table.insert(0, "rank", range(1, len(table) + 1))
        return table

    def champion(self, season: int, competition: str = "Brasileirão Série A") -> Optional[dict]:
        """Return the rank-1 team for a season, or ``None`` if no data."""
        table = self.season_standings(season=season, competition=competition)
        if table.empty:
            return None
        winner = table.iloc[0].to_dict()
        winner["season"] = season
        winner["competition"] = competition
        return winner

    # ------------------------------------------------------------------
    # Statistical analysis
    # ------------------------------------------------------------------
    def average_goals(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        df = self.find_matches(competition=competition, season=season)
        scored = df.dropna(subset=["home_goal", "away_goal"])
        n = len(scored)
        if n == 0:
            return {
                "matches": 0, "avg_goals_per_match": 0.0,
                "avg_home_goals": 0.0, "avg_away_goals": 0.0,
                "home_win_rate": 0.0, "away_win_rate": 0.0, "draw_rate": 0.0,
            }
        home_g = scored["home_goal"].astype(int)
        away_g = scored["away_goal"].astype(int)
        home_wins = int((home_g > away_g).sum())
        away_wins = int((home_g < away_g).sum())
        draws = int((home_g == away_g).sum())
        return {
            "matches": n,
            "avg_goals_per_match": round(float((home_g + away_g).mean()), 3),
            "avg_home_goals": round(float(home_g.mean()), 3),
            "avg_away_goals": round(float(away_g.mean()), 3),
            "home_win_rate": round(home_wins / n, 3),
            "away_win_rate": round(away_wins / n, 3),
            "draw_rate": round(draws / n, 3),
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> pd.DataFrame:
        df = self.find_matches(competition=competition, season=season)
        df = df.dropna(subset=["home_goal", "away_goal"]).copy()
        df["margin"] = (df["home_goal"].astype(int) - df["away_goal"].astype(int)).abs()
        df = df.sort_values(
            ["margin", "home_goal", "away_goal"], ascending=[False, False, False]
        )
        return df.head(limit).reset_index(drop=True)

    def best_home_record(
        self,
        season: Optional[int] = None,
        competition: Optional[str] = "Brasileirão Série A",
        min_matches: int = 5,
        limit: int = 5,
    ) -> pd.DataFrame:
        df = self.find_matches(competition=competition, season=season)
        df = df.dropna(subset=["home_goal", "away_goal"])
        agg = []
        for team_key, sub in df.groupby("home_team"):
            n = len(sub)
            if n < min_matches:
                continue
            wins = int((sub["home_goal"] > sub["away_goal"]).sum())
            draws = int((sub["home_goal"] == sub["away_goal"]).sum())
            losses = int((sub["home_goal"] < sub["away_goal"]).sum())
            display = sub.iloc[0]["home_team_display"]
            agg.append(
                {
                    "team": display,
                    "team_key": team_key,
                    "home_matches": n,
                    "wins": wins,
                    "draws": draws,
                    "losses": losses,
                    "win_rate": round(wins / n, 3),
                    "points": wins * 3 + draws,
                }
            )
        out = pd.DataFrame(agg)
        if out.empty:
            return out
        out = out.sort_values(
            ["win_rate", "wins"], ascending=[False, False]
        ).head(limit)
        return out.reset_index(drop=True)

    def best_away_record(
        self,
        season: Optional[int] = None,
        competition: Optional[str] = "Brasileirão Série A",
        min_matches: int = 5,
        limit: int = 5,
    ) -> pd.DataFrame:
        df = self.find_matches(competition=competition, season=season)
        df = df.dropna(subset=["home_goal", "away_goal"])
        agg = []
        for team_key, sub in df.groupby("away_team"):
            n = len(sub)
            if n < min_matches:
                continue
            wins = int((sub["away_goal"] > sub["home_goal"]).sum())
            draws = int((sub["away_goal"] == sub["home_goal"]).sum())
            losses = int((sub["away_goal"] < sub["home_goal"]).sum())
            display = sub.iloc[0]["away_team_display"]
            agg.append(
                {
                    "team": display,
                    "team_key": team_key,
                    "away_matches": n,
                    "wins": wins,
                    "draws": draws,
                    "losses": losses,
                    "win_rate": round(wins / n, 3),
                    "points": wins * 3 + draws,
                }
            )
        out = pd.DataFrame(agg)
        if out.empty:
            return out
        out = out.sort_values(
            ["win_rate", "wins"], ascending=[False, False]
        ).head(limit)
        return out.reset_index(drop=True)

    def top_scorers_by_team(
        self,
        season: int,
        competition: str = "Brasileirão Série A",
        limit: int = 5,
    ) -> pd.DataFrame:
        """Teams ranked by total goals scored in a season."""
        df = self.find_matches(season=season, competition=competition)
        df = df.dropna(subset=["home_goal", "away_goal"])
        rows: dict[str, dict] = {}
        for _, row in df.iterrows():
            for team_key, display, gf in (
                (row["home_team"], row["home_team_display"], int(row["home_goal"])),
                (row["away_team"], row["away_team_display"], int(row["away_goal"])),
            ):
                if team_key not in rows:
                    rows[team_key] = {"team": display, "goals": 0, "matches": 0}
                rows[team_key]["goals"] += gf
                rows[team_key]["matches"] += 1
        out = pd.DataFrame(rows.values())
        if out.empty:
            return out
        out = out.sort_values("goals", ascending=False).head(limit)
        return out.reset_index(drop=True)


def display_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Return only the user-facing columns for a match listing."""
    cols = [c for c in _MATCH_DISPLAY_COLUMNS if c in df.columns]
    return df[cols].copy()
