"""End-to-end tests: a real HTTP server on a free port, talked to over sockets."""

import http.client
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from books_api import create_app
from books_api.server import create_server, parse_args


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "books.db"


@pytest.fixture
def server(db_path):
    app = create_app(db_path)
    httpd = create_server(app, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield httpd.server_address[:2]
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)
    app.repository.close()


def request(address, method, path, payload=None, headers=None):
    conn = http.client.HTTPConnection(*address, timeout=5)
    try:
        body = None
        headers = dict(headers or {})
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        data = json.loads(raw) if raw else None
        return response.status, dict(response.getheaders()), data
    finally:
        conn.close()


def test_crud_round_trip_over_http(server, db_path):
    status, _, health = request(server, "GET", "/health")
    assert (status, health) == (200, {"status": "ok", "database": "ok"})

    book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    status, headers, created = request(server, "POST", "/books", book)
    assert status == 201
    assert created == {"id": created["id"], **book}
    assert headers["Location"] == f"/books/{created['id']}"

    status, _, fetched = request(server, "GET", headers["Location"])
    assert (status, fetched) == (200, created)

    status, _, listed = request(server, "GET", "/books?author=herbert")
    assert (status, listed) == (200, [created])

    status, _, updated = request(server, "PUT", f"/books/{created['id']}", {**book, "title": "Dune Messiah", "year": 1969})
    assert status == 200
    assert updated["title"] == "Dune Messiah"

    # The change really is in the SQLite file on disk.
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute("SELECT title, year FROM books WHERE id = ?", (created["id"],)).fetchone()
    assert row == ("Dune Messiah", 1969)

    status, _, body = request(server, "DELETE", f"/books/{created['id']}")
    assert (status, body) == (204, None)

    status, _, error = request(server, "GET", f"/books/{created['id']}")
    assert status == 404
    assert error == {"error": f"Book {created['id']} not found"}


def test_validation_errors_over_http(server):
    status, headers, body = request(server, "POST", "/books", {"year": 1965})
    assert status == 400
    assert headers["Content-Type"] == "application/json"
    assert body["details"] == {"title": "title is required", "author": "author is required"}


def test_missing_content_type_over_http(server):
    conn = http.client.HTTPConnection(*server, timeout=5)
    try:
        conn.request("POST", "/books", body=b'{"title": "Dune", "author": "Frank Herbert"}')
        response = conn.getresponse()
        assert response.status == 415
        assert json.loads(response.read()) == {"error": "Content-Type must be application/json"}
    finally:
        conn.close()


def test_concurrent_creates_get_unique_ids(server):
    def create(i):
        return request(server, "POST", "/books", {"title": f"Book {i}", "author": "Author"})

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(create, range(50)))

    assert all(status == 201 for status, _, _ in results)
    ids = {book["id"] for _, _, book in results}
    assert len(ids) == 50
    status, _, listed = request(server, "GET", "/books")
    assert status == 200
    assert {book["id"] for book in listed} == ids


def test_parse_args_defaults_and_environment(monkeypatch):
    for name in ("BOOKS_API_HOST", "BOOKS_API_PORT", "BOOKS_API_DB"):
        monkeypatch.delenv(name, raising=False)
    args = parse_args([])
    assert (args.host, args.port, args.db) == ("127.0.0.1", 8000, "books.db")

    monkeypatch.setenv("BOOKS_API_PORT", "9090")
    monkeypatch.setenv("BOOKS_API_DB", "/tmp/other.db")
    args = parse_args([])
    assert (args.port, args.db) == (9090, "/tmp/other.db")

    args = parse_args(["--host", "0.0.0.0", "--port", "1234", "--db", "x.db"])
    assert (args.host, args.port, args.db) == ("0.0.0.0", 1234, "x.db")
