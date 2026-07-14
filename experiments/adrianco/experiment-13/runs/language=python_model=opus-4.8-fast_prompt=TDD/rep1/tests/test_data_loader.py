"""Tests for loading the CSV datasets into normalized records."""
import datetime

import pytest

from brazilian_soccer import data_loader


@pytest.fixture(scope="module")
def matches(fixture_dir):
    return data_loader.load_matches(fixture_dir)


@pytest.fixture(scope="module")
def players(fixture_dir):
    return data_loader.load_players(fixture_dir)


# --- matches -------------------------------------------------------------

def test_loads_all_match_files(matches):
    # 3 + 2 + 2 + 2 + 2 rows across the five fixture match files.
    assert len(matches) == 11


def test_competitions_are_labelled(matches):
    comps = {m.competition for m in matches}
    assert "Brasileirão" in comps
    assert "Copa do Brasil" in comps
    assert "Copa Libertadores" in comps


def test_team_names_are_normalized(matches):
    flamengo = [m for m in matches if m.home_key == "flamengo"]
    assert flamengo
    # State suffix stripped for display.
    assert all("-RJ" not in m.home_team for m in flamengo)


def test_match_fields_parsed(matches):
    first = next(
        m for m in matches if m.competition == "Brasileirão" and m.round == "1"
        and m.home_key == "flamengo"
    )
    assert first.date == datetime.date(2019, 5, 19)
    assert first.home_goal == 2
    assert first.away_goal == 1
    assert first.season == 2019


def test_unplayed_match_has_none_goals(matches):
    unplayed = [m for m in matches if m.competition == "Copa Libertadores"
                and m.stage == "semifinals"]
    assert unplayed
    assert unplayed[0].home_goal is None


def test_winner_helper(matches):
    m = next(m for m in matches if m.home_goal == 2 and m.away_goal == 1
             and m.home_key == "flamengo" and m.competition == "Brasileirão")
    assert m.winner_key == m.home_key
    draw = next(m for m in matches if m.home_goal == 1 and m.away_goal == 1
                and m.competition == "Brasileirão")
    assert draw.winner_key is None


def test_historical_brasileirao_loaded(matches):
    guarani = [m for m in matches if m.home_key == "guarani"]
    assert guarani
    assert guarani[0].date == datetime.date(2003, 3, 29)
    assert guarani[0].competition == "Brasileirão"


# --- players -------------------------------------------------------------

def test_loads_players(players):
    assert len(players) == 4


def test_player_fields(players):
    neymar = next(p for p in players if p.name == "Neymar Jr")
    assert neymar.nationality == "Brazil"
    assert neymar.overall == 92
    assert neymar.club == "Paris Saint-Germain"
    assert neymar.position == "LW"


def test_player_club_key_normalized(players):
    gabigol = next(p for p in players if p.name == "Gabriel Barbosa")
    assert gabigol.club_key == "flamengo"


# --- real data smoke test ------------------------------------------------

def test_real_data_loads(real_data_dir):
    matches = data_loader.load_matches(real_data_dir)
    players = data_loader.load_players(real_data_dir)
    # Sanity: tens of thousands of matches, ~18k players.
    assert len(matches) > 20000
    assert len(players) > 18000
