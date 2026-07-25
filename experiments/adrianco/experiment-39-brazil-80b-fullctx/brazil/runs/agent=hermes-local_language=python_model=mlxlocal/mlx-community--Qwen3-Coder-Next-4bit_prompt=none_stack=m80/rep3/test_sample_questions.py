"""Brazilian Soccer MCP Server - Sample Questions Test.

This module tests the ability to answer sample questions from the specification.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from soccer_data import SoccerDataLoader
from match_queries import MatchQueryEngine
from team_queries import TeamQueryEngine
from player_queries import PlayerQueryEngine
from competition_queries import CompetitionQueryEngine
from statistical_analysis import StatisticalAnalysisEngine


class TestSampleQuestions:
    """Test answering sample questions from the specification."""
    
    @pytest.fixture
    def engines(self):
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
    
    # Simple Lookups
    def test_when_did_flamengo_last_play_corinthians(self, engines):
        """When did Flamengo last play Corinthians?"""
        match_engine = engines['match_engine']
        matches = match_engine.find_matches(
            team1="Flamengo", team2="Corinthians", limit=5
        )
        
        assert len(matches) > 0, "Should find at least one match between Flamengo and Corinthians"
        assert all(
            ("Flamengo" in m['home_team'] or "Flamengo" in m['away_team']) and
            ("Corinthians" in m['home_team'] or "Corinthians" in m['away_team'])
            for m in matches
        )
    
    def test_score_of_flamengo_vs_corinthians(self, engines):
        """What was the score of Flamengo vs Corinthians?"""
        match_engine = engines['match_engine']
        matches = match_engine.find_matches(
            team1="Flamengo", team2="Corinthians", limit=1
        )
        
        if matches:
            match = matches[0]
            assert 'home_goal' in match
            assert 'away_goal' in match
            assert isinstance(match['home_goal'], int)
            assert isinstance(match['away_goal'], int)
    
    def test_who_is_gabriel_barbosa(self, engines):
        """Who is Gabriel Barbosa?"""
        player_engine = engines['player_engine']
        
        # Search by name
        players = player_engine.find_players(name="Gabriel", limit=5)
        
        # Should find players with "Gabriel" in their name
        assert len(players) > 0, "Should find players with 'Gabriel' in their name"
    
    # Relationship Queries
    def test_which_players_play_for_flamengo(self, engines):
        """Which players play for Flamengo?"""
        player_engine = engines['player_engine']
        players = player_engine.get_players_by_club("Flamengo", limit=10)
        
        assert isinstance(players, list), "Should return a list of players"
        assert len(players) > 0, "Should find players for Flamengo"
    
    def test_what_competitions_has_palmeiras_played_in(self, engines):
        """What competitions has Palmeiras played in?"""
        match_engine = engines['match_engine']
        matches = match_engine.find_matches(team1="Palmeiras", limit=10)
        
        competitions = set(m['competition'] for m in matches)
        assert len(competitions) > 0, "Should find competitions for Palmeiras"
    
    def test_show_all_derbies_in_2023(self, engines):
        """Show me all derbies in 2023."""
        match_engine = engines['match_engine']
        
        # Get Flamengo vs Fluminense matches (Fla-Flu derby)
        flau_flu_matches = match_engine.find_matches(
            team1="Flamengo", team2="Fluminense", season=2023, limit=10
        )
        
        # Get Palmeiras vs Santos matches (Derby Paulista)
        derby_paulista_matches = match_engine.find_matches(
            team1="Palmeiras", team2="Santos", season=2023, limit=10
        )
        
        assert isinstance(flau_flu_matches, list)
        assert isinstance(derby_paulista_matches, list)
    
    # Analytical Queries
    def test_which_team_has_the_best_home_record(self, engines):
        """Which team has the best home record?"""
        stat_engine = engines['stat_engine']
        
        # Get home advantage stats for 2019
        stats = stat_engine.get_home_advantage(competition="Brasileirão", season=2019)
        
        assert 'home_win_rate' in stats, "Should have home win rate"
        assert 'home_wins' in stats, "Should have home wins count"
    
    def test_who_are_the_top_brazilian_players(self, engines):
        """Who are the top Brazilian players?"""
        player_engine = engines['player_engine']
        players = player_engine.get_top_brazilian_players(limit=10)
        
        assert len(players) > 0, "Should find Brazilian players"
        assert all(p['nationality'] == 'Brazil' for p in players), "All should be Brazilian"
    
    def test_compare_2018_and_2019_seasons(self, engines):
        """Compare the 2018 and 2019 seasons."""
        stat_engine = engines['stat_engine']
        comparison = stat_engine.get_season_comparison(2018, 2019, competition="Brasileirão")
        
        assert 'season1_stats' in comparison, "Should have 2018 stats"
        assert 'season2_stats' in comparison, "Should have 2019 stats"
    
    # Competition Specific Questions
    def test_who_won_the_2019_brasileirao(self, engines):
        """Who won the 2019 Brasileirão?"""
        competition_engine = engines['competition_engine']
        champion = competition_engine.get_champion("Brasileirão", 2019)
        
        assert champion is not None, "Should have a champion"
        assert isinstance(champion, str), "Champion should be a string"
    
    def test_show_2018_copa_libertadores_bracket(self, engines):
        """Show the 2018 Copa Libertadores bracket."""
        competition_engine = engines['competition_engine']
        bracket = competition_engine.get_copa_libertadores_bracket(2018)
        
        assert 'stages' in bracket, "Should have stages"
        assert 'total_matches' in bracket, "Should have total matches"
    
    def test_which_teams_were_relegated_in_2020(self, engines):
        """Which teams were relegated in 2020?"""
        competition_engine = engines['competition_engine']
        relegated = competition_engine.get_relegated_teams("Brasileirão", 2020)
        
        assert isinstance(relegated, list), "Should return a list"
        assert len(relegated) > 0, "Should find relegated teams"
    
    # Statistical Analysis Questions
    def test_average_goals_per_match_in_brasileirao(self, engines):
        """What's the average goals per match in the Brasileirão?"""
        stat_engine = engines['stat_engine']
        stats = stat_engine.get_average_goals_per_match(competition="Brasileirão")
        
        assert 'average_goals_per_match' in stats, "Should have average goals"
        assert stats['average_goals_per_match'] > 0, "Average should be positive"
    
    def test_which_team_has_the_best_away_record(self, engines):
        """Which team has the best away record?"""
        stat_engine = engines['stat_engine']
        away_stats = stat_engine.get_best_away_teams(season=2019, competition="Brasileirão")
        
        assert isinstance(away_stats, list), "Should return a list"
        if len(away_stats) > 0:
            assert 'team' in away_stats[0], "Should have team name"
            assert 'points' in away_stats[0], "Should have points"
    
    def test_biggest_wins_in_dataset(self, engines):
        """Show me the biggest wins in the dataset."""
        stat_engine = engines['stat_engine']
        victories = stat_engine.get_biggest_victories(limit=10)
        
        assert len(victories) > 0, "Should find victories"
        assert all('goal_difference' in v for v in victories), "Should have goal difference"
    
    # Cross-file queries
    def test_player_and_match_data(self, engines):
        """Test cross-file query: player + match data."""
        player_engine = engines['player_engine']
        match_engine = engines['match_engine']
        
        # Find Flamengo players
        players = player_engine.get_players_by_club("Flamengo", limit=3)
        
        # Get Flamengo matches
        matches = match_engine.find_matches(team1="Flamengo", limit=3)
        
        assert len(players) > 0, "Should find Flamengo players"
        assert len(matches) > 0, "Should find Flamengo matches"


class TestBDDScenarios:
    """Test BDD scenarios from the specification."""
    
    @pytest.fixture
    def engines(self):
        """Create all engine instances."""
        loader = SoccerDataLoader()
        loader.load_all()
        
        match_engine = MatchQueryEngine(loader)
        team_engine = TeamQueryEngine(loader, match_engine)
        
        return {
            'match_engine': match_engine,
            'team_engine': team_engine
        }
    
    def test_bdd_find_matches_between_two_teams(self, engines):
        """BDD Scenario: Find matches between two teams."""
        match_engine = engines['match_engine']
        
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        matches = match_engine.find_matches(
            team1="Flamengo", team2="Fluminense", limit=10
        )
        
        # Then I should receive a list of matches
        assert isinstance(matches, list), "Should return a list"
        assert len(matches) > 0, "Should find matches"
        
        # And each match should have date, scores, and competition
        for match in matches:
            assert 'date' in match, "Should have date"
            assert 'home_goal' in match, "Should have home goal"
            assert 'away_goal' in match, "Should have away goal"
            assert 'competition' in match, "Should have competition"
    
    def test_bdd_get_team_statistics(self, engines):
        """BDD Scenario: Get team statistics."""
        team_engine = engines['team_engine']
        
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2023"
        stats = team_engine.get_team_statistics("Palmeiras", season=2023)
        
        # Then I should receive wins, losses, draws, and goals
        assert 'wins' in stats, "Should have wins"
        assert 'draws' in stats, "Should have draws"
        assert 'losses' in stats, "Should have losses"
        assert 'goals_for' in stats, "Should have goals for"
        assert 'goals_against' in stats, "Should have goals against"


class TestPerformance:
    """Test performance requirements."""
    
    @pytest.fixture
    def engines(self):
        """Create all engine instances."""
        loader = SoccerDataLoader()
        loader.load_all()
        
        match_engine = MatchQueryEngine(loader)
        team_engine = TeamQueryEngine(loader, match_engine)
        
        return {
            'match_engine': match_engine,
            'team_engine': team_engine
        }
    
    def test_simple_lookup_response_time(self, engines):
        """Simple lookups should respond in < 2 seconds."""
        import time
        
        match_engine = engines['match_engine']
        
        start_time = time.time()
        matches = match_engine.find_matches(team1="Flamengo", limit=10)
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0, f"Simple lookup took {elapsed}s, should be < 2s"
        assert len(matches) > 0, "Should find matches"
    
    def test_aggregate_query_response_time(self, engines):
        """Aggregate queries should respond in < 5 seconds."""
        import time
        
        stat_engine = StatisticalAnalysisEngine(
            SoccerDataLoader(), 
            engines['match_engine'],
            engines['team_engine']
        )
        
        start_time = time.time()
        stats = stat_engine.get_home_advantage(competition="Brasileirão", season=2019)
        elapsed = time.time() - start_time
        
        assert elapsed < 5.0, f"Aggregate query took {elapsed}s, should be < 5s"
        assert 'home_win_rate' in stats, "Should return statistics"


class TestDataCoverage:
    """Test data coverage requirements."""
    
    @pytest.fixture
    def engines(self):
        """Create all engine instances."""
        loader = SoccerDataLoader()
        loader.load_all()
        return loader
    
    def test_all_csv_files_loadable(self, engines):
        """All 6 CSV files should be loadable."""
        data = engines.data
        
        required_files = [
            'brasileirao', 'copa_brasil', 'libertadores', 
            'br_football', 'novo_campeonato', 'fifa_players'
        ]
        
        for required in required_files:
            assert required in data, f"Missing data for {required}"
            assert len(data[required]) > 0, f"Empty data for {required}"
    
    def test_at_least_20_sample_questions(self, engines):
        """At least 20 sample questions should be answerable."""
        # This test verifies that the system can answer sample questions
        # by testing various query types
        
        match_engine = MatchQueryEngine(engines)
        player_engine = PlayerQueryEngine(engines)
        team_engine = TeamQueryEngine(engines)
        competition_engine = CompetitionQueryEngine(engines, match_engine, team_engine)
        
        questions_answered = 0
        
        # Match queries
        if match_engine.find_matches(team1="Flamengo", limit=1):
            questions_answered += 1
        if match_engine.find_matches(competition="Brasileirão", season=2019, limit=1):
            questions_answered += 1
        if match_engine.find_matches(season=2023, limit=1):
            questions_answered += 1
        
        # Team queries
        if team_engine.get_team_statistics("Palmeiras", season=2023):
            questions_answered += 1
        if team_engine.get_team_head_to_head("Flamengo", "Corinthians"):
            questions_answered += 1
        if team_engine.get_teams_in_competition("Brasileirão", 2019):
            questions_answered += 1
        
        # Player queries
        if player_engine.find_players(name="Neymar", limit=1):
            questions_answered += 1
        if player_engine.get_brazilian_players(limit=1):
            questions_answered += 1
        if player_engine.get_players_by_club("Flamengo", limit=1):
            questions_answered += 1
        
        # Competition queries
        if competition_engine.get_champion("Brasileirão", 2019):
            questions_answered += 1
        if competition_engine.get_competition_standings("Brasileirão", 2019):
            questions_answered += 1
        if competition_engine.get_competition_results("Brasileirão", 2019, limit=1):
            questions_answered += 1
        
        assert questions_answered >= 20, f"Only answered {questions_answered} questions, need at least 20"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
