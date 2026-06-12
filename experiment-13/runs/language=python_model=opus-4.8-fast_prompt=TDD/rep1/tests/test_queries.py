"""Tests for the KnowledgeGraph query engine (against fixtures)."""
import datetime

import pytest

from brazilian_soccer import data_loader
from brazilian_soccer.queries import KnowledgeGraph


@pytest.fixture(scope="module")
def kg(fixture_dir):
    matches = data_loader.load_matches(fixture_dir)
    players = data_loader.load_players(fixture_dir)
    return KnowledgeGraph(matches, players)


# --- match queries -------------------------------------------------------

def test_find_matches_by_team(kg):
    res = kg.find_matches(team="Flamengo", competition="Brasileirão")
    # m1 (home), m2 (away), m5 (home vs Coritiba)
    assert len(res) == 3


def test_find_matches_by_two_teams(kg):
    res = kg.find_matches(team="Flamengo", team2="Fluminense")
    assert len(res) == 2
    assert all({m.home_key, m.away_key} == {"flamengo", "fluminense"} for m in res)


def test_find_matches_by_season_and_competition(kg):
    res = kg.find_matches(competition="Brasileirão", season=2019)
    assert len(res) == 3


def test_find_matches_by_venue_home(kg):
    res = kg.find_matches(team="Flamengo", competition="Brasileirão", venue="home")
    assert all(m.home_key == "flamengo" for m in res)
    assert len(res) == 2


def test_find_matches_by_date_range(kg):
    res = kg.find_matches(
        team="Flamengo",
        date_from=datetime.date(2019, 1, 1),
        date_to=datetime.date(2019, 6, 1),
    )
    assert all(datetime.date(2019, 1, 1) <= m.date <= datetime.date(2019, 6, 1)
               for m in res)


def test_matches_are_deduplicated(kg):
    assert len(kg.matches) == 11


def test_near_duplicate_fixtures_collapse_keeping_played():
    # Same ordered fixture, one snapshot unplayed and one (a day later, name
    # variant) with the real result -> single played match retained.
    from brazilian_soccer.data_loader import Match
    unplayed = Match("Brasileirão", "Corinthians", "Cuiaba", None, None, 2022,
                     date=datetime.date(2022, 10, 1))
    played = Match("Serie A", "Corinthians", "Cuiaba FC", 2, 0, 2022,
                   date=datetime.date(2022, 10, 2))
    kg2 = KnowledgeGraph([unplayed, played], [])
    assert len(kg2.matches) == 1
    assert kg2.matches[0].played
    assert kg2.matches[0].home_goal == 2


def test_same_date_name_variants_collapse():
    # Same home team, same date, opponent under three name variants -> one match.
    from brazilian_soccer.data_loader import Match
    rows = [
        Match("Brasileirão", "Flamengo", "Atletico", 3, 2, 2019,
              date=datetime.date(2019, 5, 26)),
        Match("Serie A", "Flamengo", "Atletico Paranaense", 3, 2, 2019,
              date=datetime.date(2019, 5, 26)),
        Match("Brasileirão", "Flamengo", "Athletico", 3, 2, 2019,
              date=datetime.date(2019, 5, 26)),
    ]
    kg2 = KnowledgeGraph(rows, [])
    assert len(kg2.matches) == 1


def test_unplayed_no_date_fixtures_not_overmerged():
    # Two distinct future fixtures for one home team, no dates yet, must survive.
    from brazilian_soccer.data_loader import Match
    a = Match("Brasileirão", "Flamengo", "Santos", None, None, 2024, date=None)
    b = Match("Brasileirão", "Flamengo", "Palmeiras", None, None, 2024, date=None)
    kg2 = KnowledgeGraph([a, b], [])
    assert len(kg2.matches) == 2


def test_distinct_ordered_fixtures_not_merged():
    # Home and away legs are distinct ordered pairs and must both survive.
    from brazilian_soccer.data_loader import Match
    leg1 = Match("Brasileirão", "Flamengo", "Fluminense", 2, 1, 2019,
                 date=datetime.date(2019, 5, 19))
    leg2 = Match("Brasileirão", "Fluminense", "Flamengo", 0, 3, 2019,
                 date=datetime.date(2019, 8, 10))
    kg2 = KnowledgeGraph([leg1, leg2], [])
    assert len(kg2.matches) == 2


def test_cross_competition_duplicates_removed():
    # Same match labelled "Brasileirão" and "Serie A" should collapse to one.
    from brazilian_soccer.data_loader import Match
    dup_a = Match("Brasileirão", "Flamengo", "Goias", 6, 1, 2019,
                  date=datetime.date(2019, 7, 14))
    dup_b = Match("Serie A", "Flamengo", "Goias", 6, 1, 2019,
                  date=datetime.date(2019, 7, 14))
    kg2 = KnowledgeGraph([dup_a, dup_b], [])
    assert len(kg2.matches) == 1


# --- head to head --------------------------------------------------------

def test_head_to_head(kg):
    h2h = kg.head_to_head("Flamengo", "Fluminense")
    assert h2h["team_a"] == "Flamengo"
    assert h2h["wins_a"] == 2
    assert h2h["wins_b"] == 0
    assert h2h["draws"] == 0
    assert h2h["total"] == 2


# --- team record ---------------------------------------------------------

def test_team_record(kg):
    rec = kg.team_record("Flamengo", competition="Brasileirão")
    assert rec["matches"] == 3
    assert rec["wins"] == 2
    assert rec["draws"] == 1
    assert rec["losses"] == 0
    assert rec["goals_for"] == 6
    assert rec["goals_against"] == 2
    assert rec["win_rate"] == pytest.approx(66.7, abs=0.1)


def test_team_record_home_only(kg):
    rec = kg.team_record("Flamengo", competition="Brasileirão", venue="home")
    assert rec["matches"] == 2
    assert rec["wins"] == 1
    assert rec["draws"] == 1


# --- player queries ------------------------------------------------------

def test_find_players_by_nationality(kg):
    res = kg.find_players(nationality="Brazil")
    names = {p.name for p in res}
    assert names == {"Neymar Jr", "Gabriel Barbosa"}


def test_find_players_sorted_by_overall(kg):
    res = kg.find_players(nationality="Brazil")
    assert res[0].name == "Neymar Jr"  # 92 > 80


def test_find_players_by_club(kg):
    res = kg.find_players(club="Flamengo")
    assert [p.name for p in res] == ["Gabriel Barbosa"]


def test_find_players_by_name(kg):
    res = kg.find_players(name="messi")
    assert res and res[0].name == "L. Messi"


def test_find_players_by_position(kg):
    res = kg.find_players(position="GK")
    assert [p.name for p in res] == ["M. Neuer"]


# --- competition queries -------------------------------------------------

def test_standings(kg):
    table = kg.standings("Brasileirão", 2019)
    assert len(table) == 4
    assert table[0]["team"] == "Flamengo"
    assert table[0]["points"] == 6
    assert table[0]["goal_diff"] == 4


def test_champion(kg):
    assert kg.champion("Brasileirão", 2019) == "Flamengo"


# --- statistics ----------------------------------------------------------

def test_average_goals_per_match(kg):
    avg = kg.average_goals_per_match(competition="Brasileirão", season=2019)
    assert avg == pytest.approx(8 / 3, abs=0.01)


def test_biggest_wins(kg):
    res = kg.biggest_wins(limit=3)
    top = res[0]
    assert abs(top.home_goal - top.away_goal) == 3


def test_home_win_rate(kg):
    rate = kg.home_win_rate(competition="Brasileirão", season=2019)
    # m1 home win, m2 away win, m3 draw -> 1/3 home wins
    assert rate == pytest.approx(100 / 3, abs=0.1)
