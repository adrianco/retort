"""
================================================================================
Module: tests.test_statistics
--------------------------------------------------------------------------------
Context:
    BDD scenarios for the "Statistical Analysis" feature (TASK.md §5) — average
    goals per match, home/away win rates, biggest victories and best home/away
    records.

Responsibility:
    Validate KnowledgeGraph.average_goals / biggest_wins / best_record produce
    realistic, internally-consistent aggregates.
================================================================================
"""


class TestAverageGoals:
    def test_brasileirao_average_is_realistic(self, graph):
        # WHEN I compute average goals for the Brasileirão
        s = graph.average_goals("Brasileirão")
        # THEN it is a realistic football value
        assert 2.0 <= s["avg_goals_per_match"] <= 3.5
        assert s["matches"] > 1000

    def test_win_and_draw_rates_sum_to_100(self, graph):
        s = graph.average_goals("Brasileirão")
        total = s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"]
        assert abs(total - 100.0) < 0.2  # rounding tolerance

    def test_home_advantage_exists(self, graph):
        s = graph.average_goals("Brasileirão")
        # Home teams win more often than away teams (well-known football fact).
        assert s["home_win_rate"] > s["away_win_rate"]


class TestBiggestWins:
    def test_ordered_by_margin_descending(self, graph):
        matches = graph.biggest_wins(limit=10)
        assert matches
        margins = [abs(m.home_goal - m.away_goal) for m in matches]
        assert margins == sorted(margins, reverse=True)

    def test_biggest_win_is_a_blowout(self, graph):
        top = graph.biggest_wins(limit=1)[0]
        assert abs(top.home_goal - top.away_goal) >= 6


class TestBestRecord:
    def test_best_away_record_is_ranked(self, graph):
        rows = graph.best_record(venue="away", competition="Brasileirão",
                                season=2019, min_matches=10)
        assert rows
        rates = [r["win_rate"] for r in rows]
        assert rates == sorted(rates, reverse=True)
        # Each listed team met the minimum-match threshold.
        assert all(r["matches"] >= 10 for r in rows)

    def test_min_matches_threshold_filters(self, graph):
        rows = graph.best_record(venue="all", min_matches=500)
        # Very high threshold: only long-running clubs (or none) survive.
        assert all(r["matches"] >= 500 for r in rows)
