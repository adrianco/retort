import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from urllib.parse import quote

import pytest

from app import create_server

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815}
PERSUASION = {"title": "Persuasion", "author": "Jane Austen", "year": 1817}

# Bypass any proxy settings in the environment so requests reach the local server.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@contextmanager
def running_server(db_path=":memory:"):
    server = create_server(db_path, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def base_url():
    with running_server() as url:
        yield url


def call(base_url, method, path, body=None, raw=None):
    """Send a request and return (status, headers, decoded JSON body or None)."""
    if raw is None and body is not None:
        raw = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base_url + path, data=raw, method=method)
    if raw is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with OPENER.open(req) as resp:
            return resp.status, resp.headers, _decode(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, err.headers, _decode(err.read())


def _decode(raw):
    return json.loads(raw) if raw else None


def create(base_url, book):
    status, _, body = call(base_url, "POST", "/books", body=book)
    assert status == 201
    return body


def test_create_and_fetch_book(base_url):
    status, headers, created = call(base_url, "POST", "/books", body=DUNE)

    assert status == 201
    assert created == {"id": created["id"], **DUNE}
    assert headers["Location"] == f"/books/{created['id']}"

    status, _, fetched = call(base_url, "GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_without_optional_fields_stores_nulls(base_url):
    created = create(base_url, {"title": "Untitled", "author": "Anon"})
    assert created["year"] is None
    assert created["isbn"] is None


def test_create_reports_missing_required_fields(base_url):
    status, _, body = call(base_url, "POST", "/books", body={"year": 1965})

    assert status == 400
    assert body["error"] == "validation failed"
    assert body["details"] == {"title": "is required", "author": "is required"}


def test_create_rejects_malformed_json(base_url):
    status, _, body = call(base_url, "POST", "/books", raw=b"{not json")
    assert status == 400
    assert "valid JSON" in body["error"]


def test_create_rejects_non_object_body(base_url):
    status, _, body = call(base_url, "POST", "/books", raw=b'["Dune"]')
    assert status == 400
    assert body["details"] == {"body": "must be a JSON object"}


def test_list_returns_all_books_in_id_order(base_url):
    dune = create(base_url, DUNE)
    emma = create(base_url, EMMA)

    status, _, books = call(base_url, "GET", "/books")

    assert status == 200
    assert [b["id"] for b in books] == [dune["id"], emma["id"]]


def test_list_filters_by_author_case_insensitively(base_url):
    create(base_url, EMMA)
    create(base_url, PERSUASION)
    create(base_url, DUNE)

    _, _, books = call(base_url, "GET", f"/books?author={quote('jane AUSTEN')}")

    assert [b["title"] for b in books] == ["Emma", "Persuasion"]


def test_list_with_unmatched_author_returns_empty_list(base_url):
    create(base_url, DUNE)
    status, _, books = call(base_url, "GET", "/books?author=Nobody")
    assert status == 200
    assert books == []


def test_blank_author_filter_is_rejected(base_url):
    status, _, body = call(base_url, "GET", "/books?author=%20")
    assert status == 400
    assert "author filter" in body["error"]


def test_get_missing_or_non_numeric_book_returns_404(base_url):
    assert call(base_url, "GET", "/books/999")[0] == 404
    assert call(base_url, "GET", "/books/abc")[0] == 404


def test_update_replaces_book(base_url):
    created = create(base_url, DUNE)
    replacement = {"title": "Dune Messiah", "author": "Frank Herbert"}

    status, _, updated = call(base_url, "PUT", f"/books/{created['id']}", body=replacement)

    assert status == 200
    assert updated == {"id": created["id"], "title": "Dune Messiah",
                       "author": "Frank Herbert", "year": None, "isbn": None}
    assert call(base_url, "GET", f"/books/{created['id']}")[2] == updated


def test_update_with_invalid_data_leaves_book_unchanged(base_url):
    created = create(base_url, DUNE)

    status, _, body = call(base_url, "PUT", f"/books/{created['id']}",
                           body={"title": "", "author": "Frank Herbert", "year": "soon"})

    assert status == 400
    assert set(body["details"]) == {"title", "year"}
    assert call(base_url, "GET", f"/books/{created['id']}")[2] == created


def test_update_missing_book_returns_404(base_url):
    status, _, _ = call(base_url, "PUT", "/books/999", body=DUNE)
    assert status == 404


def test_delete_removes_book(base_url):
    created = create(base_url, DUNE)
    path = f"/books/{created['id']}"

    status, _, body = call(base_url, "DELETE", path)
    assert status == 204
    assert body is None

    assert call(base_url, "GET", path)[0] == 404
    assert call(base_url, "DELETE", path)[0] == 404


def test_health_reports_ok(base_url):
    status, _, body = call(base_url, "GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_unknown_route_returns_404(base_url):
    status, _, body = call(base_url, "GET", "/nope")
    assert status == 404
    assert body == {"error": "not found"}


def test_unsupported_method_returns_405_with_allow_header(base_url):
    status, headers, body = call(base_url, "PATCH", "/books")
    assert status == 405
    assert headers["Allow"] == "GET, POST"
    assert body == {"error": "method not allowed"}


def test_books_persist_across_server_restarts(tmp_path):
    db_path = str(tmp_path / "books.db")

    with running_server(db_path) as url:
        created = create(url, DUNE)

    with running_server(db_path) as url:
        status, _, fetched = call(url, "GET", f"/books/{created['id']}")

    assert status == 200
    assert fetched == created
