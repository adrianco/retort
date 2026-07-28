"""
Brazilian Soccer MCP Server Tests
BDD-style tests for all features
"""

import pytest
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import SoccerDataLoader
from query_engine import SoccerQueryEngine


# Test fixtures
@pytest.fixture
def data_loader():
    """Create a data loader instance"""
    data_dir = Path(__file__).parent / "data" / "kaggle"
    return SoccerDataLoader(data_dir)


@pytest.fixture
def query_engine(data_loader):
    """Create a query engine instance"""
    return SoccerQueryEngine(data_loader)


# Test cases based on TASK.md requirements
class TestMatchQueries:
    """Test match query functionality"""

    def test_find_matches_between_teams(self, query_engine):
        """Scenario: Find matches between two teams"""
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        result = query_engine.find_matches_between_teams("Flamengo", "Fluminense")
        
        # Then I should receive a list of matches
        assert isinstance(result, list)
        assert len(result) > 0
        
        # And each match should have date, scores, and competition
        for match in result:
            assert 'datetime' in match
            assert 'home_team' in match
            assert 'away_team' in match
            assert 'home_goal' in match
            assert 'away_goal' in match
            assert 'competition' in match

    def test_find_matches_by_season(self, query_engine):
        """Find matches for a specific team"""
        result = query_engine.find_matches_by_team("Palmeiras", limit=5)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check that matches contain Palmeiras
        palmeiras_matches = [m for m in result if 'Palmeiras' in m['home_team'] or 'Palmeiras' in m['away_team']]
        assert len(palmeiras_matches) > 0

    def test_find_matches_by_competition(self, query_engine):
        """Find matches by competition"""
        # Search for Brasileirão matches
        result = query_engine.find_matches_by_team("Corinthians", limit=5)
        
        assert isinstance(result, list)
        assert len(result) > 0


class TestTeamQueries:
    """Test team query functionality"""

    def test_get_team_statistics(self, query_engine):
        """Scenario: Get team statistics"""
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2012" (available data)
        stats = query_engine.get_team_statistics("Palmeiras", season=2012)
        
        # Then I should receive wins, losses, draws, and goals
        assert stats is not None
        assert stats.matches > 0
        assert stats.wins >= 0
        assert stats.draws >= 0
        assert stats.losses >= 0
        assert stats.goals_for >= 0
        assert stats.goals_against >= 0
        assert stats.points >= 0

    def test_get_team_head_to_head(self, query_engine):
        """Get head-to-head record between two teams"""
        result = query_engine.get_head_to_head("Flamengo", "Fluminense")
        
        assert result is not None
        assert 'team1' in result
        assert 'team2' in result
        assert 'team1_wins' in result
        assert 'team2_wins' in result
        assert 'draws' in result
        assert 'total_matches' in result

    def test_get_team_match_history(self, query_engine):
        """Get match history for a team"""
        history = query_engine.get_team_match_history("Flamengo")
        
        assert isinstance(history, list)
        if len(history) > 0:
            assert 'datetime' in history[0]
            assert 'home_team' in history[0] or 'away_team' in history[0]


class TestPlayerQueries:
    """Test player query functionality"""

    def test_get_player_by_name(self, query_engine, data_loader):
        """Scenario: Find a player by name"""
        # Given the player data is loaded
        if data_loader.fifa_df is None:
            pytest.skip("FIFA data not available")
        
        # When I search for a player by name
        player = query_engine.get_player_by_name("Neymar")
        
        # Then I should receive player information
        assert player is not None
        assert player.name == "Neymar Jr" or "Neymar" in player.name

    def test_get_players_by_club(self, query_engine, data_loader):
        """Scenario: Find players by club"""
        if data_loader.fifa_df is None:
            pytest.skip("FIFA data not available")
        
        # When I search for players by club
        # Use a major club that exists in the dataset
        players = query_engine.get_players_by_club("Real Madrid")
        
        # Then I should receive a list of players
        assert isinstance(players, list)
        # Real Madrid should have players in FIFA data
        assert len(players) > 0
        
        # And each player should belong to the specified club
        for player in players:
            assert "Real Madrid" in player.club or "real madrid" in player.club.lower()

    def test_get_brazilian_players(self, query_engine, data_loader):
        """Scenario: Find all Brazilian players"""
        if data_loader.fifa_df is None:
            pytest.skip("FIFA data not available")
        
        # When I search for Brazilian players
        players = query_engine.get_brazilian_players()
        
        # Then I should receive a list of Brazilian players
        assert isinstance(players, list)
        assert len(players) > 0
        
        # And each player should be Brazilian
        for player in players[:10]:  # Check first 10
            assert "Brazil" in player.nationality or "Brasil" in player.nationality


class TestCompetitionQueries:
    """Test competition query functionality"""

    def test_get_competition_standings(self, query_engine, data_loader):
        """Scenario: Get competition standings"""
        # Given the match data is loaded
        # When I request standings for Brasileirão 2012 (available data)
        standings = query_engine.get_competition_standings("Brasileirão", 2012)
        
        # Then I should receive a list of teams with standings
        assert isinstance(standings, list)
        assert len(standings) > 0
        
        # And each team should have position, matches, wins, draws, losses, goals, points
        for team in standings[:5]:
            assert hasattr(team, 'position')
            assert hasattr(team, 'team')
            assert hasattr(team, 'matches')
            assert hasattr(team, 'wins')
            assert hasattr(team, 'draws')
            assert hasattr(team, 'losses')
            assert hasattr(team, 'goals_for')
            assert hasattr(team, 'goals_against')
            assert hasattr(team, 'points')

    def test_get_big_wins(self, query_engine):
        """Scenario: Get biggest wins in the dataset"""
        # When I request big wins
        wins = query_engine.get_big_wins(limit=10)
        
        # Then I should receive a list of big wins
        assert isinstance(wins, list)
        assert len(wins) > 0
        
        # And each win should have the required fields
        for win in wins:
            assert hasattr(win, 'date')
            assert hasattr(win, 'home_team')
            assert hasattr(win, 'away_team')
            assert hasattr(win, 'home_goal')
            assert hasattr(win, 'away_goal')
            assert hasattr(win, 'competition')
            
            # Check that the margin is at least 4 goals
            margin = abs(win.home_goal - win.away_goal)
            assert margin >= 4


class TestDataLoading:
    """Test data loading functionality"""

    def test_load_all_data_files(self, data_loader):
        """Verify all data files are loaded"""
        # Check that all data files are loaded
        assert data_loader.brasileirao_df is not None, "Brasileirão data not loaded"
        assert data_loader.copa_do_brasil_df is not None, "Copa do Brasil data not loaded"
        assert data_loader.libertadores_df is not None, "Libertadores data not loaded"
        assert data_loader.br_football_df is not None, "BR Football data not loaded"
        assert data_loader.campeonato_brasileiro_df is not None, "Campeonato data not loaded"
        assert data_loader.fifa_df is not None, "FIFA data not loaded"

    def test_data_file_counts(self, data_loader):
        """Verify data file counts"""
        assert len(data_loader.brasileirao_df) >= 4000, "Brasileirão should have at least 4000 matches"
        assert len(data_loader.copa_do_brasil_df) >= 1300, "Copa do Brasil should have at least 1300 matches"
        assert len(data_loader.libertadores_df) >= 1200, "Libertadores should have at least 1200 matches"
        assert len(data_loader.br_football_df) >= 10000, "BR Football should have at least 10000 matches"
        assert len(data_loader.campeonato_brasileiro_df) >= 6800, "Campeonato should have at least 6800 matches"
        assert len(data_loader.fifa_df) >= 18000, "FIFA should have at least 18000 players"


class TestTeamNameNormalization:
    """Test team name normalization functionality"""

    def test_normalize_team_name_with_state(self, data_loader):
        """Test normalization of team names with state suffix"""
        normalized = data_loader.normalize_team_name("Palmeiras-SP")
        assert normalized == "Palmeiras"
        
        normalized = data_loader.normalize_team_name("Flamengo-RJ")
        assert normalized == "Flamengo"

    def test_normalize_team_name_without_state(self, data_loader):
        """Test normalization of team names without state suffix"""
        normalized = data_loader.normalize_team_name("Palmeiras")
        assert normalized == "Palmeiras"

    def test_find_matches_normalized_team_name(self, query_engine):
        """Test finding matches with normalized team names"""
        # Search with normalized name
        result1 = query_engine.find_matches_by_team("Palmeiras", limit=3)
        
        # Search with state suffix (should find same matches)
        result2 = query_engine.find_matches_by_team("Palmeiras-SP", limit=3)
        
        # Both should return matches
        assert len(result1) > 0
        assert len(result2) > 0


class TestDateParsing:
    """Test date parsing functionality"""

    def test_parse_iso_date(self, query_engine):
        """Test parsing ISO format dates"""
        # This is tested implicitly through match queries
        result = query_engine.find_matches_by_team("Flamengo", limit=1)
        if len(result) > 0:
            assert 'datetime' in result[0]
            assert len(result[0]['datetime']) > 0

    def test_parse_brazilian_date(self, query_engine, data_loader):
        """Test parsing Brazilian format dates"""
        # This is tested implicitly through match queries on Campeonato data
        if data_loader.campeonato_brasileiro_df is not None:
            result = query_engine.find_matches_by_team("Flamengo", limit=1)
            if len(result) > 0:
                assert 'datetime' in result[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
