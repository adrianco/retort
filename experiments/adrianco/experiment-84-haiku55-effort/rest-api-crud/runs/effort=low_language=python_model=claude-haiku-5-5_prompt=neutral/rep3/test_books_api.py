import json
import threading
import urllib.error
import urllib.request

import pytest

from books_api import create_server


@pytest.fixture
def base_url(tmp_path):
    server = create_server("127.0.0.1", 0, str(tmp_path / "test.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()


def request(base_url, method, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(base_url + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read()
            return resp.status, (json.loads(payload) if payload else None), resp.headers
    except urllib.error.HTTPError as err:
        payload = err.read()
        return err.code, (json.loads(payload) if payload else None), err.headers


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(base_url):
    status, body, _ = request(base_url, "GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_crud_lifecycle(base_url):
    status, created, headers = request(base_url, "POST", "/books", BOOK)
    assert status == 201
    assert created["title"] == "Dune"
    assert headers["Location"] == f"/books/{created['id']}"
    book_id = created["id"]

    status, fetched, _ = request(base_url, "GET", f"/books/{book_id}")
    assert status == 200
    assert fetched == created

    updated_payload = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}
    status, updated, _ = request(base_url, "PUT", f"/books/{book_id}", updated_payload)
    assert status == 200
    assert updated["title"] == "Dune Messiah"
    assert updated["isbn"] is None

    status, _, _ = request(base_url, "DELETE", f"/books/{book_id}")
    assert status == 204

    status, body, _ = request(base_url, "GET", f"/books/{book_id}")
    assert status == 404
    assert body["error"] == "book not found"


def test_list_and_author_filter(base_url):
    request(base_url, "POST", "/books", BOOK)
    request(base_url, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    request(base_url, "POST", "/books", {"title": "Children of Dune", "author": "frank herbert"})

    status, all_books, _ = request(base_url, "GET", "/books")
    assert status == 200
    assert [b["title"] for b in all_books] == ["Dune", "Emma", "Children of Dune"]

    status, filtered, _ = request(base_url, "GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in filtered] == ["Dune", "Children of Dune"]


def test_create_rejects_missing_required_fields(base_url):
    status, body, _ = request(base_url, "POST", "/books", {"year": 2000})
    assert status == 400
    assert body["error"] == "validation failed"
    assert any("title" in e for e in body["details"])
    assert any("author" in e for e in body["details"])


def test_create_rejects_blank_strings_and_bad_year(base_url):
    status, body, _ = request(
        base_url, "POST", "/books", {"title": "   ", "author": "A", "year": "1999"}
    )
    assert status == 400
    assert any("title" in e for e in body["details"])
    assert any("year" in e for e in body["details"])


def test_create_rejects_invalid_json(base_url):
    status, body, _ = request(base_url, "POST", "/books", raw=b"{not json")
    assert status == 400
    assert "valid JSON" in body["details"][0]


def test_duplicate_isbn_conflicts(base_url):
    request(base_url, "POST", "/books", BOOK)
    status, body, _ = request(base_url, "POST", "/books", {**BOOK, "title": "Other"})
    assert status == 409
    assert "ISBN" in body["error"]


def test_update_missing_book_returns_404(base_url):
    status, body, _ = request(
        base_url, "PUT", "/books/999", {"title": "X", "author": "Y"}
    )
    assert status == 404
    assert body["error"] == "book not found"


def test_update_validates_payload(base_url):
    _, created, _ = request(base_url, "POST", "/books", BOOK)
    status, body, _ = request(base_url, "PUT", f"/books/{created['id']}", {"author": "Y"})
    assert status == 400
    assert any("title" in e for e in body["details"])


def test_delete_missing_book_returns_404(base_url):
    status, _, _ = request(base_url, "DELETE", "/books/999")
    assert status == 404


def test_unknown_route_returns_404(base_url):
    status, body, _ = request(base_url, "GET", "/nope")
    assert status == 404
    assert body["error"] == "route not found"


def test_non_numeric_id_returns_404(base_url):
    status, _, _ = request(base_url, "GET", "/books/abc")
    assert status == 404
