"""Tests for input validation on POST and PUT."""

import pytest

from sample_data import SAMPLE_BOOK


def fields_in_error(response):
    """Collect the field names mentioned in a validation error response."""
    return {
        detail.get("field") for detail in response.get_json().get("details", [])
    }


# --------------------------------------------------------------------------- #
# Required fields
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("missing", ["title", "author"])
def test_missing_required_field_is_rejected(client, missing):
    payload = {key: value for key, value in SAMPLE_BOOK.items() if key != missing}

    response = client.post("/books", json=payload)

    assert response.status_code == 400
    assert missing in fields_in_error(response)
    assert missing in response.get_json()["error"]


def test_all_missing_fields_are_reported_at_once(client):
    response = client.post("/books", json={"year": 1999})

    assert response.status_code == 400
    assert fields_in_error(response) == {"title", "author"}


@pytest.mark.parametrize("value", ["", "   ", None])
def test_blank_title_is_rejected(client, value):
    response = client.post("/books", json={**SAMPLE_BOOK, "title": value})

    assert response.status_code == 400
    assert "title" in fields_in_error(response)


@pytest.mark.parametrize("value", [123, True, ["a"], {"a": 1}])
def test_non_string_author_is_rejected(client, value):
    response = client.post("/books", json={**SAMPLE_BOOK, "author": value})

    assert response.status_code == 400
    assert "author" in fields_in_error(response)


def test_over_long_title_is_rejected(client):
    response = client.post("/books", json={**SAMPLE_BOOK, "title": "x" * 501})

    assert response.status_code == 400


def test_nothing_is_stored_when_validation_fails(client):
    client.post("/books", json={"title": "No Author"})

    assert client.get("/books").get_json() == []


def test_surrounding_whitespace_is_trimmed(client):
    response = client.post(
        "/books", json={"title": "  Dune  ", "author": "\tFrank Herbert\n"}
    )

    book = response.get_json()
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"


# --------------------------------------------------------------------------- #
# Optional fields
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("value", ["nineteen", 0, 10000, 1937.5, True, []])
def test_invalid_year_is_rejected(client, value):
    response = client.post("/books", json={**SAMPLE_BOOK, "year": value})

    assert response.status_code == 400
    assert "year" in fields_in_error(response)


def test_year_may_be_sent_as_a_numeric_string(client):
    response = client.post("/books", json={**SAMPLE_BOOK, "year": "1937"})

    assert response.status_code == 201
    assert response.get_json()["year"] == 1937


@pytest.mark.parametrize("value", ["12345", "abcdefghij", "97803616-0", 3.5])
def test_invalid_isbn_is_rejected(client, value):
    response = client.post("/books", json={**SAMPLE_BOOK, "isbn": value})

    assert response.status_code == 400
    assert "isbn" in fields_in_error(response)


@pytest.mark.parametrize(
    "value",
    ["9780547928227", "978-0-547-92822-7", "0261102737", "026110273X"],
)
def test_valid_isbn_formats_are_stored_verbatim(client, value):
    response = client.post("/books", json={**SAMPLE_BOOK, "isbn": value})

    assert response.status_code == 201
    assert response.get_json()["isbn"] == value


def test_blank_optional_fields_become_null(client):
    response = client.post(
        "/books", json={**SAMPLE_BOOK, "year": "", "isbn": "  "}
    )

    assert response.status_code == 201
    assert response.get_json()["year"] is None
    assert response.get_json()["isbn"] is None


# --------------------------------------------------------------------------- #
# Body handling
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("body", ["", "not json", "[1, 2, 3]", '"a string"'])
def test_non_object_bodies_are_rejected(client, body):
    response = client.post(
        "/books", data=body, content_type="application/json"
    )

    assert response.status_code == 400
    assert "JSON object" in response.get_json()["error"]


def test_unknown_fields_are_ignored(client):
    response = client.post(
        "/books",
        json={**SAMPLE_BOOK, "id": 999, "publisher": "Allen & Unwin"},
    )

    assert response.status_code == 201
    book = response.get_json()
    assert book["id"] != 999
    assert "publisher" not in book


# --------------------------------------------------------------------------- #
# Validation on update
# --------------------------------------------------------------------------- #


def test_update_with_an_empty_object_is_rejected(client, make_book):
    created = make_book()

    response = client.put(f"/books/{created['id']}", json={})

    assert response.status_code == 400


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"author": None}, {"year": "soon"}, {"isbn": "nope"}],
)
def test_invalid_update_is_rejected(client, make_book, payload):
    created = make_book()

    response = client.put(f"/books/{created['id']}", json=payload)

    assert response.status_code == 400
    assert client.get(f"/books/{created['id']}").get_json() == created
