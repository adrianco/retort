"""Integration tests: start a real server on an ephemeral port per test."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from app import ValidationError, make_server, validate_book

VALID = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}


@pytest.fixture
def api(tmp_path):
    server = make_server("127.0.0.1", 0, str(tmp_path / "test.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def request(method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                text = resp.read().decode()
                return resp.status, (json.loads(text) if text else None), resp.headers
        except urllib.error.HTTPError as err:
            text = err.read().decode()
            return err.code, (json.loads(text) if text else None), err.headers

    yield request
    server.shutdown()
    server.server_close()
    server.store.close()


def test_health(api):
    status, body, _ = api("GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_create_and_get_book(api):
    status, created, headers = api("POST", "/books", VALID)
    assert status == 201
    assert created["id"] >= 1
    assert {k: created[k] for k in VALID} == VALID
    assert headers["Location"] == f"/books/{created['id']}"

    status, fetched, _ = api("GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_requires_title_and_author(api):
    status, body, _ = api("POST", "/books", {"year": 2000})
    assert status == 422
    assert "title" in body["details"] and "author" in body["details"]

    status, body, _ = api("POST", "/books", {"title": "   ", "author": "X"})
    assert status == 422
    assert "title" in body["details"]


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"title": "T", "author": "A", "year": "1999"}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "isbn": "abc"}, "isbn"),
        ({"title": "T", "author": "A", "isbn": 12345}, "isbn"),
        ({"title": "T", "author": "A", "extra": 1}, "unknown_fields"),
    ],
)
def test_create_rejects_bad_fields(api, payload, field):
    status, body, _ = api("POST", "/books", payload)
    assert status == 422
    assert field in body["details"]


def test_invalid_json_returns_400(api):
    status, body, _ = api("POST", "/books", raw=b"{not json")
    assert status == 400
    status, body, _ = api("POST", "/books", raw=b"[1, 2]")
    assert status == 422


def test_list_and_author_filter(api):
    api("POST", "/books", VALID)
    api("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    api("POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})

    status, books, _ = api("GET", "/books")
    assert status == 200
    assert len(books) == 3

    status, books, _ = api("GET", "/books?author=Jane%20Austen")
    assert status == 200
    assert sorted(b["title"] for b in books) == ["Emma", "Persuasion"]

    status, books, _ = api("GET", "/books?author=jane%20austen")
    assert len(books) == 2  # case-insensitive

    status, books, _ = api("GET", "/books?author=Nobody")
    assert books == []


def test_update_book(api):
    _, created, _ = api("POST", "/books", VALID)
    update = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}
    status, updated, _ = api("PUT", f"/books/{created['id']}", update)
    assert status == 200
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] == 1969
    assert updated["isbn"] is None

    status, fetched, _ = api("GET", f"/books/{created['id']}")
    assert fetched == updated

    status, body, _ = api("PUT", f"/books/{created['id']}", {"title": "No author"})
    assert status == 422

    status, _, _ = api("PUT", "/books/9999", update)
    assert status == 404


def test_delete_book(api):
    _, created, _ = api("POST", "/books", VALID)
    status, body, _ = api("DELETE", f"/books/{created['id']}")
    assert status == 204
    assert body is None

    status, _, _ = api("GET", f"/books/{created['id']}")
    assert status == 404
    status, _, _ = api("DELETE", f"/books/{created['id']}")
    assert status == 404


def test_not_found_and_bad_ids(api):
    assert api("GET", "/books/12345")[0] == 404
    assert api("GET", "/books/abc")[0] == 400
    assert api("GET", "/nope")[0] == 404
    assert api("DELETE", "/books")[0] == 405


def test_persists_across_restarts(tmp_path):
    from app import BookStore

    db = str(tmp_path / "persist.db")
    store = BookStore(db)
    book = store.create(validate_book(VALID))
    store.close()

    store = BookStore(db)
    assert store.get(book["id"]) == book
    store.close()


def test_validate_book_unit():
    assert validate_book({"title": " A ", "author": "B"}) == {"title": "A", "author": "B"}
    with pytest.raises(ValidationError):
        validate_book(None)
    with pytest.raises(ValidationError):
        validate_book({"title": "A"})
