"""Brazilian Soccer MCP Server - Player Queries."""

from typing import Dict, List, Optional
from soccer_data import SoccerDataLoader, get_loader
import pandas as pd


class PlayerQueryEngine:
    """Engine for querying player data from FIFA database."""
    
    def __init__(self, loader: Optional[SoccerDataLoader] = None):
        """Initialize with data loader."""
        self.loader = loader or get_loader()
        self.data = self.loader.load_all()
    
    def find_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Find players matching the given criteria."""
        if 'fifa_players' not in self.data:
            return []
        
        df = self.data['fifa_players'].copy()
        
        # Apply filters
        if name:
            df = df[df['Name'].str.contains(name, case=False, na=False)]
        
        if nationality:
            df = df[df['Nationality'].str.contains(nationality, case=False, na=False)]
        
        if club:
            club_norm = self.loader._normalize_team_name(club)
            df = df[
                df['Club'].str.contains(club, case=False, na=False) |
                df['Club'].str.contains(club_norm, case=False, na=False)
            ]
        
        if position:
            df = df[df['Position'].str.contains(position, case=False, na=False)]
        
        if min_overall:
            df = df[df['Overall'] >= min_overall]
        
        if max_overall:
            df = df[df['Overall'] <= max_overall]
        
        if min_age:
            df = df[df['Age'] >= min_age]
        
        if max_age:
            df = df[df['Age'] <= max_age]
        
        # Sort by overall rating (highest first)
        df = df.sort_values('Overall', ascending=False).head(limit)
        
        result = []
        for _, row in df.iterrows():
            result.append({
                'id': int(row['ID']) if pd.notna(row['ID']) else None,
                'name': row['Name'],
                'age': int(row['Age']) if pd.notna(row['Age']) else None,
                'nationality': row['Nationality'],
                'overall': int(row['Overall']) if pd.notna(row['Overall']) else None,
                'potential': int(row['Potential']) if pd.notna(row['Potential']) else None,
                'club': row['Club'],
                'position': row['Position'],
                'jersey_number': int(row['Jersey Number']) if pd.notna(row['Jersey Number']) else None,
                'height': row.get('Height', 'N/A'),
                'weight': row.get('Weight', 'N/A'),
                'value': row.get('Value', 'N/A')
            })
        
        return result
    
    def get_player(self, player_id: int) -> Optional[Dict]:
        """Get a specific player by ID."""
        if 'fifa_players' not in self.data:
            return None
        
        df = self.data['fifa_players']
        player = df[df['ID'] == player_id]
        
        if player.empty:
            return None
        
        row = player.iloc[0]
        return {
            'id': int(row['ID']) if pd.notna(row['ID']) else None,
            'name': row['Name'],
            'age': int(row['Age']) if pd.notna(row['Age']) else None,
            'nationality': row['Nationality'],
            'overall': int(row['Overall']) if pd.notna(row['Overall']) else None,
            'potential': int(row['Potential']) if pd.notna(row['Potential']) else None,
            'club': row['Club'],
            'position': row['Position'],
            'jersey_number': int(row['Jersey Number']) if pd.notna(row['Jersey Number']) else None,
            'height': row.get('Height', 'N/A'),
            'weight': row.get('Weight', 'N/A'),
            'value': row.get('Value', 'N/A'),
            'preferred_foot': row.get('Preferred Foot', 'N/A'),
            'international_reputation': int(row['International Reputation']) if pd.notna(row['International Reputation']) else None,
            'weak_foot': int(row['Weak Foot']) if pd.notna(row['Weak Foot']) else None,
            'skill_moves': int(row['Skill Moves']) if pd.notna(row['Skill Moves']) else None,
            'attacking_work_rate': row.get('Work Rate', 'N/A')
        }
    
    def get_player_by_name(self, name: str) -> Optional[Dict]:
        """Find a player by name (fuzzy match)."""
        players = self.find_players(name=name, limit=1)
        return players[0] if players else None
    
    def get_brazilian_players(self, limit: int = 50) -> List[Dict]:
        """Get Brazilian players from the dataset."""
        return self.find_players(nationality='Brazil', limit=limit)
    
    def get_top_brazilian_players(self, limit: int = 20) -> List[Dict]:
        """Get top-rated Brazilian players."""
        return self.find_players(
            nationality='Brazil',
            min_overall=80,
            limit=limit
        )
    
    def get_players_by_club(self, club: str, limit: int = 50) -> List[Dict]:
        """Get players for a specific club."""
        return self.find_players(club=club, limit=limit)
    
    def get_top_scorers_by_club(self, club: str, limit: int = 10) -> List[Dict]:
        """Get top scorers for a club (by overall rating as proxy)."""
        players = self.find_players(club=club, min_overall=75, limit=limit)
        # Sort by potential to find rising stars
        players.sort(key=lambda x: x.get('potential', 0), reverse=True)
        return players
    
    def get_players_by_position(
        self,
        position: str,
        nationality: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get players by position."""
        return self.find_players(
            position=position,
            nationality=nationality,
            limit=limit
        )
    
    def get_top_positions(
        self,
        nationality: Optional[str] = None,
        position: str = 'ST',
        limit: int = 10
    ) -> List[Dict]:
        """Get top players for a specific position."""
        return self.find_players(
            nationality=nationality,
            position=position,
            min_overall=85,
            limit=limit
        )
    
    def get_player_attributes(self, player_id: int) -> Dict:
        """Get detailed attributes for a player."""
        player = self.get_player(player_id)
        if not player:
            return {'error': 'Player not found'}
        
        # Get additional attributes from the raw data
        if 'fifa_players' in self.data:
            df = self.data['fifa_players']
            row = df[df['ID'] == player_id]
            if not row.empty:
                row = row.iloc[0]
                attributes = {}
                for col in row.index:
                    if col.startswith(('LS', 'ST', 'RS', 'LW', 'LF', 'CF', 'RF', 'RW', 
                                       'LAM', 'CAM', 'RAM', 'LM', 'LCM', 'CM', 'RCM', 'RM',
                                       'LWB', 'LDM', 'CDM', 'RDM', 'RWB', 'LB', 'LCB', 'CB', 'RCB', 'RB')):
                        attributes[col] = row[col]
                    elif col.startswith(('Crossing', 'Finishing', 'HeadingAccuracy', 'ShortPassing',
                                          'Volleys', 'Dribbling', 'Curve', 'FKAccuracy', 'LongPassing',
                                          'BallControl', 'Acceleration', 'SprintSpeed', 'Agility',
                                          'Reactions', 'Balance', 'ShotPower', 'Jumping', 'Stamina',
                                          'Strength', 'LongShots', 'Aggression', 'Interceptions',
                                          'Positioning', 'Vision', 'Penalties', 'Composure',
                                          'Marking', 'StandingTackle', 'SlidingTackle',
                                          'GKDiving', 'GKHandling', 'GKKicking', 'GKPositioning',
                                          'GKReflexes')):
                        attributes[col] = row[col]
                
                player['attributes'] = attributes
        
        return player
    
    def get_players_by_nationality(self, nationality: str, limit: int = 50) -> List[Dict]:
        """Get players from a specific nationality."""
        return self.find_players(nationality=nationality, limit=limit)


def get_player_engine() -> PlayerQueryEngine:
    """Get or create a player query engine instance."""
    if not hasattr(get_player_engine, "instance"):
        get_player_engine.instance = PlayerQueryEngine()
    return get_player_engine.instance
