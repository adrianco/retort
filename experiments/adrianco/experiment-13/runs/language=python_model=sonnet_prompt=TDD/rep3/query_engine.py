"""Query engine for Brazilian soccer data."""
import re
import unicodedata
import pandas as pd
from data_loader import DataLoader, normalize_team_name


def _ascii_fold(s: str) -> str:
    """Lowercase and strip accents for fuzzy team matching."""
    return unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()


def _match_competition(comp_col_value: str, query: str) -> bool:
    """Case-insensitive, accent-insensitive competition match."""
    return _ascii_fold(str(comp_col_value)).startswith(_ascii_fold(query[:10]))


def _team_matches(norm_name: str, query: str) -> bool:
    """Check if a normalized team name matches a query (case/accent-insensitive)."""
    return _ascii_fold(query) in _ascii_fold(str(norm_name))


class QueryEngine:
    def __init__(self, loader: DataLoader):
        self._loader = loader

    # ─── Match queries ────────────────────────────────────────────────────────

    def find_matches(
        self,
        team: str | None = None,
        team2: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Find matches with optional filters. Returns list of match dicts."""
        df = self._loader.all_matches.copy()

        if team:
            mask_home = df["home_team_norm"].apply(lambda n: _team_matches(n, team))
            mask_away = df["away_team_norm"].apply(lambda n: _team_matches(n, team))
            df = df[mask_home | mask_away]

        if team2:
            mask_home2 = df["home_team_norm"].apply(lambda n: _team_matches(n, team2))
            mask_away2 = df["away_team_norm"].apply(lambda n: _team_matches(n, team2))
            df = df[mask_home2 | mask_away2]

        if competition:
            df = df[df["competition"].apply(lambda c: _match_competition(c, competition))]

        if season is not None:
            df = df[df["season"] == season]

        if limit:
            df = df.head(limit)

        return df.to_dict(orient="records")

    # ─── Team statistics ─────────────────────────────────────────────────────

    def team_stats(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
    ) -> dict:
        """Return win/draw/loss record and goal tally for a team."""
        matches = self.find_matches(team=team, season=season, competition=competition)
        if not matches:
            return {
                "team": team, "total": 0, "wins": 0, "draws": 0, "losses": 0,
                "home_wins": 0, "away_wins": 0,
                "goals_scored": 0, "goals_conceded": 0,
            }

        wins = draws = losses = 0
        home_wins = away_wins = 0
        goals_scored = goals_conceded = 0

        for m in matches:
            try:
                hg = int(m["home_goal"])
                ag = int(m["away_goal"])
            except (TypeError, ValueError):
                continue
            is_home = _team_matches(str(m.get("home_team_norm", "")), team)
            if is_home:
                gs, gc = hg, ag
            else:
                gs, gc = ag, hg
            goals_scored += gs
            goals_conceded += gc
            if gs > gc:
                wins += 1
                if is_home:
                    home_wins += 1
                else:
                    away_wins += 1
            elif gs == gc:
                draws += 1
            else:
                losses += 1

        return {
            "team": team,
            "total": wins + draws + losses,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
        }

    # ─── Head-to-head ─────────────────────────────────────────────────────────

    def head_to_head(self, team1: str, team2: str) -> dict:
        """Head-to-head record between two teams."""
        matches = self.find_matches(team=team1, team2=team2)
        team1_wins = team2_wins = draws = 0
        for m in matches:
            try:
                hg = int(m["home_goal"])
                ag = int(m["away_goal"])
            except (TypeError, ValueError):
                continue
            t1_home = _team_matches(str(m.get("home_team_norm", "")), team1)
            if t1_home:
                gs1, gs2 = hg, ag
            else:
                gs1, gs2 = ag, hg
            if gs1 > gs2:
                team1_wins += 1
            elif gs1 < gs2:
                team2_wins += 1
            else:
                draws += 1
        return {
            "team1": team1,
            "team2": team2,
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "draws": draws,
            "total": team1_wins + team2_wins + draws,
        }

    # ─── Player queries ───────────────────────────────────────────────────────

    def find_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        sort_by: str = "Overall",
        limit: int | None = None,
    ) -> list[dict]:
        """Search FIFA player data."""
        df = self._loader.fifa.copy()

        if name:
            df = df[df["Name"].str.contains(name, case=False, na=False)]
        if nationality:
            df = df[df["Nationality"].str.lower() == nationality.lower()]
        if club:
            df = df[df["Club"].str.contains(club, case=False, na=False)]

        if sort_by and sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=False)

        if limit:
            df = df.head(limit)

        keep = [c for c in ("Name", "Age", "Nationality", "Overall", "Potential",
                             "Club", "Position", "Jersey Number") if c in df.columns]
        return df[keep].to_dict(orient="records")

    # ─── Season standings ─────────────────────────────────────────────────────

    def season_standings(self, season: int, competition: str) -> list[dict]:
        """Calculate league table for a given season and competition."""
        matches = self.find_matches(season=season, competition=competition)
        table: dict[str, dict] = {}

        for m in matches:
            try:
                hg = int(m["home_goal"])
                ag = int(m["away_goal"])
            except (TypeError, ValueError):
                continue
            home = str(m.get("home_team_norm", ""))
            away = str(m.get("away_team_norm", ""))
            for team in (home, away):
                if team and team not in table:
                    table[team] = {
                        "team": team, "played": 0, "wins": 0, "draws": 0,
                        "losses": 0, "goals_for": 0, "goals_against": 0,
                    }

            if home and away:
                table[home]["played"] += 1
                table[away]["played"] += 1
                table[home]["goals_for"] += hg
                table[home]["goals_against"] += ag
                table[away]["goals_for"] += ag
                table[away]["goals_against"] += hg

                if hg > ag:
                    table[home]["wins"] += 1
                    table[away]["losses"] += 1
                elif hg < ag:
                    table[away]["wins"] += 1
                    table[home]["losses"] += 1
                else:
                    table[home]["draws"] += 1
                    table[away]["draws"] += 1

        result = []
        for entry in table.values():
            entry["points"] = entry["wins"] * 3 + entry["draws"]
            entry["goal_diff"] = entry["goals_for"] - entry["goals_against"]
            result.append(entry)

        result.sort(key=lambda x: (x["points"], x["goal_diff"], x["goals_for"]), reverse=True)
        return result

    # ─── Statistical analysis ─────────────────────────────────────────────────

    def biggest_wins(
        self,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Return matches sorted by goal difference (biggest wins first)."""
        matches = self.find_matches(competition=competition, season=season)
        for m in matches:
            try:
                m["_margin"] = abs(int(m["home_goal"]) - int(m["away_goal"]))
            except (TypeError, ValueError):
                m["_margin"] = 0
        matches.sort(key=lambda m: m["_margin"], reverse=True)
        # Remove the temp key
        for m in matches:
            m.pop("_margin", None)
        return matches[:limit]

    def average_goals_per_match(self, competition: str | None = None) -> float:
        """Average total goals per match."""
        matches = self.find_matches(competition=competition)
        totals = []
        for m in matches:
            try:
                totals.append(int(m["home_goal"]) + int(m["away_goal"]))
            except (TypeError, ValueError):
                pass
        return round(sum(totals) / len(totals), 4) if totals else 0.0

    def home_win_rate(self, competition: str | None = None) -> float:
        """Fraction of matches won by the home team."""
        matches = self.find_matches(competition=competition)
        home_wins = total = 0
        for m in matches:
            try:
                hg = int(m["home_goal"])
                ag = int(m["away_goal"])
            except (TypeError, ValueError):
                continue
            total += 1
            if hg > ag:
                home_wins += 1
        return round(home_wins / total, 4) if total else 0.0

    def top_scoring_teams(
        self,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Teams sorted by total goals scored."""
        matches = self.find_matches(competition=competition, season=season)
        goals: dict[str, int] = {}
        for m in matches:
            try:
                hg = int(m["home_goal"])
                ag = int(m["away_goal"])
            except (TypeError, ValueError):
                continue
            home = str(m.get("home_team_norm", ""))
            away = str(m.get("away_team_norm", ""))
            if home:
                goals[home] = goals.get(home, 0) + hg
            if away:
                goals[away] = goals.get(away, 0) + ag
        ranked = sorted(goals.items(), key=lambda x: x[1], reverse=True)
        return [{"team": t, "goals": g} for t, g in ranked[:limit]]
