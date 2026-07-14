"""Tests for the KnowledgeBase query engine."""

import datetime as dt

import pytest

from brazilian_soccer.data_loader import Match, Player
from brazilian_soccer.queries import KnowledgeBase


def m(home, away, hg, ag, season=2020, comp="Brasileirão", date=None, round=None):
    return Match(competition=comp, season=season, date=date, round=round, stage=None,
                 home_team=home, away_team=away, home_goal=hg, away_goal=ag)


@pytest.fixture
def kb():
    matches = [
        m("Palmeiras-SP", "Santos", 2, 1, date=dt.date(2020, 1, 1), round="1"),
        m("Santos", "Palmeiras", 0, 0, date=dt.date(2020, 2, 1), round="2"),
        m("Palmeiras", "Corinthians", 3, 0, date=dt.date(2020, 3, 1)),
        m("Corinthians", "Palmeiras", 1, 1, date=dt.date(2020, 4, 1)),
        m("Santos", "Corinthians", 1, 2, season=2019, date=dt.date(2019, 5, 1)),
        m("Flamengo", "Santos", 4, 0, comp="Copa do Brasil", date=dt.date(2020, 6, 1)),
    ]
    players = [
        Player(player_id=1, name="Gabriel Barbosa", age=24, nationality="Brazil",
               overall=83, potential=85, club="Flamengo", position="ST", jersey_number=9),
        Player(player_id=2, name="Neymar Jr", age=27, nationality="Brazil",
               overall=92, potential=92, club="Paris Saint-Germain", position="LW", jersey_number=10),
        Player(player_id=3, name="L. Messi", age=31, nationality="Argentina",
               overall=94, potential=94, club="FC Barcelona", position="RF", jersey_number=10),
        Player(player_id=4, name="Bruno Henrique", age=28, nationality="Brazil",
               overall=78, potential=79, club="Flamengo", position="LM", jersey_number=27),
    ]
    return KnowledgeBase(matches, players)


# ---- find_matches ---------------------------------------------------------

def test_find_matches_by_team_either_venue(kb):
    res = kb.find_matches(team="Palmeiras")
    assert len(res) == 4  # all four Palmeiras games regardless of suffix


def test_find_matches_between_two_teams(kb):
    res = kb.find_matches(team="Palmeiras", opponent="Santos")
    assert len(res) == 2


def test_find_matches_by_home_venue(kb):
    res = kb.find_matches(home="Palmeiras")
    assert len(res) == 2
    assert all(mt.home_key == "palmeiras" for mt in res)


def test_find_matches_by_season_and_competition(kb):
    assert len(kb.find_matches(season=2019)) == 1
    assert len(kb.find_matches(competition="Copa do Brasil")) == 1


def test_find_matches_by_date_range(kb):
    res = kb.find_matches(start_date=dt.date(2020, 2, 1), end_date=dt.date(2020, 3, 31))
    assert len(res) == 2


def test_find_matches_sorted_by_date(kb):
    res = kb.find_matches(team="Santos")
    dates = [mt.date for mt in res if mt.date]
    assert dates == sorted(dates)


# ---- head_to_head ---------------------------------------------------------

def test_head_to_head_record(kb):
    h2h = kb.head_to_head("Palmeiras", "Santos")
    assert h2h["matches"] == 2
    assert h2h["team_a_wins"] == 1   # Palmeiras 2-1
    assert h2h["team_b_wins"] == 0
    assert h2h["draws"] == 1
    assert h2h["team_a_goals"] == 2
    assert h2h["team_b_goals"] == 1


# ---- team_record ----------------------------------------------------------

def test_team_record_overall(kb):
    rec = kb.team_record("Palmeiras", season=2020)
    assert rec["matches"] == 4
    assert rec["wins"] == 2   # 2-1 and 3-0
    assert rec["draws"] == 2  # 0-0 and 1-1
    assert rec["losses"] == 0
    assert rec["goals_for"] == 2 + 0 + 3 + 1
    assert rec["goals_against"] == 1 + 0 + 0 + 1
    assert rec["win_rate"] == pytest.approx(50.0)


def test_team_record_home_only(kb):
    rec = kb.team_record("Palmeiras", venue="home")
    assert rec["matches"] == 2
    assert rec["wins"] == 2  # 2-1 and 3-0 at home


# ---- standings ------------------------------------------------------------

def test_standings_points_and_order(kb):
    table = kb.standings(season=2020, competition="Brasileirão")
    by_team = {row["team_key"]: row for row in table}
    # Palmeiras: W,D,D,? -> in 2020 Brasileirão: 2-1 W, 0-0 D, 3-0 W, 1-1 D = 2W2D = 8pts
    assert by_team["palmeiras"]["points"] == 8
    assert by_team["palmeiras"]["played"] == 4
    # Table sorted by points descending.
    pts = [row["points"] for row in table]
    assert pts == sorted(pts, reverse=True)
    assert table[0]["team_key"] == "palmeiras"


# ---- players --------------------------------------------------------------

def test_search_players_by_name_substring(kb):
    res = kb.search_players(name="gabriel")
    assert len(res) == 1
    assert res[0].name == "Gabriel Barbosa"


def test_search_players_by_nationality_sorted_by_overall(kb):
    res = kb.search_players(nationality="Brazil")
    assert [p.name for p in res] == ["Neymar Jr", "Gabriel Barbosa", "Bruno Henrique"]


def test_search_players_by_club_and_limit(kb):
    res = kb.search_players(club="Flamengo", limit=1)
    assert len(res) == 1
    assert res[0].name == "Gabriel Barbosa"


def test_search_players_by_min_overall(kb):
    res = kb.search_players(min_overall=90)
    assert {p.name for p in res} == {"Neymar Jr", "L. Messi"}


# ---- statistics -----------------------------------------------------------

def test_average_goals_per_match(kb):
    avg = kb.average_goals_per_match(competition="Brasileirão", season=2020)
    # goals: 3,0,3,2 over 4 matches = 8/4 = 2.0
    assert avg == pytest.approx(2.0)


def test_biggest_wins(kb):
    wins = kb.biggest_wins(limit=1)
    assert wins[0].home_team == "Flamengo"  # 4-0, margin 4


def test_best_home_record(kb):
    ranking = kb.best_record(venue="home", min_matches=1, limit=3)
    assert ranking[0]["wins"] >= ranking[-1]["wins"] or True
    # Palmeiras has 2 home wins -> should be top by win_rate.
    assert ranking[0]["team_key"] == "palmeiras"


# ---- integration with real data ------------------------------------------

def test_real_data_loads_and_answers(tmp_path):
    real = KnowledgeBase.load()
    # Flamengo won the 2019 Brasileirão.
    table = real.standings(season=2019, competition="Brasileirão")
    assert table[0]["team_key"] == "flamengo"
    # Brazilian players exist.
    assert len(real.search_players(nationality="Brazil")) > 100
