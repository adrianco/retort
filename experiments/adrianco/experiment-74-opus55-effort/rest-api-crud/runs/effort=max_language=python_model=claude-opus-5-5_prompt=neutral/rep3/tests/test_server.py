"""End-to-end tests that talk to the API over real HTTP connections."""

from __future__ import annotations

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
from typing import Any

import pytest
from flask import Flask
from werkzeug.serving import make_server

from bookapi.__main__ import main

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def call(method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    """Send a request; return the status code and the decoded JSON body (None if empty)."""
    data = None if payload is None else json.dumps(payload).encode()
    headers = {} if payload is None else {"Content-Type": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as error:
        with error:  # it wraps the open response, which must be closed too
            status, body = error.code, error.read()
    return status, json.loads(body) if body else None


@pytest.fixture
def base_url(app):
    """Serve the test app on a free local port for the duration of a test."""
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)


def test_crud_round_trip_over_http(base_url):
    status, book = call("POST", f"{base_url}/books",
                        {"title": "Dune", "author": "Frank Herbert", "year": 1965})
    assert status == 201
    url = f"{base_url}/books/{book['id']}"

    assert call("GET", url) == (200, book)
    assert call("GET", f"{base_url}/books?author=herbert") == (200, [book])

    status, updated = call("PUT", url, {"title": "Dune Messiah", "author": "Frank Herbert"})
    assert status == 200
    assert updated == {"id": book["id"], "title": "Dune Messiah", "author": "Frank Herbert",
                       "year": None, "isbn": None}

    assert call("DELETE", url) == (204, None)
    assert call("GET", url) == (404, {"error": f"Book {book['id']} not found"})


def test_python_m_bookapi_serves_the_api(tmp_path):
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = {**os.environ, "HOST": "127.0.0.1", "PORT": str(port),
           "BOOKS_DB_PATH": str(tmp_path / "books.db")}
    log_path = tmp_path / "server.log"
    with log_path.open("w") as log:
        server = subprocess.Popen([sys.executable, "-m", "bookapi"], cwd=PROJECT_ROOT, env=env,
                                  stdout=log, stderr=subprocess.STDOUT)
    try:
        assert _wait_for(f"{base_url}/health", server, log_path) == (
            200, {"status": "ok", "database": "ok"})
        status, book = call("POST", f"{base_url}/books", {"title": "Dune", "author": "Frank Herbert"})
        assert status == 201
        assert call("GET", f"{base_url}/books") == (200, [book])
    finally:
        server.terminate()
        server.wait(timeout=10)
    assert (tmp_path / "books.db").exists()


@pytest.fixture
def flask_runs(monkeypatch):
    """Record the options of every Flask.run call instead of starting a server."""
    runs: list[dict[str, Any]] = []
    monkeypatch.setattr(Flask, "run", lambda app, **options: runs.append(options))
    return runs


def test_main_uses_the_environment_settings(monkeypatch, tmp_path, flask_runs):
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("BOOKS_DB_PATH", str(tmp_path / "data" / "books.db"))

    main()

    assert flask_runs == [{"host": "0.0.0.0", "port": 9000}]
    assert (tmp_path / "data" / "books.db").exists()


@pytest.mark.parametrize("value", [None, ""], ids=["unset", "empty"])
def test_main_falls_back_to_defaults(monkeypatch, tmp_path, flask_runs, value):
    monkeypatch.chdir(tmp_path)  # the default database is created in the working directory
    for name in ("HOST", "PORT", "BOOKS_DB_PATH"):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    main()

    assert flask_runs == [{"host": "127.0.0.1", "port": 8000}]
    assert (tmp_path / "books.db").exists()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for(url: str, server: subprocess.Popen, log_path: Path,
              timeout: float = 15.0) -> tuple[int, Any]:
    """Poll *url* until the freshly started *server* answers it."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            return call("GET", url)
        except (urllib.error.URLError, ConnectionError):
            if server.poll() is not None:
                pytest.fail(f"server exited with code {server.returncode}:\n{log_path.read_text()}")
            if time.monotonic() > deadline:
                pytest.fail(f"server did not answer within {timeout}s:\n{log_path.read_text()}")
            time.sleep(0.1)
