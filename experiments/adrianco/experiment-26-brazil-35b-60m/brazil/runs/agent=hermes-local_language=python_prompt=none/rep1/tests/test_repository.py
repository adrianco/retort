"""Unit tests for the SoccerRepository class."""
import pytest
import pandas as pd
from repository import SoccerRepository


@pytest.fixture
def repo():
    return SoccerRepository()


class TestSearchMatches:
    def test_search_matches_by_team(self, repo):
        """Test searching matches by team name."""
        results = repo.search_matches(team="Flamengo")
        assert len(results) > 0
        for _, row in results.head(10).iterrows():
            ht = str(row["home_team"])
            at = str(row["away_team"])
            assert "Flamengo" in ht or "Flamengo" in at


    def test_search_matches_by_competition(self, repo):
        """Test searching matches by competition."""
        results = repo.search_matches(competition="Copa do Brasil")
        assert len(results) > 0
        for _, row in results.iterrows():
            assert "Copa do Brasil" in str(row["competition"])


    def test_search_matches_by_season(self, repo):
        """Test searching matches by season."""
        results = repo.search_matches(season="2023")
        assert len(results) > 0
        for _, row in results.iterrows():
            assert "2023" in str(row["season"])


    def test_search_matches_with_min_score(self, repo):
        """Test searching matches with minimum total goals."""
        results = repo.search_matches(min_score=6)
        assert len(results) > 0
        for _, row in results.iterrows():
            hg = float(row.get("home_goal", 0)) if pd.notna(row.get("home_goal")) else 0
            ag = float(row.get("away_goal", 0)) if pd.notna(row.get("away_goal")) else 0
            assert hg + ag >= 6


    def test_search_matches_limit(self, repo):
        """Test that limit parameter works."""
        results = repo.search_matches(limit=5)
        assert len(results) <= 5


    def test_search_matches_by_round(self, repo):
        """Test searching matches by round number."""
        results = repo.search_matches(round_num="1")
        assert len(results) > 0


    def test_search_matches_by_stage(self, repo):
        """Test searching matches by stage."""
        results = repo.search_matches(stage="Final")
        assert len(results) >= 0


class TestTeamStats:
    def test_get_team_stats_flamengo(self, repo):
        """Test getting overall stats for Flamengo."""
        stats = repo.get_team_stats(team="Flamengo")
        assert stats["total"]["matches"] > 0
        assert "wins" in stats["total"]
        assert "losses" in stats["total"]
        assert "draws" in stats["total"]
        assert "goals_for" in stats["total"]
        assert "goals_against" in stats["total"]


    def test_get_team_stats_corinthians(self, repo):
        """Test getting stats for Corinthians."""
        stats = repo.get_team_stats(team="Corinthians")
        assert stats["total"]["matches"] > 0


    def test_get_team_stats_season(self, repo):
        """Test getting stats filtered by season."""
        stats = repo.get_team_stats(team="Palmeiras", season="2022")
        assert stats["total"]["matches"] >= 0


    def test_get_team_stats_competition(self, repo):
        """Test getting stats filtered by competition."""
        stats = repo.get_team_stats(team="Flamengo", competition="Copa do Brasil")
        assert stats["total"]["matches"] >= 0


class TestHeadToHead:
    def test_head_to_head_flamengo_fluminense(self, repo):
        """Test head-to-head between Flamengo and Fluminense."""
        h2h = repo.get_head_to_head("Flamengo", "Fluminense")
        assert "total_matches" in h2h
        assert h2h["total_matches"] > 0


    def test_head_to_head_palmeiras_santos(self, repo):
        """Test head-to-head between Palmeiras and Santos."""
        h2h = repo.get_head_to_head("Palmeiras", "Santos")
        assert "teams" in h2h


class TestSearchPlayers:
    def test_search_player_by_name(self, repo):
        """Test searching for a player by name."""
        results = repo.search_players(name="Neymar")
        assert len(results) >= 1
        assert "Neymar" in str(results.iloc[0]["Name"])


    def test_search_brazilian_players(self, repo):
        """Test searching for Brazilian players."""
        results = repo.search_players(nationality="Brazil")
        assert len(results) >= 10


    def test_search_brazilian_players_min_rating(self, repo):
        """Test searching for Brazilian players with minimum rating."""
        results = repo.search_players(nationality="Brazil", min_overall=80)
        assert len(results) > 0
        for _, row in results.iterrows():
            assert row["Overall"] >= 80


    def test_search_players_at_club(self, repo):
        """Test searching for players at a specific club."""
        results = repo.search_players(club="Real Madrid")
        assert len(results) >= 1
        for _, row in results.iterrows():
            assert "Real Madrid" in str(row["Club"])


    def test_search_players_limit(self, repo):
        """Test player search limit."""
        results = repo.search_players(limit=5)
        assert len(results) <= 5


class TestLeagueStandings:
    def test_get_league_standings_2023(self, repo):
        """Test getting league standings for 2023."""
        standings = repo.get_league_standings(season="2023")
        assert len(standings) > 0
        assert "team" in standings.columns
        assert "points" in standings.columns
        assert "wins" in standings.columns


    def test_get_league_standings_2019(self, repo):
        """Test getting league standings for 2019."""
        standings = repo.get_league_standings(season="2019")
        assert len(standings) > 0


    def test_get_league_standings_empty(self, repo):
        """Test getting league standings for non-existent season."""
        standings = repo.get_league_standings(season="1990")
        assert len(standings) == 0


class TestBiggestWins:
    def test_get_biggest_wins(self, repo):
        """Test getting biggest wins."""
        wins = repo.get_biggest_wins(limit=10)
        assert len(wins) > 0
        if len(wins) > 1:
            assert wins["margin"].iloc[0] >= wins["margin"].iloc[-1]


class TestAverageGoals:
    def test_get_average_goals(self, repo):
        """Test getting average goals statistics."""
        stats = repo.get_average_goals()
        assert stats["average_goals"] > 0
        assert stats["home_win_rate"] > 0
        assert stats["total_matches"] > 0


    def test_get_average_goals_by_competition(self, repo):
        """Test getting average goals by competition."""
        stats = repo.get_average_goals(competition="Copa do Brasil")
        assert stats["total_matches"] > 0


    def test_get_average_goals_by_season(self, repo):
        """Test getting average goals by season."""
        stats = repo.get_average_goals(season="2023")
        assert stats["total_matches"] >= 0


class TestGetCompetitions:
    def test_get_competitions(self, repo):
        """Test getting list of competitions."""
        comps = repo.get_competitions()
        assert any("Brasileir" in str(c) for c in comps)
        assert any("Copa do Brasil" in str(c) for c in comps)
        assert any("Libertadores" in str(c) for c in comps)


    def test_get_all_teams(self, repo):
        """Test getting list of all teams."""
        teams = repo.get_all_teams()
        assert len(teams) >= 50
        assert any("Flamengo" in str(t) for t in teams)
