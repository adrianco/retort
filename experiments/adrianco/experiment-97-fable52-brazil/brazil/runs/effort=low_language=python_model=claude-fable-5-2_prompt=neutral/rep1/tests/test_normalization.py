"""Feature: data quality handling (team names, dates, encoding)."""
import datetime as dt

import pytest

from brazilian_soccer_mcp.data import parse_date
from brazilian_soccer_mcp.teams import team_key


@pytest.mark.parametrize("raw, expected", [
    ("Palmeiras-SP", "Palmeiras"), ("Palmeiras - SP", "Palmeiras"), ("Palmeiras", "Palmeiras"),
    ("Flamengo-RJ", "Flamengo"), ("Sao Paulo", "São Paulo"), ("São Paulo - SP", "São Paulo"),
    ("São Paulo FC", "São Paulo"), ("Sport Club Corinthians Paulista", "Corinthians"),
    ("Gremio", "Grêmio"), ("Grêmio - RS", "Grêmio"), ("Avai-SC", "Avaí"),
    ("Atletico-MG", "Atlético-MG"), ("Atlético Mineiro", "Atlético-MG"), ("Atletico Mineiro", "Atlético-MG"),
    ("Atlético - GO", "Atlético-GO"), ("Atletico-PR", "Athletico-PR"),
    ("Athletico Paranaense - PR", "Athletico-PR"), ("Athletico", "Athletico-PR"),
    ("Vasco da Gama-RJ", "Vasco"), ("Vasco Da Gama RJ", "Vasco"), ("Sport Recife", "Sport"),
    ("America MG", "América-MG"), ("América FC (Minas Gerais)", "América-MG"),
    ("Bragantino", "Red Bull Bragantino"), ("C.s.a. - AL", "CSA"), ("Fortaleza EC", "Fortaleza"),
])
def test_team_name_variations_map_to_one_club(raw, expected):
    assert team_key(raw)[0] == expected


def test_same_base_name_in_other_state_is_a_different_club():
    assert team_key("Flamengo - PI")[0] != team_key("Flamengo - RJ")[0]
    assert team_key("Botafogo - PB")[0] != "Botafogo"
    assert team_key("Santos - AP")[0] != "Santos"
    assert team_key("Guaraní (PAR)")[0] == team_key("Guaraní-PAR")[0] != "Guarani"


@pytest.mark.parametrize("text", ["2023-09-24", "24/09/2023", "2023-09-24 18:30:00"])
def test_multiple_date_formats(text):
    assert parse_date(text) == dt.date(2023, 9, 24)


def test_bad_and_missing_dates():
    assert parse_date("NA") is None and parse_date("") is None
    with pytest.raises(ValueError):
        parse_date("next tuesday")


def test_utf8_names_are_preserved(kb):
    for name in ("São Paulo", "Grêmio", "Avaí", "Ceará", "Goiás", "Vitória"):
        assert name in kb.teams
    assert any(p.name == "Éder Militão" or "ã" in p.name for p in kb.players)


def test_minor_club_spellings_learned_across_files(kb):
    # "AE Altos" (BR-Football) and "Altos - PI" (cup file) are the same club
    assert kb.find_teams("AE Altos") == kb.find_teams("Altos - PI")
    assert kb.find_teams("ABC") == kb.find_teams("A.b.c. - RN")
