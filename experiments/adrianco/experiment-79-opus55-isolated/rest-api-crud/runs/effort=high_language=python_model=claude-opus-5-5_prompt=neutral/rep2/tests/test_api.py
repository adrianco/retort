"""API behaviour, exercised in-process through the WSGI interface."""

import sqlite3

import pytest

from bookapi.app import MAX_BODY_BYTES


def test_health(client):
    response = client.get("/health")
    assert response.status == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["Content-Type"].startswith("application/json")


def test_health_reports_unusable_database(client, store):
    store.close()
    response = client.get("/health")
    assert response.status == 503
    assert response.json() == {"error": "Database unavailable"}


# -- create ------------------------------------------------------------------


def test_create_book(client):
    response = client.post(
        "/books",
        {
            "title": "Dune",
            "author": "Frank Herbert",
            "year": 1965,
            "isbn": "978-0441172719",
        },
    )
    assert response.status == 201
    book = response.json()
    assert book == {
        "id": book["id"],
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0441172719",
    }
    assert isinstance(book["id"], int)
    assert response.headers["Location"] == f"/books/{book['id']}"
    # The book is really persisted, not just echoed back.
    assert client.get(f"/books/{book['id']}").json() == book


def test_create_book_year_and_isbn_are_optional(client):
    response = client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    assert response.status == 201
    assert response.json()["year"] is None
    assert response.json()["isbn"] is None


def test_create_book_trims_whitespace_and_ignores_unknown_fields(client):
    response = client.post(
        "/books",
        {"title": "  Emma ", "author": " Jane Austen ", "id": 999, "rating": 5},
    )
    assert response.status == 201
    book = response.json()
    assert (book["title"], book["author"]) == ("Emma", "Jane Austen")
    assert book["id"] != 999
    assert "rating" not in book


def test_create_book_preserves_non_ascii_text(client):
    created = client.post(
        "/books", {"title": "Cien años de soledad", "author": "García Márquez"}
    ).json()
    fetched = client.get(f"/books/{created['id']}")
    assert fetched.json()["title"] == "Cien años de soledad"
    assert "años".encode("utf-8") in fetched.body


@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        ({"author": "Frank Herbert"}, "title", "is required"),
        ({"title": "Dune"}, "author", "is required"),
        ({"title": None, "author": "Frank Herbert"}, "title", "is required"),
        ({"title": "", "author": "Frank Herbert"}, "title", "must not be blank"),
        ({"title": "Dune", "author": "   "}, "author", "must not be blank"),
        ({"title": 42, "author": "Frank Herbert"}, "title", "must be a string"),
        ({"title": "x" * 501, "author": "A"}, "title", "must be at most 500 characters"),
        ({"title": "\ud800", "author": "A"}, "title", "must be valid Unicode text"),
        ({"title": "Dune", "author": "A", "year": "1965"}, "year", "must be an integer"),
        ({"title": "Dune", "author": "A", "year": 1965.5}, "year", "must be an integer"),
        ({"title": "Dune", "author": "A", "year": True}, "year", "must be an integer"),
        ({"title": "Dune", "author": "A", "year": 0}, "year", "must be between 1 and 9999"),
        ({"title": "Dune", "author": "A", "year": 10**30}, "year", "must be between 1 and 9999"),
        ({"title": "Dune", "author": "A", "isbn": 9780441172719}, "isbn", "must be a string"),
        ({"title": "Dune", "author": "A", "isbn": "9" * 33}, "isbn", "must be at most 32 characters"),
    ],
)
def test_create_book_rejects_invalid_fields(client, payload, field, message):
    response = client.post("/books", payload)
    assert response.status == 400
    assert response.json() == {"error": "Validation failed", "details": {field: message}}
    assert client.get("/books").json() == []


def test_create_book_reports_every_invalid_field(client):
    response = client.post("/books", {"year": "soon"})
    assert response.status == 400
    assert set(response.json()["details"]) == {"title", "author", "year"}


@pytest.mark.parametrize(
    "raw_body", [b"", b"{not json", b"\xff\xfe", b"[" * 100_000]
)
def test_create_book_rejects_malformed_json(client, raw_body):
    response = client.post("/books", raw_body=raw_body)
    assert response.status == 400
    assert response.json() == {"error": "Request body must be valid JSON"}


@pytest.mark.parametrize("raw_body", [b"[]", b'"Dune"', b"null", b"7"])
def test_create_book_rejects_non_object_json(client, raw_body):
    response = client.post("/books", raw_body=raw_body)
    assert response.status == 400
    assert response.json()["details"] == {"body": "must be a JSON object"}


def test_create_book_rejects_oversized_body(client):
    response = client.post("/books", raw_body=b" " * (MAX_BODY_BYTES + 1))
    assert response.status == 413


@pytest.mark.parametrize("content_length", ["abc", "-1"])
def test_create_book_rejects_bad_content_length(client, content_length):
    response = client.post(
        "/books",
        {"title": "Dune", "author": "Frank Herbert"},
        environ={"CONTENT_LENGTH": content_length},
    )
    assert response.status == 400
    assert response.json() == {"error": "Invalid Content-Length"}


# -- list --------------------------------------------------------------------


def test_list_books_empty(client):
    response = client.get("/books")
    assert response.status == 200
    assert response.json() == []


def test_list_books_returns_all_in_creation_order(client):
    titles = ["Dune", "Emma", "Ulysses"]
    for title in titles:
        client.post("/books", {"title": title, "author": "Someone"})
    response = client.get("/books")
    assert response.status == 200
    assert [book["title"] for book in response.json()] == titles


def test_list_books_filters_by_author(client):
    client.post("/books", {"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    client.post("/books", {"title": "Dune Messiah", "author": "Frank Herbert"})

    response = client.get("/books?author=Frank%20Herbert")
    assert response.status == 200
    assert [book["title"] for book in response.json()] == ["Dune", "Dune Messiah"]

    # Matching is case-insensitive but on the whole name, not a substring.
    assert len(client.get("/books?author=frank+herbert").json()) == 2
    assert client.get("/books?author=Frank").json() == []
    assert client.get("/books?author=Nobody").json() == []


def test_list_books_blank_author_filter_is_ignored(client, dune):
    assert client.get("/books?author=").json() == [dune]


def test_list_books_author_filter_is_not_sql_injectable(client, dune):
    response = client.get("/books?author=x'%20OR%20'1'='1")
    assert response.status == 200
    assert response.json() == []


# -- get ---------------------------------------------------------------------


def test_get_book(client, dune):
    response = client.get(f"/books/{dune['id']}")
    assert response.status == 200
    assert response.json() == dune


@pytest.mark.parametrize("book_id", ["999", "0", "9" * 40])
def test_get_missing_book(client, dune, book_id):
    response = client.get(f"/books/{book_id}")
    assert response.status == 404
    assert "not found" in response.json()["error"]


@pytest.mark.parametrize("path", ["/books/abc", "/books/-1", "/books/1/extra", "/", "/nope"])
def test_unknown_paths_return_404(client, dune, path):
    response = client.get(path)
    assert response.status == 404
    assert response.json() == {"error": "Resource not found"}


# -- update ------------------------------------------------------------------


def test_update_book(client, dune):
    response = client.put(
        f"/books/{dune['id']}",
        {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "x"},
    )
    assert response.status == 200
    expected = {
        "id": dune["id"],
        "title": "Dune Messiah",
        "author": "Frank Herbert",
        "year": 1969,
        "isbn": "x",
    }
    assert response.json() == expected
    assert client.get(f"/books/{dune['id']}").json() == expected


def test_update_replaces_the_whole_book(client, dune):
    response = client.put(
        f"/books/{dune['id']}", {"title": "Dune", "author": "Frank Herbert"}
    )
    assert response.status == 200
    assert response.json()["year"] is None
    assert response.json()["isbn"] is None


def test_update_cannot_change_id(client, dune):
    response = client.put(
        f"/books/{dune['id']}", {"id": 77, "title": "Dune", "author": "F. Herbert"}
    )
    assert response.json()["id"] == dune["id"]
    assert client.get("/books/77").status == 404


def test_update_missing_book(client):
    response = client.put("/books/999", {"title": "Dune", "author": "Frank Herbert"})
    assert response.status == 404


def test_update_rejects_invalid_book_and_leaves_it_unchanged(client, dune):
    response = client.put(f"/books/{dune['id']}", {"title": "", "author": "Frank Herbert"})
    assert response.status == 400
    assert response.json()["details"] == {"title": "must not be blank"}
    assert client.get(f"/books/{dune['id']}").json() == dune


# -- delete ------------------------------------------------------------------


def test_delete_book(client, dune):
    response = client.delete(f"/books/{dune['id']}")
    assert response.status == 204
    assert response.body == b""
    assert client.get(f"/books/{dune['id']}").status == 404
    assert client.get("/books").json() == []


def test_delete_missing_book(client, dune):
    assert client.delete("/books/999").status == 404
    assert client.delete(f"/books/{dune['id']}").status == 204
    assert client.delete(f"/books/{dune['id']}").status == 404


def test_ids_are_not_reused_after_delete(client, dune):
    client.delete(f"/books/{dune['id']}")
    new = client.post("/books", {"title": "Emma", "author": "Jane Austen"}).json()
    assert new["id"] > dune["id"]


# -- protocol ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "allowed"),
    [
        ("DELETE", "/books", "GET, POST"),
        ("PUT", "/books", "GET, POST"),
        ("POST", "/books/1", "GET, PUT, DELETE"),
        ("PATCH", "/books/1", "GET, PUT, DELETE"),
        ("POST", "/health", "GET"),
    ],
)
def test_unsupported_methods_return_405(client, method, path, allowed):
    response = client.request(method, path)
    assert response.status == 405
    assert response.headers["Allow"] == allowed
    assert "error" in response.json()


def test_head_returns_get_headers_without_body(client, dune):
    get = client.get(f"/books/{dune['id']}")
    head = client.request("HEAD", f"/books/{dune['id']}")
    assert head.status == 200
    assert head.body == b""
    assert head.headers["Content-Length"] == str(len(get.body))


@pytest.mark.parametrize("book_id", ["0", "9" * 40])
def test_update_and_delete_with_impossible_ids_return_404(client, book_id):
    book = {"title": "Dune", "author": "Frank Herbert"}
    assert client.put(f"/books/{book_id}", book).status == 404
    assert client.delete(f"/books/{book_id}").status == 404


def test_trailing_slash_is_accepted(client, dune):
    assert client.get("/books/").json() == [dune]
    assert client.get(f"/books/{dune['id']}/").json() == dune


def test_unexpected_errors_return_500_without_leaking_details(client, store, monkeypatch):
    def boom(author=None):
        raise sqlite3.OperationalError("disk I/O error at /secret/path")

    monkeypatch.setattr(store, "list", boom)
    response = client.get("/books")
    assert response.status == 500
    assert response.json() == {"error": "Internal server error"}
