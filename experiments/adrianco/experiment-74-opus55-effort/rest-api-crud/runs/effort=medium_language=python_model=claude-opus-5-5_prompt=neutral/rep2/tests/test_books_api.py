import json
import os
import sys
import threading
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["BOOKS_API_QUIET"] = "1"

from books_api import BookAPI, BookStore, ValidationError, create_server, validate_book  # noqa: E402

BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


@pytest.fixture
def server(tmp_path):
    srv = create_server(port=0, db_path=str(tmp_path / "test.db"))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def request(base, method, path, payload=None, raw=None):
    data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body else None, resp.headers
    except urllib.error.HTTPError as err:
        body = err.read()
        return err.code, json.loads(body) if body else None, err.headers


# ---- integration tests over real HTTP ----

def test_health(server):
    status, body, headers = request(server, "GET", "/health")
    assert status == 200
    assert body["status"] == "ok"
    assert headers["Content-Type"] == "application/json"


def test_full_crud_lifecycle(server):
    status, created, _ = request(server, "POST", "/books", BOOK)
    assert status == 201
    assert created["id"] > 0
    assert {k: created[k] for k in BOOK} == BOOK
    book_id = created["id"]

    status, fetched, _ = request(server, "GET", f"/books/{book_id}")
    assert status == 200 and fetched == created

    updated_payload = {**BOOK, "title": "Dune Messiah", "year": 1969}
    status, updated, _ = request(server, "PUT", f"/books/{book_id}", updated_payload)
    assert status == 200
    assert updated["title"] == "Dune Messiah" and updated["year"] == 1969

    status, body, _ = request(server, "DELETE", f"/books/{book_id}")
    assert status == 204 and body is None

    status, body, _ = request(server, "GET", f"/books/{book_id}")
    assert status == 404
    assert "error" in body


def test_list_and_author_filter(server):
    request(server, "POST", "/books", BOOK)
    request(server, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    request(server, "POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})

    status, books, _ = request(server, "GET", "/books")
    assert status == 200 and len(books) == 3

    status, books, _ = request(server, "GET", "/books?author=Jane%20Austen")
    assert status == 200
    assert [b["title"] for b in books] == ["Emma", "Persuasion"]

    status, books, _ = request(server, "GET", "/books?author=jane%20austen")
    assert len(books) == 2  # case-insensitive

    status, books, _ = request(server, "GET", "/books?author=Nobody")
    assert status == 200 and books == []


@pytest.mark.parametrize("payload,missing", [
    ({"author": "X"}, "title"),
    ({"title": "X"}, "author"),
    ({"title": "  ", "author": "X"}, "title"),
    ({"title": "X", "author": ""}, "author"),
])
def test_create_requires_title_and_author(server, payload, missing):
    status, body, _ = request(server, "POST", "/books", payload)
    assert status == 422
    assert missing in body["details"]


def test_invalid_json_returns_400(server):
    status, body, _ = request(server, "POST", "/books", raw=b"{not json")
    assert status == 400
    assert body["error"] == "invalid JSON body"


def test_update_validation_and_missing(server):
    _, created, _ = request(server, "POST", "/books", BOOK)
    status, body, _ = request(server, "PUT", f"/books/{created['id']}", {"title": "No author"})
    assert status == 422 and "author" in body["details"]

    status, _, _ = request(server, "PUT", "/books/9999", BOOK)
    assert status == 404


def test_delete_missing_and_unknown_routes(server):
    assert request(server, "DELETE", "/books/9999")[0] == 404
    assert request(server, "GET", "/nope")[0] == 404
    assert request(server, "GET", "/books/abc")[0] == 404
    assert request(server, "PATCH", "/books")[0] == 405


def test_data_persists_across_restarts(tmp_path):
    db = str(tmp_path / "persist.db")
    BookStore(db).create({"title": "A", "author": "B", "year": None, "isbn": None})
    assert [b["title"] for b in BookStore(db).list()] == ["A"]


# ---- unit tests for validation / routing ----

@pytest.mark.parametrize("payload,field", [
    ({"title": "T", "author": "A", "year": "1999"}, "year"),
    ({"title": "T", "author": "A", "year": True}, "year"),
    ({"title": "T", "author": "A", "isbn": "123"}, "isbn"),
    ({"title": "T", "author": "A", "isbn": 9780441013593}, "isbn"),
    ({"title": "T", "author": "A", "extra": 1}, "unknown_fields"),
])
def test_validation_rejects_bad_fields(payload, field):
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert field in exc.value.errors


def test_validation_accepts_optional_fields_and_strips():
    clean = validate_book({"title": " T ", "author": "A", "isbn": "0-306-40615-2"})
    assert clean == {"title": "T", "author": "A", "year": None, "isbn": "0-306-40615-2"}


def test_validation_rejects_non_object():
    with pytest.raises(ValidationError):
        validate_book([1, 2])


def test_api_handle_direct():
    api = BookAPI(BookStore(":memory:"))
    status, book = api.handle("POST", "/books", json.dumps(BOOK).encode())
    assert status == 201
    assert api.handle("GET", "/books/")[1] == [book]  # trailing slash tolerated
