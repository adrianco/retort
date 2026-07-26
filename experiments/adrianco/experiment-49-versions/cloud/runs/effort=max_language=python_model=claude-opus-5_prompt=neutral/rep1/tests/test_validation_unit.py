"""Unit tests for the validation module, exercised without HTTP."""

import pytest

from bookapi.validation import (
    ValidationError,
    validate_book_update,
    validate_new_book,
    validate_positive_int,
)


def test_validate_new_book_normalises_the_payload():
    book = validate_new_book(
        {"title": " Dune ", "author": " Frank Herbert ", "year": "1965"}
    )

    assert book == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": None,
    }


def test_validate_new_book_collects_every_error():
    with pytest.raises(ValidationError) as excinfo:
        validate_new_book({"title": "", "year": "soon", "isbn": "x"})

    assert {error["field"] for error in excinfo.value.errors} == {
        "title",
        "author",
        "year",
        "isbn",
    }


def test_validate_book_update_returns_only_supplied_fields():
    assert validate_book_update({"year": 1965, "extra": "ignored"}) == {
        "year": 1965
    }


def test_validate_book_update_rejects_an_empty_payload():
    with pytest.raises(ValidationError):
        validate_book_update({})


def test_validate_positive_int_enforces_bounds():
    assert validate_positive_int("limit", "10", minimum=0, maximum=100) == 10

    with pytest.raises(ValidationError):
        validate_positive_int("limit", "101", minimum=0, maximum=100)
