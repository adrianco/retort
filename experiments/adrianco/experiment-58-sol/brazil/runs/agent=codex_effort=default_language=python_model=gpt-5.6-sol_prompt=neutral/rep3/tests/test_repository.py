from __future__ import annotations

from datetime import datetime

from brazilian_soccer_mcp.normalize import normalize_team_name, parse_date


def test_given_all_csvs_when_repository_loads_then_every_dataset_is_queryable(repository):
    status = repository.status()
    assert status["all_datasets_loaded"] is True
    assert status["total_matches"] > 23_000
    assert status["total_players"] == 18_207
    assert all(count > 0 for count in status["rows_by_source"].values())


def test_given_team_variants_when_normalized_then_equivalent_names_match():
    assert normalize_team_name("Flamengo-RJ") == normalize_team_name("Flamengo")
    assert normalize_team_name("São Paulo - SP") == normalize_team_name("Sao Paulo FC")
    assert normalize_team_name("Sport Club Corinthians Paulista") == "corinthians"


def test_given_ambiguous_state_clubs_when_normalized_then_they_remain_distinct():
    assert normalize_team_name("Atlético-MG") == "atletico mineiro"
    assert normalize_team_name("Atletico-GO") == "atletico goianiense"
    assert normalize_team_name("Atlético-MG") != normalize_team_name("Atletico-GO")


def test_given_supported_date_formats_when_parsed_then_dates_are_consistent():
    expected = datetime(2003, 3, 29)
    assert parse_date("29/03/2003") == expected
    assert parse_date("2003-03-29") == expected
    assert parse_date("2003-03-29 00:00:00") == expected


def test_given_extended_rows_when_loaded_then_match_statistics_are_available(repository):
    extended = next(match for match in repository.matches if match.source == "BR-Football-Dataset.csv")
    assert "total_corners" in extended.statistics

