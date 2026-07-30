"""End-to-end CRUD behaviour over the HTTP layer."""

from __future__ import annotations

import re

import pytest

from bookapi import create_app
from conftest import SAMPLE_BOOK

TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")


def test_create_returns_201_with_location_and_stored_fields(client):
    response = client.post("/books", json=SAMPLE_BOOK)

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 1
    assert body["title"] == SAMPLE_BOOK["title"]
    assert body["author"] == SAMPLE_BOOK["author"]
    assert body["year"] == 1969
    assert body["isbn"] == SAMPLE_BOOK["isbn"]
    assert TIMESTAMP.match(body["created_at"])
    assert body["updated_at"] == body["created_at"]
    assert response.headers["Location"].endswith("/books/1")


def test_create_accepts_optional_fields_as_absent(client):
    response = client.post("/books", json={"title": "Untitled", "author": "Anon"})

    assert response.status_code == 201
    body = response.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_trims_surrounding_whitespace(client):
    response = client.post(
        "/books", json={"title": "  Dune \n", "author": "\tFrank Herbert "}
    )

    body = response.get_json()
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"


def test_create_never_answers_201_with_a_null_body(client, monkeypatch):
    """If the just-inserted row cannot be read back — only possible if it is
    deleted between the commit and the re-read — fail loudly rather than
    reporting success with no resource."""
    monkeypatch.setattr("bookapi.repository.get_book", lambda conn, book_id: None)

    response = client.post("/books", json={"title": "T", "author": "A"})

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_error"


def test_get_returns_the_created_book(client, created_book):
    response = client.get(f"/books/{created_book['id']}")

    assert response.status_code == 200
    assert response.get_json() == created_book


def test_list_returns_books_in_insertion_order(client):
    client.post("/books", json={"title": "First", "author": "A"})
    client.post("/books", json={"title": "Second", "author": "B"})

    response = client.get("/books")

    assert response.status_code == 200
    body = response.get_json()
    assert [book["title"] for book in body] == ["First", "Second"]


def test_list_is_empty_array_when_no_books(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []


def test_put_replaces_every_writable_field(client, created_book):
    response = client.put(
        f"/books/{created_book['id']}",
        json={"title": "The Dispossessed", "author": "U. K. Le Guin", "year": 1974},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == created_book["id"]
    assert body["title"] == "The Dispossessed"
    assert body["year"] == 1974
    # PUT is a full replacement, so the omitted isbn is cleared.
    assert body["isbn"] is None
    assert body["created_at"] == created_book["created_at"]
    assert body["updated_at"] > created_book["updated_at"]


def test_put_writes_a_new_updated_at(client, created_book, monkeypatch):
    """Pin the clock, so this fails if the UPDATE ever stops setting updated_at.

    A plain `updated_at >= created_at` assertion cannot catch that: on a freshly
    created book the two are equal, so it holds even if the column is untouched.
    """
    sentinel = "2099-12-31T23:59:59.999999Z"
    monkeypatch.setattr("bookapi.repository.utc_now", lambda: sentinel)

    response = client.put(
        f"/books/{created_book['id']}", json={"title": "T", "author": "A"}
    )

    assert response.status_code == 200
    assert response.get_json()["updated_at"] == sentinel
    assert response.get_json()["created_at"] == created_book["created_at"]
    # And it is the stored value, not just the response body.
    stored = client.get(f"/books/{created_book['id']}").get_json()
    assert stored["updated_at"] == sentinel


def test_put_persists_the_change(client, created_book):
    client.put(
        f"/books/{created_book['id']}", json={"title": "Changed", "author": "Someone"}
    )

    body = client.get(f"/books/{created_book['id']}").get_json()
    assert body["title"] == "Changed"


def test_put_accepts_a_round_tripped_representation(client, created_book):
    """GET then PUT the same object back: server-owned fields are ignored."""
    edited = dict(created_book, title="Revised Title")

    response = client.put(f"/books/{created_book['id']}", json=edited)

    assert response.status_code == 200
    assert response.get_json()["title"] == "Revised Title"


def test_delete_returns_204_then_the_book_is_gone(client, created_book):
    response = client.delete(f"/books/{created_book['id']}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert client.get(f"/books/{created_book['id']}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_twice_returns_404(client, created_book):
    client.delete(f"/books/{created_book['id']}")

    assert client.delete(f"/books/{created_book['id']}").status_code == 404


def test_missing_book_returns_404_for_every_verb(client):
    assert client.get("/books/999").status_code == 404
    assert client.delete("/books/999").status_code == 404
    put = client.put("/books/999", json={"title": "T", "author": "A"})
    assert put.status_code == 404
    assert put.get_json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("book_id", ["abc", "1.5", "-1", "%20", "1a"])
def test_unparseable_id_returns_404(client, book_id):
    assert client.get(f"/books/{book_id}").status_code == 404


def test_trailing_slash_on_the_collection_still_lists(client, created_book):
    """/books/ is the collection, not a book with an empty id."""
    response = client.get("/books/")

    assert response.status_code == 200
    assert response.get_json() == [created_book]


@pytest.mark.parametrize(
    "book_id",
    [
        2**63,  # first value SQLite cannot bind as an integer
        10**30,
        int("9" * 400),
    ],
)
def test_id_beyond_sqlite_integer_range_returns_404_not_500(client, book_id):
    """Binding an out-of-range int raises OverflowError, which is not a
    sqlite3.Error -- it must be stopped at routing, not become a 500."""
    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.delete(f"/books/{book_id}").status_code == 404
    put = client.put(f"/books/{book_id}", json={"title": "T", "author": "A"})
    assert put.status_code == 404


def test_largest_bindable_id_still_reaches_the_query(client):
    assert client.get(f"/books/{2**63 - 1}").status_code == 404


def test_data_survives_a_fresh_application_on_the_same_file(client, db_path):
    client.post("/books", json=SAMPLE_BOOK)

    reopened = create_app({"DATABASE": str(db_path), "TESTING": True})
    body = reopened.test_client().get("/books").get_json()

    assert [book["title"] for book in body] == [SAMPLE_BOOK["title"]]
