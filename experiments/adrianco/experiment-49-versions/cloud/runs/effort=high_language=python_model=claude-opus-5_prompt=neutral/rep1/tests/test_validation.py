"""Unit tests for the payload validation rules."""

from __future__ import annotations

import pytest

from bookapi.validation import (
    MAX_AUTHOR_LENGTH,
    MAX_TITLE_LENGTH,
    ValidationError,
    parse_book,
)


def test_parse_book_normalises_a_full_payload():
    book = parse_book(
        {
            "title": "  Dune ",
            "author": "\tFrank Herbert\n",
            "year": 1965,
            "isbn": " 978-0-441-01359-3 ",
        }
    )

    assert book == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0-441-01359-3",
    }


def test_optional_fields_default_to_none():
    assert parse_book({"title": "T", "author": "A"}) == {
        "title": "T",
        "author": "A",
        "year": None,
        "isbn": None,
    }


@pytest.mark.parametrize("value", [None, "", "   "])
def test_blank_optional_fields_become_none(value):
    book = parse_book({"title": "T", "author": "A", "year": value, "isbn": value})

    assert book["year"] is None
    assert book["isbn"] is None


def test_numeric_year_strings_are_coerced():
    assert parse_book({"title": "T", "author": "A", "year": " 1949 "})["year"] == 1949


@pytest.mark.parametrize(
    "isbn",
    ["0451524934", "045152493X", "9780451524935", "978-0-452-28423-4", "0 451 52493 4"],
)
def test_valid_isbn_formats_are_accepted(isbn):
    assert parse_book({"title": "T", "author": "A", "isbn": isbn})["isbn"] == isbn.strip()


@pytest.mark.parametrize(
    "payload, expected_fields",
    [
        ({}, {"title", "author"}),
        ({"title": "T"}, {"author"}),
        ({"title": "", "author": "A"}, {"title"}),
        ({"title": "T", "author": 7}, {"author"}),
        ({"title": "T", "author": "A", "year": True}, {"year"}),
        ({"title": "T", "author": "A", "year": 3.5}, {"year"}),
        ({"title": "T", "author": "A", "year": 0}, {"year"}),
        ({"title": "T", "author": "A", "year": 10000}, {"year"}),
        ({"title": "T", "author": "A", "isbn": "12345"}, {"isbn"}),
        ({"title": "T", "author": "A", "isbn": 9780451524935}, {"isbn"}),
        ({"title": "x" * (MAX_TITLE_LENGTH + 1), "author": "A"}, {"title"}),
        ({"title": "T", "author": "x" * (MAX_AUTHOR_LENGTH + 1)}, {"author"}),
    ],
)
def test_invalid_payloads_raise(payload, expected_fields):
    with pytest.raises(ValidationError) as exc_info:
        parse_book(payload)

    assert set(exc_info.value.errors) == expected_fields


@pytest.mark.parametrize("payload", ["a string", ["a", "list"], 42, None])
def test_non_object_payloads_raise(payload):
    with pytest.raises(ValidationError) as exc_info:
        parse_book(payload)

    assert "body" in exc_info.value.errors


def test_all_errors_are_collected_in_one_pass():
    with pytest.raises(ValidationError) as exc_info:
        parse_book({"year": "soon", "isbn": "bad"})

    assert set(exc_info.value.errors) == {"title", "author", "year", "isbn"}


def test_boundary_lengths_are_allowed():
    book = parse_book(
        {"title": "x" * MAX_TITLE_LENGTH, "author": "y" * MAX_AUTHOR_LENGTH}
    )

    assert len(book["title"]) == MAX_TITLE_LENGTH
    assert len(book["author"]) == MAX_AUTHOR_LENGTH
