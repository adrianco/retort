"""Unit tests for the club registry and name resolver.

Context
-------
"Implementation should normalize team names for consistent matching" is a
stated requirement, and the failure modes are subtle: over-normalising merges
Botafogo-RJ with Botafogo-PB, under-normalising splits Athletico Paranaense
into five clubs.  Both directions are asserted here.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.clubs import (
    AMBIGUOUS_BASES,
    REGISTRY,
    alternatives_for,
    profile_for,
    resolve_club,
    rivalry_for,
)


@pytest.mark.parametrize("spelling", [
    "Atletico-PR", "Athletico-PR", "Atlético - PR", "Athletico Paranaense",
    "Atletico Paranaense", "Atlético Paranaense", "Athletico Paranaense - PR",
    "Athletico", "athletico pr",
])
def test_every_athletico_paranaense_spelling_collapses(spelling):
    assert resolve_club(spelling).slug == "athletico-pr"


@pytest.mark.parametrize("spelling,slug", [
    ("Palmeiras-SP", "palmeiras"),
    ("SE Palmeiras", "palmeiras"),
    ("EC Bahia", "bahia"),
    ("Esporte Clube Bahia", "bahia"),
    ("Sport Club do Recife", "sport"),
    ("Sport-PE", "sport"),
    ("Sport Recife", "sport"),
    ("Ceará Sporting Club", "ceara"),
    ("Fortaleza Esporte Clube", "fortaleza"),
    ("Vasco", "vasco-da-gama"),
    ("Vasco Da Gama RJ", "vasco-da-gama"),
    ("Sao Paulo", "sao-paulo"),
    ("São Paulo - SP", "sao-paulo"),
    ("Sport Club Corinthians Paulista", "corinthians"),
    ("A.b.c. - RN", "abc"),
    ("ABC - RN", "abc"),
    ("América FC (Minas Gerais)", "america-mg"),
    ("America MG", "america-mg"),
    ("Red Bull Bragantino-SP", "red-bull-bragantino"),
    ("Bragantino - SP", "red-bull-bragantino"),
])
def test_known_spellings_resolve_to_the_curated_club(spelling, slug):
    identity = resolve_club(spelling)
    assert identity.slug == slug
    assert identity.known is True


@pytest.mark.parametrize("a,b", [
    ("Botafogo - RJ", "Botafogo - PB"),
    ("Botafogo RJ", "Botafogo SP"),
    ("Atlético - MG", "Atlético - GO"),
    ("Atlético - MG", "Atlético - PR"),
    ("Bragantino - SP", "Bragantino - PA"),
    ("Grêmio", "Grêmio Prudente"),
    ("América - MG", "América - RN"),
    ("Vitoria-BA", "Vitória - ES"),
])
def test_clubs_that_must_stay_apart(a, b):
    assert resolve_club(a).slug != resolve_club(b).slug


def test_bare_ambiguous_name_picks_the_most_prominent_club():
    assert resolve_club("Botafogo").slug == "botafogo-rj"
    assert resolve_club("América").slug == "america-mg"
    assert "botafogo" in AMBIGUOUS_BASES
    assert set(alternatives_for("Botafogo")) >= {"botafogo-rj", "botafogo-pb"}


def test_a_state_suffix_removes_the_ambiguity():
    assert alternatives_for("Botafogo - PB") == ()


def test_unknown_clubs_get_a_stable_generated_slug():
    identity = resolve_club("Aquidauanense Futebol Clube - MS")
    assert identity.known is False
    assert identity.slug == resolve_club("Aquidauanense - MS").slug


def test_foreign_clubs_with_country_suffixes_stay_distinct():
    assert resolve_club("Nacional (URU)").slug == "nacional-uru"
    assert resolve_club("Nacional-URU").slug == "nacional-uru"
    assert resolve_club("Nacional (PAR)").slug == "nacional-par"
    assert resolve_club("Barcelona-EQU").slug == "barcelona-equ"
    # FC Barcelona from the FIFA file must NOT land on the Ecuadorian club.
    assert resolve_club("FC Barcelona").slug != "barcelona-equ"
    assert resolve_club("River Plate").slug != resolve_club("River Plate-URU").slug


def test_nicknames_resolve():
    assert resolve_club("Timão").slug == "corinthians"
    assert resolve_club("Verdão").slug == "palmeiras"
    assert resolve_club("Galo").slug == "atletico-mg"


def test_rivalries_are_symmetric():
    assert rivalry_for("flamengo", "fluminense") == "Fla-Flu"
    assert rivalry_for("fluminense", "flamengo") == "Fla-Flu"
    assert rivalry_for("gremio", "internacional") == "Gre-Nal"
    assert rivalry_for("flamengo", "santos") is None


def test_registry_slugs_are_unique_and_ascii():
    slugs = [club.slug for club in REGISTRY]
    assert len(slugs) == len(set(slugs))
    assert all(slug.isascii() and slug == slug.lower() for slug in slugs)


def test_profile_lookup():
    profile = profile_for("gremio")
    assert profile is not None and profile.state == "rs"
    assert profile_for("no-such-club") is None


def test_resolving_empty_input_is_safe():
    assert resolve_club("").slug == ""
    assert resolve_club(None).slug == ""
