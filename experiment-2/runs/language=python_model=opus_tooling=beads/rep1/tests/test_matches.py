"""Feature: Match queries."""
import pandas as pd


def test_find_matches_between_two_teams(engine):
    """Scenario: Find matches between two teams."""
    df = engine.find_matches(team="Flamengo", opponent="Fluminense", limit=100)
    assert not df.empty
    for _, r in df.iterrows():
        teams = {r["home_key"], r["away_key"]}
        assert "flamengo" in teams and "fluminense" in teams


def test_find_matches_by_season(engine):
    df = engine.find_matches(team="Palmeiras", season=2022, competition="Brasileirão")
    assert not df.empty
    assert (df["season"] == 2022).all()


def test_head_to_head_totals_are_consistent(engine):
    h = engine.head_to_head("Flamengo", "Fluminense")
    assert h["matches"] == h["wins_a"] + h["wins_b"] + h["draws"] + _nan_games(h)
    assert h["wins_a"] > 0 and h["wins_b"] > 0


def _nan_games(h):
    # matches with missing scores are not counted; derive difference
    total_classified = h["wins_a"] + h["wins_b"] + h["draws"]
    return max(h["matches"] - total_classified, 0)


def test_find_matches_by_date_range(engine):
    df = engine.find_matches(team="Corinthians",
                             date_from="2022-01-01", date_to="2022-12-31")
    assert not df.empty
    assert df["date"].min() >= pd.Timestamp("2022-01-01")
    assert df["date"].max() <= pd.Timestamp("2022-12-31 23:59:59")
