from datetime import date

import pytest

from books_api import BookData, ValidationError, validate_book
from books_api.validation import MAX_TEXT_LENGTH, MIN_YEAR


def errors_for(payload):
    with pytest.raises(ValidationError) as excinfo:
        validate_book(payload)
    return excinfo.value.errors


def test_valid_payload_is_cleaned():
    data = validate_book(
        {"title": "  Dune ", "author": " Frank Herbert", "year": 1965, "isbn": " 0-441-17271-7 "}
    )
    assert data == BookData(title="Dune", author="Frank Herbert", year=1965, isbn="0-441-17271-7")


def test_only_title_and_author_are_required():
    assert validate_book({"title": "Dune", "author": "Frank Herbert"}) == BookData("Dune", "Frank Herbert")
    assert validate_book({"title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}) == BookData(
        "Dune", "Frank Herbert"
    )


def test_unknown_fields_are_ignored():
    assert validate_book({"title": "Dune", "author": "Frank Herbert", "id": 99, "genre": "SF"}) == BookData(
        "Dune", "Frank Herbert"
    )


def test_missing_title_and_author_are_both_reported():
    assert errors_for({}) == {"title": "title is required", "author": "author is required"}


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_title_is_rejected(blank):
    assert errors_for({"title": blank, "author": "A"}) == {"title": "title must not be blank"}


@pytest.mark.parametrize("value", [123, ["Dune"], {"t": 1}, True])
def test_non_string_author_is_rejected(value):
    assert errors_for({"title": "Dune", "author": value}) == {"author": "author must be a string"}


def test_overlong_text_is_rejected():
    errors = errors_for({"title": "x" * (MAX_TEXT_LENGTH + 1), "author": "A"})
    assert errors == {"title": f"title must be at most {MAX_TEXT_LENGTH} characters"}
    assert validate_book({"title": "x" * MAX_TEXT_LENGTH, "author": "A"}).title == "x" * MAX_TEXT_LENGTH


@pytest.mark.parametrize("year", ["1965", 1965.0, True, [1965]])
def test_year_must_be_an_integer(year):
    assert errors_for({"title": "Dune", "author": "A", "year": year}) == {"year": "year must be an integer"}


def test_year_range():
    next_year = date.today().year + 1
    assert validate_book({"title": "T", "author": "A", "year": next_year}).year == next_year
    assert validate_book({"title": "T", "author": "A", "year": MIN_YEAR}).year == MIN_YEAR
    assert validate_book({"title": "T", "author": "A", "year": -800}).year == -800
    for year in (next_year + 1, MIN_YEAR - 1, 10**30):
        assert "year" in errors_for({"title": "T", "author": "A", "year": year})


@pytest.mark.parametrize(
    "isbn",
    ["9780441172719", "978-0-441-17271-9", "978 0 441 17271 9", "0441172717", "0-8044-2957-X", "080442957x"],
)
def test_accepts_isbn10_and_isbn13(isbn):
    assert validate_book({"title": "T", "author": "A", "isbn": isbn}).isbn == isbn


@pytest.mark.parametrize(
    "isbn",
    ["12345", "97804411727190", "978-0-441-1727X-9", "ISBN 0441172717", "-0441172717", "0441--172717", "X441172717"],
)
def test_rejects_malformed_isbn(isbn):
    assert "isbn" in errors_for({"title": "T", "author": "A", "isbn": isbn})


def test_blank_isbn_means_no_isbn():
    assert validate_book({"title": "T", "author": "A", "isbn": "  "}).isbn is None


def test_non_string_isbn_is_rejected():
    assert errors_for({"title": "T", "author": "A", "isbn": 9780441172719}) == {"isbn": "isbn must be a string"}


@pytest.mark.parametrize("payload", [None, [], "Dune", 42])
def test_payload_must_be_an_object(payload):
    assert errors_for(payload) == {"body": "must be a JSON object"}
