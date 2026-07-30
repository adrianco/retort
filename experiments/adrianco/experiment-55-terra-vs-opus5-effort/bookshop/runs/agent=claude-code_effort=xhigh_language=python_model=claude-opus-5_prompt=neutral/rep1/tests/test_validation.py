"""Input validation on create, replace and patch."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from conftest import ORWELL


def _details(response):
    body = response.get_json()
    assert body["error"] == "validation_failed"
    return body["details"]


@pytest.mark.parametrize(
    "payload, missing",
    [
        ({"author": "George Orwell"}, "title"),
        ({"title": "Nineteen Eighty-Four"}, "author"),
        ({}, "title"),
    ],
)
def test_title_and_author_are_required(client, payload, missing):
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    assert _details(response)[missing] == f"{missing} is required."


def test_all_field_errors_are_reported_at_once(client):
    response = client.post("/books", json={"year": "soon", "isbn": 12345})

    assert response.status_code == 400
    assert set(_details(response)) == {"title", "author", "year", "isbn"}


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_title_is_rejected(client, blank):
    response = client.post("/books", json={"title": blank, "author": "A"})

    assert response.status_code == 400
    assert _details(response)["title"] == "title must not be empty."


@pytest.mark.parametrize("value", [42, None, [], {}, True])
def test_non_string_title_is_rejected(client, value):
    response = client.post("/books", json={"title": value, "author": "A"})

    assert response.status_code == 400
    assert _details(response)["title"] == "title must be a string."


def test_overlong_title_is_rejected(client):
    response = client.post("/books", json={"title": "x" * 501, "author": "A"})

    assert response.status_code == 400
    assert "500 characters" in _details(response)["title"]


@pytest.mark.parametrize("value", ["1949", 1949.0, True, [1949]])
def test_non_integer_year_is_rejected(client, value):
    response = client.post("/books", json={**ORWELL, "year": value})

    assert response.status_code == 400
    assert _details(response)["year"] == "year must be an integer or null."


@pytest.mark.parametrize("offset", [2, 50])
def test_year_too_far_in_the_future_is_rejected(client, offset):
    future = datetime.now(timezone.utc).year + offset

    response = client.post("/books", json={**ORWELL, "year": future})

    assert response.status_code == 400
    assert "year must be between" in _details(response)["year"]


def test_next_years_publication_is_allowed(client):
    next_year = datetime.now(timezone.utc).year + 1

    response = client.post("/books", json={**ORWELL, "year": next_year})

    assert response.status_code == 201
    assert response.get_json()["year"] == next_year


@pytest.mark.parametrize("value", [0, -1949])
def test_non_positive_year_is_rejected(client, value):
    response = client.post("/books", json={**ORWELL, "year": value})

    assert response.status_code == 400
    assert "year must be between" in _details(response)["year"]


def test_year_may_be_explicitly_null(client):
    response = client.post("/books", json={**ORWELL, "year": None})

    assert response.status_code == 201
    assert response.get_json()["year"] is None


@pytest.mark.parametrize("value", ["12345", "978045152493X", "not-an-isbn", "x" * 40])
def test_malformed_isbn_is_rejected(client, value):
    response = client.post("/books", json={**ORWELL, "isbn": value})

    assert response.status_code == 400
    assert "10- or 13-digit ISBN" in _details(response)["isbn"]


@pytest.mark.parametrize("value", ["0451524934", "045152493X", "9780451524935"])
def test_ten_and_thirteen_character_isbns_are_accepted(client, value):
    response = client.post("/books", json={**ORWELL, "isbn": value})

    assert response.status_code == 201


def test_blank_isbn_is_treated_as_absent(client):
    response = client.post("/books", json={**ORWELL, "isbn": "  "})

    assert response.status_code == 201
    assert response.get_json()["isbn"] is None


def test_duplicate_isbn_returns_409(client, create_book):
    create_book(ORWELL)

    response = client.post("/books", json={**ORWELL, "title": "Reprint"})

    assert response.status_code == 409
    assert response.get_json()["error"] == "conflict"
    assert ORWELL["isbn"] in response.get_json()["message"]


def test_books_without_isbn_do_not_collide(client, create_book):
    create_book(ORWELL, isbn=None)

    response = client.post("/books", json={"title": "Another", "author": "Someone"})

    assert response.status_code == 201


def test_patch_cannot_steal_another_books_isbn(client, create_book):
    create_book(ORWELL)
    other = create_book({"title": "Brave New World", "author": "Aldous Huxley"})

    response = client.patch(f"/books/{other['id']}", json={"isbn": ORWELL["isbn"]})

    assert response.status_code == 409


def test_put_requires_title_and_author(client, create_book):
    created = create_book()

    response = client.put(f"/books/{created['id']}", json={"year": 1950})

    assert response.status_code == 400
    assert set(_details(response)) == {"title", "author"}


def test_patch_with_no_known_fields_is_rejected(client, create_book):
    created = create_book()

    response = client.patch(f"/books/{created['id']}", json={"publisher": "Secker"})

    assert response.status_code == 400
    assert "at least one" in _details(response)["fields"]


def test_unknown_fields_are_ignored_on_create(client):
    response = client.post(
        "/books",
        json={"title": "T", "author": "A", "id": 999, "publisher": "Secker"},
    )

    assert response.status_code == 201
    book = response.get_json()
    assert book["id"] != 999
    assert "publisher" not in book


@pytest.mark.parametrize("payload", ["a string", 42, [ORWELL], None, True])
def test_body_must_be_a_json_object(client, payload):
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_failed"


def test_malformed_json_returns_400(client):
    response = client.post(
        "/books", data="{not json", content_type="application/json"
    )

    assert response.status_code == 400
    assert "valid JSON" in response.get_json()["message"]


def test_empty_body_returns_400(client):
    response = client.post("/books")

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_failed"


def test_json_body_without_content_type_is_still_accepted(client):
    response = client.post("/books", data='{"title": "T", "author": "A"}')

    assert response.status_code == 201


@pytest.mark.parametrize(
    "query, field",
    [("limit=abc", "limit"), ("limit=0", "limit"), ("limit=9999", "limit"),
     ("offset=-1", "offset"), ("offset=x", "offset")],
)
def test_invalid_pagination_is_rejected(client, query, field):
    response = client.get(f"/books?{query}")

    assert response.status_code == 400
    assert field in _details(response)
