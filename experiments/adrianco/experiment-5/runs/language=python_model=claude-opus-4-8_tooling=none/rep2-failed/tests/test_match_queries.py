"""
Context
=======
Feature: Match Queries  (TASK.md section 1)

Scenario: Find matches between two teams
Scenario: Find matches by season / competition
Scenario: Head-to-head record between two teams
"""

from __future__ import annotations


class TestFindMatchesBetweenTeams:
    def test_flamengo_vs_fluminense_returns_matches_with_detail(self, graph):
        # WHEN I search for matches between Flamengo and Fluminense
        matches = graph.find_matches(team="Flamengo", opponent="Fluminense")
        # THEN I receive a non-empty list
        assert matches, "expected Fla-Flu matches"
        # AND each match has the two teams, a competition and (mostly) a date
        for m in matches:
            assert m.involves(graph.resolve_team("Flamengo"))
            assert m.involves(graph.resolve_team("Fluminense"))
            assert m.competition
        assert any(m.has_score for m in matches)

    def test_matches_are_sorted_newest_first(self, graph):
        matches = graph.find_matches(team="Flamengo", opponent="Fluminense")
        dated = [m.match_date for m in matches if m.match_date]
        assert dated == sorted(dated, reverse=True)


class TestFindMatchesByCriteria:
    def test_palmeiras_matches_in_a_season(self, graph):
        # WHEN I ask what matches Palmeiras played in 2019
        matches = graph.find_matches(team="Palmeiras", season=2019)
        # THEN every returned match is in 2019 and involves Palmeiras
        pal = graph.resolve_team("Palmeiras")
        assert matches
        assert all(m.season == 2019 and m.involves(pal) for m in matches)

    def test_filter_by_competition(self, graph):
        # WHEN I restrict to the Copa do Brasil
        matches = graph.find_matches(team="Flamengo", competition="Copa do Brasil")
        assert matches
        assert all("Copa do Brasil" in m.competition for m in matches)

    def test_home_venue_filter(self, graph):
        # WHEN I ask for Corinthians home matches only
        corinthians = graph.resolve_team("Corinthians")
        matches = graph.find_matches(team="Corinthians", venue="home", season=2019,
                                     competition="Brasileirão")
        assert matches
        assert all(m.home_id == corinthians for m in matches)

    def test_date_range_filter(self, graph):
        # WHEN I bound the search to a date range
        matches = graph.find_matches(
            team="Flamengo", date_from="2019-01-01", date_to="2019-12-31",
        )
        assert matches
        assert all(m.match_date and m.match_date.year == 2019 for m in matches)


class TestHeadToHead:
    def test_head_to_head_totals_are_consistent(self, graph):
        # WHEN I request the Palmeiras vs Santos head-to-head
        h2h = graph.head_to_head("Palmeiras", "Santos")
        assert h2h is not None
        # THEN wins + draws reconcile with the scored matches counted
        scored = sum(1 for m in h2h["matches"] if m.has_score)
        assert h2h["team1_wins"] + h2h["team2_wins"] + h2h["draws"] == scored
        assert h2h["total_matches"] >= scored

    def test_unknown_team_returns_none(self, graph):
        assert graph.head_to_head("Flamengo", "Not A Real Team XYZ") is None
