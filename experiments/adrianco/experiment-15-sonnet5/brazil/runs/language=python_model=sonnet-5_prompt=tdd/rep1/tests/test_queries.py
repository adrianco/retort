import datetime

import pandas as pd
import pytest

from brazilian_soccer_mcp import queries
from brazilian_soccer_mcp.data_loader import MATCH_COLUMNS


def make_match(**kwargs):
    row = {col: None for col in MATCH_COLUMNS}
    row.update(kwargs)
    return row


@pytest.fixture
def sample_matches():
    rows = [
        make_match(
            date=datetime.date(2023, 5, 28), season=2023, round=8, competition="Brasileirao",
            source="brasileirao", home_team_raw="Fluminense-RJ", away_team_raw="Flamengo-RJ",
            home_team="fluminense", away_team="flamengo",
            home_team_display="Fluminense", away_team_display="Flamengo",
            home_goal=1, away_goal=0,
        ),
        make_match(
            date=datetime.date(2023, 9, 3), season=2023, round=22, competition="Brasileirao",
            source="brasileirao", home_team_raw="Flamengo-RJ", away_team_raw="Fluminense-RJ",
            home_team="flamengo", away_team="fluminense",
            home_team_display="Flamengo", away_team_display="Fluminense",
            home_goal=2, away_goal=1,
        ),
        make_match(
            date=datetime.date(2023, 4, 10), season=2023, round=5, competition="Brasileirao",
            source="brasileirao", home_team_raw="Flamengo-RJ", away_team_raw="Palmeiras-SP",
            home_team="flamengo", away_team="palmeiras",
            home_team_display="Flamengo", away_team_display="Palmeiras",
            home_goal=0, away_goal=0,
        ),
    ]
    return pd.DataFrame(rows)


def test_find_matches_by_team(sample_matches):
    result = queries.find_matches(sample_matches, team="flamengo")
    assert len(result) == 3


def test_find_matches_by_both_teams(sample_matches):
    result = queries.find_matches(sample_matches, team="flamengo", opponent="fluminense")
    assert len(result) == 2


def test_find_matches_sorted_most_recent_first(sample_matches):
    result = queries.find_matches(sample_matches, team="flamengo")
    dates = [m["date"] for m in result]
    assert dates == sorted(dates, reverse=True)


def test_head_to_head_counts_wins_and_draws(sample_matches):
    summary = queries.head_to_head(sample_matches, "flamengo", "fluminense")
    assert summary["team_a_wins"] == 1
    assert summary["team_b_wins"] == 1
    assert summary["draws"] == 0
    assert summary["total_matches"] == 2


def test_team_record_computes_win_loss_draw(sample_matches):
    record = queries.team_record(sample_matches, "flamengo")
    assert record["matches"] == 3
    assert record["wins"] == 1
    assert record["draws"] == 1
    assert record["losses"] == 1
    assert record["goals_for"] == 2
    assert record["goals_against"] == 2


def test_team_record_includes_display_name(sample_matches):
    record = queries.team_record(sample_matches, "flamengo")
    assert record["team_display"] == "Flamengo"


def test_team_record_home_only(sample_matches):
    record = queries.team_record(sample_matches, "flamengo", venue="home")
    assert record["matches"] == 2


def test_standings_orders_by_points_then_goal_difference(sample_matches):
    table = queries.standings(sample_matches)
    assert table[0]["team"] in {"flamengo", "fluminense"}
    positions = {row["team"]: row for row in table}
    assert positions["flamengo"]["points"] == 4
    assert positions["fluminense"]["points"] == 3
    assert positions["palmeiras"]["points"] == 1
    assert positions["flamengo"]["team_display"] == "Flamengo"


def test_biggest_wins_sorted_by_margin(sample_matches):
    blowout = make_match(
        date=datetime.date(2023, 6, 1), season=2023, round=10, competition="Brasileirao",
        source="brasileirao", home_team_raw="Flamengo-RJ", away_team_raw="Bahia-BA",
        home_team="flamengo", away_team="bahia",
        home_team_display="Flamengo", away_team_display="Bahia",
        home_goal=5, away_goal=0,
    )
    matches = pd.concat([sample_matches, pd.DataFrame([blowout])], ignore_index=True)
    wins = queries.biggest_wins(matches, n=1)
    assert len(wins) == 1
    assert wins[0]["home_team_display"] == "Flamengo"
    assert wins[0]["away_team_display"] == "Bahia"
    assert wins[0]["margin"] == 5


def test_average_goals_per_match(sample_matches):
    avg = queries.average_goals_per_match(sample_matches)
    assert avg == pytest.approx((1 + 3 + 0) / 3, rel=1e-6)


def test_home_win_rate(sample_matches):
    rate = queries.home_win_rate(sample_matches)
    assert rate == pytest.approx(2 / 3, rel=1e-6)


@pytest.fixture
def sample_players():
    rows = [
        {"name": "Neymar Jr", "nationality": "Brazil", "overall": 92, "club": "Paris Saint-Germain", "club_key": "paris saint germain", "position": "LW"},
        {"name": "Alisson", "nationality": "Brazil", "overall": 89, "club": "Liverpool", "club_key": "liverpool", "position": "GK"},
        {"name": "L. Messi", "nationality": "Argentina", "overall": 94, "club": "FC Barcelona", "club_key": "fc barcelona", "position": "RF"},
    ]
    return pd.DataFrame(rows)


def test_search_players_by_name(sample_players):
    result = queries.search_players(sample_players, name="Messi")
    assert len(result) == 1
    assert result[0]["name"] == "L. Messi"


def test_search_players_by_nationality(sample_players):
    result = queries.search_players(sample_players, nationality="Brazil")
    assert len(result) == 2


def test_top_players_sorted_by_overall(sample_players):
    result = queries.top_players(sample_players, n=2, nationality="Brazil")
    assert [p["name"] for p in result] == ["Neymar Jr", "Alisson"]
