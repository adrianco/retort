"""Unit tests for the validation layer, independent of HTTP."""

import pytest

from books.validation import MAX_TEXT_LENGTH, ValidationError, validate_book


def test_valid_payload_is_normalized():
    assert validate_book(
        {"title": " Dune ", "author": "Frank Herbert", "isbn": "978-0-441-01359-3"}
    ) == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": None,
        "isbn": "9780441013593",
    }


def test_body_must_be_an_object():
    with pytest.raises(ValidationError) as exc:
        validate_book(["Dune"])
    assert exc.value.errors == {"body": "must be a JSON object"}


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"author": "Herbert"}, "title"),
        ({"title": "Dune"}, "author"),
        ({"title": 42, "author": "Herbert"}, "title"),
        ({"title": "Dune", "author": ""}, "author"),
        ({"title": "D" * (MAX_TEXT_LENGTH + 1), "author": "Herbert"}, "title"),
        ({"title": "Dune", "author": "Herbert", "year": 1.5}, "year"),
        ({"title": "Dune", "author": "Herbert", "year": True}, "year"),
        ({"title": "Dune", "author": "Herbert", "year": 0}, "year"),
        ({"title": "Dune", "author": "Herbert", "year": 10000}, "year"),
        ({"title": "Dune", "author": "Herbert", "isbn": 9780441013593}, "isbn"),
    ],
)
def test_invalid_payloads_report_the_offending_field(payload, field):
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert field in exc.value.errors


@pytest.mark.parametrize(
    "isbn", ["0441013597", "043942089X", "9780441013593", "978 0 261 10221 7"]
)
def test_accepts_well_formed_isbns(isbn):
    assert validate_book({"title": "T", "author": "A", "isbn": isbn})["isbn"]


@pytest.mark.parametrize(
    "isbn",
    [
        "0441013590",  # ISBN-10 checksum failure
        "9780441013594",  # ISBN-13 checksum failure
        "04410135X7",  # X outside the check-digit position
        "123456789",  # wrong length
        "not-an-isbn",
    ],
)
def test_rejects_malformed_isbns(isbn):
    with pytest.raises(ValidationError) as exc:
        validate_book({"title": "T", "author": "A", "isbn": isbn})
    assert "isbn" in exc.value.errors


def test_empty_isbn_is_treated_as_absent():
    assert validate_book({"title": "T", "author": "A", "isbn": ""})["isbn"] is None


def test_all_errors_are_collected_at_once():
    with pytest.raises(ValidationError) as exc:
        validate_book({"year": "soon", "isbn": "nope", "extra": 1})
    assert set(exc.value.errors) == {"title", "author", "year", "isbn", "body"}
