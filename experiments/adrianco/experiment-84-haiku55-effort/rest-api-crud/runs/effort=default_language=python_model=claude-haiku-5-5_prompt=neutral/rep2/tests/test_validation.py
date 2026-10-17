import pytest

from books_api import ValidationError, validate_book


def test_valid_book_is_cleaned_and_trimmed():
    cleaned = validate_book({"title": "  Dune ", "author": " Frank Herbert ", "year": 1965, "isbn": "978-0-306-40615-7"})

    assert cleaned == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "9780306406157",
    }


@pytest.mark.parametrize("isbn", ["0306406152", "0-306-40615-2", " 0 306 40615 2 "])
def test_isbn10_accepted_and_normalised(isbn):
    assert validate_book({"title": "T", "author": "A", "isbn": isbn})["isbn"] == "0306406152"


def test_blank_isbn_is_stored_as_none():
    assert validate_book({"title": "T", "author": "A", "isbn": "  "})["isbn"] is None


@pytest.mark.parametrize("isbn", ["0306406153", "9780306406158", "12345", "abcdefghij", 9780306406157])
def test_invalid_isbn_rejected(isbn):
    with pytest.raises(ValidationError) as exc:
        validate_book({"title": "T", "author": "A", "isbn": isbn})

    assert "isbn" in exc.value.errors


@pytest.mark.parametrize("year", [0, -5, 99999, "1990", 1990.0, True])
def test_invalid_year_rejected(year):
    with pytest.raises(ValidationError) as exc:
        validate_book({"title": "T", "author": "A", "year": year})

    assert "year" in exc.value.errors


def test_overlong_title_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_book({"title": "x" * 501, "author": "A"})

    assert "title" in exc.value.errors


def test_all_errors_reported_together():
    with pytest.raises(ValidationError) as exc:
        validate_book({"title": 5, "author": None, "year": "x", "isbn": "bad"})

    assert set(exc.value.errors) == {"title", "author", "year", "isbn"}
