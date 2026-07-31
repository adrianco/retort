"""Unit tests for text, date and number normalisation.

Context
-------
These cover the "Data Quality Notes" section of the specification directly:
team-name variations, multiple date formats and UTF-8 Brazilian Portuguese.
They are pure functions, so no fixtures or data files are needed.
"""

from __future__ import annotations

import datetime as dt

import pytest

from brazilian_soccer.normalization import (
    drop_filler,
    name_variants,
    normalize_text,
    parse_date,
    parse_float,
    parse_int,
    parse_season,
    parse_time,
    slugify,
    split_state_suffix,
    strip_accents,
)


@pytest.mark.parametrize("raw,expected", [
    ("São Paulo", "Sao Paulo"),
    ("Grêmio", "Gremio"),
    ("Avaí", "Avai"),
    ("Atlético Goianiense", "Atletico Goianiense"),
    ("Criciúma", "Criciuma"),
    ("Náutico", "Nautico"),
    ("Fortaleza", "Fortaleza"),
])
def test_strip_accents_handles_portuguese(raw, expected):
    assert strip_accents(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("Palmeiras-SP", "palmeiras sp"),
    ("América - MG", "america mg"),
    ("Sport Club do Recife", "sport club do recife"),
    ("Boavista Sport Club (antigo EC Barreira) - RJ", "boavista sport club rj"),
    ("  Rentistas  ", "rentistas"),
])
def test_normalize_text(raw, expected):
    assert normalize_text(raw) == expected


def test_normalize_text_can_keep_parentheticals():
    assert normalize_text("Nacional (URU)", drop_parentheticals=False) == "nacional uru"


def test_name_variants_prefers_the_most_specific_spelling():
    variants = name_variants("Nacional (URU)")
    assert variants[0] == "nacional uru"
    assert "nacional" in variants


def test_name_variants_glue_dotted_initialisms():
    assert "abc rn" in name_variants("A.b.c. - RN")
    assert "crb al" in name_variants("C.r.b. - AL")


@pytest.mark.parametrize("raw,base,state", [
    ("palmeiras sp", "palmeiras", "sp"),
    ("santos", "santos", None),
    ("vasco da gama rj", "vasco da gama", "rj"),
    ("america mg", "america", "mg"),
    ("sao paulo", "sao paulo", None),
])
def test_split_state_suffix(raw, base, state):
    assert split_state_suffix(raw) == (base, state)


@pytest.mark.parametrize("raw,expected", [
    ("ec bahia", "bahia"),
    ("fortaleza fc", "fortaleza"),
    ("ceara sporting club", "ceara"),
    ("sport club do recife", "sport recife"),
    ("santos", "santos"),
])
def test_drop_filler(raw, expected):
    assert drop_filler(raw) == expected


def test_drop_filler_never_empties_a_name():
    assert drop_filler("fc") == "fc"


def test_slugify():
    assert slugify("Atlético Mineiro") == "atletico-mineiro"
    assert slugify("Vasco da Gama", "rj") == "vasco-da-gama-rj"


@pytest.mark.parametrize("raw,expected", [
    ("2023-09-24", dt.date(2023, 9, 24)),
    ("2012-05-19 18:30:00", dt.date(2012, 5, 19)),
    ("29/03/2003", dt.date(2003, 3, 29)),
    ("Jul 1, 2004", dt.date(2004, 7, 1)),
    ("NA", None),
    ("-", None),
    ("", None),
    (None, None),
])
def test_parse_date_handles_every_format_in_the_data(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("2012-05-19 18:30:00", "18:30"),
    ("20:00:00", "20:00"),
    ("NA", None),
    ("", None),
])
def test_parse_time(raw, expected):
    assert parse_time(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("2", 2), ("2.0", 2), ("0", 0), ("-", None), ("NA", None), ("", None),
    (None, None), (3, 3),
])
def test_parse_int_tolerates_sentinels(raw, expected):
    assert parse_int(raw) == expected


def test_parse_float():
    assert parse_float("75.0") == 75.0
    assert parse_float("NA") is None


@pytest.mark.parametrize("raw,expected", [
    ("2019", 2019), (2019, 2019), ("2019/20", 2019), ("NA", None), ("", None),
])
def test_parse_season(raw, expected):
    assert parse_season(raw) == expected
