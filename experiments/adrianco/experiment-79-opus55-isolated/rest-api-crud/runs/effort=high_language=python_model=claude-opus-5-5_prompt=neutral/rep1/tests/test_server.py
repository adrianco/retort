"""End-to-end tests over a real socket and a real database file."""

import json
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pytest

from bookapi import create_app
from bookapi.app import make_threaded_server


def call(base_url, method, path, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(base_url + path, data=data, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read()
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "books.db")


@pytest.fixture
def base_url(db_path):
    app = create_app(db_path)
    server = make_threaded_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    thread.join()
    app.store.close()


def test_crud_round_trip_over_http(base_url):
    assert call(base_url, "GET", "/health") == (200, {"status": "ok"})

    status, book = call(base_url, "POST", "/books", {"title": "Dune", "author": "Frank Herbert"})
    assert status == 201
    url = f"/books/{book['id']}"

    assert call(base_url, "GET", url) == (200, book)
    assert call(base_url, "GET", "/books?author=Frank%20Herbert") == (200, [book])

    updated = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    assert call(base_url, "PUT", url, updated) == (200, {"id": book["id"], **updated})

    status, error = call(base_url, "POST", "/books", {"title": "No author"})
    assert status == 400
    assert error["details"] == {"author": "author is required"}

    assert call(base_url, "DELETE", url) == (204, None)
    assert call(base_url, "GET", url)[0] == 404


def test_concurrent_writes(base_url):
    def create(n):
        return call(base_url, "POST", "/books", {"title": f"Book {n}", "author": "Anon"})

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(create, range(40)))

    assert all(status == 201 for status, _ in results)
    assert len({book["id"] for _, book in results}) == 40
    status, books = call(base_url, "GET", "/books")
    assert status == 200
    assert {book["title"] for book in books} == {f"Book {n}" for n in range(40)}


def test_books_persist_across_restarts(db_path):
    first = create_app(db_path)
    book = first.store.create({"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": None})
    first.store.close()

    second = create_app(db_path)
    try:
        assert second.store.list() == [book]
    finally:
        second.store.close()
