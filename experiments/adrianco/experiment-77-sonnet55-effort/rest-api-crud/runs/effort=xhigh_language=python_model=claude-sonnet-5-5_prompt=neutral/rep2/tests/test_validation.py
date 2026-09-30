import pytest

from bookapi.validation import validate_book


def test_valid_full_payload():
    clean, errors = validate_book({"title": "T", "author": "A", "year": 2000, "isbn": "123"})
    assert errors == {}
    assert clean == {"title": "T", "author": "A", "year": 2000, "isbn": "123"}


def test_create_fills_optional_fields_with_none():
    clean, errors = validate_book({"title": "T", "author": "A"})
    assert errors == {}
    assert clean == {"title": "T", "author": "A", "year": None, "isbn": None}


def test_blank_isbn_becomes_none():
    clean, _ = validate_book({"title": "T", "author": "A", "isbn": "   "})
    assert clean["isbn"] is None


def test_year_bounds_are_inclusive():
    assert validate_book({"title": "T", "author": "A", "year": 0})[1] == {}
    assert validate_book({"title": "T", "author": "A", "year": 9999})[1] == {}
    assert "year" in validate_book({"title": "T", "author": "A", "year": 10000})[1]


def test_isbn_too_long():
    _, errors = validate_book({"title": "T", "author": "A", "isbn": "1" * 33})
    assert "isbn" in errors


@pytest.mark.parametrize("payload", [None, [], "x", 1, True])
def test_non_object_payload(payload):
    clean, errors = validate_book(payload)
    assert clean == {}
    assert "body" in errors


def test_partial_returns_only_supplied_fields():
    clean, errors = validate_book({"year": 1999, "ignored": "x"}, partial=True)
    assert errors == {}
    assert clean == {"year": 1999}


def test_partial_requires_a_known_field():
    _, errors = validate_book({"ignored": "x"}, partial=True)
    assert "body" in errors


def test_partial_still_rejects_blank_required_fields():
    _, errors = validate_book({"title": " "}, partial=True)
    assert "title" in errors
