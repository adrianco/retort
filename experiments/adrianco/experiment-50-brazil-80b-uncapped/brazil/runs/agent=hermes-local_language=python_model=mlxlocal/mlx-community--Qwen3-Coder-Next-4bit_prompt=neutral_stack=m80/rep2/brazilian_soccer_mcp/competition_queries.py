"""Competition queries for the Brazilian Soccer MCP server."""

from typing import List, Dict, Any
import pandas as pd
from .data_loader import DataFileManager
from .match_queries import MatchQueryEngine


class CompetitionQueryEngine:
    """Engine for querying competition data."""
    
    def __init__(self, data_dir: str = None):
        """Initialize with optional data directory path."""
        self.data_manager = DataFileManager(data_dir)
        self.match_engine = MatchQueryEngine(data_dir)
    
    def get_competition_standings(
        self,
        competition: str,
        season: int
    ) -> Dict[str, Any]:
        """Calculate standings for a competition in a given season."""
        # Get all matches for this competition and season
        matches = self.match_engine.find_matches(
            competition=competition,
            season=season,
            limit=1000
        )
        
        # Calculate standings
        standings = {}
        
        for match in matches:
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            
            # Initialize teams if not seen
            for team in [home_team, away_team]:
                if team not in standings:
                    standings[team] = {
                        'team': team,
                        'played': 0,
                        'won': 0,
                        'drawn': 0,
                        'lost': 0,
                        'goals_for': 0,
                        'goals_against': 0,
                        'goal_difference': 0,
                        'points': 0
                    }
            
            # Update stats
            standings[home_team]['played'] += 1
            standings[away_team]['played'] += 1
            standings[home_team]['goals_for'] += home_score
            standings[home_team]['goals_against'] += away_score
            standings[away_team]['goals_for'] += away_score
            standings[away_team]['goals_against'] += home_score
            standings[home_team]['goal_difference'] += home_score - away_score
            standings[away_team]['goal_difference'] += away_score - home_score
            
            # Determine winner
            if home_score > away_score:
                standings[home_team]['won'] += 1
                standings[home_team]['points'] += 3
                standings[away_team]['lost'] += 1
            elif away_score > home_score:
                standings[away_team]['won'] += 1
                standings[away_team]['points'] += 3
                standings[home_team]['lost'] += 1
            else:
                standings[home_team]['drawn'] += 1
                standings[away_team]['drawn'] += 1
                standings[home_team]['points'] += 1
                standings[away_team]['points'] += 1
        
        # Convert to list and sort by points
        standings_list = list(standings.values())
        standings_list.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))
        
        return {
            'competition': competition,
            'season': season,
            'standings': standings_list
        }
    
    def get_season_results(self, season: int) -> Dict[str, Any]:
        """Get results for all competitions in a season."""
        competitions = ['Brasileirão', 'Copa do Brasil', 'Copa Libertadores']
        results = {}
        
        for comp in competitions:
            standings = self.get_competition_standings(comp, season)
            if standings['standings']:
                results[comp] = standings
        
        return {
            'season': season,
            'competitions': results
        }
    
    def get_champion(self, competition: str, season: int) -> str:
        """Get the champion of a competition in a season."""
        standings = self.get_competition_standings(competition, season)
        
        if standings['standings']:
            return standings['standings'][0]['team']
        return "No champion found"
    
    def get_relegated(self, competition: str, season: int, count: int = 4) -> List[str]:
        """Get teams relegated from a competition."""
        standings = self.get_competition_standings(competition, season)
        
        if standings['standings']:
            # Brasileirão typically relegates bottom 4 teams
            return [team['team'] for team in standings['standings'][-count:]]
        return []
    
    def get_promoted(self, competition: str, season: int, count: int = 4) -> List[str]:
        """Get teams promoted to a competition."""
        # This would need data from the previous season
        # For now, return placeholder
        return []
    
    def get_cup_bracket(self, competition: str, season: int) -> Dict[str, Any]:
        """Get cup bracket for knockout competitions."""
        matches = self.match_engine.find_matches(
            competition=competition,
            season=season,
            limit=100
        )
        
        # Group by round/stage
        rounds = {}
        for match in matches:
            round_name = match.get('round', 'Unknown')
            if round_name not in rounds:
                rounds[round_name] = []
            rounds[round_name].append(match)
        
        return {
            'competition': competition,
            'season': season,
            'rounds': rounds,
            'total_rounds': len(rounds)
        }
    
    def get_top_teams(self, season: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing teams in a season."""
        competitions = ['Brasileirão']
        all_teams = {}
        
        for comp in competitions:
            standings = self.get_competition_standings(comp, season)
            for team in standings['standings'][:limit]:
                team_name = team['team']
                if team_name not in all_teams:
                    all_teams[team_name] = {
                        'team': team_name,
                        'points': 0,
                        'position': float('inf'),
                        'competition': comp
                    }
                # Take best position
                if team['points'] > all_teams[team_name]['points']:
                    all_teams[team_name]['points'] = team['points']
        
        # Sort by points
        sorted_teams = sorted(
            all_teams.values(),
            key=lambda x: -x['points']
        )[:limit]
        
        return sorted_teams
    
    def get_competition_schedule(
        self,
        competition: str,
        season: int,
        round_num: int = None
    ) -> List[Dict[str, Any]]:
        """Get match schedule for a competition."""
        matches = self.match_engine.find_matches(
            competition=competition,
            season=season,
            limit=100
        )
        
        if round_num is not None:
            # Filter by round
            matches = [m for m in matches if m.get('round') == round_num]
        
        return matches
