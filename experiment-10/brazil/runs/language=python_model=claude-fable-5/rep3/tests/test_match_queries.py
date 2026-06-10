"""Feature: Match Queries.

Scenario (from the spec): Find matches between two teams
  Given the match data is loaded
  When I search for matches between "Flamengo" and "Fluminense"
  Then I should receive a list of matches
  And each match should have date, scores, and competition
"""

from datetime import date

import queries
from models import COPA_DO_BRASIL, SERIE_A


class TestFindMatchesBetweenTwoTeams:
    def test_fla_flu_derby_returns_matches(self, db):
        # When I search for matches between "Flamengo" and "Fluminense"
        matches = queries.filter_matches(db, team="Flamengo",
                                         opponent="Fluminense")
        # Then I should receive a list of matches
        assert len(matches) >= 40
        # And each match should have date, scores, and competition
        for match in matches:
            assert match.date is not None
            assert match.competition
            assert {match.home_key.base, match.away_key.base} == {
                "flamengo", "fluminense"}

    def test_results_are_sorted_newest_first(self, db):
        matches = queries.filter_matches(db, team="Flamengo",
                                         opponent="Fluminense")
        dates = [m.date for m in matches]
        assert dates == sorted(dates, reverse=True)


class TestFilterByTeamSeasonCompetition:
    def test_palmeiras_2023_spans_competitions(self, db):
        matches = queries.filter_matches(db, team="Palmeiras", season=2023)
        assert len(matches) >= 30
        competitions = {m.competition for m in matches}
        assert SERIE_A in competitions
        assert COPA_DO_BRASIL in competitions

    def test_competition_filter_is_fuzzy(self, db):
        for alias in ("Brasileirão", "Serie A", "brasileirao serie a"):
            matches = queries.filter_matches(db, team="Palmeiras",
                                             season=2023, competition=alias)
            assert matches
            assert all(m.competition == SERIE_A for m in matches)

    def test_date_range_filter(self, db):
        matches = queries.filter_matches(
            db, team="Flamengo", date_from="2019-01-01",
            date_to="2019-12-31")
        assert matches
        for match in matches:
            assert date(2019, 1, 1) <= match.date <= date(2019, 12, 31)

    def test_copa_do_brasil_finals_exist(self, db):
        finals = [m for m in queries.filter_matches(
            db, competition="copa do brasil") if m.stage == "Final"]
        # Seven seasons (2013-2015, 2017-2020) have complete brackets with
        # two-legged finals.
        assert len(finals) == 14
        seasons = {m.season for m in finals}
        assert {2013, 2019, 2020} <= seasons

    def test_unknown_team_returns_empty(self, db):
        assert queries.filter_matches(db, team="Real Madrid CF XYZ") == []


class TestCrossFileDeduplication:
    """Scenario: the same real-world match appears in multiple CSVs but is
    reported only once."""

    def test_corinthians_2022_home_league_games(self, db):
        stats = queries.team_statistics(db, "Corinthians", season=2022,
                                        competition="brasileirao",
                                        venue="home")
        # A Série A season has exactly 19 home games per team.
        assert stats["played"] == 19

    def test_no_duplicate_fingerprints_in_team_search(self, db):
        matches = queries.filter_matches(db, team="Flamengo", season=2022,
                                         competition="serie a")
        fingerprints = {(m.home_key.base, m.away_key.base, m.round)
                        for m in matches}
        assert len(fingerprints) == len(matches)
