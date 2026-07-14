"""
Context
=======
Feature: Data normalisation
Covers the "Data Quality Notes" section of TASK.md - team-name variations,
multiple date formats and UTF-8 / accented text - at the unit level, before the
higher-level query features rely on them.
"""

from __future__ import annotations

from datetime import date

from brazilian_soccer_mcp.normalize import (
    clean_team_name,
    extract_state,
    parse_date,
    parse_int,
    strip_accents,
    team_key,
)


class TestTeamNameNormalisation:
    def test_state_suffix_is_stripped_for_matching(self):
        # GIVEN the same club written with and without a state suffix
        # WHEN we compute their match keys
        # THEN they are equal
        assert team_key("Palmeiras-SP") == team_key("Palmeiras")
        assert team_key("Flamengo-RJ") == team_key("Flamengo")

    def test_accents_do_not_affect_matching(self):
        # GIVEN accented and unaccented spellings (São Paulo / Sao Paulo)
        # THEN the keys are equal
        assert team_key("São Paulo") == team_key("Sao Paulo")
        assert team_key("Grêmio") == team_key("Gremio")

    def test_spaced_suffix_and_parentheticals_are_handled(self):
        # GIVEN names like "América - MG" and "Nacional (URU)"
        assert clean_team_name("América - MG") == "América"
        assert clean_team_name("Nacional (URU)") == "Nacional"
        assert clean_team_name("Boavista Sport Club (antigo X) - RJ") == "Boavista Sport Club"

    def test_state_is_extracted_to_disambiguate_clubs(self):
        # GIVEN two clubs sharing a base name but different states
        # THEN the extracted state codes differ
        assert extract_state("Atletico-MG") == "mg"
        assert extract_state("Atletico-PR") == "pr"
        assert extract_state("Palmeiras") == ""
        # A parenthetical country code is NOT a suffix.
        assert extract_state("Nacional (URU)") == ""

    def test_strip_accents(self):
        assert strip_accents("Avaí") == "Avai"
        assert strip_accents("Fortaleza") == "Fortaleza"


class TestDateNormalisation:
    def test_iso_format(self):
        assert parse_date("2023-09-24") == date(2023, 9, 24)

    def test_iso_with_time(self):
        assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)

    def test_brazilian_format(self):
        assert parse_date("29/03/2003") == date(2003, 3, 29)

    def test_empty_and_invalid_return_none(self):
        assert parse_date("") is None
        assert parse_date(None) is None
        assert parse_date("not a date") is None


class TestIntNormalisation:
    def test_parses_float_strings(self):
        # BR-Football stores goals as "1.0"
        assert parse_int("1.0") == 1
        assert parse_int("3") == 3
        assert parse_int(2) == 2

    def test_empty_returns_none(self):
        assert parse_int("") is None
        assert parse_int(None) is None
