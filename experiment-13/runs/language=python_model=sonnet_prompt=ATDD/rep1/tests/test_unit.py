"""
Unit tests for the DataLoader class.

These tests verify internal query logic directly — they are fine-grained
regression guards for the data normalisation and filtering functions.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import DataLoader, _normalise

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")


@pytest.fixture(scope="module")
def loader() -> DataLoader:
    """A single DataLoader shared across unit tests (CSV loading is slow)."""
    return DataLoader(DATA_DIR)


# ---------------------------------------------------------------------------
# Team name normalisation
# ---------------------------------------------------------------------------

class TestNormalise:
    def test_strips_state_suffix_uppercase(self):
        assert _normalise("Palmeiras-SP") == "Palmeiras"

    def test_strips_state_suffix_with_space(self):
        assert _normalise("Flamengo -RJ") == "Flamengo"

    def test_handles_name_without_suffix(self):
        assert _normalise("Santos") == "Santos"

    def test_handles_nan(self):
        assert _normalise(float("nan")) == ""

    def test_strips_leading_trailing_whitespace(self):
        assert _normalise("  Corinthians-SP  ") == "Corinthians"


# ---------------------------------------------------------------------------
# find_matches
# ---------------------------------------------------------------------------

class TestFindMatches:
    def test_returns_dict_with_total_found_and_matches(self, loader):
        result = loader.find_matches(team="Palmeiras")
        assert "total_found" in result
        assert "matches" in result

    def test_team_filter_returns_only_team_matches(self, loader):
        result = loader.find_matches(team="Flamengo", limit=100)
        for m in result["matches"]:
            assert "Flamengo" in m["home_team"] or "Flamengo" in m["away_team"]

    def test_season_filter_is_exact(self, loader):
        result = loader.find_matches(season=2019, competition="brasileirao", limit=100)
        for m in result["matches"]:
            assert m["season"] == 2019

    def test_head_to_head_filter(self, loader):
        result = loader.find_matches(team="Santos", opponent="Palmeiras", limit=50)
        for m in result["matches"]:
            has_san = "Santos" in m["home_team"] or "Santos" in m["away_team"]
            has_pal = "Palmeiras" in m["home_team"] or "Palmeiras" in m["away_team"]
            assert has_san and has_pal

    def test_limit_is_respected(self, loader):
        result = loader.find_matches(limit=3)
        assert len(result["matches"]) <= 3

    def test_matches_sorted_newest_first(self, loader):
        result = loader.find_matches(competition="brasileirao", limit=20)
        dates = [m["date"] for m in result["matches"] if m["date"]]
        assert dates == sorted(dates, reverse=True)

    def test_no_matches_with_nan_goals(self, loader):
        result = loader.find_matches(competition="brasileirao", limit=500)
        for m in result["matches"]:
            assert m["home_goal"] is not None
            assert m["away_goal"] is not None

    def test_copa_do_brasil_competition_filter(self, loader):
        result = loader.find_matches(competition="copa_do_brasil", limit=20)
        for m in result["matches"]:
            assert m["competition"] == "copa_do_brasil"

    def test_libertadores_competition_filter(self, loader):
        result = loader.find_matches(competition="libertadores", limit=20)
        for m in result["matches"]:
            assert m["competition"] == "libertadores"

    def test_date_from_filter(self, loader):
        result = loader.find_matches(date_from="2020-01-01", limit=20)
        for m in result["matches"]:
            assert m["date"] >= "2020-01-01"

    def test_date_to_filter(self, loader):
        result = loader.find_matches(date_to="2015-12-31", limit=20)
        for m in result["matches"]:
            assert m["date"] <= "2015-12-31"

    def test_total_found_greater_than_or_equal_to_returned(self, loader):
        result = loader.find_matches(team="Flamengo", limit=10)
        assert result["total_found"] >= len(result["matches"])


# ---------------------------------------------------------------------------
# get_team_stats
# ---------------------------------------------------------------------------

class TestGetTeamStats:
    def test_returns_all_required_fields(self, loader):
        result = loader.get_team_stats("Flamengo")
        for field in ["team", "matches", "wins", "draws", "losses",
                      "goals_for", "goals_against", "win_rate"]:
            assert field in result

    def test_wdl_sum_equals_matches(self, loader):
        result = loader.get_team_stats("Corinthians")
        assert result["wins"] + result["draws"] + result["losses"] == result["matches"]

    def test_win_rate_formula(self, loader):
        result = loader.get_team_stats("Palmeiras")
        if result["matches"] > 0:
            expected = round(result["wins"] / result["matches"] * 100, 1)
            assert result["win_rate"] == expected

    def test_unknown_team_returns_zero(self, loader):
        result = loader.get_team_stats("ZZZNOTEAMZZZ")
        assert result["matches"] == 0
        assert result["wins"] == 0

    def test_competition_filter_reduces_matches(self, loader):
        full = loader.get_team_stats("Flamengo")
        filtered = loader.get_team_stats("Flamengo", competition="brasileirao")
        assert filtered["matches"] <= full["matches"]

    def test_season_filter_reduces_matches(self, loader):
        full = loader.get_team_stats("Palmeiras", competition="brasileirao")
        filtered = loader.get_team_stats("Palmeiras", competition="brasileirao", season=2022)
        assert filtered["matches"] < full["matches"]


# ---------------------------------------------------------------------------
# find_players
# ---------------------------------------------------------------------------

class TestFindPlayers:
    def test_returns_total_found_and_players(self, loader):
        result = loader.find_players(nationality="Brazil")
        assert "total_found" in result
        assert "players" in result

    def test_nationality_filter(self, loader):
        result = loader.find_players(nationality="Brazil", limit=10)
        for p in result["players"]:
            assert "Brazil" in p["nationality"]

    def test_club_filter(self, loader):
        result = loader.find_players(club="Santos", limit=10)
        for p in result["players"]:
            assert "Santos" in p["club"]

    def test_name_filter(self, loader):
        result = loader.find_players(name="Neymar")
        assert result["total_found"] > 0
        for p in result["players"]:
            assert "Neymar" in p["name"]

    def test_min_rating_filter(self, loader):
        result = loader.find_players(min_rating=88, limit=20)
        for p in result["players"]:
            assert p["overall"] >= 88

    def test_results_sorted_by_overall_desc(self, loader):
        result = loader.find_players(nationality="Brazil", limit=10)
        ratings = [p["overall"] for p in result["players"] if p["overall"] is not None]
        assert ratings == sorted(ratings, reverse=True)

    def test_limit_caps_results(self, loader):
        result = loader.find_players(nationality="Brazil", limit=3)
        assert len(result["players"]) <= 3

    def test_player_has_required_fields(self, loader):
        result = loader.find_players(nationality="Brazil", limit=5)
        for p in result["players"]:
            for field in ["name", "nationality", "club", "position", "overall"]:
                assert field in p


# ---------------------------------------------------------------------------
# get_standings
# ---------------------------------------------------------------------------

class TestGetStandings:
    def test_2019_standings_not_empty(self, loader):
        result = loader.get_standings(2019, "brasileirao")
        assert len(result["standings"]) > 0

    def test_standings_sorted_by_points(self, loader):
        result = loader.get_standings(2019, "brasileirao")
        pts = [e["points"] for e in result["standings"]]
        assert pts == sorted(pts, reverse=True)

    def test_positions_are_1_indexed_sequential(self, loader):
        result = loader.get_standings(2019, "brasileirao")
        for i, entry in enumerate(result["standings"]):
            assert entry["position"] == i + 1

    def test_points_calculation_is_3_for_win_1_for_draw(self, loader):
        result = loader.get_standings(2019, "brasileirao")
        for e in result["standings"]:
            assert e["points"] == e["won"] * 3 + e["drawn"]

    def test_played_equals_wdl_sum(self, loader):
        result = loader.get_standings(2019, "brasileirao")
        for e in result["standings"]:
            assert e["played"] == e["won"] + e["drawn"] + e["lost"]

    def test_flamengo_is_2019_champion(self, loader):
        result = loader.get_standings(2019, "brasileirao")
        champion = result["standings"][0]
        assert "Flamengo" in champion["team"]


# ---------------------------------------------------------------------------
# get_statistics
# ---------------------------------------------------------------------------

class TestGetStatistics:
    def test_biggest_wins_sorted_by_goal_diff(self, loader):
        result = loader.get_statistics("biggest_wins", limit=10)
        diffs = [r["goal_difference"] for r in result["results"]]
        assert diffs == sorted(diffs, reverse=True)

    def test_biggest_wins_goal_diff_matches_score(self, loader):
        result = loader.get_statistics("biggest_wins", limit=5)
        for r in result["results"]:
            assert r["goal_difference"] == abs(r["home_goal"] - r["away_goal"])

    def test_avg_goals_positive(self, loader):
        result = loader.get_statistics("avg_goals", competition="brasileirao")
        assert result["avg_goals_per_match"] > 0

    def test_avg_goals_total_consistency(self, loader):
        result = loader.get_statistics("avg_goals", competition="brasileirao")
        expected = round(result["total_goals"] / result["total_matches"], 2)
        assert result["avg_goals_per_match"] == expected

    def test_home_record_adds_up(self, loader):
        result = loader.get_statistics("home_record", competition="brasileirao")
        total = result["home_wins"] + result["home_draws"] + result["home_losses"]
        assert total == result["total_matches"]

    def test_unknown_stat_type_returns_error_key(self, loader):
        result = loader.get_statistics("nonexistent_stat")
        assert "error" in result

    def test_season_filter_reduces_match_count(self, loader):
        all_res = loader.get_statistics("avg_goals", competition="brasileirao")
        s2019 = loader.get_statistics("avg_goals", competition="brasileirao", season=2019)
        assert s2019["total_matches"] < all_res["total_matches"]
