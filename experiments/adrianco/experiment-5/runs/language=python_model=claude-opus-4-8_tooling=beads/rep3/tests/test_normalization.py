"""
==============================================================================
File: tests/test_normalization.py
==============================================================================
CONTEXT
-------
BDD (Given-When-Then) tests for team-name normalization -- the trickiest part
of the dataset. Verifies that equivalent surface forms merge AND that genuinely
different clubs sharing a base name (Atlético-MG/PR/GO) stay separate.
==============================================================================
"""

import pytest

from brazilian_soccer.normalization import (
    display_name,
    fold_accents,
    names_match,
    normalize_team,
)


class TestSuffixStripping:
    def test_unambiguous_team_merges_across_suffix_forms(self):
        # Given a team that is unique by base name written with/without suffix
        # When normalized
        # Then both forms collapse to the same canonical key
        assert names_match("Flamengo-RJ", "Flamengo")
        assert names_match("Palmeiras-SP", "Palmeiras")

    def test_full_legal_name_maps_to_short_name(self):
        # Given the full legal club name
        # When normalized
        # Then it matches the common short name
        assert names_match("Sport Club Corinthians Paulista", "Corinthians")
        assert names_match("São Paulo FC", "São Paulo")


class TestAmbiguousTeams:
    @pytest.mark.parametrize(
        "a,b",
        [
            ("Atlético-MG", "Atlético-PR"),
            ("Atlético-MG", "Atlético-GO"),
            ("América-MG", "América-RN"),
        ],
    )
    def test_same_base_different_state_stay_distinct(self, a, b):
        # Given two different clubs distinguished only by state
        # When normalized
        # Then they DO NOT collapse together
        assert not names_match(a, b)

    def test_atletico_mineiro_full_name_matches_mg_suffix(self):
        # Given the FIFA-style full name and the match-data suffix form
        # When normalized
        # Then they resolve to the same club
        assert names_match("Atlético Mineiro", "Atlético-MG")

    def test_athletico_spelling_variant_unifies(self):
        # Given the "Athletico" vs "Atletico" spelling variants of Paranaense
        # When normalized
        # Then they match
        assert names_match("Athletico-PR", "Atletico-PR")


class TestAccentsAndDisplay:
    def test_accent_folding(self):
        # Given accented text
        # When folded
        # Then accents are removed
        assert fold_accents("São Grêmio Avaí") == "Sao Gremio Avai"

    def test_display_preserves_accents(self):
        # Given an accented suffixed name
        # When formatted for display
        # Then accents are preserved and suffix handled
        assert display_name("Palmeiras-SP") == "Palmeiras"
        assert display_name("Atlético-MG") == "Atlético-MG"
