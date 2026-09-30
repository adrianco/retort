import pytest

from bookapi.validation import validate_book


def test_valid_payload_is_returned_cleaned():
    fields, errors = validate_book(
        {"title": " Dune ", "author": "Frank Herbert", "year": 1965, "isbn": " 123 "}
    )
    assert errors == {}
    assert fields == {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}


def test_missing_required_fields_are_reported():
    fields, errors = validate_book({})
    assert fields == {}
    assert errors == {"title": "title is required", "author": "author is required"}


def test_partial_mode_does_not_require_any_field():
    assert validate_book({}, partial=True) == ({}, {})
    assert validate_book({"year": 2000}, partial=True) == ({"year": 2000}, {})


def test_partial_mode_still_validates_supplied_fields():
    _, errors = validate_book({"title": ""}, partial=True)
    assert "title" in errors


def test_blank_isbn_becomes_null():
    fields, errors = validate_book({"title": "T", "author": "A", "isbn": "   "})
    assert errors == {}
    assert fields["isbn"] is None


@pytest.mark.parametrize("year", [0, 1, 1949, 9999])
def test_year_boundaries_accepted(year):
    _, errors = validate_book({"title": "T", "author": "A", "year": year})
    assert errors == {}


@pytest.mark.parametrize("year", [-1, 10000, "2000", 20.5, True, [], {}])
def test_bad_years_rejected(year):
    _, errors = validate_book({"title": "T", "author": "A", "year": year})
    assert "year" in errors


def test_isbn_length_limit():
    _, errors = validate_book({"title": "T", "author": "A", "isbn": "9" * 33})
    assert "isbn" in errors
