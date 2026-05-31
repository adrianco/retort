"""
================================================================================
test_team_queries.py - BDD scenarios for team records & head-to-head
================================================================================

Feature: Team Queries
  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2019"
    Then I should receive wins, losses, draws, and goals.
================================================================================
"""


class TestTeamRecord:
    def test_team_season_record_has_all_fields(self, engine):
        # When I request Palmeiras' 2019 Série A record
        r = engine.team_record("Palmeiras", season=2019, competition="serie_a")
        # Then wins/draws/losses/goals are present and self-consistent
        assert r["matches"] == r["wins"] + r["draws"] + r["losses"]
        assert r["matches"] >= 30
        assert r["goals_for"] > 0 and r["goals_against"] >= 0
        assert 0 <= r["win_rate"] <= 100

    def test_home_record_scope(self, engine):
        # When I ask for Corinthians' home record in 2019
        r = engine.team_record("Corinthians", season=2019, competition="serie_a",
                               home_only=True)
        # Then the scope is reported as home and the count is a half-season
        assert r["scope"] == "home"
        assert r["matches"] <= 20

    def test_points_formula(self, engine):
        r = engine.team_record("Flamengo", season=2019, competition="serie_a")
        # Then points equal 3*wins + draws
        assert r["points"] == 3 * r["wins"] + r["draws"]


class TestHeadToHead:
    def test_head_to_head_totals_add_up(self, engine):
        # When I compute the Fla x Flu derby head-to-head
        h = engine.head_to_head("Flamengo", "Fluminense")
        # Then the three outcomes sum to the total meetings
        assert h["team1_wins"] + h["team2_wins"] + h["draws"] == h["total_matches"]
        assert h["total_matches"] > 0

    def test_compare_teams_bundles_records_and_h2h(self, engine):
        # When I compare Palmeiras and Santos
        c = engine.compare_teams("Palmeiras", "Santos")
        # Then I get both records and their head-to-head
        assert c["team1_record"]["team"] == "Palmeiras"
        assert c["team2_record"]["team"] == "Santos"
        assert "total_matches" in c["head_to_head"]


class TestCompetitionsForTeam:
    def test_palmeiras_played_multiple_competitions(self, engine):
        # When I ask what competitions Palmeiras has played in
        data = engine.competitions_for_team("Palmeiras")
        names = {c["competition"] for c in data["competitions"]}
        # Then Série A and at least one cup appear
        assert "Brasileirão Série A" in names
        assert len(names) >= 2
