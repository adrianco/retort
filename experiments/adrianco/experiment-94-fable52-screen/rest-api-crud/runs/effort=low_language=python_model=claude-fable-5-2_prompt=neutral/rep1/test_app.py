import json
import threading
import urllib.error
import urllib.request

import pytest

from app import BookStore, ValidationError, create_server, validate_book

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


@pytest.fixture
def api(tmp_path):
    server = create_server(port=0, db_path=str(tmp_path / "test.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def call(method, path, body=None, raw=None):
        data = raw if raw is not None else (
            json.dumps(body).encode() if body is not None else None
        )
        req = urllib.request.Request(base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status, text = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            status, text = exc.code, exc.read()
        return status, (json.loads(text) if text else None)

    yield call
    server.shutdown()
    server.server_close()
    server.store.close()
    thread.join(timeout=5)


def test_health(api):
    assert api("GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(api):
    status, book = api("POST", "/books", DUNE)
    assert status == 201
    assert book == {"id": book["id"], **DUNE}
    assert api("GET", f"/books/{book['id']}") == (200, book)


def test_create_minimal_book(api):
    status, book = api("POST", "/books", {"title": "T", "author": "A"})
    assert status == 201
    assert book["year"] is None and book["isbn"] is None


@pytest.mark.parametrize(
    "payload, bad_field",
    [
        ({"author": "A"}, "title"),
        ({"title": "T"}, "author"),
        ({"title": "   ", "author": "A"}, "title"),
        ({"title": "T", "author": 5}, "author"),
        ({"title": "T", "author": "A", "year": "1999"}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "isbn": 123}, "isbn"),
    ],
)
def test_create_validation(api, payload, bad_field):
    status, body = api("POST", "/books", payload)
    assert status == 400
    assert bad_field in body["details"]
    assert api("GET", "/books") == (200, [])


def test_create_invalid_json(api):
    status, body = api("POST", "/books", raw=b"{not json")
    assert status == 400
    assert "error" in body


def test_create_non_object_body(api):
    status, _ = api("POST", "/books", [1, 2])
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
    updated = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": None}
    status, body = api("PUT", f"/books/{book['id']}", updated)
    assert status == 200
    assert body == {"id": book["id"], **updated}
    assert api("GET", f"/books/{book['id']}") == (200, body)


def test_update_validation_and_missing(api):
    _, book = api("POST", "/books", DUNE)
    status, _ = api("PUT", f"/books/{book['id']}", {"title": "", "author": "A"})
    assert status == 400
    assert api("GET", f"/books/{book['id']}")[1]["title"] == "Dune"
    assert api("PUT", "/books/999", DUNE)[0] == 404


def test_delete(api):
    _, book = api("POST", "/books", DUNE)
    assert api("DELETE", f"/books/{book['id']}") == (204, None)
    assert api("GET", f"/books/{book['id']}")[0] == 404
    assert api("DELETE", f"/books/{book['id']}")[0] == 404


def test_not_found_and_method_not_allowed(api):
    assert api("GET", "/books/999")[0] == 404
    assert api("GET", "/books/abc")[0] == 404
    assert api("GET", "/nope")[0] == 404
    assert api("DELETE", "/books")[0] == 405
    assert api("POST", "/books/1", DUNE)[0] == 405


def test_data_persists_in_sqlite_file(tmp_path):
    path = str(tmp_path / "persist.db")
    store = BookStore(path)
    created = store.create(validate_book(DUNE))
    store.close()

    reopened = BookStore(path)
    assert reopened.get(created["id"]) == created
    reopened.close()


def test_validate_book_strips_whitespace():
    book = validate_book({"title": "  Dune ", "author": " Frank Herbert "})
    assert book["title"] == "Dune" and book["author"] == "Frank Herbert"
    with pytest.raises(ValidationError):
        validate_book("nope")
