from datetime import date

import pytest

from bookapi.validation import MAX_TEXT_LENGTH, ValidationError, validate_book


def valid_payload(**overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
    payload.update(overrides)
    return payload


def test_valid_book_is_normalised():
    book = validate_book(valid_payload(title="  Dune  ", isbn="978-0-441-17271-9"))
    assert book == {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def test_year_and_isbn_are_optional():
    book = validate_book({"title": "Dune", "author": "Frank Herbert"})
    assert book == {"title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}


@pytest.mark.parametrize("field", ["title", "author"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_title_and_author_are_required(field, value):
    with pytest.raises(ValidationError) as exc:
        validate_book(valid_payload(**{field: value}))
    assert field in exc.value.errors


def test_missing_required_fields_are_all_reported():
    with pytest.raises(ValidationError) as exc:
        validate_book({"year": 1965})
    assert exc.value.errors == {"title": "is required", "author": "is required"}


@pytest.mark.parametrize("field", ["title", "author"])
def test_text_fields_must_be_strings(field):
    with pytest.raises(ValidationError) as exc:
        validate_book(valid_payload(**{field: 42}))
    assert exc.value.errors == {field: "must be a string"}


def test_text_fields_have_a_length_limit():
    with pytest.raises(ValidationError) as exc:
        validate_book(valid_payload(title="x" * (MAX_TEXT_LENGTH + 1)))
    assert "title" in exc.value.errors


@pytest.mark.parametrize("value", ["1965", 1965.0, True])
def test_year_must_be_an_integer(value):
    with pytest.raises(ValidationError) as exc:
        validate_book(valid_payload(year=value))
    assert exc.value.errors == {"year": "must be an integer"}


@pytest.mark.parametrize("value", [999, date.today().year + 2])
def test_year_must_be_in_range(value):
    with pytest.raises(ValidationError) as exc:
        validate_book(valid_payload(year=value))
    assert "year" in exc.value.errors


@pytest.mark.parametrize("isbn", ["0306406152", "030640615X", "978-0-306-40615-7", "9780306406157"])
def test_accepts_isbn10_and_isbn13(isbn):
    assert validate_book(valid_payload(isbn=isbn))["isbn"] == isbn.replace("-", "").upper()


@pytest.mark.parametrize("isbn", ["12345", "978030640615", "abcdefghij", "0306406152X", 9780306406157])
def test_rejects_malformed_isbn(isbn):
    with pytest.raises(ValidationError) as exc:
        validate_book(valid_payload(isbn=isbn))
    assert "isbn" in exc.value.errors


@pytest.mark.parametrize("payload", [None, [], "Dune", 7])
def test_body_must_be_an_object(payload):
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert exc.value.errors == {"body": "must be a JSON object"}
