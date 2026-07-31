"""Feature: Data normalisation.

Context
-------
The spec's "Data Quality Notes" call out three hazards: team-name variations,
mixed date formats and UTF-8 Portuguese text.  These scenarios pin the
behaviour of :mod:`brazilian_soccer.normalization` for each.
"""

from __future__ import annotations

from datetime import date

import pytest

from brazilian_soccer.normalization import (
    normalize_team,
    normalize_text,
    parse_date,
    parse_float,
    parse_int,
    strip_accents,
    team_key,
)


class TestTeamNameNormalisation:
    """Scenario group: team name variations resolve to one key."""

    @pytest.mark.parametrize(
        "variants",
        [
            ["Palmeiras", "Palmeiras-SP", "Palmeiras - SP", "PALMEIRAS"],
            ["Flamengo", "Flamengo-RJ", "Flamengo - RJ"],
            ["Sao Paulo", "São Paulo", "Sao Paulo-SP", "São Paulo - SP"],
            ["Gremio", "Grêmio", "Gremio-RS", "Grêmio - RS", "Gremio RS"],
            ["Vasco", "Vasco da Gama - RJ", "Vasco Da Gama RJ", "Vasco da Gama-RJ"],
            ["Atletico Mineiro", "Atlético-MG", "Atlético - MG", "Atletico-MG"],
            ["Athletico-PR", "Atlético Paranaense", "Athletico Paranaense"],
            ["Sport", "Sport Recife", "Sport-PE", "Sport - PE"],
            ["Nautico", "Náutico", "Nautico Capibaribe", "Náutico - PE"],
            ["ABC", "Abc - RN", "A.b.c. - RN", "ABC - RN"],
            ["Avai", "Avaí", "Avai-SC", "Avaí - SC"],
            ["EC Bahia", "Bahia", "Bahia-BA", "Bahia - BA"],
            ["Fortaleza", "Fortaleza EC", "Fortaleza FC", "Fortaleza-CE"],
            ["Ceara", "Ceará", "Ceara-CE", "Ceará - CE"],
            ["Clube Do Remo", "Remo", "Remo - PA", "Remo PA"],
        ],
    )
    def test_variants_share_one_canonical_key(self, variants: list[str]) -> None:
        # Given a set of raw spellings of the same club
        # When each is normalised
        keys = {team_key(variant) for variant in variants}
        # Then they all collapse to a single canonical key
        assert len(keys) == 1, f"{variants} produced {keys}"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Palmeiras-SP", "palmeiras"),
            ("Flamengo", "flamengo-rj"),
            ("Flamengo do Piauí - PI", "flamengo-pi"),
            ("América - MG", "america-mg"),
            ("América-RN", "america-rn"),
            ("Botafogo PB", "botafogo-pb"),
            ("Botafogo-RJ", "botafogo-rj"),
            ("Botafogo", "botafogo-rj"),
            ("Nacional (URU)", "nacional-uru"),
            ("Nacional - AM", "nacional-am"),
            ("Guaraní (PAR)", "guarani-par"),
            ("Guarani SP", "guarani-sp"),
        ],
    )
    def test_ambiguous_clubs_keep_their_region(self, raw: str, expected: str) -> None:
        # Given a base name shared by several real clubs
        # When it is normalised
        # Then the region stays in the key so the clubs remain distinct
        assert team_key(raw) == expected

    @pytest.mark.parametrize(
        "left,right",
        [
            ("América - MG", "América-RN"),
            ("Botafogo-RJ", "Botafogo SP"),
            ("Flamengo", "Flamengo - PI"),
            ("Gremio", "Gremio Novorizontino"),
            ("Fluminense", "Fluminense de Feira - BA"),
            ("Santos-SP", "Santos - AP"),
        ],
    )
    def test_different_clubs_do_not_collide(self, left: str, right: str) -> None:
        # Given two genuinely different clubs with similar names
        # Then their keys differ
        assert team_key(left) != team_key(right)

    def test_normalisation_exposes_region_and_display(self) -> None:
        # Given a name carrying a state suffix
        name = normalize_team("Atlético - MG")
        # Then the decomposition is available to callers
        assert name.base == "atletico"
        assert name.region == "MG"
        assert name.key == "atletico-mg"
        assert name.display == "Atletico-MG"
        assert name.raw == "Atlético - MG"

    def test_empty_names_are_handled(self) -> None:
        assert normalize_team(None).key == ""
        assert normalize_team("   ").key == ""


class TestEncoding:
    """Scenario group: Portuguese characters survive and fold predictably."""

    @pytest.mark.parametrize(
        "raw,folded",
        [
            ("São Paulo", "Sao Paulo"),
            ("Grêmio", "Gremio"),
            ("Avaí", "Avai"),
            ("Atlético Paranaense", "Atletico Paranaense"),
            ("Fortaleza Esporte Clube", "Fortaleza Esporte Clube"),
        ],
    )
    def test_accents_fold(self, raw: str, folded: str) -> None:
        assert strip_accents(raw) == folded

    def test_free_text_normalisation_is_accent_insensitive(self) -> None:
        assert normalize_text("  Grêmio  FBPA ") == "gremio fbpa"
        assert normalize_text("SÃO PAULO") == "sao paulo"


class TestDateParsing:
    """Scenario group: all three date formats in the datasets parse."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("2023-09-24", date(2023, 9, 24)),
            ("2012-05-19 18:30:00", date(2012, 5, 19)),
            ("29/03/2003", date(2003, 3, 29)),
            ('"2016-11-27 17:00:00"', date(2016, 11, 27)),
            ("2019-01-01 00:00", date(2019, 1, 1)),
        ],
    )
    def test_supported_formats(self, raw: str, expected: date) -> None:
        assert parse_date(raw) == expected

    @pytest.mark.parametrize("raw", ["", "   ", None, "not a date", "nan"])
    def test_unparseable_dates_are_none(self, raw) -> None:
        assert parse_date(raw) is None


class TestNumberParsing:
    @pytest.mark.parametrize(
        "raw,expected",
        [("2", 2), ('"3"', 3), (1.0, 1), ("", None), (None, None), ("NA", None)],
    )
    def test_int_parsing(self, raw, expected) -> None:
        assert parse_int(raw) == expected

    def test_float_parsing(self) -> None:
        assert parse_float("75.0") == 75.0
        assert parse_float("") is None
