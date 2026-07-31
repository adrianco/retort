"""Entity resolution for club and competition names.

Context
-------
Feature: Team name normalisation

  The five match files spell clubs differently ("Palmeiras-SP", "Palmeiras - SP",
  "Sport Club do Recife", "Atlético-MG").  Every question about a club depends on
  those spellings collapsing onto one node -- and on clubs that merely *share* a
  name (Botafogo of Rio, Paraíba and Ribeirão Preto) staying apart.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.names import (
    CLUBS,
    DERBIES,
    parse_team_name,
    resolve_competition,
    resolve_team,
    search_clubs,
    slugify,
    strip_accents,
)


class TestNormalisation:
    """Scenario: Reduce a spelling to a comparison key."""

    @pytest.mark.parametrize(
        "raw, base, region",
        [
            ("Palmeiras-SP", "palmeiras", "SP"),
            ("Palmeiras - SP", "palmeiras", "SP"),
            ("Palmeiras", "palmeiras", None),
            ("Vasco Da Gama RJ", "vasco gama", "RJ"),
            ("Nacional (URU)", "nacional", "URU"),
            ("Barcelona-EQU", "barcelona", "EQU"),
            ("A.b.c. - RN", "abc", "RN"),
            ("Sport Club do Recife", "recife", None),
            ("Grêmio Esportivo Sapucaiense - RS", "sapucaiense", "RS"),
            ("Colo-Colo", "colo colo", None),  # hyphen is part of the name
        ],
    )
    def test_given_a_raw_name_when_parsed_then_base_and_region_are_split(
        self, raw, base, region
    ):
        """
        Given a club spelling from one of the CSV files
        When the name is mechanically normalised
        Then the base name and the state/country code are separated
        """
        parsed = parse_team_name(raw)

        assert parsed.base == base
        assert parsed.region == region

    def test_given_accented_text_when_stripped_then_ascii_is_returned(self):
        """
        Given Brazilian Portuguese text with accents and cedillas
        When accents are stripped
        Then the ASCII form is returned and UTF-8 input is never corrupted
        """
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Grêmio Avaí Fortaleza Esporte Clube").startswith("Gremio Avai")
        assert slugify("Atlético Mineiro") == "atletico-mineiro"


class TestResolution:
    """Scenario: Map every spelling of a club onto one canonical node."""

    @pytest.mark.parametrize(
        "spellings, team_id",
        [
            (["Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "SE Palmeiras"], "palmeiras"),
            (["Sport-PE", "Sport - PE", "Sport Recife", "Sport Club do Recife"], "sport-recife"),
            (
                ["Atletico-MG", "Atlético - MG", "Atletico Mineiro", "Atlético Mineiro - MG"],
                "atletico-mg",
            ),
            (
                ["Athletico-PR", "Atlético-PR", "Athletico", "Atletico Paranaense",
                 "Athletico Paranaense - PR"],
                "athletico-pr",
            ),
            (["Vasco", "Vasco da Gama-RJ", "Vasco Da Gama RJ"], "vasco-da-gama"),
            (["Náutico - PE", "Nautico Capibaribe", "Nautico-PE"], "nautico"),
            (["América FC (Minas Gerais)", "América-MG", "America MG"], "america-mg"),
            (["Ceará Sporting Club", "Ceará - CE", "Ceara-CE"], "ceara"),
            (["Red Bull Bragantino-SP", "Bragantino", "Bragantino - SP"], "bragantino-sp"),
            (["Portuguesa Desportos", "Portuguesa-SP", "Portuguesa"], "portuguesa-sp"),
        ],
    )
    def test_given_many_spellings_when_resolved_then_one_club_id(self, spellings, team_id):
        """
        Given the different spellings a club has across the datasets
        When each spelling is resolved
        Then they all produce the same canonical club id
        """
        resolved = {resolve_team(spelling).id for spelling in spellings}

        assert resolved == {team_id}

    @pytest.mark.parametrize(
        "raw, team_id",
        [
            ("Botafogo", "botafogo-rj"),
            ("Botafogo - PB", "botafogo-pb"),
            ("Botafogo SP", "botafogo-sp"),
            ("Vitória - BA", "vitoria-ba"),
            ("Vitoria ES", "vitoria-es"),
            ("Santos", "santos"),
            ("Santos AP", "santos-ap"),
            ("Nacional (URU)", "nacional-uru"),
            ("Nacional - AM", "nacional-am"),
            ("Peñarol", "penarol"),
            ("Penarol AM", "penarol-am"),
            ("River Plate", "river-plate"),
            ("River Plate-URU", "river-plate-uru"),
        ],
    )
    def test_given_clubs_sharing_a_name_when_resolved_then_they_stay_distinct(
        self, raw, team_id
    ):
        """
        Given several clubs that share a base name but differ by state or country
        When each is resolved
        Then every club keeps its own id instead of collapsing into one
        """
        assert resolve_team(raw).id == team_id

    def test_given_a_misspelt_club_when_resolved_then_the_active_club_wins(self):
        """
        Given the extended statistics file writes Vila Nova (Goiás) as
        "Villa Nova", which is also the name of a Minas Gerais club
        When each spelling is resolved
        Then the unqualified form goes to the club that plays these competitions
        And the Minas Gerais club still resolves when its state is given
        """
        assert resolve_team("Villa Nova").id == "vila-nova"
        assert resolve_team("Vila Nova - GO").id == "vila-nova"
        assert resolve_team("Villa Nova - MG").id == "villa-nova-mg"

    def test_given_an_unreliable_state_column_when_resolving_then_the_name_wins(self):
        """
        Given novo_campeonato_brasileiro.csv files Vitória (Bahia) under UF "ES"
        When the club is resolved with that state hint
        Then the name is trusted over the column and Vitória-BA is returned
        """
        assert resolve_team("Vitória", state_hint="ES").id == "vitoria-ba"

    def test_given_an_ambiguous_name_when_a_state_hint_exists_then_it_disambiguates(self):
        """
        Given a bare name that the registry only knows per state
        When a state hint is supplied by the source file
        Then the hint selects the right club
        """
        assert resolve_team("Atlético", state_hint="MG").id == "atletico-mg"
        assert resolve_team("Atlético", state_hint="GO").id == "atletico-go"

    def test_given_a_nickname_when_resolved_then_the_club_is_found(self):
        """
        Given a colloquial nickname used in natural language questions
        When it is resolved
        Then the club node is returned
        """
        assert resolve_team("Timão").id == "corinthians"
        assert resolve_team("Fla").id == "flamengo"
        assert resolve_team("Verdão").id == "palmeiras"
        assert resolve_team("Furacão").id == "athletico-pr"

    def test_given_an_unknown_club_when_resolved_then_a_stable_id_is_derived(self):
        """
        Given a club that is not in the curated registry
        When it is resolved twice with different spellings
        Then a stable id is derived from the name so the long tail is queryable
        """
        first = resolve_team("Clube Atlético Fictício - SP")
        second = resolve_team("Atlético Fictício")

        assert first.id == second.id
        assert first.known is False


class TestRegistryIntegrity:
    """Scenario: The curated club registry stays self-consistent."""

    def test_given_the_registry_when_loaded_then_ids_are_unique(self):
        """
        Given the curated club registry
        When it is loaded
        Then every club id appears exactly once
        """
        ids = [club.id for club in CLUBS]

        assert len(ids) == len(set(ids))

    def test_given_the_registry_when_resolving_its_own_names_then_it_round_trips(self):
        """
        Given every canonical club name and alias
        When resolved through the public API
        Then each maps back to the club that declared it
        """
        for club in CLUBS:
            for spelling in (club.name, *club.aliases):
                assert resolve_team(spelling).id == club.id, f"{spelling} -> {club.id}"

    def test_given_derby_definitions_when_checked_then_they_reference_known_clubs(self):
        """
        Given the traditional rivalry definitions
        When each pair is checked against the registry
        Then both clubs exist and no club is its own rival
        """
        known = {club.id for club in CLUBS}
        for first, second, name in DERBIES:
            assert first in known, f"{name}: unknown club {first}"
            assert second in known, f"{name}: unknown club {second}"
            assert first != second


class TestCompetitions:
    """Scenario: Recognise competition names in free text."""

    @pytest.mark.parametrize(
        "text, competition_id",
        [
            ("brasileirao", "serie-a"),
            ("Brasileirão", "serie-a"),
            ("Serie A", "serie-a"),
            ("campeonato brasileiro", "serie-a"),
            ("serie b", "serie-b"),
            ("Copa do Brasil", "copa-do-brasil"),
            ("brazilian cup", "copa-do-brasil"),
            ("libertadores", "libertadores"),
            ("Copa Libertadores", "libertadores"),
        ],
    )
    def test_given_free_text_when_resolved_then_the_competition_is_identified(
        self, text, competition_id
    ):
        """
        Given a competition named the way a user would type it
        When it is resolved
        Then the canonical competition is returned
        """
        competition = resolve_competition(text)

        assert competition is not None
        assert competition.id == competition_id

    def test_given_an_unknown_competition_when_resolved_then_none_is_returned(self):
        """
        Given text that names no competition in the data
        When it is resolved
        Then nothing is returned so the caller can explain the options
        """
        assert resolve_competition("Premier League") is None


class TestSearch:
    """Scenario: Suggest clubs for a partial name."""

    def test_given_a_partial_name_when_searching_then_candidates_are_ranked(self):
        """
        Given a partial club name
        When the registry is searched
        Then matching clubs are returned with exact matches first
        """
        results = search_clubs("santa cruz")

        assert results
        assert any(club.id == "santa-cruz-pe" for club in results)
