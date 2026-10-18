import json
import threading
import urllib.error
import urllib.request

import pytest

from bookapi.app import Api, make_server
from bookapi.db import BookStore
from bookapi.validation import is_valid_isbn

VALID_BOOK = {
    "title": "Dune",
    "author": "Frank Herbert",
    "year": 1965,
    "isbn": "978-0-441-17271-9",
}


@pytest.fixture
def api():
    store = BookStore(":memory:")
    yield Api(store)
    store.close()


def create(api, **overrides):
    payload = {**VALID_BOOK, **overrides}
    return api.handle("POST", "/books", json.dumps(payload).encode())


# -- unit-level tests on the dispatcher ------------------------------------

def test_health(api):
    assert api.handle("GET", "/health") == (200, {"status": "ok"})


def test_create_then_get(api):
    status, created = create(api)
    assert status == 201
    assert created["title"] == "Dune"
    assert created["isbn"] == "9780441172719"  # normalised

    status, fetched = api.handle("GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_rejects_missing_title_and_author(api):
    status, body = api.handle("POST", "/books", json.dumps({"year": 2000}).encode())
    assert status == 400
    assert set(body["details"]) == {"title", "author"}


def test_create_rejects_invalid_json(api):
    status, body = api.handle("POST", "/books", b"{not json")
    assert status == 400
    assert "body" in body["details"]


def test_create_rejects_bad_year_and_isbn(api):
    status, body = create(api, year="1965", isbn="123")
    assert status == 400
    assert set(body["details"]) == {"year", "isbn"}


def test_list_filters_by_author_case_insensitively(api):
    create(api)
    create(api, title="Emma", author="Jane Austen", isbn=None)

    status, body = api.handle("GET", "/books?author=frank%20herbert")
    assert status == 200
    assert [b["title"] for b in body["books"]] == ["Dune"]
    assert body["count"] == 1

    _, all_books = api.handle("GET", "/books")
    assert all_books["count"] == 2


def test_update_replaces_fields(api):
    _, created = create(api)
    status, updated = api.handle(
        "PUT",
        f"/books/{created['id']}",
        json.dumps({"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}).encode(),
    )
    assert status == 200
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] == 1969
    assert updated["isbn"] is None


def test_update_missing_book_returns_404(api):
    status, _ = api.handle("PUT", "/books/999", json.dumps(VALID_BOOK).encode())
    assert status == 404


def test_delete_then_get_returns_404(api):
    _, created = create(api)
    assert api.handle("DELETE", f"/books/{created['id']}")[0] == 200
    assert api.handle("GET", f"/books/{created['id']}")[0] == 404
    assert api.handle("DELETE", f"/books/{created['id']}")[0] == 404


def test_duplicate_isbn_returns_409(api):
    create(api)
    status, _ = create(api, title="Other")
    assert status == 409


def test_unknown_route_and_method(api):
    assert api.handle("GET", "/nope")[0] == 404
    assert api.handle("PATCH", "/books/1")[0] == 405


def test_isbn_checksums():
    assert is_valid_isbn("0-306-40615-2")  # ISBN-10
    assert is_valid_isbn("080442957X")  # ISBN-10 with X check digit
    assert is_valid_isbn("978-0-441-17271-9")  # ISBN-13
    assert not is_valid_isbn("0-306-40615-3")
    assert not is_valid_isbn("12345")


# -- integration test over a real HTTP socket ------------------------------

@pytest.fixture
def live_server():
    store = BookStore(":memory:")
    server = make_server(store, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    yield base
    server.shutdown()
    server.server_close()
    store.close()


def _request(base, method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def test_full_lifecycle_over_http(live_server):
    assert _request(live_server, "GET", "/health") == (200, {"status": "ok"})

    status, created = _request(live_server, "POST", "/books", VALID_BOOK)
    assert status == 201
    book_id = created["id"]

    status, listing = _request(live_server, "GET", "/books?author=Frank+Herbert")
    assert status == 200 and listing["count"] == 1

    status, _ = _request(live_server, "PUT", f"/books/{book_id}", {**VALID_BOOK, "year": 1966})
    assert status == 200

    status, fetched = _request(live_server, "GET", f"/books/{book_id}")
    assert status == 200 and fetched["year"] == 1966

    status, _ = _request(live_server, "DELETE", f"/books/{book_id}")
    assert status == 200

    status, body = _request(live_server, "GET", f"/books/{book_id}")
    assert status == 404 and "error" in body


def test_invalid_body_over_http_returns_400(live_server):
    status, body = _request(live_server, "POST", "/books", {"title": ""})
    assert status == 400
    assert "author" in body["details"]
