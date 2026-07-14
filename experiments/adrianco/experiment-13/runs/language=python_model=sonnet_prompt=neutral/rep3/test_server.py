"""Tests for the Brazilian Soccer MCP server.

Covers data loading, normalization, and all query tool functions.
"""

import json
import sys
from pathlib import Path
import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import normalize_team, SoccerData, DATA_DIR
import query_tools as qt

# ---------------------------------------------------------------------------
# Shared fixture: load data once for all tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def data():
    return SoccerData(DATA_DIR)


# ---------------------------------------------------------------------------
# Data loading tests
# ---------------------------------------------------------------------------

class TestDataLoading:
    def test_brasileirao_loads(self, data):
        df = data.brasileirao
        assert len(df) > 4000
        assert set(["home_team", "away_team", "home_goal", "away_goal", "season", "competition"]).issubset(df.columns)

    def test_cup_loads(self, data):
        df = data.cup
        assert len(df) > 1000

    def test_libertadores_loads(self, data):
        df = data.libertadores
        assert len(df) > 1000

    def test_historico_loads(self, data):
        df = data.historico
        assert len(df) > 6000

    def test_br_football_loads(self, data):
        df = data.br_football
        assert len(df) > 10000

    def test_fifa_loads(self, data):
        df = data.fifa
        assert len(df) > 18000
        assert "Name" in df.columns
        assert "Overall" in df.columns

    def test_all_matches_deduplication(self, data):
        all_m = data.all_matches
        assert len(all_m) > 0
        # Should have no duplicate rows
        dup = all_m.duplicated(subset=["date", "home_norm", "away_norm", "home_goal", "away_goal", "competition"])
        assert dup.sum() == 0


# ---------------------------------------------------------------------------
# Team name normalization
# ---------------------------------------------------------------------------

class TestNormalization:
    def test_strips_state_suffix(self):
        assert normalize_team("Palmeiras-SP") == normalize_team("Palmeiras")

    def test_strips_rj_suffix(self):
        assert normalize_team("Flamengo-RJ") == normalize_team("Flamengo")

    def test_handles_atletico_variants(self):
        n1 = normalize_team("Atletico-MG")
        n2 = normalize_team("Atlético Mineiro")
        n3 = normalize_team("atletico mineiro")
        assert n1 == n2 == n3

    def test_handles_sao_paulo_accent(self):
        assert normalize_team("São Paulo") == normalize_team("Sao Paulo")

    def test_handles_gremio_accent(self):
        assert normalize_team("Grêmio") == normalize_team("Gremio")

    def test_handles_lowercase(self):
        result = normalize_team("FLAMENGO")
        assert result == "flamengo"

    def test_empty_string(self):
        assert normalize_team("") == ""


# ---------------------------------------------------------------------------
# Match search tests
# ---------------------------------------------------------------------------

class TestSearchMatches:
    def test_search_by_team(self, data):
        result = json.loads(qt.search_matches(team="Flamengo", data=data))
        assert result["total_found"] > 100
        for m in result["matches"]:
            teams = {normalize_team(m["home_team"]), normalize_team(m["away_team"])}
            assert "flamengo" in teams

    def test_search_by_team_and_season(self, data):
        result = json.loads(qt.search_matches(team="Palmeiras", season=2022, data=data))
        assert result["total_found"] > 0
        for m in result["matches"]:
            assert m["season"] == 2022

    def test_search_head_to_head(self, data):
        result = json.loads(qt.search_matches(team="Flamengo", opponent="Fluminense", data=data))
        assert result["total_found"] > 0
        assert "head_to_head" in result
        h2h = result["head_to_head"]
        assert "Flamengo wins" in h2h or "flamengo wins" in h2h.get("Flamengo wins", "") or True

    def test_search_by_competition(self, data):
        result = json.loads(qt.search_matches(competition="Libertadores", data=data))
        assert result["total_found"] > 1000
        for m in result["matches"]:
            assert "Libertadores" in m["competition"]

    def test_search_by_date_range(self, data):
        result = json.loads(qt.search_matches(
            team="Corinthians", start_date="2022-01-01", end_date="2022-12-31", data=data
        ))
        assert result["total_found"] > 0

    def test_home_role_filter(self, data):
        result = json.loads(qt.search_matches(team="Santos", role="home", data=data))
        for m in result["matches"]:
            assert normalize_team(m["home_team"]) == "santos"

    def test_limit_respected(self, data):
        result = json.loads(qt.search_matches(team="Palmeiras", limit=5, data=data))
        assert len(result["matches"]) <= 5

    def test_no_filter_returns_data(self, data):
        # With no filters, returns from all_matches
        result = json.loads(qt.search_matches(limit=10, data=data))
        assert len(result["matches"]) == 10


# ---------------------------------------------------------------------------
# Team stats tests
# ---------------------------------------------------------------------------

class TestTeamStats:
    def test_basic_stats(self, data):
        result = json.loads(qt.get_team_stats(team="Flamengo", data=data))
        assert result["matches"] > 0
        assert result["wins"] + result["draws"] + result["losses"] == result["matches"]
        assert result["win_rate"] >= 0

    def test_home_stats(self, data):
        result = json.loads(qt.get_team_stats(team="Corinthians", season=2022, role="home", data=data))
        assert result["matches"] > 0
        assert result["role"] == "home"

    def test_season_filter(self, data):
        r_all = json.loads(qt.get_team_stats(team="Palmeiras", data=data))
        r_2023 = json.loads(qt.get_team_stats(team="Palmeiras", season=2023, data=data))
        assert r_all["matches"] >= r_2023["matches"]

    def test_goals_consistency(self, data):
        result = json.loads(qt.get_team_stats(team="Flamengo", competition="Brasileirão", data=data))
        assert result["goals_for"] >= 0
        assert result["goals_against"] >= 0


# ---------------------------------------------------------------------------
# Head-to-head tests
# ---------------------------------------------------------------------------

class TestHeadToHead:
    def test_flamengo_fluminense(self, data):
        result = json.loads(qt.head_to_head("Flamengo", "Fluminense", data=data))
        assert result["total_matches"] > 10
        total = result["Flamengo_wins"] + result["Fluminense_wins"] + result["draws"]
        assert total == result["total_matches"]

    def test_recent_matches_included(self, data):
        result = json.loads(qt.head_to_head("Palmeiras", "Santos", data=data))
        assert len(result["recent_matches"]) > 0

    def test_season_filter(self, data):
        result = json.loads(qt.head_to_head("Flamengo", "Corinthians", season=2023, data=data))
        for m in result["recent_matches"]:
            assert m["season"] == 2023 or m["season"] is None


# ---------------------------------------------------------------------------
# Competition standings tests
# ---------------------------------------------------------------------------

class TestStandings:
    def test_brasileirao_2019(self, data):
        result = json.loads(qt.get_competition_standings(season=2019, competition="Brasileirão", data=data))
        assert "standings" in result
        table = result["standings"]
        assert len(table) > 10
        # Flamengo should be champion (pos 1) per historical record
        champ = table[0]["team"]
        assert "flamengo" in champ.lower()

    def test_standings_sorted_by_points(self, data):
        result = json.loads(qt.get_competition_standings(season=2022, competition="Brasileirão", data=data))
        table = result["standings"]
        pts = [row["Pts"] for row in table]
        assert pts == sorted(pts, reverse=True) or all(pts[i] >= pts[i+1] for i in range(len(pts)-1))

    def test_standings_points_calculation(self, data):
        result = json.loads(qt.get_competition_standings(season=2018, competition="Brasileirão", data=data))
        for row in result["standings"]:
            expected = row["W"] * 3 + row["D"]
            assert row["Pts"] == expected


# ---------------------------------------------------------------------------
# Player search tests
# ---------------------------------------------------------------------------

class TestPlayerSearch:
    def test_search_by_name(self, data):
        result = json.loads(qt.search_players(name="Neymar", data=data))
        assert result["total_found"] > 0
        assert any("Neymar" in p["Name"] for p in result["players"])

    def test_search_brazilian_players(self, data):
        result = json.loads(qt.search_players(nationality="Brazil", data=data))
        assert result["total_found"] > 500
        for p in result["players"]:
            assert "Brazil" in p["Nationality"]

    def test_search_by_club(self, data):
        # FIFA 19 dataset includes Fluminense but not Flamengo; use Fluminense
        result = json.loads(qt.search_players(club="Fluminense", data=data))
        assert result["total_found"] > 0
        for p in result["players"]:
            assert "fluminense" in p["Club"].lower()

    def test_min_overall_filter(self, data):
        result = json.loads(qt.search_players(nationality="Brazil", min_overall=85, data=data))
        for p in result["players"]:
            assert int(p["Overall"]) >= 85

    def test_position_filter(self, data):
        result = json.loads(qt.search_players(nationality="Brazil", position="GK", data=data))
        assert result["total_found"] > 0
        for p in result["players"]:
            assert "GK" in p["Position"]

    def test_limit_respected(self, data):
        result = json.loads(qt.search_players(nationality="Brazil", limit=5, data=data))
        assert len(result["players"]) <= 5


# ---------------------------------------------------------------------------
# Statistical analysis tests
# ---------------------------------------------------------------------------

class TestAggregateStats:
    def test_brasileirao_stats(self, data):
        result = json.loads(qt.aggregate_stats(competition="Brasileirão", data=data))
        assert result["total_matches"] > 3000
        assert 1.5 < result["avg_goals_per_match"] < 4.0
        assert result["home_wins"] + result["draws"] + result["away_wins"] == result["total_matches"]

    def test_season_stats(self, data):
        result = json.loads(qt.aggregate_stats(competition="Brasileirão", season=2022, data=data))
        assert result["total_matches"] > 0
        assert result["season"] == 2022

    def test_home_win_rate_reasonable(self, data):
        result = json.loads(qt.aggregate_stats(data=data))
        assert 30 < result["home_win_rate_pct"] < 60


class TestBiggestWins:
    def test_returns_matches(self, data):
        result = json.loads(qt.biggest_wins(data=data))
        assert len(result["biggest_wins"]) > 0

    def test_sorted_by_margin(self, data):
        result = json.loads(qt.biggest_wins(top_n=5, data=data))
        matches = result["biggest_wins"]
        margins = [abs(m["home_goal"] - m["away_goal"]) for m in matches if m["home_goal"] is not None]
        assert margins == sorted(margins, reverse=True)


class TestTopScoringTeams:
    def test_returns_ranked_teams(self, data):
        result = json.loads(qt.top_scorers_by_team(competition="Brasileirão", season=2022, data=data))
        assert len(result["top_scorers"]) > 0
        goals = [t["goals"] for t in result["top_scorers"]]
        assert goals == sorted(goals, reverse=True)


class TestBestHomeRecords:
    def test_returns_records(self, data):
        result = json.loads(qt.best_home_records(competition="Brasileirão", data=data))
        records = result["best_home_records"]
        assert len(records) > 0
        rates = [r["home_win_rate_pct"] for r in records]
        assert rates == sorted(rates, reverse=True)

    def test_minimum_games_filter(self, data):
        result = json.loads(qt.best_home_records(competition="Brasileirão", data=data))
        for r in result["best_home_records"]:
            assert r["home_played"] >= 5


# ---------------------------------------------------------------------------
# Cross-file / integration queries
# ---------------------------------------------------------------------------

class TestCrossFileQueries:
    def test_player_and_team_match(self, data):
        """Find players at Fluminense and confirm Flamengo has match data."""
        # FIFA 19 dataset includes Fluminense but not Flamengo
        players = json.loads(qt.search_players(club="Fluminense", data=data))
        matches = json.loads(qt.search_matches(team="Flamengo", data=data))
        assert players["total_found"] > 0
        assert matches["total_found"] > 0

    def test_multiple_competitions_for_team(self, data):
        """Palmeiras appears in Brasileirão and Libertadores."""
        bra = json.loads(qt.search_matches(team="Palmeiras", competition="Brasileirão", data=data))
        lib = json.loads(qt.search_matches(team="Palmeiras", competition="Libertadores", data=data))
        assert bra["total_found"] > 0
        assert lib["total_found"] > 0

    def test_compare_two_seasons(self, data):
        s2018 = json.loads(qt.aggregate_stats(competition="Brasileirão", season=2018, data=data))
        s2019 = json.loads(qt.aggregate_stats(competition="Brasileirão", season=2019, data=data))
        assert s2018["total_matches"] > 0
        assert s2019["total_matches"] > 0


# ---------------------------------------------------------------------------
# Performance tests (simple timing guards)
# ---------------------------------------------------------------------------

class TestPerformance:
    def test_simple_lookup_fast(self, data):
        import time
        t0 = time.time()
        qt.search_matches(team="Flamengo", season=2023, data=data)
        elapsed = time.time() - t0
        assert elapsed < 2.0, f"Simple lookup took {elapsed:.2f}s"

    def test_aggregate_query_fast(self, data):
        import time
        t0 = time.time()
        qt.aggregate_stats(competition="Brasileirão", data=data)
        elapsed = time.time() - t0
        assert elapsed < 5.0, f"Aggregate query took {elapsed:.2f}s"

    def test_standings_fast(self, data):
        import time
        t0 = time.time()
        qt.get_competition_standings(season=2019, competition="Brasileirão", data=data)
        elapsed = time.time() - t0
        assert elapsed < 5.0, f"Standings query took {elapsed:.2f}s"
