#!/usr/bin/env python3
"""BDD Tests for Brazilian Soccer MCP Server."""

import pytest
import asyncio
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import (
    load_all_data,
    normalize_team_name,
    parse_date,
    query_matches,
    query_team_stats,
    query_player,
    query_competition,
    analyze_statistics
)


class TestTeamNameNormalization:
    """Test team name normalization."""
    
    def test_normalize_flamengo(self):
        """Test normalizing Flamengo variations."""
        assert normalize_team_name("Flamengo") == "flamengo"
        assert normalize_team_name("Flamengo-RJ") == "flamengo"
        assert normalize_team_name("flamengo") == "flamengo"
    
    def test_normalize_palmeiras(self):
        """Test normalizing Palmeiras variations."""
        assert normalize_team_name("Palmeiras") == "palmeiras"
        assert normalize_team_name("Palmeiras-SP") == "palmeiras"
        assert normalize_team_name("palmeiras") == "palmeiras"
    
    def test_normalize_atletico_mineiro(self):
        """Test normalizing Atletico Mineiro variations."""
        assert normalize_team_name("Atletico-MG") == "atletico mineiro"
        assert normalize_team_name("Atletico") == "atletico mineiro"
        assert normalize_team_name("atletico-mg-mg") == "atletico mineiro"


class TestDateParsing:
    """Test date parsing."""
    
    def test_parse_iso_date(self):
        """Test parsing ISO format dates."""
        date = parse_date("2023-09-03")
        assert date.year == 2023
        assert date.month == 9
        assert date.day == 3
    
    def test_parse_brazilian_date(self):
        """Test parsing Brazilian format dates."""
        date = parse_date("29/03/2003")
        assert date.year == 2003
        assert date.month == 3
        assert date.day == 29
    
    def test_parse_datetime(self):
        """Test parsing datetime with time."""
        date = parse_date("2023-09-03 18:30:00")
        assert date.year == 2023
        assert date.month == 9
        assert date.day == 3


def run_async(coro):
    """Helper to run async code in tests."""
    return asyncio.run(coro)


class TestMatchQueries:
    """Test match queries."""
    
    @pytest.fixture
    def data(self):
        """Load test data."""
        return load_all_data()
    
    def test_query_matches_by_team(self, data):
        """Test finding matches by team."""
        # Test with Flamengo
        results = run_async(query_matches(team="Flamengo", limit=5))
        assert len(results) == 1
        assert "Found" in results[0].text
        assert "matches:" in results[0].text.lower()
    
    def test_query_matches_between_teams(self, data):
        """Test finding matches between two teams."""
        # Test Flamengo vs Fluminense
        results = run_async(query_matches(team="Flamengo", opponent="Fluminense", limit=5))
        assert len(results) == 1
        assert "Found" in results[0].text
        assert "matches:" in results[0].text.lower()
    
    def test_query_matches_by_season(self, data):
        """Test finding matches by season."""
        results = run_async(query_matches(team="Palmeiras", season=2023, limit=5))
        assert len(results) == 1
        assert "Found" in results[0].text
        assert "matches:" in results[0].text.lower()
    
    def test_query_matches_by_competition(self, data):
        """Test finding matches by competition."""
        results = run_async(query_matches(competition="brasileirao", season=2023, limit=5))
        assert len(results) == 1
        assert "Found" in results[0].text
        assert "matches:" in results[0].text.lower()


class TestTeamQueries:
    """Test team queries."""
    
    @pytest.fixture
    def data(self):
        """Load test data."""
        return load_all_data()
    
    def test_query_team_stats(self, data):
        """Test getting team statistics."""
        results = run_async(query_team_stats(team="Palmeiras", season=2023))
        assert len(results) == 1
        assert "Team Statistics" in results[0].text
        assert "Palmeiras" in results[0].text
        assert "Matches:" in results[0].text
        assert "Wins:" in results[0].text
    
    def test_query_team_stats_flamengo(self, data):
        """Test getting Flamengo team statistics."""
        results = run_async(query_team_stats(team="Flamengo", season=2023))
        assert len(results) == 1
        assert "Team Statistics" in results[0].text
        assert "Flamengo" in results[0].text
    
    def test_query_team_stats_corinthians(self, data):
        """Test getting Corinthians team statistics."""
        results = run_async(query_team_stats(team="Corinthians", season=2022))
        assert len(results) == 1
        assert "Team Statistics" in results[0].text
        assert "Corinthians" in results[0].text


class TestPlayerQueries:
    """Test player queries."""
    
    @pytest.fixture
    def data(self):
        """Load test data."""
        return load_all_data()
    
    def test_query_player_by_name(self, data):
        """Test searching player by name."""
        results = run_async(query_player(name="Neymar"))
        assert len(results) == 1
        assert "Found" in results[0].text
        assert "Neymar" in results[0].text
    
    def test_query_player_by_nationality(self, data):
        """Test searching player by nationality."""
        results = run_async(query_player(nationality="Brazil", limit=5))
        assert len(results) == 1
        assert "Found" in results[0].text
        assert "players:" in results[0].text.lower()
    
    def test_query_player_by_club(self, data):
        """Test searching player by club."""
        results = run_async(query_player(club="Flamengo", limit=5))
        assert len(results) == 1
        assert "Found" in results[0].text
        assert "players:" in results[0].text.lower()


class TestCompetitionQueries:
    """Test competition queries."""
    
    @pytest.fixture
    def data(self):
        """Load test data."""
        return load_all_data()
    
    def test_query_competition(self, data):
        """Test getting competition information."""
        results = run_async(query_competition(competition="Brasileirao", season=2023))
        assert len(results) == 1
        assert "Matches in" in results[0].text or "Team Statistics" in results[0].text
    
    def test_query_competition_with_team(self, data):
        """Test getting competition standings for a team."""
        results = run_async(query_competition(competition="Brasileirao", season=2023, team="Palmeiras"))
        assert len(results) == 1
        assert "Team Statistics" in results[0].text
        assert "Palmeiras" in results[0].text
    
    def test_query_competition_libertadores(self, data):
        """Test getting Libertadores competition information."""
        results = run_async(query_competition(competition="Libertadores", season=2023))
        assert len(results) == 1
        assert "Matches in" in results[0].text or "Team Statistics" in results[0].text


class TestStatisticalAnalysis:
    """Test statistical analysis."""
    
    @pytest.fixture
    def data(self):
        """Load test data."""
        return load_all_data()
    
    def test_head_to_head(self, data):
        """Test head-to-head analysis."""
        results = run_async(analyze_statistics(statistic_type="head_to_head", team1="Flamengo", team2="Fluminense"))
        assert len(results) == 1
        assert "Head-to-Head" in results[0].text
        assert "Flamengo" in results[0].text
        assert "Fluminense" in results[0].text
    
    def test_biggest_wins(self, data):
        """Test biggest wins analysis."""
        results = run_async(analyze_statistics(statistic_type="biggest_wins", limit=3))
        assert len(results) == 1
        assert "Biggest wins" in results[0].text
        assert "Goal difference" in results[0].text
    
    def test_avg_goals(self, data):
        """Test average goals analysis."""
        results = run_async(analyze_statistics(statistic_type="avg_goals"))
        assert len(results) == 1
        assert "Average goals" in results[0].text
        assert "per match" in results[0].text
    
    def test_home_record(self, data):
        """Test home record analysis."""
        results = run_async(analyze_statistics(statistic_type="home_record", limit=3))
        assert len(results) == 1
        assert "Best home records" in results[0].text
        assert "W-" in results[0].text  # Wins


class TestIntegration:
    """Integration tests."""
    
    @pytest.fixture
    def data(self):
        """Load test data."""
        return load_all_data()
    
    def test_complex_query_flamengo_history(self, data):
        """Test complex query: Flamengo history."""
        # Find Flamengo matches
        match_results = run_async(query_matches(team="Flamengo", season=2023, limit=5))
        assert len(match_results) == 1
        assert "Found" in match_results[0].text
        
        # Get Flamengo stats
        stats_results = run_async(query_team_stats(team="Flamengo", season=2023))
        assert len(stats_results) == 1
        assert "Team Statistics" in stats_results[0].text
    
    def test_complex_query_player_stats(self, data):
        """Test complex query: Player statistics."""
        # Find Brazilian players
        player_results = run_async(query_player(nationality="Brazil", min_rating=85, limit=5))
        assert len(player_results) == 1
        assert "Found" in player_results[0].text
        assert "players:" in player_results[0].text.lower()
    
    def test_cross_file_query(self, data):
        """Test cross-file query: Player in team."""
        # Find players at Flamengo
        player_results = run_async(query_player(club="Flamengo", limit=3))
        assert len(player_results) == 1
        assert "Found" in player_results[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
