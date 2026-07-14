"""
================================================================================
BDD Feature: Match Queries
================================================================================

CONTEXT
-------
Covers specification capability #1: finding matches by team, opponent,
competition, season and date range, plus most-recent-match and head-to-head
records. Exact assertions use the deterministic ``synthetic_kg`` fixture;
integration checks use the real ``kg``.
================================================================================
"""

import time

from brazilian_soccer_mcp.normalize import COMP_BRASILEIRAO


class TestFindMatches:
    """Feature: Find matches between two teams."""

    def test_find_matches_between_two_teams(self, synthetic_kg):
        # Given the match data is loaded
        # When I search for matches between Flamengo and Palmeiras
        matches = synthetic_kg.find_matches(team="Flamengo", opponent="Palmeiras")
        # Then I receive the two head-to-head fixtures
        assert len(matches) == 2
        # And each match has date, scores and competition
        for m in matches:
            assert m.date is not None
            assert m.has_score
            assert m.competition

    def test_find_matches_by_season(self, synthetic_kg):
        # When I filter by season 2023
        matches = synthetic_kg.find_matches(team="Flamengo", season=2023)
        # Then only 2023 fixtures are returned
        assert matches
        assert all(m.season == 2023 for m in matches)

    def test_find_matches_by_competition_alias(self, synthetic_kg):
        # When I filter Flamengo matches by the alias "Serie A"
        matches = synthetic_kg.find_matches(team="Flamengo", competition="Serie A")
        # Then only Brasileirão fixtures come back (not the cup match)
        assert matches
        assert all(m.competition == COMP_BRASILEIRAO for m in matches)

    def test_find_matches_by_date_range(self, synthetic_kg):
        # When I restrict to the first half of 2023
        matches = synthetic_kg.find_matches(
            team="Flamengo", start_date="2023-01-01", end_date="2023-06-30"
        )
        # Then only fixtures inside the window are returned
        assert matches
        assert all("2023-01-01" <= m.date <= "2023-06-30" for m in matches)

    def test_results_sorted_by_date(self, synthetic_kg):
        matches = synthetic_kg.find_matches(team="Flamengo", season=2023)
        dates = [m.date for m in matches if m.date]
        assert dates == sorted(dates)

    def test_team_name_variation_matches(self, synthetic_kg):
        # Given the dataset stores "Flamengo-RJ"
        # When I query with the bare name "flamengo"
        with_suffix = synthetic_kg.find_matches(team="Flamengo-RJ", season=2023)
        bare = synthetic_kg.find_matches(team="flamengo", season=2023)
        # Then both queries return the same fixtures
        assert len(with_suffix) == len(bare) == 4


class TestLastMatch:
    """Feature: Most recent match between teams."""

    def test_last_match_between_two_teams(self, synthetic_kg):
        # When I ask when Flamengo last played Palmeiras
        m = synthetic_kg.last_match("Flamengo", opponent="Palmeiras")
        # Then I get the most recent fixture
        assert m is not None
        assert m.date == "2023-09-01"


class TestHeadToHead:
    """Feature: Head-to-head record."""

    def test_head_to_head_counts(self, synthetic_kg):
        # When I request Flamengo vs Palmeiras head-to-head
        h2h = synthetic_kg.head_to_head("Flamengo", "Palmeiras")
        # Then wins/draws are tallied correctly (Fla 1 win, 1 draw)
        assert h2h["total"] == 2
        assert h2h["team_a_wins"] == 1
        assert h2h["team_b_wins"] == 0
        assert h2h["draws"] == 1
        # And goals are aggregated per side
        assert h2h["team_a_goals"] == 3  # 2 + 1
        assert h2h["team_b_goals"] == 1  # 0 + 1


class TestRealMatchQueries:
    """Feature: Match queries against the real dataset."""

    def test_real_team_has_matches(self, kg):
        # Given the real data, Flamengo should have many matches
        matches = kg.find_matches(team="Flamengo")
        assert len(matches) > 50

    def test_real_lookup_is_fast(self, kg):
        # Then a simple lookup responds in well under 2 seconds
        start = time.time()
        kg.find_matches(team="Palmeiras", competition="Serie A")
        assert time.time() - start < 2.0

    def test_real_head_to_head_consistency(self, kg):
        # Then totals add up: wins + losses + draws == matches with a score
        h2h = kg.head_to_head("Flamengo", "Fluminense")
        scored = sum(1 for m in h2h["matches"] if m.has_score)
        assert (h2h["team_a_wins"] + h2h["team_b_wins"]
                + h2h["draws"]) == scored
