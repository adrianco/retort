"""Unit tests for the payload validation layer."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from validation import MAX_TEXT_LENGTH, ValidationError, validate_book

VALID = {"title": "Dune", "author": "Frank Herbert"}


def errors_for(payload):
    with pytest.raises(ValidationError) as excinfo:
        validate_book(payload)
    return excinfo.value.errors


def test_optional_fields_default_to_none():
    assert validate_book(VALID) == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": None,
        "isbn": None,
    }


def test_title_and_author_are_trimmed():
    cleaned = validate_book({"title": "  Dune \n", "author": "\tFrank Herbert "})
    assert cleaned["title"] == "Dune"
    assert cleaned["author"] == "Frank Herbert"


@pytest.mark.parametrize("field", ["title", "author"])
def test_required_fields_must_be_present(field):
    payload = {key: value for key, value in VALID.items() if key != field}
    assert errors_for(payload) == {field: f"'{field}' is required"}


@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
@pytest.mark.parametrize("field", ["title", "author"])
def test_required_fields_must_not_be_blank(field, value):
    assert field in errors_for({**VALID, field: value})


@pytest.mark.parametrize("value", [None, 42, ["Dune"], {"a": 1}])
def test_title_must_be_a_string(value):
    assert errors_for({**VALID, "title": value}) == {"title": "'title' must be a string"}


def test_text_length_is_capped():
    assert validate_book({**VALID, "title": "x" * MAX_TEXT_LENGTH})["title"]
    assert "title" in errors_for({**VALID, "title": "x" * (MAX_TEXT_LENGTH + 1)})


def test_all_field_errors_are_reported_at_once():
    assert set(errors_for({"year": "old", "isbn": "nope"})) == {
        "title",
        "author",
        "year",
        "isbn",
    }


def test_unknown_fields_are_rejected():
    assert errors_for({**VALID, "publisher": "Ace"}) == {
        "publisher": "'publisher' is not a recognised field"
    }


@pytest.mark.parametrize("payload", [None, [], "Dune", 7])
def test_payload_must_be_an_object(payload):
    assert errors_for(payload) == {"body": "Request body must be a JSON object"}


class TestYear:
    def test_accepts_null_and_integers(self):
        assert validate_book({**VALID, "year": None})["year"] is None
        assert validate_book({**VALID, "year": 1965})["year"] == 1965

    def test_accepts_next_year_but_not_beyond(self):
        next_year = datetime.now(timezone.utc).year + 1
        assert validate_book({**VALID, "year": next_year})["year"] == next_year
        assert "year" in errors_for({**VALID, "year": next_year + 1})

    @pytest.mark.parametrize("value", [999, -100, 99999])
    def test_rejects_out_of_range(self, value):
        assert "year" in errors_for({**VALID, "year": value})

    @pytest.mark.parametrize("value", ["1965", 1965.0, True])
    def test_rejects_non_integers(self, value):
        # ``True`` is an int subclass and must not sneak through as year 1.
        assert errors_for({**VALID, "year": value}) == {
            "year": "'year' must be an integer or null"
        }


class TestIsbn:
    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            ("9780441478125", "9780441478125"),
            ("978-0-441-47812-5", "9780441478125"),
            ("978 0 441 47812 5", "9780441478125"),
            ("0441478123", "0441478123"),
            ("043942089x", "043942089X"),
        ],
    )
    def test_separators_are_stripped_and_check_digit_upcased(self, given, expected):
        assert validate_book({**VALID, "isbn": given})["isbn"] == expected

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_absent_isbn_becomes_null(self, value):
        assert validate_book({**VALID, "isbn": value})["isbn"] is None

    @pytest.mark.parametrize(
        "value", ["12345", "97804414781256", "978044147812X", "abcdefghij", 9780441]
    )
    def test_rejects_malformed_isbn(self, value):
        assert "isbn" in errors_for({**VALID, "isbn": value})
