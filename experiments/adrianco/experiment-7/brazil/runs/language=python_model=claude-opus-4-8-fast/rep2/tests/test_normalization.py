"""
================================================================================
Module: tests.test_normalization
--------------------------------------------------------------------------------
Context:
    Unit-level BDD tests for the pure normalization helpers — the foundation the
    whole knowledge graph relies on (TASK.md "Data Quality Notes": team-name
    variations, multiple date formats, UTF-8 accents).

Responsibility:
    Verify accent handling, suffix-aware team identity, suffix-tolerant matching
    and multi-format date/int parsing in isolation (no dataset required).
================================================================================
"""

from datetime import date

from brazilian_soccer_mcp.normalize import (
    base_key,
    clean_team_name,
    names_match,
    parse_date,
    parse_int,
    strip_accents,
    team_key,
    team_suffix,
)


class TestTeamNameNormalization:
    def test_strip_accents_removes_diacritics(self):
        # GIVEN accented Portuguese names WHEN stripped THEN ASCII remains
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Grêmio") == "Gremio"
        assert strip_accents("Avaí") == "Avai"

    def test_clean_team_name_canonicalises_suffix(self):
        # GIVEN varied suffix spellings WHEN cleaned THEN a single canonical form
        assert clean_team_name("Palmeiras-SP") == "Palmeiras-SP"
        assert clean_team_name("América - MG") == "América-MG"
        assert clean_team_name('  "Flamengo" ') == "Flamengo"

    def test_team_key_is_accent_insensitive(self):
        # GIVEN the same club spelt two ways THEN keys are equal
        assert team_key("Atlético-MG") == team_key("Atletico-MG") == "atletico-mg"

    def test_distinct_clubs_keep_distinct_keys(self):
        # GIVEN same base name but different states THEN keys differ (disambiguation)
        assert team_key("Atlético-MG") != team_key("Atlético-GO")
        assert team_key("América-MG") != team_key("América-RN")

    def test_suffix_extraction(self):
        assert team_suffix("Palmeiras-SP") == "SP"
        assert team_suffix("Nacional (URU)") == "URU"
        assert team_suffix("Flamengo") is None

    def test_base_key_drops_suffix(self):
        assert base_key("Palmeiras-SP") == "palmeiras"
        assert base_key("Nacional (URU)") == "nacional"


class TestNameMatching:
    def test_suffixless_query_matches_suffixed_team(self):
        # GIVEN a user types "Palmeiras" THEN it matches "Palmeiras-SP"
        assert names_match("Palmeiras", "Palmeiras-SP")

    def test_accent_insensitive_match(self):
        assert names_match("Sao Paulo", "São Paulo-SP")

    def test_long_official_name_matches_short_query(self):
        assert names_match("Corinthians", "Sport Club Corinthians Paulista")

    def test_explicit_suffix_does_not_cross_match(self):
        # GIVEN an explicit "-MG" THEN it must NOT match a "-GO" club
        assert not names_match("Atlético-MG", "Atlético-GO")

    def test_unrelated_teams_do_not_match(self):
        assert not names_match("Flamengo", "Fluminense")


class TestDateParsing:
    def test_iso_datetime(self):
        assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)

    def test_iso_date(self):
        assert parse_date("2023-09-24") == date(2023, 9, 24)

    def test_brazilian_format(self):
        assert parse_date("29/03/2003") == date(2003, 3, 29)

    def test_unparseable_returns_none(self):
        assert parse_date("not-a-date") is None
        assert parse_date("") is None


class TestIntParsing:
    def test_quoted_and_float_scores(self):
        assert parse_int('"2"') == 2
        assert parse_int("1.0") == 1
        assert parse_int(3) == 3

    def test_missing_returns_none(self):
        assert parse_int("") is None
        assert parse_int("nan") is None
        assert parse_int(None) is None
