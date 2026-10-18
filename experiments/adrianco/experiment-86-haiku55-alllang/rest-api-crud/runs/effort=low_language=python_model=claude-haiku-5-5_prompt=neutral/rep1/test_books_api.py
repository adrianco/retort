"""Integration tests: run the real HTTP server on an ephemeral port and call it."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from books_api import create_server


@pytest.fixture
def base_url():
    server = create_server(port=0)
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
            text = resp.read()
            return resp.status, (json.loads(text) if text else None)
    except urllib.error.HTTPError as err:
        text = err.read()
        return err.code, (json.loads(text) if text else None)


VALID_BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(base_url):
    status, body = request(base_url, "GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_create_then_get_and_list(base_url):
    status, created = request(base_url, "POST", "/books", VALID_BOOK)
    assert status == 201
    assert created["id"] == 1
    assert created["title"] == "Dune"

    status, fetched = request(base_url, "GET", "/books/1")
    assert status == 200
    assert fetched == created

    status, books = request(base_url, "GET", "/books")
    assert status == 200
    assert books == [created]


def test_author_filter_is_case_insensitive(base_url):
    request(base_url, "POST", "/books", VALID_BOOK)
    request(base_url, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})

    _, books = request(base_url, "GET", "/books?author=frank%20herbert")
    assert [b["title"] for b in books] == ["Dune"]

    _, books = request(base_url, "GET", "/books?author=Nobody")
    assert books == []


def test_update_partial_and_full(base_url):
    request(base_url, "POST", "/books", VALID_BOOK)

    status, updated = request(base_url, "PUT", "/books/1", {"year": 1966})
    assert status == 200
    assert updated["year"] == 1966
    assert updated["title"] == "Dune"

    status, updated = request(base_url, "PUT", "/books/1", {"title": "Dune Messiah", "author": "Frank Herbert"})
    assert status == 200
    assert updated["title"] == "Dune Messiah"


def test_delete(base_url):
    request(base_url, "POST", "/books", VALID_BOOK)

    status, _ = request(base_url, "DELETE", "/books/1")
    assert status == 204
    status, _ = request(base_url, "GET", "/books/1")
    assert status == 404
    status, _ = request(base_url, "DELETE", "/books/1")
    assert status == 404


def test_missing_book_returns_404(base_url):
    assert request(base_url, "GET", "/books/999")[0] == 404
    assert request(base_url, "PUT", "/books/999", {"year": 2000})[0] == 404


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"author": "Someone"}, "title"),
        ({"title": "   ", "author": "Someone"}, "title"),
        ({"title": "Something"}, "author"),
        ({"title": "X", "author": "Y", "year": "1999"}, "year"),
        ({"title": "X", "author": "Y", "year": True}, "year"),
        ({"title": "X", "author": "Y", "isbn": "abc"}, "isbn"),
    ],
)
def test_create_validation_errors(base_url, payload, field):
    status, body = request(base_url, "POST", "/books", payload)
    assert status == 400
    assert field in body["details"]


def test_update_rejects_empty_title(base_url):
    request(base_url, "POST", "/books", VALID_BOOK)
    status, body = request(base_url, "PUT", "/books/1", {"title": ""})
    assert status == 400
    assert "title" in body["details"]


def test_malformed_json_returns_400(base_url):
    status, body = request(base_url, "POST", "/books", raw=b"{not json")
    assert status == 400
    assert "JSON" in body["error"]


def test_non_object_body_returns_400(base_url):
    status, body = request(base_url, "POST", "/books", [1, 2, 3])
    assert status == 400
    assert "body" in body["details"]


def test_unknown_route_and_method(base_url):
    assert request(base_url, "GET", "/nope")[0] == 404
    assert request(base_url, "PATCH", "/books/1", {})[0] == 405
