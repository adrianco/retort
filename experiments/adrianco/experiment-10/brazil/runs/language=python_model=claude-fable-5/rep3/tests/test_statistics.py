"""Feature: Statistical Analysis.

Aggregate statistics: goals per match, biggest wins, best home/away records.
"""

import queries


class TestGoalStatistics:
    def test_serie_a_average_goals(self, db):
        """Scenario: 'What's the average goals per match in the Brasileirão?'"""
        # ~8,400 unique Série A matches remain after cross-file dedup.
        stats = queries.goal_statistics(db, competition="brasileirao")
        assert stats["matches"] > 8000
        assert 2.0 < stats["avg_goals_per_match"] < 3.0

    def test_outcome_rates_sum_to_100(self, db):
        stats = queries.goal_statistics(db, competition="serie a",
                                        season=2019)
        total = (stats["home_win_rate"] + stats["draw_rate"]
                 + stats["away_win_rate"])
        assert abs(total - 100.0) < 0.5
        assert stats["home_wins"] + stats["draws"] + stats["away_wins"] == \
            stats["matches"]

    def test_home_advantage_exists(self, db):
        stats = queries.goal_statistics(db, competition="serie a")
        assert stats["home_win_rate"] > stats["away_win_rate"]

    def test_empty_filter_handled(self, db):
        assert queries.goal_statistics(db, season=1950)["matches"] == 0


class TestBiggestWins:
    def test_biggest_win_in_dataset(self, db):
        """Scenario: 'Show me the biggest wins in the dataset'."""
        wins = queries.biggest_wins(db, limit=5)
        assert len(wins) == 5
        assert wins[0]["margin"] == 8                  # São Paulo 9-1
        margins = [w["margin"] for w in wins]
        assert margins == sorted(margins, reverse=True)

    def test_filtered_by_competition_and_season(self, db):
        wins = queries.biggest_wins(db, competition="serie a", season=2019,
                                    limit=3)
        assert all(w["competition"] == "Brasileirão Série A" for w in wins)
        assert all(w["season"] == 2019 for w in wins)

    def test_no_duplicate_entries(self, db):
        wins = queries.biggest_wins(db, limit=20)
        seen = {(w["date"], w["score"]) for w in wins}
        assert len(seen) == len(wins)


class TestBestRecords:
    def test_best_away_record(self, db):
        """Scenario: 'Which team has the best away record?'"""
        ranked = queries.best_records(db, venue="away",
                                      competition="serie a",
                                      min_matches=100, limit=5)
        assert ranked
        rates = [e["win_rate"] for e in ranked]
        assert rates == sorted(rates, reverse=True)
        for entry in ranked:
            assert entry["played"] >= 100
            assert entry["wins"] + entry["draws"] + entry["losses"] == \
                entry["played"]

    def test_min_matches_filters_small_samples(self, db):
        ranked = queries.best_records(db, venue="home", min_matches=400)
        assert all(e["played"] >= 400 for e in ranked)

    def test_invalid_venue_rejected(self, db):
        import pytest
        with pytest.raises(ValueError):
            queries.best_records(db, venue="space")


class TestDataSummary:
    def test_summary_covers_all_competitions(self, db):
        summary = queries.data_summary(db)
        assert summary["total_matches"] == len(db.matches)
        assert summary["total_players"] == 18207
        assert summary["brazilian_players"] == 827
        serie_a = summary["competitions"]["Brasileirão Série A"]
        assert serie_a["first_season"] == 2003
        assert serie_a["last_season"] >= 2023
        assert len(summary["source_files"]) == 5
