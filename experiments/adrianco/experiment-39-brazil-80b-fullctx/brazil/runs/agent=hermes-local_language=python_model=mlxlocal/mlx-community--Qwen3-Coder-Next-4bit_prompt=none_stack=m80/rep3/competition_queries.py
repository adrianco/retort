"""Brazilian Soccer MCP Server - Competition Queries."""

from typing import Dict, List, Optional
from soccer_data import SoccerDataLoader, get_loader
from match_queries import MatchQueryEngine, get_match_engine
from team_queries import TeamQueryEngine, get_team_engine
import pandas as pd


class CompetitionQueryEngine:
    """Engine for querying competition data and standings."""
    
    def __init__(self, loader: Optional[SoccerDataLoader] = None,
                 match_engine: Optional[MatchQueryEngine] = None,
                 team_engine: Optional[TeamQueryEngine] = None):
        """Initialize with engines."""
        self.loader = loader or get_loader()
        self.match_engine = match_engine or get_match_engine()
        self.team_engine = team_engine or get_team_engine()
        self.data = self.loader.load_all()
    
    def get_competition_standings(
        self,
        competition: str,
        season: int
    ) -> List[Dict]:
        """Calculate standings for a competition by season."""
        matches = self.match_engine.find_matches(
            competition=competition, season=season
        )
        
        if not matches:
            return []
        
        # Track team statistics
        team_stats = {}
        
        for match in matches:
            home_team = match['home_team']
            away_team = match['away_team']
            home_goals = match['home_goal']
            away_goals = match['away_goal']
            
            for team in [home_team, away_team]:
                if team not in team_stats:
                    team_stats[team] = {
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
            
            # Update home team stats
            team_stats[home_team]['played'] += 1
            team_stats[home_team]['goals_for'] += home_goals
            team_stats[home_team]['goals_against'] += away_goals
            team_stats[home_team]['goal_difference'] += home_goals - away_goals
            
            # Update away team stats
            team_stats[away_team]['played'] += 1
            team_stats[away_team]['goals_for'] += away_goals
            team_stats[away_team]['goals_against'] += home_goals
            team_stats[away_team]['goal_difference'] += away_goals - home_goals
            
            # Determine winner
            if home_goals > away_goals:
                team_stats[home_team]['won'] += 1
                team_stats[home_team]['points'] += 3
                team_stats[away_team]['lost'] += 1
            elif home_goals < away_goals:
                team_stats[away_team]['won'] += 1
                team_stats[away_team]['points'] += 3
                team_stats[home_team]['lost'] += 1
            else:
                team_stats[home_team]['drawn'] += 1
                team_stats[home_team]['points'] += 1
                team_stats[away_team]['drawn'] += 1
                team_stats[away_team]['points'] += 1
        
        # Convert to list and sort
        standings = list(team_stats.values())
        standings.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))
        
        return standings
    
    def get_competition_results(
        self,
        competition: str,
        season: Optional[int] = None,
        round_num: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get match results for a competition."""
        matches = self.match_engine.find_matches(
            competition=competition,
            season=season,
            limit=limit
        )
        
        if round_num:
            matches = [m for m in matches if m.get('round') == round_num]
        
        return matches
    
    def get_champion(self, competition: str, season: int) -> Optional[str]:
        """Get the champion of a competition for a season."""
        standings = self.get_competition_standings(competition, season)
        return standings[0]['team'] if standings else None
    
    def get_relegated_teams(self, competition: str, season: int, 
                            num_relegated: int = 4) -> List[str]:
        """Get teams that were relegated from a competition."""
        standings = self.get_competition_standings(competition, season)
        return [team['team'] for team in standings[-num_relegated:]]
    
    def get_relegation_battle(self, competition: str, season: int) -> List[Dict]:
        """Get the teams involved in the relegation battle (bottom 6)."""
        standings = self.get_competition_standings(competition, season)
        return standings[-6:] if len(standings) >= 6 else standings
    
    def get_top_scorers_competition(
        self,
        competition: str,
        season: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get top scoring teams in a competition."""
        return self.team_engine.get_top_scorers(
            competition=competition, season=season, limit=limit
        )
    
    def get_competition_teams(self, competition: str, 
                              season: Optional[int] = None) -> List[str]:
        """Get all teams that participated in a competition."""
        return self.team_engine.get_teams_in_competition(competition, season)
    
    def get_match_schedule(
        self,
        competition: str,
        season: int,
        round_num: Optional[int] = None
    ) -> List[Dict]:
        """Get match schedule for a competition."""
        matches = self.match_engine.find_matches(
            competition=competition,
            season=season
        )
        
        if round_num:
            matches = [m for m in matches if m.get('round') == round_num]
        
        # Sort by date
        matches.sort(key=lambda x: x['date'] if x['date'] else '')
        return matches
    
    def get_copa_libertadores_bracket(self, season: int) -> Dict:
        """Get Copa Libertadores bracket for a season."""
        matches = self.match_engine.find_matches(
            competition='Copa Libertadores', season=season
        )
        
        if not matches:
            return {'error': 'No data found for this season'}
        
        # Group by stage
        stages = {}
        for match in matches:
            stage = match.get('stage', 'Unknown')
            if stage not in stages:
                stages[stage] = []
            stages[stage].append(match)
        
        return {
            'season': season,
            'stages': stages,
            'total_matches': len(matches)
        }


def get_competition_engine() -> CompetitionQueryEngine:
    """Get or create a competition query engine instance."""
    if not hasattr(get_competition_engine, "instance"):
        get_competition_engine.instance = CompetitionQueryEngine()
    return get_competition_engine.instance
