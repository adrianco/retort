"""Unit tests for the payload validator, exercised without HTTP."""

from __future__ import annotations

import datetime

import pytest

from bookapi.validation import MAX_ISBN_LEN, MAX_TITLE_LEN, validate_book_payload


def test_valid_full_payload_is_accepted():
    values, errors = validate_book_payload(
        {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
    )
    assert errors == {}
    assert values == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "9780441013593",
    }


def test_optional_fields_default_to_none_on_a_full_payload():
    values, errors = validate_book_payload({"title": "T", "author": "A"})
    assert errors == {}
    assert values["year"] is None and values["isbn"] is None


def test_missing_required_fields_are_reported():
    _, errors = validate_book_payload({})
    assert set(errors) == {"title", "author"}


def test_partial_payload_omits_untouched_fields():
    values, errors = validate_book_payload({"title": "Only"}, partial=True)
    assert errors == {}
    assert values == {"title": "Only"}


def test_partial_payload_rejects_an_empty_object():
    _, errors = validate_book_payload({}, partial=True)
    assert "_body" in errors


def test_non_dict_payload_is_rejected():
    for payload in ([], "text", 7, None):
        _, errors = validate_book_payload(payload)
        assert "_body" in errors


def test_numeric_year_strings_are_coerced():
    values, errors = validate_book_payload({"title": "T", "author": "A", "year": "1984"})
    assert errors == {}
    assert values["year"] == 1984


def test_boolean_year_is_not_treated_as_an_integer():
    _, errors = validate_book_payload({"title": "T", "author": "A", "year": False})
    assert "year" in errors


def test_year_may_be_next_year_but_not_later():
    next_year = datetime.date.today().year + 1
    _, errors = validate_book_payload({"title": "T", "author": "A", "year": next_year})
    assert errors == {}

    _, errors = validate_book_payload({"title": "T", "author": "A", "year": next_year + 1})
    assert "year" in errors


@pytest.mark.parametrize("isbn", ["9780441013593", "978-0-441-01359-3", "043942089X", "0 4394 208"])
def test_accepted_isbn_shapes(isbn):
    values, errors = validate_book_payload({"title": "T", "author": "A", "isbn": isbn})
    assert errors == {}
    assert values["isbn"] == isbn.strip()


@pytest.mark.parametrize("isbn", ["no-digits-here!", "978/0441013593", "9" * (MAX_ISBN_LEN + 1)])
def test_rejected_isbn_shapes(isbn):
    _, errors = validate_book_payload({"title": "T", "author": "A", "isbn": isbn})
    assert "isbn" in errors


def test_blank_isbn_is_normalised_to_none():
    values, errors = validate_book_payload({"title": "T", "author": "A", "isbn": "   "})
    assert errors == {}
    assert values["isbn"] is None


def test_over_long_title_is_rejected():
    _, errors = validate_book_payload({"title": "x" * (MAX_TITLE_LEN + 1), "author": "A"})
    assert "title" in errors


def test_title_at_the_length_limit_is_accepted():
    _, errors = validate_book_payload({"title": "x" * MAX_TITLE_LEN, "author": "A"})
    assert errors == {}


def test_unknown_fields_are_dropped():
    values, _ = validate_book_payload(
        {"title": "T", "author": "A", "id": 99, "created_at": "yesterday"}
    )
    assert set(values) == {"title", "author", "year", "isbn"}
