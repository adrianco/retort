"""End-to-end test over real HTTP against the threaded wsgiref server."""

import json
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

from bookapi import create_app
from bookapi.__main__ import ThreadingWSGIServer


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def base_url(tmp_path):
    app = create_app(str(tmp_path / "books.db"))
    server = make_server("127.0.0.1", 0, app, server_class=ThreadingWSGIServer,
                         handler_class=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    app.store.close()


def call(method, url, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, json.loads(raw) if raw else None


def test_full_crud_lifecycle_over_http(base_url):
    assert call("GET", f"{base_url}/health") == (200, {"status": "ok"})

    status, book = call("POST", f"{base_url}/books",
                        {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"})
    assert status == 201
    url = f"{base_url}/books/{book['id']}"

    assert call("GET", url) == (200, book)
    assert call("GET", f"{base_url}/books?author=frank%20herbert") == (200, [book])

    status, updated = call("PUT", url, {"title": "Dune Messiah", "author": "Frank Herbert"})
    assert status == 200 and updated["title"] == "Dune Messiah"

    assert call("DELETE", url) == (204, None)
    assert call("GET", url)[0] == 404
    assert call("POST", f"{base_url}/books", {"author": "No Title"})[0] == 400
