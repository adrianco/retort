"""Feature: Data quality - team names, dates and encodings are normalised."""

from datetime import date

import pytest

from brazilian_soccer.normalize import (
    fold, known_club, normalize_competition, parse_date, split_team_name,
)


@pytest.mark.parametrize("raw, expected", [
    ("Palmeiras-SP", "Palmeiras"),
    ("Palmeiras - SP", "Palmeiras"),
    ("Palmeiras", "Palmeiras"),
    ("Sport Club Corinthians Paulista", "Corinthians"),
    ("Sao Paulo", "São Paulo"),
    ("São Paulo FC", "São Paulo"),
    ("Gremio RS", "Grêmio"),
    ("Atletico-MG", "Atlético Mineiro"),
    ("Atlético - MG", "Atlético Mineiro"),
    ("Atletico Mineiro", "Atlético Mineiro"),
    ("Atlético - GO", "Atlético Goianiense"),
    ("Athletico-PR", "Athletico Paranaense"),
    ("Atlético Paranaense - PR", "Athletico Paranaense"),
    ("Vasco", "Vasco da Gama"),
    ("Vasco Da Gama RJ", "Vasco da Gama"),
    ("Sport-PE", "Sport Recife"),
    ("C.s.a. - AL", "CSA"),
    ("C. R. B. - AL", "CRB"),
    ("América FC (Minas Gerais)", "América Mineiro"),
])
def test_known_club_spellings_map_to_one_name(raw, expected):
    assert known_club(raw) == expected


def test_same_short_name_in_another_state_is_a_different_club():
    # Given clubs that share a name with a famous one
    # Then they are not confused with it
    assert known_club("Botafogo - PB") is None
    assert known_club("Santos AP") is None
    assert known_club("Atlético") is None  # ambiguous without a state


def test_split_team_name_extracts_state_and_country_codes():
    assert split_team_name("Nacional (URU)")[:2] == ("nacional", "URU")
    assert split_team_name("Barcelona-EQU")[:2] == ("barcelona", "EQU")
    assert split_team_name("Colo-Colo")[:2] == ("colo colo", None)
    assert split_team_name("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")[1] == "RJ"


def test_fold_strips_accents_and_case():
    assert fold("São Paulo") == "sao paulo"
    assert fold("GRÊMIO") == "gremio"
    assert fold("Avaí") == "avai"


@pytest.mark.parametrize("text, expected", [
    ("2023-09-24", date(2023, 9, 24)),
    ("29/03/2003", date(2003, 3, 29)),
    ("2012-05-19 18:30:00", date(2012, 5, 19)),
])
def test_all_dataset_date_formats_are_parsed(text, expected):
    assert parse_date(text) == expected


@pytest.mark.parametrize("text", ["NA", "", None, "not a date", "31/02/2020"])
def test_unparseable_dates_return_none(text):
    assert parse_date(text) is None


@pytest.mark.parametrize("text, expected", [
    ("Brasileirão", "Brasileirão"), ("brasileirao", "Brasileirão"), ("Serie A", "Brasileirão"),
    ("Copa do Brasil", "Copa do Brasil"), ("Brazilian Cup", "Copa do Brasil"),
    ("libertadores", "Copa Libertadores"), ("Série B", "Série B"), ("serie c", "Série C"),
    (None, None), ("", None),
])
def test_competition_names_are_normalised(text, expected):
    assert normalize_competition(text) == expected


def test_unknown_competition_is_rejected():
    with pytest.raises(ValueError):
        normalize_competition("Premier League")
