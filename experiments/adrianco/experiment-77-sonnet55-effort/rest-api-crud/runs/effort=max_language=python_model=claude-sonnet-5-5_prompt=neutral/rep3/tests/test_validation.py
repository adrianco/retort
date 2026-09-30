"""Unit tests for payload validation."""

from __future__ import annotations

from typing import Any

import pytest

from bookapi.validation import (
    MAX_AUTHOR_LENGTH,
    MAX_ISBN_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_YEAR,
    MIN_YEAR,
    ValidationError,
    validate_book,
)

MISSING = object()
VALID = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}


def errors_for(payload: dict[str, Any]) -> dict[str, str]:
    with pytest.raises(ValidationError) as excinfo:
        validate_book(payload)
    return excinfo.value.errors


def with_field(name: str, value: Any) -> dict[str, Any]:
    """A valid payload with ``name`` set to ``value`` (or removed when ``MISSING``)."""
    payload = dict(VALID)
    if value is MISSING:
        del payload[name]
    else:
        payload[name] = value
    return payload


# --- what is accepted -------------------------------------------------------------


def test_full_book_is_accepted_unchanged():
    assert validate_book(VALID) == VALID


def test_only_title_and_author_are_required():
    assert validate_book({"title": "Dune", "author": "Frank Herbert"}) == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": None,
        "isbn": None,
    }


def test_null_optional_fields_mean_not_set():
    book = validate_book({**VALID, "year": None, "isbn": None})
    assert book["year"] is None
    assert book["isbn"] is None


def test_text_is_trimmed_including_newlines_and_tabs():
    book = validate_book({"title": "\n  Dune \t", "author": "  Frank Herbert  ", "isbn": " 978-0-441-17271-9 "})
    assert (book["title"], book["author"], book["isbn"]) == ("Dune", "Frank Herbert", "978-0-441-17271-9")


def test_blank_isbn_means_not_set():
    assert validate_book({**VALID, "isbn": "   "})["isbn"] is None


def test_unknown_fields_such_as_id_are_ignored():
    assert validate_book({**VALID, "id": 99, "colour": "red"}) == VALID


def test_unicode_text_is_accepted():
    for text in ("Gabriel García Márquez", "村上春樹", "Ünïcödé 📚"):
        assert validate_book({"title": text, "author": text})["title"] == text


@pytest.mark.parametrize("year", [MIN_YEAR, 1605, 1965, 2026, MAX_YEAR])
def test_years_in_range_are_accepted(year: int):
    assert validate_book({**VALID, "year": year})["year"] == year


# --- title and author are required ------------------------------------------------


@pytest.mark.parametrize("field", ["title", "author"])
@pytest.mark.parametrize(
    "value, message",
    [
        pytest.param(MISSING, "is required", id="missing"),
        pytest.param(None, "is required", id="null"),
        pytest.param("", "must not be blank", id="empty"),
        pytest.param(" \t\n ", "must not be blank", id="whitespace"),
        pytest.param(42, "must be a string", id="number"),
        pytest.param(True, "must be a string", id="boolean"),
        pytest.param(["Dune"], "must be a string", id="list"),
        pytest.param({"name": "Dune"}, "must be a string", id="object"),
    ],
)
def test_title_and_author_must_be_non_blank_strings(field: str, value: Any, message: str):
    assert errors_for(with_field(field, value)) == {field: message}


def test_every_invalid_field_is_reported_at_once():
    payload = {"title": "", "author": None, "year": "1965", "isbn": 12345}
    assert errors_for(payload) == {
        "title": "must not be blank",
        "author": "is required",
        "year": "must be an integer",
        "isbn": "must be a string",
    }


def test_empty_payload_reports_both_required_fields():
    with pytest.raises(ValidationError) as excinfo:
        validate_book({})
    assert set(excinfo.value.errors) == {"title", "author"}
    assert "title: is required" in str(excinfo.value)


# --- year -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "year",
    [
        pytest.param(True, id="true"),
        pytest.param(False, id="false"),
        pytest.param("1965", id="numeric-string"),
        pytest.param(1965.5, id="fraction"),
        pytest.param(1965.0, id="integral-float"),
        pytest.param([1965], id="list"),
        pytest.param({"year": 1965}, id="object"),
    ],
)
def test_year_must_be_a_json_integer(year: Any):
    assert errors_for(with_field("year", year)) == {"year": "must be an integer"}


@pytest.mark.parametrize("year", [MIN_YEAR - 1, -44, MAX_YEAR + 1, 20230, 10**30])
def test_year_must_be_within_range(year: int):
    assert errors_for(with_field("year", year)) == {"year": f"must be between {MIN_YEAR} and {MAX_YEAR}"}


# --- text limits and content ------------------------------------------------------


@pytest.mark.parametrize(
    "field, limit",
    [("title", MAX_TITLE_LENGTH), ("author", MAX_AUTHOR_LENGTH), ("isbn", MAX_ISBN_LENGTH)],
)
def test_length_limit_is_inclusive_and_applies_after_trimming(field: str, limit: int):
    assert validate_book(with_field(field, f"  {'x' * limit}  "))[field] == "x" * limit
    assert errors_for(with_field(field, "x" * (limit + 1))) == {field: f"must be at most {limit} characters long"}


@pytest.mark.parametrize(
    "text",
    ["nul\x00byte", "line\nbreak", "tab\tinside", "bell\x07", "delete\x7f", "next\x85line"],
)
@pytest.mark.parametrize("field", ["title", "author", "isbn"])
def test_control_characters_are_rejected(field: str, text: str):
    assert errors_for(with_field(field, text)) == {field: "must not contain control characters"}


@pytest.mark.parametrize("field", ["title", "author", "isbn"])
def test_lone_surrogates_are_rejected(field: str):
    # Valid in a JSON document ("\ud800") but impossible to store as UTF-8.
    assert errors_for(with_field(field, "bad \ud800 text")) == {field: "must be valid Unicode text"}
