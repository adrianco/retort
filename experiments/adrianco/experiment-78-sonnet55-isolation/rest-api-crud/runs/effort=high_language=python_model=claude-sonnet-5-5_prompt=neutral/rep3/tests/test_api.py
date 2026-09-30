import http.client
import json
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ["BOOKS_QUIET"] = "1"

from bookapi import make_server  # noqa: E402


@pytest.fixture()
def api(tmp_path):
    server = make_server("127.0.0.1", 0, str(tmp_path / "test.db"))
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    port = server.server_address[1]

    def call(method, path, body=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        data = raw if raw is not None else (json.dumps(body) if body is not None else None)
        conn.request(method, path, body=data, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        text = resp.read().decode()
        conn.close()
        return resp.status, (json.loads(text) if text else None)

    yield call
    server.shutdown()
    server.server_close()


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(api):
    assert api("GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(api):
    status, created = api("POST", "/books", BOOK)
    assert status == 201
    assert created["id"] and created["title"] == "Dune" and created["year"] == 1965
    assert api("GET", f"/books/{created['id']}") == (200, created)


def test_list_and_author_filter(api):
    api("POST", "/books", BOOK)
    api("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(api("GET", "/books")[1]) == 2
    status, rows = api("GET", "/books?author=Jane%20Austen")
    assert status == 200 and [r["title"] for r in rows] == ["Emma"]
    assert api("GET", "/books?author=Nobody") == (200, [])


def test_update(api):
    _, created = api("POST", "/books", BOOK)
    status, updated = api("PUT", f"/books/{created['id']}", {**BOOK, "title": "Dune Messiah"})
    assert status == 200 and updated["title"] == "Dune Messiah"
    assert api("GET", f"/books/{created['id']}")[1]["title"] == "Dune Messiah"


def test_delete(api):
    _, created = api("POST", "/books", BOOK)
    assert api("DELETE", f"/books/{created['id']}") == (204, None)
    assert api("GET", f"/books/{created['id']}")[0] == 404
    assert api("DELETE", f"/books/{created['id']}")[0] == 404


def test_not_found(api):
    assert api("GET", "/books/999")[0] == 404
    assert api("PUT", "/books/999", BOOK)[0] == 404
    assert api("GET", "/nope")[0] == 404


@pytest.mark.parametrize("payload", [
    {"author": "X"},
    {"title": "X"},
    {"title": "  ", "author": "X"},
    {"title": "X", "author": ""},
    {"title": 5, "author": "X"},
    {"title": "X", "author": "Y", "year": "1999"},
    {"title": "X", "author": "Y", "year": True},
    {"title": "X", "author": "Y", "isbn": 123},
    [],
])
def test_validation_rejected(api, payload):
    status, body = api("POST", "/books", payload)
    assert status == 400 and body["error"] == "validation failed"
    assert api("GET", "/books")[1] == []


def test_update_validation(api):
    _, created = api("POST", "/books", BOOK)
    assert api("PUT", f"/books/{created['id']}", {"title": "", "author": "A"})[0] == 400


def test_invalid_json(api):
    assert api("POST", "/books", raw="{not json")[0] == 400


def test_method_not_allowed(api):
    assert api("DELETE", "/books")[0] == 405
    assert api("POST", "/health")[0] == 405
