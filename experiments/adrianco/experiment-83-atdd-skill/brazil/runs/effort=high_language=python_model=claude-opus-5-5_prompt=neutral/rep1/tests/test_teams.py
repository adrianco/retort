"""Team-name normalisation across the naming conventions used by the datasets."""

import pytest

from brsoccer.teams import fold, normalize_team, split_suffix


@pytest.mark.parametrize("raw, expected", [
    ("Palmeiras-SP", "palmeiras"),
    ("Palmeiras - SP", "palmeiras"),
    ("Palmeiras", "palmeiras"),
    ("palmeiras-sp", "palmeiras"),
    ("Sociedade Esportiva Palmeiras", "palmeiras"),
    ("Sport Club Corinthians Paulista", "corinthians"),
    ("Corinthians-SP", "corinthians"),
    ("Sao Paulo", "sao-paulo"),
    ("São Paulo - SP", "sao-paulo"),
    ("Sao Paulo FC", "sao-paulo"),
    ("Athletico-PR", "athletico-paranaense"),
    ("Atletico-PR", "athletico-paranaense"),
    ("Atlético Paranaense - PR", "athletico-paranaense"),
    ("Athletico", "athletico-paranaense"),
    ("Atletico-MG", "atletico-mineiro"),
    ("Atlético Mineiro - MG", "atletico-mineiro"),
    ("Atlético-GO", "atletico-goianiense"),
    ("Vasco", "vasco-da-gama"),
    ("Vasco Da Gama RJ", "vasco-da-gama"),
    ("Gremio", "gremio"),
    ("Grêmio - RS", "gremio"),
    ("Sport-PE", "sport-recife"),
    ("Sport Club do Recife", "sport-recife"),
    ("EC Bahia", "bahia"),
    ("Fortaleza EC", "fortaleza"),
    ("America MG", "america-mineiro"),
    ("América FC (Minas Gerais)", "america-mineiro"),
    ("Ceará Sporting Club", "ceara"),
    ("Red Bull Bragantino-SP", "red-bull-bragantino"),
    ("C. R. B. - AL", "crb"),
    ("Crb - AL", "crb"),
])
def test_known_club_variants(raw, expected):
    team = normalize_team(raw)
    assert team.id == expected
    assert team.known


def test_homonymous_clubs_from_other_states_are_distinct():
    assert normalize_team("Flamengo - PI").id == "flamengo-pi"
    assert normalize_team("Flamengo - PI").name == "Flamengo (PI)"
    assert normalize_team("Botafogo PB").id == "botafogo-pb"
    assert normalize_team("América - RN").id == "america-rn"
    assert normalize_team("Internacional - SC").id == "internacional-sc"
    assert normalize_team("Flamengo-RJ").id == "flamengo"


def test_foreign_clubs_keep_country():
    assert normalize_team("Nacional (URU)").id == normalize_team("Nacional-URU").id == "nacional-uru"
    assert normalize_team("Guaraní (PAR)").id == "guarani-par"
    assert normalize_team("Guarani - SP").id == "guarani"
    assert normalize_team("Barcelona-EQU").name == "Barcelona (ECU)"


def test_accents_and_display_names():
    assert normalize_team("Sao Paulo").name == "São Paulo"
    assert normalize_team("Gremio").name == "Grêmio"
    assert normalize_team("Avai-SC").name == "Avaí"
    assert fold("São Paulo") == "sao paulo"
    assert fold("A.b.c.") == "abc"


def test_split_suffix():
    assert split_suffix("Palmeiras-SP") == ("Palmeiras", "SP", None)
    assert split_suffix("Vasco Da Gama RJ") == ("Vasco Da Gama", "RJ", None)
    assert split_suffix("Nacional (URU)") == ("Nacional", None, "URU")
    assert split_suffix("Boca Juniors") == ("Boca Juniors", None, None)
    assert split_suffix("Real FC") == ("Real FC", None, None)
