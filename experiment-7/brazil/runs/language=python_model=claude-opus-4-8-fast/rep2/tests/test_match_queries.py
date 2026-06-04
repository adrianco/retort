"""
================================================================================
Module: tests.test_match_queries
--------------------------------------------------------------------------------
Context:
    BDD scenarios for the "Match Queries" feature (TASK.md §1) — searching
    matches by team, opponent, competition, season and date range, plus
    head-to-head records.

Responsibility:
    Exercise KnowledgeGraph.find_matches / head_to_head against the real
    datasets and assert structural + logical correctness.
================================================================================
"""

from brazilian_soccer_mcp.normalize import names_match


class TestFindMatchesBetweenTeams:
    def test_find_flamengo_vs_fluminense(self, graph):
        # WHEN I search for matches between Flamengo and Fluminense
        matches = graph.find_matches(team="Flamengo", opponent="Fluminense")
        # THEN I receive a non-empty list
        assert matches, "expected Fla-Flu matches in the dataset"
        # AND every match is between the two clubs with date + scores + competition
        for m in matches:
            teams = {m.home_team, m.away_team}
            assert any(names_match("Flamengo", t) for t in teams)
            assert any(names_match("Fluminense", t) for t in teams)
            assert m.competition
            assert m.match_date is not None

    def test_results_sorted_most_recent_first(self, graph):
        matches = graph.find_matches(team="Flamengo", opponent="Fluminense")
        dates = [m.match_date for m in matches if m.match_date]
        assert dates == sorted(dates, reverse=True)


class TestFindMatchesByCriteria:
    def test_team_and_season_filter(self, graph):
        # WHEN I search Palmeiras matches in 2019
        matches = graph.find_matches(team="Palmeiras", season=2019)
        assert matches
        # THEN every match involves Palmeiras and is in 2019
        for m in matches:
            assert m.season == 2019
            assert names_match("Palmeiras", m.home_team) or names_match(
                "Palmeiras", m.away_team
            )

    def test_competition_filter(self, graph):
        matches = graph.find_matches(team="Flamengo", competition="Libertadores")
        assert matches
        assert all(m.competition == "Copa Libertadores" for m in matches)

    def test_home_venue_filter(self, graph):
        matches = graph.find_matches(team="Corinthians", venue="home", season=2022,
                                     competition="Brasileirão")
        assert matches
        assert all(names_match("Corinthians", m.home_team) for m in matches)

    def test_date_range_filter(self, graph):
        matches = graph.find_matches(
            team="Flamengo", start_date="2019-01-01", end_date="2019-12-31"
        )
        assert matches
        assert all(m.match_date.year == 2019 for m in matches)

    def test_limit_is_respected(self, graph):
        matches = graph.find_matches(team="Flamengo", limit=5)
        assert len(matches) == 5

    def test_unknown_team_returns_empty(self, graph):
        assert graph.find_matches(team="Nonexistent United FC") == []


class TestHeadToHead:
    def test_head_to_head_totals_are_consistent(self, graph):
        # WHEN I request the Fla-Flu head-to-head
        h = graph.head_to_head("Flamengo", "Fluminense")
        # THEN wins + draws account for every played match
        assert h["total"] > 0
        assert h["team1_wins"] + h["team2_wins"] + h["draws"] == h["total"]
        assert h["team1_goals"] >= 0 and h["team2_goals"] >= 0

    def test_head_to_head_symmetry(self, graph):
        a = graph.head_to_head("Flamengo", "Fluminense")
        b = graph.head_to_head("Fluminense", "Flamengo")
        # Totals are symmetric; team1/team2 wins swap.
        assert a["total"] == b["total"]
        assert a["team1_wins"] == b["team2_wins"]
        assert a["draws"] == b["draws"]
