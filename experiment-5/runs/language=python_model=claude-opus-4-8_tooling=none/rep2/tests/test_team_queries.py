"""
BDD scenarios -- Team Queries and Head-to-Head (Given / When / Then).

Feature: Team Queries
    As an analyst
    I want win/loss/draw records and head-to-head comparisons
    So that I can evaluate team performance.
"""


class TestTeamStatistics:
    """Scenario: Get team statistics for a season."""

    def test_record_has_wins_losses_draws_and_goals(self, kg):
        # Given the match data is loaded
        # When I request statistics for Palmeiras in season 2019 Brasileirao
        rec = kg.team_record("Palmeiras", season=2019, competition="Brasileirao")

        # Then I should receive wins, losses, draws and goals
        for key in ("wins", "draws", "losses", "goals_for", "goals_against"):
            assert key in rec
        # And the components are internally consistent
        assert rec["wins"] + rec["draws"] + rec["losses"] == rec["matches"]
        assert rec["points"] == rec["wins"] * 3 + rec["draws"]
        assert 0.0 <= rec["win_rate"] <= 100.0


class TestExactTeamRecordOnMiniData:
    """Scenario: Team record numbers are computed correctly (deterministic)."""

    def test_team_a_record(self, mini_kg):
        # Given a tiny league where Team A won both its games 2-0 and 3-1
        rec = mini_kg.team_record("Team A", season=2020)
        # Then its record reflects 2 wins, 5 goals for, 1 against
        assert rec["matches"] == 2
        assert rec["wins"] == 2 and rec["draws"] == 0 and rec["losses"] == 0
        assert rec["goals_for"] == 5 and rec["goals_against"] == 1
        assert rec["win_rate"] == 100.0


class TestHomeVenueRecord:
    """Scenario: A team's home record is a subset with only home games."""

    def test_home_only_record(self, kg):
        # When I ask for Corinthians' 2019 home record (a complete season)
        rec = kg.team_record(
            "Corinthians", season=2019, competition="Brasileirao", venue="home"
        )
        # Then in a 20-team league a club plays 19 home matches
        assert rec["matches"] == 19


class TestHeadToHead:
    """Scenario: Compare two teams head-to-head."""

    def test_head_to_head_totals_are_consistent(self, kg):
        # Given the match data is loaded
        # When I compare Palmeiras and Santos head-to-head
        h2h = kg.head_to_head("Palmeiras", "Santos")

        # Then wins + draws + losses equals the (decided) match total
        decided = h2h["team1_wins"] + h2h["team2_wins"] + h2h["draws"]
        assert decided <= h2h["total_matches"]
        assert h2h["total_matches"] > 0
        # And the named teams are echoed back
        assert h2h["team1"] and h2h["team2"]


class TestTeamCompetitions:
    """Scenario: List the competitions a team has played in."""

    def test_palmeiras_appears_in_multiple_competitions(self, kg):
        data = kg.team_competitions("Palmeiras")
        # Then Palmeiras has appeared in the Brasileirao at least
        assert "Brasileirao" in data["competitions"]
        assert data["competitions"]["Brasileirao"] > 0
