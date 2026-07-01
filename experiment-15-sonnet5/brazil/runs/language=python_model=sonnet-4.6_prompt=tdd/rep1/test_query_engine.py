"""Tests for query_engine.py — red/green/refactor cycle."""
import pytest
from query_engine import QueryEngine


DATA_DIR = "data/kaggle"


@pytest.fixture(scope="module")
def engine():
    qe = QueryEngine(DATA_DIR)
    qe.load()
    return qe


# ------------------------------------------------------------------ search_matches

class TestSearchMatches:
    def test_find_by_team_returns_results(self, engine):
        results = engine.search_matches(team="Flamengo")
        assert len(results) > 0

    def test_find_by_team_only_includes_that_team(self, engine):
        results = engine.search_matches(team="Palmeiras")
        for r in results:
            teams = (r["home_team"].lower(), r["away_team"].lower())
            assert any("palmeiras" in t for t in teams)

    def test_find_by_home_team(self, engine):
        results = engine.search_matches(home_team="Fluminense")
        for r in results:
            assert "fluminense" in r["home_team"].lower()

    def test_find_by_away_team(self, engine):
        results = engine.search_matches(away_team="Botafogo")
        for r in results:
            assert "botafogo" in r["away_team"].lower()

    def test_find_by_season(self, engine):
        results = engine.search_matches(season=2019)
        assert len(results) > 0
        for r in results:
            assert r["season"] == 2019

    def test_find_by_competition(self, engine):
        results = engine.search_matches(competition="brasileirao")
        assert len(results) > 4000

    def test_find_copa_brasil(self, engine):
        results = engine.search_matches(competition="copa_brasil")
        assert len(results) > 1300

    def test_find_libertadores(self, engine):
        results = engine.search_matches(competition="libertadores")
        assert len(results) > 1200

    def test_find_by_team_and_season(self, engine):
        results = engine.search_matches(team="Flamengo", season=2019)
        assert len(results) > 0
        for r in results:
            assert r["season"] == 2019

    def test_result_has_required_keys(self, engine):
        results = engine.search_matches(team="Santos", season=2015)
        assert len(results) > 0
        r = results[0]
        assert "home_team" in r
        assert "away_team" in r
        assert "home_goal" in r
        assert "away_goal" in r
        assert "competition" in r

    def test_limit_parameter(self, engine):
        results = engine.search_matches(team="Flamengo", limit=10)
        assert len(results) <= 10

    def test_find_specific_derby(self, engine):
        results = engine.search_matches(team1="Flamengo", team2="Fluminense")
        assert len(results) > 0
        for r in results:
            teams = {r["home_team"].lower(), r["away_team"].lower()}
            assert any("flamengo" in t for t in teams)
            assert any("fluminense" in t for t in teams)


# ------------------------------------------------------------------ get_team_stats

class TestGetTeamStats:
    def test_returns_stats_dict(self, engine):
        stats = engine.get_team_stats("Flamengo")
        assert isinstance(stats, dict)

    def test_has_required_keys(self, engine):
        stats = engine.get_team_stats("Palmeiras")
        for key in ("matches", "wins", "draws", "losses", "goals_for", "goals_against"):
            assert key in stats, f"Missing key: {key}"

    def test_wins_plus_draws_plus_losses_equals_matches(self, engine):
        stats = engine.get_team_stats("Corinthians")
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]

    def test_filter_by_season(self, engine):
        all_stats = engine.get_team_stats("Santos")
        season_stats = engine.get_team_stats("Santos", season=2019)
        assert season_stats["matches"] <= all_stats["matches"]

    def test_filter_by_competition(self, engine):
        stats = engine.get_team_stats("Flamengo", competition="brasileirao")
        assert stats["matches"] > 0

    def test_home_record_filter(self, engine):
        stats = engine.get_team_stats("Corinthians", home_only=True)
        assert "home_wins" in stats or stats["matches"] > 0

    def test_nonexistent_team_returns_zero_matches(self, engine):
        stats = engine.get_team_stats("Team That Does Not Exist")
        assert stats["matches"] == 0


# ------------------------------------------------------------------ search_players

class TestSearchPlayers:
    def test_find_by_name(self, engine):
        results = engine.search_players(name="Neymar")
        assert len(results) > 0

    def test_name_search_case_insensitive(self, engine):
        results = engine.search_players(name="neymar")
        assert len(results) > 0

    def test_find_by_nationality_brazilian(self, engine):
        results = engine.search_players(nationality="Brazil")
        assert len(results) > 100

    def test_all_results_are_correct_nationality(self, engine):
        results = engine.search_players(nationality="Brazil")
        for r in results:
            assert r["Nationality"] == "Brazil"

    def test_find_by_club(self, engine):
        # Fluminense is a Brazilian club present in the FIFA dataset
        results = engine.search_players(club="Fluminense")
        assert len(results) > 0

    def test_find_by_position(self, engine):
        results = engine.search_players(position="GK")
        assert len(results) > 0

    def test_sort_by_overall_rating(self, engine):
        results = engine.search_players(nationality="Brazil", sort_by="Overall")
        ratings = [r["Overall"] for r in results]
        assert ratings == sorted(ratings, reverse=True)

    def test_limit_parameter(self, engine):
        results = engine.search_players(nationality="Brazil", limit=5)
        assert len(results) <= 5

    def test_result_has_required_keys(self, engine):
        results = engine.search_players(name="Neymar")
        r = results[0]
        for key in ("Name", "Nationality", "Overall", "Club", "Position"):
            assert key in r

    def test_partial_name_search(self, engine):
        results = engine.search_players(name="Gabriel")
        assert len(results) > 1


# ------------------------------------------------------------------ get_head_to_head

class TestGetHeadToHead:
    def test_returns_dict(self, engine):
        h2h = engine.get_head_to_head("Flamengo", "Fluminense")
        assert isinstance(h2h, dict)

    def test_has_summary_keys(self, engine):
        h2h = engine.get_head_to_head("Palmeiras", "Corinthians")
        for key in ("team1_wins", "team2_wins", "draws", "total_matches", "matches"):
            assert key in h2h

    def test_wins_draws_sum_to_total(self, engine):
        h2h = engine.get_head_to_head("Santos", "São Paulo")
        assert h2h["team1_wins"] + h2h["team2_wins"] + h2h["draws"] == h2h["total_matches"]

    def test_returns_match_list(self, engine):
        h2h = engine.get_head_to_head("Flamengo", "Vasco")
        assert isinstance(h2h["matches"], list)
        assert len(h2h["matches"]) > 0

    def test_symmetric_teams_order(self, engine):
        h2h_ab = engine.get_head_to_head("Flamengo", "Botafogo")
        h2h_ba = engine.get_head_to_head("Botafogo", "Flamengo")
        assert h2h_ab["total_matches"] == h2h_ba["total_matches"]
        assert h2h_ab["team1_wins"] == h2h_ba["team2_wins"]


# ------------------------------------------------------------------ get_standings

class TestGetStandings:
    def test_returns_list(self, engine):
        standings = engine.get_standings(season=2019, competition="brasileirao")
        assert isinstance(standings, list)

    def test_standings_have_required_keys(self, engine):
        standings = engine.get_standings(season=2019, competition="brasileirao")
        assert len(standings) > 0
        entry = standings[0]
        for key in ("team", "points", "wins", "draws", "losses", "goals_for", "goals_against"):
            assert key in entry

    def test_standings_sorted_by_points(self, engine):
        standings = engine.get_standings(season=2019, competition="brasileirao")
        pts = [s["points"] for s in standings]
        assert pts == sorted(pts, reverse=True)

    def test_points_calculation(self, engine):
        standings = engine.get_standings(season=2019, competition="brasileirao")
        for s in standings:
            expected = s["wins"] * 3 + s["draws"]
            assert s["points"] == expected

    def test_2019_champion_is_flamengo(self, engine):
        standings = engine.get_standings(season=2019, competition="brasileirao")
        assert "flamengo" in standings[0]["team"].lower()


# ------------------------------------------------------------------ get_statistics

class TestGetStatistics:
    def test_biggest_wins(self, engine):
        results = engine.get_biggest_wins(competition="brasileirao", limit=5)
        assert len(results) <= 5
        margins = [abs(r["home_goal"] - r["away_goal"]) for r in results]
        assert margins == sorted(margins, reverse=True)

    def test_average_goals(self, engine):
        avg = engine.get_average_goals(competition="brasileirao")
        assert isinstance(avg, float)
        assert 1.0 < avg < 6.0

    def test_home_win_rate(self, engine):
        rate = engine.get_home_win_rate(competition="brasileirao")
        assert 0.0 < rate < 1.0

    def test_top_scoring_teams(self, engine):
        results = engine.get_top_scoring_teams(season=2019, competition="brasileirao")
        assert len(results) > 0
        goals = [r["goals"] for r in results]
        assert goals == sorted(goals, reverse=True)
