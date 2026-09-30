"""Tests against a real HTTP server on a loopback socket."""

import http.client
import json
import threading

import pytest

from bookapi.server import create_server


@pytest.fixture
def server(db_path):
    httpd, store = create_server("127.0.0.1", 0, db_path)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)
    store.close()


def call(port, method, path, payload=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        body = json.dumps(payload) if payload is not None else None
        headers = {"Content-Type": "application/json"} if body else {}
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        return resp.status, (json.loads(raw) if raw else None)
    finally:
        conn.close()


def test_full_crud_lifecycle_over_http(server):
    assert call(server, "GET", "/health") == (200, {"status": "ok"})

    status, book = call(server, "POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965})
    assert status == 201
    path = f"/books/{book['id']}"

    assert call(server, "GET", path) == (200, book)
    assert call(server, "GET", "/books?author=Frank+Herbert") == (200, [book])

    status, updated = call(server, "PUT", path, {"title": "Dune (Deluxe)"})
    assert status == 200
    assert updated["title"] == "Dune (Deluxe)"

    assert call(server, "DELETE", path) == (204, None)
    assert call(server, "GET", path)[0] == 404


def test_validation_error_over_http(server):
    status, body = call(server, "POST", "/books", {"title": "No author"})
    assert status == 400
    assert "author" in body["details"]


def test_concurrent_creates_are_all_stored(server):
    errors = []

    def worker(n):
        try:
            status, _ = call(server, "POST", "/books", {"title": f"Book {n}", "author": "Same Author"})
            if status != 201:
                errors.append(status)
        except Exception as exc:  # pragma: no cover - only on failure
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert errors == []
    status, books = call(server, "GET", "/books")
    assert status == 200
    assert len(books) == 20
    assert len({b["id"] for b in books}) == 20
