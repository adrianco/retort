"""Unit tests for the validation rules, with no app or database involved."""

from __future__ import annotations

import pytest

from validation import ValidationError, parse_book


class TestFullPayload:
    def test_returns_normalised_fields(self):
        book = parse_book(
            {
                "title": "  Dune  ",
                "author": "Frank Herbert",
                "year": 1965,
                "isbn": "978-0-441-01359-3",
            }
        )
        assert book == {
            "title": "Dune",
            "author": "Frank Herbert",
            "year": 1965,
            "isbn": "9780441013593",
        }

    def test_optional_fields_default_to_none(self):
        assert parse_book({"title": "T", "author": "A"}) == {
            "title": "T",
            "author": "A",
            "year": None,
            "isbn": None,
        }

    def test_explicit_nulls_are_allowed_for_optional_fields(self):
        book = parse_book({"title": "T", "author": "A", "year": None, "isbn": None})
        assert book["year"] is None and book["isbn"] is None

    def test_numeric_string_year_is_coerced(self):
        assert parse_book({"title": "T", "author": "A", "year": " 1965 "})["year"] == 1965

    @pytest.mark.parametrize("isbn", ["0441013593", "044101359X", "9780441013593"])
    def test_accepts_isbn10_and_isbn13(self, isbn):
        assert parse_book({"title": "T", "author": "A", "isbn": isbn})["isbn"] == isbn

    def test_lowercase_isbn_check_character_is_upcased(self):
        assert parse_book({"title": "T", "author": "A", "isbn": "044101359x"})["isbn"] == (
            "044101359X"
        )

    def test_blank_isbn_is_treated_as_absent(self):
        assert parse_book({"title": "T", "author": "A", "isbn": "  "})["isbn"] is None

    def test_title_at_the_length_limit_is_accepted(self):
        title = "x" * 500
        assert parse_book({"title": title, "author": "A"})["title"] == title


class TestErrors:
    @pytest.mark.parametrize(
        ("payload", "expected_fields"),
        [
            ({}, {"title", "author"}),
            ({"title": "T"}, {"author"}),
            ({"author": "A"}, {"title"}),
            ({"title": "", "author": "A"}, {"title"}),
            ({"title": "T", "author": "\t\n"}, {"author"}),
            ({"title": ["T"], "author": "A"}, {"title"}),
            ({"title": "x" * 501, "author": "A"}, {"title"}),
            ({"title": "T", "author": "A", "year": 0}, {"year"}),
            ({"title": "T", "author": "A", "year": 2201}, {"year"}),
            ({"title": "T", "author": "A", "year": 1965.5}, {"year"}),
            ({"title": "T", "author": "A", "isbn": "044101359Y"}, {"isbn"}),
            ({"title": "T", "author": "A", "isbn": "97804410135931"}, {"isbn"}),
            ({"title": "T", "author": "A", "isbn": []}, {"isbn"}),
            ({"title": "", "author": "", "isbn": "1"}, {"title", "author", "isbn"}),
            ({"title": "T", "author": "A", "extra": 1}, {"_body"}),
        ],
    )
    def test_reports_every_offending_field(self, payload, expected_fields):
        with pytest.raises(ValidationError) as exc_info:
            parse_book(payload)
        assert set(exc_info.value.errors) == expected_fields

    @pytest.mark.parametrize("payload", [None, "Dune", 7, ["Dune"]])
    def test_non_object_payloads_are_rejected(self, payload):
        with pytest.raises(ValidationError) as exc_info:
            parse_book(payload)
        assert "_body" in exc_info.value.errors

    def test_message_mentions_each_problem(self):
        with pytest.raises(ValidationError, match="title") as exc_info:
            parse_book({"year": 1965})
        assert "author" in str(exc_info.value)


class TestPartialPayload:
    def test_returns_only_the_supplied_fields(self):
        assert parse_book({"year": 1965}, partial=True) == {"year": 1965}

    def test_does_not_require_title_or_author(self):
        assert parse_book({"isbn": "0441013593"}, partial=True) == {"isbn": "0441013593"}

    def test_still_validates_supplied_fields(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_book({"title": " "}, partial=True)
        assert "title" in exc_info.value.errors

    def test_empty_payload_is_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_book({}, partial=True)
        assert "_body" in exc_info.value.errors

    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValidationError):
            parse_book({"pages": 412}, partial=True)
