"""Integration tests: every endpoint driven over HTTP via FastAPI's TestClient."""

from __future__ import annotations

import sqlite3

import pytest

from conftest import create


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #

def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


# --------------------------------------------------------------------------- #
# POST /books
# --------------------------------------------------------------------------- #

def test_create_book_returns_201_with_the_stored_resource(client, sample_book):
    response = client.post("/books", json=sample_book)

    assert response.status_code == 201
    book = response.json()
    assert book["id"] > 0
    assert book["title"] == sample_book["title"]
    assert book["author"] == sample_book["author"]
    assert book["year"] == 1969
    # Hyphens are stripped so ISBNs compare equal regardless of formatting.
    assert book["isbn"] == "9780441478125"
    assert response.headers["location"] == f"/books/{book['id']}"


def test_create_book_persists_to_sqlite(client, db_path, sample_book):
    book = client.post("/books", json=sample_book).json()

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT title, author, year, isbn FROM books WHERE id = ?", (book["id"],)
        ).fetchone()
    finally:
        conn.close()

    assert row == (sample_book["title"], sample_book["author"], 1969, "9780441478125")


def test_create_book_accepts_only_the_required_fields(client):
    response = client.post("/books", json={"title": "Untitled", "author": "Anon"})

    assert response.status_code == 201
    assert response.json()["year"] is None
    assert response.json()["isbn"] is None


def test_created_books_get_distinct_ids(client):
    first = create(client, title="One")
    second = create(client, title="Two")

    assert first["id"] != second["id"]


@pytest.mark.parametrize(
    ("payload", "bad_field"),
    [
        ({"author": "Anon"}, "title"),
        ({"title": "Untitled"}, "author"),
        ({"title": "", "author": "Anon"}, "title"),
        ({"title": "   ", "author": "Anon"}, "title"),
        ({"title": "Untitled", "author": ""}, "author"),
        ({"title": 42, "author": "Anon"}, "title"),
        ({"title": "Untitled", "author": "Anon", "year": "long ago"}, "year"),
        ({"title": "Untitled", "author": "Anon", "year": 3999}, "year"),
        ({"title": "Untitled", "author": "Anon", "year": 5}, "year"),
        ({"title": "Untitled", "author": "Anon", "isbn": "12345"}, "isbn"),
        ({"title": "Untitled", "author": "Anon", "isbn": "not-an-isbn!"}, "isbn"),
    ],
)
def test_create_book_rejects_invalid_input(client, payload, bad_field):
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "Validation failed"
    assert bad_field in [error["field"] for error in body["errors"]]


def test_create_book_rejects_malformed_json(client):
    response = client.post(
        "/books", content=b"{not json", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 400


def test_duplicate_isbn_is_rejected_with_409(client, sample_book):
    assert client.post("/books", json=sample_book).status_code == 201

    duplicate = dict(sample_book, title="A reprint")
    response = client.post("/books", json=duplicate)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_books_without_an_isbn_do_not_collide(client):
    create(client, title="One")
    create(client, title="Two")

    assert len(client.get("/books").json()) == 2


# --------------------------------------------------------------------------- #
# GET /books
# --------------------------------------------------------------------------- #

def test_list_books_is_empty_initially(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.json() == []


def test_list_books_returns_every_book_in_id_order(client):
    created = [create(client, title=f"Book {n}") for n in range(3)]

    response = client.get("/books")

    assert response.status_code == 200
    assert [book["id"] for book in response.json()] == [b["id"] for b in created]


def test_list_books_filters_by_author(client):
    create(client, title="A Wizard of Earthsea", author="Ursula K. Le Guin")
    create(client, title="The Dispossessed", author="Ursula K. Le Guin")
    create(client, title="Dune", author="Frank Herbert")

    response = client.get("/books", params={"author": "Ursula K. Le Guin"})

    assert response.status_code == 200
    titles = sorted(book["title"] for book in response.json())
    assert titles == ["A Wizard of Earthsea", "The Dispossessed"]


def test_author_filter_is_case_insensitive_and_partial(client):
    create(client, author="Ursula K. Le Guin")
    create(client, author="Frank Herbert")

    assert len(client.get("/books", params={"author": "le guin"}).json()) == 1
    assert len(client.get("/books", params={"author": "HERBERT"}).json()) == 1
    assert client.get("/books", params={"author": "Tolkien"}).json() == []


def test_author_filter_does_not_treat_input_as_a_sql_wildcard(client):
    create(client, title="Underscore", author="Ann_Marie Smith")
    create(client, title="Wildcard", author="AnnXMarie Smith")

    matched = client.get("/books", params={"author": "Ann_Marie"}).json()

    assert [book["title"] for book in matched] == ["Underscore"]


def test_list_books_supports_limit_and_offset(client):
    ids = [create(client, title=f"Book {n}")["id"] for n in range(5)]

    page = client.get("/books", params={"limit": 2, "offset": 1})

    assert page.status_code == 200
    assert [book["id"] for book in page.json()] == ids[1:3]


def test_list_books_rejects_a_nonsense_limit(client):
    assert client.get("/books", params={"limit": 0}).status_code == 400
    assert client.get("/books", params={"offset": -1}).status_code == 400


# --------------------------------------------------------------------------- #
# GET /books/{id}
# --------------------------------------------------------------------------- #

def test_get_book_returns_the_book(client, sample_book):
    created = client.post("/books", json=sample_book).json()

    response = client.get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_book_returns_404_for_an_unknown_id(client):
    response = client.get("/books/4242")

    assert response.status_code == 404
    assert response.json()["detail"] == "Book with id 4242 not found"


def test_get_book_rejects_a_non_numeric_id(client):
    assert client.get("/books/not-a-number").status_code == 400


# --------------------------------------------------------------------------- #
# PUT /books/{id}
# --------------------------------------------------------------------------- #

def test_put_replaces_the_whole_book(client, sample_book):
    created = client.post("/books", json=sample_book).json()

    response = client.put(
        f"/books/{created['id']}",
        json={"title": "The Dispossessed", "author": "Ursula K. Le Guin"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["id"] == created["id"]
    assert updated["title"] == "The Dispossessed"
    # Fields omitted from a PUT are cleared, because PUT replaces the resource.
    assert updated["year"] is None
    assert updated["isbn"] is None
    assert client.get(f"/books/{created['id']}").json() == updated


def test_put_returns_404_for_an_unknown_id(client):
    response = client.put("/books/4242", json={"title": "Ghost", "author": "Nobody"})

    assert response.status_code == 404


def test_put_validates_its_payload(client):
    created = create(client)

    response = client.put(f"/books/{created['id']}", json={"title": "Only a title"})

    assert response.status_code == 400
    assert client.get(f"/books/{created['id']}").json() == created


def test_put_rejects_an_isbn_owned_by_another_book(client):
    create(client, title="First", isbn="9780441478125")
    second = create(client, title="Second")

    response = client.put(
        f"/books/{second['id']}",
        json={"title": "Second", "author": "An Author", "isbn": "9780441478125"},
    )

    assert response.status_code == 409


def test_put_can_keep_its_own_isbn(client):
    book = create(client, isbn="9780441478125")

    response = client.put(
        f"/books/{book['id']}",
        json={"title": "Renamed", "author": "An Author", "isbn": "978-0-441-47812-5"},
    )

    assert response.status_code == 200
    assert response.json()["isbn"] == "9780441478125"


# --------------------------------------------------------------------------- #
# PATCH /books/{id}
# --------------------------------------------------------------------------- #

def test_patch_updates_only_the_supplied_fields(client, sample_book):
    created = client.post("/books", json=sample_book).json()

    response = client.patch(f"/books/{created['id']}", json={"title": "New Title"})

    assert response.status_code == 200
    patched = response.json()
    assert patched["title"] == "New Title"
    assert patched["author"] == created["author"]
    assert patched["year"] == created["year"]
    assert patched["isbn"] == created["isbn"]


def test_patch_can_clear_an_optional_field(client, sample_book):
    created = client.post("/books", json=sample_book).json()

    response = client.patch(f"/books/{created['id']}", json={"year": None})

    assert response.status_code == 200
    assert response.json()["year"] is None


def test_patch_rejects_an_empty_body(client):
    created = create(client)

    assert client.patch(f"/books/{created['id']}", json={}).status_code == 400


def test_patch_rejects_nulling_a_required_field(client):
    created = create(client)

    assert client.patch(f"/books/{created['id']}", json={"title": None}).status_code == 400


def test_patch_returns_404_for_an_unknown_id(client):
    assert client.patch("/books/4242", json={"title": "Ghost"}).status_code == 404


# --------------------------------------------------------------------------- #
# DELETE /books/{id}
# --------------------------------------------------------------------------- #

def test_delete_removes_the_book(client):
    created = create(client)

    response = client.delete(f"/books/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.get("/books").json() == []


def test_delete_is_not_idempotent_about_status_codes(client):
    created = create(client)

    assert client.delete(f"/books/{created['id']}").status_code == 204
    assert client.delete(f"/books/{created['id']}").status_code == 404


def test_delete_frees_the_isbn_for_reuse(client):
    created = create(client, isbn="9780441478125")
    client.delete(f"/books/{created['id']}")

    assert client.post(
        "/books", json={"title": "Reissue", "author": "An Author", "isbn": "9780441478125"}
    ).status_code == 201


# --------------------------------------------------------------------------- #
# Cross-cutting
# --------------------------------------------------------------------------- #

def test_full_crud_lifecycle(client, sample_book):
    created = client.post("/books", json=sample_book).json()
    book_id = created["id"]

    assert client.get(f"/books/{book_id}").status_code == 200
    assert len(client.get("/books").json()) == 1

    updated = client.put(
        f"/books/{book_id}",
        json={"title": "Revised", "author": "Ursula K. Le Guin", "year": 1976},
    ).json()
    assert updated["title"] == "Revised"
    assert updated["year"] == 1976

    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get("/books").json() == []


def test_data_survives_an_application_restart(client, db_path, sample_book):
    from fastapi.testclient import TestClient

    from main import app

    created = client.post("/books", json=sample_book).json()

    with TestClient(app) as reborn:
        assert reborn.get(f"/books/{created['id']}").json() == created


def test_unknown_route_returns_json_404(client):
    response = client.get("/no-such-route")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_openapi_schema_is_served(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert {"/books", "/books/{book_id}", "/health"} <= set(paths)
