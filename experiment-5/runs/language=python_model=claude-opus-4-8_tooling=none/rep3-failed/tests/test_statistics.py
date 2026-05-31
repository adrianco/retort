"""BDD: statistical analysis.

Feature: Statistical Analysis
  Scenario: Average goals per match
  Scenario: Biggest victories
  Scenario: Best home / away records
"""


def test_average_goals_reasonable(graph):
    stats = graph.average_goals("Brasileirão")
    assert stats["matches"] > 1000
    assert 2.0 <= stats["avg_goals"] <= 3.5
    total = stats["home_win_rate"] + stats["away_win_rate"] + stats["draw_rate"]
    assert abs(total - 100.0) < 0.5


def test_biggest_wins_ordered_by_margin(graph):
    wins = graph.biggest_wins(limit=10)
    margins = [abs(m.home_goal - m.away_goal) for m in wins]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 5


def test_best_home_record(graph):
    ranked = graph.best_record(competition="Brasileirão", season=2019,
                               venue="home")
    assert ranked
    # Best home win-rate should be at the top.
    assert ranked[0].win_rate >= ranked[-1].win_rate


def test_top_scoring_team(graph):
    rec = graph.top_scoring_team(competition="Brasileirão", season=2019)
    assert rec is not None
    assert rec.goals_for > 0
