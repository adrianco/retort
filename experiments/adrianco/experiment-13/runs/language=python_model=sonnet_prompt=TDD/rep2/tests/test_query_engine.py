import datetime
import pytest
import pandas as pd

from query_engine import QueryEngine
from data_loader import DataLoader


# ─── Shared fixture DataFrame ──────────────────────────────────────────────────

@pytest.fixture
def matches_df():
    """Small fixture DataFrame for query engine tests."""
    return pd.DataFrame([
        # Flamengo home wins
        {"home_team": "Flamengo", "away_team": "Fluminense", "home_goal": 3, "away_goal": 1,
         "season": 2019, "date": datetime.date(2019, 5, 1), "competition": "brasileirao"},
        {"home_team": "Flamengo", "away_team": "Corinthians", "home_goal": 2, "away_goal": 0,
         "season": 2019, "date": datetime.date(2019, 6, 15), "competition": "brasileirao"},
        # Flamengo away match
        {"home_team": "Palmeiras", "away_team": "Flamengo", "home_goal": 1, "away_goal": 2,
         "season": 2019, "date": datetime.date(2019, 8, 20), "competition": "brasileirao"},
        # Fluminense vs Palmeiras
        {"home_team": "Fluminense", "away_team": "Palmeiras", "home_goal": 0, "away_goal": 0,
         "season": 2019, "date": datetime.date(2019, 9, 5), "competition": "brasileirao"},
        # Corinthians home matches
        {"home_team": "Corinthians", "away_team": "Santos", "home_goal": 1, "away_goal": 1,
         "season": 2022, "date": datetime.date(2022, 3, 10), "competition": "brasileirao"},
        {"home_team": "Corinthians", "away_team": "Palmeiras", "home_goal": 2, "away_goal": 1,
         "season": 2022, "date": datetime.date(2022, 4, 20), "competition": "brasileirao"},
        # Corinthians away match
        {"home_team": "Santos", "away_team": "Corinthians", "home_goal": 0, "away_goal": 3,
         "season": 2022, "date": datetime.date(2022, 5, 5), "competition": "brasileirao"},
        # Cup match
        {"home_team": "Flamengo", "away_team": "Santos", "home_goal": 4, "away_goal": 0,
         "season": 2020, "date": datetime.date(2020, 7, 10), "competition": "cup"},
        # Big win for biggest_wins test
        {"home_team": "Flamengo", "away_team": "Boavista", "home_goal": 8, "away_goal": 0,
         "season": 2020, "date": datetime.date(2020, 2, 1), "competition": "brasileirao"},
        # Flamengo vs Fluminense again (2020)
        {"home_team": "Fluminense", "away_team": "Flamengo", "home_goal": 1, "away_goal": 1,
         "season": 2020, "date": datetime.date(2020, 10, 15), "competition": "brasileirao"},
    ])


@pytest.fixture
def players_df():
    """Small fixture DataFrame for player tests."""
    return pd.DataFrame([
        {"Name": "Neymar Jr", "Nationality": "Brazil", "Overall": 92, "Club": "Paris SG",
         "Position": "LW", "Age": 26},
        {"Name": "neymar santos", "Nationality": "Brazil", "Overall": 75, "Club": "Santos",
         "Position": "ST", "Age": 22},
        {"Name": "Gabigol", "Nationality": "Brazil", "Overall": 80, "Club": "Flamengo",
         "Position": "ST", "Age": 23},
        {"Name": "R. Guerrero", "Nationality": "Peru", "Overall": 77, "Club": "Flamengo",
         "Position": "ST", "Age": 33},
        {"Name": "Messi", "Nationality": "Argentina", "Overall": 94, "Club": "FC Barcelona",
         "Position": "RF", "Age": 31},
        {"Name": "Nonexistent Player XYZ", "Nationality": "Unknown", "Overall": 50,
         "Club": "Unknown", "Position": "GK", "Age": 20},
    ])


@pytest.fixture
def engine(matches_df, players_df):
    """QueryEngine backed by fixture DataFrames (no real CSV loading)."""
    loader = object.__new__(DataLoader)
    loader.data_dir = None
    loader._all_matches = matches_df
    loader._players = players_df
    # Provide individual competition DataFrames for standings/stats
    brasileirao = matches_df[matches_df["competition"] == "brasileirao"].copy()
    loader._brasileirao = brasileirao
    loader._cup = matches_df[matches_df["competition"] == "cup"].copy()
    loader._libertadores = pd.DataFrame(columns=matches_df.columns)
    loader._historical = pd.DataFrame(columns=matches_df.columns)
    loader._extended = pd.DataFrame(columns=matches_df.columns)
    return QueryEngine(loader)


# ─── Cycle 4: find_matches ─────────────────────────────────────────────────────

def test_find_matches_by_team_home_and_away(engine):
    results = engine.find_matches(team="Flamengo")
    teams = [(r["home_team"], r["away_team"]) for r in results]
    for home, away in teams:
        assert home == "Flamengo" or away == "Flamengo"
    assert len(results) > 0


def test_find_matches_by_team_and_season(engine):
    results = engine.find_matches(team="Palmeiras", season=2019)
    assert all(r["season"] == 2019 for r in results)
    assert all(r["home_team"] == "Palmeiras" or r["away_team"] == "Palmeiras" for r in results)


def test_find_matches_by_competition(engine):
    results = engine.find_matches(competition="brasileirao")
    assert all(r["competition"] == "brasileirao" for r in results)
    assert len(results) > 0


def test_find_matches_by_date_range(engine):
    results = engine.find_matches(date_from="2019-01-01", date_to="2019-12-31")
    for r in results:
        assert r["date"] >= datetime.date(2019, 1, 1)
        assert r["date"] <= datetime.date(2019, 12, 31)


def test_find_matches_empty_result(engine):
    results = engine.find_matches(team="TeamThatDoesNotExist")
    assert results == []


# ─── Cycle 5: head_to_head ─────────────────────────────────────────────────────

def test_head_to_head_returns_stats(engine):
    result = engine.head_to_head("Flamengo", "Fluminense")
    assert "wins" in result
    assert "losses" in result
    assert "draws" in result
    assert "matches" in result
    assert isinstance(result["matches"], list)
    assert len(result["matches"]) > 0


def test_head_to_head_correct_win_count(engine):
    result = engine.head_to_head("Flamengo", "Fluminense")
    # Flamengo beat Fluminense 3-1 (home), drew 1-1 away
    assert result["wins"] == 1
    assert result["draws"] == 1
    assert result["losses"] == 0


def test_head_to_head_handles_state_suffix(engine):
    # "Flamengo-RJ" should match same as "Flamengo"
    result = engine.head_to_head("Flamengo-RJ", "Fluminense")
    assert len(result["matches"]) > 0


def test_head_to_head_no_matches(engine):
    result = engine.head_to_head("TeamA", "TeamB")
    assert result["wins"] == 0
    assert result["losses"] == 0
    assert result["draws"] == 0
    assert result["matches"] == []


# ─── Cycle 6: get_team_stats ───────────────────────────────────────────────────

def test_get_team_stats_returns_correct_keys(engine):
    stats = engine.get_team_stats("Corinthians")
    for key in ["wins", "draws", "losses", "goals_for", "goals_against"]:
        assert key in stats, f"Missing key: {key}"


def test_get_team_stats_correct_values(engine):
    stats = engine.get_team_stats("Corinthians")
    # Home: drew Santos 1-1 (D), beat Palmeiras 2-1 (W)
    # Away (in season 2019): lost to Flamengo 0-2
    # Away (in season 2022): beat Santos 3-0 (W)
    # Total: 2W, 1D, 1L
    assert stats["wins"] == 2
    assert stats["draws"] == 1
    assert stats["losses"] == 1


def test_get_team_stats_home_only(engine):
    stats = engine.get_team_stats("Corinthians", home_only=True)
    # Home: drew Santos 1-1 (D), beat Palmeiras 2-1 (W)
    assert stats["wins"] == 1
    assert stats["draws"] == 1
    assert stats["losses"] == 0


def test_get_team_stats_season_filter(engine):
    stats = engine.get_team_stats("Corinthians", season=2022)
    assert stats["wins"] == 2
    assert stats["draws"] == 1


# ─── Cycle 7: find_players ────────────────────────────────────────────────────

def test_find_players_by_name_partial_case_insensitive(engine):
    results = engine.find_players(name="neymar")
    assert len(results) == 2
    for r in results:
        assert "neymar" in r["Name"].lower()


def test_find_players_by_nationality(engine):
    results = engine.find_players(nationality="Brazil")
    assert all(r["Nationality"] == "Brazil" for r in results)
    assert len(results) > 0


def test_find_players_by_club(engine):
    results = engine.find_players(club="Flamengo")
    assert all(r["Club"] == "Flamengo" for r in results)
    assert len(results) > 0


def test_find_players_nonexistent(engine):
    results = engine.find_players(name="Nonexistent Player XYZ")
    # This player exists in fixture, but searching for exact match via partial should work
    assert len(results) == 1


def test_find_players_empty_when_no_match(engine):
    results = engine.find_players(name="ZZZImpossibleName999")
    assert results == []


# ─── Cycle 8: get_standings ───────────────────────────────────────────────────

def test_get_standings_returns_sorted_list(engine):
    standings = engine.get_standings(season=2019, competition="brasileirao")
    assert isinstance(standings, list)
    assert len(standings) > 0
    # Check sorted by points descending
    points = [s["points"] for s in standings]
    assert points == sorted(points, reverse=True)


def test_get_standings_correct_keys(engine):
    standings = engine.get_standings(season=2019, competition="brasileirao")
    for entry in standings:
        for key in ["team", "points", "wins", "draws", "losses", "goals_for", "goals_against"]:
            assert key in entry, f"Missing key: {key}"


def test_get_standings_points_calculation(engine):
    standings = engine.get_standings(season=2019, competition="brasileirao")
    for entry in standings:
        expected = entry["wins"] * 3 + entry["draws"]
        assert entry["points"] == expected


# ─── Cycle 9: statistics ──────────────────────────────────────────────────────

def test_get_biggest_wins_returns_sorted(engine):
    results = engine.get_biggest_wins(limit=3)
    assert len(results) <= 3
    # Sorted by goal difference descending
    diffs = [r["goal_diff"] for r in results]
    assert diffs == sorted(diffs, reverse=True)


def test_get_biggest_wins_has_correct_keys(engine):
    results = engine.get_biggest_wins(limit=3)
    for r in results:
        for key in ["home_team", "away_team", "home_goal", "away_goal", "goal_diff"]:
            assert key in r, f"Missing key: {key}"


def test_competition_averages_returns_dict(engine):
    result = engine.competition_averages()
    assert "avg_goals_per_match" in result
    assert "home_win_rate" in result


def test_competition_averages_values_in_range(engine):
    result = engine.competition_averages()
    assert 0 <= result["home_win_rate"] <= 1
    assert result["avg_goals_per_match"] >= 0
