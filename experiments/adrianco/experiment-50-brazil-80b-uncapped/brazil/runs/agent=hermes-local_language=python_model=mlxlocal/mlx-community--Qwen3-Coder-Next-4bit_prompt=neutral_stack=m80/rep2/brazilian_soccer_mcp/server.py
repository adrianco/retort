"""Main MCP server implementation for Brazilian Soccer."""

from typing import Dict, Any, List, Optional
import json
import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from .data_loader import DataFileManager
from .match_queries import MatchQueryEngine
from .team_queries import TeamQueryEngine
from .player_queries import PlayerQueryEngine
from .competition_queries import CompetitionQueryEngine
from .statistical_analysis import StatisticalAnalysisEngine


class BrazilianSoccerMCP:
    """Main MCP server class for Brazilian soccer data."""
    
    def __init__(self, data_dir: str = None):
        """Initialize the MCP server with optional data directory."""
        self.data_manager = DataFileManager(data_dir)
        self.match_engine = MatchQueryEngine(data_dir)
        self.team_engine = TeamQueryEngine(data_dir)
        self.player_engine = PlayerQueryEngine(data_dir)
        self.competition_engine = CompetitionQueryEngine(data_dir)
        self.stats_engine = StatisticalAnalysisEngine(data_dir)
    
    def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP request and return a response."""
        try:
            if method == 'match.find':
                return self.handle_match_find(params)
            elif method == 'match.get_by_teams':
                return self.handle_match_get_by_teams(params)
            elif method == 'team.get_statistics':
                return self.handle_team_get_statistics(params)
            elif method == 'team.get_home_record':
                return self.handle_team_get_home_record(params)
            elif method == 'team.get_away_record':
                return self.handle_team_get_away_record(params)
            elif method == 'team.get_head_to_head':
                return self.handle_team_get_head_to_head(params)
            elif method == 'team.get_competitions':
                return self.handle_team_get_competitions(params)
            elif method == 'player.search':
                return self.handle_player_search(params)
            elif method == 'player.get_brazilian_top_rated':
                return self.handle_player_get_brazilian_top_rated(params)
            elif method == 'player.get_by_club':
                return self.handle_player_get_by_club(params)
            elif method == 'competition.get_standings':
                return self.handle_competition_get_standings(params)
            elif method == 'competition.get_champion':
                return self.handle_competition_get_champion(params)
            elif method == 'competition.get_cup_bracket':
                return self.handle_competition_get_cup_bracket(params)
            elif method == 'stats.get_average_goals':
                return self.handle_stats_get_average_goals(params)
            elif method == 'stats.get_biggest_victories':
                return self.handle_stats_get_biggest_victories(params)
            elif method == 'stats.get_home_win_rate':
                return self.handle_stats_get_home_win_rate(params)
            elif method == 'stats.get_team_trend':
                return self.handle_stats_get_team_trend(params)
            elif method == 'stats.get_head_to_head_stats':
                return self.handle_stats_get_head_to_head_stats(params)
            elif method == 'stats.get_competition_summary':
                return self.handle_stats_get_competition_summary(params)
            else:
                return {'error': f'Unknown method: {method}'}
        except Exception as e:
            return {'error': str(e)}
    
    def handle_match_find(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle match.find method."""
        team1 = params.get('team1')
        team2 = params.get('team2')
        competition = params.get('competition')
        season = params.get('season')
        limit = params.get('limit', 20)
        
        matches = self.match_engine.find_matches(
            team1=team1,
            team2=team2,
            competition=competition,
            season=season,
            limit=limit
        )
        
        return {'matches': matches, 'count': len(matches)}
    
    def handle_match_get_by_teams(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle match.get_by_teams method."""
        team1 = params.get('team1')
        team2 = params.get('team2')
        limit = params.get('limit', 20)
        
        return self.match_engine.get_match_by_teams(team1, team2, limit)
    
    def handle_team_get_statistics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle team.get_statistics method."""
        team = params.get('team')
        season = params.get('season')
        competition = params.get('competition')
        
        return self.team_engine.get_team_statistics(
            team=team,
            season=season,
            competition=competition
        )
    
    def handle_team_get_home_record(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle team.get_home_record method."""
        team = params.get('team')
        season = params.get('season')
        
        return self.team_engine.get_team_home_record(team=team, season=season)
    
    def handle_team_get_away_record(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle team.get_away_record method."""
        team = params.get('team')
        season = params.get('season')
        
        return self.team_engine.get_team_away_record(team=team, season=season)
    
    def handle_team_get_head_to_head(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle team.get_head_to_head method."""
        team1 = params.get('team1')
        team2 = params.get('team2')
        
        return self.team_engine.get_head_to_head(team1, team2)
    
    def handle_team_get_competitions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle team.get_competitions method."""
        team = params.get('team')
        
        competitions = self.team_engine.get_competitions_for_team(team)
        return {'competitions': competitions}
    
    def handle_player_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle player.search method."""
        name = params.get('name')
        nationality = params.get('nationality')
        club = params.get('club')
        position = params.get('position')
        limit = params.get('limit', 20)
        
        if name:
            players = self.player_engine.search_players(name, limit)
        elif nationality:
            players = self.player_engine.get_players_by_nationality(nationality, limit)
        elif club:
            players = self.player_engine.get_players_by_club(club, limit)
        elif position:
            players = self.player_engine.get_players_by_position(position, limit)
        else:
            players = self.player_engine.get_all_players()[:limit]
        
        return {'players': players, 'count': len(players)}
    
    def handle_player_get_brazilian_top_rated(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle player.get_brazilian_top_rated method."""
        limit = params.get('limit', 20)
        
        players = self.player_engine.get_brazilian_top_rated(limit)
        return {'players': players, 'count': len(players)}
    
    def handle_player_get_by_club(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle player.get_by_club method."""
        club = params.get('club')
        nationality = params.get('nationality')
        limit = params.get('limit', 50)
        
        players = self.player_engine.get_players_by_club(club, limit)
        
        if nationality:
            players = [
                p for p in players
                if nationality.lower() in str(p.get('Nationality', '')).lower()
            ]
        
        return {'players': players, 'count': len(players)}
    
    def handle_competition_get_standings(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle competition.get_standings method."""
        competition = params.get('competition')
        season = params.get('season')
        
        return self.competition_engine.get_competition_standings(competition, season)
    
    def handle_competition_get_champion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle competition.get_champion method."""
        competition = params.get('competition')
        season = params.get('season')
        
        champion = self.competition_engine.get_champion(competition, season)
        return {'competition': competition, 'season': season, 'champion': champion}
    
    def handle_competition_get_cup_bracket(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle competition.get_cup_bracket method."""
        competition = params.get('competition')
        season = params.get('season')
        
        return self.competition_engine.get_cup_bracket(competition, season)
    
    def handle_stats_get_average_goals(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stats.get_average_goals method."""
        competition = params.get('competition')
        
        avg = self.stats_engine.get_average_goals_per_match(competition)
        return {'average_goals': avg, 'competition': competition}
    
    def handle_stats_get_biggest_victories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stats.get_biggest_victories method."""
        competition = params.get('competition')
        limit = params.get('limit', 10)
        
        victories = self.stats_engine.get_biggest_victories(competition, limit)
        return {'biggest_victories': victories, 'count': len(victories)}
    
    def handle_stats_get_home_win_rate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stats.get_home_win_rate method."""
        competition = params.get('competition')
        
        rate = self.stats_engine.get_home_win_rate(competition)
        return {'home_win_rate': rate, 'competition': competition}
    
    def handle_stats_get_team_trend(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stats.get_team_trend method."""
        team = params.get('team')
        season = params.get('season')
        competition = params.get('competition')
        matches_back = params.get('matches_back', 10)
        
        trend = self.stats_engine.get_team_performance_trend(
            team, season, competition, matches_back
        )
        return trend
    
    def handle_stats_get_head_to_head_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stats.get_head_to_head_stats method."""
        team1 = params.get('team1')
        team2 = params.get('team2')
        
        return self.stats_engine.get_head_to_head_statistics(team1, team2)
    
    def handle_stats_get_competition_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stats.get_competition_summary method."""
        season = params.get('season')
        competition = params.get('competition')
        
        if season and competition:
            stats = self.stats_engine.get_competition_statistics(competition)
            return {'competition': competition, 'season': season, 'statistics': stats}
        elif season:
            summary = self.stats_engine.get_season_summary(season)
            return summary
        else:
            return {'error': 'season parameter required'}


# Create a default server instance
server = BrazilianSoccerMCP()
