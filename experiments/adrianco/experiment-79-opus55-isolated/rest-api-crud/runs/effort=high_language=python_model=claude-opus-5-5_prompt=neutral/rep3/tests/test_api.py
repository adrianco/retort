"""Integration tests exercising the API through its WSGI interface."""

from __future__ import annotations

import json

import pytest

from books_api.app import MAX_BODY_BYTES


def test_health(client):
    response = client.get("/health")
    assert response.status == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok"}


def test_health_reports_unavailable_database(client, repository):
    repository.close()
    response = client.get("/health")
    assert response.status == 503
    assert response.json() == {"error": "Database unavailable"}


# -- POST /books -----------------------------------------------------------


def test_create_book(client, dune):
    response = client.post("/books", dune)
    assert response.status == 201
    assert response.json() == {"id": 1, **dune}
    assert response.headers["location"] == "/books/1"
    assert response.headers["content-type"].startswith("application/json")


def test_create_book_with_only_required_fields(client):
    response = client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    assert response.status == 201
    assert response.json() == {
        "id": 1,
        "title": "Emma",
        "author": "Jane Austen",
        "year": None,
        "isbn": None,
    }


def test_create_book_trims_whitespace_and_ignores_client_id(client):
    response = client.post(
        "/books", {"id": 99, "title": "  Emma ", "author": " Jane Austen ", "isbn": "  "}
    )
    assert response.status == 201
    assert response.json() == {
        "id": 1,
        "title": "Emma",
        "author": "Jane Austen",
        "year": None,
        "isbn": None,
    }


def test_create_book_preserves_unicode(client):
    book = {"title": "Cien años de soledad", "author": "Gabriel García Márquez"}
    created = client.post("/books", book).json()
    assert created["title"] == book["title"]
    assert client.get(f"/books/{created['id']}").json()["author"] == book["author"]


@pytest.mark.parametrize(
    ("payload", "expected_errors"),
    [
        ({"author": "Frank Herbert"}, {"title": "is required"}),
        ({"title": "Dune"}, {"author": "is required"}),
        ({}, {"title": "is required", "author": "is required"}),
        ({"title": None, "author": "A"}, {"title": "is required"}),
        ({"title": "   ", "author": "A"}, {"title": "must not be blank"}),
        ({"title": "T", "author": ""}, {"author": "must not be blank"}),
        ({"title": 42, "author": "A"}, {"title": "must be a string"}),
        ({"title": "T", "author": ["A"]}, {"author": "must be a string"}),
        ({"title": "T" * 501, "author": "A"}, {"title": "must be at most 500 characters"}),
        ({"title": "T", "author": "A", "year": "1965"}, {"year": "must be an integer"}),
        ({"title": "T", "author": "A", "year": 1965.5}, {"year": "must be an integer"}),
        ({"title": "T", "author": "A", "year": True}, {"year": "must be an integer"}),
        ({"title": "T", "author": "A", "year": 0}, {"year": "must be between 1 and 9999"}),
        ({"title": "T", "author": "A", "year": 10000}, {"year": "must be between 1 and 9999"}),
        ({"title": "T", "author": "A", "isbn": 123}, {"isbn": "must be a string"}),
        ({"title": "T", "author": "A", "isbn": "9" * 33}, {"isbn": "must be at most 32 characters"}),
    ],
)
def test_create_book_rejects_invalid_fields(client, payload, expected_errors):
    response = client.post("/books", payload)
    assert response.status == 400
    assert response.json() == {"error": "Validation failed", "details": expected_errors}
    assert client.get("/books").json() == []


@pytest.mark.parametrize("payload", [["a", "list"], "a string", 42, None])
def test_create_book_rejects_non_object_json(client, payload):
    response = client.post("/books", raw_body=json.dumps(payload).encode("utf-8"))
    assert response.status == 400
    assert response.json()["details"] == {"body": "must be a JSON object"}


@pytest.mark.parametrize("raw_body", [b"{not json", b'{"title": "Dune"', b"\xff\xfe"])
def test_create_book_rejects_malformed_json(client, raw_body):
    response = client.post("/books", raw_body=raw_body)
    assert response.status == 400
    assert response.json() == {"error": "Request body is not valid JSON"}


def test_create_book_rejects_empty_body(client):
    response = client.post("/books")
    assert response.status == 400
    assert response.json() == {"error": "Request body must be a JSON object"}


def test_create_book_rejects_oversized_body(client):
    response = client.post("/books", raw_body=b" " * (MAX_BODY_BYTES + 1))
    assert response.status == 413


@pytest.mark.parametrize("content_length", ["abc", "-5"])
def test_create_book_rejects_invalid_content_length(client, repository, content_length):
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/books",
        "CONTENT_LENGTH": content_length,
    }
    response = client.request_environ(environ)
    assert response.status == 400
    assert response.json() == {"error": "Invalid Content-Length header"}


# -- GET /books ------------------------------------------------------------


def test_list_books_is_empty_initially(client):
    response = client.get("/books")
    assert response.status == 200
    assert response.json() == []


def test_list_books_returns_all_in_creation_order(client, dune):
    client.post("/books", dune)
    client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    response = client.get("/books")
    assert response.status == 200
    assert [(b["id"], b["title"]) for b in response.json()] == [(1, "Dune"), (2, "Emma")]


def test_list_books_filters_by_author(client, dune):
    client.post("/books", dune)
    client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    client.post("/books", {"title": "Children of Dune", "author": "Frank Herbert"})

    response = client.get("/books?author=Frank%20Herbert")
    assert response.status == 200
    assert [b["title"] for b in response.json()] == ["Dune", "Children of Dune"]

    # '+' encoding and different letter case match too.
    assert len(client.get("/books?author=frank+herbert").json()) == 2
    # The filter is an exact match, not a substring search.
    assert client.get("/books?author=Frank").json() == []
    assert client.get("/books?author=Nobody").json() == []


def test_list_books_ignores_blank_author_filter(client, dune):
    client.post("/books", dune)
    assert len(client.get("/books?author=").json()) == 1


def test_author_filter_is_not_vulnerable_to_sql_injection(client, dune):
    client.post("/books", dune)
    response = client.get("/books?author=x'%20OR%20'1'%3D'1")
    assert response.status == 200
    assert response.json() == []


# -- GET /books/{id} -------------------------------------------------------


def test_get_book(client, dune):
    client.post("/books", dune)
    response = client.get("/books/1")
    assert response.status == 200
    assert response.json() == {"id": 1, **dune}


@pytest.mark.parametrize("book_id", ["1", "999", "abc", "-1", "1.5", "9" * 30])
def test_get_missing_book_returns_404(client, book_id):
    response = client.get(f"/books/{book_id}")
    assert response.status == 404
    assert response.json() == {"error": f"Book {book_id} not found"}


# -- PUT /books/{id} -------------------------------------------------------


def test_update_book(client, dune):
    client.post("/books", dune)
    updated = {
        "title": "Dune Messiah",
        "author": "Frank Herbert",
        "year": 1969,
        "isbn": "978-0593098233",
    }
    response = client.put("/books/1", updated)
    assert response.status == 200
    assert response.json() == {"id": 1, **updated}
    assert client.get("/books/1").json() == {"id": 1, **updated}


def test_update_replaces_the_whole_book(client, dune):
    client.post("/books", dune)
    response = client.put("/books/1", {"title": "Dune", "author": "Frank Herbert"})
    assert response.status == 200
    assert response.json()["year"] is None
    assert response.json()["isbn"] is None


def test_update_book_validates_input(client, dune):
    client.post("/books", dune)
    response = client.put("/books/1", {"title": "", "year": "soon"})
    assert response.status == 400
    assert response.json() == {
        "error": "Validation failed",
        "details": {
            "title": "must not be blank",
            "author": "is required",
            "year": "must be an integer",
        },
    }
    assert client.get("/books/1").json() == {"id": 1, **dune}


def test_update_missing_book_returns_404(client, dune):
    response = client.put("/books/1", dune)
    assert response.status == 404
    assert client.get("/books").json() == []


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_write_to_out_of_range_id_returns_404(client, dune, method):
    response = client.request(method, f"/books/{2**63}", dune)
    assert response.status == 404


def test_update_does_not_change_other_books(client, dune):
    client.post("/books", dune)
    client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    client.put("/books/2", {"title": "Persuasion", "author": "Jane Austen"})
    assert client.get("/books/1").json() == {"id": 1, **dune}


# -- DELETE /books/{id} ----------------------------------------------------


def test_delete_book(client, dune):
    client.post("/books", dune)
    response = client.delete("/books/1")
    assert response.status == 204
    assert response.body == b""
    assert client.get("/books/1").status == 404
    assert client.get("/books").json() == []


def test_delete_missing_book_returns_404(client):
    response = client.delete("/books/1")
    assert response.status == 404
    assert response.json() == {"error": "Book 1 not found"}


def test_ids_are_not_reused_after_delete(client, dune):
    client.post("/books", dune)
    client.delete("/books/1")
    assert client.post("/books", dune).json()["id"] == 2


# -- routing ---------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/unknown", "/books/1/extra", "/healthz"])
def test_unknown_path_returns_404(client, path):
    response = client.get(path)
    assert response.status == 404
    assert response.json() == {"error": "Resource not found"}


@pytest.mark.parametrize(
    ("method", "path", "allow"),
    [
        ("DELETE", "/books", "GET, POST"),
        ("PUT", "/books", "GET, POST"),
        ("POST", "/books/1", "DELETE, GET, PUT"),
        ("PATCH", "/books/1", "DELETE, GET, PUT"),
        ("POST", "/health", "GET"),
    ],
)
def test_unsupported_method_returns_405(client, method, path, allow):
    response = client.request(method, path)
    assert response.status == 405
    assert response.headers["allow"] == allow
    assert "error" in response.json()


def test_trailing_slash_is_tolerated(client, dune):
    assert client.post("/books/", dune).status == 201
    assert client.get("/books/").status == 200
    assert client.get("/books/1/").status == 200


def test_unexpected_errors_become_json_500(client, repository, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(repository, "list_books", boom)
    response = client.get("/books")
    assert response.status == 500
    assert response.json() == {"error": "Internal server error"}
