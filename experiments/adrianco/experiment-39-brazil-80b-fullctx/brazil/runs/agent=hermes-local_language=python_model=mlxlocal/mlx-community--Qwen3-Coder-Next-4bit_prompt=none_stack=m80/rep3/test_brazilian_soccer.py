"""Brazilian Soccer MCP Server - Tests."""

import pytest
import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from soccer_data import SoccerDataLoader
from match_queries import MatchQueryEngine
from team_queries import TeamQueryEngine
from player_queries import PlayerQueryEngine
from competition_queries import CompetitionQueryEngine
from statistical_analysis import StatisticalAnalysisEngine


class TestDataLoading:
    """Test data loading functionality."""
    
    def test_load_brasileirao_matches(self):
        """Test loading Brasileirão matches."""
        loader = SoccerDataLoader()
        df = loader.load_brasileirao_matches()
        assert df is not None
        assert len(df) > 0
        assert 'home_team' in df.columns
        assert 'away_team' in df.columns
        assert 'home_goal' in df.columns
        assert 'away_goal' in df.columns
    
    def test_load_copa_do_brasil_matches(self):
        """Test loading Copa do Brasil matches."""
        loader = SoccerDataLoader()
        df = loader.load_copa_do_brasil_matches()
        assert df is not None
        assert len(df) > 0
        assert 'home_team' in df.columns
        assert 'away_team' in df.columns
    
    def test_load_libertadores_matches(self):
        """Test loading Libertadores matches."""
        loader = SoccerDataLoader()
        df = loader.load_libertadores_matches()
        assert df is not None
        assert len(df) > 0
        assert 'home_team' in df.columns
        assert 'away_team' in df.columns
    
    def test_load_br_football_dataset(self):
        """Test loading BR Football Dataset."""
        loader = SoccerDataLoader()
        df = loader.load_br_football_dataset()
        assert df is not None
        assert len(df) > 0
    
    def test_load_novo_campeonato(self):
        """Test loading novo campeonato."""
        loader = SoccerDataLoader()
        df = loader.load_novo_campeonato()
        assert df is not None
        assert len(df) > 0
    
    def test_load_fifa_players(self):
        """Test loading FIFA player data."""
        loader = SoccerDataLoader()
        df = loader.load_fifa_players()
        assert df is not None
        assert len(df) > 0
        assert 'Name' in df.columns
        assert 'Overall' in df.columns


class TestMatchQueries:
    """Test match query functionality."""
    
    @pytest.fixture
    def match_engine(self):
        """Create a match engine instance."""
        loader = SoccerDataLoader()
        loader.load_all()
        return MatchQueryEngine(loader)
    
    def test_find_matches_by_team(self, match_engine):
        """Test finding matches by team."""
        matches = match_engine.find_matches(team1="Flamengo", limit=10)
        assert len(matches) > 0
        assert all("Flamengo" in m['home_team'] or "Flamengo" in m['away_team'] 
                   for m in matches)
    
    def test_find_matches_by_competition(self, match_engine):
        """Test finding matches by competition."""
        matches = match_engine.find_matches(competition="Brasileirão", limit=10)
        assert len(matches) > 0
        assert all(m['competition'] == "Brasileirão" for m in matches)
    
    def test_find_matches_by_season(self, match_engine):
        """Test finding matches by season."""
        # Use 2022 as the latest season available in the datasets
        matches = match_engine.find_matches(season=2022, limit=10)
        assert len(matches) > 0
        assert all(m['season'] == 2022 for m in matches)
    
    def test_get_head_to_head(self, match_engine):
        """Test getting head-to-head between two teams."""
        h2h = match_engine.get_head_to_head("Flamengo", "Fluminense", limit=10)
        assert 'statistics' in h2h
        assert 'Flamengo' in h2h['statistics']
        assert 'Fluminense' in h2h['statistics']
        assert 'total_matches' in h2h['statistics']
    
    def test_get_team_match_history(self, match_engine):
        """Test getting team match history."""
        history = match_engine.get_team_match_history("Palmeiras", limit=10)
        assert len(history) > 0
        assert all("Palmeiras" in m['home_team'] or "Palmeiras" in m['away_team'] 
                   for m in history)


class TestTeamQueries:
    """Test team query functionality."""
    
    @pytest.fixture
    def team_engine(self):
        """Create a team engine instance."""
        loader = SoccerDataLoader()
        loader.load_all()
        return TeamQueryEngine(loader)
    
    def test_get_team_statistics(self, team_engine):
        """Test getting team statistics."""
        # Use 2022 as the latest season available in the datasets
        stats = team_engine.get_team_statistics("Palmeiras", season=2022)
        assert 'team' in stats
        assert 'wins' in stats
        assert 'draws' in stats
        assert 'losses' in stats
        assert 'points' in stats
    
    def test_get_team_head_to_head(self, team_engine):
        """Test getting team head-to-head."""
        h2h = team_engine.get_team_head_to_head("Flamengo", "Corinthians")
        assert 'team1' in h2h
        assert 'team2' in h2h
        assert 'total_matches' in h2h
    
    def test_get_team_players(self, team_engine):
        """Test getting team players."""
        players = team_engine.get_team_players("Flamengo")
        assert isinstance(players, list)
    
    def test_get_top_scorers(self, team_engine):
        """Test getting top scorers."""
        scorers = team_engine.get_top_scorers(season=2022, limit=5)
        assert len(scorers) > 0
        assert all('team' in s and 'goals' in s for s in scorers)

    def test_get_teams_in_competition(self, team_engine):
        """Test getting teams in a competition."""
        teams = team_engine.get_teams_in_competition("Brasileirão", season=2022)
        assert isinstance(teams, list)
        assert len(teams) > 0


class TestPlayerQueries:
    """Test player query functionality."""
    
    @pytest.fixture
    def player_engine(self):
        """Create a player engine instance."""
        loader = SoccerDataLoader()
        loader.load_all()
        return PlayerQueryEngine(loader)
    
    def test_find_players_by_name(self, player_engine):
        """Test finding players by name."""
        players = player_engine.find_players(name="Neymar", limit=5)
        assert len(players) > 0
        assert any("Neymar" in p['name'] for p in players)
    
    def test_find_brazilian_players(self, player_engine):
        """Test finding Brazilian players."""
        players = player_engine.get_brazilian_players(limit=10)
        assert len(players) > 0
        assert all(p['nationality'] == 'Brazil' for p in players)
    
    def test_find_players_by_club(self, player_engine):
        """Test finding players by club."""
        players = player_engine.get_players_by_club("Flamengo", limit=5)
        assert isinstance(players, list)
    
    def test_find_players_by_position(self, player_engine):
        """Test finding players by position."""
        players = player_engine.find_players(position="ST", min_overall=85, limit=5)
        assert len(players) > 0
        assert all("ST" in p['position'] for p in players)
    
    def test_get_player_by_id(self, player_engine):
        """Test getting player by ID."""
        players = player_engine.find_players(min_overall=90, limit=1)
        if players:
            player_id = players[0]['id']
            player = player_engine.get_player(player_id)
            assert player is not None
            assert player['id'] == player_id


class TestCompetitionQueries:
    """Test competition query functionality."""
    
    @pytest.fixture
    def competition_engine(self):
        """Create a competition engine instance."""
        loader = SoccerDataLoader()
        loader.load_all()
        return CompetitionQueryEngine(loader)
    
    def test_get_competition_standings(self, competition_engine):
        """Test getting competition standings."""
        standings = competition_engine.get_competition_standings("Brasileirão", 2019)
        assert isinstance(standings, list)
        assert len(standings) > 0
        assert all('team' in s and 'points' in s for s in standings)
    
    def test_get_champion(self, competition_engine):
        """Test getting champion."""
        champion = competition_engine.get_champion("Brasileirão", 2019)
        assert champion is not None
        assert isinstance(champion, str)
    
    def test_get_competition_results(self, competition_engine):
        """Test getting competition results."""
        results = competition_engine.get_competition_results(
            "Brasileirão", season=2019, limit=10
        )
        assert len(results) > 0
    
    def test_get_relegated_teams(self, competition_engine):
        """Test getting relegated teams."""
        relegated = competition_engine.get_relegated_teams("Brasileirão", 2019)
        assert isinstance(relegated, list)
        assert len(relegated) > 0


class TestStatisticalAnalysis:
    """Test statistical analysis functionality."""
    
    @pytest.fixture
    def stat_engine(self):
        """Create a statistical analysis engine instance."""
        loader = SoccerDataLoader()
        loader.load_all()
        return StatisticalAnalysisEngine(loader)
    
    def test_get_average_goals_per_match(self, stat_engine):
        """Test getting average goals per match."""
        stats = stat_engine.get_average_goals_per_match(competition="Brasileirão", season=2019)
        assert 'average_goals_per_match' in stats
        assert 'total_matches' in stats
    
    def test_get_home_advantage(self, stat_engine):
        """Test getting home advantage statistics."""
        stats = stat_engine.get_home_advantage(competition="Brasileirão", season=2019)
        assert 'home_win_rate' in stats
        assert 'home_wins' in stats
        assert 'away_wins' in stats
    
    def test_get_biggest_victories(self, stat_engine):
        """Test getting biggest victories."""
        victories = stat_engine.get_biggest_victories(competition="Brasileirão", limit=5)
        assert len(victories) > 0
        assert all('goal_difference' in v for v in victories)
    
    def test_get_top_teams_by_win_rate(self, stat_engine):
        """Test getting top teams by win rate."""
        teams = stat_engine.get_top_teams_by_win_rate(season=2019)
        assert isinstance(teams, list)
        if len(teams) > 0:
            assert 'team' in teams[0]
            assert 'win_rate' in teams[0]
    
    def test_get_team_performance_trend(self, stat_engine):
        """Test getting team performance trend."""
        trend = stat_engine.get_team_performance_trend("Flamengo", season=2023, last_n=5)
        if 'results' in trend:
            assert isinstance(trend['results'], list)
            assert len(trend['results']) > 0
    
    def test_get_season_comparison(self, stat_engine):
        """Test comparing two seasons."""
        comparison = stat_engine.get_season_comparison(2018, 2019, competition="Brasileirão")
        assert 'season1_stats' in comparison
        assert 'season2_stats' in comparison


class TestIntegration:
    """Integration tests for the entire system."""
    
    @pytest.fixture
    def all_engines(self):
        """Create all engine instances."""
        loader = SoccerDataLoader()
        loader.load_all()
        
        match_engine = MatchQueryEngine(loader)
        team_engine = TeamQueryEngine(loader, match_engine)
        player_engine = PlayerQueryEngine(loader)
        competition_engine = CompetitionQueryEngine(loader, match_engine, team_engine)
        stat_engine = StatisticalAnalysisEngine(loader, match_engine, team_engine)
        
        return {
            'loader': loader,
            'match_engine': match_engine,
            'team_engine': team_engine,
            'player_engine': player_engine,
            'competition_engine': competition_engine,
            'stat_engine': stat_engine
        }
    
    def test_all_csv_files_loadable(self, all_engines):
        """All 6 CSV files should be loadable."""
        loader = all_engines['loader']
        data = loader.dataframes
        
        required_files = [
            'brasileirao', 'copa_brasil', 'libertadores', 
            'br_football', 'novo_campeonato', 'fifa_players'
        ]
        
        for required in required_files:
            assert required in data, f"Missing data for {required}"
            assert len(data[required]) > 0, f"Empty data for {required}"
    
    def test_cross_file_player_match_query(self, all_engines):
        """Test cross-file query: find players and their team's matches."""
        player_engine = all_engines['player_engine']
        match_engine = all_engines['match_engine']
        
        # Find Flamengo players
        players = player_engine.get_players_by_club("Flamengo", limit=5)
        assert len(players) > 0
        
        # Get Flamengo matches
        matches = match_engine.find_matches(team1="Flamengo", limit=5)
        assert len(matches) > 0
    
    def test_full_workflow(self, all_engines):
        """Test a complete workflow."""
        competition_engine = all_engines['competition_engine']
        stat_engine = all_engines['stat_engine']
        
        # Get 2019 Brasileirão champion
        champion = competition_engine.get_champion("Brasileirão", 2019)
        assert champion is not None
        
        # Get statistics for that champion
        stats = stat_engine.get_home_advantage(
            competition="Brasileirão", season=2019
        )
        assert 'home_win_rate' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
