import http.client
import json
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["BOOKAPI_QUIET"] = "1"

from app import ValidationError, make_server, validate_book  # noqa: E402

BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


@pytest.fixture
def client(tmp_path):
    server = make_server("127.0.0.1", 0, str(tmp_path / "test.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    def request(method, path, body=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        headers = {}
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        text = resp.read()
        conn.close()
        return resp, (json.loads(text) if text else None)

    yield request
    server.shutdown()
    server.server_close()
    server.store.close()


# -- unit tests: validation -------------------------------------------------

def test_validate_accepts_full_book():
    assert validate_book(BOOK) == BOOK


def test_validate_requires_title_and_author():
    with pytest.raises(ValidationError) as exc:
        validate_book({"title": "  ", "year": 2000})
    assert set(exc.value.errors) == {"title", "author"}


@pytest.mark.parametrize(
    "field,value",
    [("year", "1999"), ("year", True), ("isbn", "abc"), ("isbn", 123), ("bogus", 1)],
)
def test_validate_rejects_bad_optional_fields(field, value):
    with pytest.raises(ValidationError):
        validate_book({"title": "T", "author": "A", field: value})


# -- integration tests: HTTP ------------------------------------------------

def test_health(client):
    resp, body = client("GET", "/health")
    assert resp.status == 200
    assert body["status"] == "ok"


def test_create_and_get_book(client):
    resp, created = client("POST", "/books", BOOK)
    assert resp.status == 201
    assert resp.getheader("Location") == f"/books/{created['id']}"
    assert {k: created[k] for k in BOOK} == BOOK

    resp, fetched = client("GET", f"/books/{created['id']}")
    assert resp.status == 200
    assert fetched == created


def test_create_minimal_book_has_null_optionals(client):
    resp, created = client("POST", "/books", {"title": "T", "author": "A"})
    assert resp.status == 201
    assert created["year"] is None and created["isbn"] is None


def test_create_validation_errors(client):
    resp, body = client("POST", "/books", {"year": 2000})
    assert resp.status == 422
    assert "title" in body["details"] and "author" in body["details"]

    resp, body = client("POST", "/books", raw=b"{not json")
    assert resp.status == 400

    resp, body = client("POST", "/books", [1, 2])
    assert resp.status == 422


def test_list_and_author_filter(client):
    client("POST", "/books", BOOK)
    client("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    client("POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})

    resp, books = client("GET", "/books")
    assert resp.status == 200
    assert len(books) == 3

    resp, books = client("GET", "/books?author=Jane%20Austen")
    assert resp.status == 200
    assert [b["title"] for b in books] == ["Emma", "Persuasion"]

    resp, books = client("GET", "/books?author=jane+austen")
    assert len(books) == 2

    resp, books = client("GET", "/books?author=Nobody")
    assert books == []


def test_update_book(client):
    _, created = client("POST", "/books", BOOK)
    updated = {**BOOK, "title": "Dune Messiah", "year": 1969}
    resp, body = client("PUT", f"/books/{created['id']}", updated)
    assert resp.status == 200
    assert body["title"] == "Dune Messiah" and body["year"] == 1969

    _, fetched = client("GET", f"/books/{created['id']}")
    assert fetched == body

    resp, body = client("PUT", f"/books/{created['id']}", {"title": ""})
    assert resp.status == 422

    resp, _ = client("PUT", "/books/9999", BOOK)
    assert resp.status == 404


def test_delete_book(client):
    _, created = client("POST", "/books", BOOK)
    resp, body = client("DELETE", f"/books/{created['id']}")
    assert resp.status == 204
    assert body is None

    resp, _ = client("GET", f"/books/{created['id']}")
    assert resp.status == 404
    resp, _ = client("DELETE", f"/books/{created['id']}")
    assert resp.status == 404


def test_unknown_routes(client):
    assert client("GET", "/nope")[0].status == 404
    assert client("GET", "/books/abc")[0].status == 404
    assert client("DELETE", "/books")[0].status == 405


def test_data_persists_across_restarts(tmp_path):
    db = str(tmp_path / "persist.db")
    s1 = make_server("127.0.0.1", 0, db)
    s1.store.create(validate_book(BOOK))
    s1.server_close()
    s1.store.close()

    s2 = make_server("127.0.0.1", 0, db)
    try:
        assert [b["title"] for b in s2.store.list()] == ["Dune"]
    finally:
        s2.server_close()
        s2.store.close()
