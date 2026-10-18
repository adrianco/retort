import json
import threading
import urllib.error
import urllib.request

import pytest

from app import create_server


@pytest.fixture
def base_url(tmp_path):
    server = create_server(port=0, db_path=str(tmp_path / "test.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()


def request(base_url, method, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base_url + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read()
            return resp.status, (json.loads(payload) if payload else None)
    except urllib.error.HTTPError as err:
        payload = err.read()
        return err.code, (json.loads(payload) if payload else None)


SAMPLE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(base_url):
    status, body = request(base_url, "GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_crud_lifecycle(base_url):
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
    assert updated["title"] == "Dune"  # untouched fields preserved

    status, _ = request(base_url, "DELETE", f"/books/{book_id}")
    assert status == 204

    status, body = request(base_url, "GET", f"/books/{book_id}")
    assert status == 404
    assert "error" in body


def test_list_and_author_filter(base_url):
    request(base_url, "POST", "/books", SAMPLE)
    request(base_url, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})

    status, books = request(base_url, "GET", "/books")
    assert status == 200
    assert [b["title"] for b in books] == ["Dune", "Emma"]

    status, books = request(base_url, "GET", "/books?author=jane%20austen")
    assert status == 200
    assert [b["title"] for b in books] == ["Emma"]


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "X"},
        {"title": "X"},
        {"title": "   ", "author": "X"},
        {"title": 5, "author": "X"},
        {"title": "X", "author": "Y", "year": "1999"},
        {"title": "X", "author": "Y", "year": True},
    ],
)
def test_create_validation_errors(base_url, payload):
    status, body = request(base_url, "POST", "/books", payload)
    assert status == 400
    assert body["error"] == "validation failed"
    assert body["details"]


def test_create_rejects_invalid_json(base_url):
    status, body = request(base_url, "POST", "/books", raw=b"{not json")
    assert status == 400
    assert "details" in body


def test_put_validates_present_fields(base_url):
    _, created = request(base_url, "POST", "/books", SAMPLE)
    status, body = request(base_url, "PUT", f"/books/{created['id']}", {"title": ""})
    assert status == 400
    assert "title" in body["details"]


def test_missing_book_returns_404(base_url):
    assert request(base_url, "GET", "/books/999")[0] == 404
    assert request(base_url, "PUT", "/books/999", {"year": 2000})[0] == 404
    assert request(base_url, "DELETE", "/books/999")[0] == 404


def test_unknown_route_and_method(base_url):
    assert request(base_url, "GET", "/nope")[0] == 404
    assert request(base_url, "PATCH", "/books")[0] == 405
    assert request(base_url, "POST", "/health")[0] == 405
