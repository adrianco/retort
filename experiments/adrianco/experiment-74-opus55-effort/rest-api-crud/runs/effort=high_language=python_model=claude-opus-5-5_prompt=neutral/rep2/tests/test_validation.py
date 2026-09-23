import pytest

from books_api.validation import ValidationError, validate_book


def test_valid_book_is_normalised():
    result = validate_book(
        {"title": "  Dune ", "author": "Frank Herbert", "year": 1965, "isbn": "0-441-01359-7"}
    )
    assert result == {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "0441013597"}


def test_optional_fields_default_to_none():
    assert validate_book({"title": "T", "author": "A"}) == {
        "title": "T", "author": "A", "year": None, "isbn": None,
    }


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"author": "A"}, "title"),
        ({"title": "T"}, "author"),
        ({"title": "   ", "author": "A"}, "title"),
        ({"title": "T", "author": ""}, "author"),
        ({"title": 42, "author": "A"}, "title"),
        ({"title": "T", "author": "A", "year": "1965"}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "year": 99999}, "year"),
        ({"title": "T", "author": "A", "isbn": "123"}, "isbn"),
        ({"title": "T", "author": "A", "isbn": 9780441013593}, "isbn"),
        ({"title": "T", "author": "A", "genre": "sci-fi"}, "genre"),
    ],
)
def test_invalid_fields_are_reported(payload, field):
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert field in exc.value.errors


def test_non_object_body_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_book(["not", "an", "object"])
    assert "body" in exc.value.errors
