"""Tests for the book collection API.

Unit tests cover validation and the repository; integration tests run the
real HTTP server on an ephemeral port and exercise every endpoint.
"""

import http.client
import json
import threading

import pytest

from app import (
    BookRepository,
    DuplicateISBNError,
    ValidationError,
    make_server,
    validate_book,
)

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


# --------------------------------------------------------------------------
# Fixtures / helpers
# --------------------------------------------------------------------------

@pytest.fixture
def server():
    repo = BookRepository(":memory:")
    srv = make_server(repo, "127.0.0.1", 0, quiet=True)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05},
                              daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()
    repo.close()


class Client:
    def __init__(self, port):
        self.port = port

    def request(self, method, path, body=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {}
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        payload = resp.read()
        conn.close()
        parsed = json.loads(payload) if payload else None
        return resp.status, parsed, resp


@pytest.fixture
def repo():
    r = BookRepository(":memory:")
    yield r
    r.close()


@pytest.fixture
def client(server):
    return Client(server.server_port)


# --------------------------------------------------------------------------
# Unit tests: validation
# --------------------------------------------------------------------------

def test_validate_accepts_full_book_and_normalizes():
    cleaned = validate_book({**DUNE, "title": "  Dune  ", "extra": "ignored"})
    assert cleaned == {"title": "Dune", "author": "Frank Herbert",
                       "year": 1965, "isbn": "9780441013593"}


def test_validate_optional_fields_default_to_none():
    assert validate_book({"title": "T", "author": "A"}) == {
        "title": "T", "author": "A", "year": None, "isbn": None}


@pytest.mark.parametrize("payload, field", [
    ({"author": "A"}, "title"),
    ({"title": "T"}, "author"),
    ({"title": "   ", "author": "A"}, "title"),
    ({"title": "T", "author": ""}, "author"),
    ({"title": 42, "author": "A"}, "title"),
    ({"title": "T", "author": "A", "year": "1965"}, "year"),
    ({"title": "T", "author": "A", "year": True}, "year"),
    ({"title": "T", "author": "A", "year": 99999}, "year"),
    ({"title": "T", "author": "A", "isbn": "not-an-isbn"}, "isbn"),
    ({"title": "T", "author": "A", "isbn": 123}, "isbn"),
])
def test_validate_rejects_bad_fields(payload, field):
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert field in exc.value.errors


def test_validate_rejects_non_object():
    with pytest.raises(ValidationError):
        validate_book(["title", "author"])


# --------------------------------------------------------------------------
# Unit tests: repository
# --------------------------------------------------------------------------

def test_repository_crud_roundtrip(repo):
    book = repo.create(validate_book(DUNE))
    assert book["id"] == 1
    assert repo.get(1) == book
    updated = repo.update(1, validate_book({"title": "Dune Messiah", "author": "Frank Herbert"}))
    assert updated["title"] == "Dune Messiah" and updated["isbn"] is None
    assert repo.delete(1) is True
    assert repo.get(1) is None
    assert repo.delete(1) is False
    assert repo.update(1, validate_book(DUNE)) is None


def test_repository_rejects_duplicate_isbn(repo):
    repo.create(validate_book(DUNE))
    with pytest.raises(DuplicateISBNError):
        repo.create(validate_book({**DUNE, "title": "Other"}))


def test_repository_persists_to_file(tmp_path):
    db = str(tmp_path / "books.db")
    repo = BookRepository(db)
    repo.create(validate_book(DUNE))
    repo.close()
    reopened = BookRepository(db)
    assert [b["title"] for b in reopened.list()] == ["Dune"]
    reopened.close()


# --------------------------------------------------------------------------
# Integration tests: HTTP API
# --------------------------------------------------------------------------

def test_health(client):
    status, body, _ = client.request("GET", "/health")
    assert status == 200
    assert body == {"status": "ok", "database": "ok"}


def test_create_book_returns_201_with_location(client):
    status, body, resp = client.request("POST", "/books", DUNE)
    assert status == 201
    assert body["id"] == 1
    assert body["title"] == "Dune"
    assert body["isbn"] == "9780441013593"
    assert resp.getheader("Location") == "/books/1"
    assert resp.getheader("Content-Type") == "application/json"


def test_create_requires_title_and_author(client):
    status, body, _ = client.request("POST", "/books", {"year": 2000})
    assert status == 400
    assert body["error"] == "Validation failed"
    assert set(body["details"]) == {"title", "author"}


def test_create_rejects_malformed_json(client):
    status, body, _ = client.request("POST", "/books", raw=b"{not json")
    assert status == 400
    assert "JSON" in body["error"]


def test_create_rejects_empty_body(client):
    status, _, _ = client.request("POST", "/books", raw=b"")
    assert status == 400


def test_create_duplicate_isbn_returns_409(client):
    client.request("POST", "/books", DUNE)
    status, body, _ = client.request("POST", "/books", {**DUNE, "title": "Copy"})
    assert status == 409
    assert "ISBN" in body["error"]


def test_list_books_and_author_filter(client):
    client.request("POST", "/books", DUNE)
    client.request("POST", "/books", {"title": "Children of Dune", "author": "Frank Herbert"})
    client.request("POST", "/books", {"title": "Neuromancer", "author": "William Gibson"})

    status, body, _ = client.request("GET", "/books")
    assert status == 200
    assert [b["title"] for b in body] == ["Dune", "Children of Dune", "Neuromancer"]

    status, body, _ = client.request("GET", "/books?author=frank%20herbert")
    assert status == 200
    assert {b["title"] for b in body} == {"Dune", "Children of Dune"}

    status, body, _ = client.request("GET", "/books?author=Nobody")
    assert status == 200
    assert body == []


def test_list_empty(client):
    status, body, _ = client.request("GET", "/books")
    assert status == 200
    assert body == []


def test_get_book_by_id(client):
    _, created, _ = client.request("POST", "/books", DUNE)
    status, body, _ = client.request("GET", f"/books/{created['id']}")
    assert status == 200
    assert body == created


def test_get_missing_book_returns_404(client):
    status, body, _ = client.request("GET", "/books/999")
    assert status == 404
    assert body == {"error": "Book not found"}


def test_update_book(client):
    _, created, _ = client.request("POST", "/books", DUNE)
    status, body, _ = client.request(
        "PUT", f"/books/{created['id']}",
        {"title": "Dune (Deluxe)", "author": "Frank Herbert", "year": 2019},
    )
    assert status == 200
    assert body == {"id": created["id"], "title": "Dune (Deluxe)",
                    "author": "Frank Herbert", "year": 2019, "isbn": None}
    _, fetched, _ = client.request("GET", f"/books/{created['id']}")
    assert fetched == body


def test_update_validates_input(client):
    _, created, _ = client.request("POST", "/books", DUNE)
    status, body, _ = client.request("PUT", f"/books/{created['id']}", {"title": ""})
    assert status == 400
    assert set(body["details"]) == {"title", "author"}


def test_update_missing_book_returns_404(client):
    status, _, _ = client.request("PUT", "/books/42", {"title": "T", "author": "A"})
    assert status == 404


def test_update_to_existing_isbn_returns_409(client):
    client.request("POST", "/books", DUNE)
    _, other, _ = client.request("POST", "/books", {"title": "Other", "author": "X"})
    status, _, _ = client.request(
        "PUT", f"/books/{other['id']}", {"title": "Other", "author": "X", "isbn": DUNE["isbn"]})
    assert status == 409


def test_delete_book(client):
    _, created, _ = client.request("POST", "/books", DUNE)
    status, body, _ = client.request("DELETE", f"/books/{created['id']}")
    assert status == 204
    assert body is None
    status, _, _ = client.request("GET", f"/books/{created['id']}")
    assert status == 404
    status, _, _ = client.request("DELETE", f"/books/{created['id']}")
    assert status == 404


def test_unknown_route_and_bad_id(client):
    assert client.request("GET", "/nope")[0] == 404
    assert client.request("GET", "/books/abc")[0] == 404


def test_method_not_allowed(client):
    status, _, resp = client.request("DELETE", "/books")
    assert status == 405
    assert resp.getheader("Allow") == "GET, POST"
    status, _, resp = client.request("PATCH", "/books/1", {"title": "x"})
    assert status == 405
