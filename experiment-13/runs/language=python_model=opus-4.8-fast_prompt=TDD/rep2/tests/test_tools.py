"""Tests for the formatted-answer tool layer used by the MCP server."""

import datetime as dt

import pytest

from brazilian_soccer.data_loader import Match, Player
from brazilian_soccer.queries import KnowledgeBase
from brazilian_soccer.tools import SoccerTools


def m(home, away, hg, ag, season=2020, comp="Brasileirão", date=None, round=None):
    return Match(competition=comp, season=season, date=date, round=round, stage=None,
                 home_team=home, away_team=away, home_goal=hg, away_goal=ag)


@pytest.fixture
def tools():
    matches = [
        m("Palmeiras-SP", "Santos", 2, 1, date=dt.date(2020, 1, 1), round="1"),
        m("Santos", "Palmeiras", 0, 0, date=dt.date(2020, 2, 1), round="2"),
        m("Palmeiras", "Corinthians", 3, 0, date=dt.date(2020, 3, 1)),
        m("Flamengo", "Santos", 4, 0, comp="Copa do Brasil", date=dt.date(2020, 6, 1)),
    ]
    players = [
        Player(player_id=1, name="Gabriel Barbosa", age=24, nationality="Brazil",
               overall=83, potential=85, club="Flamengo", position="ST", jersey_number=9),
        Player(player_id=2, name="Neymar Jr", age=27, nationality="Brazil",
               overall=92, potential=92, club="Paris Saint-Germain", position="LW", jersey_number=10),
    ]
    return SoccerTools(KnowledgeBase(matches, players))


def test_search_matches_lists_scores(tools):
    out = tools.search_matches(team="Palmeiras", opponent="Santos")
    assert "Palmeiras" in out and "Santos" in out
    assert "2-1" in out
    assert "2020-01-01" in out


def test_search_matches_no_results_message(tools):
    out = tools.search_matches(team="Nonexistent FC")
    assert "no matches" in out.lower()


def test_head_to_head_summary(tools):
    out = tools.head_to_head("Palmeiras", "Santos")
    assert "1 win" in out.lower() or "wins: 1" in out.lower() or "1 wins" in out.lower()
    assert "draw" in out.lower()


def test_team_record_formatting(tools):
    out = tools.team_record("Palmeiras", season=2020)
    assert "Palmeiras" in out
    assert "Wins" in out or "wins" in out
    assert "%" in out  # win rate percentage shown


def test_standings_shows_positions(tools):
    out = tools.standings(season=2020, competition="Brasileirão")
    assert "1." in out
    assert "Palmeiras" in out
    assert "pts" in out.lower()


def test_search_players_formatting(tools):
    out = tools.search_players(nationality="Brazil")
    assert "Neymar Jr" in out
    assert "92" in out
    # highest rated first
    assert out.index("Neymar Jr") < out.index("Gabriel Barbosa")


def test_statistics_average_goals(tools):
    out = tools.statistics(competition="Brasileirão", season=2020)
    assert "goals per match" in out.lower()


def test_biggest_wins_formatting(tools):
    out = tools.biggest_wins(limit=1)
    assert "Flamengo" in out
    assert "4-0" in out
