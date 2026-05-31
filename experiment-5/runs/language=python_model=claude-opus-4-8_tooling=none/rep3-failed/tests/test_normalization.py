"""Unit tests for name/date normalization (Given-When-Then style)."""

import datetime

import pytest

from brazilian_soccer_mcp.normalize import (
    canonical_competition,
    competition_matches,
    normalize_team,
    parse_date,
    parse_int,
    strip_accents,
    team_key,
)


def test_strip_accents_removes_diacritics():
    # Given accented Portuguese text / When stripped / Then ASCII results
    assert strip_accents("Grêmio") == "Gremio"
    assert strip_accents("São Paulo") == "Sao Paulo"
    assert strip_accents("Avaí") == "Avai"


@pytest.mark.parametrize("raw,expected", [
    ("Palmeiras-SP", "palmeiras"),
    ("Palmeiras", "palmeiras"),
    ("Flamengo-RJ", "flamengo"),
    ("Grêmio", "gremio"),
    ("São Paulo", "sao paulo"),
    ("Sport Club Corinthians Paulista", "corinthians"),
])
def test_team_key_normalizes_variants(raw, expected):
    assert team_key(raw) == expected


def test_team_key_keeps_ambiguous_state_suffix():
    # Given clubs that share a base name / When keyed / Then state distinguishes
    assert team_key("Atlético-MG") != team_key("Atlético-PR")
    assert team_key("Atlético-MG") == "atletico-mg"
    assert team_key("America - MG") == "america-mg"   # dash-with-spaces form


def test_team_key_handles_spelling_variants():
    assert team_key("Athletico-PR") == team_key("Atletico-PR")


def test_team_key_strips_parenthetical_country():
    assert team_key("Nacional (URU)") == "nacional"


def test_normalize_team_preserves_accents():
    assert normalize_team("São Paulo-SP") == "São Paulo"
    assert normalize_team("Grêmio") == "Grêmio"


@pytest.mark.parametrize("raw,expected", [
    ("2023-09-24", datetime.date(2023, 9, 24)),
    ("2012-05-19 18:30:00", datetime.date(2012, 5, 19)),
    ("29/03/2003", datetime.date(2003, 3, 29)),
])
def test_parse_date_handles_multiple_formats(raw, expected):
    assert parse_date(raw) == expected


def test_parse_date_returns_none_on_garbage():
    assert parse_date("") is None
    assert parse_date("not a date") is None


def test_parse_int_tolerates_floats_and_blanks():
    assert parse_int("3") == 3
    assert parse_int("3.0") == 3
    assert parse_int("") is None
    assert parse_int(None) is None


def test_canonical_competition():
    assert canonical_competition("Brasileirão") == "Brasileirão Série A"
    assert canonical_competition("serie a") == "Brasileirão Série A"
    assert canonical_competition("Brazil Cup") == "Copa do Brasil"
    assert canonical_competition("Libertadores") == "Copa Libertadores"
    assert canonical_competition("nonsense competition") is None


def test_competition_matches_is_precise():
    # "Brasileirão" must not leak into Série B
    assert competition_matches("Brasileirão", "Brasileirão Série A")
    assert not competition_matches("Brasileirão", "Brasileirão Série B")
