"""BDD-style tests for SoccerData query layer."""
from __future__ import annotations

import pytest

from brazilian_soccer.data import SoccerData, normalize_team


@pytest.fixture(scope="module")
def data() -> SoccerData:
    return SoccerData()


# Feature: Team name normalization
class TestNormalization:
    def test_strips_state_suffix(self):
        assert normalize_team("Palmeiras-SP") == normalize_team("Palmeiras")

    def test_strips_country_code(self):
        assert normalize_team("Nacional (URU)") == "nacional"

    def test_strips_accents(self):
        assert normalize_team("Grêmio") == normalize_team("Gremio")

    def test_handles_none(self):
        assert normalize_team(None) == ""


# Feature: Data loading
class TestLoading:
    def test_all_frames_loaded(self, data: SoccerData):
        assert len(data.brasileirao) > 4000
        assert len(data.cup) > 1000
        assert len(data.libertadores) > 1000
        assert len(data.extended) > 10000
        assert len(data.historical) > 6000
        assert len(data.players) > 18000

    def test_unified_matches(self, data: SoccerData):
        assert len(data.matches) > 20000
        assert {"home_team", "away_team", "home_goal",
                "away_goal", "tournament", "season"}.issubset(data.matches.columns)


# Feature: Match Queries
class TestMatchQueries:
    def test_find_matches_by_team(self, data: SoccerData):
        df = data.find_matches(team="Flamengo")
        assert len(df) > 0
        teams = set(df["home_norm"]).union(df["away_norm"])
        assert "flamengo" in teams

    def test_find_matches_between_teams(self, data: SoccerData):
        df = data.find_matches(team="Flamengo", opponent="Fluminense")
        assert len(df) > 0
        for _, r in df.iterrows():
            pair = {r["home_norm"], r["away_norm"]}
            assert "flamengo" in pair and "fluminense" in pair

    def test_find_matches_by_season(self, data: SoccerData):
        df = data.find_matches(team="Palmeiras", season=2019)
        assert len(df) > 0
        assert (df["season"] == 2019).all()

    def test_find_matches_by_competition(self, data: SoccerData):
        df = data.find_matches(competition="Libertadores", limit=20)
        assert len(df) > 0
        assert df["tournament"].str.contains("Libertadores", case=False).all()


# Feature: Head-to-head
class TestHeadToHead:
    def test_returns_counts(self, data: SoccerData):
        h2h = data.head_to_head("Flamengo", "Fluminense")
        assert h2h["matches"] > 0
        assert h2h["matches"] == (
            h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
        )


# Feature: Team stats
class TestTeamStats:
    def test_stats_structure(self, data: SoccerData):
        stats = data.team_stats("Corinthians", season=2019, competition="Brasileirão")
        assert stats["matches"] >= 0
        assert stats["points"] == stats["wins"] * 3 + stats["draws"]
        assert stats["matches"] == stats["wins"] + stats["draws"] + stats["losses"]

    def test_home_only_filter(self, data: SoccerData):
        stats = data.team_stats("Palmeiras", season=2019, home_only=True)
        assert stats["matches"] > 0


# Feature: Standings
class TestStandings:
    def test_standings_ordered(self, data: SoccerData):
        table = data.standings(2019, competition="Brasileirão")
        assert not table.empty
        pts = table["Pts"].tolist()
        assert pts == sorted(pts, reverse=True)


# Feature: Aggregates
class TestAggregates:
    def test_biggest_wins(self, data: SoccerData):
        df = data.biggest_wins(limit=5)
        assert len(df) == 5
        margins = df["margin"].tolist()
        assert margins == sorted(margins, reverse=True)

    def test_average_goals(self, data: SoccerData):
        agg = data.average_goals(competition="Brasileirão")
        assert agg["matches"] > 0
        assert 0 < agg["avg_goals"] < 10
        assert 0 <= agg["home_win_rate"] <= 1


# Feature: Player queries
class TestPlayers:
    def test_find_brazilians(self, data: SoccerData):
        df = data.search_players(nationality="Brazil", limit=10)
        assert len(df) == 10
        assert df["Nationality"].str.contains("Brazil").all()

    def test_search_by_name(self, data: SoccerData):
        df = data.search_players(name="Neymar")
        assert len(df) > 0
        assert df["Name"].str.contains("Neymar", case=False).any()

    def test_filter_by_min_overall(self, data: SoccerData):
        df = data.search_players(min_overall=85, limit=20)
        assert len(df) > 0
        assert (df["Overall"] >= 85).all()
