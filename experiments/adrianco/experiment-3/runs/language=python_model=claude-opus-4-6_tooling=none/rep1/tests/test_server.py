import json
import pytest
from server import (
    search_matches,
    get_team_statistics,
    get_head_to_head,
    search_players,
    get_competition_standings,
    get_match_statistics,
)


class TestMCPTools:
    def test_search_matches_returns_string(self):
        result = search_matches(team="Palmeiras", limit=5)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "No results" not in result

    def test_search_matches_head_to_head(self):
        result = search_matches(team="Flamengo", opponent="Fluminense", limit=5)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_matches_by_competition(self):
        result = search_matches(competition="Copa do Brasil", limit=5)
        assert "Copa do Brasil" in result

    def test_get_team_statistics(self):
        result = get_team_statistics(team="Palmeiras", season=2019)
        parsed = json.loads(result)
        assert parsed["matches"] > 0
        assert "wins" in parsed
        assert "goals_for" in parsed

    def test_get_head_to_head(self):
        result = get_head_to_head(team1="Palmeiras", team2="Santos")
        parsed = json.loads(result)
        assert parsed["total_matches"] > 0

    def test_search_players(self):
        result = search_players(name="Neymar")
        assert "Neymar" in result

    def test_search_players_by_nationality(self):
        result = search_players(nationality="Brazil", limit=5)
        assert len(result) > 0
        assert "No results" not in result

    def test_get_competition_standings(self):
        result = get_competition_standings(competition="Brasileirao", season=2019)
        assert "points" in result
        assert "wins" in result

    def test_get_match_statistics(self):
        result = get_match_statistics()
        parsed = json.loads(result)
        assert parsed["total_matches"] > 0
        assert parsed["avg_goals_per_match"] > 0

    def test_get_match_statistics_by_team(self):
        result = get_match_statistics(team="Flamengo")
        parsed = json.loads(result)
        assert parsed["total_matches"] > 0
