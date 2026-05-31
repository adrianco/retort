"""BDD: team queries.

Feature: Team Queries
  As an LLM
  I want win/loss records and head-to-head comparisons
  So that I can answer "What is Corinthians' home record in 2022?"
"""

from __future__ import annotations

from brazilian_soccer_mcp import queries as q
from brazilian_soccer_mcp.data_loader import DataStore


class TestTeamRecord:
    """Scenario: compute Corinthians' home record in the 2022 Brasileirão."""

    def test_corinthians_2022_home(self, store: DataStore) -> None:
        # When I ask for the home record
        record = q.team_record(
            store,
            "Corinthians",
            competition="Serie A",
            season=2022,
            venue="home",
        )
        # Then the totals are self-consistent
        assert record["matches"] == record["wins"] + record["draws"] + record["losses"]
        assert record["matches"] >= 17  # 19 home games in real season
        assert record["matches"] <= 22  # allow slack for dedup edge cases
        assert record["points"] == record["wins"] * 3 + record["draws"]
        # And it's actually Corinthians
        assert record["team"] == "Corinthians"

    def test_overall_vs_split_consistency(self, store: DataStore) -> None:
        # Given Palmeiras' full 2022 record
        full = q.team_record(store, "Palmeiras", competition="Serie A", season=2022)
        # And separate home/away breakdowns
        home = q.team_record(
            store, "Palmeiras", competition="Serie A", season=2022, venue="home"
        )
        away = q.team_record(
            store, "Palmeiras", competition="Serie A", season=2022, venue="away"
        )
        # When we sum the split records
        # Then they match the unsplit total
        assert full["matches"] == home["matches"] + away["matches"]
        assert full["wins"] == home["wins"] + away["wins"]
        assert full["draws"] == home["draws"] + away["draws"]
        assert full["losses"] == home["losses"] + away["losses"]


class TestTopScoringTeams:
    """Scenario: rank clubs by goals scored in a given season."""

    def test_top_scorer_serie_a_2019(self, store: DataStore) -> None:
        result = q.top_scoring_teams(store, competition="Serie A", season=2019, limit=5)
        # The 2019 Brasileirão was famously dominated by Flamengo (86 goals);
        # they should be at or very near the top.
        names = [t["team"] for t in result["teams"]]
        assert "Flamengo" in names[:3]


class TestCompareTeams:
    """Scenario: side-by-side comparison of two clubs."""

    def test_palmeiras_vs_santos(self, store: DataStore) -> None:
        result = q.compare_teams(store, "Palmeiras", "Santos")
        assert result["team_a"]["team"] == "Palmeiras"
        assert result["team_b"]["team"] == "Santos"
        h2h = result["head_to_head"]
        assert h2h["matches"] > 0
        assert h2h["team_a"] == "Palmeiras"
