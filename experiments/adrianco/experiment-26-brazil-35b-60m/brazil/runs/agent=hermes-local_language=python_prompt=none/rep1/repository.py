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
        
        Args:
            team: Match includes this team (as home or away)
            home_team: Specific home team
            away_team: Specific away team
            date_from: Start date (ISO format YYYY-MM-DD)
            date_to: End date (ISO format YYYY-MM-DD)
            competition: Competition name
            season: Season year
            round_num: Round number
            stage: Tournament stage (e.g., 'group stage', 'Final')
            min_score: Minimum total goals in the match
            source: Specific source dataset
            limit: Maximum results to return
        """
        df = self._get_matches_dataframe()
        mask = pd.Series([True] * len(df), index=df.index)
        
        # Filter by team (either home or away)
        if team:
            team_norm = normalize_team_name(team)
            home_mask = df['home_team'].str.contains(re.escape(team), case=False, na=False) | \
                       df['home_team'].str.contains(re.escape(team_norm), case=False, na=False)
            away_mask = df['away_team'].str.contains(re.escape(team), case=False, na=False) | \
                       df['away_team'].str.contains(re.escape(team_norm), case=False, na=False)
            mask = mask & (home_mask | away_mask)
        
        # Filter by specific home team
        if home_team:
            ht_norm = normalize_team_name(home_team)
            home_mask = df['home_team'].str.contains(re.escape(home_team), case=False, na=False) | \
                       df['home_team'].str.contains(re.escape(ht_norm), case=False, na=False)
            mask = mask & home_mask
        
        # Filter by specific away team
        if away_team:
            at_norm = normalize_team_name(away_team)
            away_mask = df['away_team'].str.contains(re.escape(away_team), case=False, na=False) | \
                       df['away_team'].str.contains(re.escape(at_norm), case=False, na=False)
            mask = mask & away_mask
        
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
        
        # Create mask for matches involving this team
        home_mask = df['home_team'].str.contains(re.escape(team), case=False, na=False) | \
                   df['home_team'].str.contains(re.escape(team_norm), case=False, na=False)
        away_mask = df['away_team'].str.contains(re.escape(team), case=False, na=False) | \
                   df['away_team'].str.contains(re.escape(team_norm), case=False, na=False)
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
        
        # Calculate stats for home and away separately
        home_matches = team_matches[team_matches['home_team'].str.contains(re.escape(team), case=False, na=False) | 
                                   team_matches['home_team'].str.contains(re.escape(team_norm), case=False, na=False)]
        away_matches = team_matches[~home_mask & team_mask]
        
        def calc_match_stats(matches: pd.DataFrame) -> Dict[str, Any]:
            if len(matches) == 0:
                return {'matches': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'goals_for': 0, 'goals_against': 0}
            
            # Determine results from the team's perspective
            goals_for = matches['home_goal'].fillna(0).astype(float).sum()
            goals_against = matches['away_goal'].fillna(0).astype(float).sum()
            
            home_wins = (matches['home_goal'].fillna(0).astype(float) > matches['away_goal'].fillna(0).astype(float)).sum()
            home_draws = (matches['home_goal'].fillna(0).astype(float) == matches['away_goal'].fillna(0).astype(float)).sum()
            home_losses = (matches['home_goal'].fillna(0).astype(float) < matches['away_goal'].fillna(0).astype(float)).sum()
            
            # For away matches, flip the perspective
            if matches.columns.intersection(['home_goal', 'away_goal']).tolist():
                away_wins = (matches['away_goal'].fillna(0).astype(float) > matches['home_goal'].fillna(0).astype(float)).sum()
                away_draws = (matches['away_goal'].fillna(0).astype(float) == matches['home_goal'].fillna(0).astype(float)).sum()
                away_losses = (matches['away_goal'].fillna(0).astype(float) < matches['home_goal'].fillna(0).astype(float)).sum()
            
            wins = home_wins + away_wins if 'away_wins' in locals() else home_wins
            draws = home_draws + away_draws if 'away_draws' in locals() else home_draws
            losses = home_losses + away_losses if 'away_losses' in locals() else home_losses
            
            return {
                'matches': len(matches),
                'wins': int(wins),
                'losses': int(losses),
                'draws': int(draws),
                'goals_for': int(goals_for),
                'goals_against': int(goals_against),
                'win_rate': round(wins / len(matches) * 100, 1) if len(matches) > 0 else 0,
            }
        
        result = {
            'team': team,
            'total': calc_match_stats(team_matches),
            'home': calc_match_stats(home_matches),
            'away': calc_match_stats(away_matches) if len(away_matches) > 0 else calc_match_stats(home_matches),
        }
        
        return result
    
    def get_head_to_head(self, team1: str, team2: str) -> Dict[str, Any]:
        """
        Calculate head-to-head statistics between two teams.
        """
        df = self._get_matches_dataframe()
        
        # Find matches between the two teams
        t1_norm = normalize_team_name(team1)
        t2_norm = normalize_team_name(team2)
        
        matches = df[
            ((df['home_team'].str.contains(re.escape(team1), case=False, na=False) |
              df['home_team'].str.contains(re.escape(t1_norm), case=False, na=False)) &
             (df['away_team'].str.contains(re.escape(team2), case=False, na=False) |
              df['away_team'].str.contains(re.escape(t2_norm), case=False, na=False))) |
            ((df['away_team'].str.contains(re.escape(team1), case=False, na=False) |
              df['away_team'].str.contains(re.escape(t1_norm), case=False, na=False)) &
             (df['home_team'].str.contains(re.escape(team2), case=False, na=False) |
              df['home_team'].str.contains(re.escape(t2_norm), case=False, na=False)))
        ].copy()
        
        if len(matches) == 0:
            return {'teams': [team1, team2], 'matches': 0, 'message': 'No matches found between these teams'}
        
        # Count wins for each team
        t1_wins = 0
        t2_wins = 0
        draws = 0
        
        for _, row in matches.iterrows():
            hg = float(row['home_goal']) if pd.notna(row['home_goal']) else 0
            ag = float(row['away_goal']) if pd.notna(row['away_goal']) else 0
            
            # Check if t1 is home using simple string match
            ht = str(row['home_team'])
            t1_is_home = (team1.lower() in ht.lower() or t1_norm.lower() in ht.lower())
            
            if t1_is_home:
                if hg > ag:
                    t1_wins += 1
                elif ag > hg:
                    t2_wins += 1
                else:
                    draws += 1
            else:
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
        
        Args:
            name: Search player name (partial match)
            nationality: Filter by nationality
            club: Filter by club
            position: Filter by position
            min_overall: Minimum overall rating
            max_overall: Maximum overall rating
            limit: Maximum results
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
        Note: This is a simplified calculation based on team goals.
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
            home_mask = df['home_team'] == team
            away_mask = df['away_team'] == team
            
            # Home stats
            home_matches = df[home_mask]
            away_matches = df[away_mask]
            
            wins = 0
            losses = 0
            draws = 0
            goals_for = 0
            goals_against = 0
            
            # Home matches
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
            
            # Away matches
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
        
        home_wins = (df['home_goal'].fillna(0).astype(float) > df['away_goal'].fillna(0).astype(float)).sum()
        away_wins = (df['away_goal'].fillna(0).astype(float) > df['home_goal'].fillna(0).astype(float)).sum()
        draws = (df['home_goal'].fillna(0).astype(float) == df['away_goal'].fillna(0).astype(float)).sum()
        
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
