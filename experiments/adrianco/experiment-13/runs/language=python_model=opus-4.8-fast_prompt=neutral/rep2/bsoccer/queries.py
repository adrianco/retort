"""
Context
=======
Module: bsoccer.queries
Purpose: The query engine that answers the five required capability categories
         (matches, teams, players, competitions, statistics) over the normalized
         DataFrames produced by bsoccer.data.

Each public method returns a plain dict/list of JSON-serializable primitives so
the result is equally usable from the MCP server, the CLI, or tests. Methods do
not format prose; presentation/formatting lives in bsoccer.format so the raw
data can be consumed programmatically.

Team matching strategy
----------------------
Callers pass free-text team names. We normalize the query (bsoccer.normalize)
and match against the precomputed home_key/away_key columns. If an exact
normalized key is not present we fall back to substring matching on the key so
"corinthians" matches "corinthians paulista".
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .data import SoccerData
from .normalize import normalize_team


class QueryEngine:
    def __init__(self, data: SoccerData):
        self.data = data

    # ------------------------------------------------------------------ #
    # Team-name resolution
    # ------------------------------------------------------------------ #

    def resolve_team_key(self, query: str) -> str | None:
        """Resolve free text to a normalized team key present in the data.

        Tries exact key match first, then unique substring match. Returns the
        normalized key (which may itself be a substring) or None if nothing
        plausible is found.
        """
        key = normalize_team(query)
        if not key:
            return None
        directory = self.data.team_directory()
        if key in directory:
            return key
        # Substring match against known keys.
        candidates = [k for k in directory if key in k or k in key]
        if not candidates:
            return None
        # Prefer the shortest candidate (most general canonical name).
        candidates.sort(key=len)
        return candidates[0]

    def team_display(self, key: str) -> str:
        return self.data.team_directory().get(key, key)

    def _team_mask(self, df: pd.DataFrame, key: str, side: str = "either") -> pd.Series:
        """Boolean mask of rows involving *key* on the given side."""
        home = df["home_key"].str.contains(key, regex=False, na=False)
        away = df["away_key"].str.contains(key, regex=False, na=False)
        if side == "home":
            return home
        if side == "away":
            return away
        return home | away

    # ------------------------------------------------------------------ #
    # 1. Match queries
    # ------------------------------------------------------------------ #

    def find_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        side: str = "either",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Find matches by any combination of criteria."""
        df = self.data.matches
        notes: list[str] = []

        team_key = None
        if team:
            team_key = self.resolve_team_key(team)
            if team_key is None:
                return {"count": 0, "matches": [], "error": f"Team not found: {team}"}
            df = df[self._team_mask(df, team_key, side)]

        if opponent:
            opp_key = self.resolve_team_key(opponent)
            if opp_key is None:
                return {"count": 0, "matches": [], "error": f"Team not found: {opponent}"}
            df = df[self._team_mask(df, opp_key, "either")]

        if competition:
            comp_key = normalize_team(competition)
            df = df[df["competition"].map(normalize_team).str.contains(comp_key, na=False)]

        if season is not None:
            df = df[df["season"] == int(season)]

        if date_from:
            df = df[df["date"] >= pd.to_datetime(date_from, errors="coerce")]
        if date_to:
            df = df[df["date"] <= pd.to_datetime(date_to, errors="coerce")]

        total = len(df)
        df = df.sort_values("date", na_position="last").head(limit)
        return {
            "count": total,
            "returned": len(df),
            "matches": [self._match_dict(r) for _, r in df.iterrows()],
            "notes": notes,
        }

    def _match_dict(self, row: pd.Series) -> dict[str, Any]:
        date = row["date"]
        return {
            "date": None if pd.isna(date) else date.strftime("%Y-%m-%d"),
            "competition": row["competition"],
            "season": None if pd.isna(row["season"]) else int(row["season"]),
            "round": row["round"] or None,
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_goal": None if pd.isna(row["home_goal"]) else int(row["home_goal"]),
            "away_goal": None if pd.isna(row["away_goal"]) else int(row["away_goal"]),
            "stadium": row["stadium"] or None,
            "source": row["source"],
        }

    # ------------------------------------------------------------------ #
    # 2. Team queries + head to head
    # ------------------------------------------------------------------ #

    def team_record(
        self,
        team: str,
        competition: str | None = None,
        season: int | None = None,
        venue: str = "all",
    ) -> dict[str, Any]:
        """Win/draw/loss + goals record for a team, optionally filtered.

        venue: 'all' | 'home' | 'away'.
        """
        key = self.resolve_team_key(team)
        if key is None:
            return {"error": f"Team not found: {team}"}

        df = self.data.matches_dedup
        if competition:
            comp_key = normalize_team(competition)
            df = df[df["competition"].map(normalize_team).str.contains(comp_key, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]

        rec = self._record_from_matches(df, key, venue)
        rec.update({
            "team": self.team_display(key),
            "competition": competition,
            "season": season,
            "venue": venue,
        })
        return rec

    def _record_from_matches(self, df: pd.DataFrame, key: str, venue: str) -> dict[str, Any]:
        # Exact key equality: `key` is an already-canonicalized directory key, so
        # we must not substring-match (which would conflate e.g. "atletico mg"
        # with "atletico go").
        wins = draws = losses = gf = ga = 0
        is_home = df["home_key"] == key
        is_away = df["away_key"] == key

        if venue in ("all", "home"):
            home = df[is_home]
            gf += int(home["home_goal"].sum())
            ga += int(home["away_goal"].sum())
            wins += int((home["home_goal"] > home["away_goal"]).sum())
            draws += int((home["home_goal"] == home["away_goal"]).sum())
            losses += int((home["home_goal"] < home["away_goal"]).sum())
        if venue in ("all", "away"):
            away = df[is_away]
            gf += int(away["away_goal"].sum())
            ga += int(away["home_goal"].sum())
            wins += int((away["away_goal"] > away["home_goal"]).sum())
            draws += int((away["away_goal"] == away["home_goal"]).sum())
            losses += int((away["away_goal"] < away["home_goal"]).sum())

        played = wins + draws + losses
        return {
            "matches": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": round(wins / played * 100, 1) if played else 0.0,
        }

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Head-to-head record and match list between two teams."""
        key_a = self.resolve_team_key(team_a)
        key_b = self.resolve_team_key(team_b)
        if key_a is None:
            return {"error": f"Team not found: {team_a}"}
        if key_b is None:
            return {"error": f"Team not found: {team_b}"}

        df = self.data.matches_dedup
        if competition:
            comp_key = normalize_team(competition)
            df = df[df["competition"].map(normalize_team).str.contains(comp_key, na=False)]

        ah = df["home_key"] == key_a
        aa = df["away_key"] == key_a
        bh = df["home_key"] == key_b
        ba = df["away_key"] == key_b
        mask = (ah & ba) | (aa & bh)
        sub = df[mask].sort_values("date", na_position="last")

        a_wins = b_wins = draws = a_goals = b_goals = 0
        for _, r in sub.iterrows():
            a_is_home = r["home_key"] == key_a
            a_g = r["home_goal"] if a_is_home else r["away_goal"]
            b_g = r["away_goal"] if a_is_home else r["home_goal"]
            a_goals += int(a_g)
            b_goals += int(b_g)
            if a_g > b_g:
                a_wins += 1
            elif b_g > a_g:
                b_wins += 1
            else:
                draws += 1

        return {
            "team_a": self.team_display(key_a),
            "team_b": self.team_display(key_b),
            "total_matches": len(sub),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
            "matches": [self._match_dict(r) for _, r in sub.head(limit).iterrows()],
        }

    # ------------------------------------------------------------------ #
    # 3. Player queries
    # ------------------------------------------------------------------ #

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        sort_by: str = "Overall",
        limit: int = 25,
    ) -> dict[str, Any]:
        """Search the FIFA player database with optional filters."""
        df = self.data.players
        if name:
            df = df[df["Name"].str.contains(name, case=False, na=False)]
        if nationality:
            df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
        if club:
            club_key = normalize_team(club)
            df = df[df["club_key"].str.contains(club_key, regex=False, na=False)]
        if position:
            positions = [p.strip().upper() for p in position.split(",")]
            df = df[df["Position"].isin(positions)]
        if min_overall is not None:
            df = df[df["Overall"] >= int(min_overall)]

        total = len(df)
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=False)
        df = df.head(limit)
        return {
            "count": total,
            "returned": len(df),
            "players": [self._player_dict(r) for _, r in df.iterrows()],
        }

    def _player_dict(self, row: pd.Series) -> dict[str, Any]:
        def val(col):
            v = row.get(col)
            if pd.isna(v):
                return None
            return v

        return {
            "name": val("Name"),
            "age": int(row["Age"]) if not pd.isna(row.get("Age")) else None,
            "nationality": val("Nationality"),
            "overall": int(row["Overall"]) if not pd.isna(row.get("Overall")) else None,
            "potential": int(row["Potential"]) if not pd.isna(row.get("Potential")) else None,
            "club": val("Club"),
            "position": val("Position"),
            "jersey_number": val("Jersey Number"),
            "height": val("Height"),
            "weight": val("Weight"),
            "value": val("Value"),
        }

    def players_by_club_summary(self, nationality: str = "Brazil", top: int = 10) -> dict[str, Any]:
        """Aggregate player counts / average rating per club for a nationality."""
        df = self.data.players
        df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
        grouped = (
            df.groupby("Club")
            .agg(players=("Name", "count"), avg_overall=("Overall", "mean"))
            .sort_values("players", ascending=False)
            .head(top)
        )
        clubs = [
            {
                "club": club,
                "players": int(r["players"]),
                "avg_overall": round(float(r["avg_overall"]), 1),
            }
            for club, r in grouped.iterrows()
        ]
        return {"nationality": nationality, "total_players": len(df), "clubs": clubs}

    # ------------------------------------------------------------------ #
    # 4. Competition queries
    # ------------------------------------------------------------------ #

    def standings(
        self,
        competition: str = "Brasileirão",
        season: int | None = None,
        top: int | None = None,
    ) -> dict[str, Any]:
        """League table computed from match results (3pts win, 1 draw)."""
        df = self.data.matches_dedup
        comp_key = normalize_team(competition)
        df = df[df["competition"].map(normalize_team).str.contains(comp_key, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]
        if df.empty:
            return {"competition": competition, "season": season, "table": [],
                    "error": "No matches found for this competition/season."}

        # Gather all team keys appearing.
        keys = pd.unique(pd.concat([df["home_key"], df["away_key"]]))
        rows = []
        for key in keys:
            if not key:
                continue
            rec = self._record_from_matches(df, key, "all")
            if rec["matches"] == 0:
                continue
            rec["team"] = self.team_display(key)
            rows.append(rec)

        rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]))
        for i, r in enumerate(rows, 1):
            r["position"] = i
        if top:
            rows = rows[:top]
        return {"competition": competition, "season": season,
                "teams": len(rows), "table": rows}

    def champion(self, competition: str = "Brasileirão", season: int | None = None) -> dict[str, Any]:
        """Return the top-of-table team for a season (league competitions)."""
        table = self.standings(competition, season)
        if table.get("error"):
            return table
        if not table["table"]:
            return {"error": "No standings available."}
        champ = table["table"][0]
        return {
            "competition": competition,
            "season": season,
            "champion": champ["team"],
            "points": champ["points"],
            "record": f"{champ['wins']}W-{champ['draws']}D-{champ['losses']}L",
            "goals_for": champ["goals_for"],
            "goals_against": champ["goals_against"],
        }

    def seasons_available(self, competition: str | None = None) -> dict[str, Any]:
        df = self.data.matches
        if competition:
            comp_key = normalize_team(competition)
            df = df[df["competition"].map(normalize_team).str.contains(comp_key, na=False)]
        seasons = sorted(int(s) for s in df["season"].dropna().unique())
        return {
            "competition": competition,
            "competitions": self.data.competitions,
            "seasons": seasons,
        }

    # ------------------------------------------------------------------ #
    # 5. Statistical analysis
    # ------------------------------------------------------------------ #

    def competition_stats(
        self, competition: str | None = None, season: int | None = None
    ) -> dict[str, Any]:
        """Aggregate goal / home-advantage statistics."""
        df = self.data.matches_dedup
        if competition:
            comp_key = normalize_team(competition)
            df = df[df["competition"].map(normalize_team).str.contains(comp_key, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]
        if df.empty:
            return {"error": "No matches found for criteria."}

        n = len(df)
        total_goals = int(df["home_goal"].sum() + df["away_goal"].sum())
        home_wins = int((df["home_goal"] > df["away_goal"]).sum())
        away_wins = int((df["away_goal"] > df["home_goal"]).sum())
        draws = int((df["home_goal"] == df["away_goal"]).sum())
        return {
            "competition": competition,
            "season": season,
            "matches": n,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / n, 2),
            "avg_home_goals": round(float(df["home_goal"].mean()), 2),
            "avg_away_goals": round(float(df["away_goal"].mean()), 2),
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(home_wins / n * 100, 1),
            "away_win_rate": round(away_wins / n * 100, 1),
            "draw_rate": round(draws / n * 100, 1),
        }

    def biggest_wins(
        self,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Matches with the largest goal margin."""
        df = self.data.matches_dedup.copy()
        if competition:
            comp_key = normalize_team(competition)
            df = df[df["competition"].map(normalize_team).str.contains(comp_key, na=False)]
        if season is not None:
            df = df[df["season"] == int(season)]
        if df.empty:
            return {"matches": []}
        df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
        df["total"] = df["home_goal"] + df["away_goal"]
        df = df.sort_values(["margin", "total"], ascending=False).head(limit)
        return {
            "competition": competition,
            "season": season,
            "matches": [
                {**self._match_dict(r), "margin": int(r["margin"])}
                for _, r in df.iterrows()
            ],
        }

    def top_scoring_teams(
        self,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Teams ranked by total goals scored."""
        table = self.standings(competition or "Brasileirão", season)
        rows = table.get("table", [])
        rows = sorted(rows, key=lambda r: -r["goals_for"])[:limit]
        return {
            "competition": competition,
            "season": season,
            "teams": [
                {"team": r["team"], "goals_for": r["goals_for"],
                 "matches": r["matches"]}
                for r in rows
            ],
        }
