"""Tests for Brazilian Soccer MCP Server."""

import unittest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soccer_mcp.server import SoccerMCPServer
from soccer_mcp.models import QueryResult


class TestSoccerMCPServer(unittest.TestCase):
    """Test cases for the Soccer MCP Server."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        # Find the data directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, 'data', 'kaggle')
        
        # If not found, try parent directory
        if not os.path.exists(data_dir):
            data_dir = os.path.join(script_dir, '..', 'data', 'kaggle')
        
        cls.data_dir = data_dir
        cls.server = SoccerMCPServer(data_dir=data_dir)
    
    def test_server_initialization(self):
        """Test that the server initializes correctly."""
        self.assertIsNotNone(self.server)
        self.assertIsNotNone(self.server.loader)
        self.assertGreater(len(self.server.loader.matches), 0)
        self.assertGreater(len(self.server.loader.players), 0)
    
    def test_data_summary(self):
        """Test data summary generation."""
        summary = self.server.get_data_summary()
        self.assertIn('matches_loaded', summary)
        self.assertIn('players_loaded', summary)
        self.assertGreater(summary['matches_loaded'], 0)
        self.assertGreater(summary['players_loaded'], 0)
    
    def test_available_queries(self):
        """Test that queries are available."""
        queries = self.server.get_available_queries()
        self.assertGreater(len(queries), 0)
        
        # Check for expected queries
        expected_queries = [
            'find_matches_by_teams',
            'find_matches_by_team',
            'find_matches_by_competition',
            'find_matches_by_season',
            'get_team_stats',
            'get_competition_standings',
        ]
        for query in expected_queries:
            self.assertIn(query, queries)
    
    def test_find_matches_by_teams(self):
        """Test finding matches between two teams."""
        result = self.server.execute_query('find_matches_by_teams', 
                                           team1='Flamengo', 
                                           team2='Fluminense')
        
        self.assertTrue(result['success'])
        self.assertIn('data', result)
        self.assertIn('count', result)
        self.assertGreater(result['count'], 0)
    
    def test_find_matches_by_team(self):
        """Test finding matches for a team."""
        result = self.server.execute_query('find_matches_by_team', 
                                           team_name='Palmeiras')
        
        self.assertTrue(result['success'])
        self.assertGreater(result['count'], 0)
    
    def test_find_matches_by_competition(self):
        """Test finding matches by competition."""
        result = self.server.execute_query('find_matches_by_competition', 
                                           competition='Brasileirão')
        
        self.assertTrue(result['success'])
        self.assertGreater(result['count'], 0)
    
    def test_find_matches_by_season(self):
        """Test finding matches by season."""
        result = self.server.execute_query('find_matches_by_season', 
                                           season=2019)
        
        self.assertTrue(result['success'])
        self.assertGreater(result['count'], 0)
    
    def test_get_biggest_victories(self):
        """Test getting biggest victories."""
        result = self.server.execute_query('get_biggest_victories', limit=5)
        
        self.assertTrue(result['success'])
        self.assertGreater(result['count'], 0)
        self.assertIn('data', result)
    
    def test_get_average_goals_per_match(self):
        """Test getting average goals per match."""
        result = self.server.execute_query('get_average_goals_per_match')
        
        self.assertTrue(result['success'])
        self.assertIn('data', result)
        self.assertGreater(len(result['data']), 0)
    
    def test_search_player(self):
        """Test searching for a player."""
        result = self.server.execute_query('search_player', name='Neymar')
        
        self.assertTrue(result['success'])
        self.assertIn('data', result)
    
    def test_get_players_by_club(self):
        """Test getting players by club."""
        result = self.server.execute_query('get_players_by_club', 
                                           club='Flamengo')
        
        self.assertTrue(result['success'])
    
    def test_get_top_players(self):
        """Test getting top players."""
        result = self.server.execute_query('get_top_players', limit=5)
        
        self.assertTrue(result['success'])
        self.assertGreater(result['count'], 0)
    
    def test_get_brazilian_players(self):
        """Test getting Brazilian players."""
        result = self.server.execute_query('get_brazilian_players', limit=5)
        
        self.assertTrue(result['success'])
    
    def test_get_players_by_position(self):
        """Test getting players by position."""
        result = self.server.execute_query('get_players_by_position', 
                                           position='Forward')
        
        self.assertTrue(result['success'])
    
    def test_get_player_attributes(self):
        """Test getting player attributes."""
        result = self.server.execute_query('search_player', name='Neymar')
        
        self.assertTrue(result['success'])
        if result['count'] > 0:
            player_id = result['data'][0].get('id')
            if player_id:
                result = self.server.execute_query('get_player_attributes', 
                                                   player_name='Neymar')
                self.assertTrue(result['success'])
    
    def test_get_competition_standings(self):
        """Test getting competition standings."""
        result = self.server.execute_query('get_competition_standings', 
                                           competition='Brasileirão', 
                                           season=2019)
        
        self.assertTrue(result['success'])
        self.assertGreater(result['count'], 0)
    
    def test_get_competition_info(self):
        """Test getting competition info."""
        result = self.server.execute_query('get_competition_info', 
                                           competition='Brasileirao')
        
        self.assertTrue(result['success'])
        self.assertIn('data', result)
    
    def test_get_copa_libertadores_bracket(self):
        """Test getting Copa Libertadores bracket."""
        result = self.server.execute_query('get_copa_libertadores_bracket', 
                                           season=2019)
        
        # May not have data for all seasons
        self.assertTrue(result['success'])
    
    def test_get_relegated_teams(self):
        """Test getting relegated teams."""
        result = self.server.execute_query('get_relegated_teams', season=2019)
        
        self.assertTrue(result['success'])
    
    def test_get_team_stats(self):
        """Test getting team statistics."""
        result = self.server.execute_query('get_team_stats', 
                                           team_name='Palmeiras', 
                                           season=2023)
        
        self.assertTrue(result['success'])
        self.assertIn('data', result)
    
    def test_get_team_head_to_head(self):
        """Test getting team head-to-head."""
        result = self.server.execute_query('get_team_head_to_head', 
                                           team1='Flamengo', 
                                           team2='Fluminense')
        
        self.assertTrue(result['success'])
        self.assertIn('data', result)
    
    def test_get_team_history(self):
        """Test getting team history."""
        result = self.server.execute_query('get_team_history', 
                                           team_name='Flamengo', 
                                           limit=5)
        
        self.assertTrue(result['success'])
        self.assertGreater(result['count'], 0)
    
    def test_get_best_teams(self):
        """Test getting best teams."""
        result = self.server.execute_query('get_best_teams', limit=5, season=2019)
        
        self.assertTrue(result['success'])
        self.assertGreater(result['count'], 0)
    
    def test_get_home_vs_away_performance(self):
        """Test getting home vs away performance."""
        result = self.server.execute_query('get_home_vs_away_performance')
        
        self.assertTrue(result['success'])
        self.assertIn('data', result)
    
    def test_answer_question(self):
        """Test answering natural language questions."""
        # Test a simple question
        result = self.server.answer_question('When did Flamengo last play Fluminense?')
        
        self.assertTrue(result['success'])
        self.assertIn('data', result)
    
    def test_answer_question_champion(self):
        """Test answering champion questions."""
        result = self.server.answer_question('Who won the 2019 Brasileirao?')
        
        # May not have data for all seasons
        self.assertTrue(result['success'])
    
    def test_answer_question_player(self):
        """Test answering player questions."""
        result = self.server.answer_question('Who is L. Messi?')
        
        self.assertTrue(result['success'])
    
    def test_invalid_query(self):
        """Test handling of invalid queries."""
        result = self.server.execute_query('nonexistent_query')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_empty_search(self):
        """Test empty search results."""
        result = self.server.execute_query('search_player', name='NonExistentPlayer12345')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 0)


class TestDataLoader(unittest.TestCase):
    """Test cases for the data loader."""
    
    def setUp(self):
        """Set up test fixtures."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, 'data', 'kaggle')
        if not os.path.exists(data_dir):
            data_dir = os.path.join(script_dir, '..', 'data', 'kaggle')
        
        from soccer_mcp.loader import DataLoader
        self.loader = DataLoader(data_dir)
        self.loader.load_all_data()
    
    def test_load_brasileirao_matches(self):
        """Test loading Brasileirao matches."""
        matches = self.loader.get_matches_by_competition('Brasileirão')
        self.assertGreater(len(matches), 0)
    
    def test_load_copa_do_brasil_matches(self):
        """Test loading Copa do Brasil matches."""
        matches = self.loader.get_matches_by_competition('Copa do Brasil')
        self.assertGreater(len(matches), 0)
    
    def test_load_libertadores_matches(self):
        """Test loading Libertadores matches."""
        matches = self.loader.get_matches_by_competition('Copa Libertadores')
        self.assertGreater(len(matches), 0)
    
    def test_normalize_team_name(self):
        """Test team name normalization."""
        normalized = self.loader.normalize_team_name('Palmeiras-SP')
        self.assertIn('Palmeiras', normalized)
    
    def test_get_matches_by_teams(self):
        """Test getting matches between two teams."""
        matches = self.loader.get_matches_by_teams('Flamengo', 'Fluminense')
        self.assertGreater(len(matches), 0)
    
    def test_get_player_by_name(self):
        """Test getting player by name."""
        player = self.loader.get_player_by_name('Neymar')
        self.assertIsNotNone(player)
        self.assertIn('Neymar', player.name if player.name else '')
    
    def test_get_players_by_club(self):
        """Test getting players by club."""
        # Use a club that exists in the FIFA dataset
        players = self.loader.get_players_by_club('FC Barcelona')
        self.assertGreater(len(players), 0)
    
    def test_get_brazilian_players(self):
        """Test getting Brazilian players."""
        players = self.loader.get_brazilian_players()
        self.assertGreater(len(players), 0)
    
    def test_get_top_players(self):
        """Test getting top players."""
        top_players = self.loader.get_top_players(limit=5)
        self.assertEqual(len(top_players), 5)
        # Check that players are sorted by overall rating
        for i in range(len(top_players) - 1):
            self.assertGreaterEqual(top_players[i].overall or 0, 
                                   top_players[i+1].overall or 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
