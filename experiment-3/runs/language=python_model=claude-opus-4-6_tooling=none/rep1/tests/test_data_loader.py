import pytest
from data_loader import (
    BrazilianSoccerData,
    load_brasileirao,
    load_copa_do_brasil,
    load_libertadores,
    load_br_football,
    load_historical_brasileirao,
    load_fifa_players,
    _normalize_team_name,
)


class TestTeamNameNormalization:
    def test_strip_state_suffix(self):
        assert _normalize_team_name("Palmeiras-SP") == "Palmeiras"
        assert _normalize_team_name("Flamengo-RJ") == "Flamengo"
        assert _normalize_team_name("Grêmio-RS") == "Grêmio"

    def test_no_suffix(self):
        assert _normalize_team_name("Palmeiras") == "Palmeiras"

    def test_whitespace(self):
        assert _normalize_team_name("  Palmeiras-SP  ") == "Palmeiras"


class TestDataLoading:
    def test_load_brasileirao(self):
        df = load_brasileirao()
        assert len(df) > 0
        assert "home" in df.columns
        assert "away" in df.columns
        assert "competition" in df.columns
        assert (df["competition"] == "Brasileirao").all()

    def test_load_copa_do_brasil(self):
        df = load_copa_do_brasil()
        assert len(df) > 0
        assert (df["competition"] == "Copa do Brasil").all()

    def test_load_libertadores(self):
        df = load_libertadores()
        assert len(df) > 0
        assert (df["competition"] == "Copa Libertadores").all()

    def test_load_br_football(self):
        df = load_br_football()
        assert len(df) > 0

    def test_load_historical(self):
        df = load_historical_brasileirao()
        assert len(df) > 0
        assert "arena" in df.columns

    def test_load_fifa(self):
        df = load_fifa_players()
        assert len(df) > 0
        assert "Name" in df.columns
        assert "Overall" in df.columns


class TestBrazilianSoccerData:
    @pytest.fixture(scope="class")
    def data(self):
        return BrazilianSoccerData()

    def test_all_matches_loaded(self, data):
        assert len(data.all_matches) > 10000

    def test_search_matches_by_team(self, data):
        df = data.search_matches(team="Flamengo")
        assert len(df) > 0

    def test_search_matches_head_to_head(self, data):
        df = data.search_matches(team="Flamengo", opponent="Fluminense")
        assert len(df) > 0

    def test_search_matches_by_season(self, data):
        df = data.search_matches(season=2019)
        assert len(df) > 0
        assert (df["season"] == 2019).all()

    def test_search_matches_by_competition(self, data):
        df = data.search_matches(competition="Copa do Brasil")
        assert len(df) > 0

    def test_search_matches_by_date_range(self, data):
        df = data.search_matches(date_from="2019-01-01", date_to="2019-12-31")
        assert len(df) > 0

    def test_team_statistics(self, data):
        stats = data.team_statistics("Palmeiras", season=2019)
        assert stats["matches"] > 0
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]
        assert stats["goals_for"] >= 0
        assert "win_rate" in stats

    def test_team_statistics_home_only(self, data):
        home = data.team_statistics("Corinthians", home_only=True)
        both = data.team_statistics("Corinthians")
        assert home["matches"] < both["matches"]

    def test_head_to_head(self, data):
        h2h = data.head_to_head("Palmeiras", "Santos")
        assert h2h["total_matches"] > 0
        assert "Palmeiras_wins" in h2h
        assert "Santos_wins" in h2h
        assert "draws" in h2h

    def test_search_players_by_name(self, data):
        df = data.search_players(name="Neymar")
        assert len(df) > 0

    def test_search_players_by_nationality(self, data):
        df = data.search_players(nationality="Brazil", limit=10)
        assert len(df) > 0

    def test_search_players_by_club(self, data):
        df = data.search_players(club="Santos")
        assert len(df) > 0

    def test_search_players_by_min_overall(self, data):
        df = data.search_players(min_overall=85)
        assert len(df) > 0
        assert (df["Overall"] >= 85).all()

    def test_competition_standings(self, data):
        standings = data.competition_standings("Brasileirao", 2019)
        assert len(standings) > 0
        assert "points" in standings.columns
        assert "wins" in standings.columns
        first = standings.iloc[0]
        assert first["points"] >= standings.iloc[-1]["points"]

    def test_match_statistics(self, data):
        stats = data.match_statistics()
        assert stats["total_matches"] > 0
        assert stats["avg_goals_per_match"] > 0
        assert "home_win_rate" in stats
        assert "biggest_win" in stats

    def test_match_statistics_by_team(self, data):
        stats = data.match_statistics(team="Flamengo")
        assert stats["total_matches"] > 0

    def test_match_statistics_by_competition(self, data):
        stats = data.match_statistics(competition="Brasileirao")
        assert stats["total_matches"] > 0
