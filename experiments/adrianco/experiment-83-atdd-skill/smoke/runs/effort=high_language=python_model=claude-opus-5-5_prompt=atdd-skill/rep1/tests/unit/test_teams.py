"""Unit tests for team identity (name normalisation across datasets)."""

import pytest

from brazilian_soccer_mcp.teams import TeamRegistry, identify


@pytest.mark.parametrize("raw, display", [
    ("Palmeiras-SP", "Palmeiras"),
    ("Palmeiras - SP", "Palmeiras"),
    ("Sociedade Esportiva Palmeiras", "Palmeiras"),
    ("Sport Club Corinthians Paulista", "Corinthians"),
    ("Sao Paulo", "São Paulo"),
    ("São Paulo-SP", "São Paulo"),
    ("Gremio", "Grêmio"),
    ("EC Bahia", "Bahia"),
    ("Vasco", "Vasco da Gama"),
    ("Atletico-MG", "Atlético Mineiro"),
    ("Atletico Mineiro", "Atlético Mineiro"),
    ("Atlético - PR", "Athletico Paranaense"),
    ("Athletico", "Athletico Paranaense"),
    ("America MG", "América Mineiro"),
    ("América FC (Minas Gerais)", "América Mineiro"),
    ("Botafogo RJ", "Botafogo"),
    ("Red Bull Bragantino-SP", "Red Bull Bragantino"),
    ("Sport Club do Recife", "Sport Recife"),
])
def test_known_clubs_are_identified_whatever_the_spelling(raw, display):
    assert identify(raw) == identify(display)
    assert identify(raw)[1] == display


@pytest.mark.parametrize("a, b", [
    ("Botafogo-RJ", "Botafogo-SP"),
    ("Atletico-MG", "Atletico-GO"),
    ("Bragantino", "Bragantino PA"),
    ("Guaraní (PAR)", "Guarani"),
    ("Santos", "Santos Laguna"),
])
def test_different_clubs_stay_apart(a, b):
    assert identify(a)[0] != identify(b)[0]


def test_foreign_country_tags_are_equivalent():
    assert identify("Guaraní (PAR)")[0] == identify("Guaraní-PAR")[0]


def test_registry_prefers_the_accented_display_name():
    registry = TeamRegistry()
    registry.register("Criciuma-SC")
    key = registry.register("Criciúma")
    assert registry.display(key) == "Criciúma"


def test_registry_resolves_partial_names_to_the_most_prominent_team():
    registry = TeamRegistry()
    registry.register("Atletico-MG")
    registry.register("Atletico-GO")
    key = registry.resolve("Mineiro")
    assert registry.display(key) == "Atlético Mineiro"
    assert registry.resolve("Real Madrid") is None
