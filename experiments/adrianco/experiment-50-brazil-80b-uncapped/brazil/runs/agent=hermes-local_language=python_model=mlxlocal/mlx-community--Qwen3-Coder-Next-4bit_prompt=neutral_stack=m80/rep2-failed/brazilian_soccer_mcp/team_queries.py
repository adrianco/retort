"""Team queries for the Brazilian Soccer MCP server."""

from typing import List, Dict, Any
import pandas as pd
from .data_loader import DataFileManager
from .match_queries import MatchQueryEngine


class TeamQueryEngine:
    """Engine for querying team data."""
    
    def __init__(self, data_dir: str = None):
        """Initialize with optional data directory path."""
        self.data_manager = DataFileManager(data_dir)
        self.match_engine = MatchQueryEngine(data_dir)
    
    def get_team_info(self, team: str) -> Dict[str, Any]:
        """Get basic information about a team."""
        team_normalized = self.data_manager.normalize_team_name(team)
        
        return {
            'team': team,
            'normalized_name': team_normalized,
            'status': 'found'
        }
    
    def get_team_statistics(
        self,
        team: str,
        season: int = None,
        competition: str = None
    ) -> Dict[str, Any]:
        """Get comprehensive statistics for a team."""
        team_normalized = self.data_manager.normalize_team_name(team)
        
        # Get match history
        history = self.match_engine.get_team_match_history(
            team=team,
            season=season,
            competition=competition
        )
        
        stats = history['statistics']
        matches = history['matches']
        
        # Calculate additional stats
        total_matches = stats['matches']
        if total_matches > 0:
            win_rate = round((stats['wins'] / total_matches) * 100, 1)
            draw_rate = round((stats['draws'] / total_matches) * 100, 1)
            loss_rate = round((stats['losses'] / total_matches) * 100, 1)
            goal_difference = stats['goals_for'] - stats['goals_against']
        else:
            win_rate = draw_rate = loss_rate = goal_difference = 0
        
        return {
            'team': team,
            'normalized_name': team_normalized,
            'season': season,
            'competition': competition,
            'total_matches': total_matches,
            'wins': stats['wins'],
            'draws': stats['draws'],
            'losses': stats['losses'],
            'points': stats['points'],
            'goals_for': stats['goals_for'],
            'goals_against': stats['goals_against'],
            'goal_difference': goal_difference,
            'win_rate': f"{win_rate}%",
            'draw_rate': f"{draw_rate}%",
            'loss_rate': f"{loss_rate}%",
            'matches': matches[:10]  # Return first 10 matches
        }
    
    def get_team_home_record(
        self,
        team: str,
        season: int = None
    ) -> Dict[str, Any]:
        """Get home record for a team."""
        team_normalized = self.data_manager.normalize_team_name(team)
        
        # Get matches where team is home
        matches = self.match_engine.find_matches(team1=team, season=season)
        
        home_matches = []
        for match in matches:
            home = match.get('home_team', '')
            if team_normalized.lower() in home.lower():
                home_matches.append(match)
        
        # Calculate home stats
        stats = {
            'team': team,
            'home_matches': len(home_matches),
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'points': 0
        }
        
        for match in home_matches:
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            
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
        
        if stats['home_matches'] > 0:
            stats['win_rate'] = f"{round((stats['wins'] / stats['home_matches']) * 100, 1)}%"
        
        return {
            'team': team,
            'season': season,
            'statistics': stats,
            'matches': home_matches
        }
    
    def get_team_away_record(
        self,
        team: str,
        season: int = None
    ) -> Dict[str, Any]:
        """Get away record for a team."""
        team_normalized = self.data_manager.normalize_team_name(team)
        
        # Get matches where team is away
        matches = self.match_engine.find_matches(team1=team, season=season)
        
        away_matches = []
        for match in matches:
            away = match.get('away_team', '')
            if team_normalized.lower() in away.lower():
                away_matches.append(match)
        
        # Calculate away stats
        stats = {
            'team': team,
            'away_matches': len(away_matches),
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'points': 0
        }
        
        for match in away_matches:
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            
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
        
        if stats['away_matches'] > 0:
            stats['win_rate'] = f"{round((stats['wins'] / stats['away_matches']) * 100, 1)}%"
        
        return {
            'team': team,
            'season': season,
            'statistics': stats,
            'matches': away_matches
        }
    
    def get_head_to_head(
        self,
        team1: str,
        team2: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get head-to-head record between two teams."""
        return self.match_engine.get_match_by_teams(team1, team2, limit)
    
    def get_competitions_for_team(self, team: str) -> List[str]:
        """Get list of competitions a team has played in."""
        matches = self.match_engine.find_matches(team1=team, limit=1000)
        
        competitions = set()
        for match in matches:
            comp = match.get('competition') or match.get('tournament')
            if comp:
                competitions.add(comp)
        
        return sorted(list(competitions))
    
    def get_recent_matches(self, team: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent matches for a team."""
        return self.match_engine.find_matches(team1=team, limit=limit)
    
    def get_top_scorers(self, season: int = None, competition: str = None) -> List[Dict[str, Any]]:
        """Get top scorers (from available data)."""
        # Note: The match data doesn't have individual scorer info
        # This is a placeholder for competitions that might have it
        players = self.get_players_for_competition(competition, season)
        
        # Sort by rating as a proxy for scoring ability
        if 'Overall' in players[0]:
            players.sort(key=lambda x: x.get('Overall', 0), reverse=True)
        
        return players[:10]
    
    def get_players_for_competition(
        self,
        competition: str,
        season: int = None
    ) -> List[Dict[str, Any]]:
        """Get players associated with a competition."""
        from .player_queries import PlayerQueryEngine
        
        player_engine = PlayerQueryEngine()
        players = player_engine.get_all_players()
        
        # Filter by nationality (Brazilian players)
        brazilian_players = [p for p in players if 'Brazil' in str(p.get('Nationality', ''))]
        
        return brazilian_players
