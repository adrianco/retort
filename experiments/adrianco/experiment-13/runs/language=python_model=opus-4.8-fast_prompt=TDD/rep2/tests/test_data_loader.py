"""Tests for loading the Kaggle CSVs into normalized records."""

import datetime as dt

import pytest

from brazilian_soccer.data_loader import (
    DATA_DIR,
    Match,
    Player,
    load_all_matches,
    load_players,
    parse_date,
    parse_int,
)


def test_parse_int_handles_floats_and_blanks():
    assert parse_int("3") == 3
    assert parse_int("2.0") == 2
    assert parse_int("") is None
    assert parse_int(None) is None
    assert parse_int("x") is None


def test_parse_date_handles_multiple_formats():
    assert parse_date("2012-05-19 18:30:00") == dt.date(2012, 5, 19)
    assert parse_date("2023-09-24") == dt.date(2023, 9, 24)
    assert parse_date("29/03/2003") == dt.date(2003, 3, 29)
    assert parse_date("") is None


def test_match_winner_property():
    home = Match(competition="X", season=2020, date=None, round=None, stage=None,
                 home_team="A", away_team="B", home_goal=2, away_goal=1)
    draw = Match(competition="X", season=2020, date=None, round=None, stage=None,
                 home_team="A", away_team="B", home_goal=1, away_goal=1)
    away = Match(competition="X", season=2020, date=None, round=None, stage=None,
                 home_team="A", away_team="B", home_goal=0, away_goal=3)
    unknown = Match(competition="X", season=2020, date=None, round=None, stage=None,
                    home_team="A", away_team="B", home_goal=None, away_goal=None)
    assert home.winner == "home"
    assert draw.winner == "draw"
    assert away.winner == "away"
    assert unknown.winner is None


def test_match_normalized_keys_are_populated():
    m = Match(competition="X", season=2020, date=None, round=None, stage=None,
              home_team="Palmeiras-SP", away_team="São Paulo", home_goal=1, away_goal=0)
    assert m.home_key == "palmeiras"
    assert m.away_key == "sao paulo"


# ---- Integration with the real data directory -----------------------------

@pytest.fixture(scope="session")
def matches():
    return load_all_matches(DATA_DIR)


@pytest.fixture(scope="session")
def players():
    return load_players(DATA_DIR / "fifa_data.csv")


def test_load_all_matches_covers_every_file(matches):
    # Every source file contributes at least some rows (overlapping Brasileirão
    # seasons are de-duplicated, so the total is below the raw row sum).
    sources = {m.source for m in matches}
    assert sources == {
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
    }
    competitions = {m.competition for m in matches}
    assert "Brasileirão" in competitions
    assert "Copa do Brasil" in competitions
    assert "Copa Libertadores" in competitions


def test_loaded_matches_have_normalized_keys(matches):
    assert all(m.home_key and m.away_key for m in matches)


def test_brasileirao_season_not_double_counted(matches):
    # The two Brasileirão sources overlap on 2012-2019; each (season) must be
    # served by exactly one source file so standings are not double-counted.
    seasons_sources = {}
    for mt in matches:
        if mt.competition == "Brasileirão" and mt.season:
            seasons_sources.setdefault(mt.season, set()).add(mt.source)
    assert all(len(s) == 1 for s in seasons_sources.values())
    # A modern 20-team season has 380 matches (single source, no duplication).
    s2019 = [mt for mt in matches
             if mt.competition == "Brasileirão" and mt.season == 2019]
    assert len(s2019) == 380


def test_known_brasileirao_match_present(matches):
    # First row of Brasileirao_Matches.csv
    hits = [m for m in matches
            if m.competition == "Brasileirão" and m.season == 2012
            and m.date == dt.date(2012, 5, 19)
            and m.home_key == "palmeiras" and m.away_key == "portuguesa"]
    assert any(m.home_goal == 1 and m.away_goal == 1 for m in hits)


def test_load_players_count_and_fields(players):
    assert len(players) == 18207
    messi = next(p for p in players if p.name == "L. Messi")
    assert messi.nationality == "Argentina"
    assert messi.overall == 94
    assert messi.club == "FC Barcelona"


def test_players_include_brazilians(players):
    brazilians = [p for p in players if p.nationality == "Brazil"]
    assert len(brazilians) > 100
