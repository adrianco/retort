"""Unit tests for dataset parsing helpers."""

import datetime

import pytest

from brazilian_soccer_mcp.data import parse_date
from brazilian_soccer_mcp.queries import QueryError, resolve_competition


@pytest.mark.parametrize("text, expected", [
    ("2023-09-24", datetime.date(2023, 9, 24)),
    ("2012-05-19 18:30:00", datetime.date(2012, 5, 19)),
    ("29/03/2003", datetime.date(2003, 3, 29)),
    ("NA", None),
    ("", None),
    ("not a date", None),
])
def test_dates_in_every_dataset_format_are_parsed(text, expected):
    assert parse_date(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Brasileirão", "Brasileirão Série A"),
    ("serie a", "Brasileirão Série A"),
    ("Série B", "Brasileirão Série B"),
    ("Brasileirão Série C", "Brasileirão Série C"),
    ("Copa do Brasil", "Copa do Brasil"),
    ("brazilian cup", "Copa do Brasil"),
    ("Copa Libertadores", "Copa Libertadores"),
    (None, None),
    ("all", None),
])
def test_competition_names_are_understood(text, expected):
    assert resolve_competition(text) == expected


def test_unknown_competition_is_explained():
    with pytest.raises(QueryError) as error:
        resolve_competition("Premier League")
    assert error.value.code == "unknown_competition"
