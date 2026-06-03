"""
================================================================================
Feature: Team name normalization
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
BDD (Given/When/Then) tests for ``normalize.normalize_key`` — the function that
collapses the many naming conventions in the datasets onto one key per club.
================================================================================
"""

import pytest

from normalize import normalize_key, canonical_name, strip_accents


class TestStateSuffixNormalization:
    """Feature: collapse state-suffix variants onto one key."""

    @pytest.mark.parametrize("raw", ["Palmeiras", "Palmeiras-SP", "palmeiras SP"])
    def test_state_suffix_is_stripped_for_unique_clubs(self, raw):
        # Given a club whose base name is unique across states
        # When the name is normalized
        # Then the state suffix is dropped and all forms share one key
        assert normalize_key(raw) == "palmeiras"

    def test_flamengo_variants_collapse(self):
        # Given several spellings of Flamengo
        # Then they all normalize to the same key
        assert normalize_key("Flamengo-RJ") == normalize_key("Flamengo") == "flamengo"


class TestAccentAndEncoding:
    """Feature: handle UTF-8 Portuguese accents."""

    def test_strip_accents(self):
        # Given accented Portuguese text
        # Then diacritics are removed
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Grêmio") == "Gremio"

    def test_accented_and_ascii_forms_match(self):
        # Given accented and ASCII spellings of the same club
        # Then they normalize identically
        assert normalize_key("São Paulo") == normalize_key("Sao Paulo FC") == "sao paulo"
        assert normalize_key("Grêmio") == normalize_key("Gremio") == "gremio"


class TestAmbiguousBaseDisambiguation:
    """Feature: clubs sharing a base name are kept distinct by state."""

    def test_atletico_variants_resolve_by_state(self):
        # Given the three different Atlético clubs in assorted spellings
        # Then each resolves to a distinct state-qualified key
        assert normalize_key("Atletico Mineiro") == normalize_key("Atletico-MG") == "atletico mg"
        assert normalize_key("Athletico Paranaense") == normalize_key("Athletico-PR") == "atletico pr"
        assert normalize_key("Atletico Goianiense") == normalize_key("Atletico-GO") == "atletico go"

    def test_different_atleticos_are_not_confused(self):
        # Then Mineiro and Paranaense are NOT the same entity
        assert normalize_key("Atletico Mineiro") != normalize_key("Atletico Paranaense")

    def test_country_code_clubs(self):
        # Given Libertadores opponents with country codes
        # Then the code disambiguates them
        assert normalize_key("Nacional (URU)") == "nacional uru"
        assert normalize_key("Nacional (URU)") != normalize_key("Nacional (PAR)")

    def test_vasco_da_gama_collapses(self):
        # Given "Vasco da Gama" and the short form "Vasco"
        # Then both collapse to one key
        assert normalize_key("Vasco da Gama") == normalize_key("Vasco") == "vasco"


class TestCanonicalDisplayName:
    def test_canonical_name_is_human_readable(self):
        # Given a raw club name
        # When asking for a display label
        # Then it is title-cased with the state code upper-cased
        assert canonical_name("atletico-mg") == "Atletico MG"
        assert canonical_name("São Paulo") == "Sao Paulo"

    def test_empty_input(self):
        # Given empty/None input
        # Then normalization yields empty values rather than raising
        assert normalize_key("") == ""
        assert normalize_key(None) == ""
        assert canonical_name(None) == ""
