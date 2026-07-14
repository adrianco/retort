"""BDD: team name normalization.

Feature: Team name normalization
  As an MCP consumer
  I want every spelling of a club to map to the same canonical key
  So that filters and joins work across the 5 match CSV files
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.normalize import normalize_team, teams_match


class TestStateSuffixVariations:
    """Scenario: ``Palmeiras-SP`` and ``Palmeiras`` mean the same club."""

    @pytest.mark.parametrize(
        "raw",
        ["Palmeiras", "Palmeiras-SP", "palmeiras", "  Palmeiras-sp  "],
    )
    def test_palmeiras_variants_collapse(self, raw: str) -> None:
        # Given a Palmeiras spelling
        # When we normalize it
        key = normalize_team(raw)
        # Then it produces the canonical key
        assert key == "palmeiras"


class TestAccentedNames:
    """Scenario: accents and ASCII forms collide cleanly."""

    def test_sao_paulo(self) -> None:
        assert normalize_team("São Paulo") == normalize_team("Sao Paulo") == "sao paulo"

    def test_gremio(self) -> None:
        assert normalize_team("Grêmio") == normalize_team("Gremio") == "gremio"


class TestStateAwareAmbiguousNames:
    """Scenario: ``Atlético-MG`` and ``Atlético-PR`` are different clubs."""

    def test_atletico_mineiro(self) -> None:
        assert normalize_team("Atlético-MG") == "atletico mineiro"
        assert normalize_team("Atletico Mineiro") == "atletico mineiro"

    def test_athletico_paranaense(self) -> None:
        assert normalize_team("Atlético-PR") == "athletico paranaense"
        assert normalize_team("Athletico-PR") == "athletico paranaense"

    def test_state_distinguishes_them(self) -> None:
        # The whole point of the state mapping
        assert normalize_team("Atlético-MG") != normalize_team("Atlético-PR")
        assert normalize_team("Atlético-MG") != normalize_team("Atlético-GO")


class TestAliases:
    """Scenario: nicknames map to the formal canonical key."""

    @pytest.mark.parametrize(
        "alias,canonical",
        [
            ("Galo", "atletico mineiro"),
            ("Flu", "fluminense"),
            ("Inter", "internacional"),
            ("Sport Club Corinthians Paulista", "corinthians"),
            ("Sport Club do Recife", "sport recife"),
        ],
    )
    def test_alias_maps_to_canonical(self, alias: str, canonical: str) -> None:
        assert normalize_team(alias) == canonical


class TestCountrySuffix:
    """Scenario: Libertadores opponents like 'Nacional (URU)' lose the country tag."""

    def test_country_suffix_stripped(self) -> None:
        assert normalize_team("Nacional (URU)") == "nacional"


class TestTeamsMatch:
    """Scenario: convenience equality check."""

    def test_two_spellings_match(self) -> None:
        assert teams_match("Palmeiras-SP", "Palmeiras")

    def test_unrelated_teams_do_not_match(self) -> None:
        assert not teams_match("Palmeiras", "Corinthians")

    def test_empty_inputs_do_not_match(self) -> None:
        # avoids the trap where normalize("") == normalize(None) == "" matching itself
        assert not teams_match("", "")
        assert not teams_match(None, None)
