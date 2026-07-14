"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
File      : tests/test_teams.py
Purpose   : BDD tests for team statistics (brazilian_soccer.queries.teams).

Mirrors the Gherkin "Scenario: Get team statistics" — requesting a team's record
for a season yields wins/losses/draws and goals, with internally consistent
totals.
================================================================================
"""

from brazilian_soccer.queries import teams


class TestTeamRecord:
    def test_record_fields_are_consistent(self, kg):
        # When I request Palmeiras' 2019 record
        rec = teams.team_record(kg, "Palmeiras", season=2019)
        # Then wins + draws + losses equals matches played
        assert rec["matches"] > 0
        assert rec["wins"] + rec["draws"] + rec["losses"] == rec["matches"]
        # And points follow the 3/1/0 rule
        assert rec["points"] == rec["wins"] * 3 + rec["draws"]
        # And win rate is a sensible fraction
        assert 0.0 <= rec["win_rate"] <= 1.0

    def test_home_and_away_split_sums_to_total(self, kg):
        # Given Corinthians' 2022 record split by venue
        total = teams.team_record(kg, "Corinthians", season=2022)
        home = teams.team_record(kg, "Corinthians", season=2022, venue="home")
        away = teams.team_record(kg, "Corinthians", season=2022, venue="away")
        # Then home + away matches equals all matches
        assert home["matches"] + away["matches"] == total["matches"]
        assert home["wins"] + away["wins"] == total["wins"]
        assert home["goals_for"] + away["goals_for"] == total["goals_for"]

    def test_unknown_team_returns_empty_record(self, kg):
        # When I request a team that does not exist
        rec = teams.team_record(kg, "Nonexistent United FC")
        # Then an empty (zeroed) record is returned, not an error
        assert rec["matches"] == 0
        assert rec["win_rate"] == 0.0


class TestTeamCompetitions:
    def test_lists_known_competitions(self, kg):
        # When I ask which competitions Palmeiras has played in
        info = teams.team_competitions(kg, "Palmeiras")
        # Then the major Brazilian competitions appear
        assert info["total_matches"] > 0
        assert "Brasileirao" in info["competitions"]
