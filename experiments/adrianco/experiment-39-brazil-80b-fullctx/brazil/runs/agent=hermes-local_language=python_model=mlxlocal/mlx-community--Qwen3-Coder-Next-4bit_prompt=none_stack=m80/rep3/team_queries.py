"""Brazilian Soccer MCP Server - Team Queries."""

from typing import Dict, List, Optional
from soccer_data import SoccerDataLoader, get_loader
from match_queries import MatchQueryEngine, get_match_engine
import pandas as pd


class TeamQueryEngine:
    """Engine for querying team data and statistics."""
    
    def __init__(self, loader: Optional[SoccerDataLoader] = None, 
                 match_engine: Optional[MatchQueryEngine] = None):
        """Initialize with data loader and match engine."""
        self.loader = loader or get_loader()
        self.match_engine = match_engine or get_match_engine()
        self.data = self.loader.load_all()
    
    def get_team_statistics(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None
    ) -> Dict:
        """Get comprehensive statistics for a team."""
        team_norm = self.loader._normalize_team_name(team)
        
        # Get matches for this team
        matches = self.match_engine.find_matches(
            team1=team, competition=competition, season=season
        )
        
        if not matches:
            return {
                'team': team,
                'season': season,
                'competition': competition,
                'error': 'No matches found'
            }
        
        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0
        home_wins = 0
        home_draws = 0
        home_losses = 0
        away_wins = 0
        away_draws = 0
        away_losses = 0
        
        for match in matches:
            is_home = (match['home_team'] == team) or (match['home_team'] == team_norm)
            
            if is_home:
                if match['home_goal'] > match['away_goal']:
                    wins += 1
                    home_wins += 1
                elif match['home_goal'] == match['away_goal']:
                    draws += 1
                    home_draws += 1
                else:
                    losses += 1
                    home_losses += 1
            else:
                if match['away_goal'] > match['home_goal']:
                    wins += 1
                    away_wins += 1
                elif match['away_goal'] == match['home_goal']:
                    draws += 1
                    away_draws += 1
                else:
                    losses += 1
                    away_losses += 1
            
            goals_for += match['home_goal'] if is_home else match['away_goal']
            goals_against += match['away_goal'] if is_home else match['home_goal']
        
        total_matches = wins + draws + losses
        points = wins * 3 + draws
        
        return {
            'team': team,
            'season': season,
            'competition': competition,
            'total_matches': total_matches,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'points': points,
            'win_rate': round(wins / total_matches * 100, 1) if total_matches > 0 else 0,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'goal_difference': goals_for - goals_against,
            'home_record': {
                'matches': home_wins + home_draws + home_losses,
                'wins': home_wins,
                'draws': home_draws,
                'losses': home_losses,
                'win_rate': round(home_wins / (home_wins + home_draws + home_losses) * 100, 1) if (home_wins + home_draws + home_losses) > 0 else 0
            },
            'away_record': {
                'matches': away_wins + away_draws + away_losses,
                'wins': away_wins,
                'draws': away_draws,
                'losses': away_losses,
                'win_rate': round(away_wins / (away_wins + away_draws + away_losses) * 100, 1) if (away_wins + away_draws + away_losses) > 0 else 0
            }
        }
    
    def get_team_head_to_head(
        self,
        team1: str,
        team2: str
    ) -> Dict:
        """Get head-to-head record between two teams."""
        h2h = self.match_engine.get_head_to_head(team1, team2)
        
        stats = h2h['statistics']
        
        return {
            'team1': team1,
            'team2': team2,
            'total_matches': stats['total_matches'],
            f'{team1}_wins': stats[f'{team1}_wins'],
            f'{team2}_wins': stats[f'{team2}_wins'],
            'draws': stats['draws'],
            f'{team1}_goals': stats[f'{team1}_goals'],
            f'{team2}_goals': stats[f'{team2}_goals']
        }
    
    def get_team_players(self, team: str) -> List[Dict]:
        """Get players for a specific team from FIFA data."""
        if 'fifa_players' not in self.data:
            return []
        
        df = self.data['fifa_players']
        team_norm = self.loader._normalize_team_name(team)
        
        # Try exact match first, then partial match
        players = df[df['Club'].str.contains(team, case=False, na=False)]
        
        if players.empty:
            # Try normalized team name
            players = df[df['Club'].str.contains(team_norm, case=False, na=False)]
        
        result = []
        for _, row in players.head(50).iterrows():
            result.append({
                'name': str(row['Name']),
                'age': int(row['Age']) if pd.notna(row['Age']) else None,
                'nationality': str(row['Nationality']),
                'position': str(row['Position']),
                'overall': int(row['Overall']) if pd.notna(row['Overall']) else None,
                'potential': int(row['Potential']) if pd.notna(row['Potential']) else None,
                'value': str(row.get('Value', 'N/A'))
            })
        
        return result
    
    def get_top_scorers(
        self,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get top scorers (simulated based on match data)."""
        matches = self.match_engine.find_matches(
            season=season, competition=competition
        )
        
        # Aggregate goals by team
        team_goals = {}
        for match in matches:
            home = match['home_team']
            away = match['away_team']
            home_goals = match['home_goal']
            away_goals = match['away_goal']
            
            team_goals[home] = team_goals.get(home, 0) + home_goals
            team_goals[away] = team_goals.get(away, 0) + away_goals
        
        # Sort by goals
        sorted_teams = sorted(team_goals.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [{'team': team, 'goals': goals} for team, goals in sorted_teams]
    
    def get_teams_in_competition(
        self,
        competition: str,
        season: Optional[int] = None
    ) -> List[str]:
        """Get all teams that participated in a competition."""
        matches = self.match_engine.find_matches(
            competition=competition, season=season
        )
        
        teams = set()
        for match in matches:
            teams.add(match['home_team'])
            teams.add(match['away_team'])
        
        return sorted(list(teams))
    
    def get_team_match_history(
        self,
        team: str,
        limit: int = 20,
        competition: Optional[str] = None,
        season: Optional[int] = None
    ) -> List[Dict]:
        """Get recent matches for a team."""
        return self.match_engine.get_team_match_history(
            team, limit, competition, season
        )


def get_team_engine() -> TeamQueryEngine:
    """Get or create a team query engine instance."""
    if not hasattr(get_team_engine, "instance"):
        get_team_engine.instance = TeamQueryEngine()
    return get_team_engine.instance
