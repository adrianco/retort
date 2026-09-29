import json
import os
import sys
import threading
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import create_server  # noqa: E402


@pytest.fixture()
def base(tmp_path):
    srv = create_server(str(tmp_path / "t.db"), port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def call(method, url, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None


def test_health(base):
    assert call("GET", base + "/health") == (200, {"status": "ok"})


def test_create_and_get(base):
    s, b = call("POST", base + "/books",
                {"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"})
    assert s == 201 and b["id"] == 1
    assert call("GET", base + "/books/1") == (200, b)


def test_validation(base):
    assert call("POST", base + "/books", {"author": "x"})[0] == 400
    assert call("POST", base + "/books", {"title": "x", "author": " "})[0] == 400
    assert call("POST", base + "/books", {"title": "x", "author": "y", "year": "1"})[0] == 400


def test_list_filter(base):
    call("POST", base + "/books", {"title": "A", "author": "X"})
    call("POST", base + "/books", {"title": "B", "author": "Y"})
    assert len(call("GET", base + "/books")[1]) == 2
    s, b = call("GET", base + "/books?author=Y")
    assert s == 200 and [x["title"] for x in b] == ["B"]


def test_update_delete(base):
    call("POST", base + "/books", {"title": "A", "author": "X"})
    s, b = call("PUT", base + "/books/1", {"title": "A2", "author": "X", "year": 2000})
    assert s == 200 and b["title"] == "A2" and b["year"] == 2000
    assert call("PUT", base + "/books/1", {"title": ""})[0] == 400
    assert call("DELETE", base + "/books/1")[0] == 204
    assert call("GET", base + "/books/1")[0] == 404
    assert call("DELETE", base + "/books/1")[0] == 404
