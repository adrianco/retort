import json
import threading
import urllib.error
import urllib.request

import pytest

from app import ApiError, make_server, validate_book

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


@pytest.fixture
def api(tmp_path):
    server = make_server(port=0, db_path=str(tmp_path / "books.db"), quiet=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def call(method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status, payload = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            status, payload = e.code, e.read()
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
    status, book = api("POST", "/books", {"title": "T", "author": "A"})
    assert status == 201
    assert book["year"] is None and book["isbn"] is None


@pytest.mark.parametrize(
    "body, bad_field",
    [
        ({"author": "A"}, "title"),
        ({"title": "T"}, "author"),
        ({"title": "   ", "author": "A"}, "title"),
        ({"title": "T", "author": 5}, "author"),
        ({"title": "T", "author": "A", "year": "1965"}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "isbn": 123}, "isbn"),
    ],
)
def test_create_validation(api, body, bad_field):
    status, payload = api("POST", "/books", body)
    assert status == 400
    assert bad_field in payload["details"]
    assert api("GET", "/books") == (200, [])


def test_create_rejects_bad_json(api):
    assert api("POST", "/books", raw=b"{not json")[0] == 400
    assert api("POST", "/books", raw=b"[1, 2]")[0] == 400
    assert api("POST", "/books")[0] == 400


def test_list_and_author_filter(api):
    api("POST", "/books", DUNE)
    api("POST", "/books", {"title": "Emma", "author": "Jane Austen", "year": 1815})
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
    status, payload = api("PUT", f"/books/{book['id']}", updated)
    assert status == 200
    assert payload == {"id": book["id"], **updated}
    assert api("GET", f"/books/{book['id']}") == (200, payload)


def test_update_validation_and_missing(api):
    _, book = api("POST", "/books", DUNE)
    assert api("PUT", f"/books/{book['id']}", {"title": "No author"})[0] == 400
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


def test_data_persists_across_restart(tmp_path):
    from app import BookStore

    db = str(tmp_path / "books.db")
    created = BookStore(db).create(validate_book(DUNE))
    assert BookStore(db).get(created["id"]) == created


def test_validate_book_strips_whitespace():
    assert validate_book({"title": " T ", "author": " A "})["title"] == "T"
    with pytest.raises(ApiError):
        validate_book("nope")
