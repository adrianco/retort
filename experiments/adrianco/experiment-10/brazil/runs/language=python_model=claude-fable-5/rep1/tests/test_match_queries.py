"""Feature: Match queries

Scenario: Find matches between two teams
  Given the match data is loaded
  When I search for matches between "Flamengo" and "Fluminense"
  Then I should receive a list of matches
  And each match should have date, scores, and competition
"""

import pytest

import queries


class TestFindMatchesBetweenTwoTeams:
    @pytest.fixture(scope="class")
    def result(self, db):
        # When I search for matches between Flamengo and Fluminense
        return queries.head_to_head("Flamengo", "Fluminense")

    def test_returns_a_list_of_matches(self, result):
        assert result["total_matches"] > 0
        assert len(result["matches"]) == result["total_matches"]

    def test_each_match_has_date_scores_and_competition(self, result):
        for match in result["matches"]:
            assert match["date"]
            assert match["competition"]
            assert match["score"] is None or "-" in match["score"]

    def test_head_to_head_record_adds_up(self, result):
        record = result["record"]
        scored = [m for m in result["matches"] if m["score"]]
        assert (record["Flamengo_wins"] + record["Fluminense_wins"]
                + record["draws"]) == len(scored)

    def test_summary_is_formatted(self, result):
        assert result["summary"].startswith("Head-to-head in dataset:")


class TestSearchFilters:
    def test_search_by_team_and_season(self, db):
        # "What matches did Palmeiras play in 2023?"
        result = queries.search_matches(team="Palmeiras", season=2023)
        assert result["total_matches"] > 0
        for m in result["matches"]:
            assert m["season"] == 2023
            assert "Palmeiras" in m["home_team"] or "Palmeiras" in m["away_team"]

    def test_search_by_competition(self, db):
        result = queries.search_matches(team="Flamengo",
                                        competition="libertadores", limit=10)
        for m in result["matches"]:
            assert m["competition"] == "Copa Libertadores"

    def test_search_by_date_range(self, db):
        result = queries.search_matches(team="Santos", date_from="2015-01-01",
                                        date_to="2015-12-31")
        assert result["total_matches"] > 0
        for m in result["matches"]:
            assert m["date"].startswith("2015")

    def test_results_are_most_recent_first(self, db):
        result = queries.search_matches(team="Corinthians", limit=20)
        dates = [m["date"] for m in result["matches"] if m["date"]]
        assert dates == sorted(dates, reverse=True)

    def test_competition_name_aliases_work(self, db):
        a = queries.search_matches(team="Grêmio", competition="Brasileirão")
        b = queries.search_matches(team="Gremio", competition="serie-a")
        assert a["total_matches"] == b["total_matches"]

    def test_unknown_team_raises_helpful_error(self, db):
        with pytest.raises(queries.TeamNotFoundError):
            queries.search_matches(team="Real Madrid CF Basket")

    def test_limit_is_respected(self, db):
        result = queries.search_matches(team="Flamengo", limit=5)
        assert len(result["matches"]) <= 5
        assert result["showing"] <= 5
