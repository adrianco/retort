"""Query engine over Brazilian soccer datasets."""
from __future__ import annotations

from typing import Any

import pandas as pd

from data_loader import DataLoader, normalize_team_name


def _team_matches(name: str, norm: str) -> bool:
    """Return True if search term `name` appears in normalized team string `norm`."""
    return name.lower() in norm.lower()


def _to_int(val) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


class QueryEngine:
    """High-level query interface over all datasets."""

    def __init__(self, data_dir: str):
        self._loader = DataLoader(data_dir)

    def load(self) -> None:
        self._loader.load_all()

    # ------------------------------------------------------------------ helpers

    def _unified_matches(self, competition: str | None = None) -> list[tuple[str, pd.DataFrame]]:
        """Return list of (label, df) pairs respecting the competition filter."""
        all_dfs = [
            ("brasileirao", self._loader.brasileirao),
            ("copa_brasil", self._loader.copa_brasil),
            ("libertadores", self._loader.libertadores),
            ("br_football", self._loader.br_football),
            ("historical", self._loader.historical),
        ]
        if competition:
            comp = competition.lower().replace(" ", "_")
            all_dfs = [(label, df) for label, df in all_dfs if comp in label]
        return all_dfs

    def _row_to_match(self, row: pd.Series, label: str) -> dict[str, Any]:
        """Convert a DataFrame row to a normalised match dict."""
        home_norm = str(row.get("home_team_norm", "") or "")
        away_norm = str(row.get("away_team_norm", "") or "")

        # Raw team names (with state suffixes) for disambiguation
        home_raw = str(row.get("home_team", row.get("home", row.get("Equipe_mandante", home_norm))))
        away_raw = str(row.get("away_team", row.get("away", row.get("Equipe_visitante", away_norm))))

        home_g = _to_int(row.get("home_goal", row.get("Gols_mandante", 0)))
        away_g = _to_int(row.get("away_goal", row.get("Gols_visitante", 0)))
        season_val = row.get("season")
        if season_val is None or (isinstance(season_val, float) and pd.isna(season_val)):
            season_val = row.get("Ano", None)
        date = row.get("date_parsed", None)

        return {
            "home_team": home_norm or home_raw,
            "away_team": away_norm or away_raw,
            "home_team_raw": home_raw,
            "away_team_raw": away_raw,
            "home_goal": home_g,
            "away_goal": away_g,
            "season": int(season_val) if season_val is not None and pd.notna(season_val) else None,
            "date": str(date.date()) if date is not None and pd.notna(date) else None,
            "competition": label,
        }

    # ------------------------------------------------------------------ search_matches

    def search_matches(
        self,
        team: str | None = None,
        home_team: str | None = None,
        away_team: str | None = None,
        team1: str | None = None,
        team2: str | None = None,
        season: int | None = None,
        competition: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict] = []
        for label, df in self._unified_matches(competition):
            if df is None or df.empty:
                continue

            home_col = "home_team_norm"
            away_col = "away_team_norm"

            mask = pd.Series([True] * len(df), index=df.index)

            if season is not None:
                if "season" in df.columns:
                    mask &= df["season"].apply(_to_int) == season
                elif "Ano" in df.columns:
                    mask &= df["Ano"].apply(_to_int) == season

            if team1 and team2:
                t1, t2 = team1.lower(), team2.lower()
                mask &= (
                    (df[home_col].str.lower().str.contains(t1, na=False, regex=False) &
                     df[away_col].str.lower().str.contains(t2, na=False, regex=False)) |
                    (df[home_col].str.lower().str.contains(t2, na=False, regex=False) &
                     df[away_col].str.lower().str.contains(t1, na=False, regex=False))
                )
            else:
                if team:
                    t = team.lower()
                    mask &= (
                        df[home_col].str.lower().str.contains(t, na=False, regex=False) |
                        df[away_col].str.lower().str.contains(t, na=False, regex=False)
                    )
                if home_team:
                    t = home_team.lower()
                    mask &= df[home_col].str.lower().str.contains(t, na=False, regex=False)
                if away_team:
                    t = away_team.lower()
                    mask &= df[away_col].str.lower().str.contains(t, na=False, regex=False)

            filtered = df[mask]
            for _, row in filtered.iterrows():
                results.append(self._row_to_match(row, label))

        if limit:
            results = results[:limit]
        return results

    # ------------------------------------------------------------------ get_team_stats

    def get_team_stats(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        home_only: bool = False,
    ) -> dict[str, Any]:
        matches = self.search_matches(
            team=team,
            season=season,
            competition=competition,
        )

        stats: dict[str, Any] = {
            "team": team,
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }

        for m in matches:
            is_home = team.lower() in m["home_team"].lower()
            if home_only and not is_home:
                continue
            stats["matches"] += 1
            if is_home:
                gf, ga = m["home_goal"], m["away_goal"]
            else:
                gf, ga = m["away_goal"], m["home_goal"]
            stats["goals_for"] += gf
            stats["goals_against"] += ga
            if gf > ga:
                stats["wins"] += 1
            elif gf == ga:
                stats["draws"] += 1
            else:
                stats["losses"] += 1

        if home_only:
            stats["home_wins"] = stats["wins"]

        return stats

    # ------------------------------------------------------------------ search_players

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        df = self._loader.fifa
        if df is None:
            return []

        mask = pd.Series([True] * len(df), index=df.index)

        if name:
            mask &= df["Name"].str.lower().str.contains(name.lower(), na=False, regex=False)
        if nationality:
            mask &= df["Nationality"] == nationality
        if club:
            mask &= df["Club"].str.lower().str.contains(club.lower(), na=False, regex=False)
        if position:
            mask &= df["Position"].str.lower() == position.lower()

        filtered = df[mask]

        if sort_by and sort_by in filtered.columns:
            filtered = filtered.sort_values(sort_by, ascending=False)

        cols = ["Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position",
                "Jersey Number", "Height", "Weight"]
        cols = [c for c in cols if c in filtered.columns]
        records = filtered[cols].to_dict(orient="records")

        if limit:
            records = records[:limit]
        return records

    # ------------------------------------------------------------------ get_head_to_head

    def get_head_to_head(self, team1: str, team2: str) -> dict[str, Any]:
        matches = self.search_matches(team1=team1, team2=team2)
        t1_wins = t2_wins = draws = 0
        for m in matches:
            is_t1_home = team1.lower() in m["home_team"].lower()
            if is_t1_home:
                gf, ga = m["home_goal"], m["away_goal"]
            else:
                gf, ga = m["away_goal"], m["home_goal"]
            if gf > ga:
                t1_wins += 1
            elif gf == ga:
                draws += 1
            else:
                t2_wins += 1

        return {
            "team1": team1,
            "team2": team2,
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "total_matches": len(matches),
            "matches": matches,
        }

    # ------------------------------------------------------------------ get_standings

    def get_standings(self, season: int, competition: str = "brasileirao") -> list[dict[str, Any]]:
        matches = self.search_matches(season=season, competition=competition)
        table: dict[str, dict] = {}

        def _team_entry(name: str) -> dict:
            return {"team": name, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0}

        for m in matches:
            # Use raw team names to keep Atletico-MG and Atletico-PR distinct
            h = m.get("home_team_raw", m["home_team"])
            a = m.get("away_team_raw", m["away_team"])
            for t in (h, a):
                if t not in table:
                    table[t] = _team_entry(t)

            hg, ag = m["home_goal"], m["away_goal"]
            table[h]["goals_for"] += hg
            table[h]["goals_against"] += ag
            table[a]["goals_for"] += ag
            table[a]["goals_against"] += hg

            if hg > ag:
                table[h]["wins"] += 1
                table[a]["losses"] += 1
            elif hg == ag:
                table[h]["draws"] += 1
                table[a]["draws"] += 1
            else:
                table[a]["wins"] += 1
                table[h]["losses"] += 1

        # Normalise team names for display (strip state suffix)
        from data_loader import normalize_team_name as _norm
        for entry in table.values():
            entry["team"] = _norm(entry["team"])

        standings = []
        for entry in table.values():
            entry["points"] = entry["wins"] * 3 + entry["draws"]
            entry["matches"] = entry["wins"] + entry["draws"] + entry["losses"]
            standings.append(entry)

        standings.sort(key=lambda x: (x["points"], x["wins"], x["goals_for"] - x["goals_against"]),
                       reverse=True)
        return standings

    # ------------------------------------------------------------------ statistics

    def get_biggest_wins(
        self, competition: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        matches = self.search_matches(competition=competition)
        for m in matches:
            m["goal_diff"] = abs(m["home_goal"] - m["away_goal"])
        matches.sort(key=lambda x: x["goal_diff"], reverse=True)
        return matches[:limit]

    def get_average_goals(self, competition: str | None = None) -> float:
        matches = self.search_matches(competition=competition)
        if not matches:
            return 0.0
        total = sum(m["home_goal"] + m["away_goal"] for m in matches)
        return total / len(matches)

    def get_home_win_rate(self, competition: str | None = None) -> float:
        matches = self.search_matches(competition=competition)
        if not matches:
            return 0.0
        home_wins = sum(1 for m in matches if m["home_goal"] > m["away_goal"])
        return home_wins / len(matches)

    def get_top_scoring_teams(
        self, season: int | None = None, competition: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        matches = self.search_matches(season=season, competition=competition)
        goals: dict[str, int] = {}
        for m in matches:
            goals[m["home_team"]] = goals.get(m["home_team"], 0) + m["home_goal"]
            goals[m["away_team"]] = goals.get(m["away_team"], 0) + m["away_goal"]
        results = [{"team": t, "goals": g} for t, g in goals.items()]
        results.sort(key=lambda x: x["goals"], reverse=True)
        return results[:limit]
