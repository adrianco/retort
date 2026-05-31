"""BDD: team queries.

Feature: Team Queries
  Scenario: Get team statistics for a season
  Scenario: Compare two teams head-to-head
"""


def test_team_record_known_values(graph):
    # Atlético-MG finished 2019 Série A with 18W 7D 13L (61 pts).
    rec = graph.team_record("Atlético-MG", season=2019, competition="Brasileirão")
    assert rec.matches == 38
    assert rec.wins == 18
    assert rec.draws == 7
    assert rec.losses == 13
    assert rec.points == 61


def test_team_record_internally_consistent(graph):
    rec = graph.team_record("Palmeiras", season=2022, competition="Brasileirão")
    assert rec.matches == rec.wins + rec.draws + rec.losses
    assert rec.matches > 0
    assert 0 <= rec.win_rate <= 100


def test_home_and_away_split_sums_to_total(graph):
    overall = graph.team_record("Corinthians", season=2022, competition="Brasileirão")
    home = graph.team_record("Corinthians", season=2022,
                             competition="Brasileirão", venue="home")
    away = graph.team_record("Corinthians", season=2022,
                             competition="Brasileirão", venue="away")
    assert home.matches + away.matches == overall.matches
    assert home.wins + away.wins == overall.wins


def test_compare_teams_head_to_head(graph):
    h2h = graph.head_to_head("Palmeiras", "Santos")
    assert h2h["total"] > 0
    assert h2h["team1"].lower().startswith("palmeiras")
