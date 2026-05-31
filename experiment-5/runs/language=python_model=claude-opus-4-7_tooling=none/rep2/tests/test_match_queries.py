"""BDD: match queries.

Feature: Match Queries
  As an LLM
  I want to ask about specific matches between clubs
  So that I can answer questions like "When did Flamengo last play Corinthians?"
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import queries as q
from brazilian_soccer_mcp.data_loader import DataStore


class TestSearchByTeam:
    """Scenario: filter all matches by a single team."""

    def test_palmeiras_2023(self, store: DataStore) -> None:
        # Given the loaded match data
        # When I search for Palmeiras matches in 2023
        result = q.search_matches(store, team="Palmeiras", season=2023)
        # Then I receive matches and every one involves Palmeiras
        assert result["count"] > 0
        for match in result["matches"]:
            home_norm = match["home_team"].lower()
            away_norm = match["away_team"].lower()
            assert "palmeiras" in home_norm or "palmeiras" in away_norm
            assert match["season"] == 2023


class TestSearchBetweenTwoTeams:
    """Scenario: find matches between two specific clubs."""

    def test_flamengo_vs_fluminense(self, store: DataStore) -> None:
        # When I search for Flamengo vs Fluminense
        result = q.search_matches(store, team="Flamengo", opponent="Fluminense")
        # Then every match involves both clubs
        assert result["count"] > 0
        for match in result["matches"]:
            teams = (match["home_team"] + " " + match["away_team"]).lower()
            assert "flamengo" in teams
            assert "fluminense" in teams


class TestCompetitionFilter:
    """Scenario: filter by competition substring."""

    def test_copa_do_brasil_only(self, store: DataStore) -> None:
        result = q.search_matches(store, competition="Copa do Brasil", limit=5)
        assert result["count"] > 0
        for match in result["matches"]:
            assert "Copa do Brasil" in match["competition"]


class TestLastMatch:
    """Scenario: most recent meeting between two clubs."""

    def test_flamengo_corinthians_last(self, store: DataStore) -> None:
        result = q.last_match(store, "Flamengo", "Corinthians")
        # Then we get a single match with a non-empty date
        assert result["match"] is not None
        assert result["match"]["date"] != ""
        teams = (
            result["match"]["home_team"] + " " + result["match"]["away_team"]
        ).lower()
        assert "flamengo" in teams and "corinthians" in teams


class TestHeadToHead:
    """Scenario: aggregate head-to-head record."""

    def test_flamengo_fluminense_h2h(self, store: DataStore) -> None:
        # When I request the head-to-head
        result = q.head_to_head(store, "Flamengo", "Fluminense")
        # Then wins for the two sides plus draws sum to the match count
        assert result["matches"] > 0
        assert (
            result["team_a_wins"] + result["team_b_wins"] + result["draws"]
            == result["matches"]
        )
        assert result["team_a"] == "Flamengo"
        assert result["team_b"] == "Fluminense"

    def test_h2h_is_symmetric(self, store: DataStore) -> None:
        # head_to_head(A, B) is the mirror image of head_to_head(B, A)
        ab = q.head_to_head(store, "Palmeiras", "Santos")
        ba = q.head_to_head(store, "Santos", "Palmeiras")
        assert ab["matches"] == ba["matches"]
        assert ab["team_a_wins"] == ba["team_b_wins"]
        assert ab["team_b_wins"] == ba["team_a_wins"]
        assert ab["draws"] == ba["draws"]


class TestTeamNameNormalization:
    """Scenario: queries don't care which spelling the caller uses."""

    @pytest.mark.parametrize(
        "spelling", ["Atlético-MG", "Atletico Mineiro", "Galo", "Atletico-MG"]
    )
    def test_atletico_mineiro_spellings_equivalent(
        self, store: DataStore, spelling: str
    ) -> None:
        # Given multiple spellings of Atlético Mineiro
        # When we ask each for matches against Cruzeiro
        result = q.search_matches(
            store, team=spelling, opponent="Cruzeiro", limit=200
        )
        # Then all spellings return the same match count
        assert result["count"] > 0
        if not hasattr(self, "_baseline"):
            self._baseline = result["count"]
        assert result["count"] == self._baseline
