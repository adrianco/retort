"""Tests that every provided CSV loads and is parsed correctly.

Context
-------
The specification's data-coverage criterion is "all 6 CSV files are loadable
and queryable".  Each loader is exercised against the real file, with row
counts pinned to the numbers quoted in the specification.
"""

from __future__ import annotations

import datetime as dt

import pytest

from brazilian_soccer.loaders import (
    SOURCES,
    load_br_football,
    load_brasileirao,
    load_copa_do_brasil,
    load_historical_brasileirao,
    load_libertadores,
    load_players,
)

#: Row counts quoted in the specification.
EXPECTED_ROWS = {
    "Brasileirao_Matches.csv": 4180,
    "Brazilian_Cup_Matches.csv": 1337,
    "Libertadores_Matches.csv": 1255,
    "BR-Football-Dataset.csv": 10296,
    "novo_campeonato_brasileiro.csv": 6886,
    "fifa_data.csv": 18207,
}


def test_all_six_source_files_are_declared():
    assert len(SOURCES) == 6
    assert {source.filename for source in SOURCES} == set(EXPECTED_ROWS)


def test_every_source_file_exists(data_dir):
    for source in SOURCES:
        assert (data_dir / source.filename).is_file(), source.filename


@pytest.mark.parametrize("filename", sorted(EXPECTED_ROWS))
def test_row_counts_match_the_specification(data_dir, filename):
    source = next(s for s in SOURCES if s.filename == filename)
    rows = source.loader(data_dir)
    assert len(rows) == EXPECTED_ROWS[filename]


def test_brasileirao_loader(data_dir):
    matches = load_brasileirao(data_dir)
    seasons = {m.season for m in matches}
    assert seasons == set(range(2012, 2023))
    assert all(m.competition == "serie-a" for m in matches)
    assert all(m.round for m in matches)
    first = min(matches, key=lambda m: (m.date, m.match_id))
    assert first.date == dt.date(2012, 5, 19)
    assert all(m.sources == ("Brasileirao_Matches.csv",) for m in matches)


def test_historical_loader_parses_brazilian_dates_and_stadiums(data_dir):
    matches = load_historical_brasileirao(data_dir)
    assert {m.season for m in matches} == set(range(2003, 2020))
    assert any(m.venue == "Maracanã" for m in matches)
    sample = next(m for m in matches if m.match_id == "hist-00000")
    assert sample.date == dt.date(2003, 3, 29)
    assert sample.home_slug == "guarani" and sample.away_slug == "vasco-da-gama"
    assert sample.home_goals == 4 and sample.away_goals == 2


def test_copa_do_brasil_loader_labels_the_knockout_ladder(data_dir):
    matches = load_copa_do_brasil(data_dir)
    finals = [m for m in matches if m.stage == "Final"]
    # Nine completed editions (2012-2020), each with a two-legged final.
    assert len(finals) == 18
    assert {m.season for m in finals} == set(range(2012, 2021))
    assert all(m.competition == "copa-do-brasil" for m in matches)
    semis = [m for m in matches if m.stage == "Semifinals"]
    assert len(semis) == 9 * 4


def test_libertadores_loader_keeps_stages_and_foreign_clubs(data_dir):
    matches = load_libertadores(data_dir)
    stages = {m.stage for m in matches}
    assert {"Group stage", "Round of 16", "Quarterfinals", "Semifinals",
            "Final"} <= stages
    assert any(m.home_slug == "boca-juniors" for m in matches)
    # One row in this file has no date and no score.
    assert any(not m.played for m in matches)


def test_br_football_loader_extracts_extended_statistics(data_dir):
    matches = load_br_football(data_dir)
    competitions = {m.competition for m in matches}
    assert competitions == {"serie-a", "serie-b", "serie-c", "copa-do-brasil"}
    with_stats = [m for m in matches if m.stats]
    assert len(with_stats) > 9000
    sample = with_stats[0]
    assert {"home", "away"} <= set(sample.stats)
    assert "corners" in sample.stats["home"]


def test_br_football_season_inference_handles_the_covid_calendar(data_dir):
    """The 2020 Série A finished in February 2021; those rows are season 2020."""
    matches = load_br_football(data_dir)
    february_2021 = [m for m in matches
                     if m.competition == "serie-a" and m.date
                     and m.date.year == 2021 and m.date.month == 2]
    assert february_2021
    assert all(m.season == 2020 for m in february_2021)


def test_player_loader(data_dir):
    players = load_players(data_dir)
    assert len(players) == 18207
    messi = next(p for p in players if p.player_id == 158023)
    assert messi.name == "L. Messi" and messi.overall == 94
    assert messi.skills["Dribbling"] == 97
    neymar = next(p for p in players if p.name == "Neymar Jr")
    assert neymar.is_brazilian and neymar.position == "LW"
    assert neymar.club_slug == "paris-saint-germain"


def test_player_position_groups(data_dir):
    players = load_players(data_dir)
    by_name = {p.name: p for p in players}
    assert by_name["Neymar Jr"].position_group == "FWD"
    assert by_name["Casemiro"].position_group == "MID"
    assert by_name["Marcelo"].position_group == "DEF"
    assert by_name["Alisson"].position_group == "GK"
