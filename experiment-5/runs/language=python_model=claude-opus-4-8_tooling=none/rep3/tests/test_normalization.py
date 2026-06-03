# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : tests.test_normalization
# Purpose : BDD (Given-When-Then) scenarios for the normalisation helpers that
#           underpin team-name and date matching across the messy multi-source
#           datasets. These are pure-function tests with no data dependency.
# =============================================================================

from soccer_mcp.normalize import (
    normalize_team,
    parse_date,
    strip_accents,
    team_matches,
)


class TestTeamNameNormalization:
    """Feature: Normalize team names across naming conventions."""

    def test_strips_state_suffix(self):
        # Given a team name with a state suffix
        # When it is normalised
        # Then the suffix is removed
        assert normalize_team("Palmeiras-SP") == "palmeiras"
        assert normalize_team("Flamengo-RJ") == "flamengo"

    def test_strips_country_suffix(self):
        # Given a name with a parenthesised country code
        assert normalize_team("Nacional (URU)") == "nacional"
        assert normalize_team("Barcelona-EQU") == "barcelona"

    def test_folds_accents(self):
        # Given names with Portuguese accents
        assert normalize_team("Grêmio") == "gremio"
        assert normalize_team("São Paulo") == normalize_team("Sao Paulo")

    def test_resolves_long_official_name(self):
        # Given a long official club name
        # Then it normalises to the common short key
        assert normalize_team("Sport Club Corinthians Paulista") == "corinthians"

    def test_loose_matching_is_symmetric(self):
        # Given a normalised candidate and a loose query
        assert team_matches("Flamengo", normalize_team("Flamengo-RJ"))
        assert team_matches("flamengo", "flamengo")


class TestAccentHelper:
    def test_strip_accents(self):
        assert strip_accents("Avaí") == "Avai"
        assert strip_accents("Atlético") == "Atletico"


class TestDateParsing:
    """Feature: Parse the multiple date formats in the datasets."""

    def test_iso_with_time(self):
        # Given an ISO datetime with a time component
        assert parse_date("2012-05-19 18:30:00") == "2012-05-19"

    def test_iso_date_only(self):
        assert parse_date("2023-09-24") == "2023-09-24"

    def test_brazilian_format(self):
        # Given a Brazilian DD/MM/YYYY date
        assert parse_date("29/03/2003") == "2003-03-29"

    def test_invalid_returns_none(self):
        assert parse_date("") is None
        assert parse_date("not-a-date") is None
