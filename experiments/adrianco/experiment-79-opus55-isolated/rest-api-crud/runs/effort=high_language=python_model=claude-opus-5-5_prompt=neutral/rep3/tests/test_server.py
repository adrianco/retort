"""End-to-end tests against a real HTTP server and an on-disk SQLite file."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

from books_api import BookRepository, create_app
from books_api.__main__ import ThreadingWSGIServer, parse_args


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args) -> None:
        pass


@pytest.fixture
def base_url(tmp_path):
    app = create_app(str(tmp_path / "books.db"))
    server = make_server(
        "127.0.0.1", 0, app, server_class=ThreadingWSGIServer, handler_class=QuietHandler
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        app.repository.close()


def call(method: str, url: str, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read()
        status = error.code
    return status, json.loads(raw) if raw else None


def test_crud_round_trip_over_http(base_url):
    assert call("GET", f"{base_url}/health") == (200, {"status": "ok"})

    status, book = call(
        "POST", f"{base_url}/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965}
    )
    assert status == 201
    book_url = f"{base_url}/books/{book['id']}"

    assert call("GET", book_url) == (200, book)
    assert call("GET", f"{base_url}/books?author=Frank%20Herbert") == (200, [book])

    status, updated = call("PUT", book_url, {"title": "Dune", "author": "F. Herbert"})
    assert status == 200
    assert updated == {**book, "author": "F. Herbert", "year": None}

    assert call("POST", f"{base_url}/books", {"title": "No author"})[0] == 400
    assert call("DELETE", book_url) == (204, None)
    assert call("GET", book_url)[0] == 404


def test_concurrent_creates_get_distinct_ids(base_url):
    results = []

    def create(n: int) -> None:
        results.append(call("POST", f"{base_url}/books", {"title": f"Book {n}", "author": "A"}))

    threads = [threading.Thread(target=create, args=(n,)) for n in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert [status for status, _ in results] == [201] * 20
    assert sorted(book["id"] for _, book in results) == list(range(1, 21))
    assert len(call("GET", f"{base_url}/books")[1]) == 20


def test_books_persist_across_restarts(tmp_path):
    db_path = str(tmp_path / "books.db")
    first = BookRepository(db_path)
    created = first.create({"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": None})
    first.close()

    second = BookRepository(db_path)
    try:
        assert second.list_books() == [created]
    finally:
        second.close()


def test_cli_arguments_and_environment(monkeypatch):
    monkeypatch.delenv("BOOKS_HOST", raising=False)
    monkeypatch.setenv("BOOKS_PORT", "9001")
    monkeypatch.setenv("BOOKS_DB", "/tmp/env.db")

    args = parse_args([])
    assert (args.host, args.port, args.db) == ("127.0.0.1", 9001, "/tmp/env.db")

    args = parse_args(["--host", "0.0.0.0", "--port", "8080", "--db", "cli.db"])
    assert (args.host, args.port, args.db) == ("0.0.0.0", 8080, "cli.db")
