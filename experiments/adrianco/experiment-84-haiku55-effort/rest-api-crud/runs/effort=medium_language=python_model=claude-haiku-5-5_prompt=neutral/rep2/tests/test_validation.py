import pytest

from books.validation import ValidationError, parse_book


def test_strips_whitespace_and_normalises_isbn():
    book = parse_book({"title": "  Dune ", "author": " Frank Herbert", "isbn": "0-306 40615-2"})

    assert book == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": None,
        "isbn": "0306406152",
    }


@pytest.mark.parametrize("isbn", ["0306406152", "097522980X", "9780306406157", "978-0-306-40615-7"])
def test_accepts_valid_isbns(isbn):
    assert parse_book({"title": "T", "author": "A", "isbn": isbn})["isbn"] is not None


@pytest.mark.parametrize("isbn", ["0306406153", "9780306406158", "12345", "abcdefghij", ""])
def test_rejects_invalid_isbns(isbn):
    with pytest.raises(ValidationError) as exc:
        parse_book({"title": "T", "author": "A", "isbn": isbn})
    assert exc.value.errors == {"isbn": "must be a valid ISBN-10 or ISBN-13"}


@pytest.mark.parametrize("year", ["1965", 1.5, True, 0, -3, 99999])
def test_rejects_bad_years(year):
    with pytest.raises(ValidationError) as exc:
        parse_book({"title": "T", "author": "A", "year": year})
    assert set(exc.value.errors) == {"year"}


def test_accepts_year_in_range():
    assert parse_book({"title": "T", "author": "A", "year": 1})["year"] == 1


def test_reports_all_errors_at_once():
    with pytest.raises(ValidationError) as exc:
        parse_book({"title": 5, "author": None, "year": "x", "isbn": 123})

    assert set(exc.value.errors) == {"title", "author", "year", "isbn"}


def test_rejects_overlong_title():
    with pytest.raises(ValidationError) as exc:
        parse_book({"title": "x" * 256, "author": "A"})
    assert "title" in exc.value.errors


def test_rejects_non_dict_payload():
    with pytest.raises(ValidationError) as exc:
        parse_book("just a string")
    assert exc.value.errors == {"body": "must be a JSON object"}
