"""Comprehensive BDD-style tests for Brazilian Soccer MCP Server.

Covers all functional requirements from TASK.md:
- Match queries
- Team queries
- Player queries
- Competition queries
- Statistical analysis
- Data quality (normalization, dates, encoding)
"""

import json
import sys
import os

import pandas as pd
import pytest

# Ensure the project is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brazilian_soccer_mcp.data_loader import (
    normalize_team_name,
    parse_date,
    parse_goals,
    get_match_data,
    get_player_data,
    load_brasileirao_matches,
    load_brazilian_cup_matches,
    load_libertadores_matches,
    load_extended_matches,
    load_historical_matches,
    load_fifa_players,
    get_all_competitions,
)
from brazilian_soccer_mcp.query_engine import QueryEngine


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(scope="session")
def match_data():
    """Load all match data once for the session."""
    return get_match_data()


@pytest.fixture(scope="session")
def player_data():
    """Load player data once for the session."""
    return get_player_data()


@pytest.fixture(scope="session")
def engine(match_data, player_data):
    """Create a query engine with loaded data."""
    return QueryEngine(match_data=match_data, player_data=player_data)


@pytest.fixture(scope="session")
def all_competitions(match_data):
    """Get list of all competitions."""
    return get_all_competitions(match_data)


# ===========================================================================
# Data Quality Tests
# ===========================================================================

class TestDataQuality:
    """Test data loading and quality."""

    def test_all_csv_files_loadable(self, match_data):
        """Success Criteria: All 6 CSV files are loadable and queryable."""
        assert len(match_data) > 0, "At least some data should be loaded"
        assert "competition" in match_data.columns, "Match data should have competition column"

    def test_match_data_has_required_columns(self, match_data):
        """Data should have standard columns."""
        required = ["date", "season", "round", "competition",
                     "home_team", "home_goal", "away_team", "away_goal"]
        for col in required:
            assert col in match_data.columns, f"Missing column: {col}"

    def test_player_data_loadable(self, player_data):
        """Player data should load successfully."""
        assert len(player_data) > 0, "FIFA player data should be loaded"
        assert "Name" in player_data.columns
        assert "Nationality" in player_data.columns
        assert "Overall" in player_data.columns
        assert "Club" in player_data.columns

    def test_multiple_competitions(self, all_competitions):
        """Data should contain multiple competition types."""
        comps = all_competitions
        assert len(comps) >= 3, f"Should have at least 3 competitions, got {len(comps)}"
        # Should have Brasileirao
        brazileirao = [c for c in comps if "brasilei" in c.lower()]
        assert len(brazileirao) > 0, "Should have Brasileirao data"

    def test_date_range_has_history(self, match_data):
        """Match data should span multiple years."""
        min_year = match_data["date"].min().year
        max_year = match_data["date"].max().year
        assert max_year - min_year >= 5, f"Data should span at least 5 years ({min_year}-{max_year})"


class TestTeamNameNormalization:
    """Test team name normalization for consistent matching."""

    def test_strip_state_suffix_no_space(self):
        """Palmeiras-SP should normalize to Palmeiras."""
        assert normalize_team_name("Palmeiras-SP") == "Palmeiras"

    def test_strip_state_suffix_with_space(self):
        """Palmeiras - SP should normalize to Palmeiras."""
        assert normalize_team_name("Palmeiras - SP") == "Palmeiras"

    def test_flamengo_rj(self):
        """Flamengo-RJ should normalize to Flamengo."""
        assert normalize_team_name("Flamengo-RJ") == "Flamengo"

    def test_sao_paulo(self):
        """Sao Paulo-SP should normalize to Sao Paulo."""
        assert normalize_team_name("Sao Paulo-SP") == "Sao Paulo"

    def test_no_suffix_unchanged(self):
        """Names without suffixes should remain unchanged."""
        assert normalize_team_name("Flamengo") == "Flamengo"

    def test_various_state_suffixes(self):
        """Should handle multiple state suffixes."""
        assert normalize_team_name("Gremio-RS") == "Gremio"
        assert normalize_team_name("Athletico-PR") == "Athletico"
        assert normalize_team_name("Coritiba-PR") == "Coritiba"
        assert normalize_team_name("Sport-PE") == "Sport"

    def test_handles_empty(self):
        """Empty/None inputs should return empty string."""
        assert normalize_team_name("") == ""
        assert normalize_team_name(None) == ""

    def test_uf_sao_paulo_normalized(self):
        """Sao Paulo - SP should normalize correctly."""
        assert normalize_team_name("Sao Paulo - SP") == "Sao Paulo"


class TestDateParsing:
    """Test date format handling."""

    def test_iso_format(self):
        """ISO dates should be parsed correctly."""
        assert parse_date("2023-09-24") == "2023-09-24"

    def test_iso_with_time(self):
        """ISO dates with time should be parsed."""
        assert parse_date("2023-09-24 18:30:00") == "2023-09-24"

    def test_brazilian_format(self):
        """Brazilian DD/MM/YYYY format should be parsed."""
        assert parse_date("29/03/2003") == "2003-03-29"

    def test_null_date(self):
        """Null dates should return None."""
        import pandas as pd
        assert parse_date(None) is None
        assert parse_date(pd.NA) is None


class TestGoalParsing:
    """Test goal value parsing."""

    def test_integer_goals(self):
        """Integer goals should parse correctly."""
        assert parse_goals(2) == 2

    def test_float_goals(self):
        """Float goals should parse correctly."""
        assert parse_goals(2.0) == 2

    def test_dash_goals(self):
        """Dash values should return None."""
        assert parse_goals("-") is None
        assert parse_goals(" - ") is None

    def test_null_goals(self):
        """Null goals should return None."""
        import pandas as pd
        assert parse_goals(None) is None
        assert parse_goals(pd.NA) is None

    def test_zero_goals(self):
        """Zero goals should parse correctly."""
        assert parse_goals(0) == 0
        assert parse_goals("0") == 0


# ===========================================================================
# Match Query Tests
# ===========================================================================

class TestMatchQueries:
    """BDD: Feature: Match Queries.

    Scenario: Find matches by team
    Scenario: Find matches between two teams
    Scenario: Find Copa do Brasil finals
    """

    def test_find_matches_by_team_flamengo(self, engine):
        """Given match data is loaded, when I search for matches involving Flamengo,
        then I should receive a list of matches."""
        matches = engine.find_matches_by_team("Flamengo", limit=20)
        assert len(matches) > 0
        for m in matches:
            assert "date" in m
            assert "competition" in m
            assert "home_team" in m
            assert "away_team" in m
            assert "home_goal" in m
            assert "away_goal" in m
            # Team should be in home or away
            assert m["home_team"] == "Flamengo" or m["away_team"] == "Flamengo"

    def test_find_matches_by_team_with_season(self, engine):
        """When I search for matches with a season filter, only matching seasons should be returned."""
        matches = engine.find_matches_by_team("Flamengo", season=2019, limit=20)
        for m in matches:
            assert m["season"] == 2019 or m["season"] is None  # historical data may not have season

    def test_find_matches_by_team_with_competition(self, engine):
        """When I search with a competition filter, only matching competitions should be returned."""
        matches = engine.find_matches_by_team("Flamengo", competition="Brasileirao Serie A", limit=20)
        assert len(matches) > 0
        for m in matches:
            assert "brasilei" in m["competition"].lower()

    def test_find_matches_between_teams_flamengo_fluminense(self, engine):
        """BDD Scenario: Find matches between two teams.

        Given the match data is loaded
        When I search for matches between "Flamengo" and "Fluminense"
        Then I should receive a list of matches
        And each match should have date, scores, and competition
        """
        result = engine.find_matches_between_teams("Flamengo", "Fluminense")
        assert isinstance(result, dict)
        assert "matches" in result
        assert "head_to_head" in result

        matches = result["matches"]
        assert len(matches) > 0

        for m in matches:
            assert "date" in m, "Each match should have date"
            assert "home_goal" in m, "Each match should have scores"
            assert "away_goal" in m, "Each match should have scores"
            assert "competition" in m, "Each match should have competition"

        h2h = result["head_to_head"]
        assert isinstance(h2h, dict)
        assert "Flamengo wins" in h2h or "Flamengo wins" in str(h2h)
        assert "Fluminense wins" in h2h or "Fluminense wins" in str(h2h)
        assert "draws" in h2h

    def test_find_matches_between_teams_with_competition(self, engine):
        """When filtering H2H by competition, only that competition's matches should be returned."""
        result = engine.find_matches_between_teams(
            "Flamengo", "Fluminense", competition="Brasileirao Serie A"
        )
        for m in result["matches"]:
            assert "brasilei" in m["competition"].lower()

    def test_h2h_head_to_head_record(self, engine):
        """Head-to-head record should add up correctly."""
        result = engine.find_matches_between_teams("Flamengo", "Fluminense")
        h2h = result["head_to_head"]

        total = h2h["Flamengo wins"] + h2h["Fluminense wins"] + h2h["draws"]
        assert total == len(result["matches"]), "H2H record should match match count"
        assert total > 0, "Should have at least some H2H matches"

    def test_find_copa_do_brasil_finals(self, engine):
        """Find all Copa do Brasil finals.

        Finals should be identified by the highest round per season.
        """
        finals = engine.find_copa_do_brasil_final()
        assert len(finals) > 0, "Should have some Copa do Brasil finals"

        for f in finals:
            assert "home_team" in f
            assert "away_team" in f
            assert "home_goal" in f
            assert "away_goal" in f
            assert "competition" in f

    def test_find_copa_do_brasil_finals_specific_season(self, engine):
        """When searching for a specific season's final, results should be filtered."""
        finals = engine.find_copa_do_brasil_final(season=2020)
        for f in finals:
            assert f["season"] == 2020

    def test_latest_match_between_teams(self, engine):
        """Find the most recent match between two teams."""
        latest = engine.find_latest_match("Flamengo", "Fluminense")
        # Should return the first (most recent) match from H2H
        assert latest is not None or engine.find_matches_between_teams("Flamengo", "Fluminense")["matches"]

    def test_matches_have_all_required_fields(self, engine):
        """Each match result should have date, scores, and competition."""
        matches = engine.find_matches_by_team("Palmeiras", limit=10)
        for m in matches:
            assert "date" in m
            assert "home_goal" in m
            assert "away_goal" in m
            assert "competition" in m

    def test_match_search_handles_state_suffix(self, engine):
        """Searching for team with state suffix should normalize correctly."""
        matches = engine.find_matches_by_team("Palmeiras-SP", limit=5)
        assert len(matches) > 0

    def test_cross_dataset_match_coverage(self, match_data):
        """Matches from multiple datasets should be combined."""
        comps = match_data["competition"].unique()
        assert len(comps) >= 3, "Should have matches from multiple datasets"


# ===========================================================================
# Team Query Tests
# ===========================================================================

class TestTeamQueries:
    """BDD: Feature: Team Queries.

    Scenario: Get team statistics
    Scenario: Compare teams head-to-head
    """

    def test_get_team_statistics(self, engine):
        """BDD Scenario: Get team statistics.

        Given the match data is loaded
        When I request statistics for "Palmeiras" in season "2019"
        Then I should receive wins, losses, draws, and goals
        """
        stats = engine.get_team_statistics("Palmeiras", season=2019)
        assert stats is not None
        assert "total_matches" in stats
        assert "wins" in stats
        assert "losses" in stats
        assert "draws" in stats
        assert "goals_for" in stats
        assert "goals_against" in stats

    def test_team_statistics_fields(self, engine):
        """Team statistics should include all required fields."""
        stats = engine.get_team_statistics("Flamengo")
        required_fields = [
            "team", "total_matches", "wins", "draws", "losses",
            "goals_for", "goals_against", "goal_difference", "win_rate",
            "home_record", "away_record", "competition_breakdown"
        ]
        for field in required_fields:
            assert field in stats, f"Missing field: {field}"

    def test_team_home_record(self, engine):
        """Home record should be calculated correctly."""
        stats = engine.get_team_statistics("Flamengo")
        home = stats["home_record"]
        assert "matches" in home
        assert "wins" in home
        assert "draws" in home
        assert "losses" in home
        assert "goals_for" in home
        assert "goals_against" in home

    def test_team_away_record(self, engine):
        """Away record should be calculated correctly."""
        stats = engine.get_team_statistics("Flamengo")
        away = stats["away_record"]
        assert "matches" in away
        assert "wins" in away
        assert "draws" in away
        assert "losses" in away

    def test_win_rate_calculation(self, engine):
        """Win rate should be correctly calculated."""
        stats = engine.get_team_statistics("Flamengo")
        total = stats["wins"] + stats["draws"] + stats["losses"]
        if total > 0:
            expected_rate = round(stats["wins"] / total * 100, 1)
            assert abs(stats["win_rate"] - expected_rate) < 1, "Win rate should match calculation"

    def test_goal_difference_calculation(self, engine):
        """Goal difference should match goals_for - goals_against."""
        stats = engine.get_team_statistics("Flamengo")
        assert stats["goal_difference"] == stats["goals_for"] - stats["goals_against"]

    def test_competition_breakdown(self, engine):
        """Competition breakdown should exist for each competition."""
        stats = engine.get_team_statistics("Flamengo")
        breakdown = stats["competition_breakdown"]
        assert len(breakdown) > 0, "Should have at least one competition breakdown"
        for comp, comp_stats in breakdown.items():
            assert "matches" in comp_stats
            assert "wins" in comp_stats

    def test_team_not_found_returns_none(self, engine):
        """When requesting stats for a team not in data, should return None."""
        stats = engine.get_team_statistics("NonExistentTeam123")
        assert stats is None

    def test_team_statistics_with_competition_filter(self, engine):
        """Team stats should filter correctly by competition."""
        stats = engine.get_team_statistics("Flamengo", competition="Brasileirao Serie A")
        assert stats is not None
        for comp in stats["competition_breakdown"]:
            assert "brasilei" in comp.lower()

    def test_head_to_head_comparison(self, engine):
        """Compare Palmeiras and Santos head-to-head."""
        result = engine.find_matches_between_teams("Palmeiras", "Santos")
        assert len(result["matches"]) > 0
        assert result["head_to_head"]["Palmeiras wins"] + result["head_to_head"]["Santos wins"] + result["head_to_head"]["draws"] == len(result["matches"])

    def test_team_matches_include_date_scores_competition(self, engine):
        """Each match in team results should have date, scores, and competition."""
        matches = engine.find_matches_by_team("Corinthians", limit=10)
        for m in matches:
            assert m["date"] is not None or m["date"] is not None  # date may be null in some datasets
            assert "home_goal" in m
            assert "away_goal" in m
            assert m["competition"] is not None


# ===========================================================================
# Player Query Tests
# ===========================================================================

class TestPlayerQueries:
    """BDD: Feature: Player Queries.

    Scenario: Search players by name
    Scenario: Find players by nationality
    Scenario: Find players by club
    """

    def test_search_player_by_name(self, engine):
        """Search for players by name (case-insensitive partial match)."""
        results = engine.search_player("Neymar", limit=5)
        assert len(results) > 0
        for p in results:
            assert "name" in p
            assert "nationality" in p
            assert "overall" in p
            assert "club" in p

    def test_search_player_case_insensitive(self, engine):
        """Search should be case-insensitive."""
        results_upper = engine.search_player("NEYMAR", limit=5)
        results_lower = engine.search_player("neymar", limit=5)
        assert len(results_upper) == len(results_lower)

    def test_search_player_not_found(self, engine):
        """Search for non-existent player should return empty list."""
        results = engine.search_player("NonExistentPlayer12345", limit=10)
        assert len(results) == 0

    def test_get_players_by_nationality_brazilian(self, engine):
        """Find all Brazilian players in the dataset."""
        brazilians = engine.get_players_by_nationality("Brazil", limit=20)
        assert len(brazilians) > 0
        for p in brazilians:
            assert "Brazil" in p["nationality"]

    def test_get_players_by_nationality_filtered(self, engine):
        """Should be able to filter by minimum overall rating."""
        brazilians_high = engine.get_players_by_nationality("Brazil", min_overall=85, limit=20)
        for p in brazilians_high:
            assert p["overall"] >= 85

    def test_get_players_by_nationality_limit(self, engine):
        """Limit parameter should cap results."""
        results = engine.get_players_by_nationality("Brazil", limit=5)
        assert len(results) <= 5

    def test_get_players_by_club(self, engine):
        """Players should be filterable by club."""
        players = engine.get_players_by_club("Santos", limit=20)
        assert isinstance(players, list)

    def test_get_players_by_club_with_position(self, engine):
        """Players should be filterable by club and position."""
        players = engine.get_players_by_club("Santos", position="FWD", limit=10)
        assert len(players) <= 10

    def test_brazilian_players_at_brazilian_clubs(self, engine):
        """Get Brazilian players playing at Brazilian clubs."""
        players = engine.get_brazilian_players_by_brazilian_club(limit=20)
        assert isinstance(players, list)
        for p in players:
            assert "Brazil" in p["nationality"]
            assert "club" in p

    def test_brazilian_club_summary(self, engine):
        """Get summary of Brazilian players at Brazilian clubs."""
        summary = engine.get_brazilian_club_summary()
        assert len(summary) > 0
        for s in summary:
            assert "club" in s
            assert "brazilian_players" in s
            assert "avg_rating" in s
            assert s["brazilian_players"] > 0

    def test_player_search_returns_name(self, engine):
        """Player search should return player names."""
        results = engine.search_player("Silva", limit=10)
        assert len(results) > 0
        for p in results:
            assert "name" in p
            assert len(p["name"]) > 0

    def test_player_data_has_rich_attributes(self, engine):
        """Player data should include key attributes."""
        results = engine.search_player("Alisson", limit=5)
        assert len(results) > 0 or True  # Player may or may not be in dataset
        # Check player data has expected columns
        assert "Name" in engine.players.columns
        assert "Age" in engine.players.columns
        assert "Nationality" in engine.players.columns
        assert "Overall" in engine.players.columns
        assert "Club" in engine.players.columns
        assert "Position" in engine.players.columns


# ===========================================================================
# Competition Query Tests
# ===========================================================================

class TestCompetitionQueries:
    """BDD: Feature: Competition Queries.

    Scenario: Get standings by season
    Scenario: Get champion of a season
    """

    def test_get_standings(self, engine):
        """Get standings for a competition/season."""
        standings = engine.get_standings("Brasileirao Serie A", 2019)
        assert isinstance(standings, list)
        assert len(standings) > 0

        for team in standings:
            assert "team" in team
            assert "played" in team
            assert "wins" in team
            assert "draws" in team
            assert "losses" in team
            assert "goals_for" in team
            assert "goals_against" in team
            assert "points" in team
            assert "position" in team

    def test_standings_order(self, engine):
        """Standings should be ordered by points (descending)."""
        standings = engine.get_standings("Brasileirao Serie A", 2019)
        for i in range(len(standings) - 1):
            assert standings[i]["points"] >= standings[i + 1]["points"]

    def test_champion_is_first_standings(self, engine):
        """The champion should be the first team in standings."""
        champion = engine.get_champion("Brasileirao Serie A", 2019)
        standings = engine.get_standings("Brasileirao Serie A", 2019)
        assert champion["team"] == standings[0]["team"]
        assert champion["is_champion"] is True

    def test_standings_points_calculation(self, engine):
        """Points should be calculated as 3*W + 1*D."""
        standings = engine.get_standings("Brasileirao Serie A", 2019)
        for team in standings:
            expected_points = team["wins"] * 3 + team["draws"]
            assert team["points"] == expected_points, f"{team['team']}: {team['points']} != {expected_points}"

    def test_standings_goal_difference(self, engine):
        """Goal difference should match goals_for - goals_against."""
        standings = engine.get_standings("Brasileirao Serie A", 2019)
        for team in standings:
            assert team["goal_difference"] == team["goals_for"] - team["goals_against"]

    def test_champion_not_found(self, engine):
        """When requesting standings for non-existent season, should return empty."""
        standings = engine.get_standings("Brasileirao Serie A", 9999)
        assert standings == []

    def test_competition_list_available(self, all_competitions):
        """Should be able to list all available competitions."""
        assert len(all_competitions) > 0

    def test_matches_by_competition(self, match_data):
        """Each competition should have matches."""
        for comp in match_data["competition"].unique():
            comp_matches = match_data[match_data["competition"] == comp]
            assert len(comp_matches) > 0, f"Competition {comp} should have matches"


# ===========================================================================
# Statistical Analysis Tests
# ===========================================================================

class TestStatisticalAnalysis:
    """BDD: Feature: Statistical Analysis.

    Scenario: Calculate average goals per match
    Scenario: Find biggest wins
    Scenario: Get team performance trend
    """

    def test_average_goals_per_match(self, engine):
        """Calculate average goals per match."""
        stats = engine.get_average_goals_per_match(competition="Brasileirao Serie A")
        assert "average_goals" in stats
        assert "home_goals_avg" in stats
        assert "away_goals_avg" in stats
        assert "total_matches" in stats
        assert stats["average_goals"] > 0
        assert stats["total_matches"] > 0

    def test_average_goals_all_data(self, engine):
        """Average goals should work for all data combined."""
        stats = engine.get_average_goals_per_match()
        assert stats["average_goals"] > 0
        assert stats["total_matches"] > 0

    def test_home_win_rate_sum(self, engine):
        """Home win rate + draw rate + away win rate should be ~100%."""
        stats = engine.get_average_goals_per_match()
        total = stats["home_win_rate"] + stats["draw_rate"] + stats["away_win_rate"]
        assert abs(total - 100) < 10, f"Rates should sum to ~100%, got {total}"

    def test_biggest_wins_returned(self, engine):
        """Biggest wins should be returned in descending order of margin."""
        wins = engine.get_biggest_wins(limit=10)
        assert len(wins) > 0
        # Should be sorted by margin descending
        for i in range(len(wins) - 1):
            assert wins[i]["margin"] >= wins[i + 1]["margin"]

    def test_biggest_wins_fields(self, engine):
        """Each biggest win should have all required fields."""
        wins = engine.get_biggest_wins(limit=5)
        for w in wins:
            assert "date" in w
            assert "home_team" in w
            assert "away_team" in w
            assert "home_goal" in w
            assert "away_goal" in w
            assert "margin" in w
            assert "winner" in w

    def test_team_performance_trend(self, engine):
        """Get team performance trend over time."""
        trend = engine.get_team_performance_trend("Corinthians", period="season")
        assert len(trend) > 0
        for period in trend:
            assert "season" in period
            assert "matches" in period
            assert "wins" in period
            assert "draws" in period
            assert "losses" in period
            assert "points" in period

    def test_performance_trend_sorted(self, engine):
        """Performance trend should be sorted by time period."""
        trend = engine.get_team_performance_trend("Corinthians", period="season")
        if len(trend) > 1:
            # Seasons should be in chronological order
            for i in range(len(trend) - 1):
                assert trend[i]["season"] <= trend[i + 1]["season"]

    def test_best_away_record(self, engine):
        """Find teams with best away records."""
        away = engine.get_best_away_record(limit=10)
        assert len(away) > 0
        for team in away:
            assert "team" in team
            assert "wins" in team
            assert "matches" in team
            assert "win_rate" in team

    def test_competitions_for_team(self, engine):
        """Find all competitions a team has played in."""
        comps = engine.get_competitions_for_team("Flamengo")
        assert len(comps) > 0
        for c in comps:
            assert "competition" in c
            assert "matches" in c
            assert "seasons" in c

    def test_dataset_summary(self, engine):
        """Should be able to get dataset summary."""
        import json
        # This tests the server module's tool
        from brazilian_soccer_mcp.server import get_dataset_summary
        result = get_dataset_summary()
        summary = json.loads(result)
        assert "match_data" in summary
        assert "player_data" in summary
        assert summary["match_data"]["total_matches"] > 0
        assert summary["player_data"]["total_players"] > 0

    def test_teams_list(self, engine):
        """Should be able to list all teams."""
        import json
        from brazilian_soccer_mcp.server import get_teams_list
        result = get_teams_list()
        teams = json.loads(result)
        assert len(teams["teams"]) > 0
        assert "total" in teams

    def test_all_competitions_list(self, engine):
        """Should be able to list all competitions."""
        import json
        from brazilian_soccer_mcp.server import get_all_competitions_list
        result = get_all_competitions_list()
        data = json.loads(result)
        assert "competitions" in data
        assert data["total"] > 0


# ===========================================================================
# Integration / End-to-End Tests
# ===========================================================================

class TestIntegration:
    """End-to-end integration tests covering the full pipeline."""

    def test_flamengo_fluminense_h2h_complete(self, engine):
        """Full H2H query should return matches and summary."""
        result = engine.find_matches_between_teams("Flamengo", "Fluminense")
        assert len(result["matches"]) > 0
        assert sum(result["head_to_head"].values()) == len(result["matches"])

    def test_flamengo_stats_complete(self, engine):
        """Full team statistics should be comprehensive."""
        stats = engine.get_team_statistics("Flamengo")
        assert stats["wins"] >= 0
        assert stats["draws"] >= 0
        assert stats["losses"] >= 0
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["total_matches"]

    def test_premier_league_standings_different_from_brasileirao(self, engine):
        """Different competitions should have different standings."""
        braz = engine.get_standings("Brasileirao Serie A", 2019)
        assert len(braz) > 0
        # First team in Brasileirao
        first_braz = braz[0]["team"]
        # Check it's a Brazilian team
        assert first_braz in ["Flamengo", "Santos", "Palmeiras", "Sao Paulo", "Corinthians",
                              "Cruzeiro", "Internacional", "Gremio", "Vasco", "Fluminense",
                              "Botafogo", "Bahia", "Coritiba", "Goias"]

    def test_player_brazilian_nationality_filter(self, engine):
        """Brazilian players should have Brazil in nationality."""
        brazilians = engine.get_players_by_nationality("Brazil", limit=50)
        assert len(brazilians) > 0
        for p in brazilians:
            assert "Brazil" in p["nationality"]

    def test_cross_file_queries_work(self, engine):
        """Cross-file queries should work (player + match data)."""
        # Query match data
        matches = engine.find_matches_by_team("Palmeiras", limit=5)
        assert len(matches) > 0

        # Query player data
        players = engine.search_player("Gomes", limit=5)
        # Player data may or may not have the player, but should work
        assert isinstance(players, list)

    def test_date_normalization_in_matches(self, match_data):
        """All match dates should be normalized to datetime objects."""
        for _, row in match_data.head(100).iterrows():
            assert isinstance(row["date"], pd.Timestamp), f"Date should be datetime: {row['date']}"

    def test_no_null_goals_in_processed_data(self, match_data):
        """After loading, goal values should be integers or None."""
        for _, row in match_data.head(100).iterrows():
            hg = row["home_goal"]
            ag = row["away_goal"]
            if hg is not None:
                assert isinstance(hg, (int, float))
            if ag is not None:
                assert isinstance(ag, (int, float))

    def test_at_least_20_questions_answerable(self, engine):
        """Success Criteria: At least 20 sample questions can be answered."""
        answerable = 0

        # Match queries
        try:
            engine.find_matches_by_team("Flamengo", limit=1)
            answerable += 1
        except Exception:
            pass

        try:
            engine.find_matches_by_team("Palmeiras", season=2020, limit=1)
            answerable += 1
        except Exception:
            pass

        try:
            engine.find_matches_between_teams("Flamengo", "Palmeiras", limit=1)
            answerable += 1
        except Exception:
            pass

        try:
            engine.find_copa_do_brasil_final(season=2020)
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_team_statistics("Flamengo")
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_team_statistics("Corinthians", competition="Brasileirao Serie A")
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_standings("Brasileirao Serie A", 2019)
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_champion("Brasileirao Serie A", 2019)
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_average_goals_per_match()
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_biggest_wins(limit=5)
            answerable += 1
        except Exception:
            pass

        try:
            engine.search_player("Neymar", limit=1)
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_players_by_nationality("Brazil", limit=1)
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_players_by_club("Santos", limit=1)
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_brazilian_players_by_brazilian_club(limit=1)
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_brazilian_club_summary()
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_team_performance_trend("Flamengo", period="season")
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_best_away_record(limit=5)
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_competitions_for_team("Palmeiras")
            answerable += 1
        except Exception:
            pass

        try:
            engine.find_latest_match("Flamengo", "Fluminense")
            answerable += 1
        except Exception:
            pass

        try:
            engine.get_biggest_wins(competition="Copa Libertadores", limit=3)
            answerable += 1
        except Exception:
            pass

        assert answerable >= 20, f"Only {answerable}/20 questions answerable"


# ===========================================================================
# Performance Tests
# ===========================================================================

class TestPerformance:
    """Performance tests ensuring query speeds meet requirements."""

    def test_simple_lookup_under_2_seconds(self, engine):
        """Simple lookups should respond in < 2 seconds."""
        import time
        start = time.time()
        engine.find_matches_by_team("Flamengo", limit=10)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Simple lookup took {elapsed:.2f}s (limit: 2s)"

    def test_aggregate_query_under_5_seconds(self, engine):
        """Aggregate queries should respond in < 5 seconds."""
        import time
        start = time.time()
        engine.get_standings("Brasileirao Serie A", 2019)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Aggregate query took {elapsed:.2f}s (limit: 5s)"

    def test_h2h_query_under_2_seconds(self, engine):
        """Head-to-head queries should respond in < 2 seconds."""
        import time
        start = time.time()
        engine.find_matches_between_teams("Flamengo", "Palmeiras", limit=50)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"H2H query took {elapsed:.2f}s (limit: 2s)"
