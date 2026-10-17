import pytest

from bookapi import ValidationError, validate_book

VALID = {"title": "Dune", "author": "Frank Herbert"}


def test_minimal_book_is_accepted_and_optional_fields_default_to_none():
    assert validate_book(VALID) == {"title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}


@pytest.mark.parametrize("field", ["title", "author"])
def test_title_and_author_are_required(field):
    payload = dict(VALID)
    del payload[field]
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert exc.value.errors == {field: "is required"}


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_text_is_rejected(value):
    with pytest.raises(ValidationError) as exc:
        validate_book({**VALID, "title": value})
    assert exc.value.errors == {"title": "must not be blank"}


def test_text_is_stripped():
    assert validate_book({**VALID, "title": "  Dune  "})["title"] == "Dune"


def test_non_string_text_is_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_book({**VALID, "author": 42})
    assert exc.value.errors == {"author": "must be a string"}


@pytest.mark.parametrize("value", [True, 1.5, "1965"])
def test_year_must_be_a_plausible_integer(value):
    with pytest.raises(ValidationError) as exc:
        validate_book({**VALID, "year": value})
    assert "year" in exc.value.errors


def test_year_range_is_enforced():
    with pytest.raises(ValidationError):
        validate_book({**VALID, "year": 0})
    assert validate_book({**VALID, "year": 1965})["year"] == 1965


@pytest.mark.parametrize("isbn", ["0306406152", "097522980X", "9780306406157", "978-0-306-40615-7"])
def test_valid_isbns_are_normalised(isbn):
    result = validate_book({**VALID, "isbn": isbn})["isbn"]
    assert result == isbn.replace("-", "").upper()


@pytest.mark.parametrize("isbn", ["0306406153", "9780306406158", "123", "abcdefghij", 9780306406157])
def test_invalid_isbns_are_rejected(isbn):
    with pytest.raises(ValidationError) as exc:
        validate_book({**VALID, "isbn": isbn})
    assert "isbn" in exc.value.errors


@pytest.mark.parametrize("payload", [None, [], "book", 3])
def test_body_must_be_an_object(payload):
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert exc.value.errors == {"body": "must be a JSON object"}


def test_all_errors_are_reported_together():
    with pytest.raises(ValidationError) as exc:
        validate_book({"title": "", "year": "soon", "isbn": "nope"})
    assert set(exc.value.errors) == {"title", "author", "year", "isbn"}
