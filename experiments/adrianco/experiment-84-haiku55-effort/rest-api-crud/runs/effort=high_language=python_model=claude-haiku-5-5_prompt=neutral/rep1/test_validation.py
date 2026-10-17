import pytest

from validation import ValidationError, validate_book

VALID = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-01359-3"}


def test_valid_book_is_cleaned_and_isbn_normalised():
    assert validate_book(VALID) == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "9780441013593",
    }


def test_text_fields_are_stripped():
    book = validate_book({"title": "  Dune  ", "author": " Frank Herbert "})
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"


def test_year_and_isbn_are_optional():
    assert validate_book({"title": "T", "author": "A"}) == {
        "title": "T",
        "author": "A",
        "year": None,
        "isbn": None,
    }


@pytest.mark.parametrize("field", ["title", "author"])
def test_title_and_author_are_required(field):
    data = {**VALID}
    del data[field]
    with pytest.raises(ValidationError) as info:
        validate_book(data)
    assert info.value.fields == {field: "is required"}


@pytest.mark.parametrize("field", ["title", "author"])
def test_blank_text_is_rejected(field):
    with pytest.raises(ValidationError) as info:
        validate_book({**VALID, field: "   "})
    assert info.value.fields == {field: "must not be blank"}


@pytest.mark.parametrize("field", ["title", "author"])
def test_text_must_be_a_string(field):
    with pytest.raises(ValidationError) as info:
        validate_book({**VALID, field: 42})
    assert info.value.fields == {field: "must be a string"}


def test_text_length_is_limited():
    with pytest.raises(ValidationError) as info:
        validate_book({**VALID, "title": "x" * 501})
    assert "title" in info.value.fields


@pytest.mark.parametrize("year", ["1965", 1.5, True, 999, 99999])
def test_invalid_year_is_rejected(year):
    with pytest.raises(ValidationError) as info:
        validate_book({**VALID, "year": year})
    assert "year" in info.value.fields


@pytest.mark.parametrize("isbn", ["123", "abcdefghij", "97804410135934", 9780441013593])
def test_invalid_isbn_is_rejected(isbn):
    with pytest.raises(ValidationError) as info:
        validate_book({**VALID, "isbn": isbn})
    assert "isbn" in info.value.fields


def test_isbn10_with_check_character_x_is_accepted():
    assert validate_book({**VALID, "isbn": "0-439-42089x"})["isbn"] == "043942089X"


def test_non_object_body_is_rejected():
    with pytest.raises(ValidationError) as info:
        validate_book(["Dune"])
    assert info.value.fields == {"body": "must be a JSON object"}


def test_all_errors_are_reported_together():
    with pytest.raises(ValidationError) as info:
        validate_book({})
    assert set(info.value.fields) == {"title", "author"}
