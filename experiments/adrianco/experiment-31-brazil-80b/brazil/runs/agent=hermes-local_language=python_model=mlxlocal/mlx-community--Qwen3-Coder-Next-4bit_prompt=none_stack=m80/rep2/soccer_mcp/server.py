"""MCP Server for Brazilian Soccer Data."""

from typing import Dict, Any, List, Optional
import os

from soccer_mcp.loader import DataLoader
from soccer_mcp.queries import MatchQueries, PlayerQueries, CompetitionQueries, TeamQueries, StatisticalAnalysis


class SoccerMCPServer:
    """MCP Server for Brazilian Soccer Data.
    
    Provides natural language queries about players, teams, matches, and competitions.
    """
    
    def __init__(self, data_dir: str = None):
        """Initialize the MCP server.
        
        Args:
            data_dir: Path to the data directory containing CSV files.
                     Defaults to 'data/kaggle/' relative to this module.
        """
        if data_dir is None:
            # Default to data/kaggle relative to this module
            module_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(os.path.dirname(module_dir), 'data', 'kaggle')
        
        self.data_dir = data_dir
        self.loader = DataLoader(data_dir)
        self.loader.load_all_data()
        
        # Initialize query handlers
        self.match_queries = MatchQueries(self.loader)
        self.player_queries = PlayerQueries(self.loader)
        self.competition_queries = CompetitionQueries(self.loader)
        self.team_queries = TeamQueries(self.loader)
        self.stats_analysis = StatisticalAnalysis(self.loader)
        
        # Register query handlers
        self.handlers = {
            # Match queries
            'find_matches_by_teams': self.match_queries.find_matches_by_teams,
            'find_matches_by_team': self.match_queries.find_matches_by_team,
            'find_matches_by_competition': self.match_queries.find_matches_by_competition,
            'find_matches_by_season': self.match_queries.find_matches_by_season,
            'get_match_by_id': self.match_queries.get_match_by_id,
            'get_biggest_victories': self.match_queries.get_biggest_victories,
            'get_average_goals_per_match': self.match_queries.get_average_goals_per_match,
            
            # Player queries
            'search_player': self.player_queries.search_player,
            'get_players_by_club': self.player_queries.get_players_by_club,
            'get_top_players': self.player_queries.get_top_players,
            'get_brazilian_players': self.player_queries.get_brazilian_players,
            'get_players_by_position': self.player_queries.get_players_by_position,
            'get_player_attributes': self.player_queries.get_player_attributes,
            
            # Competition queries
            'get_competition_standings': self.competition_queries.get_competition_standings,
            'get_competition_info': self.competition_queries.get_competition_info,
            'get_copa_libertadores_bracket': self.competition_queries.get_copa_libertadores_bracket,
            'get_relegated_teams': self.competition_queries.get_relegated_teams,
            
            # Team queries
            'get_team_stats': self.team_queries.get_team_stats,
            'get_team_head_to_head': self.team_queries.get_team_head_to_head,
            'get_team_history': self.team_queries.get_team_history,
            'get_best_teams': self.team_queries.get_best_teams,
            'get_team_achievements': self.team_queries.get_team_achievements,
            
            # Statistical analysis
            'get_average_goals_per_match': self.stats_analysis.get_average_goals_per_match,
            'get_biggest_victories': self.stats_analysis.get_biggest_victories,
            'get_home_vs_away_performance': self.stats_analysis.get_home_vs_away_performance,
            'get_top_scorers_by_season': self.stats_analysis.get_top_scorers_by_season,
        }
    
    def execute_query(self, query_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a query by name.
        
        Args:
            query_name: Name of the query handler to execute
            **kwargs: Arguments to pass to the query handler
            
        Returns:
            QueryResult as a dictionary
        """
        handler = self.handlers.get(query_name)
        if handler is None:
            return {
                'success': False,
                'error': f"Unknown query: {query_name}",
                'data': [],
                'count': 0
            }
        
        try:
            result = handler(**kwargs)
            return {
                'success': result.success,
                'error': result.error,
                'data': result.data,
                'summary': result.summary,
                'count': result.count,
                'metadata': result.metadata
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0
            }
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded data."""
        return {
            'matches_loaded': len(self.loader.matches),
            'players_loaded': len(self.loader.players),
            'team_name_mappings': len(self.loader.team_name_mapping),
            'data_directory': self.data_dir
        }
    
    def get_available_queries(self) -> List[str]:
        """Get list of available query names."""
        return list(self.handlers.keys())
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """Try to answer a natural language question.
        
        This is a simple heuristic-based approach to detect the type of question
        and route it to the appropriate handler.
        
        Args:
            question: The natural language question
            
        Returns:
            Answer as a dictionary
        """
        question_lower = question.lower()
        
        # Detect question type and route to appropriate handler
        if 'vs' in question_lower or 'versus' in question_lower or 'head-to-head' in question_lower:
            # Try to extract team names
            teams = self._extract_team_names(question_lower)
            if len(teams) >= 2:
                return self.execute_query('find_matches_by_teams', team1=teams[0], team2=teams[1])
        
        if 'last time' in question_lower and ('play' in question_lower or 'match' in question_lower):
            teams = self._extract_team_names(question_lower)
            if len(teams) >= 2:
                return self.execute_query('find_matches_by_teams', team1=teams[0], team2=teams[1])
        
        if 'record' in question_lower and ('home' in question_lower or 'away' in question_lower):
            teams = self._extract_team_names(question_lower)
            if teams:
                return self.execute_query('get_team_stats', team_name=teams[0])
        
        if 'win' in question_lower and ('record' in question_lower or 'stats' in question_lower):
            teams = self._extract_team_names(question_lower)
            if teams:
                return self.execute_query('get_team_stats', team_name=teams[0])
        
        if 'champion' in question_lower or 'won' in question_lower or 'winner' in question_lower:
            if 'brasileirao' in question_lower or 'brasileiro' in question_lower:
                # Extract season
                season = self._extract_season(question_lower)
                if season:
                    return self.execute_query('get_competition_standings', competition='Brasileirao', season=season)
        
        if 'relegat' in question_lower:
            season = self._extract_season(question_lower)
            if season:
                return self.execute_query('get_relegated_teams', season=season)
        
        if 'top' in question_lower and 'player' in question_lower:
            limit = self._extract_limit(question_lower)
            return self.execute_query('get_top_players', limit=limit)
        
        if 'brazilian player' in question_lower or 'brazil player' in question_lower:
            limit = self._extract_limit(question_lower)
            return self.execute_query('get_brazilian_players', limit=limit)
        
        if 'club' in question_lower or 'team' in question_lower:
            teams = self._extract_team_names(question_lower)
            if teams:
                return self.execute_query('get_players_by_club', club=teams[0])
        
        if 'player' in question_lower:
            # Try to extract player name
            player_name = self._extract_player_name(question_lower)
            if player_name:
                return self.execute_query('search_player', name=player_name)
        
        # Handle "Who is/was..." questions that might be about players
        if question_lower.startswith('who is') or question_lower.startswith('who was'):
            player_name = self._extract_player_name(question_lower)
            if player_name:
                return self.execute_query('search_player', name=player_name)
        
        if 'average goals' in question_lower or 'goals per match' in question_lower:
            return self.execute_query('get_average_goals_per_match')
        
        if 'biggest win' in question_lower or 'biggest victory' in question_lower:
            return self.execute_query('get_biggest_victories')
        
        # Default: try to search for matches
        teams = self._extract_team_names(question_lower)
        if teams:
            return self.execute_query('find_matches_by_team', team_name=teams[0])
        
        return {
            'success': False,
            'error': 'Could not understand the question. Try asking about matches, teams, players, or competitions.',
            'data': [],
            'count': 0
        }
    
    def _extract_team_names(self, question: str) -> List[str]:
        """Extract team names from a question."""
        # Common Brazilian team names
        team_names = [
            'flamengo', 'fluminense', 'palmeiras', 'sao paulo', 'corinthians',
            'santos', 'gremio', 'internacional', 'botafogo', 'vasco',
            'crac', 'atletico', 'bahia', 'fortaleza', 'ceara',
            'brazil', 'brasil'
        ]
        
        found_teams = []
        for team in team_names:
            if team in question:
                # Normalize to common format
                if team == 'flamengo':
                    found_teams.append('Flamengo')
                elif team == 'fluminense':
                    found_teams.append('Fluminense')
                elif team == 'palmeiras':
                    found_teams.append('Palmeiras')
                elif team == 'sao paulo':
                    found_teams.append('Sao Paulo')
                elif team == 'corinthians':
                    found_teams.append('Corinthians')
                elif team == 'santos':
                    found_teams.append('Santos')
                elif team == 'gremio':
                    found_teams.append('Gremio')
                elif team == 'internacional':
                    found_teams.append('Internacional')
                elif team == 'botafogo':
                    found_teams.append('Botafogo')
                elif team == 'vasco':
                    found_teams.append('Vasco')
                elif team == 'atletico':
                    found_teams.append('Atletico-MG')
                else:
                    found_teams.append(team.title())
        
        return found_teams[:2]  # Return at most 2 teams
    
    def _extract_season(self, question: str) -> Optional[int]:
        """Extract a season/year from a question."""
        import re
        # Look for 4-digit years
        match = re.search(r'\b(19|20)\d{2}\b', question)
        if match:
            return int(match.group())
        return None
    
    def _extract_limit(self, question: str) -> int:
        """Extract a limit number from a question."""
        import re
        match = re.search(r'\b(\d+)\b', question)
        if match:
            return int(match.group())
        return 10  # Default limit
    
    def _extract_player_name(self, question: str) -> Optional[str]:
        """Extract a player name from a question."""
        # Common player names (Brazilian and international)
        player_names = [
            'neymar', 'messi', 'lionel messi', 'cristiano ronaldo', 'ronaldo', 'kaká',
            'ronaldinho', 'garrincha', 'pele', 'maradona', 'zico',
            'romario', 'rivaldo', 'dida', 'thiago silva', 'marquinhos',
            'casemiro', 'alisson', 'ederson', 'bruno henrique'
        ]
        
        question_lower = question.lower()
        for player in player_names:
            if player in question_lower:
                return player.title()
        
        return None
