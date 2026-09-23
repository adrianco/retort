"""End-to-end tests over real HTTP against a file-backed SQLite database."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from books_api.__main__ import make_books_server
from books_api.db import BookRepository


@pytest.fixture
def server(tmp_path):
    db_path = tmp_path / "books.db"
    srv = make_books_server("127.0.0.1", 0, str(db_path), quiet=True)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    host, port = srv.server_address[:2]
    yield f"http://{host}:{port}", db_path
    srv.shutdown()
    srv.server_close()
    srv.get_app().repo.close()


def call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        raw = err.read()
        return err.code, json.loads(raw) if raw else None


def test_full_crud_lifecycle_over_http(server):
    base, _ = server
    assert call(base, "GET", "/health") == (200, {"status": "ok", "database": "ok"})

    status, book = call(base, "POST", "/books",
                        {"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937})
    assert status == 201
    book_id = book["id"]

    status, books = call(base, "GET", "/books?author=J.R.R.%20Tolkien")
    assert status == 200 and [b["id"] for b in books] == [book_id]

    status, updated = call(base, "PUT", f"/books/{book_id}",
                           {"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1938})
    assert status == 200 and updated["year"] == 1938

    assert call(base, "DELETE", f"/books/{book_id}") == (204, None)
    assert call(base, "GET", f"/books/{book_id}")[0] == 404

    status, err = call(base, "POST", "/books", {"year": 2001})
    assert status == 400 and set(err["details"]) == {"title", "author"}


def test_data_persists_in_sqlite_file(server):
    base, db_path = server
    call(base, "POST", "/books", {"title": "Emma", "author": "Jane Austen", "year": 1815})

    repo = BookRepository(str(db_path))
    try:
        assert [b["title"] for b in repo.list()] == ["Emma"]
    finally:
        repo.close()


def test_concurrent_creates(server):
    base, _ = server
    results = []

    def worker(i):
        results.append(call(base, "POST", "/books", {"title": f"Book {i}", "author": "Many"})[0])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == [201] * 20
    status, books = call(base, "GET", "/books?author=many")
    assert status == 200 and len(books) == 20
    assert len({b["id"] for b in books}) == 20
