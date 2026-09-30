"""End-to-end smoke test over a real socket using the bundled server."""

import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

from bookapi import create_app
from bookapi.__main__ import ThreadingWSGIServer

SRC = Path(__file__).resolve().parent.parent / "src"


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def base_url(tmp_path):
    app = create_app(str(tmp_path / "books.db"))
    server = make_server(
        "127.0.0.1", 0, app, server_class=ThreadingWSGIServer, handler_class=QuietHandler
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    app.close()


def call(method, url, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as err:
        with err:  # HTTPError is an open response; close it
            raw = err.read()
            return err.code, (json.loads(raw) if raw else None)


def test_full_crud_lifecycle_over_http(base_url):
    assert call("GET", f"{base_url}/health") == (200, {"status": "ok"})

    status, created = call(
        "POST", f"{base_url}/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965}
    )
    assert status == 201
    book_url = f"{base_url}/books/{created['id']}"

    assert call("GET", book_url) == (200, created)
    assert call("GET", f"{base_url}/books?author=Frank%20Herbert") == (200, [created])

    status, updated = call("PUT", book_url, {"year": 1966})
    assert (status, updated["year"]) == (200, 1966)

    assert call("DELETE", book_url) == (204, None)
    assert call("GET", book_url)[0] == 404


def test_python_dash_m_bookapi_serves_and_persists(tmp_path):
    """Launch the documented entry point in a subprocess and talk to it."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    db = tmp_path / "cli.db"
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    proc = subprocess.Popen(
        [sys.executable, "-m", "bookapi", "--port", str(port), "--db", str(db)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                assert call("GET", f"{url}/health") == (200, {"status": "ok"})
                break
            except urllib.error.URLError:
                time.sleep(0.1)
        else:
            pytest.fail("server did not start")
        assert call("POST", f"{url}/books", {"title": "T", "author": "A"})[0] == 201
    finally:
        proc.terminate()
        proc.wait(timeout=10)

    assert db.exists()  # the book went to the SQLite file given by --db


def test_validation_error_over_http(base_url):
    status, body = call("POST", f"{base_url}/books", {"title": "No author"})
    assert status == 400
    assert "author" in body["details"]
