"""Integration tests: run the real server on an ephemeral port with an in-memory DB."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from app import ValidationError, create_server, validate_book


@pytest.fixture
def api():
    server = create_server(port=0, db_path=":memory:", quiet=True)
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
                status, payload = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            status, payload = exc.code, exc.read()
        return status, json.loads(payload) if payload else None

    yield call

    server.shutdown()
    server.server_close()
    server.store.close()
    thread.join(timeout=5)


DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def test_health(api):
    assert api("GET", "/health") == (200, {"status": "ok"})


def test_create_and_get_book(api):
    status, created = api("POST", "/books", DUNE)
    assert status == 201
    assert created == {"id": created["id"], **DUNE}

    status, fetched = api("GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_with_only_required_fields(api):
    status, created = api("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert status == 201
    assert created["year"] is None
    assert created["isbn"] is None


@pytest.mark.parametrize(
    "body, bad_field",
    [
        ({"author": "Frank Herbert"}, "title"),
        ({"title": "Dune"}, "author"),
        ({"title": "   ", "author": "Frank Herbert"}, "title"),
        ({"title": "Dune", "author": 42}, "author"),
        ({"title": "Dune", "author": "Frank Herbert", "year": "1965"}, "year"),
        ({"title": "Dune", "author": "Frank Herbert", "year": True}, "year"),
        ({"title": "Dune", "author": "Frank Herbert", "isbn": 123}, "isbn"),
    ],
)
def test_create_validation_errors(api, body, bad_field):
    status, payload = api("POST", "/books", body)
    assert status == 400
    assert bad_field in payload["details"]
    assert api("GET", "/books") == (200, [])


def test_create_rejects_malformed_json(api):
    status, payload = api("POST", "/books", raw=b"{not json")
    assert status == 400
    assert "error" in payload


def test_create_rejects_non_object_body(api):
    status, _ = api("POST", "/books", ["Dune"])
    assert status == 400


def test_list_and_author_filter(api):
    api("POST", "/books", DUNE)
    api("POST", "/books", {"title": "Emma", "author": "Jane Austen", "year": 1815})
    api("POST", "/books", {"title": "Persuasion", "author": "Jane Austen", "year": 1817})

    status, books = api("GET", "/books")
    assert status == 200
    assert [b["title"] for b in books] == ["Dune", "Emma", "Persuasion"]

    status, books = api("GET", "/books?author=Jane%20Austen")
    assert status == 200
    assert [b["title"] for b in books] == ["Emma", "Persuasion"]

    assert api("GET", "/books?author=Nobody") == (200, [])


def test_update_book(api):
    _, created = api("POST", "/books", DUNE)
    book_id = created["id"]

    updated_body = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}
    status, updated = api("PUT", f"/books/{book_id}", updated_body)
    assert status == 200
    assert updated == {"id": book_id, **updated_body, "isbn": None}
    assert api("GET", f"/books/{book_id}") == (200, updated)


def test_update_validation_and_missing(api):
    _, created = api("POST", "/books", DUNE)

    status, payload = api("PUT", f"/books/{created['id']}", {"title": "No author"})
    assert status == 400
    assert "author" in payload["details"]
    # the failed update must not have changed the stored book
    assert api("GET", f"/books/{created['id']}") == (200, created)

    status, _ = api("PUT", "/books/9999", DUNE)
    assert status == 404


def test_delete_book(api):
    _, created = api("POST", "/books", DUNE)
    book_id = created["id"]

    assert api("DELETE", f"/books/{book_id}") == (204, None)
    assert api("GET", f"/books/{book_id}")[0] == 404
    assert api("DELETE", f"/books/{book_id}")[0] == 404


def test_unknown_routes_and_methods(api):
    assert api("GET", "/books/9999")[0] == 404
    assert api("GET", "/books/abc")[0] == 404
    assert api("GET", "/nope")[0] == 404
    assert api("DELETE", "/books")[0] == 405
    assert api("POST", "/books/1", DUNE)[0] == 405


def test_validate_book_strips_whitespace():
    cleaned = validate_book({"title": "  Dune ", "author": " Frank Herbert "})
    assert cleaned == {"title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}


def test_validate_book_reports_all_errors():
    with pytest.raises(ValidationError) as excinfo:
        validate_book({"year": "x"})
    assert set(excinfo.value.errors) == {"title", "author", "year"}
