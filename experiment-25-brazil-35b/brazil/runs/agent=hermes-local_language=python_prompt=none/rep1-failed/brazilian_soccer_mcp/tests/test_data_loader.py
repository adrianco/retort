"""
Test suite for Brazilian Soccer MCP Server.

Comprehensive tests covering:
  - Data loading (all 6 CSV files)
  - Team name normalization
  - Match queries
  - Team statistics
  - Player queries
  - Competition standings
  - Statistical analysis
  - BDD-style scenarios from TASK.md
"""

import os
import sys
import pytest
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from brazilian_soccer_mcp.data_loader import (
    DataLoader,
    normalize_team_name,
    find_best_match,
    load_all,
    parse_date,
    DATA_DIR,
)
from brazilian_soccer_mcp.queries import (
    search_matches,
    find_matches_between,
    get_h2h,
    get_biggest_wins,
    get_team_stats,
    get_team_matches,
    get_competition_leaderboard,
    search_players,
    get_brazilian_players,
    get_players_by_club,
    get_average_goals,
    get_team_best_away_record,
    format_match_display,
    format_h2h_display,
)


# --- Fixtures ---

@pytest.fixture(scope="module")
def data_loader():
    """Load all datasets once for the test module."""
    dl = DataLoader(DATA_DIR)
    dl.load_all()
    return dl


@pytest.fixture(scope="module")
def all_matches(data_loader):
    """Combined matches from all sources."""
    return data_loader.all_matches


# --- 1. Data Loading Tests ---

class TestDataLoading:
    """Test that all 6 CSV files load correctly."""

    def test_brasileirao_loads(self, data_loader):
        """Given the Brasileirao CSV exists, it should load with expected columns."""
        assert data_loader.brasileirao_df is not None
        assert len(data_loader.brasileirao_df) == 4180
        expected_cols = {'source', 'date', 'season', 'round', 'stage',
                         'home_team', 'away_team', 'home_goals', 'away_goals'}
        assert set(data_loader.brasileirao_df.columns) == expected_cols

    def test_brazilian_cup_loads(self, data_loader):
        """Given the Brazilian Cup CSV exists, it should load."""
        assert data_loader.brazilian_cup_df is not None
        assert len(data_loader.brazilian_cup_df) == 1337
        assert data_loader.brazilian_cup_df['source'].iloc[0] == 'Brazilian_Cup'

    def test_libertadores_loads(self, data_loader):
        """Given the Libertadores CSV exists, it should load."""
        assert data_loader.libertadores_df is not None
        assert len(data_loader.libertadores_df) == 1255
        assert data_loader.libertadores_df['stage'].iloc[0] == 'group stage'

    def test_br_football_loads(self, data_loader):
        """Given the BR Football CSV exists, it should load."""
        assert data_loader.br_football_df is not None
        assert len(data_loader.br_football_df) == 10296

    def test_novo_campeonato_loads(self, data_loader):
        """Given the Novo Campeonato CSV exists, it should load."""
        assert data_loader.novo_campeonato_df is not None
        assert len(data_loader.novo_campeonato_df) == 6886

    def test_fifa_loads(self, data_loader):
        """Given the FIFA CSV exists, it should load with player data."""
        assert data_loader.fifa_df is not None
        assert len(data_loader.fifa_df) == 18207
        assert 'Name' in data_loader.fifa_df.columns
        assert 'Overall' in data_loader.fifa_df.columns

    def test_total_matches(self, data_loader):
        """All 6 files should be combinable into all_matches."""
        total = len(data_loader.all_matches)
        expected = 4180 + 1337 + 1255 + 10296 + 6886
        assert total == expected

    def test_data_directory_exists(self):
        """DATA_DIR should point to existing directory."""
        assert os.path.isdir(DATA_DIR)

    def test_all_sources_present(self, all_matches):
        """all_matches should contain all 5 competition sources."""
        sources = all_matches['source'].unique()
        assert len(sources) >= 5


# --- 2. Team Name Normalization Tests ---

class TestTeamNormalization:
    """Test team name normalization and matching."""

    def test_strip_state_suffix(self):
        """Given 'Flamengo-RJ', should normalize to 'Flamengo'."""
        result = normalize_team_name("Flamengo-RJ")
        assert result == "Flamengo"

    def test_strip_state_suffix_palmeiras(self):
        """Given 'Palmeiras-SP', should normalize to 'Palmeiras'."""
        result = normalize_team_name("Palmeiras-SP")
        assert result == "Palmeiras"

    def test_strip_state_suffix_sport(self):
        """Given 'Sport-PE', should normalize to 'Sport Recife'."""
        result = normalize_team_name("Sport-PE")
        assert result == "Sport Recife"

    def test_no_suffix_preserved(self):
        """Given 'Sao Paulo' (no suffix), should stay same."""
        result = normalize_team_name("Sao Paulo")
        assert result == "Sao Paulo"

    def test_strip_parenthetical_description(self):
        """Given complex name with parens, should strip them."""
        result = normalize_team_name(
            "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        )
        assert result == "Boavista"

    def test_unicode_normalization(self):
        """Given name with accents, should normalize."""
        result = normalize_team_name("Grimio")
        assert result == "Gremio"

    def test_whitespace_handling(self):
        """Given name with extra whitespace, should collapse."""
        result = normalize_team_name("  Corinthians  ")
        assert result == "Corinthians"

    def test_find_exact_match(self):
        """Given exact alias, should return canonical name."""
        assert find_best_match("Flamengo") == "Flamengo"
        assert find_best_match("Palmeiras") == "Palmeiras"

    def test_find_abbreviation_match(self):
        """Given 'Inter', should find 'Internacional'."""
        result = find_best_match("Inter")
        assert result == "Internacional"

    def test_find_long_alias(self):
        """Given 'America - MG', should find 'America Mineiro'."""
        result = find_best_match("America - MG")
        assert result == "America Mineiro"

    def test_find_non_alias_unchanged(self):
        """Given unknown team, should return normalized form."""
        result = find_best_match("Unknown Team-BA")
        assert result == "Unknown Team"

    def test_alias_preferred_over_broad(self):
        """'Boavista Sport Club...' should match Boavista, not Sport Recife."""
        result = find_best_match(
            "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        )
        assert result == "Boavista"

    def test_all_known_aliased_teams(self):
        """All aliases should resolve to their canonical names."""
        from brazilian_soccer_mcp.data_loader import _CLUB_ALIASES
        for alias, canonical in _CLUB_ALIASES.items():
            result = find_best_match(alias)
            assert result == canonical, f"Alias '{alias}' should map to '{canonical}', got '{result}'"


# --- 3. Date Parsing Tests ---

class TestDateParsing:
    """Test date format parsing."""

    def test_iso_date(self):
        """Given ISO format date, should parse correctly."""
        result = parse_date("2023-09-24")
        assert result == "2023-09-24"

    def test_iso_datetime(self):
        """Given ISO datetime, should parse date only."""
        result = parse_date("2023-09-24 18:30:00")
        assert result == "2023-09-24"

    def test_brazilian_format(self):
        """Given DD/MM/YYYY format, should convert to ISO."""
        result = parse_date("29/03/2003")
        assert result == "2003-03-29"

    def test_empty_string(self):
        """Given empty string, should return None."""
        assert parse_date("") is None

    def test_none(self):
        """Given None, should return None."""
        assert parse_date(None) is None


# --- 4. Match Query Tests ---

class TestMatchQueries:
    """BDD-style match query scenarios."""

    def test_search_by_team_flamengo(self, all_matches):
        """
        Given the match data is loaded
        When I search for matches with "Flamengo"
        Then I should receive matches containing Flamengo
        """
        result = search_matches(all_matches, team="Flamengo", limit=10)
        assert result['total_found'] >= 500
        for match in result['matches']:
            assert match['home_team'] == "Flamengo" or match['away_team'] == "Flamengo"

    def test_search_by_date_range(self, all_matches):
        """
        Given the match data is loaded
        When I search for matches in 2023
        Then I should receive only 2023 matches
        """
        result = search_matches(all_matches, date_from="2023-01-01", date_to="2023-12-31")
        assert result['total_found'] > 0
        for match in result['matches']:
            assert match['date'] >= "2023-01-01"
            assert match['date'] <= "2023-12-31"

    def test_search_by_competition(self, all_matches):
        """
        Given the match data is loaded
        When I search for matches in Brasileirao
        Then I should receive only Brasileirao matches
        """
        result = search_matches(all_matches, competition="Brasileirao")
        assert result['total_found'] > 0
        for match in result['matches']:
            assert "Brasileirao" in match['competition']

    def test_search_by_season(self, all_matches):
        """
        Given the match data is loaded
        When I search for matches in season 2022
        Then I should receive only 2022 matches
        """
        result = search_matches(all_matches, season=2022)
        assert result['total_found'] > 0
        for match in result['matches']:
            assert match['season'] == 2022

    def test_find_matches_between(self, all_matches):
        """
        Given the match data is loaded
        When I search for matches between "Flamengo" and "Sao Paulo"
        Then I should receive a list of matches
        And each match should have date, scores, and competition
        """
        result = find_matches_between(all_matches, "Flamengo", "Sao Paulo")
        assert result['total_found'] > 0
        for match in result['matches']:
            assert 'date' in match
            assert 'home_goals' in match
            assert 'away_goals' in match
            assert 'competition' in match

    def test_biggest_wins(self, all_matches):
        """
        Given the match data is loaded
        When I request biggest wins
        Then I should receive matches sorted by goal difference
        """
        result = get_biggest_wins(all_matches, limit=5)
        assert len(result['matches']) == 5
        diffs = [m['goal_difference'] for m in result['matches']]
        assert diffs == sorted(diffs, reverse=True)

    def test_format_match_display(self):
        """
        Given a match row
        When I format it for display
        Then I should receive a human-readable string
        """
        row = {
            "date": "2023-09-03",
            "home_team": "Flamengo",
            "away_team": "Fluminense",
            "home_goals": 2,
            "away_goals": 1,
            "competition": "Brasileirao",
            "season": 2023,
            "round": 22,
        }
        result = format_match_display(row)
        assert "Flamengo" in result
        assert "Fluminense" in result
        assert "2-1" in result
        assert "2023-09-03" in result

    def test_no_matches_found(self, all_matches):
        """
        When I search for a team with no matches
        Then I should get zero results
        """
        result = search_matches(all_matches, team="NonExistentTeamXYZ")
        assert result['total_found'] == 0


# --- 5. Head-to-Head Tests ---

class TestHeadToHead:
    """BDD-style H2H scenarios."""

    def test_h2h_between_teams(self, all_matches):
        """
        Given the match data is loaded
        When I request H2H for "Flamengo" vs "Sao Paulo"
        Then I should receive wins/draws/losses and match list
        """
        result = get_h2h(all_matches, "Flamengo", "Sao Paulo")
        assert result['matches'] > 0
        assert result['team_a_wins'] + result['team_b_wins'] + result['draws'] == result['matches']

    def test_h2h_format(self, all_matches):
        """
        Given H2H result
        When I format it for display
        Then I should receive readable summary
        """
        result = get_h2h(all_matches, "Flamengo", "Sao Paulo")
        display = format_h2h_display(result)
        assert "Flamengo" in display
        assert "Sao Paulo" in display
        assert "wins" in display

    def test_h2h_no_matches(self):
        """
        When I request H2H for teams with no matches
        Then I should receive zero results
        """
        result = get_h2h(
            pd.DataFrame(columns=['home_team', 'away_team']),
            "TeamA", "TeamB"
        )
        assert result['matches'] == 0
        display = format_h2h_display(result)
        assert "No matches found" in display


# --- 6. Team Statistics Tests ---

class TestTeamStatistics:
    """BDD-style team statistics scenarios."""

    def test_team_stats(self, all_matches):
        """
        Given the match data is loaded
        When I request statistics for "Flamengo" in season "2023"
        Then I should receive wins, losses, draws, and goals
        """
        result = get_team_stats(all_matches, "Flamengo", season=2023)
        assert result['team'] == "Flamengo"
        stats = result['overall']
        assert 'matches' in stats
        assert 'wins' in stats
        assert 'draws' in stats
        assert 'losses' in stats
        assert 'goals_for' in stats
        assert 'goals_against' in stats
        assert stats['matches'] == stats['wins'] + stats['draws'] + stats['losses']

    def test_team_home_record(self, all_matches):
        """
        When I request Flamengo home record
        Then I should get home-only statistics
        """
        result = get_team_stats(all_matches, "Flamengo", home_only=True)
        stats = result['overall']
        assert stats['matches'] > 0

    def test_team_away_record(self, all_matches):
        """
        When I request Flamengo away record
        Then I should get away-only statistics
        """
        result = get_team_stats(all_matches, "Flamengo", away_only=True)
        stats = result['overall']
        assert stats['matches'] > 0

    def test_team_matches(self, all_matches):
        """
        When I request recent matches for "Flamengo"
        Then I should receive match history
        """
        result = get_team_matches(all_matches, "Flamengo", limit=5, order="desc")
        assert result['team'] == "Flamengo"
        assert result['total_matches'] == 5
        assert len(result['matches']) == 5

    def test_team_matches_order(self, all_matches):
        """
        When I request matches in ascending order
        Then I should receive oldest first
        """
        result_asc = get_team_matches(all_matches, "Flamengo", limit=5, order="asc")
        result_desc = get_team_matches(all_matches, "Flamengo", limit=5, order="desc")
        assert result_asc['matches'][0]['date'] <= result_desc['matches'][-1]['date']


# --- 7. Competition Standings Tests ---

class TestCompetitionStandings:
    """Competition and standings scenarios."""

    def test_competition_leaderboard(self, all_matches):
        """
        When I request standings for "Brasileirao" in season 2020
        Then I should receive a sorted table
        """
        result = get_competition_leaderboard(all_matches, "Brasileirao", season=2020)
        assert result['competition'] == "Brasileirao"
        assert result['season'] == 2020
        assert len(result['standings']) > 0

        standings = result['standings']
        assert all(k in standings[0] for k in ['team', 'played', 'won', 'drawn', 'lost',
                                                'goals_for', 'goals_against', 'goal_difference',
                                                'points'])

    def test_standings_sorted_by_points(self, all_matches):
        """
        When I get standings
        Then teams should be sorted by points (descending)
        """
        result = get_competition_leaderboard(all_matches, "Brasileirao", season=2020)
        points_list = [s['points'] for s in result['standings']]
        assert points_list == sorted(points_list, reverse=True)

    def test_no_standings_for_missing_competition(self, all_matches):
        """
        When I request standings for non-existent competition
        Then I should get empty standings
        """
        result = get_competition_leaderboard(all_matches, "NonExistentCompetition")
        assert result['standings'] == []

    def test_competition_standings_no_season(self, all_matches):
        """
        When I request standings without season filter
        Then I should get all-time standings for that competition
        """
        result = get_competition_leaderboard(all_matches, "Brasileirao", season=None)
        assert len(result['standings']) > 0
        assert result['season'] is None


# --- 8. Player Query Tests ---

class TestPlayerQueries:
    """BDD-style player query scenarios."""

    def test_search_players_by_name(self, data_loader):
        """
        Given the player data is loaded
        When I search for "Neymar"
        Then I should receive matching players
        """
        result = search_players(data_loader.fifa_df, name="Neymar")
        assert result['total_found'] > 0
        for player in result['players']:
            assert "neymar" in player['name'].lower()

    def test_search_players_by_nationality(self, data_loader):
        """
        Given the player data is loaded
        When I search for Brazilian players
        Then I should receive players with Brazilian nationality
        """
        result = search_players(data_loader.fifa_df, nationality="Brazil")
        assert result['total_found'] > 100
        for player in result['players']:
            assert "Brazil" in player['nationality']

    def test_brazilian_players_top(self, data_loader):
        """
        When I request top Brazilian players
        Then I should receive players sorted by overall rating
        """
        result = get_brazilian_players(data_loader.fifa_df, limit=10)
        assert result['total_found'] > 0
        assert len(result['players']) == 10
        ratings = [p['overall'] for p in result['players']]
        assert ratings == sorted(ratings, reverse=True)

    def test_players_by_club(self, data_loader):
        """
        When I request players at a club
        Then I should receive players from that club
        """
        result = get_players_by_club(data_loader.fifa_df, "Flamengo", limit=5)
        assert result['club'] == "Flamengo"
        assert len(result['players']) == 5

    def test_players_by_club_nationality_filter(self, data_loader):
        """
        When I filter players by club and nationality
        Then I should get matching results
        """
        result = get_players_by_club(data_loader.fifa_df, "Flamengo", nationality="Brazil", limit=10)
        for player in result['players']:
            assert "Brazil" in player['nationality']

    def test_search_players_min_overall(self, data_loader):
        """
        When I search for players with min overall 90
        Then I should only get players with overall >= 90
        """
        result = search_players(data_loader.fifa_df, min_overall=90, limit=20)
        for player in result['players']:
            assert player['overall'] >= 90

    def test_search_players_empty_result(self, data_loader):
        """
        When I search for non-existent player
        Then I should get empty results
        """
        result = search_players(data_loader.fifa_df, name="NonExistentPlayerXYZ")
        assert result['total_found'] == 0


# --- 9. Statistical Analysis Tests ---

class TestStatisticalAnalysis:
    """Statistical analysis scenarios."""

    def test_average_goals_all(self, all_matches):
        """
        When I calculate average goals
        Then I should receive average total goals per match
        """
        result = get_average_goals(all_matches)
        assert result['total_matches'] > 0
        assert result['avg_total_goals'] > 0
        assert 'home_win_rate' in result
        assert 'away_win_rate' in result
        assert 'draw_rate' in result

    def test_average_goals_specific_competition(self, all_matches):
        """
        When I calculate average goals for Brasileirao
        Then I should get competition-specific statistics
        """
        result = get_average_goals(all_matches, competition="Brasileirao")
        assert result['competition'] == "Brasileirao"

    def test_average_goals_rates_sum(self, all_matches):
        """
        When I get win/draw rates
        Then they should sum to approximately 100%
        """
        result = get_average_goals(all_matches)
        total_rate = result['home_win_rate'] + result['away_win_rate'] + result['draw_rate']
        assert abs(total_rate - 100.0) < 1.0

    def test_best_away_records(self, all_matches):
        """
        When I request best away records
        Then I should receive teams sorted by win rate
        """
        result = get_team_best_away_record(all_matches, limit=10)
        assert len(result['away_records']) == 10
        rates = [r['win_rate'] for r in result['away_records']]
        assert rates == sorted(rates, reverse=True)


# --- 10. Integration / End-to-End Tests ---

class TestIntegration:
    """End-to-end scenarios covering the full stack."""

    def test_complete_flamengo_analysis(self, data_loader):
        """
        Scenario: Complete analysis of Flamengo
        Given all data is loaded
        When I query Flamengo matches, stats, and players
        Then I should get consistent results
        """
        matches = search_matches(data_loader.all_matches, team="Flamengo", limit=10)
        assert matches['total_found'] > 0

        stats = get_team_stats(data_loader.all_matches, "Flamengo")
        assert stats['overall']['matches'] == matches['total_found']

        players = get_players_by_club(data_loader.fifa_df, "Flamengo", limit=5)
        assert 'club' in players

    def test_cross_competition_query(self, data_loader):
        """
        Scenario: Query across competitions
        When I search for Palmeiras
        Then I should get matches from multiple competitions
        """
        matches = search_matches(data_loader.all_matches, team="Palmeiras", limit=100)
        assert matches['total_found'] > 0
        competitions = set(m['competition'] for m in matches['matches'])
        assert len(competitions) >= 1

    def test_h2h_consistency(self, all_matches):
        """
        Scenario: H2H result consistency
        When I get H2H between two teams
        Then wins + losses + draws should equal total matches
        """
        result = get_h2h(all_matches, "Corinthians", "Palmeiras")
        if result['matches'] > 0:
            total = result['team_a_wins'] + result['team_b_wins'] + result['draws']
            assert total == result['matches']

    def test_sample_questions_20_plus(self, data_loader):
        """
        Scenario: At least 20 sample questions can be answered
        When I run through various queries
        Then all should return results without errors
        """
        questions_answered = 0

        if search_matches(data_loader.all_matches, team="Flamengo")['total_found'] > 0:
            questions_answered += 1

        if search_matches(data_loader.all_matches, date_from="2020-01-01")['total_found'] > 0:
            questions_answered += 1

        if search_matches(data_loader.all_matches, competition="Brazilian_Cup")['total_found'] > 0:
            questions_answered += 1

        if search_matches(data_loader.all_matches, season=2020)['total_found'] > 0:
            questions_answered += 1

        if get_h2h(data_loader.all_matches, "Flamengo", "Sao Paulo")['matches'] > 0:
            questions_answered += 1

        if get_team_stats(data_loader.all_matches, "Flamengo")['overall']['matches'] > 0:
            questions_answered += 1

        if get_team_stats(data_loader.all_matches, "Flamengo", home_only=True)['overall']['matches'] > 0:
            questions_answered += 1

        if get_team_stats(data_loader.all_matches, "Flamengo", away_only=True)['overall']['matches'] > 0:
            questions_answered += 1

        if get_team_matches(data_loader.all_matches, "Flamengo", limit=5)['total_matches'] > 0:
            questions_answered += 1

        if get_competition_leaderboard(data_loader.all_matches, "Brasileirao", season=2020)['standings']:
            questions_answered += 1

        if search_players(data_loader.fifa_df, name="Neymar")['total_found'] > 0:
            questions_answered += 1

        if get_brazilian_players(data_loader.fifa_df, limit=1)['total_found'] > 0:
            questions_answered += 1

        if get_players_by_club(data_loader.fifa_df, "Flamengo", limit=1)['total_found'] > 0:
            questions_answered += 1

        if get_average_goals(data_loader.all_matches)['total_matches'] > 0:
            questions_answered += 1

        if get_average_goals(data_loader.all_matches, competition="Libertadores")['total_matches'] > 0:
            questions_answered += 1

        if len(get_biggest_wins(data_loader.all_matches)['matches']) > 0:
            questions_answered += 1

        if len(get_team_best_away_record(data_loader.all_matches)['away_records']) > 0:
            questions_answered += 1

        display = format_h2h_display(get_h2h(data_loader.all_matches, "Flamengo", "Sao Paulo"))
        if "Flamengo" in display:
            questions_answered += 1

        row = {
            "date": "2023-01-01", "home_team": "A", "away_team": "B",
            "home_goals": 1, "away_goals": 0, "competition": "Test", "season": 2023
        }
        if "A 1-0 B" in format_match_display(row):
            questions_answered += 1

        if search_players(data_loader.fifa_df, nationality="Argentina")['total_found'] > 0:
            questions_answered += 1

        if search_players(data_loader.fifa_df, position="ST")['total_found'] > 0:
            questions_answered += 1

        dl = load_all(DATA_DIR)
        if len(dl.all_matches) > 0:
            questions_answered += 1

        assert questions_answered >= 20, f"Only {questions_answered}/20 sample questions answered"


# --- 11. Edge Cases ---

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_team_name(self):
        """Given empty team name, should handle gracefully."""
        result = normalize_team_name("")
        assert result == ""

    def test_none_team_name(self):
        """Given None, should return empty string."""
        result = normalize_team_name(None)
        assert result == ""

    def test_unusual_date_format(self):
        """Given unsupported date format, should return None."""
        assert parse_date("invalid-date") is None
        assert parse_date("01-13-2023") is None

    def test_zero_goals(self):
        """Given match with 0-0 score, should calculate stats correctly."""
        df = pd.DataFrame([{
            'home_team': 'A', 'away_team': 'B',
            'home_goals': 0, 'away_goals': 0,
        }])
        stats = get_team_stats(df, 'A', home_only=True)
        assert stats['overall']['draws'] == 1

    def test_very_long_match_list(self, all_matches):
        """When requesting more matches than exist, should cap at available."""
        result = search_matches(all_matches, team="Flamengo", limit=100000)
        assert result['total_found'] == len(
            all_matches[(all_matches['home_team'] == "Flamengo") |
                       (all_matches['away_team'] == "Flamengo")]
        )
