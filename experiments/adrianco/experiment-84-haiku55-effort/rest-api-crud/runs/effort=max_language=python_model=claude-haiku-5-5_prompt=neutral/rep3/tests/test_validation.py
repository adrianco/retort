from datetime import date

import pytest

from bookapi.errors import ApiError
from bookapi.validation import (
    MAX_TEXT_LENGTH,
    normalize_isbn,
    validate_author_filter,
    validate_book,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("978-0-306-40615-7", "9780306406157"),  # ISBN-13 with hyphens
        ("0-306-40615-2", "0306406152"),  # ISBN-10 with hyphens
        ("0 8044 2957 X", "080442957X"),  # ISBN-10 ending in X, with spaces
        ("080442957x", "080442957X"),  # lowercase x is accepted
    ],
)
def test_normalize_isbn_accepts_valid_isbns(raw, expected):
    assert normalize_isbn(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "978-0-306-40615-8",  # ISBN-13 with a wrong check digit
        "0-306-40615-3",  # ISBN-10 with a wrong check digit
        "977-0-306-40615-8",  # check digit is right but the prefix must be 978 or 979
        "978030640615",  # 12 digits
        "97803064061577",  # 14 digits
        "0-306-4061X-2",  # X is only allowed as the final ISBN-10 character
        "97803064061X7",  # X is not allowed in ISBN-13
        "abcdefghij",  # not digits
        "",
    ],
)
def test_normalize_isbn_rejects_invalid_isbns(raw):
    assert normalize_isbn(raw) is None


def test_validate_book_trims_text_and_normalizes_isbn():
    fields = validate_book(
        {"title": "  Dune ", "author": " Frank Herbert ", "year": 1965, "isbn": "0-441-17271-7"}
    )

    assert fields == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "0441172717",
    }


def test_validate_book_accepts_null_optional_fields():
    fields = validate_book({"title": "Untitled", "author": "Anon", "year": None, "isbn": None})

    assert fields["year"] is None
    assert fields["isbn"] is None


def test_validate_book_rejects_non_string_isbn():
    with pytest.raises(ApiError) as excinfo:
        validate_book({"title": "T", "author": "A", "isbn": 9780547928227})

    assert excinfo.value.details == {"isbn": "Must be a string"}


def test_validate_book_reports_every_invalid_field():
    with pytest.raises(ApiError) as excinfo:
        validate_book({"title": "", "author": 42, "year": "1965", "isbn": "nope"})

    assert excinfo.value.status_code == 400
    assert excinfo.value.details == {
        "title": "Must not be blank",
        "author": "Must be a string",
        "year": "Must be an integer",
        "isbn": "Must be a valid ISBN-10 or ISBN-13",
    }


@pytest.mark.parametrize("year", [1, date.today().year + 1])
def test_validate_book_accepts_year_bounds(year):
    assert validate_book({"title": "T", "author": "A", "year": year})["year"] == year


@pytest.mark.parametrize("year", [0, -5, date.today().year + 2, True, 1965.0])
def test_validate_book_rejects_bad_years(year):
    with pytest.raises(ApiError) as excinfo:
        validate_book({"title": "T", "author": "A", "year": year})

    assert "year" in excinfo.value.details


def test_validate_book_limits_text_length():
    with pytest.raises(ApiError) as excinfo:
        validate_book({"title": "x" * (MAX_TEXT_LENGTH + 1), "author": "A"})

    assert excinfo.value.details == {"title": f"Must be at most {MAX_TEXT_LENGTH} characters"}
    fields = validate_book({"title": "x" * MAX_TEXT_LENGTH, "author": "A"})
    assert len(fields["title"]) == MAX_TEXT_LENGTH


def test_validate_author_filter_trims_and_passes_none_through():
    assert validate_author_filter(None) is None
    assert validate_author_filter("  George Orwell ") == "George Orwell"


@pytest.mark.parametrize("value", ["", "   "])
def test_validate_author_filter_rejects_blank_values(value):
    with pytest.raises(ApiError) as excinfo:
        validate_author_filter(value)

    assert excinfo.value.details == {"author": "Must not be blank"}
