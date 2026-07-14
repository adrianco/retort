"""Tests for the SoccerKB query/analytics layer using small fixtures."""
import pytest

from brazilian_soccer.data_loader import Match, Player
from brazilian_soccer.knowledge_base import SoccerKB


def M(comp, home, away, hs, as_, season=2019, date="2019-05-01", **kw):
    return Match(competition=comp, home_team=home, away_team=away,
                 home_score=hs, away_score=as_, season=season, date=date, **kw)


@pytest.fixture
def kb():
    matches = [
        # A tiny 3-team Serie A "league" for 2019 (each pair plays twice).
        M("Brasileirão Série A", "Flamengo", "Santos", 2, 0, date="2019-05-01", round="1"),
        M("Brasileirão Série A", "Santos", "Flamengo", 1, 1, date="2019-08-01", round="20"),
        M("Brasileirão Série A", "Flamengo", "Palmeiras", 3, 1, date="2019-05-08", round="2"),
        M("Brasileirão Série A", "Palmeiras", "Flamengo", 0, 0, date="2019-08-08", round="21"),
        M("Brasileirão Série A", "Santos", "Palmeiras", 1, 2, date="2019-05-15", round="3"),
        M("Brasileirão Série A", "Palmeiras", "Santos", 4, 0, date="2019-08-15", round="22"),
        # A different season / competition for filtering tests.
        M("Brasileirão Série A", "Flamengo", "Santos", 0, 1, season=2018, date="2018-05-01"),
        M("Copa Libertadores", "Flamengo", "Santos", 5, 0, season=2019,
          date="2019-06-01", stage="final"),
        # State-suffixed opponent name must still match a suffix-less query.
        M("Brasileirão Série A", "Flamengo", "Vasco-RJ", 2, 1, date="2019-09-01"),
    ]
    players = [
        Player(1, "Neymar Jr", 26, "Brazil", 92, 93, "Paris Saint-Germain", "LW"),
        Player(2, "Gabriel Barbosa", 22, "Brazil", 78, 85, "Flamengo", "ST"),
        Player(3, "L. Messi", 31, "Argentina", 94, 94, "FC Barcelona", "RF"),
        Player(4, "Bruno Henrique", 28, "Brazil", 77, 78, "Flamengo", "LW"),
        Player(5, "Marinho", 29, "Brazil", 75, 75, "Santos", "RW"),
    ]
    return SoccerKB(matches, players)


class TestFindMatches:
    def test_by_team_either_venue(self, kb):
        res = kb.find_matches(team="Flamengo")
        # 2019 SA (5: vs Santos x2, vs Palmeiras x2, vs Vasco) + 2018 SA (1)
        # + Libertadores (1) = 7
        assert len(res) == 7

    def test_team_name_variation_matches(self, kb):
        res = kb.find_matches(team="Vasco")
        assert len(res) == 1
        assert res[0].away_team == "Vasco"

    def test_by_two_teams(self, kb):
        res = kb.find_matches(team="Flamengo", opponent="Santos")
        # Across all comps/seasons: 2019 SA home, 2019 SA away, 2018 SA, Libertadores
        assert len(res) == 4

    def test_filter_by_competition(self, kb):
        res = kb.find_matches(team="Flamengo", competition="Libertadores")
        assert len(res) == 1
        assert res[0].competition == "Copa Libertadores"

    def test_filter_by_season(self, kb):
        res = kb.find_matches(team="Flamengo", season=2018)
        assert len(res) == 1
        assert res[0].season == 2018

    def test_filter_by_venue_home(self, kb):
        res = kb.find_matches(team="Flamengo", venue="home",
                              competition="Brasileirão", season=2019)
        assert all(m.home_key == "flamengo" for m in res)
        assert len(res) == 3  # vs Santos, vs Palmeiras, vs Vasco

    def test_date_range(self, kb):
        res = kb.find_matches(team="Flamengo", start_date="2019-08-01",
                              end_date="2019-08-31")
        # Aug 2019: Santos 1-1 Fla (08-01) and Palmeiras 0-0 Fla (08-08).
        assert len(res) == 2

    def test_limit_and_sorted_by_date_desc(self, kb):
        res = kb.find_matches(team="Flamengo", limit=2)
        assert len(res) == 2
        assert res[0].date >= res[1].date


class TestHeadToHead:
    def test_counts_wins_and_draws(self, kb):
        h2h = kb.head_to_head("Flamengo", "Santos", competition="Brasileirão",
                              season=2019)
        # 2019 SA: Fla 2-0 Santos (Fla win), Santos 1-1 Fla (draw)
        assert h2h["team1_wins"] == 1
        assert h2h["team2_wins"] == 0
        assert h2h["draws"] == 1
        assert h2h["total"] == 2

    def test_symmetric_perspective(self, kb):
        h2h = kb.head_to_head("Santos", "Flamengo", competition="Brasileirão",
                              season=2019)
        assert h2h["team1_wins"] == 0  # Santos
        assert h2h["team2_wins"] == 1  # Flamengo


class TestTeamRecord:
    def test_full_season_record(self, kb):
        rec = kb.team_record("Flamengo", competition="Brasileirão", season=2019)
        # Matches: 2-0 W, 1-1 D, 3-1 W, 0-0 D, 2-1 W  => 5 matches
        assert rec["matches"] == 5
        assert rec["wins"] == 3
        assert rec["draws"] == 2
        assert rec["losses"] == 0
        assert rec["goals_for"] == 2 + 1 + 3 + 0 + 2
        assert rec["goals_against"] == 0 + 1 + 1 + 0 + 1
        assert rec["win_rate"] == pytest.approx(60.0, abs=0.1)

    def test_home_only_record(self, kb):
        rec = kb.team_record("Flamengo", competition="Brasileirão", season=2019,
                             venue="home")
        # Home games: 2-0 vs Santos, 3-1 vs Palmeiras, 2-1 vs Vasco => 3 wins.
        assert rec["matches"] == 3
        assert rec["wins"] == 3
        assert rec["draws"] == 0


class TestStandings:
    def test_points_and_order(self, kb):
        table = kb.standings("Brasileirão", 2019)
        assert [row["team"] for row in table][0] == "Flamengo"
        fl: dict = table[0]
        # Flamengo: 3W 2D 0L (within these 3-team double round-robin) => but only
        # vs Santos and Palmeiras count here (Vasco played once). Verify points.
        assert fl["points"] == fl["wins"] * 3 + fl["draws"]
        # Table is sorted by points descending.
        pts = [row["points"] for row in table]
        assert pts == sorted(pts, reverse=True)

    def test_only_includes_requested_season(self, kb):
        table = kb.standings("Brasileirão", 2018)
        # 2018 had a single match Flamengo 0-1 Santos.
        santos = next(r for r in table if r["team"] == "Santos")
        assert santos["points"] == 3
        assert santos["wins"] == 1


class TestPlayers:
    def test_search_by_name(self, kb):
        res = kb.search_players(name="gabriel")
        assert len(res) == 1
        assert res[0].name == "Gabriel Barbosa"

    def test_filter_by_nationality_sorted_by_overall(self, kb):
        res = kb.search_players(nationality="Brazil")
        assert [p.name for p in res][0] == "Neymar Jr"
        assert all(p.nationality == "Brazil" for p in res)

    def test_filter_by_club(self, kb):
        res = kb.search_players(club="Flamengo")
        assert {p.name for p in res} == {"Gabriel Barbosa", "Bruno Henrique"}

    def test_filter_by_position_and_min_overall(self, kb):
        res = kb.search_players(position="LW", min_overall=80)
        assert [p.name for p in res] == ["Neymar Jr"]

    def test_limit(self, kb):
        res = kb.search_players(nationality="Brazil", limit=2)
        assert len(res) == 2


class TestStatistics:
    def test_competition_stats(self, kb):
        stats = kb.competition_stats(competition="Brasileirão", season=2019)
        assert stats["matches"] == 7
        total = 2 + 1 + 3 + 0 + 1 + 4 + 2  # home goals
        total += 0 + 1 + 1 + 0 + 2 + 0 + 1  # away goals
        assert stats["total_goals"] == total
        assert stats["avg_goals_per_match"] == pytest.approx(total / 7, abs=0.01)
        assert 0 <= stats["home_win_rate"] <= 100

    def test_biggest_wins(self, kb):
        res = kb.biggest_wins(limit=1)
        # Libertadores Flamengo 5-0 Santos is the biggest margin.
        top = res[0]
        assert top.home_team == "Flamengo" and top.home_score == 5

    def test_list_competitions_and_seasons(self, kb):
        comps = kb.list_competitions()
        assert "Brasileirão Série A" in comps
        assert "Copa Libertadores" in comps
        seasons = kb.list_seasons("Brasileirão")
        assert 2018 in seasons and 2019 in seasons
