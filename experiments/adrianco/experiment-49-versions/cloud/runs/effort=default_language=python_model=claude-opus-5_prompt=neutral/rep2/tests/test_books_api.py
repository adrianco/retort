"""Integration tests for the book endpoints, driven through HTTP."""

from __future__ import annotations

import pytest

from tests.conftest import SAMPLE


# ------------------------------------------------------------------ health


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


# ------------------------------------------------------------------ create


def test_create_book_returns_201_with_the_stored_book(client):
    response = client.post("/books", json={**SAMPLE, "isbn": "978-0441013593"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"] >= 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441013593"  # separators are stripped on the way in
    assert body["created_at"] == body["updated_at"]
    assert response.headers["Location"] == f"/books/{body['id']}"


def test_create_book_without_optional_fields(client):
    response = client.post("/books", json={"title": "Untitled", "author": "Anon"})

    assert response.status_code == 201
    assert response.json()["year"] is None
    assert response.json()["isbn"] is None


def test_created_book_is_retrievable(client, make_book):
    created = make_book(title="Neuromancer", author="William Gibson", year=1984)

    response = client.get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_ids_are_unique_per_book(make_book):
    first = make_book()
    second = make_book(title="Dune Messiah")

    assert first["id"] != second["id"]


def test_duplicate_isbn_is_rejected_with_409(client, make_book):
    make_book(isbn="9780441013593")

    response = client.post("/books", json={**SAMPLE, "isbn": "978-0-441-01359-3"})

    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


# -------------------------------------------------------------------- list


def test_list_is_empty_before_anything_is_created(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_every_book(make_book, client):
    make_book(title="Dune")
    make_book(title="Snow Crash", author="Neal Stephenson")

    response = client.get("/books")

    assert response.status_code == 200
    assert [book["title"] for book in response.json()] == ["Dune", "Snow Crash"]


def test_list_filters_by_author(make_book, client):
    make_book(title="Dune", author="Frank Herbert")
    make_book(title="Dune Messiah", author="Frank Herbert")
    make_book(title="Snow Crash", author="Neal Stephenson")

    response = client.get("/books", params={"author": "Frank Herbert"})

    assert response.status_code == 200
    assert [book["title"] for book in response.json()] == ["Dune", "Dune Messiah"]


def test_author_filter_is_case_insensitive(make_book, client):
    make_book(author="Ursula K. Le Guin")

    response = client.get("/books", params={"author": "ursula k. le guin"})

    assert len(response.json()) == 1


def test_author_filter_with_no_match_returns_empty_list(make_book, client):
    make_book(author="Frank Herbert")

    response = client.get("/books", params={"author": "Nobody"})

    assert response.status_code == 200
    assert response.json() == []


def test_blank_author_filter_is_ignored(make_book, client):
    make_book()

    response = client.get("/books?author=")

    assert len(response.json()) == 1


# ------------------------------------------------------------------ update


def test_update_replaces_the_book(client, make_book):
    created = make_book(year=1965)

    response = client.put(
        f"/books/{created['id']}",
        json={"title": "Dune (revised)", "author": "F. Herbert", "year": 1990},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["title"] == "Dune (revised)"
    assert body["author"] == "F. Herbert"
    assert body["year"] == 1990
    assert body["created_at"] == created["created_at"]
    assert client.get(f"/books/{created['id']}").json() == body


def test_update_clears_omitted_optional_fields(client, make_book):
    created = make_book(year=1965, isbn="9780441013593")

    response = client.put(f"/books/{created['id']}", json={"title": "Dune", "author": "FH"})

    assert response.status_code == 200
    assert response.json()["year"] is None
    assert response.json()["isbn"] is None


def test_update_to_an_isbn_owned_by_another_book_returns_409(client, make_book):
    make_book(isbn="9780441013593")
    other = make_book(title="Snow Crash")

    response = client.put(
        f"/books/{other['id']}",
        json={"title": "Snow Crash", "author": "Neal Stephenson", "isbn": "9780441013593"},
    )

    assert response.status_code == 409


# ------------------------------------------------------------------ delete


def test_delete_removes_the_book(client, make_book):
    created = make_book()

    response = client.delete(f"/books/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.get("/books").json() == []


def test_delete_twice_returns_404(client, make_book):
    created = make_book()
    client.delete(f"/books/{created['id']}")

    assert client.delete(f"/books/{created['id']}").status_code == 404


# --------------------------------------------------------------- not found


@pytest.mark.parametrize(
    ("method", "payload"),
    [
        ("get", None),
        ("put", {"title": "t", "author": "a"}),
        ("delete", None),
    ],
)
def test_unknown_id_returns_404(client, method, payload):
    kwargs = {"json": payload} if payload is not None else {}

    response = getattr(client, method)("/books/4242", **kwargs)

    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "not_found"
    assert "4242" in body["message"]


def test_non_numeric_id_returns_400(client):
    response = client.get("/books/not-a-number")

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    assert response.json()["details"][0]["field"] == "book_id"
