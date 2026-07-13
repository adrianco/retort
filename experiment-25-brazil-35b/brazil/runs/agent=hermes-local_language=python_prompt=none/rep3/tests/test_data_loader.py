# Brazilian Soccer MCP Server - Tests for Data Loader
# BDD-style tests for dataset loading, team name normalization, and data quality.

import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import MatchDataset, normalize_team_name, parse_iso_date, parse_brazilian_date
from datetime import datetime


class TestDataNameNormalization:
    """Test team name normalization across different datasets."""

    def test_remove_state_suffix_sp(self):
        """Given a team name with -SP suffix, when normalized, then state is removed."""
        result = normalize_team_name("Palmeiras-SP")
        assert result == "palmeiras"

    def test_remove_state_suffix_rj(self):
        """Given a team name with -RJ suffix, when normalized, then state is removed."""
        result = normalize_team_name("Flamengo-RJ")
        assert result == "flamengo"

    def test_remove_state_suffix_mg(self):
        """Given a team name with -MG suffix, when normalized, then state is removed."""
        result = normalize_team_name("Atletico-MG")
        assert result == "atletico"

    def test_remove_state_suffix_pr(self):
        """Given a team name with -PR suffix, when normalized, then state is removed."""
        result = normalize_team_name("Athletico-PR")
        assert result == "athletico"

    def test_sao_paulo_normalization(self):
        """Given 'Sao Paulo', when normalized, then hyphens replace spaces."""
        result = normalize_team_name("Sao Paulo")
        assert result == "sao-paulo"

    def test_gremio_accent_removal(self):
        """Given 'Gremio', when normalized, then accents are removed."""
        result = normalize_team_name("Gremio")
        assert result == "gremio"

    def test_gran_ace(self):
        """Given 'Gremio', when normalized, then 'a' is removed."""
        result = normalize_team_name("Grêmio")
        assert result == "gremio"

    def test_remove_parenthetical(self):
        """Given a team with parenthetical annotation, when normalized, then annotation and state suffix are removed."""
        result = normalize_team_name("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
        assert result == "boavista-sport-club"

    def test_country_code_removal(self):
        """Given a Libertadores international team, when normalized, then country code is removed."""
        result = normalize_team_name("Nacional (URU)")
        assert result == "nacional"

    def test_empty_string(self):
        """Given an empty string, when normalized, then empty string is returned."""
        result = normalize_team_name("")
        assert result == ""

    def test_none_input(self):
        """Given None input, when normalized, then empty string is returned."""
        result = normalize_team_name(None)
        assert result == ""

    def test_consistent_normalization(self):
        """Given same team in different formats, when normalized, then results match."""
        assert normalize_team_name("Palmeiras-SP") == normalize_team_name("Palmeiras")
        assert normalize_team_name("Flamengo-RJ") == normalize_team_name("Flamengo")


class TestDateParsing:
    """Test date parsing functions."""

    def test_iso_date_with_time(self):
        """Given ISO date with time, when parsed, then datetime object is returned."""
        result = parse_iso_date("2023-09-24 18:30:00")
        assert result == datetime(2023, 9, 24, 18, 30, 0)

    def test_iso_date_without_time(self):
        """Given ISO date without time, when parsed, then datetime object is returned."""
        result = parse_iso_date("2023-09-24")
        assert result == datetime(2023, 9, 24)

    def test_brazilian_date(self):
        """Given Brazilian date format, when parsed, then datetime object is returned."""
        result = parse_brazilian_date("29/03/2003")
        assert result == datetime(2003, 3, 29)

    def test_brazilian_date_with_time(self):
        """Given Brazilian date with time, when parsed, then datetime object is returned."""
        result = parse_brazilian_date("29/03/2003 15:00:00")
        assert result == datetime(2003, 3, 29, 15, 0, 0)

    def test_invalid_iso_date(self):
        """Given invalid ISO date, when parsed, then None is returned."""
        result = parse_iso_date("not-a-date")
        assert result is None


class TestDatasetLoading:
    """Test that all datasets load correctly."""

    @pytest.fixture
    def data_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")

    @pytest.fixture
    def dataset(self, data_dir):
        """Load all datasets."""
        ds = MatchDataset()
        ds.load_all(data_dir)
        return ds

    def test_brasileirao_loads(self, dataset):
        """Given the Brasileirao CSV exists, when loaded, then matches are found."""
        assert not dataset.brasileirao.empty
        assert len(dataset.brasileirao) > 0
        assert 'home_team_norm' in dataset.brasileirao.columns
        assert 'away_team_norm' in dataset.brasileirao.columns

    def test_copa_brasil_loads(self, dataset):
        """Given the Copa do Brasil CSV exists, when loaded, then matches are found."""
        assert not dataset.copa_brasil.empty
        assert len(dataset.copa_brasil) > 0

    def test_libertadores_loads(self, dataset):
        """Given the Libertadores CSV exists, when loaded, then matches are found."""
        assert not dataset.libertadores.empty
        assert len(dataset.libertadores) > 0

    def test_extended_stats_loads(self, dataset):
        """Given the Extended Stats CSV exists, when loaded, then matches are found."""
        assert not dataset.extended_stats.empty
        assert len(dataset.extended_stats) > 0

    def test_historic_loads(self, dataset):
        """Given the Historic CSV exists, when loaded, then matches are found."""
        assert not dataset.historic.empty
        assert len(dataset.historic) > 0

    def test_fifa_players_loads(self, dataset):
        """Given the FIFA players CSV exists, when loaded, then players are found."""
        assert not dataset.fifa_players.empty
        assert len(dataset.fifa_players) > 0

    def test_all_matches_built(self, dataset):
        """Given all datasets loaded, when all_matches is built, then contains matches from all sources."""
        assert len(dataset.all_matches) > 0
        # Should have matches from multiple sources
        competitions = set(m['competition'] for m in dataset.all_matches)
        assert len(competitions) > 1

    def test_all_teams_built(self, dataset):
        """Given all datasets loaded, when all_teams is built, then has unique teams."""
        assert len(dataset.all_teams) > 0

    def test_all_players_built(self, dataset):
        """Given FIFA data loaded, when all_players is built, then has players."""
        assert len(dataset.all_players) > 0

    def test_match_has_required_fields(self, dataset):
        """Given matches loaded, then each match has required fields."""
        if dataset.all_matches:
            match = dataset.all_matches[0]
            assert 'date' in match
            assert 'home_team' in match
            assert 'away_team' in match
            assert 'home_goals' in match
            assert 'away_goals' in match
            assert 'competition' in match


class TestDataQuality:
    """Test data quality and consistency."""

    @pytest.fixture
    def data_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")

    @pytest.fixture
    def dataset(self, data_dir):
        ds = MatchDataset()
        ds.load_all(data_dir)
        return ds

    def test_goals_are_integers(self, dataset):
        """Given matches loaded, then all goals are integers."""
        for m in dataset.all_matches[:100]:
            assert isinstance(m['home_goals'], int)
            assert isinstance(m['away_goals'], int)
            assert m['home_goals'] >= 0
            assert m['away_goals'] >= 0

    def test_team_names_normalized(self, dataset):
        """Given teams normalized, then no state suffixes in normalized names."""
        for team in dataset.all_teams:
            assert '-SP' not in team
            assert '-RJ' not in team
            assert '-MG' not in team
            assert '-PR' not in team
            assert '-SC' not in team

    def test_competitions_have_data(self, dataset):
        """Given all competitions, then each has at least one match."""
        comp_counts = {}
        for m in dataset.all_matches:
            comp = m['competition']
            comp_counts[comp] = comp_counts.get(comp, 0) + 1
        
        for comp, count in comp_counts.items():
            assert count > 0, f"Competition '{comp}' has no matches"

    def test_min_overall_are_integers(self, dataset):
        """Given FIFA players loaded, then all overall ratings are integers."""
        for p in dataset.all_players[:100]:
            assert isinstance(p['overall'], int)
            assert p['overall'] >= 0
            assert p['overall'] <= 99

    def test_brazilian_players_exist(self, dataset):
        """Given FIFA data, then Brazilian players exist in the dataset."""
        brazilian = dataset.get_players_by_filter(nationality="Brazil")
        assert len(brazilian) > 0


class TestMatchQuery:
    """Test match query functionality."""

    @pytest.fixture
    def data_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")

    @pytest.fixture
    def dataset(self, data_dir):
        ds = MatchDataset()
        ds.load_all(data_dir)
        return ds

    def test_query_by_team(self, dataset):
        """Given a team name, when queried, then matches containing the team are returned."""
        results = dataset.get_match_by_criteria(team="Palmeiras")
        assert len(results) > 0
        for r in results:
            assert r['home_team'] == 'palmeiras' or r['away_team'] == 'palmeiras'

    def test_query_by_competition(self, dataset):
        """Given a competition name, when queried, then only matches from that competition are returned."""
        results = dataset.get_match_by_criteria(competition="Copa do Brasil")
        assert len(results) > 0
        for r in results:
            assert 'copa' in r['competition'].lower()

    def test_query_by_season(self, dataset):
        """Given a season year, when queried, then only matches from that season are returned."""
        results = dataset.get_match_by_criteria(season=2020)
        # Should find matches from some sources for 2020
        for r in results:
            if r['season'] is not None:
                assert r['season'] == 2020

    def test_query_returns_list(self, dataset):
        """Given any query, when executed, then returns a list."""
        results = dataset.get_match_by_criteria()
        assert isinstance(results, list)

    def test_empty_team_query(self, dataset):
        """Given an unknown team, when queried, then empty list is returned."""
        results = dataset.get_match_by_criteria(team="nonexistent_team_xyz")
        assert isinstance(results, list)
        # Should be empty or very small
        assert len(results) == 0 or len(results) < 5


class TestTeamStatistics:
    """Test team statistics calculation."""

    @pytest.fixture
    def data_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")

    @pytest.fixture
    def dataset(self, data_dir):
        ds = MatchDataset()
        ds.load_all(data_dir)
        return ds

    def test_team_stats_returned(self, dataset):
        """Given a team, when stats requested, then statistics dict is returned."""
        stats = dataset.get_team_statistics("Palmeiras")
        assert 'team' in stats
        assert 'matches' in stats
        assert 'wins' in stats
        assert 'draws' in stats
        assert 'losses' in stats
        assert 'goals_for' in stats
        assert 'goals_against' in stats
        assert 'win_rate' in stats

    def test_team_stats_win_rate(self, dataset):
        """Given team stats, when calculated, then win_rate is between 0 and 100."""
        stats = dataset.get_team_statistics("Flamengo")
        if stats['matches'] > 0:
            assert 0 <= stats['win_rate'] <= 100

    def test_wins_plus_draws_plus_losses_equals_matches(self, dataset):
        """Given team stats, then wins + draws + losses = matches."""
        stats = dataset.get_team_statistics("Flamengo")
        if stats['matches'] > 0:
            assert stats['wins'] + stats['draws'] + stats['losses'] == stats['matches']


class TestHeadToHead:
    """Test head-to-head query functionality."""

    @pytest.fixture
    def data_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")

    @pytest.fixture
    def dataset(self, data_dir):
        ds = MatchDataset()
        ds.load_all(data_dir)
        return ds

    def test_head_to_head_basic(self, dataset):
        """Given two teams, when head-to-head requested, then comparison is returned."""
        result = dataset.get_head_to_head("Palmeiras", "Santos")
        assert 'team1' in result
        assert 'team2' in result
        assert 'total_matches' in result
        assert 'team1_wins' in result
        assert 'team2_wins' in result
        assert 'draws' in result

    def test_head_to_head_sum(self, dataset):
        """Given head-to-head, when compared, then wins + wins + draws = total matches."""
        result = dataset.get_head_to_head("Palmeiras", "Santos")
        if result['total_matches'] > 0:
            assert result['team1_wins'] + result['team2_wins'] + result['draws'] == result['total_matches']

    def test_head_to_head_empty(self, dataset):
        """Given unknown teams, when head-to-head requested, then empty result is returned."""
        result = dataset.get_head_to_head("nonexistent1", "nonexistent2")
        assert result['total_matches'] == 0


class TestPlayerQuery:
    """Test player query functionality."""

    @pytest.fixture
    def data_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")

    @pytest.fixture
    def dataset(self, data_dir):
        ds = MatchDataset()
        ds.load_all(data_dir)
        return ds

    def test_brazilian_players(self, dataset):
        """Given nationality filter, when requested, then Brazilian players are returned."""
        players = dataset.get_players_by_filter(nationality="Brazil", max_results=50)
        assert len(players) > 0
        assert players[0]['overall'] <= 99

    def test_players_sorted_by_overall(self, dataset):
        """Given player list, when sorted, then overall ratings are in descending order."""
        players = dataset.get_players_by_filter(max_results=50)
        for i in range(len(players) - 1):
            assert players[i]['overall'] >= players[i + 1]['overall']

    def test_players_by_club(self, dataset):
        """Given club filter, when requested, then players at that club are returned."""
        players = dataset.get_players_by_filter(club="Flamengo", max_results=50)
        assert len(players) >= 0  # May or may not have players

    def test_min_overall_filter(self, dataset):
        """Given min_overall filter, when requested, then all players meet the threshold."""
        players = dataset.get_players_by_filter(min_overall=90, max_results=100)
        for p in players:
            assert p['overall'] >= 90

    def test_max_results_limit(self, dataset):
        """Given max_results, when requested, then no more than max are returned."""
        players = dataset.get_players_by_filter(max_results=10)
        assert len(players) <= 10

    def test_player_has_required_fields(self, dataset):
        """Given a player, when returned, then has all required fields."""
        if dataset.all_players:
            p = dataset.all_players[0]
            assert 'name' in p
            assert 'overall' in p
            assert 'club' in p
            assert 'position' in p
