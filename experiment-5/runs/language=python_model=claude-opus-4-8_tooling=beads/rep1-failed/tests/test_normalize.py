"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
File      : tests/test_normalize.py
Purpose   : BDD tests for the normalization layer (brazilian_soccer.normalize).

Covers the spec's "Data Quality Notes": team-name variations, multiple date
formats and UTF-8/accent handling. These are unit-level behaviours that the rest
of the system depends on, so they have no external fixtures.
================================================================================
"""

from datetime import date

from brazilian_soccer.normalize import (
    normalize_team_name,
    parse_date,
    strip_accents,
)


class TestTeamNameNormalization:
    def test_state_suffix_is_ignored(self):
        # Given two spellings of the same club that differ only by state suffix
        # When normalized
        # Then they produce the same key
        assert normalize_team_name("Palmeiras-SP") == normalize_team_name("Palmeiras")

    def test_accents_are_folded(self):
        # Given an accented and an unaccented spelling
        # Then they normalize identically
        assert normalize_team_name("Grêmio") == normalize_team_name("Gremio")

    def test_full_name_collapses_to_short_name(self):
        # Given a full club name with a generic club token
        # Then it matches the short suffixed form
        assert normalize_team_name("Ceará SC") == normalize_team_name("Ceara-CE")

    def test_alias_maps_renamed_club(self):
        # Given a club that was renamed across datasets
        # Then both names map to one key
        assert normalize_team_name("Red Bull Bragantino") == normalize_team_name(
            "Bragantino"
        )

    def test_ambiguous_atleticos_stay_distinct(self):
        # Given three different clubs that share the base name "Atlético"
        # Then they must NOT collapse into one key
        mg = normalize_team_name("Atletico-MG")
        pr = normalize_team_name("Athletico-PR")
        go = normalize_team_name("Atletico-GO")
        assert len({mg, pr, go}) == 3

    def test_athletico_pr_variants_match(self):
        # Given the many spellings of Athletico Paranaense
        # Then they all normalize to the same key
        keys = {
            normalize_team_name("Athletico-PR"),
            normalize_team_name("Atletico-PR"),
            normalize_team_name("Atletico Paranaense"),
        }
        assert len(keys) == 1


class TestDateParsing:
    def test_iso_date(self):
        assert parse_date("2023-09-24") == date(2023, 9, 24)

    def test_datetime_with_time(self):
        assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)

    def test_brazilian_format(self):
        assert parse_date("29/03/2003") == date(2003, 3, 29)

    def test_blank_returns_none(self):
        assert parse_date("") is None
        assert parse_date(None) is None


class TestAccents:
    def test_strip_accents(self):
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Avaí") == "Avai"
