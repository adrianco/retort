"""
================================================================================
Module: knowledge_graph.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
-------
The query engine for the Brazilian Soccer knowledge graph.  It wraps the two
unified DataFrames produced by :mod:`data_loader` and exposes the analytical
operations required by the specification (``brazilian-soccer-mcp-guide.md``):

    1. Match queries     - find_matches, head_to_head, last_meeting
    2. Team queries      - team_record, compare_teams
    3. Player queries    - search_players, get_player, brazilian_players_by_club
    4. Competition       - standings, top_scoring_teams, list_*
    5. Statistics        - average_goals, biggest_wins, home_advantage

We model the data conceptually as a knowledge graph:

    (Team) --[played]--> (Match) <--[played]-- (Team)
    (Match) --[in]--> (Competition, Season)
    (Player) --[plays_for]--> (Club/Team)
    (Player) --[from]--> (Nationality)

In practice the graph is backed by indexed pandas DataFrames for speed; the
methods below are the "edges" you traverse.  Every method returns plain Python
dicts / lists (never DataFrames) so the MCP server layer can format them without
knowing about pandas.

DEDUPLICATION
-------------
The Brasileirão Série A is covered by three overlapping sources.  For
standings / records we must count each fixture once, so :meth:`dedupe_matches`
keeps a single row per (competition, season, home_norm, away_norm, round)
fixture, preferring the most authoritative source for that competition.

All returned team names use the cleaned display form (accents kept, state
suffix dropped).  Returned structures are JSON-serialisable.
================================================================================
"""

from __future__ import annotations

import re
from typing import Any, Optional

import pandas as pd

from data_loader import Dataset, load_dataset
from normalization import normalize_team_name, strip_accents

# Global source preference for deduplication (lower rank = more authoritative).
# Dedicated single-competition files beat the broad BR-Football-Dataset, which
# uses fuller, harder-to-normalize team names ("Vasco Da Gama RJ" vs "Vasco").
_SOURCE_RANK = {
    "Brasileirao_Matches.csv": 0,         # Série A, 2012-2022
    "novo_campeonato_brasileiro.csv": 1,  # Série A, 2003-2019
    "Brazilian_Cup_Matches.csv": 0,       # Copa do Brasil
    "Libertadores_Matches.csv": 0,        # Copa Libertadores
    "BR-Football-Dataset.csv": 5,         # broad supplementary source
}


def _result(home_goal: Any, away_goal: Any) -> Optional[str]:
    """Return 'H', 'A', 'D' for the match result, or None if goals are missing."""
    if pd.isna(home_goal) or pd.isna(away_goal):
        return None
    if home_goal > away_goal:
        return "H"
    if away_goal > home_goal:
        return "A"
    return "D"


class KnowledgeGraph:
    """In-memory query engine over Brazilian soccer matches and players."""

    def __init__(self, dataset: Optional[Dataset] = None):
        self.dataset = dataset if dataset is not None else load_dataset()
        self.matches: pd.DataFrame = self.dataset.matches
        self.players: pd.DataFrame = self.dataset.players

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _team_mask(self, df: pd.DataFrame, query: str, side: str) -> pd.Series:
        """Boolean mask: does *query* match the team on *side* ('home'/'away')?

        Bidirectional whole-word match (see :func:`normalization.team_matches`):
        the query may appear inside the cell ("flamengo" in "flamengo rj") or the
        cell may be a sub-window of the query ("flamengo" cell vs "flamengo rj"
        query).  The reverse direction is handled by ``isin`` over the contiguous
        word-windows of the query, keeping the whole operation vectorised.
        """
        nq = normalize_team_name(query)
        col = df[f"{side}_norm"]
        if not nq:
            return pd.Series(False, index=df.index)
        forward = col.str.contains(rf"\b{nq}\b", regex=True, na=False)  # query in cell
        toks = nq.split()
        windows = {
            " ".join(toks[i:j])
            for i in range(len(toks))
            for j in range(i + 1, len(toks) + 1)
        }
        reverse = col.isin(windows)  # cell is a word-window of the query
        return forward | reverse

    @staticmethod
    def _name_matches(query_norm: str, cell_norm: str) -> bool:
        """Scalar version of :meth:`_team_mask` for a single normalized cell."""
        if not query_norm or not isinstance(cell_norm, str):
            return False
        if cell_norm == query_norm:
            return True
        return (
            re.search(rf"\b{query_norm}\b", cell_norm) is not None
            or re.search(rf"\b{re.escape(cell_norm)}\b", query_norm) is not None
        )

    def dedupe_matches(self, df: pd.DataFrame) -> pd.DataFrame:
        """Collapse overlapping sources by choosing ONE source per
        (competition, season).

        The Brasileirão Série A and Copa do Brasil are each described by more
        than one file with overlapping years.  Because the sources disagree on
        team spelling ("Vasco Da Gama RJ" vs "Vasco"), fixture-level dedup would
        leave phantom duplicate teams.  Instead, for every (competition, season)
        group we keep rows from a single source, chosen in this priority order:

          1. a *complete* round-robin season beats an incomplete one.  A league
             season is complete when ``played >= teams*(teams-1)`` (a double
             round-robin).  This is what protects against the BR-Football-Dataset
             grouping matches by *calendar year*: the COVID-delayed 2020 season
             spills into calendar 2021, inflating it to 24 teams / 491 games —
             that is NOT complete, so the clean 20-team / 380-game dedicated
             source wins;
          2. then most *played* matches — so when neither source is a clean full
             season (e.g. the mid-2022 capture), the fuller one wins;
          3. then lowest source rank — so on ties the dedicated, clean-named file
             beats the broad BR-Football-Dataset.

        Competitions with a single source pass through unchanged.
        """
        if df.empty:
            return df
        tmp = df.copy()

        # Summarise every (competition, season, source) group.  The group count
        # is small (~150), so the per-group team-set union is cheap.
        summary = []
        for (comp, season, source), g in tmp.groupby(
            ["competition", "season", "source"], dropna=False
        ):
            played = int((g["home_goal"].notna() & g["away_goal"].notna()).sum())
            teams = len(set(g["home_norm"]) | set(g["away_norm"]))
            expected = teams * (teams - 1) if teams > 1 else 0
            complete = expected > 0 and played >= expected
            rank = _SOURCE_RANK.get(source, 9)
            summary.append((comp, season, source, complete, played, rank))

        summ = pd.DataFrame(
            summary,
            columns=["competition", "season", "source", "complete", "played", "rank"],
        ).sort_values(
            ["competition", "season", "complete", "played", "rank"],
            ascending=[True, True, False, False, True],
        )
        chosen = summ.drop_duplicates(subset=["competition", "season"], keep="first")
        chosen_keys = set(zip(chosen["competition"], chosen["season"], chosen["source"]))

        keys = list(zip(tmp["competition"], tmp["season"], tmp["source"]))
        keep_mask = pd.Series([k in chosen_keys for k in keys], index=tmp.index)
        return tmp[keep_mask]

    @staticmethod
    def _match_to_dict(row) -> dict:
        """Convert a matches-DataFrame row to a JSON-serialisable dict."""
        date = row["date"]
        return {
            "competition": row["competition"],
            "season": int(row["season"]) if pd.notna(row["season"]) else None,
            "stage": None if pd.isna(row["stage"]) else str(row["stage"]),
            "date": None if pd.isna(date) else date.strftime("%Y-%m-%d"),
            "home_team": row["home_disp"],
            "away_team": row["away_disp"],
            "home_goal": int(row["home_goal"]) if pd.notna(row["home_goal"]) else None,
            "away_goal": int(row["away_goal"]) if pd.notna(row["away_goal"]) else None,
            "source": row["source"],
        }

    # ------------------------------------------------------------------ #
    # 1. Match queries
    # ------------------------------------------------------------------ #
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        dedupe: bool = True,
        limit: int = 50,
    ) -> list[dict]:
        """Find matches by any combination of criteria, newest first.

        * ``team``     - team played, home OR away
        * ``opponent`` - restrict ``team`` matches to ones against this opponent
        * ``home_team`` / ``away_team`` - team on a specific side
        * ``competition`` - canonical competition label (substring, accent-insensitive)
        * ``season``   - year
        * ``start_date`` / ``end_date`` - ISO ``YYYY-MM-DD`` bounds (inclusive)
        """
        df = self.matches
        mask = pd.Series(True, index=df.index)

        if team:
            mask &= self._team_mask(df, team, "home") | self._team_mask(df, team, "away")
        if opponent:
            mask &= self._team_mask(df, opponent, "home") | self._team_mask(df, opponent, "away")
        if home_team:
            mask &= self._team_mask(df, home_team, "home")
        if away_team:
            mask &= self._team_mask(df, away_team, "away")
        if competition:
            nc = strip_accents(competition).lower()
            comp_norm = df["competition"].map(lambda c: strip_accents(c).lower())
            mask &= comp_norm.str.contains(nc, regex=False, na=False)
        if season is not None:
            mask &= df["season"] == season
        if start_date:
            mask &= df["date"] >= pd.Timestamp(start_date)
        if end_date:
            mask &= df["date"] <= pd.Timestamp(end_date)

        result = df[mask]
        if dedupe:
            result = self.dedupe_matches(result)
        result = result.sort_values("date", ascending=False, na_position="last")
        rows = [self._match_to_dict(r) for _, r in result.head(limit).iterrows()]
        return rows

    def head_to_head(
        self,
        team1: str,
        team2: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        """Aggregate head-to-head record between two teams.

        Returns wins for each team, draws, goals, and the list of matches.
        """
        df = self.matches
        mask = (
            (self._team_mask(df, team1, "home") & self._team_mask(df, team2, "away"))
            | (self._team_mask(df, team1, "away") & self._team_mask(df, team2, "home"))
        )
        if competition:
            nc = strip_accents(competition).lower()
            mask &= df["competition"].map(lambda c: strip_accents(c).lower()).str.contains(nc, regex=False, na=False)
        if season is not None:
            mask &= df["season"] == season

        sub = self.dedupe_matches(df[mask]).sort_values("date", ascending=False, na_position="last")

        nq1 = normalize_team_name(team1)
        t1_wins = t2_wins = draws = t1_goals = t2_goals = 0
        for _, row in sub.iterrows():
            res = _result(row["home_goal"], row["away_goal"])
            if res is None:
                continue
            t1_home = self._name_matches(nq1, row["home_norm"])
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
            if t1_home:
                t1_goals += hg
                t2_goals += ag
                t1_wins += res == "H"
                t2_wins += res == "A"
            else:
                t1_goals += ag
                t2_goals += hg
                t1_wins += res == "A"
                t2_wins += res == "H"
            draws += res == "D"

        return {
            "team1": team1,
            "team2": team2,
            "total_matches": int(len(sub)),
            "team1_wins": int(t1_wins),
            "team2_wins": int(t2_wins),
            "draws": int(draws),
            "team1_goals": int(t1_goals),
            "team2_goals": int(t2_goals),
            "matches": [self._match_to_dict(r) for _, r in sub.iterrows()],
        }

    # ------------------------------------------------------------------ #
    # 2. Team queries
    # ------------------------------------------------------------------ #
    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",
    ) -> dict:
        """Win/draw/loss + goals record for a team.

        ``venue`` is one of 'all', 'home', 'away'.
        """
        df = self.matches
        if venue == "home":
            mask = self._team_mask(df, team, "home")
        elif venue == "away":
            mask = self._team_mask(df, team, "away")
        else:
            mask = self._team_mask(df, team, "home") | self._team_mask(df, team, "away")

        if competition:
            nc = strip_accents(competition).lower()
            mask &= df["competition"].map(lambda c: strip_accents(c).lower()).str.contains(nc, regex=False, na=False)
        if season is not None:
            mask &= df["season"] == season

        sub = self.dedupe_matches(df[mask])

        nq = normalize_team_name(team)
        wins = draws = losses = gf = ga = played = 0
        for _, row in sub.iterrows():
            res = _result(row["home_goal"], row["away_goal"])
            if res is None:
                continue
            played += 1
            is_home = self._name_matches(nq, row["home_norm"])
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
            if is_home:
                gf += hg
                ga += ag
                wins += res == "H"
                losses += res == "A"
            else:
                gf += ag
                ga += hg
                wins += res == "A"
                losses += res == "H"
            draws += res == "D"

        win_rate = round(100 * wins / played, 1) if played else 0.0
        return {
            "team": team,
            "season": season,
            "competition": competition,
            "venue": venue,
            "played": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": win_rate,
        }

    def compare_teams(self, team1: str, team2: str) -> dict:
        """Head-to-head plus each team's overall record."""
        return {
            "head_to_head": self.head_to_head(team1, team2),
            "team1_record": self.team_record(team1),
            "team2_record": self.team_record(team2),
        }

    # ------------------------------------------------------------------ #
    # 4. Competition queries
    # ------------------------------------------------------------------ #
    def standings(self, competition: str, season: int) -> list[dict]:
        """Compute a league table from match results.

        Standard 3-1-0 scoring, sorted by points, then goal difference, then
        goals scored.  Intended for round-robin competitions (Série A/B/C).
        """
        df = self.matches
        nc = strip_accents(competition).lower()
        mask = (
            df["competition"].map(lambda c: strip_accents(c).lower()).str.contains(nc, regex=False, na=False)
            & (df["season"] == season)
        )
        sub = self.dedupe_matches(df[mask])

        table: dict[str, dict] = {}

        def row_for(norm: str, disp: str) -> dict:
            if norm not in table:
                table[norm] = {
                    "team": disp, "played": 0, "wins": 0, "draws": 0,
                    "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0,
                }
            return table[norm]

        for _, m in sub.iterrows():
            res = _result(m["home_goal"], m["away_goal"])
            if res is None:
                continue
            hg, ag = int(m["home_goal"]), int(m["away_goal"])
            home = row_for(m["home_norm"], m["home_disp"])
            away = row_for(m["away_norm"], m["away_disp"])
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += hg
            home["goals_against"] += ag
            away["goals_for"] += ag
            away["goals_against"] += hg
            if res == "H":
                home["wins"] += 1
                away["losses"] += 1
                home["points"] += 3
            elif res == "A":
                away["wins"] += 1
                home["losses"] += 1
                away["points"] += 3
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        standings = list(table.values())
        for t in standings:
            t["goal_difference"] = t["goals_for"] - t["goals_against"]
        standings.sort(
            key=lambda t: (t["points"], t["goal_difference"], t["goals_for"]),
            reverse=True,
        )
        for i, t in enumerate(standings, 1):
            t["position"] = i
        return standings

    def champion(self, competition: str, season: int) -> Optional[dict]:
        """Return the top row of the standings (league champion)."""
        table = self.standings(competition, season)
        return table[0] if table else None

    def top_scoring_teams(self, competition: str, season: int, limit: int = 5) -> list[dict]:
        """Teams ranked by goals scored in a competition/season."""
        table = self.standings(competition, season)
        ranked = sorted(table, key=lambda t: t["goals_for"], reverse=True)
        return [
            {"team": t["team"], "goals_for": t["goals_for"], "played": t["played"]}
            for t in ranked[:limit]
        ]

    # ------------------------------------------------------------------ #
    # 5. Statistical analysis
    # ------------------------------------------------------------------ #
    def average_goals(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        """Average goals per match and home-win rate for a slice of the data."""
        df = self.matches
        mask = pd.Series(True, index=df.index)
        if competition:
            nc = strip_accents(competition).lower()
            mask &= df["competition"].map(lambda c: strip_accents(c).lower()).str.contains(nc, regex=False, na=False)
        if season is not None:
            mask &= df["season"] == season
        sub = self.dedupe_matches(df[mask])
        sub = sub[sub["home_goal"].notna() & sub["away_goal"].notna()]

        n = len(sub)
        if n == 0:
            return {"matches": 0, "avg_goals_per_match": 0.0,
                    "home_win_rate": 0.0, "draw_rate": 0.0, "away_win_rate": 0.0}
        total_goals = int((sub["home_goal"] + sub["away_goal"]).sum())
        home_wins = int((sub["home_goal"] > sub["away_goal"]).sum())
        away_wins = int((sub["home_goal"] < sub["away_goal"]).sum())
        draws = n - home_wins - away_wins
        return {
            "competition": competition,
            "season": season,
            "matches": n,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / n, 2),
            "home_win_rate": round(100 * home_wins / n, 1),
            "draw_rate": round(100 * draws / n, 1),
            "away_win_rate": round(100 * away_wins / n, 1),
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        team: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Matches with the largest goal margin, biggest first."""
        df = self.matches
        mask = df["home_goal"].notna() & df["away_goal"].notna()
        if competition:
            nc = strip_accents(competition).lower()
            mask &= df["competition"].map(lambda c: strip_accents(c).lower()).str.contains(nc, regex=False, na=False)
        if season is not None:
            mask &= df["season"] == season
        if team:
            mask &= self._team_mask(df, team, "home") | self._team_mask(df, team, "away")

        sub = self.dedupe_matches(df[mask]).copy()
        if sub.empty:
            return []
        sub["margin"] = (sub["home_goal"] - sub["away_goal"]).abs()
        sub = sub.sort_values(["margin", "date"], ascending=[False, False])
        out = []
        for _, row in sub.head(limit).iterrows():
            d = self._match_to_dict(row)
            d["margin"] = int(abs(int(row["home_goal"]) - int(row["away_goal"])))
            out.append(d)
        return out

    # ------------------------------------------------------------------ #
    # 3. Player queries
    # ------------------------------------------------------------------ #
    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort_by: str = "Overall",
        limit: int = 20,
    ) -> list[dict]:
        """Search the FIFA player database by any combination of filters."""
        df = self.players
        mask = pd.Series(True, index=df.index)
        if name:
            key = strip_accents(name).lower()
            mask &= df["name_lower"].str.contains(key, regex=False, na=False)
        if nationality:
            mask &= df["nationality_lower"] == nationality.lower()
        if club:
            nclub = normalize_team_name(club)
            mask &= df["club_norm"].str.contains(rf"\b{nclub}\b", regex=True, na=False)
        if position:
            mask &= df["Position"].fillna("").str.upper() == position.upper()
        if min_overall is not None:
            mask &= df["Overall"] >= min_overall

        sub = df[mask]
        if sort_by in sub.columns:
            sub = sub.sort_values(sort_by, ascending=False)
        return [self._player_to_dict(r) for _, r in sub.head(limit).iterrows()]

    def get_player(self, name: str) -> Optional[dict]:
        """Return the single best-rated player matching *name*."""
        results = self.search_players(name=name, limit=1)
        return results[0] if results else None

    def brazilian_players_by_club(self, limit: int = 20) -> list[dict]:
        """Summarise Brazilian players grouped by their club.

        Returns clubs ordered by number of Brazilian players, with the average
        FIFA Overall rating for each.
        """
        df = self.players
        braz = df[(df["nationality_lower"] == "brazil") & df["Club"].notna()]
        grouped = (
            braz.groupby("Club")
            .agg(players=("Name", "count"), avg_overall=("Overall", "mean"))
            .reset_index()
            .sort_values("players", ascending=False)
        )
        out = []
        for _, row in grouped.head(limit).iterrows():
            out.append({
                "club": row["Club"],
                "players": int(row["players"]),
                "avg_overall": round(float(row["avg_overall"]), 1),
            })
        return out

    @staticmethod
    def _player_to_dict(row) -> dict:
        def val(col):
            return None if col not in row or pd.isna(row[col]) else row[col]

        overall = val("Overall")
        return {
            "name": val("Name"),
            "age": int(row["Age"]) if pd.notna(row.get("Age")) else None,
            "nationality": val("Nationality"),
            "overall": int(overall) if overall is not None else None,
            "potential": int(row["Potential"]) if pd.notna(row.get("Potential")) else None,
            "club": val("Club"),
            "position": val("Position"),
            "value": val("Value"),
        }

    # ------------------------------------------------------------------ #
    # Discovery helpers
    # ------------------------------------------------------------------ #
    def list_competitions(self) -> list[str]:
        return sorted(self.matches["competition"].dropna().unique().tolist())

    def list_seasons(self, competition: Optional[str] = None) -> list[int]:
        df = self.matches
        if competition:
            nc = strip_accents(competition).lower()
            df = df[df["competition"].map(lambda c: strip_accents(c).lower()).str.contains(nc, regex=False, na=False)]
        seasons = sorted(int(s) for s in df["season"].dropna().unique())
        return seasons

    def list_teams(self, competition: Optional[str] = None, season: Optional[int] = None) -> list[str]:
        df = self.matches
        if competition:
            nc = strip_accents(competition).lower()
            df = df[df["competition"].map(lambda c: strip_accents(c).lower()).str.contains(nc, regex=False, na=False)]
        if season is not None:
            df = df[df["season"] == season]
        # Dedupe sources so we list each team once with its canonical spelling,
        # rather than every cross-source variant ("Atletico-MG" vs "Atletico Mineiro").
        df = self.dedupe_matches(df)
        names = pd.concat([df["home_disp"], df["away_disp"]]).dropna().unique().tolist()
        return sorted(names)
