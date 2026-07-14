"""Query layer: answers the structured questions the MCP tools expose
(match search, team records, head-to-head, standings, player search,
statistical analysis) against a KnowledgeGraph.

Every method here returns plain data (DataFrames, dicts, floats) rather
than formatted text, so it can be unit tested directly; `formatting.py`
turns these results into the human-readable strings the MCP tools return.
"""

from __future__ import annotations

import pandas as pd

from .graph import KnowledgeGraph
from .normalize import normalize_key, parse_datetime, strip_accents

COMPETITION_ALIASES = {
    "brasileirao": "Brasileirao Serie A",
    "brasileirao serie a": "Brasileirao Serie A",
    "serie a": "Brasileirao Serie A",
    "campeonato brasileiro": "Brasileirao Serie A",
    "brasileirao serie b": "Brasileirao Serie B",
    "serie b": "Brasileirao Serie B",
    "brasileirao serie c": "Brasileirao Serie C",
    "serie c": "Brasileirao Serie C",
    "copa do brasil": "Copa do Brasil",
    "brazilian cup": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
}

CUP_STYLE_COMPETITIONS = {"Copa do Brasil", "Copa Libertadores"}

# Which source file to treat as authoritative for standings/champion
# calculations, so overlapping sources (e.g. Brasileirao_Matches.csv and
# novo_campeonato_brasileiro.csv both cover 2012-2019) don't double-count
# matches. Brasileirao Serie A is resolved per-season in _primary_source
# since its coverage is split across two files.
_FIXED_PRIMARY_SOURCE = {
    "Brasileirao Serie B": "BR-Football-Dataset",
    "Brasileirao Serie C": "BR-Football-Dataset",
    "Copa do Brasil": "Brazilian_Cup_Matches",
    "Copa Libertadores": "Libertadores_Matches",
}

POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"LB", "LCB", "CB", "RCB", "RB", "LWB", "RWB"},
    "midfielder": {"LDM", "CDM", "RDM", "LM", "LCM", "CM", "RCM", "RM", "LAM", "CAM", "RAM"},
    "forward": {"LW", "RW", "LF", "CF", "RF", "LS", "ST", "RS"},
}


def resolve_competition(name: str) -> str:
    """Map a user-supplied competition name (any casing/accents, e.g.
    "brasileirao", "Libertadores") onto its canonical form.
    """
    key = strip_accents(name).lower().strip()
    if key not in COMPETITION_ALIASES:
        raise ValueError(f"Unknown competition: {name!r}")
    return COMPETITION_ALIASES[key]


def _primary_source(competition: str, season: int) -> str:
    if competition == "Brasileirao Serie A":
        return "Brasileirao_Matches" if season >= 2012 else "novo_campeonato_brasileiro"
    return _FIXED_PRIMARY_SOURCE[competition]


class QueryEngine:
    """High-level, business-facing queries over a KnowledgeGraph."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    # -- Match queries ------------------------------------------------

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Find matches by team, opponent, competition, season and/or date
        range. Most recent matches are returned first.
        """
        df = self.graph.matches
        if team is not None:
            key = normalize_key(team)
            df = df[(df["home_team_key"] == key) | (df["away_team_key"] == key)]
        if opponent is not None:
            key = normalize_key(opponent)
            df = df[(df["home_team_key"] == key) | (df["away_team_key"] == key)]
        if competition is not None:
            df = df[df["competition"] == resolve_competition(competition)]
        if season is not None:
            df = df[df["season"] == season]
        if date_from is not None:
            df = df[df["datetime"] >= parse_datetime(date_from)]
        if date_to is not None:
            df = df[df["datetime"] <= parse_datetime(date_to)]
        # The same real-world match often appears in more than one source
        # file (e.g. Brasileirao_Matches.csv and BR-Football-Dataset.csv
        # both cover recent Serie A seasons); collapse those duplicates so
        # results read as one match, not two.
        df = df.drop_duplicates(subset=["date", "home_team_key", "away_team_key", "home_goal", "away_goal"])
        df = df.sort_values("datetime", ascending=False, na_position="last")
        return df.head(limit) if limit is not None else df

    def head_to_head(self, team_a: str, team_b: str, competition: str | None = None) -> dict:
        """Win/loss/draw record between two teams across all shared matches."""
        node_a = self.graph.resolve_team(team_a)
        node_b = self.graph.resolve_team(team_b)
        matches = self.search_matches(team=team_a, opponent=team_b, competition=competition)
        played = matches.dropna(subset=["home_goal", "away_goal"])

        is_a_home = played["home_team_key"] == node_a.key
        a_goals = played["home_goal"].where(is_a_home, played["away_goal"])
        b_goals = played["away_goal"].where(is_a_home, played["home_goal"])

        return {
            "team_a": node_a.display,
            "team_b": node_b.display,
            "matches": matches,
            "wins_a": int((a_goals > b_goals).sum()),
            "wins_b": int((a_goals < b_goals).sum()),
            "draws": int((a_goals == b_goals).sum()),
            "total": len(matches),
        }

    # -- Team queries ---------------------------------------------------

    def team_record(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str | None = None,
    ) -> dict:
        """Win/draw/loss and goal record for a team, optionally scoped to a
        season, competition, and/or venue ("home"/"away").
        """
        node = self.graph.resolve_team(team)
        df = self.graph.matches.iloc[node.match_indices]
        if season is not None:
            df = df[df["season"] == season]
        if competition is not None:
            df = df[df["competition"] == resolve_competition(competition)]
        if venue == "home":
            df = df[df["home_team_key"] == node.key]
        elif venue == "away":
            df = df[df["away_team_key"] == node.key]
        df = df.dropna(subset=["home_goal", "away_goal"])

        is_home = df["home_team_key"] == node.key
        team_goals = df["home_goal"].where(is_home, df["away_goal"])
        opp_goals = df["away_goal"].where(is_home, df["home_goal"])

        wins = int((team_goals > opp_goals).sum())
        draws = int((team_goals == opp_goals).sum())
        losses = int((team_goals < opp_goals).sum())
        played = wins + draws + losses
        goals_for = int(team_goals.sum())
        goals_against = int(opp_goals.sum())

        return {
            "team": node.display,
            "season": season,
            "competition": competition,
            "venue": venue,
            "played": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_diff": goals_for - goals_against,
            "win_rate": round(wins / played * 100, 1) if played else 0.0,
        }

    def compare_teams(
        self, team_a: str, team_b: str, season: int | None = None, competition: str | None = None
    ) -> dict:
        """Combine each team's overall record with their head-to-head history."""
        return {
            "team_a": self.team_record(team_a, season=season, competition=competition),
            "team_b": self.team_record(team_b, season=season, competition=competition),
            "head_to_head": self.head_to_head(team_a, team_b, competition=competition),
        }

    def top_scoring_teams(
        self, competition: str | None = None, season: int | None = None, n: int = 10
    ) -> pd.DataFrame:
        """Teams ranked by total goals scored (home + away)."""
        df = self._filtered_matches(competition, season).dropna(subset=["home_goal", "away_goal"])
        home = pd.DataFrame({"team_key": df["home_team_key"], "team": df["home_team"], "goals": df["home_goal"]})
        away = pd.DataFrame({"team_key": df["away_team_key"], "team": df["away_team"], "goals": df["away_goal"]})
        combined = pd.concat([home, away], ignore_index=True)
        grouped = combined.groupby(["team_key", "team"], as_index=False)["goals"].sum()
        grouped = grouped.sort_values("goals", ascending=False).head(n).reset_index(drop=True)
        return grouped.drop(columns=["team_key"])

    def team_competitions(self, team: str) -> set[str]:
        """Every competition a team has appeared in across all match sources."""
        return self.graph.team_competitions(team)

    # -- Player queries ---------------------------------------------------

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_age: int | None = None,
        limit: int | None = 50,
    ) -> pd.DataFrame:
        """Search the FIFA player database by name, nationality, club,
        position (either a FIFA code like "ST" or a group like "forward"),
        and/or minimum overall rating.
        """
        df = self.graph.players
        if name is not None:
            needle = strip_accents(name).lower().strip()
            haystack = df["name"].fillna("").map(lambda n: strip_accents(n).lower())
            df = df[haystack.str.contains(needle, na=False, regex=False)]
        if nationality is not None:
            nat = nationality.strip().lower()
            if nat in ("brazil", "brasil", "brazilian"):
                df = df[df["nationality"] == "Brazil"]
            else:
                df = df[df["nationality"].str.lower() == nat]
        if club is not None:
            df = df[df["club_key"] == normalize_key(club)]
        if position is not None:
            pos = position.strip().lower()
            if pos in POSITION_GROUPS:
                df = df[df["position"].isin(POSITION_GROUPS[pos])]
            else:
                df = df[df["position"].str.lower() == pos]
        if min_overall is not None:
            df = df[df["overall"] >= min_overall]
        if max_age is not None:
            df = df[df["age"] <= max_age]
        df = df.sort_values("overall", ascending=False, na_position="last")
        return df.head(limit) if limit is not None else df

    def top_rated_at_club(self, club: str, n: int = 10) -> pd.DataFrame:
        """Highest-overall-rated players at a given club."""
        players = self.graph.club_players(club)
        return players.sort_values("overall", ascending=False).head(n)

    def brazilian_players_by_club(self, limit: int | None = None) -> pd.DataFrame:
        """Count and average rating of Brazilian players at each Brazilian
        club that appears in both the match data and the FIFA player data.
        """
        players = self.graph.players
        club_keys = set(self.graph.all_team_keys())
        subset = players[(players["nationality"] == "Brazil") & (players["club_key"].isin(club_keys))]
        grouped = subset.groupby("club_key", as_index=False).agg(
            players=("player_id", "count"), avg_overall=("overall", "mean")
        )
        grouped["club"] = grouped["club_key"].map(self.graph.team_display)
        grouped["avg_overall"] = grouped["avg_overall"].round(1)
        grouped = grouped.sort_values("players", ascending=False).drop(columns=["club_key"])
        grouped = grouped[["club", "players", "avg_overall"]].reset_index(drop=True)
        return grouped.head(limit) if limit is not None else grouped

    # -- Competition queries ---------------------------------------------

    def standings(self, competition: str, season: int) -> pd.DataFrame:
        """League table (points, W/D/L, goals) calculated from match
        results, using one authoritative source per competition/season so
        overlapping datasets don't double-count matches.
        """
        competition = resolve_competition(competition)
        source = _primary_source(competition, season)
        df = self.graph.matches
        matches = df[
            (df["competition"] == competition) & (df["season"] == season) & (df["source"] == source)
        ].dropna(subset=["home_goal", "away_goal"])
        if matches.empty:
            raise ValueError(f"No {competition} match data for season {season}")

        home = pd.DataFrame({
            "team_key": matches["home_team_key"],
            "team": matches["home_team"],
            "goals_for": matches["home_goal"],
            "goals_against": matches["away_goal"],
            "win": matches["home_goal"] > matches["away_goal"],
            "draw": matches["home_goal"] == matches["away_goal"],
            "loss": matches["home_goal"] < matches["away_goal"],
        })
        away = pd.DataFrame({
            "team_key": matches["away_team_key"],
            "team": matches["away_team"],
            "goals_for": matches["away_goal"],
            "goals_against": matches["home_goal"],
            "win": matches["away_goal"] > matches["home_goal"],
            "draw": matches["away_goal"] == matches["home_goal"],
            "loss": matches["away_goal"] < matches["home_goal"],
        })
        combined = pd.concat([home, away], ignore_index=True)
        table = combined.groupby(["team_key", "team"], as_index=False).agg(
            played=("team_key", "size"),
            wins=("win", "sum"),
            draws=("draw", "sum"),
            losses=("loss", "sum"),
            goals_for=("goals_for", "sum"),
            goals_against=("goals_against", "sum"),
        )
        table["goal_diff"] = table["goals_for"] - table["goals_against"]
        table["points"] = table["wins"] * 3 + table["draws"]
        table = table.sort_values(
            ["points", "goal_diff", "goals_for"], ascending=False
        ).reset_index(drop=True)
        table.insert(0, "position", table.index + 1)
        return table.drop(columns=["team_key"])

    def champion(self, competition: str, season: int) -> dict:
        """The winner of a competition/season: top of the table for league
        competitions, or the aggregate final winner for knockout cups.
        """
        competition = resolve_competition(competition)
        if competition in CUP_STYLE_COMPETITIONS:
            return self._cup_champion(competition, season)
        table = self.standings(competition, season)
        top = table.iloc[0]
        return {
            "champion": top["team"],
            "season": season,
            "competition": competition,
            "standings_row": top.to_dict(),
        }

    def _cup_champion(self, competition: str, season: int) -> dict:
        source = _FIXED_PRIMARY_SOURCE[competition]
        df = self.graph.matches
        subset = df[
            (df["competition"] == competition) & (df["season"] == season) & (df["source"] == source)
        ].dropna(subset=["home_goal", "away_goal"])
        if subset.empty:
            raise ValueError(f"No {competition} match data for season {season}")

        if competition == "Copa Libertadores":
            final_matches = subset[subset["stage"] == "final"]
        else:
            round_numeric = pd.to_numeric(subset["round"], errors="coerce")
            final_matches = subset[round_numeric == round_numeric.max()]
        if final_matches.empty:
            raise ValueError(f"Could not identify a final for {competition} {season}")

        aggregate: dict[str, dict] = {}
        for _, row in final_matches.iterrows():
            for side, other in (("home", "away"), ("away", "home")):
                key = row[f"{side}_team_key"]
                entry = aggregate.setdefault(key, {"team": row[f"{side}_team"], "goals_for": 0, "goals_against": 0})
                entry["goals_for"] += int(row[f"{side}_goal"])
                entry["goals_against"] += int(row[f"{other}_goal"])

        ranked = sorted(aggregate.values(), key=lambda e: e["goals_for"] - e["goals_against"], reverse=True)
        winner = ranked[0]
        is_draw = len(ranked) > 1 and (
            winner["goals_for"] - winner["goals_against"]
            == ranked[1]["goals_for"] - ranked[1]["goals_against"]
        )
        return {
            "champion": None if is_draw else winner["team"],
            "season": season,
            "competition": competition,
            "final_matches": final_matches,
            "aggregate": ranked,
            "note": (
                "Final was level on aggregate; real-world tiebreakers (away goals, "
                "penalties) are not present in this dataset."
                if is_draw
                else None
            ),
        }

    def relegated_teams(self, competition: str, season: int, n: int = 4) -> pd.DataFrame:
        """Bottom `n` teams in a competition/season's standings."""
        table = self.standings(competition, season)
        return table.tail(n).reset_index(drop=True)

    # -- Statistical analysis ---------------------------------------------

    def _filtered_matches(self, competition: str | None = None, season: int | None = None) -> pd.DataFrame:
        df = self.graph.matches
        if competition is not None:
            df = df[df["competition"] == resolve_competition(competition)]
        if season is not None:
            df = df[df["season"] == season]
        return df

    def average_goals_per_match(self, competition: str | None = None, season: int | None = None) -> float:
        df = self._filtered_matches(competition, season).dropna(subset=["home_goal", "away_goal"])
        if df.empty:
            return 0.0
        return round(float((df["home_goal"] + df["away_goal"]).sum()) / len(df), 2)

    def home_win_rate(self, competition: str | None = None, season: int | None = None) -> float:
        df = self._filtered_matches(competition, season).dropna(subset=["home_goal", "away_goal"])
        if df.empty:
            return 0.0
        return round(float((df["home_goal"] > df["away_goal"]).mean()) * 100, 1)

    def best_away_record(
        self,
        competition: str | None = None,
        season: int | None = None,
        min_matches: int = 5,
        n: int = 5,
    ) -> pd.DataFrame:
        df = self._filtered_matches(competition, season).dropna(subset=["home_goal", "away_goal"])
        away = pd.DataFrame({
            "team_key": df["away_team_key"],
            "team": df["away_team"],
            "win": df["away_goal"] > df["home_goal"],
            "draw": df["away_goal"] == df["home_goal"],
        })
        table = away.groupby(["team_key", "team"], as_index=False).agg(
            played=("win", "size"), wins=("win", "sum"), draws=("draw", "sum")
        )
        table = table[table["played"] >= min_matches]
        table["win_rate"] = (table["wins"] / table["played"] * 100).round(1)
        table = table.sort_values("win_rate", ascending=False).head(n).reset_index(drop=True)
        return table.drop(columns=["team_key"])

    def biggest_wins(
        self, competition: str | None = None, season: int | None = None, n: int = 10
    ) -> pd.DataFrame:
        df = self._filtered_matches(competition, season).dropna(subset=["home_goal", "away_goal"]).copy()
        df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
        df = df.sort_values(["margin", "home_goal", "away_goal"], ascending=False).head(n)
        return df[
            ["date", "competition", "season", "home_team", "away_team", "home_goal", "away_goal", "margin"]
        ].reset_index(drop=True)
