"""
DataLoader: loads and normalises all Brazilian soccer CSV datasets,
and provides query methods used by the MCP server tools.
"""
from __future__ import annotations

import os
import re
from typing import Optional

import pandas as pd


def _normalise(name: str) -> str:
    """Strip state suffix (e.g. '-SP', '- MG') and extra whitespace."""
    if pd.isna(name):
        return ""
    name = str(name).strip()
    name = re.sub(r"\s*-\s*[A-Z]{2}\s*$", "", name)
    return name.strip()


def _team_contains(series: pd.Series, fragment: str) -> pd.Series:
    return series.str.contains(fragment, case=False, na=False, regex=False)


class DataLoader:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        self._load_all()

    # ------------------------------------------------------------------
    # Internal loaders
    # ------------------------------------------------------------------

    def _path(self, filename: str) -> str:
        return os.path.join(self.data_dir, filename)

    def _load_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("Brasileirao_Matches.csv"))
        df["competition"] = "brasileirao"
        df["home_team_norm"] = df["home_team"].apply(_normalise)
        df["away_team_norm"] = df["away_team"].apply(_normalise)
        df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        return df

    def _load_copa_do_brasil(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("Brazilian_Cup_Matches.csv"))
        df["competition"] = "copa_do_brasil"
        df["home_team_norm"] = df["home_team"].apply(_normalise)
        df["away_team_norm"] = df["away_team"].apply(_normalise)
        df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        return df

    def _load_libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("Libertadores_Matches.csv"))
        df["competition"] = "libertadores"
        df["home_team_norm"] = df["home_team"].apply(_normalise)
        df["away_team_norm"] = df["away_team"].apply(_normalise)
        df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        return df

    def _load_historico(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("novo_campeonato_brasileiro.csv"))
        df["competition"] = "brasileirao"
        df["home_team"] = df["Equipe_mandante"]
        df["away_team"] = df["Equipe_visitante"]
        df["home_team_norm"] = df["Equipe_mandante"].apply(_normalise)
        df["away_team_norm"] = df["Equipe_visitante"].apply(_normalise)
        df["home_goal"] = pd.to_numeric(df["Gols_mandante"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["Gols_visitante"], errors="coerce")
        df["season"] = df["Ano"]
        df["date"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
        return df

    def _load_br_football(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("BR-Football-Dataset.csv"))
        # Map tournament name to competition key
        def _map_comp(t: str) -> str:
            t = (t or "").lower()
            if "brasil" in t:
                return "brasileirao"
            if "copa do brasil" in t or "cup" in t:
                return "copa_do_brasil"
            if "libertadores" in t:
                return "libertadores"
            return t.replace(" ", "_")

        df["competition"] = df["tournament"].apply(_map_comp)
        df["home_team"] = df["home"]
        df["away_team"] = df["away"]
        df["home_team_norm"] = df["home"].apply(_normalise)
        df["away_team_norm"] = df["away"].apply(_normalise)
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["season"] = df["date"].dt.year
        return df

    def _load_players(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("fifa_data.csv"), index_col=0)
        df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
        df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce")
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
        return df

    def _load_all(self) -> None:
        self._brasileirao = self._load_brasileirao()
        self._copa = self._load_copa_do_brasil()
        self._libertadores = self._load_libertadores()
        self._historico = self._load_historico()
        self._br_football = self._load_br_football()
        self._players = self._load_players()

        # Unified match table (brasileirao only uses Brasileirao_Matches.csv to avoid
        # double-counting; historico is kept for older seasons 2003-2011)
        brasileirao_seasons = set(self._brasileirao["season"].dropna().astype(int))
        historico_older = self._historico[~self._historico["season"].isin(brasileirao_seasons)]

        common_cols = ["date", "home_team", "away_team", "home_team_norm",
                       "away_team_norm", "home_goal", "away_goal", "season", "competition"]

        frames = []
        for df in [self._brasileirao, historico_older, self._copa, self._libertadores]:
            available = [c for c in common_cols if c in df.columns]
            frames.append(df[available].copy())

        self._all_matches = pd.concat(frames, ignore_index=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _competition_df(self, competition: Optional[str]) -> pd.DataFrame:
        comp = (competition or "").lower()

        # BR-Football-Dataset covers 2014-2023 and is the authoritative source for
        # competitions with normalised competition labels. The other CSV files (with their
        # exact competition-named sources) take priority; BR-Football fills gaps (e.g. 2023).
        mapping = {
            "brasileirao": [self._brasileirao, self._historico, self._br_football],
            "copa_do_brasil": [self._copa, self._br_football],
            "libertadores": [self._libertadores, self._br_football],
        }
        if comp in mapping:
            sources = mapping[comp]
        else:
            sources = [self._brasileirao, self._historico, self._copa,
                       self._libertadores, self._br_football]

        common_cols = ["date", "home_team", "away_team", "home_team_norm",
                       "away_team_norm", "home_goal", "away_goal", "season", "competition"]

        frames = []
        for df in sources:
            sub = df.copy()
            # For br_football, filter to matching competition when requested
            if comp and "tournament" in df.columns:
                sub = sub[sub["competition"] == comp]
            available = [c for c in common_cols if c in sub.columns]
            frames.append(sub[available].copy())

        combined = pd.concat(frames, ignore_index=True)

        # Drop records with no score (unplayed / postponed fixtures)
        combined = combined.dropna(subset=["home_goal", "away_goal"])

        # Deduplicate on (date, home_team_norm, away_team_norm) — keeps the first
        # occurrence (primary dataset takes priority via order of sources above)
        combined = combined.drop_duplicates(
            subset=["date", "home_team_norm", "away_team_norm"], keep="first"
        )

        return combined

    # ------------------------------------------------------------------
    # Public query methods (called by MCP tools)
    # ------------------------------------------------------------------

    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        df = self._competition_df(competition)

        if team:
            frag = _normalise(team)
            mask = _team_contains(df["home_team_norm"], frag) | _team_contains(df["away_team_norm"], frag)
            df = df[mask]

        if opponent:
            frag = _normalise(opponent)
            mask = _team_contains(df["home_team_norm"], frag) | _team_contains(df["away_team_norm"], frag)
            df = df[mask]

        if season is not None:
            df = df[df["season"] == int(season)]

        if date_from:
            df = df[df["date"] >= pd.to_datetime(date_from)]

        if date_to:
            df = df[df["date"] <= pd.to_datetime(date_to)]

        total = len(df)
        df = df.sort_values("date", ascending=False).head(int(limit))

        matches = []
        for _, row in df.iterrows():
            matches.append({
                "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else None,
                "home_team": str(row.get("home_team", "")),
                "away_team": str(row.get("away_team", "")),
                "home_goal": int(row["home_goal"]) if pd.notna(row.get("home_goal")) else None,
                "away_goal": int(row["away_goal"]) if pd.notna(row.get("away_goal")) else None,
                "competition": str(row.get("competition", "")),
                "season": int(row["season"]) if pd.notna(row.get("season")) else None,
            })

        return {"total_found": total, "matches": matches}

    def get_team_stats(
        self,
        team: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        result = self.find_matches(team=team, competition=competition, season=season, limit=100_000)
        frag = _normalise(team).lower()

        wins = draws = losses = goals_for = goals_against = 0

        for m in result["matches"]:
            home_norm = _normalise(m["home_team"]).lower()
            away_norm = _normalise(m["away_team"]).lower()
            hg = m["home_goal"] or 0
            ag = m["away_goal"] or 0

            is_home = frag in home_norm
            is_away = frag in away_norm

            if is_home:
                goals_for += hg
                goals_against += ag
                if hg > ag:
                    wins += 1
                elif hg == ag:
                    draws += 1
                else:
                    losses += 1
            elif is_away:
                goals_for += ag
                goals_against += hg
                if ag > hg:
                    wins += 1
                elif ag == hg:
                    draws += 1
                else:
                    losses += 1

        total = wins + draws + losses
        return {
            "team": team,
            "competition": competition,
            "season": season,
            "matches": total,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0.0,
        }

    def find_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_rating: Optional[int] = None,
        limit: int = 20,
    ) -> dict:
        df = self._players.copy()

        if name:
            df = df[df["Name"].str.contains(name, case=False, na=False, regex=False)]
        if nationality:
            df = df[df["Nationality"].str.contains(nationality, case=False, na=False, regex=False)]
        if club:
            df = df[df["Club"].str.contains(club, case=False, na=False, regex=False)]
        if position:
            df = df[df["Position"].str.contains(position, case=False, na=False, regex=False)]
        if min_rating is not None:
            df = df[df["Overall"] >= int(min_rating)]

        total = len(df)
        df = df.sort_values("Overall", ascending=False).head(int(limit))

        players = []
        for _, row in df.iterrows():
            players.append({
                "name": str(row.get("Name", "")),
                "nationality": str(row.get("Nationality", "")),
                "club": str(row.get("Club", "")),
                "position": str(row.get("Position", "")),
                "overall": int(row["Overall"]) if pd.notna(row.get("Overall")) else None,
                "potential": int(row["Potential"]) if pd.notna(row.get("Potential")) else None,
                "age": int(row["Age"]) if pd.notna(row.get("Age")) else None,
            })

        return {"total_found": total, "players": players}

    def get_standings(
        self,
        season: int,
        competition: str = "brasileirao",
    ) -> dict:
        result = self.find_matches(competition=competition, season=season, limit=100_000)
        standings: dict[str, dict] = {}

        for m in result["matches"]:
            home = _normalise(m["home_team"])
            away = _normalise(m["away_team"])
            hg = m["home_goal"] or 0
            ag = m["away_goal"] or 0

            for t in (home, away):
                if t and t not in standings:
                    standings[t] = {
                        "team": t, "played": 0, "won": 0, "drawn": 0,
                        "lost": 0, "goals_for": 0, "goals_against": 0, "points": 0,
                    }

            if not home or not away:
                continue

            standings[home]["played"] += 1
            standings[away]["played"] += 1
            standings[home]["goals_for"] += hg
            standings[home]["goals_against"] += ag
            standings[away]["goals_for"] += ag
            standings[away]["goals_against"] += hg

            if hg > ag:
                standings[home]["won"] += 1
                standings[home]["points"] += 3
                standings[away]["lost"] += 1
            elif ag > hg:
                standings[away]["won"] += 1
                standings[away]["points"] += 3
                standings[home]["lost"] += 1
            else:
                standings[home]["drawn"] += 1
                standings[away]["drawn"] += 1
                standings[home]["points"] += 1
                standings[away]["points"] += 1

        table = sorted(
            standings.values(),
            key=lambda x: (x["points"], x["won"], x["goals_for"] - x["goals_against"]),
            reverse=True,
        )
        for i, row in enumerate(table):
            row["position"] = i + 1

        return {
            "season": season,
            "competition": competition,
            "total_matches": len(result["matches"]),
            "standings": table,
        }

    def get_statistics(
        self,
        stat_type: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> dict:
        result = self.find_matches(competition=competition, season=season, limit=100_000)
        matches = result["matches"]

        if stat_type == "biggest_wins":
            wins = []
            for m in matches:
                hg = m["home_goal"] or 0
                ag = m["away_goal"] or 0
                diff = abs(hg - ag)
                if diff > 0:
                    wins.append({
                        "date": m["date"],
                        "home_team": m["home_team"],
                        "away_team": m["away_team"],
                        "home_goal": hg,
                        "away_goal": ag,
                        "goal_difference": diff,
                        "competition": m["competition"],
                        "season": m["season"],
                    })
            wins.sort(key=lambda x: x["goal_difference"], reverse=True)
            return {"stat_type": stat_type, "results": wins[: int(limit)]}

        if stat_type == "avg_goals":
            if not matches:
                return {"stat_type": stat_type, "avg_goals_per_match": 0.0,
                        "total_matches": 0, "total_goals": 0}
            total_goals = sum((m["home_goal"] or 0) + (m["away_goal"] or 0) for m in matches)
            return {
                "stat_type": stat_type,
                "avg_goals_per_match": round(total_goals / len(matches), 2),
                "total_matches": len(matches),
                "total_goals": total_goals,
            }

        if stat_type == "home_record":
            hw = hd = hl = 0
            for m in matches:
                hg = m["home_goal"] or 0
                ag = m["away_goal"] or 0
                if hg > ag:
                    hw += 1
                elif hg == ag:
                    hd += 1
                else:
                    hl += 1
            total = hw + hd + hl
            return {
                "stat_type": stat_type,
                "home_wins": hw,
                "home_draws": hd,
                "home_losses": hl,
                "total_matches": total,
                "home_win_rate": round(hw / total * 100, 1) if total > 0 else 0.0,
            }

        return {"error": f"Unknown stat_type: {stat_type}. Use biggest_wins, avg_goals, or home_record."}
