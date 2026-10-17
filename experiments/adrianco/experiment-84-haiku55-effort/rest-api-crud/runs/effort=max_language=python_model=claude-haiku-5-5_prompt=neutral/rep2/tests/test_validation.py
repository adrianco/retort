"""Unit tests for the validation helpers, independent of Flask."""

from datetime import date

import pytest

from validation import ValidationError, parse_author_filter, parse_book


def test_parse_book_trims_text_and_defaults_optional_fields_to_none():
    book = parse_book({"title": "  Dune  ", "author": " Frank Herbert "})

    assert book == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": None,
        "isbn": None,
    }


def test_parse_book_reports_every_invalid_field_at_once():
    with pytest.raises(ValidationError) as excinfo:
        parse_book({"title": "", "author": None, "year": "soon", "isbn": "nope"})

    assert set(excinfo.value.errors) == {"title", "author", "year", "isbn"}


@pytest.mark.parametrize("year", [1, 1949, date.today().year + 1])
def test_parse_book_accepts_years_in_range(year):
    assert parse_book({"title": "T", "author": "A", "year": year})["year"] == year


def test_parse_author_filter_trims_and_passes_through_none():
    assert parse_author_filter(None) is None
    assert parse_author_filter("  Orwell ") == "Orwell"


def test_parse_author_filter_rejects_blank_values():
    with pytest.raises(ValidationError) as excinfo:
        parse_author_filter("   ")

    assert excinfo.value.errors == {"author": "must not be blank"}
