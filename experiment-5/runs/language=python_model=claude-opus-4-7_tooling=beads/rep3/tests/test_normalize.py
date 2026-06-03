"""BDD-style tests for the team-name normalizer.

Feature: Canonical team-name keys
  In order to match team references across heterogeneous datasets
  Equivalent variants of a name should produce equal canonical keys
  And distinct clubs in different states should never collide.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.normalize import (
    normalize_team_name,
    strip_state_suffix,
    team_query_matches,
)


class TestNormalizeTeamName:
    # Scenario: stripping state suffix and accents from common Brasileirão clubs
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Palmeiras-SP", "palmeiras sp"),
            ("Flamengo-RJ", "flamengo rj"),
            ("São Paulo-SP", "sao paulo sp"),
            ("Grêmio-RS", "gremio rs"),
            ("Avaí-SC", "avai sc"),
            ("Flamengo", "flamengo"),
            ("  ", ""),
            (None, ""),
        ],
    )
    def test_returns_canonical_key(self, raw, expected):
        # When: the value is normalized
        result = normalize_team_name(raw)
        # Then: it matches the expected canonical form
        assert result == expected

    def test_distinct_state_clubs_stay_distinct(self):
        # Given: two real clubs in different states
        # When: both are normalized
        # Then: the keys differ so head-to-head queries don't merge them
        assert normalize_team_name("Atletico-MG") != normalize_team_name("Athletico-PR")

    def test_paranaense_spelling_variants_collapse(self):
        # Athletico Paranaense is sometimes spelt with and without the 'h'.
        assert normalize_team_name("Atletico-PR") == normalize_team_name("Athletico-PR")

    def test_long_form_aliases_collapse_to_short(self):
        assert normalize_team_name("Sport Club Corinthians Paulista") == "corinthians"
        assert normalize_team_name("Clube de Regatas do Flamengo") == "flamengo"

    def test_libertadores_country_suffix_is_dropped(self):
        # "Nacional (URU)" should canonicalize to "nacional uru"
        assert normalize_team_name("Nacional (URU)") == "nacional uru"


class TestStripStateSuffix:
    def test_strips_state(self):
        assert strip_state_suffix("palmeiras sp") == "palmeiras"

    def test_leaves_short_name_alone(self):
        assert strip_state_suffix("flamengo") == "flamengo"

    def test_handles_empty(self):
        assert strip_state_suffix("") == ""


class TestTeamQueryMatches:
    def test_query_without_state_matches_full_form(self):
        full = normalize_team_name("Palmeiras-SP")
        short = strip_state_suffix(full)
        assert team_query_matches("Palmeiras", full, short)

    def test_state_qualified_query_requires_exact(self):
        full = normalize_team_name("Atletico-MG")
        short = strip_state_suffix(full)
        assert team_query_matches("Atletico-MG", full, short)
        # A state-qualified query for the wrong state should not match.
        other_full = normalize_team_name("Athletico-PR")
        other_short = strip_state_suffix(other_full)
        assert not team_query_matches("Atletico-MG", other_full, other_short)
