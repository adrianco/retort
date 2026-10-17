"""Integration tests: run the real HTTP server on an ephemeral port and call it over the network."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from bookapi import create_server

VALID_BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


@pytest.fixture
def base_url():
    server = create_server("127.0.0.1", 0, ":memory:")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()
    server.store.close()


def request(base_url, method, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base_url + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, _parse(resp.read()), resp.headers
    except urllib.error.HTTPError as err:
        return err.code, _parse(err.read()), err.headers


def _parse(raw):
    return json.loads(raw) if raw else None


def test_health_endpoint(base_url):
    status, body, _ = request(base_url, "GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_create_then_get_book(base_url):
    status, created, headers = request(base_url, "POST", "/books", VALID_BOOK)
    assert status == 201
    assert created["id"] >= 1
    assert created["title"] == "Dune"
    assert headers["Location"] == f"/books/{created['id']}"

    status, fetched, _ = request(base_url, "GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_with_only_required_fields_defaults_optional_to_null(base_url):
    status, body, _ = request(base_url, "POST", "/books", {"title": "T", "author": "A"})
    assert status == 201
    assert body["year"] is None
    assert body["isbn"] is None


def test_list_books_and_author_filter_is_case_insensitive(base_url):
    request(base_url, "POST", "/books", VALID_BOOK)
    request(base_url, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    request(base_url, "POST", "/books", {"title": "Children of Dune", "author": "frank herbert"})

    status, all_books, _ = request(base_url, "GET", "/books")
    assert status == 200
    assert len(all_books) == 3

    status, filtered, _ = request(base_url, "GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in filtered] == ["Dune", "Children of Dune"]


def test_update_book_replaces_fields(base_url):
    _, created, _ = request(base_url, "POST", "/books", VALID_BOOK)
    status, updated, _ = request(
        base_url, "PUT", f"/books/{created['id']}", {"title": "Dune Messiah", "author": "Frank Herbert"}
    )
    assert status == 200
    assert updated["id"] == created["id"]
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] is None  # PUT is a full replacement


def test_delete_book(base_url):
    _, created, _ = request(base_url, "POST", "/books", VALID_BOOK)
    status, body, _ = request(base_url, "DELETE", f"/books/{created['id']}")
    assert status == 204
    assert body is None

    status, body, _ = request(base_url, "GET", f"/books/{created['id']}")
    assert status == 404
    assert body["error"] == "book not found"


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_missing_book_returns_404(base_url, method):
    body = VALID_BOOK if method == "PUT" else None
    status, resp, _ = request(base_url, method, "/books/999", body)
    assert status == 404
    assert resp["error"] == "book not found"


def test_non_numeric_id_returns_404(base_url):
    status, _, _ = request(base_url, "GET", "/books/abc")
    assert status == 404


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"author": "A"}, "title"),
        ({"title": "T"}, "author"),
        ({"title": "   ", "author": "A"}, "title"),
        ({"title": "T", "author": 42}, "author"),
        ({"title": "T", "author": "A", "year": "1999"}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "year": -5}, "year"),
        ({"title": "T", "author": "A", "isbn": 123}, "isbn"),
    ],
)
def test_invalid_payload_returns_400_with_field_errors(base_url, payload, field):
    status, body, _ = request(base_url, "POST", "/books", payload)
    assert status == 400
    assert body["error"] == "validation failed"
    assert field in body["details"]


def test_put_validates_payload_too(base_url):
    _, created, _ = request(base_url, "POST", "/books", VALID_BOOK)
    status, body, _ = request(base_url, "PUT", f"/books/{created['id']}", {"title": "X"})
    assert status == 400
    assert "author" in body["details"]


def test_malformed_json_returns_400(base_url):
    status, body, _ = request(base_url, "POST", "/books", raw=b"{not json")
    assert status == 400
    assert body["error"] == "invalid JSON body"


def test_non_object_json_returns_400(base_url):
    status, body, _ = request(base_url, "POST", "/books", ["a", "list"])
    assert status == 400
    assert "body" in body["details"]


def test_unknown_route_returns_404(base_url):
    status, _, _ = request(base_url, "GET", "/nope")
    assert status == 404


def test_wrong_method_returns_405_with_allow_header(base_url):
    status, _, headers = request(base_url, "PATCH", "/books")
    assert status == 405
    assert headers["Allow"] == "GET, POST"
