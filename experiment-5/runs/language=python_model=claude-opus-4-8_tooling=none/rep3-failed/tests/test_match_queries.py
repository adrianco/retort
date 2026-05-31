"""BDD: match queries.

Feature: Match Queries
  Scenario: Find matches between two teams
  Scenario: Filter matches by season / competition / venue
  Scenario: Head-to-head record between rivals
"""


def test_find_matches_between_two_teams(graph):
    # Given match data / When searching Flamengo vs Fluminense / Then matches
    matches = graph.find_matches(team="Flamengo", opponent="Fluminense")
    assert matches
    for m in matches:
        keys = {m.home_key, m.away_key}
        assert "flamengo" in keys and "fluminense" in keys
        assert m.match_date is not None
        assert m.competition


def test_find_matches_by_season(graph):
    matches = graph.find_matches(team="Palmeiras", season=2022,
                                 competition="Brasileirão")
    assert matches
    assert all(m.season == 2022 for m in matches)
    assert all(m.competition == "Brasileirão Série A" for m in matches)


def test_find_matches_home_only(graph):
    home = graph.find_matches(team="Corinthians", season=2022,
                              competition="Brasileirão", venue="home")
    assert home
    assert all(m.home_key == "corinthians" for m in home)


def test_find_matches_sorted_newest_first(graph):
    matches = graph.find_matches(team="Santos", limit=10)
    dates = [m.date_str for m in matches]
    assert dates == sorted(dates, reverse=True)


def test_head_to_head_totals_are_consistent(graph):
    h2h = graph.head_to_head("Flamengo", "Fluminense")
    assert h2h["total"] > 10
    decided = h2h["team1_wins"] + h2h["team2_wins"] + h2h["draws"]
    # decided counts only scored matches; cannot exceed total
    assert decided <= h2h["total"]
    assert decided > 0


def test_find_matches_by_date_range(graph):
    matches = graph.find_matches(team="Flamengo",
                                 date_from="2019-01-01", date_to="2019-12-31")
    assert matches
    assert all("2019-01-01" <= m.date_str <= "2019-12-31" for m in matches)
