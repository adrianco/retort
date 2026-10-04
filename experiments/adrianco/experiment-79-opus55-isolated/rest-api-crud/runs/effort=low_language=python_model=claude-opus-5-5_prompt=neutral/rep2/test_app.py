"""Integration tests: run the real server on an ephemeral port against a temp SQLite file."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from app import make_server, validate_book, ValidationError

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


@pytest.fixture
def api(tmp_path):
    server = make_server(port=0, db_path=str(tmp_path / "books.db"), quiet=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def call(method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(base + path, data=data, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status, payload, headers = resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as exc:
            status, payload, headers = exc.code, exc.read(), exc.headers
        if payload:
            assert headers["Content-Type"] == "application/json"
        return status, (json.loads(payload) if payload else None)

    yield call
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_health(api):
    assert api("GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(api):
    status, book = api("POST", "/books", DUNE)
    assert status == 201
    assert book == {"id": book["id"], **DUNE}
    assert api("GET", f"/books/{book['id']}") == (200, book)


def test_create_with_only_required_fields(api):
    status, book = api("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert status == 201
    assert book["year"] is None and book["isbn"] is None


@pytest.mark.parametrize(
    "body, bad_fields",
    [
        ({"author": "A"}, {"title"}),
        ({"title": "T"}, {"author"}),
        ({}, {"title", "author"}),
        ({"title": "  ", "author": "A"}, {"title"}),
        ({"title": 5, "author": "A"}, {"title"}),
        ({"title": "T", "author": "A", "year": "1965"}, {"year"}),
        ({"title": "T", "author": "A", "year": True}, {"year"}),
        ({"title": "T", "author": "A", "isbn": 123}, {"isbn"}),
    ],
)
def test_create_validation(api, body, bad_fields):
    status, payload = api("POST", "/books", body)
    assert status == 400
    assert set(payload["details"]) == bad_fields
    assert api("GET", "/books") == (200, [])


def test_create_rejects_malformed_json(api):
    status, payload = api("POST", "/books", raw=b"{not json")
    assert status == 400 and "error" in payload
    status, _ = api("POST", "/books", raw=b"[1, 2]")
    assert status == 400


def test_list_and_author_filter(api):
    api("POST", "/books", DUNE)
    api("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    api("POST", "/books", {"title": "Children of Dune", "author": "Frank Herbert"})

    status, books = api("GET", "/books")
    assert status == 200
    assert [b["title"] for b in books] == ["Dune", "Emma", "Children of Dune"]

    status, books = api("GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in books] == ["Dune", "Children of Dune"]

    assert api("GET", "/books?author=Nobody") == (200, [])


def test_update(api):
    _, book = api("POST", "/books", DUNE)
    status, updated = api("PUT", f"/books/{book['id']}", {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
    assert status == 200
    assert updated == {"id": book["id"], "title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": None}
    assert api("GET", f"/books/{book['id']}") == (200, updated)


def test_update_validation_and_missing(api):
    _, book = api("POST", "/books", DUNE)
    status, payload = api("PUT", f"/books/{book['id']}", {"title": "No author"})
    assert status == 400 and "author" in payload["details"]
    assert api("GET", f"/books/{book['id']}")[1] == book  # unchanged

    assert api("PUT", "/books/9999", DUNE)[0] == 404


def test_delete(api):
    _, book = api("POST", "/books", DUNE)
    assert api("DELETE", f"/books/{book['id']}") == (204, None)
    assert api("GET", f"/books/{book['id']}")[0] == 404
    assert api("DELETE", f"/books/{book['id']}")[0] == 404


def test_not_found_and_method_not_allowed(api):
    assert api("GET", "/books/9999")[0] == 404
    assert api("GET", "/books/abc")[0] == 404
    assert api("GET", "/nope")[0] == 404
    assert api("DELETE", "/books")[0] == 405
    assert api("POST", "/health", {})[0] == 405


def test_data_persists_across_server_restart(tmp_path):
    db = str(tmp_path / "books.db")
    from app import BookStore

    created = BookStore(db).create(validate_book(DUNE))
    assert BookStore(db).get(created["id"]) == created


def test_validate_book_strips_whitespace():
    assert validate_book({"title": " Dune ", "author": " Frank Herbert "}) == {
        "title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None,
    }
    with pytest.raises(ValidationError):
        validate_book("not an object")
