"""
Unit tests for the CSV readers.

Context
-------
"All 6 CSV files are loadable and queryable" is an explicit success criterion in
TASK.md.  These tests assert the exact row counts the specification quotes, the
per-file quirks each reader has to absorb, and the derived fields (Copa do
Brasil knockout stage names, the league season of a February fixture).
"""

from __future__ import annotations

import datetime as dt

import pytest

from brazilian_soccer import loaders
from brazilian_soccer.config import DATASETS, dataset_path
from brazilian_soccer.teams import TeamRegistry

#: Row counts quoted in TASK.md for each provided dataset.
EXPECTED_ROWS = {
    "brasileirao": 4180,
    "copa_do_brasil": 1337,
    "libertadores": 1255,
    "br_football": 10296,
    "historical_brasileirao": 6886,
    "fifa_players": 18207,
}


@pytest.fixture(scope="module")
def parsed_rows():
    return loaders.read_all_match_rows()


def test_every_required_csv_is_present():
    missing = [spec.filename for spec in DATASETS if not dataset_path(spec.key).exists()]
    assert missing == []


@pytest.mark.parametrize("key", sorted(k for k in EXPECTED_ROWS if k != "fifa_players"))
def test_match_files_have_the_documented_row_count(parsed_rows, key):
    assert len(parsed_rows[key]) == EXPECTED_ROWS[key]


def test_player_file_has_the_documented_row_count(graph):
    assert len(graph.players) == EXPECTED_ROWS["fifa_players"]


def test_brasileirao_rows_carry_state_hints(parsed_rows):
    row = parsed_rows["brasileirao"][0]
    assert row.competition_id == "serie-a"
    assert row.home_state and row.away_state
    assert row.date == dt.date(2012, 5, 19)
    assert row.kickoff == "18:30"


def test_historical_brasileirao_parses_brazilian_dates_and_venues(parsed_rows):
    row = parsed_rows["historical_brasileirao"][0]
    assert row.date == dt.date(2003, 3, 29)
    assert row.season == 2003
    assert row.venue == "Brinco de Ouro"


def test_copa_do_brasil_tolerates_missing_scores(parsed_rows):
    rows = parsed_rows["copa_do_brasil"]
    unscored = [row for row in rows if row.home_goals is None]
    assert unscored, "the cup file is known to contain NA scores"
    assert all(row.away_goals is None for row in unscored)


def test_copa_do_brasil_rounds_are_named(parsed_rows):
    rows = [row for row in parsed_rows["copa_do_brasil"] if row.season == 2019]
    stages = {row.stage for row in rows}
    assert {"final", "semifinals", "quarterfinals", "round of 16"} <= stages
    finals = [row for row in rows if row.stage == "final"]
    assert len(finals) == 2, "the 2019 final was played over two legs"


def test_incomplete_cup_season_does_not_invent_a_final(parsed_rows):
    """The 2021 cup file stops after the round of 16 -- do not call it a final."""

    rows = [row for row in parsed_rows["copa_do_brasil"] if row.season == 2021]
    assert rows, "2021 rows should be present"
    assert "final" not in {row.stage for row in rows}
    assert "round of 16" in {row.stage for row in rows}


def test_libertadores_keeps_its_explicit_stages(parsed_rows):
    stages = {row.stage for row in parsed_rows["libertadores"]}
    assert {"group stage", "round of 16", "quarterfinals", "semifinals", "final"} <= stages


def test_libertadores_row_with_no_data_is_kept_but_unscored(parsed_rows):
    broken = [row for row in parsed_rows["libertadores"] if row.date is None]
    assert len(broken) == 1
    assert broken[0].home_goals is None and broken[0].away_goals is None


def test_br_football_carries_extended_statistics(parsed_rows):
    rows = [row for row in parsed_rows["br_football"] if row.stats]
    assert rows
    stats = rows[0].stats
    assert "home_corners" in stats and "away_corners" in stats
    assert "home_shots" in stats or "away_shots" in stats


def test_br_football_maps_tournaments_to_competitions(parsed_rows):
    competitions = {row.competition_id for row in parsed_rows["br_football"]}
    assert competitions == {"serie-a", "serie-b", "serie-c", "copa-do-brasil"}


@pytest.mark.parametrize(
    "competition_id, date, expected_season",
    [
        ("serie-a", dt.date(2021, 2, 25), 2020),
        ("serie-a", dt.date(2021, 1, 20), 2020),
        ("serie-a", dt.date(2021, 5, 30), 2021),
        ("serie-b", dt.date(2021, 1, 30), 2020),
        ("copa-do-brasil", dt.date(2021, 2, 25), 2021),
        ("copa-do-brasil", dt.date(2021, 3, 3), 2021),
    ],
)
def test_league_seasons_that_run_into_the_new_year(competition_id, date, expected_season):
    assert loaders._br_football_season(competition_id, date) == expected_season


def test_load_matches_resolves_both_clubs(parsed_rows):
    registry = TeamRegistry()
    rejected: list = []
    matches = loaders.load_matches(registry, parsed_rows, rejected=rejected)
    assert len(matches) + len(rejected) == sum(len(rows) for rows in parsed_rows.values())
    assert all(match.home_team_id and match.away_team_id for match in matches)
    assert all(match.home_team_id != match.away_team_id for match in matches)


def test_rows_where_a_club_plays_itself_are_rejected(parsed_rows):
    """The cup file lists "Bragantino - PA" as both sides of two 2019 ties."""

    registry = TeamRegistry()
    rejected: list = []
    loaders.load_matches(registry, parsed_rows, rejected=rejected)
    assert len(rejected) == 2
    assert all(row.home_raw == row.away_raw for row in rejected)


def test_players_have_skills_and_ratings(graph):
    neymar = next(p for p in graph.players if p.name == "Neymar Jr")
    assert neymar.overall == 92
    assert neymar.nationality == "Brazil"
    assert neymar.position == "LW"
    assert neymar.skills["Dribbling"] >= 90
    assert len(neymar.skills) >= 30


def test_position_groups_cover_every_fifa_position(graph):
    positions = {p.position for p in graph.players if p.position}
    ungrouped = {p for p in positions if loaders.position_group(p) is None}
    assert ungrouped == set(), f"positions without a group: {sorted(ungrouped)}"
