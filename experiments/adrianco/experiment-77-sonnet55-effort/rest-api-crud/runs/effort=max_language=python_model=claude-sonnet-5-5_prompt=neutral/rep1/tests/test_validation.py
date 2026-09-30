"""Unit tests for payload validation (no HTTP, no database)."""

import pytest

from bookapi.models import BookData
from bookapi.validation import (
    MAX_AUTHOR_LENGTH,
    MAX_ISBN_LENGTH,
    MAX_TITLE_LENGTH,
    MIN_YEAR,
    ValidationError,
    latest_year,
    validate_book,
)

VALID = {"title": "Dune", "author": "Frank Herbert"}


def errors_for(payload):
    with pytest.raises(ValidationError) as excinfo:
        validate_book(payload)
    return excinfo.value.errors


def test_title_and_author_are_enough():
    assert validate_book(VALID) == BookData("Dune", "Frank Herbert", None, None)


def test_accepts_every_field():
    payload = {**VALID, "year": 1965, "isbn": "978-0441013593"}
    assert validate_book(payload) == BookData("Dune", "Frank Herbert", 1965, "978-0441013593")


def test_text_is_stripped_of_surrounding_whitespace():
    payload = {"title": "  Dune\n", "author": "\tFrank Herbert ", "isbn": " 123 "}
    assert validate_book(payload) == BookData("Dune", "Frank Herbert", None, "123")


def test_blank_or_null_optional_fields_mean_absent():
    payload = {**VALID, "year": None, "isbn": "   "}
    assert validate_book(payload) == BookData("Dune", "Frank Herbert", None, None)


def test_unknown_keys_are_ignored():
    assert validate_book({**VALID, "id": 7, "rating": 5}) == BookData("Dune", "Frank Herbert")


def test_unicode_text_is_preserved():
    data = validate_book({"title": "Cien años de soledad 📚", "author": "Gabriel García Márquez"})
    assert (data.title, data.author) == ("Cien años de soledad 📚", "Gabriel García Márquez")


@pytest.mark.parametrize("field", ["title", "author"])
class TestRequiredText:
    def test_missing(self, field):
        payload = {k: v for k, v in VALID.items() if k != field}
        assert errors_for(payload) == {field: f"{field} is required"}

    def test_null(self, field):
        assert errors_for({**VALID, field: None}) == {field: f"{field} is required"}

    @pytest.mark.parametrize("blank", ["", "   ", "\t\n", " "])
    def test_blank(self, field, blank):
        assert errors_for({**VALID, field: blank}) == {field: f"{field} must not be blank"}

    @pytest.mark.parametrize("value", [123, 1.5, True, ["x"], {"x": 1}])
    def test_wrong_type(self, field, value):
        assert errors_for({**VALID, field: value}) == {field: f"{field} must be a string"}

    def test_lone_surrogate(self, field):
        assert errors_for({**VALID, field: "\ud800"}) == {
            field: f"{field} must be valid Unicode text"
        }


@pytest.mark.parametrize(
    "field, limit",
    [("title", MAX_TITLE_LENGTH), ("author", MAX_AUTHOR_LENGTH), ("isbn", MAX_ISBN_LENGTH)],
)
def test_length_limit_is_inclusive(field, limit):
    assert getattr(validate_book({**VALID, field: "x" * limit}), field) == "x" * limit
    assert errors_for({**VALID, field: "x" * (limit + 1)}) == {
        field: f"{field} must be at most {limit} characters"
    }


def test_length_is_measured_after_stripping():
    assert (
        validate_book({**VALID, "title": " " + "x" * MAX_TITLE_LENGTH + " "}).title
        == "x" * MAX_TITLE_LENGTH
    )


class TestYear:
    def test_bounds_are_inclusive(self):
        assert validate_book({**VALID, "year": MIN_YEAR}).year == MIN_YEAR
        assert validate_book({**VALID, "year": latest_year()}).year == latest_year()

    @pytest.mark.parametrize("offset", [-1, 1])
    def test_just_outside_the_bounds(self, offset):
        edge = MIN_YEAR if offset < 0 else latest_year()
        errors = errors_for({**VALID, "year": edge + offset})
        assert errors == {"year": f"year must be between {MIN_YEAR} and {latest_year()}"}

    @pytest.mark.parametrize("value", [0, -500, 10**30])
    def test_out_of_range(self, value):
        assert list(errors_for({**VALID, "year": value})) == ["year"]

    @pytest.mark.parametrize("value", ["1999", 1999.5, 1999.0, True, False, [1999], {"y": 1}])
    def test_must_be_an_integer(self, value):
        assert errors_for({**VALID, "year": value}) == {"year": "year must be an integer"}


class TestIsbn:
    @pytest.mark.parametrize("value", ["0-306-40615-2", "9780306406157", "123", "ISBN 1-2-3"])
    def test_any_reasonable_string_is_accepted(self, value):
        assert validate_book({**VALID, "isbn": value}).isbn == value

    @pytest.mark.parametrize("value", [9780306406157, 1.5, True, ["x"]])
    def test_must_be_a_string(self, value):
        # A number would silently lose leading zeros, so it is rejected rather than coerced.
        assert errors_for({**VALID, "isbn": value}) == {"isbn": "isbn must be a string"}


def test_every_problem_is_reported_at_once():
    payload = {"title": "", "author": None, "year": "1999", "isbn": 12}
    assert errors_for(payload) == {
        "title": "title must not be blank",
        "author": "author is required",
        "year": "year must be an integer",
        "isbn": "isbn must be a string",
    }
