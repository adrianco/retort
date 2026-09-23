"""Integration tests of the HTTP API, through Flask's test client."""

import sqlite3

import pytest

from bookapi import create_app
from bookapi.repository import BookRepository

ORWELL = {
    "title": "Nineteen Eighty-Four",
    "author": "George Orwell",
    "year": 1949,
    "isbn": "9780451524935",
}


# -- GET /health ----------------------------------------------------------------


def test_health_check_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


@pytest.mark.parametrize("breakage", ["missing directory", "deleted file", "corrupt file"])
def test_health_check_reports_unusable_database(app, client, tmp_path, breakage):
    database = tmp_path / "books.db"
    if breakage == "missing directory":
        app.config["DATABASE"] = str(tmp_path / "no-such-directory" / "books.db")
    elif breakage == "deleted file":
        database.unlink()
    else:
        database.write_bytes(b"not a SQLite database " * 100)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json() == {"status": "unavailable", "database": "error"}


# -- POST /books ----------------------------------------------------------------


def test_create_book_returns_201_and_the_stored_book(client):
    response = client.post("/books", json=ORWELL)
    assert response.status_code == 201
    book = response.get_json()
    assert book == {"id": book["id"], **ORWELL}
    assert response.headers["Location"] == f"/books/{book['id']}"
    assert client.get(response.headers["Location"]).get_json() == book


def test_create_book_needs_only_title_and_author(client):
    response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    assert response.status_code == 201
    assert response.get_json() == {
        "id": 1, "title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None,
    }


@pytest.mark.parametrize(
    "payload, details",
    [
        ({"author": "George Orwell"}, {"title": "title is required"}),
        ({"title": "Animal Farm"}, {"author": "author is required"}),
        ({}, {"title": "title is required", "author": "author is required"}),
        (
            {"title": "   ", "author": None},
            {"title": "title must not be blank", "author": "author is required"},
        ),
    ],
)
def test_create_book_requires_title_and_author(client, payload, details):
    response = client.post("/books", json=payload)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Validation failed", "details": details}
    assert client.get("/books").get_json() == []


def test_create_book_reports_every_invalid_field(client):
    response = client.post(
        "/books",
        json={"title": 1984, "author": "George Orwell", "year": "1949", "isbn": 9780451524935},
    )
    assert response.status_code == 400
    assert response.get_json()["details"] == {
        "title": "title must be a string",
        "year": "year must be an integer",
        "isbn": "isbn must be a string",
    }


def test_create_book_rejects_non_json_content_type(client):
    response = client.post(
        "/books",
        data="title=Dune&author=Frank+Herbert",
        content_type="application/x-www-form-urlencoded",
    )
    assert response.status_code == 415
    assert response.get_json() == {
        "error": "Request body must be JSON (Content-Type: application/json)"
    }


@pytest.mark.parametrize("body", ["{not json", "[]", '"Dune"', "null"])
def test_create_book_rejects_bodies_that_are_not_json_objects(client, body):
    response = client.post("/books", data=body, content_type="application/json")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body must be a JSON object"}


def test_create_book_rejects_oversized_body(client):
    response = client.post("/books", json={"title": "x" * 100_000, "author": "Anon"})
    assert response.status_code == 413
    assert "error" in response.get_json()


# -- GET /books -----------------------------------------------------------------


def test_list_books_is_empty_initially(client):
    response = client.get("/books")
    assert response.status_code == 200
    assert response.get_json() == []


def test_list_books_returns_every_book_in_creation_order(client, create_book):
    books = [
        create_book(**ORWELL),
        create_book(),
        create_book(title="Emma", author="Jane Austen", year=1815, isbn=None),
    ]
    assert client.get("/books").get_json() == books


@pytest.mark.parametrize("author", ["George Orwell", "george orwell", "ORWELL", "  orwell "])
def test_list_books_filters_by_author_ignoring_case(client, create_book, author):
    nineteen_eighty_four = create_book(**ORWELL)
    create_book()  # Dune, by Frank Herbert
    animal_farm = create_book(
        title="Animal Farm", author="George Orwell", year=1945, isbn="9780451526342"
    )
    response = client.get("/books", query_string={"author": author})
    assert response.status_code == 200
    assert response.get_json() == [nineteen_eighty_four, animal_farm]


def test_author_filter_ignores_case_beyond_ascii(client, create_book):
    book = create_book(
        title="Cien años de soledad", author="Gabriel García Márquez", year=1967, isbn=None
    )
    response = client.get("/books", query_string={"author": "GARCÍA MÁRQUEZ"})
    assert response.get_json() == [book]


def test_author_filter_without_matches_returns_empty_list(client, create_book):
    create_book()
    response = client.get("/books?author=Tolkien")
    assert response.status_code == 200
    assert response.get_json() == []


def test_author_filter_treats_sql_wildcards_literally(client, create_book):
    create_book()
    assert client.get("/books", query_string={"author": "%"}).get_json() == []
    assert client.get("/books", query_string={"author": "_"}).get_json() == []


def test_blank_author_filter_lists_every_book(client, create_book):
    book = create_book()
    assert client.get("/books?author=").get_json() == [book]


# -- GET /books/{id} ------------------------------------------------------------


def test_get_book(client, create_book):
    book = create_book()
    response = client.get(f"/books/{book['id']}")
    assert response.status_code == 200
    assert response.get_json() == book


def test_get_missing_book_returns_404(client):
    response = client.get("/books/42")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Book 42 not found"}


@pytest.mark.parametrize("book_id", ["abc", "0", "-1", "1.5", str(2**64)])
def test_invalid_book_ids_return_404(client, book_id):
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404
    assert "error" in response.get_json()


# -- PUT /books/{id} ------------------------------------------------------------


def test_update_book_replaces_it(client, create_book):
    book = create_book()
    changes = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969,
               "isbn": "9780593098233"}
    response = client.put(f"/books/{book['id']}", json=changes)
    assert response.status_code == 200
    assert response.get_json() == {"id": book["id"], **changes}
    assert client.get(f"/books/{book['id']}").get_json() == {"id": book["id"], **changes}


def test_update_book_clears_omitted_optional_fields(client, create_book):
    book = create_book()
    response = client.put(f"/books/{book['id']}", json={"title": "Dune", "author": "F. Herbert"})
    assert response.status_code == 200
    assert response.get_json() == {
        "id": book["id"], "title": "Dune", "author": "F. Herbert", "year": None, "isbn": None,
    }


def test_update_book_validates_input_and_keeps_the_original(client, create_book):
    book = create_book()
    response = client.put(f"/books/{book['id']}", json={"title": "Dune Messiah", "author": ""})
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Validation failed", "details": {"author": "author must not be blank"},
    }
    assert client.get(f"/books/{book['id']}").get_json() == book


def test_update_missing_book_returns_404(client):
    response = client.put("/books/42", json=ORWELL)
    assert response.status_code == 404
    assert response.get_json() == {"error": "Book 42 not found"}


# -- DELETE /books/{id} ---------------------------------------------------------


def test_delete_book(client, create_book):
    book = create_book()
    response = client.delete(f"/books/{book['id']}")
    assert response.status_code == 204
    assert response.data == b""
    assert client.get(f"/books/{book['id']}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_missing_book_returns_404(client):
    response = client.delete("/books/42")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Book 42 not found"}


def test_deleted_ids_are_never_reused(client, create_book):
    first = create_book()
    client.delete(f"/books/{first['id']}")
    assert create_book()["id"] > first["id"]


# -- Behaviour across the API ---------------------------------------------------


def test_books_persist_across_restarts(tmp_path):
    config = {"TESTING": True, "DATABASE": str(tmp_path / "books.db")}
    book = create_app(config).test_client().post("/books", json=ORWELL).get_json()
    restarted = create_app(config).test_client()
    assert restarted.get(f"/books/{book['id']}").get_json() == book


def test_unknown_route_returns_json_404(client):
    response = client.get("/authors")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_unsupported_method_returns_json_405_with_allow_header(client):
    response = client.delete("/books")
    assert response.status_code == 405
    assert "error" in response.get_json()
    assert {"GET", "POST"} <= set(response.headers["Allow"].split(", "))


def test_unexpected_error_returns_json_500_without_details(client, monkeypatch):
    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(BookRepository, "find", fail)
    response = client.get("/books")
    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}
