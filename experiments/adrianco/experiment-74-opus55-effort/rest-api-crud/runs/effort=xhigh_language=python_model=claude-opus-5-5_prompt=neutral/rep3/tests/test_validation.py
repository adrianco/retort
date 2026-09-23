import datetime

import pytest

from books_api.validation import MAX_TEXT_LENGTH, ValidationError, validate_book

YEAR = 2026


def errors_for(payload):
    with pytest.raises(ValidationError) as excinfo:
        validate_book(payload, current_year=YEAR)
    return excinfo.value.errors


def test_valid_payload_is_cleaned():
    fields = validate_book(
        {"title": "  Dune ", "author": "Frank Herbert\n", "year": 1965, "isbn": " 0-441-17271-7 "},
        current_year=YEAR,
    )
    assert fields == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "0-441-17271-7",
    }


def test_only_title_and_author_are_required():
    fields = validate_book({"title": "Dune", "author": "Frank Herbert"}, current_year=YEAR)
    assert fields == {"title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}


def test_missing_title_and_author_are_both_reported():
    assert errors_for({}) == {"title": "title is required", "author": "author is required"}


@pytest.mark.parametrize(
    "value, message",
    [
        (None, "title is required"),
        ("", "title must not be blank"),
        ("   ", "title must not be blank"),
        (42, "title must be a string"),
        (["Dune"], "title must be a string"),
        ("x" * (MAX_TEXT_LENGTH + 1), f"title must be at most {MAX_TEXT_LENGTH} characters"),
    ],
)
def test_invalid_title(value, message):
    assert errors_for({"title": value, "author": "Frank Herbert"}) == {"title": message}


def test_invalid_author():
    assert errors_for({"title": "Dune", "author": " "}) == {"author": "author must not be blank"}


def test_title_at_max_length_is_accepted():
    title = "x" * MAX_TEXT_LENGTH
    assert validate_book({"title": title, "author": "A"}, current_year=YEAR)["title"] == title


@pytest.mark.parametrize("value", ["1965", 1965.0, True, {"y": 1965}])
def test_year_must_be_an_integer(value):
    errors = errors_for({"title": "Dune", "author": "Frank Herbert", "year": value})
    assert errors == {"year": "year must be an integer"}


@pytest.mark.parametrize("value", [0, -500, YEAR + 1, 10**30])
def test_year_must_be_in_range(value):
    errors = errors_for({"title": "Dune", "author": "Frank Herbert", "year": value})
    assert errors == {"year": f"year must be between 1 and {YEAR}"}


def test_current_year_is_accepted():
    assert validate_book({"title": "T", "author": "A", "year": YEAR}, current_year=YEAR)["year"] == YEAR


@pytest.mark.parametrize(
    "isbn",
    ["0441172717", "0-441-17271-7", "080442957X", "080442957x", "9780441172719", "978-0-441-17271-9", "978 0 441 17271 9"],
)
def test_valid_isbn_formats(isbn):
    assert validate_book({"title": "T", "author": "A", "isbn": isbn}, current_year=YEAR)["isbn"] == isbn


@pytest.mark.parametrize(
    "isbn",
    ["12345", "978044117271", "97804411727190", "X441172717", "978044117271X", "abcdefghij", "978-0-441-17271-9-----", "٠٤٤١١٧٢٧١٧"],
)
def test_invalid_isbn_formats(isbn):
    errors = errors_for({"title": "T", "author": "A", "isbn": isbn})
    assert set(errors) == {"isbn"}


def test_isbn_must_be_a_string():
    assert errors_for({"title": "T", "author": "A", "isbn": 9780441172719}) == {"isbn": "isbn must be a string"}


@pytest.mark.parametrize("isbn", [None, "", "   "])
def test_blank_isbn_is_stored_as_null(isbn):
    assert validate_book({"title": "T", "author": "A", "isbn": isbn}, current_year=YEAR)["isbn"] is None


def test_unknown_fields_are_rejected():
    errors = errors_for({"title": "T", "author": "A", "autor": "typo"})
    assert list(errors) == ["autor"]


def test_id_is_accepted_but_ignored():
    fields = validate_book({"id": 99, "title": "T", "author": "A"}, current_year=YEAR)
    assert "id" not in fields


@pytest.mark.parametrize("payload", [[], "Dune", 1, None])
def test_payload_must_be_an_object(payload):
    with pytest.raises(ValidationError, match="must be a JSON object"):
        validate_book(payload)


def test_defaults_to_the_real_current_year():
    this_year = datetime.date.today().year
    assert validate_book({"title": "T", "author": "A", "year": this_year})["year"] == this_year
    with pytest.raises(ValidationError):
        validate_book({"title": "T", "author": "A", "year": this_year + 1})
