"""Brazilian Soccer MCP Server - Match Queries."""

from typing import Dict, List, Optional, Tuple
from soccer_data import SoccerDataLoader, get_loader
import pandas as pd


class MatchQueryEngine:
    """Engine for querying match data across all datasets."""
    
    def __init__(self, loader: Optional[SoccerDataLoader] = None):
        """Initialize with a data loader."""
        self.loader = loader or get_loader()
        self.data = self.loader.load_all()
    
    def find_matches(
        self,
        team1: Optional[str] = None,
        team2: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_range: Optional[Tuple[str, str]] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Find matches matching the given criteria."""
        results = []
        
        # Combine all match dataframes
        all_matches = []
        for key in ['brasileirao', 'copa_brasil', 'libertadores', 'br_football', 'novo_campeonato']:
            if key in self.data:
                df = self.data[key].copy()
                df['source'] = key
                all_matches.append(df)
        
        if not all_matches:
            return []
        
        combined = pd.concat(all_matches, ignore_index=True)
        
        # Apply filters
        if team1:
            team1_norm = self.loader._normalize_team_name(team1)
            combined = combined[
                (combined['home_team_normalized'] == team1_norm) |
                (combined['away_team_normalized'] == team1_norm)
            ]
        
        if team2:
            team2_norm = self.loader._normalize_team_name(team2)
            combined = combined[
                (combined['home_team_normalized'] == team2_norm) |
                (combined['away_team_normalized'] == team2_norm)
            ]
        
        if competition:
            # Normalize competition name
            comp_norm = competition.lower()
            combined = combined[combined['competition'].str.lower() == comp_norm]
        
        if season:
            combined = combined[combined['season'] == season]
        
        if date_range:
            start_date, end_date = date_range
            combined = combined[
                (combined['datetime'] >= start_date) &
                (combined['datetime'] <= end_date)
            ]
        
        # Sort by date (most recent first) and limit
        if not combined.empty:
            combined = combined.sort_values('datetime', ascending=False).head(limit)
        
        for _, row in combined.iterrows():
            # Handle NaN values properly - use home_team/home and away_team/away
            # based on which has valid data
            if 'home_team' in row and not pd.isna(row['home_team']):
                home_team = row['home_team']
            elif 'home' in row and not pd.isna(row['home']):
                home_team = row['home']
            else:
                home_team = 'N/A'
            
            if 'away_team' in row and not pd.isna(row['away_team']):
                away_team = row['away_team']
            elif 'away' in row and not pd.isna(row['away']):
                away_team = row['away']
            else:
                away_team = 'N/A'
            
            competition_val = row.get('competition')
            if competition_val is None or pd.isna(competition_val):
                competition_val = 'Unknown'
            
            result = {
                'date': str(row['datetime'].date()) if pd.notna(row['datetime']) else None,
                'home_team': str(home_team),
                'away_team': str(away_team),
                'home_goal': int(row['home_goal']) if pd.notna(row['home_goal']) else None,
                'away_goal': int(row['away_goal']) if pd.notna(row['away_goal']) else None,
                'competition': str(competition_val),
                'round': str(row.get('round', 'N/A')) if pd.notna(row.get('round')) else 'N/A',
                'season': int(row['season']) if pd.notna(row['season']) else None,
                'source': str(row.get('source', 'unknown'))
            }
            results.append(result)
        
        return results
    
    def get_match(self, match_id: int) -> Optional[Dict]:
        """Get a specific match by ID."""
        for key in self.data:
            if 'ID' in self.data[key].columns:
                match = self.data[key][self.data[key]['ID'] == match_id]
                if not match.empty:
                    row = match.iloc[0]
                    return {
                        'date': str(row['datetime'].date()) if pd.notna(row['datetime']) else None,
                        'home_team': row['home_team'] if 'home_team' in row else row['home'],
                        'away_team': row['away_team'] if 'away_team' in row else row['away'],
                        'home_goal': int(row['home_goal']) if pd.notna(row['home_goal']) else None,
                        'away_goal': int(row['away_goal']) if pd.notna(row['away_goal']) else None,
                        'competition': row.get('competition', 'Unknown'),
                        'round': row.get('round', 'N/A'),
                        'season': int(row['season']) if pd.notna(row['season']) else None
                    }
        return None
    
    def get_team_match_history(
        self,
        team: str,
        limit: int = 20,
        competition: Optional[str] = None,
        season: Optional[int] = None
    ) -> List[Dict]:
        """Get recent matches for a specific team."""
        team_norm = self.loader._normalize_team_name(team)
        results = []
        
        all_matches = []
        for key in ['brasileirao', 'copa_brasil', 'libertadores', 'br_football', 'novo_campeonato']:
            if key in self.data:
                df = self.data[key].copy()
                df['source'] = key
                all_matches.append(df)
        
        if not all_matches:
            return []
        
        combined = pd.concat(all_matches, ignore_index=True)
        
        # Filter by team
        combined = combined[
            (combined['home_team_normalized'] == team_norm) |
            (combined['away_team_normalized'] == team_norm)
        ]
        
        if competition:
            comp_norm = competition.lower()
            combined = combined[combined['competition'].str.lower() == comp_norm]
        
        if season:
            combined = combined[combined['season'] == season]
        
        # Sort by date and limit
        if not combined.empty:
            combined = combined.sort_values('datetime', ascending=False).head(limit)
        
        for _, row in combined.iterrows():
            # Handle NaN values properly
            if 'home_team' in row and not pd.isna(row['home_team']):
                home_team = row['home_team']
            elif 'home' in row and not pd.isna(row['home']):
                home_team = row['home']
            else:
                home_team = 'N/A'
            
            if 'away_team' in row and not pd.isna(row['away_team']):
                away_team = row['away_team']
            elif 'away' in row and not pd.isna(row['away']):
                away_team = row['away']
            else:
                away_team = 'N/A'
            
            is_home = (str(row['home_team_normalized']) == team_norm) or \
                     (str(row.get('home', '')).lower() == team.lower())
            
            competition_val = row.get('competition')
            if competition_val is None or pd.isna(competition_val):
                competition_val = 'Unknown'
            
            result = {
                'date': str(row['datetime'].date()) if pd.notna(row['datetime']) else None,
                'home_team': str(home_team),
                'away_team': str(away_team),
                'home_goal': int(row['home_goal']) if pd.notna(row['home_goal']) else None,
                'away_goal': int(row['away_goal']) if pd.notna(row['away_goal']) else None,
                'competition': str(competition_val),
                'round': str(row.get('round', 'N/A')) if pd.notna(row.get('round')) else 'N/A',
                'season': int(row['season']) if pd.notna(row['season']) else None,
                'is_home': is_home
            }
            results.append(result)
        
        return results
    
    def get_head_to_head(
        self,
        team1: str,
        team2: str,
        limit: int = 20
    ) -> Dict:
        """Get head-to-head record between two teams."""
        team1_norm = self.loader._normalize_team_name(team1)
        team2_norm = self.loader._normalize_team_name(team2)
        
        matches = self.find_matches(team1=team1, team2=team2, limit=limit)
        
        # Calculate statistics
        team1_wins = 0
        team2_wins = 0
        draws = 0
        team1_goals = 0
        team2_goals = 0
        
        for match in matches:
            home_goal = match['home_goal'] if match['home_goal'] is not None else 0
            away_goal = match['away_goal'] if match['away_goal'] is not None else 0
            
            if match['home_team'] == team1 or match['home_team'] == team1_norm:
                if home_goal > away_goal:
                    team1_wins += 1
                elif home_goal < away_goal:
                    team2_wins += 1
                else:
                    draws += 1
                team1_goals += home_goal
                team2_goals += away_goal
            else:
                if away_goal > home_goal:
                    team1_wins += 1
                elif away_goal < home_goal:
                    team2_wins += 1
                else:
                    draws += 1
                team1_goals += away_goal
                team2_goals += home_goal
        
        return {
            'team1': team1,
            'team2': team2,
            'matches': matches,
            'statistics': {
                'total_matches': len(matches),
                f'{team1}_wins': team1_wins,
                f'{team2}_wins': team2_wins,
                'draws': draws,
                f'{team1}_goals': team1_goals,
                f'{team2}_goals': team2_goals
            }
        }
    
    def get_competition_matches(
        self,
        competition: str,
        season: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get all matches for a specific competition."""
        return self.find_matches(
            competition=competition,
            season=season,
            limit=limit
        )
    
    def get_date_range_matches(
        self,
        start_date: str,
        end_date: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get all matches within a date range."""
        return self.find_matches(
            date_range=(start_date, end_date),
            limit=limit
        )


def get_match_engine() -> MatchQueryEngine:
    """Get or create a match query engine instance."""
    if not hasattr(get_match_engine, "instance"):
        get_match_engine.instance = MatchQueryEngine()
    return get_match_engine.instance
