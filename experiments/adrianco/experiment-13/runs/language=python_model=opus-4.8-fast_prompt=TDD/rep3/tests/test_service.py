"""Tests for the service layer that formats KB results into answer text."""
import pytest

from brazilian_soccer.data_loader import Match, Player
from brazilian_soccer.knowledge_base import SoccerKB
from brazilian_soccer import service as svc


def M(comp, home, away, hs, as_, season=2019, date="2019-05-01", **kw):
    return Match(competition=comp, home_team=home, away_team=away,
                 home_score=hs, away_score=as_, season=season, date=date, **kw)


@pytest.fixture
def kb():
    matches = [
        M("Brasileirão Série A", "Flamengo", "Santos", 2, 0, date="2019-05-01", round="1"),
        M("Brasileirão Série A", "Santos", "Flamengo", 1, 1, date="2019-08-01", round="20"),
        M("Brasileirão Série A", "Flamengo", "Palmeiras", 3, 1, date="2019-05-08", round="2"),
        M("Copa Libertadores", "Flamengo", "Santos", 5, 0, season=2019,
          date="2019-06-01", stage="final"),
    ]
    players = [
        Player(1, "Neymar Jr", 26, "Brazil", 92, 93, "Paris Saint-Germain", "LW"),
        Player(2, "Gabriel Barbosa", 22, "Brazil", 78, 85, "Flamengo", "ST"),
    ]
    return SoccerKB(matches, players)


class TestFindMatches:
    def test_lists_matches_with_scores(self, kb):
        out = svc.answer_find_matches(kb, team="Flamengo")
        assert "Flamengo" in out
        assert "5-0" in out or "5 - 0" in out  # the Libertadores win
        assert "2019-06-01" in out

    def test_head_to_head_summary_when_opponent_given(self, kb):
        out = svc.answer_find_matches(kb, team="Flamengo", opponent="Santos")
        # Fla 2-0, Santos 1-1 Fla (draw), Fla 5-0 -> Fla 2 wins, 1 draw
        assert "Flamengo" in out and "Santos" in out
        assert "2 win" in out.lower()

    def test_no_results_message(self, kb):
        out = svc.answer_find_matches(kb, team="Nonexistent FC")
        assert "no match" in out.lower()


class TestTeamRecord:
    def test_includes_record_fields(self, kb):
        out = svc.answer_team_record(kb, team="Flamengo",
                                     competition="Brasileirão", season=2019)
        assert "Flamengo" in out
        assert "Wins" in out and "Draws" in out and "Losses" in out
        assert "Win rate" in out


class TestStandings:
    def test_renders_table(self, kb):
        out = svc.answer_standings(kb, competition="Brasileirão", season=2019)
        assert "Standings" in out
        assert "Flamengo" in out
        assert "pts" in out


class TestPlayers:
    def test_lists_players_sorted(self, kb):
        out = svc.answer_search_players(kb, nationality="Brazil")
        assert out.index("Neymar Jr") < out.index("Gabriel Barbosa")
        assert "Overall" in out

    def test_no_players_message(self, kb):
        out = svc.answer_search_players(kb, name="zzzzz")
        assert "no player" in out.lower()


class TestStats:
    def test_competition_stats_text(self, kb):
        out = svc.answer_competition_stats(kb, competition="Brasileirão",
                                           season=2019)
        assert "Avg goals" in out or "Average goals" in out

    def test_biggest_wins_text(self, kb):
        out = svc.answer_biggest_wins(kb, limit=1)
        assert "5-0" in out or "5 - 0" in out


class TestListings:
    def test_competitions(self, kb):
        out = svc.answer_list_competitions(kb)
        assert "Copa Libertadores" in out
        assert "Brasileirão Série A" in out

    def test_seasons(self, kb):
        out = svc.answer_list_seasons(kb, competition="Brasileirão")
        assert "2019" in out
