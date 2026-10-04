import pytest

from team_names import canonical_team_id, derby_name, normalize_text, split_state, strip_accents


@pytest.mark.parametrize("raw,expected", [
    ("Palmeiras-SP", ("Palmeiras", "SP")),
    ("Palmeiras - SP", ("Palmeiras", "SP")),
    ("Botafogo RJ", ("Botafogo", "RJ")),
    ("Nacional (URU)", ("Nacional", "URU")),
    ("Barcelona-EQU", ("Barcelona", "EQU")),
    ("Sao Jose - POA", ("Sao Jose", "RS")),
    ("Flamengo", ("Flamengo", None)),
    ("Colo-Colo", ("Colo-Colo", None)),
    ("Sport Recife", ("Sport Recife", None)),
])
def test_split_state(raw, expected):
    assert split_state(raw) == expected


def test_normalize_text_handles_accents_and_initials():
    assert strip_accents("São Paulo Grêmio Avaí Ceará") == "Sao Paulo Gremio Avai Ceara"
    assert normalize_text("C. R. B.") == "crb"
    assert normalize_text("A.b.c.") == "abc"
    assert normalize_text("  Atlético-MG ") == "atletico mg"


@pytest.mark.parametrize("variants,team_id", [
    (["Palmeiras-SP", "Palmeiras", "Palmeiras - SP", "SE Palmeiras", "Sociedade Esportiva Palmeiras"], "palmeiras"),
    (["Flamengo-RJ", "Flamengo", "Flamengo - RJ", "CR Flamengo"], "flamengo"),
    (["Sao Paulo-SP", "São Paulo", "São Paulo - SP", "Sao Paulo", "São Paulo FC"], "sao paulo"),
    (["Corinthians-SP", "Corinthians", "Sport Club Corinthians Paulista"], "corinthians"),
    (["Atletico-MG", "Atlético-MG", "Atletico Mineiro", "Atlético - MG", "Atlético Mineiro - MG"], "atletico-mg"),
    (["Atletico-PR", "Athletico-PR", "Athletico", "Atletico Paranaense", "Athletico Paranaense",
      "Atlético - PR", "Atlético-PR"], "athletico-pr"),
    (["Atletico-GO", "Atlético-GO", "Atletico Goianiense", "Atlético - GO"], "atletico-go"),
    (["Vasco da Gama-RJ", "Vasco", "Vasco Da Gama RJ", "Vasco da Gama - RJ"], "vasco"),
    (["Gremio-RS", "Grêmio", "Gremio RS", "Grêmio - RS"], "gremio"),
    (["Sport-PE", "Sport", "Sport Recife", "Sport Club do Recife"], "sport"),
    (["Red Bull Bragantino-SP", "Red Bull Bragantino", "Bragantino", "Bragantino - SP"], "bragantino"),
    (["Fortaleza-CE", "Fortaleza", "Fortaleza EC", "Fortaleza FC", "Fortaleza - CE"], "fortaleza"),
    (["EC Bahia", "Bahia", "Bahia-BA", "Bahia - BA"], "bahia"),
    (["Csa-AL", "CSA", "Csa - AL", "C.s.a. - AL", "CS Alagoano"], "csa"),
    (["C. R. B. - AL", "Crb - AL", "CRB"], "crb"),
    (["Nautico-PE", "Náutico", "Nautico Capibaribe"], "nautico"),
])
def test_variants_map_to_same_team(variants, team_id):
    assert {canonical_team_id(v) for v in variants} == {team_id}


def test_state_column_is_used_for_lookup_but_cannot_split_known_clubs():
    assert canonical_team_id("Grêmio", "RS") == "gremio"
    # The 2003-2019 file has wrong state codes for some clubs ('Bahia' + 'BH').
    assert canonical_team_id("Bahia", "BH") == "bahia"
    assert canonical_team_id("Vitória", "ES") == "vitoria"


@pytest.mark.parametrize("raw,team_id", [
    ("Botafogo - PB", "botafogo-pb"),
    ("Botafogo SP", "botafogo-sp"),
    ("Flamengo - PI", "flamengo-pi"),
    ("Flamengo do Piauí - PI", "flamengo-pi"),
    ("Guaraní (PAR)", "guarani-par"),
    ("Guaraní-PAR", "guarani-par"),
    ("Guarani - CE", "guarani-ce"),
    ("Nacional (URU)", "nacional-uru"),
    ("Nacional-URU", "nacional-uru"),
    ("Nacional (PAR)", "nacional-par"),
    ("Santos AP", "santos-ap"),
    ("América - RN", "america-rn"),
    ("América-MG", "america-mg"),
])
def test_same_name_different_club(raw, team_id):
    assert canonical_team_id(raw) == team_id


def test_derby_names():
    assert derby_name("flamengo", "fluminense") == "Fla-Flu"
    assert derby_name("internacional", "gremio") == "Grenal"
    assert derby_name("flamengo", "gremio") is None
