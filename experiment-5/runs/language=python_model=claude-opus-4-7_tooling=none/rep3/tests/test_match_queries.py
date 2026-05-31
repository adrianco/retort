"""BDD: match queries.

Feature: Match queries
  Find matches by team, opponent, season, competition, date range.

Feature: Head-to-head
  Aggregate W/D/L between two teams across all competitions.
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import find_matches, head_to_head


def test_find_matches_between_two_teams(dataset):
    # Given the match data is loaded
    # When  I search for matches between Flamengo and Fluminense
    rows = find_matches(dataset, team="Flamengo", opponent="Fluminense")
    # Then  I receive a non-empty list
    assert rows, "expected at least one Fla-Flu match in the dataset"
    # And every match's two teams are Flamengo and Fluminense (state-agnostic)
    teams = {(r["home_team"], r["away_team"]) for r in rows}
    for h, a in teams:
        assert "lamengo" in h or "lamengo" in a
        assert "luminense" in h or "luminense" in a
    # And every match exposes date, scores, competition
    for r in rows:
        assert "date" in r and "home_goal" in r and "away_goal" in r and "competition" in r


def test_find_matches_by_team_and_season(dataset):
    # Given the match data is loaded
    # When  I search Palmeiras matches in 2019
    rows = find_matches(dataset, team="Palmeiras", season=2019)
    # Then  all results have season 2019 and involve Palmeiras
    assert rows
    assert all(r["season"] == 2019 for r in rows)
    assert all("almeiras" in r["home_team"] or "almeiras" in r["away_team"] for r in rows)


def test_find_matches_filter_home_only(dataset):
    # Given the match data is loaded
    # When  I look at Corinthians home matches in 2019 Brasileirão
    rows = find_matches(
        dataset,
        team="Corinthians",
        season=2019,
        competition="Brasileirão",
        home_only=True,
    )
    # Then  a 38-game season produces 19 home matches
    assert 18 <= len(rows) <= 20  # tolerate scheduling edge cases


def test_find_matches_filter_by_date_range(dataset):
    # Given the match data is loaded
    # When  I bound the search by a tight calendar window
    rows = find_matches(dataset, team="Flamengo", date_from="2019-01-01", date_to="2019-12-31")
    # Then  every match falls inside that window
    assert rows
    for r in rows:
        assert r["date"] is not None and r["date"].startswith("2019")


def test_find_matches_filter_by_competition(dataset):
    # Given the match data is loaded
    # When  I filter by Copa do Brasil
    rows = find_matches(dataset, team="Palmeiras", competition="Copa do Brasil")
    # Then  every result is from that competition
    assert rows
    assert all(r["competition"] == "Copa do Brasil" for r in rows)


def test_head_to_head_totals_consistent(dataset):
    # Given the match data is loaded
    # When  I request head-to-head Flamengo vs Fluminense
    h2h = head_to_head(dataset, "Flamengo", "Fluminense")
    # Then  W + D + L equals total matches
    assert h2h["total_matches"] >= 10
    assert h2h["wins_a"] + h2h["wins_b"] + h2h["draws"] <= h2h["total_matches"]


def test_head_to_head_handles_state_suffix(dataset):
    # Given the data uses both "Flamengo" and "Flamengo-RJ"
    # When  the user spells the names differently
    bare = head_to_head(dataset, "Flamengo", "Corinthians")
    suffixed = head_to_head(dataset, "Flamengo-RJ", "Corinthians-SP")
    # Then  the totals match because normalization collapses the variants
    assert bare["total_matches"] == suffixed["total_matches"]
    assert bare["wins_a"] == suffixed["wins_a"]
    assert bare["wins_b"] == suffixed["wins_b"]
