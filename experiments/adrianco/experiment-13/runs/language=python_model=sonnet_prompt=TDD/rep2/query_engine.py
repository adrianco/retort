import datetime
from typing import Optional
import pandas as pd

from data_loader import DataLoader, normalize_team_name, parse_date


class QueryEngine:
    """Query engine over Brazilian soccer data."""

    def __init__(self, data_loader: DataLoader):
        self.loader = data_loader

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _all_matches(self) -> pd.DataFrame:
        return self.loader.load_all_matches()

    def _team_mask(self, df: pd.DataFrame, team: str) -> pd.Series:
        """Return boolean mask for rows where team is home or away (after normalization)."""
        norm = normalize_team_name(team)
        return (
            df["home_team"].apply(normalize_team_name).eq(norm) |
            df["away_team"].apply(normalize_team_name).eq(norm)
        )

    def _to_date(self, val) -> Optional[datetime.date]:
        if isinstance(val, datetime.date):
            return val
        return parse_date(val)

    # ─── Cycle 4: find_matches ─────────────────────────────────────────────────

    def find_matches(
        self,
        team: Optional[str] = None,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        df = self._all_matches().copy()

        if team is not None:
            df = df[self._team_mask(df, team)]

        if season is not None:
            df = df[df["season"] == season]

        if competition is not None:
            df = df[df["competition"] == competition]

        if date_from is not None:
            d_from = self._to_date(date_from)
            if d_from is not None and "date" in df.columns:
                df = df[df["date"].apply(lambda d: d >= d_from if d else False)]

        if date_to is not None:
            d_to = self._to_date(date_to)
            if d_to is not None and "date" in df.columns:
                df = df[df["date"].apply(lambda d: d <= d_to if d else False)]

        df = df.head(limit)
        return df.to_dict(orient="records")

    # ─── Cycle 5: head_to_head ─────────────────────────────────────────────────

    def head_to_head(self, team1: str, team2: str) -> dict:
        norm1 = normalize_team_name(team1)
        norm2 = normalize_team_name(team2)
        df = self._all_matches().copy()

        # Normalize in-place for comparison
        df["_home"] = df["home_team"].apply(normalize_team_name)
        df["_away"] = df["away_team"].apply(normalize_team_name)

        mask = (
            (df["_home"].eq(norm1) & df["_away"].eq(norm2)) |
            (df["_home"].eq(norm2) & df["_away"].eq(norm1))
        )
        h2h = df[mask].drop(columns=["_home", "_away"])

        wins = losses = draws = 0
        matches = []
        for _, row in h2h.iterrows():
            hg = row["home_goal"]
            ag = row["away_goal"]
            home = normalize_team_name(row["home_team"])
            match_dict = row.to_dict()
            if hg > ag:
                winner = home
            elif ag > hg:
                winner = normalize_team_name(row["away_team"])
            else:
                winner = None

            if winner is None:
                draws += 1
            elif winner == norm1:
                wins += 1
            else:
                losses += 1

            matches.append(match_dict)

        return {
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "matches": matches,
        }

    # ─── Cycle 6: get_team_stats ───────────────────────────────────────────────

    def get_team_stats(
        self,
        team: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        home_only: bool = False,
        away_only: bool = False,
    ) -> dict:
        df = self._all_matches().copy()
        norm = normalize_team_name(team)

        if competition is not None:
            df = df[df["competition"] == competition]
        if season is not None:
            df = df[df["season"] == season]

        df["_home"] = df["home_team"].apply(normalize_team_name)
        df["_away"] = df["away_team"].apply(normalize_team_name)

        if home_only:
            df = df[df["_home"].eq(norm)]
        elif away_only:
            df = df[df["_away"].eq(norm)]
        else:
            df = df[df["_home"].eq(norm) | df["_away"].eq(norm)]

        wins = draws = losses = goals_for = goals_against = 0

        for _, row in df.iterrows():
            hg = row["home_goal"]
            ag = row["away_goal"]
            is_home = normalize_team_name(row["home_team"]) == norm

            if is_home:
                gf, ga = hg, ag
            else:
                gf, ga = ag, hg

            goals_for += gf
            goals_against += ga

            if gf > ga:
                wins += 1
            elif gf == ga:
                draws += 1
            else:
                losses += 1

        return {
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "matches_played": wins + draws + losses,
        }

    # ─── Cycle 7: find_players ────────────────────────────────────────────────

    def find_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_rating: Optional[int] = None,
        limit: int = 20,
    ) -> list[dict]:
        df = self.loader.load_players().copy()

        if name is not None:
            df = df[df["Name"].str.contains(name, case=False, na=False)]

        if nationality is not None:
            df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]

        if club is not None:
            df = df[df["Club"].str.contains(club, case=False, na=False)]

        if position is not None:
            df = df[df["Position"].str.contains(position, case=False, na=False)]

        if min_rating is not None:
            df = df[pd.to_numeric(df["Overall"], errors="coerce") >= min_rating]

        df = df.head(limit)
        return df.to_dict(orient="records")

    # ─── Cycle 8: get_standings ───────────────────────────────────────────────

    def get_standings(self, season: int, competition: str = "brasileirao") -> list[dict]:
        df = self._all_matches()
        df = df[(df["season"] == season) & (df["competition"] == competition)].copy()

        # Collect all teams
        teams = set(df["home_team"].apply(normalize_team_name)) | \
                set(df["away_team"].apply(normalize_team_name))

        standings = []
        for team in teams:
            stats = self.get_team_stats(
                team,
                competition=competition,
                season=season,
            )
            points = stats["wins"] * 3 + stats["draws"]
            standings.append({
                "team": team,
                "points": points,
                "wins": stats["wins"],
                "draws": stats["draws"],
                "losses": stats["losses"],
                "goals_for": stats["goals_for"],
                "goals_against": stats["goals_against"],
            })

        standings.sort(key=lambda x: (x["points"], x["goals_for"] - x["goals_against"]),
                       reverse=True)
        return standings

    # ─── Cycle 9: statistics ──────────────────────────────────────────────────

    def get_biggest_wins(
        self,
        competition: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        df = self._all_matches().copy()

        if competition is not None:
            df = df[df["competition"] == competition]

        df["goal_diff"] = (
            pd.to_numeric(df["home_goal"], errors="coerce") -
            pd.to_numeric(df["away_goal"], errors="coerce")
        ).abs()

        df = df.sort_values("goal_diff", ascending=False).head(limit)
        return df.to_dict(orient="records")

    def competition_averages(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        df = self._all_matches().copy()

        if competition is not None:
            df = df[df["competition"] == competition]
        if season is not None:
            df = df[df["season"] == season]

        if len(df) == 0:
            return {"avg_goals_per_match": 0.0, "home_win_rate": 0.0}

        home_goals = pd.to_numeric(df["home_goal"], errors="coerce").fillna(0)
        away_goals = pd.to_numeric(df["away_goal"], errors="coerce").fillna(0)

        total_goals = (home_goals + away_goals).sum()
        avg_goals = float(total_goals) / len(df)

        home_wins = (home_goals > away_goals).sum()
        home_win_rate = float(home_wins) / len(df)

        return {
            "avg_goals_per_match": round(avg_goals, 4),
            "home_win_rate": round(home_win_rate, 4),
        }
