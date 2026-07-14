"""Tests for team-name normalization (the data-quality backbone)."""

from normalization import (
    clean_display_name,
    normalize_team_name,
    strip_accents,
    team_matches,
)


def test_strip_accents():
    assert strip_accents("São Paulo") == "Sao Paulo"
    assert strip_accents("Grêmio") == "Gremio"
    assert strip_accents("Avaí") == "Avai"


def test_normalize_handles_state_suffix_variations():
    # All three spellings of the same club collapse to one key.
    assert normalize_team_name("Palmeiras-SP") == "palmeiras sp"
    assert normalize_team_name("Palmeiras - SP") == "palmeiras sp"
    assert normalize_team_name("Palmeiras SP") == "palmeiras sp"


def test_normalize_accent_and_case_insensitive():
    assert normalize_team_name("São Paulo") == normalize_team_name("Sao Paulo")
    assert normalize_team_name("Grêmio-RS") == normalize_team_name("Gremio RS")


def test_normalize_strips_country_parenthetical():
    assert normalize_team_name("Nacional (URU)") == "nacional"
    assert normalize_team_name("Barcelona-EQU") == "barcelona equ"  # not a BR state


def test_state_suffix_is_retained_to_disambiguate_clubs():
    # Distinct clubs that share a base name must NOT collapse together.
    assert normalize_team_name("Atletico-MG") != normalize_team_name("Atletico-GO")
    assert normalize_team_name("America-MG") != normalize_team_name("America-RN")


def test_team_matches_bare_query_against_suffixed_cell():
    # A casual "Flamengo" query still finds the stored "Flamengo-RJ".
    assert team_matches("Flamengo", "Flamengo-RJ")
    assert team_matches("Flamengo-RJ", "Flamengo")
    assert team_matches("vasco", "Vasco da Gama")


def test_team_matches_rejects_different_clubs():
    assert not team_matches("Atletico-MG", "Atletico-GO")
    assert not team_matches("Santos", "Flamengo")


def test_clean_display_name():
    assert clean_display_name("Flamengo-RJ") == "Flamengo-RJ"
    assert clean_display_name("América - MG") == "América-MG"
    assert clean_display_name("Nacional (URU)") == "Nacional"
