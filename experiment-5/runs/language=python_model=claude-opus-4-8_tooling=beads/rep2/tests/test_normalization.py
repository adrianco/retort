"""
================================================================================
test_normalization.py - BDD scenarios for team-name & date normalisation
================================================================================

Feature: Data normalisation
  As a query engine consuming heterogeneous datasets
  I need team names and dates collapsed to canonical forms
  So that the same club/date matches across every file.
================================================================================
"""

import datetime

from brazilian_soccer_mcp.normalize import (
    normalize_team,
    parse_date,
    parse_int,
    team_display,
    teams_match,
)


class TestTeamNameNormalisation:
    def test_state_suffix_is_stripped(self):
        # Given two spellings of the same club differing only by state suffix
        # When both are normalised
        # Then they produce the same canonical key
        assert normalize_team("Palmeiras-SP") == normalize_team("Palmeiras")

    def test_accents_are_folded(self):
        # Given an accented and an un-accented spelling
        # Then they normalise identically
        assert normalize_team("São Paulo") == normalize_team("Sao Paulo-SP")

    def test_ambiguous_atletico_clubs_stay_distinct(self):
        # Given the three different "Atlético" clubs
        # Then each keeps a distinct canonical key
        mg = normalize_team("Atletico-MG")
        pr = normalize_team("Atletico-PR")
        go = normalize_team("Atletico-GO")
        assert len({mg, pr, go}) == 3

    def test_fifa_club_matches_match_data_team(self):
        # Given a FIFA club name and a match-file team name for the same club
        # Then they are recognised as the same team
        assert teams_match("Atlético Mineiro", "Atletico-MG")
        assert teams_match("Grêmio", "Gremio-RS")

    def test_country_code_suffix_is_handled(self):
        # Given a Libertadores team with a parenthetical country code
        # Then normalisation does not choke and strips the code
        assert normalize_team("Nacional (URU)") == "nacional"

    def test_display_name_keeps_accents(self):
        # Given a canonical club
        # Then its display name is nicely accented
        assert team_display("Sao Paulo-SP") == "São Paulo"
        assert team_display("Gremio-RS") == "Grêmio"


class TestDateParsing:
    def test_iso_with_time(self):
        assert parse_date("2012-05-19 18:30:00") == datetime.date(2012, 5, 19)

    def test_iso_plain(self):
        assert parse_date("2023-09-24") == datetime.date(2023, 9, 24)

    def test_brazilian_format(self):
        assert parse_date("29/03/2003") == datetime.date(2003, 3, 29)

    def test_empty_and_na_return_none(self):
        assert parse_date("") is None
        assert parse_date("NA") is None
        assert parse_date(None) is None


class TestIntParsing:
    def test_handles_float_strings(self):
        assert parse_int("3.0") == 3

    def test_handles_blanks(self):
        assert parse_int("") is None
        assert parse_int("NA") is None
