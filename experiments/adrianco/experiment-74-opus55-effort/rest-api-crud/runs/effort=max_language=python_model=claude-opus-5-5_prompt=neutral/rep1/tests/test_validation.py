"""Unit tests for the payload rules in validation.py."""

from datetime import date

import pytest

from validation import MAX_TEXT_LENGTH, ValidationError, validate_book

MINIMAL = {"title": "Dune", "author": "Frank Herbert"}
THIS_YEAR = date.today().year


def rejection(payload):
    """The per-field errors that validate_book raises for *payload*."""
    with pytest.raises(ValidationError) as caught:
        validate_book(payload)
    return caught.value.details


def test_minimal_book_is_valid():
    assert validate_book(MINIMAL) == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": None,
        "isbn": None,
    }


def test_title_and_author_are_trimmed():
    book = validate_book({"title": "  Dune ", "author": "\tFrank Herbert\n"})

    assert (book["title"], book["author"]) == ("Dune", "Frank Herbert")


def test_title_may_be_as_long_as_the_limit():
    title = "x" * MAX_TEXT_LENGTH

    assert validate_book({**MINIMAL, "title": title})["title"] == title


@pytest.mark.parametrize("field", ["title", "author"])
@pytest.mark.parametrize(
    ("value", "problem"),
    [
        (None, "is required"),
        ("", "is required"),
        ("   ", "is required"),
        (42, "must be a string"),
        (["Dune"], "must be a string"),
        ("x" * (MAX_TEXT_LENGTH + 1), f"must be at most {MAX_TEXT_LENGTH} characters"),
    ],
)
def test_invalid_title_or_author(field, value, problem):
    assert rejection({**MINIMAL, field: value}) == {field: f"{field} {problem}"}


@pytest.mark.parametrize("year", [1, 1965, THIS_YEAR])
def test_valid_year(year):
    assert validate_book({**MINIMAL, "year": year})["year"] == year


@pytest.mark.parametrize(
    ("year", "problem"),
    [
        ("1965", "must be an integer"),
        (1965.0, "must be an integer"),
        (True, "must be an integer"),
        (0, f"must be between 1 and {THIS_YEAR}"),
        (THIS_YEAR + 1, f"must be between 1 and {THIS_YEAR}"),
    ],
)
def test_invalid_year(year, problem):
    assert rejection({**MINIMAL, "year": year}) == {"year": f"year {problem}"}


@pytest.mark.parametrize(
    ("isbn", "stored"),
    [
        ("0-306-40615-2", "0306406152"),  # ISBN-10
        ("0-8044-2957-x", "080442957X"),  # ISBN-10 with an X check digit
        ("978-0-306-40615-7", "9780306406157"),  # ISBN-13
        (" 978 0 306 40615 7 ", "9780306406157"),  # spaces separate groups too
        ("", None),  # blank means no ISBN
        (None, None),
    ],
)
def test_valid_isbn_is_stored_without_separators(isbn, stored):
    assert validate_book({**MINIMAL, "isbn": isbn})["isbn"] == stored


@pytest.mark.parametrize(
    "isbn",
    [
        "0-306-40615-3",  # wrong ISBN-10 check digit
        "978-0-306-40615-8",  # wrong ISBN-13 check digit
        "030640615",  # too short
        "X306406152",  # X is only allowed as the ISBN-10 check digit
        "978030640615X",  # ... and never in an ISBN-13
    ],
)
def test_invalid_isbn(isbn):
    assert rejection({**MINIMAL, "isbn": isbn}) == {
        "isbn": "isbn must be a valid ISBN-10 or ISBN-13"
    }


def test_isbn_must_be_a_string():
    assert rejection({**MINIMAL, "isbn": 306406152}) == {
        "isbn": "isbn must be a string"
    }


def test_unknown_fields_are_rejected_but_id_is_ignored():
    assert rejection({**MINIMAL, "id": 7, "genre": "SF"}) == {"genre": "unknown field"}
    assert validate_book({**MINIMAL, "id": 7}) == validate_book(MINIMAL)


@pytest.mark.parametrize("payload", [None, ["Dune"], "Dune", 42])
def test_payload_must_be_a_json_object(payload):
    with pytest.raises(ValidationError, match="must be a JSON object") as caught:
        validate_book(payload)

    assert caught.value.details == {}
