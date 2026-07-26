"""Tests for POST /books."""

from __future__ import annotations

from .conftest import SAMPLE_BOOK


def test_create_returns_201_with_the_stored_book(client):
    response = client.post("/books", json=SAMPLE_BOOK)

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] > 0
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "978-0-441-01359-3"
    assert body["created_at"] == body["updated_at"]


def test_create_sets_a_location_header_pointing_at_the_new_book(client):
    response = client.post("/books", json=SAMPLE_BOOK)
    location = response.headers["Location"]

    assert location == "/books/{}".format(response.get_json()["id"])
    assert client.get(location).get_json() == response.get_json()


def test_created_book_is_immediately_readable(client, create_book):
    book = create_book()

    fetched = client.get("/books/{}".format(book["id"]))

    assert fetched.status_code == 200
    assert fetched.get_json() == book


def test_year_and_isbn_are_optional(client):
    response = client.post("/books", json={"title": "Untitled", "author": "Anonymous"})

    assert response.status_code == 201
    body = response.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_explicit_nulls_are_accepted_for_optional_fields(client):
    response = client.post(
        "/books", json={"title": "Untitled", "author": "Anonymous", "year": None, "isbn": None}
    )

    assert response.status_code == 201
    assert response.get_json()["year"] is None


def test_surrounding_whitespace_is_trimmed(client):
    response = client.post("/books", json={"title": "  Dune  ", "author": "\tFrank Herbert\n"})

    body = response.get_json()
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"


def test_ids_are_assigned_sequentially(create_book):
    first = create_book(isbn=None)
    second = create_book(isbn=None)

    assert second["id"] == first["id"] + 1


def test_client_supplied_ids_and_timestamps_are_ignored(client):
    response = client.post(
        "/books",
        json={
            "id": 999,
            "title": "Dune",
            "author": "Frank Herbert",
            "created_at": "1900-01-01T00:00:00Z",
            "unknown_field": "ignored",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] != 999
    assert body["created_at"] != "1900-01-01T00:00:00Z"


def test_a_duplicate_isbn_is_rejected_with_409(client, create_book):
    create_book(isbn="9780441013593")

    response = client.post(
        "/books", json={"title": "Dune reprint", "author": "Frank Herbert", "isbn": "978-0-441-01359-3"}
    )

    assert response.status_code == 409
    body = response.get_json()
    assert body["error"] == "conflict"
    assert "isbn" in body["details"]


def test_books_without_an_isbn_do_not_collide(create_book):
    first = create_book(title="One", isbn=None)
    second = create_book(title="Two", isbn=None)

    assert first["id"] != second["id"]


def test_a_missing_content_type_header_is_tolerated(client):
    response = client.post(
        "/books", data='{"title": "Dune", "author": "Frank Herbert"}', content_type="text/plain"
    )

    assert response.status_code == 201
