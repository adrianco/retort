"""
Unit tests for the unicode / date / number helpers.

Context
-------
These cover the hazards TASK.md lists under "Data Quality Notes" at the lowest
level, where they are cheap to pin down: accent folding, the four ways a club
name carries its state or country, three date formats and the several spellings
of "no data".
"""

from __future__ import annotations

import datetime as dt

import pytest

from brazilian_soccer import text


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Grêmio", "Gremio"),
        ("São Paulo", "Sao Paulo"),
        ("Avaí", "Avai"),
        ("Atlético-MG", "Atletico-MG"),
        ("Peñarol", "Penarol"),
        ("Criciúma", "Criciuma"),
    ],
)
def test_strip_accents(raw, expected):
    assert text.strip_accents(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Ponte Preta", "ponte preta"),
        ("A.b.c.", "abc"),
        ("C. R. B.", "crb"),
        ("C.r.a.c.", "crac"),
        ("  Rentistas  ", "rentistas"),
        ("Newell's Old Boys", "newells old boys"),
        ("4 de Julho EC", "4 de julho ec"),
    ],
)
def test_normalize_name(raw, expected):
    assert text.normalize_name(raw) == expected


@pytest.mark.parametrize(
    "raw, base, qualifier",
    [
        ("Palmeiras-SP", "Palmeiras", "SP"),
        ("América - MG", "América", "MG"),
        ("America MG", "America", "MG"),
        ("Nacional (URU)", "Nacional", "URU"),
        ("Nacional-URU", "Nacional", "URU"),
        ("Barcelona-EQU", "Barcelona", "ECU"),
        ("América FC (Minas Gerais)", "América FC", "MG"),
        ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ",
         "Boavista Sport Club", "RJ"),
        ("Flamengo", "Flamengo", None),
        ("Colo-Colo", "Colo-Colo", None),
        ("Sport Boys", "Sport Boys", None),
        ("Ind. Santa Fe", "Ind. Santa Fe", None),
    ],
)
def test_split_qualifier(raw, base, qualifier):
    assert text.split_qualifier(raw) == (base, qualifier)


def test_split_qualifier_never_consumes_the_whole_name():
    assert text.split_qualifier("SP") == ("SP", None)
    assert text.split_qualifier("MG") == ("MG", None)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2023-09-24", dt.date(2023, 9, 24)),
        ("29/03/2003", dt.date(2003, 3, 29)),
        ("2012-05-19 18:30:00", dt.date(2012, 5, 19)),
        ("2012-05-19T18:30:00", dt.date(2012, 5, 19)),
        ("NA", None),
        ("", None),
        (None, None),
        ("not a date", None),
    ],
)
def test_parse_date(raw, expected):
    assert text.parse_date(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [("2012-05-19 18:30:00", "18:30"), ("20:00:00", "20:00"), ("NA", None), ("", None)],
)
def test_parse_time(raw, expected):
    assert text.parse_time(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [("2", 2), ("2.0", 2), (2.0, 2), (" 3 ", 3), ("NA", None), ("-", None), ("", None)],
)
def test_parse_int(raw, expected):
    assert text.parse_int(raw) == expected


@pytest.mark.parametrize("raw", ["", "NA", "n/a", "NaN", "None", "-", None])
def test_is_missing(raw):
    assert text.is_missing(raw) is True


@pytest.mark.parametrize("raw", ["0", "Flamengo", 0, 1.5])
def test_is_not_missing(raw):
    assert text.is_missing(raw) is False


def test_slugify():
    assert text.slugify("São Paulo-SP") == "sao-paulo-sp"
    assert text.slugify("Red Bull Bragantino") == "red-bull-bragantino"


def test_titleize_keeps_portuguese_particles_lowercase():
    assert text.titleize("vasco da gama") == "Vasco da Gama"
    assert text.titleize("CLUBE DO REMO") == "Clube do REMO"


def test_titleize_leaves_acronyms_and_mixed_case_alone():
    assert text.titleize("ABC") == "ABC"
    assert text.titleize("CRB") == "CRB"
    assert text.titleize("Red Bull Bragantino") == "Red Bull Bragantino"
