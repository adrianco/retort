import datetime

import pytest

from bookapi.validation import ValidationError, validate_book

VALID = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def test_accepts_complete_book():
    assert validate_book(VALID) == VALID


def test_year_and_isbn_are_optional():
    assert validate_book({"title": "T", "author": "A"}) == {
        "title": "T",
        "author": "A",
        "year": None,
        "isbn": None,
    }


def test_strips_surrounding_whitespace():
    cleaned = validate_book({"title": "  Dune  ", "author": " Frank Herbert "})
    assert cleaned["title"] == "Dune"
    assert cleaned["author"] == "Frank Herbert"


@pytest.mark.parametrize("field", ["title", "author"])
def test_title_and_author_are_required(field):
    payload = dict(VALID)
    del payload[field]
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert exc.value.errors == {field: "is required"}


@pytest.mark.parametrize("field", ["title", "author"])
@pytest.mark.parametrize("value", ["", "   "])
def test_blank_text_is_rejected(field, value):
    with pytest.raises(ValidationError) as exc:
        validate_book({**VALID, field: value})
    assert exc.value.errors == {field: "must not be blank"}


@pytest.mark.parametrize("value", [42, ["Dune"], {"name": "Dune"}])
def test_text_fields_must_be_strings(value):
    with pytest.raises(ValidationError) as exc:
        validate_book({**VALID, "title": value})
    assert exc.value.errors == {"title": "must be a string"}


def test_text_length_is_capped():
    with pytest.raises(ValidationError) as exc:
        validate_book({**VALID, "title": "x" * 501})
    assert "title" in exc.value.errors


def test_reports_every_problem_at_once():
    with pytest.raises(ValidationError) as exc:
        validate_book({"year": "soon", "isbn": "nope"})
    assert set(exc.value.errors) == {"title", "author", "year", "isbn"}


@pytest.mark.parametrize("payload", [None, "Dune", ["Dune"], 42])
def test_body_must_be_a_json_object(payload):
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert exc.value.errors == {"body": "must be a JSON object"}


@pytest.mark.parametrize("year", ["1965", 1965.5, True])
def test_year_must_be_an_integer(year):
    with pytest.raises(ValidationError) as exc:
        validate_book({**VALID, "year": year})
    assert exc.value.errors == {"year": "must be an integer"}


def test_year_range_allows_next_year_but_not_beyond():
    next_year = datetime.date.today().year + 1
    assert validate_book({**VALID, "year": next_year})["year"] == next_year
    with pytest.raises(ValidationError):
        validate_book({**VALID, "year": next_year + 1})
    with pytest.raises(ValidationError):
        validate_book({**VALID, "year": -3001})


@pytest.mark.parametrize(
    "isbn",
    ["0441172717", "044117271X", "044117271x", "978-0-441-17271-9", "978 0441172719", "9780441172719"],
)
def test_accepts_isbn_10_and_13_with_optional_separators(isbn):
    assert validate_book({**VALID, "isbn": isbn})["isbn"] == isbn


@pytest.mark.parametrize("isbn", ["123", "978044117271", "abcdefghij", "", 9780441172719])
def test_rejects_malformed_isbn(isbn):
    with pytest.raises(ValidationError) as exc:
        validate_book({**VALID, "isbn": isbn})
    assert set(exc.value.errors) == {"isbn"}
