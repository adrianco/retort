"""
==============================================================================
File: tests/test_team_queries.py
==============================================================================
CONTEXT
-------
BDD tests for the TEAM query category (spec section 2), including the Gherkin
"Get team statistics" scenario and the worked "Corinthians home record (2022)"
example from the specification.
==============================================================================
"""

from brazilian_soccer import queries as q


class TestTeamRecord:
    def test_team_statistics_have_all_fields(self, graph):
        # Given the match data is loaded
        # When I request statistics for Palmeiras in season 2019
        r = q.team_record(graph, "Palmeiras", season=2019, competition="Brasileirão")
        # Then I receive wins, losses, draws and goals
        for field in ("wins", "losses", "draws", "goals_for", "goals_against"):
            assert field in r
        assert r["played"] == r["wins"] + r["draws"] + r["losses"]

    def test_corinthians_home_record_2022_matches_spec_shape(self, graph):
        # Given the data / When I compute Corinthians' 2022 home Brasileirão record
        r = q.team_record(
            graph, "Corinthians", season=2022,
            competition="Brasileirão", venue="home",
        )
        # Then a home campaign is reported. NOTE: the provided 2022 dataset is a
        # mid-season snapshot -- 4 of Corinthians' 19 home fixtures have no score
        # yet, so only the 15 *completed* home matches are counted.
        assert r["played"] == 15
        assert 0 <= r["win_rate"] <= 100
        assert r["wins"] + r["draws"] + r["losses"] == r["played"]
        assert "Win rate" in r["summary"]

    def test_points_calculation(self, graph):
        # Given a record / Then points == 3*wins + draws
        r = q.team_record(graph, "Flamengo", season=2019, competition="Brasileirão")
        assert r["points"] == r["wins"] * 3 + r["draws"]

    def test_venue_split_sums_to_overall(self, graph):
        # Given home and away splits / Then they sum to the overall record
        overall = q.team_record(graph, "Santos", season=2019, competition="Brasileirão")
        home = q.team_record(graph, "Santos", season=2019,
                             competition="Brasileirão", venue="home")
        away = q.team_record(graph, "Santos", season=2019,
                             competition="Brasileirão", venue="away")
        assert overall["played"] == home["played"] + away["played"]
        assert overall["wins"] == home["wins"] + away["wins"]


class TestCompareTeams:
    def test_compare_returns_both_records_and_h2h(self, graph):
        # Given the data / When comparing Palmeiras and Santos
        c = q.compare_teams(graph, "Palmeiras", "Santos")
        # Then I get both teams' records and a head-to-head block
        assert c["team_a"]["team"]
        assert c["team_b"]["team"]
        assert "total_matches" in c["head_to_head"]
