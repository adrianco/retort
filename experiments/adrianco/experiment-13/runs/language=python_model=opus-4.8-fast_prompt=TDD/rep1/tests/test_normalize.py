"""Tests for team-name, date and score normalization helpers."""
import datetime

import pytest

from brazilian_soccer import normalize


# --- strip_accents -------------------------------------------------------

def test_strip_accents_removes_diacritics():
    assert normalize.strip_accents("São Paulo") == "Sao Paulo"
    assert normalize.strip_accents("Grêmio") == "Gremio"
    assert normalize.strip_accents("Avaí") == "Avai"


# --- normalize_team_name (display form) ----------------------------------

def test_strips_state_suffix():
    assert normalize.normalize_team_name("Palmeiras-SP") == "Palmeiras"
    assert normalize.normalize_team_name("Flamengo-RJ") == "Flamengo"


def test_strips_spaced_state_suffix():
    assert normalize.normalize_team_name("América - MG") == "América"


def test_strips_country_parenthetical():
    assert normalize.normalize_team_name("Nacional (URU)") == "Nacional"
    assert normalize.normalize_team_name("Barcelona-EQU") == "Barcelona"


def test_known_full_name_maps_to_short_name():
    assert (
        normalize.normalize_team_name("Sport Club Corinthians Paulista")
        == "Corinthians"
    )


def test_plain_name_unchanged():
    assert normalize.normalize_team_name("Santos") == "Santos"


# --- team_key (matching form) --------------------------------------------

def test_team_key_is_accent_and_case_insensitive():
    assert normalize.team_key("São Paulo") == normalize.team_key("sao paulo")


def test_team_key_ignores_state_suffix():
    assert normalize.team_key("Palmeiras-SP") == normalize.team_key("Palmeiras")


def test_team_key_matches_full_and_short_name():
    assert normalize.team_key("Sport Club Corinthians Paulista") == normalize.team_key(
        "Corinthians"
    )


def test_team_key_strips_club_type_tokens():
    assert normalize.team_key("Cuiaba FC") == normalize.team_key("Cuiaba")
    assert normalize.team_key("EC Juventude") == normalize.team_key("Juventude")
    assert normalize.team_key("Fortaleza FC") == normalize.team_key("Fortaleza")


def test_team_key_strips_trailing_state_word():
    assert normalize.team_key("Botafogo RJ") == normalize.team_key("Botafogo")
    assert normalize.team_key("America MG") == normalize.team_key("America")


def test_team_key_keeps_distinct_teams_distinct():
    assert normalize.team_key("Flamengo") != normalize.team_key("Fluminense")
    # Don't collapse a club-type-only-ish name to empty.
    assert normalize.team_key("Sport") != ""


# --- parse_date ----------------------------------------------------------

def test_parse_iso_date():
    assert normalize.parse_date("2023-09-24") == datetime.date(2023, 9, 24)


def test_parse_iso_datetime():
    assert normalize.parse_date("2012-05-19 18:30:00") == datetime.date(2012, 5, 19)


def test_parse_brazilian_date():
    assert normalize.parse_date("29/03/2003") == datetime.date(2003, 3, 29)


def test_parse_date_handles_blank():
    assert normalize.parse_date("") is None
    assert normalize.parse_date(None) is None


# --- parse_goal ----------------------------------------------------------

def test_parse_goal_int_and_float_strings():
    assert normalize.parse_goal("3") == 3
    assert normalize.parse_goal("1.0") == 1
    assert normalize.parse_goal(2) == 2


def test_parse_goal_unplayed_returns_none():
    assert normalize.parse_goal("-") is None
    assert normalize.parse_goal("") is None
    assert normalize.parse_goal(None) is None
