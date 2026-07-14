"""Feature: Team queries

Scenario: Get team statistics
  Given the match data is loaded
  When I request statistics for "Palmeiras" in season "2023"
  Then I should receive wins, losses, draws, and goals
"""

import queries


class TestTeamStatistics:
    def test_palmeiras_2023_statistics(self, db):
        # When I request statistics for "Palmeiras" in season "2023"
        stats = queries.team_stats("Palmeiras", season=2023)
        # Then I should receive wins, losses, draws, and goals
        assert stats["matches"] > 0
        for key in ("wins", "losses", "draws", "goals_for", "goals_against"):
            assert key in stats and stats[key] >= 0
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]

    def test_home_record(self, db):
        # "What is Corinthians' home record in 2022?"
        stats = queries.team_stats("Corinthians", season=2022,
                                   competition="brasileirao", venue="home")
        assert stats["venue"] == "home"
        assert stats["matches"] > 0
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]
        assert 0 <= stats["win_rate"] <= 100

    def test_home_and_away_sum_to_total(self, db):
        total = queries.team_stats("Santos", season=2019, competition="serie-a")
        home = queries.team_stats("Santos", season=2019, competition="serie-a",
                                  venue="home")
        away = queries.team_stats("Santos", season=2019, competition="serie-a",
                                  venue="away")
        assert home["matches"] + away["matches"] == total["matches"]
        assert home["wins"] + away["wins"] == total["wins"]
        assert home["goals_for"] + away["goals_for"] == total["goals_for"]

    def test_team_name_variants_give_same_stats(self, db):
        # Handles team name variations correctly
        a = queries.team_stats("Flamengo-RJ", season=2019, competition="serie-a")
        b = queries.team_stats("Flamengo", season=2019, competition="serie-a")
        assert a["matches"] == b["matches"] == 38
        assert a["wins"] == b["wins"]


class TestTeamCompetitions:
    def test_palmeiras_competitions(self, db):
        # "What competitions has Palmeiras played in?"
        result = queries.team_competitions("Palmeiras")
        comps = set(result["competitions"])
        assert "Brasileirão Série A" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps

    def test_cross_file_coverage(self, db):
        # Cross-file queries: Flamengo appears in matches from several files
        result = queries.team_competitions("Flamengo")
        assert result["total_matches"] > 500
