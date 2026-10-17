from datetime import date

import pytest

from bookapi import ValidationError, validate_book
from bookapi.validation import MAX_TEXT_LENGTH, MIN_YEAR, normalize_isbn

VALID = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def test_valid_payload_is_returned_as_fields():
    fields = validate_book(VALID)

    assert fields.title == "Dune"
    assert fields.author == "Frank Herbert"
    assert fields.year == 1965
    assert fields.isbn == "9780441172719"


def test_title_and_author_are_stripped():
    fields = validate_book({"title": "  Dune  ", "author": "\tFrank Herbert\n"})

    assert fields.title == "Dune"
    assert fields.author == "Frank Herbert"


def test_year_and_isbn_are_optional():
    fields = validate_book({"title": "Dune", "author": "Frank Herbert"})

    assert fields.year is None
    assert fields.isbn is None


@pytest.mark.parametrize("field", ["title", "author"])
@pytest.mark.parametrize(
    "value, message",
    [
        (None, "is required"),
        ("", "must not be blank"),
        ("   ", "must not be blank"),
        (42, "must be a string"),
        (["Dune"], "must be a string"),
        ("x" * (MAX_TEXT_LENGTH + 1), f"must be at most {MAX_TEXT_LENGTH} characters"),
    ],
)
def test_title_and_author_rules(field, value, message):
    payload = dict(VALID, **{field: value})

    with pytest.raises(ValidationError) as excinfo:
        validate_book(payload)

    assert excinfo.value.errors == {field: message}


def test_missing_title_and_author_are_reported_together():
    with pytest.raises(ValidationError) as excinfo:
        validate_book({"year": 1965})

    assert excinfo.value.errors == {"title": "is required", "author": "is required"}


@pytest.mark.parametrize("payload", [None, "Dune", 42, ["Dune"]])
def test_body_must_be_a_json_object(payload):
    with pytest.raises(ValidationError) as excinfo:
        validate_book(payload)

    assert excinfo.value.errors == {"body": "must be a JSON object"}


@pytest.mark.parametrize("year", ["1965", True, 1965.0])
def test_year_must_be_an_integer(year):
    with pytest.raises(ValidationError) as excinfo:
        validate_book(dict(VALID, year=year))

    assert excinfo.value.errors == {"year": "must be an integer"}


def test_year_bounds_are_inclusive():
    next_year = date.today().year + 1

    assert validate_book(dict(VALID, year=MIN_YEAR)).year == MIN_YEAR
    assert validate_book(dict(VALID, year=next_year)).year == next_year


@pytest.mark.parametrize("year", [MIN_YEAR - 1, date.today().year + 2])
def test_year_outside_bounds_is_rejected(year):
    with pytest.raises(ValidationError) as excinfo:
        validate_book(dict(VALID, year=year))

    assert "year" in excinfo.value.errors


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("9780441172719", "9780441172719"),  # ISBN-13
        ("978-0-441-17271-9", "9780441172719"),  # hyphens are removed
        ("978 0 441 17271 9", "9780441172719"),  # spaces too
        ("0306406152", "0306406152"),  # ISBN-10
        ("080442957x", "080442957X"),  # ISBN-10 check digit X, normalised to upper case
    ],
)
def test_valid_isbns_are_normalised(raw, expected):
    assert normalize_isbn(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "9780441172710",  # ISBN-13 with a wrong check digit
        "0306406153",  # ISBN-10 with a wrong check digit
        "978044117271",  # 12 digits
        "97804411727191",  # 14 digits
        "abcdefghij",  # not digits
        "",
    ],
)
def test_invalid_isbns_are_rejected(raw):
    assert normalize_isbn(raw) is None


def test_non_ascii_digits_are_not_accepted_as_isbn():
    # Python's \d matches other Unicode digits; ISBNs must be ASCII 0-9.
    assert normalize_isbn("９７８０４４１１７２７１９") is None


def test_invalid_isbn_in_payload_is_reported():
    with pytest.raises(ValidationError) as excinfo:
        validate_book(dict(VALID, isbn="9780441172710"))

    assert excinfo.value.errors == {"isbn": "must be a valid ISBN-10 or ISBN-13"}


def test_all_field_errors_are_collected_at_once():
    with pytest.raises(ValidationError) as excinfo:
        validate_book({"title": "", "author": None, "year": "soon", "isbn": "123"})

    assert excinfo.value.errors == {
        "title": "must not be blank",
        "author": "is required",
        "year": "must be an integer",
        "isbn": "must be a valid ISBN-10 or ISBN-13",
    }


def test_isbn_must_be_a_string():
    with pytest.raises(ValidationError) as excinfo:
        validate_book(dict(VALID, isbn=9780441172719))

    assert excinfo.value.errors == {"isbn": "must be a string"}
