"""Unit tests for the normalization helpers."""

from datetime import date

from brazilian_soccer_mcp.normalize import (
    canonical_competition,
    clean_team_name,
    parse_date,
    team_key,
    text_key,
)


def test_strip_state_suffix():
    assert clean_team_name("Palmeiras-SP") == "Palmeiras"
    assert clean_team_name("América - MG") == "América"


def test_strip_parenthetical_qualifier():
    assert clean_team_name("Nacional (URU)") == "Nacional"


def test_team_key_folds_accents_and_suffix():
    assert team_key("São Paulo-SP") == team_key("Sao Paulo")
    assert team_key("Grêmio-RS") == "gremio"


def test_team_key_country_suffix():
    assert team_key("Barcelona-EQU") == "barcelona"


def test_canonical_competition_aliases():
    assert canonical_competition("Serie A") == "Brasileirão"
    assert canonical_competition("brasileirao") == "Brasileirão"
    assert canonical_competition("Libertadores") == "Copa Libertadores"
    assert canonical_competition("Copa do Brasil") == "Copa do Brasil"


def test_parse_iso_date():
    assert parse_date("2023-09-24") == date(2023, 9, 24)


def test_parse_iso_datetime_with_time():
    assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)


def test_parse_brazilian_date():
    assert parse_date("29/03/2003") == date(2003, 3, 29)


def test_parse_invalid_date_returns_none():
    assert parse_date("") is None
    assert parse_date("not-a-date") is None
    assert parse_date(None) is None


def test_text_key_folds_accents():
    assert text_key("São Paulo") == "sao paulo"
