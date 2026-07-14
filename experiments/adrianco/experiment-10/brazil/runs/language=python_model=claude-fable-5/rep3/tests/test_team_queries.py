"""Feature: Team Queries.

Scenario (from the spec): Get team statistics
  Given the match data is loaded
  When I request statistics for "Palmeiras" in season "2023"
  Then I should receive wins, losses, draws, and goals
"""

import queries


class TestTeamStatistics:
    def test_palmeiras_2023_statistics(self, db):
        # When I request statistics for "Palmeiras" in season "2023"
        stats = queries.team_statistics(db, "Palmeiras", season=2023)
        # Then I should receive wins, losses, draws, and goals
        assert stats["played"] > 0
        assert stats["played"] == (stats["wins"] + stats["draws"]
                                   + stats["losses"])
        assert stats["goals_for"] > 0
        assert stats["goals_against"] > 0
        assert 0 <= stats["win_rate"] <= 100

    def test_home_away_split_adds_up(self, db):
        total = queries.team_statistics(db, "Flamengo", season=2019,
                                        competition="serie a")
        home = queries.team_statistics(db, "Flamengo", season=2019,
                                       competition="serie a", venue="home")
        away = queries.team_statistics(db, "Flamengo", season=2019,
                                       competition="serie a", venue="away")
        assert home["played"] == away["played"] == 19
        assert home["played"] + away["played"] == total["played"]
        assert home["wins"] + away["wins"] == total["wins"]
        assert home["goals_for"] + away["goals_for"] == total["goals_for"]

    def test_team_name_variants_give_identical_stats(self, db):
        a = queries.team_statistics(db, "Flamengo-RJ", season=2019)
        b = queries.team_statistics(db, "flamengo", season=2019)
        assert a == b

    def test_invalid_venue_rejected(self, db):
        import pytest
        with pytest.raises(ValueError):
            queries.team_statistics(db, "Santos", venue="neutral")


class TestHeadToHead:
    def test_fla_flu_record_is_consistent(self, db):
        result = queries.head_to_head(db, "Flamengo", "Fluminense")
        assert result["team1"] == "Flamengo"
        assert result["team2"] == "Fluminense"
        assert result["matches"] >= 40
        scored = (result["team1_wins"] + result["team2_wins"]
                  + result["draws"])
        assert scored <= result["matches"]
        assert len(result["recent_matches"]) == result["matches"]

    def test_head_to_head_is_symmetric(self, db):
        ab = queries.head_to_head(db, "Palmeiras", "Santos")
        ba = queries.head_to_head(db, "Santos", "Palmeiras")
        assert ab["matches"] == ba["matches"]
        assert ab["team1_wins"] == ba["team2_wins"]
        assert ab["draws"] == ba["draws"]
        assert ab["team1_goals"] == ba["team2_goals"]

    def test_no_meetings_reports_zero(self, db):
        result = queries.head_to_head(db, "Flamengo", "Atlantis United FC")
        assert result["matches"] == 0
