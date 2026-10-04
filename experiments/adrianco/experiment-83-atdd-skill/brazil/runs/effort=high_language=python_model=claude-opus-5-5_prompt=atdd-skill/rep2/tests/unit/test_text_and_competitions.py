"""Unit tests: date formats, name normalisation and competition names."""
import datetime

import pytest

from brazilian_soccer_mcp import competitions
from brazilian_soccer_mcp.text import parse_date, plain


@pytest.mark.parametrize("value, expected", [
    ("2023-09-24", datetime.date(2023, 9, 24)),
    ("2012-05-19 18:30:00", datetime.date(2012, 5, 19)),
    ("29/03/2003", datetime.date(2003, 3, 29)),
    ("NA", None),
    ("", None),
    ("not a date", None),
])
def test_parses_every_date_format_in_the_datasets(value, expected):
    assert parse_date(value) == expected


def test_plain_names_ignore_accents_case_and_punctuation():
    assert plain("Grêmio") == "gremio"
    assert plain("Avaí") == "avai"
    assert plain("A.b.c.") == "abc"


@pytest.mark.parametrize("question, expected", [
    ("Brasileirão", competitions.SERIE_A),
    ("serie a", competitions.SERIE_A),
    ("Série B", competitions.SERIE_B),
    ("copa do brasil", competitions.COPA_DO_BRASIL),
    ("Libertadores", competitions.LIBERTADORES),
    ("Copa Libertadores da América", competitions.LIBERTADORES),
])
def test_resolves_competition_names(question, expected):
    assert competitions.resolve(question) == expected


def test_rejects_unknown_competitions():
    with pytest.raises(competitions.UnknownCompetition):
        competitions.resolve("Premier League")
