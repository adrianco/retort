"""Query engine for Brazilian soccer data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

import re

from .data_loader import Datasets, normalize_team, team_key


def _team_mask(df: pd.DataFrame, team: str, *, side: str = "either") -> pd.Series:
    """Return a boolean mask selecting rows where the team plays on the given side."""
    t = normalize_team(team)
    has_suffix = bool(re.search(r"-[a-z]{2,3}$", t))
    tk = team_key(team)
    if side == "home":
        return (df["home_team"] == t) if has_suffix else (df["home_key"] == tk)
    if side == "away":
        return (df["away_team"] == t) if has_suffix else (df["away_key"] == tk)
    if has_suffix:
        return (df["home_team"] == t) | (df["away_team"] == t)
    return (df["home_key"] == tk) | (df["away_key"] == tk)


@dataclass
class QueryEngine:
    data: Datasets

    # ---------- matches ----------
    def find_matches(self, team: Optional[str] = None, opponent: Optional[str] = None,
                     competition: Optional[str] = None, season: Optional[int] = None,
                     date_from: Optional[str] = None, date_to: Optional[str] = None,
                     limit: int = 50) -> pd.DataFrame:
        df = self.data.matches
        if team:
            df = df[_team_mask(df, team)]
        if opponent:
            df = df[_team_mask(df, opponent)]
        if competition:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]
        if date_from:
            df = df[df["date"] >= pd.to_datetime(date_from)]
        if date_to:
            df = df[df["date"] <= pd.to_datetime(date_to)]
        return df.sort_values("date", ascending=False).head(limit).reset_index(drop=True)

    def head_to_head(self, team_a: str, team_b: str) -> dict:
        df = self.data.matches
        mask_a = _team_mask(df, team_a)
        mask_b = _team_mask(df, team_b)
        sub = df[mask_a & mask_b]
        ak = team_key(team_a)
        wins_a = draws = wins_b = 0
        for _, r in sub.iterrows():
            hg, ag = r["home_goal"], r["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            if hg == ag:
                draws += 1
            elif (r["home_key"] == ak and hg > ag) or (r["away_key"] == ak and ag > hg):
                wins_a += 1
            else:
                wins_b += 1
        return {
            "team_a": team_a, "team_b": team_b,
            "matches": len(sub),
            "wins_a": wins_a, "wins_b": wins_b, "draws": draws,
            "sample": sub.sort_values("date", ascending=False).head(20).reset_index(drop=True),
        }

    # ---------- team stats ----------
    def team_record(self, team: str, season: Optional[int] = None,
                    competition: Optional[str] = None, home_only: bool = False,
                    away_only: bool = False) -> dict:
        tk = team_key(team)
        df = self.data.matches
        if season is not None:
            df = df[df["season"] == int(season)]
        if competition:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]
        if home_only:
            df = df[_team_mask(df, team, side="home")]
        elif away_only:
            df = df[_team_mask(df, team, side="away")]
        else:
            df = df[_team_mask(df, team)]

        wins = draws = losses = gf = ga = 0
        for _, r in df.iterrows():
            hg, ag = r["home_goal"], r["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            if r["home_key"] == tk:
                gf += hg; ga += ag
                if hg > ag: wins += 1
                elif hg == ag: draws += 1
                else: losses += 1
            else:
                gf += ag; ga += hg
                if ag > hg: wins += 1
                elif hg == ag: draws += 1
                else: losses += 1
        played = wins + draws + losses
        return {
            "team": team, "season": season, "competition": competition,
            "home_only": home_only, "away_only": away_only,
            "matches": played, "wins": wins, "draws": draws, "losses": losses,
            "goals_for": int(gf), "goals_against": int(ga),
            "goal_diff": int(gf - ga),
            "win_rate": (wins / played) if played else 0.0,
            "points": wins * 3 + draws,
        }

    # ---------- competition standings ----------
    def standings(self, competition: str, season: int) -> pd.DataFrame:
        df = self.data.matches
        df = df[df["season"] == int(season)]
        key = competition.lower()
        # pick a primary source to avoid duplicates across datasets
        if "brasileir" in key or "serie a" in key:
            primary = df[df["competition"] == "Brasileirão"]
            if primary.empty:
                primary = df[df["competition"] == "Brasileirão (histórico)"]
            df = primary
        elif "copa do brasil" in key:
            df = df[df["competition"] == "Copa do Brasil"]
        elif "libertadores" in key:
            df = df[df["competition"] == "Copa Libertadores"]
        else:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]
            df = df.drop_duplicates(subset=["date", "home_team", "away_team", "home_goal", "away_goal"])
        teams: dict[str, dict] = {}
        for _, r in df.iterrows():
            hg, ag = r["home_goal"], r["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            for t, gf, ga in [(r["home_team"], hg, ag), (r["away_team"], ag, hg)]:
                d = teams.setdefault(t, {"team": t, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0})
                d["P"] += 1; d["GF"] += gf; d["GA"] += ga
                if gf > ga:
                    d["W"] += 1; d["Pts"] += 3
                elif gf == ga:
                    d["D"] += 1; d["Pts"] += 1
                else:
                    d["L"] += 1
        out = pd.DataFrame(list(teams.values()))
        if out.empty:
            return out
        out["GD"] = out["GF"] - out["GA"]
        out = out.sort_values(["Pts", "GD", "GF"], ascending=[False, False, False]).reset_index(drop=True)
        out.index = out.index + 1
        return out

    # ---------- player queries ----------
    def find_players(self, name: Optional[str] = None, nationality: Optional[str] = None,
                     club: Optional[str] = None, position: Optional[str] = None,
                     min_overall: Optional[int] = None, limit: int = 25) -> pd.DataFrame:
        df = self.data.fifa
        if name:
            df = df[df["Name"].str.contains(name, case=False, na=False)]
        if nationality:
            df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
        if club:
            df = df[df["Club"].str.contains(club, case=False, na=False)]
        if position:
            df = df[df["Position"].astype(str).str.contains(position, case=False, na=False)]
        if min_overall is not None:
            df = df[pd.to_numeric(df["Overall"], errors="coerce") >= int(min_overall)]
        cols = [c for c in ["ID", "Name", "Age", "Nationality", "Overall", "Potential",
                            "Club", "Position", "Jersey Number"] if c in df.columns]
        return df.sort_values("Overall", ascending=False)[cols].head(limit).reset_index(drop=True)

    # ---------- stats ----------
    def biggest_wins(self, competition: Optional[str] = None, limit: int = 10) -> pd.DataFrame:
        df = self.data.matches.copy()
        if competition:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]
        df = df.dropna(subset=["home_goal", "away_goal"])
        df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
        df["total"] = df["home_goal"] + df["away_goal"]
        return df.sort_values(["margin", "total"], ascending=[False, False]).head(limit).reset_index(drop=True)

    def average_goals(self, competition: Optional[str] = None,
                      season: Optional[int] = None) -> dict:
        df = self.data.matches
        if competition:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]
        df = df.dropna(subset=["home_goal", "away_goal"])
        if df.empty:
            return {"matches": 0, "avg_goals_per_match": 0.0, "home_win_rate": 0.0}
        total = df["home_goal"] + df["away_goal"]
        home_wins = (df["home_goal"] > df["away_goal"]).sum()
        return {
            "matches": int(len(df)),
            "avg_goals_per_match": float(total.mean()),
            "home_win_rate": float(home_wins / len(df)),
            "competition": competition, "season": season,
        }

    def top_scoring_teams(self, competition: str, season: int, limit: int = 10) -> pd.DataFrame:
        s = self.standings(competition, season)
        if s.empty:
            return s
        return s.sort_values("GF", ascending=False).head(limit).reset_index(drop=True)
