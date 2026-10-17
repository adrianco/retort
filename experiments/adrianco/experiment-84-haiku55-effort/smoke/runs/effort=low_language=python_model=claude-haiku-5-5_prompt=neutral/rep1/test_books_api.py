import json
import threading
import urllib.error
import urllib.request

import pytest

from books_api import ValidationError, create_server, validate_book


@pytest.fixture
def base_url(tmp_path):
    server = create_server("127.0.0.1", 0, str(tmp_path / "test.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()
    server.book_store.close()


def request(base_url, method, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(base_url + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read()
            return resp.status, (json.loads(text) if text else None)
    except urllib.error.HTTPError as err:
        text = err.read()
        return err.code, (json.loads(text) if text else None)


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


# ---- validation (unit) ------------------------------------------------------

def test_validate_requires_title_and_author():
    with pytest.raises(ValidationError, match="'title' is required"):
        validate_book({"author": "A"})
    with pytest.raises(ValidationError, match="'author' is required"):
        validate_book({"title": "T"})


def test_validate_rejects_blank_strings_and_bad_year():
    with pytest.raises(ValidationError):
        validate_book({"title": "   ", "author": "A"})
    with pytest.raises(ValidationError, match="'year' must be an integer"):
        validate_book({"title": "T", "author": "A", "year": "1999"})
    with pytest.raises(ValidationError, match="'year' must be an integer"):
        validate_book({"title": "T", "author": "A", "year": True})


def test_validate_partial_allows_subset():
    assert validate_book({"year": 2001}, partial=True) == {"year": 2001}


# ---- health -----------------------------------------------------------------

def test_health_check(base_url):
    status, body = request(base_url, "GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


# ---- CRUD integration -------------------------------------------------------

def test_full_crud_lifecycle(base_url):
    status, created = request(base_url, "POST", "/books", BOOK)
    assert status == 201
    assert created["id"] == 1
    assert created["title"] == "Dune"

    status, fetched = request(base_url, "GET", "/books/1")
    assert status == 200
    assert fetched == created

    status, updated = request(base_url, "PUT", "/books/1", {"year": 1966})
    assert status == 200
    assert updated["year"] == 1966
    assert updated["title"] == "Dune"

    status, _ = request(base_url, "DELETE", "/books/1")
    assert status == 204

    status, body = request(base_url, "GET", "/books/1")
    assert status == 404
    assert body == {"error": "book not found"}


def test_list_and_author_filter(base_url):
    request(base_url, "POST", "/books", BOOK)
    request(base_url, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    request(base_url, "POST", "/books", {"title": "Children of Dune", "author": "frank herbert"})

    status, all_books = request(base_url, "GET", "/books")
    assert status == 200
    assert [b["title"] for b in all_books] == ["Dune", "Emma", "Children of Dune"]

    status, filtered = request(base_url, "GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in filtered] == ["Dune", "Children of Dune"]


def test_create_validation_returns_400(base_url):
    status, body = request(base_url, "POST", "/books", {"author": "Nobody"})
    assert status == 400
    assert "title" in body["error"]


def test_invalid_json_returns_400(base_url):
    status, body = request(base_url, "POST", "/books", raw=b"{not json")
    assert status == 400
    assert body == {"error": "request body must be valid JSON"}


def test_update_missing_book_returns_404(base_url):
    status, _ = request(base_url, "PUT", "/books/999", {"year": 2000})
    assert status == 404


def test_delete_missing_book_returns_404(base_url):
    status, _ = request(base_url, "DELETE", "/books/999")
    assert status == 404


def test_unknown_route_and_method(base_url):
    status, _ = request(base_url, "GET", "/nope")
    assert status == 404
    status, _ = request(base_url, "PATCH", "/books/1")
    assert status == 405
