import json
import os
import sys
import threading
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bookapi import make_server  # noqa: E402


@pytest.fixture()
def base_url():
    server = make_server(port=0, db_path=":memory:")
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    server.store.close()


def call(base, method, path, body=None, raw=None):
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read()
            return resp.status, json.loads(text) if text else None
    except urllib.error.HTTPError as err:
        text = err.read()
        return err.code, json.loads(text) if text else None


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(base_url):
    assert call(base_url, "GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(base_url):
    status, created = call(base_url, "POST", "/books", BOOK)
    assert status == 201
    assert created == {"id": created["id"], **BOOK}
    assert call(base_url, "GET", f"/books/{created['id']}") == (200, created)


def test_create_minimal_book(base_url):
    status, created = call(base_url, "POST", "/books", {"title": "T", "author": "A"})
    assert status == 201 and created["year"] is None and created["isbn"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"author": "A"},
        {"title": "T"},
        {"title": "  ", "author": "A"},
        {"title": "T", "author": 5},
        {"title": "T", "author": "A", "year": "1999"},
        {"title": "T", "author": "A", "year": True},
        {"title": "T", "author": "A", "isbn": 123},
        ["not", "an", "object"],
    ],
)
def test_create_validation(base_url, payload):
    status, body = call(base_url, "POST", "/books", payload)
    assert status == 400 and "error" in body
    assert call(base_url, "GET", "/books") == (200, [])


def test_invalid_json(base_url):
    status, _ = call(base_url, "POST", "/books", raw=b"{nope")
    assert status == 400


def test_list_and_author_filter(base_url):
    call(base_url, "POST", "/books", BOOK)
    call(base_url, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    call(base_url, "POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})
    _, everything = call(base_url, "GET", "/books")
    assert len(everything) == 3
    _, austen = call(base_url, "GET", "/books?author=Jane%20Austen")
    assert [b["title"] for b in austen] == ["Emma", "Persuasion"]
    assert call(base_url, "GET", "/books?author=Nobody") == (200, [])


def test_update(base_url):
    _, created = call(base_url, "POST", "/books", BOOK)
    new = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "x"}
    status, updated = call(base_url, "PUT", f"/books/{created['id']}", new)
    assert status == 200 and updated == {"id": created["id"], **new}
    assert call(base_url, "GET", f"/books/{created['id']}")[1] == updated


def test_update_validation_and_missing(base_url):
    _, created = call(base_url, "POST", "/books", BOOK)
    assert call(base_url, "PUT", f"/books/{created['id']}", {"title": "only"})[0] == 400
    assert call(base_url, "PUT", "/books/999", BOOK)[0] == 404


def test_delete(base_url):
    _, created = call(base_url, "POST", "/books", BOOK)
    assert call(base_url, "DELETE", f"/books/{created['id']}") == (204, None)
    assert call(base_url, "GET", f"/books/{created['id']}")[0] == 404
    assert call(base_url, "DELETE", f"/books/{created['id']}")[0] == 404


@pytest.mark.parametrize("bad_id", ["999", "abc", "-1", "0"])
def test_not_found_ids(base_url, bad_id):
    assert call(base_url, "GET", f"/books/{bad_id}")[0] == 404


def test_unknown_route_and_method(base_url):
    assert call(base_url, "GET", "/nope")[0] == 404
    assert call(base_url, "DELETE", "/books")[0] == 405
