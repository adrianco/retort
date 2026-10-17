import json
import os
import sys
import threading
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from book_store import BookStore, ValidationError, validate_book  # noqa: E402
from server import make_server  # noqa: E402


@pytest.fixture
def base_url(tmp_path):
    httpd = make_server(str(tmp_path / "test.db"), host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    yield f"http://{host}:{port}"
    httpd.shutdown()
    httpd.server_close()
    httpd.store.close()


def request(base_url, method, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(base_url + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read()
            return resp.status, (json.loads(payload) if payload else None)
    except urllib.error.HTTPError as err:
        payload = err.read()
        return err.code, (json.loads(payload) if payload else None)


SAMPLE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


# ----- integration tests over HTTP -----

def test_health_check(base_url):
    status, body = request(base_url, "GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_full_crud_lifecycle(base_url):
    status, created = request(base_url, "POST", "/books", SAMPLE)
    assert status == 201
    assert created["id"] >= 1
    assert created["title"] == "Dune"
    book_id = created["id"]

    status, fetched = request(base_url, "GET", f"/books/{book_id}")
    assert status == 200
    assert fetched == created

    status, updated = request(base_url, "PUT", f"/books/{book_id}", {"year": 1966})
    assert status == 200
    assert updated["year"] == 1966
    assert updated["title"] == "Dune"  # partial update keeps other fields

    status, _ = request(base_url, "DELETE", f"/books/{book_id}")
    assert status == 204

    status, body = request(base_url, "GET", f"/books/{book_id}")
    assert status == 404
    assert "error" in body


def test_list_and_author_filter(base_url):
    request(base_url, "POST", "/books", SAMPLE)
    request(base_url, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    request(base_url, "POST", "/books", {"title": "Dune Messiah", "author": "frank herbert"})

    status, all_books = request(base_url, "GET", "/books")
    assert status == 200
    assert len(all_books) == 3

    status, herbert = request(base_url, "GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in herbert] == ["Dune", "Dune Messiah"]

    status, none = request(base_url, "GET", "/books?author=Nobody")
    assert status == 200
    assert none == []


def test_create_validation_rejects_missing_required_fields(base_url):
    status, body = request(base_url, "POST", "/books", {"year": 2000})
    assert status == 400
    assert set(body["details"]) == {"title", "author"}

    status, body = request(base_url, "POST", "/books", {"title": "   ", "author": "X"})
    assert status == 400
    assert "title" in body["details"]


def test_invalid_json_and_non_object_bodies(base_url):
    status, _ = request(base_url, "POST", "/books", raw=b"{not json")
    assert status == 400

    status, _ = request(base_url, "POST", "/books", raw=b'["a", "b"]')
    assert status == 400


def test_unknown_book_returns_404_for_get_put_delete(base_url):
    assert request(base_url, "GET", "/books/999")[0] == 404
    assert request(base_url, "PUT", "/books/999", {"title": "X"})[0] == 404
    assert request(base_url, "DELETE", "/books/999")[0] == 404


def test_unknown_route_returns_404(base_url):
    status, _ = request(base_url, "GET", "/nope")
    assert status == 404


# ----- unit tests for validation and storage -----

def test_validate_book_requires_title_and_author():
    with pytest.raises(ValidationError) as exc:
        validate_book({})
    assert set(exc.value.errors) == {"title", "author"}


def test_validate_book_rejects_bool_as_year():
    with pytest.raises(ValidationError) as exc:
        validate_book({"title": "T", "author": "A", "year": True})
    assert "year" in exc.value.errors


def test_validate_book_partial_allows_missing_required_fields():
    assert validate_book({"year": 1999}, partial=True) == {"year": 1999}


def test_store_create_get_update_delete_roundtrip():
    store = BookStore(":memory:")
    book = store.create({"title": "Neuromancer", "author": "William Gibson"})
    assert book["year"] is None and book["isbn"] is None

    updated = store.update(book["id"], {"isbn": "9780441569595"})
    assert updated["isbn"] == "9780441569595"

    assert store.delete(book["id"]) is True
    assert store.get(book["id"]) is None
    assert store.delete(book["id"]) is False
    store.close()
