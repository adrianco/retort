"""BDD: team-name normalization handles dataset variations.

Feature: Team name normalization
  Scenario: Same club, different naming conventions
    Given two raw team strings that refer to the same club
    When  I normalize both
    Then  they map to the same canonical name
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.team_utils import normalize_team_name, teams_match


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Palmeiras-SP", "palmeiras"),
        ("Palmeiras", "palmeiras"),
        ("São Paulo", "sao paulo"),
        ("São Paulo FC", "sao paulo"),
        ("Sao Paulo", "sao paulo"),
        ("Clube de Regatas do Flamengo", "flamengo"),
        ("Flamengo-RJ", "flamengo"),
        ("Atletico-MG", "atletico mineiro"),
        ("Atlético Mineiro", "atletico mineiro"),
        ("Atletico-PR", "athletico paranaense"),
        ("Athletico-PR", "athletico paranaense"),
        ("Atletico-GO", "atletico goianiense"),
        ("Sport Club Corinthians Paulista", "corinthians"),
        ("Sport-PE", "sport recife"),
        ("Fortaleza Esporte Clube", "fortaleza"),
        ("Esporte Clube Vitória", "vitoria"),
        ("Nacional (URU)", "nacional"),  # parenthetical country tag stripped
        ("", ""),
        (None, ""),
    ],
)
def test_canonical_normalization(raw, expected):
    # Given a raw club name
    # When  it is normalized
    # Then  it equals the expected canonical form
    assert normalize_team_name(raw) == expected


def test_two_atleticos_are_distinct():
    # Given Atlético MG and Atlético PR
    # When  we compare them
    # Then  they are NOT recognized as the same club
    assert not teams_match("Atletico-MG", "Atletico-PR")


def test_botafogo_pb_is_distinct_from_botafogo_rj():
    # Given the Botafogo from Paraíba and the Botafogo from Rio
    # When  we compare them
    # Then  they remain distinct
    assert not teams_match("Botafogo - PB", "Botafogo-RJ")


@pytest.mark.parametrize(
    "a,b",
    [
        ("Palmeiras-SP", "Sociedade Esportiva Palmeiras"),
        ("Flamengo-RJ", "Flamengo"),
        ("Clube de Regatas do Flamengo", "Flamengo-RJ"),
        ("São Paulo", "Sao Paulo FC"),
        ("Atlético - MG", "Clube Atletico Mineiro"),
    ],
)
def test_known_aliases_match(a, b):
    # Given two ways the same club is written
    # When  we compare them
    # Then  they are recognized as the same club
    assert teams_match(a, b)
