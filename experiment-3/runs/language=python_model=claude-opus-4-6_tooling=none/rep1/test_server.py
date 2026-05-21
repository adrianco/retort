"""BDD-style tests for Brazilian Soccer MCP Server."""

import json
import pytest
from data_loader import BrazilianSoccerData, _normalize_team_name


@pytest.fixture(scope="module")
def data():
    return BrazilianSoccerData()


# ---------------------------------------------------------------------------
# Feature: Data Loading
# ---------------------------------------------------------------------------

class TestDataLoading:
    """Scenario: All 6 CSV files are loadable and queryable."""

    def test_brasileirao_loaded(self, data):
        assert len(data.brasileirao) > 0, "Brasileirao data should be loaded"

    def test_copa_do_brasil_loaded(self, data):
        assert len(data.copa_do_brasil) > 0, "Copa do Brasil data should be loaded"

    def test_libertadores_loaded(self, data):
        assert len(data.libertadores) > 0, "Libertadores data should be loaded"

    def test_extended_stats_loaded(self, data):
        assert len(data.extended_stats) > 0, "Extended stats should be loaded"

    def test_historical_loaded(self, data):
        assert len(data.historical) > 0, "Historical data should be loaded"

    def test_fifa_players_loaded(self, data):
        assert len(data.players) > 0, "FIFA player data should be loaded"


# ---------------------------------------------------------------------------
# Feature: Team Name Normalization
# ---------------------------------------------------------------------------

class TestTeamNameNormalization:
    """Scenario: Team names are normalized consistently."""

    def test_strip_state_suffix(self):
        assert _normalize_team_name("Palmeiras-SP") == "Palmeiras"

    def test_strip_rj_suffix(self):
        assert _normalize_team_name("Flamengo-RJ") == "Flamengo"

    def test_no_suffix(self):
        assert _normalize_team_name("Flamengo") == "Flamengo"

    def test_accent_normalization(self):
        assert _normalize_team_name("Grêmio") == "Gremio"

    def test_sao_paulo_accent(self):
        assert _normalize_team_name("São Paulo") == "Sao Paulo"

    def test_athletico_alias(self):
        assert _normalize_team_name("Athletico-PR") == "Athletico"
        assert _normalize_team_name("Atletico-PR") == "Athletico"


# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------

class TestMatchQueries:
    """Scenario: Find matches between two teams."""

    def test_search_by_single_team(self, data):
        """Given the match data is loaded,
        When I search for matches for 'Flamengo',
        Then I should receive a list of matches."""
        results = data.search_matches(team="Flamengo")
        assert len(results) > 0
        for m in results:
            team_found = (
                "Flamengo" in m["home_team"] or "Flamengo" in m["away_team"]
            )
            assert team_found, f"Match should involve Flamengo: {m}"

    def test_search_head_to_head(self, data):
        """Given the match data is loaded,
        When I search for matches between 'Flamengo' and 'Fluminense',
        Then I should receive matches involving both teams."""
        results = data.search_matches(team="Flamengo", team2="Fluminense")
        assert len(results) > 0
        for m in results:
            teams = {m["home_team"], m["away_team"]}
            norms = {_normalize_team_name(t).lower() for t in teams}
            assert "flamengo" in norms or any("flamengo" in n for n in norms)

    def test_match_has_required_fields(self, data):
        """Each match should have date, scores, and competition."""
        results = data.search_matches(team="Palmeiras", limit=5)
        assert len(results) > 0
        for m in results:
            assert "date" in m
            assert "home_team" in m
            assert "away_team" in m
            assert "home_goal" in m
            assert "away_goal" in m
            assert "competition" in m

    def test_search_by_competition(self, data):
        results = data.search_matches(competition="Libertadores", limit=10)
        assert len(results) > 0
        for m in results:
            assert "Libertadores" in m["competition"]

    def test_search_by_season(self, data):
        results = data.search_matches(team="Palmeiras", season=2019, limit=10)
        assert len(results) > 0

    def test_search_by_date_range(self, data):
        results = data.search_matches(
            date_from="2019-01-01", date_to="2019-12-31", limit=10
        )
        assert len(results) > 0
        for m in results:
            assert m["date"].startswith("2019")


# ---------------------------------------------------------------------------
# Feature: Team Statistics
# ---------------------------------------------------------------------------

class TestTeamStatistics:
    """Scenario: Get team statistics."""

    def test_basic_stats(self, data):
        """Given the match data is loaded,
        When I request statistics for 'Palmeiras',
        Then I should receive wins, losses, draws, and goals."""
        stats = data.team_statistics(team="Palmeiras")
        assert stats["matches"] > 0
        assert "wins" in stats
        assert "draws" in stats
        assert "losses" in stats
        assert "goals_for" in stats
        assert "goals_against" in stats
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]

    def test_stats_by_season(self, data):
        """When I request statistics for 'Palmeiras' in season 2019."""
        stats = data.team_statistics(team="Palmeiras", season=2019)
        assert stats["matches"] > 0

    def test_home_only_stats(self, data):
        stats = data.team_statistics(team="Corinthians", home_only=True)
        assert stats["matches"] > 0

    def test_away_only_stats(self, data):
        stats = data.team_statistics(team="Corinthians", away_only=True)
        assert stats["matches"] > 0

    def test_points_calculation(self, data):
        stats = data.team_statistics(team="Flamengo")
        assert stats["points"] == stats["wins"] * 3 + stats["draws"]

    def test_win_rate(self, data):
        stats = data.team_statistics(team="Flamengo")
        expected = round(stats["wins"] / stats["matches"] * 100, 1)
        assert stats["win_rate"] == expected


# ---------------------------------------------------------------------------
# Feature: Head to Head
# ---------------------------------------------------------------------------

class TestHeadToHead:
    def test_head_to_head(self, data):
        result = data.head_to_head("Flamengo", "Fluminense")
        assert result["total_matches"] > 0
        assert result["Flamengo_wins"] >= 0
        assert result["Fluminense_wins"] >= 0
        assert result["draws"] >= 0
        total = result["Flamengo_wins"] + result["Fluminense_wins"] + result["draws"]
        assert total == result["total_matches"]

    def test_head_to_head_has_recent_matches(self, data):
        result = data.head_to_head("Palmeiras", "Santos")
        assert "recent_matches" in result
        assert len(result["recent_matches"]) > 0


# ---------------------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------------------

class TestPlayerQueries:
    def test_search_by_name(self, data):
        results = data.search_players(name="Neymar")
        assert len(results) > 0
        assert any("Neymar" in p["name"] for p in results)

    def test_search_brazilian_players(self, data):
        results = data.search_players(nationality="Brazil", limit=10)
        assert len(results) > 0
        for p in results:
            assert p["nationality"] == "Brazil"

    def test_search_by_club(self, data):
        results = data.search_players(club="Santos")
        assert len(results) > 0

    def test_search_by_position(self, data):
        results = data.search_players(position="ST", nationality="Brazil", limit=10)
        assert len(results) > 0
        for p in results:
            assert "ST" in p["position"]

    def test_search_by_min_overall(self, data):
        results = data.search_players(min_overall=85, limit=10)
        assert len(results) > 0
        for p in results:
            assert p["overall"] >= 85

    def test_player_has_required_fields(self, data):
        results = data.search_players(name="Messi", limit=1)
        assert len(results) > 0
        p = results[0]
        assert "name" in p
        assert "nationality" in p
        assert "overall" in p
        assert "club" in p
        assert "position" in p


# ---------------------------------------------------------------------------
# Feature: Competition Standings
# ---------------------------------------------------------------------------

class TestCompetitionStandings:
    def test_brasileirao_standings(self, data):
        standings = data.competition_standings("Brasileirao", 2019)
        assert len(standings) > 0
        assert standings[0]["position"] == 1
        assert standings[0]["points"] >= standings[1]["points"]

    def test_standings_have_required_fields(self, data):
        standings = data.competition_standings("Brasileirao", 2018)
        assert len(standings) > 0
        for s in standings:
            assert "team" in s
            assert "played" in s
            assert "wins" in s
            assert "draws" in s
            assert "losses" in s
            assert "points" in s
            assert "goals_for" in s
            assert "goals_against" in s

    def test_standings_consistency(self, data):
        standings = data.competition_standings("Brasileirao", 2017)
        for s in standings:
            assert s["wins"] + s["draws"] + s["losses"] == s["played"]
            assert s["points"] == s["wins"] * 3 + s["draws"]


# ---------------------------------------------------------------------------
# Feature: Statistical Analysis
# ---------------------------------------------------------------------------

class TestStatisticalAnalysis:
    def test_overall_summary(self, data):
        stats = data.statistical_summary()
        assert stats["total_matches"] > 0
        assert stats["avg_goals_per_match"] > 0
        assert stats["home_win_pct"] + stats["away_win_pct"] + stats["draw_pct"] == pytest.approx(100.0, abs=0.5)

    def test_summary_by_competition(self, data):
        stats = data.statistical_summary(competition="Brasileirao")
        assert stats["total_matches"] > 0

    def test_summary_by_season(self, data):
        stats = data.statistical_summary(competition="Brasileirao", season=2019)
        assert stats["total_matches"] > 0

    def test_biggest_win(self, data):
        stats = data.statistical_summary()
        bw = stats["biggest_win"]
        assert abs(bw["home_goal"] - bw["away_goal"]) > 0


# ---------------------------------------------------------------------------
# Feature: MCP Server Tools
# ---------------------------------------------------------------------------

class TestMCPServerTools:
    """Verify that MCP tools return valid JSON strings."""

    def test_search_matches_tool(self):
        from server import search_matches
        result = search_matches(team="Flamengo", limit=5)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_team_statistics_tool(self):
        from server import team_statistics
        result = team_statistics(team="Palmeiras")
        parsed = json.loads(result)
        assert parsed["matches"] > 0

    def test_head_to_head_tool(self):
        from server import head_to_head
        result = head_to_head(team1="Flamengo", team2="Corinthians")
        parsed = json.loads(result)
        assert parsed["total_matches"] > 0

    def test_search_players_tool(self):
        from server import search_players
        result = search_players(name="Neymar")
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_competition_standings_tool(self):
        from server import competition_standings
        result = competition_standings(competition="Brasileirao", season=2019)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_statistical_summary_tool(self):
        from server import statistical_summary
        result = statistical_summary()
        parsed = json.loads(result)
        assert parsed["total_matches"] > 0

    def test_no_results_message(self):
        from server import search_matches
        result = search_matches(team="NonexistentTeamXYZ")
        assert "No matches found" in result


# ---------------------------------------------------------------------------
# Feature: Cross-file Queries
# ---------------------------------------------------------------------------

class TestCrossFileQueries:
    def test_player_and_team_match_data(self, data):
        """Find players for a club that also appears in match data."""
        players = data.search_players(club="Santos", limit=5)
        assert len(players) > 0
        matches = data.search_matches(team="Santos", limit=5)
        assert len(matches) > 0

    def test_multiple_competitions(self, data):
        """Search across multiple competitions."""
        brasileirao = data.search_matches(team="Palmeiras", competition="Brasileirao", limit=5)
        libertadores = data.search_matches(team="Palmeiras", competition="Libertadores", limit=5)
        assert len(brasileirao) > 0
        assert len(libertadores) > 0


# ---------------------------------------------------------------------------
# Feature: Performance
# ---------------------------------------------------------------------------

class TestPerformance:
    def test_simple_lookup_under_2s(self, data):
        import time
        start = time.time()
        data.search_matches(team="Flamengo", limit=10)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Simple lookup took {elapsed:.2f}s"

    def test_aggregate_query_under_5s(self, data):
        import time
        start = time.time()
        data.competition_standings("Brasileirao", 2019)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Aggregate query took {elapsed:.2f}s"

    def test_player_search_under_2s(self, data):
        import time
        start = time.time()
        data.search_players(nationality="Brazil", limit=20)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Player search took {elapsed:.2f}s"
