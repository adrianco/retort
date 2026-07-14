"""Tests for query_engine.py - TDD for Brazilian Soccer MCP Server."""
import os
import pytest
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "kaggle")


@pytest.fixture(scope="module")
def engine():
    from data_loader import DataLoader
    from query_engine import QueryEngine
    loader = DataLoader(DATA_DIR)
    return QueryEngine(loader)


# ─── Cycle 1: find_matches ────────────────────────────────────────────────────

def test_find_matches_by_team_returns_list(engine):
    results = engine.find_matches(team="Flamengo")
    assert isinstance(results, list)
    assert len(results) > 0


def test_find_matches_by_team_only_includes_that_team(engine):
    results = engine.find_matches(team="Palmeiras")
    for m in results:
        names = {m["home_team_norm"], m["away_team_norm"]}
        assert "Palmeiras" in names, f"Palmeiras not in {names}"


def test_find_matches_by_competition_brasileirao(engine):
    results = engine.find_matches(competition="Brasileirão")
    assert len(results) > 4000
    for m in results:
        assert m["competition"] == "Brasileirão"


def test_find_matches_by_competition_case_insensitive(engine):
    r1 = engine.find_matches(competition="brasileirao")
    r2 = engine.find_matches(competition="Brasileirão")
    assert len(r1) == len(r2)


def test_find_matches_by_season(engine):
    results = engine.find_matches(season=2022)
    assert len(results) > 0
    for m in results:
        assert m["season"] == 2022


def test_find_matches_by_two_teams_head_to_head(engine):
    results = engine.find_matches(team="Flamengo", team2="Fluminense")
    assert len(results) > 0
    for m in results:
        teams = {m["home_team_norm"], m["away_team_norm"]}
        assert "Flamengo" in teams and "Fluminense" in teams


def test_find_matches_combined_filters(engine):
    results = engine.find_matches(team="Corinthians", season=2021)
    assert len(results) > 0
    for m in results:
        assert m["season"] == 2021
        teams = {m["home_team_norm"], m["away_team_norm"]}
        assert "Corinthians" in teams


def test_find_matches_limit(engine):
    results = engine.find_matches(team="Flamengo", limit=10)
    assert len(results) <= 10


def test_find_matches_returns_score(engine):
    results = engine.find_matches(team="Flamengo", limit=5)
    for m in results:
        assert "home_goal" in m and "away_goal" in m


# ─── Cycle 2: team_stats ─────────────────────────────────────────────────────

def test_team_stats_returns_dict(engine):
    stats = engine.team_stats("Corinthians")
    assert isinstance(stats, dict)


def test_team_stats_has_wins_losses_draws(engine):
    stats = engine.team_stats("Flamengo")
    assert "wins" in stats and "losses" in stats and "draws" in stats


def test_team_stats_total_matches_equals_sum(engine):
    stats = engine.team_stats("Palmeiras")
    assert stats["total"] == stats["wins"] + stats["losses"] + stats["draws"]


def test_team_stats_filtered_by_season(engine):
    stats_all = engine.team_stats("Corinthians")
    stats_2022 = engine.team_stats("Corinthians", season=2022)
    assert stats_2022["total"] < stats_all["total"]


def test_team_stats_filtered_by_competition(engine):
    stats = engine.team_stats("Palmeiras", competition="Brasileirão")
    assert stats["total"] > 0


def test_team_stats_home_away_split(engine):
    stats = engine.team_stats("Flamengo")
    assert "home_wins" in stats and "away_wins" in stats


def test_team_stats_goals(engine):
    stats = engine.team_stats("Flamengo")
    assert "goals_scored" in stats and "goals_conceded" in stats
    assert stats["goals_scored"] > 0


def test_team_stats_unknown_team_returns_zero_total(engine):
    stats = engine.team_stats("NonExistentTeamXYZ")
    assert stats["total"] == 0


# ─── Cycle 3: head_to_head ────────────────────────────────────────────────────

def test_head_to_head_returns_dict(engine):
    result = engine.head_to_head("Flamengo", "Fluminense")
    assert isinstance(result, dict)


def test_head_to_head_has_win_counts(engine):
    result = engine.head_to_head("Flamengo", "Fluminense")
    assert "team1_wins" in result and "team2_wins" in result and "draws" in result


def test_head_to_head_totals_consistent(engine):
    result = engine.head_to_head("Flamengo", "Corinthians")
    assert result["total"] == result["team1_wins"] + result["team2_wins"] + result["draws"]


def test_head_to_head_symmetric_totals(engine):
    r1 = engine.head_to_head("Flamengo", "Fluminense")
    r2 = engine.head_to_head("Fluminense", "Flamengo")
    assert r1["total"] == r2["total"]


# ─── Cycle 4: find_players ───────────────────────────────────────────────────

def test_find_players_by_name_returns_list(engine):
    results = engine.find_players(name="Neymar")
    assert isinstance(results, list)
    assert len(results) > 0


def test_find_players_by_name_case_insensitive(engine):
    r1 = engine.find_players(name="neymar")
    r2 = engine.find_players(name="Neymar")
    assert len(r1) == len(r2)


def test_find_players_by_nationality(engine):
    results = engine.find_players(nationality="Brazil")
    assert len(results) > 100
    for p in results:
        assert p["Nationality"] == "Brazil"


def test_find_players_by_club(engine):
    results = engine.find_players(club="Fluminense")
    assert len(results) > 0
    for p in results:
        assert "Fluminense" in str(p["Club"])


def test_find_players_sorted_by_overall(engine):
    results = engine.find_players(nationality="Brazil", sort_by="Overall", limit=10)
    ratings = [p["Overall"] for p in results]
    assert ratings == sorted(ratings, reverse=True)


def test_find_players_limit(engine):
    results = engine.find_players(nationality="Brazil", limit=5)
    assert len(results) == 5


def test_find_players_has_required_fields(engine):
    results = engine.find_players(name="Neymar", limit=1)
    assert len(results) > 0
    p = results[0]
    for field in ("Name", "Nationality", "Overall", "Club", "Position"):
        assert field in p


# ─── Cycle 5: season_standings ───────────────────────────────────────────────

def test_season_standings_returns_list(engine):
    table = engine.season_standings(2019, "Brasileirão")
    assert isinstance(table, list)
    assert len(table) > 0


def test_season_standings_sorted_by_points(engine):
    table = engine.season_standings(2019, "Brasileirão")
    points = [t["points"] for t in table]
    assert points == sorted(points, reverse=True)


def test_season_standings_has_required_fields(engine):
    table = engine.season_standings(2019, "Brasileirão")
    for entry in table[:5]:
        for field in ("team", "points", "wins", "draws", "losses", "goals_for", "goals_against"):
            assert field in entry, f"Missing {field}"


def test_season_standings_points_formula(engine):
    table = engine.season_standings(2019, "Brasileirão")
    for t in table:
        expected = t["wins"] * 3 + t["draws"]
        assert t["points"] == expected


def test_season_standings_flamengo_won_2019(engine):
    table = engine.season_standings(2019, "Brasileirão")
    # Flamengo won 2019 Brasileirão
    if table:
        champion = table[0]["team"]
        assert "Flamengo" in champion


# ─── Cycle 6: top_stats ──────────────────────────────────────────────────────

def test_biggest_wins_returns_list(engine):
    results = engine.biggest_wins(competition="Brasileirão", limit=5)
    assert isinstance(results, list)
    assert len(results) <= 5


def test_biggest_wins_sorted_by_margin(engine):
    results = engine.biggest_wins(competition="Brasileirão", limit=10)
    margins = [abs(m["home_goal"] - m["away_goal"]) for m in results]
    assert margins == sorted(margins, reverse=True)


def test_average_goals_per_match(engine):
    avg = engine.average_goals_per_match("Brasileirão")
    assert isinstance(avg, float)
    assert 1.5 < avg < 5.0


def test_home_win_rate(engine):
    rate = engine.home_win_rate("Brasileirão")
    assert isinstance(rate, float)
    assert 0.3 < rate < 0.7


def test_top_scoring_teams(engine):
    results = engine.top_scoring_teams("Brasileirão", season=2022, limit=5)
    assert isinstance(results, list)
    assert len(results) <= 5
    goals = [t["goals"] for t in results]
    assert goals == sorted(goals, reverse=True)
