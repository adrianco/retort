import json
import threading
import urllib.error
import urllib.request

import pytest

from books_api import BookStore, ValidationError, handle_request, make_server, validate_book

SAMPLE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-01359-3"}


# --------------------------------------------------------------------------- #
# Unit tests: validation
# --------------------------------------------------------------------------- #
def test_validate_book_normalises_fields():
    book = validate_book({**SAMPLE, "title": "  Dune  "})
    assert book == {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"author": "A"}, "title"),
        ({"title": "T"}, "author"),
        ({"title": "   ", "author": "A"}, "title"),
        ({"title": "T", "author": 42}, "author"),
        ({"title": "T", "author": "A", "year": "1999"}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "year": 99999}, "year"),
        ({"title": "T", "author": "A", "isbn": "abc"}, "isbn"),
        ({"title": "T", "author": "A", "genre": "sf"}, "unknown_fields"),
    ],
)
def test_validate_book_rejects_bad_input(payload, field):
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert field in exc.value.errors


def test_validate_book_requires_object():
    with pytest.raises(ValidationError):
        validate_book(["not", "an", "object"])


# --------------------------------------------------------------------------- #
# Handler tests against an in-memory store
# --------------------------------------------------------------------------- #
@pytest.fixture
def store():
    s = BookStore(":memory:")
    yield s
    s.close()


def call(store, method, path, payload=None, raw=None):
    body = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    return handle_request(store, method, path, body)


def test_health(store):
    assert call(store, "GET", "/health") == (200, {"status": "ok", "database": "ok"})


def test_crud_lifecycle(store):
    status, created = call(store, "POST", "/books", SAMPLE)
    assert status == 201
    assert created["id"] == 1 and created["title"] == "Dune"

    assert call(store, "GET", "/books/1") == (200, created)

    status, updated = call(store, "PUT", "/books/1", {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
    assert status == 200
    assert updated == {"id": 1, "title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": None}

    assert call(store, "DELETE", "/books/1") == (204, None)
    assert call(store, "GET", "/books/1")[0] == 404
    assert call(store, "DELETE", "/books/1")[0] == 404


def test_list_with_author_filter(store):
    call(store, "POST", "/books", {"title": "Dune", "author": "Frank Herbert"})
    call(store, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    call(store, "POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})

    status, books = call(store, "GET", "/books")
    assert status == 200 and len(books) == 3

    status, books = call(store, "GET", "/books?author=jane%20austen")
    assert status == 200
    assert [b["title"] for b in books] == ["Emma", "Persuasion"]

    assert call(store, "GET", "/books?author=Nobody") == (200, [])


def test_create_validation_errors(store):
    status, body = call(store, "POST", "/books", {"year": 2000})
    assert status == 400
    assert set(body["details"]) >= {"title", "author"}

    assert call(store, "POST", "/books", raw=b"{not json")[0] == 400
    assert call(store, "POST", "/books")[0] == 400
    assert call(store, "GET", "/books")[1] == []


def test_update_missing_and_invalid(store):
    assert call(store, "PUT", "/books/99", {"title": "T", "author": "A"})[0] == 404
    call(store, "POST", "/books", SAMPLE)
    assert call(store, "PUT", "/books/1", {"title": ""})[0] == 400
    assert call(store, "GET", "/books/1")[1]["title"] == "Dune"


def test_duplicate_isbn_conflict(store):
    assert call(store, "POST", "/books", SAMPLE)[0] == 201
    status, body = call(store, "POST", "/books", SAMPLE)
    assert status == 409 and "isbn" in body["error"]


def test_unknown_routes_and_methods(store):
    assert call(store, "GET", "/nope")[0] == 404
    assert call(store, "GET", "/books/abc")[0] == 404
    assert call(store, "PATCH", "/books")[0] == 405
    assert call(store, "POST", "/books/1", SAMPLE)[0] == 405


def test_data_persists_in_sqlite_file(tmp_path):
    db = str(tmp_path / "books.db")
    s1 = BookStore(db)
    s1.create(validate_book(SAMPLE))
    s1.close()
    s2 = BookStore(db)
    assert s2.get(1)["title"] == "Dune"
    s2.close()


# --------------------------------------------------------------------------- #
# Integration test over real HTTP
# --------------------------------------------------------------------------- #
@pytest.fixture
def server_url(tmp_path):
    server = make_server(port=0, db_path=str(tmp_path / "it.db"), quiet=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    server.store.close()


def http(method, url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, resp.headers.get("Content-Type"), json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("Content-Type"), json.loads(err.read())


def test_http_end_to_end(server_url):
    assert http("GET", f"{server_url}/health")[:2] == (200, "application/json")

    status, ctype, book = http("POST", f"{server_url}/books", SAMPLE)
    assert (status, ctype) == (201, "application/json")

    assert http("GET", f"{server_url}/books?author=Frank%20Herbert")[2] == [book]
    assert http("PUT", f"{server_url}/books/{book['id']}", {**SAMPLE, "year": 1966})[2]["year"] == 1966
    assert http("POST", f"{server_url}/books", {"title": "No author"})[0] == 400
    assert http("DELETE", f"{server_url}/books/{book['id']}")[0] == 204
    assert http("GET", f"{server_url}/books/{book['id']}")[0] == 404
