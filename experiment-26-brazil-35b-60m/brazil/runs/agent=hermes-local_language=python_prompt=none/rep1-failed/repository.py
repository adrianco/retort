"""
Repository layer for Brazilian Soccer MCP Server.
Provides query interfaces for matches, teams, players, and competitions.
"""

import re
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from data_loader import load_all_data, normalize_team_name


class SoccerRepository:
    """
    Query interface over loaded Brazilian soccer datasets.
    Provides methods for searching matches, teams, players, and competitions.
    """

    def __init__(self, data: Optional[Dict[str, pd.DataFrame]] = None):
        """Initialize with data dictionary from data_loader."""
        if data is None:
            data = load_all_data()
        self.data = data
        self.matches = data['matches']
        self.players = data['players']

    def search_matches(
        self,
        team: Optional[str] = None,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[str] = None,
        round_num: Optional[str] = None,
        stage: Optional[str] = None,
        min_score: Optional[int] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Search matches by various criteria.
        """
        df = self._get_matches_dataframe()
        mask = pd.Series([True] * len(df), index=df.index)

        def team_in_df(df_col, query_team):
            """Check if a team name (possibly normalized) is in a dataframe column."""
            norm = normalize_team_name(query_team)
            c1 = df_col.str.contains(re.escape(query_team), case=False, na=False)
            c2 = df_col.str.contains(re.escape(norm), case=False, na=False)
            c3 = df_col.str.contains(re.escape(norm.lower().replace(" ", "")), case=False, na=False)
            return c1 | c2 | c3

        # Filter by team (either home or away)
        if team:
            home_mask = team_in_df(df['home_team'], team)
            away_mask = team_in_df(df['away_team'], team)
            mask = mask & (home_mask | away_mask)

        # Filter by specific home team
        if home_team:
            mask = mask & team_in_df(df['home_team'], home_team)

        # Filter by specific away team
        if away_team:
            mask = mask & team_in_df(df['away_team'], away_team)

        # Filter by date range
        if date_from:
            mask = mask & (df['date'] >= date_from)
        if date_to:
            mask = mask & (df['date'] <= date_to)

        # Filter by competition
        if competition:
            comp_mask = df['competition'].str.contains(re.escape(competition), case=False, na=False)
            mask = mask & comp_mask

        # Filter by season
        if season:
            season_mask = df['season'].astype(str).str.contains(re.escape(str(season)), na=False)
            mask = mask & season_mask

        # Filter by round
        if round_num:
            round_mask = df['round'].astype(str).str.contains(re.escape(str(round_num)), na=False)
            mask = mask & round_mask

        # Filter by stage
        if stage:
            if 'stage' in df.columns:
                stage_mask = df['stage'].str.contains(re.escape(stage), case=False, na=False)
                mask = mask & stage_mask

        # Filter by minimum score
        if min_score is not None:
            total_goals = (df['home_goal'].fillna(0) + df['away_goal'].fillna(0)).astype(float)
            mask = mask & (total_goals >= min_score)

        # Filter by source
        if source:
            source_mask = df['source'] == source
            mask = mask & source_mask

        result = df[mask].copy()

        # Fill NaN goals with 0
        if "home_goal" in result.columns:
            result["home_goal"] = result["home_goal"].fillna(0)
        if "away_goal" in result.columns:
            result["away_goal"] = result["away_goal"].fillna(0)

        # Sort by date (most recent first) and limit
        if 'date' in result.columns:
            result = result.sort_values('date', ascending=False)
        result = result.head(limit)

        return result

    def get_team_stats(
        self,
        team: str,
        season: Optional[str] = None,
        competition: Optional[str] = None,
        source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate team statistics from match data.
        Returns dict with wins, losses, draws, goals for/against, etc.
        """
        df = self._get_matches_dataframe()
        team_norm = normalize_team_name(team)

        # Create mask for matches involving this team (both home and away)
        def team_involved(col):
            norm = normalize_team_name(team)
            c1 = col.str.contains(re.escape(team), case=False, na=False)
            c2 = col.str.contains(re.escape(norm), case=False, na=False)
            c3 = col.str.contains(re.escape(norm.lower().replace(" ", "")), case=False, na=False)
            return c1 | c2 | c3

        home_mask = team_involved(df['home_team'])
        away_mask = team_involved(df['away_team'])
        team_mask = home_mask | away_mask

        # Filter by season if specified
        if season:
            season_mask = df['season'].astype(str).str.contains(re.escape(str(season)), na=False)
            team_mask = team_mask & season_mask

        # Filter by competition if specified
        if competition:
            comp_mask = df['competition'].str.contains(re.escape(competition), case=False, na=False)
            team_mask = team_mask & comp_mask

        # Filter by source if specified
        if source:
            source_mask = df['source'] == source
            team_mask = team_mask & source_mask

        team_matches = df[team_mask]

        if len(team_matches) == 0:
            return {'team': team, 'matches': 0, 'error': 'No matches found for this team'}

        # Calculate stats for home matches only (team is home)
        home_matches_df = team_matches[home_mask & team_mask]
        # Calculate stats for away matches only (team is away)
        away_matches_df = team_matches[away_mask & team_mask]

        def calc_team_stats_from_matches(matches, team_is_home):
            """Calculate W/L/D and goals for a specific team perspective."""
            if len(matches) == 0:
                return {'matches': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'goals_for': 0, 'goals_against': 0}

            home_goals = matches['home_goal'].fillna(0).astype(float)
            away_goals = matches['away_goal'].fillna(0).astype(float)

            if team_is_home:
                goals_for = home_goals.sum()
                goals_against = away_goals.sum()
                wins = int((home_goals > away_goals).sum())
                draws = int((home_goals == away_goals).sum())
                losses = int((home_goals < away_goals).sum())
            else:
                # Team is away
                goals_for = away_goals.sum()
                goals_against = home_goals.sum()
                wins = int((away_goals > home_goals).sum())
                draws = int((away_goals == home_goals).sum())
                losses = int((away_goals < home_goals).sum())

            return {
                'matches': int(len(matches)),
                'wins': wins,
                'losses': losses,
                'draws': draws,
                'goals_for': int(goals_for),
                'goals_against': int(goals_against),
            }

        home_stats = calc_team_stats_from_matches(home_matches_df, team_is_home=True)
        away_stats = calc_team_stats_from_matches(away_matches_df, team_is_home=False)

        total_wins = home_stats['wins'] + away_stats['wins']
        total_draws = home_stats['draws'] + away_stats['draws']
        total_losses = home_stats['losses'] + away_stats['losses']
        total_matches_count = home_stats['matches'] + away_stats['matches']
        total_gf = home_stats['goals_for'] + away_stats['goals_for']
        total_ga = home_stats['goals_against'] + away_stats['goals_against']

        return {
            'team': team,
            'total': {
                'matches': total_matches_count,
                'wins': total_wins,
                'losses': total_losses,
                'draws': total_draws,
                'goals_for': total_gf,
                'goals_against': total_ga,
                'win_rate': round(total_wins / total_matches_count * 100, 1) if total_matches_count > 0 else 0,
            },
            'home': home_stats,
            'away': away_stats,
        }

    def get_head_to_head(self, team1, team2) -> Dict[str, Any]:
        """
        Calculate head-to-head statistics between two teams.
        """
        df = self._get_matches_dataframe()

        t1_norm = normalize_team_name(team1)
        t2_norm = normalize_team_name(team2)

        def team_match(col, name, norm_name):
            c1 = col.str.contains(re.escape(name), case=False, na=False)
            c2 = col.str.contains(re.escape(norm_name), case=False, na=False)
            c3 = col.str.contains(re.escape(norm_name.lower().replace(" ", "")), case=False, na=False)
            return c1 | c2 | c3

        # Matches where team1 is home vs team2 away, OR team2 is home vs team1 away
        h2h_mask = (
            (team_match(df['home_team'], team1, t1_norm) & team_match(df['away_team'], team2, t2_norm)) |
            (team_match(df['away_team'], team1, t1_norm) & team_match(df['home_team'], team2, t2_norm))
        )

        matches = df[h2h_mask].copy()

        if len(matches) == 0:
            return {'teams': [team1, team2], 'matches': 0, 'message': 'No matches found between these teams'}

        # Count wins for each team
        t1_wins = 0
        t2_wins = 0
        draws = 0

        for _, row in matches.iterrows():
            hg = float(row['home_goal']) if pd.notna(row['home_goal']) else 0
            ag = float(row['away_goal']) if pd.notna(row['away_goal']) else 0

            # Check if t1 is home
            ht = str(row['home_team'])
            t1_is_home = (
                team1.lower() in ht.lower() or
                t1_norm.lower() in ht.lower() or
                t1_norm.lower().replace(" ", "") in ht.lower()
            )

            if t1_is_home:
                if hg > ag:
                    t1_wins += 1
                elif ag > hg:
                    t2_wins += 1
                else:
                    draws += 1
            else:
                # t1 is away
                if ag > hg:
                    t1_wins += 1
                elif hg > ag:
                    t2_wins += 1
                else:
                    draws += 1

        return {
            'teams': [team1, team2],
            'total_matches': len(matches),
            f'{team1} wins': t1_wins,
            f'{team2} wins': t2_wins,
            'draws': draws,
            'matches': matches[['date', 'home_team', 'away_team', 'home_goal', 'away_goal', 'competition']].to_dict('records'),
        }

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        limit: int = 50
    ) -> pd.DataFrame:
        """
        Search FIFA player database.
        """
        df = self.players.copy()
        mask = pd.Series([True] * len(df), index=df.index)

        if name:
            name_mask = df['Name'].str.contains(re.escape(name), case=False, na=False)
            mask = mask & name_mask

        if nationality:
            nat_mask = df['Nationality'].str.contains(re.escape(nationality), case=False, na=False)
            mask = mask & nat_mask

        if club:
            club_mask = df['Club'].str.contains(re.escape(club), case=False, na=False)
            mask = mask & club_mask

        if position:
            pos_mask = df['Position'].str.contains(re.escape(position), case=False, na=False)
            mask = mask & pos_mask

        if min_overall is not None:
            mask = mask & (df['Overall'] >= min_overall)

        if max_overall is not None:
            mask = mask & (df['Overall'] <= max_overall)

        result = df[mask].copy()

        # Sort by overall rating descending and limit
        result = result.sort_values('Overall', ascending=False)
        result = result.head(limit)

        # Select key columns
        key_cols = ['Name', 'Age', 'Nationality', 'Overall', 'Potential', 'Club', 'Position']
        available_cols = [c for c in key_cols if c in result.columns]

        return result[available_cols]

    def get_top_scorers(
        self,
        season: Optional[str] = None,
        competition: Optional[str] = None,
        limit: int = 10
    ) -> pd.DataFrame:
        """
        Return top goal scorers (inferred from match data).
        This is a simplified calculation based on team goals.
        """
        df = self._get_matches_dataframe()

        if season:
            season_mask = df['season'].astype(str).str.contains(re.escape(str(season)), na=False)
            df = df[season_mask]

        if competition:
            comp_mask = df['competition'].str.contains(re.escape(competition), case=False, na=False)
            df = df[comp_mask]

        # Aggregate team goals
        team_goals = pd.DataFrame()
        team_goals['team'] = df['home_team'].tolist()
        team_goals['goals'] = df['home_goal'].fillna(0).astype(int).tolist()
        team_goals_comp = team_goals.copy()

        team_goals2 = pd.DataFrame()
        team_goals2['team'] = df['away_team'].tolist()
        team_goals2['goals'] = df['away_goal'].fillna(0).astype(int).tolist()
        team_goals2_comp = team_goals2.copy()

        all_team_goals = pd.concat([team_goals_comp, team_goals2_comp], ignore_index=True)
        team_totals = all_team_goals.groupby('team')['goals'].sum().sort_values(ascending=False)

        return team_totals.head(limit)

    def get_league_standings(
        self,
        season: str,
        competition: Optional[str] = None,
        source: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Calculate league standings from match results.
        Points: 3 for win, 1 for draw, 0 for loss.
        """
        df = self._get_matches_dataframe()

        # Filter by season
        season_mask = df['season'].astype(str).str.contains(re.escape(str(season)), na=False)
        df = df[season_mask]

        # Filter by competition/source
        if competition:
            comp_mask = df['competition'].str.contains(re.escape(competition), case=False, na=False)
            df = df[comp_mask]
        if source:
            source_mask = df['source'] == source
            df = df[source_mask]

        if len(df) == 0:
            return pd.DataFrame()

        # Get unique teams
        all_teams = set(df['home_team'].unique()) | set(df['away_team'].unique())

        standings = []
        for team in all_teams:
            home_matches = df[df['home_team'] == team]
            away_matches = df[df['away_team'] == team]

            wins = 0
            losses = 0
            draws = 0
            goals_for = 0
            goals_against = 0

            # Home matches (team is home)
            for _, row in home_matches.iterrows():
                hg = float(row['home_goal']) if pd.notna(row['home_goal']) else 0
                ag = float(row['away_goal']) if pd.notna(row['away_goal']) else 0
                goals_for += hg
                goals_against += ag
                if hg > ag:
                    wins += 1
                elif hg == ag:
                    draws += 1
                else:
                    losses += 1

            # Away matches (team is away)
            for _, row in away_matches.iterrows():
                hg = float(row['home_goal']) if pd.notna(row['home_goal']) else 0
                ag = float(row['away_goal']) if pd.notna(row['away_goal']) else 0
                goals_for += ag
                goals_against += hg
                if ag > hg:
                    wins += 1
                elif ag == hg:
                    draws += 1
                else:
                    losses += 1

            points = wins * 3 + draws
            standings.append({
                'team': team,
                'played': len(home_matches) + len(away_matches),
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'goals_for': goals_for,
                'goals_against': goals_against,
                'goal_difference': goals_for - goals_against,
                'points': points,
            })

        standings_df = pd.DataFrame(standings)
        standings_df = standings_df.sort_values(['points', 'goal_difference', 'goals_for'], ascending=False)
        standings_df.insert(0, 'position', range(1, len(standings_df) + 1))

        return standings_df

    def get_biggest_wins(
        self,
        limit: int = 10,
        competition: Optional[str] = None,
        source: Optional[str] = None
    ) -> pd.DataFrame:
        """Return the biggest wins/margins in the dataset."""
        df = self._get_matches_dataframe()

        if competition:
            comp_mask = df['competition'].str.contains(re.escape(competition), case=False, na=False)
            df = df[comp_mask]

        if source:
            source_mask = df['source'] == source
            df = df[source_mask]

        # Calculate goal margin
        df = df.copy()
        df['margin'] = (df['home_goal'].fillna(0).astype(float) - df['away_goal'].fillna(0).astype(float)).abs()

        result = df.sort_values('margin', ascending=False).head(limit)

        return result[['date', 'home_team', 'away_team', 'home_goal', 'away_goal', 'competition', 'margin']]

    def get_average_goals(
        self,
        competition: Optional[str] = None,
        source: Optional[str] = None,
        season: Optional[str] = None,
    ) -> Dict[str, float]:
        """Calculate average goals per match and home/away win rates."""
        df = self._get_matches_dataframe()

        if competition:
            comp_mask = df['competition'].str.contains(re.escape(competition), case=False, na=False)
            df = df[comp_mask]

        if source:
            source_mask = df['source'] == source
            df = df[source_mask]

        if season:
            season_mask = df['season'].astype(str).str.contains(re.escape(str(season)), na=False)
            df = df[season_mask]

        if len(df) == 0:
            return {'average_goals': 0, 'home_win_rate': 0, 'away_win_rate': 0, 'draw_rate': 0, 'total_matches': 0}

        total_goals = (df['home_goal'].fillna(0).astype(float) + df['away_goal'].fillna(0).astype(float)).sum()
        avg_goals = total_goals / len(df)

        home_wins = int((df['home_goal'].fillna(0).astype(float) > df['away_goal'].fillna(0).astype(float)).sum())
        away_wins = int((df['away_goal'].fillna(0).astype(float) > df['home_goal'].fillna(0).astype(float)).sum())
        draws = int((df['home_goal'].fillna(0).astype(float) == df['away_goal'].fillna(0).astype(float)).sum())

        return {
            'average_goals': round(float(avg_goals), 2),
            'home_win_rate': round(float(home_wins / len(df) * 100), 1),
            'away_win_rate': round(float(away_wins / len(df) * 100), 1),
            'draw_rate': round(float(draws / len(df) * 100), 1),
            'total_matches': int(len(df)),
        }

    def get_competitions(self) -> List[str]:
        """Return list of unique competitions in the dataset."""
        return sorted(self.matches['competition'].unique().tolist())

    def get_seasons(self, competition: Optional[str] = None) -> List[str]:
        """Return list of unique seasons."""
        if competition:
            comp_mask = self.matches['competition'].str.contains(re.escape(competition), case=False, na=False)
            seasons = self.matches[comp_mask]['season'].unique().tolist()
        else:
            seasons = self.matches['season'].unique().tolist()
        return sorted(seasons)

    def get_all_teams(self) -> List[str]:
        """Return list of all unique teams."""
        teams = set(self.matches['home_team'].unique()) | set(self.matches['away_team'].unique())
        return sorted([t for t in teams if t])

    def _get_matches_dataframe(self) -> pd.DataFrame:
        """Return the full matches dataframe."""
        return self.matches
