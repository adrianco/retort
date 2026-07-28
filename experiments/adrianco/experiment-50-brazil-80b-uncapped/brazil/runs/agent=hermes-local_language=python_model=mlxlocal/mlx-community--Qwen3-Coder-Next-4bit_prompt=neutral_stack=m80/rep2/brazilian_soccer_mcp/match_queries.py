"""Match queries for the Brazilian Soccer MCP server."""

from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
from .data_loader import DataFileManager, parse_date, normalize_team_name


class MatchQueryEngine:
    """Engine for querying match data."""
    
    def __init__(self, data_dir: str = None):
        """Initialize with optional data directory path."""
        self.data_manager = DataFileManager(data_dir)
        self._matches_df = None
    
    def _load_matches(self) -> pd.DataFrame:
        """Load all match data (cached)."""
        if self._matches_df is None:
            self._matches_df = self.data_manager.get_all_matches()
        return self._matches_df
    
    def find_matches(
        self,
        team1: str = None,
        team2: str = None,
        competition: str = None,
        season: int = None,
        date_from: str = None,
        date_to: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find matches by various criteria."""
        df = self._load_matches()
        results = df.copy()
        
        # Normalize team names
        if team1:
            team1_normalized = self.data_manager.normalize_team_name(team1)
            # Check both home and away columns
            results = results[
                results['home_team'].str.contains(team1_normalized, case=False, na=False) |
                results['away_team'].str.contains(team1_normalized, case=False, na=False)
            ]
        
        if team2:
            team2_normalized = self.data_manager.normalize_team_name(team2)
            results = results[
                results['home_team'].str.contains(team2_normalized, case=False, na=False) |
                results['away_team'].str.contains(team2_normalized, case=False, na=False)
            ]
        
        # Filter by competition
        if competition:
            competition_normalized = competition.lower()
            results = results[
                results['competition'].str.contains(competition_normalized, case=False, na=False) |
                results['tournament'].str.contains(competition_normalized, case=False, na=False)
            ]
        
        # Filter by season
        if season:
            if 'season' in results.columns:
                results = results[results['season'] == season]
            elif 'Ano' in results.columns:
                results = results[results['Ano'] == season]
        
        # Filter by date range
        if date_from:
            date_from_parsed = parse_date(date_from)
            if date_from_parsed:
                if 'datetime' in results.columns:
                    results['datetime'] = pd.to_datetime(results['datetime'], errors='coerce')
                    results = results[results['datetime'] >= pd.Timestamp(date_from_parsed)]
        
        if date_to:
            date_to_parsed = parse_date(date_to)
            if date_to_parsed:
                if 'datetime' in results.columns:
                    results['datetime'] = pd.to_datetime(results['datetime'], errors='coerce')
                    results = results[results['datetime'] <= pd.Timestamp(date_to_parsed)]
        
        # Limit results
        results = results.head(limit)
        
        # Format results
        formatted = []
        for _, row in results.iterrows():
            formatted.append(self._format_match_row(row))
        
        return formatted
    
    def _format_match_row(self, row: pd.Series) -> Dict[str, Any]:
        """Format a single match row for output."""
        result = {}
        
        # Basic match info
        if 'datetime' in row.index and pd.notna(row['datetime']):
            result['date'] = str(row['datetime'])
        elif 'date' in row.index and pd.notna(row['date']):
            result['date'] = str(row['date'])
        
        # Team names
        if 'home_team' in row.index and pd.notna(row['home_team']):
            result['home_team'] = str(row['home_team'])
        if 'away_team' in row.index and pd.notna(row['away_team']):
            result['away_team'] = str(row['away_team'])
        
        # Handle extended match format with 'home' and 'away' columns
        if 'home' in row.index and pd.notna(row['home']):
            result['home_team'] = str(row['home'])
        if 'away' in row.index and pd.notna(row['away']):
            result['away_team'] = str(row['away'])
        
        # Scores - handle NaN values properly
        home_score = None
        away_score = None
        
        for col in ['home_goal', 'home_score']:
            if col in row.index and pd.notna(row[col]):
                try:
                    home_score = int(float(row[col]))
                    break
                except (ValueError, TypeError):
                    pass
        
        for col in ['away_goal', 'away_score']:
            if col in row.index and pd.notna(row[col]):
                try:
                    away_score = int(float(row[col]))
                    break
                except (ValueError, TypeError):
                    pass
        
        if home_score is not None:
            result['home_score'] = home_score
        if away_score is not None:
            result['away_score'] = away_score
        
        # Competition
        for col in ['competition', 'tournament']:
            if col in row.index and pd.notna(row[col]):
                result['competition'] = str(row[col])
                break
        
        # Round
        for col in ['round', 'Rodada']:
            if col in row.index and pd.notna(row[col]):
                try:
                    result['round'] = int(float(row[col]))
                except (ValueError, TypeError):
                    result['round'] = str(row[col])
                break
        
        # Season
        for col in ['season', 'Ano']:
            if col in row.index and pd.notna(row[col]):
                try:
                    result['season'] = int(float(row[col]))
                except (ValueError, TypeError):
                    pass
                break
        
        return result
    
    def get_match_by_teams(
        self,
        team1: str,
        team2: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get matches between two specific teams."""
        matches = self.find_matches(team1=team1, team2=team2, limit=limit)
        
        # Calculate statistics
        team1_normalized = self.data_manager.normalize_team_name(team1)
        team2_normalized = self.data_manager.normalize_team_name(team2)
        
        stats = {
            'team1': team1,
            'team2': team2,
            'total_matches': len(matches),
            'head_to_head': {
                'team1_wins': 0,
                'team2_wins': 0,
                'draws': 0
            }
        }
        
        for match in matches:
            home = match.get('home_team', '')
            away = match.get('away_team', '')
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            
            if team1_normalized.lower() in home.lower() or team1_normalized.lower() in away.lower():
                # Team1 is involved
                if home_score > away_score and team1_normalized.lower() in home.lower():
                    stats['head_to_head']['team1_wins'] += 1
                elif away_score > home_score and team1_normalized.lower() in away.lower():
                    stats['head_to_head']['team1_wins'] += 1
                elif home_score == away_score:
                    stats['head_to_head']['draws'] += 1
                else:
                    stats['head_to_head']['team2_wins'] += 1
            else:
                # Team2 is involved
                if home_score > away_score and team2_normalized.lower() in home.lower():
                    stats['head_to_head']['team2_wins'] += 1
                elif away_score > home_score and team2_normalized.lower() in away.lower():
                    stats['head_to_head']['team2_wins'] += 1
                else:
                    stats['head_to_head']['team1_wins'] += 1
        
        return {
            'matches': matches,
            'statistics': stats
        }
    
    def get_team_match_history(
        self,
        team: str,
        season: int = None,
        competition: str = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get match history for a team."""
        matches = self.find_matches(
            team1=team,
            competition=competition,
            season=season,
            limit=limit
        )
        
        # Calculate team stats
        team_normalized = self.data_manager.normalize_team_name(team)
        stats = {
            'team': team,
            'matches': len(matches),
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'points': 0
        }
        
        for match in matches:
            home = match.get('home_team', '')
            away = match.get('away_team', '')
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            
            if team_normalized.lower() in home.lower():
                stats['goals_for'] += home_score
                stats['goals_against'] += away_score
                if home_score > away_score:
                    stats['wins'] += 1
                    stats['points'] += 3
                elif home_score == away_score:
                    stats['draws'] += 1
                    stats['points'] += 1
                else:
                    stats['losses'] += 1
            elif team_normalized.lower() in away.lower():
                stats['goals_for'] += away_score
                stats['goals_against'] += home_score
                if away_score > home_score:
                    stats['wins'] += 1
                    stats['points'] += 3
                elif away_score == home_score:
                    stats['draws'] += 1
                    stats['points'] += 1
                else:
                    stats['losses'] += 1
        
        return {
            'matches': matches,
            'statistics': stats
        }
    
    def get_competition_matches(
        self,
        competition: str,
        season: int = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get matches for a specific competition."""
        return self.find_matches(
            competition=competition,
            season=season,
            limit=limit
        )
