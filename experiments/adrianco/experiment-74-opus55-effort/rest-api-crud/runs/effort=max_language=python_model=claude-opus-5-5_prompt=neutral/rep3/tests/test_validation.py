"""Unit tests of the book payload validation rules."""

import pytest

from bookapi.validation import (
    MAX_AUTHOR_LENGTH,
    MAX_ISBN_LENGTH,
    MAX_TITLE_LENGTH,
    MIN_YEAR,
    ValidationError,
    latest_valid_year,
    validate_book,
)

VALID = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


def test_valid_book_is_returned_normalised():
    payload = {
        "title": "  Dune ",
        "author": "Frank Herbert\n",
        "year": 1965,
        "isbn": " 978-0441013593 ",
        "genre": "science fiction",  # unknown fields are dropped
    }
    assert validate_book(payload) == VALID


def test_year_and_isbn_are_optional():
    assert validate_book({"title": "Dune", "author": "Frank Herbert"}) == {
        "title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None,
    }


def test_blank_isbn_is_treated_as_absent():
    assert validate_book({**VALID, "isbn": "  "})["isbn"] is None


@pytest.mark.parametrize("year", [MIN_YEAR, 1965, latest_valid_year()])
def test_years_in_range_are_accepted(year):
    assert validate_book({**VALID, "year": year})["year"] == year


def test_values_at_the_length_limits_are_accepted():
    payload = {
        "title": "t" * MAX_TITLE_LENGTH,
        "author": "a" * MAX_AUTHOR_LENGTH,
        "isbn": "9" * MAX_ISBN_LENGTH,
    }
    assert validate_book(payload) == {**payload, "year": None}


YEAR_RANGE = f"year must be between {MIN_YEAR} and {latest_valid_year()}"


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("title", None, "title is required"),
        ("title", "", "title must not be blank"),
        ("title", " \t\n", "title must not be blank"),
        ("title", 1984, "title must be a string"),
        ("title", "t" * (MAX_TITLE_LENGTH + 1),
         f"title must be at most {MAX_TITLE_LENGTH} characters"),
        ("author", None, "author is required"),
        ("author", ["George Orwell"], "author must be a string"),
        ("author", "a" * (MAX_AUTHOR_LENGTH + 1),
         f"author must be at most {MAX_AUTHOR_LENGTH} characters"),
        ("year", "1965", "year must be an integer"),
        ("year", 1965.0, "year must be an integer"),
        ("year", True, "year must be an integer"),
        ("year", MIN_YEAR - 1, YEAR_RANGE),
        ("year", latest_valid_year() + 1, YEAR_RANGE),
        ("isbn", 9780441013593, "isbn must be a string"),
        ("isbn", "9" * (MAX_ISBN_LENGTH + 1),
         f"isbn must be at most {MAX_ISBN_LENGTH} characters"),
    ],
)
def test_invalid_field_is_rejected(field, value, message):
    with pytest.raises(ValidationError) as excinfo:
        validate_book({**VALID, field: value})
    assert excinfo.value.errors == {field: message}


def test_every_error_is_reported_together():
    with pytest.raises(ValidationError) as excinfo:
        validate_book({"year": "soon"})
    assert excinfo.value.errors == {
        "title": "title is required",
        "author": "author is required",
        "year": "year must be an integer",
    }
