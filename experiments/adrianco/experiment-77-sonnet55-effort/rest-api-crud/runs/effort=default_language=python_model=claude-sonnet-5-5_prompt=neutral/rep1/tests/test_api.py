import json
import os
import sys
import threading
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_server  # noqa: E402


@pytest.fixture
def base(tmp_path):
    srv = create_server(port=0, db_path=str(tmp_path / "t.db"))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def call(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


def test_health(base):
    assert call("GET", base + "/health") == (200, {"status": "ok"})


def test_create_and_get(base):
    status, b = call("POST", base + "/books", BOOK)
    assert status == 201 and b["id"] and b["title"] == "Dune"
    assert call("GET", f"{base}/books/{b['id']}") == (200, b)


def test_validation(base):
    assert call("POST", base + "/books", {"author": "x"})[0] == 400
    assert call("POST", base + "/books", {"title": " ", "author": "x"})[0] == 400
    assert call("POST", base + "/books", {"title": "t", "author": "a", "year": "1999"})[0] == 400


def test_list_and_filter(base):
    call("POST", base + "/books", BOOK)
    call("POST", base + "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(call("GET", base + "/books")[1]) == 2
    s, res = call("GET", base + "/books?author=Jane%20Austen")
    assert [b["title"] for b in res] == ["Emma"]


def test_update(base):
    _, b = call("POST", base + "/books", BOOK)
    s, u = call("PUT", f"{base}/books/{b['id']}", {**BOOK, "title": "Dune Messiah"})
    assert s == 200 and u["title"] == "Dune Messiah"
    assert call("PUT", f"{base}/books/{b['id']}", {"title": "x"})[0] == 400
    assert call("PUT", base + "/books/999", BOOK)[0] == 404


def test_delete(base):
    _, b = call("POST", base + "/books", BOOK)
    assert call("DELETE", f"{base}/books/{b['id']}")[0] == 204
    assert call("GET", f"{base}/books/{b['id']}")[0] == 404
    assert call("DELETE", f"{base}/books/{b['id']}")[0] == 404
