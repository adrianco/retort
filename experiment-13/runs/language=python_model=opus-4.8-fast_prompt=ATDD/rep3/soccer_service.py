"""
Domain service for the Brazilian Soccer MCP server.

This layer turns the normalized pandas tables held by ``SoccerRepository`` into
plain-Python answer dictionaries in the language of the problem domain:
matches, team records, head-to-head comparisons, player searches, league
standings and competition statistics.

The MCP server (``server.py``) is a thin adapter that exposes each method here
as an MCP tool; keeping the logic in this provider makes it directly unit
testable and free of protocol concerns.
"""

from __future__ import annotations

import pandas as pd

from soccer_data import SoccerRepository
from team_names import normalize_team


def _round_label(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text or None


class SoccerService:
    def __init__(self, repository: SoccerRepository | None = None):
        self.repo = repository or SoccerRepository.default()

    # ------------------------------------------------------------------ #
    # Match queries                                                       #
    # ------------------------------------------------------------------ #
    def find_matches(
        self,
        team=None,
        opponent=None,
        competition=None,
        season=None,
        start_date=None,
        end_date=None,
        limit=50,
    ):
        df = self.repo.matches
        mask = pd.Series(True, index=df.index)

        if team:
            key = normalize_team(team)
            involves = (df["home_key"] == key) | (df["away_key"] == key)
            if opponent:
                okey = normalize_team(opponent)
                involves &= (df["home_key"] == okey) | (df["away_key"] == okey)
            mask &= involves
        elif opponent:
            okey = normalize_team(opponent)
            mask &= (df["home_key"] == okey) | (df["away_key"] == okey)

        if competition:
            mask &= df["competition"].str.lower() == competition.strip().lower()
        if season is not None:
            mask &= df["season"] == int(season)
        if start_date:
            mask &= df["date"] >= str(start_date)
        if end_date:
            mask &= df["date"] <= str(end_date)

        found = df[mask].sort_values("date", ascending=False, na_position="last")
        total = len(found)
        rows = [self._match_dict(r) for _, r in found.head(limit).iterrows()]

        head_to_head = None
        if team and opponent:
            head_to_head = self._head_to_head(found, normalize_team(team), team, opponent)

        return {
            "count": total,
            "returned": len(rows),
            "matches": rows,
            "head_to_head": head_to_head,
        }

    def _match_dict(self, r):
        return {
            "date": None if pd.isna(r["date"]) else r["date"],
            "competition": r["competition"],
            "season": int(r["season"]),
            "round": _round_label(r["round"]),
            "home_team": r["home_team"],
            "away_team": r["away_team"],
            "home_goal": int(r["home_goal"]),
            "away_goal": int(r["away_goal"]),
            "score": f"{int(r['home_goal'])}-{int(r['away_goal'])}",
        }

    def _head_to_head(self, found, team_a_key, team_a_label, team_b_label):
        a_wins = b_wins = draws = a_goals = b_goals = 0
        for _, r in found.iterrows():
            home_is_a = r["home_key"] == team_a_key
            a_g = r["home_goal"] if home_is_a else r["away_goal"]
            b_g = r["away_goal"] if home_is_a else r["home_goal"]
            a_goals += int(a_g)
            b_goals += int(b_g)
            if a_g > b_g:
                a_wins += 1
            elif a_g < b_g:
                b_wins += 1
            else:
                draws += 1
        return {
            "team_a": team_a_label,
            "team_b": team_b_label,
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
            "total": a_wins + b_wins + draws,
        }

    # ------------------------------------------------------------------ #
    # Team queries                                                        #
    # ------------------------------------------------------------------ #
    def get_team_record(self, team, season=None, competition=None, venue="all"):
        key = normalize_team(team)
        df = self.repo.matches
        if season is not None:
            df = df[df["season"] == int(season)]
        if competition:
            df = df[df["competition"].str.lower() == competition.strip().lower()]

        venue = (venue or "all").lower()
        if venue == "home":
            df = df[df["home_key"] == key]
        elif venue == "away":
            df = df[df["away_key"] == key]
        else:
            df = df[(df["home_key"] == key) | (df["away_key"] == key)]

        wins = draws = losses = gf = ga = 0
        for _, r in df.iterrows():
            home = r["home_key"] == key
            scored = r["home_goal"] if home else r["away_goal"]
            conceded = r["away_goal"] if home else r["home_goal"]
            gf += int(scored)
            ga += int(conceded)
            if scored > conceded:
                wins += 1
            elif scored < conceded:
                losses += 1
            else:
                draws += 1

        played = wins + draws + losses
        win_rate = round(100.0 * wins / played, 1) if played else 0.0
        return {
            "team": team,
            "season": int(season) if season is not None else None,
            "competition": competition,
            "venue": venue,
            "matches": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": win_rate,
        }

    def compare_teams(self, team_a, team_b, season=None, competition=None):
        result = self.find_matches(
            team=team_a,
            opponent=team_b,
            season=season,
            competition=competition,
            limit=1000,
        )
        h2h = result["head_to_head"] or {
            "team_a_wins": 0,
            "team_b_wins": 0,
            "draws": 0,
            "team_a_goals": 0,
            "team_b_goals": 0,
        }
        return {
            "team_a": team_a,
            "team_b": team_b,
            "total_matches": result["count"],
            "team_a_wins": h2h["team_a_wins"],
            "team_b_wins": h2h["team_b_wins"],
            "draws": h2h["draws"],
            "team_a_goals": h2h["team_a_goals"],
            "team_b_goals": h2h["team_b_goals"],
            "matches": result["matches"],
        }

    def list_team_competitions(self, team):
        key = normalize_team(team)
        df = self.repo.matches
        df = df[(df["home_key"] == key) | (df["away_key"] == key)]
        competitions = []
        for name, group in df.groupby("competition"):
            seasons = sorted(int(s) for s in group["season"].unique())
            competitions.append(
                {
                    "competition": name,
                    "matches": len(group),
                    "seasons": seasons,
                    "first_season": seasons[0] if seasons else None,
                    "last_season": seasons[-1] if seasons else None,
                }
            )
        competitions.sort(key=lambda c: c["matches"], reverse=True)
        return {"team": team, "competitions": competitions}

    # ------------------------------------------------------------------ #
    # Player queries                                                      #
    # ------------------------------------------------------------------ #
    def search_players(
        self, name=None, nationality=None, club=None, position=None, limit=10
    ):
        df = self.repo.players
        mask = pd.Series(True, index=df.index)
        if name:
            mask &= df["name"].str.contains(name, case=False, na=False, regex=False)
        if nationality:
            mask &= df["nationality"].str.lower() == nationality.strip().lower()
        if club:
            ckey = normalize_team(club)
            mask &= df["club_key"] == ckey
        if position:
            mask &= df["position"].str.upper() == position.strip().upper()

        found = df[mask].sort_values("overall", ascending=False)
        total = len(found)
        players = [self._player_dict(r) for _, r in found.head(limit).iterrows()]
        return {"count": total, "returned": len(players), "players": players}

    def _player_dict(self, r):
        return {
            "name": r["name"],
            "age": int(r["age"]),
            "nationality": r["nationality"],
            "overall": int(r["overall"]),
            "potential": int(r["potential"]),
            "position": r["position"],
            "club": r["club"],
        }

    # ------------------------------------------------------------------ #
    # Competition queries                                                 #
    # ------------------------------------------------------------------ #
    def get_standings(self, season, competition="Brasileirão", limit=20):
        df = self.repo.matches
        df = df[
            (df["season"] == int(season))
            & (df["competition"].str.lower() == competition.strip().lower())
        ]

        stats = {}

        def row(team_display):
            return stats.setdefault(
                team_display,
                {
                    "team": team_display,
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "points": 0,
                },
            )

        # Use the canonical key to merge name variants, but display the most
        # frequent label seen for each team.
        labels = self._canonical_labels(df)

        for _, r in df.iterrows():
            home = row(labels[r["home_key"]])
            away = row(labels[r["away_key"]])
            hg, ag = int(r["home_goal"]), int(r["away_goal"])
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += hg
            home["goals_against"] += ag
            away["goals_for"] += ag
            away["goals_against"] += hg
            if hg > ag:
                home["wins"] += 1
                away["losses"] += 1
                home["points"] += 3
            elif hg < ag:
                away["wins"] += 1
                home["losses"] += 1
                away["points"] += 3
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        # Brazilian league tie-break order: points, then wins, then goal
        # difference, then goals scored.
        table = sorted(
            stats.values(),
            key=lambda t: (
                t["points"],
                t["wins"],
                t["goals_for"] - t["goals_against"],
                t["goals_for"],
            ),
            reverse=True,
        )
        for i, t in enumerate(table, start=1):
            t["position"] = i
            t["goal_difference"] = t["goals_for"] - t["goals_against"]

        table = table[:limit]
        return {
            "season": int(season),
            "competition": competition,
            "champion": table[0]["team"] if table else None,
            "table": table,
        }

    def _canonical_labels(self, df):
        """Map each team key to its most common display name in ``df``."""
        labels = {}
        counts = {}
        for _, r in df.iterrows():
            for key, label in ((r["home_key"], r["home_team"]), (r["away_key"], r["away_team"])):
                c = counts.setdefault(key, {})
                c[label] = c.get(label, 0) + 1
        for key, label_counts in counts.items():
            labels[key] = max(label_counts.items(), key=lambda kv: kv[1])[0]
        return labels

    # ------------------------------------------------------------------ #
    # Statistical analysis                                                #
    # ------------------------------------------------------------------ #
    def get_competition_summary(self, competition=None, season=None, top_n=10):
        df = self.repo.matches
        if competition:
            df = df[df["competition"].str.lower() == competition.strip().lower()]
        if season is not None:
            df = df[df["season"] == int(season)]

        matches = len(df)
        if matches == 0:
            return {
                "competition": competition,
                "season": int(season) if season is not None else None,
                "matches": 0,
                "total_goals": 0,
                "avg_goals_per_match": 0.0,
                "home_wins": 0,
                "away_wins": 0,
                "draws": 0,
                "home_win_rate": 0.0,
                "biggest_wins": [],
            }

        hg = df["home_goal"].astype(int)
        ag = df["away_goal"].astype(int)
        total_goals = int((hg + ag).sum())
        home_wins = int((hg > ag).sum())
        away_wins = int((hg < ag).sum())
        draws = int((hg == ag).sum())

        biggest = df.assign(margin=(hg - ag).abs()).sort_values(
            ["margin", "date"], ascending=[False, False]
        ).head(top_n)
        biggest_wins = []
        for _, r in biggest.iterrows():
            d = self._match_dict(r)
            d["margin"] = abs(d["home_goal"] - d["away_goal"])
            biggest_wins.append(d)

        return {
            "competition": competition,
            "season": int(season) if season is not None else None,
            "matches": matches,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / matches, 2),
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(100.0 * home_wins / matches, 1),
            "biggest_wins": biggest_wins,
        }

    # ------------------------------------------------------------------ #
    # Cross-file query                                                    #
    # ------------------------------------------------------------------ #
    def get_team_profile(self, team):
        record = self.get_team_record(team)
        squad = self.search_players(club=team, limit=30)
        avg = (
            round(sum(p["overall"] for p in squad["players"]) / len(squad["players"]), 1)
            if squad["players"]
            else 0.0
        )
        return {
            "team": team,
            "record": record,
            "competitions": self.list_team_competitions(team)["competitions"],
            "squad": {
                "club": team,
                "player_count": squad["count"],
                "average_overall": avg,
                "players": squad["players"],
            },
        }
