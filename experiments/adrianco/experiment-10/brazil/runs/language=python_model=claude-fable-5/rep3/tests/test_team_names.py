"""Feature: Team name normalization.

The datasets spell the same club many different ways; queries must line up
regardless of accents, state suffixes, club-type affixes and renames.
"""

import pytest

from team_names import TeamKey, parse_team


class TestStateSuffixes:
    """Scenario: names with and without state suffixes match."""

    @pytest.mark.parametrize("variant", [
        "Palmeiras-SP", "Palmeiras", "palmeiras", "PALMEIRAS-SP",
    ])
    def test_palmeiras_variants_share_base(self, variant):
        assert parse_team(variant).base == "palmeiras"

    @pytest.mark.parametrize("left,right", [
        ("Flamengo-RJ", "Flamengo"),
        ("América - MG", "America MG"),
        ("Botafogo RJ", "Botafogo - RJ"),
        ("Nacional (URU)", "Nacional-URU"),
        ("Guaraní (PAR)", "Guaraní-PAR"),
    ])
    def test_suffix_styles_are_equivalent(self, left, right):
        assert parse_team(left).matches(parse_team(right))

    def test_same_base_different_state_does_not_match(self):
        assert not parse_team("América-MG").matches(parse_team("América-RN"))
        assert not parse_team("Botafogo-SP").matches(parse_team("Botafogo-RJ"))


class TestAccents:
    """Scenario: accented and unaccented spellings match (UTF-8 handling)."""

    @pytest.mark.parametrize("left,right", [
        ("São Paulo", "Sao Paulo"),
        ("Grêmio", "Gremio"),
        ("Avaí", "Avai-SC"),
        ("Atlético-GO", "Atletico-GO"),
        ("Criciúma", "Criciuma-SC"),
    ])
    def test_accent_insensitive(self, left, right):
        assert parse_team(left).matches(parse_team(right))


class TestAliasesAndAffixes:
    """Scenario: renamed clubs, official long names and club-type affixes."""

    def test_athletico_paranaense_rename(self):
        keys = {parse_team(n) for n in
                ("Athletico Paranaense", "Atlético-PR", "Atletico-PR",
                 "Atlético Paranaense - PR", "Athletico")}
        assert len(keys) == 1
        assert keys.pop() == TeamKey("atletico", "PR")

    def test_official_long_names(self):
        assert parse_team("Sport Club Corinthians Paulista").matches(
            parse_team("Corinthians-SP"))
        assert parse_team("Sport Club do Recife").matches(
            parse_team("Sport-PE"))
        assert parse_team("Ceará Sporting Club").matches(parse_team("Ceara"))

    def test_club_type_affixes_stripped(self):
        assert parse_team("EC Juventude").matches(parse_team("Juventude"))
        assert parse_team("Fortaleza FC").matches(parse_team("Fortaleza-CE"))
        assert parse_team("4 de Julho EC").matches(
            parse_team("4 de Julho - PI"))
        assert parse_team("Arapongas Esporte Clube - PR").base == "arapongas"

    def test_red_bull_bragantino_rebrand(self):
        assert parse_team("Red Bull Bragantino-SP").matches(
            parse_team("Bragantino"))
        assert not parse_team("Bragantino PA").matches(
            parse_team("Red Bull Bragantino"))

    def test_acronym_clubs_keep_their_name(self):
        assert parse_team("CSA").matches(parse_team("Csa-AL"))
        assert parse_team("CSA").base == "csa"

    def test_vasco_da_gama(self):
        assert parse_team("Vasco da Gama-RJ").matches(parse_team("Vasco"))
