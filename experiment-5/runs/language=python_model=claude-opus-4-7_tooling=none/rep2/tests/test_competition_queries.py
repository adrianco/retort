"""BDD: competition queries.

Feature: Competition Queries
  As an LLM
  I want season standings reconstructed from match results
  So that I can answer "Who won the 2019 Brasileirão?"
"""

from __future__ import annotations

from brazilian_soccer_mcp import queries as q
from brazilian_soccer_mcp.data_loader import DataStore


class TestSeasonStandings:
    """Scenario: rebuild league standings from match data."""

    def test_2019_brasileirao_champion(self, store: DataStore) -> None:
        # Given the 2019 Brasileirão Serie A
        result = q.season_standings(store, 2019)
        # When I read the top of the table
        # Then Flamengo are champions with ~90 points (real value: 90)
        assert result["champion"] == "Flamengo"
        top = result["standings"][0]
        assert top["team"] == "Flamengo"
        assert 85 <= top["points"] <= 95
        assert top["wins"] >= 25
        # And the table is sorted by points descending
        points = [team["points"] for team in result["standings"]]
        assert points == sorted(points, reverse=True)

    def test_standings_are_internally_consistent(self, store: DataStore) -> None:
        result = q.season_standings(store, 2020)
        for row in result["standings"]:
            # matches = W + D + L
            assert row["matches"] == row["wins"] + row["draws"] + row["losses"]
            # points = 3*W + D
            assert row["points"] == row["wins"] * 3 + row["draws"]
            # goal_difference = goals_for - goals_against
            assert row["goal_difference"] == row["goals_for"] - row["goals_against"]


class TestListCompetitions:
    """Scenario: enumerate available competitions."""

    def test_brasileirao_and_cup_present(self, store: DataStore) -> None:
        result = q.list_competitions(store)
        names = {c["name"] for c in result["competitions"]}
        assert "Brasileirão Serie A" in names
        assert "Copa do Brasil" in names
        assert "Copa Libertadores" in names
        for entry in result["competitions"]:
            assert entry["match_count"] > 0


class TestListSeasons:
    """Scenario: list seasons, optionally per competition."""

    def test_brasileirao_seasons_cover_modern_era(self, store: DataStore) -> None:
        result = q.list_seasons(store, competition="Serie A")
        seasons = result["seasons"]
        # The spec's CSVs cover 2003 onwards through 2023.
        assert min(seasons) <= 2010
        assert max(seasons) >= 2022
