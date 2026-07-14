"""BDD scenarios: statistical analysis (TASK.md capability 5).

Feature: Statistical Analysis
  Goals-per-match averages, home/away performance, biggest wins.
"""


class TestAverageGoals:
    """Scenario: What's the average goals per match in the Brasileirão?"""

    def test_serie_a_average(self, kb):
        result = kb.average_goals(competition="Brasileirão")
        # Then a plausible league-wide average is computed
        assert result["matches"] > 8000
        assert 2.0 <= result["avg_goals_per_match"] <= 3.0
        # And outcome rates sum to ~100%
        total = (result["home_win_rate"] + result["away_win_rate"]
                 + result["draw_rate"])
        assert abs(total - 100.0) < 0.5

    def test_home_advantage_exists(self, kb):
        result = kb.average_goals(competition="Serie A")
        assert result["home_win_rate"] > result["away_win_rate"]

    def test_single_season_average(self, kb):
        result = kb.average_goals(competition="Serie A", season=2019)
        assert result["matches"] == 380


class TestBiggestWins:
    """Scenario: Show me the biggest wins in the dataset."""

    def test_sorted_by_margin(self, kb):
        wins = kb.biggest_wins(limit=10)
        margins = [w["margin"] for w in wins]
        assert len(wins) == 10
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 7

    def test_competition_filter(self, kb):
        wins = kb.biggest_wins(competition="Serie A", limit=5)
        assert all(w["competition"] == "Brasileirão Série A" for w in wins)
        # The famous 7-0s appear at the top
        assert wins[0]["margin"] == 7


class TestBestRecords:
    """Scenario: Which team has the best away record?"""

    def test_best_away_record_2019(self, kb):
        result = kb.best_record(venue="away", competition="Serie A",
                                season=2019, min_matches=10)
        teams = result["teams"]
        assert teams
        # Champions Flamengo had the best away record in 2019
        assert any("Flamengo" in t["team"] for t in teams[:1])
        rates = [t["win_rate"] for t in teams]
        assert rates == sorted(rates, reverse=True)

    def test_min_matches_threshold(self, kb):
        result = kb.best_record(venue="home", min_matches=50)
        assert all(t["matches"] >= 50 for t in result["teams"])


class TestCrossFileQueries:
    """Scenario: player data and match data can be combined."""

    def test_club_appears_in_both_datasets(self, kb):
        # Given a club present in FIFA data and in match data
        players = kb.search_players(club="Santos", limit=0)
        matches = kb.find_matches(team="Santos", competition="Serie A",
                                  season=2019, limit=0)
        # Then both sides return records for the same club
        assert players and matches
        stats = kb.team_statistics("Santos", season=2019, competition="Serie A")
        assert stats["matches"] == 38
