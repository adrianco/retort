import datetime

import pytest

from books_api.validation import MAX_AUTHOR_LENGTH, MAX_TITLE_LENGTH, ValidationError, validate_book


def errors_for(payload, **kwargs):
    with pytest.raises(ValidationError) as excinfo:
        validate_book(payload, **kwargs)
    return excinfo.value.errors


def test_valid_payload_is_cleaned_and_unknown_keys_dropped():
    cleaned = validate_book(
        {"title": "  Dune ", "author": "Frank Herbert\n", "year": 1965, "isbn": " 9780441013593 ", "id": 99}
    )
    assert cleaned == {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_only_title_and_author_are_required():
    assert validate_book({"title": "Dune", "author": "Frank Herbert"}) == {
        "title": "Dune",
        "author": "Frank Herbert",
    }


def test_missing_title_and_author_are_both_reported():
    assert errors_for({}) == {"title": "title is required", "author": "author is required"}


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "title is required"),
        ("", "title must not be empty"),
        ("   ", "title must not be empty"),
        (42, "title must be a string"),
        (["Dune"], "title must be a string"),
        ("x" * (MAX_TITLE_LENGTH + 1), f"title must be at most {MAX_TITLE_LENGTH} characters"),
    ],
)
def test_invalid_title(value, message):
    assert errors_for({"title": value, "author": "Someone"}) == {"title": message}


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "author is required"),
        ("\t", "author must not be empty"),
        ({"name": "x"}, "author must be a string"),
        ("x" * (MAX_AUTHOR_LENGTH + 1), f"author must be at most {MAX_AUTHOR_LENGTH} characters"),
    ],
)
def test_invalid_author(value, message):
    assert errors_for({"title": "Something", "author": value}) == {"author": message}


@pytest.mark.parametrize("year", [None, 1, 1949, -800, datetime.date.today().year])
def test_valid_years(year):
    assert validate_book({"title": "t", "author": "a", "year": year})["year"] == year


@pytest.mark.parametrize("year", ["1949", 1949.0, True, False, [1949]])
def test_year_must_be_an_integer(year):
    assert errors_for({"title": "t", "author": "a", "year": year}) == {"year": "year must be an integer"}


@pytest.mark.parametrize("year", [datetime.date.today().year + 1, -10000, 10**30])
def test_year_must_be_in_range(year):
    assert "between" in errors_for({"title": "t", "author": "a", "year": year})["year"]


@pytest.mark.parametrize(
    "isbn",
    ["9780452284234", "978-0-452-28423-4", "978 0 452 28423 4", "0452284236", "0-8044-2957-X", "080442957x"],
)
def test_valid_isbns_are_kept_as_given(isbn):
    assert validate_book({"title": "t", "author": "a", "isbn": isbn})["isbn"] == isbn


@pytest.mark.parametrize("isbn", ["", "   ", None])
def test_blank_isbn_means_no_isbn(isbn):
    assert validate_book({"title": "t", "author": "a", "isbn": isbn})["isbn"] is None


@pytest.mark.parametrize(
    "isbn", ["12345", "97804522842345", "978--0452284234", "-9780452284234", "X452284236", "ISBN 0452284236", 9780452284234]
)
def test_invalid_isbns(isbn):
    assert "isbn" in errors_for({"title": "t", "author": "a", "isbn": isbn})


@pytest.mark.parametrize("payload", [None, [], ["title"], "Dune", 7])
def test_payload_must_be_an_object(payload):
    assert errors_for(payload) == {"body": "request body must be a JSON object"}


def test_all_errors_are_reported_together():
    errors = errors_for({"title": "", "year": "old", "isbn": "nope"})
    assert set(errors) == {"title", "author", "year", "isbn"}


def test_partial_allows_any_subset_of_fields():
    assert validate_book({"year": 2001}, partial=True) == {"year": 2001}
    assert validate_book({"isbn": None, "year": None}, partial=True) == {"isbn": None, "year": None}


def test_partial_still_rejects_clearing_required_fields():
    assert errors_for({"title": None}, partial=True) == {"title": "title is required"}
    assert errors_for({"author": " "}, partial=True) == {"author": "author must not be empty"}


def test_partial_requires_at_least_one_known_field():
    assert "body" in errors_for({}, partial=True)
    assert "body" in errors_for({"unknown": 1}, partial=True)
