"""BDD: competition queries.

Feature: Computed standings
  Calculate a league table from match results.

Feature: Champion lookup
  Identify the top of a season's standings.

Feature: Season / competition listing
  Surface what's in the dataset.
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    champion,
    competition_standings,
    list_competitions,
    list_seasons,
)


def test_2019_brasileirao_champion_is_flamengo(dataset):
    # Given the data is loaded
    # When  we ask who won the 2019 Brasileirão
    c = champion(dataset, "Brasileirão", 2019)
    # Then  Flamengo is the champion
    assert c is not None
    assert c["team"] == "flamengo"
    assert c["points"] == 90


def test_standings_are_sorted_correctly(dataset):
    # Given a season is requested
    # When  we compute the standings
    table = competition_standings(dataset, "Brasileirão", 2019)
    # Then  positions are strictly increasing
    positions = [r["position"] for r in table]
    assert positions == sorted(positions)
    # And  points are non-increasing
    points = [r["points"] for r in table]
    assert points == sorted(points, reverse=True)
    # And  every team played the same number of matches in a single-round season
    matches = [r["matches"] for r in table]
    assert max(matches) - min(matches) <= 1


def test_list_competitions_includes_canonical_three(dataset):
    # Given the data covers Brasileirão, Copa do Brasil, Libertadores
    # When  we list competitions
    comps = list_competitions(dataset)
    # Then  all three appear
    assert "Brasileirão Série A" in comps
    assert "Copa do Brasil" in comps
    assert "Copa Libertadores" in comps


def test_list_seasons_for_brasileirao_includes_recent_years(dataset):
    # Given Brasileirão data spans 2003+
    # When  we list seasons
    years = list_seasons(dataset, "Brasileirão")
    # Then  recent years are present and the list is sorted
    assert 2003 in years
    assert 2019 in years
    assert years == sorted(years)


def test_unknown_season_returns_empty_standings(dataset):
    # Given a year before the data starts
    # When  we ask for standings
    table = competition_standings(dataset, "Brasileirão", 1900)
    # Then  the result is empty (not an error)
    assert table == []
