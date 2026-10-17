import pytest

from book_api.models import BookFields
from book_api.validation import MAX_TEXT_LENGTH, MAX_YEAR, MIN_YEAR, ValidationError, validate_book

VALID = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}


def test_accepts_full_payload_and_normalises_isbn():
    fields = validate_book(VALID)

    assert fields == BookFields(title="Dune", author="Frank Herbert", year=1965, isbn="9780441172719")


def test_strips_surrounding_whitespace_from_text_fields():
    fields = validate_book({"title": "  Dune  ", "author": "\tFrank Herbert\n"})

    assert fields.title == "Dune"
    assert fields.author == "Frank Herbert"


def test_optional_fields_default_to_none():
    fields = validate_book({"title": "Dune", "author": "Frank Herbert"})

    assert fields.year is None
    assert fields.isbn is None


def test_null_and_blank_optional_fields_are_treated_as_absent():
    fields = validate_book({"title": "Dune", "author": "Frank Herbert", "year": None, "isbn": "  "})

    assert fields.year is None
    assert fields.isbn is None


def test_title_and_author_are_required():
    with pytest.raises(ValidationError) as exc_info:
        validate_book({"year": 1965})

    assert exc_info.value.details == {"title": "is required", "author": "is required"}


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_title_is_rejected(blank):
    with pytest.raises(ValidationError) as exc_info:
        validate_book({"title": blank, "author": "Frank Herbert"})

    assert exc_info.value.details == {"title": "must not be blank"}


def test_text_fields_must_be_strings():
    with pytest.raises(ValidationError) as exc_info:
        validate_book({"title": 42, "author": ["Frank Herbert"]})

    assert exc_info.value.details == {"title": "must be a string", "author": "must be a string"}


def test_text_fields_have_a_length_limit():
    with pytest.raises(ValidationError) as exc_info:
        validate_book({"title": "x" * (MAX_TEXT_LENGTH + 1), "author": "Frank Herbert"})

    assert exc_info.value.details == {"title": f"must be at most {MAX_TEXT_LENGTH} characters"}


@pytest.mark.parametrize("year", ["1999", 1999.0, True, MIN_YEAR - 1, MAX_YEAR + 1])
def test_invalid_year_is_rejected(year):
    with pytest.raises(ValidationError) as exc_info:
        validate_book({"title": "Dune", "author": "Frank Herbert", "year": year})

    assert set(exc_info.value.details) == {"year"}


def test_year_boundaries_are_accepted():
    for year in (MIN_YEAR, MAX_YEAR):
        assert validate_book({"title": "Dune", "author": "Frank Herbert", "year": year}).year == year


@pytest.mark.parametrize(
    "isbn, expected",
    [
        ("0-306-40615-2", "0306406152"),
        ("030640615x", "030640615X"),
        ("978 0 306 40615 7", "9780306406157"),
        ("9780306406157", "9780306406157"),
    ],
)
def test_valid_isbns_are_normalised(isbn, expected):
    assert validate_book({"title": "T", "author": "A", "isbn": isbn}).isbn == expected


@pytest.mark.parametrize("isbn", ["12345", "978-0-306-40615-", "abcdefghij", "97803064061571", 9780306406157])
def test_invalid_isbn_is_rejected(isbn):
    with pytest.raises(ValidationError) as exc_info:
        validate_book({"title": "T", "author": "A", "isbn": isbn})

    assert set(exc_info.value.details) == {"isbn"}
