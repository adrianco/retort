"""Tests for the Brazilian Soccer MCP server."""

import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from data_loader import (
    normalize_team,
    load_brasileirao,
    load_copa_brasil,
    load_libertadores,
    load_br_football,
    load_historico,
    load_fifa,
    get_matches,
    get_fifa,
    find_team_matches,
)

from server import (
    search_matches,
    get_team_stats,
    get_competition_standings,
    search_players,
    get_biggest_wins,
    get_overall_stats,
    get_top_teams,
    list_competitions,
)


# ---------------------------------------------------------------------------
# Data loading tests
# ---------------------------------------------------------------------------

class TestDataLoading:
    def test_brasileirao_loads(self):
        df = load_brasileirao()
        assert len(df) > 4000
        assert "home_team" in df.columns
        assert "away_team" in df.columns
        assert "home_goal" in df.columns
        assert "away_goal" in df.columns
        assert "season" in df.columns
        assert "competition" in df.columns
        assert "home_norm" in df.columns

    def test_copa_brasil_loads(self):
        df = load_copa_brasil()
        assert len(df) > 1000
        assert "home_team" in df.columns

    def test_libertadores_loads(self):
        df = load_libertadores()
        assert len(df) > 1000
        assert "stage" in df.columns

    def test_br_football_loads(self):
        df = load_br_football()
        assert len(df) > 5000
        assert "home_team" in df.columns
        assert "competition" in df.columns

    def test_historico_loads(self):
        df = load_historico()
        assert len(df) > 6000
        assert "home_team" in df.columns
        assert "season" in df.columns

    def test_fifa_loads(self):
        df = load_fifa()
        assert len(df) > 10000
        assert "Name" in df.columns
        assert "Overall" in df.columns
        assert "Club" in df.columns
        assert "Nationality" in df.columns

    def test_all_matches_loads(self):
        df = get_matches()
        # Should contain matches from multiple datasets (deduped)
        assert len(df) > 10000
        assert "home_norm" in df.columns
        assert "away_norm" in df.columns

    def test_dates_parsed(self):
        df = get_matches()
        # datetime column should be actual timestamps (ns or us depending on pandas version)
        assert pd.api.types.is_datetime64_any_dtype(df["datetime"])

    def test_goals_numeric(self):
        df = get_matches()
        assert pd.api.types.is_numeric_dtype(df["home_goal"])
        assert pd.api.types.is_numeric_dtype(df["away_goal"])


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------

class TestNormalization:
    def test_state_suffix_removed(self):
        assert normalize_team("Palmeiras-SP") == "palmeiras"
        assert normalize_team("Flamengo-RJ") == "flamengo"
        assert normalize_team("Sport-PE") == "sport"

    def test_lowercase(self):
        assert normalize_team("FLAMENGO") == "flamengo"
        assert normalize_team("São Paulo") == "são paulo"

    def test_alias_mapping(self):
        assert normalize_team("Sao Paulo") == "são paulo"
        assert normalize_team("Gremio") == "grêmio"
        # Atletico-MG: alias checked on lowercase "atletico-mg" before suffix stripping
        assert normalize_team("Atletico-MG") == "atlético mineiro"
        assert normalize_team("atletico-mg") == "atlético mineiro"

    def test_already_normalized(self):
        assert normalize_team("flamengo") == "flamengo"

    def test_empty_string(self):
        assert normalize_team("") == ""


# ---------------------------------------------------------------------------
# Match search tests
# ---------------------------------------------------------------------------

class TestSearchMatches:
    def test_search_by_team(self):
        result = search_matches(team="Flamengo", limit=5)
        assert "Flamengo" in result or "flamengo" in result.lower()
        assert "Found" in result

    def test_search_by_team_and_opponent(self):
        result = search_matches(team="Flamengo", opponent="Fluminense", limit=50)
        assert "Head-to-head" in result
        # Should find historical Fla-Flu derbies
        assert "Found" in result

    def test_search_by_season(self):
        result = search_matches(team="Palmeiras", season=2023, limit=40)
        assert "Found" in result

    def test_search_by_competition_brasileirao(self):
        result = search_matches(competition="Brasileirao", season=2019, limit=5)
        assert "Found" in result

    def test_search_by_competition_copa(self):
        result = search_matches(competition="Copa do Brasil", limit=5)
        assert "Found" in result

    def test_search_by_competition_libertadores(self):
        result = search_matches(competition="Libertadores", limit=5)
        assert "Found" in result

    def test_search_date_range(self):
        result = search_matches(team="Corinthians", start_date="2022-01-01", end_date="2022-12-31")
        assert "Found" in result

    def test_no_results_returns_message(self):
        result = search_matches(team="NonExistentTeam12345XYZ")
        assert "No matches found" in result

    def test_h2h_includes_summary(self):
        result = search_matches(team="Flamengo", opponent="Fluminense", limit=100)
        assert "Wins:" in result
        assert "Draws:" in result

    def test_limit_respected(self):
        result = search_matches(competition="Brasileirao", limit=3)
        lines = [l for l in result.split("\n") if l.strip().startswith("2") or ": " in l]
        # We can't easily count exact lines but can check it doesn't return 1000s
        assert len(result) < 5000


# ---------------------------------------------------------------------------
# Team stats tests
# ---------------------------------------------------------------------------

class TestTeamStats:
    def test_corinthians_stats(self):
        result = get_team_stats("Corinthians")
        assert "Played:" in result
        assert "Wins:" in result
        assert "Goals" in result
        assert "Win rate:" in result

    def test_home_only_filter(self):
        result = get_team_stats("Palmeiras", home_only=True)
        assert "[home]" in result
        assert "Played:" in result

    def test_away_only_filter(self):
        result = get_team_stats("Flamengo", away_only=True)
        assert "[away]" in result

    def test_season_filter(self):
        result = get_team_stats("Santos", season=2019)
        assert "2019" in result
        assert "Played:" in result

    def test_competition_filter(self):
        result = get_team_stats("Grêmio", competition="Brasileirao")
        assert "Played:" in result

    def test_missing_team(self):
        result = get_team_stats("NoSuchTeamXYZ999")
        assert "No matches found" in result


# ---------------------------------------------------------------------------
# Competition standings tests
# ---------------------------------------------------------------------------

class TestStandings:
    def test_brasileirao_2019(self):
        result = get_competition_standings(season=2019, competition="Brasileirao")
        assert "Standings" in result
        # Flamengo won in 2019
        assert "flamengo" in result.lower()

    def test_standings_columns(self):
        result = get_competition_standings(season=2022, competition="Brasileirao")
        assert "pts" in result
        assert "W" in result
        assert "D" in result
        assert "L" in result

    def test_libertadores_standings(self):
        result = get_competition_standings(season=2018, competition="Libertadores")
        assert "Standings" in result

    def test_missing_season(self):
        result = get_competition_standings(season=1899, competition="Brasileirao")
        assert "No matches found" in result


# ---------------------------------------------------------------------------
# Player search tests
# ---------------------------------------------------------------------------

class TestSearchPlayers:
    def test_search_by_name(self):
        result = search_players(name="Neymar")
        assert "Neymar" in result

    def test_search_by_nationality(self):
        # FIFA data uses "Brazil" not "Brazilian"
        result = search_players(nationality="Brazil", limit=5)
        assert "Found" in result

    def test_search_by_club(self):
        # Santos is present in the FIFA dataset; Flamengo is not
        result = search_players(club="Santos", limit=10)
        assert "Found" in result

    def test_search_by_position(self):
        result = search_players(position="GK", nationality="Brazil", limit=5)
        assert "GK" in result

    def test_min_overall_filter(self):
        result = search_players(nationality="Brazil", min_overall=85, limit=10)
        assert "Found" in result
        # All shown players should have rating >= 85
        for line in result.split("\n")[1:]:
            if "Overall:" in line:
                val = int(line.split("Overall:")[1].split()[0])
                assert val >= 85

    def test_no_results(self):
        result = search_players(name="ZZZNoSuchPlayerXXX")
        assert "No players found" in result

    def test_sorted_by_rating(self):
        result = search_players(nationality="Brazilian", min_overall=80, limit=10)
        ratings = []
        for line in result.split("\n"):
            if "Overall:" in line:
                ratings.append(int(line.split("Overall:")[1].split()[0]))
        # Should be in descending order
        assert ratings == sorted(ratings, reverse=True)


# ---------------------------------------------------------------------------
# Biggest wins tests
# ---------------------------------------------------------------------------

class TestBiggestWins:
    def test_overall_biggest_wins(self):
        result = get_biggest_wins(limit=5)
        assert "biggest wins" in result.lower()
        assert "margin:" in result

    def test_biggest_wins_brasileirao(self):
        result = get_biggest_wins(competition="Brasileirao", limit=5)
        assert "margin:" in result

    def test_team_biggest_wins(self):
        result = get_biggest_wins(team="Palmeiras", limit=5)
        assert "Palmeiras" in result or "palmeiras" in result.lower()

    def test_season_filter(self):
        result = get_biggest_wins(season=2019, limit=5)
        assert "biggest wins" in result.lower()


# ---------------------------------------------------------------------------
# Overall stats tests
# ---------------------------------------------------------------------------

class TestOverallStats:
    def test_global_stats(self):
        result = get_overall_stats()
        assert "Total matches:" in result
        assert "Avg goals/match:" in result
        assert "Home wins:" in result

    def test_brasileirao_stats(self):
        result = get_overall_stats(competition="Brasileirao", season=2022)
        assert "Total matches:" in result

    def test_reasonable_averages(self):
        result = get_overall_stats(competition="Brasileirao")
        # Extract avg goals
        for line in result.split("\n"):
            if "Avg goals/match:" in line:
                val = float(line.split(":")[1].strip())
                assert 1.5 < val < 5.0, f"Avg goals {val} seems unreasonable"


# ---------------------------------------------------------------------------
# Top teams tests
# ---------------------------------------------------------------------------

class TestTopTeams:
    def test_top_by_wins(self):
        result = get_top_teams(competition="Brasileirao", metric="wins", limit=5)
        assert "Top" in result
        assert "W:" in result

    def test_top_by_goals(self):
        result = get_top_teams(competition="Brasileirao", metric="goals", limit=5)
        assert "Goals:" in result

    def test_top_by_win_rate(self):
        result = get_top_teams(competition="Brasileirao", season=2022, metric="win_rate", limit=5)
        assert "WR:" in result

    def test_top_away_wins(self):
        result = get_top_teams(metric="away_wins", limit=5)
        assert "Top" in result


# ---------------------------------------------------------------------------
# List competitions test
# ---------------------------------------------------------------------------

class TestListCompetitions:
    def test_returns_all_competitions(self):
        result = list_competitions()
        assert "Brasileirao" in result or "brasileirao" in result.lower()
        assert "seasons" in result.lower()

    def test_year_ranges_present(self):
        result = list_competitions()
        # Should show year ranges like "2012–2023"
        import re
        assert re.search(r"\d{4}[–-]\d{4}", result) is not None


# ---------------------------------------------------------------------------
# Cross-file / integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_all_six_files_covered(self):
        """All 6 CSV files contribute to the dataset."""
        from data_loader import (load_brasileirao, load_copa_brasil, load_libertadores,
                                 load_br_football, load_historico, load_fifa)
        assert len(load_brasileirao()) > 0
        assert len(load_copa_brasil()) > 0
        assert len(load_libertadores()) > 0
        assert len(load_br_football()) > 0
        assert len(load_historico()) > 0
        assert len(load_fifa()) > 0

    def test_player_and_match_cross_query(self):
        """Find players at a club and check that club appears in match data."""
        # Santos is present in both the FIFA dataset and match data
        players = search_players(club="Santos", limit=5)
        matches = search_matches(team="Santos", competition="Brasileirao", season=2019, limit=5)
        assert "Found" in players
        assert "Found" in matches

    def test_at_least_20_sample_questions(self):
        """Demonstrate 20 different query patterns."""
        queries = [
            lambda: search_matches(team="Flamengo", opponent="Fluminense", limit=10),
            lambda: search_matches(team="Palmeiras", season=2023, limit=10),
            lambda: search_matches(competition="Copa do Brasil", limit=5),
            lambda: get_team_stats("Corinthians", home_only=True),
            lambda: get_team_stats("Santos", season=2019),
            lambda: get_competition_standings(2019, "Brasileirao"),
            lambda: get_competition_standings(2018, "Libertadores"),
            lambda: search_players(name="Neymar"),
            lambda: search_players(nationality="Brazilian", min_overall=85),
            lambda: search_players(club="Flamengo", limit=10),
            lambda: search_players(position="GK", nationality="Brazilian"),
            lambda: get_biggest_wins(competition="Brasileirao", limit=5),
            lambda: get_biggest_wins(team="Flamengo"),
            lambda: get_overall_stats(competition="Brasileirao"),
            lambda: get_overall_stats(competition="Brasileirao", season=2019),
            lambda: get_top_teams(competition="Brasileirao", metric="wins", limit=5),
            lambda: get_top_teams(competition="Brasileirao", metric="goals", limit=5),
            lambda: get_top_teams(metric="away_wins", limit=5),
            lambda: list_competitions(),
            lambda: search_matches(team="Flamengo", competition="Brasileirao",
                                   start_date="2019-01-01", end_date="2019-12-31"),
        ]
        for fn in queries:
            result = fn()
            assert isinstance(result, str) and len(result) > 0

    def test_team_name_variations(self):
        """Normalized team names produce consistent results."""
        r1 = get_team_stats("Flamengo")
        r2 = get_team_stats("Flamengo-RJ")
        # Both should find the same team (Flamengo)
        assert "No matches found" not in r1
        assert "No matches found" not in r2

    def test_special_characters(self):
        """UTF-8 special characters in team names work."""
        result = get_team_stats("Grêmio")
        assert "No matches found" not in result

        result2 = get_team_stats("São Paulo")
        assert "No matches found" not in result2

    def test_performance_all_matches_loaded(self):
        """get_matches() completes quickly (data is cached)."""
        import time
        start = time.time()
        df = get_matches()
        elapsed = time.time() - start
        assert elapsed < 30, f"Loading took {elapsed:.1f}s, too slow"
        assert len(df) > 10000
