#!/usr/bin/env python3
"""
BDD-style tests for Brazilian Soccer MCP Server
"""

import pytest
import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import (
    load_data, 
    normalize_team_name, 
    get_team_matches, 
    get_head_to_head, 
    calculate_team_stats,
    calculate_standings,
    calculate_top_scorers,
    format_match,
    DATA
)


class TestDataLoading:
    """Test data loading functionality."""
    
    def test_data_loaded(self):
        """Test that all data files are loaded."""
        assert DATA is not None
        assert len(DATA) > 0
    
    def test_brasileirao_loaded(self):
        """Test Brasileirão data loaded."""
        assert 'brasileirao' in DATA
        assert len(DATA['brasileirao']) > 0
    
    def test_copa_brasil_loaded(self):
        """Test Copa do Brasil data loaded."""
        assert 'copa_brasil' in DATA
        assert len(DATA['copa_brasil']) > 0
    
    def test_libertadores_loaded(self):
        """Test Libertadores data loaded."""
        assert 'libertadores' in DATA
        assert len(DATA['libertadores']) > 0
    
    def test_br_football_loaded(self):
        """Test BR Football data loaded."""
        assert 'br_football' in DATA
        assert len(DATA['br_football']) > 0
    
    def test_brasileirao_hist_loaded(self):
        """Test Historical Brasileirão data loaded."""
        assert 'brasileirao_hist' in DATA
        assert len(DATA['brasileirao_hist']) > 0
    
    def test_fifa_loaded(self):
        """Test FIFA player data loaded."""
        assert 'fifa' in DATA
        assert len(DATA['fifa']) > 0


class TestTeamNormalization:
    """Test team name normalization."""
    
    def test_flamengo_normalization(self):
        """Test Flamengo name variations."""
        assert normalize_team_name("Flamengo") == "Flamengo"
        assert normalize_team_name("flamengo") == "Flamengo"
        assert normalize_team_name("Flamengo-RJ") == "Flamengo"
        assert normalize_team_name("flamengo-rj") == "Flamengo"
    
    def test_palmeiras_normalization(self):
        """Test Palmeiras name variations."""
        assert normalize_team_name("Palmeiras") == "Palmeiras"
        assert normalize_team_name("palmeiras") == "Palmeiras"
        assert normalize_team_name("Palmeiras-SP") == "Palmeiras"
        assert normalize_team_name("palmeiras-sp") == "Palmeiras"
    
    def test_sao_paulo_normalization(self):
        """Test São Paulo name variations."""
        assert normalize_team_name("São Paulo") == "São Paulo"
        assert normalize_team_name("sao paulo") == "São Paulo"
        assert normalize_team_name("São Paulo-SP") == "São Paulo"
    
    def test_corinthians_normalization(self):
        """Test Corinthians name variations."""
        assert normalize_team_name("Corinthians") == "Corinthians"
        assert normalize_team_name("Sport Club Corinthians Paulista") == "Corinthians"


class TestMatchQueries:
    """Test match query functionality."""
    
    def test_get_team_matches_flamengo(self):
        """Test getting Flamengo matches."""
        if 'brasileirao' in DATA:
            matches = get_team_matches(DATA['brasileirao'], "Flamengo")
            assert len(matches) > 0
            assert all("Flamengo" in str(row.get('home_team', '')) or 
                      "Flamengo" in str(row.get('away_team', '')) 
                      for _, row in matches.iterrows())
    
    def test_get_team_matches_palmeiras(self):
        """Test getting Palmeiras matches."""
        if 'brasileirao' in DATA:
            matches = get_team_matches(DATA['brasileirao'], "Palmeiras")
            assert len(matches) > 0
    
    def test_head_to_head_flamengo_fluminense(self):
        """Test Flamengo vs Fluminense head-to-head."""
        if 'brasileirao' in DATA:
            h2h = get_head_to_head(DATA['brasileirao'], "Flamengo", "Fluminense")
            assert h2h["team1"] == "Flamengo"
            assert h2h["team2"] == "Fluminense"
            assert h2h["total_matches"] > 0
    
    def test_head_to_head_palmeiras_santos(self):
        """Test Palmeiras vs Santos head-to-head."""
        if 'brasileirao' in DATA:
            h2h = get_head_to_head(DATA['brasileirao'], "Palmeiras", "Santos")
            assert h2h["total_matches"] > 0


class TestTeamStatistics:
    """Test team statistics calculation."""
    
    def test_calculate_team_stats(self):
        """Test team statistics calculation."""
        if 'brasileirao' in DATA and len(DATA['brasileirao']) > 0:
            matches = get_team_matches(DATA['brasileirao'], "Flamengo")
            stats = calculate_team_stats(matches, "Flamengo")
            
            assert stats["team"] == "Flamengo"
            assert stats["total_matches"] > 0
            assert stats["wins"] >= 0
            assert stats["draws"] >= 0
            assert stats["losses"] >= 0
            assert stats["goals_for"] >= 0
            assert stats["goals_against"] >= 0
            assert 0 <= stats["win_rate"] <= 100
    
    def test_palmeiras_2023_stats(self):
        """Test Palmeiras 2023 statistics."""
        if 'brasileirao' in DATA and 2023 in DATA['brasileirao']['season'].values:
            season_matches = DATA['brasileirao'][DATA['brasileirao']['season'] == 2023]
            palmeiras_matches = get_team_matches(season_matches, "Palmeiras")
            stats = calculate_team_stats(palmeiras_matches, "Palmeiras")
            assert stats["total_matches"] > 0


class TestCompetitionQueries:
    """Test competition and standings queries."""
    
    def test_calculate_standings(self):
        """Test standings calculation."""
        if 'brasileirao' in DATA:
            # Get matches for a specific season
            season = 2019
            season_matches = DATA['brasileirao'][DATA['brasileirao']['season'] == season]
            
            if len(season_matches) > 0:
                standings = calculate_standings(season_matches)
                assert len(standings) > 0
                assert standings[0]["points"] >= standings[-1]["points"]
    
    def test_top_scorers(self):
        """Test top scorers calculation."""
        if 'brasileirao' in DATA:
            top_scorers = calculate_top_scorers(DATA['brasileirao'].head(1000))
            assert len(top_scorers) > 0


class TestFormatMatch:
    """Test match formatting."""
    
    def test_format_match_basic(self):
        """Test basic match formatting."""
        row = {
            'datetime': '2023-09-03 18:00:00',
            'home_team': 'Flamengo-RJ',
            'away_team': 'Fluminense-RJ',
            'home_goal': 2,
            'away_goal': 1,
            'season': 2023,
            'round': 22
        }
        
        formatted = format_match(row)
        
        assert formatted['date'] == '2023-09-03'
        assert formatted['home_team'] == 'Flamengo'
        assert formatted['away_team'] == 'Fluminense'
        assert formatted['home_score'] == 2
        assert formatted['away_score'] == 1
        assert formatted['total_score'] == '2-1'


class TestBDDScenarios:
    """BDD-style scenario tests."""
    
    def test_scenario_find_matches_between_teams(self):
        """Scenario: Find matches between two teams."""
        # Given the match data is loaded
        assert 'brasileirao' in DATA
        # When I search for matches between "Flamengo" and "Fluminense"
        h2h = get_head_to_head(DATA['brasileirao'], "Flamengo", "Fluminense")
        # Then I should receive a list of matches
        assert h2h["total_matches"] > 0
        # And each match should have date, scores, and competition
        if len(h2h["matches"]) > 0:
            match = h2h["matches"][0]
            assert 'date' in match
            assert 'home_score' in match
            assert 'away_score' in match
    
    def test_scenario_get_team_statistics(self):
        """Scenario: Get team statistics."""
        # Given the match data is loaded
        assert 'brasileirao' in DATA
        # When I request statistics for "Palmeiras" in season "2023"
        if 'brasileirao' in DATA and 2023 in DATA['brasileirao']['season'].values:
            season_matches = DATA['brasileirao'][DATA['brasileirao']['season'] == 2023]
            palmeiras_matches = get_team_matches(season_matches, "Palmeiras")
            stats = calculate_team_stats(palmeiras_matches, "Palmeiras")
            # Then I should receive wins, losses, draws, and goals
            assert stats["total_matches"] > 0
            assert stats["wins"] >= 0
            assert stats["draws"] >= 0
            assert stats["losses"] >= 0
            assert stats["goals_for"] >= 0
            assert stats["goals_against"] >= 0
    
    def test_scenario_find_brazilian_players(self):
        """Scenario: Find Brazilian players."""
        # Given the player data is loaded
        assert 'fifa' in DATA
        # When I search for Brazilian players
        brazilian_players = DATA['fifa'][DATA['fifa']['Nationality'].str.contains('Brazil', case=False, na=False)]
        # Then I should receive a list of Brazilian players
        assert len(brazilian_players) > 0
    
    def test_scenario_find_players_at_fluminense(self):
        """Scenario: Find players at Fluminense."""
        # Given the player data is loaded
        assert 'fifa' in DATA
        # When I search for players at Fluminense
        fluminense_players = DATA['fifa'][DATA['fifa']['Club'].str.contains('Fluminense', case=False, na=False)]
        # Then I should receive a list of Fluminense players
        assert len(fluminense_players) > 0
    
    def test_scenario_find_top_brazilian_players(self):
        """Scenario: Find top Brazilian players."""
        # Given the player data is loaded
        assert 'fifa' in DATA
        # When I search for top Brazilian players
        brazilian_players = DATA['fifa'][DATA['fifa']['Nationality'].str.contains('Brazil', case=False, na=False)]
        top_brazilian = brazilian_players.sort_values('Overall', ascending=False).head(10)
        # Then I should receive the top Brazilian players
        assert len(top_brazilian) > 0
        # Verify they are sorted by overall rating
        if len(top_brazilian) > 1:
            assert top_brazilian.iloc[0]['Overall'] >= top_brazilian.iloc[-1]['Overall']
    
    def test_scenario_who_won_2019_brasileirao(self):
        """Scenario: Who won the 2019 Brasileirão?"""
        if 'brasileirao' in DATA:
            season_2019 = DATA['brasileirao'][DATA['brasileirao']['season'] == 2019]
            if len(season_2019) > 0:
                standings = calculate_standings(season_2019)
                assert len(standings) > 0
                assert standings[0]["team"] is not None


class TestPerformance:
    """Test query performance."""
    
    def test_simple_lookup_performance(self):
        """Test that simple lookups respond quickly."""
        import time
        
        # Simple lookup: find Flamengo vs Fluminense
        start = time.time()
        h2h = get_head_to_head(DATA['brasileirao'], "Flamengo", "Fluminense")
        elapsed = time.time() - start
        
        # Should respond in less than 2 seconds
        assert elapsed < 2, f"Query took {elapsed:.2f}s, expected < 2s"
    
    def test_aggregate_query_performance(self):
        """Test that aggregate queries respond quickly."""
        import time
        
        # Aggregate query: calculate standings
        start = time.time()
        standings = calculate_standings(DATA['brasileirao'].head(1000))
        elapsed = time.time() - start
        
        # Should respond in less than 5 seconds
        assert elapsed < 5, f"Query took {elapsed:.2f}s, expected < 5s"


class TestSampleQuestions:
    """Test sample questions from the specification."""
    
    def test_question_flamengo_last_play_corinthians(self):
        """Question: When did Flamengo last play Corinthians?"""
        if 'brasileirao' in DATA:
            # Find Flamengo vs Corinthians matches
            h2h = get_head_to_head(DATA['brasileirao'], "Flamengo", "Corinthians")
            assert h2h["total_matches"] > 0
            assert len(h2h["matches"]) > 0
    
    def test_question_who_is_neymar(self):
        """Question: Who is Neymar?"""
        assert 'fifa' in DATA
        neymar_players = DATA['fifa'][DATA['fifa']['Name'].str.contains('Neymar', case=False, na=False)]
        assert len(neymar_players) > 0
        assert any('Neymar Jr' in str(name) for name in neymar_players['Name'])
    
    def test_question_which_players_play_for_fluminense(self):
        """Question: Which players play for Fluminense?"""
        assert 'fifa' in DATA
        fluminense_players = DATA['fifa'][DATA['fifa']['Club'].str.contains('Fluminense', case=False, na=False)]
        assert len(fluminense_players) > 0
    
    def test_question_who_won_2019_brasileirao(self):
        """Question: Who won the 2019 Brasileirão?"""
        if 'brasileirao' in DATA:
            season_2019 = DATA['brasileirao'][DATA['brasileirao']['season'] == 2019]
            if len(season_2019) > 0:
                standings = calculate_standings(season_2019)
                assert len(standings) > 0
                assert standings[0]["team"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
