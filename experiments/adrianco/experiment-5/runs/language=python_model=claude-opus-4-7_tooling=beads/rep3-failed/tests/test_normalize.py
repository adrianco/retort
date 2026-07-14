"""Feature: team-name normalization across the dataset's conventions."""

import pytest

from brazilian_soccer_mcp.normalize import (
    display_team,
    normalize_team,
    state_full_name,
    strip_accents,
    team_matches,
)


class TestNormalization:
    """
    Scenario: Different formats of the same team name must collapse together.
    """

    @pytest.mark.parametrize(
        "raw",
        [
            "Flamengo",
            "Flamengo-RJ",
            "Flamengo RJ",
            "Clube de Regatas do Flamengo",
        ],
    )
    def test_flamengo_variants(self, raw):
        assert normalize_team(raw) == "flamengo"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Palmeiras", "palmeiras"),
            ("Palmeiras-SP", "palmeiras"),
            ("Sociedade Esportiva Palmeiras", "palmeiras"),
        ],
    )
    def test_palmeiras_variants(self, raw, expected):
        assert normalize_team(raw) == expected

    def test_atletico_mineiro_disambiguates_from_paranaense(self):
        assert normalize_team("Atlético-MG") == "atletico mineiro"
        assert normalize_team("Atlético Mineiro") == "atletico mineiro"
        assert normalize_team("Athletico-PR") == "athletico paranaense"
        assert normalize_team("Athletico Paranaense") == "athletico paranaense"
        assert normalize_team("Atletico-MG") != normalize_team("Atletico-PR")

    def test_country_suffix_stripped(self):
        assert normalize_team("Nacional (URU)") == "nacional"
        assert normalize_team("Barcelona-EQU") == "barcelona"

    def test_bahia_aliases(self):
        assert normalize_team("Bahia") == "bahia"
        assert normalize_team("EC Bahia") == "bahia"
        assert normalize_team("Esporte Clube Bahia") == "bahia"

    def test_empty_and_none(self):
        assert normalize_team(None) == ""
        assert normalize_team("") == ""

    def test_strip_accents(self):
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Grêmio") == "Gremio"
        assert strip_accents(None) == ""

    def test_display_team_preserves_accents(self):
        assert "São" in display_team("São Paulo-SP")

    def test_team_matches_loose(self):
        assert team_matches("Flamengo", "Clube de Regatas do Flamengo")
        assert team_matches("Palmeiras", "Palmeiras-SP")
        assert not team_matches("Flamengo", "Fluminense")

    def test_state_full_name(self):
        assert state_full_name("SP") == "São Paulo"
        assert state_full_name("RJ") == "Rio de Janeiro"
        assert state_full_name("XX") == "XX"  # unknown code passes through
