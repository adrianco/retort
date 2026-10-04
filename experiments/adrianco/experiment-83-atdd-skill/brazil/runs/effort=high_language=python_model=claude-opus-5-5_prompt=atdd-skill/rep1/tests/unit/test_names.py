import pytest

from brazilian_soccer_mcp.names import (competition_name, display_name, position_codes, simplify, split_state,
                                        team_key)


@pytest.mark.parametrize("raw, key", [
    ("Palmeiras-SP", "palmeiras"), ("Palmeiras - SP", "palmeiras"), ("Palmeiras", "palmeiras"),
    ("Sociedade Esportiva Palmeiras", "palmeiras"), ("Sport Club Corinthians Paulista", "corinthians"),
    ("Grêmio", "gremio"), ("Gremio RS", "gremio"), ("Sao Paulo-SP", "sao paulo"), ("São Paulo FC", "sao paulo"),
    ("Atlético-MG", "atletico-mg"), ("Atletico Mineiro", "atletico-mg"), ("Atlético - MG", "atletico-mg"),
    ("Atletico-PR", "athletico-pr"), ("Athletico Paranaense - PR", "athletico-pr"), ("Athletico", "athletico-pr"),
    ("Atlético Paranaense", "athletico-pr"), ("Atletico-GO", "atletico-go"), ("Atletico Goianiense", "atletico-go"),
    ("Flamengo - RJ", "flamengo"), ("Flamengo - PI", "flamengo-pi"), ("Vasco da Gama - RJ", "vasco"),
    ("Vasco Da Gama RJ", "vasco"), ("Vasco", "vasco"), ("Red Bull Bragantino-SP", "bragantino"),
    ("Bragantino - SP", "bragantino"), ("America FC (Minas Gerais)", "america-mg"), ("América-MG", "america-mg"),
    ("Sport Club do Recife", "sport"), ("Sport-PE", "sport"), ("Ceará Sporting Club", "ceara"),
    ("C.r.b. - AL", "crb"), ("C. R. B. - AL", "crb"), ("Boavista FC", "boavista fc"),
    ("Boavista - RJ", "boavista-rj"), ("Nacional (URU)", "nacional uru"), ("Barcelona-EQU", "barcelona equ"),
])
def test_team_keys(raw, key):
    assert team_key(raw) == key


def test_display_names():
    assert display_name("Sao Paulo-SP") == "São Paulo"
    assert display_name("Flamengo - PI") == "Flamengo-PI"
    assert display_name("Bolívar") == "Bolívar"
    assert display_name("Atletico-PR") == "Athletico-PR"


def test_split_state_ignores_foreign_suffixes():
    assert split_state("Guaraní-PAR") == ("Guaraní-PAR", None)
    assert split_state("ASA AL") == ("ASA", "AL")


def test_simplify():
    assert simplify("  São Paulo-SP ") == "sao paulo sp"


@pytest.mark.parametrize("text, name", [("Serie A", "Brasileirão"), ("brasileirao", "Brasileirão"),
                                        ("Libertadores", "Copa Libertadores"), ("Série B", "Série B"),
                                        ("copa do brasil", "Copa do Brasil"), ("La Liga", None)])
def test_competition_names(text, name):
    assert competition_name(text) == name


def test_position_groups():
    assert position_codes("forwards") >= {"ST", "LW", "RW"}
    assert position_codes("gk") == {"GK"}
