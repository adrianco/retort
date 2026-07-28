"""Player queries for the Brazilian Soccer MCP server."""

from typing import List, Dict, Any
import pandas as pd
from .data_loader import DataFileManager


class PlayerQueryEngine:
    """Engine for querying player data."""
    
    def __init__(self, data_dir: str = None):
        """Initialize with optional data directory path."""
        self.data_manager = DataFileManager(data_dir)
        self._players_df = None
    
    def _load_players(self) -> pd.DataFrame:
        """Load FIFA player data (cached)."""
        if self._players_df is None:
            self._players_df = self.data_manager.get_fifa_players()
        return self._players_df
    
    def get_all_players(self) -> List[Dict[str, Any]]:
        """Get all players."""
        df = self._load_players()
        return self._format_players(df)
    
    def search_players(self, name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search players by name."""
        df = self._load_players()
        
        # Search in Name column
        mask = df['Name'].str.contains(name, case=False, na=False)
        results = df[mask].head(limit)
        
        return self._format_players(results)
    
    def get_players_by_nationality(
        self,
        nationality: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get players by nationality."""
        df = self._load_players()
        
        # Handle Brazilian nationality
        if nationality.lower() == 'brazil':
            nationality = 'Brazil'
        
        mask = df['Nationality'].str.contains(nationality, case=False, na=False)
        results = df[mask].head(limit)
        
        return self._format_players(results)
    
    def get_brazilian_players(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all Brazilian players."""
        return self.get_players_by_nationality('Brazil', limit)
    
    def get_players_by_club(
        self,
        club: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get players by club."""
        df = self._load_players()
        
        # Search in Club column - handle NaN values
        mask = df['Club'].str.contains(club, case=False, na=False)
        results = df[mask].head(limit)
        
        return self._format_players(results)
    
    def get_players_by_position(
        self,
        position: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get players by position."""
        df = self._load_players()
        
        # Handle common position aliases
        position_map = {
            'forward': ['ST', 'CF', 'LF', 'RF', 'RW'],
            'striker': ['ST', 'CF'],
            'winger': ['LW', 'RW', 'LAM', 'RAM'],
            'midfielder': ['CM', 'CAM', 'CDM', 'LM', 'RM', 'LAM', 'RAM'],
            'defender': ['LB', 'RB', 'CB', 'LWB', 'RWB'],
            'goalkeeper': ['GK'],
        }
        
        positions = position_map.get(position.lower(), [position.upper()])
        mask = df['Position'].isin(positions)
        results = df[mask].head(limit)
        
        return self._format_players(results)
    
    def get_top_rated_players(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top rated players."""
        df = self._load_players()
        
        # Sort by Overall rating
        df = df.sort_values('Overall', ascending=False)
        results = df.head(limit)
        
        return self._format_players(results)
    
    def get_brazilian_top_rated(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top rated Brazilian players."""
        players = self.get_brazilian_players(limit=1000)
        
        # Sort by Overall rating
        players.sort(key=lambda x: x.get('Overall', 0), reverse=True)
        
        return players[:limit]
    
    def get_players_by_club_in_brazil(
        self,
        club: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get Brazilian players at a specific club."""
        players = self.get_players_by_club(club, limit)
        
        # Filter for Brazilian players
        brazilian_players = [
            p for p in players
            if 'Brazil' in str(p.get('Nationality', ''))
        ]
        
        return brazilian_players
    
    def get_player_details(self, player_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific player."""
        df = self._load_players()
        
        mask = df['Name'].str.contains(player_name, case=False, na=False)
        player = df[mask].head(1)
        
        if len(player) == 0:
            return {'error': f'Player "{player_name}" not found'}
        
        return self._format_player(player.iloc[0])
    
    def _format_players(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Format a DataFrame of players for output."""
        formatted = []
        for _, row in df.iterrows():
            formatted.append(self._format_player(row))
        return formatted
    
    def _format_player(self, row: pd.Series) -> Dict[str, Any]:
        """Format a single player row for output."""
        result = {}
        
        # Basic info
        for col in ['ID', 'Name', 'Age', 'Photo', 'Nationality', 'Flag']:
            if col in row.index and pd.notna(row[col]):
                result[col] = str(row[col])
        
        # Ratings
        for col in ['Overall', 'Potential']:
            if col in row.index and pd.notna(row[col]):
                try:
                    result[col] = int(float(row[col]))
                except (ValueError, TypeError):
                    pass
        
        # Club info
        for col in ['Club', 'Club Logo']:
            if col in row.index and pd.notna(row[col]):
                result[col] = str(row[col])
        
        # Position info
        for col in ['Position', 'Jersey Number']:
            if col in row.index and pd.notna(row[col]):
                result[col] = str(row[col])
        
        # Physical attributes
        for col in ['Height', 'Weight']:
            if col in row.index and pd.notna(row[col]):
                result[col] = str(row[col])
        
        # Key skill ratings
        skills = ['Crossing', 'Finishing', 'HeadingAccuracy', 'ShortPassing',
                  'Dribbling', 'Curve', 'FKAccuracy', 'BallControl',
                  'Acceleration', 'SprintSpeed', 'Agility', 'Reactions',
                  'ShotPower', 'Stamina', 'Strength', 'LongShots']
        
        for skill in skills:
            if skill in row.index and pd.notna(row[skill]):
                try:
                    result[skill] = int(float(row[skill]))
                except (ValueError, TypeError):
                    pass
        
        return result
    
    def get_brazilian_players_by_club(self, club: str) -> List[Dict[str, Any]]:
        """Get Brazilian players at a specific club."""
        players = self.get_players_by_club(club)
        
        # Filter for Brazilian players
        brazilian_players = [
            p for p in players
            if 'Brazil' in str(p.get('Nationality', ''))
        ]
        
        return brazilian_players
