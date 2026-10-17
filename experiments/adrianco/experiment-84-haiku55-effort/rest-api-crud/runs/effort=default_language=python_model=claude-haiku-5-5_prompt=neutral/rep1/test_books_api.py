"""Integration tests for the books REST API.

Each test runs a real HTTP server on an ephemeral port backed by an in-memory
SQLite database, and talks to it over the network with urllib.
"""

import json
import threading
import urllib.error
import urllib.request

import pytest

from books_api import create_server, validate_book, ValidationError


@pytest.fixture
def base_url():
    server = create_server(host="127.0.0.1", port=0, db_path=":memory:")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        server.store.close()


def request(base_url, method, path, body=None, raw=None):
    """Send a request and return (status, headers, parsed_json_or_None)."""
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(base_url + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read()
            return resp.status, resp.headers, json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        return exc.code, exc.headers, json.loads(payload) if payload else None


SAMPLE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health_check(base_url):
    status, _, body = request(base_url, "GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_create_and_get_book(base_url):
    status, headers, created = request(base_url, "POST", "/books", SAMPLE)
    assert status == 201
    assert created["id"] >= 1
    assert created["title"] == "Dune"
    assert created["author"] == "Frank Herbert"
    assert created["year"] == 1965
    assert created["isbn"] == "9780441013593"
    assert headers["Location"] == f"/books/{created['id']}"

    status, _, fetched = request(base_url, "GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_requires_title_and_author(base_url):
    status, _, body = request(base_url, "POST", "/books", {"year": 2000})
    assert status == 400
    assert "'title' is required" in body["error"]
    assert "'author' is required" in body["error"]


def test_create_rejects_blank_strings_and_bad_year_and_isbn(base_url):
    status, _, body = request(base_url, "POST", "/books", {"title": "  ", "author": "A", "year": "1999"})
    assert status == 400
    assert "'title' must be a non-empty string" in body["error"]
    assert "'year' must be an integer" in body["error"]

    status, _, body = request(base_url, "POST", "/books", {"title": "T", "author": "A", "isbn": "123"})
    assert status == 400
    assert "'isbn'" in body["error"]


def test_create_rejects_invalid_json_and_non_object_body(base_url):
    status, _, body = request(base_url, "POST", "/books", raw=b"{not json")
    assert status == 400
    assert body["error"] == "request body must be valid JSON"

    status, _, body = request(base_url, "POST", "/books", ["not", "an", "object"])
    assert status == 400
    assert body["error"] == "request body must be a JSON object"


def test_list_books_and_filter_by_author(base_url):
    request(base_url, "POST", "/books", SAMPLE)
    request(base_url, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    request(base_url, "POST", "/books", {"title": "Dune Messiah", "author": "frank herbert"})

    status, _, books = request(base_url, "GET", "/books")
    assert status == 200
    assert [b["title"] for b in books] == ["Dune", "Emma", "Dune Messiah"]

    status, _, books = request(base_url, "GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in books] == ["Dune", "Dune Messiah"]

    status, _, books = request(base_url, "GET", "/books?author=Nobody")
    assert status == 200
    assert books == []


def test_get_missing_book_returns_404(base_url):
    status, _, body = request(base_url, "GET", "/books/999")
    assert status == 404
    assert body["error"] == "book not found"


def test_update_book_partial_and_full(base_url):
    _, _, created = request(base_url, "POST", "/books", SAMPLE)
    book_id = created["id"]

    status, _, updated = request(base_url, "PUT", f"/books/{book_id}", {"year": 1966})
    assert status == 200
    assert updated["year"] == 1966
    assert updated["title"] == "Dune"  # untouched fields are preserved

    status, _, updated = request(base_url, "PUT", f"/books/{book_id}", {
        "title": "Dune (Revised)", "author": "F. Herbert", "year": None, "isbn": None,
    })
    assert status == 200
    assert updated == {"id": book_id, "title": "Dune (Revised)", "author": "F. Herbert",
                       "year": None, "isbn": None}


def test_update_validates_input(base_url):
    _, _, created = request(base_url, "POST", "/books", SAMPLE)
    status, _, body = request(base_url, "PUT", f"/books/{created['id']}", {"author": ""})
    assert status == 400
    assert "'author' must be a non-empty string" in body["error"]


def test_update_missing_book_returns_404(base_url):
    status, _, body = request(base_url, "PUT", "/books/999", {"title": "X"})
    assert status == 404
    assert body["error"] == "book not found"


def test_delete_book(base_url):
    _, _, created = request(base_url, "POST", "/books", SAMPLE)
    book_id = created["id"]

    status, _, body = request(base_url, "DELETE", f"/books/{book_id}")
    assert status == 204
    assert body is None

    status, _, _ = request(base_url, "GET", f"/books/{book_id}")
    assert status == 404


def test_delete_missing_book_returns_404(base_url):
    status, _, body = request(base_url, "DELETE", "/books/999")
    assert status == 404
    assert body["error"] == "book not found"


def test_unknown_route_and_wrong_method(base_url):
    status, _, body = request(base_url, "GET", "/nope")
    assert status == 404

    status, headers, body = request(base_url, "PATCH", "/books/1")
    assert status == 405
    assert headers["Allow"] == "GET, PUT, DELETE"

    status, headers, _ = request(base_url, "DELETE", "/books")
    assert status == 405
    assert headers["Allow"] == "GET, POST"


def test_non_numeric_id_is_not_found(base_url):
    status, _, _ = request(base_url, "GET", "/books/abc")
    assert status == 404


def test_validate_book_unit_cases():
    assert validate_book({"title": " T ", "author": "A"}) == {"title": "T", "author": "A"}
    assert validate_book({"title": "T", "author": "A", "isbn": "0-306-40615-2"}) == {
        "title": "T", "author": "A", "isbn": "0306406152"}
    with pytest.raises(ValidationError):
        validate_book({"title": "T", "author": "A", "year": True})
    with pytest.raises(ValidationError):
        validate_book({"title": "T"}, partial=False)
    assert validate_book({"year": 2001}, partial=True) == {"year": 2001}
