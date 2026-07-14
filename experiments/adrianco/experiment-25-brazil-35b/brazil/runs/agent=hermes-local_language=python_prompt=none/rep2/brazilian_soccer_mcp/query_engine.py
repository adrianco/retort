"""Query engine for Brazilian soccer data.

Provides structured query methods for:
- Match queries (find matches by criteria)
- Team queries (team statistics, head-to-head)
- Player queries (search, filter, ratings)
- Competition queries (standings, top scorers)
- Statistical analysis (aggregated stats)
"""

from datetime import datetime
from typing import Any, Optional

import pandas as pd

from .data_loader import get_match_data, get_player_data, normalize_team_name


class QueryEngine:
    """Handles all query logic over the Brazilian soccer datasets."""

    def __init__(self, match_data=None, player_data=None):
        if match_data is not None:
            self.matches = match_data
        else:
            self.matches = get_match_data()
        if player_data is not None:
            self.players = player_data
        else:
            self.players = get_player_data()

    # -------------------------------------------------------------------------
    # MATCH QUERIES
    # -------------------------------------------------------------------------

    def find_matches_by_team(self, team, competition=None, season=None,
                             date_from=None, date_to=None, limit=100):
        """Find all matches involving a given team."""
        team_norm = normalize_team_name(team)
        df = self._filter_matches(team_norm, competition, season, date_from, date_to)

        results = []
        for _, row in df.head(limit).iterrows():
            is_home = row["home_team"] == team_norm
            results.append({
                "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else None,
                "season": int(row["season"]) if pd.notna(row["season"]) else None,
                "round": int(row["round"]) if pd.notna(row["round"]) else None,
                "competition": row["competition"],
                "home_team": row["home_team"],
                "home_goal": int(row["home_goal"]) if pd.notna(row["home_goal"]) else None,
                "away_team": row["away_team"],
                "away_goal": int(row["away_goal"]) if pd.notna(row["away_goal"]) else None,
                "is_home": is_home,
                "is_away": not is_home,
            })
        return results

    def find_matches_between_teams(self, team_a, team_b, competition=None, limit=100):
        """Find head-to-head matches between two teams."""
        team_a_norm = normalize_team_name(team_a)
        team_b_norm = normalize_team_name(team_b)

        df_a_home = self.matches[self.matches["home_team"] == team_a_norm].copy()
        df_a_away = self.matches[self.matches["away_team"] == team_a_norm].copy()
        df_b_home = self.matches[self.matches["home_team"] == team_b_norm].copy()
        df_b_away = self.matches[self.matches["away_team"] == team_b_norm].copy()

        between_a = df_a_home[df_a_home["away_team"] == team_b_norm].copy()
        between_a["is_home"] = True
        between_b = df_a_away[df_a_away["away_team"] == team_b_norm].copy()
        between_b["is_home"] = False
        between_b2 = df_b_home[df_b_home["away_team"] == team_a_norm].copy()
        between_b2["is_home"] = True
        between_b3 = df_b_away[df_b_away["away_team"] == team_a_norm].copy()
        between_b3["is_home"] = False

        all_h2h = pd.concat([between_a, between_b, between_b2, between_b3], ignore_index=True)
        all_h2h = all_h2h.drop_duplicates(subset=["date", "home_team", "away_team"])

        if competition:
            all_h2h = all_h2h[all_h2h["competition"].str.lower() == competition.lower()]
        all_h2h = all_h2h.sort_values("date")

        results = []
        for _, row in all_h2h.head(limit).iterrows():
            results.append({
                "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else None,
                "season": int(row["season"]) if pd.notna(row["season"]) else None,
                "round": int(row["round"]) if pd.notna(row["round"]) else None,
                "competition": row["competition"],
                "home_team": row["home_team"],
                "home_goal": int(row["home_goal"]) if pd.notna(row["home_goal"]) else None,
                "away_team": row["away_team"],
                "away_goal": int(row["away_goal"]) if pd.notna(row["away_goal"]) else None,
                "is_home": row["is_home"],
            })

        wins_a = 0
        wins_b = 0
        draws = 0
        for _, row in all_h2h.iterrows():
            hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else None
            ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else None
            if hg is not None and ag is not None:
                if row["home_team"] == team_a_norm:
                    if hg > ag:
                        wins_a += 1
                    elif hg < ag:
                        wins_b += 1
                    else:
                        draws += 1
                else:
                    if ag > hg:
                        wins_a += 1
                    elif ag < hg:
                        wins_b += 1
                    else:
                        draws += 1

        return {
            "matches": results,
            "head_to_head": {
                f"{team_a} wins": wins_a,
                f"{team_b} wins": wins_b,
                "draws": draws,
            }
        }

    def find_latest_match(self, team_a, team_b, competition=None):
        """Find the most recent match between two teams."""
        h2h = self.find_matches_between_teams(team_a, team_b, competition)
        matches = h2h["matches"]
        if matches:
            return matches[0]
        return None

    def find_copa_do_brasil_final(self, season=None):
        """Find Copa do Brasil final matches."""
        df = self.matches[self.matches["competition"].str.lower().str.contains("copa")]
        if season:
            df = df[df["season"] == season]
        df = df.sort_values(["season", "round"], ascending=[True, False])

        final_matches = []
        for season_val in df["season"].unique():
            season_df = df[df["season"] == season_val]
            if len(season_df) > 0:
                final_match = season_df.sort_values("round", ascending=False).iloc[0]
                season_val = int(final_match["season"]) if pd.notna(final_match["season"]) else None
                round_val = int(final_match["round"]) if pd.notna(final_match["round"]) else None
                final_matches.append({
                    "date": final_match["date"].strftime("%Y-%m-%d") if pd.notna(final_match["date"]) else None,
                    "season": season_val,
                    "round": round_val,
                    "competition": final_match["competition"],
                    "home_team": final_match["home_team"],
                    "home_goal": int(final_match["home_goal"]) if pd.notna(final_match["home_goal"]) else None,
                    "away_team": final_match["away_team"],
                    "away_goal": int(final_match["away_goal"]) if pd.notna(final_match["away_goal"]) else None,
                })
        return final_matches

    # -------------------------------------------------------------------------
    # TEAM QUERIES
    # -------------------------------------------------------------------------

    def get_team_statistics(self, team, competition=None, season=None,
                            date_from=None, date_to=None):
        """Calculate comprehensive team statistics."""
        team_norm = normalize_team_name(team)
        df = self._filter_matches(team_norm, competition, season, date_from, date_to)

        if df.empty:
            return None

        home_wins = 0
        away_wins = 0
        home_losses = 0
        away_losses = 0
        draws = 0
        goals_for = 0
        goals_against = 0
        total_matches = 0

        for _, row in df.iterrows():
            hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else None
            ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else None
            if hg is None or ag is None:
                continue

            total_matches += 1
            is_home = row["home_team"] == team_norm
            if is_home:
                goals_for += hg
                goals_against += ag
                if hg > ag:
                    home_wins += 1
                elif hg < ag:
                    home_losses += 1
                else:
                    draws += 1
            else:
                goals_for += ag
                goals_against += hg
                if ag > hg:
                    away_wins += 1
                elif ag < hg:
                    away_losses += 1
                else:
                    draws += 1

        total_wins = home_wins + away_wins
        total_losses = home_losses + away_losses
        win_rate = (total_wins / total_matches * 100) if total_matches > 0 else 0

        home_df = df[df["home_team"] == team_norm]
        away_df = df[df["away_team"] == team_norm]

        home_wins_count = 0
        home_draws = 0
        home_losses_count = 0
        home_goals_for = 0
        home_goals_against = 0
        for _, row in home_df.iterrows():
            hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else None
            ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else None
            if hg is not None and ag is not None:
                home_goals_for += hg
                home_goals_against += ag
                if hg > ag:
                    home_wins_count += 1
                elif hg < ag:
                    home_losses_count += 1
                else:
                    home_draws += 1

        away_wins_count = 0
        away_draws = 0
        away_losses_count = 0
        away_goals_for = 0
        away_goals_against = 0
        for _, row in away_df.iterrows():
            hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else None
            ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else None
            if hg is not None and ag is not None:
                away_goals_for += ag
                away_goals_against += hg
                if ag > hg:
                    away_wins_count += 1
                elif ag < hg:
                    away_losses_count += 1
                else:
                    away_draws += 1

        comp_breakdown = {}
        for comp in df["competition"].unique():
            comp_df = df[df["competition"] == comp]
            comp_wins = 0
            comp_draws = 0
            comp_losses = 0
            comp_gf = 0
            comp_ga = 0
            for _, row in comp_df.iterrows():
                hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else None
                ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else None
                if hg is None or ag is None:
                    continue
                is_home = row["home_team"] == team_norm
                if is_home:
                    comp_gf += hg
                    comp_ga += ag
                else:
                    comp_gf += ag
                    comp_ga += hg
                if is_home:
                    if hg > ag:
                        comp_wins += 1
                    elif hg < ag:
                        comp_losses += 1
                    else:
                        comp_draws += 1
                else:
                    if ag > hg:
                        comp_wins += 1
                    elif ag < hg:
                        comp_losses += 1
                    else:
                        comp_draws += 1
            comp_breakdown[comp] = {
                "matches": len(comp_df),
                "wins": comp_wins,
                "draws": comp_draws,
                "losses": comp_losses,
                "goals_for": comp_gf,
                "goals_against": comp_ga,
            }

        return {
            "team": team_norm,
            "total_matches": total_matches,
            "wins": total_wins,
            "draws": draws,
            "losses": total_losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_difference": goals_for - goals_against,
            "win_rate": round(win_rate, 1),
            "home_record": {
                "matches": len(home_df),
                "wins": home_wins_count,
                "draws": home_draws,
                "losses": home_losses_count,
                "goals_for": home_goals_for,
                "goals_against": home_goals_against,
            },
            "away_record": {
                "matches": len(away_df),
                "wins": away_wins_count,
                "draws": away_draws,
                "losses": away_losses_count,
                "goals_for": away_goals_for,
                "goals_against": away_goals_against,
            },
            "competition_breakdown": comp_breakdown,
        }

    def top_scorers_by_team(self, team, season=None, competition=None, limit=10):
        """Get top scoring matches for a team."""
        team_norm = normalize_team_name(team)
        df = self._filter_matches(team_norm, competition, season)
        if df.empty:
            return []

        matches_scores = []
        for _, row in df.iterrows():
            hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else None
            ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else None
            if hg is None or ag is None:
                continue
            is_home = row["home_team"] == team_norm
            team_goals = hg if is_home else ag
            opp_goals = ag if is_home else hg
            matches_scores.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "competition": row["competition"],
                "opponent": row["away_team"] if is_home else row["home_team"],
                "team_goals": team_goals,
                "opponent_goals": opp_goals,
                "result": "W" if team_goals > opp_goals else ("D" if team_goals == opp_goals else "L"),
                "margin": abs(team_goals - opp_goals),
            })
        return sorted(matches_scores, key=lambda x: x["margin"], reverse=True)[:limit]

    # -------------------------------------------------------------------------
    # PLAYER QUERIES
    # -------------------------------------------------------------------------

    def search_player(self, name, limit=10):
        """Search for players by name (case-insensitive partial match)."""
        mask = self.players["Name"].str.contains(name, case=False, na=False)
        results = self.players[mask].head(limit)
        return results.apply(
            lambda r: {
                "name": r["Name"],
                "age": int(r["Age"]) if pd.notna(r["Age"]) else None,
                "nationality": r["Nationality"],
                "overall": int(r["Overall"]) if pd.notna(r["Overall"]) else None,
                "potential": int(r["Potential"]) if pd.notna(r["Potential"]) else None,
                "club": r["Club"],
                "position": r["Position"],
                "jersey_number": int(r["Jersey Number"]) if pd.notna(r.get("Jersey Number")) else None,
            },
            axis=1,
        ).tolist()

    def get_players_by_nationality(self, nationality, min_overall=None, limit=50):
        """Get players filtered by nationality."""
        mask = self.players["Nationality"].str.contains(nationality, case=False, na=False)
        if min_overall:
            mask = mask & (self.players["Overall"] >= min_overall)
        results = self.players[mask].sort_values("Overall", ascending=False).head(limit)
        return results.apply(
            lambda r: {
                "name": r["Name"],
                "age": int(r["Age"]) if pd.notna(r["Age"]) else None,
                "nationality": r["Nationality"],
                "overall": int(r["Overall"]) if pd.notna(r["Overall"]) else None,
                "potential": int(r["Potential"]) if pd.notna(r["Potential"]) else None,
                "club": r["Club"],
                "position": r["Position"],
            },
            axis=1,
        ).tolist()

    def get_players_by_club(self, club, min_overall=None, position=None, limit=50):
        """Get players filtered by club."""
        mask = self.players["Club"].str.contains(club, case=False, na=False)
        if min_overall:
            mask = mask & (self.players["Overall"] >= min_overall)
        if position:
            mask = mask & (self.players["Position"].str.contains(position, case=False, na=False))
        results = self.players[mask].sort_values("Overall", ascending=False).head(limit)
        return results.apply(
            lambda r: {
                "name": r["Name"],
                "age": int(r["Age"]) if pd.notna(r["Age"]) else None,
                "nationality": r["Nationality"],
                "overall": int(r["Overall"]) if pd.notna(r["Overall"]) else None,
                "potential": int(r["Potential"]) if pd.notna(r["Potential"]) else None,
                "club": r["Club"],
                "position": r["Position"],
                "jersey_number": int(r["Jersey Number"]) if pd.notna(r.get("Jersey Number")) else None,
            },
            axis=1,
        ).tolist()

    def get_brazilian_players_by_brazilian_club(self, min_overall=None, limit=100):
        """Get Brazilian players playing at Brazilian clubs."""
        brazilian_clubs_mask = (
            self.players["Club"].str.contains(
                "flamengo|palmeiras|santos|corinthians|sao paulo|"
                "atletico|cruzeiro|internacional|gremio|fluminense|"
                "vasco|botafogo|bahia|fortaleza|ceara|sport|vitoria|"
                "coritiba|goias|athletico|bota|juventude|"
                "red bull|novorizontino|crb|cuiaba|sampaio|chapecoense",
                case=False, na=False
            )
        )
        brazilian_clubs = self.players[brazilian_clubs_mask]
        if min_overall:
            brazilian_clubs = brazilian_clubs[brazilian_clubs["Overall"] >= min_overall]
        brazilian_players = brazilian_clubs[
            brazilian_clubs["Nationality"].str.contains("Brazil", case=False, na=False)
        ]
        if limit:
            brazilian_players = brazilian_players.head(limit)
        return brazilian_players.apply(
            lambda r: {
                "name": r["Name"],
                "age": int(r["Age"]) if pd.notna(r["Age"]) else None,
                "nationality": r["Nationality"],
                "overall": int(r["Overall"]) if pd.notna(r["Overall"]) else None,
                "potential": int(r["Potential"]) if pd.notna(r["Potential"]) else None,
                "club": r["Club"],
                "position": r["Position"],
            },
            axis=1,
        ).tolist()

    def get_brazilian_club_summary(self):
        """Get summary of Brazilian players at Brazilian clubs."""
        brazilian_clubs_mask = (
            self.players["Club"].str.contains(
                "flamengo|palmeiras|santos|corinthians|sao paulo|"
                "atletico|cruzeiro|internacional|gremio|fluminense|"
                "vasco|botafogo|bahia|fortaleza|ceara|sport|vitoria|"
                "coritiba|goias|athletico|bota|juventude|"
                "red bull|novorizontino|crb|cuiaba|sampaio|chapecoense",
                case=False, na=False
            )
        )
        brazilian_clubs = self.players[brazilian_clubs_mask]
        brazilian_players = brazilian_clubs[
            brazilian_clubs["Nationality"].str.contains("Brazil", case=False, na=False)
        ]

        summary = brazilian_players.groupby("Club").agg(
            count=("Overall", "count"),
            avg_overall=("Overall", "mean"),
            max_overall=("Overall", "max"),
            min_overall=("Overall", "min"),
        ).reset_index()
        summary = summary.sort_values("count", ascending=False)
        return summary.apply(
            lambda r: {
                "club": r["Club"],
                "brazilian_players": int(r["count"]),
                "avg_rating": round(r["avg_overall"], 1),
                "max_rating": int(r["max_overall"]),
                "min_rating": int(r["min_overall"]),
            },
            axis=1,
        ).tolist()

    # -------------------------------------------------------------------------
    # COMPETITION QUERIES
    # -------------------------------------------------------------------------

    def get_standings(self, competition, season):
        """Calculate standings for a competition/season based on match results."""
        df = self.matches[
            (self.matches["competition"].str.lower() == competition.lower()) &
            (self.matches["season"] == season)
        ]
        if df.empty:
            return []

        teams = set()
        for _, row in df.iterrows():
            teams.add(row["home_team"])
            teams.add(row["away_team"])

        standings = {}
        for team in teams:
            standings[team] = {
                "team": team,
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "goal_difference": 0,
                "points": 0,
            }

        for _, row in df.iterrows():
            hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else None
            ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else None
            if hg is None or ag is None:
                continue
            home = row["home_team"]
            away = row["away_team"]
            standings[home]["played"] += 1
            standings[away]["played"] += 1
            standings[home]["goals_for"] += hg
            standings[home]["goals_against"] += ag
            standings[away]["goals_for"] += ag
            standings[away]["goals_against"] += hg
            if hg > ag:
                standings[home]["wins"] += 1
                standings[home]["points"] += 3
                standings[away]["losses"] += 1
            elif hg < ag:
                standings[away]["wins"] += 1
                standings[away]["points"] += 3
                standings[home]["losses"] += 1
            else:
                standings[home]["draws"] += 1
                standings[away]["draws"] += 1
                standings[home]["points"] += 1
                standings[away]["points"] += 1

        for team in standings:
            standings[team]["goal_difference"] = (
                standings[team]["goals_for"] - standings[team]["goals_against"]
            )

        result = sorted(
            standings.values(),
            key=lambda x: (-x["points"], -x["goal_difference"], -x["goals_for"]),
        )
        for i, r in enumerate(result):
            r["position"] = i + 1
        return result

    def get_champion(self, competition, season):
        """Get the champion of a competition/season."""
        standings = self.get_standings(competition, season)
        if standings:
            champion = standings[0].copy()
            champion["is_champion"] = True
            return champion
        return None

    # -------------------------------------------------------------------------
    # STATISTICAL ANALYSIS
    # -------------------------------------------------------------------------

    def get_average_goals_per_match(self, competition=None, season=None):
        """Calculate average goals per match."""
        df = self.matches.copy()
        if competition:
            df = df[df["competition"].str.lower() == competition.lower()]
        if season:
            df = df[df["season"] == season]
        valid = df.dropna(subset=["home_goal", "away_goal"])
        if valid.empty:
            return {"average_goals": 0, "total_matches": 0}

        total_goals = valid["home_goal"].sum() + valid["away_goal"].sum()
        total_matches = len(valid)
        avg_goals = total_goals / total_matches if total_matches > 0 else 0
        home_goals = valid["home_goal"].sum()
        away_goals = valid["away_goal"].sum()
        home_avg = home_goals / total_matches
        away_avg = away_goals / total_matches

        home_wins = len(valid[valid["home_goal"] > valid["away_goal"]])
        draws = len(valid[valid["home_goal"] == valid["away_goal"]])
        home_win_rate = home_wins / total_matches * 100
        draw_rate = draws / total_matches * 100
        away_win_rate = (total_matches - home_wins - draws) / total_matches * 100

        return {
            "competition": competition or "All",
            "season": season or "All",
            "average_goals": round(avg_goals, 2),
            "home_goals_avg": round(home_avg, 2),
            "away_goals_avg": round(away_avg, 2),
            "home_win_rate": round(home_win_rate, 1),
            "draw_rate": round(draw_rate, 1),
            "away_win_rate": round(away_win_rate, 1),
            "total_matches": total_matches,
        }

    def get_biggest_wins(self, competition=None, limit=10):
        """Get the biggest goal margin wins."""
        df = self.matches.copy()
        if competition:
            df = df[df["competition"].str.lower() == competition.lower()]
        df = df.dropna(subset=["home_goal", "away_goal"]).copy()
        df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
        df = df.sort_values("margin", ascending=False)

        results = []
        for _, row in df.head(limit).iterrows():
            margin = int(row["margin"])
            winner = row["home_team"] if row["home_goal"] > row["away_goal"] else row["away_team"]
            loser = row["away_team"] if row["home_goal"] > row["away_goal"] else row["home_team"]
            results.append({
                "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else None,
                "competition": row["competition"],
                "home_team": row["home_team"],
                "home_goal": int(row["home_goal"]),
                "away_team": row["away_team"],
                "away_goal": int(row["away_goal"]),
                "margin": margin,
                "winner": winner,
                "loser": loser,
            })
        return results

    def get_team_performance_trend(self, team, competition=None, season=None, period="season"):
        """Get team performance trend over time."""
        team_norm = normalize_team_name(team)
        df = self._filter_matches(team_norm, competition, season)
        if df.empty:
            return []

        group_col = "season" if period == "season" else "round"
        trend = []
        for group_val, group_df in df.groupby(group_col):
            team_gf = 0
            team_ga = 0
            wins = 0
            draws = 0
            losses = 0
            matches = 0
            for _, row in group_df.iterrows():
                hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else None
                ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else None
                if hg is None or ag is None:
                    continue
                matches += 1
                is_home = row["home_team"] == team_norm
                team_goals = hg if is_home else ag
                opp_goals = ag if is_home else hg
                team_gf += team_goals
                team_ga += opp_goals
                if team_goals > opp_goals:
                    wins += 1
                elif team_goals == opp_goals:
                    draws += 1
                else:
                    losses += 1

            trend.append({
                period: group_val,
                "matches": matches,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "goals_for": team_gf,
                "goals_against": team_ga,
                "points": wins * 3 + draws,
                "win_rate": round(wins / matches * 100, 1) if matches > 0 else 0,
            })
        return trend

    def get_best_away_record(self, competition=None, season=None, limit=10):
        """Find teams with the best away records."""
        df = self.matches.copy()
        if competition:
            df = df[df["competition"].str.lower() == competition.lower()]
        if season:
            df = df[df["season"] == season]

        away_stats = {}
        for _, row in df.iterrows():
            hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else None
            ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else None
            if hg is None or ag is None:
                continue
            away_team = row["away_team"]
            if away_team not in away_stats:
                away_stats[away_team] = {
                    "team": away_team,
                    "matches": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                }
            away_stats[away_team]["matches"] += 1
            away_stats[away_team]["goals_for"] += ag
            away_stats[away_team]["goals_against"] += hg
            if ag > hg:
                away_stats[away_team]["wins"] += 1
            elif ag == hg:
                away_stats[away_team]["draws"] += 1
            else:
                away_stats[away_team]["losses"] += 1

        result = sorted(
            away_stats.values(),
            key=lambda x: (-x["wins"], x["goals_against"]),
        )[:limit]
        for r in result:
            r["win_rate"] = round(r["wins"] / r["matches"] * 100, 1) if r["matches"] > 0 else 0
        return result

    def get_competitions_for_team(self, team):
        """Find all competitions a team has played in."""
        team_norm = normalize_team_name(team)
        df = self.matches[
            (self.matches["home_team"] == team_norm) |
            (self.matches["away_team"] == team_norm)
        ]
        if df.empty:
            return []

        competitions = {}
        for comp in df["competition"].unique():
            comp_df = df[df["competition"] == comp]
            seasons = sorted(comp_df["season"].dropna().unique().tolist())
            competitions[comp] = {
                "competition": comp,
                "matches": len(comp_df),
                "seasons": [int(s) for s in seasons if pd.notna(s)],
                "years_span": f"{min(seasons)}-{max(seasons)}" if seasons else None,
            }
        return sorted(competitions.values(), key=lambda x: x["matches"], reverse=True)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _filter_matches(self, team, competition=None, season=None, date_from=None, date_to=None):
        """Internal helper to filter match data for a team."""
        df = self.matches[
            (self.matches["home_team"] == team) |
            (self.matches["away_team"] == team)
        ]
        if competition:
            df = df[df["competition"].str.lower() == competition.lower()]
        if season:
            df = df[df["season"] == season]
        if date_from:
            df = df[df["date"] >= pd.Timestamp(date_from)]
        if date_to:
            df = df[df["date"] <= pd.Timestamp(date_to)]
        return df
