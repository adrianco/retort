"""HTTP-level tests that drive the API through Flask's test client."""

from pathlib import Path

import pytest
from flask import Flask

import app as app_module
from app import create_app

DUNE = {
    "title": "Dune",
    "author": "Frank Herbert",
    "year": 1965,
    "isbn": "978-0-441-17271-9",
}


# --- health ------------------------------------------------------------------


def test_health_check_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_check_fails_when_database_is_unusable(app, client):
    # With the file gone, SQLite opens a new, empty database: no books table.
    Path(app.config["DATABASE"]).unlink()

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "unavailable"}


# --- create ------------------------------------------------------------------


def test_create_book(client):
    response = client.post("/books", json=DUNE)

    assert response.status_code == 201
    assert response.headers["Location"] == "/books/1"
    assert response.get_json() == {
        "id": 1,
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "9780441172719",
    }


def test_create_book_with_only_the_required_fields(client):
    response = client.post("/books", json={"title": "Emma", "author": "Jane Austen"})

    assert response.status_code == 201
    assert response.get_json() == {
        "id": 1,
        "title": "Emma",
        "author": "Jane Austen",
        "year": None,
        "isbn": None,
    }


@pytest.mark.parametrize("field", ["title", "author"])
def test_create_book_requires_title_and_author(client, field):
    payload = {name: value for name, value in DUNE.items() if name != field}

    response = client.post("/books", json=payload)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Invalid book data",
        "details": {field: f"{field} is required"},
    }
    assert client.get("/books").get_json() == []


def test_create_book_reports_every_invalid_field(client):
    payload = {"title": "  ", "year": "1965", "isbn": "123", "rating": 5}

    response = client.post("/books", json=payload)

    assert response.status_code == 400
    assert response.get_json()["details"] == {
        "title": "title is required",
        "author": "author is required",
        "year": "year must be an integer",
        "isbn": "isbn must be a valid ISBN-10 or ISBN-13",
        "rating": "unknown field",
    }


@pytest.mark.parametrize(
    ("request_body", "status", "error"),
    [
        ({"json": ["Dune"]}, 400, "Request body must be a JSON object"),
        (
            {"data": '{"title": "Dune",', "content_type": "application/json"},
            400,
            "Request body is not valid JSON",
        ),
        ({"data": "title=Dune", "content_type": "text/plain"}, 415, None),
        ({"json": {"title": "x" * 70_000, "author": "A"}}, 413, None),
    ],
    ids=["not-an-object", "malformed-json", "not-json", "too-large"],
)
def test_create_book_rejects_unusable_bodies(client, request_body, status, error):
    response = client.post("/books", **request_body)

    assert response.status_code == status
    assert response.is_json
    if error is not None:
        assert response.get_json() == {"error": error}


# --- list --------------------------------------------------------------------


def test_list_books_is_empty_initially(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []


def test_list_books_returns_every_book_in_creation_order(client, add_book):
    books = [add_book(title=title) for title in ("Dune", "Emma", "Beloved")]

    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == books


@pytest.mark.parametrize(
    ("author", "titles"),
    [
        ("Frank Herbert", ["Dune"]),
        ("herbert", ["Dune", "Dune: House Atreides"]),  # case-insensitive substring
        ("GARCÍA", ["Cien años de soledad"]),  # non-ASCII letters fold too
        ("%", []),  # no SQL wildcards
        ("Tolkien", []),
        ("  ", ["Dune", "Dune: House Atreides", "Cien años de soledad"]),  # no filter
    ],
)
def test_list_books_filters_by_author(client, add_book, author, titles):
    add_book(title="Dune", author="Frank Herbert")
    add_book(title="Dune: House Atreides", author="Brian Herbert")
    add_book(title="Cien años de soledad", author="Gabriel García Márquez")

    response = client.get("/books", query_string={"author": author})

    assert response.status_code == 200
    assert [book["title"] for book in response.get_json()] == titles


# --- read one ----------------------------------------------------------------


def test_get_book(client, add_book):
    book = add_book(**DUNE)

    response = client.get(f"/books/{book['id']}")

    assert response.status_code == 200
    assert response.get_json() == book


def test_get_missing_book_returns_404(client):
    response = client.get("/books/42")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Book 42 not found"}


# --- update ------------------------------------------------------------------


def test_update_book_replaces_it(client, add_book):
    book = add_book(**DUNE)
    changes = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}

    response = client.put(f"/books/{book['id']}", json=changes)

    expected = {"id": book["id"], **changes, "isbn": None}  # omitted, so cleared
    assert response.status_code == 200
    assert response.get_json() == expected
    assert client.get(f"/books/{book['id']}").get_json() == expected


def test_update_book_accepts_a_fetched_book_sent_back(client, add_book):
    book = add_book(**DUNE)

    response = client.put(f"/books/{book['id']}", json={**book, "year": 1966})

    assert response.status_code == 200
    assert response.get_json() == {**book, "year": 1966}


def test_update_book_rejects_invalid_data_and_keeps_the_book(client, add_book):
    book = add_book()

    response = client.put(f"/books/{book['id']}", json={"title": "Dune Messiah"})

    assert response.status_code == 400
    assert response.get_json()["details"] == {"author": "author is required"}
    assert client.get(f"/books/{book['id']}").get_json() == book


def test_update_missing_book_returns_404(client):
    response = client.put("/books/42", json=DUNE)

    assert response.status_code == 404
    assert response.get_json() == {"error": "Book 42 not found"}


# --- delete ------------------------------------------------------------------


def test_delete_book(client, add_book):
    book = add_book()

    response = client.delete(f"/books/{book['id']}")

    assert response.status_code == 200
    assert response.get_json() == {"id": book["id"], "deleted": True}
    assert client.get(f"/books/{book['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    response = client.delete("/books/42")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Book 42 not found"}


def test_ids_of_deleted_books_are_not_reused(client, add_book):
    book = add_book()
    client.delete(f"/books/{book['id']}")

    assert add_book()["id"] == book["id"] + 1


# --- general -----------------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_ids_beyond_the_sqlite_integer_range_are_not_found(client, method):
    response = getattr(client, method)(f"/books/{2**63}", json=DUNE)

    assert response.status_code == 404
    assert response.get_json() == {"error": f"Book {2**63} not found"}


def test_unknown_route_returns_json_404(client):
    response = client.get("/authors")

    assert response.status_code == 404
    assert "error" in response.get_json()


def test_unsupported_method_returns_json_405(client):
    response = client.patch("/books/1", json={"year": 1966})

    assert response.status_code == 405
    assert "error" in response.get_json()
    assert {"GET", "PUT", "DELETE"} <= set(response.headers["Allow"].split(", "))


def test_books_persist_across_restarts(tmp_path):
    config = {"TESTING": True, "DATABASE": tmp_path / "books.db"}
    create_app(config).test_client().post("/books", json=DUNE)

    restarted = create_app(config).test_client()

    assert [book["title"] for book in restarted.get("/books").get_json()] == ["Dune"]


def test_main_serves_on_host_and_port_from_the_environment(monkeypatch, tmp_path):
    database = tmp_path / "data" / "books.db"
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("BOOKS_DB_PATH", str(database))
    runs = []
    monkeypatch.setattr(Flask, "run", lambda self, **options: runs.append(options))

    app_module.main()

    assert runs == [{"host": "0.0.0.0", "port": 9000}]
    assert database.exists()
