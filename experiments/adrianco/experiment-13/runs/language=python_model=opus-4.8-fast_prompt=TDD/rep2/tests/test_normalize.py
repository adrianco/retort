"""Tests for team-name normalization helpers."""

from brazilian_soccer.normalize import normalize_team, strip_accents, teams_match


def test_strip_accents_removes_portuguese_diacritics():
    assert strip_accents("São Paulo") == "Sao Paulo"
    assert strip_accents("Grêmio") == "Gremio"
    assert strip_accents("Avaí") == "Avai"


def test_normalize_strips_state_suffix_dash():
    assert normalize_team("Palmeiras-SP") == "palmeiras"
    assert normalize_team("Flamengo-RJ") == "flamengo"


def test_normalize_strips_spaced_state_suffix():
    assert normalize_team("Grêmio - RS") == "gremio"


def test_normalize_strips_country_suffix_in_parens():
    assert normalize_team("Nacional (URU)") == "nacional"
    assert normalize_team("Barcelona-EQU") == "barcelona"


def test_normalize_is_accent_and_case_insensitive():
    assert normalize_team("São Paulo") == normalize_team("Sao Paulo")
    assert normalize_team("GRÊMIO") == normalize_team("gremio")


def test_ambiguous_clubs_keep_their_state_distinction():
    # "Atlético" with different states are DIFFERENT clubs and must not merge.
    assert normalize_team("Atletico-MG") != normalize_team("Atletico-PR")
    # ...but each still maps to a stable canonical key.
    assert normalize_team("Atletico-MG") == normalize_team("Atlético Mineiro")
    assert normalize_team("América - MG") == normalize_team("América Mineiro")


def test_normalize_known_aliases_collapse_to_canonical():
    # Full official names normalize to the common short name.
    assert normalize_team("Sport Club Corinthians Paulista") == normalize_team("Corinthians")


def test_teams_match_handles_variations():
    assert teams_match("Palmeiras-SP", "Palmeiras")
    assert teams_match("São Paulo", "Sao Paulo-SP")
    assert not teams_match("Palmeiras", "Santos")
