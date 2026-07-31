"""
Unit tests for the club registry.

Context
-------
Name reconciliation is the single highest-risk part of this project: if
"Atletico-MG" and "Atlético Mineiro" become two clubs, every standing, record
and head-to-head silently splits in half.  These tests pin down both directions
of the risk -- variants that *must* merge, and homonyms that *must not*.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.teams import TeamRegistry, match_key


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Esporte Clube Bahia", "bahia"),
        ("EC Bahia", "bahia"),
        ("Bahia - BA", "bahia"),
        ("CA Paraná", "parana"),
        ("Clube Do Remo", "remo"),
        ("Independiente Del Valle", "independiente valle"),
        ("Independiente del Valle", "independiente valle"),
        ("Sport", "sport"),
        ("Vasco da Gama-RJ", "vasco gama"),
    ],
)
def test_match_key_strips_club_type_noise(raw, expected):
    assert match_key(raw) == expected


@pytest.fixture(scope="module")
def registry(graph):
    return graph.registry


@pytest.mark.parametrize(
    "spelling, team_id",
    [
        ("Flamengo", "flamengo-rj"),
        ("Flamengo-RJ", "flamengo-rj"),
        ("CR Flamengo", "flamengo-rj"),
        ("Palmeiras-SP", "palmeiras-sp"),
        ("SE Palmeiras", "palmeiras-sp"),
        ("Sport Club Corinthians Paulista", "corinthians-sp"),
        ("Corinthians-SP", "corinthians-sp"),
        ("São Paulo", "sao-paulo-sp"),
        ("Sao Paulo-SP", "sao-paulo-sp"),
        ("Atletico-MG", "atletico-mg"),
        ("Atlético - MG", "atletico-mg"),
        ("Atletico Mineiro", "atletico-mg"),
        ("Athletico", "athletico-pr"),
        ("Athletico-PR", "athletico-pr"),
        ("Atletico-PR", "athletico-pr"),
        ("Atletico Paranaense", "athletico-pr"),
        ("Atletico-GO", "atletico-go"),
        ("Atletico Goianiense", "atletico-go"),
        ("Vasco", "vasco-da-gama-rj"),
        ("Vasco da Gama-RJ", "vasco-da-gama-rj"),
        ("EC Bahia", "bahia-ba"),
        ("Bahia - BA", "bahia-ba"),
        ("Sport-PE", "sport-pe"),
        ("Sport Club do Recife", "sport-pe"),
        ("Ceará Sporting Club", "ceara-ce"),
        ("Fortaleza FC", "fortaleza-ce"),
        ("América FC (Minas Gerais)", "america-mg"),
        ("América-MG", "america-mg"),
        ("Red Bull Bragantino-SP", "bragantino-sp"),
        ("Bragantino", "bragantino-sp"),
    ],
)
def test_variants_resolve_to_one_club(registry, spelling, team_id):
    assert registry.resolve_id(spelling) == team_id


@pytest.mark.parametrize(
    "spelling, team_id",
    [
        ("Botafogo", "botafogo-rj"),
        ("Botafogo-RJ", "botafogo-rj"),
        ("Botafogo SP", "botafogo-sp"),
        ("Botafogo - PB", "botafogo-pb"),
        ("América - RN", "america-rn"),
        ("Bragantino - PA", "bragantino-pa"),
        ("Vila Nova-GO", "vila-nova-go"),
    ],
)
def test_ambiguous_bases_stay_distinct(registry, spelling, team_id):
    assert registry.resolve_id(spelling) == team_id


def test_river_plate_argentina_and_uruguay_are_different_clubs(registry):
    argentina = registry.resolve("River Plate")
    uruguay = registry.resolve("River Plate-URU")
    assert argentina.id != uruguay.id
    assert argentina.country == "ARG"
    assert uruguay.country == "URU"


def test_nacional_uruguay_and_paraguay_are_different_clubs(registry):
    assert registry.resolve_id("Nacional (URU)") == registry.resolve_id("Nacional-URU")
    assert registry.resolve_id("Nacional (URU)") != registry.resolve_id("Nacional (PAR)")


def test_country_suffix_synonyms_merge(registry):
    assert registry.resolve_id("Delfín") == registry.resolve_id("Delfín-EQU")
    assert registry.resolve_id("Guaraní (PAR)") == registry.resolve_id("Guaraní-PAR")
    assert registry.resolve_id("Universitario (PER)") == registry.resolve_id("Universitario-PER")


def test_paraguayan_guarani_is_not_the_sao_paulo_club(registry):
    assert registry.resolve_id("Guarani") == "guarani-sp"
    assert registry.resolve_id("Guaraní-PAR") == "guarani-par"


def test_fifa_club_lookup_is_strict_about_nationality(registry):
    """"FC Barcelona" must not be mistaken for Barcelona SC of Ecuador."""

    assert registry.lookup("FC Barcelona", brazilian_only=True) is None
    assert registry.lookup("Club América", brazilian_only=True) is None
    assert registry.lookup("Atlético Madrid", brazilian_only=True) is None
    assert registry.lookup("Grêmio", brazilian_only=True).id == "gremio-rs"
    assert registry.lookup("Sport Club do Recife", brazilian_only=True).id == "sport-pe"


def test_search_finds_clubs_by_nickname(registry):
    assert registry.search("Mengão")[0].id == "flamengo-rj"
    assert registry.search("Timão")[0].id == "corinthians-sp"
    assert registry.search("Verdão")[0].id == "palmeiras-sp"


def test_search_returns_several_botafogos(registry):
    ids = {team.id for team in registry.search("Botafogo", limit=10)}
    assert {"botafogo-rj", "botafogo-sp", "botafogo-pb"} <= ids


def test_registry_is_stable_across_repeated_resolution(registry):
    first = [registry.resolve_id(name) for name in ("Flamengo", "Flamengo-RJ", "flamengo")]
    second = [registry.resolve_id(name) for name in ("Flamengo", "Flamengo-RJ", "flamengo")]
    assert first == second == ["flamengo-rj"] * 3


def test_state_and_country_are_recorded(registry):
    assert registry.resolve("Palmeiras-SP").state == "SP"
    assert registry.resolve("Palmeiras-SP").country == "BRA"
    assert registry.resolve("Boca Juniors").country == "ARG"


def test_display_name_disambiguates():
    empty = TeamRegistry()
    empty.build()
    assert empty.resolve("Botafogo").display_name == "Botafogo (RJ)"
    assert empty.resolve("Boca Juniors").display_name == "Boca Juniors (ARG)"


def test_unknown_club_is_minted_once():
    empty = TeamRegistry()
    empty.observe("Clube Imaginário - XX", competition_id="serie-a")
    empty.build()
    first = empty.resolve_id("Clube Imaginário - XX")
    second = empty.resolve_id("Clube Imaginário - XX")
    assert first == second
    assert empty.get(first).name == "Clube Imaginário - XX"


def test_empty_observations_and_queries_are_ignored():
    empty = TeamRegistry()
    empty.observe("")
    empty.observe("   ")
    empty.build()
    empty.build()  # idempotent
    assert empty.search("") == []
    assert empty.lookup("") is None
    assert empty.lookup("Nowhere United") is None


def test_observing_after_build_is_a_programming_error():
    empty = TeamRegistry()
    empty.build()
    with pytest.raises(RuntimeError):
        empty.observe("Too Late FC")


def test_display_name_is_title_cased_when_the_source_shouts():
    registry = TeamRegistry()
    registry.observe("CLUBE FICTICIO - SP", competition_id="serie-b")
    registry.observe("CLUBE FICTICIO - SP", competition_id="serie-b")
    registry.build()
    assert registry.resolve("CLUBE FICTICIO - SP").name == "Clube Ficticio"


def test_the_most_common_accented_spelling_wins():
    registry = TeamRegistry()
    for _ in range(3):
        registry.observe("Grêmio Ficticio - RS", competition_id="serie-b")
    registry.observe("Gremio Ficticio - RS", competition_id="serie-b")
    registry.build()
    assert registry.resolve("Gremio Ficticio-RS").name == "Grêmio Ficticio"


def test_unqualified_name_joins_a_single_qualified_cluster():
    registry = TeamRegistry()
    registry.observe("Novo Clube - PI", competition_id="serie-c")
    registry.observe("Novo Clube", competition_id="serie-c")
    registry.build()
    assert registry.resolve_id("Novo Clube") == registry.resolve_id("Novo Clube - PI")


def test_unqualified_name_stays_apart_when_two_qualifiers_exist():
    registry = TeamRegistry()
    registry.observe("Outro Clube - PI", competition_id="serie-c")
    registry.observe("Outro Clube - BA", competition_id="serie-c")
    registry.observe("Outro Clube", competition_id="serie-c")
    registry.build()
    ids = {registry.resolve_id(name) for name in
           ("Outro Clube", "Outro Clube - PI", "Outro Clube - BA")}
    assert len(ids) == 3


def test_libertadores_only_clubs_are_not_marked_brazilian():
    registry = TeamRegistry()
    registry.observe("Clube Sul Americano", competition_id="libertadores")
    registry.build()
    assert registry.resolve("Clube Sul Americano").country == ""


def test_a_club_seen_in_a_brazilian_competition_is_brazilian():
    registry = TeamRegistry()
    registry.observe("Clube Nacional Ficticio", competition_id="copa-do-brasil")
    registry.build()
    assert registry.resolve("Clube Nacional Ficticio").country == "BRA"
