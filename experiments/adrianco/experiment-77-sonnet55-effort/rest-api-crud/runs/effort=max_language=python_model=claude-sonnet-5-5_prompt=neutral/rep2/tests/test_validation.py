"""Unit tests for payload validation (no HTTP, no database)."""

from __future__ import annotations

import pytest

from bookapi.models import BookInput
from bookapi.validation import (
    MAX_AUTHOR_LENGTH,
    MAX_ISBN_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_YEAR,
    MIN_YEAR,
    ValidationError,
    validate_book,
)

VALID = {"title": "Dune", "author": "Frank Herbert"}


def errors_for(payload) -> dict[str, str]:
    with pytest.raises(ValidationError) as excinfo:
        validate_book(payload)
    return excinfo.value.errors


def test_accepts_a_complete_payload():
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    assert validate_book(payload) == BookInput("Dune", "Frank Herbert", 1965, "9780441172719")


def test_year_and_isbn_are_optional():
    assert validate_book(VALID) == BookInput("Dune", "Frank Herbert", None, None)


def test_null_and_blank_optional_values_become_none():
    book = validate_book({**VALID, "year": None, "isbn": "   "})
    assert (book.year, book.isbn) == (None, None)


def test_text_is_stripped():
    book = validate_book({"title": "  Dune\t", "author": "\nFrank Herbert ", "isbn": " 123 "})
    assert (book.title, book.author, book.isbn) == ("Dune", "Frank Herbert", "123")


def test_unknown_keys_are_ignored():
    # Clients often PUT back exactly what they GOT, including the id.
    assert validate_book({**VALID, "id": 7, "shelf": "A3"}) == BookInput("Dune", "Frank Herbert")


@pytest.mark.parametrize("text", ["Les Misérables", "吾輩は猫である", "Ünïcödé ✓", "😀 emoji"])
def test_non_ascii_text_is_accepted(text):
    assert validate_book({**VALID, "title": text}).title == text


@pytest.mark.parametrize("field", ["title", "author"])
class TestRequiredText:
    def test_missing(self, field):
        payload = {k: v for k, v in VALID.items() if k != field}
        assert errors_for(payload) == {field: f"{field} is required"}

    @pytest.mark.parametrize("value", [None, "", "   ", "\t\n"], ids=repr)
    def test_null_or_blank(self, field, value):
        assert errors_for({**VALID, field: value}) == {field: f"{field} is required"}

    @pytest.mark.parametrize("value", [123, 1.5, True, ["x"], {"a": 1}], ids=repr)
    def test_must_be_a_string(self, field, value):
        assert errors_for({**VALID, field: value}) == {field: f"{field} must be a string"}


@pytest.mark.parametrize(
    ("field", "limit"),
    [("title", MAX_TITLE_LENGTH), ("author", MAX_AUTHOR_LENGTH), ("isbn", MAX_ISBN_LENGTH)],
)
class TestLengthLimits:
    def test_limit_itself_is_accepted(self, field, limit):
        assert getattr(validate_book({**VALID, field: "x" * limit}), field) == "x" * limit

    def test_one_over_the_limit_is_rejected(self, field, limit):
        assert errors_for({**VALID, field: "x" * (limit + 1)}) == {
            field: f"{field} must be at most {limit} characters"
        }

    def test_padding_does_not_count(self, field, limit):
        padded = " " * 50 + "x" * limit + " " * 50
        assert getattr(validate_book({**VALID, field: padded}), field) == "x" * limit


class TestOptionalIsbn:
    @pytest.mark.parametrize("value", [123, 9780441172719, True, ["x"]], ids=repr)
    def test_must_be_a_string(self, value):
        assert errors_for({**VALID, "isbn": value}) == {"isbn": "isbn must be a string"}

    @pytest.mark.parametrize("value", ["not-an-isbn", "123", "978-0-441-17271-9"])
    def test_format_is_not_policed(self, value):
        # Only title and author are mandated by the spec; ISBNs are stored as given.
        assert validate_book({**VALID, "isbn": value}).isbn == value


class TestYear:
    @pytest.mark.parametrize("year", [MIN_YEAR, 1454, 1999, 2026, MAX_YEAR])
    def test_accepts_integers_in_range(self, year):
        assert validate_book({**VALID, "year": year}).year == year

    @pytest.mark.parametrize("year", ["1999", 19.99, 1999.0, True, False, [], {}], ids=repr)
    def test_must_be_an_integer(self, year):
        assert errors_for({**VALID, "year": year}) == {"year": "year must be an integer"}

    @pytest.mark.parametrize("year", [0, -1, MIN_YEAR - 1, MAX_YEAR + 1, 10**30])
    def test_must_be_in_range(self, year):
        assert errors_for({**VALID, "year": year}) == {
            "year": f"year must be between {MIN_YEAR} and {MAX_YEAR}"
        }


class TestInvisibleText:
    @pytest.mark.parametrize(
        "blank",
        [
            "\N{ZERO WIDTH SPACE}",
            "\N{ZERO WIDTH SPACE}\N{ZERO WIDTH NON-JOINER}\N{ZERO WIDTH NO-BREAK SPACE}",
            " \N{WORD JOINER} ",
            "\N{NO-BREAK SPACE}\N{ZERO WIDTH SPACE}",
        ],
        ids=ascii,
    )
    def test_text_with_nothing_to_see_counts_as_blank(self, blank):
        assert errors_for({**VALID, "title": blank}) == {"title": "title is required"}
        assert validate_book({**VALID, "isbn": blank}).isbn is None

    def test_zero_width_characters_inside_visible_text_are_kept(self):
        title = "Zero\N{ZERO WIDTH SPACE}Width"
        assert validate_book({**VALID, "title": title}).title == title


class TestUnrepresentableText:
    @pytest.mark.parametrize(
        "bad", ["a\x00b", "line1\nline2", "tab\there", "\x1b[31mred", "del\x7f"]
    )
    def test_control_characters_are_rejected(self, bad):
        assert errors_for({**VALID, "title": bad}) == {
            "title": "title must not contain control characters"
        }

    def test_lone_surrogates_are_rejected(self):
        # Valid in JSON ("\ud800") but impossible to store or return as UTF-8.
        assert errors_for({**VALID, "author": "bad \ud800 text"}) == {
            "author": "author must be valid Unicode text"
        }


def test_every_problem_is_reported_at_once():
    errors = errors_for({"title": " ", "year": "1999", "isbn": 42})
    assert errors == {
        "title": "title is required",
        "author": "author is required",
        "year": "year must be an integer",
        "isbn": "isbn must be a string",
    }


def test_exception_message_joins_the_field_messages():
    with pytest.raises(ValidationError, match="title is required; author is required"):
        validate_book({})


@pytest.mark.parametrize("payload", [None, [], [VALID], "book", 42, 1.5, True], ids=repr)
def test_payload_must_be_a_json_object(payload):
    assert errors_for(payload) == {"body": "body must be a JSON object"}
