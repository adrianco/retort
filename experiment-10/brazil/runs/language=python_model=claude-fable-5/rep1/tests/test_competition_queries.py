"""Feature: Competition queries and statistical analysis

Standings are calculated from match results; aggregates such as average
goals per match and biggest wins are computed across the datasets.
"""

import queries


class TestStandings:
    def test_2019_brasileirao_champion(self, db):
        # "Who won the 2019 Brasileirão?" — Flamengo, with 90 points
        table = queries.standings(2019)
        assert table["champion"] == "Flamengo"
        top = table["standings"][0]
        assert top["points"] == 90
        assert top["wins"] == 28
        assert top["draws"] == 6
        assert top["losses"] == 4

    def test_standings_are_a_complete_league_table(self, db):
        table = queries.standings(2019)
        assert len(table["standings"]) == 20
        for row in table["standings"]:
            assert row["played"] == 38
            assert row["points"] == row["wins"] * 3 + row["draws"]

    def test_relegated_teams(self, db):
        # The bottom four of a complete season are relegated
        table = queries.standings(2019)
        assert len(table["relegated"]) == 4
        assert "Cruzeiro" in table["relegated"]  # famous 2019 relegation

    def test_historical_season_from_2003_file(self, db):
        # Seasons before 2012 only exist in novo_campeonato_brasileiro.csv
        table = queries.standings(2008)
        assert table["standings"], "2008 season should be available"
        assert table["champion"] == "São Paulo"

    def test_unavailable_season_reports_options(self, db):
        result = queries.standings(1980)
        assert "error" in result
        assert 2019 in result["available_seasons"]


class TestStatisticalAnalysis:
    def test_average_goals_per_match_is_plausible(self, db):
        # "What's the average goals per match in the Brasileirão?"
        stats = queries.competition_stats(competition="serie-a")
        assert 2.0 <= stats["avg_goals_per_match"] <= 3.2
        assert stats["matches"] > 8000

    def test_home_advantage_exists(self, db):
        stats = queries.competition_stats(competition="serie-a")
        assert stats["home_win_rate"] > stats["away_win_rate"]
        rates = stats["home_win_rate"] + stats["away_win_rate"] + stats["draw_rate"]
        assert abs(rates - 100) < 0.5

    def test_biggest_wins_are_sorted_by_margin(self, db):
        result = queries.biggest_wins(limit=10)
        margins = [m["margin"] for m in result["matches"]]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 5

    def test_best_away_records(self, db):
        # "Which team has the best away record?"
        result = queries.best_records(venue="away", min_matches=50, limit=5)
        assert result["teams"]
        rates = [t["win_rate"] for t in result["teams"]]
        assert rates == sorted(rates, reverse=True)
        for t in result["teams"]:
            assert t["matches"] >= 50

    def test_season_comparison(self, db):
        # "Compare the 2018 and 2019 seasons"
        s2018 = queries.competition_stats(competition="serie-a", season=2018)
        s2019 = queries.competition_stats(competition="serie-a", season=2019)
        assert s2018["matches"] == s2019["matches"] == 380


class TestDataSummary:
    def test_all_competitions_are_covered(self, db):
        summary = queries.competition_seasons()
        assert "Brasileirão Série A" in summary
        assert "Copa do Brasil" in summary
        assert "Copa Libertadores" in summary
        assert summary["Brasileirão Série A"]["seasons"].startswith("2003")
